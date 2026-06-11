import os
from urllib.parse import quote_plus
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()


def _get_secret(key: str, default: str = None):
    try:
        import streamlit as st
        return st.secrets.get(key, os.getenv(key, default))
    except Exception:
        return os.getenv(key, default)


# CTE que extrai o mapeamento correto id_vendedor → nome_vendedor via view
_VENDEDOR_CTE = """
    vendedor_map AS (
        SELECT DISTINCT id_vendedor, nome_vendedor
        FROM vw_divergencia_estoque
        WHERE id_vendedor IS NOT NULL
    )
"""

# Filtro padrão dos dashboards: ignora pedidos cancelados
_FILTRO_VALIDO = "p.cancelado_em IS NULL AND p.status != 'CANCELADO'"


def get_engine():
    host = _get_secret("DB_HOST", "localhost")
    port = _get_secret("DB_PORT", "5432")
    name = _get_secret("DB_NAME")
    user = _get_secret("DB_USER")
    password = _get_secret("DB_PASSWORD")

    if not all([name, user, password]):
        raise ValueError("Credenciais incompletas. Verifique o arquivo .env ou os Secrets do Streamlit Cloud.")

    url = f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{name}"
    return create_engine(url)


def _query(sql: str, params: dict = None) -> pd.DataFrame:
    """Executa uma query parametrizada e devolve DataFrame."""
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def _clausula_periodo(clauses: list, params: dict, data_ini, data_fim):
    """Adiciona filtro de período (p.data) às cláusulas, se informado."""
    if data_ini:
        clauses.append("p.data >= :data_ini")
        params["data_ini"] = data_ini
    if data_fim:
        clauses.append("p.data <= :data_fim")
        params["data_fim"] = data_fim


# ══════════════════════════════════════════════════════════════════════════════
# CONSULTAS — app.py (Movimentação / Buscar Pedido / Ajuste de Estoque)
# ══════════════════════════════════════════════════════════════════════════════

def load_pedidos(data_ini=None, data_fim=None, status=None, tipo_pedido=None, id_vendedor=None) -> pd.DataFrame:
    clauses = ["1=1"]
    params = {}
    _clausula_periodo(clauses, params, data_ini, data_fim)

    if status:
        clauses.append("p.status = :status")
        params["status"] = status
    if tipo_pedido:
        clauses.append("p.tipo_pedido = :tipo_pedido")
        params["tipo_pedido"] = tipo_pedido
    if id_vendedor:
        clauses.append("p.id_vendedor = :id_vendedor")
        params["id_vendedor"] = id_vendedor

    where = " AND ".join(clauses)

    sql = f"""
        WITH {_VENDEDOR_CTE}
        SELECT
            p.id,
            p.data,
            p.tipo_pedido,
            p.status,
            p.valor_total,
            p.id_cliente,
            vm.nome_vendedor AS vendedor,
            p.id_rota,
            p.obs,
            p.created_at,
            p.cancelado_em
        FROM pedido p
        LEFT JOIN vendedor_map vm ON vm.id_vendedor = p.id_vendedor
        WHERE {where}
        ORDER BY p.data DESC
    """
    return _query(sql, params)


