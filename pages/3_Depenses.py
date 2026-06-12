"""
Page Depenses Aira : suivi des depenses, categories et edition.
"""

from datetime import date

import pandas as pd
import streamlit as st

from core import auth, models
from core.components import section_header, footer, render_sidebar
from core.db import init_db
from core.styles import inject
from config import taux

st.set_page_config(page_title="Aira — Dépenses", page_icon="✦", layout="wide")
init_db()
inject()
auth.require_auth()
render_sidebar("3_Depenses")

st.title("🧾 Dépenses")

st.caption(
    "Suivi de tes dépenses réelles (trésorerie). En micro-entreprise, "
    "elles ne sont pas déductibles fiscalement mais impactent ta marge."
)

annees = models.annees_disponibles() or [date.today().year]
annee = st.sidebar.selectbox("Année", ["Toutes"] + annees)

# ─── Stats ──────────────────────────────────────────────────────────────────

df = models.get_depenses(None if annee == "Toutes" else annee)
if not df.empty:
    total = df["montant"].sum()
    nb = len(df)
    top_cat = df.groupby("categorie")["montant"].sum().sort_values(ascending=False)
    cols = st.columns(3, gap="medium")
    cols[0].metric("Dépenses", nb)
    cols[1].metric("Total", f"{total:,.2f} €")
    cols[2].metric("Top catégorie", f"{top_cat.index[0]}" if not top_cat.empty else "—")

# ─── Formulaire d'ajout ────────────────────────────────────────────────────
with st.expander("+ Ajouter une dépense", expanded=False):
    with st.form("ajout_depense", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            d = st.date_input("Date", value=date.today())
            montant = st.number_input("Montant (EUR TTC)", min_value=0.01,
                                      step=10.0, format="%.2f")
            categorie = st.selectbox("Catégorie", taux.CATEGORIES_DEPENSES)
        with col2:
            description = st.text_input("Description", placeholder="ex : Adobe Creative Cloud")
            moyen = st.selectbox("Moyen de paiement",
                                 ["Revolut", "CB", "Virement", "Espèces", "Autre"])

        if st.form_submit_button("Enregistrer la dépense", type="primary"):
            if montant <= 0:
                st.error("Le montant doit être supérieur à 0.")
            else:
                models.add_depense(
                    date=d.isoformat(),
                    montant=montant,
                    categorie=categorie,
                    description=description or None,
                    moyen_paiement=moyen,
                    source="manuel",
                )
                st.success("✅ Dépense ajoutée.")
                st.rerun()

st.divider()

# ─── Liste / édition ──────────────────────────────────────────────────────
if df.empty:
    st.info("Aucune dépense enregistrée.")
else:
    section_header(f"{len(df)} dépense(s) — {total:,.2f} € total",
                   badge=annee if annee != "Toutes" else None)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    edited = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        disabled=["id", "source", "revolut_ref", "created_at"],
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
            "montant": st.column_config.NumberColumn("Montant", format="%.2f €"),
            "categorie": st.column_config.SelectboxColumn(
                "Catégorie", options=taux.CATEGORIES_DEPENSES
            ),
            "description": st.column_config.TextColumn("Description"),
            "moyen_paiement": st.column_config.TextColumn("Paiement"),
        },
        key="editor_depenses",
    )

    col_save, col_del = st.columns([1, 1])
    with col_save:
        if st.button("💾 Enregistrer les modifications", type="primary",
                     use_container_width=True):
            for _, row in edited.iterrows():
                models.update_depense(
                    int(row["id"]),
                    date=row["date"],
                    montant=float(row["montant"]),
                    categorie=row["categorie"],
                    description=row["description"],
                    moyen_paiement=row["moyen_paiement"],
                )
            st.success("✅ Modifications enregistrées.")
            st.rerun()

    with col_del:
        ids = df["id"].tolist()
        del_id = st.selectbox("Supprimer la dépense n°", [""] + ids, key="del_depense")
        if st.button("🗑 Supprimer", use_container_width=True) and del_id != "":
            models.delete_depense(int(del_id))
            st.success(f"Dépense {del_id} supprimée.")
            st.rerun()

footer()
