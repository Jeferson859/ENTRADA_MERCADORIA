# encoding: utf-8
"""Autenticação com perfis por empresa — usuários gravados no GITHUB (sem banco).

Os usuários ficam em um arquivo JSON num repositório GitHub (use um repo
PRIVADO!), acessado pela API de Contents. Nada de tabela app_usuario.

Configure em .streamlit/secrets.toml (ou Secrets do Streamlit Cloud):

    [github]
    token  = "github_pat_..."          # fine-grained, Contents: Read/Write
    repo   = "Jeferson859/adrilar-dados"   # REPO PRIVADO para os usuários
    branch = "main"
    path   = "dados/usuarios.json"

Perfis:
  - admin ....... vê todas as empresas, gerencia usuários e pode deletar.
  - empresa ..... vê apenas os dados da empresa vinculada (id_empresa).

No primeiro acesso, se não houver nenhum usuário, é criado o usuário
`admin` com a senha do secret ADMIN_SENHA (ou APP_SENHA como reserva,
ou "admin123" se nenhum secret existir — troque imediatamente).
"""
import base64
import hashlib
import json
import os
import secrets as _secrets
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st

_PERFIS = ("admin", "empresa")

# Módulos que podem ser liberados por usuário (páginas de admin ficam de fora)
MODULOS = {
    "pedidos": "📋 Pedidos",
    "estoque": "📦 Estoque",
}


# ── secrets / config ──────────────────────────────────────────────────────────

def _get_secret(nome: str, padrao=None):
    try:
        if nome in st.secrets:
            return st.secrets[nome]
    except Exception:
        pass
    return os.environ.get(nome, padrao)


def _gh_cfg():
    gh = {}
    try:
        gh = dict(st.secrets.get("github", {}))
    except Exception:
        pass
    token = gh.get("token") or _get_secret("GITHUB_TOKEN")
    repo = gh.get("repo") or _get_secret("GITHUB_REPO")
    branch = gh.get("branch") or _get_secret("GITHUB_BRANCH", "main")
    path = gh.get("path") or _get_secret("GITHUB_PATH", "dados/usuarios.json")
    if not token or not repo:
        st.error(
            "Configuração do GitHub ausente. Adicione nos Secrets do app:\n\n"
            "```toml\n[github]\ntoken  = \"github_pat_...\"\n"
            "repo   = \"usuario/repo-privado\"\nbranch = \"main\"\n"
            "path   = \"dados/usuarios.json\"\n```"
        )
        st.stop()
    return token, repo, branch, path


def _api():
    token, repo, branch, path = _gh_cfg()
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    return url, headers, branch


# ── armazenamento no GitHub ───────────────────────────────────────────────────

def _carregar():
    """Retorna (lista_de_usuarios, sha). sha=None se o arquivo ainda não existe."""
    url, headers, branch = _api()
    r = requests.get(url, headers=headers, params={"ref": branch}, timeout=20)
    if r.status_code == 404:
        return [], None
    r.raise_for_status()
    dados = r.json()
    try:
        usuarios = json.loads(base64.b64decode(dados["content"]).decode("utf-8"))
    except (json.JSONDecodeError, KeyError):
        usuarios = []
    return usuarios, dados["sha"]


