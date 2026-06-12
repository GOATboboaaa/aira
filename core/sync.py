"""Synchronisation des modifications dictées à l'agent.

Quand l'utilisateur me dit "ajoute Spotify en dépense", je :
  1. Modifie la base locale
  2. Écris le changement dans data/sync_data.json
  3. Push sur GitHub
  4. L'app sur Streamlit Cloud lit ce fichier au démarrage
     et applique UNIQUEMENT les changements pour l'utilisateur connecté.

La table sync_log en DB empêche de rejouer un même changement 2x.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from core.auth import get_current_user_email, get_current_user_id, is_authenticated
from core.db import DB_PATH, get_connection

logger = logging.getLogger("aira.sync")

# Le fichier de sync est dans data/ à côté de la base
SYNC_FILE = DB_PATH.parent / "sync_data.json"


def _conn() -> ...:
    return get_connection()


def apply_pending() -> int:
    """Applique les changements en attente pour l'utilisateur connecté.

    Lit sync_data.json, filtre par user_email, vérifie sync_log,
    et execute les INSERT pour les changements non encore appliqués.

    Returns:
        Nombre de changements appliqués.
    """
    if not SYNC_FILE.exists():
        return 0

    if not is_authenticated():
        return 0  # personne de connecté, rien à appliquer

    user_id = get_current_user_id()
    user_email = (get_current_user_email() or "").lower()

    if not user_id or not user_email:
        return 0

    try:
        with open(SYNC_FILE, encoding="utf-8") as f:
            changes = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return 0

    if not isinstance(changes, list):
        return 0

    conn = _conn()
    applied = 0
    try:
        for change in changes:
            change_id = change.get("id")
            target_email = (change.get("user_email") or "").lower()

            # Ne pas appliquer si ce n'est pas pour l'utilisateur connecté
            if target_email != user_email:
                continue

            # Vérifier si déjà appliqué
            already = conn.execute(
                "SELECT 1 FROM sync_log WHERE change_id = ?",
                (change_id,),
            ).fetchone()
            if already:
                continue

            table = change.get("table")
            data = change.get("data")
            if not table or not data:
                continue

            # Construire et exécuter l'INSERT
            cols = ", ".join(data.keys())
            placeholders = ", ".join("?" for _ in data)
            values = list(data.values())

            # Ajouter user_id
            sql = f"INSERT INTO {table} ({cols}, user_id) VALUES ({placeholders}, ?)"
            values.append(user_id)

            try:
                conn.execute(sql, values)
                conn.execute(
                    "INSERT INTO sync_log (change_id) VALUES (?)",
                    (change_id,),
                )
                applied += 1
            except Exception as e:
                logger.warning(
                    "Sync: echec sur %s (%s): %s", change_id, table, e
                )

        conn.commit()
    finally:
        conn.close()

    if applied > 0:
        logger.info("Sync: %d changement(s) appliqué(s) pour %s", applied, user_email)

    return applied
