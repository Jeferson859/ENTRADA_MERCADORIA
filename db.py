import os
from urllib.parse import quote_plus
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()


def get_engine():
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    if not all([name, user, password]):
        raise ValueError("Credenciais incompletas. Verifique o arquivo .env.")

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
        SELECT
            p.id,
            p.data,
            p.tipo_pedido,
            p.status,
            p.valor_total,
            p.id_cliente,
            f.nome_completo  AS vendedor,
            p.id_rota,
            p.obs,
            p.created_at,
            p.cancelado_em
        FROM pedido p
        LEFT JOIN funcionario f ON f.id = p.id_vendedor
        WHERE {where}
        ORDER BY p.data DESC
    """)

    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params=params)


def buscar_pedido_por_id(pedido_id: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    engine = get_engine()

    sql_pedido = text("""
        SELECT
            p.id,
            p.data,
            p.tipo_pedido,
            p.status,
            p.valor_total,
            p.id_cliente,
            f.nome_completo  AS vendedor,
            p.id_rota,
            p.obs,
            p.created_at,
            p.updated_at,
            p.cancelado_em
        FROM pedido p
        LEFT JOIN funcionario f ON f.id = p.id_vendedor
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
    sql = text("""
        SELECT
            p.id,
            p.data,
            p.tipo_pedido,
            p.status,
            p.valor_total,
            p.id_cliente,
            f.nome_completo  AS vendedor,
            pr.cod_barras,
            pr.nome_produto,
            pi.quantidade,
            pi.valor_unitario,
            pi.valor_total   AS valor_item
        FROM pedido_itens pi
        JOIN pedido p  ON p.id = pi.id_pedido
        JOIN produto pr ON pr.id_produto = pi.id_produto
        LEFT JOIN funcionario f ON f.id = p.id_vendedor
        WHERE pr.cod_barras ILIKE :cod
        ORDER BY p.data DESC
    """)
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params={"cod": f"%{cod_barras}%"})


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
            text("""
                SELECT DISTINCT p.id_vendedor, f.nome_completo
                FROM pedido p
                LEFT JOIN funcionario f ON f.id = p.id_vendedor
                WHERE p.id_vendedor IS NOT NULL
                ORDER BY f.nome_completo
            """),
            conn,
        )

    return {"status": status, "tipos": tipos, "vendedores": vendedores}
