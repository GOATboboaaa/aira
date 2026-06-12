"""
Aira Design System — CSS personnalisé.

Palette :
  Fond        : #0F0F13 (charcoal profond)
  Surface     : #1A1A24 (cards, sidebar)
  Bordure     : #2A2A3A
  Primaire    : #7C5CFC (violet électrique)
  Secondaire  : #06B6D4 (cyan)
  Succès      : #10B981 (émeraude)
  Warning     : #F59E0B (ambre)
  Danger      : #F43F5E (rose)
  Texte       : #F1F5F9 (gris clair)
  Texte sec.  : #94A3B8
"""

import streamlit as st


def inject():
    """Injecte le CSS Aira dans la page Streamlit."""
    st.markdown(
        f"""
        <style>
        /* ─── Reset globaux ─── */
        .stApp {{
            background: #0F0F13;
        }}
        .main .block-container {{
            padding-top: 1.5rem;
            padding-bottom: 3rem;
            max-width: 1200px;
        }}

        /* ─── Sidebar ─── */
        section[data-testid="stSidebar"] {{
            background: #1A1A24 !important;
            border-right: 1px solid #2A2A3A;
        }}
        section[data-testid="stSidebar"] .stButton button {{
            width: 100%;
            border: 1px solid #2A2A3A;
            background: transparent;
            color: #94A3B8;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-size: 0.875rem;
            transition: all 0.2s;
        }}
        section[data-testid="stSidebar"] .stButton button:hover {{
            border-color: #7C5CFC;
            color: #F1F5F9;
            background: rgba(124, 92, 252, 0.08);
        }}

        /* ─── Cards / Metrics ─── */
        div[data-testid="metric-container"] {{
            background: #1A1A24;
            border: 1px solid #2A2A3A;
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
            transition: border-color 0.2s, box-shadow 0.2s;
        }}
        div[data-testid="metric-container"]:hover {{
            border-color: rgba(124, 92, 252, 0.4);
            box-shadow: 0 4px 12px rgba(124, 92, 252, 0.08);
        }}
        div[data-testid="metric-container"] label {{
            color: #94A3B8 !important;
            font-size: 0.75rem !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        div[data-testid="metric-container"] div[data-testid="stMetricValue"] {{
            color: #F1F5F9 !important;
            font-size: 1.75rem !important;
            font-weight: 700;
            line-height: 1.2;
        }}
        div[data-testid="metric-container"] div[data-testid="stMetricDelta"] {{
            font-size: 0.8rem !important;
        }}
        div[data-testid="metric-container"] .st-emotion-cache-1wivap2 {{
            /* delta color overrides via inline styles, can't always override */
        }}

        /* ─── Titres ─── */
        h1, h2, h3 {{
            color: #F1F5F9 !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em;
        }}
        h1 {{
            font-size: 1.75rem !important;
            border-bottom: 1px solid #2A2A3A;
            padding-bottom: 0.75rem;
            margin-bottom: 1.5rem;
        }}
        h2 {{
            font-size: 1.25rem !important;
            margin-top: 1.5rem;
        }}
        .stCaption {{
            color: #64748B !important;
            font-size: 0.8rem;
        }}

        /* ─── DataFrames / Tables ─── */
        .stDataFrame {{
            border: 1px solid #2A2A3A;
            border-radius: 10px;
            overflow: hidden;
        }}
        .stDataFrame table {{
            background: #1A1A24 !important;
            color: #F1F5F9 !important;
        }}
        .stDataFrame th {{
            background: #14141E !important;
            color: #94A3B8 !important;
            font-size: 0.75rem !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 1px solid #2A2A3A !important;
        }}
        .stDataFrame td {{
            background: #1A1A24 !important;
            border-bottom: 1px solid #222233 !important;
        }}

        /* ─── Data editor ─── */
        div[data-testid="stDataEditor"] {{
            border: 1px solid #2A2A3A;
            border-radius: 10px;
            overflow: hidden;
        }}
        div[data-testid="stDataEditor"] table {{
            background: #1A1A24 !important;
        }}

        /* ─── Formulaires ─── */
        .stForm {{
            background: #1A1A24;
            border: 1px solid #2A2A3A;
            border-radius: 12px;
            padding: 1.5rem;
        }}
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div, .stTextArea textarea {{
            background: #14141E !important;
            border: 1px solid #2A2A3A !important;
            border-radius: 8px !important;
            color: #F1F5F9 !important;
            transition: border-color 0.2s;
        }}
        .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {{
            border-color: #7C5CFC !important;
            box-shadow: 0 0 0 2px rgba(124, 92, 252, 0.15) !important;
        }}

        /* ─── Boutons ─── */
        .stButton button, .stForm button {{
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 0.875rem !important;
            padding: 0.5rem 1.25rem !important;
            transition: all 0.2s;
        }}
        .stButton button[kind="primary"], .stForm button[type="primary"] {{
            background: linear-gradient(135deg, #7C5CFC, #6D4FFF) !important;
            border: none !important;
            color: white !important;
        }}
        .stButton button[kind="primary"]:hover, .stForm button[type="primary"]:hover {{
            background: linear-gradient(135deg, #8B6DFC, #7C5CFC) !important;
            box-shadow: 0 4px 14px rgba(124, 92, 252, 0.3) !important;
        }}
        .stButton button:not([kind="primary"]), .stForm button:not([type="primary"]) {{
            background: transparent !important;
            border: 1px solid #2A2A3A !important;
            color: #94A3B8 !important;
        }}
        .stButton button:not([kind="primary"]):hover {{
            border-color: #7C5CFC !important;
            color: #F1F5F9 !important;
        }}

        /* ─── Expander ─── */
        .st-expander {{
            background: #1A1A24;
            border: 1px solid #2A2A3A;
            border-radius: 10px;
        }}
        .st-expander summary {{
            color: #F1F5F9;
            font-weight: 600;
        }}

        /* ─── Tabs ─── */
        .stTabs [data-baseweb="tab-list"] {{
            background: transparent;
            border-bottom: 1px solid #2A2A3A;
            gap: 0;
        }}
        .stTabs [data-baseweb="tab"] {{
            color: #94A3B8;
            font-weight: 500;
            padding: 0.75rem 1.25rem;
        }}
        .stTabs [aria-selected="true"] {{
            color: #7C5CFC !important;
            border-bottom: 2px solid #7C5CFC !important;
        }}

        /* ─── Alerts / Messages ─── */
        .stAlert {{
            border-radius: 10px;
            border: none;
            font-size: 0.875rem;
        }}
        .stAlert[data-baseweb="notification"] {{
            border-left: 3px solid;
        }}
        div[data-testid="stSuccess"] {{
            background: rgba(16, 185, 129, 0.08);
            border: 1px solid rgba(16, 185, 129, 0.2);
            color: #6EE7B7;
        }}
        div[data-testid="stError"] {{
            background: rgba(244, 63, 94, 0.08);
            border: 1px solid rgba(244, 63, 94, 0.2);
            color: #FDA4AF;
        }}
        div[data-testid="stWarning"] {{
            background: rgba(245, 158, 11, 0.08);
            border: 1px solid rgba(245, 158, 11, 0.2);
            color: #FDE68A;
        }}
        div[data-testid="stInfo"] {{
            background: rgba(6, 182, 212, 0.08);
            border: 1px solid rgba(6, 182, 212, 0.2);
            color: #67E8F9;
        }}

        /* ─── Progress bar ─── */
        .stProgress > div > div > div > div {{
            background: linear-gradient(90deg, #7C5CFC, #A78BFA) !important;
        }}
        .stProgress > div > div {{
            height: 22px !important;
            border-radius: 6px !important;
            background: #14141E !important;
        }}
        .stProgress > div > div > div {{
            border-radius: 6px !important;
            min-width: 4px !important;
        }}

        /* ─── Waterfall row compact ─── */
        .waterfall-row {{
            margin-bottom: 0.25rem !important;
        }}

        /* ─── Divider ─── */
        hr {{
            border-color: #2A2A3A !important;
            margin: 1.5rem 0 !important;
        }}

        /* ─── Tooltip personnalisé ─── */
        .stTooltipIcon {{
            color: #64748B;
        }}

        /* ─── Scrollbar ─── */
        ::-webkit-scrollbar {{
            width: 6px;
            height: 6px;
        }}
        ::-webkit-scrollbar-track {{
            background: #0F0F13;
        }}
        ::-webkit-scrollbar-thumb {{
            background: #2A2A3A;
            border-radius: 3px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: #3A3A4A;
        }}

        /* ─── KPI Cards — custom variant ─── */
        .kpi-card {{
            background: #1A1A24;
            border: 1px solid #2A2A3A;
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            transition: border-color 0.2s;
            margin-bottom: 0.5rem;
        }}
        .kpi-card:hover {{
            border-color: rgba(124, 92, 252, 0.4);
        }}
        .kpi-card .kpi-label {{
            color: #94A3B8;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .kpi-card .kpi-value {{
            color: #F1F5F9;
            font-size: 1.75rem;
            font-weight: 700;
            line-height: 1.2;
            margin-top: 0.25rem;
        }}
        .kpi-card .kpi-delta {{
            font-size: 0.8rem;
            margin-top: 0.25rem;
        }}
        .kpi-card .kpi-help {{
            color: #64748B;
            font-size: 0.75rem;
            margin-top: 0.25rem;
        }}

        /* ─── Section header with gradient ─── */
        .section-header {{
            padding: 0.75rem 0;
            margin: 1.5rem 0 1rem 0;
            border-bottom: 1px solid #2A2A3A;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .section-header h2 {{
            margin: 0 !important;
            border: none !important;
        }}
        .section-header .badge {{
            background: rgba(124, 92, 252, 0.12);
            color: #A78BFA;
            font-size: 0.7rem;
            font-weight: 600;
            padding: 0.15rem 0.5rem;
            border-radius: 999px;
        }}

        /* ─── Color chips for tax breakdown ─── */
        .color-chip-urssaf {{ background: #7C5CFC; }}
        .color-chip-ir {{ background: #06B6D4; }}
        .color-chip-depenses {{ background: #F59E0B; }}
        .color-chip-reste {{ background: #10B981; }}

        /* ─── Footer ─── */
        .app-footer {{
            text-align: center;
            color: #64748B;
            font-size: 0.7rem;
            padding: 2rem 0 0.5rem 0;
            border-top: 1px solid #2A2A3A;
            margin-top: 3rem;
        }}
        .app-footer span {{
            color: #7C5CFC;
        }}

        /* ─── Cacher la navigation auto Streamlit ─── */
        section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] {{
            display: none !important;
        }}

        /* ─── Réduire l'espace après le logo Aira ─── */
        section[data-testid="stSidebar"] .stButton {{
            margin-bottom: 0.25rem;
        }}

        /* ─── Sidebar app-header compact ─── */
        .sidebar-header {{
            padding: 0.25rem 0 1rem 0;
        }}

        /* ─── Responsive: grille KPI ─── */
        @media (max-width: 992px) {{
            div[data-testid="column"] {{
                min-width: 48% !important;
                flex: 1 1 48% !important;
            }}
        }}

        @media (max-width: 640px) {{
            div[data-testid="column"] {{
                min-width: 100% !important;
                flex: 1 1 100% !important;
            }}
            div[data-testid="metric-container"] div[data-testid="stMetricValue"] {{
                font-size: 1.25rem !important;
            }}
            .main .block-container {{
                padding-left: 0.75rem;
                padding-right: 0.75rem;
            }}
        }}

        /* ─── Éviter le débordement des cartes waterfall ─── */
        .tax-bar-label {{
            min-width: 70px;
        }}

        /* ─── Responsive waterfall: stack labels above bars on tiny screens ─── */
        @media (max-width: 480px) {{
            .tax-bar-label {{
                width: 60px !important;
                font-size: 0.65rem !important;
            }}
            div[data-testid="column"] {{
                min-width: 100% !important;
                flex: 1 1 100% !important;
            }}
        }}

        /* ═══════════════════════════════════════════════════════════════
           AUTH UI — ANIMATIONS
           ═══════════════════════════════════════════════════════════════ */

        /* ─── Auth card container ─── */
        .auth-card {{
            max-width: 440px;
            margin: 0 auto;
            background: #1A1A24;
            border: 1px solid #2A2A3A;
            border-radius: 16px;
            padding: 2rem 1.75rem;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
            position: relative;
            overflow: hidden;
        }}
        .auth-card::before {{
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
            background: linear-gradient(90deg, #7C5CFC, #A78BFA, #7C5CFC);
            background-size: 200% 100%;
            animation: shimmer 3s ease-in-out infinite;
        }}

        /* ─── Form slide/fade transitions ─── */
        .auth-form {{
            animation: fadeSlideIn 0.35s ease-out;
        }}
        .auth-form-exit {{
            animation: fadeSlideOut 0.25s ease-in forwards;
        }}

        @keyframes fadeSlideIn {{
            from {{
                opacity: 0;
                transform: translateX(24px);
            }}
            to {{
                opacity: 1;
                transform: translateX(0);
            }}
        }}
        @keyframes fadeSlideOut {{
            from {{
                opacity: 1;
                transform: translateX(0);
            }}
            to {{
                opacity: 0;
                transform: translateX(-24px);
            }}
        }}
        @keyframes shimmer {{
            0%, 100% {{ background-position: 200% 0; }}
            50% {{ background-position: -200% 0; }}
        }}

        /* ─── Shake effect sur les erreurs ─── */
        .auth-shake {{
            animation: shake 0.4s ease-in-out;
        }}
        @keyframes shake {{
            0%, 100% {{ transform: translateX(0); }}
            20% {{ transform: translateX(-10px); }}
            40% {{ transform: translateX(10px); }}
            60% {{ transform: translateX(-8px); }}
            80% {{ transform: translateX(8px); }}
        }}

        /* ─── Spinner loading ─── */
        .auth-spinner {{
            display: inline-block;
            width: 18px;
            height: 18px;
            border: 2px solid rgba(255,255,255,0.2);
            border-top-color: #F1F5F9;
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
            vertical-align: middle;
            margin-right: 0.4rem;
        }}
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}

        /* ─── Bouton submit avec animation ─── */
        .auth-btn {{
            position: relative;
            overflow: hidden;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }}
        .auth-btn:hover {{
            transform: scale(1.02);
            box-shadow: 0 6px 20px rgba(124, 92, 252, 0.35);
        }}
        .auth-btn:active {{
            transform: scale(0.98);
        }}
        .auth-btn:disabled {{
            opacity: 0.7;
            transform: scale(0.98);
        }}

        /* ─── Input focus glow ─── */
        .auth-input {{
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }}
        .auth-input:focus {{
            border-color: #7C5CFC !important;
            box-shadow: 0 0 0 3px rgba(124, 92, 252, 0.15) !important;
        }}

        /* ─── Success toast animation ─── */
        .auth-toast {{
            animation: toastIn 0.3s ease-out, toastOut 0.3s ease-in 3s forwards;
        }}
        @keyframes toastIn {{
            from {{ opacity: 0; transform: translateY(-12px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes toastOut {{
            from {{ opacity: 1; }}
            to {{ opacity: 0; }}
        }}

        /* ─── Accessibility: prefer reduced motion ─── */
        @media (prefers-reduced-motion: reduce) {{
            .auth-form,
            .auth-form-exit,
            .auth-shake,
            .auth-card::before,
            .auth-btn:hover,
            .auth-toast,
            .aira-fade-in,
            [data-testid="stMetricValue"] {{
                animation: none !important;
                transform: none !important;
                transition: none !important;
            }}
            [data-testid="stMetricValue"] {{
                opacity: 1 !important;
            }}
        }}

        /* ═══════════════════════════════════════════════════════════════
           PAGE TRANSITION — Fade-in du conteneur principal
           ═══════════════════════════════════════════════════════════════ */
        .aira-fade-in {{
            animation: airaFadeIn 0.4s ease-out;
        }}
        @keyframes airaFadeIn {{
            from {{ opacity: 0; transform: translateY(6px); }}
            to   {{ opacity: 1; transform: translateY(0); }}
        }}

        /* ═══════════════════════════════════════════════════════════════
           COUNT-UP — Cacher les metrics le temps que JS les anime
           ═══════════════════════════════════════════════════════════════ */
        .aira-countup-ready [data-testid="stMetricValue"] {{
            opacity: 0;
            transition: none;
        }}
        .aira-countup-done [data-testid="stMetricValue"] {{
            opacity: 1;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ─── JS : Page transition + Count-up ────────────────────────────────
    # Applique la classe de fade après un micro-delai (laisse Streamlit finir son render)
    st.markdown("""
    <script>
    (function() {
      /* ─── FADE-IN TRANSITION ─────────────────────────── */
      function addFadeIn() {
        var container = document.querySelector('.main .block-container');
        if (container) {
          container.classList.add('aira-fade-in');
          // Re-trigger animation on each Streamlit re-run
        }
      }

      /* ─── COUNT-UP ANIMATION ──────────────────────────── */
      function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

      function countUpMetrics() {
        var metrics = document.querySelectorAll('[data-testid="stMetricValue"]');
        if (metrics.length === 0) return;

        // Add ready class to hide initial values
        document.body.classList.add('aira-countup-ready');

        metrics.forEach(function(el) {
          // Skip if already animated in this session
          if (el.getAttribute('data-aira-counted')) return;

          var raw = el.textContent.trim();
          var numStr = raw.replace(/[^0-9,.-]/g, '').replace(',', '.');
          var target = parseFloat(numStr);
          if (isNaN(target) || target <= 0) {
            el.style.opacity = '1';
            el.setAttribute('data-aira-counted', '1');
            return;
          }

          var suffix = raw.replace(/[0-9,.-]/g, '').trim();
          var duration = 1.2;
          var start = null;

          function format(v) {
            var n = Math.round(v);
            var formatted = n.toLocaleString('fr-FR');
            return formatted + (suffix ? ' ' + suffix : '');
          }

          // Start from 0
          el.textContent = '0' + (suffix ? ' ' + suffix : '');
          el.style.opacity = '1';
          el.setAttribute('data-aira-counted', '1');

          function step(ts) {
            if (!start) start = ts;
            var elapsed = (ts - start) / 1000;
            var progress = Math.min(elapsed / duration, 1);
            var current = easeOut(progress) * target;
            el.textContent = format(current);
            if (progress < 1) {
              requestAnimationFrame(step);
            } else {
              el.textContent = format(target);
            }
          }
          requestAnimationFrame(step);
        });

        setTimeout(function() {
          document.body.classList.remove('aira-countup-ready');
          document.body.classList.add('aira-countup-done');
        }, 100);
      }

      /* ─── RUN ─────────────────────────────────────────── */
      addFadeIn();
      countUpMetrics();

      // Re-run when Streamlit injects NEW metrics (full re-render only)
      var observer = new MutationObserver(function() {
        // Only act if there are unprocessed metrics
        var fresh = document.querySelectorAll('[data-testid="stMetricValue"]:not([data-aira-counted])');
        if (fresh.length > 0) {
          addFadeIn();
          countUpMetrics();
        }
      });
      observer.observe(document.body, { childList: true, subtree: true });
    })();
    </script>
    """, unsafe_allow_html=True)
