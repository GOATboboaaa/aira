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


# =============================================================================
# ABONNEMENTS (subscriptions)
# =============================================================================


def add_subscription(
    name: str,
    amount: float,
    frequency: str,
    billing_day: int,
    category: str = "Abonnements logiciels",
    last_detected: str | None = None,
    is_manual: bool = True,
) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO subscriptions
               (name, amount, frequency, billing_day, category, last_detected, is_manual)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, amount, frequency, billing_day, category, last_detected,
             1 if is_manual else 0),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_subscriptions() -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql_query(
            "SELECT * FROM subscriptions ORDER BY name", conn
        )
    finally:
        conn.close()


def get_subscriptions_list() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM subscriptions ORDER BY name"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_subscription(sub_id: int, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE subscriptions SET {cols} WHERE id = ?",
            (*fields.values(), sub_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_subscription(sub_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM subscriptions WHERE id = ?", (sub_id,))
        conn.commit()
    finally:
        conn.close()


# =============================================================================
# DÉPENSES PLANIFIÉES (planned_expenses — projections calendrier)
# =============================================================================


def generate_planned_expenses(
    year: int,
    month: int | None = None,
) -> None:
    """Generer (ou met a jour) les depenses planifiees pour chaque abonnement actif
    sur la periode donnee. Si month est None, genere pour toute l annee."""
    conn = get_connection()
    try:
        subs = conn.execute(
            "SELECT * FROM subscriptions"
        ).fetchall()

        import calendar

        for sub in subs:
            sub = dict(sub)
            for m in ([month] if month else range(1, 13)):
                max_day = calendar.monthrange(year, m)[1]
                day = min(sub["billing_day"], max_day)
                due_date = f"{year}-{m:02d}-{day:02d}"

                existing = conn.execute(
                    "SELECT id FROM planned_expenses "
                    "WHERE subscription_id = ? AND due_date = ?",
                    (sub["id"], due_date),
                ).fetchone()

                if not existing:
                    conn.execute(
                        """INSERT INTO planned_expenses
                           (subscription_id, name, amount, due_date, status)
                           VALUES (?, ?, ?, ?, 'predicted')""",
                        (sub["id"], sub["name"], sub["amount"], due_date),
                    )

        conn.commit()
    finally:
        conn.close()


def get_planned_expenses(
    year: int,
    month: int | None = None,
) -> pd.DataFrame:
    """Retourne les depenses planifiees pour un mois donne (ou toute l annee)."""
    conn = get_connection()
    try:
        if month:
            query = (
                "SELECT pe.*, s.frequency, s.is_manual, s.category "
                "FROM planned_expenses pe "
                "LEFT JOIN subscriptions s ON pe.subscription_id = s.id "
                "WHERE strftime('%Y', pe.due_date) = ? "
                "AND strftime('%m', pe.due_date) = ? "
                "ORDER BY pe.due_date ASC"
            )
            df = pd.read_sql_query(
                query, conn, params=(str(year), f"{month:02d}")
            )
        else:
            query = (
                "SELECT pe.*, s.frequency, s.is_manual, s.category "
                "FROM planned_expenses pe "
                "LEFT JOIN subscriptions s ON pe.subscription_id = s.id "
                "WHERE strftime('%Y', pe.due_date) = ? "
                "ORDER BY pe.due_date ASC"
            )
            df = pd.read_sql_query(query, conn, params=(str(year),))
        return df
    finally:
        conn.close()


def mark_planned_paid(expense_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE planned_expenses SET status = 'paid' WHERE id = ?",
            (expense_id,),
        )
        conn.commit()
    finally:
        conn.close()


def delete_planned_expense(expense_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM planned_expenses WHERE id = ?", (expense_id,)
        )
        conn.commit()
    finally:
        conn.close()


def get_calendar_cashflow(year: int, month: int) -> dict:
    """Calcule le resume financier du mois : total abonnements, etc."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT COALESCE(SUM(pe.amount), 0) AS total_predicted
               FROM planned_expenses pe
               WHERE strftime('%Y', pe.due_date) = ?
                 AND strftime('%m', pe.due_date) = ?
                 AND pe.status = 'predicted'""",
            (str(year), f"{month:02d}"),
        ).fetchone()
        total_predicted = float(row["total_predicted"]) if row else 0.0

        row2 = conn.execute(
            """SELECT COALESCE(SUM(pe.amount), 0) AS total_paid
               FROM planned_expenses pe
               WHERE strftime('%Y', pe.due_date) = ?
                 AND strftime('%m', pe.due_date) = ?
                 AND pe.status = 'paid'""",
            (str(year), f"{month:02d}"),
        ).fetchone()
        total_paid = float(row2["total_paid"]) if row2 else 0

        row3 = conn.execute(
            "SELECT COUNT(*) AS n FROM subscriptions"
        ).fetchone()
        abos_count = row3["n"] if row3 else 0

        return {
            "total_predicted": total_predicted,
            "total_paid": total_paid,
            "total_all": total_predicted + total_paid,
            "abos_count": abos_count,
        }
    finally:
        conn.close()


# =============================================================================
# MOTEUR DE DÉTECTION D'ABONNEMENTS (analyse de transactions CSV)
# =============================================================================


def detect_subscriptions_from_transactions(
    transactions: list[dict],
) -> list[dict]:
    """Analyse une liste de transactions CSV pour detecter des abonnements.

    Args:
        transactions: liste de dicts avec 'description', 'montant', 'date'

    Returns:
        liste de dicts avec les abonnements detectes:
            {name, amount, frequency, billing_day, last_detected, confidence}
    """
    from collections import defaultdict
    from datetime import datetime
    import re

    # 1. Normaliser les libellés : extraire le nom court
    def normalize(name: str) -> str:
        n = name.strip().upper()
        # Enlever les suffixes type prélèvement, carte, etc.
        n = re.sub(r'\b(PRELEVEMENT|SEPA|CARTE|PAIEMENT|CB|DIRECT DEBIT)\b', '', n)
        n = re.sub(r'\b\d{2}/\d{2}\b', '', n)  # dates
        n = re.sub(r'\b\d{4}\b', '', n)  # années
        n = re.sub(r'\s+', ' ', n).strip()
        # Prendre les 3-4 premiers mots significatifs
        parts = n.split()
        if len(parts) > 4:
            n = ' '.join(parts[:4])
        return n.strip().rstrip('*').strip()

    # 2. Grouper par libellé normalisé
    groups: dict[str, list[dict]] = defaultdict(list)
    for tx in transactions:
        key = normalize(str(tx.get("description", "")))
        if key and len(key) > 2:
            groups[key].append(tx)

    # 3. Analyser chaque groupe
    detected = []
    for raw_name, txs in groups.items():
        if len(txs) < 2:
            continue  # besoin d'au moins 2 occurrences

        # Trier par date
        txs_sorted = sorted(
            txs,
            key=lambda t: str(t.get("date", "")),
        )

        # Verifier que les montants sont coherents (marge 5%)
        montants = [abs(float(t.get("montant", 0))) for t in txs_sorted]
        montant_moyen = sum(montants) / len(montants)

        # Ecart-type relatif < 10% = montant stable
        if max(montants) - min(montants) > montant_moyen * 0.15:
            continue  # trop variable, pas un abonnement

        amount = round(montant_moyen, 2)

        # Analyser les intervalles entre dates
        dates = sorted(set(
            str(t.get("date", "")) for t in txs_sorted if t.get("date")
        ))

        if len(dates) < 2:
            continue

        # Calculer les ecarts en jours
        intervals = []
        for i in range(1, len(dates)):
            try:
                d1 = datetime.strptime(dates[i - 1][:10], "%Y-%m-%d")
                d2 = datetime.strptime(dates[i][:10], "%Y-%m-%d")
                intervals.append((d2 - d1).days)
            except (ValueError, IndexError):
                continue

        if not intervals:
            continue

        interval_moyen = sum(intervals) / len(intervals)

        # Determiner la frequence
        if 25 <= interval_moyen <= 35:
            frequency = "monthly"
            billing_day = int(dates[-1][8:10]) if dates[-1][8:10].isdigit() else 1
        elif 355 <= interval_moyen <= 375:
            frequency = "yearly"
            billing_day = int(dates[-1][8:10]) if dates[-1][8:10].isdigit() else 1
        elif 7 <= interval_moyen <= 8:
            frequency = "weekly"
            billing_day = int(dates[-1][8:10]) if dates[-1][8:10].isdigit() else 1
        else:
            continue  # pas un pattern reconnu

        detected.append({
            "name": raw_name.title(),
            "amount": amount,
            "frequency": frequency,
            "billing_day": min(billing_day, 28),  # safe
            "last_detected": dates[-1],
            "confidence": round(
                (1 - (max(montants) - min(montants)) / montant_moyen / 2) * 100
                if montant_moyen > 0 else 50
            ),
        })

    return detected
