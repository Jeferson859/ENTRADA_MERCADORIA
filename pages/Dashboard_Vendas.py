# encoding: utf-8
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from db import (
    load_vendas_por_rota,
    load_tendencia_semanal,
    load_vendas_faixa_etaria,
    load_vendas_vendedor_estado,
    load_produtos_por_tipo,
)

st.set_page_config(page_title="Dashboard de Vendas", page_icon="📊", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""<style>
.block-container{padding-top:.7rem;padding-bottom:.5rem;max-width:100%}
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

# ── CONSTANTES ────────────────────────────────────────────────────────────────
PURPLE = "#7B61FF"; CYAN = "#00D4FF"; GREEN = "#00FF94"
AMBER = "#FFB800"; RED = "#FF6B6B"
SEQ = [PURPLE,"#5B8EFF",CYAN,"#00FFB8",GREEN,"#B0FF66",AMBER,RED]
HEAT = [[0,"#0D1117"],[.3,PURPLE],[.7,"#5B8EFF"],[1,CYAN]]
HEAT_WARM = [[0,"#0D1117"],[.4,AMBER],[1,RED]]
HEAT_GREEN = [[0,"#0D1117"],[.4,PURPLE],[1,GREEN]]
PL = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#C4C9D4", size=11, family="Inter,sans-serif"),
    margin=dict(l=0,r=4,t=30,b=0),
)

# ── FILTRO DE PERÍODO (sidebar — vale para todas as abas) ────────────────────
with st.sidebar:
    st.header("Filtros — Dashboard")
    col_di, col_df = st.columns(2)
    with col_di:
        f_ini = st.date_input("De", value=None, key="dash_ini")
    with col_df:
        f_fim = st.date_input("Até", value=None, key="dash_fim")
    st.caption("Vazio = histórico completo")
    if st.button("🔄 Recarregar dados"):
        st.cache_data.clear()
        st.rerun()

# ── DADOS (consultas centralizadas no db.py, cache 10 min) ───────────────────
@st.cache_data(ttl=600, show_spinner="Carregando rotas...")
def fetch_rotas(di, df):
    return load_vendas_por_rota(data_ini=di, data_fim=df)

@st.cache_data(ttl=600, show_spinner=False)
def fetch_trend(di, df):
    return load_tendencia_semanal(data_ini=di, data_fim=df)

@st.cache_data(ttl=600, show_spinner="Carregando faixas etárias...")
def fetch_faixa_etaria(di, df):
    return load_vendas_faixa_etaria(data_ini=di, data_fim=df)

@st.cache_data(ttl=600, show_spinner="Carregando vendedores...")
def fetch_vendedor_estado(di, df):
    return load_vendas_vendedor_estado(data_ini=di, data_fim=df)

@st.cache_data(ttl=600, show_spinner="Carregando produtos...")
def fetch_produtos(tipo, di, df):
    return load_produtos_por_tipo(tipo, data_ini=di, data_fim=df)

# ── HELPERS ───────────────────────────────────────────────────────────────────
def brl(v): return f"R$ {v:,.0f}".replace(",",".")
def brls(v): return f"R${v/1000:.0f}k" if v>=1000 else f"R${v:.0f}"
def badge(v, p25, p75):
    if v >= p75: return "🟢 Alto"
    if v >= p25: return "🟡 Médio"
    return "🔴 Baixo"

def _sparksvg(series, color, w=80, h=28):
    pts = [float(x) for x in list(series) if pd.notna(x)][-20:]
    if len(pts) < 2: return ""
    mx=max(pts); mn=min(pts); rng=mx-mn or 1
    cs = [f"{round(i*w/(len(pts)-1))},{round(h-(v-mn)/rng*h)}" for i,v in enumerate(pts)]
    p = "M "+" L ".join(cs)
    gid = f"g{abs(hash(str(pts[:2])))%99999}"
    return (f'<svg width="{w}" height="{h}" style="overflow:visible;display:block">'
            f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0%" stop-color="{color}" stop-opacity=".3"/>'
            f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>'
            f'<path d="{p} L{w},{h} L0,{h}Z" fill="url(#{gid})"/>'
            f'<path d="{p}" stroke="{color}" stroke-width="1.8" fill="none"/></svg>')

