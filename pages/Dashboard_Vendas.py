# encoding: utf-8
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta

from db import (
    load_vendas_por_rota,
    load_tendencia_semanal,
    load_vendas_faixa_etaria,
    load_vendas_vendedor_estado,
    load_produtos_por_tipo,
    load_pedidos_sem_rota,
    load_divergencia_pedido_itens,
)

st.set_page_config(page_title="Dashboard de Vendas", page_icon="📊", layout="wide")

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

    preset = st.radio(
        "Período",
        ["Tudo", "Últimos 30 dias", "Últimos 90 dias", "Este ano", "Personalizado"],
        index=0,
    )

    f_ini, f_fim = None, None
    hoje = date.today()
    if preset == "Últimos 30 dias":
        f_ini = hoje - timedelta(days=30)
    elif preset == "Últimos 90 dias":
        f_ini = hoje - timedelta(days=90)
    elif preset == "Este ano":
        f_ini = date(hoje.year, 1, 1)
    elif preset == "Personalizado":
        col_di, col_df = st.columns(2)
        with col_di:
            f_ini = st.date_input("De", value=None, key="dash_ini")
        with col_df:
            f_fim = st.date_input("Até", value=None, key="dash_fim")

    st.markdown("---")
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

@st.cache_data(ttl=600, show_spinner=False)
def fetch_sem_rota(di, df):
    return load_pedidos_sem_rota(data_ini=di, data_fim=df)

@st.cache_data(ttl=600, show_spinner=False)
def fetch_divergencias(di, df):
    return load_divergencia_pedido_itens(data_ini=di, data_fim=df)

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

def col_moeda(label):
    return st.column_config.NumberColumn(label, format="R$ %.0f")

def col_progresso(label, max_val):
    return st.column_config.ProgressColumn(
        label, format="R$ %.0f", min_value=0, max_value=float(max_val or 1))

