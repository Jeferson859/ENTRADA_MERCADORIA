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


def get_engine():
    host     = _get_secret("DB_HOST", "localhost")
    port     = _get_secret("DB_PORT", "5432")
    name     = _get_secret("DB_NAME")
    user     = _get_secret("DB_USER")
    password = _get_secret("DB_PASSWORD")

    if not all([name, user, password]):
        raise ValueError("Credenciais incompletas. Verifique o arquivo .env ou os Secrets do Streamlit Cloud.")

    url = f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{name}"
    return create_engine(url)


def load_pedidos(data_ini=None, data_fim=None, status=None, tipo_pedido=None, id_vendedor=None) -> pd.DataFrame:
    engine = get_engine()
    clauses = ["1=1"]
    params = {}

    if data_ini:
        clauses.append("p.data >= :data_ini")
        params["data_ini"] = data_ini
    if data_fim:
        clauses.append("p.data <= :data_fim")
        params["data_fim"] = data_fim
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

    sql = text(f"""
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
    """)

    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params=params)


def buscar_pedido_por_id(pedido_id: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    engine = get_engine()

    sql_pedido = text(f"""
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
    """)

    sql_itens = text("""
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
    """)

    with engine.connect() as conn:
        df_pedido = pd.read_sql(sql_pedido, conn, params={"pid": pedido_id})
        df_itens  = pd.read_sql(sql_itens,  conn, params={"pid": pedido_id})

    return df_pedido, df_itens


def buscar_pedidos_por_produto(cod_barras: str) -> pd.DataFrame:
    engine = get_engine()
    sql = text(f"""
        WITH {_VENDEDOR_CTE}
        SELECT
            p.id            AS id_pedido,
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
            pi.valor_total   AS valor_item
        FROM pedido_itens pi
        JOIN pedido p   ON p.id = pi.id_pedido
        JOIN produto pr ON pr.id_produto = pi.id_produto
        LEFT JOIN vendedor_map vm ON vm.id_vendedor = p.id_vendedor
        WHERE pr.cod_barras ILIKE :cod
        ORDER BY p.data DESC
    """)
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params={"cod": f"%{cod_barras}%"})


def buscar_ids_por_produto(termo: str) -> list[int]:
    engine = get_engine()
    sql = text("""
        SELECT DISTINCT pi.id_pedido
        FROM pedido_itens pi
        JOIN produto pr ON pr.id_produto = pi.id_produto
        WHERE pr.nome_produto ILIKE :termo
           OR pr.cod_barras   ILIKE :termo
    """)
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn, params={"termo": f"%{termo}%"})
    return df["id_pedido"].tolist()


def load_contagens(data_ini=None, data_fim=None, status=None) -> pd.DataFrame:
    engine = get_engine()
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

    sql = text(f"""
        SELECT
            c.id,
            c.data,
            c.status,
            c.obs,
            u.name          AS criado_por,
            COUNT(ci.id)    AS total_itens,
            COUNT(ci.id) FILTER (WHERE ci.quantidade_fisica <> ci.quantidade_sistema) AS itens_divergentes,
            SUM(ci.quantidade_fisica - ci.quantidade_sistema) AS saldo_ajuste
        FROM contagem_estoque c
        LEFT JOIN users u ON u.id = c.created_by
        LEFT JOIN contagem_estoque_item ci ON ci.id_contagem = c.id
        WHERE {where}
        GROUP BY c.id, c.data, c.status, c.obs, u.name
        ORDER BY c.data DESC
    """)

    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params=params)


def load_itens_contagem(id_contagem: int) -> pd.DataFrame:
    engine = get_engine()
    sql = text("""
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
    """)
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params={"cid": id_contagem})


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
