import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, date

# === CONFIGURAÇÃO ===
st.set_page_config(page_title="Painel Comercial - Dunorte", layout="wide")
st.image("logo_alfa-protecao-veicular_Bs4CuH.png", width=150)
st.markdown("<h1 style='margin-top: -10px;'>📊 Painel Comercial - Dunorte</h1>", unsafe_allow_html=True)

# === FILTROS ===
with st.sidebar:
    st.subheader("📅 Filtrar por Gestor")
    data_inicial = st.date_input("Início", value=pd.to_datetime("2025-06-01"))
    data_final = st.date_input("Fim", value=pd.to_datetime("2025-06-18"))
    gestor_selecionado = st.selectbox("👤 Filtrar por Gestor", ['Todos'])

# === IMPORTAR BASE DE VENDAS ===
df = pd.read_csv("VENDAS.csv", encoding="latin1", sep=";")
df.columns = df.columns.str.strip()
df.rename(columns={
    'Data Cadastro': 'DataVenda',
    'Valor Produtos + Taxa Adm.': 'ValorVenda',
    'Cooperativa': 'Cooperativa',
    'Gestor': 'Gestor'
}, inplace=True)
df['DataVenda'] = pd.to_datetime(df['DataVenda'], dayfirst=True, errors='coerce')
df = df.dropna(subset=['DataVenda'])
df['ValorVenda'] = df['ValorVenda'].astype(str).str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
df['Mes'] = df['DataVenda'].dt.to_period("M")

# === IMPORTAR BASE DE COTAÇÕES ===
cotacoes = pd.read_excel("COTACOES.xlsx")
cotacoes.columns = cotacoes.columns.str.strip()
cotacoes['Situacao'] = cotacoes['Situacao'].astype(str).str.strip().str.lower()
cotacoes['Data'] = pd.to_datetime(cotacoes.iloc[:, 0], errors='coerce')
cotacoes = cotacoes.dropna(subset=['Data'])

# === FILTRO POR DATA ===
hoje = pd.to_datetime("today")
data_final = min(data_final, hoje)
df = df[(df['DataVenda'] >= pd.to_datetime(data_inicial)) & (df['DataVenda'] <= pd.to_datetime(data_final))]
cotacoes = cotacoes[(cotacoes['Data'] >= pd.to_datetime(data_inicial)) & (cotacoes['Data'] <= pd.to_datetime(data_final))]

# === FILTRO POR GESTOR ===
if gestor_selecionado != 'Todos':
    df = df[df['Gestor'] == gestor_selecionado]

# === PROJEÇÃO COM BASE EM DIAS ÚTEIS ===
dias_trabalhados = np.busday_count(np.datetime64(data_inicial), np.datetime64(min(hoje, data_final)))
dias_mes = np.busday_count(np.datetime64(data_inicial), np.datetime64(date(data_inicial.year, data_inicial.month, 30)))  # ajuste conforme mês
fator_projecao = dias_mes / dias_trabalhados if dias_trabalhados > 0 else 1

# === RESUMO GERAL ===
total_vendas = len(df)
projecao_geral = int(total_vendas * fator_projecao)
soma_faturamento = df['ValorVenda'].sum()
ticket_medio = df['ValorVenda'].mean()

# Cotações
total_cotacoes = len(cotacoes)
vendas_concretizadas = cotacoes[cotacoes['Situacao'] == 'vendas concretizadas']
total_vendas_cotacoes = len(vendas_concretizadas)
conversao = (total_vendas_cotacoes / total_cotacoes) * 100 if total_cotacoes > 0 else 0

# === CARTÕES ===
def card(label, value):
    st.markdown(f"""
        <div style='background-color:#f9f9f9;padding:20px 10px;border-radius:10px;
                    box-shadow: 2px 2px 6px rgba(0,0,0,0.1);text-align:center;
                    height:120px;display:flex;flex-direction:column;justify-content:center'>
            <h6 style='margin:0;font-size:15px;'>{label}</h6>
            <h3 style='margin:5px 0;'>{value}</h3>
        </div>
    """, unsafe_allow_html=True)

