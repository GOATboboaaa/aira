"""
aira_db_manager.py — Pont asynchrone SSOT entre saisie dépenses et calendrier.

Principe :
  - Single Source of Truth : table `expenses` (date + montant + catégorie + description).
  - Les vraies dépenses (page Dépenses) et les événements du calendrier
    lisent/écrivent au même endroit, sans duplication ni cache mémoire.
  - Context pruning : les requêtes calendrier ne chargent QUE le mois affiché.

Tables utilisées :
  - `expenses`  : SSOT des dépenses réelles (écriture depuis le formulaire).
  - `planned_expenses` + `subscriptions` : dépenses prévisionnelles (abonnements).
  - `depenses`   : table legacy (conservée pour rétrocompatibilité).

Architecture :
  +--------------+     insert_expense()     +------------------+
  |  Page        |==========================>|  aira_db_manager |
  |  Dépenses    |                           |  (SSOT)          |
  +--------------+                           |  +------------+  |
                                             |  |  expenses  |  |
  +--------------+   get_calendar_events()   |  +------------+  |
  |  Page        |<==========================|  + planned      |
  |  Calendrier  |                           |    _expenses    |
  +--------------+                           +------------------+
"""

from __future__ import annotations

import calendar as _calendar
import sqlite3
from datetime import date, datetime
from typing import Optional

from core.db import get_connection

# ──────────────────────────────────────────────────────────────────────────────
# INDEX (la table `expenses` est créée dans le SCHEMA principal de db.py)
# ──────────────────────────────────────────────────────────────────────────────

EXPENSES_INDEX = """
CREATE INDEX IF NOT EXISTS idx_expenses_date
    ON expenses(date_expense);
"""


def init_expenses_table() -> None:
    """Crée l'index et backfill les données legacy.

    La table `expenses` elle-même est créée dans le SCHEMA principal
    (core/db.py) pour garantir que `users` existe au moment du CREATE TABLE.
    """
    conn = get_connection()
    try:
        conn.execute(EXPENSES_INDEX)
        _backfill_from_depenses(conn)
        conn.commit()
    finally:
        conn.close()


def _backfill_from_depenses(conn: sqlite3.Connection) -> None:
    """Remplit la table `expenses` depuis les lignes `depenses` non encore copiées.

    Utilise un LEFT JOIN anti-doublon via la date + description + montant
    pour ne pas recopier ce qui existe déjà.
    """
    existing_count = conn.execute(
        "SELECT COUNT(*) FROM expenses"
    ).fetchone()[0]
    legacy_count = conn.execute(
        "SELECT COUNT(*) FROM depenses"
    ).fetchone()[0]

    if existing_count >= legacy_count:
        return  # Rien à backfill

    conn.execute("""
        INSERT OR IGNORE INTO expenses (user_id, date_expense, description, amount, category)
        SELECT
            0,
            d.date,
            COALESCE(d.description, ''),
            d.montant,
            d.categorie
        FROM depenses d
        LEFT JOIN expenses e
            ON e.date_expense = d.date
            AND e.description = COALESCE(d.description, '')
            AND e.amount = d.montant
        WHERE e.id IS NULL
    """)

# ──────────────────────────────────────────────────────────────────────────────
# ÉCRITURE  SSOT
# ──────────────────────────────────────────────────────────────────────────────


def insert_expense(
    date_expense: str,
    description: str,
    amount: float,
    category: str,
    user_id: int | None = None,
) -> int:
    """Insère une dépense dans la table SSOT `expenses`.

    Paramètres
    ----------
    date_expense : str   format 'YYYY-MM-DD'
    description  : str   texte libre
    amount       : float  montant en  TTC
    category     : str   'Alimentation', 'Abonnements logiciels', etc.

    Retourne l'ID de la ligne insérée.
    COMMIT immédiat  pas de cache, pas de session state.

    Thread-safe : chaque appel ouvre/ferme sa propre connexion.
    """
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO expenses (user_id, date_expense, description, amount, category)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id or 0, date_expense, description, amount, category),
        )
        row_id = cur.lastrowid
        conn.commit()
        return row_id
    finally:
        conn.close()


