"""
data_loader.py

Responsavel por obter todos os dados usados pelo dashboard:
- precos reais das 5 acoes da B3, via yfinance
- cotacao real do Ibovespa (^BVSP), via yfinance
- cotas de 2 fundos de investimento e 1 posicao de renda fixa (Tesouro Selic),
  simuladas via GBM (nao existe ticker publico para elas nesta carteira fictícia)
- serie do CDI, simulada como taxa composta diaria (nao ha fonte gratuita via
  yfinance; uma evolucao futura seria buscar a taxa real via Banco Central/python-bcb)

Tratamento de erro em 3 niveis para os dados que vem do yfinance (acoes e
Ibovespa), do mais para o menos confiavel:
1. Busca ao vivo na API do yfinance
2. Se falhar (sem internet, API fora do ar, etc.), usa o ultimo CSV salvo em
   cache na pasta data/ (dados reais, só que desatualizados)
3. Se nao houver cache nenhum, gera uma serie simulada via GBM como ultimo
   recurso, so para o dashboard nao quebrar
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:  # biblioteca opcional: sem ela, cai direto no fallback simulado
    yf = None

# Diretorio onde os CSVs de cache ficam salvos
DIRETORIO_DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Periodo de historico buscado na yfinance
PERIODO_HISTORICO_YFINANCE = "2y"

# Numero de dias uteis simulados quando nao ha internet nem cache (~2 anos)
DIAS_UTEIS_HISTORICO_FALLBACK = 504

# Semente fixa para que a parte simulada da carteira seja reprodutivel
SEMENTE_ALEATORIA = 42

# Valor total (hipotetico) investido na carteira, usado para transformar os
# pesos-alvo em quantidade de cada ativo no dia da "compra" (inicio do historico)
VALOR_TOTAL_INVESTIDO = 100_000.00

CDI_RETORNO_ANUAL = 0.1075  # aproximacao da taxa CDI/Selic (simulado)


@dataclass
class ConfiguracaoAtivo:
    """
    Parametros de um ativo da carteira.

    Para acoes da B3 (fonte="real"), retorno_medio_anual/volatilidade_anual/
    preco_inicial_simulado sao usados apenas como fallback, caso a yfinance e
    o cache local falhem ao mesmo tempo.

    Para fundos e renda fixa (fonte="simulado"), esses mesmos campos sao os
    parametros efetivos do GBM que gera a serie de precos.
    """

    ticker: str
    nome: str
    classe: str  # "Renda Variavel", "Fundos" ou "Renda Fixa"
    peso_carteira: float  # percentual alocado na carteira (soma = 1.0)
    fonte: str  # "real" (yfinance) ou "simulado" (GBM)
    retorno_medio_anual: float = 0.0
    volatilidade_anual: float = 0.0
    preco_inicial_simulado: float = 0.0


# 5 acoes da B3 com pesos diferentes entre si (dados reais via yfinance,
# ticker.SA). Os parametros de retorno/volatilidade abaixo so entram em jogo
# se a busca real E o cache local falharem (fallback de ultimo recurso).
ACOES_B3 = [
    ConfiguracaoAtivo(
        ticker="PETR4", nome="Petrobras PN", classe="Renda Variavel",
        peso_carteira=0.15, fonte="real",
        retorno_medio_anual=0.12, volatilidade_anual=0.38, preco_inicial_simulado=36.50,
    ),
    ConfiguracaoAtivo(
        ticker="VALE3", nome="Vale ON", classe="Renda Variavel",
        peso_carteira=0.12, fonte="real",
        retorno_medio_anual=0.08, volatilidade_anual=0.34, preco_inicial_simulado=62.00,
    ),
    ConfiguracaoAtivo(
        ticker="ITUB4", nome="Itau Unibanco PN", classe="Renda Variavel",
        peso_carteira=0.10, fonte="real",
        retorno_medio_anual=0.14, volatilidade_anual=0.26, preco_inicial_simulado=28.90,
    ),
    ConfiguracaoAtivo(
        ticker="WEGE3", nome="WEG ON", classe="Renda Variavel",
        peso_carteira=0.08, fonte="real",
        retorno_medio_anual=0.16, volatilidade_anual=0.28, preco_inicial_simulado=40.20,
    ),
    ConfiguracaoAtivo(
        ticker="BBAS3", nome="Banco do Brasil ON", classe="Renda Variavel",
        peso_carteira=0.10, fonte="real",
        retorno_medio_anual=0.15, volatilidade_anual=0.30, preco_inicial_simulado=25.40,
    ),
]

# 2 fundos + 1 renda fixa, com cotas simuladas via GBM (nao ha ticker publico)
ATIVOS_SIMULADOS = [
    ConfiguracaoAtivo(
        ticker="FUNDO_MULTI", nome="Fundo Multimercado XP", classe="Fundos",
        peso_carteira=0.15, fonte="simulado",
        retorno_medio_anual=0.13, volatilidade_anual=0.09, preco_inicial_simulado=1000.00,
    ),
    ConfiguracaoAtivo(
        ticker="FUNDO_ACOES_GLOBAL", nome="Fundo Acoes Global FIA", classe="Fundos",
        peso_carteira=0.10, fonte="simulado",
        retorno_medio_anual=0.11, volatilidade_anual=0.20, preco_inicial_simulado=500.00,
    ),
    ConfiguracaoAtivo(
        ticker="TESOURO_SELIC", nome="Tesouro Selic 2029", classe="Renda Fixa",
        peso_carteira=0.20, fonte="simulado",
        retorno_medio_anual=CDI_RETORNO_ANUAL, volatilidade_anual=0.005, preco_inicial_simulado=100.00,
    ),
]

COMPOSICAO_CARTEIRA = ACOES_B3 + ATIVOS_SIMULADOS

# Parametros do Ibovespa usados apenas no fallback simulado (real via yfinance)
IBOVESPA_RETORNO_ANUAL_FALLBACK = 0.10
IBOVESPA_VOLATILIDADE_ANUAL_FALLBACK = 0.22
IBOVESPA_PRECO_INICIAL_FALLBACK = 118_000.0


def _gerar_serie_gbm(
    preco_inicial: float,
    retorno_medio_anual: float,
    volatilidade_anual: float,
    dias_uteis: int,
    gerador: np.random.Generator,
) -> np.ndarray:
    """
    Gera uma serie de precos usando Movimento Browniano Geometrico (GBM).

    E o modelo classico para simular precos de ativos financeiros: os
    retornos diarios seguem uma distribuicao normal, e o preco e a
    composicao (produto acumulado) desses retornos. Retorna um array com
    `dias_uteis + 1` pontos (o preco inicial mais os dias simulados).
    """
    dias_uteis_ano = 252
    drift_diario = retorno_medio_anual / dias_uteis_ano
    vol_diaria = volatilidade_anual / np.sqrt(dias_uteis_ano)

    retornos_diarios = gerador.normal(loc=drift_diario, scale=vol_diaria, size=dias_uteis)
    fator_acumulado = np.cumprod(1 + retornos_diarios)
    precos = preco_inicial * fator_acumulado
    return np.concatenate([[preco_inicial], precos])


def _gerar_datas_uteis(dias_uteis: int) -> pd.DatetimeIndex:
    """Gera um indice de datas uteis terminando hoje (usado só no fallback simulado)."""
    return pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=dias_uteis + 1)


def _caminho_csv(nome_arquivo: str) -> str:
    return os.path.join(DIRETORIO_DADOS, nome_arquivo)


def _extrair_coluna_close(dados_yfinance: pd.DataFrame) -> pd.DataFrame:
    """
    Extrai apenas os precos de fechamento de um DataFrame retornado pela
    yfinance, que vem com colunas em MultiIndex (Price, Ticker).
    """
    if isinstance(dados_yfinance.columns, pd.MultiIndex):
        return dados_yfinance["Close"]
    return dados_yfinance[["Close"]]


def _fallback_simulado_acoes() -> pd.DataFrame:
    """Ultimo recurso: gera precos de acoes via GBM quando nao ha internet nem cache."""
    datas = _gerar_datas_uteis(DIAS_UTEIS_HISTORICO_FALLBACK)
    tabela = pd.DataFrame(index=datas)
    tabela.index.name = "data"
    for i, ativo in enumerate(ACOES_B3):
        gerador = np.random.default_rng(SEMENTE_ALEATORIA + i)
        tabela[ativo.ticker] = _gerar_serie_gbm(
            preco_inicial=ativo.preco_inicial_simulado,
            retorno_medio_anual=ativo.retorno_medio_anual,
            volatilidade_anual=ativo.volatilidade_anual,
            dias_uteis=DIAS_UTEIS_HISTORICO_FALLBACK,
            gerador=gerador,
        )
    return tabela


def carregar_precos_acoes() -> tuple[pd.DataFrame, str]:
    """
    Carrega os precos historicos das 5 acoes da B3.

    Retorna (tabela_precos, fonte), com fonte em:
    - "yfinance": dados reais buscados agora
    - "cache_local": ultimo dado real salvo com sucesso, usado por a busca ao vivo ter falhado
    - "simulado": nem a busca ao vivo nem o cache funcionaram; serie gerada via GBM
    """
    tickers = [ativo.ticker for ativo in ACOES_B3]
    caminho = _caminho_csv("precos_acoes_b3.csv")

    if yf is not None:
        try:
            tickers_yf = [f"{t}.SA" for t in tickers]
            # threads=False evita um bug conhecido de "database is locked" no
            # cache sqlite interno da yfinance quando varios tickers sao
            # baixados em paralelo
            dados_brutos = yf.download(
                tickers_yf,
                period=PERIODO_HISTORICO_YFINANCE,
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            if dados_brutos is None or dados_brutos.empty:
                raise ValueError("yfinance retornou dados vazios")

            precos = _extrair_coluna_close(dados_brutos)[tickers_yf]
            precos.columns = tickers
            precos.index.name = "data"

            if precos.isna().all().any():
                raise ValueError("uma ou mais acoes vieram sem nenhum dado da yfinance")

            precos = precos.ffill().dropna()
            os.makedirs(DIRETORIO_DADOS, exist_ok=True)
            precos.to_csv(caminho)
            return precos, "yfinance"
        except Exception:
            pass  # cai para o cache local / fallback simulado abaixo

    try:
        precos = pd.read_csv(caminho, index_col="data", parse_dates=True)
        if precos.empty:
            raise ValueError("cache de acoes esta vazio")
        return precos, "cache_local"
    except (FileNotFoundError, ValueError, pd.errors.EmptyDataError):
        pass

    return _fallback_simulado_acoes(), "simulado"


def carregar_ibovespa() -> tuple[pd.Series, str]:
    """
    Carrega a serie historica do Ibovespa (^BVSP), com a mesma cadeia de
    fallback de `carregar_precos_acoes`: yfinance -> cache local -> simulado.
    """
    caminho = _caminho_csv("ibovespa.csv")

    if yf is not None:
        try:
            dados_brutos = yf.download(
                "^BVSP",
                period=PERIODO_HISTORICO_YFINANCE,
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            if dados_brutos is None or dados_brutos.empty:
                raise ValueError("yfinance retornou dados vazios para o Ibovespa")

            serie = _extrair_coluna_close(dados_brutos).iloc[:, 0]
            serie.name = "IBOVESPA"
            serie.index.name = "data"
            serie = serie.ffill().dropna()

            os.makedirs(DIRETORIO_DADOS, exist_ok=True)
            serie.to_frame().to_csv(caminho)
            return serie, "yfinance"
        except Exception:
            pass

    try:
        tabela = pd.read_csv(caminho, index_col="data", parse_dates=True)
        if tabela.empty:
            raise ValueError("cache do Ibovespa esta vazio")
        return tabela.iloc[:, 0], "cache_local"
    except (FileNotFoundError, ValueError, pd.errors.EmptyDataError):
        pass

    datas = _gerar_datas_uteis(DIAS_UTEIS_HISTORICO_FALLBACK)
    gerador = np.random.default_rng(SEMENTE_ALEATORIA + 100)
    valores = _gerar_serie_gbm(
        preco_inicial=IBOVESPA_PRECO_INICIAL_FALLBACK,
        retorno_medio_anual=IBOVESPA_RETORNO_ANUAL_FALLBACK,
        volatilidade_anual=IBOVESPA_VOLATILIDADE_ANUAL_FALLBACK,
        dias_uteis=DIAS_UTEIS_HISTORICO_FALLBACK,
        gerador=gerador,
    )
    return pd.Series(valores, index=datas, name="IBOVESPA"), "simulado"


def _gerar_ativos_simulados(indice_datas: pd.DatetimeIndex) -> pd.DataFrame:
    """Gera as series de cotas dos 2 fundos e da renda fixa, alinhadas ao calendario das acoes."""
    dias_uteis = len(indice_datas) - 1
    tabela = pd.DataFrame(index=indice_datas)
    tabela.index.name = "data"
    for i, ativo in enumerate(ATIVOS_SIMULADOS):
        gerador = np.random.default_rng(SEMENTE_ALEATORIA + 50 + i)
        tabela[ativo.ticker] = _gerar_serie_gbm(
            preco_inicial=ativo.preco_inicial_simulado,
            retorno_medio_anual=ativo.retorno_medio_anual,
            volatilidade_anual=ativo.volatilidade_anual,
            dias_uteis=dias_uteis,
            gerador=gerador,
        )
    return tabela


def _gerar_cdi(indice_datas: pd.DatetimeIndex) -> pd.Series:
    """Gera a serie do CDI acumulado (base 100) como taxa composta diaria simulada."""
    dias_uteis_ano = 252
    cdi_diario = (1 + CDI_RETORNO_ANUAL) ** (1 / dias_uteis_ano) - 1
    valores = 100 * (1 + cdi_diario) ** np.arange(len(indice_datas))
    return pd.Series(valores, index=indice_datas, name="CDI")


def carregar_todos_os_dados() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    """
    Monta o conjunto completo de dados usado pelo dashboard.

    Retorna:
    - precos_completos: DataFrame com uma coluna de preco por ativo (8 ao todo)
    - benchmarks: DataFrame com as colunas CDI e IBOVESPA (base compativel)
    - fontes: dicionario informando de onde vieram os dados de acoes e Ibovespa
      ("yfinance", "cache_local" ou "simulado"), para exibir no dashboard
    """
    precos_acoes, fonte_acoes = carregar_precos_acoes()
    ibovespa, fonte_ibovespa = carregar_ibovespa()

    indice_datas = precos_acoes.index
    ativos_simulados = _gerar_ativos_simulados(indice_datas)
    precos_completos = pd.concat([precos_acoes, ativos_simulados], axis=1)

    cdi = _gerar_cdi(indice_datas)
    # o Ibovespa pode ter um calendario de pregao levemente diferente do das
    # acoes (feriados, etc.); reindexamos para o mesmo eixo de datas da carteira
    ibovespa_alinhado = ibovespa.reindex(indice_datas).ffill().bfill()
    benchmarks = pd.DataFrame({"CDI": cdi, "IBOVESPA": ibovespa_alinhado})

    fontes = {"acoes": fonte_acoes, "ibovespa": fonte_ibovespa}
    return precos_completos, benchmarks, fontes


def _calcular_quantidades(precos_completos: pd.DataFrame) -> dict[str, float]:
    """
    Calcula a quantidade comprada de cada ativo no dia inicial do historico,
    de forma que o peso de cada um bata exatamente com `peso_carteira` no
    dia da "compra" (primeiro preco disponivel de cada serie).
    """
    return {
        ativo.ticker: (ativo.peso_carteira * VALOR_TOTAL_INVESTIDO)
        / precos_completos[ativo.ticker].iloc[0]
        for ativo in COMPOSICAO_CARTEIRA
    }


def montar_tabela_posicoes(precos_completos: pd.DataFrame) -> pd.DataFrame:
    """
    Monta a tabela de posicoes atuais da carteira: quantidade, preco medio
    (preco no dia da compra simulada), preco atual, valor investido e valor
    atual por ativo.
    """
    quantidades = _calcular_quantidades(precos_completos)
    linhas = []
    for ativo in COMPOSICAO_CARTEIRA:
        quantidade = quantidades[ativo.ticker]
        preco_medio = precos_completos[ativo.ticker].iloc[0]
        preco_atual = precos_completos[ativo.ticker].iloc[-1]
        valor_investido = preco_medio * quantidade
        valor_atual = preco_atual * quantidade

        linhas.append(
            {
                "ticker": ativo.ticker,
                "nome": ativo.nome,
                "classe": ativo.classe,
                "quantidade": quantidade,
                "preco_medio": preco_medio,
                "preco_atual": preco_atual,
                "valor_investido": valor_investido,
                "valor_atual": valor_atual,
                "retorno_pct": (preco_atual / preco_medio - 1) * 100,
                "peso_alvo": ativo.peso_carteira,
            }
        )

    tabela = pd.DataFrame(linhas)
    tabela["peso_atual"] = tabela["valor_atual"] / tabela["valor_atual"].sum()
    return tabela


def calcular_serie_valor_carteira(precos_completos: pd.DataFrame) -> pd.Series:
    """
    Calcula a evolucao do valor total da carteira ao longo do tempo,
    multiplicando a quantidade de cada ativo pelo seu preco em cada data
    e somando tudo.
    """
    quantidades = _calcular_quantidades(precos_completos)
    valor_total = pd.Series(0.0, index=precos_completos.index)
    for ativo in COMPOSICAO_CARTEIRA:
        valor_total += precos_completos[ativo.ticker] * quantidades[ativo.ticker]
    return valor_total
