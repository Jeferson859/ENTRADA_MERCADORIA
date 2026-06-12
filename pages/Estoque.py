# encoding: utf-8
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from db import load_empresas, load_giro_estoque

st.set_page_config(page_title="Estoque", page_icon="📦", layout="wide")

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
@st.cache_data(ttl=600, show_spinner=False)
def fetch_empresas():
    return load_empresas()

@st.cache_data(ttl=600, show_spinner="Calculando giro de estoque...")
def fetch_giro(dias, id_empresa):
    return load_giro_estoque(dias, id_empresa)

try:
    empresas = fetch_empresas()
except Exception as e:
    st.error(f"Não foi possível carregar as empresas: {e}")
    st.stop()

if empresas.empty:
    st.warning("Nenhuma empresa cadastrada na tabela `empresa`.")
    st.stop()

# ── HEADER + FILTROS ─────────────────────────────────────────────────────────
st.markdown(
    f'## 📦 Estoque — Giro e Cobertura&nbsp;&nbsp;'
    f'<span style="font-size:.75rem;color:#8B92A5;font-weight:400">'
    f'Atualizado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}'
    f' · saídas: PRE-VENDA + BRINDE + REPOSICAO · cache 10 min</span>',
    unsafe_allow_html=True)

fc0, fc1, fc2, fc3 = st.columns([3, 2, 2, 3])
with fc0:
    emp_nome = st.selectbox(
        "🏢 Empresa",
        empresas.nome_empresa.tolist(), key="est_empresa")
    emp_id = int(empresas.loc[empresas.nome_empresa == emp_nome, 'id_empresa'].iloc[0])
with fc1:
    janela = st.radio("Janela de saída", [30, 60, 90], horizontal=True,
                      format_func=lambda d: f"{d} dias", key="est_janela")
with fc2:
    lead = st.slider("Prazo de reposição (dias)", 5, 45, LEAD_TIME_DIAS, 5,
                     key="est_lead")
with fc3:
    busca = st.text_input("🔍 Buscar produto", "", key="est_busca",
                          placeholder="Digite parte do nome...")

ge = fetch_giro(janela, emp_id)

def status_giro(r):
    if r.saida_periodo > 0 and r.estoque <= 0:
        return "🔴 Sem estoque"
    if r.saida_periodo == 0:
        return "🟡 Parado"
    if pd.notna(r.cobertura_dias) and r.cobertura_dias <= lead:
        return "🔴 Risco ruptura"
    if pd.notna(r.cobertura_dias) and r.cobertura_dias > 90:
        return "🟠 Excesso"
    return "🟢 Saudável"

ge = ge.copy()
ge['status'] = ge.apply(status_giro, axis=1)

sem_estoque = (ge.status == "🔴 Sem estoque").sum()
risco = (ge.status == "🔴 Risco ruptura").sum()
parados = (ge.status == "🟡 Parado").sum()
com_venda = ge[ge.saida_periodo > 0]
giro_geral = (com_venda.saida_periodo.sum() / com_venda.estoque.sum()) \
             if com_venda.estoque.sum() > 0 else 0

c1, c2, c3, c4 = st.columns(4)
kpi(c1, "Sem Estoque", str(sem_estoque), RED, "vendendo com saldo zerado")
kpi(c2, "Repor Urgente", str(risco), AMBER, f"cobertura entre 1 e {lead} dias")
kpi(c3, "Produtos Parados", str(parados), PURPLE, f"sem saída em {janela} dias")
kpi(c4, "Giro Geral", f"{giro_geral:.2f}x", GREEN, f"saída ÷ estoque em {janela} dias")
st.markdown("---")

gef = ge[ge.produto.str.contains(busca, case=False, na=False)] if busca else ge

ca, cb = st.columns([2, 3])
with ca:
    st.markdown(f"### ⏳ Repor Urgente — cobertura de 1 a {lead*2} dias")
    st.caption("Produtos com saldo zerado não entram aqui — estão no KPI 'Sem Estoque' e na tabela ao lado.")
    crit = gef[(gef.saida_periodo > 0) & (gef.estoque > 0)
               & (gef.cobertura_dias <= lead * 2)] \
            .nsmallest(15, 'cobertura_dias')
    if len(crit):
        fgi = go.Figure(go.Bar(
            x=crit.cobertura_dias, y=crit.produto, orientation='h',
            marker=dict(color=crit.cobertura_dias,
                        colorscale=[[0, RED], [.6, AMBER], [1, '#30363D']],
                        showscale=False, line=dict(width=0)),
            text=crit.cobertura_dias.apply(lambda v: f"{v:.0f}d"),
            textposition='outside',
            textfont=dict(size=9, color='#8B92A5')))
        fgi.add_vline(x=lead, line_dash="dash", line_color=RED,
                      annotation_text=f"reposição ({lead}d)",
                      annotation_font_size=9)
        fgi.update_traces(cliponaxis=False)
        fgi.update_layout(**PL, height=max(360, 30*len(crit)))
        fgi.update_layout(margin=dict(l=0, r=40, t=30, b=0))
        fgi.update_yaxes(autorange='reversed', tickfont=dict(size=9))
        fgi.update_xaxes(tickfont=dict(size=9),
                         gridcolor='rgba(255,255,255,.05)')
        st.plotly_chart(fgi, use_container_width=True)
    else:
        st.info("Nenhum produto com cobertura crítica nessa empresa. 👍")
with cb:
    st.markdown(f"### Visão Completa — {emp_nome}")
    sel_status = st.multiselect(
        "Filtrar por status (vazio = todos)",
        sorted(ge.status.unique().tolist()), key="est_status")
    gtab = gef[gef.status.isin(sel_status)] if sel_status else gef
    gtab = gtab.sort_values(['estoque', 'saida_periodo'],
                            ascending=[True, False])
    st.dataframe(
        gtab[['produto','estoque','saida_periodo','media_dia',
              'giro','cobertura_dias','status']],
        column_config={
            'produto': st.column_config.TextColumn('Produto'),
            'estoque': st.column_config.NumberColumn('Estoque', format="%d"),
            'saida_periodo': st.column_config.NumberColumn(f'Saída {janela}d', format="%d"),
            'media_dia': st.column_config.NumberColumn('Média/Dia', format="%.2f"),
            'giro': st.column_config.NumberColumn('Giro', format="%.2fx"),
            'cobertura_dias': st.column_config.NumberColumn('Cobertura (dias)', format="%.0f"),
            'status': st.column_config.TextColumn('Status'),
        },
        height=520, use_container_width=True, hide_index=True)

st.caption(
    f"Empresa: **{emp_nome}** · Saídas = unidades de itens ativos em pedidos "
    f"PRE-VENDA, BRINDE e REPOSICAO da empresa nos últimos {janela} dias · "
    f"Estoque = saldo disponível atual da empresa · "
    f"Cobertura = estoque ÷ média diária de saída · "
    f"Giro = saída do período ÷ estoque atual")
