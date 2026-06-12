"""
Aira — Pilotage financier micro-entreprise pour créateurs.

Point d'entrée Streamlit. Affiche l'accueil et gère la navigation.
Toute la logique métier est dans core/ ; le rendu dans pages/.
"""

import streamlit as st

from core import models
from core.components import footer, render_sidebar
from core.db import init_db
from core.styles import inject

st.set_page_config(
    page_title="Aira — Pilotage financier",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)
init_db()
inject()
render_sidebar()

config = models.get_config()

# ─── Page d'accueil ─────────────────────────────────────────────────────────
st.markdown(
    """<div style="text-align:center; padding:3rem 1rem 2rem 1rem;">
        <div style="font-size:3rem; margin-bottom:0.5rem;">✦</div>
        <h1 style="font-size:2.5rem; font-weight:800; letter-spacing:-0.03em;
                   background:linear-gradient(135deg, #7C5CFC, #A78BFA);
                   -webkit-background-clip:text; -webkit-text-fill-color:transparent;
                   background-clip:text;">
            Aira
        </h1>
        <p style="color:#94A3B8; font-size:1.1rem; max-width:480px; margin:0.5rem auto 1.5rem auto;">
            Pilotage financier pour créateurs de contenu et monteurs vidéo
            en micro-entreprise.
        </p>
    </div>""",
    unsafe_allow_html=True,
)

# ─── Cartes de navigation rapide ─────────────────────────────────────────────
cols = st.columns(5, gap="medium")
cards = [
    ("📊", "Dashboard", "Vue d'ensemble économique", "1_Dashboard"),
    ("🎬", "Projets", "Facturation et suivi des paiements", "2_Projets"),
    ("🧾", "Dépenses", "Suivi des dépenses réelles", "3_Depenses"),
    ("📅", "Calendrier", "Abonnements et prévisions", "6_Calendrier"),
    ("💰", "Fiscalité", "URSSAF, IR et seuils", "4_Fiscalite"),
]
for col, (icon, title, desc, page) in zip(cols, cards):
    with col:
        st.markdown(
            f"""<div onclick="window.location.href='{page}'"
                 style="cursor:pointer; background:#1A1A24; border:1px solid #2A2A3A;
                        border-radius:12px; padding:1.5rem 1rem; text-align:center;
                        transition:border-color 0.2s, transform 0.2s;"
                 onmouseover="this.style.borderColor='#7C5CFC'; this.style.transform='translateY(-2px)';"
                 onmouseout="this.style.borderColor='#2A2A3A'; this.style.transform='translateY(0)';">
                <div style="font-size:2rem; margin-bottom:0.5rem;">{icon}</div>
                <div style="color:#F1F5F9; font-weight:700; font-size:1rem;">{title}</div>
                <div style="color:#94A3B8; font-size:0.8rem; margin-top:0.25rem;">{desc}</div>
            </div>""",
            unsafe_allow_html=True,
        )
        if st.button(f"Ouvrir {title}", key=f"home_{page}"):
            st.switch_page(f"pages/{page}.py")

# ─── Infos en bas ──────────────────────────────────────────────────────────
st.divider()
cols_info = st.columns(2)
with cols_info[0]:
    st.markdown("**Régime** : Micro-entreprise BNC · Versement libératoire")
    st.markdown(f"**URSSAF** : {config.get('taux_urssaf', 0):.1f} % · **IR** : {config.get('taux_ir', 0):.1f} %")
with cols_info[1]:
    st.markdown("**Total prélèvements** : ~27,8 % du CA encaissé")
    st.markdown("**Conseil** : mets ce pourcentage de côté sur chaque encaissement.")

footer()
