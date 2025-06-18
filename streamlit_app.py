import streamlit as st
import pandas as pd
from datetime import datetime

# Configurações iniciais da página
st.set_page_config(page_title="Painel Comercial Dunorte", layout="wide")

# Logo
st.image("logo_alfa-protecao-veicular_Bs4CuH.png", use_column_width=True)

# Título
st.title("📊 Painel Comercial - Dunorte")

# Importação dos dados
vendas = pd.read_csv("VENDAS.csv", sep=";", encoding="latin1")
cotacoes = pd.read_excel("COTACOES.xlsx")

# Conversão de datas
vendas['Data Cadastro'] = pd.to_datetime(vendas['Data Cadastro'], errors='coerce')
cotacoes['Data'] = pd.to_datetime(cotacoes['Data'], errors='coerce')

# Filtros
col1, col2 = st.columns(2)
with col1:
    data_inicial = st.date_input("Início", value=datetime(2025, 6, 1))
with col2:
    data_final = st.date_input("Fim", value=datetime(2025, 6, 18))

# Corrige o tipo das datas
data_inicial = pd.to_datetime(data_inicial)
data_final = pd.to_datetime(data_final)

# Filtro por gestor (vendas)
gestores = vendas['GESTOR'].dropna().unique()
gestor_selecionado = st.selectbox("Filtrar por Gestor", options=["Todos"] + list(gestores))

# Aplica filtros
vendas_filtrado = vendas[(vendas['Data Cadastro'] >= data_inicial) & (vendas['Data Cadastro'] <= data_final)]
cotacoes_filtrado = cotacoes[(cotacoes['Data'] >= data_inicial) & (cotacoes['Data'] <= data_final)]

if gestor_selecionado != "Todos":
    vendas_filtrado = vendas_filtrado[vendas_filtrado['GESTOR'] == gestor_selecionado]
    cotacoes_filtrado = cotacoes_filtrado[cotacoes_filtrado['GESTOR'] == gestor_selecionado]

# Indicadores principais
total_vendas = len(vendas_filtrado)
faturamento = vendas_filtrado['Valor Produtos + Taxa Adm'].sum()
ticket_medio = faturamento / total_vendas if total_vendas else 0

total_cotacoes = len(cotacoes_filtrado)
vendas_concretizadas = cotacoes_filtrado[cotacoes_filtrado['Situação'] == 'Venda Concretizada']
qtd_vendas_concretizadas = len(vendas_concretizadas)
percentual_conversao = (qtd_vendas_concretizadas / total_cotacoes) * 100 if total_cotacoes else 0

# Cartões
col1, col2, col3 = st.columns(3)
col1.metric("💰 Total de Vendas", total_vendas)
col2.metric("📦 Faturamento (R$)", f"R$ {faturamento:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
col3.metric("🎯 Ticket Médio", f"R$ {ticket_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

col4, col5, col6 = st.columns(3)
col4.metric("📝 Cotações Realizadas", total_cotacoes)
col5.metric("✅ Vendas Concretizadas", qtd_vendas_concretizadas)
col6.metric("📈 % Conversão", f"{percentual_conversao:.0f}%")

# Tabelas por cooperativa
st.subheader("📌 Tabela por Cooperativa")
tabela = vendas_filtrado.groupby("Cooperativa").agg({
    'Valor Produtos + Taxa Adm': ['count', 'sum']
})
tabela.columns = ['Total Vendas', 'Faturamento']
tabela['Ticket Médio'] = tabela['Faturamento'] / tabela['Total Vendas']
tabela = tabela.reset_index()

# Adiciona dados de cotações
cotacoes_por_coop = cotacoes_filtrado.groupby("Cooperativa").agg({
    'Situação': lambda x: (x == 'Venda Concretizada').sum(),
    'Data': 'count'
}).rename(columns={'Situação': 'Vendas Concretizadas', 'Data': 'Total Cotações'})
cotacoes_por_coop['% Conversão'] = (cotacoes_por_coop['Vendas Concretizadas'] / cotacoes_por_coop['Total Cotações']) * 100
cotacoes_por_coop = cotacoes_por_coop.reset_index()

# Mescla as tabelas
tabela_final = pd.merge(tabela, cotacoes_por_coop, on="Cooperativa", how="left")

# Exibe a tabela
st.dataframe(tabela_final.style.format({
    "Faturamento": "R$ {:,.2f}".format,
    "Ticket Médio": "R$ {:,.2f}".format,
    "% Conversão": "{:.0f}%".format
}))
