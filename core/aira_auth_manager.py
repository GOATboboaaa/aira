"""Aira Auth Manager — auth hybride URL param + cache serveur.

Survit au F5 (rafraîchissement navigateur) via un mécanisme double :
  1. Token conservé dans l'URL (`?auth_token=`) — pas de purge
  2. Cache serveur `st.cache_resource` — survit au WebSocket Streamlit

Architecture :
  - Le token est un random 32 bytes (pas un JWT), hashé en DB
  - Le garder dans l'URL est safe : pas de données utilisateur exposées
  - Le cache serveur permet un fallback si le param URL est perdu
    (navigation externe, bookmarks partiels, etc.)

Ordre de vérification (verify_auth_state) :
  1. session_state → return True (fast path, navigation entre pages)
  2. URL param → valide DB → restore + stocke en cache → return True
  3. Cache serveur → restore + ré-injecte URL param + rerun → return True
  4. Rien → return False (page de login)
"""

from __future__ import annotations

import logging
from typing import Optional

import streamlit as st

from core import session as session_mod

logger = logging.getLogger("aira.auth_manager")

# Nom de la clé auth dans l'URL
_URL_KEY = "auth_token"

# Durée de validité du cache (secondes) — 7 jours comme la session
_CACHE_TTL = 7 * 24 * 60 * 60


# =============================================================================
# SESSION STORE (serveur) — survit au F5
# =============================================================================


@st.cache_resource(ttl=_CACHE_TTL)
def _get_session_store() -> dict:
    """Cache serveur global des sessions actives.

    Survit au rafraîchissement Streamlit (F5) car le même processus
    Python sert toutes les sessions. Clé = token brut, valeur = user_data.

    Format : {token: {"user_id": int, "email": str}}
    """
    return {}


# =============================================================================
# API PUBLIQUE
# =============================================================================


def store_auth(token: str, user_id: int, email: str) -> None:
    """Stocke la session dans le cache serveur (post-login)."""
    store = _get_session_store()
    store[token] = {"user_id": user_id, "email": email}


def remove_auth(token: str) -> None:
    """Supprime la session du cache serveur (logout)."""
    store = _get_session_store()
    store.pop(token, None)


def restore_from_store(token: str) -> bool:
    """Restaure session_state depuis le cache serveur.

    Returns:
        True si la session a été restaurée.
    """
    store = _get_session_store()
    data = store.get(token)
    if data is None:
        return False

    from core.auth import set_session

    set_session(data["user_id"], data["email"])
    return True


# =============================================================================
# HELPERS URL
# =============================================================================


def _get_url_token() -> Optional[str]:
    """Lit le token depuis st.query_params.

    Accepte 'auth_token' ou 'session' pour compatibilité ascendante.
    """
    for key in (_URL_KEY, "session"):
        token = st.query_params.get(key)
        if isinstance(token, list):
            token = token[0] if token else None
        if token:
            return str(token)
    return None


def _inject_url_token(token: str) -> None:
    """Ajoute ou met à jour le token dans l'URL."""
    # Priorité à auth_token (nouveau) ; supprime session si présent
    q = st.query_params
    if "session" in q:
        del q["session"]
    q[_URL_KEY] = token
    st.query_params = q


# =============================================================================
# VALIDATION
# =============================================================================


def _validate_and_restore(token: str) -> bool:
    """Valide un token contre la DB et restore la session.

    Returns:
        True si la session a été restaurée.
    """
    user_id = session_mod.validate_session(token)
    if user_id is None:
        return False

    from core.db import get_connection

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT email FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if row:
            from core.auth import set_session

            set_session(user_id, row["email"])
            # Back up dans le cache serveur
            store_auth(token, user_id, row["email"])
            return True
    finally:
        conn.close()
    return False


# =============================================================================
# VERIFY AUTH STATE — BLOQUE LE RENDU
# =============================================================================


def verify_auth_state() -> bool:
    """Vérifie et RESTAURE l'état d'auth AVANT tout rendu UI.

    Ordre des checks :
      1. session_state authentifié → return True (fast path)
      2. URL param → valide DB → restore + cache serveur → return True
      3. Cache serveur → restore + ré-injecte URL param + st.rerun()
      4. Rien → return False (le caller affiche le login)

    Returns:
        True si authentifié, False sinon.
    """
    from core.auth import is_authenticated

    # ─── 1. DÉJÀ AUTHENTIFIÉ (session_state) ──────────────────────────
    if is_authenticated():
        return True

    # ─── 2. URL PARAM ──────────────────────────────────────────────────
    url_token = _get_url_token()
    if url_token:
        restored = _validate_and_restore(url_token)
        if restored:
            # On GARDE le token dans l'URL — pas de purge
            # Il survivra au F5
            return True
        else:
            # Token invalide → nettoyer l'URL
            q = st.query_params
            for key in (_URL_KEY, "session"):
                if key in q:
                    del q[key]
            st.query_params = q

    # ─── 3. CACHE SERVEUR (fallback F5) ────────────────────────────────
    # Si on arrive ici, le token URL est absent ou invalide.
    # On checke le cache serveur qui survit au F5.
    store = _get_session_store()
    for token, data in store.items():
        # Vérifier que la session DB est encore valide
        user_id = session_mod.validate_session(token)
        if user_id and user_id == data["user_id"]:
            # Restaurer depuis le cache
            from core.auth import set_session

            set_session(data["user_id"], data["email"])
            # Ré-injecter le token dans l'URL pour le prochain F5
            _inject_url_token(token)
            st.rerun()
            return True  # après rerun, on revient au check 1 ou 2

    # ─── 4. PAS AUTHENTIFIÉ ────────────────────────────────────────────
    return False
