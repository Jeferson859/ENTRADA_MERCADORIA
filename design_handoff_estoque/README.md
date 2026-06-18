# Handoff: Sistema de Gestão de Estoque — AdriLar

Pacote para implementação via **Claude Code** no app real (Streamlit + PostgreSQL).
Repositório base: `Jeferson859/ENTRADA_MERCADORIA`.

---

## 1. Visão geral

Redesign de três módulos do sistema interno de controle de mercadoria, com
**filtros interativos (sem recarregar)** e **dashboards novos de giro e ruptura**:

- **Estoque · Giro & Ruptura** — matriz Giro×Cobertura, runway de ruptura, curva ABC, tempo parado
- **Vendas** — tendência semanal, rotas, vendedor×estado, produtos, faixa etária
- **Pedidos** — movimentação, busca de pedido, ajuste de estoque

Os três são unidos por um shell com **navegação lateral** (`Sistema.dc.html`).

---

## 2. Sobre os arquivos de design

Os arquivos `.dc.html` deste pacote são **referências de design feitas em HTML** —
protótipos que mostram a aparência e o comportamento pretendidos, **não** código de
produção para copiar direto. Eles rodam no navegador com dados de demonstração.

A tarefa do desenvolvedor é **recriar estas telas no ambiente real do projeto**.
O app atual é **Streamlit (Python)** — então as telas devem virar páginas Streamlit
(`pages/*.py`) usando o `db.py` existente para os dados reais. Se preferir migrar
para outro front-end (React etc.), use estes arquivos como espec visual fiel.

> ⚠️ Os `.dc.html` usam um runtime próprio (`support.js`) só para o protótipo abrir
> no navegador. **Não** porte o `support.js` — porte o **layout, os tokens e as
> regras de negócio** descritos abaixo.

---

## 3. Fidelidade

**Alta fidelidade (hi-fi).** Cores, tipografia, espaçamento e interações são finais.
Recrie pixel-a-pixel usando as bibliotecas/padrões do destino. Em Streamlit, aplique
o tema via `.streamlit/config.toml` + CSS injetado; os gráficos podem ser Plotly/Altair
respeitando as cores abaixo.

---

## 4. Design tokens

### Cores
| Uso | Hex |
|---|---|
| Fundo base | `#070B12` |
| Fundo sidebar (gradiente) | `#0B1322` → `#080D17` |
| Superfície de card | `rgba(255,255,255,.025)` sobre o fundo |
| Borda de card / divisória | `rgba(59,169,255,.16)` |
| Texto primário | `#F2F6FC` |
| Texto corpo | `#D7DEEA` |
| Texto secundário | `#9AA3B4` / `#8B92A5` |
| Texto sutil / label | `#6B7385` / `#5E6678` |
| **Azul primário** | `#2E7CF6` |
| **Ciano** | `#00D4FF` / `#22D3EE` |
| Azul claro (destaque texto) | `#3BA9FF` / `#9CC6FF` |
| Verde (saudável/positivo) | `#00E0A1` |
| Âmbar (excesso/atenção) | `#FFC53D` |
| Laranja (risco) | `#FF8A4C` |
| Vermelho (ruptura/sem estoque) | `#FF5C6C` |
| Roxo (capital/secundário) | `#7B8BFF` |
| Gradiente de marca | `linear-gradient(150deg,#2E7CF6,#00D4FF)` |

### Status de estoque (cor + fundo do pill)
| Status | Texto | Fundo |
|---|---|---|
| Sem estoque | `#FF5C6C` | `rgba(255,92,108,.12)` |
| Risco ruptura | `#FF8A4C` | `rgba(255,138,76,.12)` |
| Parado | `#8B92A5` | `rgba(139,146,165,.12)` |
| Excesso | `#FFC53D` | `rgba(255,197,61,.12)` |
| Saudável | `#00E0A1` | `rgba(0,224,161,.12)` |

### Classe ABC
`A` = `#00E0A1` · `B` = `#FFC53D` · `C` = `#7B8499`

### Tipografia
- Família: **Inter** (400/500/600/700/800/900), fallback `system-ui, sans-serif`
- Título de página: 21px / 800 / letter-spacing −.02em
- Subtítulo de página: 12px / 500 / `#6B7385`
- Valor de KPI: 26–29px / 800 / tabular-nums
- Label de KPI: 10.5px / 600 / uppercase / letter-spacing .07em
- Título de card: 12px / 700 / uppercase / letter-spacing .08em / `#9CC6FF`
- Corpo de tabela: 12.5px / tabular-nums
- Cabeçalho de tabela: 10.5px / 700 / uppercase / letter-spacing .05em / `#6B7385`

### Forma
- Raio: cards 14–16px · pills/inputs 10–11px · chips 20px (pílula) · badge ABC 5px
- Borda de card: 1px `rgba(59,169,255,.16)`
- Sombra da marca: `0 6px 20px rgba(46,124,246,.35)`
- Faixa de acento no topo do KPI: barra 3px na cor do KPI
- Fundo de página: `radial-gradient(1200px 600px at 80% -10%, rgba(46,124,246,.10), transparent 60%)` sobre `#070B12`
- Espaçamento de página: padding 26px 30px · gap entre cards 12–16px · max-width do conteúdo 1400px

---

## 5. Telas

### 5.1 Shell — `Sistema.dc.html`
- **Layout**: flex horizontal. Sidebar fixa de **236px** (sticky, 100vh) + `main` flexível.
- **Sidebar**: marca no topo (ícone gradiente 42px + "AdriLar / Estoque"), nav vertical
  (Estoque 📦 · Vendas 📊 · Pedidos 📋), rodapé com avatar do usuário + versão.
