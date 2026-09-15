# Dashboard de Carteira de Investimentos

Dashboard interativo que simula uma carteira de investimentos diversificada (ações da B3, fundos
e renda fixa) e apresenta métricas de rentabilidade, risco e alocação — projeto de portfólio
construído durante minha transição do mercado financeiro (CPA-10, CPA-20, CEA) para Análise de
Dados.

## Objetivo

Aplicar, num caso de uso que já domino do dia a dia bancário, as ferramentas do ciclo de dados:
modelagem de dados de mercado, cálculo de métricas de risco/retorno e visualização interativa.
O foco não é prever preços, e sim **transformar uma carteira bruta em indicadores que sustentam
decisão** — o mesmo raciocínio usado numa mesa de investimentos, agora em Python.

## Screenshots

> Rode o dashboard localmente (`streamlit run app.py`) e salve os prints das 4 abas em
> `docs/screenshots/`, substituindo os links abaixo:

| Visão Geral | Rentabilidade |
|---|---|
| ![Visão geral da carteira](docs/screenshots/visao-geral.png) | ![Rentabilidade da carteira](docs/screenshots/rentabilidade.png) |

| Risco | Detalhamento por Ativo |
|---|---|
| ![Métricas de risco](docs/screenshots/risco.png) | ![Detalhamento por ativo](docs/screenshots/detalhamento.png) |

## Funcionalidades

- **Visão geral**: valor investido, valor atual, retorno total (R$ e %) e gráfico de rosca com a
  alocação por classe de ativo (Renda Variável, Fundos, Renda Fixa).
- **Rentabilidade**: evolução do valor da carteira ao longo do tempo, comparação com CDI e
  Ibovespa em base 100, e retorno acumulado em janelas de 1 mês, 6 meses, 12 meses e desde o início.
- **Risco**: volatilidade anualizada, Sharpe Ratio simplificado (contra o CDI) e drawdown máximo,
  com gráfico da evolução do drawdown.
- **Detalhamento por ativo**: tabela com quantidade, preço médio, preço atual, retorno individual
  e peso na carteira, com destaque visual verde/vermelho para retorno positivo/negativo.

## Sobre os dados

Este projeto usa **dados 100% simulados** (nenhuma chamada a API externa de cotações). A carteira
fictícia tem:

- 5 ações da B3: PETR4, VALE3, ITUB4, WEGE3, BBAS3
- 2 fundos de investimento: Fundo Multimercado e Fundo de Ações Global
- 1 posição de renda fixa: Tesouro Selic (rentabilidade atrelada ao CDI)
- Pesos de alocação diferentes entre os ativos (ver `data_loader.py`)

Os preços são gerados com **Movimento Browniano Geométrico** (GBM) — o modelo clássico para
simular séries de preços de ativos financeiros, com retorno esperado (drift) e volatilidade
próprios de cada ativo. CDI e Ibovespa são simulados como benchmark de comparação. Os dados
gerados são cacheados em CSV na pasta `data/` (ignorada pelo Git) para que a carteira não mude a
cada vez que o dashboard é recarregado.

## Stack técnica

- Python 3.11+
- [Streamlit](https://streamlit.io/) para o dashboard interativo
- [pandas](https://pandas.pydata.org/) e [NumPy](https://numpy.org/) para manipulação de dados
- [Plotly](https://plotly.com/python/) para os gráficos interativos

## Estrutura do projeto

```
dashboard-carteira-investimentos/
├── app.py            # interface Streamlit (as 4 abas do dashboard)
├── data_loader.py     # geração/cache dos dados simulados da carteira e benchmarks
├── metrics.py         # cálculos de rentabilidade e risco
├── data/               # cache dos CSVs gerados (criado automaticamente, ignorado pelo Git)
├── docs/screenshots/   # prints do dashboard para este README
├── requirements.txt
└── .gitignore
```

## Como instalar e rodar localmente

```bash
# 1. Clone o repositório
git clone https://github.com/<seu-usuario>/dashboard-carteira-investimentos.git
cd dashboard-carteira-investimentos

# 2. Crie e ative um ambiente virtual (opcional, mas recomendado)
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Rode o dashboard
streamlit run app.py
```

O dashboard abre em `http://localhost:8501`.

## Principais decisões técnicas

- **Dados 100% simulados, sem dependência de API externa.** Prioriza reprodutibilidade: qualquer
  pessoa clona o repositório e o dashboard funciona offline, sem chave de API nem risco de rate
  limit. As séries de preço usam uma semente (`seed`) fixa, então a carteira é sempre a mesma entre
  execuções — importante para poder discutir os números em uma entrevista.
- **Movimento Browniano Geométrico (GBM)** em vez de números aleatórios simples, para gerar séries
  de preços com propriedades estatísticas realistas (retornos log-normais, volatilidade
  configurável por ativo).
- **Cache em CSV na pasta `data/`** com fallback automático: se o arquivo não existir ou estiver
  corrompido, os dados são regenerados e salvos novamente — é o "tratamento de erro" do projeto,
  já que não há uma API externa que possa falhar.
- **Separação em módulos** (`data_loader.py` para dados, `metrics.py` para os cálculos,
  `app.py` só para a interface) em vez de um único script, para isolar a lógica de negócio da
  camada de apresentação — mais fácil de testar e de explicar em entrevista.
- **Paleta de cores fixa e consistente** entre todos os gráficos (uma cor por classe de ativo, uma
  cor por benchmark, verde/vermelho reservado para status de retorno positivo/negativo).

## Possíveis melhorias futuras

- Adicionar suporte a dados reais via `yfinance` como opção alternativa (a estrutura de
  `data_loader.py` já isola a origem dos dados, então trocar a simulação por uma chamada real é
  uma mudança localizada).
- Buscar CDI e Ibovespa históricos reais via Banco Central (`python-bcb`) ou B3, em vez de
  simulados.
- Permitir editar a composição da carteira (ativos, pesos, quantidades) pela própria interface,
  em vez de fixa no código.
- Adicionar métricas adicionais: Sortino Ratio, Value at Risk (VaR), correlação entre ativos.
- Deploy no [Streamlit Community Cloud](https://streamlit.io/cloud) para acesso sem rodar
  localmente.

## Aviso

Projeto **educacional e de portfólio**. Os dados são simulados e não constituem recomendação de
investimento.