col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
with col1: card("Total de Vendas", total_vendas)
with col2: card("Projeção", projecao_geral)
with col3: card("Cotações", total_cotacoes)
with col4: card("Vendas Fechadas", total_vendas_cotacoes)
with col5: card("Conversão", f"{conversao:.1f}%")
with col6: card("Faturamento (R$)", f"R$ {soma_faturamento/1000:,.1f}k")
with col7: card("Ticket Médio (R$)", f"R$ {ticket_medio:,.2f}")

# === TABELA COOPERATIVA ===
vendas_agrupadas = df.groupby('Cooperativa').agg(
    Vendas=('ValorVenda', 'count'),
    Faturamento=('ValorVenda', 'sum'),
    Ticket_Medio=('ValorVenda', 'mean')
).reset_index()
vendas_agrupadas['Projecao'] = (vendas_agrupadas['Vendas'] * fator_projecao).round(0).astype(int)

cotacoes_por_coop = cotacoes.groupby('Cooperativa').agg(
    Cotacoes=('Situacao', 'count'),
    Fechadas=('Situacao', lambda x: (x == 'vendas concretizadas').sum())
).reset_index()
cotacoes_por_coop['% Conversão'] = (cotacoes_por_coop['Fechadas'] / cotacoes_por_coop['Cotacoes'] * 100).fillna(0).round(1)

final = pd.merge(vendas_agrupadas, cotacoes_por_coop, on='Cooperativa', how='outer').fillna(0)
final['Faturamento'] = final['Faturamento'].round(2)
final['Ticket_Medio'] = final['Ticket_Medio'].round(2)

st.subheader("📌 Desempenho por Cooperativa")
st.dataframe(
    final.style.format({
        'Vendas': '{:.0f}',
        'Projecao': '{:.0f}',
        'Cotacoes': '{:.0f}',
        'Fechadas': '{:.0f}',
        '% Conversão': '{:.1f}%',
        'Faturamento': 'R$ {:,.2f}',
        'Ticket_Medio': 'R$ {:,.2f}'
    }).set_properties(**{'text-align': 'center'}),
    use_container_width=True
)

# === GRÁFICO TOP 10 ===
top10 = final.sort_values(by='Projecao', ascending=False).head(10)
st.subheader("🏆 Top 10 Cooperativas - Projeção")
fig, ax = plt.subplots(figsize=(10, 4))
bars = ax.bar(top10['Cooperativa'], top10['Projecao'], color='#1f77b4')
ax.set_xticklabels(top10['Cooperativa'], rotation=45, ha='right', fontsize=8)
for bar in bars:
    ax.annotate(f"{int(bar.get_height())}", xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 3), textcoords="offset points", ha='center', fontsize=8)
st.pyplot(fig)

# === TABELAS DE DESTAQUE ===
atencao = final[final['Projecao'] < final['Vendas']].copy()
destaque = final[final['Projecao'] > final['Vendas']].copy()

atencao['Diferença (%)'] = ((atencao['Projecao'] - atencao['Vendas']) / atencao['Vendas'].replace(0, np.nan) * 100).round(0)
destaque['Diferença (%)'] = ((destaque['Projecao'] - destaque['Vendas']) / destaque['Vendas'].replace(0, np.nan) * 100).round(0)

st.subheader("🔴 Cooperativas a Ter Atenção")
st.dataframe(atencao[['Cooperativa', 'Vendas', 'Projecao', 'Diferença (%)']],
             use_container_width=True)

st.subheader("🟢 Destaques Positivos")
st.dataframe(destaque[['Cooperativa', 'Vendas', 'Projecao', 'Diferença (%)']],
             use_container_width=True)
