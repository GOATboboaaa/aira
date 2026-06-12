"""Page Import Revolut Aira : import CSV + regles de categorisation + detection abonnements."""

import streamlit as st

from core import auth, models, revolut
from core.components import footer, render_sidebar
from core.db import init_db
from core.styles import inject
from config import taux

st.set_page_config(page_title="Aira — Import Revolut", page_icon="✦", layout="wide")
init_db()
inject()
render_sidebar("5_Import_Revolut")
auth.require_auth()

st.title("💳 Import Revolut")

tab_csv, tab_abo, tab_regles, tab_api = st.tabs(
    ["📄 Import CSV", "🤖 Détection abonnements", "🏷️ Règles de catégorisation", "🔌 API Business"]
)

# =============================================================================
# OPTION A : IMPORT CSV
# =============================================================================
with tab_csv:
    st.markdown("### Importer un relevé CSV Revolut")
    st.caption(
        "Exporte ton relevé depuis l'app Revolut (Account statement, format CSV) "
        "puis dépose le fichier ici. Les transactions sont catégorisées "
        "automatiquement et les doublons ignorés."
    )

    fichier = st.file_uploader("Fichier CSV Revolut", type=["csv"])

    if fichier is not None:
        regles = models.get_regles()
        try:
            df = revolut.parser_csv(fichier.getvalue(), regles)
        except ValueError as e:
            st.error(f"❌ {e}")
            df = None

        if df is not None and not df.empty:
            st.success(f"✅ {len(df)} transaction(s) détectée(s).")

            nb_depenses = (df["type"] == "depense").sum()
            nb_revenus = (df["type"] == "revenu").sum()
            col1, col2 = st.columns(2)
            col1.metric("Dépenses détectées", nb_depenses)
            col2.metric("Revenus (non importés)", nb_revenus)

            st.markdown("**Aperçu — dépenses à importer** (catégories modifiables)")
            df_dep = df[df["type"] == "depense"].copy()

            if df_dep.empty:
                st.info(
                    "📭 Aucune dépense à importer dans ce fichier. "
                    "Les montants positifs (revenus) ne sont pas importés "
                    "automatiquement — utilise la page Projets pour "
                    "enregistrer tes encaissements."
                )
            else:
                edited = st.data_editor(
                    df_dep,
                    use_container_width=True,
                    hide_index=True,
                    disabled=["date", "montant", "type", "revolut_ref"],
                    column_config={
                        "date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                        "description": st.column_config.TextColumn("Libellé"),
                        "montant": st.column_config.NumberColumn("Montant", format="%.2f €"),
                        "categorie": st.column_config.SelectboxColumn(
                            "Catégorie",
                            options=sorted(
                                set(
                                    taux.CATEGORIES_DEPENSES
                                    + [r["categorie"] for r in regles]
                                    + df_dep["categorie"].tolist()
                                )
                            ),
                        ),
                    },
                    key="editor_import",
                )

                st.info(
                    "Les revenus (montants positifs) ne sont pas importés "
                    "automatiquement — utilise la page Projets pour "
                    "enregistrer tes encaissements avec le lien client/projet."
                )

                if st.button("📥 Importer les dépenses", type="primary"):
                    ajoutes, doublons = 0, 0
                    for _, row in edited.iterrows():
                        ok = models.add_depense(
                            date=row["date"],
                            montant=float(row["montant"]),
                            categorie=row["categorie"],
                            description=row["description"],
                            moyen_paiement="Revolut",
                            source="import_revolut",
                            revolut_ref=row["revolut_ref"],
                        )
                        if ok:
                            ajoutes += 1
                        else:
                            doublons += 1
                    st.success(
                        f"✅ Import terminé : {ajoutes} ajoutée(s), "
                        f"{doublons} doublon(s) ignoré(s)."
                    )

