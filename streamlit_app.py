import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(page_title="Painel Comercial - Dunorte", layout="wide")
st.image("logo_alfa-protecao-veicular_Bs4CuH.png", width=150)
st.title("📊 Painel Comercial - Dunorte")

# 🔁 Lê o CSV direto do GitHub (sem file uploader)
url = "https://raw.githubusercontent.com/DeboraFlow/Indicadores-Dunorte/main/VENDAS.csv"
df = pd.read_csv(url, encoding="latin1", sep=";", header=1)
df.columns = df.columns.str.strip()

df.rename(columns={
    'Data Cadastro': 'DataVenda',
    'Valor Produtos + Taxa Adm.': 'ValorVenda',
    'Cooperativa': 'Cooperativa'
}, inplace=True)

df['DataVenda'] = pd.to_datetime(df['DataVenda'], dayfirst=True, errors='coerce')
df = df.dropna(subset=['DataVenda'])
df['Mes'] = df['DataVenda'].dt.to_period("M")

resumo = df.groupby(['Cooperativa', 'Mes']).agg(
    TotalVendas=('ValorVenda', 'count')
).reset_index()

meses_ordenados = sorted(resumo['Mes'].unique())
if len(meses_ordenados) >= 2:
    mes_atual = meses_ordenados[-1]
    mes_anterior = meses_ordenados[-2]

    atual = resumo[resumo['Mes'] == mes_atual]
    anterior = resumo[resumo['Mes'] == mes_anterior]

    comparativo = pd.merge(atual, anterior, on='Cooperativa', how='outer', suffixes=('_Atual', '_Anterior')).fillna(0)
    comparativo['Variação (%)'] = ((comparativo['TotalVendas_Atual'] - comparativo['TotalVendas_Anterior']) /
                                   comparativo['TotalVendas_Anterior'].replace(0, np.nan)) * 100

    media = comparativo['TotalVendas_Atual'].mean()
    desvio = comparativo['TotalVendas_Atual'].std()
    LSC = media + 2 * desvio
    LIC = media - 2 * desvio

    comparativo['Status'] = comparativo['TotalVendas_Atual'].apply(
        lambda x: 'Fora do Controle 🔴' if x < LIC or x > LSC else 'Normal 🟢'
    )

    st.subheader(f"📊 Comparativo {mes_anterior} vs {mes_atual}")
    st.dataframe(comparativo[['Cooperativa', 'TotalVendas_Atual', 'TotalVendas_Anterior',
                              'Variação (%)', 'Status']].style.format({
                                  'TotalVendas_Atual': '{:.0f}',
                                  'TotalVendas_Anterior': '{:.0f}',
                                  'Variação (%)': '{:.1f}%'
                              }))

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(comparativo['Cooperativa'], comparativo['TotalVendas_Atual'], label='Mês Atual')
    ax.bar(comparativo['Cooperativa'], comparativo['TotalVendas_Anterior'],
           label='Mês Anterior', alpha=0.6)
    ax.axhline(LSC, color='red', linestyle='--', label='LSC')
    ax.axhline(LIC, color='orange', linestyle='--', label='LIC')
    plt.xticks(rotation=45, ha='right')
    ax.set_ylabel('Total de Vendas')
    ax.set_title('Comparativo de Vendas por Cooperativa')
    ax.legend()
    st.pyplot(fig)

else:
    st.warning("A base precisa conter pelo menos 2 meses para comparação.")
