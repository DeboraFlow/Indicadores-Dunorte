import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Painel Comercial - Dunorte", layout="wide")
st.image("logo_alfa-protecao-veicular_Bs4CuH.png", width=150)
st.markdown("<h1 style='margin-top: -10px;'>📊 Painel Comercial - Dunorte</h1>", unsafe_allow_html=True)

# === IMPORTAÇÃO DOS DADOS ===
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

# === IMPORTAÇÃO DAS COTAÇÕES ===
cotacoes = pd.read_excel("COTACOES.xlsx", header=0)
cotacoes.columns = cotacoes.columns.str.strip()
cotacoes.rename(columns={
    cotacoes.columns[0]: 'DataCotacao',
    'AP': 'Cooperativa',
    'AX': 'Situacao'
}, inplace=True)

cotacoes['DataCotacao'] = pd.to_datetime(cotacoes['DataCotacao'], errors='coerce')
cotacoes = cotacoes.dropna(subset=['DataCotacao'])

# === FILTROS DE DATA ===
data_min = df['DataVenda'].min()
data_max = df['DataVenda'].max()
ontem = datetime.now().date() - timedelta(days=1)

periodo = st.date_input("📅 Filtrar por Gestor", value=(data_min, ontem), min_value=data_min, max_value=ontem)
df = df[(df['DataVenda'] >= pd.to_datetime(periodo[0])) & (df['DataVenda'] <= pd.to_datetime(periodo[1]))]
cotacoes_filtrado = cotacoes[(cotacoes['DataCotacao'] >= pd.to_datetime(periodo[0])) & (cotacoes['DataCotacao'] <= pd.to_datetime(periodo[1]))]

# === FILTRO POR GESTOR ===
gestores = ['Todos'] + sorted(df['Gestor'].dropna().unique())
gestor = st.selectbox("🧑‍💼 Filtrar por Gestor", gestores)
if gestor != 'Todos':
    df = df[df['Gestor'] == gestor]

# === VARIÁVEIS DE PROJEÇÃO ===
dias_uteis_mes = 20  # Junho com feriado dia 19
dias_trabalhados = len(pd.bdate_range(periodo[0], ontem))
fator_projecao = dias_uteis_mes / dias_trabalhados if dias_trabalhados else 1

# === RESUMO DAS VENDAS ===
vendas_por_coop = df.groupby('Cooperativa').agg(
    Vendas=('ValorVenda', 'count'),
    Faturamento=('ValorVenda', 'sum'),
    Ticket_Medio=('ValorVenda', 'mean')
).reset_index()

vendas_por_coop['Projecao'] = (vendas_por_coop['Vendas'] * fator_projecao).round(0).astype(int)

# === RESUMO DAS COTAÇÕES ===
cotacoes_por_coop = cotacoes_filtrado.groupby('Cooperativa').agg(
    Cotacoes=('Situacao', 'count'),
    Fechadas=('Situacao', lambda x: (x.str.lower() == 'venda concretizada').sum())
).reset_index()

# === MERGE DAS BASES ===
base = pd.merge(vendas_por_coop, cotacoes_por_coop, on='Cooperativa', how='outer').fillna(0)
base['% Conversão'] = (base['Fechadas'] / base['Cotacoes'].replace(0, np.nan) * 100).round(1).fillna(0).astype(str) + "%"
base['% Conversão Num'] = (base['Fechadas'] / base['Cotacoes'].replace(0, np.nan) * 100).fillna(0)
base['Faturamento'] = base['Faturamento'].round(2)
base['Ticket_Medio'] = base['Ticket_Medio'].round(2)

# === TOTAIS GERAIS ===
total_vendas = int(base['Vendas'].sum())
total_projecao = int(base['Projecao'].sum())
total_cotacoes = int(base['Cotacoes'].sum())
total_fechadas = int(base['Fechadas'].sum())
total_conversao = (total_fechadas / total_cotacoes * 100) if total_cotacoes else 0
faturamento_geral = base['Faturamento'].sum()
ticket_medio_geral = base['Ticket_Medio'].mean()

# === CARTÕES ===
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

with col1:
    st.metric("Total de Vendas", f"{total_vendas}")
with col2:
    st.metric("Projeção", f"{total_projecao}")
with col3:
    st.metric("Cotações", f"{total_cotacoes}")
with col4:
    st.metric("Vendas Fechadas", f"{total_fechadas}")
with col5:
    st.metric("Conversão", f"{total_conversao:.1f}%")
with col6:
    st.metric("Faturamento (R$)", f"R$ {faturamento_geral:,.2f}".replace(".", ","))
with col7:
    st.metric("Ticket Médio (R$)", f"R$ {ticket_medio_geral:,.2f}".replace(".", ","))

# === TABELA PRINCIPAL ===
st.markdown("### 📌 Desempenho por Cooperativa")
st.dataframe(base[[
    'Cooperativa', 'Vendas', 'Projecao', 'Cotacoes', 'Fechadas', '% Conversão',
    'Faturamento', 'Ticket_Medio'
]].style.set_properties(**{'text-align': 'center'}), use_container_width=True)

# === DESTAQUES POSITIVOS E ATENÇÃO ===
destaques = base.copy()
destaques['Diferença %'] = ((destaques['Projecao'] - destaques['Cotacoes']) / destaques['Cotacoes'].replace(0, np.nan) * 100).round(0).fillna(0)

positivos = destaques[destaques['Diferença %'] > 0].sort_values(by='Diferença %', ascending=False)
negativos = destaques[destaques['Diferença %'] < 0].sort_values(by='Diferença %')

st.markdown("### 🟢 Cooperativas com Alta Conversão")
st.dataframe(
    positivos[['Cooperativa', 'Vendas', 'Projecao', 'Diferença %']].style.set_properties(**{'text-align': 'center'}),
    use_container_width=True
)

st.markdown("### 🔴 Cooperativas a Ter Atenção")
st.dataframe(
    negativos[['Cooperativa', 'Vendas', 'Projecao', 'Diferença %']].style.set_properties(**{'text-align': 'center'}),
    use_container_width=True
)

# === GRÁFICO TOP 10 PROJEÇÃO ===
st.markdown("### 📊 Top 10 Cooperativas (Projeção)")
top10 = base.sort_values(by='Projecao', ascending=False).head(10)
fig, ax = plt.subplots(figsize=(10, 4))
bars = ax.bar(top10['Cooperativa'], top10['Projecao'], color='#3399ff')
ax.set_xticklabels(top10['Cooperativa'], rotation=45, ha='right', fontsize=8)
ax.set_ylabel("Projeção")

for bar in bars:
    height = bar.get_height()
    ax.annotate(f'{int(height)}', xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8)

st.pyplot(fig)

