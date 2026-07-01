# encoding: utf-8
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from db import _query

st.set_page_config(page_title="Diag", layout="wide")
st.title("Diagnóstico — produtos hoje")

st.header("0. Data do servidor")
try:
    st.table(_query("SELECT CURRENT_DATE AS hoje, NOW() AS agora"))
except Exception as e:
    st.error(str(e))

st.header("A. Total de produtos cadastrados")
try:
    st.table(_query("SELECT COUNT(*) AS total_produtos FROM produto"))
except Exception as e:
    st.error(str(e))

st.header("B. Entradas de mercadoria HOJE — contagem e itens")
try:
    st.table(_query(
        """
        SELECT COUNT(DISTINCT e.id)            AS entradas,
               COUNT(i.id)                     AS linhas_itens,
               COUNT(DISTINCT i.id_produto)    AS produtos_distintos,
               COALESCE(SUM(i.quantidade), 0)  AS soma_quantidade
        FROM entrada_estoque e
        LEFT JOIN entrada_estoque_item i ON i.id_entrada = e.id
        WHERE e.data::date = CURRENT_DATE
        """
    ))
except Exception as e:
    st.error(str(e))

st.header("C. Entradas de HOJE por empresa")
try:
    st.table(_query(
        """
        SELECT em.nome_empresa,
               COUNT(DISTINCT e.id)            AS entradas,
               COUNT(DISTINCT i.id_produto)    AS produtos_distintos,
               COALESCE(SUM(i.quantidade), 0)  AS soma_quantidade
        FROM entrada_estoque e
        JOIN empresa em ON em.id_empresa = e.id_empresa
        LEFT JOIN entrada_estoque_item i ON i.id_entrada = e.id
        WHERE e.data::date = CURRENT_DATE
        GROUP BY em.nome_empresa
        ORDER BY entradas DESC
        """
    ))
except Exception as e:
    st.error(str(e))

st.header("D. Últimas datas com entrada (referência)")
try:
    st.table(_query(
        """
        SELECT e.data::date AS dia,
               COUNT(DISTINCT e.id) AS entradas,
               COALESCE(SUM(i.quantidade), 0) AS soma_quantidade
        FROM entrada_estoque e
        LEFT JOIN entrada_estoque_item i ON i.id_entrada = e.id
        GROUP BY e.data::date
        ORDER BY dia DESC
        LIMIT 7
        """
    ))
except Exception as e:
    st.error(str(e))
