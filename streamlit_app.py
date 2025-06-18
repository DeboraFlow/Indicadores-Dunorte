import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import calendar

st.set_page_config(page_title="Painel Comercial - Dunorte", layout="wide")

# Logo e título
st.image("logo_alfa-protecao-veicular_Bs4CuH.png", width=150)
st.markdown("<h1 style='margin-top: -10px;'>📊 Painel Comercial - Dunorte</h1>", unsafe_allow_html=True)

# === Importação dos dados ===
df = pd.read_csv("VENDAS.csv", encoding="latin1", sep=";")
cotacoes = pd.read_excel("COTACOES.xlsx")

df.columns = df.columns.str.strip()
cotacoes.columns = cotacoes.columns.str.strip()

df.rename(columns={
    'Data Cadastro': 'DataVenda',
    'Valor Produtos + Taxa Adm.': 'ValorVenda',
    'Cooperativa': 'Cooperativa',
    'Gestor': 'Gestor'
}, inplace=True)

cotacoes.rename(columns={
    cotacoes.columns[0]: 'DataCotacao',
    cotacoes.columns[41]: 'Cooperativa',
    cotacoes.columns[49]: 'Situacao'
}, inplace=True)

# Tratamento de datas e valores
df['DataVenda'] = pd.to_datetime(df['DataVenda'], dayfirst=True, errors='coerce')
df = df.dropna(subset=['DataVenda'])
df['Mes'] = df['DataVenda'].dt.to_period("M")

cotacoes['DataCotacao'] = pd.to_datetime(cotacoes['DataCotacao'], dayfirst=True, errors='coerce')
cotacoes['Situacao'] = cotacoes['Situacao'].astype(str).str.strip().str.lower()

df['ValorVenda'] = (
    df['ValorVenda'].astype(str)
    .str.replace('R$', '', regex=False)
    .str.replace('.', '', regex=False)
    .str.replace(',', '.', regex=False)
    .str.strip()
    .astype(float)
)

# === Filtros interativos ===
gestores_disponiveis = ['Todos'] + sorted(df['Gestor'].dropna().unique().tolist())
gestor_selecionado = st.selectbox("🧑‍💼 Filtrar por Gestor", gestores_disponiveis)

# Referência de data
ontem = datetime.now() - timedelta(days=1)
inicio_mes = datetime(ontem.year, ontem.month, 1)
feriados = [datetime(ontem.year, 6, 19)]

dias_uteis_mes = 20
dias_uteis_trabalhados = np.busday_count(inicio_mes.date(), ontem.date(), holidays=[f.date() for f in feriados])
fator_projecao = dias_uteis_mes / max(dias_uteis_trabalhados, 1)

# Filtragem
df_mes = df[(df['DataVenda'].dt.month == ontem.month) & (df['DataVenda'].dt.year == ontem.year)]
cotacoes_mes = cotacoes[(cotacoes['DataCotacao'].dt.month == ontem.month) & (cotacoes['DataCotacao'].dt.year == ontem.year)]

if gestor_selecionado != 'Todos':
    df_mes = df_mes[df_mes['Gestor'] == gestor_selecionado]

# Cálculo de vendas
total_vendas = len(df_mes)
projecao_geral = int(total_vendas * fator_projecao)
soma_faturamento = df_mes['ValorVenda'].sum()
ticket_medio = df_mes['ValorVenda'].mean()

# Cálculo de cotações
total_cotacoes = len(cotacoes_mes)
vendas_concretizadas = cotacoes_mes[cotacoes_mes['Situacao'].str.lower() == 'venda concretizada']
total_concretizadas = len(vendas_concretizadas)
taxa_conversao = (total_concretizadas / total_cotacoes) * 100 if total_cotacoes > 0 else 0

# === Cartões ===
def card(label, value):
    st.markdown(f"""
        <div style='background-color:#f0f2f6;padding:18px;border-radius:10px;
                    box-shadow: 2px 2px 8px rgba(0,0,0,0.15);text-align:center;display:flex;flex-direction:column;justify-content:center;height:100px'>
            <h5 style='margin-bottom:5px;font-size:14px;'>{label}</h5>
            <h2 style='margin-top:0px;font-size:22px;'>{value}</h2>
        </div>
    """, unsafe_allow_html=True)

