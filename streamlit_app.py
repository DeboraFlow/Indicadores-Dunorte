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
df.rename(columns={
    'Data Cadastro': 'DataVenda',
    'Valor Produtos + Taxa Adm.': 'ValorVenda',
    'Cooperativa': 'Cooperativa',
    'Gestor': 'Gestor'
}, inplace=True)
df['DataVenda'] = pd.to_datetime(df['DataVenda'], dayfirst=True, errors='coerce')
df = df.dropna(subset=['DataVenda'])
df['Mes'] = df['DataVenda'].dt.to_period("M")
df['ValorVenda'] = (
    df['ValorVenda'].astype(str)
    .str.replace('R$', '', regex=False)
    .str.replace('.', '', regex=False)
    .str.replace(',', '.', regex=False)
    .str.strip()
    .astype(float)
)

cotacoes = pd.read_excel("COTACOES.xlsx", header=0)
cotacoes.columns = cotacoes.columns.str.strip()
cotacoes['DataCotacao'] = pd.to_datetime(cotacoes.iloc[:, 0], dayfirst=True, errors='coerce')
cotacoes['Mes'] = cotacoes['DataCotacao'].dt.to_period("M")
cotacoes['Cooperativa'] = cotacoes.iloc[:, 41]  # coluna AP
cotacoes['Situacao'] = cotacoes.iloc[:, 49]     # coluna AX

# === FILTROS INTERATIVOS ===
meses_disponiveis = sorted(df['Mes'].astype(str).unique())
mes_selecionado = st.selectbox("🧑‍💼 Filtrar por Gestor", ['Todos'] + sorted(df['Gestor'].dropna().unique().tolist()))
mes_atual = str(max(df['Mes']))
mes_anterior = str(sorted(df['Mes'].unique())[-2]) if len(df['Mes'].unique()) > 1 else None

df_filtrado = df[df['Mes'].astype(str) == mes_atual]
cotacoes_filtrado = cotacoes[cotacoes['Mes'].astype(str) == mes_atual]

if mes_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['Gestor'] == mes_selecionado]

dias_corridos = datetime.now().day
dias_mes = pd.Period(mes_atual).days_in_month
fator_projecao = dias_mes / dias_corridos

# === REFERÊNCIA DOS DADOS ===
data_min = df['DataVenda'].min().strftime('%d/%m')
data_max = df['DataVenda'].max().strftime('%d/%m')
st.markdown(f"📅 **Referência dos dados:** de **{data_min}** até **{data_max}**")

# === MÉTRICAS COMERCIAIS GERAIS ===
total_vendas = len(df_filtrado)
projecao_geral = int(total_vendas * fator_projecao)
soma_faturamento = df_filtrado['ValorVenda'].sum()
ticket_medio = df_filtrado['ValorVenda'].mean()

total_cotacoes = len(cotacoes_filtrado)
vendas_concretizadas = len(cotacoes_filtrado[cotacoes_filtrado['Situacao'].str.lower() == 'venda concretizada'])
taxa_conversao = (vendas_concretizadas / total_cotacoes * 100) if total_cotacoes > 0 else 0

# === FUNÇÃO DE CARTÃO
def card(label, value):
    st.markdown(f"""
        <div style='background-color:#f0f2f6;padding:15px 10px;border-radius:10px;
                    box-shadow:2px 2px 8px rgba(0,0,0,0.1);text-align:center;height:110px'>
            <h5 style='margin-bottom:5px;font-size:16px'>{label}</h5>
            <h2 style='margin-top:0px;font-size:28px'>{value}</h2>
        </div>
        """, unsafe_allow_html=True)

# === EXIBIR CARTÕES ===
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
with col1: card("Total de Vendas", total_vendas)
with col2: card("Projeção", projecao_geral)
with col3: card("Cotações", total_cotacoes)
with col4: card("Vendas Fechadas", vendas_concretizadas)
with col5: card("Conversão", f"{taxa_conversao:.1f}%")
with col6: card("Faturamento (R$)", f"R$ {soma_faturamento:,.2f}".replace('.', ','))
with col7: card("Ticket Médio (R$)", f"R$ {ticket_medio:,.2f}".replace('.', ','))

# === TABELA DESEMPENHO POR COOPERATIVA ===
st.subheader("📌 Desempenho por Cooperativa")
resumo = df_filtrado.groupby('Cooperativa').agg(
    TotalAtual=('ValorVenda', 'count'),
    SomaAtual=('ValorVenda', 'sum'),
    Ticket=('ValorVenda', 'mean')
).reset_index()

cotacoes_resumo = cotacoes_filtrado.groupby('Cooperativa').agg(
    Cotas=('Situacao', 'count'),
    VendasCota=('Situacao', lambda x: (x.str.lower() == 'venda concretizada').sum())
).reset_index()

base = pd.merge(resumo, cotacoes_resumo, on='Cooperativa', how='outer').fillna(0)
base['Projecao'] = (base['TotalAtual'] * fator_projecao).round(0).astype(int)
base['Conversao'] = (base['VendasCota'] / base['Cotas'].replace(0, np.nan) * 100).round(1)
base['Status'] = base['Projecao'] - base['TotalAtual']
base['% Conversão'] = base['Conversao'].astype(str) + '%'

# === TABELA GERAL
st.dataframe(base[['Cooperativa', 'TotalAtual', 'Projecao', 'Cotas', 'VendasCota', '% Conversão', 'SomaAtual', 'Ticket']]
             .rename(columns={
                 'TotalAtual': 'Vendas',
                 'SomaAtual': 'Faturamento',
                 'Ticket': 'Ticket Médio',
                 'Cotas': 'Cotações',
                 'VendasCota': 'Fechadas'
             })
             .style.format({
                 'Faturamento': 'R$ {:,.2f}'.format,
                 'Ticket Médio': 'R$ {:,.2f}'.format,
                 'Vendas': '{:.0f}',
                 'Projecao': '{:.0f}'
             }).set_properties(**{'text-align': 'center'}),
             use_container_width=True)

# === DESTAQUES
st.markdown("### 🟢 Destaques Positivos")
positivos = base[base['Status'] > 0].sort_values(by='Status', ascending=False)
st.dataframe(positivos[['Cooperativa', 'Projecao', 'TotalAtual', 'Status']]
             .rename(columns={'TotalAtual': 'Atual'})
             .style.format({'Projecao': '{:.0f}', 'Atual': '{:.0f}', 'Status': '{:.0f}'})
             .set_properties(**{'text-align': 'center'}),
             use_container_width=True)

st.markdown("### 🔴 Cooperativas a Ter Atenção")
negativos = base[base['Status'] < 0].sort_values(by='Status', ascending=True)
st.dataframe(negativos[['Cooperativa', 'Projecao', 'TotalAtual', 'Status']]
             .rename(columns={'TotalAtual': 'Atual'})
             .style.format({'Projecao': '{:.0f}', 'Atual': '{:.0f}', 'Status': '{:.0f}'})
             .set_properties(**{'text-align': 'center'}),
             use_container_width=True)
