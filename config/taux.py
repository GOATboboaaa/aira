"""
Taux fiscaux et seuils de la micro-entreprise.

Ces valeurs sont les VALEURS PAR DEFAUT injectees dans la base au premier
lancement. Elles restent ensuite editables depuis la page "Fiscalite".

Configuration utilisateur (validee) :
    - Regime              : BNC
    - Versement liberatoire : OUI
    - Total prelevements  : 27,80 % du CA encaisse
        * dont URSSAF (cotisations sociales) : 25,6 %
        * dont IR (versement liberatoire)    : 2,2 %
    - ACRE : Non

ATTENTION : en micro-entreprise, les cotisations et l'impot (en versement
liberatoire) sont assis sur le CHIFFRE D'AFFAIRES ENCAISSE, sans deduction
des depenses reelles.
"""

# --- Prelevements par defaut (BNC, versement liberatoire) ---------------------
# Total = TAUX_URSSAF + TAUX_IR = 27,80 %
TAUX_URSSAF_DEFAUT = 0.256  # 25,6 % cotisations sociales
TAUX_IR_DEFAUT = 0.022  # 2,2 %  versement liberatoire de l'IR

# Reduction ACRE (1ere annee) : ~50 % sur les cotisations URSSAF uniquement.
TAUX_ACRE = 0.50

# Abattement forfaitaire BNC (utilise uniquement en mode bareme classique,
# affiche a titre informatif puisque l'utilisateur est en versement liberatoire).
ABATTEMENT_BNC = 0.34

# --- Seuils officiels (BNC / prestations de services) -------------------------
# Franchise en base de TVA
SEUIL_TVA = 37_500  # seuil de base
SEUIL_TVA_MAJORE = 41_250  # seuil majore (tolerance)

# Plafond de la micro-entreprise (prestations de services / BNC)
PLAFOND_MICRO = 77_700

# --- Categories de depenses predefinies ---------------------------------------
CATEGORIES_DEPENSES = [
    "Abonnements logiciels",  # Adobe Creative Cloud, Frame.io, etc.
    "Materiel",  # ordinateur, disque dur, peripheriques
    "Sous-traitance",  # minimaker, autres monteurs
    "Banque / Frais",  # frais Revolut, commissions
    "Marketing",  # pub, site web
    "Formation",
    "Deplacements",
    "Autre",
]

# --- Regles de categorisation automatique pour l'import Revolut ---------------
# (motif recherche dans le libelle -> categorie). Insensible a la casse.
REGLES_CATEGORISATION_DEFAUT = [
    ("ADOBE", "Abonnements logiciels", "depense"),
    ("CREATIVE CLOUD", "Abonnements logiciels", "depense"),
    ("FRAME.IO", "Abonnements logiciels", "depense"),
    ("EPIDEMIC", "Abonnements logiciels", "depense"),
    ("ARTLIST", "Abonnements logiciels", "depense"),
    ("MINIMAKER", "Sous-traitance", "depense"),
    ("APPLE", "Materiel", "depense"),
    ("AMAZON", "Materiel", "depense"),
    ("REVOLUT", "Banque / Frais", "depense"),
]
