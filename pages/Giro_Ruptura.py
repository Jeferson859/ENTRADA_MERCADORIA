# encoding: utf-8
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import load_empresas, load_giro_estoque, load_colunas, load_idade_estoque

st.set_page_config(page_title="Giro & Ruptura", page_icon="📦", layout="wide")


LEAD_TIME_DIAS = 15  # prazo médio de reposição

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""<style>
.block-container{padding-top:2.4rem;padding-bottom:.5rem;max-width:100%}
.kpi-card{
  background:linear-gradient(135deg,rgba(123,97,255,.13) 0%,rgba(0,212,255,.07) 100%);
  border:1px solid rgba(123,97,255,.35);border-radius:14px;
  padding:1rem 1.3rem;display:flex;justify-content:space-between;
  align-items:flex-end;min-height:90px;margin-bottom:.5rem;
  transition:border-color .2s;
}
.kpi-card:hover{border-color:rgba(0,212,255,.6)}
.kpi-label{font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;
  color:#8B92A5;margin-bottom:.3rem}
.kpi-value{font-size:1.85rem;font-weight:800;color:#fff;
  letter-spacing:-.02em;line-height:1}
.kpi-sub{font-size:.7rem;color:#8B92A5;margin-top:.2rem}
.stTabs [data-baseweb="tab-list"]{gap:5px;background:rgba(255,255,255,.04);
  padding:5px;border-radius:12px;margin-bottom:.5rem}
.stTabs [data-baseweb="tab"]{padding:7px 20px;border-radius:8px;
  font-size:.82rem;font-weight:500;letter-spacing:.02em}
h3{font-size:.8rem!important;text-transform:uppercase;letter-spacing:.09em;
  color:#8B92A5!important;margin:.1rem 0 .5rem 0!important;
  padding-bottom:.35rem;border-bottom:1px solid rgba(123,97,255,.28)}
hr{border-color:rgba(123,97,255,.15)!important;margin:.6rem 0!important}
</style>""", unsafe_allow_html=True)

PURPLE = "#7B61FF"; CYAN = "#00D4FF"; GREEN = "#00FF94"
AMBER = "#FFB800"; RED = "#FF6B6B"
PL = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#C4C9D4", size=11, family="Inter,sans-serif"),
    margin=dict(l=0,r=4,t=30,b=0),
)
COR_CLASSE = {'A': GREEN, 'B': AMBER, 'C': '#8B92A5'}

def kpi(col, label, value, color=CYAN, sub=None):
    sub_h = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    with col:
        st.markdown(
            f'<div class="kpi-card">'
            f'<div><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value" style="color:{color}">{value}</div>{sub_h}</div>'
            f'</div>',
            unsafe_allow_html=True)

# ── DADOS ─────────────────────────────────────────────────────────────────────


# ── Giro & Ruptura: dados consolidados ──
from db_giro_ruptura import (
    load_giro_ruptura,
    kpis_giro_ruptura,
    runway_ruptura,
    classe_a_em_risco,
)


@st.cache_data(ttl=120, show_spinner=False)
def fetch_empresas_gr():
    return load_empresas()


@st.cache_data(ttl=120, show_spinner="Calculando giro e ruptura...")
def fetch_giro_ruptura(dias, lead, id_emp):
    return load_giro_ruptura(dias=dias, lead_time=lead, id_empresa=id_emp)


STT_COR = {
    "Risco ruptura": "#f59e0b",
    "Sem estoque": "#ef4444",
    "Parado": "#9ca3af",
    "Excesso": "#3b82f6",
    "Saudável": "#22c55e",
}

hc1, hc2 = st.columns([8, 1])
hc1.markdown(
    '<div style="display:flex;align-items:center;gap:.6rem;margin:.2rem 0 .4rem">'
    '<span style="font-size:1.9rem">📦</span><div>'
    '<div style="font-size:1.7rem;font-weight:800;color:#fff;line-height:1.1">Estoque — Giro &amp; Ruptura</div>'
    '<div style="color:#8892A5;font-size:.8rem">Cobertura, curva ABC e tempo parado · '
    'saídas PRE-VENDA + BRINDE + REPOSIÇÃO · cache 2 min</div></div></div>',
    unsafe_allow_html=True,
)
with hc2:
    if st.button("🔄 Recarregar"):
        st.cache_data.clear()
        st.rerun()

empresas = fetch_empresas_gr()
fc1, fc2, fc3, fc4 = st.columns([2, 1.5, 1.5, 2])
emp = fc1.selectbox("EMPRESA", empresas["nome_empresa"])
id_emp = int(empresas.loc[empresas["nome_empresa"] == emp, "id_empresa"].iloc[0])
dias = fc2.radio("JANELA DE SAÍDA", [30, 60, 90], horizontal=True)
lead = fc3.slider("PRAZO DE REPOSIÇÃO (dias)", 5, 45, 15, step=5)
busca = fc4.text_input("BUSCAR PRODUTO", "", placeholder="Nome do produto...")

df = fetch_giro_ruptura(dias, lead, id_emp)
dfv = df[df["produto"].str.contains(busca, case=False, na=False)] if busca else df


def _chip(label, n, cor):
    return (
        '<span style="display:inline-flex;align-items:center;gap:6px;background:#1b2233;'
        'border:1px solid #2a3650;border-radius:20px;padding:4px 12px;margin:0 6px 6px 0;'
        f'font-size:.8rem;color:#cdd6e5"><span style="width:8px;height:8px;border-radius:50%;'
        f'background:{cor}"></span>{label} <b style="color:#fff">{n}</b></span>'
    )


chips = '<div style="margin:.3rem 0 .7rem"><span style="color:#8892A5;font-size:.72rem;letter-spacing:.08em;margin-right:4px">STATUS</span>'
for s, c in STT_COR.items():
    chips += _chip(s, int((df["status"] == s).sum()), c)
chips += '<span style="color:#8892A5;font-size:.72rem;letter-spacing:.08em;margin:0 4px 0 14px">CLASSE</span>'
for cl in ["A", "B", "C"]:
    chips += _chip(f"Classe {cl}", int((df["classe"] == cl).sum()), "#8892A5")
chips += "</div>"
st.markdown(chips, unsafe_allow_html=True)

k = kpis_giro_ruptura(df)
kc = st.columns(5)
kpi(kc[0], "RISCO DE RUPTURA", str(k["risco_ruptura"]), color=RED, sub=f"rompem em ≤ {lead}d")
kpi(kc[1], "SEM ESTOQUE", str(k["sem_estoque"]), color=AMBER, sub="vendendo com saldo zerado")
kpi(kc[2], "GIRO GERAL", f'{k["giro_geral"]}x', color=CYAN, sub=f"saída ÷ estoque · {dias}d")
kpi(kc[3], "COBERTURA MEDIANA", f'{k["cobertura_mediana"]}d', color=CYAN, sub="dias de estoque restante")
kpi(kc[4], "CLASSE A EM RISCO", str(k["classe_a_risco"]), color=AMBER, sub="alto giro rompendo")

st.write("")
tab1, tab2, tab3 = st.tabs(["📊 Giro & Cobertura", "🔢 Curva ABC", "⏰ Tempo Parado"])

with tab1:
    cL, cR = st.columns(2)
    with cL:
        st.markdown("##### ⏱️ RUNWAY DE RUPTURA")
        st.caption(f"Produtos que rompem primeiro · linha = prazo de reposição ({lead}d)")
        zer = int((df["status"] == "Sem estoque").sum())
        if zer:
            st.error(f"{zer} produto(s) já zeraram e seguem vendendo — comprar primeiro.")
        rw = runway_ruptura(dfv)
        st.dataframe(
            rw[["produto", "estoque", "saida_periodo", "cobertura_dias", "status"]],
            use_container_width=True, hide_index=True,
        )
    with cR:
        st.markdown("##### 🎯 MATRIZ GIRO × COBERTURA")
        st.caption("Cada bolha = um produto · tamanho = estoque · cor = status")
        mtx = dfv.dropna(subset=["cobertura_dias"])
        fig = go.Figure()
        for s, c in STT_COR.items():
            g = mtx[mtx["status"] == s]
            if len(g):
                fig.add_trace(go.Scatter(
                    x=g["media_dia"], y=g["cobertura_dias"], mode="markers", name=s,
                    marker=dict(size=(g["estoque"] ** 0.5).clip(7, 38), color=c, line=dict(width=0), opacity=0.85),
                    text=g["produto"],
                    hovertemplate="%{text}<br>demanda %{x}/dia<br>cobertura %{y}d<extra></extra>",
                ))
        fig.add_hline(y=lead, line_dash="dot", line_color="#ef4444")
        fig.update_layout(
            template="plotly_dark", height=430, showlegend=True,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="Demanda (un/dia)", yaxis_title="Cobertura (dias)",
            legend=dict(orientation="h", y=-0.2), margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown("##### 🔢 CURVA ABC")
    abc = (
        df.groupby("classe")
          .agg(produtos=("produto", "count"), saida=("saida_periodo", "sum"))
          .reindex(["A", "B", "C"]).fillna(0).reset_index()
    )
    cc = st.columns(3)
    cores_abc = [GREEN, AMBER, RED]
    for i in range(len(abc)):
        row = abc.iloc[i]
        kpi(cc[i], f"CLASSE {row['classe']}", str(int(row["produtos"])),
            color=cores_abc[i], sub=f"{int(row['saida'])} un. de saída")
    fig2 = go.Figure(go.Bar(x=abc["classe"], y=abc["saida"], marker_color=cores_abc))
    fig2.update_layout(template="plotly_dark", height=300, paper_bgcolor="rgba(0,0,0,0)",
                       plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=20, b=10),
                       yaxis_title="Saída no período")
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown("###### 🚨 Classe A em risco")
    st.dataframe(
        classe_a_em_risco(dfv)[["produto", "estoque", "cobertura_dias", "status"]],
        use_container_width=True, hide_index=True,
    )

with tab3:
    st.markdown("##### ⏰ TEMPO PARADO")
    try:
        idade = load_idade_estoque(id_emp)
        st.dataframe(idade, use_container_width=True, hide_index=True)
    except Exception as exc:
        st.info(f"Tempo parado indisponível: {exc}")
