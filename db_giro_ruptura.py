# ══════════════════════════════════════════════════════════════════════════════
# db_giro_ruptura.py  —  Consultas para o dashboard "Estoque · Giro & Ruptura"
#
# COMO USAR:
#   1) Cole estas funções no seu db.py (ou importe este módulo).
#   2) Elas reutilizam o mesmo get_engine()/_query() já existentes no db.py.
#      Se importar como módulo separado, troque a linha abaixo por:
#          from db import _query
#
# Casam com o schema real do projeto:
#   produto(id_produto, nome_produto, cod_barras, id_fornecedor)
#   estoque_geral(id_produto, id_empresa, saldo_disponivel)
#   pedido(id, data, tipo_pedido, status, cancelado_em, id_vendedor)
#   pedido_itens(id_pedido, id_produto, quantidade, valor_total, status)
#   vendedor(id_vendedor, id_empresa)
# ══════════════════════════════════════════════════════════════════════════════

from db import _query   # reaproveita engine + execução parametrizada do projeto


def load_giro_ruptura(dias: int = 30, lead_time: int = 15, id_empresa=None):
    """Giro, cobertura, classe ABC e status de ruptura por produto.

    Uma única consulta alimenta TODO o dashboard:
      • KPIs (risco, sem estoque, giro geral, cobertura mediana, classe A em risco)
      • Matriz Giro × Cobertura  (eixos: media_dia × cobertura_dias; cor: status)
      • Runway de ruptura        (ordenar por cobertura_dias, itens com saída > 0)
      • Tabela completa          (todas as colunas)

    Parâmetros
    ----------
    dias        : janela de saída considerada (30 / 60 / 90).
    lead_time   : prazo de reposição em dias. cobertura <= lead_time => 'Risco ruptura'.
    id_empresa  : separa estoque e saídas por empresa (None = consolidado).

    Classe ABC : participação acumulada no volume de SAÍDA do período
                 (A <= 80%, B <= 95%, C o restante; sem saída => C).
    Status     : Sem estoque | Risco ruptura | Parado | Excesso | Saudável
    """
    params = {"dias": int(dias), "lead": int(lead_time)}
    filtro_emp_saida = ""
    filtro_emp_estoque = ""
    if id_empresa is not None:
        params["emp"] = int(id_empresa)
        # pedido não tem id_empresa: a empresa vem do vendedor do pedido
        filtro_emp_saida = ("AND p.id_vendedor IN "
                            "(SELECT id_vendedor FROM vendedor WHERE id_empresa = :emp)")
        filtro_emp_estoque = "AND eg.id_empresa = :emp"

    sql = f"""
        WITH saidas AS (
            SELECT pi.id_produto,
                   SUM(pi.quantidade) AS qtd_saida
            FROM pedido p
            JOIN pedido_itens pi ON pi.id_pedido = p.id
            WHERE p.cancelado_em IS NULL
              AND p.status != 'CANCELADO'
              AND p.tipo_pedido IN ('PRE-VENDA', 'BRINDE', 'REPOSICAO')
              AND COALESCE(pi.status, 'ATIVO') = 'ATIVO'
              AND p.data >= CURRENT_DATE - make_interval(days => :dias)
              {filtro_emp_saida}
            GROUP BY pi.id_produto
        ),
        base AS (
            SELECT pr.id_produto,
                   pr.cod_barras,
                   pr.nome_produto                       AS produto,
                   pr.id_fornecedor,
                   COALESCE(eg.saldo_disponivel, 0)      AS estoque,
                   COALESCE(s.qtd_saida, 0)              AS saida_periodo,
                   ROUND(COALESCE(s.qtd_saida, 0)::numeric / :dias, 2) AS media_dia,
                   CASE WHEN COALESCE(eg.saldo_disponivel, 0) > 0
                        THEN ROUND(COALESCE(s.qtd_saida, 0)::numeric
                                   / eg.saldo_disponivel, 2)
                   END AS giro,
                   CASE WHEN COALESCE(s.qtd_saida, 0) > 0
                        THEN ROUND(COALESCE(eg.saldo_disponivel, 0)::numeric
                                   * :dias / s.qtd_saida, 1)
                   END AS cobertura_dias
            FROM produto pr
            LEFT JOIN estoque_geral eg
                   ON eg.id_produto = pr.id_produto {filtro_emp_estoque}
            LEFT JOIN saidas s ON s.id_produto = pr.id_produto
            WHERE COALESCE(eg.saldo_disponivel, 0) > 0
               OR COALESCE(s.qtd_saida, 0) > 0
        ),
        abc AS (
            SELECT *,
                   CASE WHEN SUM(saida_periodo) OVER () > 0
                        THEN SUM(saida_periodo) OVER (
                                 ORDER BY saida_periodo DESC, id_produto
                                 ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                             )::numeric / SUM(saida_periodo) OVER ()
                   END AS pct_acumulado
            FROM base
        )
        SELECT cod_barras,
               produto,
               id_fornecedor,
               estoque,
               saida_periodo,
               media_dia,
               giro,
               cobertura_dias,
               CASE
                   WHEN saida_periodo <= 0       THEN 'C'
                   WHEN pct_acumulado <= 0.80    THEN 'A'
                   WHEN pct_acumulado <= 0.95    THEN 'B'
                   ELSE 'C'
               END AS classe,
               CASE
                   WHEN saida_periodo > 0 AND estoque <= 0      THEN 'Sem estoque'
                   WHEN saida_periodo = 0                       THEN 'Parado'
                   WHEN cobertura_dias <= :lead                 THEN 'Risco ruptura'
                   WHEN cobertura_dias > 90                     THEN 'Excesso'
                   ELSE 'Saudável'
               END AS status
        FROM abc
        ORDER BY cobertura_dias ASC NULLS LAST
    """
    return _query(sql, params)


def kpis_giro_ruptura(df):
    """KPIs do topo do dashboard a partir do DataFrame de load_giro_ruptura.

    Retorna dict pronto para st.metric(...).
    """
    com_venda = df[(df["saida_periodo"] > 0) & (df["estoque"] > 0)]
    giro_geral = (com_venda["saida_periodo"].sum() / com_venda["estoque"].sum()
                  if len(com_venda) and com_venda["estoque"].sum() > 0 else 0)
    cob = df.loc[(df["estoque"] > 0) & (df["media_dia"] > 0), "cobertura_dias"].dropna()
    return {
        "risco_ruptura":     int((df["status"] == "Risco ruptura").sum()),
        "sem_estoque":       int((df["status"] == "Sem estoque").sum()),
        "giro_geral":        round(float(giro_geral), 2),
        "cobertura_mediana": int(cob.median()) if len(cob) else 0,
        "classe_a_risco":    int(((df["classe"] == "A") &
                                  (df["status"].isin(["Sem estoque", "Risco ruptura"]))).sum()),
    }


def runway_ruptura(df, limite: int = 12):
    """Produtos que rompem primeiro (para o gráfico 'Runway de ruptura')."""
    r = df[(df["estoque"] > 0) & (df["saida_periodo"] > 0)].copy()
    return r.sort_values("cobertura_dias").head(limite)


def classe_a_em_risco(df):
    """Lista priorizada de itens classe A zerados ou rompendo (compra urgente)."""
    r = df[(df["classe"] == "A") &
           (df["status"].isin(["Sem estoque", "Risco ruptura"]))].copy()
    return r.sort_values("cobertura_dias", na_position="first")

