import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Dashboard de Vendas", page_icon="📊", layout="wide")

@st.cache_resource
def get_conn():
    return psycopg2.connect(
        host=st.secrets["DB_HOST"],
        port=st.secrets["DB_PORT"],
        dbname=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
    )

@st.cache_data(ttl=600)
def query(sql):
    conn = get_conn()
    return pd.read_sql(sql, conn)

def fmt_brl(v):
    return f"R$ {v:,.0f}".replace(",", ".")

st.title("📊 Dashboard de Vendas — SGV")
st.caption(f"Atualizado em: {datetime.now().strftime('%d/%m/%Y %H:%M')} · Somente pedidos PRE-VENDA válidos")

tabs = st.tabs([
    "🛣️ Rotas",
    "👥 Faixa Etária",
    "🧑‍💼 Vendedor × Estado",
    "🎁 Produtos BRINDE",
    "🛒 Produtos PRE-VENDA",
])

with tabs[0]:
    st.subheader("Média Semanal por Rota — PRE-VENDA")
    df_rotas = query("""
        SELECT
            r.nome_rota AS rota,
            COUNT(DISTINCT DATE_TRUNC('week', p.data)) AS semanas_ativas,
            COUNT(p.id) AS total_pedidos,
            ROUND(SUM(p.valor_total)::numeric, 2) AS faturamento_total,
            ROUND((COUNT(p.id)::numeric / COUNT(DISTINCT DATE_TRUNC('week', p.data))), 1) AS media_pedidos_semana,
            ROUND((SUM(p.valor_total) / COUNT(DISTINCT DATE_TRUNC('week', p.data)))::numeric, 2) AS media_faturamento_semana,
            ROUND(AVG(p.valor_total)::numeric, 2) AS ticket_medio
        FROM pedido p
        JOIN rotas r ON r.id_rota = p.id_rota
        WHERE p.cancelado_em IS NULL
            AND p.status != 'CANCELADO'
            AND p.tipo_pedido = 'PRE-VENDA'
            AND p.id_rota IS NOT NULL
        GROUP BY r.nome_rota
        HAVING COUNT(p.id) > 0
        ORDER BY media_faturamento_semana DESC
    """)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Rotas", len(df_rotas))
    col2.metric("Faturamento Total", fmt_brl(df_rotas['faturamento_total'].sum()))
    col3.metric("Ticket Médio Geral", fmt_brl(df_rotas['ticket_medio'].mean()))
    st.divider()
    col_a, col_b = st.columns([3, 2])
    with col_a:
        fig = px.bar(df_rotas.head(20), x="media_faturamento_semana", y="rota", orientation="h",
                     title="Top 20 Rotas — Fat. Médio/Semana (R$)",
                     labels={"media_faturamento_semana": "R$/semana", "rota": ""},
                     color="media_faturamento_semana", color_continuous_scale="Blues")
        fig.update_layout(height=550, showlegend=False, coloraxis_showscale=False)
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        st.dataframe(
            df_rotas[["rota","media_pedidos_semana","media_faturamento_semana","ticket_medio","semanas_ativas"]].rename(columns={
                "rota": "Rota", "media_pedidos_semana": "Pedidos/sem",
                "media_faturamento_semana": "Fat./sem (R$)", "ticket_medio": "Ticket Médio", "semanas_ativas": "Semanas",
            }), use_container_width=True, height=550)

