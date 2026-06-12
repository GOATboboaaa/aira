"""
Couche d'acces aux donnees (CRUD + requetes agregees).

Toutes les fonctions ouvrent/ferment leur propre connexion pour rester
compatibles avec le modele d'execution de Streamlit.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from core.auth import get_current_user_id
from core.db import get_connection

# =============================================================================
# CONFIG FISCALE
# =============================================================================


class AuthenticationRequiredError(RuntimeError):
    """Levée quand une fonction métier est appelée sans utilisateur connecté."""
    pass


def _uid() -> int:
    """Retourne le user_id courant.

    Lève AuthenticationRequiredError si pas connecté — ne retourne JAMAIS 0
    pour éviter les corruptions silencieuses ou les FK violations.
    """
    uid = get_current_user_id()
    if uid is None:
        raise AuthenticationRequiredError(
            "Tu dois être connecté pour accéder à cette fonctionnalité."
        )
    return uid


def get_config(uid: int | None = None) -> dict:
    """Retourne la configuration fiscale pour un utilisateur."""
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM config_fiscale WHERE user_id = ? LIMIT 1",
            (uid,),
        ).fetchone()
        if row:
            return dict(row)
        # Seed auto si pas de config
        from config import taux
        conn.execute(
            """INSERT INTO config_fiscale
               (user_id, type_activite, versement_liberatoire, acre,
                taux_urssaf, taux_ir, annee_reference)
               VALUES (?, 'BNC', 1, 0, ?, ?, 2025)""",
            (uid, taux.TAUX_URSSAF_DEFAUT, taux.TAUX_IR_DEFAUT),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM config_fiscale WHERE user_id = ? LIMIT 1",
            (uid,),
        ).fetchone()
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
    uid: int | None = None,
) -> None:
    if uid is None:
        uid = _uid()
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
            WHERE user_id = ?
            """,
            (
                type_activite,
                versement_liberatoire,
                acre,
                taux_urssaf,
                taux_ir,
                annee_reference,
                date_debut_activite,
                uid,
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
    uid: int | None = None,
) -> None:
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO projets
                (user_id, client, projet, tarif, date_facture, date_encaiss, statut, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (uid, client, projet, tarif, date_facture, date_encaiss, statut, notes),
        )
        conn.commit()
    finally:
        conn.close()


def get_projets(annee: Optional[int] = None, uid: int | None = None) -> pd.DataFrame:
    """Retourne les projets, eventuellement filtres par annee de facturation."""
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        if annee:
            query = (
                "SELECT * FROM projets "
                "WHERE user_id = ? AND strftime('%Y', date_facture) = ? "
                "ORDER BY date_facture DESC"
            )
            df = pd.read_sql_query(query, conn, params=(uid, str(annee)))
        else:
            df = pd.read_sql_query(
                "SELECT * FROM projets WHERE user_id = ? ORDER BY date_facture DESC",
                conn, params=(uid,),
            )
        return df
    finally:
        conn.close()


def update_projet(projet_id: int, uid: int | None = None, **fields) -> None:
    if uid is None:
        uid = _uid()
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE projets SET {cols} WHERE id = ? AND user_id = ?",
            (*fields.values(), projet_id, uid),
        )
        conn.commit()
    finally:
        conn.close()


def delete_projet(projet_id: int, uid: int | None = None) -> None:
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM projets WHERE id = ? AND user_id = ?",
            (projet_id, uid),
        )
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
    uid: int | None = None,
) -> bool:
    """Ajoute une depense. Retourne False si doublon Revolut (ref existante)."""
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO depenses
                (user_id, date, montant, categorie, description, moyen_paiement,
                 source, revolut_ref)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uid, date, montant, categorie, description,
                moyen_paiement, source, revolut_ref,
            ),
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_depenses(annee: Optional[int] = None, uid: int | None = None) -> pd.DataFrame:
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        if annee:
            query = (
                "SELECT * FROM depenses "
                "WHERE user_id = ? AND strftime('%Y', date) = ? "
                "ORDER BY date DESC"
            )
            df = pd.read_sql_query(query, conn, params=(uid, str(annee)))
        else:
            df = pd.read_sql_query(
                "SELECT * FROM depenses WHERE user_id = ? ORDER BY date DESC",
                conn, params=(uid,),
            )
        return df
    finally:
        conn.close()


def update_depense(depense_id: int, uid: int | None = None, **fields) -> None:
    if uid is None:
        uid = _uid()
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE depenses SET {cols} WHERE id = ? AND user_id = ?",
            (*fields.values(), depense_id, uid),
        )
        conn.commit()
    finally:
        conn.close()


