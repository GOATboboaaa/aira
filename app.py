"""
Aira — Pilotage financier micro-entreprise pour createurs.

Page d'accueil : connexion / inscription.
Si deja connecte : montre le tableau de bord de navigation.
"""

from __future__ import annotations

import streamlit as st

from core import auth, models
from core.components import footer
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

# ─── Logo / Hero ────────────────────────────────────────────────────────────
st.markdown(
    """<div style="text-align:center; padding:2rem 1rem 1rem 1rem;">
        <div style="font-size:3rem; margin-bottom:0.5rem;">✦</div>
        <h1 style="font-size:2.5rem; font-weight:800; letter-spacing:-0.03em;
                   background:linear-gradient(135deg, #7C5CFC, #A78BFA);
                   -webkit-background-clip:text; -webkit-text-fill-color:transparent;
                   background-clip:text;">
            Aira
        </h1>
        <p style="color:#94A3B8; font-size:1rem; max-width:480px; margin:0.5rem auto 1rem auto;">
            Pilotage financier pour createurs de contenu et monteurs video
            en micro-entreprise.
        </p>
    </div>""",
    unsafe_allow_html=True,
)

# ─── CHECK AUTH : si connecte, montrer la home ==============================
if auth.is_authenticated():
    config = models.get_config()
    user_email = auth.get_current_user_email()

    st.success(f"✅ Connecté en tant que **{user_email}**")

    # Cartes de navigation rapide
    cols = st.columns(5, gap="medium")
    cards = [
        ("📊", "Dashboard", "Vue d'ensemble economique", "1_Dashboard"),
        ("🎬", "Projets", "Facturation et suivi des paiements", "2_Projets"),
        ("🧾", "Depenses", "Suivi des depenses reelles", "3_Depenses"),
        ("📅", "Calendrier", "Abonnements et previsions", "6_Calendrier"),
        ("💰", "Fiscalite", "URSSAF, IR et seuils", "4_Fiscalite"),
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

    st.divider()
    cols_info = st.columns(2)
    with cols_info[0]:
        st.markdown("**Regime** : Micro-entreprise BNC · Versement liberatoire")
        st.markdown(f"**URSSAF** : {config.get('taux_urssaf', 0):.1f} % · **IR** : {config.get('taux_ir', 0):.1f} %")
    with cols_info[1]:
        st.markdown("**Total prelevements** : ~27,8 % du CA encaisse")
        st.markdown("**Conseil** : mets ce pourcentage de cote sur chaque encaissement.")
else:
    # ─── Login / Register ───────────────────────────────────────────────────
    st.markdown("### 🔐 Connexion")
    tab_login, tab_register = st.tabs(["Se connecter", "Creer un compte"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="ex: toi@email.com")
            password = st.text_input("Mot de passe", type="password")
            if st.form_submit_button("Se connecter", type="primary", use_container_width=True):
                if not email or not password:
                    st.error("Email et mot de passe obligatoires.")
                else:
                    ok, msg, user_id = auth.login_user(email, password)
                    if ok:
                        auth.set_session(user_id, email.strip().lower())
                        st.success("✅ Connecte !")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

    with tab_register:
        with st.form("register_form"):
            email_r = st.text_input("Email", placeholder="ex: toi@email.com",
                                    key="reg_email")
            password_r = st.text_input(
                "Mot de passe (min 6 caracteres)", type="password",
                key="reg_pass"
            )
            password_r2 = st.text_input(
                "Confirmer le mot de passe", type="password",
                key="reg_pass2"
            )
            if st.form_submit_button("Creer mon compte", type="primary",
                                     use_container_width=True):
                if not email_r or not password_r:
                    st.error("Tous les champs sont obligatoires.")
                elif password_r != password_r2:
                    st.error("Les mots de passe ne correspondent pas.")
                else:
                    ok, msg = auth.register_user(email_r, password_r)
                    if ok:
                        # Auto-login apres inscription
                        _, _, uid = auth.login_user(email_r, password_r)
                        if uid:
                            auth.set_session(uid, email_r.strip().lower())
                        st.success("✅ Compte cree ! Bienvenue sur Aira.")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

footer()
