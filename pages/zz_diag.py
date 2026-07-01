# encoding: utf-8
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from db import _query

st.set_page_config(page_title="Diag", layout="wide")
st.title("Diagnóstico de schema (temporário)")

st.header("1. Tabelas (public)")
try:
    st.dataframe(_query(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' ORDER BY table_name"
    ), use_container_width=True, height=400)
except Exception as e:
    st.error(str(e))

st.header("2. Colunas de RFID / tag / entrada / produção")
try:
    st.dataframe(_query(
        """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema='public'
          AND (column_name ILIKE '%rfid%'
               OR column_name ILIKE '%tag%'
               OR column_name ILIKE '%entrada%'
               OR table_name  ILIKE '%entrada%'
               OR column_name ILIKE '%produc%'
               OR table_name  ILIKE '%produc%'
               OR column_name ILIKE '%nota%'
               OR table_name  ILIKE '%nota%')
        ORDER BY table_name, ordinal_position
        """
    ), use_container_width=True, height=500)
except Exception as e:
    st.error(str(e))

st.header("3. Empresa")
try:
    st.dataframe(_query("SELECT * FROM empresa ORDER BY id_empresa"), use_container_width=True)
except Exception as e:
    st.error(str(e))
