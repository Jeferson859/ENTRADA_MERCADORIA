# encoding: utf-8
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

import db
import auth
from db_giro_ruptura import (
    load_giro_ruptura,
    kpis_giro_ruptura,
    runway_ruptura,
    classe_a_em_risco,
)

st.set_page_config(page_title="Giro & Ruptura", page_icon="📊", layout="wide")
auth.protect()

CORES = {
    "Sem estoque": "#ef4444",
    "Risco ruptura": "#f59e0b",
    "Parado": "#9ca3af",
    "Excesso": "#3b82f6",
    "Saudável": "#22c55e",
}


@st.cache_data(ttl=120, show_spinner="Consultando o banco...")
def carregar(dias, lead, id_emp):
    return load_giro_ruptura(dias=dias, lead_time=lead, id_empresa=id_emp)


topo = st.columns([6, 1])
topo[0].title("Estoque · Giro & Ruptura")
if topo[1].button("🔄 Atualizar"):
    st.cache_data.clear()
    st.rerun()

empresas = db.load_empresas()
f1, f2, f3 = st.columns([2, 1, 1])
emp = f1.selectbox("Empresa", empresas["nome_empresa"])
id_emp = int(empresas.loc[empresas["nome_empresa"] == emp, "id_empresa"].iloc[0])
dias = f2.radio("Janela de saída", [30, 60, 90], horizontal=True)
lead = f3.slider("Prazo de reposição (dias)", 5, 45, 15, step=5)

df = carregar(dias, lead, id_emp)
k = kpis_giro_ruptura(df)

m = st.columns(5)
m[0].metric("Risco de ruptura", k["risco_ruptura"])
m[1].metric("Sem estoque", k["sem_estoque"])
m[2].metric("Giro geral", f'{k["giro_geral"]}x')
m[3].metric("Cobertura mediana", f'{k["cobertura_mediana"]}d')
m[4].metric("Classe A em risco", k["classe_a_risco"])

b1, b2, b3 = st.columns([2, 1, 1])
busca = b1.text_input("Buscar produto", "")
status_sel = b2.multiselect("Status", sorted(df["status"].dropna().unique()))
classe_sel = b3.multiselect("Classe", ["A", "B", "C"])

dfv = df.copy()
if busca:
    dfv = dfv[dfv["produto"].str.contains(busca, case=False, na=False)]
if status_sel:
    dfv = dfv[dfv["status"].isin(status_sel)]
if classe_sel:
    dfv = dfv[dfv["classe"].isin(classe_sel)]

st.subheader("Matriz Giro × Cobertura")
mtx = dfv.dropna(subset=["cobertura_dias"])
fig = go.Figure()
for stt, grp in mtx.groupby("status"):
    fig.add_trace(go.Scatter(
        x=grp["media_dia"],
        y=grp["cobertura_dias"],
        mode="markers",
        name=stt,
        marker=dict(
            size=(grp["estoque"] ** 0.5).clip(6, 40),
            color=CORES.get(stt, "#888888"),
            line=dict(width=0),
        ),
        text=grp["produto"],
        hovertemplate="%{text}<br>saída/dia=%{x}<br>cobertura=%{y}d<extra></extra>",
    ))
fig.update_layout(
    xaxis_title="Saída média/dia",
    yaxis_title="Cobertura (dias)",
    height=430,
    template="plotly_dark",
    legend=dict(orientation="h"),
    margin=dict(l=10, r=10, t=10, b=10),
)
st.plotly_chart(fig, use_container_width=True)

c1, c2 = st.columns(2)
with c1:
    st.subheader("Runway de ruptura")
    st.dataframe(
        runway_ruptura(dfv)[["produto", "estoque", "saida_periodo", "cobertura_dias", "status"]],
        use_container_width=True, hide_index=True,
    )
with c2:
    st.subheader("Classe A em risco")
    st.dataframe(
        classe_a_em_risco(dfv)[["produto", "estoque", "cobertura_dias", "status"]],
        use_container_width=True, hide_index=True,
    )

st.subheader("Visão completa")
st.dataframe(dfv, use_container_width=True, hide_index=True)
