# encoding: utf-8
import streamlit as st

import auth

# página ativa → módulo controlado por usuário (páginas de admin não entram aqui)
_MODULO_DA_PAGINA = {"Pedidos": "pedidos", "Estoque": "estoque"}


def render(active: str = ""):
    """Menu lateral da marca AdriLar (esconde a navegação padrão do Streamlit).

    Os links exibidos dependem do perfil e dos módulos liberados:
    - Estoque / Pedidos: somente quem tem o módulo liberado (admin vê tudo)
    - Vendas e Central de Usuários: somente admin
    Também BLOQUEIA a página atual se o usuário não tiver o módulo dela.
    """
    user = auth.usuario_atual()

    # trava de acesso da página ativa (defesa central, além do menu)
    if active in _MODULO_DA_PAGINA and user and not auth.tem_acesso(_MODULO_DA_PAGINA[active]):
        st.error(
            f"Seu usuário não tem acesso ao módulo "
            f"{auth.MODULOS.get(_MODULO_DA_PAGINA[active], active)}. "
            "Fale com o administrador."
        )
        st.stop()

    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] { display: none; }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0B1322, #080D17);
            border-right: 1px solid rgba(59,169,255,.16);
        }
        section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] {
            border-radius: 10px;
            padding: 8px 10px;
            margin: 2px 0;
            font-weight: 600;
        }
        section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover {
            background: rgba(59,169,255,.13);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.sidebar:
        st.markdown(
            """
            <div style="display:flex;align-items:center;gap:12px;padding:4px 2px 14px">
              <div style="width:42px;height:42px;border-radius:12px;background:linear-gradient(150deg,#2E7CF6,#00D4FF);display:flex;align-items:center;justify-content:center;font-size:21px;box-shadow:0 6px 20px rgba(46,124,246,.35)">📦</div>
              <div>
                <div style="font-size:15px;font-weight:800;color:#F2F6FC;line-height:1.1">AdriLar</div>
                <div style="font-size:11px;color:#8B92A5">Estoque</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if auth.tem_acesso("estoque"):
            st.page_link("pages/Giro_Ruptura.py", label="Estoque", icon="📦")
        if auth.is_admin():
            st.page_link("pages/Dashboard_Vendas.py", label="Vendas", icon="📊")
            st.page_link("pages/Consignado_x_Venda.py", label="Consignado × Venda", icon="🤝")
        if auth.tem_acesso("pedidos"):
            st.page_link("app.py", label="Pedidos", icon="📋")
        if auth.is_admin():
            st.page_link("pages/Central_Usuarios.py", label="Central de Usuários", icon="🔐")

        # ── rodapé do usuário logado ──────────────────────────────────────────
        if user:
            iniciais = user["usuario"][:2].upper()
            escopo = "todas as empresas" if user["perfil"] == "admin" \
                else (user.get("nome_empresa") or "empresa")
            st.markdown(
                f"""
                <div style="border-top:1px solid rgba(255,255,255,.07);margin-top:14px;padding-top:12px;display:flex;align-items:center;gap:10px">
                  <div style="width:34px;height:34px;border-radius:9px;background:#16243b;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#9CC6FF">{iniciais}</div>
                  <div>
                    <div style="font-size:13px;color:#E4EAF3;font-weight:600">{user['usuario']}</div>
                    <div style="font-size:11px;color:#6B7385">{user['perfil']} · {escopo}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Sair", use_container_width=True):
                auth.logout()
        st.markdown(
            '<div style="font-size:10px;color:#5A6275;margin-top:6px;line-height:1.5">v2.2 · produto interno · conectado: AdriLar</div>',
            unsafe_allow_html=True,
        )
