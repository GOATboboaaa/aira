"""Aira Auth Manager — auth par URL param, sans cookie (ITP-safe).

Résout les race conditions du cycle de rendu Streamlit en bloquant
tout affichage TANT QUE l'état d'auth n'est pas résolu.

Fonctionnement :
  1. verify_auth_state() appelée en TOUT PREMIER sur chaque page
  2. Check : session_state → URL param (`?auth_token=` ou `?session=`)
  3. Si token valide → restore la session + purge l'URL
  4. Si rien → return False (le caller affiche le login)

Pas de cookie : les navigateurs bloquent les cookies tierce partie
en iframe (ITP, SameSite par défaut). L'URL param est le seul canal
fiable cross-iframe.
"""

from __future__ import annotations

import logging
from typing import Optional

import streamlit as st

from core import session as session_mod

logger = logging.getLogger("aira.auth_manager")


# =============================================================================
# HELPERS
# =============================================================================


def _get_url_token() -> Optional[str]:
    """Lit le token depuis st.query_params.

    Accepte les clés 'auth_token' ou 'session' pour compatibilité.
    Retourne le premier token trouvé, ou None.
    """
    for key in ("auth_token", "session"):
        token = st.query_params.get(key)
        if isinstance(token, list):
            token = token[0] if token else None
        if token:
            return str(token)
    return None


def _purge_url_token() -> None:
    """Supprime auth_token ET session des query params."""
    q = st.query_params
    changed = False
    for key in ("auth_token", "session"):
        if key in q:
            del q[key]
            changed = True
    if changed:
        st.query_params = q


def _validate_and_restore(token: str) -> bool:
    """Valide un token et restaure la session si valide.

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
            return True
    finally:
        conn.close()
    return False


# =============================================================================
# VERIFY AUTH STATE — BLOQUE LE RENDU TANT QUE PAS RÉSOLU
# =============================================================================


def verify_auth_state() -> bool:
    """Vérifie et RESTAURE l'état d'auth AVANT tout rendu UI.

    Ordre des checks :
      1. session_state authentifié → return True (fast path)
      2. URL param `?auth_token=` ou `?session=` → valide, restore,
         purge l'URL, return True
      3. Rien → return False (le caller affiche le login)

    Returns:
        True si authentifié, False sinon.
    """
    # ─── 1. DÉJÀ AUTHENTIFIÉ (session_state) ──────────────────────────
    from core.auth import is_authenticated

    if is_authenticated():
        return True

    # ─── 2. URL PARAM ──────────────────────────────────────────────────
    url_token = _get_url_token()
    if url_token:
        restored = _validate_and_restore(url_token)
        if restored:
            # Sécurité : purger le token de l'URL immédiatement
            _purge_url_token()
            return True
        else:
            # Token invalide → nettoyer l'URL
            _purge_url_token()

    # ─── 3. PAS AUTHENTIFIÉ ────────────────────────────────────────────
    return False
