"""
Moteur de calcul fiscal de la micro-entreprise.

Regle fondamentale : en micro-entreprise, les cotisations URSSAF et l'impot
(en versement liberatoire) sont calcules sur le CHIFFRE D'AFFAIRES ENCAISSE,
SANS deduction des depenses reelles.

Configuration utilisateur :
    - BNC, versement liberatoire active
    - URSSAF 25,6 % + IR 2,2 % = 27,80 % du CA encaisse
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from config import taux


@dataclass
class CalculFiscal:
    """Resultat detaille du calcul fiscal pour un CA donne."""

    ca: float  # CA encaisse (assiette)
    taux_urssaf: float  # taux applique (apres eventuel ACRE)
    taux_ir: float  # taux versement liberatoire
    cotisations_urssaf: float  # montant URSSAF
    impot: float  # montant IR
    total_prelevements: float  # URSSAF + IR
    ca_net_fiscal: float  # CA - prelevements (avant depenses)

    @property
    def taux_total(self) -> float:
        return self.taux_urssaf + self.taux_ir


def calculer(ca: float, config: dict) -> CalculFiscal:
    """
    Calcule les prelevements sur un CA encaisse selon la config fiscale.

    config attendu (depuis models.get_config) :
        taux_urssaf, taux_ir, versement_liberatoire, acre
    """
    taux_urssaf = float(config.get("taux_urssaf", taux.TAUX_URSSAF_DEFAUT))
    taux_ir = float(config.get("taux_ir", taux.TAUX_IR_DEFAUT))

    # ACRE : reduction ~50 % sur les cotisations URSSAF uniquement.
    if config.get("acre"):
        taux_urssaf *= taux.TAUX_ACRE

    # Versement liberatoire desactive => l'IR n'est pas preleve a la source.
    if not config.get("versement_liberatoire", 1):
        taux_ir = 0.0

    cotisations = ca * taux_urssaf / 100
    impot = ca * taux_ir / 100
    total = cotisations + impot

    return CalculFiscal(
        ca=ca,
        taux_urssaf=taux_urssaf,
        taux_ir=taux_ir,
        cotisations_urssaf=cotisations,
        impot=impot,
        total_prelevements=total,
        ca_net_fiscal=ca - total,
    )


def ca_net_reel(ca: float, depenses: float, config: dict) -> float:
    """
    Resultat economique reel = CA - prelevements obligatoires - depenses reelles.
    Les depenses ne sont PAS deductibles fiscalement, mais elles impactent
    la tresorerie : c'est la vraie marge du freelance.
    """
    calc = calculer(ca, config)
    return calc.ca_net_fiscal - depenses


# =============================================================================
# SEUILS (franchise TVA + plafond micro)
# =============================================================================


@dataclass
class EtatSeuil:
    label: str
    seuil: float
    montant: float
    pourcentage: float  # 0.0 -> 1.0+ (peut depasser 100 %)
    depasse: bool


def _prorata_temporis(seuil: float, date_debut: str | None, annee: int) -> float:
    """
    Proratisation du seuil la 1ere annee d'activite (debut en cours d'annee).
    Si pas de date de debut connue, on ne proratise pas.
    """
    if not date_debut:
        return seuil
    try:
        d = date.fromisoformat(date_debut)
    except ValueError:
        return seuil
    if d.year != annee:
        return seuil
    # nombre de jours d'activite sur l'annee / 365
    jours_actifs = (date(annee, 12, 31) - d).days + 1
    return seuil * jours_actifs / 365


def etat_seuils(ca: float, config: dict, annee: int) -> list[EtatSeuil]:
    """
    Retourne l'etat de progression vis-a-vis des seuils :
        - Franchise TVA (base + majore)
        - Plafond micro-entreprise
    """
    date_debut = config.get("date_debut_activite")

    seuil_tva = _prorata_temporis(taux.SEUIL_TVA, date_debut, annee)
    seuil_tva_maj = _prorata_temporis(taux.SEUIL_TVA_MAJORE, date_debut, annee)
    plafond = _prorata_temporis(taux.PLAFOND_MICRO, date_debut, annee)

    def make(label: str, seuil: float) -> EtatSeuil:
        pct = ca / seuil if seuil > 0 else 0.0
        return EtatSeuil(
            label=label,
            seuil=seuil,
            montant=ca,
            pourcentage=pct,
            depasse=ca > seuil,
        )

    return [
        make("Franchise TVA (base)", seuil_tva),
        make("Franchise TVA (seuil majore)", seuil_tva_maj),
        make("Plafond micro-entreprise", plafond),
    ]


def alertes_seuils(etats: list[EtatSeuil]) -> list[str]:
    """Genere des messages d'alerte lisibles selon la proximite des seuils."""
    messages = []
    for e in etats:
        if e.depasse:
            messages.append(
                f"DEPASSEMENT : {e.label} ({e.montant:,.0f} EUR > {e.seuil:,.0f} EUR)."
            )
        elif e.pourcentage >= 0.80:
            messages.append(
                f"ATTENTION : {e.label} a {e.pourcentage * 100:.0f} % "
                f"({e.montant:,.0f} / {e.seuil:,.0f} EUR)."
            )
    return messages
