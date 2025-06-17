import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

st.set_page_config(page_title="Painel Comercial", layout="wide")
st.image("logo_alfa-protecao-veicular_Bs4CuH.png", width=150)
st.markdown("<h1 style='margin-top: -10px;'>📊 Painel Comercial - Dunorte</h1>", unsafe_allow_html=True)

# === Referência de Data ===
ontem = datetime.now() - timedelta(days=1)
referencia = f"Referência dos dados: de 01/06 até {ontem.strftime('%d/%m')}"
st.markdown(f"<p style='color: gray; margin-top: -10px;'>{referencia}</p>", unsafe_allow_html=True)

# === Leitura da Base de Vendas ===
df = pd.read_csv("VENDAS.csv", encoding="latin1", sep=";", header=0)
df.columns = df.columns.str.strip()

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

# === Filtros Interativos ===
meses_disponiveis = sorted(df['Mes'].astype(str).unique())
mes_selecionado = st.selectbox("📅 Selecione o mês", meses_disponiveis, index=len(meses_disponiveis) - 1)
gestores_disponiveis = ['Todos'] + sorted(df['Gestor'].dropna().unique().tolist())
gestor_selecionado = st.selectbox("🧑‍💼 Filtrar por Gestor", gestores_disponiveis)

# Aplicar filtros
df_filtrado = df[df['Mes'].astype(str) == mes_selecionado]
if gestor_selecionado != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['Gestor'] == gestor_selecionado]

# === Leitura da Base de Cotações ===
cotacoes = pd.read_excel("COTACOES.xlsx", header=0)
cotacoes.rename(columns=lambda x: x.strip(), inplace=True)
cotacoes['Data'] = pd.to_datetime(cotacoes['Data'], errors='coerce')
cotacoes = cotacoes.dropna(subset=['Data'])
cotacoes = cotacoes[cotacoes['Data'] <= ontem]

# === Agrupamento por Cooperativa ===
agrupado = cotacoes.groupby('Cooperativa').agg(
    TotalCotacoes=('Situacao', 'count'),
    VendasConcretizadas=('Situacao', lambda x: (x == 'Venda Concretizada').sum())
).reset_index()

agrupado['Conversao (%)'] = (agrupado['VendasConcretizadas'] / agrupado['TotalCotacoes'] * 100).round(1)
agrupado['Conversao (%)'] = agrupado['Conversao (%)'].fillna(0)

# === Seção de Conversão ===
st.markdown("## 📩 Conversão de Cotações")
col1, col2, col3 = st.columns(3)
total_cotacoes = agrupado['TotalCotacoes'].sum()
vendas_concretizadas = agrupado['VendasConcretizadas'].sum()
conversao_geral = (vendas_concretizadas / total_cotacoes * 100) if total_cotacoes > 0 else 0

with col1:
    st.metric("Total de Cotações", f"{total_cotacoes}")
with col2:
    st.metric("Vendas Concretizadas", f"{vendas_concretizadas}")
with col3:
    st.metric("Conversão Geral", f"{conversao_geral:.1f}%")

st.dataframe(agrupado.style.format({
    'TotalCotacoes': '{:.0f}',
    'VendasConcretizadas': '{:.0f}',
    'Conversao (%)': '{:.1f}%'
}), use_container_width=True)

# === Continuação: Painel Comercial como antes ===
mes_atual = pd.Period(mes_selecionado)
meses_validos = sorted(df['Mes'].unique())
mes_anterior = meses_validos[meses_validos.index(mes_atual) - 1] if mes_atual in meses_validos and meses_validos.index(mes_atual) > 0 else None

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

    col1, col2, col3, col4 = st.columns(4)
    with col1: card("Total de Vendas", total_vendas)
    with col2: card("Projeção", projecao_geral)
    with col3: card("Faturamento (R$)", f"R$ {soma_faturamento:,.2f}".replace('.', ','))
    with col4: card("Ticket Médio (R$)", f"R$ {ticket_medio:,.2f}".replace('.', ','))

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

    st.subheader("📊 Top 10 Cooperativas (Projeção)")
    top10 = base.head(10)
    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(top10['Cooperativa'], top10['Projecao'], color='#3399ff')
    ax.set_xticklabels(top10['Cooperativa'], rotation=45, ha='right', fontsize=8)
    ax.set_ylabel("Projeção")
    ax.set_title("Top 10 Cooperativas - Projeção do Mês")

    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{int(height)}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=8)
    st.pyplot(fig)

    st.subheader("📋 Comparativo por Cooperativa")
    st.dataframe(
        base[['Cooperativa', 'TotalAtual', 'TotalAnterior', 'Projecao', 'Variação (%)', 'Status']]
        .style.format({
            'TotalAtual': '{:.0f}',
            'TotalAnterior': '{:.0f}',
            'Projecao': '{:.0f}',
            'Variação (%)': '{:.1f}'
        }).set_properties(**{'text-align': 'center'}),
        use_container_width=True
    )

    positivos = base[base['Variação (%)'] > 0].sort_values(by='Variação (%)', ascending=False)
    negativos = base[base['Variação (%)'] < 0].sort_values(by='Variação (%)', ascending=True)

    st.markdown("### 🟢 Destaques Positivos")
    st.dataframe(
        positivos[['Cooperativa', 'Projecao', 'TotalAnterior', 'Variação (%)']]
        .style.format({
            'Projecao': '{:.0f}',
            'TotalAnterior': '{:.0f}',
            'Variação (%)': '{:.1f}'
        }).set_properties(**{'text-align': 'center'}),
        use_container_width=True
    )

    st.markdown("### 🔴 Cooperativas a Ter Atenção")
    st.dataframe(
        negativos[['Cooperativa', 'Projecao', 'TotalAnterior', 'Variação (%)']]
        .style.format({
            'Projecao': '{:.0f}',
            'TotalAnterior': '{:.0f}',
            'Variação (%)': '{:.1f}'
        }).set_properties(**{'text-align': 'center'}),
        use_container_width=True
    )
else:
    st.warning("A base precisa conter pelo menos 2 meses distintos.")