def bulk_insert_expenses(
    expenses: list[dict],
    user_id: int | None = None,
) -> list[int]:
    """Insertion multiple dans une seule transaction.

    Chaque dict doit avoir : date_expense, description, amount, category.
    Retourne la liste des IDs insérés.
    """
    conn = get_connection()
    ids = []
    try:
        for exp in expenses:
            cur = conn.execute(
                """
                INSERT INTO expenses (user_id, date_expense, description, amount, category)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id or 0,
                    exp["date_expense"],
                    exp["description"],
                    exp["amount"],
                    exp["category"],
                ),
            )
            ids.append(cur.lastrowid)
        conn.commit()
        return ids
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# LECTURE  Calendrier avec context pruning
# ──────────────────────────────────────────────────────────────────────────────


def get_calendar_events(
    year: int,
    month: int,
    user_id: int | None = None,
) -> list[dict]:
    """Retourne TOUS les événements pour le mois demandé, prêts pour calendrier.

    **Context Pruning** : la requête SQL filtre UNIQUEMENT les lignes du mois
    demandé  pas de chargement inutile.

    Deux sources fusionnées :
      1. Dépenses réelles (table `expenses`  SSOT)
      2. Dépenses planifiées (table `planned_expenses`  abonnements)

    Format retourné (compatible streamlit-calendar) :
    ```python
    [
        {
            "title": "Dépense: Baguette Marie Blachère (6.60)",
            "start": "2026-06-10",
            "end": "2026-06-10",
            "color": "#FF4B4B",
            "type": "real",           # 'real' ou 'predicted'
            "category": "Alimentation",
            "amount": 6.60,
            "id": 42,
        },
        ...
    ]
    ```
    """
    uid = user_id or 0
    month_str = f"{month:02d}"

    events: list[dict] = []

    conn = get_connection()
    try:
        #  1. Dépenses réelles (SSOT  table `expenses`)
        rows_real = conn.execute(
            """
            SELECT id, date_expense, description, amount, category
            FROM expenses
            WHERE strftime('%Y', date_expense) = ?
              AND strftime('%m', date_expense) = ?
            ORDER BY date_expense ASC
            """,
            (str(year), month_str),
        ).fetchall()

        for row in rows_real:
            r = dict(row)
            amt = r["amount"]
            desc = r["description"][:40] if r["description"] else "Sans libellé"
            events.append({
                "id": r["id"],
                "title": f"Dépense: {desc} ({amt:.2f})",
                "start": r["date_expense"],
                "end": r["date_expense"],
                "color": "#FF4B4B",         # Rouge pour dépenses réelles
                "type": "real",
                "category": r["category"],
                "amount": amt,
                "description": r["description"],
            })

        #  2. Dépenses planifiées (abonnements)
        rows_planned = conn.execute(
            """
            SELECT pe.id, pe.name, pe.amount, pe.due_date, pe.status,
                   s.frequency, s.category
            FROM planned_expenses pe
            LEFT JOIN subscriptions s ON pe.subscription_id = s.id
            WHERE strftime('%Y', pe.due_date) = ?
              AND strftime('%m', pe.due_date) = ?
            ORDER BY pe.due_date ASC
            """,
            (str(year), month_str),
        ).fetchall()

        for row in rows_planned:
            r = dict(row)
            amt = r["amount"]
            name = r["name"][:40] if r["name"] else "Abonnement"
            paid = r["status"] == "paid"
            freq_color = {
                "monthly": "#7C5CFC",    # Violet (mensuel)
                "yearly": "#F59E0B",      # Ambre (annuel)
                "weekly": "#06B6D4",      # Cyan (hebdo)
            }
            color = freq_color.get(r.get("frequency"), "#94A3B8")
            if paid:
                color = "#4A5568"  # Grisé si payé

            events.append({
                "id": r["id"],
                "title": f"{' ' if paid else ''}{name} ({amt:.2f})",
                "start": r["due_date"],
                "end": r["due_date"],
                "color": color,
                "type": "predicted",
                "category": r.get("category") or "Abonnements logiciels",
                "amount": amt,
                "status": r["status"],
                "frequency": r.get("frequency"),
            })

        return events

    finally:
        conn.close()


def get_monthly_summary(
    year: int,
    month: int,
    user_id: int | None = None,
) -> dict:
    """Agrégation rapide pour les KPIs du haut de page calendrier.

    Retourne :
      - total_real       : somme des dépenses réelles du mois
      - count_real       : nombre de dépenses réelles
      - total_predicted  : somme des dépenses planifiées (predicted)
      - total_paid       : somme des planifiées marquées paid
      - total_all        : total_real + total_predicted
    """
    uid = user_id or 0
    month_str = f"{month:02d}"
    conn = get_connection()
    try:
        real = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total,
                   COUNT(*) AS cnt
            FROM expenses
            WHERE strftime('%Y', date_expense) = ?
              AND strftime('%m', date_expense) = ?
            """,
            (str(year), month_str),
        ).fetchone()

        planned = conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN status='predicted' THEN amount ELSE 0 END), 0) AS total_predicted,
                COALESCE(SUM(CASE WHEN status='paid' THEN amount ELSE 0 END), 0) AS total_paid
            FROM planned_expenses
            WHERE strftime('%Y', due_date) = ?
              AND strftime('%m', due_date) = ?
            """,
            (str(year), month_str),
        ).fetchone()

        total_real = real["total"]
        total_predicted = planned["total_predicted"]
        total_paid = planned["total_paid"]

        return {
            "total_real": total_real,
            "count_real": real["cnt"],
            "total_predicted": total_predicted,
            "total_paid": total_paid,
            "total_all": total_real + total_predicted + total_paid,
        }
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# UTILITAIRES (pour la page Dépenses)
# ──────────────────────────────────────────────────────────────────────────────


def get_expenses_for_month(
    year: int,
    month: int,
    user_id: int | None = None,
) -> list[dict]:
    """Retourne toutes les dépenses réelles d'un mois (sans les planifiées).

    Utile pour la page Dépenses si elle veut sa version filtrée.
    """
    uid = user_id or 0
    month_str = f"{month:02d}"
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, date_expense, description, amount, category
            FROM expenses
            WHERE strftime('%Y', date_expense) = ?
              AND strftime('%m', date_expense) = ?
            ORDER BY date_expense DESC
            """,
            (str(year), month_str),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
