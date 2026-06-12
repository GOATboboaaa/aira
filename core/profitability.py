"""
Profitability — analyse de rentabilité par projet.

Calcule pour chaque projet :
  - Son CA net après URSSAF + IR (pro-rata du CA total)
  - Sa part proportionnelle des dépenses
  - Sa marge nette réelle

Principe : les charges sont réparties proportionnellement au CA de chaque projet.
Pas de table de liaison projet-dépense pour l'instant.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from core import models, fiscal


@dataclass
class ProjetRentability:
    id: int
    client: str
    projet: str
    tarif: float
    part_ca: float  # % du CA total
    charges_sociales: float  # URSSAF + IR alloué
    depenses_allouees: float  # part des dépenses totales
    cout_total: float  # charges + dépenses
    marge: float  # tarif - cout_total
    marge_pct: float  # marge en % du tarif


def calculer_rentabilite(annee: int) -> list[ProjetRentability]:
    """Analyse la rentabilité de chaque projet pour une année donnée."""
    config = models.get_config()
    df_projets = models.get_projets(annee)
    ca_total = models.ca_encaisse(annee)
    depenses_total = models.total_depenses(annee)

    if df_projets.empty or ca_total <= 0:
        return []

    # Calcul du taux de prélèvement global
    calc_global = fiscal.calculer(ca_total, config)
    taux_global = calc_global.total_prelevements / ca_total if ca_total > 0 else 0

    resultats = []
    for _, row in df_projets.iterrows():
        tarif = float(row["tarif"])
        part = tarif / ca_total if ca_total > 0 else 0

        # Charges sociales proportionnelles au CA du projet
        charges = tarif * taux_global

        # Dépenses proportionnelles
        dep_allouees = depenses_total * part

        cout_total = charges + dep_allouees
        marge = tarif - cout_total
        marge_pct = (marge / tarif * 100) if tarif > 0 else 0

        resultats.append(ProjetRentability(
            id=int(row["id"]),
            client=row["client"],
            projet=row["projet"],
            tarif=tarif,
            part_ca=part * 100,
            charges_sociales=charges,
            depenses_allouees=dep_allouees,
            cout_total=cout_total,
            marge=marge,
            marge_pct=marge_pct,
        ))

    return resultats


def to_dataframe(resultats: list[ProjetRentability]) -> pd.DataFrame:
    """Convertit la liste en DataFrame pour affichage."""
    rows = []
    for r in resultats:
        rows.append({
            "Client": r.client,
            "Projet": r.projet,
            "CA": f"{r.tarif:,.0f} €",
            "Charges": f"{r.charges_sociales:,.0f} €",
            "Dépenses*": f"{r.depenses_allouees:,.0f} €",
            "Marge nette": f"{r.marge:,.0f} €",
            "Marge %": f"{r.marge_pct:.0f}%",
        })
    return pd.DataFrame(rows)
