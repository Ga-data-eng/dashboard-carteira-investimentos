# Dashboard de Carteira de Investimentos

Dashboard interativo de uma carteira de investimentos diversificada (ações da B3 com cotação
real via yfinance, fundos e renda fixa simulados) que apresenta métricas de rentabilidade, risco
e alocação — projeto de portfólio construído durante minha transição do mercado financeiro
(CPA-10, CPA-20, CEA) para Análise de Dados.

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

A carteira fictícia tem:

- 5 ações da B3 (**dados reais**, via `yfinance`): PETR4, VALE3, ITUB4, WEGE3, BBAS3
- Índice **Ibovespa** (**dados reais**, via `yfinance`, ticker `^BVSP`), usado como benchmark
- 2 fundos de investimento simulados: Fundo Multimercado e Fundo de Ações Global
- 1 posição de renda fixa simulada: Tesouro Selic (rentabilidade atrelada ao CDI)
- CDI simulado como benchmark (não há fonte gratuita via yfinance; ver melhorias futuras)
- Pesos de alocação diferentes entre os ativos (ver `data_loader.py`), convertidos em quantidade
  de cada ativo a partir de um valor total investido hipotético, de forma que a alocação bata
  exatamente com o peso-alvo no primeiro dia do histórico

Fundos e renda fixa são gerados com **Movimento Browniano Geométrico** (GBM) — o modelo clássico
para simular séries de preços financeiros, com retorno esperado (drift) e volatilidade próprios
de cada ativo — porque não existe ticker público para uma carteira fictícia de fundos.

**Tratamento de erro em 3 níveis** para os dados reais (ações e Ibovespa), do mais para o menos
confiável:
1. Busca ao vivo na API do `yfinance`
2. Se falhar (sem internet, API fora do ar), usa o último CSV salvo em cache em `data/`
3. Se não houver cache nenhum, gera uma série simulada via GBM como último recurso

O dashboard mostra no topo, de forma transparente, qual dessas 3 fontes foi usada em cada
carregamento. Um botão "Atualizar cotações" força uma nova busca (por padrão, os dados ficam em
cache por 30 minutos para não sobrecarregar a API a cada interação na tela).

## Stack técnica

- Python 3.11+
- [Streamlit](https://streamlit.io/) para o dashboard interativo
- [pandas](https://pandas.pydata.org/) e [NumPy](https://numpy.org/) para manipulação de dados
- [Plotly](https://plotly.com/python/) para os gráficos interativos
- [yfinance](https://github.com/ranaroussi/yfinance) para cotações reais de ações da B3 e do Ibovespa

## Estrutura do projeto

```
dashboard-carteira-investimentos/
├── app.py            # interface Streamlit (as 4 abas do dashboard)
├── data_loader.py     # busca (yfinance) + simulação + cache dos dados da carteira e benchmarks
├── metrics.py         # cálculos de rentabilidade e risco
├── data/               # cache dos CSVs (real ou simulado, conforme o fallback) - ignorado pelo Git
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

- **Dados reais de mercado (ações e Ibovespa) com fallback em 3 níveis.** yfinance ao vivo → cache
  local em CSV → simulação via GBM. O dashboard nunca quebra por falta de internet ou instabilidade
  da API, e sempre deixa explícito qual fonte foi usada.
- **`threads=False` nas chamadas ao yfinance.** Ao testar, o download simultâneo de múltiplos
  tickers (`threads=True`, padrão da biblioteca) esbarrava intermitentemente num bug conhecido de
  "database is locked" no cache SQLite interno do yfinance. Desativar o paralelismo eliminou o
  problema, ao custo de um download levemente mais lento.
- **Fundos e renda fixa continuam simulados via Movimento Browniano Geométrico (GBM)** — não existe
  ticker público para uma carteira fictícia de fundos. O CDI também é simulado, como taxa composta
  diária, pela mesma razão (não há fonte gratuita de CDI real no yfinance).
- **Quantidade de cada ativo calculada a partir do peso-alvo**, e não fixada no código: dado um
  valor total investido hipotético, a quantidade comprada de cada ativo é `peso_alvo × valor_total
  / preço no primeiro dia do histórico`. Isso evita que os pesos-alvo definidos em `data_loader.py`
  fiquem desalinhados do preço real de mercado, que muda a cada atualização.
- **Cache do Streamlit com TTL de 30 minutos** (`st.cache_data(ttl=1800)`) mais um botão manual de
  atualização, para equilibrar dados atualizados com não sobrecarregar a API a cada interação na
  tela.
- **Separação em módulos** (`data_loader.py` para dados, `metrics.py` para os cálculos,
  `app.py` só para a interface) em vez de um único script, para isolar a lógica de negócio da
  camada de apresentação — mais fácil de testar e de explicar em entrevista.
- **Paleta de cores fixa e consistente** entre todos os gráficos (uma cor por classe de ativo, uma
  cor por benchmark, verde/vermelho reservado para status de retorno positivo/negativo).

## Possíveis melhorias futuras

- Buscar o CDI histórico real via Banco Central (`python-bcb`), em vez de simulado — hoje é o único
  benchmark ainda simulado.
- Simular os fundos com uma metodologia mais próxima de fundos reais (ex.: replicar a
  volatilidade/correlação de um índice de referência, em vez de GBM puro).
- Permitir editar a composição da carteira (ativos, pesos, valor investido) pela própria interface,
  em vez de fixa no código.
- Adicionar métricas adicionais: Sortino Ratio, Value at Risk (VaR), correlação entre ativos.
- Deploy no [Streamlit Community Cloud](https://streamlit.io/cloud) para acesso sem rodar
  localmente (checar se o ambiente de deploy tem acesso de saída à API do Yahoo Finance).

## Aviso

Projeto **educacional e de portfólio**. As quantidades e o valor total investido são fictícios; os
preços das ações e do Ibovespa são reais, mas isso não constitui recomendação de investimento.
