# encoding: utf-8
"""Autenticação com perfis por empresa.

Perfis:
  - admin ....... vê todas as empresas, gerencia usuários (Central de Usuários)
                  e é o ÚNICO que pode deletar registros.
  - empresa ..... vê apenas os dados da empresa vinculada (id_empresa).

Os usuários ficam na tabela `app_usuario` do mesmo Postgres do app.
No primeiro acesso, se não houver nenhum usuário, é criado o usuário
`admin` com a senha do secret ADMIN_SENHA (ou APP_SENHA como reserva,
ou "admin123" se nenhum secret existir — troque imediatamente).
"""
import hashlib
import secrets as _secrets

import pandas as pd
import streamlit as st
from sqlalchemy import text

from db import get_engine, _get_secret

_PERFIS = ("admin", "empresa")


# ── infraestrutura ────────────────────────────────────────────────────────────

def _exec(sql: str, params: dict = None):
    with get_engine().begin() as conn:
        conn.execute(text(sql), params or {})


def _df(sql: str, params: dict = None) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def _hash(senha: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", senha.encode("utf-8"), bytes.fromhex(salt), 120_000
    ).hex()


_SQL_CRIAR_TABELA = """
CREATE TABLE IF NOT EXISTS app_usuario (
    id          SERIAL PRIMARY KEY,
    usuario     TEXT UNIQUE NOT NULL,
    senha_hash  TEXT NOT NULL,
    salt        TEXT NOT NULL,
    perfil      TEXT NOT NULL DEFAULT 'empresa',
    id_empresa  INT,
    ativo       BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em   TIMESTAMP NOT NULL DEFAULT NOW()
);
"""


def _tabela_existe() -> bool:
    df = _df("SELECT to_regclass('app_usuario') IS NOT NULL AS ok")
    return bool(df.iloc[0]["ok"])


@st.cache_resource(show_spinner=False)
def init_usuarios():
    """Garante a tabela de usuários e o admin inicial (roda 1x por processo)."""
    if not _tabela_existe():
        try:
            _exec(_SQL_CRIAR_TABELA)
        except Exception:
            # usuário do banco sem permissão de CREATE (ex.: permission denied
            # for schema public) → orienta a criar a tabela manualmente
            st.error(
                "O usuário do banco não tem permissão para criar tabelas. "
                "Peça ao administrador do banco para executar o SQL abaixo "
                "uma única vez (e conceda SELECT/INSERT/UPDATE/DELETE na "
                "tabela ao usuário do app):"
            )
            st.code(
                _SQL_CRIAR_TABELA
                + "\nGRANT SELECT, INSERT, UPDATE, DELETE ON app_usuario TO SEU_DB_USER;"
                + "\nGRANT USAGE, SELECT ON SEQUENCE app_usuario_id_seq TO SEU_DB_USER;",
                language="sql",
            )
            st.stop()
    n = int(_df("SELECT COUNT(*) AS n FROM app_usuario").iloc[0]["n"])
    if n == 0:
        senha = _get_secret("ADMIN_SENHA", _get_secret("APP_SENHA", "admin123"))
        criar_usuario("admin", senha, perfil="admin")
    return True


# ── CRUD de usuários (usado pela Central de Usuários) ────────────────────────

def criar_usuario(usuario: str, senha: str, perfil: str = "empresa", id_empresa=None):
    if perfil not in _PERFIS:
        raise ValueError(f"Perfil inválido: {perfil}")
    if perfil == "empresa" and id_empresa is None:
        raise ValueError("Usuário de empresa precisa de uma empresa vinculada.")
    salt = _secrets.token_hex(16)
    _exec(
        """INSERT INTO app_usuario (usuario, senha_hash, salt, perfil, id_empresa)
           VALUES (:u, :h, :s, :p, :e)""",
        {"u": usuario.strip().lower(), "h": _hash(senha, salt), "s": salt,
         "p": perfil, "e": int(id_empresa) if id_empresa is not None else None},
    )


