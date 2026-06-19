# encoding: utf-8
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from db import load_empresas, load_idade_estoque
from db_giro_ruptura import (
    load_giro_ruptura,
    kpis_giro_ruptura,
    runway_ruptura,
    classe_a_em_risco,
)

st.set_page_config(page_title="Giro & Ruptura", page_icon="📦", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
    .stApp { background: radial-gradient(1200px 600px at 80% -10%, rgba(46,124,246,.10), transparent 60%), #070B12; }
    html, body, [class*="css"] { font-family:'Inter',system-ui,sans-serif; color:#D7DEEA; }
    .block-container { padding-top:1.4rem; max-width:1440px; }
    div[data-baseweb="select"] > div, .stTextInput input { background:#0E1422 !important; border:1px solid rgba(59,169,255,.2) !important; color:#E4EAF3 !important; border-radius:10px !important; }
    .stTextInput input::placeholder { color:#4A5365; }
    .stRadio [role="radiogroup"] { gap:4px; background:#0E1422; border:1px solid rgba(59,169,255,.2); padding:4px; border-radius:11px; }
    .stTabs [data-baseweb="tab-list"] { gap:5px; background:rgba(255,255,255,.03); padding:5px; border-radius:12px; }
    .stTabs [data-baseweb="tab"] { border-radius:9px; padding:6px 16px; color:#9AA3B4; }
    .stTabs [aria-selected="true"] { background:linear-gradient(150deg,#2E7CF6,#00D4FF); color:#fff !important; }
    .stDataFrame { border:1px solid rgba(59,169,255,.16); border-radius:12px; }
    .stSelectbox label, .stRadio label, .stSlider label, .stTextInput label { color:#6B7385 !important; font-size:10.5px !important; text-transform:uppercase; letter-spacing:.09em; font-weight:600 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

STATUS_STYLE = {
    "Sem estoque":   ("#FF5C6C", "rgba(255,92,108,.12)", "rgba(255,92,108,.3)"),
    "Risco ruptura": ("#FF8A4C", "rgba(255,138,76,.12)", "rgba(255,138,76,.3)"),
    "Parado":        ("#8B92A5", "rgba(139,146,165,.12)", "rgba(139,146,165,.3)"),
    "Excesso":       ("#FFC53D", "rgba(255,197,61,.12)", "rgba(255,197,61,.3)"),
    "Saudável":      ("#00E0A1", "rgba(0,224,161,.12)", "rgba(0,224,161,.3)"),
}
CLASSE_COR = {"A": "#00E0A1", "B": "#FFC53D", "C": "#7B8499"}
CLASSE_BG = {"A": "rgba(0,224,161,.14)", "B": "rgba(255,197,61,.14)", "C": "rgba(123,132,153,.14)"}


@st.cache_data(ttl=120, show_spinner=False)
def _empresas():
    return load_empresas()


@st.cache_data(ttl=120, show_spinner="Calculando giro e ruptura...")
def _data(dias, lead, id_emp):
    return load_giro_ruptura(dias=dias, lead_time=lead, id_empresa=id_emp)


hcol, bcol = st.columns([8, 1.3])
hcol.markdown(
    """
    <div style="display:flex;align-items:center;gap:14px;margin:.1rem 0">
      <div style="width:46px;height:46px;border-radius:13px;background:linear-gradient(150deg,#2E7CF6,#00D4FF);display:flex;align-items:center;justify-content:center;font-size:23px;box-shadow:0 6px 20px rgba(46,124,246,.35)">📦</div>
      <div>
        <div style="font-size:21px;font-weight:800;letter-spacing:-.02em;color:#F2F6FC">Estoque — Giro &amp; Ruptura</div>
        <div style="font-size:12px;color:#6B7385;font-weight:500;margin-top:2px">Cobertura, curva ABC e tempo parado · saídas PRE-VENDA + BRINDE + REPOSIÇÃO · cache 2 min</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
with bcol:
    st.write("")
    if st.button("↻ Recarregar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

empresas = _empresas()
f1, f2, f3, f4 = st.columns([2, 1.5, 1.5, 2])
emp = f1.selectbox("🏢 Empresa", empresas["nome_empresa"])
id_emp = int(empresas.loc[empresas["nome_empresa"] == emp, "id_empresa"].iloc[0])
dias = f2.radio("Janela de saída", [30, 60, 90], horizontal=True)
lead = f3.slider("Prazo de reposição (dias)", 5, 45, 15, step=5)
busca = f4.text_input("Buscar produto", "", placeholder="Nome do produto...")

df = _data(dias, lead, id_emp)
dfv = df[df["produto"].str.contains(busca, case=False, na=False)] if busca else df

chips = '<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:4px 0 16px">'
chips += '<span style="font-size:10.5px;text-transform:uppercase;letter-spacing:.09em;color:#5A6275;font-weight:600;margin-right:2px">Status</span>'
for s, (fg, bg, brd) in STATUS_STYLE.items():
    n = int((df["status"] == s).sum())
    chips += ('<span style="display:inline-flex;align-items:center;gap:6px;border:1px solid ' + brd + ';background:' + bg + ';color:' + fg +
              ';font-size:12px;font-weight:600;padding:6px 11px;border-radius:20px"><span style="width:7px;height:7px;border-radius:50%;background:' + fg + '"></span>' + s +
              ' <span style="opacity:.6">' + str(n) + '</span></span>')
chips += '<span style="width:1px;height:18px;background:rgba(255,255,255,.1);margin:0 4px"></span>'
chips += '<span style="font-size:10.5px;text-transform:uppercase;letter-spacing:.09em;color:#5A6275;font-weight:600;margin-right:2px">Classe</span>'
for cl in ["A", "B", "C"]:
    n = int((df["classe"] == cl).sum())
    chips += ('<span style="display:inline-flex;align-items:center;gap:6px;border:1px solid rgba(255,255,255,.12);background:' + CLASSE_BG[cl] +
              ';color:' + CLASSE_COR[cl] + ';font-size:12px;font-weight:700;padding:6px 12px;border-radius:20px">Classe ' + cl +
              ' <span style="opacity:.6;font-weight:600">' + str(n) + '</span></span>')
chips += '</div>'
st.markdown(chips, unsafe_allow_html=True)

k = kpis_giro_ruptura(df)
KPIS = [
    ("Risco de ruptura", str(k["risco_ruptura"]), "#FF8A4C", "rompem em <= " + str(lead) + "d"),
    ("Sem estoque", str(k["sem_estoque"]), "#FF5C6C", "vendendo com saldo zerado"),
    ("Giro geral", str(k["giro_geral"]) + "x", "#00D4FF", "saída / estoque · " + str(dias) + "d"),
    ("Cobertura mediana", str(k["cobertura_mediana"]) + "d", "#3BA9FF", "dias de estoque restante"),
    ("Classe A em risco", str(k["classe_a_risco"]), "#FFC53D", "alto giro rompendo"),
]
cards = '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:16px">'
for label, val, cor, sub in KPIS:
    cards += ('<div style="position:relative;overflow:hidden;background:linear-gradient(155deg,rgba(59,169,255,.09),rgba(0,212,255,.025));'
              'border:1px solid rgba(59,169,255,.16);border-radius:14px;padding:15px 16px;min-height:104px;display:flex;flex-direction:column;justify-content:space-between">'
              '<div style="position:absolute;top:0;left:0;right:0;height:3px;background:' + cor + '"></div>'
              '<div style="font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;color:#7B8499;font-weight:600;line-height:1.3">' + label + '</div>'
              '<div><div style="font-size:29px;font-weight:800;letter-spacing:-.02em;line-height:1;color:' + cor + ';font-variant-numeric:tabular-nums">' + val + '</div>'
              '<div style="font-size:10.5px;color:#5E6678;margin-top:5px">' + sub + '</div></div></div>')
cards += '</div>'
st.markdown(cards, unsafe_allow_html=True)

SECT = 'background:rgba(255,255,255,.025);border:1px solid rgba(59,169,255,.16);border-radius:16px;padding:18px 20px'
TITLE = 'font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#9CC6FF;font-weight:700'

tab1, tab2, tab3 = st.tabs(["📊 Giro & Cobertura", "🔢 Curva ABC", "⏰ Tempo Parado"])

with tab1:
    cL, cR = st.columns([1, 1.25])
    rw = runway_ruptura(dfv)
    scale = max(lead * 3, 1)
    zer = int((df["status"] == "Sem estoque").sum())
    html = '<div style="' + SECT + '"><div style="' + TITLE + '">⏳ Runway de ruptura</div>'
    html += '<div style="font-size:11px;color:#5E6678;margin:3px 0 14px">Os produtos que rompem primeiro · linha tracejada = prazo de reposição (' + str(lead) + 'd)</div>'
    if zer:
        html += ('<div style="background:rgba(255,92,108,.1);border:1px solid rgba(255,92,108,.3);border-radius:9px;padding:8px 11px;font-size:11.5px;color:#FF8A99;margin-bottom:13px"><b style="color:#FF5C6C">' + str(zer) + '</b> produto(s) já zeraram e seguem vendendo — comprar primeiro.</div>')
    html += '<div style="display:flex;flex-direction:column;gap:9px">'
    for _, r in rw.iterrows():
        cob = float(r["cobertura_dias"]) if pd.notna(r["cobertura_dias"]) else 0.0
        w = min(cob / scale * 100, 100)
        fg = STATUS_STYLE.get(r["status"], ("#8B92A5", "", ""))[0]
        nome = str(r["produto"])
        short = (nome[:24] + "…") if len(nome) > 24 else nome
        ws = ("%.1f" % w)
        html += ('<div style="display:grid;grid-template-columns:135px 1fr;gap:11px;align-items:center">'
                 '<div style="font-size:11.5px;color:#AEB6C6;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="' + nome + '">' + short + '</div>'
                 '<div style="position:relative;height:22px;background:rgba(255,255,255,.04);border-radius:7px">'
                 '<div style="position:absolute;left:0;top:0;bottom:0;width:' + ws + '%;background:' + fg + ';border-radius:7px;min-width:3px"></div>'
                 '<div style="position:absolute;left:33.33%;top:0;bottom:0;border-left:1.5px dashed rgba(255,92,108,.65)"></div>'
                 '<div style="position:absolute;left:calc(' + ws + '% + 7px);top:50%;transform:translateY(-50%);font-size:10.5px;font-weight:700;color:#C4CCDA">' + ("%.0f" % cob) + 'd</div>'
                 '</div></div>')
    html += '</div></div>'
    cL.markdown(html, unsafe_allow_html=True)
    with cR:
        st.markdown('<div style="' + TITLE + ';margin-bottom:2px">🎯 Matriz Giro × Cobertura</div><div style="font-size:11px;color:#5E6678;margin-bottom:4px">Cada bolha = um produto · tamanho = estoque · cor = status</div>', unsafe_allow_html=True)
        mtx = dfv.dropna(subset=["cobertura_dias"]).copy()
        mtx["cob_plot"] = mtx["cobertura_dias"].clip(upper=120)
        fig = go.Figure()
        for s, (fg, bg, brd) in STATUS_STYLE.items():
            g = mtx[mtx["status"] == s]
            if len(g):
                fig.add_trace(go.Scatter(x=g["cob_plot"], y=g["media_dia"], mode="markers", name=s,
                    marker=dict(size=(g["estoque"] ** 0.5).clip(7, 36), color=fg, line=dict(width=0), opacity=0.8),
                    text=g["produto"], hovertemplate="%{text}<br>cobertura %{x}d · demanda %{y}/dia<extra></extra>"))
        fig.add_vrect(x0=0, x1=lead, fillcolor="rgba(255,92,108,.12)", line_width=0)
        fig.add_vline(x=lead, line_dash="dash", line_color="rgba(255,92,108,.6)")
        fig.add_vline(x=90, line_dash="dash", line_color="rgba(255,197,61,.4)")
        fig.update_layout(template="plotly_dark", height=360, showlegend=True,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(title="Cobertura (dias)", range=[0, 122]), yaxis=dict(title="Demanda (un/dia)"),
            legend=dict(orientation="h", y=-0.25), margin=dict(l=10, r=10, t=6, b=6))
        st.plotly_chart(fig, use_container_width=True)
    st.markdown('<div style="' + TITLE + ';margin:8px 0 8px">Visão completa · ' + str(emp) + ' — ' + str(len(dfv)) + ' de ' + str(len(df)) + ' produtos</div>', unsafe_allow_html=True)
    st.dataframe(dfv[["produto", "classe", "estoque", "saida_periodo", "media_dia", "giro", "cobertura_dias", "status"]],
        use_container_width=True, hide_index=True, height=360,
        column_config={"produto": "Produto", "classe": "ABC", "estoque": "Estoque", "saida_periodo": "Saída",
            "media_dia": "Méd/dia", "giro": "Giro", "cobertura_dias": "Cobertura (d)", "status": "Status"})

with tab2:
    st.markdown('<div style="' + TITLE + ';margin-bottom:10px">🔢 Curva ABC</div>', unsafe_allow_html=True)
    abc = (df.groupby("classe").agg(produtos=("produto", "count"), saida=("saida_periodo", "sum")).reindex(["A", "B", "C"]).fillna(0).reset_index())
    cc = st.columns(3)
    for i in range(len(abc)):
        row = abc.iloc[i]
        cl = row["classe"]
        cc[i].markdown('<div style="background:linear-gradient(155deg,rgba(59,169,255,.09),rgba(0,212,255,.025));border:1px solid rgba(59,169,255,.16);border-top:3px solid ' + CLASSE_COR[cl] + ';border-radius:14px;padding:15px 16px">'
            '<div style="font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;color:#7B8499;font-weight:600">Classe ' + cl + '</div>'
            '<div style="font-size:29px;font-weight:800;color:' + CLASSE_COR[cl] + '">' + str(int(row["produtos"])) + '</div>'
            '<div style="font-size:10.5px;color:#5E6678">' + str(int(row["saida"])) + ' un. de saída</div></div>', unsafe_allow_html=True)
    st.write("")
    fig2 = go.Figure(go.Bar(x=abc["classe"], y=abc["saida"], marker_color=[CLASSE_COR[c] for c in abc["classe"]]))
    fig2.update_layout(template="plotly_dark", height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=20, b=10), yaxis_title="Saída no período")
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown('<div style="' + TITLE + ';margin:6px 0 8px">🚨 Classe A em risco</div>', unsafe_allow_html=True)
    st.dataframe(classe_a_em_risco(dfv)[["produto", "estoque", "cobertura_dias", "status"]], use_container_width=True, hide_index=True)

with tab3:
    st.markdown('<div style="' + TITLE + ';margin-bottom:10px">⏰ Tempo Parado</div>', unsafe_allow_html=True)
    try:
        idade = load_idade_estoque(id_emp)
        st.dataframe(idade, use_container_width=True, hide_index=True)
    except Exception as exc:
        st.info("Tempo parado indisponível: " + str(exc))
