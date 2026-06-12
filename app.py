"""
Aira — Pilotage financier micro-entreprise pour createurs.

Page d'accueil : connexion / inscription.
Si deja connecte : montre le tableau de bord de navigation.
"""

from __future__ import annotations

import streamlit as st

from core import auth, models
from core import sync as sync_mod
from core import session as session_mod
from core.aira_auth_manager import verify_auth_state
from core.components import footer, auth_card, close_auth_card, trigger_shake
from core.db import init_db
from core.styles import inject, inject_premium_animations

st.set_page_config(
    page_title="Aira — Pilotage financier",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)
init_db()
inject()
inject_premium_animations()

# ═══════════════════════════════════════════════════════════════════════════
# AUTH GATE — BLOQUE LE RENDU TANT QUE L'ÉTAT D'AUTH N'EST PAS RÉSOLU
# ═══════════════════════════════════════════════════════════════════════════
session_mod.cleanup_expired()
authenticated = verify_auth_state()

# ─── Sync + Reset token cleanup (après auth gate) ─────────────────────────
n = sync_mod.apply_pending()
if n > 0 and authenticated:
    st.toast(f"📥 {n} modification(s) synchronisée(s) avec succès !", icon="✅")

reset_tok = st.query_params.get("reset_token")
if isinstance(reset_tok, list):
    reset_tok = reset_tok[0] if reset_tok else None
if reset_tok and authenticated:
    q = st.query_params
    if "reset_token" in q:
        del q["reset_token"]
    st.query_params = q

# ═══════════════════════════════════════════════════════════════════════════
# VUE AUTHENTIFIÉE — Page d'accueil pour utilisateur connecté
# ═══════════════════════════════════════════════════════════════════════════
if authenticated:
    config = models.get_config()
    user_email = auth.get_current_user_email()

    st.markdown(
        """<div style="text-align:center; padding:0.5rem 1rem 0 1rem;">
            <div style="font-size:2rem; margin-bottom:0.25rem;">✦</div>
            <h1 style="font-size:2rem; font-weight:800; letter-spacing:-0.03em;
                       background:linear-gradient(135deg, #7C5CFC, #A78BFA);
                       -webkit-background-clip:text; -webkit-text-fill-color:transparent;
                       background-clip:text;">
                Aira
            </h1>
            <p style="color:#64748B; font-size:0.85rem;">
                Connecté en tant que {user_email}
            </p>
        </div>""",
        unsafe_allow_html=True,
    )

    if st.button("🔑 Tableau de bord", type="primary", use_container_width=True):
        st.switch_page("pages/1_Dashboard.py")

    st.markdown("""<hr style="margin:1.5rem 0;">""", unsafe_allow_html=True)
    st.markdown("### Navigation rapide")
    cols = st.columns(5, gap="medium")
    nav_items = [
        ("📊", "Dashboard", "Vue d'ensemble", "1_Dashboard"),
        ("🎬", "Projets", "Facturation", "2_Projets"),
        ("🧾", "Dépenses", "Suivi réel", "3_Depenses"),
        ("📅", "Calendrier", "Prévisions", "6_Calendrier"),
        ("💰", "Fiscalité", "URSSAF/IR", "4_Fiscalite"),
    ]
    session_token = st.query_params.get("session", "")
    for col, (icon, title, desc, page) in zip(cols, nav_items):
        with col:
            st.markdown(
                f"""<div style="background:#1A1A24; border:1px solid #2A2A3A;
                        border-radius:12px; padding:1.25rem 0.75rem; text-align:center;
                        transition:border-color 0.2s, transform 0.2s;"
                     onmouseover="this.style.borderColor='#7C5CFC'; this.style.transform='translateY(-2px)';"
                     onmouseout="this.style.borderColor='#2A2A3A'; this.style.transform='translateY(0)';">
                    <div style="font-size:1.75rem; margin-bottom:0.35rem;">{icon}</div>
                    <div style="color:#F1F5F9; font-weight:700; font-size:0.9rem;">{title}</div>
                    <div style="color:#94A3B8; font-size:0.7rem; margin-top:0.15rem;">{desc}</div>
                </div>""",
                unsafe_allow_html=True,
            )
            if st.button(f"Ouvrir {title}", key=f"home_{page}", use_container_width=True):
                st.switch_page(f"pages/{page}.py")

    st.divider()
    footer()
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════
# VUE NON AUTHENTIFIÉE — Login / Forgot / Reset
# ═══════════════════════════════════════════════════════════════════════════

# ─── Détection reset_token dans l'URL ────────────────────────────────────
query = st.query_params
url_token = query.get("reset_token", [None])
if isinstance(url_token, list):
    url_token = url_token[0] if url_token else None

if url_token:
    st.session_state.auth_view = "reset"
    st.session_state.reset_token = url_token
    query.clear()
    st.query_params = query

# État par défaut
if "auth_view" not in st.session_state:
    st.session_state.auth_view = "login"

