# encoding: utf-8
"""Consignado × Venda — percentuais por período e vendedor (exclusivo do admin)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

st.set_page_config(page_title="Consignado × Venda", page_icon="🤝", layout="wide")

import pandas as pd

import auth
import nav
from db import _query

auth.exigir_admin()
nav.render("Consignado")

st.markdown(
    """
    <div style="display:flex;align-items:center;gap:14px;margin:.1rem 0 1rem">
      <div style="width:46px;height:46px;border-radius:13px;background:linear-gradient(150deg,#2E7CF6,#00D4FF);display:flex;align-items:center;justify-content:center;font-size:23px">🤝</div>
      <div>
        <div style="font-size:21px;font-weight:800;color:#F2F6FC">Consignado × Venda</div>
        <div style="font-size:12px;color:#6B7385">Participação do consignado sobre a venda · pedidos válidos (não cancelados)</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

_FILTRO = "p.cancelado_em IS NULL AND p.status <> 'CANCELADO'"


@st.cache_data(ttl=120, show_spinner="Carregando tipos...")
def carregar_tipos():
    return _query(f"""
        SELECT p.tipo_pedido,
               COUNT(*)                            AS pedidos,
               ROUND(SUM(p.valor_total)::numeric, 2) AS valor
        FROM pedido p
        WHERE {_FILTRO} AND p.tipo_pedido IS NOT NULL
        GROUP BY p.tipo_pedido
        ORDER BY valor DESC
    """)


try:
    df_tipos = carregar_tipos()
except Exception as e:
    st.error(f"Erro ao consultar o banco: {e}")
    st.stop()

tipos = df_tipos["tipo_pedido"].tolist()
if not tipos:
    st.info("Nenhum pedido válido encontrado.")
    st.stop()


def _default(lista, alvo, evitar=None):
    for i, t in enumerate(lista):
        if alvo.upper() in str(t).upper() and t != evitar:
            return i
    return 0


c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
with c1:
    tipo_consig = st.selectbox("Tipo consignado", tipos, index=_default(tipos, "CONSIG"))
with c2:
    tipo_venda = st.selectbox("Tipo venda", tipos, index=_default(tipos, "PRE-VENDA", evitar=tipo_consig))
with c3:
    data_ini = st.date_input("De", value=None, key="cv_ini")
with c4:
    data_fim = st.date_input("Até", value=None, key="cv_fim")

if tipo_consig == tipo_venda:
    st.warning("Escolha tipos diferentes para comparar.")
    st.stop()

per = ""
params = {"tc": tipo_consig, "tv": tipo_venda}
if data_ini:
    per += " AND p.data >= :d1"
    params["d1"] = data_ini
if data_fim:
    per += " AND p.data < :d2 + INTERVAL '1 day'"
    params["d2"] = data_fim


@st.cache_data(ttl=120, show_spinner="Calculando percentuais...")
def carregar(per, params):
    geral = _query(f"""
        SELECT
            COALESCE(SUM(p.valor_total) FILTER (WHERE p.tipo_pedido = :tc), 0) AS consignado,
            COALESCE(SUM(p.valor_total) FILTER (WHERE p.tipo_pedido = :tv), 0) AS venda,
            COUNT(*) FILTER (WHERE p.tipo_pedido = :tc) AS ped_consig,
            COUNT(*) FILTER (WHERE p.tipo_pedido = :tv) AS ped_venda
        FROM pedido p
        WHERE {_FILTRO}{per}
    """, params)
    mensal = _query(f"""
        SELECT DATE_TRUNC('month', p.data)::date AS mes,
               COALESCE(SUM(p.valor_total) FILTER (WHERE p.tipo_pedido = :tc), 0) AS consignado,
               COALESCE(SUM(p.valor_total) FILTER (WHERE p.tipo_pedido = :tv), 0) AS venda
        FROM pedido p
        WHERE {_FILTRO}{per} AND p.tipo_pedido IN (:tc, :tv)
        GROUP BY mes ORDER BY mes
    """, params)
    vendedor = _query(f"""
        SELECT COALESCE(v.nome_vendedor, 'SEM VENDEDOR') AS vendedor,
               COALESCE(SUM(p.valor_total) FILTER (WHERE p.tipo_pedido = :tc), 0) AS consignado,
               COALESCE(SUM(p.valor_total) FILTER (WHERE p.tipo_pedido = :tv), 0) AS venda
        FROM pedido p
        LEFT JOIN vendedor v ON v.id_vendedor = p.id_vendedor
        WHERE {_FILTRO}{per} AND p.tipo_pedido IN (:tc, :tv)
        GROUP BY 1 ORDER BY consignado DESC
    """, params)
    return geral, mensal, vendedor


try:
    geral, mensal, vendedor = carregar(per, params)
except Exception as e:
    st.error(f"Erro ao consultar o banco: {e}")
    st.stop()

g = geral.iloc[0]
consig, venda = float(g["consignado"]), float(g["venda"])
total = consig + venda
pct_sobre_venda = (100 * consig / venda) if venda else None
pct_do_total = (100 * consig / total) if total else None

k1, k2, k3, k4 = st.columns(4)
k1.metric(f"💰 {tipo_venda}", f"R$ {venda:,.2f}", f"{int(g['ped_venda'])} pedidos")
k2.metric(f"🤝 {tipo_consig}", f"R$ {consig:,.2f}", f"{int(g['ped_consig'])} pedidos")
k3.metric("Consignado ÷ Venda", f"{pct_sobre_venda:.1f}%" if pct_sobre_venda is not None else "—")
k4.metric("Consignado no total", f"{pct_do_total:.1f}%" if pct_do_total is not None else "—")

st.divider()

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("📅 Mês a mês")
    if mensal.empty:
        st.info("Sem dados no período.")
    else:
        m = mensal.copy()
        m["% consig/venda"] = (100 * m["consignado"] / m["venda"].replace(0, pd.NA)).round(1)
        st.dataframe(m, use_container_width=True, hide_index=True)
        st.line_chart(m.set_index("mes")["% consig/venda"])

with col_b:
    st.subheader("🧑‍💼 Por vendedor")
    if vendedor.empty:
        st.info("Sem dados no período.")
    else:
        vd = vendedor.copy()
        vd["% consig/venda"] = (100 * vd["consignado"] / vd["venda"].replace(0, pd.NA)).round(1)
        st.dataframe(vd, use_container_width=True, hide_index=True)

st.caption("Percentuais sobre o valor dos pedidos. Cancelados ficam fora. "
           "Sem filtro de data = histórico completo.")

with st.expander("📋 Todos os tipos de pedido (referência)"):
    st.dataframe(df_tipos, use_container_width=True, hide_index=True)
