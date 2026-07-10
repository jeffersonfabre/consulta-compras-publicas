"""
Consulta Compras Públicas

App web em Streamlit para consultar:
  • Licitações da Lei 14.133/2021
  • Atas de Registro de Preços (ARP)
  • Contratos firmados

Fonte: API pública do Compras.gov.br.
"""
from __future__ import annotations

import streamlit as st

from paginas import arp, contratos, licitacoes

# =============================================================================
# Configuração da página
# =============================================================================
st.set_page_config(
    page_title="Consulta Compras Públicas",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =============================================================================
# CSS global — visual clean e moderno
# =============================================================================
st.markdown(
    """
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", sans-serif;
}
#MainMenu, footer, header {visibility: hidden;}

.block-container {
    padding-top: 2.5rem;
    padding-bottom: 4rem;
    max-width: 1100px;
}

/* Cabeçalho do app */
.app-header {
    border-bottom: 1px solid #E2E8F0;
    padding-bottom: 1.5rem;
    margin-bottom: 1.5rem;
}
.app-header h1 {
    font-size: 1.875rem;
    font-weight: 600;
    color: #0F172A;
    margin: 0;
    letter-spacing: -0.025em;
}
.app-header p {
    color: #64748B;
    margin: 0.5rem 0 0 0;
    font-size: 0.95rem;
}
.pill {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    background: #F0FDF4;
    color: #15803D;
    border: 1px solid #BBF7D0;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 500;
    margin-right: 0.5rem;
}

/* Intro de cada página/tab */
.page-intro {
    color: #64748B;
    font-size: 0.95rem;
    margin: 1rem 0 1.5rem 0;
    line-height: 1.5;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid #E2E8F0;
}
.stTabs [data-baseweb="tab"] {
    padding: 0.75rem 1.25rem;
    font-weight: 500;
    color: #64748B;
    border: none;
    background: transparent;
}
.stTabs [aria-selected="true"] {
    color: #0F172A !important;
    border-bottom: 2px solid #0F172A !important;
}

/* Inputs */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div {
    border-radius: 8px !important;
    border: 1px solid #E2E8F0 !important;
}
.stTextInput > label, .stNumberInput > label, .stSelectbox > label {
    font-weight: 500 !important;
    color: #334155 !important;
    font-size: 0.875rem !important;
}

/* Botão primário */
.stButton > button {
    border-radius: 8px;
    border: 1px solid #0F172A;
    background: #0F172A;
    color: white;
    font-weight: 500;
    padding: 0.625rem 1.5rem;
    transition: all 0.15s ease;
}
.stButton > button:hover {
    background: #1E293B;
    border-color: #1E293B;
    transform: translateY(-1px);
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
}

/* Download button verde */
.stDownloadButton > button {
    border-radius: 8px;
    border: 1px solid #10B981;
    background: #10B981;
    color: white;
    font-weight: 500;
    padding: 0.625rem 1.5rem;
}
.stDownloadButton > button:hover {
    background: #059669;
    border-color: #059669;
}

/* Cards de métrica */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 1.25rem;
}
[data-testid="stMetricLabel"] {
    color: #64748B;
    font-size: 0.8rem !important;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
[data-testid="stMetricValue"] {
    color: #0F172A;
    font-size: 1.5rem !important;
    font-weight: 600;
}

.streamlit-expanderHeader {
    border-radius: 8px;
    background: #F8FAFC;
    font-weight: 500;
}

[data-testid="stDataFrame"] {
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #E2E8F0;
}

.section-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #0F172A;
    margin: 2rem 0 1rem 0;
}
</style>
""",
    unsafe_allow_html=True,
)

# =============================================================================
# Cabeçalho
# =============================================================================
st.markdown(
    """
<div class="app-header">
    <h1>Consulta Compras Públicas</h1>
    <p>
        <span class="pill">Lei 14.133/2021</span>
        Licitações, atas de registro de preços e contratos — fonte oficial Compras.gov.br
    </p>
</div>
""",
    unsafe_allow_html=True,
)

# =============================================================================
# Roteamento por tabs
# =============================================================================
tab_licitacoes, tab_arp, tab_contratos = st.tabs(
    ["📋  Licitações", "📑  Atas de Registro de Preços", "📝  Contratos"]
)

with tab_licitacoes:
    licitacoes.render()

with tab_arp:
    arp.render()

with tab_contratos:
    contratos.render()

# =============================================================================
# Rodapé
# =============================================================================
st.markdown(
    """
<div style="margin-top:4rem; padding-top:1.5rem; border-top:1px solid #E2E8F0;
            color:#94A3B8; font-size:0.8rem; text-align:center;">
    Dados públicos via API do Compras.gov.br · Lei nº 14.133/2021 ·
    <a href="https://dadosabertos.compras.gov.br/" target="_blank"
       style="color:#94A3B8;">documentação da API</a>
</div>
""",
    unsafe_allow_html=True,
)
