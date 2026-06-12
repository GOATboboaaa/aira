"""Page Calendrier Aira : abonnements, prévisions, et indicateur de trésorerie.

Interface :
  - Cashflow indicator (total abonnements du mois + nombre d'abonnements)
  - Grille calendrier mensuelle avec badges colorés par dépense planifiée
  - Ajout manuel d'abonnement
  - Gestion des abonnements existants
"""

from __future__ import annotations

import calendar as cal_mod
from datetime import date, datetime

import streamlit as st

from core import auth, models
from core.components import footer, render_sidebar, page_header
from core.db import init_db
from core.styles import inject

st.set_page_config(page_title="Aira — Calendrier", page_icon="✦", layout="wide")
init_db()
inject()
render_sidebar("6_Calendrier")
auth.require_auth()

# ─── Gestion mois courant ───────────────────────────────────────────────────
today = date.today()
annee_courante = today.year
mois_courant = today.month

if "cal_year" not in st.session_state:
    st.session_state.cal_year = annee_courante
if "cal_month" not in st.session_state:
    st.session_state.cal_month = mois_courant

# ─── Barre de contrôle mois/année ───────────────────────────────────────────
page_header("📅 Calendrier", "Abonnements, dépenses récurrentes et prévisions")

col_nav, col_filler = st.columns([2, 6])
with col_nav:
    st.markdown("### Navigation")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        if st.button("◀", key="prev_month"):
            if st.session_state.cal_month == 1:
                st.session_state.cal_month = 12
                st.session_state.cal_year -= 1
            else:
                st.session_state.cal_month -= 1
            st.rerun()
    with c2:
        st.markdown(
            f"<div style='text-align:center;font-size:1.1rem;font-weight:700;"
            f"color:#F1F5F9;'>{datetime(st.session_state.cal_year, st.session_state.cal_month, 1).strftime('%B %Y')}</div>",
            unsafe_allow_html=True,
        )
    with c3:
        if st.button("▶", key="next_month"):
            if st.session_state.cal_month == 12:
                st.session_state.cal_month = 1
                st.session_state.cal_year += 1
            else:
                st.session_state.cal_month += 1
            st.rerun()

st.divider()

# ─── Cashflow indicator ─────────────────────────────────────────────────────
# Génère les planned_expenses pour le mois courant (si abonnements existent)
subs = models.get_subscriptions_list()
if subs:
    models.generate_planned_expenses(st.session_state.cal_year, st.session_state.cal_month)

cf = models.get_calendar_cashflow(st.session_state.cal_year, st.session_state.cal_month)

st.markdown("### Résumé du mois")
kpi_cols = st.columns(4, gap="medium")
with kpi_cols[0]:
    st.metric(
        label="Abonnements actifs",
        value=f"{cf['abos_count']}",
    )
with kpi_cols[1]:
    st.metric(
        label="À prévoir ce mois-ci",
        value=f"{cf['total_predicted']:,.2f} €",
        delta=f"{-cf['total_predicted']:,.2f} €" if cf["total_predicted"] > 0 else None,
        delta_color="inverse",
    )
with kpi_cols[2]:
    st.metric(
        label="Déjà payé",
        value=f"{cf['total_paid']:,.2f} €",
    )
with kpi_cols[3]:
    st.metric(
        label="Total abonnements",
        value=f"{cf['total_all']:,.2f} €",
    )

st.divider()

# ─── Calendrier Mensuel (grille HTML/CSS) ──────────────────────────────────
year = st.session_state.cal_year
month = st.session_state.cal_month

# Récupérer les dépenses planifiées
df_planned = models.get_planned_expenses(year, month)

# Indexer par jour
expenses_by_day: dict[int, list[dict]] = {}
for _, row in df_planned.iterrows():
    try:
        d = int(row["due_date"][8:10])
    except (ValueError, IndexError):
        continue
    if d not in expenses_by_day:
        expenses_by_day[d] = []
    expenses_by_day[d].append(dict(row))

# Couleurs par fréquence
freq_colors = {
    "monthly": "#7C5CFC",
    "yearly": "#F59E0B",
    "weekly": "#06B6D4",
    None: "#94A3B8",
}

# Construire la grille
cal = cal_mod.Calendar(firstweekday=0)  # Lundi premier jour
month_days = cal.monthdayscalendar(year, month)

# En-tête des jours
day_names = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]

rows_html = ""
for week in month_days:
    cells = ""
    for i, day in enumerate(week):
        if day == 0:
            cells += '<td class="cal-empty"></td>'
        else:
            is_today = (day == today.day and month == today.month and year == today.year)
            today_cls = " cal-today" if is_today else ""
            day_expenses = expenses_by_day.get(day, [])

            # Badges HTML pour chaque dépense
            badges_html = ""
            for exp in day_expenses:
                color = freq_colors.get(exp.get("frequency"), "#7C5CFC")
                paid = exp.get("status") == "paid"
                amt = exp["amount"]
                name = exp["name"][:12] + "…" if len(str(exp["name"])) > 12 else exp["name"]
                paid_cls = " cal-paid" if paid else ""
                badges_html += (
                    f'<div class="cal-badge{paid_cls}" '
                    f'style="background:{color}22;border-left:2px solid {color};'
                    f'color:{color};">'
                    f'{amt:,.0f}€ {name}</div>'
                )

            cells += (
                f'<td class="cal-day{today_cls}">'
                f'<div class="cal-day-num">{day}</div>'
                f'{badges_html}</td>'
            )
    rows_html += f"<tr>{cells}</tr>"

