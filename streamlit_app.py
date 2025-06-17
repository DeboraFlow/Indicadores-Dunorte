import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(page_title="Painel Comercial", layout="wide")
st.image("logo_alfa-protecao-veicular_Bs4CuH.png", width=150)
st.markdown("<h1 style='margin-top: -10px;'>📊 Painel Comercial - Dunorte</h1>", unsafe_allow_html=True)

# Leitura automática dos dados
df = pd.read_csv("VENDAS.csv", encoding="latin1", sep=";", header=0)
df.columns = df.columns.str.strip()

# Renomeia colunas da base de vendas
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

# === Cotação ===
cotacoes = pd.read_excel("COTACOES.xlsx", header=0)
cotacoes.columns = cotacoes.columns.str.strip()
cotacoes['Data'] = pd.to_datetime(cotacoes.iloc[:, 0], errors='coerce')  # coluna A
cotacoes['Mes'] = cotacoes['Data'].dt.to_period("M")
cotacoes['Cooperativa'] = cotacoes.iloc[:, 41].astype(str).str.strip()  # coluna AP
cotacoes['Situacao'] = cotacoes.iloc[:, 49].astype(str).str.strip().str.lower()     # coluna AX

# === FILTROS ===
meses_disponiveis = sorted(df['Mes'].astype(str).unique())
mes_selecionado = st.selectbox("🧑‍💼 Filtrar por Gestor", ['Todos'] + sorted(df['Gestor'].dropna().unique()))
mes_atual = pd.Period(datetime.now(), freq='M')
mes_hoje = datetime.now()
data_ref = f"{df['DataVenda'].min():%d/%m} até {df['DataVenda'].max():%d/%m}"
st.markdown(f"📅 <b>Referência dos dados:</b> de <b>{df['DataVenda'].min():%d/%m}</b> até <b>{df['DataVenda'].max():%d/%m}</b>", unsafe_allow_html=True)

df_filtrado = df[df['Mes'] == mes_atual]
if mes_selecionado != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['Gestor'] == mes_selecionado]

meses_validos = sorted(df['Mes'].unique())
mes_anterior = meses_validos[meses_validos.index(mes_atual) - 1] if mes_atual in meses_validos and meses_validos.index(mes_atual) > 0 else None

# Filtro da cotação por mês
cotacoes_filtrado = cotacoes[cotacoes['Mes'] == mes_atual]
total_cotacoes = len(cotacoes_filtrado)
vendas_concretizadas = len(cotacoes_filtrado[cotacoes_filtrado['Situacao'] == 'venda concretizada'])
perc_conversao = (vendas_concretizadas / total_cotacoes * 100) if total_cotacoes > 0 else 0

if not df_filtrado.empty and mes_anterior is not None:
    vendas_atual = df_filtrado
    vendas_anterior = df[df['Mes'] == mes_anterior]
    dias_corridos = datetime.now().day
    dias_mes = pd.Period(mes_atual).days_in_month
    fator_projecao = dias_mes / dias_corridos

    resumo = vendas_atual.groupby('Cooperativa').agg(
        TotalAtual=('ValorVenda', 'count'),
        SomaAtual=('ValorVenda', 'sum')
    ).reset_index()

    resumo_ant = vendas_anterior.groupby('Cooperativa').agg(
        TotalAnterior=('ValorVenda', 'count')
    ).reset_index()

    base = pd.merge(resumo, resumo_ant, on='Cooperativa', how='left').fillna(0)
    base['Projecao'] = (base['TotalAtual'] * fator_projecao).round(0).astype(int)
    base['Variação (%)'] = ((base['Projecao'] - base['TotalAnterior']) / base['TotalAnterior'].replace(0, np.nan) * 100).round(1)
    base['Status'] = base['Variação (%)'].apply(lambda x: "🟢" if x >= 0 else "🔴")
    base = base.sort_values(by='Projecao', ascending=False)

    # === CARTÕES ===
    total_vendas = len(vendas_atual)
    projecao_geral = int(total_vendas * fator_projecao)
    soma_faturamento = vendas_atual['ValorVenda'].sum()
    ticket_medio = vendas_atual['ValorVenda'].mean()

    def card(label, value):
        st.markdown(f"""
        <div style='background-color:#f0f2f6;padding:20px;border-radius:10px;
                    box-shadow: 2px 2px 8px rgba(0,0,0,0.15);text-align:center'>
            <h5 style='margin-bottom:5px;'>{label}</h5>
            <h2 style='margin-top:0px;'>{value}</h2>
        </div>
        """, unsafe_allow_html=True)

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1: card("Total de Vendas", total_vendas)
    with col2: card("Projeção", projecao_geral)
    with col3: card("Faturamento (R$)", f"R$ {soma_faturamento:,.2f}".replace('.', ','))
    with col4: card("Ticket Médio (R$)", f"R$ {ticket_medio:,.2f}".replace('.', ','))
    with col5: card("Cotações", total_cotacoes)
    with col6: card("Conversão", f"{perc_conversao:.1f}%")

    # === GESTOR
    st.subheader("📌 Desempenho por Gestor")
    meta = 150
    por_gestor = vendas_atual.groupby('Gestor').agg(
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

    # === GRÁFICO
    st.subheader("📊 Top 10 Cooperativas (Projeção)")
    top10 = base.head(10)
    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(top10['Cooperativa'], top10['Projecao'], color='#3399ff')
    ax.set_xticklabels(top10['Cooperativa'], rotation=45, ha='right', fontsize=8)
    ax.set_ylabel("Projeção")
    ax.set_title("Top 10 Cooperativas - Projeção do Mês")
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{int(height)}', xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8)
    st.pyplot(fig)

    # === TABELA GERAL
    st.subheader("📋 Comparativo por Cooperativa")
    base['Cotacoes'] = base['Cooperativa'].map(cotacoes_filtrado['Cooperativa'].value_counts())
    base['Conversão (%)'] = (base['TotalAtual'] / base['Cotacoes'].replace(0, np.nan) * 100).round(1)
    st.dataframe(base[['Cooperativa', 'TotalAtual', 'TotalAnterior', 'Projecao', 'Cotacoes', 'Conversão (%)', 'Variação (%)', 'Status']]
                 .style.format({
                     'TotalAtual': '{:.0f}',
                     'TotalAnterior': '{:.0f}',
                     'Projecao': '{:.0f}',
                     'Cotacoes': '{:.0f}',
                     'Conversão (%)': '{:.1f}',
                     'Variação (%)': '{:.1f}'
                 }).set_properties(**{'text-align': 'center'}), use_container_width=True)
else:
    st.warning("A base precisa conter pelo menos 2 meses distintos.")

