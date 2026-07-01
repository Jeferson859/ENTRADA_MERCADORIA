# encoding: utf-8
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from db import _query

st.set_page_config(page_title="Diag", layout="wide")
st.title("Mato Grosso — entradas FINALIZADAS de HOJE")

st.header("Todas as entradas EXECUTADA de hoje")
try:
    df = _query(
        """
        SELECT e.id,
               e.data,
               e.tipo,
               e.qtd_nf,
               COUNT(i.id)                    AS itens,
               COUNT(DISTINCT i.id_produto)   AS produtos,
               COALESCE(SUM(i.quantidade), 0) AS unidades
        FROM entrada_estoque e
        JOIN empresa em ON em.id_empresa = e.id_empresa
        LEFT JOIN entrada_estoque_item i ON i.id_entrada = e.id
        WHERE em.nome_empresa = 'MATO GROSSO'
          AND e.status = 'EXECUTADA'
          AND e.data::date = CURRENT_DATE
        GROUP BY e.id, e.data, e.tipo, e.qtd_nf
        ORDER BY e.data DESC
        """
    )
    st.caption(f"{len(df)} entradas · {int(df['unidades'].sum())} unidades no total")
    st.table(df)
except Exception as e:
    st.error(str(e))
