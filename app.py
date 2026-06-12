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
from core import sync as sync_mod

st.set_page_config(
    page_title="Aira — Pilotage financier",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)
init_db()
inject()

# Synchroniser les changements dictés à l'agent (uniquement pour
# l'utilisateur connecté, une seule fois par changement)
n = sync_mod.apply_pending()
if n > 0 and auth.is_authenticated():
    st.toast(f"📥 {n} modification(s) synchronisée(s) avec succès !", icon="✅")

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
    # ─── Vues : Login, Forgot Password, Reset Password ─────────────────
    # Detecter un reset_token dans l'URL (Streamlit 1.35+)
    query = st.query_params
    url_token = query.get("reset_token", [None])
    if isinstance(url_token, list):
        url_token = url_token[0] if url_token else None

    if url_token:
        st.session_state.auth_view = "reset"
        st.session_state.reset_token = url_token
        # Nettoyer l'URL pour eviter le re-jeu du token au refresh
        query.clear()
        st.query_params = query

    # État par defaut
    if "auth_view" not in st.session_state:
        st.session_state.auth_view = "login"

    current_view = st.session_state.auth_view

    # ─── Vue : Forgot Password ────────────────────────────────────────
    if current_view == "forgot":
        st.markdown("### 🔐 Mot de passe oublie")
        st.caption("Saisis ton email pour recevoir un lien de reinitialisation.")

        with st.form("forgot_form"):
            forgot_email = st.text_input(
                "Email",
                placeholder="ex: toi@email.com",
                key="forgot_email",
            )
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button(
                    "📧 Envoyer le lien",
                    type="primary",
                    use_container_width=True,
                )
            with col2:
                if st.form_submit_button("⬅️ Retour", use_container_width=True):
                    st.session_state.auth_view = "login"
                    st.rerun()

        if submitted and forgot_email:
            msg = auth.generate_password_reset(forgot_email)
            st.success(msg)
            st.info(
                "💡 Sur Streamlit Cloud, le lien est affiche dans les logs "
                "de l'application (console / stderr). "
                "Va dans 'Manage app' → 'Logs' pour le trouver, "
                "ou regarde le terminal si tu es en local."
            )
            # Afficher le lien directement pour le debug (uniquement local)
            import sys
            from io import StringIO
            st.code(
                f"# Le lien de reset a ete imprime dans les logs.\n"
                f"# Copie le ?reset_token=... depuis l'URL ci-dessous\n"
                f"# et ajoute-le a l'URL de l'app :\n"
                f"# {auth.RESET_BASE_URL}?reset_token=TON_TOKEN",
                language="text",
            )

    # ─── Vue : Reset Password ─────────────────────────────────────────
    elif current_view == "reset":
        token = st.session_state.get("reset_token", "")
        # Verifier si le token est encore valide
        user_id = auth.verify_reset_token(token)

        if user_id is None:
            st.error(
                "❌ Lien invalide ou expire. "
                "Fais une nouvelle demande de reinitialisation."
            )
            if st.button("⬅️ Retour à la connexion", use_container_width=True):
                st.session_state.auth_view = "login"
                st.query_params.clear()
                st.rerun()
        else:
            st.markdown("### 🔐 Nouveau mot de passe")
            st.caption("Choisis un nouveau mot de passe (min 6 caracteres).")

            with st.form("reset_form"):
                new_pass = st.text_input(
                    "Nouveau mot de passe",
                    type="password",
                    placeholder="Min 6 caracteres",
                    key="reset_new_pass",
                )
                new_pass2 = st.text_input(
                    "Confirmer le mot de passe",
                    type="password",
                    key="reset_new_pass2",
                )
                if st.form_submit_button(
                    "✅ Réinitialiser le mot de passe",
                    type="primary",
                    use_container_width=True,
                ):
                    if not new_pass:
                        st.error("Mot de passe obligatoire.")
                    elif new_pass != new_pass2:
                        st.error("Les mots de passe ne correspondent pas.")
                    elif len(new_pass) < 6:
                        st.error("Mot de passe trop court (min 6 caracteres).")
                    else:
                        ok, msg = auth.reset_password(token, new_pass)
                        if ok:
                            st.success(
                                "✅ Mot de passe réinitialise ! "
                                "Connecte-toi avec ton nouveau mot de passe."
                            )
                            # Nettoyer et revenir au login
                            if "reset_token" in st.session_state:
                                del st.session_state.reset_token
                            st.session_state.auth_view = "login"
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

    # ─── Vue : Login / Register (defaut) ──────────────────────────
    else:
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
            # Lien "Mot de passe oublie"
            st.markdown(
                f"<div style='text-align:center; margin-top:0.5rem;'>"
                f"<a href='#' onclick='return false;' "
                f"style='color:#A78BFA; font-size:0.85rem; "
                f"text-decoration:none; cursor:pointer;' "
                f"id='forgot-link'>"
                f"Mot de passe oublie ?</a></div>",
                unsafe_allow_html=True,
            )
            if st.button("Mot de passe oublie ?", key="goto_forgot",
                         use_container_width=True):
                st.session_state.auth_view = "forgot"
                st.rerun()

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
                            _, _, uid = auth.login_user(email_r, password_r)
                            if uid:
                                auth.set_session(uid, email_r.strip().lower())
                            st.success("✅ Compte cree ! Bienvenue sur Aira.")
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

footer()