def delete_depense(depense_id: int, uid: int | None = None) -> None:
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM depenses WHERE id = ? AND user_id = ?",
            (depense_id, uid),
        )
        conn.commit()
    finally:
        conn.close()


# =============================================================================
# REGLES DE CATEGORISATION
# =============================================================================


def get_regles(uid: int | None = None) -> list[dict]:
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM regles_categorisation WHERE user_id = ? ORDER BY motif",
            (uid,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_regle(motif: str, categorie: str, type_: str = "depense",
              uid: int | None = None) -> None:
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO regles_categorisation (user_id, motif, categorie, type) "
            "VALUES (?, ?, ?, ?)",
            (uid, motif.upper(), categorie, type_),
        )
        conn.commit()
    finally:
        conn.close()


def delete_regle(regle_id: int, uid: int | None = None) -> None:
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM regles_categorisation WHERE id = ? AND user_id = ?",
            (regle_id, uid),
        )
        conn.commit()
    finally:
        conn.close()


# =============================================================================
# AGREGATIONS / KPI
# =============================================================================


def ca_encaisse(annee: int, uid: int | None = None) -> float:
    """CA reellement encaisse sur l'annee pour un utilisateur."""
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(tarif), 0) AS total
            FROM projets
            WHERE user_id = ?
              AND statut = 'Paye'
              AND date_encaiss IS NOT NULL
              AND strftime('%Y', date_encaiss) = ?
            """,
            (uid, str(annee)),
        ).fetchone()
        return float(row["total"])
    finally:
        conn.close()


def ca_facture(annee: int, uid: int | None = None) -> float:
    """CA brut facture sur l'annee pour un utilisateur."""
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(tarif), 0) AS total
            FROM projets
            WHERE user_id = ?
              AND strftime('%Y', date_facture) = ?
            """,
            (uid, str(annee)),
        ).fetchone()
        return float(row["total"])
    finally:
        conn.close()


def ca_en_attente(annee: int, uid: int | None = None) -> float:
    """Montant facture mais non encore encaisse pour un utilisateur."""
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(tarif), 0) AS total
            FROM projets
            WHERE user_id = ?
              AND statut = 'En attente'
              AND strftime('%Y', date_facture) = ?
            """,
            (uid, str(annee)),
        ).fetchone()
        return float(row["total"])
    finally:
        conn.close()


def total_depenses(annee: int, uid: int | None = None) -> float:
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(montant), 0) AS total
            FROM depenses
            WHERE user_id = ?
              AND strftime('%Y', date) = ?
            """,
            (uid, str(annee)),
        ).fetchone()
        return float(row["total"])
    finally:
        conn.close()


def depenses_par_categorie(annee: int, uid: int | None = None) -> pd.DataFrame:
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT categorie, COALESCE(SUM(montant), 0) AS total
            FROM depenses
            WHERE user_id = ? AND strftime('%Y', date) = ?
            GROUP BY categorie
            ORDER BY total DESC
            """,
            conn,
            params=(uid, str(annee)),
        )
    finally:
        conn.close()


def ca_mensuel(annee: int, uid: int | None = None) -> pd.DataFrame:
    """CA encaisse agrege par mois pour un utilisateur."""
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT strftime('%Y-%m', date_encaiss) AS mois,
                   COALESCE(SUM(tarif), 0) AS ca
            FROM projets
            WHERE user_id = ?
              AND statut = 'Paye'
              AND date_encaiss IS NOT NULL
              AND strftime('%Y', date_encaiss) = ?
            GROUP BY mois
            ORDER BY mois
            """,
            conn,
            params=(uid, str(annee)),
        )
    finally:
        conn.close()


def annees_disponibles(uid: int | None = None) -> list[int]:
    """Liste des annees presentes en base pour un utilisateur."""
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT strftime('%Y', date_facture) AS a FROM projets WHERE user_id = ?
            UNION
            SELECT strftime('%Y', date) AS a FROM depenses WHERE user_id = ?
            """,
            (uid, uid),
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
    uid: int | None = None,
) -> int:
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO subscriptions
               (user_id, name, amount, frequency, billing_day, category, last_detected, is_manual)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (uid, name, amount, frequency, billing_day, category, last_detected,
             1 if is_manual else 0),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_subscriptions(uid: int | None = None) -> pd.DataFrame:
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        return pd.read_sql_query(
            "SELECT * FROM subscriptions WHERE user_id = ? ORDER BY name",
            conn, params=(uid,),
        )
    finally:
        conn.close()