with tabs[1]:
    st.subheader("Faixa Etária × Ticket Médio — PRE-VENDA")
    df_idade = query("""
        SELECT
            CASE
                WHEN DATE_PART('year', AGE(c.data_nascimento)) < 18 THEN 'Menor de 18'
                WHEN DATE_PART('year', AGE(c.data_nascimento)) BETWEEN 18 AND 25 THEN '18-25'
                WHEN DATE_PART('year', AGE(c.data_nascimento)) BETWEEN 26 AND 35 THEN '26-35'
                WHEN DATE_PART('year', AGE(c.data_nascimento)) BETWEEN 36 AND 45 THEN '36-45'
                WHEN DATE_PART('year', AGE(c.data_nascimento)) BETWEEN 46 AND 60 THEN '46-60'
                ELSE 'Acima de 60'
            END AS faixa_etaria,
            COUNT(DISTINCT c.id_cliente) AS total_clientes,
            COUNT(p.id) AS total_pedidos,
            ROUND(AVG(p.valor_total)::numeric, 2) AS ticket_medio,
            ROUND(SUM(p.valor_total)::numeric, 2) AS faturamento_total
        FROM clientes c
        JOIN pedido p ON p.id_cliente = c.id_cliente
        WHERE c.data_nascimento IS NOT NULL
            AND p.tipo_pedido = 'PRE-VENDA'
            AND p.cancelado_em IS NULL
            AND p.status != 'CANCELADO'
            AND c.deleted_at IS NULL
        GROUP BY faixa_etaria
        ORDER BY MIN(DATE_PART('year', AGE(c.data_nascimento)))
    """)
    ordem = ['Menor de 18', '18-25', '26-35', '36-45', '46-60', 'Acima de 60']
    df_idade['faixa_etaria'] = pd.Categorical(df_idade['faixa_etaria'], categories=ordem, ordered=True)
    df_idade = df_idade.sort_values('faixa_etaria')
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(df_idade, x="faixa_etaria", y="ticket_medio",
                     title="Ticket Médio por Faixa Etária (R$)",
                     labels={"faixa_etaria": "Faixa Etária", "ticket_medio": "Ticket Médio (R$)"},
                     color="ticket_medio", color_continuous_scale="Greens")
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.bar(df_idade, x="faixa_etaria", y="total_clientes",
                      title="Nº de Clientes por Faixa Etária",
                      labels={"faixa_etaria": "Faixa Etária", "total_clientes": "Clientes"},
                      color="total_clientes", color_continuous_scale="Blues")
        fig2.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)
    st.dataframe(df_idade.rename(columns={
        "faixa_etaria": "Faixa Etária", "total_clientes": "Clientes",
        "total_pedidos": "Pedidos", "ticket_medio": "Ticket Médio (R$)", "faturamento_total": "Faturamento (R$)",
    }), use_container_width=True, hide_index=True)

