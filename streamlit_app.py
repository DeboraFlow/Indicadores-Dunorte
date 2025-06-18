import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

st.set_page_config(page_title="Painel Comercial - Dunorte", layout="wide")
st.image("logo_alfa-protecao-veicular_Bs4CuH.png", width=150)
st.markdown("<h1 style='margin-top: -10px;'>📊 Painel Comercial - Dunorte</h1>", unsafe_allow_html=True)

# === IMPORTAÇÃO DAS BASES ===
df = pd.read_csv("VENDAS.csv", encoding="latin1", sep=";")
df.columns = df.columns.str.strip()
df.rename(columns={'Data Cadastro': 'DataVenda', 'Valor Produtos + Taxa Adm.': 'ValorVenda', 'Cooperativa': 'Cooperativa', 'Gestor': 'Gestor'}, inplace=True)
df['DataVenda'] = pd.to_datetime(df['DataVenda'], dayfirst=True, errors='coerce')
df = df.dropna(subset=['DataVenda'])
df['ValorVenda'] = df['ValorVenda'].astype(str).str.replace('R$', '').str.replace('.', '').str.replace(',', '.').astype(float)
df['Mes'] = df['DataVenda'].dt.to_period("M")

cotacoes = pd.read_excel("COTACOES.xlsx", header=0)
cotacoes.columns = cotacoes.columns.str.strip()
cotacoes.rename(columns={cotacoes.columns[0]: 'DataCotacao', 'AP': 'Cooperativa', 'AX': 'Situacao'}, inplace=True)
cotacoes['DataCotacao'] = pd.to_datetime(cotacoes['DataCotacao'], errors='coerce')
cotacoes = cotacoes.dropna(subset=['DataCotacao'])

# === FILTROS ===
st.sidebar.markdown("📅 **Filtrar por Gestor**")
data_inicial = st.sidebar.date_input("Início", value=pd.to_datetime("2025-06-01"), key="data_ini")
data_final = st.sidebar.date_input("Fim", value=pd.to_datetime("today"), key="data_fim")

gestores_disponiveis = ['Todos'] + sorted(df['Gestor'].dropna().unique().tolist())
gestor_selecionado = st.sidebar.selectbox("👤 Filtrar por Gestor", gestores_disponiveis)

hoje = pd.to_datetime("today")
data_final = min(data_final, hoje)
dias_trabalhados = np.busday_count(data_inicial.date(), data_final.date())
dias_totais_mes = np.busday_count(datetime(data_inicial.year, data_inicial.month, 1).date(), datetime(data_inicial.year, data_inicial.month + 1, 1).date()) - 1 if data_inicial.month != 12 else 31

# === APLICAR FILTROS NAS BASES ===
vendas_filtrado = df[(df['DataVenda'] >= pd.to_datetime(data_inicial)) & (df['DataVenda'] <= pd.to_datetime(data_final))]
cotacoes_filtrado = cotacoes[(cotacoes['DataCotacao'] >= pd.to_datetime(data_inicial)) & (cotacoes['DataCotacao'] <= pd.to_datetime(data_final))]
if gestor_selecionado != "Todos":
    vendas_filtrado = vendas_filtrado[vendas_filtrado['Gestor'] == gestor_selecionado]

# === INDICADORES GERAIS ===
total_vendas = len(vendas_filtrado)
soma_faturamento = vendas_filtrado['ValorVenda'].sum()
ticket_medio = vendas_filtrado['ValorVenda'].mean()
fator_projecao = dias_totais_mes / dias_trabalhados if dias_trabalhados != 0 else 1
projecao_geral = int(total_vendas * fator_projecao)

total_cotacoes = len(cotacoes_filtrado)
vendas_concretizadas = cotacoes_filtrado[cotacoes_filtrado['Situacao'].str.lower() == 'venda concretizada']
qtde_concretizadas = len(vendas_concretizadas)
percentual_conversao = (qtde_concretizadas / total_cotacoes) * 100 if total_cotacoes else 0

# === CARDS ===
def format_k(value):
    if value >= 1000:
        return f"R$ {value/1000:.1f}k"
    else:
        return f"R$ {value:,.2f}".replace(".", ",")