def listar_usuarios() -> pd.DataFrame:
    return _df("""
        SELECT au.id, au.usuario, au.perfil,
               COALESCE(e.nome_empresa, '— todas —') AS empresa,
               au.ativo, au.criado_em
        FROM app_usuario au
        LEFT JOIN empresa e ON e.id_empresa = au.id_empresa
        ORDER BY au.usuario
    """)


def alterar_senha(usuario: str, nova_senha: str):
    salt = _secrets.token_hex(16)
    _exec(
        "UPDATE app_usuario SET senha_hash = :h, salt = :s WHERE usuario = :u",
        {"h": _hash(nova_senha, salt), "s": salt, "u": usuario},
    )


def definir_ativo(usuario: str, ativo: bool):
    _exec("UPDATE app_usuario SET ativo = :a WHERE usuario = :u",
          {"a": bool(ativo), "u": usuario})


def excluir_usuario(usuario: str):
    _exec("DELETE FROM app_usuario WHERE usuario = :u", {"u": usuario})


def autenticar(usuario: str, senha: str):
    """Devolve o dict do usuário se usuário/senha conferem, senão None."""
    df = _df(
        """SELECT au.usuario, au.senha_hash, au.salt, au.perfil, au.id_empresa,
                  e.nome_empresa
           FROM app_usuario au
           LEFT JOIN empresa e ON e.id_empresa = au.id_empresa
           WHERE au.usuario = :u AND au.ativo""",
        {"u": usuario.strip().lower()},
    )
    if df.empty:
        return None
    row = df.iloc[0]
    if _hash(senha, row["salt"]) != row["senha_hash"]:
        return None
    return {
        "usuario": row["usuario"],
        "perfil": row["perfil"],
        "id_empresa": None if pd.isna(row["id_empresa"]) else int(row["id_empresa"]),
        "nome_empresa": row["nome_empresa"] if pd.notna(row["nome_empresa"]) else None,
    }


# ── sessão / permissões ───────────────────────────────────────────────────────

def usuario_atual():
    return st.session_state.get("usuario")


def is_admin() -> bool:
    u = usuario_atual()
    return bool(u) and u["perfil"] == "admin"


def id_empresa_usuario():
    """None = admin (vê todas as empresas); int = restrito àquela empresa."""
    u = usuario_atual()
    if not u or u["perfil"] == "admin":
        return None
    return u["id_empresa"]


def pode_deletar() -> bool:
    """Regra global: somente o admin pode deletar registros."""
    return is_admin()


def logout():
    st.session_state.pop("usuario", None)
    st.rerun()


def require_login():
    """Exige login. Bloqueia a página até o usuário se autenticar."""
    init_usuarios()
    if usuario_atual():
        return st.session_state["usuario"]

    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:14px;margin:2rem 0 1rem">
          <div style="width:46px;height:46px;border-radius:13px;background:linear-gradient(150deg,#2E7CF6,#00D4FF);display:flex;align-items:center;justify-content:center;font-size:23px">🔐</div>
          <div>
            <div style="font-size:21px;font-weight:800;color:#F2F6FC">AdriLar · Acesso restrito</div>
            <div style="font-size:12px;color:#6B7385">Entre com o usuário e a senha fornecidos pelo administrador</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("login"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        ok = st.form_submit_button("Entrar", use_container_width=True)
    if ok:
        user = autenticar(usuario, senha)
        if user:
            st.session_state["usuario"] = user
            st.rerun()
        st.error("Usuário ou senha incorretos (ou usuário desativado).")
    st.stop()


def exigir_admin():
    """Exige login E perfil admin. Use nas páginas exclusivas do administrador."""
    require_login()
    if not is_admin():
        st.error("Acesso restrito ao administrador.")
        st.stop()


# compatibilidade com o código antigo (senha única) — não usar em páginas novas
def protect():
    require_login()
