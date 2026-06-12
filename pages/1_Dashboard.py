"""Page Dashboard Aira : vue d'ensemble économique premium."""

from datetime import date
from textwrap import shorten

import altair as alt
import pandas as pd
import streamlit as st

from core import models, fiscal
from core.components import (
    kpi_card,
    section_header,
    tax_waterfall,
    footer,
    render_sidebar,
)
from core.db import init_db
from core.styles import inject

st.set_page_config(page_title="Aira — Dashboard", page_icon="✦", layout="wide")
init_db()
inject()
render_sidebar("1_Dashboard")

config = models.get_config()
annees = models.annees_disponibles() or [date.today().year]
annee = st.sidebar.selectbox("Année", annees, index=0)

ca_enc = models.ca_encaisse(annee)
ca_fac = models.ca_facture(annee)
ca_att = models.ca_en_attente(annee)
depenses = models.total_depenses(annee)

calc = fiscal.calculer(ca_enc, config)
net_reel = fiscal.ca_net_reel(ca_enc, depenses, config)

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    f"""<div style="display:flex; align-items:flex-end; justify-content:space-between; margin-bottom:1.5rem;">
        <div>
            <div style="color:#64748B; font-size:0.75rem; font-weight:600; text-transform:uppercase; letter-spacing:0.05em;">
                Année {annee}
            </div>
            <div style="color:#F1F5F9; font-size:1.75rem; font-weight:700; letter-spacing:-0.02em;">
                ✦ Aira
            </div>
            <div style="color:#94A3B8; font-size:0.85rem; margin-top:0.15rem;">
                {config.get('type_activite', 'BNC')}
                · {ca_enc:,.0f} € encaissé{ ' · ACRE' if config.get('acre') else '' }
            </div>
        </div>
        <div style="text-align:right;">
            <div style="color:#94A3B8; font-size:0.75rem;">Taux de prélèvement</div>
            <div style="color:#F1F5F9; font-size:1.25rem; font-weight:700;">
                {calc.taux_total:.1f}%
            </div>
        </div>
    </div>""",
    unsafe_allow_html=True,
)

# ─── Ligne KPI principale ─────────────────────────────────────────────────────
col_kpis = st.columns(4, gap="medium")

with col_kpis[0]:
    kpi_card("CA encaissé", f"{ca_enc:,.0f} €",
             help_text="Assiette des cotisations (projets payés)",
             delta=f"{ca_fac:,.0f} € facturé" if ca_fac != ca_enc else None)

with col_kpis[1]:
    pct_prelev = calc.taux_total
    kpi_card("Prélèvements", f"{calc.total_prelevements:,.0f} €",
             delta=f"{pct_prelev:.1f} % du CA",
             delta_color="inverse",
             help_text="URSSAF + Versement libératoire IR")

with col_kpis[2]:
    kpi_card("Dépenses réelles", f"{depenses:,.0f} €",
             help_text="Non déductibles fiscalement, impactent la trésorerie",
             delta_color="inverse")

with col_kpis[3]:
    delta_color = "normal" if net_reel >= 0 else "inverse"
    delta_str = f"+{net_reel:,.0f} €" if net_reel >= 0 else f"{net_reel:,.0f} €"
    kpi_card("Résultat net", f"{net_reel:,.0f} €",
             delta=delta_str if ca_enc > 0 else None,
             delta_color=delta_color,
             help_text="CA encaissé − prélèvements − dépenses réelles")

# ─── Section : Détail des prélèvements ────────────────────────────────────────
section_header("Répartition du CA", badge="Revenus - Charges")

c_left, c_right = st.columns([1.4, 1], gap="large")

