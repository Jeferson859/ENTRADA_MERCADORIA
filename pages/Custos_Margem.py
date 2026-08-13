# encoding: utf-8
"""Custos & Margem por região — exclusiva do administrador.

Os custos por produto × estado (GO, TO, PA, MT) vivem em dados/custos.csv,
DENTRO do repositório — nada é criado ou alterado no banco de dados.
O banco recebe apenas UMA consulta de leitura (vendas por produto × UF);
o cruzamento com o custo é feito aqui, em pandas.

Para atualizar os custos: substitua dados/custos.csv no GitHub
(gerado a partir da planilha de custos).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

st.set_page_config(page_title="Custos & Margem", page_icon="💰", layout="wide")

import pandas as pd

import auth
import nav
from db import load_vendas_produto_uf

auth.exigir_admin()
nav.render("Custos")

UFS = ["GO", "TO", "PA", "MT"]
_CSV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "dados", "custos.csv")

st.markdown(
    """
    <div style="display:flex;align-items:center;gap:14px;margin:.1rem 0 1rem">
      <div style="width:46px;height:46px;border-radius:13px;background:linear-gradient(150deg,#2E7CF6,#00D4FF);display:flex;align-items:center;justify-content:center;font-size:23px">💰</div>
      <div>
        <div style="font-size:21px;font-weight:800;color:#F2F6FC">Custos &amp; Margem por região</div>
        <div style="font-size:12px;color:#6B7385">GO · TO · PA · MT — custos do repositório (dados/custos.csv) · banco somente leitura</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def carregar_custos() -> pd.DataFrame:
    df = pd.read_csv(_CSV, dtype={"codigo": str, "uf": str})
    df["codigo"] = df["codigo"].str.strip()
    return df


try:
    custos = carregar_custos()
except Exception as e:
    st.error(f"Não consegui ler dados/custos.csv do repositório: {e}")
    st.stop()

tab_real, tab_tabela = st.tabs(["📈 Margem real por região", "🗺️ Tabela de custos"])