# ── HEADER ────────────────────────────────────────────────────────────────────
periodo_txt = "histórico completo" if preset == "Tudo" else preset.lower()
if preset == "Personalizado":
    periodo_txt = (f"{f_ini.strftime('%d/%m/%y') if f_ini else '...'} → "
                   f"{f_fim.strftime('%d/%m/%y') if f_fim else 'hoje'}")

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

    # Filtros da aba
    fc1, fc2 = st.columns([3, 1])
    with fc1:
        sel_rotas = st.multiselect(
            "🛣️ Filtrar rotas específicas (vazio = todas)",
            rotas.rota.tolist(), key="sel_rotas")
    with fc2:
        top_n = st.slider("Top N no gráfico", 5, 50, 20, 5, key="topn_rotas")

    rotas_f = rotas[rotas.rota.isin(sel_rotas)] if sel_rotas else rotas

    # KPIs
    c1, c2, c3 = st.columns(3)
    kpi(c1, "Total de Rotas", str(len(rotas_f)),
        trend.pedidos, PURPLE)
    kpi(c2, "Faturamento Total", brl(rotas_f.fat_total.sum()),
        trend.faturamento, CYAN)
    ticket_geral = (rotas_f.fat_total.sum() / rotas_f.pedidos.sum()) if rotas_f.pedidos.sum() else 0
    kpi(c3, "Ticket Médio Geral", brl(ticket_geral) if len(rotas_f) else "—",
        trend.faturamento, GREEN)
    st.markdown("<div style='margin:.4rem 0'></div>", unsafe_allow_html=True)

    # Pedidos PRE-VENDA sem rota — ficam fora dos totais desta aba
    sem_rota = fetch_sem_rota(f_ini, f_fim)
    if len(sem_rota):
        with st.expander(
            f"⚠️ {len(sem_rota)} pedido(s) PRE-VENDA sem rota vinculada — "
            f"{brl(sem_rota.valor_total.sum())} fora do faturamento desta aba"
        ):
            st.dataframe(
                sem_rota,
                column_config={
                    'id': st.column_config.NumberColumn('Pedido', format="%d"),
                    'data': st.column_config.DatetimeColumn('Data', format="DD/MM/YYYY HH:mm"),
                    'id_cliente': st.column_config.NumberColumn('Cliente', format="%d"),
                    'vendedor': st.column_config.TextColumn('Vendedor'),
                    'status': st.column_config.TextColumn('Status'),
                    'valor_total': col_moeda('Valor'),
                    'obs': st.column_config.TextColumn('Obs'),
                },
                use_container_width=True, hide_index=True)

    # Pedidos onde o valor do cabeçalho difere da soma dos itens
    div = fetch_divergencias(f_ini, f_fim)
    if len(div):
        with st.expander(
            f"🔎 {len(div)} pedido(s) com valor do pedido ≠ soma dos itens — "
            f"diferença líquida de {brl(div.diferenca.sum())} entre as abas Rotas e Produtos"
        ):
            st.caption(
                "A aba **Rotas** soma o `valor_total` do pedido (cabeçalho); a aba "
                "**Produtos PRE-VENDA** soma os itens. Nestes pedidos os dois não batem — "
                "normalmente desconto/ajuste aplicado só no cabeçalho ou item alterado depois.")
            st.dataframe(
                div,
                column_config={
                    'id': st.column_config.NumberColumn('Pedido', format="%d"),
                    'data': st.column_config.DatetimeColumn('Data', format="DD/MM/YYYY"),
                    'status': st.column_config.TextColumn('Status'),
                    'valor_pedido': st.column_config.NumberColumn('Valor Pedido', format="R$ %.2f"),
                    'valor_itens': st.column_config.NumberColumn('Soma Itens', format="R$ %.2f"),
                    'diferenca': st.column_config.NumberColumn('Diferença', format="R$ %.2f"),
                },
                use_container_width=True, hide_index=True)

    # Trend sparkline
    st.markdown("### 📈 Tendência Semanal — Faturamento PRE-VENDA")
    ft = go.Figure(go.Scatter(
        x=trend.semana, y=trend.faturamento, mode='lines+markers',
        line=dict(color=CYAN, width=2.5), marker=dict(size=5, color=PURPLE),
        fill='tozeroy', fillcolor='rgba(123,97,255,.08)',
        hovertemplate='%{x|%d/%m/%y}<br>R$ %{y:,.0f}<extra></extra>'))
    ft.update_layout(**PL, height=160, showlegend=False)
    # Ticks exatamente nas segundas-feiras (início real de cada semana ISO)
    ft.update_xaxes(tickmode='array', tickvals=trend.semana,
                    tickformat='%d/%m', tickfont=dict(size=9),
                    gridcolor='rgba(255,255,255,.05)')
    ft.update_yaxes(tickformat=',.0f', tickfont=dict(size=9),
                    gridcolor='rgba(255,255,255,.05)')
    st.plotly_chart(ft, use_container_width=True)
    st.markdown("---")

    # Bar + Table
    p25 = rotas.fat_sem.quantile(.25); p75 = rotas.fat_sem.quantile(.75)
    ca, cb = st.columns([5, 6])
    with ca:
        st.markdown(f"### Top {top_n} Rotas — Média Semanal (R$)")
        d_top = rotas_f.head(top_n)
        fb = go.Figure(go.Bar(
            x=d_top.fat_sem, y=d_top.rota, orientation='h',
            marker=dict(color=d_top.fat_sem, colorscale=HEAT,
                        showscale=False, line=dict(width=0)),
            text=d_top.fat_sem.apply(brls), textposition='outside',
            textfont=dict(size=9, color='#8B92A5')))
        fb.update_traces(cliponaxis=False)  # não corta o rótulo na borda
        fb.update_layout(**PL, height=max(360, 28*len(d_top)))
        fb.update_layout(margin=dict(l=0, r=52, t=30, b=0))
        fb.update_yaxes(autorange='reversed', tickfont=dict(size=9))
        fb.update_xaxes(visible=False)
        st.plotly_chart(fb, use_container_width=True)
    with cb:
        st.markdown("### Visão Detalhada por Rota")
        rt = rotas_f.copy()
        rt['Status'] = rt.fat_sem.apply(lambda v: badge(v, p25, p75))
        rt.index = range(1, len(rt)+1); rt.index.name = 'Pos.'
        st.dataframe(
            rt[['rota','ped_sem','fat_sem','ticket','Status']],
            column_config={
                'rota': st.column_config.TextColumn('Rota'),
                'ped_sem': st.column_config.NumberColumn('Ped/Sem', format="%.1f"),
                'fat_sem': col_progresso('Fat/Sem', rotas.fat_sem.max()),
                'ticket': col_moeda('Ticket Médio'),
                'Status': st.column_config.TextColumn('Status'),
            },
            height=560, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 – FAIXA ETÁRIA
# ════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    fe = fetch_faixa_etaria(f_ini, f_fim)

    imc = fe.clientes.idxmax(); imt = fe.ticket.idxmax()
    c1, c2, c3, c4 = st.columns(4)
    kpi(c1, "Faixas Mapeadas", str(len(fe)), fe.clientes, PURPLE)
    kpi(c2, "Total Clientes",
        f"{int(fe.clientes.sum()):,}".replace(",","."), fe.faturamento, CYAN)
    kpi(c3, "Faixa Dominante", fe.loc[imc,'faixa'], fe.clientes, GREEN,
        f"{int(fe.clientes.max()):,}".replace(",",".")+" clientes")
    kpi(c4, "Maior Ticket", fe.loc[imt,'faixa'], fe.ticket, AMBER,
        brl(fe.ticket.max()))
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
        fg.update_traces(cliponaxis=False)
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
        fg2.update_traces(cliponaxis=False)
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
    fe_t = fe.copy()
    fe_t['pct_clientes'] = (fe_t.clientes / fe_t.clientes.sum() * 100).round(1)
    st.dataframe(
        fe_t[['faixa','clientes','pct_clientes','pedidos','ticket','faturamento']],
        column_config={
            'faixa': st.column_config.TextColumn('Faixa'),
            'clientes': st.column_config.NumberColumn('Clientes', format="%d"),
            'pct_clientes': st.column_config.NumberColumn('% Clientes', format="%.1f%%"),
            'pedidos': st.column_config.NumberColumn('Pedidos', format="%d"),
            'ticket': col_moeda('Ticket Médio'),
            'faturamento': col_progresso('Faturamento', fe_t.faturamento.max()),
        },
        use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 – VENDEDOR × ESTADO
# ════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    vd = fetch_vendedor_estado(f_ini, f_fim)

    # Filtros da aba
    fc1, fc2 = st.columns([2, 1])
    with fc1:
        estados = ["Todos"] + sorted(vd.estado.unique().tolist())
        sel_estado = st.selectbox("📍 Estado", estados, key="sel_estado")
    with fc2:
        top_v = st.slider("Top N vendedores", 5, 40, 20, 5, key="topn_vend")

    vd_f = vd if sel_estado == "Todos" else vd[vd.estado == sel_estado]

    res = (vd_f.groupby('vendedor')
             .agg(fat=('faturamento','sum'), ped=('pedidos','sum'),
                  cli=('clientes','sum'))
             .sort_values('fat', ascending=False))
    res['ticket'] = res.fat / res.ped.replace(0, pd.NA)  # ticket ponderado: faturamento ÷ pedidos

    c1, c2, c3 = st.columns(3)
    kpi(c1, "Vendedores", str(vd_f.vendedor.nunique()), res.fat, PURPLE)
    kpi(c2, "Faturamento Total", brl(vd_f.faturamento.sum()), res.fat, CYAN)
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
        pivot = vd_f.pivot_table(
            values='faturamento', index='vendedor', columns='estado',
            aggfunc='sum', fill_value=0)
        pivot['_t'] = pivot.sum(axis=1)
        pivot = (pivot.sort_values('_t', ascending=False)
                      .drop(columns='_t').head(top_v))
        z_text = pivot.map(lambda v: brls(v) if v > 0 else "—")
        fh = px.imshow(pivot, color_continuous_scale=HEAT, aspect='auto', zmin=0)
        fh.update_traces(
            xgap=4, ygap=4,  # separa as células formando uma grade organizada
            text=z_text.values, texttemplate="%{text}",
            textfont=dict(size=9),
            hovertemplate='%{y} × %{x}<br>R$ %{z:,.0f}<extra></extra>')
        fh.update_layout(**PL, height=max(380, 34*len(pivot)),
                         coloraxis_showscale=False)
        fh.update_layout(plot_bgcolor='rgba(123,97,255,.06)')
        fh.update_xaxes(tickfont=dict(size=11), side='top',
                        showgrid=False, fixedrange=True)
        fh.update_yaxes(tickfont=dict(size=9),
                        showgrid=False, fixedrange=True)
        st.plotly_chart(fh, use_container_width=True)
    with cb:
        st.markdown("### Ranking de Vendedores")
        st.dataframe(
            res.reset_index(),
            column_config={
                'vendedor': st.column_config.TextColumn('Vendedor'),
                'fat': col_progresso('Faturamento', res.fat.max() if len(res) else 1),
                'ped': st.column_config.NumberColumn('Pedidos', format="%d"),
                'cli': st.column_config.NumberColumn('Clientes', format="%d"),
                'ticket': col_moeda('Ticket Médio'),
            },
            height=520, use_container_width=True, hide_index=True)

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

    busca_br = st.text_input("🔍 Buscar brinde", "", key="busca_br",
                             placeholder="Digite parte do nome...")
    brf = br[br.produto.str.contains(busca_br, case=False, na=False)] if busca_br else br
    st.markdown("---")

    ca, cb = st.columns([2, 3])
    with ca:
        st.markdown("### Top 15 Brindes")
        d15 = brf.head(15)
        fbar = go.Figure(go.Bar(
            x=d15.faturamento, y=d15.produto, orientation='h',
            marker=dict(color=d15.faturamento, colorscale=HEAT_WARM,
                        showscale=False, line=dict(width=0)),
            text=d15.faturamento.apply(brls), textposition='outside',
            textfont=dict(size=9, color='#8B92A5')))
        fbar.update_traces(cliponaxis=False)
        fbar.update_layout(**PL, height=490)
        fbar.update_layout(margin=dict(l=0, r=52, t=30, b=0))
        fbar.update_yaxes(autorange='reversed', tickfont=dict(size=9))
        fbar.update_xaxes(visible=False)
        st.plotly_chart(fbar, use_container_width=True)
    with cb:
        st.markdown("### Lista Completa")
        st.dataframe(
            brf,
            column_config={
                'produto': st.column_config.TextColumn('Produto'),
                'qtd': st.column_config.NumberColumn('Qtd', format="%d"),
                'pedidos': st.column_config.NumberColumn('Pedidos', format="%d"),
                'preco': col_moeda('Preço Médio'),
                'faturamento': col_progresso('Valor Total', br.faturamento.max()),
            },
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

    fc1, fc2 = st.columns([3, 1])
    with fc1:
        busca = st.text_input("🔍 Buscar produto", "", key="busca_pv",
                              placeholder="Digite parte do nome...")
    with fc2:
        metrica = st.radio("Ranking por", ["Faturamento", "Quantidade"],
                           horizontal=True, key="metrica_pv")

    col_rank = "faturamento" if metrica == "Faturamento" else "qtd"
    dff = pv[pv.produto.str.contains(busca, case=False, na=False)] if busca else pv
    dff = dff.sort_values(col_rank, ascending=False)
    st.markdown("---")

    ca, cb = st.columns([3, 4])
    with ca:
        st.markdown(f"### Top 15 Produtos — {metrica}")
        d15 = dff.head(15)
        txt = d15[col_rank].apply(brls) if col_rank == "faturamento" \
              else d15[col_rank].apply(lambda v: f"{int(v):,}".replace(",","."))
        fpv = go.Figure(go.Bar(
            x=d15[col_rank], y=d15.produto, orientation='h',
            marker=dict(color=d15[col_rank], colorscale=HEAT_GREEN,
                        showscale=False, line=dict(width=0)),
            text=txt, textposition='outside',
            textfont=dict(size=9, color='#8B92A5')))
        fpv.update_traces(cliponaxis=False)
        fpv.update_layout(**PL, height=490)
        fpv.update_layout(margin=dict(l=0, r=52, t=30, b=0))
        fpv.update_yaxes(autorange='reversed', tickfont=dict(size=9))
        fpv.update_xaxes(visible=False)
        st.plotly_chart(fpv, use_container_width=True)
    with cb:
        st.markdown("### Ranking Completo")
        st.dataframe(
            dff,
            column_config={
                'produto': st.column_config.TextColumn('Produto'),
                'qtd': st.column_config.NumberColumn('Qtd', format="%d"),
                'pedidos': st.column_config.NumberColumn('Pedidos', format="%d"),
                'preco': col_moeda('Preço Médio'),
                'faturamento': col_progresso('Faturamento', pv.faturamento.max()),
            },
            height=490, use_container_width=True, hide_index=True)