# =============================================================================
# DÉTECTION D'ABONNEMENTS (CSV)
# =============================================================================
with tab_abo:
    st.markdown("### 🤖 Détection automatique d'abonnements")
    st.caption(
        "Importe un fichier CSV Revolut pour détecter les abonnements récurrents "
        "par analyse des libellés et des intervalles de temps entre transactions."
    )

    fichier_abo = st.file_uploader(
        "Fichier CSV Revolut (détection abonnements)",
        type=["csv"],
        key="abo_uploader",
    )

    if fichier_abo is not None:
        regles = models.get_regles()
        try:
            df_abo = revolut.parser_csv(fichier_abo.getvalue(), regles)
        except ValueError as e:
            st.error(f"❌ {e}")
            df_abo = None

        if df_abo is not None and not df_abo.empty:
            # Construire la liste des transactions pour le moteur de détection
            transactions = []
            for _, row in df_abo.iterrows():
                transactions.append({
                    "description": row.get("description", ""),
                    "montant": float(row.get("montant", 0)),
                    "date": str(row.get("date", "")),
                })

            detected = models.detect_subscriptions_from_transactions(transactions)

            if not detected:
                st.info(
                    "📭 Aucun abonnement récurrent détecté dans ce fichier. "
                    "Il faut au moins 2 occurrences du même libellé avec un "
                    "montant similaire à ~30 jours d'intervalle."
                )
            else:
                st.success(f"🔍 {len(detected)} abonnement(s) potentiel(s) détecté(s) !")

                st.markdown("**Abonnements détectés — cochés ceux à ajouter :**")
                selected = []
                for i, abo in enumerate(detected):
                    freq_label = {
                        "monthly": "Mensuel",
                        "yearly": "Annuel",
                        "weekly": "Hebdomadaire",
                    }.get(abo["frequency"], abo["frequency"])

                    col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
                    with col1:
                        checked = st.checkbox(
                            f"**{abo['name']}**",
                            value=True,
                            key=f"abo_detect_{i}",
                        )
                    with col2:
                        st.markdown(f"`{abo['amount']:.2f} €`")
                    with col3:
                        st.markdown(f"_{freq_label}_")
                    with col4:
                        st.markdown(f"Jour {abo['billing_day']}")
                    with col5:
                        conf = abo["confidence"]
                        color = "#10B981" if conf >= 80 else "#F59E0B" if conf >= 60 else "#F43F5E"
                        st.markdown(
                            f"<span style='color:{color};font-weight:700;'>{conf}%</span>",
                            unsafe_allow_html=True,
                        )
                    if checked:
                        selected.append(abo)

                if selected and st.button(
                    "✅ Ajouter les abonnements sélectionnés au calendrier",
                    type="primary",
                    use_container_width=True,
                ):
                    from datetime import datetime

                    ajoutes = 0
                    for abo in selected:
                        # Vérifier si déjà existant
                        existants = models.get_subscriptions_list()
                        deja_present = any(
                            s["name"].upper() == abo["name"].upper()
                            for s in existants
                        )
                        if not deja_present:
                            models.add_subscription(
                                name=abo["name"],
                                amount=abo["amount"],
                                frequency=abo["frequency"],
                                billing_day=abo["billing_day"],
                                category="Abonnements logiciels",
                                last_detected=abo["last_detected"],
                                is_manual=False,
                            )
                            ajoutes += 1

                    if ajoutes > 0:
                        today = datetime.now()
                        models.generate_planned_expenses(today.year)
                        st.success(
                            f"✅ {ajoutes} abonnement(s) ajouté(s) au calendrier ! "
                            f"Va voir la page **📅 Calendrier** pour les visualiser."
                        )
                    else:
                        st.info("Tous ces abonnements étaient déjà enregistrés.")

# =============================================================================
# RÈGLES DE CATÉGORISATION
# =============================================================================
with tab_regles:
    st.markdown("### Règles de catégorisation automatique")
    st.caption(
        "Quand un mot-clé est présent dans le libellé d'une transaction, "
        "la catégorie associée est appliquée automatiquement à l'import."
    )

    regles = models.get_regles()
    if regles:
        st.dataframe(regles, use_container_width=True, hide_index=True)

    with st.form("ajout_regle", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            motif = st.text_input("Mot-clé dans le libellé", placeholder="ex : ADOBE")
        with c2:
            categorie = st.text_input("Catégorie à appliquer",
                                      placeholder="ex : Abonnements logiciels")
        if st.form_submit_button("+ Ajouter la règle"):
            if motif and categorie:
                models.add_regle(motif.strip(), categorie.strip())
                st.success("✅ Règle ajoutée.")
                st.rerun()
            else:
                st.error("Mot-clé et catégorie obligatoires.")

    if regles:
        ids = [r["id"] for r in regles]
        del_id = st.selectbox("Supprimer la règle n°", [""] + ids, key="del_regle")
        if st.button("🗑 Supprimer", use_container_width=True) and del_id != "":
            models.delete_regle(int(del_id))
            st.rerun()

# =============================================================================
# OPTION B : API
# =============================================================================
with tab_api:
    st.markdown(revolut.DOC_API_REVOLUT)

footer()
