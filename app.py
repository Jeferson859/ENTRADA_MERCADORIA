import streamlit as st
import pandas as pd
import plotly.express as px
from db import load_pedidos, buscar_pedido_por_id, buscar_pedidos_por_produto, load_contagens, load_itens_contagem, get_opcoes_filtros

st.set_page_config(
    page_title="Entrada Mercadoria",
    page_icon="📋",
    layout="wide",
)

st.title("📋 Pedidos — Movimentação e Consulta")

# ── Carrega opções de filtro ──────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def fetch_opcoes():
    return get_opcoes_filtros()

try:
    opcoes = fetch_opcoes()
except Exception as e:
    st.error(f"Não foi possível conectar ao banco de dados: {e}")
    st.info("Verifique o arquivo `.env` com DB_HOST, DB_PORT, DB_NAME, DB_USER e DB_PASSWORD.")
    st.stop()

aba_mov, aba_busca, aba_ajuste = st.tabs(["📊 Movimentação", "🔍 Buscar Pedido", "📦 Ajuste de Estoque"])


# ══════════════════════════════════════════════════════════════════════════════
# ABA 1 — MOVIMENTAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
with aba_mov:

    with st.sidebar:
        st.header("Filtros — Movimentação")

        col_di, col_df = st.columns(2)
        with col_di:
            data_ini = st.date_input("De", value=None, key="ini")
        with col_df:
            data_fim = st.date_input("Até", value=None, key="fim")

        sel_status = st.selectbox("Status", ["Todos"] + opcoes["status"])
        sel_tipo   = st.selectbox("Tipo de Pedido", ["Todos"] + opcoes["tipos"])

        vend_df   = opcoes["vendedores"]
        vend_opts = ["Todos"] + vend_df["nome_vendedor"].fillna("Sem nome").tolist()
        sel_vend  = st.selectbox("Vendedor", vend_opts)

        st.markdown("---")
        if st.button("🔄 Recarregar"):
            st.cache_data.clear()
            st.rerun()

    # Monta parâmetros
    id_vend = None
    if sel_vend != "Todos":
        row = vend_df[vend_df["nome_vendedor"] == sel_vend]
        if not row.empty:
            id_vend = int(row.iloc[0]["id_vendedor"])

    @st.cache_data(ttl=60, show_spinner="Carregando pedidos...")
    def fetch_mov(di, df, st_val, tp_val, vd_val):
        return load_pedidos(
            data_ini=di,
            data_fim=df,
            status=None if st_val == "Todos" else st_val,
            tipo_pedido=None if tp_val == "Todos" else tp_val,
            id_vendedor=vd_val,
        )

    try:
        df = fetch_mov(data_ini, data_fim, sel_status, sel_tipo, id_vend)
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        st.stop()

    # ── KPIs ──────────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total de pedidos",  f"{len(df):,}")
    k2.metric("Valor total",       f"R$ {df['valor_total'].sum():,.2f}")
    k3.metric("Cancelados",        f"{df['cancelado_em'].notna().sum():,}")
    k4.metric("Tipos distintos",   f"{df['tipo_pedido'].nunique()}")

    st.divider()

    # ── Gráfico por status ────────────────────────────────────────────────────
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        if not df.empty and "status" in df.columns:
            st_df = df["status"].value_counts().reset_index()
            st_df.columns = ["status", "total"]
            fig = px.bar(
                st_df, x="status", y="total", text="total",
                title="Pedidos por Status",
                labels={"status": "Status", "total": "Qtd."},
                color="status",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(showlegend=False, height=320, margin=dict(t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)

    with col_g2:
        if not df.empty and "tipo_pedido" in df.columns:
            tp_df = df["tipo_pedido"].value_counts().reset_index()
            tp_df.columns = ["tipo_pedido", "total"]
            fig2 = px.pie(
                tp_df, names="tipo_pedido", values="total",
                title="Distribuição por Tipo",
                hole=0.45,
            )
            fig2.update_layout(height=320, margin=dict(t=40, b=10))
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── Evolução temporal ─────────────────────────────────────────────────────
    if not df.empty and "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
        tempo = (
            df.groupby(df["data"].dt.date)
            .agg(qtd=("id", "count"), valor=("valor_total", "sum"))
            .reset_index()
            .rename(columns={"data": "dia"})
        )
        fig3 = px.line(
            tempo, x="dia", y="qtd",
            markers=True,
            title="Pedidos por Dia",
            labels={"dia": "Data", "qtd": "Pedidos"},
        )
        fig3.update_layout(height=300, margin=dict(t=40, b=10))
        st.plotly_chart(fig3, use_container_width=True)
        st.divider()

    # ── Filtros da tabela ─────────────────────────────────────────────────────
    st.subheader("Lista de Pedidos")

    fc1, fc2, fc3, fc4, fc5, fc6 = st.columns([1, 2, 2, 2, 2, 1])
    with fc1:
        f_id = st.text_input("ID Pedido", placeholder="Ex: 2536")
    with fc2:
        f_data = st.date_input("Data", value=None, key="f_data_tab")
    with fc3:
        tipos_tab = ["Todos"] + sorted(df["tipo_pedido"].dropna().unique().tolist())
        f_tipo = st.selectbox("Tipo", tipos_tab, key="f_tipo_tab")
    with fc4:
        status_tab = ["Todos"] + sorted(df["status"].dropna().unique().tolist())
        f_status = st.selectbox("Status", status_tab, key="f_status_tab")
    with fc5:
        vend_tab = sorted(df["vendedor"].dropna().unique().tolist())
        f_vend = st.multiselect("Vendedor", vend_tab, key="f_vend_tab")
    with fc6:
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            "⬇️ CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="pedidos.csv",
            mime="text/csv",
        )

    show = df.copy()
    if f_id:
        show = show[show["id"].astype(str).str.contains(f_id.strip(), case=False, na=False)]
    if f_data:
        show["data"] = pd.to_datetime(show["data"], errors="coerce")
        show = show[show["data"].dt.date == f_data]
    if f_tipo != "Todos":
        show = show[show["tipo_pedido"] == f_tipo]
    if f_status != "Todos":
        show = show[show["status"] == f_status]
    if f_vend:
        show = show[show["vendedor"].isin(f_vend)]

    # formata colunas monetárias
    show_fmt = show.copy()
    if "valor_total" in show_fmt.columns:
        show_fmt["valor_total"] = show_fmt["valor_total"].apply(lambda v: f"R$ {float(v):,.2f}" if pd.notna(v) else "")

    st.dataframe(show_fmt, use_container_width=True, height=420, hide_index=True)
    st.caption(f"Exibindo {len(show):,} de {len(df):,} registros")


# ══════════════════════════════════════════════════════════════════════════════
# ABA 2 — BUSCAR PEDIDO
# ══════════════════════════════════════════════════════════════════════════════
with aba_busca:
    tipo_busca = st.radio(
        "Buscar por",
        ["Número do Pedido", "Código do Produto"],
        horizontal=True,
    )

    st.divider()

    # ── Busca por ID do pedido ────────────────────────────────────────────────
    if tipo_busca == "Número do Pedido":
        st.subheader("Buscar Pedido por ID")
        pid = st.number_input("Número do Pedido", min_value=1, step=1, value=None, placeholder="Digite o ID...")

        if pid:
            try:
                df_ped, df_itens = buscar_pedido_por_id(int(pid))
            except Exception as e:
                st.error(f"Erro ao buscar pedido: {e}")
                st.stop()

            if df_ped.empty:
                st.warning(f"Pedido #{int(pid)} não encontrado.")
            else:
                row = df_ped.iloc[0]

                st.markdown(f"### Pedido #{int(pid)}")

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Status",      str(row.get("status", "-")))
                c2.metric("Tipo",        str(row.get("tipo_pedido", "-")))
                c3.metric("Valor Total", f"R$ {float(row.get('valor_total', 0)):,.2f}")
                c4.metric("Vendedor",    str(row.get("vendedor", "-") or "-"))

                c5, c6, c7 = st.columns(3)
                c5.metric("Data",       str(row.get("data", "-"))[:16] if row.get("data") else "-")
                c6.metric("ID Cliente", str(row.get("id_cliente", "-")))
                c7.metric("ID Rota",    str(row.get("id_rota", "-")))

                if row.get("obs"):
                    st.info(f"Observação: {row['obs']}")
                if pd.notna(row.get("cancelado_em")):
                    st.error(f"Pedido cancelado em: {str(row['cancelado_em'])[:16]}")

                st.divider()
                st.subheader("Itens do Pedido")

                if df_itens.empty:
                    st.info("Nenhum item encontrado para este pedido.")
                else:
                    for col in ["valor_unitario", "valor_total"]:
                        if col in df_itens.columns:
                            df_itens[col] = df_itens[col].apply(
                                lambda v: f"R$ {float(v):,.2f}" if pd.notna(v) else ""
                            )
                    st.dataframe(df_itens, use_container_width=True, hide_index=True)
                    st.caption(f"{len(df_itens)} item(ns)")
        else:
            st.info("Digite o número do pedido acima para consultar.")

    # ── Busca por código do produto ───────────────────────────────────────────
    else:
        st.subheader("Buscar Pedidos por Código do Produto")
        cod = st.text_input("Código do Produto", placeholder="Ex: LDT20.0154")

        if cod:
            try:
                df_prod = buscar_pedidos_por_produto(cod.strip())
            except Exception as e:
                st.error(f"Erro ao buscar produto: {e}")
                st.stop()

            if df_prod.empty:
                st.warning(f"Nenhum pedido encontrado com o código '{cod}'.")
            else:
                # resumo do produto encontrado
                nome = df_prod["nome_produto"].iloc[0]
                cod_real = df_prod["cod_barras"].iloc[0]
                st.success(f"Produto: **{nome}** — Código: `{cod_real}`")

                k1, k2, k3 = st.columns(3)
                k1.metric("Pedidos encontrados", f"{df_prod['id_pedido'].nunique():,}")
                k2.metric("Qtd. total vendida",  f"{df_prod['quantidade'].sum():,.0f}")
                k3.metric("Valor total",          f"R$ {df_prod['valor_item'].sum():,.2f}")

                st.divider()

                # formata colunas
                show_prod = df_prod.copy()
                for col in ["valor_unitario", "valor_item"]:
                    if col in show_prod.columns:
                        show_prod[col] = show_prod[col].apply(
                            lambda v: f"R$ {float(v):,.2f}" if pd.notna(v) else ""
                        )
                if "valor_total" in show_prod.columns:
                    show_prod["valor_total"] = show_prod["valor_total"].apply(
                        lambda v: f"R$ {float(v):,.2f}" if pd.notna(v) else ""
                    )

                st.dataframe(show_prod, use_container_width=True, hide_index=True)
                st.caption(f"{len(show_prod)} linha(s) — {df_prod['id_pedido'].nunique()} pedido(s)")
        else:
            st.info("Digite o código do produto acima para consultar.")


# ══════════════════════════════════════════════════════════════════════════════
# ABA 3 — AJUSTE DE ESTOQUE
# ══════════════════════════════════════════════════════════════════════════════
with aba_ajuste:
    st.subheader("Contagens e Ajustes de Estoque")

    # ── Filtros ───────────────────────────────────────────────────────────────
    fa1, fa2, fa3 = st.columns([2, 2, 2])
    with fa1:
        aj_di = st.date_input("De", value=None, key="aj_ini")
    with fa2:
        aj_df = st.date_input("Até", value=None, key="aj_fim")
    with fa3:
        aj_status = st.selectbox("Status", ["Todos", "FINALIZADA", "EM_ANDAMENTO", "PENDENTE"], key="aj_st")

    @st.cache_data(ttl=60, show_spinner="Carregando contagens...")
    def fetch_contagens(di, df, st_val):
        return load_contagens(
            data_ini=di,
            data_fim=df,
            status=None if st_val == "Todos" else st_val,
        )

    try:
        df_cont = fetch_contagens(aj_di, aj_df, aj_status)
    except Exception as e:
        st.error(f"Erro ao carregar contagens: {e}")
        st.stop()

    # ── KPIs ──────────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total de contagens",    f"{len(df_cont):,}")
    k2.metric("Total de itens",        f"{df_cont['total_itens'].sum():,.0f}")
    k3.metric("Itens com divergência", f"{df_cont['itens_divergentes'].sum():,.0f}")
    saldo = float(df_cont['saldo_ajuste'].sum()) if not df_cont.empty else 0
    k4.metric("Saldo de ajuste",       f"{saldo:+,.0f} un.")

    st.divider()

    # ── Lista de contagens ────────────────────────────────────────────────────
    st.subheader("Lista de Contagens")

    if df_cont.empty:
        st.info("Nenhuma contagem encontrada.")
    else:
        show_cont = df_cont.copy()
        show_cont["saldo_ajuste"] = show_cont["saldo_ajuste"].apply(
            lambda v: f"{float(v):+,.0f}" if pd.notna(v) else "0"
        )
        st.dataframe(show_cont, use_container_width=True, height=280, hide_index=True)

        st.divider()

        # ── Detalhe de uma contagem ───────────────────────────────────────────
        st.subheader("Detalhe da Contagem")

        ids_disponiveis = df_cont["id"].tolist()
        id_sel = st.selectbox(
            "Selecione a contagem",
            ids_disponiveis,
            format_func=lambda x: f"#{x} — {df_cont[df_cont['id']==x]['obs'].values[0] or 'sem obs.'} ({df_cont[df_cont['id']==x]['data'].values[0]})",
        )

        if id_sel:
            @st.cache_data(ttl=60, show_spinner="Carregando itens...")
            def fetch_itens(cid):
                return load_itens_contagem(cid)

            df_itens_cont = fetch_itens(int(id_sel))

            if df_itens_cont.empty:
                st.info("Nenhum item encontrado para esta contagem.")
            else:
                total_itens = len(df_itens_cont)
                com_div     = (df_itens_cont["diferenca"] != 0).sum()
                positivos   = (df_itens_cont["diferenca"] > 0).sum()
                negativos   = (df_itens_cont["diferenca"] < 0).sum()

                d1, d2, d3, d4 = st.columns(4)
                d1.metric("Total de itens",   f"{total_itens:,}")
                d2.metric("Com divergência",  f"{com_div:,}")
                d3.metric("Sobra (física>sistema)", f"{positivos:,}")
                d4.metric("Falta (física<sistema)", f"{negativos:,}")

                # gráfico top divergências
                top = df_itens_cont[df_itens_cont["diferenca"] != 0].head(20).copy()
                if not top.empty:
                    top["cor"] = top["diferenca"].apply(lambda v: "Sobra" if v > 0 else "Falta")
                    fig_div = px.bar(
                        top,
                        x="diferenca",
                        y="nome_produto",
                        orientation="h",
                        color="cor",
                        color_discrete_map={"Sobra": "#27AE60", "Falta": "#E74C3C"},
                        text="diferenca",
                        title="Top divergências (física − sistema)",
                        labels={"diferenca": "Diferença", "nome_produto": "", "cor": ""},
                    )
                    fig_div.update_traces(textposition="outside", texttemplate="%{text:+.0f}")
                    fig_div.update_layout(height=max(300, len(top) * 30), margin=dict(t=40, b=10, l=10, r=80))
                    st.plotly_chart(fig_div, use_container_width=True)

                # tabela detalhada com highlight
                st.subheader("Itens da Contagem")

                busca_item = st.text_input("Buscar produto", placeholder="Nome ou código...", key="busca_item")
                df_show_item = df_itens_cont.copy()
                if busca_item:
                    mask = df_show_item.astype(str).apply(lambda c: c.str.contains(busca_item, case=False, na=False)).any(axis=1)
                    df_show_item = df_show_item[mask]

                def highlight_diff(row):
                    diff = row.get("diferenca", 0)
                    if diff > 0:
                        return ["background-color: #D5F5E3; color: #1A1A1A"] * len(row)
                    if diff < 0:
                        return ["background-color: #FADBD8; color: #1A1A1A"] * len(row)
                    return [""] * len(row)

                styled_itens = df_show_item.style.apply(highlight_diff, axis=1)
                st.dataframe(styled_itens, use_container_width=True, height=420, hide_index=True)
                st.caption(
                    f"Exibindo {len(df_show_item):,} de {total_itens:,} itens  |  "
                    "Verde = sobra · Vermelho = falta"
                )
