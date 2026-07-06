# encoding: utf-8
"""Central de Usuários — exclusiva do administrador.

Os usuários são gravados em um arquivo JSON no GitHub (sem banco).
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

auth.exigir_admin()
nav.render("Central")

# ── estilo ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    div[data-testid="stForm"] {
        background: linear-gradient(165deg, rgba(46,124,246,.09), rgba(0,212,255,.03));
        border: 1px solid rgba(59,169,255,.22);
        border-radius: 18px;
        padding: 26px 28px;
        box-shadow: 0 18px 55px rgba(0,0,0,.35);
    }
    div[data-testid="stForm"] input { border-radius: 10px !important; }
    div[data-testid="stForm"] button[kind="primaryFormSubmit"],
    div[data-testid="stForm"] button {
        background: linear-gradient(135deg, #2E7CF6, #00D4FF);
        color: #06121F; font-weight: 700; border: none; border-radius: 10px;
        padding: 10px 0; transition: transform .15s ease, box-shadow .15s ease;
    }
    div[data-testid="stForm"] button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 26px rgba(46,124,246,.45);
    }
    .badge-github {
        display:inline-flex;align-items:center;gap:6px;
        background:rgba(0,224,161,.12);border:1px solid rgba(0,224,161,.35);
        color:#00E0A1;font-size:11px;font-weight:600;
        padding:3px 10px;border-radius:20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div style="display:flex;align-items:center;justify-content:space-between;gap:14px;margin:.1rem 0 1rem">
      <div style="display:flex;align-items:center;gap:14px">
        <div style="width:46px;height:46px;border-radius:13px;background:linear-gradient(150deg,#2E7CF6,#00D4FF);display:flex;align-items:center;justify-content:center;font-size:23px">🔐</div>
        <div>
          <div style="font-size:21px;font-weight:800;color:#F2F6FC">Central de Usuários</div>
          <div style="font-size:12px;color:#6B7385">Crie logins por empresa · o perfil <b>admin</b> vê todas as empresas e é o único que pode deletar</div>
        </div>
      </div>
      <span class="badge-github">● dados gravados no GitHub</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── empresas (opcional — se o banco falhar, informa o ID manualmente) ─────────
empresas = None
try:
    from db import load_empresas
    empresas = load_empresas()
except Exception:
    pass

col_novo, col_lista = st.columns([1, 1.6], gap="large")

# ── Criar usuário ─────────────────────────────────────────────────────────────
with col_novo:
    st.subheader("➕ Novo usuário")
    with st.form("novo_usuario", clear_on_submit=True):
        usuario = st.text_input("Usuário (login)", placeholder="ex.: joao.adrilar")
        c1, c2 = st.columns(2)
        with c1:
            senha = st.text_input("Senha", type="password", placeholder="mín. 6 caracteres")
        with c2:
            senha2 = st.text_input("Confirmar senha", type="password", placeholder="repita a senha")
        perfil = st.radio(
            "Perfil",
            ["empresa", "admin"],
            horizontal=True,
            help="empresa: vê só a empresa vinculada · admin: vê todas e pode deletar",
        )
        if empresas is not None and not empresas.empty:
            emp_nome = st.selectbox(
                "Empresa vinculada (apenas para perfil empresa)",
                empresas["nome_empresa"].tolist(),
            )
            emp_id_manual = None
        else:
            st.caption("⚠️ Lista de empresas indisponível — informe o ID manualmente.")
            emp_nome = None
            emp_id_manual = st.number_input(
                "ID da empresa (apenas para perfil empresa)", min_value=1, step=1, value=1
            )
        criar = st.form_submit_button("✅  Criar usuário", use_container_width=True)

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
                    if emp_nome is not None:
                        id_emp = int(
                            empresas.loc[empresas["nome_empresa"] == emp_nome, "id_empresa"].iloc[0]
                        )
                    else:
                        id_emp = int(emp_id_manual)
                with st.spinner("Gravando no GitHub..."):
                    auth.criar_usuario(usuario, senha, perfil=perfil, id_empresa=id_emp)
                st.success(f"Usuário **{usuario.strip().lower()}** criado.")
                st.balloons()
            except Exception as e:
                st.error(f"Erro ao criar usuário: {e}")

# ── Lista e gerenciamento ─────────────────────────────────────────────────────
with col_lista:
    st.subheader("👥 Usuários cadastrados")
    try:
        usuarios = auth.listar_usuarios()
    except Exception as e:
        st.error(f"Não foi possível carregar os usuários do GitHub: {e}")
        st.stop()

    if usuarios.empty:
        st.info("Nenhum usuário cadastrado ainda.")
    else:
        st.dataframe(
            usuarios.assign(ativo=usuarios["ativo"].map({True: "✅", False: "🚫"}))
            .rename(columns={
                "usuario": "Usuário", "perfil": "Perfil",
                "empresa": "Empresa", "ativo": "Ativo", "criado_em": "Criado em",
            }).drop(columns=["id"]),
            use_container_width=True, hide_index=True,
        )

        st.markdown("#### 🔧 Gerenciar usuário")
        nomes = usuarios["usuario"].tolist()
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
