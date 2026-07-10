# encoding: utf-8
"""Consignado × Venda — venda efetiva por tipo (exclusivo do admin).

Fonte: tabela `venda` do app_sgv (mesma do sistema de vendas).
Regra validada em 10/07/2026 com o Jeferson:
  - venda efetiva = registros com status FORA de ('RESTANTE', 'CANCELADA')
    (o "restante" do consignado volta como linha status='RESTANTE')
  - data_venda é texto DD/MM/AAAA → convertida com to_date
  - tipos: CONSIGNADO, VENDA DIRETA, PRE VENDA
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

st.set_page_config(page_title="Consignado × Venda", page_icon="🤝", layout="wide")

from datetime import date

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
        <div style="font-size:21px;font-weight:800;color:#F2F6FC">Consignado × Venda — venda efetiva</div>
        <div style="font-size:12px;color:#6B7385">Tabela <b>venda</b> · exclui status RESTANTE e CANCELADA · consignado já líquido do que voltou</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

_REGRA = ("v.status NOT IN ('RESTANTE', 'CANCELADA') "
          "AND v.data_venda ~ '^\\d{2}/\\d{2}/\\d{4}$'")

hoje = date.today()
c1, c2 = st.columns(2)
with c1:
    data_ini = st.date_input("De", value=date(hoje.year, 1, 1), key="cv_ini")
with c2:
    data_fim = st.date_input("Até", value=hoje, key="cv_fim")


@st.cache_data(ttl=300, show_spinner="Consultando as vendas...")
def carregar(d1, d2):
    return _query(f"""
        SELECT v.tipo,
               DATE_TRUNC('month', to_date(v.data_venda, 'DD/MM/YYYY'))::date AS mes,
               COALESCE(r.nome_rota, 'SEM ROTA') AS rota,
               COUNT(*)                              AS vendas,
               ROUND(SUM(v.valor_venda)::numeric, 2) AS valor
        FROM venda v
        LEFT JOIN rotas r ON r.id_rota = v.id_rota
        WHERE {_REGRA}
          AND to_date(v.data_venda, 'DD/MM/YYYY') >= :d1
          AND to_date(v.data_venda, 'DD/MM/YYYY') <= :d2
          AND v.tipo IS NOT NULL
        GROUP BY v.tipo, mes, rota
    """, {"d1": d1, "d2": d2})


try:
    df = carregar(data_ini, data_fim)
except Exception as e:
    st.error(f"Erro ao consultar o banco: {e}")
    st.stop()

if df.empty:
    st.info("Nenhuma venda no período.")
    st.stop()

# ── KPIs ──────────────────────────────────────────────────────────────────────
por_tipo = df.groupby("tipo", as_index=False).agg(vendas=("vendas", "sum"), valor=("valor", "sum"))
total = float(por_tipo["valor"].sum())
consig = float(por_tipo.loc[por_tipo["tipo"] == "CONSIGNADO", "valor"].sum())
outras = total - consig
pct_total = 100 * consig / total if total else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("🤝 Consignado (efetivo)", f"R$ {consig:,.0f}")
k2.metric("🛒 Demais vendas", f"R$ {outras:,.0f}")
k3.metric("Consignado no total", f"{pct_total:.1f}%")
k4.metric("Consignado ÷ demais", f"{(100 * consig / outras):.0f}%" if outras else "—")

st.divider()

# ── Resumo por tipo ───────────────────────────────────────────────────────────
st.subheader("💰 Resumo por tipo")
res = por_tipo.copy()
res["ticket_medio"] = (res["valor"] / res["vendas"]).round(2)
res["pct_do_total"] = (100 * res["valor"] / total).round(1) if total else 0
st.dataframe(res.sort_values("valor", ascending=False),
             use_container_width=True, hide_index=True)

col_a, col_b = st.columns(2)

# ── Mês a mês ─────────────────────────────────────────────────────────────────
with col_a:
    st.subheader("📅 Mês a mês")
    piv = (df.pivot_table(index="mes", columns="tipo", values="valor", aggfunc="sum")
             .round(2).fillna(0))
    piv["TOTAL"] = piv.sum(axis=1).round(2)
    if "CONSIGNADO" in piv.columns:
        piv["% consig"] = (100 * piv["CONSIGNADO"] / piv["TOTAL"].replace(0, pd.NA)).round(1)
    st.dataframe(piv.reset_index(), use_container_width=True, hide_index=True)
    if "% consig" in piv.columns:
        st.line_chart(piv["% consig"])

# ── Por rota ──────────────────────────────────────────────────────────────────
with col_b:
    st.subheader("🚚 Por rota")
    piv_r = (df.pivot_table(index="rota", columns="tipo", values="valor", aggfunc="sum")
               .round(2).fillna(0))
    piv_r["TOTAL"] = piv_r.sum(axis=1).round(2)
    if "CONSIGNADO" in piv_r.columns:
        piv_r["% consig"] = (100 * piv_r["CONSIGNADO"] / piv_r["TOTAL"].replace(0, pd.NA)).round(1)
    st.dataframe(piv_r.sort_values("TOTAL", ascending=False).reset_index(),
                 use_container_width=True, hide_index=True)

st.caption("Venda efetiva: registros de venda excluindo status RESTANTE (retorno do consignado) "
           "e CANCELADA. Fonte: tabela venda · atualização a cada 5 min.")
