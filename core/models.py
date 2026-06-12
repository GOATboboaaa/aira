"""
Couche d'acces aux donnees (CRUD + requetes agregees).

Toutes les fonctions ouvrent/ferment leur propre connexion pour rester
compatibles avec le modele d'execution de Streamlit.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from core.db import get_connection

# =============================================================================
# CONFIG FISCALE
# =============================================================================


def get_config() -> dict:
    """Retourne la configuration fiscale (ligne unique id=1)."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM config_fiscale WHERE id = 1").fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def update_config(
    type_activite: str,
    versement_liberatoire: int,
    acre: int,
    taux_urssaf: float,
    taux_ir: float,
    annee_reference: int,
    date_debut_activite: Optional[str] = None,
) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE config_fiscale SET
                type_activite = ?,
                versement_liberatoire = ?,
                acre = ?,
                taux_urssaf = ?,
                taux_ir = ?,
                annee_reference = ?,
                date_debut_activite = ?
            WHERE id = 1
            """,
            (
                type_activite,
                versement_liberatoire,
                acre,
                taux_urssaf,
                taux_ir,
                annee_reference,
                date_debut_activite,
            ),
        )
        conn.commit()
    finally:
        conn.close()


# =============================================================================
# PROJETS
# =============================================================================


def add_projet(
    client: str,
    projet: str,
    tarif: float,
    date_facture: str,
    statut: str = "En attente",
    date_encaiss: Optional[str] = None,
    notes: Optional[str] = None,
) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO projets
                (client, projet, tarif, date_facture, date_encaiss, statut, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (client, projet, tarif, date_facture, date_encaiss, statut, notes),
        )
        conn.commit()
    finally:
        conn.close()


def get_projets(annee: Optional[int] = None) -> pd.DataFrame:
    """Retourne les projets, eventuellement filtres par annee de facturation."""
    conn = get_connection()
    try:
        if annee:
            query = (
                "SELECT * FROM projets "
                "WHERE strftime('%Y', date_facture) = ? "
                "ORDER BY date_facture DESC"
            )
            df = pd.read_sql_query(query, conn, params=(str(annee),))
        else:
            df = pd.read_sql_query(
                "SELECT * FROM projets ORDER BY date_facture DESC", conn
            )
        return df
    finally:
        conn.close()


def update_projet(projet_id: int, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE projets SET {cols} WHERE id = ?",
            (*fields.values(), projet_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_projet(projet_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM projets WHERE id = ?", (projet_id,))
        conn.commit()
    finally:
        conn.close()


# =============================================================================
# DEPENSES
# =============================================================================


def add_depense(
    date: str,
    montant: float,
    categorie: str,
    description: Optional[str] = None,
    moyen_paiement: Optional[str] = None,
    source: str = "manuel",
    revolut_ref: Optional[str] = None,
) -> bool:
    """Ajoute une depense. Retourne False si doublon Revolut (ref existante)."""
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO depenses
                (date, montant, categorie, description, moyen_paiement,
                 source, revolut_ref)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date,
                montant,
                categorie,
                description,
                moyen_paiement,
                source,
                revolut_ref,
            ),
        )
        conn.commit()
        return True
    except Exception:
        # Violation de l'index unique (doublon revolut_ref)
        return False
    finally:
        conn.close()


def get_depenses(annee: Optional[int] = None) -> pd.DataFrame:
    conn = get_connection()
    try:
        if annee:
            query = (
                "SELECT * FROM depenses "
                "WHERE strftime('%Y', date) = ? "
                "ORDER BY date DESC"
            )
            df = pd.read_sql_query(query, conn, params=(str(annee),))
        else:
            df = pd.read_sql_query("SELECT * FROM depenses ORDER BY date DESC", conn)
        return df
    finally:
        conn.close()


def update_depense(depense_id: int, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE depenses SET {cols} WHERE id = ?",
            (*fields.values(), depense_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_depense(depense_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM depenses WHERE id = ?", (depense_id,))
        conn.commit()
    finally:
        conn.close()


# =============================================================================
# REGLES DE CATEGORISATION
# =============================================================================


def get_regles() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM regles_categorisation ORDER BY motif"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_regle(motif: str, categorie: str, type_: str = "depense") -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO regles_categorisation (motif, categorie, type) "
            "VALUES (?, ?, ?)",
            (motif.upper(), categorie, type_),
        )
        conn.commit()
    finally:
        conn.close()


def delete_regle(regle_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM regles_categorisation WHERE id = ?", (regle_id,))
        conn.commit()
    finally:
        conn.close()


# =============================================================================
# AGREGATIONS / KPI
# =============================================================================


def ca_encaisse(annee: int) -> float:
    """
    CA reellement encaisse sur l'annee = somme des tarifs des projets
    marques 'Paye' (avec date d'encaissement dans l'annee).
    C'est l'assiette des cotisations en micro-entreprise.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(tarif), 0) AS total
            FROM projets
            WHERE statut = 'Paye'
              AND date_encaiss IS NOT NULL
              AND strftime('%Y', date_encaiss) = ?
            """,
            (str(annee),),
        ).fetchone()
        return float(row["total"])
    finally:
        conn.close()


def ca_facture(annee: int) -> float:
    """CA brut facture sur l'annee (paye + en attente), base date de facture."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(tarif), 0) AS total
            FROM projets
            WHERE strftime('%Y', date_facture) = ?
            """,
            (str(annee),),
        ).fetchone()
        return float(row["total"])
    finally:
        conn.close()


def ca_en_attente(annee: int) -> float:
    """Montant facture mais non encore encaisse (statut En attente)."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(tarif), 0) AS total
            FROM projets
            WHERE statut = 'En attente'
              AND strftime('%Y', date_facture) = ?
            """,
            (str(annee),),
        ).fetchone()
        return float(row["total"])
    finally:
        conn.close()


def total_depenses(annee: int) -> float:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(montant), 0) AS total
            FROM depenses
            WHERE strftime('%Y', date) = ?
            """,
            (str(annee),),
        ).fetchone()
        return float(row["total"])
    finally:
        conn.close()


def depenses_par_categorie(annee: int) -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT categorie, COALESCE(SUM(montant), 0) AS total
            FROM depenses
            WHERE strftime('%Y', date) = ?
            GROUP BY categorie
            ORDER BY total DESC
            """,
            conn,
            params=(str(annee),),
        )
    finally:
        conn.close()


def ca_mensuel(annee: int) -> pd.DataFrame:
    """CA encaisse agrege par mois (pour le graphe du dashboard)."""
    conn = get_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT strftime('%Y-%m', date_encaiss) AS mois,
                   COALESCE(SUM(tarif), 0) AS ca
            FROM projets
            WHERE statut = 'Paye'
              AND date_encaiss IS NOT NULL
              AND strftime('%Y', date_encaiss) = ?
            GROUP BY mois
            ORDER BY mois
            """,
            conn,
            params=(str(annee),),
        )
    finally:
        conn.close()


def annees_disponibles() -> list[int]:
    """Liste des annees presentes en base (projets ou depenses)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT strftime('%Y', date_facture) AS a FROM projets
            UNION
            SELECT strftime('%Y', date) AS a FROM depenses
            """
        ).fetchall()
        annees = sorted({int(r["a"]) for r in rows if r["a"]}, reverse=True)
        return annees
    finally:
        conn.close()
