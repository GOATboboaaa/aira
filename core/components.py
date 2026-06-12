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
import streamlit.components.v1 as components


def kpi_card(label: str, value: str, delta: str | None = None,
             help_text: str | None = None, delta_color: str = "normal"):
    """Affiche une KPI card stylée Aira.

    Utilise le metric-container natif Streamlit avec notre CSS.
    """
    help_kw = {"help": help_text} if help_text else {}
    delta_kw = {"delta": delta, "delta_color": delta_color} if delta else {}
    st.metric(label=label, value=value, **delta_kw, **help_kw)


def animated_kpi_row(
    ca_enc: float,
    ca_fac: float,
    total_prelevements: float,
    pct_prelev: float,
    depenses: float,
    net_reel: float,
    taux_urssaf: float,
    taux_ir: float,
    annee: int = 2026,
):
    """Rend les 4 KPIs du dashboard dans un composant isolé avec count-up animé.

    Utilise st.components.v1.html() pour que le HTML/CSS/JS cohabitent
    dans le même iframe — pas de stripping de scripts par Streamlit,
    pas de conflit de sanitization.

    Les valeurs numériques sont passées en data-target pour le JS count-up.
    """
    # ─── Pré-calcul des deltas et couleurs ────────────────────────────────
    delta_ca = f"{ca_fac:,.0f} € facturé" if ca_fac != ca_enc and ca_fac > 0 else ""

    delta_color_prel = "#F43F5E"  # inverse
    delta_prel = f"{pct_prelev:.1f} % du CA"

    delta_color_net = "#10B981" if net_reel >= 0 else "#F43F5E"
    delta_net = ""
    if ca_enc > 0:
        delta_net = f"+{net_reel:,.0f} €" if net_reel >= 0 else f"{net_reel:,.0f} €"

    # ─── CSS (injecté dans l'iframe) ──────────────────────────────────────
    css = """
    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      body {
        font-family: 'Source Sans Pro', -apple-system, sans-serif;
        background: transparent;
      }
      .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
      }
      @media (max-width: 900px) {
        .kpi-grid { grid-template-columns: repeat(2, 1fr); }
      }
      @media (max-width: 500px) {
        .kpi-grid { grid-template-columns: 1fr; }
      }
      .kpi-card {
        background: #1A1A24;
        border: 1px solid #2A2A3A;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        transition: border-color 0.2s, box-shadow 0.2s;
      }
      .kpi-card:hover {
        border-color: rgba(124, 92, 252, 0.4);
        box-shadow: 0 4px 12px rgba(124, 92, 252, 0.08);
      }
      .kpi-label {
        color: #94A3B8;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        display: flex;
        align-items: center;
        gap: 0.35rem;
      }
      .kpi-label .help-icon {
        cursor: help;
        opacity: 0.5;
        font-size: 0.7rem;
      }
      .kpi-value {
        color: #F1F5F9;
        font-size: 1.75rem;
        font-weight: 700;
        line-height: 1.2;
        margin-top: 0.25rem;
        font-variant-numeric: tabular-nums;
      }
      .kpi-delta {
        font-size: 0.8rem;
        margin-top: 0.25rem;
      }
      .kpi-help {
        color: #64748B;
        font-size: 0.7rem;
        margin-top: 0.25rem;
        cursor: help;
      }
      @media (prefers-reduced-motion: reduce) {
        .kpi-value { opacity: 1 !important; }
      }
    </style>
    """

    # ─── Générateur de card ───────────────────────────────────────────────
    def card(label, value, target_id, help_text="", delta="", delta_color="#10B981"):
        help_icon = f'<span class="help-icon" title="{help_text}">ⓘ</span>' if help_text else ""
        help_row = f'<div class="kpi-help">{help_text}</div>' if help_text else ""
        delta_row = f'<div class="kpi-delta" style="color:{delta_color}">{delta}</div>' if delta else ""
        return f"""
        <div class="kpi-card">
          <div class="kpi-label">{label} {help_icon}</div>
          <div class="kpi-value">
            <span id="{target_id}" data-target="{value:,.0f}">0</span>
          </div>
          {delta_row}
          {help_row}
        </div>"""

    # ─── Cards ────────────────────────────────────────────────────────────
    cards_html = ""
    cards_html += card(
        "CA encaissé", ca_enc, "kpi-ca",
        help_text="Assiette des cotisations (projets payés)",
        delta=delta_ca,
        delta_color="#10B981",
    )
    cards_html += card(
        "Prélèvements", total_prelevements, "kpi-prel",
        help_text="URSSAF + Versement libératoire IR",
        delta=delta_prel,
        delta_color=delta_color_prel,
    )
    cards_html += card(
        "Dépenses réelles", depenses, "kpi-dep",
        help_text="Non déductibles fiscalement, impactent la trésorerie",
    )
    cards_html += card(
        "Résultat net", net_reel, "kpi-net",
        help_text=("CA encaissé − prélèvements − dépenses réelles"
                   if ca_enc > 0 else ""),
        delta=delta_net,
        delta_color=delta_color_net,
    )

    # ─── JS Count-up ──────────────────────────────────────────────────────
    js = """
    <script>
    (function() {
      function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

      function parseTarget(el) {
        var raw = el.getAttribute('data-target');
        if (!raw) return NaN;
        return parseFloat(raw.replace(/,/g, ''));
      }

      function animate(id) {
        var el = document.getElementById(id);
        if (!el) return;
        var target = parseTarget(el);
        if (isNaN(target) || target <= 0) return;

        var suffix = '';
        var text = el.textContent.trim();
        if (text.indexOf('\u20AC') !== -1) suffix = ' \u20AC';

        var duration = 1.2;
        var start = null;

        function format(v) {
          var n = Math.round(v);
          return n.toLocaleString('fr-FR') + suffix;
        }

        el.textContent = '0' + suffix;

        function step(ts) {
          if (!start) start = ts;
          var progress = Math.min((ts - start) / 1000 / duration, 1);
          el.textContent = format(easeOut(progress) * target);
          if (progress < 1) requestAnimationFrame(step);
          else el.textContent = format(target);
        }
        requestAnimationFrame(step);
      }

      animate('kpi-ca');
      animate('kpi-prel');
      animate('kpi-dep');
      animate('kpi-net');
    })();
    </script>
    """

    html = f"<div class='kpi-grid'>{cards_html}</div>{css}{js}"
    components.html(html, height=185, scrolling=False)


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
                from core.aira_auth_manager import clear_session_cookie
                session_token = st.query_params.get("session")
                if isinstance(session_token, list):
                    session_token = session_token[0] if session_token else None
                if session_token:
                    session_mod.delete_session(session_token)
                clear_session_cookie()
                q = st.query_params
                if "session" in q:
                    del q["session"]
                st.query_params = q
                auth_mod.logout_user()
                st.switch_page("app.py")

        st.markdown("### Navigation")
        for label, page in pages:
            active = "active" if page_title and Path(page).stem == page_title else ""
            if st.button(label, key=f"nav_{page}", use_container_width=True):
                st.switch_page(f"pages/{page}.py")

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


def auth_card(key: str = "auth") -> None:
    """Wrapper pour les formulaires d'authentification.

    Ajoute le container stylé auth-card + animations de transition.
    À appeler au début de chaque bloc de formulaire.

    Args:
        key: identifiant pour les animations de transition (ex: "login", "forgot").
    """
    st.markdown(
        f"""<div class="auth-card" id="auth-card-{key}">
            <div class="auth-form" id="auth-form-{key}">""",
        unsafe_allow_html=True,
    )


def close_auth_card() -> None:
    """Ferme le wrapper auth-card."""
    st.markdown("</div></div>", unsafe_allow_html=True)


def trigger_shake(key: str = "auth") -> None:
    """Déclenche l'effet shake sur la carte auth via JavaScript."""
    st.markdown(
        f"""<script>
            (function() {{
                var card = document.getElementById('auth-card-{key}');
                if (card) {{
                    card.classList.remove('auth-shake');
                    void card.offsetWidth;
                    card.classList.add('auth-shake');
                    setTimeout(function() {{
                        card.classList.remove('auth-shake');
                    }}, 500);
                }}
            }})();
        </script>""",
        unsafe_allow_html=True,
    )
