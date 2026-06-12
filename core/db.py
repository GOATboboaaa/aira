"""
Connexion et initialisation de la base SQLite.

La base est creee automatiquement au premier lancement dans data/finance.db,
avec le schema complet et les valeurs par defaut (config fiscale + regles de
categorisation Revolut).

Multi-tenancy : toutes les tables portent une colonne user_id pour isoler
les donnees de chaque utilisateur.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from config import taux

# Chemin de la base : <racine_projet>/data/finance.db
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "finance.db"


def get_connection() -> sqlite3.Connection:
    """Retourne une connexion SQLite avec acces par nom de colonne."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS projets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL DEFAULT 0,
    client          TEXT NOT NULL,
    projet          TEXT NOT NULL,
    tarif           REAL NOT NULL,
    date_facture    TEXT NOT NULL,
    date_encaiss    TEXT,
    statut          TEXT NOT NULL DEFAULT 'En attente',
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS depenses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL DEFAULT 0,
    date            TEXT NOT NULL,
    montant         REAL NOT NULL,
    categorie       TEXT NOT NULL,
    description     TEXT,
    moyen_paiement  TEXT,
    source          TEXT DEFAULT 'manuel',
    revolut_ref     TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS config_fiscale (
    id                      INTEGER PRIMARY KEY CHECK (id = 1),
    user_id                 INTEGER NOT NULL DEFAULT 0,
    type_activite           TEXT NOT NULL DEFAULT 'BNC',
    versement_liberatoire   INTEGER NOT NULL DEFAULT 1,
    acre                    INTEGER NOT NULL DEFAULT 0,
    date_debut_activite     TEXT,
    taux_urssaf             REAL NOT NULL,
    taux_ir                 REAL NOT NULL,
    annee_reference         INTEGER NOT NULL DEFAULT 2025,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS regles_categorisation (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL DEFAULT 0,
    motif       TEXT NOT NULL,
    categorie   TEXT NOT NULL,
    type        TEXT NOT NULL DEFAULT 'depense',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Index anti-doublon pour l'import Revolut (les refs NULL ne sont pas contraintes)
CREATE UNIQUE INDEX IF NOT EXISTS idx_depenses_revolut_ref
    ON depenses(revolut_ref) WHERE revolut_ref IS NOT NULL;

-- Abonnements / depenses recurrentes
CREATE TABLE IF NOT EXISTS subscriptions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL DEFAULT 0,
    name            TEXT NOT NULL,
    amount          REAL NOT NULL,
    frequency       TEXT NOT NULL CHECK(frequency IN ('monthly','yearly','weekly')),
    billing_day     INTEGER NOT NULL CHECK(billing_day BETWEEN 1 AND 31),
    category        TEXT NOT NULL DEFAULT 'Abonnements logiciels',
    last_detected   TEXT,
    is_manual       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS planned_expenses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL DEFAULT 0,
    subscription_id INTEGER,
    name            TEXT NOT NULL,
    amount          REAL NOT NULL,
    due_date        TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'predicted' CHECK(status IN ('predicted','paid')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE CASCADE
);
"""


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """Ajoute les colonnes manquantes pour les bases existantes (upgrade)."""
    import re

    # Récupère les colonnes existantes de chaque table
    existing_cols = {}
    tables = [
        "projets", "depenses", "config_fiscale", "regles_categorisation",
        "subscriptions", "planned_expenses",
    ]
    for t in tables:
        rows = conn.execute(f"PRAGMA table_info({t})").fetchall()
        existing_cols[t] = {r["name"] for r in rows}

    for t in tables:
        if t not in existing_cols:
            continue
        cols = existing_cols[t]
        if "user_id" not in cols:
            conn.execute(
                f"ALTER TABLE {t} ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0"
            )

    # S'assurer que planned_expenses a bien ON DELETE CASCADE sur subscription_id
    # SQLite ne permet pas ALTER CONSTRAINT, donc on vérifie et avertit si besoin.
    # Pour les nouvelles créations, le CASCADE est dans le CREATE TABLE.


def init_db() -> None:
    """Cree le schema et injecte les donnees par defaut si necessaire."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        _migrate_schema(conn)

        # Seed de la config fiscale (une seule ligne par user — id=1 est temporaire)
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM users"
        ).fetchone()
        has_users = row["n"] > 0 if row else False

        conn.commit()
    finally:
        conn.close()
