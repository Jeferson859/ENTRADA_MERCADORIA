# encoding: utf-8
import streamlit as st


def render(active: str = ""):
    """Menu lateral da marca AdriLar (esconde a navegação padrão do Streamlit)."""
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
        /* espaço para o rodapé fixo do usuário */
        section[data-testid="stSidebar"] > div:first-child { padding-bottom: 104px; }
        .adrilar-userbox {
            position: fixed;
            bottom: 0;
            left: 0;
            width: 244px;
            background: linear-gradient(180deg, rgba(8,13,23,0), #080D17 30%);
            padding: 18px 16px 16px;
            z-index: 100;
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
        st.page_link("pages/Giro_Ruptura.py", label="Estoque", icon="📦")
        st.page_link("pages/Dashboard_Vendas.py", label="Vendas", icon="📊")
        st.page_link("app.py", label="Pedidos", icon="📋")
        st.markdown(
            """
            <div class="adrilar-userbox">
              <div style="border-top:1px solid rgba(255,255,255,.07);padding-top:12px;display:flex;align-items:center;gap:10px">
                <div style="width:34px;height:34px;border-radius:9px;background:#16243b;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#9CC6FF">JA</div>
                <div>
                  <div style="font-size:13px;color:#E4EAF3;font-weight:600">Jeferson A.</div>
                  <div style="font-size:11px;color:#6B7385">administrador</div>
                </div>
              </div>
              <div style="font-size:10px;color:#5A6275;margin-top:8px;line-height:1.5">v2.0 · produto interno · conectado: AdriLar</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
