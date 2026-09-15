"""
app.py

Dashboard de Carteira de Investimentos - interface em Streamlit.

Este e o ponto de entrada do projeto. Ele consome os dados gerados em
`data_loader.py` e as metricas calculadas em `metrics.py`, e monta 4 secoes:
1. Visao geral da carteira
2. Rentabilidade (evolucao e comparacao com CDI/Ibovespa)
3. Risco (volatilidade, Sharpe, drawdown)
4. Detalhamento por ativo

Para rodar: `streamlit run app.py`
"""

import plotly.graph_objects as go
import streamlit as st

import metrics
from data_loader import (
    CDI_RETORNO_ANUAL,
    calcular_serie_valor_carteira,
    carregar_todos_os_dados,
    montar_tabela_posicoes,
)

# Rotulos legiveis para a fonte de cada bloco de dados, exibidos no topo do dashboard
ROTULO_FONTE = {
    "yfinance": "🟢 dados reais (yfinance)",
    "cache_local": "🟡 cache local (ultima atualizacao bem-sucedida)",
    "simulado": "🔴 simulado (sem internet e sem cache local)",
}

# Paleta de cores fixa do projeto (categorica + status), para manter
# consistencia visual entre todos os graficos do dashboard
COR_CLASSE = {
    "Renda Variavel": "#2a78d6",  # azul
    "Fundos": "#eb6834",  # laranja
    "Renda Fixa": "#1baf7a",  # verde-agua
}
COR_CARTEIRA = "#2a78d6"  # azul
COR_CDI = "#eda100"  # amarelo
COR_IBOVESPA = "#4a3aa7"  # violeta
COR_POSITIVO = "#0ca30c"  # verde (status "good")
COR_NEGATIVO = "#d03b3b"  # vermelho (status "critical")


st.set_page_config(
    page_title="Dashboard de Carteira de Investimentos",
    page_icon="📊",
    layout="wide",
)


@st.cache_data(ttl=1800)
def carregar_dados():
    """
    Carrega os dados da carteira e dos benchmarks (com cache do Streamlit por
    30 minutos, para nao bater na API do yfinance a cada interacao na tela).
    """
    precos_ativos, benchmarks, fontes = carregar_todos_os_dados()
    tabela_posicoes = montar_tabela_posicoes(precos_ativos)
    serie_valor_carteira = calcular_serie_valor_carteira(precos_ativos)
    return precos_ativos, benchmarks, tabela_posicoes, serie_valor_carteira, fontes


coluna_titulo, coluna_botao = st.columns([5, 1])
with coluna_titulo:
    st.title("📊 Dashboard de Carteira de Investimentos")
with coluna_botao:
    st.write("")
    if st.button("🔄 Atualizar cotacoes"):
        carregar_dados.clear()
        st.rerun()

precos_ativos, benchmarks, tabela_posicoes, serie_valor_carteira, fontes = carregar_dados()

st.caption(
    f"Acoes da B3: {ROTULO_FONTE[fontes['acoes']]} · "
    f"Ibovespa: {ROTULO_FONTE[fontes['ibovespa']]} · "
    "Fundos, Tesouro Selic e CDI: simulados (nao ha ticker publico para eles nesta carteira "
    "fictícia). Projeto de portfolio — nao constitui recomendacao de investimento."
)

aba_visao_geral, aba_rentabilidade, aba_risco, aba_detalhamento = st.tabs(
    ["Visao Geral", "Rentabilidade", "Risco", "Detalhamento por Ativo"]
)

# ---------------------------------------------------------------------------
# 1. VISAO GERAL
# ---------------------------------------------------------------------------
with aba_visao_geral:
    valor_investido_total = tabela_posicoes["valor_investido"].sum()
    valor_atual_total = tabela_posicoes["valor_atual"].sum()
    retorno_total_reais = valor_atual_total - valor_investido_total
    retorno_total_pct = (valor_atual_total / valor_investido_total - 1) * 100

    coluna1, coluna2, coluna3 = st.columns(3)
    coluna1.metric("Valor Investido", f"R$ {valor_investido_total:,.2f}")
    coluna2.metric("Valor Atual", f"R$ {valor_atual_total:,.2f}")
    coluna3.metric(
        "Retorno Total",
        f"R$ {retorno_total_reais:,.2f}",
        delta=f"{retorno_total_pct:.2f}%",
    )

    st.subheader("Alocacao por Classe de Ativo")
    alocacao_por_classe = (
        tabela_posicoes.groupby("classe")["valor_atual"].sum().reset_index()
    )

    grafico_alocacao = go.Figure(
        data=[
            go.Pie(
                labels=alocacao_por_classe["classe"],
                values=alocacao_por_classe["valor_atual"],
                hole=0.55,
                marker=dict(
                    colors=[COR_CLASSE[classe] for classe in alocacao_por_classe["classe"]]
                ),
                textinfo="label+percent",
            )
        ]
    )
    grafico_alocacao.update_layout(
        showlegend=True,
        margin=dict(t=10, b=10, l=10, r=10),
        height=420,
    )
    st.plotly_chart(grafico_alocacao, width="stretch")