st.markdown(f"📅 <b>Referência dos dados:</b> de <b>01/{ontem.strftime('%m')}</b> até <b>{ontem.strftime('%d/%m')}</b>", unsafe_allow_html=True)

col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
with col1: card("Total de Vendas", total_vendas)
with col2: card("Projeção", projecao_geral)
with col3: card("Cotações", total_cotacoes)
with col4: card("Vendas Fechadas", total_concretizadas)
with col5: card("Conversão", f"{taxa_conversao:.1f}%")
with col6: card("Faturamento (R$)", f"R$ {soma_faturamento:,.2f}".replace('.', ','))
with col7: card("Ticket Médio (R$)", f"R$ {ticket_medio:,.2f}".replace('.', ','))

# === Tabela por cooperativa
vendas_coop = df_mes.groupby('Cooperativa').agg(
    Vendas=('ValorVenda', 'count'),
    Faturamento=('ValorVenda', 'sum'),
    Ticket_Medio=('ValorVenda', 'mean')
).reset_index()
vendas_coop['Projecao'] = (vendas_coop['Vendas'] * fator_projecao).round(0).astype(int)

cotacoes_coop = cotacoes_mes.groupby('Cooperativa').agg(
    Cotacoes=('Situacao', 'count'),
    Fechadas=('Situacao', lambda x: (x.str.lower() == 'venda concretizada').sum())
).reset_index()
cotacoes_coop['% Conversão'] = (cotacoes_coop['Fechadas'] / cotacoes_coop['Cotacoes']) * 100

base = pd.merge(vendas_coop, cotacoes_coop, on='Cooperativa', how='outer').fillna(0)
base['% Conversão'] = base['% Conversão'].round(1)
base['Faturamento'] = base['Faturamento'].round(2)
base['Ticket_Medio'] = base['Ticket_Medio'].round(2)

st.subheader("📌 Desempenho por Cooperativa")
st.dataframe(
    base[['Cooperativa', 'Vendas', 'Projecao', 'Cotacoes', 'Fechadas', '% Conversão', 'Faturamento', 'Ticket_Medio']]
    .sort_values(by='Projecao', ascending=False)
    .style.format({
        'Faturamento': 'R$ {:,.2f}'.format,
        'Ticket_Medio': 'R$ {:,.2f}'.format,
        'Vendas': '{:.0f}',
        'Projecao': '{:.0f}',
        'Cotacoes': '{:.0f}',
        'Fechadas': '{:.0f}',
        '% Conversão': '{:.1f}%'
    }).set_properties(**{'text-align': 'center'}),
    use_container_width=True
)

# === Gráfico Top 10 Cooperativas
st.subheader("📊 Top 10 Cooperativas (Projeção)")
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

# === Destaques positivos e atenção
base['Diferenca'] = base['Projecao'] - base['Vendas']
positivos = base[base['Diferenca'] > 0].sort_values(by='Diferenca', ascending=False)
negativos = base[base['Diferenca'] < 0].sort_values(by='Diferenca', ascending=True)

st.markdown("### 🟢 Destaques Positivos")
st.dataframe(
    positivos[['Cooperativa', 'Vendas', 'Projecao', 'Diferenca']]
    .style.format({
        'Vendas': '{:.0f}',
        'Projecao': '{:.0f}',
        'Diferenca': '{:.0f}'
    }).set_properties(**{'text-align': 'center'}),
    use_container_width=True
)

st.markdown("### 🔴 Cooperativas a Ter Atenção")
st.dataframe(
    negativos[['Cooperativa', 'Vendas', 'Projecao', 'Diferenca']]
    .style.format({
        'Vendas': '{:.0f}',
        'Projecao': '{:.0f}',
        'Diferenca': '{:.0f}'
    }).set_properties(**{'text-align': 'center'}),
    use_container_width=True
)

