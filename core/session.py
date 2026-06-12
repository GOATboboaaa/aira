"""Sessions persistantes pour auto-login dans Streamlit.

Principe :
  - À la connexion, on genere un token aleatoire.
  - Le hash SHA-256 du token est stocke en DB (table `sessions`) avec
    une expiration a 7 jours.
  - Le token brut est mis dans l'URL via st.query_params.
  - Au chargement de l'app, on lit le token depuis l'URL, on le valide
    contre la DB, et on restaure la session.

Securite :
  - Le token n'est jamais stocke en clair en base (uniquement le hash).
  - Expiration a 7 jours, renouvele a chaque reconnexion.
  - Nettoyage automatique des tokens expires au demarrage.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from core.db import get_connection

SESSION_DURATION_DAYS = 7


def _hash_token(token: str) -> str:
    """Hache un token avec SHA-256 pour stockage securise."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(user_id: int) -> str:
    """Cree une session persistante pour l'utilisateur.

    Retourne le token brut (a mettre dans l'URL).
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=SESSION_DURATION_DAYS)
    ).isoformat()

    conn = get_connection()
    try:
        # Supprime les anciennes sessions de cet utilisateur pour eviter
        # l'accumulation (1 seul token actif par user a la fois)
        conn.execute(
            "DELETE FROM sessions WHERE user_id = ?", (user_id,)
        )
        conn.execute(
            "INSERT INTO sessions (user_id, token_hash, expires_at) "
            "VALUES (?, ?, ?)",
            (user_id, token_hash, expires_at),
        )
        conn.commit()
    finally:
        conn.close()

    return raw_token


def validate_session(token: str) -> Optional[int]:
    """Valide un token de session.

    Args:
        token: Le token brut depuis l'URL.

    Returns:
        user_id si valide et non expire, None sinon.
    """
    if not token:
        return None

    token_hash = _hash_token(token)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT user_id, expires_at FROM sessions WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()

        if row is None:
            return None

        try:
            expiry = datetime.fromisoformat(row["expires_at"])
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None

        if datetime.now(timezone.utc) > expiry:
            # Token expire → le supprimer
            conn.execute(
                "DELETE FROM sessions WHERE token_hash = ?",
                (token_hash,),
            )
            conn.commit()
            return None

        return row["user_id"]
    finally:
        conn.close()


def cleanup_expired() -> int:
    """Supprime tous les tokens expires.

    Returns:
        Nombre de sessions supprimees.
    """
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            "DELETE FROM sessions WHERE expires_at < ?", (now,)
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def restore_from_url() -> Optional[int]:
    """Tente de restaurer la session depuis le query param `session` dans l'URL.

    À appeler sur TOUTES les pages (app.py ET pages/*.py) au cas où
    st.session_state aurait ete perdu (refresh navigateur).

    Returns:
        user_id si restaure avec succes, None sinon.
    """
    import streamlit as st

    # Deja connecte → rien a faire
    from core.auth import is_authenticated
    if is_authenticated():
        return None

    token = st.query_params.get("session")
    if isinstance(token, list):
        token = token[0] if token else None

    if not token:
        return None

    user_id = validate_session(token)
    if user_id is None:
        return None

    # Restaurer : recuperer l'email et set_session
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT email FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if row:
            from core.auth import set_session
            set_session(user_id, row["email"])
            return user_id
    finally:
        conn.close()
    return None


def delete_session(token: str) -> None:
    """Supprime une session specifique (utilise a la deconnexion)."""
    if not token:
        return
    token_hash = _hash_token(token)
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM sessions WHERE token_hash = ?", (token_hash,)
        )
        conn.commit()
    finally:
        conn.close()
