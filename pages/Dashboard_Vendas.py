import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Dashboard de Vendas", page_icon="📊", layout="wide")

# ── CSS – Bento Grid & Modern Dark ───────────────────────────────────────────
st.markdown("""
<style>
.block-container{padding-top:.7rem;padding-bottom:.5rem;max-width:100%}
div[data-testid="metric-container"]{
    background:linear-gradient(135deg,rgba(123,97,255,.13) 0%,rgba(0,212,255,.07) 100%);
    border:1px solid rgba(123,97,255,.35);
    border-radius:14px;padding:1rem 1.3rem;
    transition:border-color .2s;
}
div[data-testid="metric-container"]:hover{border-color:rgba(0,212,255,.6)}
[data-testid="stMetricValue"]{font-size:1.85rem!important;font-weight:800!important;letter-spacing:-.02em}
[data-testid="stMetricLabel"]{font-size:.72rem!important;text-transform:uppercase;letter-spacing:.08em;opacity:.6}
[data-testid="stMetricDelta"]>div{font-size:.72rem!important}
.stTabs [data-baseweb="tab-list"]{gap:5px;background:rgba(255,255,255,.04);padding:5px;border-radius:12px;margin-bottom:.5rem}
.stTabs [data-baseweb="tab"]{padding:7px 20px;border-radius:8px;font-size:.82rem;font-weight:500;letter-spacing:.02em}
h3{font-size:.8rem!important;text-transform:uppercase;letter-spacing:.09em;color:#8B92A5!important;
   margin:.1rem 0 .5rem 0!important;padding-bottom:.35rem;border-bottom:1px solid rgba(123,97,255,.28)}
hr{border-color:rgba(123,97,255,.15)!important;margin:.6rem 0!important}
[data-testid="stDataFrame"]{border-radius:10px;overflow:hidden}
</style>
""", unsafe_allow_html=True)

# ── CONSTANTES ────────────────────────────────────────────────────────────────
PL = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#C4C9D4", size=11, family="Inter,sans-serif"),
    margin=dict(l=0, r=4, t=30, b=0),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
)
PURPLE = "#7B61FF"; CYAN = "#00D4FF"; GREEN = "#00FF94"; AMBER = "#FFB800"; RED = "#FF6B6B"
SEQ = [PURPLE, "#5B8EFF", CYAN, "#00FFB8", GREEN, "#B0FF66", AMBER, RED]
HEAT = [[0,"#0D1117"],[.3,PURPLE],[.7,"#5B8EFF"],[1,CYAN]]
HEAT_WARM = [[0,"#0D1117"],[.4,AMBER],[1,RED]]
HEAT_GREEN = [[0,"#0D1117"],[.4,PURPLE],[1,GREEN]]

# ── DB ────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_conn():
    return psycopg2.connect(
        host=st.secrets["DB_HOST"], port=st.secrets["DB_PORT"],
        dbname=st.secrets["DB_NAME"], user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
    )

@st.cache_data(ttl=600)
def Q(sql): return pd.read_sql(sql, get_conn())

def brl(v): return f"R$ {v:,.0f}".replace(",",".")
def brls(v): return f"R${v/1000:.0f}k" if v >= 1000 else f"R${v:.0f}"

def badge(v, p25, p75):
    if v >= p75: return "🟢 Alto"
    if v >= p25: return "🟡 Médio"
    return "🔴 Baixo"

# ── CABEÇALHO ─────────────────────────────────────────────────────────────────
st.markdown(
    f"## 📊 Dashboard de Vendas — SGV  "
    f"<span style='font-size:.75rem;color:#8B92A5;font-weight:400'>"
    f"Atualizado {datetime.now().strftime('%d/%m/%Y %H:%M')} · PRE-VENDA válidos · cache 10 min</span>",
    unsafe_allow_html=True
)

tabs = st.tabs(["🛣️ Rotas","👥 Faixa Etária","🧑‍💼 Vendedor × Estado","🎁 Brindes","🛒 PRE-VENDA"])

