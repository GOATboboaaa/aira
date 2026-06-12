"""
Aira Components — blocs d'interface réutilisables.

Tous les composants suivent le Aira Design System :
  - Cards, KPIs, badges, barres de progression
  - Tax breakdown waterfall
  - Footer automatique
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st


def kpi_card(label: str, value: str, delta: str | None = None,
             help_text: str | None = None, delta_color: str = "normal"):
    """Affiche une KPI card stylée Aira.

    Utilise le metric-container natif Streamlit avec notre CSS.
    """
    help_kw = {"help": help_text} if help_text else {}
    delta_kw = {"delta": delta, "delta_color": delta_color} if delta else {}
    st.metric(label=label, value=value, **delta_kw, **help_kw)


def section_header(title: str, badge: str | None = None):
    """Affiche un en-tête de section avec badge optionnel."""
    badge_html = f'<span class="badge">{badge}</span>' if badge else ""
    st.markdown(
        f'<div class="section-header"><h2>{title}</h2>{badge_html}</div>',
        unsafe_allow_html=True,
    )


def tax_waterfall(urssaf: float, impot: float, depenses: float,
                  reste: float):
    """Affiche la répartition visuelle du CA en barres horizontales."""
    total = urssaf + impot + depenses + max(reste, 0)
    if total <= 0:
        return

    items = [
        ("URSSAF", urssaf, "#7C5CFC"),
        ("Impôt (IR)", impot, "#06B6D4"),
        ("Dépenses", depenses, "#F59E0B"),
        ("Reste pour toi", max(reste, 0), "#10B981" if reste >= 0 else "#F43F5E"),
    ]
    items = [(l, v, c) for l, v, c in items if v > 0]
    if reste < 0:
        items.append(("Perte nette", abs(reste), "#F43F5E"))

    st.markdown(
        "<div style='margin-bottom:0.5rem;color:#94A3B8;font-size:0.7rem;"
        "font-weight:600;text-transform:uppercase;letter-spacing:0.05em;'>"
        "Répartition du CA encaissé</div>",
        unsafe_allow_html=True,
    )

    for label, val, color in items:
        pct = val / total * 100
        cols = st.columns([1, 6, 1], gap="small")
        cols[0].markdown(
            f"<div style='text-align:right;color:#94A3B8;font-size:0.75rem;'>"
            f"{label}</div>",
            unsafe_allow_html=True,
        )
        # Colored bar via inline HTML (specific color per category)
        cols[1].markdown(
            f"<div style='height:22px;background:#14141E;border-radius:6px;overflow:hidden;'>"
            f"<div style='width:{pct:.1f}%;height:100%;background:{color};"
            f"border-radius:6px;min-width:4px;'></div></div>",
            unsafe_allow_html=True,
        )
        cols[2].markdown(
            f"<div style='color:#F1F5F9;font-weight:600;font-size:0.75rem;'>"
            f"{val:,.0f} €</div>",
            unsafe_allow_html=True,
        )


def stat_badge(label: str, value: str, color: str = "#7C5CFC"):
    """Petit badge statistique inline."""
    st.markdown(
        f"""<div style="display:inline-flex; align-items:center; gap:0.4rem;
            background:rgba({','.join(str(int(c,16)) for c in [color[1:3],color[3:5],color[5:7]])},0.1);
            border:1px solid rgba({','.join(str(int(c,16)) for c in [color[1:3],color[3:5],color[5:7]])},0.2);
            border-radius:8px; padding:0.3rem 0.7rem; font-size:0.75rem;">
            <span style="color:{color}; font-weight:600;">{value}</span>
            <span style="color:#94A3B8;">{label}</span>
        </div>""",
        unsafe_allow_html=True,
    )


def montant_text(value: float, currency: str = "EUR",
                 color_negative: bool = True) -> str:
    """Formate un montant avec couleur conditionnelle."""
    color = ""
    if color_negative and value < 0:
        color = ' style="color:#F43F5E"'
    elif color_negative and value > 0:
        color = ' style="color:#10B981"'
    return f'<span{color}>{value:,.2f} {currency}</span>'


def footer():
    """Pied de page Aira."""
    st.markdown(
        '<div class="app-footer">'
        'Aira · <span>✦</span> · Pilotage micro-entreprise'
        '</div>',
        unsafe_allow_html=True,
    )


def render_sidebar(page_title: str | None = None):
    """Sidebar Aira partage — logo, navigation, user info, apercu rapide.

    A appeler au debut de chaque page (apres set_page_config).
    """
    from core import auth as auth_mod

    pages = [
        ("📊 Dashboard", "1_Dashboard"),
        ("🎬 Projets", "2_Projets"),
        ("🧾 Dépenses", "3_Depenses"),
        ("📅 Calendrier", "6_Calendrier"),
        ("💰 Fiscalité", "4_Fiscalite"),
        ("💳 Import Revolut", "5_Import_Revolut"),
    ]

    with st.sidebar:
        st.markdown(
            """<div class="sidebar-header">
                <div style="color:#7C5CFC; font-size:1.25rem; font-weight:700; letter-spacing:-0.02em;">
                    ✦ Aira
                </div>
                <div style="color:#64748B; font-size:0.75rem; margin-top:0.15rem;">
                    Pilotage micro-entreprise
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

        # ─── User info + Logout ────────────────────────────────────────────
        user_email = auth_mod.get_current_user_email()
        if user_email:
            st.markdown(
                f"""<div style="background:#14141E; border-radius:8px; padding:0.5rem 0.75rem;
                            margin-bottom:1rem;">
                    <div style="color:#94A3B8; font-size:0.65rem; text-transform:uppercase;
                                letter-spacing:0.05em;">Connecte</div>
                    <div style="color:#F1F5F9; font-size:0.8rem; font-weight:600;">{user_email}</div>
                </div>""",
                unsafe_allow_html=True,
            )
            if st.button("🔒 Deconnexion", key="logout_btn", use_container_width=True):
                from core import session as session_mod
                session_token = st.query_params.get("session")
                if isinstance(session_token, list):
                    session_token = session_token[0] if session_token else None
                if session_token:
                    session_mod.delete_session(session_token)
                q = st.query_params
                if "session" in q:
                    del q["session"]
                st.query_params = q
                auth_mod.logout_user()
                st.switch_page("app.py")

        st.markdown("### Navigation")
        for label, page in pages:
            active = "active" if page_title and Path(page).stem == page_title else ""
            # Inclure le session token dans le lien si present
            session_token = st.query_params.get("session")
            if isinstance(session_token, list):
                session_token = session_token[0] if session_token else None
            session_suffix = f"?session={session_token}" if session_token else ""
            if st.button(label, key=f"nav_{page}", use_container_width=True):
                st.switch_page(f"pages/{page}.py{session_suffix}")

        if auth_mod.is_authenticated():
            st.divider()

            # Aperçu rapide
            from core import models

            config = models.get_config()
            ca = models.ca_encaisse(2026)
            dep = models.total_depenses(2026)
            taux_u = config.get("taux_urssaf", 0)
            taux_i = config.get("taux_ir", 0)

            st.markdown("### Aperçu rapide")
            st.markdown(
                f"""<div style="background:#14141E; border-radius:8px; padding:0.75rem;">
                    <div style="display:flex; justify-content:space-between; font-size:0.8rem;">
                        <span style="color:#94A3B8;">CA 2026</span>
                        <span style="color:#F1F5F9; font-weight:600;">{ca:,.0f} €</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-top:0.25rem;">
                        <span style="color:#94A3B8;">Dépenses</span>
                        <span style="color:#F1F5F9; font-weight:600;">{dep:,.0f} €</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-top:0.25rem;">
                        <span style="color:#94A3B8;">Prélèvements</span>
                        <span style="color:#F1F5F9; font-weight:600;">{taux_u + taux_i:.1f}%</span>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )


def page_header(title: str, subtitle: str | None = None, icon: str = ""):
    """En-tête de page Aira avec titre et sous-titre."""
    icon_html = f'{icon} ' if icon else ""
    st.markdown(
        f"<h1>{icon_html}{title}</h1>",
        unsafe_allow_html=True,
    )
    if subtitle:
        st.caption(subtitle)
