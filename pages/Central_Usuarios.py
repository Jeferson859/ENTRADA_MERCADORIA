# encoding: utf-8
"""Central de Usuários — exclusiva do administrador.

Aqui o admin cria usuários e senhas, vincula cada usuário a uma empresa,
reseta senhas, desativa e exclui contas.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

st.set_page_config(page_title="Central de Usuários", page_icon="🔐", layout="wide")

import auth
import nav
from db import load_empresas

auth.exigir_admin()
nav.render("Central")

st.markdown(
    """
    <div style="display:flex;align-items:center;gap:14px;margin:.1rem 0 1rem">
      <div style="width:46px;height:46px;border-radius:13px;background:linear-gradient(150deg,#2E7CF6,#00D4FF);display:flex;align-items:center;justify-content:center;font-size:23px">🔐</div>
      <div>
        <div style="font-size:21px;font-weight:800;color:#F2F6FC">Central de Usuários</div>
        <div style="font-size:12px;color:#6B7385">Crie logins por empresa · o perfil <b>admin</b> vê todas as empresas e é o único que pode deletar</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    empresas = load_empresas()
except Exception as e:
    st.error(f"Não foi possível carregar as empresas: {e}")
    st.stop()

col_novo, col_lista = st.columns([1, 1.6], gap="large")

# ── Criar usuário ─────────────────────────────────────────────────────────────
with col_novo:
    st.subheader("➕ Novo usuário")
    with st.form("novo_usuario", clear_on_submit=True):
        usuario = st.text_input("Usuário (login)", placeholder="ex.: joao.adrilar")
        senha = st.text_input("Senha", type="password")
        senha2 = st.text_input("Confirmar senha", type="password")
        perfil = st.radio(
            "Perfil",
            ["empresa", "admin"],
            horizontal=True,
            help="empresa: vê só a empresa vinculada · admin: vê todas e pode deletar",
        )
        emp_nome = st.selectbox(
            "Empresa vinculada (apenas para perfil empresa)",
            empresas["nome_empresa"].tolist() if not empresas.empty else [],
        )
        criar = st.form_submit_button("Criar usuário", use_container_width=True)

    if criar:
        if not usuario.strip() or not senha:
            st.error("Informe usuário e senha.")
        elif len(senha) < 6:
            st.error("A senha deve ter pelo menos 6 caracteres.")
        elif senha != senha2:
            st.error("As senhas não conferem.")
        else:
            try:
                id_emp = None
                if perfil == "empresa":
                    id_emp = int(
                        empresas.loc[empresas["nome_empresa"] == emp_nome, "id_empresa"].iloc[0]
                    )
                auth.criar_usuario(usuario, senha, perfil=perfil, id_empresa=id_emp)
                st.success(f"Usuário **{usuario.strip().lower()}** criado.")
            except Exception as e:
                st.error(f"Erro ao criar usuário (já existe?): {e}")

# ── Lista e gerenciamento ─────────────────────────────────────────────────────
with col_lista:
    st.subheader("👥 Usuários cadastrados")
    usuarios = auth.listar_usuarios()
    st.dataframe(
        usuarios.rename(columns={
            "usuario": "Usuário", "perfil": "Perfil",
            "empresa": "Empresa", "ativo": "Ativo", "criado_em": "Criado em",
        }).drop(columns=["id"]),
        use_container_width=True, hide_index=True,
    )

    st.markdown("#### 🔧 Gerenciar usuário")
    nomes = usuarios["usuario"].tolist()
    if nomes:
        alvo = st.selectbox("Usuário", nomes, key="ger_usuario")
        eu = auth.usuario_atual()["usuario"]
        c1, c2, c3 = st.columns(3)

        with c1:
            with st.popover("🔑 Resetar senha", use_container_width=True):
                ns = st.text_input("Nova senha", type="password", key="ns")
                if st.button("Salvar nova senha", use_container_width=True):
                    if len(ns) < 6:
                        st.error("Mínimo de 6 caracteres.")
                    else:
                        auth.alterar_senha(alvo, ns)
                        st.success("Senha alterada.")

        with c2:
            ativo_atual = bool(usuarios.loc[usuarios["usuario"] == alvo, "ativo"].iloc[0])
            rotulo = "🚫 Desativar" if ativo_atual else "✅ Reativar"
            if st.button(rotulo, use_container_width=True, disabled=(alvo == eu)):
                auth.definir_ativo(alvo, not ativo_atual)
                st.rerun()

        with c3:
            with st.popover("🗑️ Excluir", use_container_width=True):
                st.warning(f"Excluir **{alvo}** definitivamente?")
                if st.button("Confirmar exclusão", use_container_width=True,
                             disabled=(alvo == eu)):
                    auth.excluir_usuario(alvo)
                    st.rerun()
        if alvo == eu:
            st.caption("Você não pode desativar nem excluir o seu próprio usuário.")
