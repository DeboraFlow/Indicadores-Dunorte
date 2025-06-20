import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Painel Comercial Dunorte", layout="wide")
st.markdown("<h1 style='text-align: center;'>📊 Painel Comercial - Dunorte</h1>", unsafe_allow_html=True)

# === SIDEBAR ===
with st.sidebar:
    st.image("logo_alfa-protecao-veicular_Bs4CuH.png", use_container_width=True)
    st.markdown("## 🗓️ Filtro por Gestor e Período")

    data_inicial = st.date_input("Início", value=datetime(2025, 6, 1))
    data_final = st.date_input("Fim", value=datetime(2025, 6, 18))

    data_inicial = pd.to_datetime(data_inicial)
    data_final = pd.to_datetime(data_final)

# === LEITURA ===
vendas = pd.read_csv("VENDAS.csv", sep=";", encoding="latin1")
cotacoes = pd.read_excel("COTACOES.xlsx")

# === TRATAMENTO ===
vendas.columns = [col.strip() for col in vendas.columns]
cotacoes.columns = [col.strip() for col in cotacoes.columns]

vendas['Data Cadastro'] = pd.to_datetime(vendas['Data Cadastro'], errors='coerce')
cotacoes['Data'] = pd.to_datetime(cotacoes['Data'], errors='coerce')

vendas = vendas[vendas['Data Cadastro'].notna()]
cotacoes = cotacoes[cotacoes['Data'].notna()]

# FILTROS DE DATA
vendas = vendas[(vendas['Data Cadastro'] >= data_inicial) & (vendas['Data Cadastro'] <= data_final)]
cotacoes = cotacoes[(cotacoes['Data'] >= data_inicial) & (cotacoes['Data'] <= data_final)]

# GESTOR
if 'GESTOR' in vendas.columns:
    vendas['GESTOR'] = vendas['GESTOR'].astype(str).str.strip()
    gestores = sorted([g for g in vendas['GESTOR'].dropna().unique().tolist() if g and g.upper() != 'NAN'])
    gestor_selecionado = st.sidebar.selectbox("👤 Filtrar por Gestor", ["Todos"] + gestores)

    if gestor_selecionado != "Todos":
        vendas = vendas[vendas['GESTOR'] == gestor_selecionado]
        if 'GESTOR' in cotacoes.columns:
            cotacoes = cotacoes[cotacoes['GESTOR'] == gestor_selecionado]

# VALOR
vendas['Valor Produtos + Taxa Adm.'] = vendas['Valor Produtos + Taxa Adm.'].astype(str).str.replace("R$", "").str.replace(",", ".").str.strip()
vendas['Valor Produtos + Taxa Adm.'] = pd.to_numeric(vendas['Valor Produtos + Taxa Adm.'], errors='coerce')

# PROJEÇÃO em QUANTIDADE DE VENDAS
dias_uteis = 20
dias_passados = (datetime.now().date() - data_inicial.date()).days
dias_passados = min(dias_passados, dias_uteis)
fator_projecao = dias_uteis / dias_passados if dias_passados > 0 else 1
projecao_vendas = int(vendas.shape[0] * fator_projecao)

# VENDAS FECHADAS
cotacoes['Situacao'] = cotacoes['Situacao'].astype(str)
vendas_concretizadas = cotacoes[cotacoes['Situacao'].str.lower().str.strip() == "vendas concretizadas"]
percentual_conv = (vendas_concretizadas.shape[0] / cotacoes.shape[0]) * 100 if cotacoes.shape[0] > 0 else 0

# TICKET MÉDIO E FATURAMENTO
faturamento = vendas['Valor Produtos + Taxa Adm.'].sum()
ticket_medio = vendas['Valor Produtos + Taxa Adm.'].mean() if not vendas.empty else 0

# === CARTÕES ===
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

col1.metric("📦 Total de Vendas", vendas.shape[0])
col2.metric("📈 Projeção", f"{projecao_vendas}")
col3.metric("📋 Cotações Realizadas", cotacoes.shape[0])
col4.metric("✅ Vendas Fechadas", vendas_concretizadas.shape[0])
col5.metric("📊 % Conversão", f"{percentual_conv:.0f}%")
col6.markdown(f"<div style='font-size:13px'>💰<br>Faturamento</div>", unsafe_allow_html=True)
col6.metric("", f"R$ {faturamento:,.2f}".replace(".", ","))
col7.markdown(f"<div style='font-size:13px'>🎯<br>Ticket Médio</div>", unsafe_allow_html=True)
col7.metric("", f"R$ {ticket_medio:,.2f}".replace(".", ","))

# === TABELA COOPERATIVA ===
st.subheader("📊 Cooperativas – Detalhamento")

tabela = vendas.groupby('Cooperativa').agg({
    'Valor Produtos + Taxa Adm.': ['count', 'sum', 'mean']
}).reset_index()

tabela.columns = ['Cooperativa', 'Qtd Vendas', 'Faturamento', 'Ticket Médio']
tabela = tabela.sort_values(by='Faturamento', ascending=False)

st.dataframe(tabela.style.format({
    'Faturamento': 'R$ {:,.2f}',
    'Ticket Médio': 'R$ {:,.2f}'
}, decimal=',', thousands='.'), use_container_width=True)

# === GRÁFICO ===
top10 = tabela.head(10)
fig = px.bar(top10, x='Cooperativa', y='Faturamento', title='Top 10 Cooperativas por Faturamento')
st.plotly_chart(fig, use_container_width=True)

# === DESTAQUES ===
st.subheader("🔍 Destaques")

col_melhores, col_piores = st.columns(2)

melhores = tabela.head(5)
piores = tabela.tail(5)

with col_melhores:
    st.markdown("✅ **Melhores Cooperativas**")
    st.dataframe(melhores, use_container_width=True)

with col_piores:
    st.markdown("⚠️ **Cooperativas com Menor Volume**")
    st.dataframe(piores, use_container_width=True)

