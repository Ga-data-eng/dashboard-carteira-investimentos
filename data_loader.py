"""
data_loader.py

Responsavel por gerar e/ou carregar os dados simulados da carteira de investimentos:
- series de precos das acoes da B3
- series de cotas dos fundos de investimento
- serie de rentabilidade da renda fixa (atrelada ao CDI)
- series de benchmark (CDI e Ibovespa)

Como o projeto usa dados 100% simulados, as series sao geradas com um modelo
de passeio aleatorio geometrico (GBM - Geometric Brownian Motion), que e uma
forma simples e realista de simular precos de ativos financeiros ao longo do
tempo. Os dados gerados sao salvos em CSV (pasta data/) para que a carteira
nao mude a cada vez que o dashboard e recarregado.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import pandas as pd

# Diretorio onde os CSVs de cache ficam salvos
DIRETORIO_DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Numero de dias uteis simulados (~2 anos de historico, permite calcular
# janelas de 1m, 6m, 12m e "desde o inicio")
DIAS_UTEIS_HISTORICO = 504

# Semente fixa para que a carteira simulada seja sempre a mesma entre execucoes
SEMENTE_ALEATORIA = 42


@dataclass
class ConfiguracaoAtivo:
    """Guarda os parametros usados para simular um ativo especifico."""

    ticker: str
    nome: str
    classe: str  # "Renda Variavel", "Fundos" ou "Renda Fixa"
    preco_inicial: float
    retorno_medio_anual: float  # retorno esperado ao ano (drift)
    volatilidade_anual: float  # volatilidade anualizada
    peso_carteira: float  # percentual alocado na carteira (soma = 1.0)
    quantidade: float  # quantidade de cotas/acoes compradas


# Composicao da carteira simulada: 5 acoes B3 + 2 fundos + 1 renda fixa,
# com pesos diferentes entre si (nao uniformes)
COMPOSICAO_CARTEIRA = [
    ConfiguracaoAtivo(
        ticker="PETR4",
        nome="Petrobras PN",
        classe="Renda Variavel",
        preco_inicial=36.50,
        retorno_medio_anual=0.12,
        volatilidade_anual=0.38,
        peso_carteira=0.15,
        quantidade=300,
    ),
    ConfiguracaoAtivo(
        ticker="VALE3",
        nome="Vale ON",
        classe="Renda Variavel",
        preco_inicial=62.00,
        retorno_medio_anual=0.08,
        volatilidade_anual=0.34,
        peso_carteira=0.12,
        quantidade=140,
    ),
    ConfiguracaoAtivo(
        ticker="ITUB4",
        nome="Itau Unibanco PN",
        classe="Renda Variavel",
        preco_inicial=28.90,
        retorno_medio_anual=0.14,
        volatilidade_anual=0.26,
        peso_carteira=0.10,
        quantidade=250,
    ),
    ConfiguracaoAtivo(
        ticker="WEGE3",
        nome="WEG ON",
        classe="Renda Variavel",
        preco_inicial=40.20,
        retorno_medio_anual=0.16,
        volatilidade_anual=0.28,
        peso_carteira=0.08,
        quantidade=150,
    ),
    ConfiguracaoAtivo(
        ticker="BBAS3",
        nome="Banco do Brasil ON",
        classe="Renda Variavel",
        preco_inicial=25.40,
        retorno_medio_anual=0.15,
        volatilidade_anual=0.30,
        peso_carteira=0.10,
        quantidade=280,
    ),
    ConfiguracaoAtivo(
        ticker="FUNDO_MULTI",
        nome="Fundo Multimercado XP",
        classe="Fundos",
        preco_inicial=1000.00,
        retorno_medio_anual=0.13,
        volatilidade_anual=0.09,
        peso_carteira=0.15,
        quantidade=6.5,
    ),
    ConfiguracaoAtivo(
        ticker="FUNDO_ACOES_GLOBAL",
        nome="Fundo Acoes Global FIA",
        classe="Fundos",
        preco_inicial=500.00,
        retorno_medio_anual=0.11,
        volatilidade_anual=0.20,
        peso_carteira=0.10,
        quantidade=10.0,
    ),
    ConfiguracaoAtivo(
        ticker="TESOURO_SELIC",
        nome="Tesouro Selic 2029",
        classe="Renda Fixa",
        preco_inicial=100.00,
        retorno_medio_anual=0.1075,  # proximo do CDI
        volatilidade_anual=0.005,  # renda fixa pos-fixada: volatilidade muito baixa
        peso_carteira=0.20,
        quantidade=100.0,
    ),
]

# Parametros dos benchmarks
CDI_RETORNO_ANUAL = 0.1075  # aproximacao da taxa CDI/Selic no periodo simulado
IBOVESPA_RETORNO_ANUAL = 0.10
IBOVESPA_VOLATILIDADE_ANUAL = 0.22
IBOVESPA_PRECO_INICIAL = 118000.0


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
    composicao (produto acumulado) desses retornos.
    """
    dias_uteis_ano = 252
    drift_diario = retorno_medio_anual / dias_uteis_ano
    vol_diaria = volatilidade_anual / np.sqrt(dias_uteis_ano)

    retornos_diarios = gerador.normal(loc=drift_diario, scale=vol_diaria, size=dias_uteis)
    fator_acumulado = np.cumprod(1 + retornos_diarios)
    precos = preco_inicial * fator_acumulado
    return np.concatenate([[preco_inicial], precos])


