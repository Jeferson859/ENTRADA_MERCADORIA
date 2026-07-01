# encoding: utf-8
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from db import _query

st.set_page_config(page_title="Diag", layout="wide")
st.title("Entradas FINALIZADAS (EXECUTADA) — ontem e hoje")

st.header("Resumo por dia")
try:
    st.table(_query(
        """
        SELECT CASE WHEN e.data::date = CURRENT_DATE THEN 'HOJE (' || CURRENT_DATE || ')'
                    ELSE 'ONTEM (' || (CURRENT_DATE - 1) || ')' END AS dia,
               COUNT(DISTINCT e.id)            AS entradas,
               COUNT(DISTINCT i.id_produto)    AS produtos_distintos,
               COALESCE(SUM(i.quantidade), 0)  AS unidades
        FROM entrada_estoque e
        LEFT JOIN entrada_estoque_item i ON i.id_entrada = e.id
        WHERE e.status = 'EXECUTADA'
          AND e.data::date IN (CURRENT_DATE, CURRENT_DATE - 1)
        GROUP BY 1
        ORDER BY 1 DESC
        """
    ))
except Exception as e:
    st.error(str(e))

st.header("HOJE — finalizadas por empresa")
try:
    st.table(_query(
        """
        SELECT em.nome_empresa,
               COUNT(DISTINCT e.id)            AS entradas,
               COUNT(DISTINCT i.id_produto)    AS produtos_distintos,
               COALESCE(SUM(i.quantidade), 0)  AS unidades
        FROM entrada_estoque e
        JOIN empresa em ON em.id_empresa = e.id_empresa
        LEFT JOIN entrada_estoque_item i ON i.id_entrada = e.id
        WHERE e.status = 'EXECUTADA' AND e.data::date = CURRENT_DATE
        GROUP BY em.nome_empresa ORDER BY entradas DESC
        """
    ))
except Exception as e:
    st.error(str(e))

st.header("ONTEM — finalizadas por empresa")
try:
    st.table(_query(
        """
        SELECT em.nome_empresa,
               COUNT(DISTINCT e.id)            AS entradas,
               COUNT(DISTINCT i.id_produto)    AS produtos_distintos,
               COALESCE(SUM(i.quantidade), 0)  AS unidades
        FROM entrada_estoque e
        JOIN empresa em ON em.id_empresa = e.id_empresa
        LEFT JOIN entrada_estoque_item i ON i.id_entrada = e.id
        WHERE e.status = 'EXECUTADA' AND e.data::date = CURRENT_DATE - 1
        GROUP BY em.nome_empresa ORDER BY entradas DESC
        """
    ))
except Exception as e:
    st.error(str(e))