def buscar_pedido_por_id(pedido_id: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    sql_pedido = f"""
        WITH {_VENDEDOR_CTE}
        SELECT
            p.id,
            p.data,
            p.tipo_pedido,
            p.status,
            p.valor_total,
            p.id_cliente,
            vm.nome_vendedor AS vendedor,
            p.id_rota,
            p.obs,
            p.created_at,
            p.updated_at,
            p.cancelado_em
        FROM pedido p
        LEFT JOIN vendedor_map vm ON vm.id_vendedor = p.id_vendedor
        WHERE p.id = :pid
    """

    sql_itens = """
        SELECT
            pi.id,
            pr.nome_produto,
            pr.cod_barras,
            pi.quantidade,
            pi.valor_unitario,
            pi.valor_total,
            pi.status,
            pi.obs
        FROM pedido_itens pi
        LEFT JOIN produto pr ON pr.id_produto = pi.id_produto
        WHERE pi.id_pedido = :pid
        ORDER BY pi.id
    """

    df_pedido = _query(sql_pedido, {"pid": pedido_id})
    df_itens = _query(sql_itens, {"pid": pedido_id})
    return df_pedido, df_itens


def buscar_pedidos_por_produto(cod_barras: str) -> pd.DataFrame:
    sql = f"""
        WITH {_VENDEDOR_CTE}
        SELECT
            p.id AS id_pedido,
            p.data,
            p.tipo_pedido,
            p.status,
            p.valor_total,
            p.id_cliente,
            vm.nome_vendedor AS vendedor,
            pr.cod_barras,
            pr.nome_produto,
            pi.quantidade,
            pi.valor_unitario,
            pi.valor_total AS valor_item
        FROM pedido_itens pi
        JOIN pedido p ON p.id = pi.id_pedido
        JOIN produto pr ON pr.id_produto = pi.id_produto
        LEFT JOIN vendedor_map vm ON vm.id_vendedor = p.id_vendedor
        WHERE pr.cod_barras ILIKE :cod
        ORDER BY p.data DESC
    """
    return _query(sql, {"cod": f"%{cod_barras}%"})


def buscar_ids_por_produto(termo: str) -> list[int]:
    sql = """
        SELECT DISTINCT pi.id_pedido
        FROM pedido_itens pi
        JOIN produto pr ON pr.id_produto = pi.id_produto
        WHERE pr.nome_produto ILIKE :termo
           OR pr.cod_barras ILIKE :termo
    """
    df = _query(sql, {"termo": f"%{termo}%"})
    return df["id_pedido"].tolist()


def load_contagens(data_ini=None, data_fim=None, status=None) -> pd.DataFrame:
    clauses = ["1=1"]
    params = {}

    if data_ini:
        clauses.append("c.data >= :data_ini")
        params["data_ini"] = data_ini
    if data_fim:
        clauses.append("c.data <= :data_fim")
        params["data_fim"] = data_fim
    if status:
        clauses.append("c.status = :status")
        params["status"] = status

    where = " AND ".join(clauses)

    sql = f"""
        SELECT
            c.id,
            c.data,
            c.status,
            c.obs,
            u.name AS criado_por,
            COUNT(ci.id) AS total_itens,
            COUNT(ci.id) FILTER (WHERE ci.quantidade_fisica <> ci.quantidade_sistema) AS itens_divergentes,
            SUM(ci.quantidade_fisica - ci.quantidade_sistema) AS saldo_ajuste
        FROM contagem_estoque c
        LEFT JOIN users u ON u.id = c.created_by
        LEFT JOIN contagem_estoque_item ci ON ci.id_contagem = c.id
        WHERE {where}
        GROUP BY c.id, c.data, c.status, c.obs, u.name
        ORDER BY c.data DESC
    """
    return _query(sql, params)


def load_itens_contagem(id_contagem: int) -> pd.DataFrame:
    sql = """
        SELECT
            pr.cod_barras,
            pr.nome_produto,
            ci.quantidade_sistema,
            ci.quantidade_fisica,
            (ci.quantidade_fisica - ci.quantidade_sistema) AS diferenca
        FROM contagem_estoque_item ci
        LEFT JOIN produto pr ON pr.id_produto = ci.id_produto
        WHERE ci.id_contagem = :cid
        ORDER BY ABS(ci.quantidade_fisica - ci.quantidade_sistema) DESC
    """
    return _query(sql, {"cid": id_contagem})


def get_opcoes_filtros() -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        status = pd.read_sql(
            text("SELECT DISTINCT status FROM pedido WHERE status IS NOT NULL ORDER BY status"),
            conn,
        )["status"].tolist()

        tipos = pd.read_sql(
            text("SELECT DISTINCT tipo_pedido FROM pedido WHERE tipo_pedido IS NOT NULL ORDER BY tipo_pedido"),
            conn,
        )["tipo_pedido"].tolist()

        vendedores = pd.read_sql(
            text(f"""
                WITH {_VENDEDOR_CTE}
                SELECT DISTINCT p.id_vendedor, vm.nome_vendedor
                FROM pedido p
                LEFT JOIN vendedor_map vm ON vm.id_vendedor = p.id_vendedor
                WHERE p.id_vendedor IS NOT NULL
                ORDER BY vm.nome_vendedor
            """),
            conn,
        )

    return {"status": status, "tipos": tipos, "vendedores": vendedores}


# ══════════════════════════════════════════════════════════════════════════════
# CONSULTAS — pages/Dashboard_Vendas.py
# Todas aceitam data_ini/data_fim opcionais (None = histórico completo)
# e excluem pedidos cancelados.
# ══════════════════════════════════════════════════════════════════════════════

def load_vendas_por_rota(data_ini=None, data_fim=None) -> pd.DataFrame:
    """Faturamento, pedidos e ticket por rota (apenas PRE-VENDA válidos)."""
    clauses = [_FILTRO_VALIDO, "p.tipo_pedido = 'PRE-VENDA'", "p.id_rota IS NOT NULL"]
    params = {}
    _clausula_periodo(clauses, params, data_ini, data_fim)
    where = " AND ".join(clauses)

    sql = f"""
        SELECT r.nome_rota AS rota,
               COUNT(DISTINCT DATE_TRUNC('week', p.data)) AS semanas,
               COUNT(p.id) AS pedidos,
               ROUND(SUM(p.valor_total)::numeric, 2) AS fat_total,
               ROUND(COUNT(p.id)::numeric /
                     NULLIF(COUNT(DISTINCT DATE_TRUNC('week', p.data)), 0), 1) AS ped_sem,
               ROUND(SUM(p.valor_total) /
                     NULLIF(COUNT(DISTINCT DATE_TRUNC('week', p.data))::numeric, 0), 2) AS fat_sem,
               ROUND(AVG(p.valor_total)::numeric, 2) AS ticket
        FROM pedido p
        JOIN rotas r ON r.id_rota = p.id_rota
        WHERE {where}
        GROUP BY r.nome_rota
        HAVING COUNT(p.id) > 0
        ORDER BY fat_sem DESC
    """
    return _query(sql, params)


def load_tendencia_semanal(data_ini=None, data_fim=None) -> pd.DataFrame:
    """Pedidos e faturamento PRE-VENDA agrupados por semana."""
    clauses = [_FILTRO_VALIDO, "p.tipo_pedido = 'PRE-VENDA'"]
    params = {}
    _clausula_periodo(clauses, params, data_ini, data_fim)
    where = " AND ".join(clauses)

    sql = f"""
        SELECT DATE_TRUNC('week', p.data)::date AS semana,
               COUNT(p.id) AS pedidos,
               ROUND(SUM(p.valor_total)::numeric, 2) AS faturamento
        FROM pedido p
        WHERE {where}
        GROUP BY semana
        ORDER BY semana
    """
    return _query(sql, params)


def load_vendas_faixa_etaria(data_ini=None, data_fim=None) -> pd.DataFrame:
    """Clientes, pedidos, ticket e faturamento por faixa etária (PRE-VENDA válidos)."""
    clauses = [
        _FILTRO_VALIDO,
        "p.tipo_pedido = 'PRE-VENDA'",
        "c.data_nascimento IS NOT NULL",
        "c.deleted_at IS NULL",
    ]
    params = {}
    _clausula_periodo(clauses, params, data_ini, data_fim)
    where = " AND ".join(clauses)

    sql = f"""
        SELECT
            CASE
                WHEN DATE_PART('year', AGE(c.data_nascimento)) < 18 THEN 'Menor 18'
                WHEN DATE_PART('year', AGE(c.data_nascimento)) BETWEEN 18 AND 25 THEN '18-25'
                WHEN DATE_PART('year', AGE(c.data_nascimento)) BETWEEN 26 AND 35 THEN '26-35'
                WHEN DATE_PART('year', AGE(c.data_nascimento)) BETWEEN 36 AND 45 THEN '36-45'
                WHEN DATE_PART('year', AGE(c.data_nascimento)) BETWEEN 46 AND 60 THEN '46-60'
                ELSE '+60'
            END AS faixa,
            COUNT(DISTINCT c.id_cliente) AS clientes,
            COUNT(p.id) AS pedidos,
            ROUND(AVG(p.valor_total)::numeric, 2) AS ticket,
            ROUND(SUM(p.valor_total)::numeric, 2) AS faturamento
        FROM clientes c
        JOIN pedido p ON p.id_cliente = c.id_cliente
        WHERE {where}
        GROUP BY faixa
        ORDER BY MIN(DATE_PART('year', AGE(c.data_nascimento)))
    """
    return _query(sql, params)


def load_vendas_vendedor_estado(data_ini=None, data_fim=None) -> pd.DataFrame:
    """Faturamento por vendedor × estado (deduzido pelo CEP do cliente)."""
    clauses = [
        _FILTRO_VALIDO,
        "p.tipo_pedido = 'PRE-VENDA'",
        "c.deleted_at IS NULL",
        "c.cep_cliente IS NOT NULL",
        "c.cep_cliente != ''",
        r"c.cep_cliente ~ '^\d'",
    ]
    params = {}
    _clausula_periodo(clauses, params, data_ini, data_fim)
    where = " AND ".join(clauses)

    sql = r"""
        SELECT v.nome_vendedor AS vendedor,
               CASE
                   WHEN c.cep_cliente ~ '^\d{5}'
                        AND CAST(LEFT(c.cep_cliente, 5) AS BIGINT) BETWEEN 66000 AND 68999 THEN 'PA'
                   WHEN c.cep_cliente ~ '^\d{5}'
                        AND CAST(LEFT(c.cep_cliente, 5) AS BIGINT) BETWEEN 78000 AND 78999 THEN 'MT'
                   WHEN c.cep_cliente ~ '^\d{5}'
                        AND CAST(LEFT(c.cep_cliente, 5) AS BIGINT) BETWEEN 74000 AND 76999 THEN 'GO'
                   ELSE 'Outro'
               END AS estado,
               COUNT(DISTINCT c.id_cliente) AS clientes,
               COUNT(p.id) AS pedidos,
               ROUND(AVG(p.valor_total)::numeric, 2) AS ticket,
               ROUND(SUM(p.valor_total)::numeric, 2) AS faturamento
        FROM clientes c
        JOIN vendedor v ON v.id_vendedor = c.id_geral_vendedor
        JOIN pedido p ON p.id_cliente = c.id_cliente
        WHERE __WHERE__
        GROUP BY v.nome_vendedor, estado
        ORDER BY faturamento DESC
    """.replace("__WHERE__", where)
    return _query(sql, params)


def load_produtos_por_tipo(tipo_pedido: str = "PRE-VENDA", data_ini=None, data_fim=None) -> pd.DataFrame:
    """Ranking de produtos por faturamento para um tipo de pedido (PRE-VENDA, BRINDE etc.)."""
    clauses = [_FILTRO_VALIDO, "p.tipo_pedido = :tipo_pedido"]
    params = {"tipo_pedido": tipo_pedido}
    _clausula_periodo(clauses, params, data_ini, data_fim)
    where = " AND ".join(clauses)

    sql = f"""
        SELECT pr.nome_produto AS produto,
               SUM(pi.quantidade) AS qtd,
               COUNT(DISTINCT p.id) AS pedidos,
               ROUND(AVG(pi.valor_unitario)::numeric, 2) AS preco,
               ROUND(SUM(pi.valor_total)::numeric, 2) AS faturamento
        FROM pedido p
        JOIN pedido_itens pi ON pi.id_pedido = p.id
        JOIN produto pr ON pr.id_produto = pi.id_produto
        WHERE {where}
        GROUP BY pr.nome_produto
        ORDER BY faturamento DESC
    """
    return _query(sql, params)