# ════ TAB 1 – ROTAS ══════════════════════════════════════════════════════════
with tabs[0]:
    df = Q("""
        SELECT r.nome_rota AS rota,
            COUNT(DISTINCT DATE_TRUNC('week', p.data)) AS semanas,
            COUNT(p.id) AS pedidos,
            ROUND(SUM(p.valor_total)::numeric,2) AS fat_total,
            ROUND(COUNT(p.id)::numeric/COUNT(DISTINCT DATE_TRUNC('week',p.data)),1) AS ped_sem,
            ROUND(SUM(p.valor_total)/COUNT(DISTINCT DATE_TRUNC('week',p.data))::numeric,2) AS fat_sem,
            ROUND(AVG(p.valor_total)::numeric,2) AS ticket
        FROM pedido p JOIN rotas r ON r.id_rota=p.id_rota
        WHERE p.cancelado_em IS NULL AND p.status!='CANCELADO'
          AND p.tipo_pedido='PRE-VENDA' AND p.id_rota IS NOT NULL
        GROUP BY r.nome_rota HAVING COUNT(p.id)>0
        ORDER BY fat_sem DESC
    """)
    trend = Q("""
        SELECT DATE_TRUNC('week', p.data)::date AS semana,
            COUNT(p.id) AS pedidos,
            ROUND(SUM(p.valor_total)::numeric,2) AS faturamento
        FROM pedido p
        WHERE p.cancelado_em IS NULL AND p.status!='CANCELADO' AND p.tipo_pedido='PRE-VENDA'
        GROUP BY semana ORDER BY semana
    """)

    p25 = df.fat_sem.quantile(.25); p75 = df.fat_sem.quantile(.75)
    ka, kb, kc, kd = st.columns(4)
    ka.metric("Rotas Ativas", f"{len(df)}", "PRE-VENDA")
    kb.metric("Faturamento Total", brl(df.fat_total.sum()))
    kc.metric("Top Rota / Semana", brl(df.fat_sem.iloc[0]), df.rota.iloc[0][:28])
    kd.metric("Ticket Médio Geral", brl(df.ticket.mean()))
    st.markdown("---")

    st.markdown("### 📈 Tendência Semanal — Faturamento PRE-VENDA")
    fig_t = go.Figure()
    fig_t.add_trace(go.Scatter(
        x=trend.semana, y=trend.faturamento, mode='lines+markers',
        line=dict(color=CYAN, width=2.5), marker=dict(size=5, color=PURPLE),
        fill='tozeroy', fillcolor='rgba(123,97,255,.08)',
        hovertemplate='%{x|%d/%m/%y}<br>R$ %{y:,.0f}<extra></extra>',
    ))
    fig_t.update_layout(**PL, height=160, showlegend=False)
    fig_t.update_xaxes(tickformat='%b/%y', tickfont=dict(size=9), gridcolor='rgba(255,255,255,.05)')
    fig_t.update_yaxes(tickformat=',.0f', tickfont=dict(size=9), gridcolor='rgba(255,255,255,.05)')
    st.plotly_chart(fig_t, use_container_width=True)
    st.markdown("---")

    ca, cb = st.columns([5,6])
    with ca:
        st.markdown("### Top 20 Rotas — Média Semanal (R$)")
        d20 = df.head(20)
        fig = go.Figure(go.Bar(
            x=d20.fat_sem, y=d20.rota, orientation='h',
            marker=dict(color=d20.fat_sem, colorscale=HEAT, showscale=False, line=dict(width=0)),
            text=d20.fat_sem.apply(brls), textposition='outside', textfont=dict(size=9, color='#8B92A5'),
        ))
        fig.update_layout(**PL, height=530)
        fig.update_yaxes(autorange='reversed', tickfont=dict(size=9))
        fig.update_xaxes(visible=False)
        st.plotly_chart(fig, use_container_width=True)
    with cb:
        st.markdown("### Visão Detalhada por Rota")
        df_tbl = df.copy()
        df_tbl['Status'] = df_tbl.fat_sem.apply(lambda v: badge(v, p25, p75))
        df_tbl.index = range(1, len(df_tbl)+1); df_tbl.index.name = 'Pos.'
        st.dataframe(df_tbl[['rota','ped_sem','fat_sem','ticket','Status']].rename(columns={
            'rota':'Rota','ped_sem':'Ped/Sem','fat_sem':'Fat/Sem (R$)','ticket':'Ticket','Status':'Status'
        }), height=530, use_container_width=True)

