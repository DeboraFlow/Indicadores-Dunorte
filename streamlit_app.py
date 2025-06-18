import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configurações da página
st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: center;'>📊 Painel Comercial - Dunorte</h1>", unsafe_allow_html=True)

# Filtro lateral com logo e período
with st.sidebar:
    st.image("logo_alfa-protecao-veicular_Bs4CuH.png", use_container_width=True)
    st.markdown("## 🗓️ Filtro por Gestor e Período")

    data_inicial = st.date_input("Início", value=datetime(2025, 6, 1))
    data_final = st.date_input("Fim", value=datetime(2025, 6, 18))

    hoje = pd.to_datetime(datetime.now().date())
    data_final = pd.to_datetime(data_final)

    if data_final > hoje:
        st.warning("A data final não pode ser maior que hoje.")
        st.stop()

    # Leitura dos dados
    vendas = pd.read_csv("VENDAS.csv", sep=";", encoding="utf-8")
    cotacoes = pd.read_excel("COTACOES.xlsx")

    # Tratamento de datas
    vendas['Data Venda'] = pd.to_datetime(vendas['Data Venda'], dayfirst=True, errors='coerce')
    cotacoes['Data'] = pd.to_datetime(cotacoes['Data'], dayfirst=True, errors='coerce')

    # Filtro de período
    vendas = vendas[(vendas['Data Venda'] >= data_inicial) & (vendas['Data Venda'] <= data_final)]
    cotacoes = cotacoes[(cotacoes['Data'] >= data_inicial) & (cotacoes['Data'] <= data_final)]

    # Filtro por gestor
    if 'Gestor' in vendas.columns:
        gestores = vendas['Gestor'].dropna().unique().tolist()
        gestores.sort()
        gestor_selecionado = st.selectbox("👤 Filtrar por Gestor", ["Todos"] + gestores)

        if gestor_selecionado != "Todos":
            vendas = vendas[vendas['Gestor'] == gestor_selecionado]
            if 'Gestor' in cotacoes.columns:
                cotacoes = cotacoes[cotacoes['Gestor'] == gestor_selecionado]
    else:
        st.warning("⚠️ A coluna 'Gestor' não foi encontrada na base.")

# Dias úteis no mês de junho (excluindo feriado 19)
dias_uteis = 20
dias_passados = (datetime.now().date() - data_inicial).days
dias_passados = min(dias_passados, dias_uteis)
fator_projecao = dias_uteis / dias_passados if dias_passados > 0 else 1

# Adiciona projeção
vendas['Projecao'] = vendas['Valor Adesão'] * fator_projecao

# === CARTÕES === #
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

col1.metric("📦 Total de Vendas", vendas.shape[0])
col2.metric("📈 Projeção", f"R$ {vendas['Projecao'].sum():,.2f}".replace(".", ","))
col3.metric("📋 Cotações Realizadas", cotacoes.shape[0])
col4.metric("✅ Vendas Fechadas", cotacoes[cotacoes['Situação'] == "Venda Concretizada"].shape[0])
percentual_conv = (cotacoes[cotacoes['Situação'] == "Venda Concretizada"].shape[0] / cotacoes.shape[0]) * 100 if cotacoes.shape[0] > 0 else 0
col5.metric("🎯 % Conversão", f"{percentual_conv:.0f}%")
col6.metric("💰 Faturamento", f"R$ {vendas['Valor Adesão'].sum():,.2f}".replace(".", ","))
ticket_medio = vendas['Valor Adesão'].mean() if not vendas.empty else 0
col7.metric("🎯 Ticket Médio", f"R$ {ticket_medio:,.2f}".replace(".", ","))

# === TABELA POR COOPERATIVA === #
st.subheader("📊 Cooperativas – Detalhamento")

tabela = vendas.groupby('Cooperativa').agg({
    'Valor Adesão': ['count', 'sum', 'mean'],
    'Projecao': 'sum'
}).reset_index()

tabela.columns = ['Cooperativa', 'Qtd Vendas', 'Faturamento', 'Ticket Médio', 'Projeção']
tabela['% Meta'] = ((tabela['Projeção'] - tabela['Faturamento']) / tabela['Faturamento']) * 100
tabela['% Meta'] = tabela['% Meta'].fillna(0).astype(float).round(0).astype(int).astype(str) + '%'

st.dataframe(tabela.style.format({
    'Faturamento': 'R$ {:,.2f}',
    'Ticket Médio': 'R$ {:,.2f}',
    'Projeção': 'R$ {:,.2f}'
}, decimal=',', thousands='.'), use_container_width=True)

# === GRÁFICO TOP 10 COOPERATIVAS POR PROJEÇÃO === #
top10 = tabela.sort_values(by='Projeção', ascending=False).head(10)
fig = px.bar(top10, x='Cooperativa', y='Projeção', title='Top 10 Cooperativas por Projeção')
st.plotly_chart(fig, use_container_width=True)

# === DESTAQUES === #
st.subheader("🔍 Destaques")

melhores = tabela.sort_values(by='Projeção', ascending=False).head(5)
piores = tabela[tabela['% Meta'].str.replace('%', '').astype(int) < 0].sort_values(by='% Meta').head(5)

col_melhores, col_piores = st.columns(2)
with col_melhores:
    st.markdown("✅ **Cooperativas com melhor desempenho**")
    st.dataframe(melhores[['Cooperativa', 'Projeção', 'Faturamento', 'Ticket Médio']], use_container_width=True)

with col_piores:
    st.markdown("⚠️ **Cooperativas com atenção (queda na projeção)**")
    st.dataframe(piores[['Cooperativa', 'Projeção', 'Faturamento', 'Ticket Médio']], use_container_width=True)

