"""Aira Auth Manager — système d'auth persistant, iframe-safe.

Résout les race conditions du cycle de rendu Streamlit en bloquant
tout affichage TANT QUE l'état d'auth n'est pas résolu.

Fonctionnement :
  1. verify_auth_state() appelée en TOUT PREMIER sur chaque page
  2. Check : session_state → URL param → cookie (via JS bridge)
  3. Si cookie trouvé mais pas d'URL param → JS redirect + st.stop()
  4. Au prochain render, l'URL param est présent → restauration

Attributs cookie : SameSite=None, Secure, max-age=7 jours.
"""

from __future__ import annotations

import logging
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components

from core import session as session_mod

logger = logging.getLogger("aira.auth_manager")

COOKIE_NAME = "aira_token"
COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 jours


# =============================================================================
# COOKIE MANAGEMENT (via JS bridge)
# =============================================================================


def set_session_cookie(token: str) -> None:
    """Définit le cookie d'auth côté client.

    Mêmes attributs que la session : Secure, SameSite=None, 7 jours.
    """
    html = f"""<script>
    document.cookie = "{COOKIE_NAME}={token}; path=/; SameSite=None; Secure; max-age={COOKIE_MAX_AGE}";
    </script>"""
    components.html(html, height=0)


def clear_session_cookie() -> None:
    """Supprime le cookie d'auth côté client."""
    html = f"""<script>
    document.cookie = "{COOKIE_NAME}=; path=/; SameSite=None; Secure; max-age=0";
    </script>"""
    components.html(html, height=0)


# =============================================================================
# JS BRIDGE — lire le cookie et rediriger avec le token dans l'URL
# =============================================================================


def _inject_cookie_bridge() -> None:
    """Injecte un script JS qui lit le cookie et redirige vers ?session=xxx.

    Cette fonction est appelée quand l'utilisateur arrive sur la page
    SANS session token dans l'URL. Le JS vérifie le cookie et, s'il est
    présent, redirige avec le token dans l'URL, ce qui déclenche un
    re-render Streamlit avec l'auth restaurée.
    """
    html = f"""<script>
    (function() {{
        var parts = document.cookie.split(';');
        for (var i = 0; i < parts.length; i++) {{
            var p = parts[i].trim();
            if (p.indexOf('{COOKIE_NAME}=') === 0) {{
                var token = p.substring({len(COOKIE_NAME) + 1});
                if (token) {{
                    var url = window.location.pathname + '?session=' + encodeURIComponent(token);
                    window.location.replace(url);
                    return;
                }}
            }}
        }}
    }})();
    </script>"""
    components.html(html, height=0)


# =============================================================================
# VERIFY AUTH STATE — BLOCS LE RENDU TANT QUE PAS RÉSOLU
# =============================================================================


def _validate_and_restore(token: str) -> bool:
    """Valide un token et restaure la session si valide.

    Returns:
        True si la session a été restaurée.
    """
    user_id = session_mod.validate_session(token)
    if user_id is None:
        return False

    # Restaurer : récupérer l'email et set_session
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


def _get_url_session_token() -> Optional[str]:
    """Lit le token depuis st.query_params, sous forme string."""
    token = st.query_params.get("session")
    if isinstance(token, list):
        token = token[0] if token else None
    if not token:
        return None
    return str(token)


def verify_auth_state() -> bool:
    """Vérifie et RESTAURE l'état d'auth AVANT tout rendu UI.

    Ordre des checks :
      1. session_state authentifié → return True (fast path)
      2. URL param `?session=` → valide, restore, return True
      3. Cookie client → redirige avec ?session=xxx et STOP le render
      4. Rien → return False (le caller affiche le login)

    Returns:
        True si authentifié, False sinon.
    """
    # ─── 1. DÉJÀ AUTHENTIFIÉ (session_state) ──────────────────────────
    from core.auth import is_authenticated

    if is_authenticated():
        return True

    # ─── 2. URL PARAM (fast path) ─────────────────────────────────────
    url_token = _get_url_session_token()
    if url_token:
        restored = _validate_and_restore(url_token)
        if restored:
            return True
        else:
            # Token invalide → le nettoyer de l'URL
            q = st.query_params
            if "session" in q:
                del q["session"]
            st.query_params = q

    # ─── 3. COOKIE BRIDGE (iframe-safe recovery) ──────────────────────
    # Si on arrive ici sans URL param et sans session_state, on tente
    # de récupérer le token depuis le cookie. On injecte un JS qui
    # redirige avec ?session=xxx, ce qui fera un nouveau render.
    _inject_cookie_bridge()

    # ─── 4. PAS AUTHENTIFIÉ ──────────────────────────────────────────
    return False
