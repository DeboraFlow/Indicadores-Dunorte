import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(page_title="Análise de Vendas - Flow", layout="wide")
st.title("📈 Controle de Vendas por Cooperativa")

# Carrega automaticamente o CSV do GitHub
url = "https://raw.githubusercontent.com/DeboraFlow/Indicadores-Dunorte/main/VENDAS.csv"
df = pd.read_csv(url, encoding="latin1", sep=";", header=1)
df.columns = df.columns.str.strip()  # Remove espaços extras nos nomes das colunas

# Renomeia colunas
df.rename(columns={
    'Data Cadastro': 'DataVenda',
    'Valor Produtos + Taxa Adm.': 'ValorVenda',
    'Cooperativa': 'Cooperativa'
}, inplace=True)

# Converte para data e gera coluna de mês
df['DataVenda'] = pd.to_datetime(df['DataVenda'], dayfirst=True, errors='coerce')
df = df.dropna(subset=['DataVenda'])
df['Mes'] = df['DataVenda'].dt.to_period("M")

# Agrupamento
resumo = df.groupby(['Cooperativa', 'Mes']).agg(
    TotalVendas=('ValorVenda', 'count'),
    SomaVendas=('ValorVenda', 'count')
).reset_index()

# Identifica meses
meses_ordenados = sorted(resumo['Mes'].unique())
if len(meses_ordenados) >= 2:
    mes_atual = meses_ordenados[-1]
    mes_anterior = meses_ordenados[-2]

    atual = resumo[resumo['Mes'] == mes_atual]
    anterior = resumo[resumo['Mes'] == mes_anterior]

    comparativo = pd.merge(
        atual, anterior,
        on='Cooperativa', how='outer', suffixes=('_atual', '_anterior')
    ).fillna(0)

    comparativo['Variação (%)'] = ((comparativo['TotalVendas_atual'] - comparativo['TotalVendas_anterior']) /
                                    comparativo['TotalVendas_anterior'].replace(0, np.nan)) * 100

    media = comparativo['TotalVendas_atual'].mean()
    desvio = comparativo['TotalVendas_atual'].std()
    LSC = media + 2 * desvio
    LIC = media - 2 * desvio

    comparativo['Status'] = comparativo['TotalVendas_atual'].apply(
        lambda x: 'Fora do Controle 🔴' if x < LIC or x > LSC else 'Normal 🟢'
    )

    st.subheader(f"📊 Comparativo {mes_anterior} vs {mes_atual}")
    st.dataframe(comparativo[['Cooperativa', 'TotalVendas_atual', 'TotalVendas_anterior',
                              'Variação (%)', 'Status']].style.format({
                                  'TotalVendas_atual': '{:.0f}',
                                  'TotalVendas_anterior': '{:.0f}',
                                  'Variação (%)': '{:.1f}%'
                              }))

    # Gráfico
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(comparativo['Cooperativa'], comparativo['TotalVendas_atual'], label='Mês Atual')
    ax.bar(comparativo['Cooperativa'], comparativo['TotalVendas_anterior'],
           label='Mês Anterior', alpha=0.6)
    ax.axhline(LSC, color='red', linestyle='--', label='LSC')
    ax.axhline(LIC, color='orange', linestyle='--', label='LIC')
    plt.xticks(rotation=45, ha='right')
    ax.set_ylabel('Total de Vendas')
    ax.set_title('Comparativo de Vendas por Cooperativa')
    ax.legend()
    st.pyplot(fig)

    st.subheader("🔎 Diagnóstico Automatizado")
    for _, row in comparativo.iterrows():
        if row['Status'] == 'Fora do Controle 🔴':
            st.markdown(f"**{row['Cooperativa']}** teve uma variação de "
                        f"{row['Variação (%)']:.1f}% em relação ao mês anterior, o que está fora dos limites esperados.")
else:
    st.warning("A base precisa conter pelo menos 2 meses para comparação.")
