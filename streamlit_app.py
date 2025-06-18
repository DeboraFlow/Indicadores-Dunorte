import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, date

st.set_page_config(page_title="Painel Comercial - Dunorte", layout="wide")

# === LOGO E TÍTULO ===
with st.sidebar:
    st.image("logo_alfa-protecao-veicular_Bs4CuH.png", width=200)
    st.title("📅 Filtro por Gestor e Período")
    data_inicial = st.date_input("Início", value=pd.to_datetime("2025-06-01"))
    data_final = st.date_input("Fim", value=pd.to_datetime("2025-06-18"))
    gestor_selecionado = st.selectbox("👤 Filtrar por Gestor", options=["Todos"])

st.markdown("<h1 style='margin-top: -20px;'>📊 Painel Comercial - Dunorte</h1>", unsafe_allow_html=True)

# === IMPORTAÇÃO DOS DADOS ===
df = pd.read_csv("VENDAS.csv", encoding="latin1", sep=";")
cotacoes = pd.read_excel("COTACOES.xlsx", header=0)

df.columns = df.columns.str.strip()
cotacoes.columns = cotacoes.columns.str.strip()
df.rename(columns={'Data Cadastro': 'DataVenda', 'Valor Produtos + Taxa Adm.': 'ValorVenda'}, inplace=True)
cotacoes.rename(columns={'AP': 'Cooperativa', 'AX': 'Situacao', 'A': 'Data'}, inplace=True)

df['DataVenda'] = pd.to_datetime(df['DataVenda'], dayfirst=True, errors='coerce')
cotacoes['Data'] = pd.to_datetime(cotacoes['Data'], dayfirst=True, errors='coerce')
df.dropna(subset=['DataVenda'], inplace=True)
cotacoes.dropna(subset=['Data'], inplace=True)

# === AJUSTE LIMITE DE DATA ===
hoje = pd.to_datetime("today")
if data_final > hoje:
    data_final = hoje

# === FILTROS POR DATA ===
df = df[(df['DataVenda'] >= pd.to_datetime(data_inicial)) & (df['DataVenda'] <= pd.to_datetime(data_final))]
cotacoes = cotacoes[(cotacoes['Data'] >= pd.to_datetime(data_inicial)) & (cotacoes['Data'] <= pd.to_datetime(data_final))]

# === FILTRO POR GESTOR ===
if gestor_selecionado != "Todos" and "Gestor" in df.columns:
    df = df[df['Gestor'].str.lower() == gestor_selecionado.lower()]

# === VALORES ===
df['ValorVenda'] = (
    df['ValorVenda'].astype(str)
    .str.replace('R$', '', regex=False)
    .str.replace('.', '', regex=False)
    .str.replace(',', '.', regex=False)
    .str.strip()
    .astype(float)
)

cotacoes['Situacao'] = cotacoes['Situacao'].astype(str).str.lower().str.strip()
cotacoes['Cooperativa'] = cotacoes['Cooperativa'].astype(str).str.strip()

# === PROJEÇÃO ===
dias_uteis_mes = 20
dias_trabalhados = len(pd.bdate_range(data_inicial, min(data_final, hoje)))
fator_projecao = dias_uteis_mes / dias_trabalhados if dias_trabalhados else 0

# === CARTÕES ===
total_vendas = len(df)
projecao = int(total_vendas * fator_projecao)
faturamento = df['ValorVenda'].sum()
ticket = df['ValorVenda'].mean()

cot_total = len(cotacoes)
cot_fechadas = cotacoes[cotacoes['Situacao'] == 'vendas concretizadas']
cot_fechadas_total = len(cot_fechadas)
taxa_conv = cot_fechadas_total / cot_total if cot_total else 0

def card(titulo, valor, sufixo=""):
    st.markdown(f"""
    <div style='background-color:#f0f2f6;padding:15px 20px;border-radius:10px;
                box-shadow:2px 2px 8px rgba(0,0,0,0.15);text-align:center;display:flex;flex-direction:column;height:100px'>
        <div style='font-size:13px'>{titulo}</div>
        <div style='font-size:24px;font-weight:bold'>{valor}{sufixo}</div>
    </div>
    """, unsafe_allow_html=True)

col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
with col1: card("Total de Vendas", total_vendas)
with col2: card("Projeção", projecao)
with col3: card("Cotações", cot_total)
with col4: card("Vendas Fechadas", cot_fechadas_total)
with col5: card("Conversão", f"{taxa_conv*100:.0f}", "%")
with col6: card("Faturamento (R$)", f"{faturamento/1000:.1f}", "k")
with col7: card("Ticket Médio (R$)", f"{ticket:.2f}".replace('.', ','))

# === TABELA DESEMPENHO ===
vendas = df.groupby("Cooperativa").agg(
    Vendas=('ValorVenda', 'count'),
    Faturamento=('ValorVenda', 'sum'),
    Ticket_Medio=('ValorVenda', 'mean')
).reset_index()
vendas['Projecao'] = (vendas['Vendas'] * fator_projecao).round(0).astype(int)

cotacoes_coop = cotacoes.groupby("Cooperativa").agg(
    Cotacoes=('Situacao', 'count'),
    Fechadas=('Situacao', lambda x: (x == "vendas concretizadas").sum())
).reset_index()
cotacoes_coop['% Conversão'] = cotacoes_coop.apply(
    lambda row: f"{(row['Fechadas'] / row['Cotacoes'] * 100):.0f}%" if row['Cotacoes'] else "0%", axis=1)

df_final = pd.merge(vendas, cotacoes_coop, how="outer", on="Cooperativa").fillna(0)
df_final['Vendas'] = df_final['Vendas'].astype(int)
df_final['Projecao'] = df_final['Projecao'].astype(int)
df_final['Cotacoes'] = df_final['Cotacoes'].astype(int)
df_final['Fechadas'] = df_final['Fechadas'].astype(int)

st.markdown("### 📌 Desempenho por Cooperativa")
st.dataframe(df_final.style.format({
    'Faturamento': 'R$ {:,.2f}'.format,
    'Ticket_Medio': 'R$ {:,.2f}'.format,
}), use_container_width=True)