# ════ TAB 2 – FAIXA ETÁRIA ═══════════════════════════════════════════════════
with tabs[1]:
    df = Q("""
        SELECT CASE
            WHEN DATE_PART('year',AGE(c.data_nascimento))<18 THEN 'Menor 18'
            WHEN DATE_PART('year',AGE(c.data_nascimento)) BETWEEN 18 AND 25 THEN '18-25'
            WHEN DATE_PART('year',AGE(c.data_nascimento)) BETWEEN 26 AND 35 THEN '26-35'
            WHEN DATE_PART('year',AGE(c.data_nascimento)) BETWEEN 36 AND 45 THEN '36-45'
            WHEN DATE_PART('year',AGE(c.data_nascimento)) BETWEEN 46 AND 60 THEN '46-60'
            ELSE '+60' END AS faixa,
            COUNT(DISTINCT c.id_cliente) AS clientes,
            COUNT(p.id) AS pedidos,
            ROUND(AVG(p.valor_total)::numeric,2) AS ticket,
            ROUND(SUM(p.valor_total)::numeric,2) AS faturamento
        FROM clientes c JOIN pedido p ON p.id_cliente=c.id_cliente
        WHERE c.data_nascimento IS NOT NULL AND p.tipo_pedido='PRE-VENDA'
          AND p.cancelado_em IS NULL AND p.status!='CANCELADO' AND c.deleted_at IS NULL
        GROUP BY faixa ORDER BY MIN(DATE_PART('year',AGE(c.data_nascimento)))
    """)

    idx_mc = df.clientes.idxmax(); idx_mt = df.ticket.idxmax()
    ka, kb, kc, kd = st.columns(4)
    ka.metric("Faixas Mapeadas", len(df))
    kb.metric("Total Clientes", f"{int(df.clientes.sum()):,}".replace(",","."))
    kc.metric("Faixa Dominante", df.loc[idx_mc,'faixa'], f"{int(df.clientes.max()):,}".replace(",",".")+" cli")
    kd.metric("Maior Ticket", df.loc[idx_mt,'faixa'], brl(df.ticket.max()))
    st.markdown("---")

    ca, cb, cc = st.columns([4,4,3])
    with ca:
        st.markdown("### Ticket Médio por Faixa")
        fig = go.Figure(go.Bar(
            x=df.faixa, y=df.ticket,
            marker=dict(color=df.ticket, colorscale=HEAT_GREEN, showscale=False, line=dict(width=0)),
            text=df.ticket.apply(lambda v: f"R${v:,.0f}".replace(",",".")),
            textposition='outside', textfont=dict(size=10),
        ))
        fig.update_layout(**PL, height=360)
        fig.update_xaxes(tickfont=dict(size=11)); fig.update_yaxes(visible=False)
        st.plotly_chart(fig, use_container_width=True)
    with cb:
        st.markdown("### Faturamento por Faixa")
        fig2 = go.Figure(go.Bar(
            x=df.faixa, y=df.faturamento,
            marker=dict(color=df.faturamento, colorscale=HEAT, showscale=False, line=dict(width=0)),
            text=df.faturamento.apply(brls), textposition='outside', textfont=dict(size=10),
        ))
        fig2.update_layout(**PL, height=360)
        fig2.update_xaxes(tickfont=dict(size=11)); fig2.update_yaxes(visible=False)
        st.plotly_chart(fig2, use_container_width=True)
    with cc:
        st.markdown("### Distribuição")
        fig3 = go.Figure(go.Pie(
            labels=df.faixa, values=df.clientes, hole=0.62,
            marker=dict(colors=SEQ[:len(df)], line=dict(width=0)),
            textinfo='percent', textfont=dict(size=10),
        ))
        fig3.update_layout(**PL, height=360, showlegend=True,
                           legend=dict(orientation='v',x=1,y=0.5))
        st.plotly_chart(fig3, use_container_width=True)

    st.dataframe(df.rename(columns={
        'faixa':'Faixa','clientes':'Clientes','pedidos':'Pedidos',
        'ticket':'Ticket Médio (R$)','faturamento':'Faturamento (R$)'
    }), use_container_width=True, hide_index=True)

