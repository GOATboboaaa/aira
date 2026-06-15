# ✦ Aira — Pilotage micro-entreprise

Dashboard financier pour créateurs de contenu et monteurs vidéo en micro-entreprise (BNC).

Stack : **Python 3.11+** · **Streamlit** · **SQLite** · **Pandas** · **Altair**

## Installation

```bash
# 1. Cloner
git clone git@github.com:TON_USER/aira.git
cd aira

# 2. (Optionnel) Créer un venv
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# ou .venv\Scripts\activate  # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Lancer
streamlit run app.py
```

Le dashboard est accessible sur **http://localhost:8501**.

## Pages

| Page | Description |
|------|-------------|
| Dashboard | Vue d'ensemble, KPIs, rentabilité par projet |
| Projets | Facturation et suivi des paiements |
| Dépenses | Suivi des dépenses réelles |
| Fiscalité | Calcul URSSAF + IR, seuils |
| Import Revolut | Import CSV Revolut + règles de catégorisation |

## Structure

```
aira/
├── app.py              # Point d'entrée
├── core/               # Moteur métier
│   ├── db.py           # Base SQLite
│   ├── models.py       # CRUD
│   ├── fiscal.py       # Calcul URSSAF/IR
│   ├── components.py   # Composants UI
│   ├── profitability.py# Rentabilité par projet
│   ├── styles.py       # Design System
│   └── revolut.py      # Parser CSV Revolut
├── config/             # Taux et seuils
├── pages/              # Pages Streamlit
├── data/               # SQLite (ignoré par git)
├── .streamlit/         # Thème
└── requirements.txt
```

---

Projet privé · Ne pas partager les données de `data/`.
# Test connexion Mon Jun 15 12:42:07 UTC 2026
