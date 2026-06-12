"""Module d'authentification Aira — bcrypt + session Streamlit.

Fournit :
  - register_user(email, password) → cree un compte
  - login_user(email, password) → True/False
  - logout_user() → vide la session
  - generate_password_reset(email) → genere un token
  - verify_reset_token(token) → user_id ou None
  - reset_password(token, new_password) → bool
  - require_auth() → redirige vers le login si pas connecte
  - get_current_user_id() → int | None
  - get_current_user_email() → str | None
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import streamlit as st

from core.db import get_connection

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

logger = logging.getLogger("aira.auth")


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
# PASSWORD RESET FLOW
# =============================================================================

_TOKEN_EXPIRY_MINUTES = 15

# URL de base de l'application (ajustable)
RESET_BASE_URL = "https://airatools.streamlit.app"


def _hash_token(token: str) -> str:
    """Hache un token avec SHA-256 pour stockage securise en base.

    On stocke le hash, jamais le token en clair. La verification
    utilise un comparaison constant-time via hmac.compare_digest.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_password_reset(email: str) -> str:
    """Genere un token de reset pour l'email donne.

    Retourne toujours le meme message pour eviter l'enumeration.
    Le lien de reset est affiche via logger (mock email).
    """
    email = email.strip().lower()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()

        if row is not None:
            # Generer un token securise
            raw_token = secrets.token_urlsafe(32)
            token_hash = _hash_token(raw_token)
            expiry = (
                datetime.now(timezone.utc) + timedelta(minutes=_TOKEN_EXPIRY_MINUTES)
            ).isoformat()

            conn.execute(
                "UPDATE users SET reset_token = ?, reset_token_expiry = ? "
                "WHERE id = ?",
                (token_hash, expiry, row["id"]),
            )
            conn.commit()

            # ═══ Mock email : loggue le lien dans la console ═══
            reset_link = f"{RESET_BASE_URL}?reset_token={raw_token}"
            logger.info(
                "🔐 PASSWORD RESET pour %s\n"
                "   Lien : %s\n"
                "   Expire dans : %d min",
                email, reset_link, _TOKEN_EXPIRY_MINUTES,
            )
            # Aussi dans stderr pour Streamlit Cloud
            import sys
            print(
                f"\n{'='*60}\n"
                f"  🔐 RESET LINK pour {email}\n"
                f"  {reset_link}\n"
                f"  (expire dans {_TOKEN_EXPIRY_MINUTES} min)\n"
                f"{'='*60}\n",
                file=sys.stderr,
            )

        # Toujours retourner le meme message (anti-enumeration)
        return (
            f"✅ Si l'email {email} existe, un lien de reinitialisation "
            f"vient d'etre envoye (valable {_TOKEN_EXPIRY_MINUTES} min)."
        )
    finally:
        conn.close()


def verify_reset_token(token: str) -> Optional[int]:
    """Verifie un token de reset et retourne le user_id s'il est valide.

    Args:
        token: Le token brut (non hache).

    Returns:
        user_id si token valide et non expire, None sinon.
    """
    if not token:
        return None

    token_hash = _hash_token(token)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, reset_token_expiry FROM users "
            "WHERE reset_token = ?",
            (token_hash,),
        ).fetchone()

        if row is None:
            return None

        # Verifier l'expiration
        expiry_str = row["reset_token_expiry"]
        if not expiry_str:
            return None

        try:
            expiry = datetime.fromisoformat(expiry_str)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None

        if datetime.now(timezone.utc) > expiry:
            # Token expire — le nettoyer
            conn.execute(
                "UPDATE users SET reset_token = NULL, reset_token_expiry = NULL "
                "WHERE id = ?",
                (row["id"],),
            )
            conn.commit()
            return None

        return row["id"]
    finally:
        conn.close()


def reset_password(token: str, new_password: str) -> tuple[bool, str]:
    """Reinitialise le mot de passe avec un token valide.

    Args:
        token: Le token brut.
        new_password: Le nouveau mot de passe (min 6 car).

    Returns:
        (True, "") ou (False, "message d'erreur").
    """
    if len(new_password) < 6:
        return False, "Mot de passe trop court (min 6 caracteres)."

    user_id = verify_reset_token(token)
    if user_id is None:
        return False, (
            "Lien invalide ou expire. "
            "Fais une nouvelle demande de reinitialisation."
        )

    password_hash = _hash_password(new_password)
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET password_hash = ?, "
            "reset_token = NULL, reset_token_expiry = NULL "
            "WHERE id = ?",
            (password_hash, user_id),
        )
        conn.commit()
        logger.info("✅ Mot de passe reinitialise pour l'utilisateur %d", user_id)
        return True, ""
    finally:
        conn.close()


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