with tabs[2]:
    st.subheader("Vendedor × Estado × Faixa Etária")
    df_vend = query("""
        SELECT
            v.nome_vendedor AS vendedor,
            CASE
                WHEN CAST(LEFT(c.cep_cliente, 2) AS INT) BETWEEN 66 AND 68 THEN 'PA'
                WHEN CAST(LEFT(c.cep_cliente, 2) AS INT) = 78 THEN 'MT'
                WHEN CAST(LEFT(c.cep_cliente, 2) AS INT) BETWEEN 74 AND 76 THEN 'GO'
                ELSE 'Outro'
            END AS estado,
            CASE
                WHEN DATE_PART('year', AGE(c.data_nascimento)) < 18 THEN 'Menor de 18'
                WHEN DATE_PART('year', AGE(c.data_nascimento)) BETWEEN 18 AND 25 THEN '18-25'
                WHEN DATE_PART('year', AGE(c.data_nascimento)) BETWEEN 26 AND 35 THEN '26-35'
                WHEN DATE_PART('year', AGE(c.data_nascimento)) BETWEEN 36 AND 45 THEN '36-45'
                WHEN DATE_PART('year', AGE(c.data_nascimento)) BETWEEN 46 AND 60 THEN '46-60'
                ELSE 'Acima de 60'
            END AS faixa_etaria,
            COUNT(DISTINCT c.id_cliente) AS total_clientes,
            COUNT(p.id) AS total_pedidos,
            ROUND(AVG(p.valor_total)::numeric, 2) AS ticket_medio
        FROM clientes c
        JOIN vendedor v ON v.id_vendedor = c.id_geral_vendedor
        JOIN pedido p ON p.id_cliente = c.id_cliente
        WHERE p.cancelado_em IS NULL
            AND p.status != 'CANCELADO'
            AND p.tipo_pedido = 'PRE-VENDA'
            AND c.deleted_at IS NULL
            AND c.data_nascimento IS NOT NULL
            AND c.cep_cliente IS NOT NULL AND c.cep_cliente != '' AND c.cep_cliente ~ '^\d'
        GROUP BY v.nome_vendedor, estado, faixa_etaria
        ORDER BY v.nome_vendedor, estado, ticket_medio DESC
    """)
    vendedores = sorted(df_vend['vendedor'].unique())
    sel_vend = st.multiselect("Filtrar por vendedor", vendedores, default=vendedores[:5] if len(vendedores) >= 5 else vendedores)
    df_f = df_vend[df_vend['vendedor'].isin(sel_vend)] if sel_vend else df_vend
    fig = px.bar(
        df_f.groupby(['vendedor', 'estado'])['ticket_medio'].mean().reset_index(),
        x="vendedor", y="ticket_medio", color="estado", barmode="group",
        title="Ticket Médio por Vendedor e Estado",
        labels={"ticket_medio": "Ticket Médio (R$)", "vendedor": "Vendedor"},
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_f.rename(columns={
        "vendedor": "Vendedor", "estado": "Estado", "faixa_etaria": "Faixa Etária",
        "total_clientes": "Clientes", "total_pedidos": "Pedidos", "ticket_medio": "Ticket Médio (R$)"
    }), use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("Produtos distribuídos como BRINDE")
    df_brinde = query("""
        SELECT
            pr.nome_produto AS produto,
            SUM(pi.quantidade) AS qtd_total,
            COUNT(DISTINCT p.id) AS pedidos,
            ROUND(AVG(pi.valor_unitario)::numeric, 2) AS preco_medio,
            ROUND(SUM(pi.valor_total)::numeric, 2) AS faturamento_total
        FROM pedido p
        JOIN pedido_itens pi ON pi.id_pedido = p.id
        JOIN produto pr ON pr.id_produto = pi.id_produto
        WHERE p.tipo_pedido = 'BRINDE'
            AND p.cancelado_em IS NULL
            AND p.status != 'CANCELADO'
        GROUP BY pr.nome_produto
        ORDER BY faturamento_total DESC
    """)
    col1, col2, col3 = st.columns(3)
    col1.metric("Produtos distintos", len(df_brinde))
    col2.metric("Unidades doadas", f"{int(df_brinde['qtd_total'].sum()):,}".replace(",", "."))
    col3.metric("Valor total", fmt_brl(df_brinde['faturamento_total'].sum()))
    st.divider()
    col_a, col_b = st.columns([2, 3])
    with col_a:
        fig = px.bar(df_brinde.head(15), x="faturamento_total", y="produto", orientation="h",
                     title="Top 15 Brindes — Valor Total (R$)",
                     labels={"faturamento_total": "Valor (R$)", "produto": ""},
                     color="faturamento_total", color_continuous_scale="Oranges")
        fig.update_layout(height=500, showlegend=False, coloraxis_showscale=False)
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        st.dataframe(df_brinde.rename(columns={
            "produto": "Produto", "qtd_total": "Qtd", "pedidos": "Pedidos",
            "preco_medio": "Preço Médio (R$)", "faturamento_total": "Valor Total (R$)"
        }), use_container_width=True, height=500, hide_index=True)

with tabs[4]:
    st.subheader("Produtos vendidos — PRE-VENDA")
    df_pv = query("""
        SELECT
            pr.nome_produto AS produto,
            SUM(pi.quantidade) AS qtd_total,
            COUNT(DISTINCT p.id) AS pedidos,
            ROUND(AVG(pi.valor_unitario)::numeric, 2) AS preco_medio,
            ROUND(SUM(pi.valor_total)::numeric, 2) AS faturamento_total
        FROM pedido p
        JOIN pedido_itens pi ON pi.id_pedido = p.id
        JOIN produto pr ON pr.id_produto = pi.id_produto
        WHERE p.tipo_pedido = 'PRE-VENDA'
            AND p.cancelado_em IS NULL
            AND p.status != 'CANCELADO'
        GROUP BY pr.nome_produto
        ORDER BY faturamento_total DESC
    """)
    col1, col2, col3 = st.columns(3)
    col1.metric("Produtos distintos", len(df_pv))
    col2.metric("Unidades vendidas", f"{int(df_pv['qtd_total'].sum()):,}".replace(",", "."))
    col3.metric("Faturamento total", fmt_brl(df_pv['faturamento_total'].sum()))
    st.divider()
    busca = st.text_input("🔍 Buscar produto", "")
    df_show = df_pv[df_pv['produto'].str.contains(busca, case=False, na=False)] if busca else df_pv
    col_a, col_b = st.columns([2, 3])
    with col_a:
        fig = px.bar(df_show.head(15), x="faturamento_total", y="produto", orientation="h",
                     title="Top 15 Produtos — Faturamento (R$)",
                     labels={"faturamento_total": "R$", "produto": ""},
                     color="faturamento_total", color_continuous_scale="Greens")
        fig.update_layout(height=500, showlegend=False, coloraxis_showscale=False)
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        st.dataframe(df_show.rename(columns={
            "produto": "Produto", "qtd_total": "Qtd", "pedidos": "Pedidos",
            "preco_medio": "Preço Médio (R$)", "faturamento_total": "Faturamento (R$)"
        }), use_container_width=True, height=500, hide_index=True)
