import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(page_title="Painel Comercial - Dunorte", layout="wide")
st.markdown("<h1 style='margin-top: -10px;'>📊 Painel Comercial - Dunorte</h1>", unsafe_allow_html=True)

# === CARREGAMENTO DOS ARQUIVOS ===
df = pd.read_csv("VENDAS.csv", encoding="latin1", sep=";")
df.columns = df.columns.str.strip()

cotacoes = pd.read_excel("COTACOES.xlsx", header=0)
cotacoes.columns = cotacoes.columns.str.strip()

# === PREPARAÇÃO DOS DADOS ===
df.rename(columns={
    'Data Cadastro': 'DataVenda',
    'Valor Produtos + Taxa Adm.': 'ValorVenda',
    'Gestor': 'Gestor',
    'Cooperativa': 'Cooperativa'
}, inplace=True)

df['DataVenda'] = pd.to_datetime(df['DataVenda'], dayfirst=True, errors='coerce')
df = df.dropna(subset=['DataVenda'])
df['ValorVenda'] = (
    df['ValorVenda'].astype(str)
    .str.replace('R$', '', regex=False)
    .str.replace('.', '', regex=False)
    .str.replace(',', '.', regex=False)
    .str.strip()
    .astype(float)
)

# === FILTRO DE DATA E GESTOR ===
data_min = df['DataVenda'].min()
data_max = df['DataVenda'].max()
data_inicial, data_final = st.date_input("📅 Filtrar por Gestor", [data_min, data_max])

df = df[(df['DataVenda'] >= pd.to_datetime(data_inicial)) & (df['DataVenda'] <= pd.to_datetime(data_final))]
cotacoes['DataCotacao'] = pd.to_datetime(cotacoes.iloc[:, 0], errors='coerce')
cotacoes = cotacoes[(cotacoes['DataCotacao'] >= pd.to_datetime(data_inicial)) & (cotacoes['DataCotacao'] <= pd.to_datetime(data_final))]

gestores_disponiveis = ['Todos'] + sorted(df['Gestor'].dropna().unique().tolist())
gestor_selecionado = st.selectbox("🧑‍💼 Filtrar por Gestor", gestores_disponiveis)

if gestor_selecionado != 'Todos':
    df = df[df['Gestor'] == gestor_selecionado]

# === CÁLCULOS ===
dias_uteis_mes = 20
hoje = pd.to_datetime("today").normalize()
dias_trabalhados = np.busday_count(np.datetime64(data_inicial), np.datetime64(min(hoje, data_final)))
fator_projecao = dias_uteis_mes / max(dias_trabalhados, 1)

total_vendas = len(df)
projecao = int(total_vendas * fator_projecao)
faturamento = df['ValorVenda'].sum()
ticket_medio = df['ValorVenda'].mean()

total_cotacoes = len(cotacoes)
vendas_concretizadas = cotacoes[cotacoes['AX'].astype(str).str.lower().str.strip() == 'venda concretizada']
total_fechadas = len(vendas_concretizadas)
percentual_conversao = (total_fechadas / total_cotacoes) * 100 if total_cotacoes > 0 else 0

# === FUNÇÃO DE CARTÃO ===
def card(label, valor):
    st.markdown(f"""
    <div style='background-color:#f4f6fa;padding:15px 10px;border-radius:10px;
                box-shadow: 0px 0px 5px rgba(0,0,0,0.1);text-align:center;
                display:flex;flex-direction:column;justify-content:center'>
        <small style='font-size:13px;color:#333'>{label}</small>
        <h2 style='margin:5px 0'>{valor}</h2>
    </div>
    """, unsafe_allow_html=True)

# === EXIBIÇÃO DOS CARTÕES ===
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
with col1: card("Total de Vendas", f"{total_vendas:,}".replace(",", "."))
with col2: card("Projeção", f"{projecao:,}".replace(",", "."))
with col3: card("Cotações", f"{total_cotacoes:,}".replace(",", "."))
with col4: card("Vendas Fechadas", f"{total_fechadas:,}".replace(",", "."))
with col5: card("Conversão", f"{percentual_conversao:.1f}%")
with col6: card("Faturamento (R$)", f"R$ {faturamento/1000:,.1f}k".replace(",", "."))
with col7: card("Ticket Médio (R$)", f"R$ {ticket_medio:,.0f}".replace(",", "."))

# === AGRUPAMENTO POR COOPERATIVA ===
vendas_coop = df.groupby('Cooperativa').agg(
    Vendas=('ValorVenda', 'count'),
    Faturamento=('ValorVenda', 'sum'),
    Ticket_Medio=('ValorVenda', 'mean')
)

vendas_coop['Projecao'] = (vendas_coop['Vendas'] * fator_projecao).round(0).astype(int)

cotacoes_por_coop = cotacoes['AP'].value_counts().rename('Cotacoes')
fechadas_por_coop = vendas_concretizadas['AP'].value_counts().rename('Fechadas')

base_coop = vendas_coop.join(cotacoes_por_coop, how='outer').join(fechadas_por_coop, how='outer').fillna(0)
base_coop['% Conversão'] = (base_coop['Fechadas'] / base_coop['Cotacoes'].replace(0, np.nan)) * 100
base_coop['% Conversão'] = base_coop['% Conversão'].fillna(0)

base_coop = base_coop.reset_index()

# === EXIBIÇÃO DAS TABELAS ===
st.subheader("📌 Desempenho por Cooperativa")
st.dataframe(base_coop.style.format({
    'Vendas': '{:.0f}',
    'Projecao': '{:.0f}',
    'Cotacoes': '{:.0f}',
    'Fechadas': '{:.0f}',
    '% Conversão': '{:.1f}%',
    'Faturamento': 'R$ {:,.2f}'.format,
    'Ticket_Medio': 'R$ {:,.2f}'.format,
}).set_properties(**{'text-align': 'center'}),
use_container_width=True)

