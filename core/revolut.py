"""
Import et categorisation des transactions Revolut (CSV).

Format CSV Revolut typique (export "Account statement") :
    Type, Product, Started Date, Completed Date, Description,
    Amount, Fee, Currency, State, Balance

- Amount negatif  => depense
- Amount positif  => revenu (encaissement)

La categorisation s'appuie sur les regles stockees en base
(table regles_categorisation : motif -> categorie).
"""

from __future__ import annotations

import io

import pandas as pd

# Mapping souple des noms de colonnes possibles -> nom interne
COLONNES_DATE = ["Completed Date", "Started Date", "Date completed", "Date"]
COLONNES_DESC = ["Description", "Reference", "Merchant"]
COLONNES_AMOUNT = ["Amount", "Montant"]
COLONNES_FEE = ["Fee", "Frais"]
COLONNES_STATE = ["State", "Status", "Statut"]


def _trouver_colonne(df: pd.DataFrame, candidats: list[str]) -> str | None:
    for c in candidats:
        if c in df.columns:
            return c
    # recherche insensible a la casse
    lower = {col.lower(): col for col in df.columns}
    for c in candidats:
        if c.lower() in lower:
            return lower[c.lower()]
    return None


def categoriser(description: str, regles: list[dict]) -> str:
    """Retourne la categorie d'une transaction selon les regles (sinon 'Autre')."""
    desc = (description or "").upper()
    for r in regles:
        if r["type"] == "depense" and r["motif"].upper() in desc:
            return r["categorie"]
    return "Autre"


def parser_csv(contenu: bytes, regles: list[dict]) -> pd.DataFrame:
    """
    Parse un CSV Revolut et retourne un DataFrame normalise avec colonnes :
        date, description, montant, type ('depense'|'revenu'),
        categorie, moyen_paiement, revolut_ref

    `revolut_ref` est une cle de deduplication construite a partir de
    date + description + montant.
    """
    df = pd.read_csv(io.BytesIO(contenu))

    col_date = _trouver_colonne(df, COLONNES_DATE)
    col_desc = _trouver_colonne(df, COLONNES_DESC)
    col_amount = _trouver_colonne(df, COLONNES_AMOUNT)
    col_fee = _trouver_colonne(df, COLONNES_FEE)
    col_state = _trouver_colonne(df, COLONNES_STATE)

    if not (col_date and col_amount):
        raise ValueError(
            "CSV non reconnu : colonnes date/montant introuvables. "
            f"Colonnes detectees : {list(df.columns)}"
        )

    # Ne garder que les transactions completees si l'info existe
    if col_state:
        df = df[
            df[col_state]
            .astype(str)
            .str.upper()
            .isin(["COMPLETED", "COMPLETE", "TERMINE", "OK"])
        ]

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(df[col_date], errors="coerce").dt.strftime("%Y-%m-%d")
    out["description"] = df[col_desc].astype(str) if col_desc else ""

    montant = pd.to_numeric(df[col_amount], errors="coerce").fillna(0.0)
    if col_fee:
        fee = pd.to_numeric(df[col_fee], errors="coerce").fillna(0.0)
        # Les frais sont une depense supplementaire
        montant = montant - fee
    out["montant_signe"] = montant

    out["type"] = out["montant_signe"].apply(lambda m: "revenu" if m > 0 else "depense")
    # Montant absolu pour le stockage
    out["montant"] = out["montant_signe"].abs()

    out["categorie"] = out["description"].apply(lambda d: categoriser(d, regles))
    out["moyen_paiement"] = "Revolut"

    # Cle de deduplication stable
    out["revolut_ref"] = (
        out["date"].astype(str)
        + "|"
        + out["description"].astype(str).str[:40]
        + "|"
        + out["montant_signe"].round(2).astype(str)
    )

    out = out.dropna(subset=["date"])
    return out[
        [
            "date",
            "description",
            "montant",
            "type",
            "categorie",
            "moyen_paiement",
            "revolut_ref",
        ]
    ].reset_index(drop=True)


# =============================================================================
# DOCUMENTATION API REVOLUT BUSINESS (Option B)
# =============================================================================

DOC_API_REVOLUT = """
### Option B - Connexion API Revolut Business (synchronisation directe)

L'API n'est disponible que sur un **compte Revolut Business** (pas sur un
compte personnel/particulier).

**1. Activer l'API**
- Se connecter au portail Business : https://business.revolut.com
- Aller dans **Settings -> API** (ou **APIs -> Merchant/Business API**).
- Choisir l'API **Business** (pour lister tes comptes et transactions).

**2. Generer les identifiants (OAuth 2.0 + cle privee)**
- Generer une paire de cles (cle privee + certificat X.509 auto-signe).
- Uploader le **certificat public** sur le portail.
- Recuperer le **Client ID** (issuer) fourni par Revolut.
- Le flux utilise un **JWT signe** avec ta cle privee pour obtenir
  un *access_token* (valable ~40 min) et un *refresh_token*.

**3. Endpoints utiles (base : https://b2b.revolut.com/api/1.0/)**
- `GET /accounts`              -> liste de tes comptes
- `GET /transactions`          -> transactions (filtrage par date `from`/`to`)
- `GET /transaction/{id}`      -> detail d'une transaction

**4. Boucle de synchronisation (pseudo-code)**
```python
import requests, jwt, time

def get_access_token(client_id, private_key, refresh_token):
    assertion = jwt.encode(
        {
            "iss": "ton-domaine.com",
            "sub": client_id,
            "aud": "https://revolut.com",
            "exp": int(time.time()) + 300,
        },
        private_key,
        algorithm="RS256",
    )
    r = requests.post(
        "https://b2b.revolut.com/api/1.0/auth/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_assertion_type":
                "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": assertion,
        },
    )
    return r.json()["access_token"]

def fetch_transactions(token, date_from):
    r = requests.get(
        "https://b2b.revolut.com/api/1.0/transactions",
        headers={"Authorization": f"Bearer {token}"},
        params={"from": date_from, "count": 1000},
    )
    return r.json()
```

**5. Integration dans ce dashboard**
- Stocker `client_id`, la cle privee et le `refresh_token` dans un fichier
  `.streamlit/secrets.toml` (jamais dans le code, jamais sur Git).
- Mapper chaque transaction sur le meme schema que l'import CSV
  (date, description, montant, type) puis reutiliser `categoriser()` et
  l'insertion anti-doublon via `revolut_ref` (= l'`id` Revolut, ideal).

> En V1, l'import CSV couvre 100 % du besoin sans authentification.
> L'API n'apporte que l'automatisation de la recuperation.
"""
