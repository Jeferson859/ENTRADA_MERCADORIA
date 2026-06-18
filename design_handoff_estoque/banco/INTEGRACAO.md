# Integração com o banco PostgreSQL — Estoque · Giro & Ruptura

As telas em HTML (`Sistema.dc.html` e os módulos) são a **referência visual**.
Os dados reais vêm do seu PostgreSQL pelo `db.py`. Este pacote adiciona o que
faltava para os gráficos novos (classe ABC, status de ruptura, prazo de reposição).

## Arquivos

- **`db_giro_ruptura.py`** — cole as funções no seu `db.py` (ou importe o módulo).
  Reaproveita `get_engine()` e `_query()` já existentes.

## De cada elemento da tela → função do banco

| Elemento da tela (aba Giro & Cobertura)        | Função / fonte                                  |
|------------------------------------------------|-------------------------------------------------|
| KPIs do topo (risco, sem estoque, giro…)       | `kpis_giro_ruptura(df)`                         |
| Matriz Giro × Cobertura (bolhas)               | `df` → eixos `media_dia` × `cobertura_dias`, cor=`status`, tamanho=`estoque` |
| Runway de ruptura                              | `runway_ruptura(df)`                            |
| Tabela completa                                | `df` (todas as colunas)                         |
| **Aba Curva ABC** — Pareto / contagem A,B,C    | `df` agrupado por `classe` (ordenar por `saida_periodo`) |
| **Aba Curva ABC** — "Classe A em risco"        | `classe_a_em_risco(df)`                         |
| **Aba Tempo Parado** — distribuição + tabela   | `load_idade_estoque(id_empresa)` (já existe no db.py) |

Os filtros da tela mapeiam direto nos parâmetros:

- **Empresa** → `id_empresa` (use `load_empresas()` para popular o select)
- **Janela de saída 30/60/90** → `dias`
- **Prazo de reposição (slider)** → `lead_time`
- **Busca / chips de status / chips de classe** → filtros no próprio DataFrame (client-side), sem nova consulta

## Exemplo de página Streamlit

```python
import streamlit as st
import db
from db_giro_ruptura import (
    load_giro_ruptura, kpis_giro_ruptura, runway_ruptura, classe_a_em_risco,
)

st.set_page_config(page_title="Estoque · Giro & Ruptura", layout="wide")

# ---- filtros ----
empresas = db.load_empresas()
col1, col2, col3 = st.columns([2, 1, 1])
emp = col1.selectbox("Empresa", empresas["nome_empresa"])
id_emp = int(empresas.loc[empresas["nome_empresa"] == emp, "id_empresa"].iloc[0])
dias = col2.radio("Janela de saída", [30, 60, 90], horizontal=True)
lead = col3.slider("Prazo de reposição (dias)", 5, 45, 15, step=5)

# ---- uma consulta alimenta tudo ----
df = load_giro_ruptura(dias=dias, lead_time=lead, id_empresa=id_emp)
k = kpis_giro_ruptura(df)

c = st.columns(5)
c[0].metric("Risco de ruptura", k["risco_ruptura"])
c[1].metric("Sem estoque", k["sem_estoque"])
c[2].metric("Giro geral", f'{k["giro_geral"]}x')
c[3].metric("Cobertura mediana", f'{k["cobertura_mediana"]}d')
c[4].metric("Classe A em risco", k["classe_a_risco"])

st.subheader("Runway de ruptura")
st.dataframe(runway_ruptura(df)[["produto", "estoque", "cobertura_dias", "status"]])

st.subheader("Classe A em risco")
st.dataframe(classe_a_em_risco(df)[["produto", "estoque", "cobertura_dias", "status"]])

st.subheader("Visão completa")
st.dataframe(df)
```

## Notas

- Mantém suas regras: ignora cancelados, conta itens `ATIVO`, saídas de
  `PRE-VENDA + BRINDE + REPOSICAO`, estoque de `estoque_geral.saldo_disponivel`,
  empresa derivada do vendedor do pedido — idêntico ao seu `load_giro_estoque`.
- A classe ABC é calculada **dentro da janela e da empresa selecionadas** (com
  `SUM() OVER` acumulado), então muda conforme o filtro — comportamento correto.
- `cobertura_dias` e `giro` são `NULL` quando não há saída/estoque; trate como
  "sem saída" na tela (já é o que o protótipo faz).
```
