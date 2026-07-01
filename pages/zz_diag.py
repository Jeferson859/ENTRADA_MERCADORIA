# encoding: utf-8
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from db import _query

st.set_page_config(page_title="Diag", layout="wide")
st.title("Diagnóstico — entradas RFID")

st.header("A. Todas as colunas de entrada_estoque")
try:
    st.table(_query(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name='entrada_estoque' ORDER BY ordinal_position"
    ))
except Exception as e:
    st.error(str(e))

st.header("B. status × tipo (todas empresas)")
try:
    st.table(_query(
        "SELECT tipo, status, COUNT(*) AS qtd FROM entrada_estoque "
        "GROUP BY tipo, status ORDER BY tipo, qtd DESC"
    ))
except Exception as e:
    st.error(str(e))

st.header("C. entradas RFID em Matriz(5) e Goiás(1) — por empresa e status")
try:
    st.table(_query(
        "SELECT e.id_empresa, em.nome_empresa, e.status, COUNT(*) AS qtd "
        "FROM entrada_estoque e JOIN empresa em ON em.id_empresa = e.id_empresa "
        "WHERE e.tipo='RFID' AND e.id_empresa IN (1,5) "
        "GROUP BY e.id_empresa, em.nome_empresa, e.status ORDER BY e.id_empresa, qtd DESC"
    ))
except Exception as e:
    st.error(str(e))

st.header("D. Total entradas RFID por empresa (todas)")
try:
    st.table(_query(
        "SELECT em.nome_empresa, COUNT(*) AS qtd "
        "FROM entrada_estoque e JOIN empresa em ON em.id_empresa = e.id_empresa "
        "WHERE e.tipo='RFID' GROUP BY em.nome_empresa ORDER BY qtd DESC"
    ))
except Exception as e:
    st.error(str(e))

st.header("E. Amostra de obs/status das entradas RFID (procurar 'produção')")
try:
    st.table(_query(
        "SELECT DISTINCT status FROM entrada_estoque ORDER BY status"
    ))
except Exception as e:
    st.error(str(e))