# ════ TAB 3 – VENDEDOR × ESTADO ══════════════════════════════════════════════
with tabs[2]:
    df = Q("""
        SELECT v.nome_vendedor AS vendedor,
            CASE
                WHEN CAST(LEFT(c.cep_cliente,2) AS INT) BETWEEN 66 AND 68 THEN 'PA'
                WHEN CAST(LEFT(c.cep_cliente,2) AS INT)=78 THEN 'MT'
                WHEN CAST(LEFT(c.cep_cliente,2) AS INT) BETWEEN 74 AND 76 THEN 'GO'
                ELSE 'Outro' END AS estado,
            COUNT(DISTINCT c.id_cliente) AS clientes,
            COUNT(p.id) AS pedidos,
            ROUND(AVG(p.valor_total)::numeric,2) AS ticket,
            ROUND(SUM(p.valor_total)::numeric,2) AS faturamento
        FROM clientes c
        JOIN vendedor v ON v.id_vendedor=c.id_geral_vendedor
        JOIN pedido p ON p.id_cliente=c.id_cliente
        WHERE p.cancelado_em IS NULL AND p.status!='CANCELADO' AND p.tipo_pedido='PRE-VENDA'
          AND c.deleted_at IS NULL AND c.data_nascimento IS NOT NULL
          AND c.cep_cliente IS NOT NULL AND c.cep_cliente!='' AND c.cep_cliente ~ '^\d'
        GROUP BY v.nome_vendedor, estado ORDER BY faturamento DESC
    """)
    resumo = df.groupby('vendedor').agg(
        fat=('faturamento','sum'), ped=('pedidos','sum'),
        cli=('clientes','sum'), ticket=('ticket','mean')
    ).sort_values('fat', ascending=False)

    ka, kb, kc, kd = st.columns(4)
    ka.metric("Vendedores", df.vendedor.nunique())
    kb.metric("Faturamento Total", brl(df.faturamento.sum()))
    kc.metric("Top Vendedor", resumo.index[0][:25], brl(resumo.fat.iloc[0]))
    kd.metric("Ticket Médio", brl(df.ticket.mean()))
    st.markdown("---")

    ca, cb = st.columns([3,2])
    with ca:
        st.markdown("### 🗺️ Heatmap — Faturamento por Vendedor × Estado")
        pivot = df.pivot_table(values='faturamento', index='vendedor', columns='estado',
                               aggfunc='sum', fill_value=0)
        pivot['_t'] = pivot.sum(axis=1)
        pivot = pivot.sort_values('_t', ascending=False).drop(columns='_t').head(20)
        z_text = pivot.map(lambda v: brls(v) if v > 0 else "")
        fig = px.imshow(pivot, color_continuous_scale=HEAT, aspect='auto', zmin=0)
        fig.update_traces(text=z_text.values, texttemplate="%{text}",
                          textfont=dict(size=9),
                          hovertemplate='%{y} × %{x}<br>R$ %{z:,.0f}<extra></extra>')
        fig.update_layout(**PL, height=520, coloraxis_showscale=False)
        fig.update_xaxes(tickfont=dict(size=11), side='top')
        fig.update_yaxes(tickfont=dict(size=9))
        st.plotly_chart(fig, use_container_width=True)
    with cb:
        st.markdown("### Ranking de Vendedores")
        st.dataframe(resumo.rename(columns={
            'fat':'Faturamento (R$)','ped':'Pedidos','cli':'Clientes','ticket':'Ticket Médio'
        }), height=520, use_container_width=True)