def kpi(col, label, value, series=None, color=CYAN, sub=None):
    spark = _sparksvg(series, color) if series is not None and len(series) > 1 else ""
    sub_h = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    with col:
        st.markdown(
            f'<div class="kpi-card">'
            f'<div><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div>{sub_h}</div>'
            f'<div>{spark}</div></div>',
            unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
periodo_txt = "histórico completo"
if f_ini or f_fim:
    periodo_txt = f"{f_ini.strftime('%d/%m/%y') if f_ini else '...'} → {f_fim.strftime('%d/%m/%y') if f_fim else 'hoje'}"

st.markdown(
    f'## 📊 Dashboard de Vendas — SGV&nbsp;&nbsp;'
    f'<span style="font-size:.75rem;color:#8B92A5;font-weight:400">'
    f'Atualizado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}'
    f' · PRE-VENDA válidos · período: {periodo_txt} · cache 10 min</span>',
    unsafe_allow_html=True)

tabs = st.tabs(["🛣️ Rotas","👥 Faixa Etária",
                "🧑‍💼 Vendedor × Estado","🎁 Produtos BRINDE","🛒 Produtos PRE-VENDA"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 – ROTAS
# ════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    rotas = fetch_rotas(f_ini, f_fim)
    trend = fetch_trend(f_ini, f_fim)

    # KPIs
    c1, c2, c3 = st.columns(3)
    kpi(c1, "Total de Rotas", str(len(rotas)),
        trend.pedidos, PURPLE)
    kpi(c2, "Faturamento Total", brl(rotas.fat_total.sum()),
        trend.faturamento, CYAN)
    kpi(c3, "Ticket Médio Geral", brl(rotas.ticket.mean()),
        trend.faturamento, GREEN)
    st.markdown("<div style='margin:.4rem 0'></div>", unsafe_allow_html=True)

    # Trend sparkline
    st.markdown("### 📈 Tendência Semanal — Faturamento PRE-VENDA")
    ft = go.Figure(go.Scatter(
        x=trend.semana, y=trend.faturamento, mode='lines+markers',
        line=dict(color=CYAN, width=2.5), marker=dict(size=5, color=PURPLE),
        fill='tozeroy', fillcolor='rgba(123,97,255,.08)',
        hovertemplate='%{x|%d/%m/%y}<br>R$ %{y:,.0f}<extra></extra>'))
    ft.update_layout(**PL, height=160, showlegend=False)
    ft.update_xaxes(tickformat='%b/%y', tickfont=dict(size=9),
                    gridcolor='rgba(255,255,255,.05)')
    ft.update_yaxes(tickformat=',.0f', tickfont=dict(size=9),
                    gridcolor='rgba(255,255,255,.05)')
    st.plotly_chart(ft, use_container_width=True)
    st.markdown("---")

    # Bar + Table
    p25 = rotas.fat_sem.quantile(.25); p75 = rotas.fat_sem.quantile(.75)
    ca, cb = st.columns([5, 6])
    with ca:
        st.markdown("### Top 20 Rotas — Média Semanal (R$)")
        d20 = rotas.head(20)
        fb = go.Figure(go.Bar(
            x=d20.fat_sem, y=d20.rota, orientation='h',
            marker=dict(color=d20.fat_sem, colorscale=HEAT,
                        showscale=False, line=dict(width=0)),
            text=d20.fat_sem.apply(brls), textposition='outside',
            textfont=dict(size=9, color='#8B92A5')))
        fb.update_layout(**PL, height=560)
        fb.update_yaxes(autorange='reversed', tickfont=dict(size=9))
        fb.update_xaxes(visible=False)
        st.plotly_chart(fb, use_container_width=True)
    with cb:
        st.markdown("### Visão Detalhada por Rota")
        rt = rotas.copy()
        rt['Status'] = rt.fat_sem.apply(lambda v: badge(v, p25, p75))
        rt['fat_sem'] = rt['fat_sem'].apply(brl)
        rt['ticket'] = rt['ticket'].apply(brl)
        rt.index = range(1, len(rt)+1); rt.index.name = 'Pos.'
        st.dataframe(
            rt[['rota','ped_sem','fat_sem','ticket','Status']].rename(columns={
                'rota':'Rota','ped_sem':'Ped/Sem',
                'fat_sem':'Fat/Sem (R$)','ticket':'Ticket Médio','Status':'Status'}),
            height=560, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 – FAIXA ETÁRIA
# ════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    fe = fetch_faixa_etaria(f_ini, f_fim)

    imc = fe.clientes.idxmax(); imt = fe.ticket.idxmax()
    c1, c2, c3 = st.columns(3)
    kpi(c1, "Faixas Mapeadas", str(len(fe)), fe.clientes, PURPLE)
    kpi(c2, "Total Clientes",
        f"{int(fe.clientes.sum()):,}".replace(",","."), fe.faturamento, CYAN)
    kpi(c3, "Faixa Dominante", fe.loc[imc,'faixa'], fe.clientes, GREEN,
        f"{int(fe.clientes.max()):,}".replace(",",".")+" clientes")
    st.markdown("<div style='margin:.4rem 0'></div>", unsafe_allow_html=True)
    st.markdown("---")

    ca, cb, cc = st.columns([4, 4, 3])
    with ca:
        st.markdown("### Ticket Médio por Faixa")
        fg = go.Figure(go.Bar(
            x=fe.faixa, y=fe.ticket,
            marker=dict(color=fe.ticket, colorscale=HEAT_GREEN,
                        showscale=False, line=dict(width=0)),
            text=fe.ticket.apply(lambda v: f"R${v:,.0f}".replace(",",".")),
            textposition='outside', textfont=dict(size=10)))
        fg.update_layout(**PL, height=340)
        fg.update_xaxes(tickfont=dict(size=11))
        fg.update_yaxes(visible=False)
        st.plotly_chart(fg, use_container_width=True)
    with cb:
        st.markdown("### Faturamento por Faixa")
        fg2 = go.Figure(go.Bar(
            x=fe.faixa, y=fe.faturamento,
            marker=dict(color=fe.faturamento, colorscale=HEAT,
                        showscale=False, line=dict(width=0)),
            text=fe.faturamento.apply(brls),
            textposition='outside', textfont=dict(size=10)))
        fg2.update_layout(**PL, height=340)
        fg2.update_xaxes(tickfont=dict(size=11))
        fg2.update_yaxes(visible=False)
        st.plotly_chart(fg2, use_container_width=True)
    with cc:
        st.markdown("### Distribuição")
        fg3 = go.Figure(go.Pie(
            labels=fe.faixa, values=fe.clientes, hole=0.6,
            marker=dict(colors=SEQ[:len(fe)], line=dict(width=0)),
            textinfo='percent', textfont=dict(size=10)))
        fg3.update_layout(**PL, height=340, showlegend=True)
        fg3.update_layout(legend=dict(bgcolor="rgba(0,0,0,0)", orientation='v',
                                      x=1, y=0.5, font=dict(size=9)))
        st.plotly_chart(fg3, use_container_width=True)

    st.markdown("---")
    fe_disp = fe.copy()
    fe_disp['ticket'] = fe_disp['ticket'].apply(brl)
    fe_disp['faturamento']= fe_disp['faturamento'].apply(brl)
    st.dataframe(fe_disp.rename(columns={
        'faixa':'Faixa','clientes':'Clientes','pedidos':'Pedidos',
        'ticket':'Ticket Médio','faturamento':'Faturamento'}),
        use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 – VENDEDOR × ESTADO
# ════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    vd = fetch_vendedor_estado(f_ini, f_fim)
    res = (vd.groupby('vendedor')
             .agg(fat=('faturamento','sum'), ped=('pedidos','sum'),
                  cli=('clientes','sum'), ticket=('ticket','mean'))
             .sort_values('fat', ascending=False))

    c1, c2, c3 = st.columns(3)
    kpi(c1, "Vendedores", str(vd.vendedor.nunique()), res.fat, PURPLE)
    kpi(c2, "Faturamento Total", brl(vd.faturamento.sum()), res.fat, CYAN)
    if len(res) > 0:
        kpi(c3, "Top Vendedor", res.index[0][:22], res.fat, GREEN,
            brl(res.fat.iloc[0]))
    else:
        kpi(c3, "Top Vendedor", "—", None, GREEN)
    st.markdown("<div style='margin:.4rem 0'></div>", unsafe_allow_html=True)
    st.markdown("---")

    ca, cb = st.columns([3, 2])
    with ca:
        st.markdown("### 🗺️ Heatmap — Faturamento por Vendedor × Estado")
        pivot = vd.pivot_table(
            values='faturamento', index='vendedor', columns='estado',
            aggfunc='sum', fill_value=0)
        pivot['_t'] = pivot.sum(axis=1)
        pivot = (pivot.sort_values('_t', ascending=False)
                      .drop(columns='_t').head(20))
        z_text = pivot.map(lambda v: brls(v) if v > 0 else "")
        fh = px.imshow(pivot, color_continuous_scale=HEAT, aspect='auto', zmin=0)
        fh.update_traces(
            text=z_text.values, texttemplate="%{text}",
            textfont=dict(size=9),
            hovertemplate='%{y} × %{x}<br>R$ %{z:,.0f}<extra></extra>')
        fh.update_layout(**PL, height=520, coloraxis_showscale=False)
        fh.update_xaxes(tickfont=dict(size=11), side='top')
        fh.update_yaxes(tickfont=dict(size=9))
        st.plotly_chart(fh, use_container_width=True)
    with cb:
        st.markdown("### Ranking de Vendedores")
        res_disp = res.copy()
        res_disp['fat'] = res_disp['fat'].apply(brl)
        res_disp['ticket'] = res_disp['ticket'].apply(brl)
        st.dataframe(res_disp.rename(columns={
            'fat':'Faturamento','ped':'Pedidos',
            'cli':'Clientes','ticket':'Ticket Médio'}),
            height=520, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 4 – BRINDES
# ════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    br = fetch_produtos("BRINDE", f_ini, f_fim)

    c1, c2, c3 = st.columns(3)
    kpi(c1, "Produtos Distintos", str(len(br)), br.qtd, AMBER)
    kpi(c2, "Unidades Doadas",
        f"{int(br.qtd.sum()):,}".replace(",","."), br.qtd, RED)
    kpi(c3, "Valor Total", brl(br.faturamento.sum()), br.faturamento, PURPLE)
    st.markdown("<div style='margin:.4rem 0'></div>", unsafe_allow_html=True)
    st.markdown("---")

    ca, cb = st.columns([2, 3])
    with ca:
        st.markdown("### Top 15 Brindes")
        d15 = br.head(15)
        fbar = go.Figure(go.Bar(
            x=d15.faturamento, y=d15.produto, orientation='h',
            marker=dict(color=d15.faturamento, colorscale=HEAT_WARM,
                        showscale=False, line=dict(width=0)),
            text=d15.faturamento.apply(brls), textposition='outside',
            textfont=dict(size=9, color='#8B92A5')))
        fbar.update_layout(**PL, height=490)
        fbar.update_yaxes(autorange='reversed', tickfont=dict(size=9))
        fbar.update_xaxes(visible=False)
        st.plotly_chart(fbar, use_container_width=True)
    with cb:
        st.markdown("### Lista Completa")
        br_disp = br.copy()
        br_disp['preco'] = br_disp['preco'].apply(brl)
        br_disp['faturamento'] = br_disp['faturamento'].apply(brl)
        st.dataframe(br_disp.rename(columns={
            'produto':'Produto','qtd':'Qtd','pedidos':'Pedidos',
            'preco':'Preço Médio','faturamento':'Valor Total'}),
            height=490, use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 5 – PRE-VENDA
# ════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    pv = fetch_produtos("PRE-VENDA", f_ini, f_fim)

    c1, c2, c3 = st.columns(3)
    kpi(c1, "Produtos Distintos", str(len(pv)), pv.qtd, PURPLE)
    kpi(c2, "Unidades Vendidas",
        f"{int(pv.qtd.sum()):,}".replace(",","."), pv.faturamento, CYAN)
    kpi(c3, "Faturamento Total", brl(pv.faturamento.sum()), pv.faturamento, GREEN)
    st.markdown("<div style='margin:.4rem 0'></div>", unsafe_allow_html=True)

    busca = st.text_input("🔍 Buscar produto", "", key="busca_pv",
                          placeholder="Digite parte do nome...")
    dff = pv[pv.produto.str.contains(busca, case=False, na=False)] if busca else pv
    st.markdown("---")

    ca, cb = st.columns([3, 4])
    with ca:
        st.markdown("### Top 15 Produtos — Faturamento")
        d15 = dff.head(15)
        fpv = go.Figure(go.Bar(
            x=d15.faturamento, y=d15.produto, orientation='h',
            marker=dict(color=d15.faturamento, colorscale=HEAT_GREEN,
                        showscale=False, line=dict(width=0)),
            text=d15.faturamento.apply(brls), textposition='outside',
            textfont=dict(size=9, color='#8B92A5')))
        fpv.update_layout(**PL, height=490)
        fpv.update_yaxes(autorange='reversed', tickfont=dict(size=9))
        fpv.update_xaxes(visible=False)
        st.plotly_chart(fpv, use_container_width=True)
    with cb:
        st.markdown("### Ranking Completo")
        dff_disp = dff.copy()
        dff_disp['preco'] = dff_disp['preco'].apply(brl)
        dff_disp['faturamento'] = dff_disp['faturamento'].apply(brl)
        st.dataframe(dff_disp.rename(columns={
            'produto':'Produto','qtd':'Qtd','pedidos':'Pedidos',
            'preco':'Preço Médio','faturamento':'Faturamento'}),
            height=490, use_container_width=True, hide_index=True)
