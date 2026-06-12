"""
Connexion et initialisation de la base SQLite.

La base est creee automatiquement au premier lancement dans data/finance.db,
avec le schema complet et les valeurs par defaut (config fiscale + regles de
categorisation Revolut).
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
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS projets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client          TEXT NOT NULL,
    projet          TEXT NOT NULL,
    tarif           REAL NOT NULL,
    date_facture    TEXT NOT NULL,
    date_encaiss    TEXT,
    statut          TEXT NOT NULL DEFAULT 'En attente',
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS depenses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL,
    montant         REAL NOT NULL,
    categorie       TEXT NOT NULL,
    description     TEXT,
    moyen_paiement  TEXT,
    source          TEXT DEFAULT 'manuel',
    revolut_ref     TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS config_fiscale (
    id                      INTEGER PRIMARY KEY CHECK (id = 1),
    type_activite           TEXT NOT NULL DEFAULT 'BNC',
    versement_liberatoire   INTEGER NOT NULL DEFAULT 1,
    acre                    INTEGER NOT NULL DEFAULT 0,
    date_debut_activite     TEXT,
    taux_urssaf             REAL NOT NULL,
    taux_ir                 REAL NOT NULL,
    annee_reference         INTEGER NOT NULL DEFAULT 2025
);

CREATE TABLE IF NOT EXISTS regles_categorisation (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    motif       TEXT NOT NULL,
    categorie   TEXT NOT NULL,
    type        TEXT NOT NULL DEFAULT 'depense'
);

-- Index anti-doublon pour l'import Revolut (les refs NULL ne sont pas contraintes)
CREATE UNIQUE INDEX IF NOT EXISTS idx_depenses_revolut_ref
    ON depenses(revolut_ref) WHERE revolut_ref IS NOT NULL;
"""


def init_db() -> None:
    """Cree le schema et injecte les donnees par defaut si necessaire."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)

        # Seed de la config fiscale (une seule ligne, id=1)
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM config_fiscale WHERE id = 1"
        ).fetchone()
        if row["n"] == 0:
            conn.execute(
                """
                INSERT INTO config_fiscale
                    (id, type_activite, versement_liberatoire, acre,
                     taux_urssaf, taux_ir, annee_reference)
                VALUES (1, 'BNC', 1, 0, ?, ?, 2025)
                """,
                (taux.TAUX_URSSAF_DEFAUT, taux.TAUX_IR_DEFAUT),
            )

        # Seed des regles de categorisation Revolut
        row = conn.execute("SELECT COUNT(*) AS n FROM regles_categorisation").fetchone()
        if row["n"] == 0:
            conn.executemany(
                "INSERT INTO regles_categorisation (motif, categorie, type) "
                "VALUES (?, ?, ?)",
                taux.REGLES_CATEGORISATION_DEFAUT,
            )

        conn.commit()
    finally:
        conn.close()