# ════ TAB 4 – BRINDES ════════════════════════════════════════════════════════
with tabs[3]:
    df = Q("""
        SELECT pr.nome_produto AS produto,
            SUM(pi.quantidade) AS qtd,
            COUNT(DISTINCT p.id) AS pedidos,
            ROUND(AVG(pi.valor_unitario)::numeric,2) AS preco,
            ROUND(SUM(pi.valor_total)::numeric,2) AS valor_total
        FROM pedido p
        JOIN pedido_itens pi ON pi.id_pedido=p.id
        JOIN produto pr ON pr.id_produto=pi.id_produto
        WHERE p.tipo_pedido='BRINDE' AND p.cancelado_em IS NULL AND p.status!='CANCELADO'
        GROUP BY pr.nome_produto ORDER BY valor_total DESC
    """)

    ka, kb, kc, kd = st.columns(4)
    ka.metric("Produtos Distintos", len(df))
    kb.metric("Unidades Doadas", f"{int(df.qtd.sum()):,}".replace(",","."))
    kc.metric("Valor Total", brl(df.valor_total.sum()))
    kd.metric("Produto #1", df.produto.iloc[0][:28], brl(df.valor_total.iloc[0]))
    st.markdown("---")

    ca, cb = st.columns([2,3])
    with ca:
        st.markdown("### Top 15 Brindes")
        d15 = df.head(15)
        fig = go.Figure(go.Bar(
            x=d15.valor_total, y=d15.produto, orientation='h',
            marker=dict(color=d15.valor_total, colorscale=HEAT_WARM, showscale=False, line=dict(width=0)),
            text=d15.valor_total.apply(brls), textposition='outside', textfont=dict(size=9, color='#8B92A5'),
        ))
        fig.update_layout(**PL, height=490)
        fig.update_yaxes(autorange='reversed', tickfont=dict(size=9)); fig.update_xaxes(visible=False)
        st.plotly_chart(fig, use_container_width=True)
    with cb:
        st.markdown("### Lista Completa")
        st.dataframe(df.rename(columns={
            'produto':'Produto','qtd':'Qtd','pedidos':'Pedidos',
            'preco':'Preço Médio (R$)','valor_total':'Valor Total (R$)'
        }), height=490, use_container_width=True, hide_index=True)

# ════ TAB 5 – PRE-VENDA ══════════════════════════════════════════════════════
with tabs[4]:
    df = Q("""
        SELECT pr.nome_produto AS produto,
            SUM(pi.quantidade) AS qtd,
            COUNT(DISTINCT p.id) AS pedidos,
            ROUND(AVG(pi.valor_unitario)::numeric,2) AS preco,
            ROUND(SUM(pi.valor_total)::numeric,2) AS faturamento
        FROM pedido p
        JOIN pedido_itens pi ON pi.id_pedido=p.id
        JOIN produto pr ON pr.id_produto=pi.id_produto
        WHERE p.tipo_pedido='PRE-VENDA' AND p.cancelado_em IS NULL AND p.status!='CANCELADO'
        GROUP BY pr.nome_produto ORDER BY faturamento DESC
    """)

    ka, kb, kc, kd = st.columns(4)
    ka.metric("Produtos Distintos", len(df))
    kb.metric("Unidades Vendidas", f"{int(df.qtd.sum()):,}".replace(",","."))
    kc.metric("Faturamento Total", brl(df.faturamento.sum()))
    kd.metric("Produto #1", df.produto.iloc[0][:28], brl(df.faturamento.iloc[0]))
    st.markdown("---")

    busca = st.text_input("🔍 Buscar produto", "", key="busca_pv", placeholder="Digite parte do nome...")
    dff = df[df.produto.str.contains(busca, case=False, na=False)] if busca else df

    ca, cb = st.columns([3,4])
    with ca:
        st.markdown("### Top 15 Produtos — Faturamento")
        d15 = dff.head(15)
        fig = go.Figure(go.Bar(
            x=d15.faturamento, y=d15.produto, orientation='h',
            marker=dict(color=d15.faturamento, colorscale=HEAT_GREEN, showscale=False, line=dict(width=0)),
            text=d15.faturamento.apply(brls), textposition='outside', textfont=dict(size=9, color='#8B92A5'),
        ))
        fig.update_layout(**PL, height=490)
        fig.update_yaxes(autorange='reversed', tickfont=dict(size=9)); fig.update_xaxes(visible=False)
        st.plotly_chart(fig, use_container_width=True)
    with cb:
        st.markdown("### Ranking Completo")
        st.dataframe(dff.rename(columns={
            'produto':'Produto','qtd':'Qtd','pedidos':'Pedidos',
            'preco':'Preço Médio (R$)','faturamento':'Faturamento (R$)'
        }), height=490, use_container_width=True, hide_index=True)