- Item ativo: fundo `rgba(59,169,255,.13)`, texto `#EAF2FF`, barra vertical 3px gradiente à esquerda.
- Troca de seção é só mostrar/esconder o módulo (estado preservado). Em Streamlit, use as páginas nativas da pasta `pages/` como navegação.

### 5.2 Estoque · Giro & Ruptura — `Estoque Giro e Ruptura.dc.html`
Tela principal do pedido. **Filtros** (recalculam na hora): Empresa (select), Janela
de saída (30/60/90, segmented), Prazo de reposição (slider 5–45d), Busca (texto),
chips de Status (multi) e de Classe ABC (multi), "limpar filtros".

- **6 KPIs**: Risco de ruptura · Sem estoque · Giro geral (×) · Cobertura mediana (d) · Classe A em risco · Capital parado (R$ de itens +90d).
- **Abas**:
  - **Giro & Cobertura**: *Runway de ruptura* (barras horizontais dos 12 que rompem primeiro, marca tracejada no prazo de reposição) + *Matriz Giro×Cobertura* (scatter: x=cobertura 0–120d, y=demanda un/dia, tamanho da bolha=estoque, cor=status; faixa vermelha = dentro do prazo; tooltip on-hover) + tabela completa ordenável.
  - **Curva ABC**: Pareto top-25 (barras por classe + linha % acumulado) + cards A/B/C + lista "Classe A em risco".
  - **Tempo Parado**: 4 stats + histograma por faixa de dias parado (0–30/31–60/61–90/91–180/+180) + tabela por dias desde última saída.

### 5.3 Vendas — `Dashboard de Vendas.dc.html`
Filtro de período (Tudo/30/90/Este ano). 6 KPIs (faturamento, pedidos, ticket, rotas,
clientes, top vendedor). Abas: **Rotas** (tendência semanal em área + top rotas + tabela
com nível Alto/Médio/Baixo por quartil) · **Vendedores** (heatmap vendedor×estado +
ranking) · **Produtos** (busca + ranking por faturamento/quantidade) · **Faixa Etária**
(barras faturamento+ticket + donut de distribuição de clientes).

### 5.4 Pedidos — `Pedidos.dc.html`
Abas: **Movimentação** (filtros busca/status/tipo/vendedor + 6 KPIs + barras por dia +
barras por status + donut por tipo + tabela) · **Buscar Pedido** (por ID → cabeçalho +
metadados + itens) · **Ajuste de Estoque** (KPIs de contagem + tabela de divergências).

---

## 6. Interações & estado

- **Todos os filtros são instantâneos** (client-side sobre os dados já carregados — não refazem consulta, exceto quando muda Empresa/Janela/Prazo, que são parâmetros da query).
- Estado por módulo: empresa, janela, lead time, busca, filtros de status/classe, aba ativa, chave+direção de ordenação, hover da matriz.
- Ordenação de tabela: clique no cabeçalho alterna asc/desc; `cobertura_dias` nula vai para o fim.
- Hover na matriz: tooltip com nome, cobertura, giro, estoque, status.
- Sem estados de loading/erro no protótipo — adicione conforme o padrão do app real (spinner do Streamlit).

---

## 7. Dados reais (PostgreSQL) — pasta `banco/`

O protótipo usa dados de demonstração. Para ligar ao banco:

- **`banco/db_giro_ruptura.py`** — query única `load_giro_ruptura(dias, lead_time, id_empresa)`
  que devolve, por produto: estoque, saída no período, média/dia, giro, cobertura_dias,
  **classe ABC** (participação acumulada no volume de saída) e **status de ruptura**.
  Inclui helpers: `kpis_giro_ruptura`, `runway_ruptura`, `classe_a_em_risco`.
  Reaproveita `get_engine()`/`_query()` do `db.py` e segue as regras existentes
  (ignora cancelados, itens `ATIVO`, saídas PRE-VENDA+BRINDE+REPOSICAO, estoque de
  `estoque_geral.saldo_disponivel`, empresa derivada do vendedor).
- **`banco/INTEGRACAO.md`** — mapa "elemento da tela → função do banco", correspondência
  dos filtros com os parâmetros, e exemplo completo de página Streamlit.

Schema usado (do `db.py` real): `produto`, `estoque_geral`, `pedido`, `pedido_itens`,
`vendedor`. A aba **Tempo Parado** reaproveita `load_idade_estoque()` existente.

### Tarefa para o Claude Code
1. Colar as funções de `banco/db_giro_ruptura.py` no `db.py` (ou importar o módulo).
2. Criar `pages/Estoque_Giro_Ruptura.py` recriando a tela 5.2 com o tema da seção 4,
   ligando filtros → parâmetros e usando os helpers para KPIs/gráficos.
3. Aplicar o mesmo tema às páginas de Vendas e Pedidos, ligando às funções já
   existentes no `db.py` (`load_*` de vendas/pedidos).
4. Aplicar o tema global em `.streamlit/config.toml` (base dark) + CSS injetado para
   cards/KPIs/chips conforme os tokens.

---

## 8. Arquivos deste pacote

| Arquivo | O que é |
|---|---|
| `Sistema.dc.html` | Shell com navegação lateral (referência visual) |
| `Estoque Giro e Ruptura.dc.html` | Tela principal — giro & ruptura |
| `Dashboard de Vendas.dc.html` | Tela de vendas |
| `Pedidos.dc.html` | Tela de pedidos |
| `support.js` | Runtime do protótipo — **não portar**, só faz os HTML abrirem |
| `banco/db_giro_ruptura.py` | Queries PostgreSQL para colar no `db.py` |
| `banco/INTEGRACAO.md` | Guia de integração + exemplo Streamlit |

Para ver os protótipos: abra os `.dc.html` num navegador (precisam do `support.js` ao lado).
