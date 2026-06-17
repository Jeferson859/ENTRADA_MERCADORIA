import streamlit as st

def protect():
    if st.session_state.get("auth_ok"):
        return
    senha = st.secrets.get("APP_SENHA", "")
    digitada = st.text_input("Senha de acesso", type="password")
    if senha and digitada == senha:
        st.session_state["auth_ok"] = True
        st.rerun()
    if digitada:
        st.error("Senha incorreta.")
    st.stop()
