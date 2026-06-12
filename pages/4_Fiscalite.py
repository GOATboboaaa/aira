"""
Page Fiscalite Aira : parametres fiscaux, waterfall, seuils.
"""

from datetime import date

import streamlit as st

from core import auth, models, fiscal
from core.components import section_header, tax_waterfall, footer, render_sidebar
from core.db import init_db
from core.styles import inject

st.set_page_config(page_title="Aira — Fiscalité", page_icon="✦", layout="wide")
init_db()
inject()
auth.require_auth()
render_sidebar("4_Fiscalite")

st.title("💰 Fiscalité")

annees = models.annees_disponibles() or [date.today().year]
annee = st.sidebar.selectbox("Année", annees, index=0)

config = models.get_config()
ca_enc = models.ca_encaisse(annee)
calc = fiscal.calculer(ca_enc, config)

# ─── Paramètres fiscaux ────────────────────────────────────────────────────
with st.expander("⚙️ Paramètres fiscaux", expanded=False):
    st.caption(
        "Valeurs par défaut : BNC, versement libératoire, "
        "25,6 % + 2,2 % = 27,8 % du CA encaissé."
    )
    with st.form("config_fiscale"):
        c1, c2, c3 = st.columns(3)
        with c1:
            type_activite = st.selectbox(
                "Type d'activité",
                ["BNC", "BIC_service"],
                index=0 if config.get("type_activite") == "BNC" else 1,
            )
            annee_ref = st.number_input(
                "Année de référence", min_value=2020, max_value=2100,
                value=int(config.get("annee_reference", 2025)),
            )
        with c2:
            taux_urssaf = st.number_input(
                "Taux URSSAF %", min_value=0.0, max_value=100.0,
                value=float(config.get("taux_urssaf", 25.6)),
                step=0.1, format="%.2f",
            )
            taux_ir = st.number_input(
                "Taux IR (vl) %", min_value=0.0, max_value=100.0,
                value=float(config.get("taux_ir", 2.2)),
                step=0.1, format="%.2f",
            )
        with c3:
            versement_lib = st.checkbox(
                "Versement libératoire",
                value=bool(config.get("versement_liberatoire", 1)),
            )
            acre = st.checkbox("ACRE (1ʳᵉ année)",
                               value=bool(config.get("acre", 0)))
            date_debut = st.date_input(
                "Début d'activité",
                value=(date.fromisoformat(config["date_debut_activite"])
                       if config.get("date_debut_activite")
                       else date.today()),
            )

        if st.form_submit_button("💾 Sauvegarder", type="primary"):
            models.update_config(
                type_activite=type_activite,
                versement_liberatoire=int(versement_lib),
                acre=int(acre),
                taux_urssaf=taux_urssaf,
                taux_ir=taux_ir,
                annee_reference=int(annee_ref),
                date_debut_activite=date_debut.isoformat(),
            )
            st.success("✅ Paramètres sauvegardés.")
            st.rerun()

st.divider()

# ─── Calcul en temps réel ─────────────────────────────────────────────────
config = models.get_config()
calc = fiscal.calculer(ca_enc, config)

section_header(f"Prélèvements {annee}", badge=f"{ca_enc:,.0f} € encaissé")

# KPIs
c1, c2, c3, c4 = st.columns(4, gap="medium")
c1.metric("Cotisations URSSAF", f"{calc.cotisations_urssaf:,.2f} €",
          help=f"{calc.taux_urssaf:.2f} % du CA")
c2.metric("Impôt (IR)", f"{calc.impot:,.2f} €",
          help=f"{calc.taux_ir:.2f} % du CA")
c3.metric("Total prélèvements", f"{calc.total_prelevements:,.2f} €",
          help=f"{calc.taux_total:.2f} % du CA")
c4.metric("CA net (après)", f"{calc.ca_net_fiscal:,.2f} €")
# Pas de delta_color "inverse" ici car le help suffit

# Waterfall
if ca_enc > 0:
    tax_waterfall(
        urssaf=calc.cotisations_urssaf,
        impot=calc.impot,
        depenses=0,
        reste=calc.ca_net_fiscal,
    )

# Infos ACRE / VL
if config.get("acre"):
    st.info("📌 ACRE active : cotisations URSSAF réduites de 50 %.")
if not config.get("versement_liberatoire"):
    st.warning(
        "⚠️ Versement libératoire désactivé : l'IR n'est pas prélevé à la source. "
        f"Bénéfice imposable estimé : "
        f"{ca_enc * (1 - fiscal.taux.ABATTEMENT_BNC):,.0f} €."
    )

st.divider()

# ─── Seuils ────────────────────────────────────────────────────────────────
section_header("Seuils à surveiller")

etats = fiscal.etat_seuils(ca_enc, config, annee)
alertes = fiscal.alertes_seuils(etats)

for msg in alertes:
    if msg.startswith("DEPASSEMENT"):
        st.error(f"🚨 {msg}")
    else:
        st.warning(f"⚠️ {msg}")

for e in etats:
    pct = min(e.pourcentage, 1.0)
    st.markdown(
        f"**{e.label}** — {e.montant:,.0f} / {e.seuil:,.0f} € "
        f"({e.pourcentage * 100:.1f} %)"
    )
    st.progress(pct)

with st.expander("📘 Rappel des seuils 2025"):
    st.markdown(
        f"""
        - **Franchise TVA** : {fiscal.taux.SEUIL_TVA:,.0f} €
          (seuil majoré : {fiscal.taux.SEUIL_TVA_MAJORE:,.0f} €)
        - **Plafond micro-entreprise** : {fiscal.taux.PLAFOND_MICRO:,.0f} €
        - Seuils **proratisés** la 1ʳᵉ année selon la date de début d'activité.
        """
    )

footer()
