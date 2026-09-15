"""
metrics.py

Funcoes de calculo de rentabilidade e risco da carteira:
- retorno acumulado em janelas de tempo (1m, 6m, 12m, desde o inicio)
- serie em "base 100" para comparar carteira, CDI e Ibovespa
- volatilidade anualizada
- indice de Sharpe simplificado
- drawdown maximo
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DIAS_UTEIS_ANO = 252

# Janelas de tempo usadas no calculo de retorno acumulado (em dias uteis)
JANELAS_DIAS_UTEIS = {
    "1 mes": 21,
    "6 meses": 126,
    "12 meses": 252,
}


def calcular_base_100(serie: pd.Series) -> pd.Series:
    """Reindexa uma serie de precos/valores para comecar em 100."""
    return serie / serie.iloc[0] * 100


def calcular_retornos_diarios(serie: pd.Series) -> pd.Series:
    """Calcula os retornos diarios percentuais a partir de uma serie de precos."""
    return serie.pct_change().dropna()


def calcular_retorno_periodo(serie: pd.Series, dias_uteis: int) -> float:
    """
    Calcula o retorno acumulado (%) nos ultimos `dias_uteis` da serie.
    Se a serie tiver menos historico que o solicitado, usa o inicio disponivel.
    """
    dias_uteis = min(dias_uteis, len(serie) - 1)
    valor_inicial = serie.iloc[-(dias_uteis + 1)]
    valor_final = serie.iloc[-1]
    return (valor_final / valor_inicial - 1) * 100


def calcular_retorno_desde_inicio(serie: pd.Series) -> float:
    """Calcula o retorno acumulado (%) desde o primeiro valor da serie."""
    return (serie.iloc[-1] / serie.iloc[0] - 1) * 100


def calcular_retornos_por_janela(serie: pd.Series) -> dict[str, float]:
    """Retorna um dicionario {nome_da_janela: retorno_pct} para todas as janelas padrao."""
    resultado = {
        nome: calcular_retorno_periodo(serie, dias) for nome, dias in JANELAS_DIAS_UTEIS.items()
    }
    resultado["Desde o inicio"] = calcular_retorno_desde_inicio(serie)
    return resultado


def calcular_volatilidade_anualizada(retornos_diarios: pd.Series) -> float:
    """
    Calcula a volatilidade anualizada (%) a partir dos retornos diarios,
    multiplicando o desvio padrao diario pela raiz quadrada de 252
    (numero aproximado de dias uteis no ano).
    """
    return retornos_diarios.std() * np.sqrt(DIAS_UTEIS_ANO) * 100


def calcular_sharpe_ratio(
    retornos_diarios: pd.Series, taxa_livre_risco_anual: float
) -> float:
    """
    Calcula o indice de Sharpe simplificado: mede o retorno obtido acima da
    taxa livre de risco (CDI) para cada unidade de risco (volatilidade) assumida.

    Formula: (retorno anualizado da carteira - taxa livre de risco) / volatilidade anualizada
    """
    retorno_anualizado = retornos_diarios.mean() * DIAS_UTEIS_ANO
    volatilidade_anualizada = retornos_diarios.std() * np.sqrt(DIAS_UTEIS_ANO)

    if volatilidade_anualizada == 0:
        return 0.0

    return (retorno_anualizado - taxa_livre_risco_anual) / volatilidade_anualizada


def calcular_drawdown_maximo(serie: pd.Series) -> float:
    """
    Calcula o drawdown maximo (%): a maior queda percentual da carteira
    em relacao ao seu pico historico ate aquele momento.
    """
    pico_historico = serie.cummax()
    drawdown = (serie - pico_historico) / pico_historico
    return drawdown.min() * 100


def calcular_serie_drawdown(serie: pd.Series) -> pd.Series:
    """Calcula a serie completa de drawdown (%) ao longo do tempo, para plotagem."""
    pico_historico = serie.cummax()
    return (serie - pico_historico) / pico_historico * 100


def calcular_metricas_risco(
    serie_valor_carteira: pd.Series, taxa_livre_risco_anual: float
) -> dict[str, float]:
    """Agrupa todas as metricas de risco da carteira em um unico dicionario."""
    retornos_diarios = calcular_retornos_diarios(serie_valor_carteira)
    return {
        "volatilidade_anualizada": calcular_volatilidade_anualizada(retornos_diarios),
        "sharpe_ratio": calcular_sharpe_ratio(retornos_diarios, taxa_livre_risco_anual),
        "drawdown_maximo": calcular_drawdown_maximo(serie_valor_carteira),
    }