def card(label, value):
    st.markdown(f"""
        <div style='background-color:#f9f9f9;padding:20px;border-radius:10px;
                    box-shadow: 2px 2px 6px rgba(0,0,0,0.1);text-align:center;display:flex;flex-direction:column;justify-content:center;align-items:center;height:100px'>
            <h5 style='margin-bottom:5px;'>{label}</h5>
            <h2 style='margin-top:0px;'>{value}</h2>
        </div>
    """, unsafe_allow_html=True)

col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
with col1: card("Total de Vendas", f"{total_vendas}")
with col2: card("Projeção", f"{projecao_geral}")
with col3: card("Cotações", f"{total_cotacoes}")
with col4: card("Vendas Fechadas", f"{qtde_concretizadas}")
with col5: card("Conversão", f"{percentual_conversao:.1f}%")
with col6: card("Faturamento (R$)", format_k(soma_faturamento))
with col7: card("Ticket Médio (R$)", format_k(ticket_medio))

# === TABELA GERAL POR COOPERATIVA ===
resumo = vendas_filtrado.groupby("Cooperativa").agg(
    Vendas=("ValorVenda", "count"),
    Faturamento=("ValorVenda", "sum"),
    Ticket_Medio=("ValorVenda", "mean")
).reset_index()
resumo['Projecao'] = (resumo['Vendas'] * fator_projecao).round(0)

cotacoes_agrupadas = cotacoes_filtrado.groupby("Cooperativa").agg(
    Cotacoes=("Situacao", "count"),
    Fechadas=("Situacao", lambda x: (x.str.lower() == "venda concretizada").sum())
).reset_index()
cotacoes_agrupadas['% Conversão'] = (cotacoes_agrupadas['Fechadas'] / cotacoes_agrupadas['Cotacoes'].replace(0, np.nan) * 100).round(1).fillna(0)

base = pd.merge(resumo, cotacoes_agrupadas, how="outer", on="Cooperativa").fillna(0)
base = base[[
    "Cooperativa", "Vendas", "Projecao", "Cotacoes", "Fechadas", "% Conversão", "Faturamento", "Ticket_Medio"
]]
base["Vendas"] = base["Vendas"].astype(int)
base["Projecao"] = base["Projecao"].astype(int)
base["Cotacoes"] = base["Cotacoes"].astype(int)
base["Fechadas"] = base["Fechadas"].astype(int)

st.markdown("### 📌 Desempenho por Cooperativa")
st.dataframe(base.style.format({
    "Faturamento": "R$ {:,.2f}".format,
    "Ticket_Medio": "R$ {:,.2f}".format,
    "% Conversão": "{:.1f}%",
}), use_container_width=True)

# === TOP 10 GRÁFICO PROJEÇÃO
top10 = base.sort_values("Projecao", ascending=False).head(10)
fig, ax = plt.subplots(figsize=(10, 4))
bars = ax.bar(top10["Cooperativa"], top10["Projecao"], color="#4C8BF5")
ax.set_title("Top 10 Cooperativas - Projeção de Vendas", fontsize=12)
ax.set_ylabel("Projeção")
ax.set_xticklabels(top10["Cooperativa"], rotation=45, ha="right", fontsize=8)
for bar in bars:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f'{int(bar.get_height())}', ha='center', va='bottom', fontsize=8)
st.pyplot(fig)

# === TABELAS DESTAQUE / ATENÇÃO
meta_mes = 150
base['% da Meta'] = (base['Vendas'] / meta_mes * 100).round(1)
positivos = base[base['% da Meta'] >= 100].copy()
atencao = base[base['% da Meta'] < 100].copy()

st.markdown("### 🟢 Destaques Positivos")
st.dataframe(positivos[['Cooperativa', 'Vendas', 'Projecao', '% da Meta']].style.format({
    'Vendas': '{:.0f}',
    'Projecao': '{:.0f}',
    '% da Meta': '{:.0f}%'
}), use_container_width=True)

st.markdown("### 🔴 Cooperativas a Ter Atenção")
st.dataframe(atencao[['Cooperativa', 'Vendas', 'Projecao', '% da Meta']].style.format({
    'Vendas': '{:.0f}',
    'Projecao': '{:.0f}',
    '% da Meta': '{:.0f}%'
}), use_container_width=True)

# === REFERÊNCIA DE DATAS
st.markdown(f"<p style='font-size:13px;margin-top:20px;'>📅 Referência dos dados: de <b>{data_inicial.strftime('%d/%m')}</b> até <b>{data_final.strftime('%d/%m')}</b></p>", unsafe_allow_html=True)