# ---------------------------------------------------------------------------
# 2. RENTABILIDADE
# ---------------------------------------------------------------------------
with aba_rentabilidade:
    st.subheader("Evolucao do Valor da Carteira")
    grafico_evolucao = go.Figure()
    grafico_evolucao.add_trace(
        go.Scatter(
            x=serie_valor_carteira.index,
            y=serie_valor_carteira.values,
            mode="lines",
            name="Carteira (R$)",
            line=dict(color=COR_CARTEIRA, width=2),
        )
    )
    grafico_evolucao.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        height=380,
        yaxis_title="Valor (R$)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(grafico_evolucao, width="stretch")

    st.subheader("Carteira vs. CDI vs. Ibovespa (base 100)")
    carteira_base_100 = metrics.calcular_base_100(serie_valor_carteira)
    cdi_base_100 = metrics.calcular_base_100(benchmarks["CDI"])
    ibovespa_base_100 = metrics.calcular_base_100(benchmarks["IBOVESPA"])

    grafico_comparacao = go.Figure()
    grafico_comparacao.add_trace(
        go.Scatter(
            x=carteira_base_100.index,
            y=carteira_base_100.values,
            mode="lines",
            name="Carteira",
            line=dict(color=COR_CARTEIRA, width=2),
        )
    )
    grafico_comparacao.add_trace(
        go.Scatter(
            x=cdi_base_100.index,
            y=cdi_base_100.values,
            mode="lines",
            name="CDI",
            line=dict(color=COR_CDI, width=2),
        )
    )
    grafico_comparacao.add_trace(
        go.Scatter(
            x=ibovespa_base_100.index,
            y=ibovespa_base_100.values,
            mode="lines",
            name="Ibovespa",
            line=dict(color=COR_IBOVESPA, width=2),
        )
    )
    grafico_comparacao.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        height=380,
        yaxis_title="Indice (base 100)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(grafico_comparacao, width="stretch")

    st.subheader("Retorno Acumulado por Janela de Tempo")
    retornos_janelas = metrics.calcular_retornos_por_janela(serie_valor_carteira)
    colunas_janelas = st.columns(len(retornos_janelas))
    for coluna, (nome_janela, retorno_pct) in zip(colunas_janelas, retornos_janelas.items()):
        coluna.metric(nome_janela, f"{retorno_pct:.2f}%")

# ---------------------------------------------------------------------------
# 3. RISCO
# ---------------------------------------------------------------------------
with aba_risco:
    metricas_risco = metrics.calcular_metricas_risco(
        serie_valor_carteira, taxa_livre_risco_anual=CDI_RETORNO_ANUAL
    )

    coluna1, coluna2, coluna3 = st.columns(3)
    coluna1.metric(
        "Volatilidade Anualizada",
        f"{metricas_risco['volatilidade_anualizada']:.2f}%",
        help="Desvio padrao dos retornos diarios da carteira, anualizado.",
    )
    coluna2.metric(
        "Sharpe Ratio",
        f"{metricas_risco['sharpe_ratio']:.2f}",
        help="Retorno da carteira acima do CDI, por unidade de risco (volatilidade) assumida.",
    )
    coluna3.metric(
        "Drawdown Maximo",
        f"{metricas_risco['drawdown_maximo']:.2f}%",
        help="Maior queda percentual da carteira em relacao ao seu pico historico.",
    )

    st.subheader("Drawdown da Carteira ao Longo do Tempo")
    serie_drawdown = metrics.calcular_serie_drawdown(serie_valor_carteira)
    grafico_drawdown = go.Figure()
    grafico_drawdown.add_trace(
        go.Scatter(
            x=serie_drawdown.index,
            y=serie_drawdown.values,
            mode="lines",
            name="Drawdown",
            line=dict(color=COR_NEGATIVO, width=2),
            fill="tozeroy",
        )
    )
    grafico_drawdown.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        height=380,
        yaxis_title="Drawdown (%)",
    )
    st.plotly_chart(grafico_drawdown, width="stretch")

# ---------------------------------------------------------------------------
# 4. DETALHAMENTO POR ATIVO
# ---------------------------------------------------------------------------
with aba_detalhamento:
    st.subheader("Posicoes da Carteira")

    tabela_exibicao = tabela_posicoes.copy()
    tabela_exibicao["peso_atual"] = tabela_exibicao["peso_atual"] * 100

    def estilo_retorno(valor: float) -> str:
        """Aplica cor verde/vermelha conforme o sinal do retorno."""
        cor = COR_POSITIVO if valor >= 0 else COR_NEGATIVO
        return f"color: {cor}; font-weight: 600"

    tabela_formatada = tabela_exibicao[
        [
            "ticker",
            "nome",
            "classe",
            "quantidade",
            "preco_medio",
            "preco_atual",
            "retorno_pct",
            "peso_atual",
        ]
    ].rename(
        columns={
            "ticker": "Ticker",
            "nome": "Nome",
            "classe": "Classe",
            "quantidade": "Quantidade",
            "preco_medio": "Preco Medio (R$)",
            "preco_atual": "Preco Atual (R$)",
            "retorno_pct": "Retorno (%)",
            "peso_atual": "Peso na Carteira (%)",
        }
    )

    estilo = (
        tabela_formatada.style.map(estilo_retorno, subset=["Retorno (%)"])
        .format(
            {
                "Quantidade": "{:.2f}",
                "Preco Medio (R$)": "R$ {:.2f}",
                "Preco Atual (R$)": "R$ {:.2f}",
                "Retorno (%)": "{:.2f}%",
                "Peso na Carteira (%)": "{:.2f}%",
            }
        )
    )
    st.dataframe(estilo, width="stretch", hide_index=True)
