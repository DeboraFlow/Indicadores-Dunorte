import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: center;'>📊 Painel Comercial - Dunorte</h1>", unsafe_allow_html=True)

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

# === 1. Leitura das bases ===
vendas = pd.read_csv("VENDAS.csv", sep=";", encoding="latin1")
cotacoes = pd.read_excel("COTACOES.xlsx")

# === 2. Limpeza dos nomes de colunas ===
vendas.columns = [col.strip() for col in vendas.columns]
cotacoes.columns = [col.strip() for col in cotacoes.columns]

# === 3. Conversão da data de cadastro ===
vendas['Data Cadastro'] = pd.to_datetime(
    vendas['Data Cadastro'].astype(str).str.strip(),
    format="%d/%m/%Y",
    errors='coerce'
)
vendas = vendas[vendas['Data Cadastro'].notna()]

cotacoes['Data'] = pd.to_datetime(
    cotacoes['Data'].astype(str).str.strip(),
    dayfirst=True,
    errors='coerce'
)

# === 4. Filtro por período ===
vendas = vendas[(vendas['Data Cadastro'] >= data_inicial) & (vendas['Data Cadastro'] <= data_final)]
cotacoes = cotacoes[(cotacoes['Data'] >= data_inicial) & (cotacoes['Data'] <= data_final)]

# === 5. Filtro por gestor ===
if 'GESTOR' in vendas.columns:
    vendas['GESTOR'] = vendas['GESTOR'].astype(str).str.strip()
    gestores = [g for g in vendas['GESTOR'].dropna().unique().tolist() if g and g.upper() != 'NAN']
    gestores.sort()
    gestor_selecionado = st.selectbox("👤 Filtrar por Gestor", ["Todos"] + gestores)

    if gestor_selecionado != "Todos":
        vendas = vendas[vendas['GESTOR'] == gestor_selecionado]
        if 'GESTOR' in cotacoes.columns:
            cotacoes = cotacoes[cotacoes['GESTOR'] == gestor_selecionado]
else:
    st.warning("⚠️ A coluna 'GESTOR' não foi encontrada na base.")

# === 6. Conversão do valor da mensalidade ===
vendas['Valor Produtos + Taxa Adm.'] = vendas['Valor Produtos + Taxa Adm.'].astype(str).str.replace("R$", "").str.replace(",", ".").str.strip()
vendas['Valor Produtos + Taxa Adm.'] = pd.to_numeric(vendas['Valor Produtos + Taxa Adm.'], errors='coerce')

# === 7. Cálculo da projeção ===
dias_uteis = 20
dias_passados = (datetime.now().date() - data_inicial).days
dias_passados = min(dias_passados, dias_uteis)
fator_projecao = dias_uteis / dias_passados if dias_passados > 0 else 1
vendas['Projecao'] = vendas['Valor Produtos + Taxa Adm.'] * fator_projecao

# === 8. Cartões principais ===
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
col1.metric("📦 Total de Vendas", vendas.shape[0])
col2.metric("📈 Projeção", f"R$ {vendas['Projecao'].sum():,.2f}".replace(".", ","))
col3.metric("📋 Cotações Realizadas", cotacoes.shape[0])
col4.metric("✅ Vendas Fechadas", cotacoes[cotacoes['Situação'] == "Venda Concretizada"].shape[0])
percentual_conv = (cotacoes[cotacoes['Situação'] == "Venda Concretizada"].shape[0] / cotacoes.shape[0]) * 100 if cotacoes.shape[0] > 0 else 0
col5.metric("🎯 % Conversão", f"{percentual_conv:.0f}%")
col6.metric("💰 Faturamento", f"R$ {vendas['Valor Produtos + Taxa Adm.'].sum():,.2f}".replace(".", ","))
ticket_medio = vendas['Valor Produtos + Taxa Adm.'].mean() if not vendas.empty else 0
col7.metric("🎯 Ticket Médio", f"R$ {ticket_medio:,.2f}".replace(".", ","))

# === 9. Tabela por cooperativa ===
st.subheader("📊 Cooperativas – Detalhamento")
tabela = vendas.groupby('Cooperativa').agg({
    'Valor Produtos + Taxa Adm.': ['count', 'sum', 'mean'],
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

# === 10. Gráfico e destaques ===
top10 = tabela.sort_values(by='Projeção', ascending=False).head(10)
fig = px.bar(top10, x='Cooperativa', y='Projeção', title='Top 10 Cooperativas por Projeção')
st.plotly_chart(fig, use_container_width=True)

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
