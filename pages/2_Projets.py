"""
Page Projets Aira : gestion des projets, facturation et encaissements.
"""

from datetime import date

import pandas as pd
import streamlit as st

from core import auth, models
from core.components import section_header, footer, render_sidebar
from core.db import init_db
from core.styles import inject

st.set_page_config(page_title="Aira — Projets", page_icon="✦", layout="wide")
init_db()
inject()
render_sidebar("2_Projets")
auth.require_auth()

st.title("🎬 Projets / Facturation")

annees = models.annees_disponibles() or [date.today().year]
annee = st.sidebar.selectbox("Année", ["Toutes"] + annees)

df = models.get_projets(None if annee == "Toutes" else annee)
if not df.empty:
    ca_paye = df[df["statut"] == "Paye"]["tarif"].sum()
    ca_att = df[df["statut"] == "En attente"]["tarif"].sum()
    nb = len(df)
    cols = st.columns(3, gap="medium")
    cols[0].metric("Projets", nb)
    cols[1].metric("Encaissé", f"{ca_paye:,.0f} €")
    cols[2].metric("En attente", f"{ca_att:,.0f} €")

# ─── Formulaire d'ajout ────────────────────────────────────────────────────
with st.expander("+ Ajouter un projet", expanded=False):
    with st.form("ajout_projet", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            client = st.text_input("Client", placeholder="ex : Stundzow")
            projet = st.text_input("Projet", placeholder="ex : Montage Stunt LaSalle")
            tarif = st.number_input("Montant (EUR)", min_value=0.01, step=50.0, format="%.2f")
        with col2:
            date_facture = st.date_input("Date de facture", value=date.today())
            statut = st.selectbox("Statut", ["En attente", "Paye"])
            if statut == "Paye":
                date_encaiss = st.date_input("Date d'encaissement", value=date.today())
            else:
                date_encaiss = None
                st.caption("Date définie après passage en 'Paye'")
        notes = st.text_area("Notes", placeholder="Optionnel : lien vidéo, remarques...")

        if st.form_submit_button("Enregistrer le projet", type="primary"):
            if not client or not projet or tarif <= 0:
                st.error("Client, projet et montant (> 0) sont obligatoires.")
            else:
                models.add_projet(
                    client=client,
                    projet=projet,
                    tarif=tarif,
                    date_facture=date_facture.isoformat(),
                    statut=statut,
                    date_encaiss=date_encaiss.isoformat() if statut == "Paye" else None,
                    notes=notes or None,
                )
                st.success(f"✅ Projet « {projet} » ajouté.")
                st.rerun()

st.divider()

# ─── Liste / édition ──────────────────────────────────────────────────────
if df.empty:
    st.info("Aucun projet enregistré.")
else:
    section_header(f"{len(df)} projet(s)", badge=annee if annee != "Toutes" else None)

    # Marquer le statut avec des emojis
    df_display = df.copy()
    df_display["statut"] = df_display["statut"].apply(
        lambda s: "✅ Payé" if s == "Paye" else "⏳ En attente"
    )
    df_display["tarif"] = df_display["tarif"].apply(lambda x: f"{x:,.2f} €")

    # Convertir les dates string → datetime pour le data_editor
    df["date_facture"] = pd.to_datetime(df["date_facture"], errors="coerce")
    df["date_encaiss"] = pd.to_datetime(df["date_encaiss"], errors="coerce")

    edited = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        disabled=["id", "created_at"],
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "client": st.column_config.TextColumn("Client"),
            "projet": st.column_config.TextColumn("Projet"),
            "tarif": st.column_config.NumberColumn("Montant", format="%.2f €"),
            "date_facture": st.column_config.DateColumn("Date facture", format="DD/MM/YYYY"),
            "date_encaiss": st.column_config.DateColumn("Encaissement", format="DD/MM/YYYY"),
            "statut": st.column_config.SelectboxColumn(
                "Statut", options=["En attente", "Paye"]
            ),
            "notes": st.column_config.TextColumn("Notes"),
        },
        key="editor_projets",
    )

    col_save, col_del = st.columns([1, 1])
    with col_save:
        if st.button("💾 Enregistrer les modifications", type="primary",
                     use_container_width=True):
            for _, row in edited.iterrows():
                models.update_projet(
                    int(row["id"]),
                    client=row["client"],
                    projet=row["projet"],
                    tarif=float(row["tarif"]),
                    date_facture=row["date_facture"],
                    date_encaiss=row["date_encaiss"] if row["date_encaiss"] else None,
                    statut=row["statut"],
                    notes=row["notes"],
                )
            st.success("✅ Modifications enregistrées.")
            st.rerun()

    with col_del:
        ids = df["id"].tolist()
        del_id = st.selectbox("Supprimer le projet n°", [""] + ids, key="del_projet")
        if st.button("🗑 Supprimer", use_container_width=True) and del_id != "":
            models.delete_projet(int(del_id))
            st.success(f"Projet {del_id} supprimé.")
            st.rerun()

    st.caption(
        "💡 Passe un projet en « Payé » et renseigne sa date d'encaissement "
        "pour qu'il entre dans l'assiette des cotisations URSSAF."
    )

footer()