with c_left:
    if ca_enc > 0:
        tax_waterfall(
            urssaf=calc.cotisations_urssaf,
            impot=calc.impot,
            depenses=depenses,
            reste=net_reel,
        )
    else:
        st.info("Ajoute des projets payés pour voir la répartition.")

    # ─── Graphique mensuel ───
    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
    section_header("Évolution mensuelle")
    df_mois = models.ca_mensuel(annee)
    if not df_mois.empty:
        chart = (
            alt.Chart(df_mois)
            .mark_bar(
                cornerRadiusTopLeft=4,
                cornerRadiusTopRight=4,
                color="#7C5CFC",
                opacity=0.85,
            )
            .encode(
                x=alt.X("mois:N", title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("ca:Q", title=None),
                tooltip=[
                    alt.Tooltip("mois:N", title="Mois"),
                    alt.Tooltip("ca:Q", title="CA", format=",.0f"),
                ],
            )
            .properties(height=200)
            .configure_view(strokeWidth=0)
            .configure_axis(
                gridColor="#2A2A3A",
                labelColor="#94A3B8",
                titleColor="#94A3B8",
                tickColor="#2A2A3A",
            )
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.caption("Aucun encaissement ce mois-ci.")

with c_right:
    # ─── Encart — Ce qu'il faut provisionner ───
    section_header("À provisionner")
    provision = calc.total_prelevements
    st.markdown(
        f"""<div style="background:#1A1A24; border:1px solid #2A2A3A; border-radius:12px; padding:1.25rem;">
            <div style="color:#94A3B8; font-size:0.7rem; font-weight:600; text-transform:uppercase;
                        letter-spacing:0.05em; margin-bottom:0.5rem;">
                Sur {ca_enc:,.0f} € encaissés
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
                <span style="color:#F1F5F9; font-size:1.25rem;">Mets de côté</span>
                <span style="color:#7C5CFC; font-size:1.75rem; font-weight:700;">{provision:,.0f} €</span>
            </div>
            <div style="display:flex; gap:1rem; margin-bottom:1rem;">
                <div style="flex:1; background:#14141E; border-radius:8px; padding:0.5rem 0.75rem;">
                    <div style="color:#94A3B8; font-size:0.65rem; text-transform:uppercase;">URSSAF</div>
                    <div style="color:#A78BFA; font-size:1rem; font-weight:600;">{calc.cotisations_urssaf:,.0f} €</div>
                </div>
                <div style="flex:1; background:#14141E; border-radius:8px; padding:0.5rem 0.75rem;">
                    <div style="color:#94A3B8; font-size:0.65rem; text-transform:uppercase;">Impôt (IR)</div>
                    <div style="color:#06B6D4; font-size:1rem; font-weight:600;">{calc.impot:,.0f} €</div>
                </div>
            </div>
            <div style="background:#14141E; border-radius:6px; padding:0.5rem 0.75rem;">
                <div style="display:flex; justify-content:space-between; font-size:0.8rem;">
                    <span style="color:#94A3B8;">Taux URSSAF</span>
                    <span style="color:#F1F5F9; font-weight:600;">{calc.taux_urssaf:.1f}%</span>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-top:0.25rem;">
                    <span style="color:#94A3B8;">Taux IR (vl)</span>
                    <span style="color:#F1F5F9; font-weight:600;">{calc.taux_ir:.1f}%</span>
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # ─── Encart — Projets en attente ───
    if ca_att > 0:
        st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
        section_header("Encaissements à venir")
        st.markdown(
            f"""<div style="background:#1A1A24; border:1px solid #2A2A3A; border-radius:12px; padding:1.25rem;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="color:#94A3B8;">En attente de paiement</span>
                    <span style="color:#F59E0B; font-size:1.25rem; font-weight:700;">{ca_att:,.0f} €</span>
                </div>
                <div style="margin-top:0.5rem; color:#64748B; font-size:0.8rem;">
                    Provision supplémentaire : <strong style="color:#F1F5F9;">{ca_att * calc.taux_total / 100:,.0f} €</strong>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

    # ─── Encart — Info fiscale ───
    if config.get("acre"):
        st.info("ACRE active : cotisations URSSAF réduites de 50 %.")
    if not config.get("versement_liberatoire"):
        st.warning("Versement libératoire désactivé — l'IR sera calculé au barème.")

# ─── Section : Projets récents ──────────────────────────────────────────────
section_header("Derniers projets")
df_projets = models.get_projets(annee)
if not df_projets.empty:
    display = df_projets[["client", "projet", "tarif", "statut", "date_encaiss"]].head(5).copy()
    display["tarif"] = display["tarif"].apply(lambda x: f"{x:,.0f} €")
    display["date_encaiss"] = display["date_encaiss"].fillna("—")
    st.dataframe(display, use_container_width=True, hide_index=True,
                 column_config={
                     "tarif": st.column_config.TextColumn("Montant"),
                     "statut": st.column_config.TextColumn("Statut"),
                 })
else:
    st.caption("Aucun projet enregistré pour cette année.")

# ─── Section : Rentabilité par projet ──────────────────────────────────────
if ca_enc > 0 and not df_projets.empty:
    from core.profitability import calculer_rentabilite, to_dataframe
    renta = calculer_rentabilite(annee)
    if renta:
        section_header("Rentabilité par projet")
        st.caption(
            "* Les dépenses sont réparties proportionnellement au CA de chaque projet. "
            "Pour une allocation précise, associe chaque dépense à un projet."
        )
        df_renta = to_dataframe(renta)
        st.dataframe(df_renta, use_container_width=True, hide_index=True)

        # Mini barres de marge
        st.markdown("#### Marges")
        for r in renta:
            color = "#10B981" if r.marge_pct >= 30 else ("#F59E0B" if r.marge_pct >= 10 else "#F43F5E")
            st.markdown(
                f"""<div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:0.4rem;">
                    <div style="width:120px; color:#94A3B8; font-size:0.8rem; flex-shrink:0;">
                        {r.client}
                    </div>
                    <div style="flex:1; height:20px; background:#14141E; border-radius:4px; overflow:hidden;">
                        <div style="width:{max(r.marge_pct, 0):.0f}%; height:100%;
                                    background:{color}; border-radius:4px; min-width:4px;"></div>
                    </div>
                    <div style="width:60px; color:{color}; font-size:0.8rem; font-weight:600; text-align:right; flex-shrink:0;">
                        {r.marge_pct:.0f}%
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )
        st.caption("👆 La marge cible recommandée est > 50 % (après charges + dépenses).")

footer()