def _salvar(usuarios: list, sha, mensagem: str):
    url, headers, branch = _api()
    payload = {
        "message": mensagem,
        "content": base64.b64encode(
            json.dumps(usuarios, ensure_ascii=False, indent=2).encode("utf-8")
        ).decode("ascii"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload, timeout=20)
    if r.status_code == 409:  # conflito de sha → recarrega e tenta 1x
        atuais, sha2 = _carregar()
        payload["sha"] = sha2
        r = requests.put(url, headers=headers, json=payload, timeout=20)
    r.raise_for_status()


# ── senha ─────────────────────────────────────────────────────────────────────

def _hash(senha: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", senha.encode("utf-8"), bytes.fromhex(salt), 120_000
    ).hex()


# ── bootstrap ─────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def init_usuarios():
    """Garante o admin inicial no JSON do GitHub (roda 1x por processo)."""
    try:
        usuarios, sha = _carregar()
    except requests.HTTPError as e:
        st.error(
            f"Não foi possível acessar o GitHub ({e.response.status_code}). "
            "Verifique token/permissões nos Secrets."
        )
        st.stop()
    if not usuarios:
        senha = _get_secret("ADMIN_SENHA", _get_secret("APP_SENHA", "admin123"))
        salt = _secrets.token_hex(16)
        usuarios = [{
            "id": 1,
            "usuario": "admin",
            "senha_hash": _hash(senha, salt),
            "salt": salt,
            "perfil": "admin",
            "id_empresa": None,
            "ativo": True,
            "criado_em": datetime.now(timezone.utc).isoformat(),
        }]
        _salvar(usuarios, sha, "Bootstrap: usuário admin inicial")
    return True


# ── nome da empresa (opcional, via banco; falha silenciosa) ───────────────────

def _nome_empresa(id_empresa):
    if id_empresa is None:
        return None
    try:
        from db import load_empresas
        emp = load_empresas()
        row = emp[emp["id_empresa"] == int(id_empresa)]
        if not row.empty:
            return str(row.iloc[0]["nome_empresa"])
    except Exception:
        pass
    return f"Empresa {id_empresa}"


# ── CRUD de usuários (usado pela Central de Usuários) ────────────────────────

def criar_usuario(usuario: str, senha: str, perfil: str = "empresa", id_empresa=None,
                  modulos=None):
    if perfil not in _PERFIS:
        raise ValueError(f"Perfil inválido: {perfil}")
    if perfil == "empresa" and id_empresa is None:
        raise ValueError("Usuário de empresa precisa de uma empresa vinculada.")
    if modulos is not None:
        modulos = [m for m in modulos if m in MODULOS]
        if perfil == "empresa" and not modulos:
            raise ValueError("Selecione ao menos um módulo para o usuário.")
    usuario = usuario.strip().lower()
    usuarios, sha = _carregar()
    if any(u["usuario"] == usuario for u in usuarios):
        raise ValueError(f"O usuário '{usuario}' já existe.")
    salt = _secrets.token_hex(16)
    usuarios.append({
        "id": max((u["id"] for u in usuarios), default=0) + 1,
        "usuario": usuario,
        "senha_hash": _hash(senha, salt),
        "salt": salt,
        "perfil": perfil,
        "id_empresa": int(id_empresa) if id_empresa is not None else None,
        "modulos": modulos,  # None = todos os módulos
        "ativo": True,
        "criado_em": datetime.now(timezone.utc).isoformat(),
    })
    _salvar(usuarios, sha, f"Novo usuário: {usuario}")


def listar_usuarios() -> pd.DataFrame:
    usuarios, _ = _carregar()
    linhas = [{
        "id": u["id"],
        "usuario": u["usuario"],
        "perfil": u["perfil"],
        "empresa": "— todas —" if u.get("id_empresa") is None
                   else _nome_empresa(u["id_empresa"]),
        "modulos": "— todos —" if u["perfil"] == "admin" or u.get("modulos") is None
                   else ", ".join(MODULOS.get(m, m) for m in u["modulos"]),
        "ativo": bool(u.get("ativo", True)),
        "criado_em": (u.get("criado_em") or "")[:19].replace("T", " "),
    } for u in usuarios]
    df = pd.DataFrame(linhas, columns=["id", "usuario", "perfil", "empresa", "modulos", "ativo", "criado_em"])
    return df.sort_values("usuario").reset_index(drop=True) if not df.empty else df


def _alterar(usuario: str, mensagem: str, fn):
    usuarios, sha = _carregar()
    for u in usuarios:
        if u["usuario"] == usuario:
            fn(u)
            break
    _salvar(usuarios, sha, mensagem)


def alterar_senha(usuario: str, nova_senha: str):
    salt = _secrets.token_hex(16)
    def fn(u):
        u["senha_hash"] = _hash(nova_senha, salt)
        u["salt"] = salt
    _alterar(usuario, f"Senha alterada: {usuario}", fn)


def definir_ativo(usuario: str, ativo: bool):
    _alterar(usuario, f"{'Ativado' if ativo else 'Desativado'}: {usuario}",
             lambda u: u.__setitem__("ativo", bool(ativo)))


def definir_modulos(usuario: str, modulos):
    """modulos: lista de chaves de MODULOS, ou None para liberar todos."""
    if modulos is not None:
        modulos = [m for m in modulos if m in MODULOS]
    _alterar(usuario, f"Módulos alterados: {usuario}",
             lambda u: u.__setitem__("modulos", modulos))


def excluir_usuario(usuario: str):
    usuarios, sha = _carregar()
    usuarios = [u for u in usuarios if u["usuario"] != usuario]
    _salvar(usuarios, sha, f"Usuário excluído: {usuario}")


def autenticar(usuario: str, senha: str):
    """Devolve o dict do usuário se usuário/senha conferem, senão None."""
    usuarios, _ = _carregar()
    usuario = usuario.strip().lower()
    for u in usuarios:
        if u["usuario"] == usuario and u.get("ativo", True):
            if _hash(senha, u["salt"]) == u["senha_hash"]:
                return {
                    "usuario": u["usuario"],
                    "perfil": u["perfil"],
                    "id_empresa": u.get("id_empresa"),
                    "nome_empresa": _nome_empresa(u.get("id_empresa")),
                    "modulos": u.get("modulos"),  # None = todos
                }
            return None
    return None


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


def tem_acesso(modulo: str) -> bool:
    """Admin acessa tudo; demais usuários só os módulos liberados.
    Usuário sem o campo 'modulos' (None) mantém acesso a todos (compatibilidade)."""
    u = usuario_atual()
    if not u:
        return False
    if u["perfil"] == "admin":
        return True
    mods = u.get("modulos")
    if mods is None:
        return True
    return modulo in mods


def exigir_acesso(modulo: str):
    """Exige login E acesso ao módulo. Use no topo das páginas de módulo."""
    require_login()
    if not tem_acesso(modulo):
        st.error(f"Seu usuário não tem acesso ao módulo {MODULOS.get(modulo, modulo)}. "
                 "Fale com o administrador.")
        st.stop()


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
        <style>
        div[data-testid="stForm"] {
            background: linear-gradient(165deg, rgba(46,124,246,.08), rgba(0,212,255,.03));
            border: 1px solid rgba(59,169,255,.22);
            border-radius: 18px;
            padding: 30px 34px;
            max-width: 460px;
            margin: 0 auto;
            box-shadow: 0 24px 70px rgba(0,0,0,.45);
        }
        div[data-testid="stForm"] button {
            background: linear-gradient(135deg, #2E7CF6, #00D4FF);
            color: #06121F; font-weight: 700; border: none;
            border-radius: 10px; transition: transform .15s ease, box-shadow .15s ease;
        }
        div[data-testid="stForm"] button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 26px rgba(46,124,246,.45);
        }
        </style>
        <div style="display:flex;flex-direction:column;align-items:center;gap:10px;margin:3rem 0 1.4rem;text-align:center">
          <div style="width:62px;height:62px;border-radius:17px;background:linear-gradient(150deg,#2E7CF6,#00D4FF);display:flex;align-items:center;justify-content:center;font-size:30px;box-shadow:0 10px 32px rgba(46,124,246,.45)">🔐</div>
          <div>
            <div style="font-size:24px;font-weight:800;color:#F2F6FC;letter-spacing:-.02em">AdriLar · Acesso restrito</div>
            <div style="font-size:12.5px;color:#6B7385;margin-top:4px">Entre com o usuário e a senha fornecidos pelo administrador</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("login"):
        usuario = st.text_input("Usuário", placeholder="seu.usuario")
        senha = st.text_input("Senha", type="password", placeholder="••••••••")
        ok = st.form_submit_button("Entrar", use_container_width=True)
    if ok:
        with st.spinner("Verificando..."):
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
# v2.2 módulos por usuário
