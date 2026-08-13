# encoding: utf-8
"""Custos & Margem por região — exclusiva do administrador.

Os custos por produto × estado (GO, TO, PA, MT) vivem em dados/custos.csv,
DENTRO do repositório — nada é criado ou alterado no banco de dados.
O banco recebe apenas UMA consulta de leitura (vendas por produto × UF);
o cruzamento com o custo é feito aqui, em pandas.

CASAMENTO DE CÓDIGOS
--------------------
O código do banco (produto.cod_barras) casa com a coluna CÓDIGO da planilha.
Produtos com prefixo **LD** são itens COM DEFEITO: têm o mesmo custo do
produto original, mas costumam ser vendidos mais barato. Por isso o
cruzamento é feito em cascata:
  1) casamento exato do código;
  2) se não casar e o código começar com LD, tenta o código sem o LD
     (só aceita se esse código base existir na planilha — nunca inventa par).
A aba "Diagnóstico" mostra exatamente o que casou e o que não casou.
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
        <div style="font-size:12px;color:#6B7385">GO · TO · PA · MT — custos do repositório (dados/custos.csv) · banco somente leitura · itens LD = com defeito</div>
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

_CODIGOS_BASE = set(custos["codigo"].unique())


def _resolver_codigo(cod: str):
    """Devolve (codigo_para_casar, eh_defeito).

    Itens com prefixo LD são produtos com defeito: usam o custo do código
    base. Só remove o LD se o código resultante existir na planilha.
    """
    c = str(cod).strip()
    if c in _CODIGOS_BASE:
        return c, False
    if c.upper().startswith("LD"):
        resto = c[2:]
        if resto in _CODIGOS_BASE:
            return resto, True
    return c, False


tab_real, tab_tabela, tab_diag = st.tabs(
    ["📈 Margem real por região", "🗺️ Tabela de custos", "🔎 Diagnóstico"])


@st.cache_data(ttl=300, show_spinner="Consultando vendas (somente leitura)...")
def carregar_vendas(d1, d2, tp):
    return load_vendas_produto_uf(d1, d2, tipo_pedido=tp)


def preparar(vendas: pd.DataFrame) -> pd.DataFrame:
    """Cruza vendas × custos aplicando a regra do prefixo LD."""
    v = vendas.copy()
    v["codigo"] = v["codigo"].astype(str).str.strip()
    resolvido = v["codigo"].map(_resolver_codigo)
    v["codigo_custo"] = [r[0] for r in resolvido]
    v["defeito"] = [r[1] for r in resolvido]
    df = v.merge(custos[["codigo", "uf", "custo"]],
                 left_on=["codigo_custo", "uf"], right_on=["codigo", "uf"],
                 how="left", suffixes=("", "_csv"))
    df = df.drop(columns=[c for c in ["codigo_csv"] if c in df.columns])
    df["custo_total"] = (df["quantidade"] * df["custo"]).round(2)
    df["lucro"] = (df["faturamento"] - df["custo_total"].fillna(0)).round(2)
    df["margem_pct"] = (100 * df["lucro"] / df["faturamento"].replace(0, pd.NA)).round(1)
    df["sem_custo"] = df["custo"].isna()
    return df.sort_values("lucro", ascending=False)


# ── filtros compartilhados ────────────────────────────────────────────────────
f1, f2, f3 = st.columns(3)
with f1:
    data_ini = st.date_input("De", value=None, key="mr_ini")
with f2:
    data_fim = st.date_input("Até", value=None, key="mr_fim")
with f3:
    tipo = st.selectbox("Tipo de pedido", ["(todos)", "PRE-VENDA", "BRINDE", "REPOSICAO"], key="mr_tipo")

try:
    vendas = carregar_vendas(data_ini or None, data_fim or None,
                             None if tipo == "(todos)" else tipo)
except Exception as e:
    st.error(f"Erro na consulta de vendas: {e}")
    st.stop()

if vendas.empty:
    st.info("Nenhuma venda no período selecionado.")
    st.stop()

df = preparar(vendas)

# ── Aba 1: margem real ────────────────────────────────────────────────────────
with tab_real:
    c1, c2 = st.columns(2)
    with c1:
        uf_sel = st.selectbox("Estado", ["(todos)"] + UFS + ["Outro"], key="mr_uf")
    with c2:
        filtro_def = st.radio("Itens", ["Todos", "Só normais", "Só com defeito (LD)"],
                              horizontal=True, key="mr_def")

    exibir = df if uf_sel == "(todos)" else df[df["uf"] == uf_sel]
    if filtro_def == "Só normais":
        exibir = exibir[~exibir["defeito"]]
    elif filtro_def == "Só com defeito (LD)":
        exibir = exibir[exibir["defeito"]]

    if exibir.empty:
        st.info("Nada encontrado com esses filtros.")
    else:
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
            fat_sem = float(exibir.loc[exibir["sem_custo"], "faturamento"].sum())
            st.warning(
                f"⚠️ {sem} de {len(exibir)} linhas sem custo (R$ {fat_sem:,.2f} de faturamento). "
                "O lucro delas aparece igual ao faturamento, inflando o total. "
                "Veja a aba 🔎 Diagnóstico."
            )

        # comparativo normal × defeito
        if filtro_def == "Todos" and df["defeito"].any():
            st.subheader("Normal × Com defeito (LD)")
            comp = (exibir.assign(tipo_item=exibir["defeito"].map({False: "Normal", True: "Com defeito (LD)"}))
                          .groupby("tipo_item", as_index=False)
                          .agg(itens=("codigo", "count"),
                               qtd=("quantidade", "sum"),
                               faturamento=("faturamento", "sum"),
                               custo=("custo_total", "sum"),
                               lucro=("lucro", "sum")))
            comp["margem_pct"] = (100 * comp["lucro"] / comp["faturamento"].replace(0, pd.NA)).round(1)
            comp["preco_medio"] = (comp["faturamento"] / comp["qtd"].replace(0, pd.NA)).round(2)
            st.dataframe(
                comp.rename(columns={"tipo_item": "Tipo", "itens": "Linhas", "qtd": "Qtd",
                                     "faturamento": "Faturamento (R$)", "custo": "Custo (R$)",
                                     "lucro": "Lucro (R$)", "margem_pct": "Margem %",
                                     "preco_medio": "Preço médio (R$)"}),
                use_container_width=True, hide_index=True,
            )
            st.caption("Itens LD têm o mesmo custo do produto original — a diferença de margem "
                       "mostra quanto o defeito custa ao negócio.")

        if uf_sel == "(todos)":
            st.subheader("Resumo por estado")
            res = (exibir.groupby("uf", as_index=False)
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
            exibir[["codigo", "produto", "uf", "defeito", "quantidade", "faturamento",
                    "custo_total", "lucro", "margem_pct", "sem_custo"]].rename(columns={
                "codigo": "Código", "produto": "Produto", "uf": "UF", "defeito": "Defeito (LD)?",
                "quantidade": "Qtd", "faturamento": "Faturamento (R$)",
                "custo_total": "Custo (R$)", "lucro": "Lucro (R$)",
                "margem_pct": "Margem %", "sem_custo": "Sem custo?"}),
            use_container_width=True, hide_index=True,
        )

        st.subheader("Top 15 — lucro")
        top = exibir.dropna(subset=["lucro"]).head(15)
        st.bar_chart(top.assign(rotulo=top["produto"].str.slice(0, 28) + " (" + top["uf"] + ")")
                        .set_index("rotulo")["lucro"])

# ── Aba 2: tabela de custos (só o CSV, sem banco) ─────────────────────────────
with tab_tabela:
    c1, c2, c3 = st.columns(3)
    c1.metric("Produtos", custos["codigo"].nunique())
    c2.metric("Registros produto × UF", len(custos))
    c3.metric("Fornecedores", custos["fornecedor"].nunique())

    busca = st.text_input("🔍 Filtrar por código, produto ou fornecedor", key="tb_busca")
    vis = custos
    if busca:
        m = (custos["codigo"].str.contains(busca, case=False, na=False)
             | custos["produto"].str.contains(busca, case=False, na=False)
             | custos["fornecedor"].str.contains(busca, case=False, na=False))
        vis = custos[m]

    piv = vis.pivot_table(index=["codigo", "produto", "fornecedor"],
                          columns="uf", values=["custo", "valor_venda"], aggfunc="first")
    piv.columns = [f"{a}_{b}" for a, b in piv.columns]
    st.dataframe(piv.reset_index(), use_container_width=True, hide_index=True)

    st.subheader("Margem de tabela média por estado")
    aux = vis.dropna(subset=["custo", "valor_venda"]).copy()
    aux = aux[aux["valor_venda"] > 0]
    aux["margem_tabela_pct"] = 100 * (aux["valor_venda"] - aux["custo"]) / aux["valor_venda"]
    st.bar_chart(aux.groupby("uf")["margem_tabela_pct"].mean().round(1))

    st.caption("Para atualizar os custos, substitua **dados/custos.csv** no GitHub.")

# ── Aba 3: diagnóstico do casamento ───────────────────────────────────────────
with tab_diag:
    st.caption("Confere se os códigos vendidos no período encontraram custo na planilha.")

    prod = df.drop_duplicates(subset=["codigo"])
    total = len(prod)
    casou_exato = int((~prod["sem_custo"] & ~prod["defeito"]).sum())
    casou_ld = int((~prod["sem_custo"] & prod["defeito"]).sum())
    nao_casou = int(prod["sem_custo"].sum())

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Produtos vendidos", total)
    d2.metric("Casaram direto", casou_exato)
    d3.metric("Casaram via LD", casou_ld)
    d4.metric("Sem custo", nao_casou,
              delta=f"{100*nao_casou/total:.0f}%" if total else None,
              delta_color="inverse")

    if nao_casou:
        st.subheader("Produtos vendidos SEM custo na planilha")
        st.caption("Ordenados por faturamento — os de cima são os que mais distorcem o resultado. "
                   "Linhas com UF 'Outro' são clientes com CEP fora de GO/TO/PA/MT.")
        faltantes = (df[df["sem_custo"]]
                     .groupby(["codigo", "produto", "uf"], as_index=False)
                     .agg(qtd=("quantidade", "sum"), faturamento=("faturamento", "sum"))
                     .sort_values("faturamento", ascending=False))
        st.dataframe(
            faltantes.rename(columns={"codigo": "Código", "produto": "Produto", "uf": "UF",
                                      "qtd": "Qtd", "faturamento": "Faturamento (R$)"}),
            use_container_width=True, hide_index=True,
        )
        st.download_button(
            "⬇️ Baixar lista em CSV",
            faltantes.to_csv(index=False).encode("utf-8"),
            file_name="produtos_sem_custo.csv", mime="text/csv",
        )
    else:
        st.success("Todos os produtos vendidos no período têm custo cadastrado.")