current_view = st.session_state.auth_view

# ─── Logo / Hero ──────────────────────────────────────────────────────────
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

# ─── Vue : Forgot Password ────────────────────────────────────────────────
if current_view == "forgot":
    auth_card("forgot")
    st.markdown("### 🔐 Mot de passe oublié")
    st.caption("Saisis ton email pour recevoir un lien de réinitialisation.")

    with st.form("forgot_form"):
        email = st.text_input("Email", placeholder="ton@email.com")
        submitted = st.form_submit_button(
            "Envoyer le lien", type="primary", use_container_width=True
        )
        if submitted:
            if not email:
                st.error("Veuillez saisir un email.")
            else:
                msg = auth.generate_password_reset(email)
                st.success(msg)
                st.info(
                    "💡 Le lien apparaît dans les logs de l'application "
                    "(stderr) — vérifie la console Streamlit Cloud."
                )

    if st.button("← Retour à la connexion"):
        st.session_state.auth_view = "login"
        st.rerun()
    close_auth_card()

# ─── Vue : Reset Password ────────────────────────────────────────────────
elif current_view == "reset":
    auth_card("reset")
    st.markdown("### 🔑 Nouveau mot de passe")
    st.caption("Choisis un mot de passe sécurisé (min 6 caractères).")

    with st.form("reset_form"):
        new_pwd = st.text_input(
            "Nouveau mot de passe",
            type="password",
            placeholder="••••••••",
        )
        confirm = st.text_input(
            "Confirme le mot de passe",
            type="password",
            placeholder="••••••••",
        )
        submitted = st.form_submit_button(
            "Réinitialiser", type="primary", use_container_width=True
        )
        if submitted:
            tok = st.session_state.get("reset_token", "")
            if new_pwd != confirm:
                st.error("Les mots de passe ne correspondent pas.")
            elif len(new_pwd) < 6:
                st.error("Mot de passe trop court (min 6 caractères).")
            elif not tok:
                st.error("Token de réinitialisation manquant.")
            else:
                ok, msg = auth.reset_password(tok, new_pwd)
                if ok:
                    st.success("✅ Mot de passe réinitialisé ! Tu peux te connecter.")
                    st.session_state.auth_view = "login"
                    st.rerun()
                else:
                    st.error(msg)
                    trigger_shake("reset")

    if st.button("← Retour à la connexion"):
        st.session_state.auth_view = "login"
        st.rerun()
    close_auth_card()

# ─── Vue : Login / Register (par défaut) ─────────────────────────────────
else:
    auth_card("login")
    tab_login, tab_register = st.tabs(["Connexion", "Inscription"])

    # ─── Login ──────────────────────────────────────────────────────────
    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="ton@email.com")
            password = st.text_input(
                "Mot de passe", type="password", placeholder="••••••••"
            )
            remember = st.checkbox("Se souvenir de moi", value=True)
            submitted = st.form_submit_button(
                "Se connecter", type="primary", use_container_width=True
            )
            if submitted:
                if not email or not password:
                    st.error("Veuillez remplir tous les champs.")
                    trigger_shake("login")
                else:
                    ok, msg, user_id = auth.login_user(email, password)
                    if ok and user_id:
                        # Créer session persistante
                        from core.session import create_session

                        raw_token = create_session(user_id)
                        auth.set_session(user_id, email)
                        st.query_params["auth_token"] = raw_token

                        # Sauvegarder dans le cache serveur (survit au F5)
                        from core.aira_auth_manager import store_auth
                        store_auth(raw_token, user_id, email)

                        st.success("✅ Connecté !")
                        st.rerun()
                    else:
                        st.error(msg)
                        trigger_shake("login")

        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔐 Mot de passe oublié ?", use_container_width=True):
                st.session_state.auth_view = "forgot"
                st.rerun()

    # ─── Register ───────────────────────────────────────────────────────
    with tab_register:
        with st.form("register_form"):
            reg_email = st.text_input(
                "Email", placeholder="ton@email.com", key="reg_email"
            )
            reg_password = st.text_input(
                "Mot de passe",
                type="password",
                placeholder="•••••••• (min 6 car.)",
                key="reg_password",
            )
            reg_confirm = st.text_input(
                "Confirme le mot de passe",
                type="password",
                placeholder="••••••••",
                key="reg_confirm",
            )
            submitted_reg = st.form_submit_button(
                "Créer mon compte", type="primary", use_container_width=True
            )
            if submitted_reg:
                if not reg_email or not reg_password:
                    st.error("Veuillez remplir tous les champs.")
                elif reg_password != reg_confirm:
                    st.error("Les mots de passe ne correspondent pas.")
                else:
                    ok, err_msg = auth.register_user(reg_email, reg_password)
                    if ok:
                        st.success(
                            "✅ Compte créé ! Tu peux te connecter."
                        )
                    else:
                        st.error(err_msg)

    close_auth_card()

footer()
