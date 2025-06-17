import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# CONFIGURAÇÃO
st.set_page_config(page_title="Painel Comercial", layout="wide")
st.image("logo_alfa-protecao-veicular_Bs4CuH.png", width=150)
st.markdown("<h1 style='margin-top: -10px;'>📊 Painel Comercial - Dunorte</h1>", unsafe_allow_html=True)

# LEITURA DOS DADOS
df = pd.read_csv("VENDAS.csv", encoding="latin1", sep=";")
cotacoes = pd.read_excel("COTACOES.xlsx")

# AJUSTES VENDAS
df.columns = df.columns.str.strip()
df.rename(columns={
    'Data Cadastro': 'DataVenda',
    'Valor Produtos + Taxa Adm.': 'ValorVenda',
    'Gestor': 'Gestor',
    'Cooperativa': 'Cooperativa'
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

# AJUSTES COTAÇÕES
cotacoes.columns = cotacoes.columns.str.strip()
cotacoes.rename(columns={
    cotacoes.columns[0]: 'DataCotacao',
    cotacoes.columns[40]: 'Cooperativa',
    cotacoes.columns[49]: 'Situacao'
}, inplace=True)

cotacoes['DataCotacao'] = pd.to_datetime(cotacoes['DataCotacao'], dayfirst=True, errors='coerce')
cotacoes = cotacoes.dropna(subset=['DataCotacao'])
cotacoes['Mes'] = cotacoes['DataCotacao'].dt.to_period("M")

# REFERÊNCIA DE DATA
data_min = df['DataVenda'].min().strftime("%d/%m")
data_max = df['DataVenda'].max().strftime("%d/%m")
st.markdown(f"<p style='color:gray'>📅 <b>Referência dos dados:</b> de <b>{data_min}</b> até <b>{data_max}</b></p>", unsafe_allow_html=True)

# === FILTROS ===
meses_disponiveis = sorted(df['Mes'].astype(str).unique())
mes_selecionado = st.selectbox("📅 Selecione o mês", meses_disponiveis, index=len(meses_disponiveis)-1)
gestores_disponiveis = ['Todos'] + sorted(df['Gestor'].dropna().unique().tolist())
gestor_selecionado = st.selectbox("🧑‍💼 Filtrar por Gestor", gestores_disponiveis)

df_filtrado = df[df['Mes'].astype(str) == mes_selecionado]
cotacoes_filtrado = cotacoes[cotacoes['Mes'].astype(str) == mes_selecionado]

if gestor_selecionado != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['Gestor'] == gestor_selecionado]

# MÉTRICAS
total_vendas = len(df_filtrado)
dias_corridos = datetime.now().day
dias_mes = pd.Period(mes_selecionado).days_in_month
fator_projecao = dias_mes / dias_corridos
projecao = int(total_vendas * fator_projecao)
faturamento = df_filtrado['ValorVenda'].sum()
ticket = df_filtrado['ValorVenda'].mean()

total_cotacoes = len(cotacoes_filtrado)
vendas_concretizadas = len(cotacoes_filtrado[cotacoes_filtrado['Situacao'].str.lower() == 'venda concretizada'])
conversao = (vendas_concretizadas / total_cotacoes * 100) if total_cotacoes > 0 else 0

# === CARTÕES ===
def card(label, value):
    st.markdown(f"""
    <div style='background-color:#f0f2f6;padding:20px;border-radius:10px;
                box-shadow: 2px 2px 8px rgba(0,0,0,0.15);text-align:center'>
        <h5 style='margin-bottom:5px;'>{label}</h5>
        <h2 style='margin-top:0px;'>{value}</h2>
    </div>
    """, unsafe_allow_html=True)

col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
with col1: card("Total de Vendas", total_vendas)
with col2: card("Projeção", projecao)
with col3: card("Cotações", total_cotacoes)
with col4: card("Vendas Concretizadas", vendas_concretizadas)
with col5: card("Conversão", f"{conversao:.1f}%")
with col6: card("Faturamento (R$)", f"R$ {faturamento:,.2f}".replace(".", ","))
with col7: card("Ticket Médio (R$)", f"R$ {ticket:,.2f}".replace(".", ","))

# === TABELA POR GESTOR
st.subheader("📌 Desempenho por Gestor")
meta = 150
por_gestor = df_filtrado.groupby('Gestor').agg(
    Vendas=('ValorVenda', 'count'),
    Faturamento=('ValorVenda', 'sum'),
    Ticket=('ValorVenda', 'mean')
).reset_index()
por_gestor['Projeção'] = (por_gestor['Vendas'] * fator_projecao).round(0).astype(int)
por_gestor['% Meta'] = ((por_gestor['Vendas'] / meta) * 100).round(1).astype(str) + "%"
st.dataframe(por_gestor.style.format({
    'Faturamento': 'R$ {:,.2f}'.format,
    'Ticket': 'R$ {:,.2f}'.format,
    'Vendas': '{:.0f}',
    'Projeção': '{:.0f}'
}).set_properties(**{'text-align': 'center'}), use_container_width=True)

