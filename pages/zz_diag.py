# encoding: utf-8
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from db import _query

st.set_page_config(page_title="Diag", layout="wide")
st.title("Diagnóstico de schema (temporário)")

st.header("A. Colunas de entrada_estoque")
try:
    st.table(_query(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name='entrada_estoque' ORDER BY ordinal_position"
    ))
except Exception as e:
    st.error(str(e))

st.header("B. Colunas de entrada_estoque_item")
try:
    st.table(_query(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name='entrada_estoque_item' ORDER BY ordinal_position"
    ))
except Exception as e:
    st.error(str(e))

st.header("C. Colunas com 'rfid' em qualquer tabela")
try:
    st.table(_query(
        "SELECT table_name, column_name, data_type FROM information_schema.columns "
        "WHERE column_name ILIKE '%rfid%' ORDER BY table_name, ordinal_position"
    ))
except Exception as e:
    st.error(str(e))

st.header("D. entrada_estoque.tipo — distribuição")
try:
    st.table(_query(
        "SELECT tipo, COUNT(*) AS qtd FROM entrada_estoque GROUP BY tipo ORDER BY qtd DESC"
    ))
except Exception as e:
    st.error(str(e))
