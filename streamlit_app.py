import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

st.set_page_config(page_title="Painel Comercial - Dunorte", layout="wide")

st.image("logo_alfa-protecao-veicular_Bs4CuH.png", width=150)
st.markdown("<h1 style='margin-top: -10px;'>📊 Painel Comercial - Dunorte</h1>", unsafe_allow_html=True)

# === IMPORTAÇÃO DAS BASES ===
df = pd.read_csv("vendas.csv", encoding="latin1", sep=";")
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

cotacoes = pd.read_excel("COTACOES.xlsx", header=0)
cotacoes['Data'] = pd.to_datetime(cotacoes.iloc[:, 0], dayfirst=True, errors='coerce')
cotacoes['Cooperativa'] = cotacoes.iloc[:, 41]  # coluna AP
cotacoes['Situacao'] = cotacoes.iloc[:, 49]     # coluna AX

# === FILTROS ===
df['Mes_str'] = df['Mes'].astype(str)
meses_disponiveis = sorted(df['Mes_str'].unique())
mes_selecionado = st.selectbox("📅 Selecione o mês", meses_disponiveis, index=len(meses_disponiveis)-1)
gestores_disponiveis = ['Todos'] + sorted(df['Gestor'].dropna().unique().tolist())
gestor_selecionado = st.selectbox("🧑‍💼 Filtrar por Gestor", gestores_disponiveis)

df_filtrado = df[df['Mes_str'] == mes_selecionado]
if gestor_selecionado != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['Gestor'] == gestor_selecionado]

# === COTAÇÕES ===
cotacoes_mes = cotacoes[cotacoes['Data'].dt.to_period("M").astype(str) == mes_selecionado]
cotacoes_total = cotacoes_mes.groupby('Cooperativa').size().reset_index(name='TotalCotacoes')
vendas_cotacoes = cotacoes_mes[cotacoes_mes['Situacao'] == 'Venda Concretizada']
vendas_por_coop = vendas_cotacoes.groupby('Cooperativa').size().reset_index(name='VendasCotacoes')

base_cotacao = pd.merge(cotacoes_total, vendas_por_coop, on='Cooperativa', how='left').fillna(0)
base_cotacao['% Conversao'] = (base_cotacao['VendasCotacoes'] / base_cotacao['TotalCotacoes'] * 100).round(1)

# === INDICADORES GERAIS
dias_corridos = datetime.now().day
dias_mes = pd.Period(mes_selecionado).days_in_month
fator_projecao = dias_mes / dias_corridos

vendas_atual = df_filtrado
vendas_anterior = df[df['Mes'] == pd.Period(mes_selecionado) - 1]

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

# Junta com base de cotações
final = pd.merge(base, base_cotacao, on='Cooperativa', how='left').fillna(0)

# === FRASE REFERENCIAL ===
ontem = (datetime.now() - timedelta(days=1)).strftime('%d/%m/%Y')
st.markdown(f"<p style='font-size:14px;color:gray;'>📌 Referência dos dados: de 01/06 até {ontem}</p>", unsafe_allow_html=True)

# === CARTÕES ===
total_vendas = len(vendas_atual)
projecao_geral = int(total_vendas * fator_projecao)
soma_faturamento = vendas_atual['ValorVenda'].sum()
ticket_medio = vendas_atual['ValorVenda'].mean()
total_cotacoes = cotacoes_mes.shape[0]
total_vendas_cot = vendas_cotacoes.shape[0]
conversao = (total_vendas_cot / total_cotacoes * 100) if total_cotacoes else 0

def card(label, value):
    return f"""
    <div style='background-color:#f0f2f6;padding:15px 10px;border-radius:8px;
                box-shadow: 1px 1px 6px rgba(0,0,0,0.1);text-align:center; min-width: 150px'>
        <h6 style='margin-bottom:4px; font-size:14px;'>{label}</h6>
        <h3 style='margin-top:0px; font-size:18px;'>{value}</h3>
    </div>
    """

cards_html = "<div style='display:flex;gap:10px;flex-wrap:wrap;'>" + "".join([
    card("Total de Vendas", total_vendas),
    card("Projeção", projecao_geral),
    card("Cotações Realizadas", total_cotacoes),
    card("Vendas Fechadas", total_vendas_cot),
    card("% Conversão", f"{conversao:.1f}%"),
    card("Faturamento (R$)", f"R$ {soma_faturamento:,.2f}".replace('.', ',')),
    card("Ticket Médio (R$)", f"R$ {ticket_medio:,.2f}".replace('.', ','))
]) + "</div>"
st.markdown(cards_html, unsafe_allow_html=True)

# === TABELA GERAL
st.subheader("📋 Comparativo por Cooperativa")
st.dataframe(
    final[['Cooperativa', 'TotalAtual', 'TotalAnterior', 'Projecao', 'Variação (%)', 'TotalCotacoes', 'VendasCotacoes', '% Conversao', 'Status']]
    .style.format({
        'TotalAtual': '{:.0f}',
        'TotalAnterior': '{:.0f}',
        'Projecao': '{:.0f}',
        'Variação (%)': '{:.1f}',
        'TotalCotacoes': '{:.0f}',
        'VendasCotacoes': '{:.0f}',
        '% Conversao': '{:.1f}%'
    }).set_properties(**{'text-align': 'center'}),
    use_container_width=True
)

# === DESTAQUES
positivos = final[final['% Conversao'] >= 50].sort_values(by='% Conversao', ascending=False)
negativos = final[final['% Conversao'] < 50].sort_values(by='% Conversao')

st.markdown("### 🟢 Cooperativas com Alta Conversão")
st.dataframe(positivos[['Cooperativa', 'TotalCotacoes', 'VendasCotacoes', '% Conversao']].style.format('{:.1f}'))

st.markdown("### 🔴 Cooperativas com Baixa Conversão")
st.dataframe(negativos[['Cooperativa', 'TotalCotacoes', 'VendasCotacoes', '% Conversao']].style.format('{:.1f}'))
