# encoding: utf-8
"""Custos & Margem por região — exclusiva do administrador.

Custos por produto × estado (GO, TO, PA, MT) vindos da planilha de custos.
Aba 1: margem REAL (vendas × custo da UF do cliente).
Aba 2: tabela de custos/preços por região.
Aba 3: importação da planilha (mesmo layout da planilha de custos).

Requisito: rodar scripts/custo_regiao.sql e a carga inicial no banco.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

st.set_page_config(page_title="Custos & Margem", page_icon="💰", layout="wide")

import pandas as pd

import auth
import nav
from db import (importar_custos_regiao, load_custos_regiao,
                load_margem_por_uf, load_margem_regiao)

auth.exigir_admin()
nav.render("Custos")

UFS = ["GO", "TO", "PA", "MT"]

st.markdown(
    """
    <div style="display:flex;align-items:center;gap:14px;margin:.1rem 0 1rem">
      <div style="width:46px;height:46px;border-radius:13px;background:linear-gradient(150deg,#2E7CF6,#00D4FF);display:flex;align-items:center;justify-content:center;font-size:23px">💰</div>
      <div>
        <div style="font-size:21px;font-weight:800;color:#F2F6FC">Custos &amp; Margem por região</div>
        <div style="font-size:12px;color:#6B7385">GO · TO · PA · MT — margem real das vendas e tabela de custos por estado</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_real, tab_tabela, tab_imp = st.tabs(
    ["📈 Margem real por região", "🗺️ Tabela de custos", "📥 Importar planilha"])

# ── Aba 1: margem real ────────────────────────────────────────────────────────
with tab_real:
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        data_ini = st.date_input("De", value=None, key="mr_ini")
    with f2:
        data_fim = st.date_input("Até", value=None, key="mr_fim")
    with f3:
        uf_sel = st.selectbox("Estado", ["(todos)"] + UFS + ["Outro"], key="mr_uf")
    with f4:
        tipo = st.selectbox("Tipo de pedido", ["(todos)", "PRE-VENDA", "BRINDE", "REPOSICAO"], key="mr_tipo")

    try:
        df = load_margem_regiao(
            data_ini or None, data_fim or None,
            uf=None if uf_sel == "(todos)" else uf_sel,
            tipo_pedido=None if tipo == "(todos)" else tipo,
        )
    except Exception as e:
        st.error(f"Erro ao consultar: {e}\n\nRode **scripts/custo_regiao.sql** no banco se ainda não rodou.")
        st.stop()

    if df.empty:
        st.info("Nenhuma venda no período/filtro selecionado.")
    else:
        fat = float(df["faturamento"].sum())
        custo = float(df["custo_total"].fillna(0).sum())
        lucro = float(df["lucro"].sum())
        margem = (100 * lucro / fat) if fat else 0

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Faturamento", f"R$ {fat:,.2f}")
        k2.metric("Custo", f"R$ {custo:,.2f}")
        k3.metric("Lucro bruto", f"R$ {lucro:,.2f}")
        k4.metric("Margem", f"{margem:.1f}%")

        sem = int(df["sem_custo"].sum())
        if sem:
            st.warning(f"⚠️ {sem} linha(s) produto×estado **sem custo cadastrado** — "
                       "o lucro delas aparece igual ao faturamento. Importe/atualize a planilha na aba 📥.")

        if uf_sel == "(todos)":
            st.subheader("Resumo por estado")
            try:
                resumo = load_margem_por_uf(data_ini or None, data_fim or None,
                                            tipo_pedido=None if tipo == "(todos)" else tipo)
                st.dataframe(
                    resumo.rename(columns={
                        "uf": "UF", "faturamento": "Faturamento (R$)",
                        "custo_total": "Custo (R$)", "lucro": "Lucro (R$)",
                        "margem_pct": "Margem %", "produtos_sem_custo": "Produtos sem custo",
                    }),
                    use_container_width=True, hide_index=True,
                )
            except Exception:
                pass

        st.subheader("Margem por produto × estado")
        st.dataframe(
            df.rename(columns={
                "produto": "Produto", "uf": "UF", "quantidade": "Qtd",
                "faturamento": "Faturamento (R$)", "custo_total": "Custo (R$)",
                "lucro": "Lucro (R$)", "margem_pct": "Margem %", "sem_custo": "Sem custo?",
            }),
            use_container_width=True, hide_index=True,
        )

        st.subheader("Top 15 — lucro")
        top = df.dropna(subset=["lucro"]).head(15)
        st.bar_chart(top.assign(rotulo=top["produto"] + " (" + top["uf"] + ")")
                        .set_index("rotulo")["lucro"])

