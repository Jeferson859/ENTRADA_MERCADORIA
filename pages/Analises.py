# encoding: utf-8
"""Análises (rascunho) — valores de venda por tipo de pedido (exclusivo do admin).

Página de exploração: diagnóstico do valor (cabeçalho × itens) e visões de
valor por tipo, mês e vendedor. Sem abertura por produto.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

st.set_page_config(page_title="Análises", page_icon="🔎", layout="wide")

import pandas as pd

import auth
import nav
from db import _query

auth.exigir_admin()
nav.render("Analises")

st.markdown(
    """
    <div style="display:flex;align-items:center;gap:14px;margin:.1rem 0 1rem">
      <div style="width:46px;height:46px;border-radius:13px;background:linear-gradient(150deg,#2E7CF6,#00D4FF);display:flex;align-items:center;justify-content:center;font-size:23px">🔎</div>
      <div>
        <div style="font-size:21px;font-weight:800;color:#F2F6FC">Análises — valores por tipo de pedido</div>
        <div style="font-size:12px;color:#6B7385">Consignado · Brinde · Venda direta · pedidos válidos (não cancelados) · direto de pedido/pedido_itens</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2 = st.columns(2)
with c1:
    data_ini = st.date_input("De", value=None, key="an_ini")
with c2:
    data_fim = st.date_input("Até", value=None, key="an_fim")

per = ""
params = {}
if data_ini:
    per += " AND p.data >= :d1"
    params["d1"] = data_ini
if data_fim:
    per += " AND p.data < :d2 + INTERVAL '1 day'"
    params["d2"] = data_fim


@st.cache_data(ttl=120, show_spinner="Consultando o banco...")
def carregar(per, params):
    return _query(f"""
        SELECT p.tipo_pedido,
               DATE_TRUNC('month', p.data)::date          AS mes,
               COALESCE(v.nome_vendedor, 'SEM VENDEDOR')  AS vendedor,
               COUNT(*)                                   AS pedidos,
               ROUND(SUM(p.valor_total)::numeric, 2)      AS valor_cabecalho,
               ROUND(SUM(it.valor_itens)::numeric, 2)     AS valor_itens
        FROM pedido p
        LEFT JOIN vendedor v ON v.id_vendedor = p.id_vendedor
        LEFT JOIN (
            SELECT id_pedido,
                   SUM(valor_total) FILTER (WHERE COALESCE(status, 'ATIVO') = 'ATIVO') AS valor_itens
            FROM pedido_itens
            GROUP BY id_pedido
        ) it ON it.id_pedido = p.id
        WHERE p.cancelado_em IS NULL AND p.status <> 'CANCELADO'
          AND p.tipo_pedido IS NOT NULL{per}
        GROUP BY p.tipo_pedido, mes, vendedor
    """, params)


try:
    df = carregar(per, params)
except Exception as e:
    st.error(f"Erro ao consultar o banco: {e}")
    st.stop()

if df.empty:
    st.info("Nenhum pedido válido no período.")
    st.stop()

fonte = st.radio(
    "Fonte do valor de venda",
    ["Cabeçalho do pedido (valor_total)", "Soma dos itens ativos"],
    horizontal=True,
    help="Se algum tipo vier zerado numa fonte, compare com a outra na tabela de diagnóstico abaixo.",
)
col_valor = "valor_cabecalho" if fonte.startswith("Cabeçalho") else "valor_itens"

# ── 1) Diagnóstico: cabeçalho × itens por tipo ────────────────────────────────
st.subheader("🩺 Diagnóstico — onde está o valor de cada tipo")
diag = (df.groupby("tipo_pedido", as_index=False)
          .agg(pedidos=("pedidos", "sum"),
               valor_cabecalho=("valor_cabecalho", "sum"),
               valor_itens=("valor_itens", "sum"))
          .sort_values("valor_cabecalho", ascending=False))
diag["diferenca"] = (diag["valor_cabecalho"].fillna(0) - diag["valor_itens"].fillna(0)).round(2)
st.dataframe(diag, use_container_width=True, hide_index=True)
st.caption("Se 'valor_cabecalho' vier vazio/zerado para um tipo, o valor de venda dele está nos itens (use a outra fonte acima).")

st.divider()

# ── 2) Resumo por tipo ────────────────────────────────────────────────────────
st.subheader("💰 Resumo por tipo (valor de venda)")
res = (df.groupby("tipo_pedido", as_index=False)
         .agg(pedidos=("pedidos", "sum"), valor=(col_valor, "sum")))
total = res["valor"].sum()
res["ticket_medio"] = (res["valor"] / res["pedidos"]).round(2)
res["pct_do_total"] = (100 * res["valor"] / total).round(1) if total else 0
res = res.sort_values("valor", ascending=False)
st.dataframe(res, use_container_width=True, hide_index=True)

# ── 3) Mês a mês (tipos lado a lado) ─────────────────────────────────────────
st.subheader("📅 Mês a mês — valores lado a lado")
piv_mes = (df.pivot_table(index="mes", columns="tipo_pedido",
                          values=col_valor, aggfunc="sum")
             .round(2).fillna(0))
piv_mes["TOTAL"] = piv_mes.sum(axis=1).round(2)
st.dataframe(piv_mes.reset_index(), use_container_width=True, hide_index=True)
st.line_chart(piv_mes.drop(columns=["TOTAL"]))

# ── 4) Por vendedor (tipos lado a lado) ──────────────────────────────────────
st.subheader("🧑‍💼 Por vendedor — valores lado a lado")
piv_vend = (df.pivot_table(index="vendedor", columns="tipo_pedido",
                           values=col_valor, aggfunc="sum")
              .round(2).fillna(0))
piv_vend["TOTAL"] = piv_vend.sum(axis=1).round(2)
st.dataframe(piv_vend.sort_values("TOTAL", ascending=False).reset_index(),
             use_container_width=True, hide_index=True)

st.caption("Página de exploração — quando fecharmos as análises, elas viram uma página definitiva com visual completo.")