def _gerar_datas_uteis(dias_uteis: int) -> pd.DatetimeIndex:
    """Gera um indice de datas uteis terminando hoje."""
    return pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=dias_uteis + 1)


def _gerar_precos_ativos() -> pd.DataFrame:
    """Gera a serie historica de precos de todos os ativos da carteira."""
    datas = _gerar_datas_uteis(DIAS_UTEIS_HISTORICO)
    tabela_precos = pd.DataFrame(index=datas)
    tabela_precos.index.name = "data"

    for i, ativo in enumerate(COMPOSICAO_CARTEIRA):
        # Cada ativo usa uma semente derivada para gerar series diferentes,
        # mas sempre reprodutiveis entre execucoes
        gerador = np.random.default_rng(SEMENTE_ALEATORIA + i)
        tabela_precos[ativo.ticker] = _gerar_serie_gbm(
            preco_inicial=ativo.preco_inicial,
            retorno_medio_anual=ativo.retorno_medio_anual,
            volatilidade_anual=ativo.volatilidade_anual,
            dias_uteis=DIAS_UTEIS_HISTORICO,
            gerador=gerador,
        )

    return tabela_precos


def _gerar_benchmarks() -> pd.DataFrame:
    """Gera as series de CDI (acumulado) e Ibovespa para comparacao."""
    datas = _gerar_datas_uteis(DIAS_UTEIS_HISTORICO)
    tabela_benchmarks = pd.DataFrame(index=datas)
    tabela_benchmarks.index.name = "data"

    # CDI: taxa diaria composta, praticamente sem volatilidade (pos-fixado)
    dias_uteis_ano = 252
    cdi_diario = (1 + CDI_RETORNO_ANUAL) ** (1 / dias_uteis_ano) - 1
    fator_cdi = np.cumprod(np.full(DIAS_UTEIS_HISTORICO, 1 + cdi_diario))
    tabela_benchmarks["CDI"] = np.concatenate([[1.0], fator_cdi]) * 100

    # Ibovespa: simulado via GBM, com volatilidade tipica de bolsa
    gerador_ibov = np.random.default_rng(SEMENTE_ALEATORIA + 100)
    tabela_benchmarks["IBOVESPA"] = _gerar_serie_gbm(
        preco_inicial=IBOVESPA_PRECO_INICIAL,
        retorno_medio_anual=IBOVESPA_RETORNO_ANUAL,
        volatilidade_anual=IBOVESPA_VOLATILIDADE_ANUAL,
        dias_uteis=DIAS_UTEIS_HISTORICO,
        gerador=gerador_ibov,
    )

    return tabela_benchmarks


def _caminho_csv(nome_arquivo: str) -> str:
    return os.path.join(DIRETORIO_DADOS, nome_arquivo)


def carregar_precos_ativos() -> pd.DataFrame:
    """
    Carrega a serie historica de precos dos ativos da carteira.

    Tenta ler do cache em CSV; se o arquivo nao existir ou estiver corrompido,
    gera novamente os dados simulados e salva o cache para as proximas execucoes.
    Esse e o "tratamento de erro" do projeto: como nao ha API externa (dados
    100% simulados), o unico ponto de falha possivel e leitura/escrita de arquivo.
    """
    caminho = _caminho_csv("precos_ativos.csv")
    try:
        tabela = pd.read_csv(caminho, index_col="data", parse_dates=True)
        if tabela.empty:
            raise ValueError("Cache de precos esta vazio")
        return tabela
    except (FileNotFoundError, ValueError, pd.errors.EmptyDataError):
        os.makedirs(DIRETORIO_DADOS, exist_ok=True)
        tabela = _gerar_precos_ativos()
        tabela.to_csv(caminho)
        return tabela


def carregar_benchmarks() -> pd.DataFrame:
    """Carrega (ou gera e cacheia) as series de CDI e Ibovespa em base 100."""
    caminho = _caminho_csv("benchmarks.csv")
    try:
        tabela = pd.read_csv(caminho, index_col="data", parse_dates=True)
        if tabela.empty:
            raise ValueError("Cache de benchmarks esta vazio")
        return tabela
    except (FileNotFoundError, ValueError, pd.errors.EmptyDataError):
        os.makedirs(DIRETORIO_DADOS, exist_ok=True)
        tabela = _gerar_benchmarks()
        tabela.to_csv(caminho)
        return tabela


def montar_tabela_posicoes(precos_ativos: pd.DataFrame) -> pd.DataFrame:
    """
    Monta a tabela de posicoes atuais da carteira: quantidade, preco medio
    (preco de compra simulado), preco atual, valor investido e valor atual
    por ativo.
    """
    linhas = []
    for ativo in COMPOSICAO_CARTEIRA:
        preco_medio = ativo.preco_inicial
        preco_atual = precos_ativos[ativo.ticker].iloc[-1]
        valor_investido = preco_medio * ativo.quantidade
        valor_atual = preco_atual * ativo.quantidade

        linhas.append(
            {
                "ticker": ativo.ticker,
                "nome": ativo.nome,
                "classe": ativo.classe,
                "quantidade": ativo.quantidade,
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


def calcular_serie_valor_carteira(precos_ativos: pd.DataFrame) -> pd.Series:
    """
    Calcula a evolucao do valor total da carteira ao longo do tempo,
    multiplicando a quantidade de cada ativo pelo seu preco em cada data
    e somando tudo.
    """
    valor_total = pd.Series(0.0, index=precos_ativos.index)
    for ativo in COMPOSICAO_CARTEIRA:
        valor_total += precos_ativos[ativo.ticker] * ativo.quantidade
    return valor_total