# ── Aba 2: tabela de custos ───────────────────────────────────────────────────
with tab_tabela:
    try:
        tab = load_custos_regiao()
    except Exception as e:
        st.error(f"Erro ao carregar: {e}\n\nRode **scripts/custo_regiao.sql** no banco.")
        st.stop()

    if tab.empty:
        st.info("Nenhum custo importado ainda — use a aba 📥 Importar planilha.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Produtos com custo", tab["codigo"].nunique())
        c2.metric("Registros produto × UF", len(tab))
        c3.metric("Não casados com o cadastro", int(tab["nome_produto"].isna().sum()))
        if tab["nome_produto"].isna().any():
            st.caption("⚠️ 'Não casados' = código da planilha não encontrado em produto.cod_barras. "
                       "Esses produtos não entram na margem real.")

        busca = st.text_input("🔍 Filtrar por código, produto ou fornecedor", key="tb_busca")
        exibir = tab
        if busca:
            m = (tab["codigo"].str.contains(busca, case=False, na=False)
                 | tab["nome_produto"].str.contains(busca, case=False, na=False)
                 | tab["fornecedor"].str.contains(busca, case=False, na=False))
            exibir = tab[m]

        piv = exibir.pivot_table(index=["codigo", "nome_produto", "fornecedor"],
                                 columns="uf", values=["custo", "valor_venda"], aggfunc="first")
        piv.columns = [f"{a}_{b}" for a, b in piv.columns]
        st.dataframe(piv.reset_index(), use_container_width=True, hide_index=True)

        st.subheader("Margem de tabela média por estado")
        med = (exibir.dropna(subset=["margem_tabela_pct"])
                     .groupby("uf")["margem_tabela_pct"].mean().round(1))
        st.bar_chart(med)

# ── Aba 3: importar planilha ──────────────────────────────────────────────────
with tab_imp:
    st.caption(
        "Envie a planilha no mesmo layout da planilha de custos: colunas "
        "**CÓDIGO, PRODUTO, FORNECEDOR, CUSTOS - GO, VL. VENDA-GO, ... TO, PA, MT**. "
        "Registros existentes são atualizados (código + UF)."
    )
    arq = st.file_uploader("Planilha de custos (.xlsx)", type=["xlsx"], key="imp_arq")

    def _num(v):
        if pd.isna(v):
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = re.sub(r"[R$\s]", "", str(v))
        if s in ("", "-", "--"):
            return None
        s = s.replace(".", "").replace(",", ".") if "," in s else s.replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    if arq is not None:
        try:
            plan = pd.read_excel(arq)
        except Exception as e:
            st.error(f"Não consegui ler o arquivo: {e}")
            st.stop()

        obrig = ["CÓDIGO", "PRODUTO", "FORNECEDOR"]
        faltando = [c for c in obrig if c not in plan.columns]
        pares = []
        for uf in UFS:
            ccol, vcol = f"CUSTOS - {uf}", f"VL. VENDA-{uf}"
            if ccol in plan.columns and vcol in plan.columns:
                pares.append((uf, ccol, vcol))
        if faltando or not pares:
            st.error(f"Layout inesperado. Faltando: {faltando or 'colunas de custo/venda por UF'}.")
            st.stop()

        registros = []
        for _, r in plan.iterrows():
            if pd.isna(r["CÓDIGO"]):
                continue
            forn = str(r["FORNECEDOR"]).strip() if pd.notna(r["FORNECEDOR"]) else None
            for uf, ccol, vcol in pares:
                c, v = _num(r[ccol]), _num(r[vcol])
                if c is None and v is None:
                    continue
                registros.append({"codigo": str(r["CÓDIGO"]).strip(), "uf": uf,
                                  "custo": c, "valor_venda": v, "fornecedor": forn})

        st.info(f"Prévia: **{len(registros)}** registros produto × UF "
                f"({plan['CÓDIGO'].nunique()} produtos, estados: {', '.join(u for u, _, _ in pares)}).")
        st.dataframe(pd.DataFrame(registros).head(12), use_container_width=True, hide_index=True)

        if st.button("📥 Importar para o banco", type="primary", key="btn_imp"):
            try:
                with st.spinner("Importando..."):
                    n = importar_custos_regiao(registros)
                st.success(f"{n} registros importados/atualizados.")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Erro na importação: {e}\n\nRode **scripts/custo_regiao.sql** no banco primeiro.")