# ── Aba 1: margem real (vendas do banco × custo do CSV) ───────────────────────
with tab_real:
    f1, f2, f3 = st.columns(3)
    with f1:
        data_ini = st.date_input("De", value=None, key="mr_ini")
    with f2:
        data_fim = st.date_input("Até", value=None, key="mr_fim")
    with f3:
        tipo = st.selectbox("Tipo de pedido", ["(todos)", "PRE-VENDA", "BRINDE", "REPOSICAO"], key="mr_tipo")

    @st.cache_data(ttl=300, show_spinner="Consultando vendas (somente leitura)...")
    def carregar_vendas(d1, d2, tp):
        return load_vendas_produto_uf(d1, d2, tipo_pedido=tp)

    try:
        vendas = carregar_vendas(data_ini or None, data_fim or None,
                                 None if tipo == "(todos)" else tipo)
    except Exception as e:
        st.error(f"Erro na consulta de vendas: {e}")
        st.stop()

    if vendas.empty:
        st.info("Nenhuma venda no período selecionado.")
        st.stop()

    vendas["codigo"] = vendas["codigo"].astype(str).str.strip()
    df = vendas.merge(custos[["codigo", "uf", "custo"]], on=["codigo", "uf"], how="left")
    df["custo_total"] = (df["quantidade"] * df["custo"]).round(2)
    df["lucro"] = (df["faturamento"] - df["custo_total"].fillna(0)).round(2)
    df["margem_pct"] = (100 * df["lucro"] / df["faturamento"].replace(0, pd.NA)).round(1)
    df["sem_custo"] = df["custo"].isna()
    df = df.sort_values("lucro", ascending=False)

    uf_sel = st.selectbox("Estado", ["(todos)"] + UFS + ["Outro"], key="mr_uf")
    exibir = df if uf_sel == "(todos)" else df[df["uf"] == uf_sel]

    fat = float(exibir["faturamento"].sum())
    custo_t = float(exibir["custo_total"].fillna(0).sum())
    lucro = float(exibir["lucro"].sum())
    margem = (100 * lucro / fat) if fat else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Faturamento", f"R$ {fat:,.2f}")
    k2.metric("Custo", f"R$ {custo_t:,.2f}")
    k3.metric("Lucro bruto", f"R$ {lucro:,.2f}")
    k4.metric("Margem", f"{margem:.1f}%")

    sem = int(exibir["sem_custo"].sum())
    if sem:
        st.warning(f"⚠️ {sem} linha(s) produto×estado sem custo no CSV (inclui vendas de "
                   "clientes com CEP fora de GO/TO/PA/MT, que caem em 'Outro'). "
                   "O lucro dessas linhas aparece igual ao faturamento.")

    if uf_sel == "(todos)":
        st.subheader("Resumo por estado")
        res = (df.groupby("uf", as_index=False)
                 .agg(faturamento=("faturamento", "sum"),
                      custo=("custo_total", "sum"),
                      lucro=("lucro", "sum"),
                      sem_custo=("sem_custo", "sum")))
        res["margem_pct"] = (100 * res["lucro"] / res["faturamento"].replace(0, pd.NA)).round(1)
        st.dataframe(
            res.rename(columns={"uf": "UF", "faturamento": "Faturamento (R$)",
                                "custo": "Custo (R$)", "lucro": "Lucro (R$)",
                                "margem_pct": "Margem %", "sem_custo": "Linhas sem custo"}),
            use_container_width=True, hide_index=True,
        )

    st.subheader("Margem por produto × estado")
    st.dataframe(
        exibir.drop(columns=["custo"]).rename(columns={
            "codigo": "Código", "produto": "Produto", "uf": "UF",
            "quantidade": "Qtd", "faturamento": "Faturamento (R$)",
            "custo_total": "Custo (R$)", "lucro": "Lucro (R$)",
            "margem_pct": "Margem %", "sem_custo": "Sem custo?"}),
        use_container_width=True, hide_index=True,
    )

    st.subheader("Top 15 — lucro")
    top = exibir.dropna(subset=["lucro"]).head(15)
    st.bar_chart(top.assign(rotulo=top["produto"].str.slice(0, 30) + " (" + top["uf"] + ")")
                    .set_index("rotulo")["lucro"])

# ── Aba 2: tabela de custos (só o CSV, sem banco) ─────────────────────────────
with tab_tabela:
    c1, c2, c3 = st.columns(3)
    c1.metric("Produtos", custos["codigo"].nunique())
    c2.metric("Registros produto × UF", len(custos))
    c3.metric("Fornecedores", custos["fornecedor"].nunique())

    busca = st.text_input("🔍 Filtrar por código, produto ou fornecedor", key="tb_busca")
    exibir = custos
    if busca:
        m = (custos["codigo"].str.contains(busca, case=False, na=False)
             | custos["produto"].str.contains(busca, case=False, na=False)
             | custos["fornecedor"].str.contains(busca, case=False, na=False))
        exibir = custos[m]

    piv = exibir.pivot_table(index=["codigo", "produto", "fornecedor"],
                             columns="uf", values=["custo", "valor_venda"], aggfunc="first")
    piv.columns = [f"{a}_{b}" for a, b in piv.columns]
    st.dataframe(piv.reset_index(), use_container_width=True, hide_index=True)

    st.subheader("Margem de tabela média por estado")
    aux = exibir.dropna(subset=["custo", "valor_venda"]).copy()
    aux = aux[aux["valor_venda"] > 0]
    aux["margem_tabela_pct"] = 100 * (aux["valor_venda"] - aux["custo"]) / aux["valor_venda"]
    st.bar_chart(aux.groupby("uf")["margem_tabela_pct"].mean().round(1))

    st.caption("Para atualizar os custos, substitua **dados/custos.csv** no GitHub "
               "(me mande a planilha nova que eu gero e subo o arquivo).")