# CSS pour le calendrier
cal_css = """
<style>
.cal-table {
    width: 100%;
    border-collapse: collapse;
    background: #1A1A24;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #2A2A3A;
}
.cal-table th {
    background: #14141E;
    color: #94A3B8;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0.6rem 0.3rem;
    text-align: center;
    border-bottom: 1px solid #2A2A3A;
}
.cal-table td {
    vertical-align: top;
    padding: 0.35rem;
    border: 1px solid #2A2A3A;
    width: 14.28%;
    height: 95px;
    min-height: 80px;
}
.cal-empty {
    background: #14141E22;
}
.cal-day {
    background: #1A1A24;
    transition: background 0.15s;
}
.cal-day:hover {
    background: #222233;
}
.cal-today {
    background: rgba(124, 92, 252, 0.06) !important;
    box-shadow: inset 0 0 0 1px #7C5CFC55;
}
.cal-day-num {
    font-size: 0.75rem;
    font-weight: 700;
    color: #F1F5F9;
    margin-bottom: 0.25rem;
}
.cal-today .cal-day-num {
    color: #A78BFA;
}
.cal-badge {
    font-size: 0.6rem;
    font-weight: 500;
    padding: 0.12rem 0.3rem;
    margin-bottom: 0.15rem;
    border-radius: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.3;
}
.cal-paid {
    opacity: 0.4;
    text-decoration: line-through;
}
@media (max-width: 768px) {
    .cal-table td { height: 70px; min-height: 60px; padding: 0.2rem; }
    .cal-badge { font-size: 0.5rem; }
}
</style>
"""

st.markdown(cal_css + f"""
<table class="cal-table">
<thead><tr>{"".join(f'<th>{n}</th>' for n in day_names)}</tr></thead>
<tbody>{rows_html}</tbody>
</table>
""", unsafe_allow_html=True)

# ─── Section Ajout / Gestion Abonnements ───────────────────────────────────
st.divider()

tab_ajout, tab_liste = st.tabs(["➕ Ajouter un abonnement", "📋 Gérer les abonnements"])

with tab_ajout:
    st.markdown("### Nouvel abonnement")
    with st.form("add_subscription", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Nom de l'abonnement",
                                 placeholder="ex: Adobe Creative Cloud")
            amount = st.number_input("Montant (€)", min_value=0.01, step=0.50,
                                     format="%.2f")
        with c2:
            frequency = st.selectbox("Fréquence", ["monthly", "yearly", "weekly"],
                                     format_func=lambda x: {
                                         "monthly": "Mensuel",
                                         "yearly": "Annuel",
                                         "weekly": "Hebdomadaire",
                                     }[x])
            billing_day = st.number_input("Jour de prélèvement (1-31)",
                                          min_value=1, max_value=31, value=1)
        category = st.text_input("Catégorie", value="Abonnements logiciels",
                                 placeholder="ex: Abonnements logiciels")
        submitted = st.form_submit_button("➕ Ajouter au calendrier",
                                          type="primary",
                                          use_container_width=True)
        if submitted and name and amount > 0:
            sub_id = models.add_subscription(
                name=name.strip(),
                amount=amount,
                frequency=frequency,
                billing_day=billing_day,
                category=category.strip() or "Abonnements logiciels",
                is_manual=True,
            )
            models.generate_planned_expenses(year, month)
            st.success(f"✅ Abonnement « {name} » ajouté au calendrier !")
            st.rerun()

with tab_liste:
    st.markdown("### Abonnements enregistrés")
    if not subs:
        st.info("Aucun abonnement pour le moment. Ajoutes-en un ou importe un CSV avec détection automatique.")
    else:
        df_subs = models.get_subscriptions()
        # Colonnes lisibles
        df_display = df_subs.copy()
        df_display["Fréquence"] = df_display["frequency"].map({
            "monthly": "Mensuel",
            "yearly": "Annuel",
            "weekly": "Hebdomadaire",
        })
        df_display["Montant"] = df_display["amount"].apply(lambda x: f"{x:.2f} €")
        df_display["Jour"] = df_display["billing_day"]
        df_display["Catégorie"] = df_display["category"]
        df_display["Manuel"] = df_display["is_manual"].apply(lambda x: "✅ Oui" if x else "🤖 Auto")
        df_display["Détecté le"] = df_display["last_detected"].fillna("—")

        show_cols = ["name", "Montant", "Fréquence", "Jour", "Catégorie", "Manuel", "Détecté le"]
        st.dataframe(
            df_display[show_cols].rename(columns={"name": "Nom"}),
            use_container_width=True,
            hide_index=True,
        )

        # Supprimer un abonnement
        st.markdown("**Supprimer un abonnement**")
        sub_choices = {f"{r['id']} — {r['name']} ({r['amount']:.2f}€)": r['id']
                       for r in subs}
        sub_names = ["— Sélectionne un abonnement —"] + list(sub_choices.keys())
        to_del = st.selectbox(
            "Choisis l'abonnement à supprimer",
            sub_names,
            key="del_sub",
        )
        if st.button(
            "🗑 Supprimer définitivement",
            use_container_width=True,
            type="primary",
            disabled=(to_del == sub_names[0]),
        ):
            if to_del != sub_names[0]:
                sid = sub_choices[to_del]
                deleted = models.delete_subscription(sid)
                if deleted:
                    st.success("✅ Abonnement supprimé (ses occurrences dans le calendrier ont été retirées).")
                else:
                    st.warning("Abonnement introuvable — peut-être déjà supprimé.")
                st.rerun()

        # Régénérer les planned_expenses
        if st.button("🔄 Régénérer les prévisions", use_container_width=True):
            models.generate_planned_expenses(year)
            st.success("✅ Prévisions régénérées pour toute l'année.")
            st.rerun()

footer()