def get_subscriptions_list(uid: int | None = None) -> list[dict]:
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM subscriptions WHERE user_id = ? ORDER BY name",
            (uid,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_subscription(sub_id: int, uid: int | None = None, **fields) -> None:
    if uid is None:
        uid = _uid()
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE subscriptions SET {cols} WHERE id = ? AND user_id = ?",
            (*fields.values(), sub_id, uid),
        )
        conn.commit()
    finally:
        conn.close()


def delete_subscription(sub_id: int, uid: int | None = None) -> None:
    """Supprime un abonnement et cascade automatiquement sur ses planned_expenses."""
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        cur = conn.execute(
            "DELETE FROM subscriptions WHERE id = ? AND user_id = ?",
            (sub_id, uid),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# =============================================================================
# DÉPENSES PLANIFIÉES (planned_expenses — projections calendrier)
# =============================================================================


def generate_planned_expenses(
    year: int,
    month: int | None = None,
    uid: int | None = None,
) -> None:
    """Generer (ou met a jour) les depenses planifiees pour chaque abonnement actif."""
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        subs = conn.execute(
            "SELECT * FROM subscriptions WHERE user_id = ?",
            (uid,),
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
                    "WHERE user_id = ? AND subscription_id = ? AND due_date = ?",
                    (uid, sub["id"], due_date),
                ).fetchone()

                if not existing:
                    conn.execute(
                        """INSERT INTO planned_expenses
                           (user_id, subscription_id, name, amount, due_date, status)
                           VALUES (?, ?, ?, ?, ?, 'predicted')""",
                        (uid, sub["id"], sub["name"], sub["amount"], due_date),
                    )

        conn.commit()
    finally:
        conn.close()


def get_planned_expenses(
    year: int,
    month: int | None = None,
    uid: int | None = None,
) -> pd.DataFrame:
    """Retourne les depenses planifiees pour un mois donne."""
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        if month:
            query = (
                "SELECT pe.*, s.frequency, s.is_manual, s.category "
                "FROM planned_expenses pe "
                "LEFT JOIN subscriptions s ON pe.subscription_id = s.id "
                "WHERE pe.user_id = ? "
                "AND strftime('%Y', pe.due_date) = ? "
                "AND strftime('%m', pe.due_date) = ? "
                "ORDER BY pe.due_date ASC"
            )
            df = pd.read_sql_query(
                query, conn, params=(uid, str(year), f"{month:02d}")
            )
        else:
            query = (
                "SELECT pe.*, s.frequency, s.is_manual, s.category "
                "FROM planned_expenses pe "
                "LEFT JOIN subscriptions s ON pe.subscription_id = s.id "
                "WHERE pe.user_id = ? "
                "AND strftime('%Y', pe.due_date) = ? "
                "ORDER BY pe.due_date ASC"
            )
            df = pd.read_sql_query(query, conn, params=(uid, str(year)))
        return df
    finally:
        conn.close()


def mark_planned_paid(expense_id: int, uid: int | None = None) -> None:
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE planned_expenses SET status = 'paid' "
            "WHERE id = ? AND user_id = ?",
            (expense_id, uid),
        )
        conn.commit()
    finally:
        conn.close()


def delete_planned_expense(expense_id: int, uid: int | None = None) -> None:
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM planned_expenses WHERE id = ? AND user_id = ?",
            (expense_id, uid),
        )
        conn.commit()
    finally:
        conn.close()


def get_calendar_cashflow(year: int, month: int, uid: int | None = None) -> dict:
    """Calcule le resume financier du mois pour un utilisateur."""
    if uid is None:
        uid = _uid()
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT COALESCE(SUM(pe.amount), 0) AS total_predicted
               FROM planned_expenses pe
               WHERE pe.user_id = ?
                 AND strftime('%Y', pe.due_date) = ?
                 AND strftime('%m', pe.due_date) = ?
                 AND pe.status = 'predicted'""",
            (uid, str(year), f"{month:02d}"),
        ).fetchone()
        total_predicted = float(row["total_predicted"]) if row else 0.0

        row2 = conn.execute(
            """SELECT COALESCE(SUM(pe.amount), 0) AS total_paid
               FROM planned_expenses pe
               WHERE pe.user_id = ?
                 AND strftime('%Y', pe.due_date) = ?
                 AND strftime('%m', pe.due_date) = ?
                 AND pe.status = 'paid'""",
            (uid, str(year), f"{month:02d}"),
        ).fetchone()
        total_paid = float(row2["total_paid"]) if row2 else 0

        row3 = conn.execute(
            "SELECT COUNT(*) AS n FROM subscriptions WHERE user_id = ?",
            (uid,),
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
