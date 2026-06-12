"""Module d'authentification Aira — bcrypt + session Streamlit.

Fournit :
  - register_user(email, password) → crée un compte
  - login_user(email, password) → True/False
  - logout_user() → vide la session
  - require_auth() → redirige vers le login si pas connecté
  - get_current_user_id() → int | None
  - get_current_user_email() → str | None
"""

from __future__ import annotations

import re
from typing import Optional

import bcrypt
import streamlit as st

from core.db import get_connection

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


# =============================================================================
# Hachage bcrypt
# =============================================================================


def _hash_password(password: str) -> str:
    """Hash un mot de passe avec bcrypt (sel automatique, 12 rounds)."""
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=12)
    ).decode("utf-8")


def _check_password(password: str, hashed: str) -> bool:
    """Vérifie un mot de passe contre son hash bcrypt."""
    return bcrypt.checkpw(
        password.encode("utf-8"), hashed.encode("utf-8")
    )


# =============================================================================
# CRUD Utilisateurs
# =============================================================================


def register_user(email: str, password: str) -> tuple[bool, str]:
    """Crée un nouvel utilisateur.

    Returns:
        (True, "") en cas de succès, ou (False, "message d'erreur").
    """
    email = email.strip().lower()

    if not EMAIL_RE.match(email):
        return False, "Email invalide."

    if len(password) < 6:
        return False, "Mot de passe trop court (min 6 caractères)."

    conn = get_connection()
    try:
        # Vérifier si l'email existe déjà
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()
        if existing:
            return False, "Cet email est déjà utilisé."

        password_hash = _hash_password(password)
        cur = conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, password_hash),
        )
        user_id = cur.lastrowid

        # ═══ MIGRATION : adopter les données orphelines ═══
        # Si c'est le premier utilisateur, ré-assigne les données sans user_id
        total = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()
        if total and total["n"] == 1:
            for table in ("projets", "depenses", "config_fiscale",
                          "regles_categorisation", "subscriptions",
                          "planned_expenses"):
                try:
                    conn.execute(
                        f"UPDATE {table} SET user_id = ? "
                        f"WHERE user_id IS NULL OR user_id = 0",
                        (user_id,),
                    )
                except Exception:
                    pass  # la colonne n'existe pas encore → ignoré
            conn.commit()

        conn.commit()
        return True, ""
    finally:
        conn.close()


def login_user(email: str, password: str) -> tuple[bool, str, Optional[int]]:
    """Authentifie un utilisateur.

    Returns:
        (True, "", user_id) ou (False, "message d'erreur", None).
    """
    email = email.strip().lower()

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if not row:
            return False, "Email ou mot de passe incorrect.", None

        if not _check_password(password, row["password_hash"]):
            return False, "Email ou mot de passe incorrect.", None

        return True, "", row["id"]
    finally:
        conn.close()


def logout_user() -> None:
    """Vide la session de l'utilisateur."""
    for key in ("user_id", "user_email", "user_name"):
        if key in st.session_state:
            del st.session_state[key]


def set_session(user_id: int, email: str) -> None:
    """Enregistre l'utilisateur dans la session Streamlit."""
    st.session_state.user_id = user_id
    st.session_state.user_email = email


# =============================================================================
# Helpers session
# =============================================================================


def get_current_user_id() -> Optional[int]:
    """Retourne l'ID de l'utilisateur connecté, ou None."""
    return st.session_state.get("user_id")


def get_current_user_email() -> Optional[str]:
    """Retourne l'email de l'utilisateur connecté, ou None."""
    return st.session_state.get("user_email")


def is_authenticated() -> bool:
    """Vérifie si un utilisateur est connecté."""
    return "user_id" in st.session_state


# =============================================================================
# Decorateur / garde pour les pages
# =============================================================================


def require_auth() -> bool:
    """Appeler en haut de chaque page. Retourne True si authentifié.

    Si pas authentifié, affiche un message et propose d'aller à l'accueil.
    """
    if is_authenticated():
        return True

    import streamlit as st

    st.error("🔒 Tu dois être connecté pour accéder à cette page.")
    if st.button("🏠 Aller à la page de connexion"):
        st.switch_page("app.py")
    st.stop()
    return False
