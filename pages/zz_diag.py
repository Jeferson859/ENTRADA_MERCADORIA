# encoding: utf-8
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from db import _query

st.set_page_config(page_title="Diag", layout="wide")
st.title("Última entrada FINALIZADA — Mato Grosso")

st.header("Últimas 10 entradas EXECUTADA de Mato Grosso")
try:
    st.table(_query(
        """
        SELECT e.id,
               e.data,
               e.status,
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
        GROUP BY e.id, e.data, e.status, e.tipo, e.qtd_nf
        ORDER BY e.data DESC
        LIMIT 10
        """
    ))
except Exception as e:
    st.error(str(e))
