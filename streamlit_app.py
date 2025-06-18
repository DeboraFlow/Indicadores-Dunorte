import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# === CONFIGURAÇÃO DA PÁGINA ===
st.set_page_config(page_title="Painel Comercial - Dunorte", layout="wide")

# === ESTILO PERSONALIZADO ===
st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            width: 240px;
        }
        [data-testid="stSidebar"] > div:first-child {
            padding: 1rem;
        }
        .card {
            background-color: #f0f2f6;
            padding: 18px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 2px 2px 8px rgba(0,0,0,0.15);
        }
        .card h5 {
            margin-bottom: 5px;
            font-size: 16px;
        }
        .card h2 {
            margin-top: 0px;
            font-size: 26px;
        }
    </style>
""", unsafe_allow_html=True)

# === LOGO E TÍTULO ===
st.image("logo_alfa-protecao-veicular_Bs4CuH.png", width=120)
st.markdown("<h1>📊 Painel Comercial - Dunorte</h1>", unsafe_allow_html=True)

# === FILTROS ===
with st.sidebar:
    st.markdown("📅 **Filtrar por Gestor**")
    data_inicial = st.date_input("Início", value=datetime(2025, 6, 1))
    data_final = st.date_input("Fim", value=datetime(2025, 6, 18))
    gestor_filtrado = st.selectbox("👤 Filtrar por Gestor", ['Todos'])

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
df['ValorVenda'] = (
    df['ValorVenda'].astype(str)
    .str.replace('R$', '', regex=False)
    .str.replace('.', '', regex=False)
    .str.replace(',', '.', regex=False)
    .str.strip()
    .astype(float)
)

# === FILTRO DE DATAS E GESTOR ===
hoje = datetime.now()
data_final = min(data_final, hoje.date())
df = df[(df['DataVenda'].dt.date >= data_inicial) & (df['DataVenda'].dt.date <= data_final)]
if gestor_filtrado != "Todos":
    df = df[df["Gestor"] == gestor_filtrado]

# === BASE DE COTAÇÕES ===
cotacoes = pd.read_excel("COTACOES.xlsx")
cotacoes.columns = cotacoes.columns.str.strip()
cotacoes['Data'] = pd.to_datetime(cotacoes.iloc[:, 0], errors='coerce')  # coluna A
cotacoes = cotacoes.dropna(subset=['Data'])

cotacoes = cotacoes[(cotacoes['Data'].dt.date >= data_inicial) & (cotacoes['Data'].dt.date <= data_final)]
cotacoes['Situacao'] = cotacoes['AX'].astype(str).str.strip().str.lower()
cotacoes['Cooperativa'] = cotacoes['AP'].astype(str).str.strip()

vendas_concretizadas = cotacoes[cotacoes['Situacao'] == 'venda concretizada']
cotacoes_por_coop = cotacoes.groupby("Cooperativa").size().reset_index(name="Cotações")
fechadas_por_coop = vendas_concretizadas.groupby("Cooperativa").size().reset_index(name="Fechadas")

# === AGRUPAMENTO PRINCIPAL ===
dias_uteis_mes = 20
dias_trabalhados = np.busday_count(data_inicial.strftime('%Y-%m-%d'), data_final.strftime('%Y-%m-%d')) - 1
fator = dias_uteis_mes / dias_trabalhados if dias_trabalhados > 0 else 1

resumo = df.groupby("Cooperativa").agg({
    "ValorVenda": ["count", "sum", "mean"]
}).reset_index()
resumo.columns = ['Cooperativa', 'Vendas', 'Faturamento', 'Ticket_Medio']
resumo['Projecao'] = (resumo['Vendas'] * fator).round(0).astype(int)

# === MERGE COM COTAÇÕES ===
resumo = resumo.merge(cotacoes_por_coop, on='Cooperativa', how='left')
resumo = resumo.merge(fechadas_por_coop, on='Cooperativa', how='left')
resumo[['Cotações', 'Fechadas']] = resumo[['Cotações', 'Fechadas']].fillna(0).astype(int)
resumo['% Conversão'] = np.where(resumo['Cotações'] > 0,
                                 (resumo['Fechadas'] / resumo['Cotações'] * 100).round(1).astype(str) + '%',
                                 '0.0%')

# === CARTÕES ===
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
with col1:
    st.markdown(f"<div class='card'><h5>Total de Vendas</h5><h2>{df.shape[0]}</h2></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='card'><h5>Projeção</h5><h2>{int(df.shape[0] * fator)}</h2></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='card'><h5>Cotações</h5><h2>{cotacoes.shape[0]}</h2></div>", unsafe_allow_html=True)
with col4:
    st.markdown(f"<div class='card'><h5>Vendas Fechadas</h5><h2>{vendas_concretizadas.shape[0]}</h2></div>", unsafe_allow_html=True)
with col5:
    taxa_conv = (vendas_concretizadas.shape[0] / cotacoes.shape[0]) * 100 if cotacoes.shape[0] > 0 else 0
    st.markdown(f"<div class='card'><h5>Conversão</h5><h2>{taxa_conv:.1f}%</h2></div>", unsafe_allow_html=True)
with col6:
    faturamento = df['ValorVenda'].sum()
    st.markdown(f"<div class='card'><h5>Faturamento (R$)</h5><h2>R$ {faturamento/1000:,.1f}k</h2></div>", unsafe_allow_html=True)
with col7:
    ticket = df['ValorVenda'].mean()
    st.markdown(f"<div class='card'><h5>Ticket Médio (R$)</h5><h2>R$ {ticket/1000:,.1f}k</h2></div>", unsafe_allow_html=True)

# === TABELA COMPARATIVA ===
st.markdown("### 📌 Desempenho por Cooperativa")
tabela = resumo[['Cooperativa', 'Vendas', 'Projecao', 'Cotações', 'Fechadas', '% Conversão', 'Faturamento', 'Ticket_Medio']]
tabela = tabela.sort_values(by='Projecao', ascending=False)
st.dataframe(
    tabela.style.format({
        'Vendas': '{:.0f}', 'Projecao': '{:.0f}', 'Cotações': '{:.0f}', 'Fechadas': '{:.0f}',
        'Faturamento': 'R$ {:,.2f}', 'Ticket_Medio': 'R$ {:,.2f}'
    }).set_properties(**{'text-align': 'center'}),
    use_container_width=True
)

# === DESTAQUE ATENÇÃO ===
tabela['Diferença (%)'] = ((tabela['Projecao'] - tabela['Vendas']) / tabela['Projecao'].replace(0, np.nan)) * 100
atencao = tabela[tabela['Diferença (%)'] > 30].copy()
atencao = atencao[['Cooperativa', 'Vendas', 'Projecao']]
atencao['% Diferença'] = ((atencao['Projecao'] - atencao['Vendas']) / atencao['Projecao']) * 100
atencao['% Diferença'] = atencao['% Diferença'].round(0).astype(int).astype(str) + '%'

st.markdown("### 🔴 Cooperativas a Ter Atenção")
st.dataframe(
    atencao[['Cooperativa', 'Vendas', 'Projecao', '% Diferença']]
    .style.set_properties(**{'text-align': 'center'}),
    use_container_width=True
)

# === GRÁFICO TOP 10 ===
top10 = tabela.head(10)
st.markdown("### 📊 Top 10 Cooperativas - Projeção")
fig, ax = plt.subplots(figsize=(10, 4))
bars = ax.bar(top10['Cooperativa'], top10['Projecao'], color='#2e7be7')
ax.set_xticklabels(top10['Cooperativa'], rotation=45, ha='right', fontsize=8)
for bar in bars:
    height = bar.get_height()
    ax.annotate(f'{int(height)}', xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3), textcoords="offset points",
                ha='center', va='bottom', fontsize=8)
st.pyplot(fig)
