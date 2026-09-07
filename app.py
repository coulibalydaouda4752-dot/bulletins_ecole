import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- CONFIGURATION SUPABASE ---
SUPABASE_URL = "https://ckjoarpmpptjrqonwbcv.supabase.co"
SUPABASE_KEY = "sb_publishable_fbdmOrHigq32Sgog-RFhuw_Rcac30bS"

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

st.set_page_config(page_title="Gestion des Bulletins - École Privée Diaratigui Coulibaly", layout="wide")

# --- FONCTIONS BASE DE DONNÉES ---
def charger_eleves():
    try:
        response = supabase.table("eleves").select("*").execute()
        return response.data
    except Exception as e:
        st.error(f"Erreur de connexion à Supabase : {e}")
        return []

def sauvegarder_eleve(id_eleve, nom, prenom, classe, notes, total_points, moyenne):
    data = {
        "nom": nom,
        "prenom": prenom,
        "classe": classe,
        "notes": notes,
        "total_points": total_points,
        "moyenne": moyenne
    }
    if id_eleve:
        supabase.table("eleves").update(data).eq("id", id_eleve).execute()
    else:
        supabase.table("eleves").insert(data).execute()

def supprimer_eleve(id_eleve):
    try:
        supabase.table("eleves").delete().eq("id", id_eleve).execute()
        return True
    except Exception as e:
        st.error(f"Erreur lors de la suppression : {e}")
        return False

# --- MATIÈRES AVEC LEURS COEFFICIENTS OFFICIELS ---
MATIERES = [
    {"code": "REDACTION", "nom": "Rédaction", "coef": 3},
    {"code": "DICTEE_QUEST", "nom": "Dictée-Questions", "coef": 2},
    {"code": "MATH", "nom": "Mathématique", "coef": 3},
    {"code": "PC", "nom": "Physique-chimie", "coef": 3},
    {"code": "ANG", "nom": "Anglais", "coef": 2},
    {"code": "SVT", "nom": "Science Nat", "coef": 2},
    {"code": "HG", "nom": "Hist-Géo", "coef": 2},
    {"code": "ECM", "nom": "Ed civ. Morale", "coef": 1},
    {"code": "EPS", "nom": "Ed Physique", "coef": 1},
    {"code": "LECTURE", "nom": "Lecture", "coef": 1},
    {"code": "RECITATION", "nom": "Récitation", "coef": 1},
    {"code": "CONDUITE", "nom": "Conduite", "coef": 1}
]

TOTAL_COEFFS = sum(m["coef"] for m in MATIERES) # 22

def obtenir_appreciation(moyenne):
    if moyenne >= 18:
        return "Excellent"
    elif moyenne >= 16:
        return "Très-bien"
    elif moyenne >= 14:
        return "Bien"
    elif moyenne >= 12:
        return "Assez-bien"
    elif moyenne >= 10:
        return "Passable"
    elif moyenne >= 8:
        return "Médiocre"
    else:
        return "Faible"

# --- DÉTECTION DU MODE D'ACCÈS ---
query_params = st.query_params
mode_saisie = query_params.get("mode") == "saisie"

# ==========================================
# 1. MODE MOBILE : SAISIE SIMPLIFIÉE
# ==========================================
if mode_saisie:
    st.title("📲 Espace de Saisie des Notes")
    st.info("Portail mobile pour les assistants. Enregistrement direct vers la base centrale.")

    eleves_data = charger_eleves()
    if not eleves_data:
        st.warning("Aucun élève enregistré. Demandez à l'administrateur d'ajouter des élèves.")
    else:
        options_eleves = {f"{e['nom'].upper()} {e['prenom']} ({e['classe']})": e for e in eleves_data}
        choix = st.selectbox("Sélectionner l'élève :", list(options_eleves.keys()))
        eleve = options_eleves[choix]

        st.subheader(f"Notes pour : {eleve['nom'].upper()} {eleve['prenom']}")
        
        notes_existantes = eleve.get("notes") or {}
        nouvelles_notes = {}
        sum_points_coeff = 0.0

        with st.form("form_saisie_mobile"):
            for m in MATIERES:
                st.markdown(f"**{m['nom']} (Coeff : {m['coef']})**")
                col_c, col_e = st.columns(2)
                
                val_c_defaut = float(notes_existantes.get(m['code'], {}).get('classe', 10.0))
                val_e_defaut = float(notes_existantes.get(m['code'], {}).get('compo', 10.0))

                v_classe = col_c.number_input("Note Classe /20", min_value=0.0, max_value=20.0, value=val_c_defaut, step=0.5, key=f"m_{m['code']}_c")
                v_compo = col_e.number_input("Note Compo /40", min_value=0.0, max_value=40.0, value=val_e_defaut, step=0.5, key=f"m_{m['code']}_e")

                moy_matiere = ((v_classe / 20.0) + (v_compo / 40.0)) / 3.0 * 20.0
                moy_coeff = moy_matiere * m['coef']
                sum_points_coeff += moy_coeff

                nouvelles_notes[m['code']] = {
                    "classe": v_classe,
                    "compo": v_compo,
                    "moyenne": round(moy_matiere, 2),
                    "moyenne_coeff": round(moy_coeff, 2),
                    "appreciation": obtenir_appreciation(moy_matiere)
                }

            moyenne_generale = sum_points_coeff / TOTAL_COEFFS

            submitted = st.form_submit_button("💾 Enregistrer la Saisie")
            if submitted:
                sauvegarder_eleve(
                    id_eleve=eleve["id"],
                    nom=eleve["nom"],
                    prenom=eleve["prenom"],
                    classe=eleve["classe"],
                    notes=nouvelles_notes,
                    total_points=round(sum_points_coeff, 2),
                    moyenne=round(moyenne_generale, 2)
                )
                st.success(f"Notes enregistrées ! Moyenne Générale : {moyenne_generale:.2f}/20")

# ==========================================
# 2. MODE ADMIN CENTRAL (PC)
# ==========================================
else:
    st.sidebar.title("🏛️ Administration Centralisée")
    menu = st.sidebar.radio("Navigation :", [
        "1. Gestion des Élèves",
        "2. Saisie des Notes (PC)",
        "3. Classement & Résultats",
        "4. Impression des Bulletins"
    ])

    # --------------------------------------
    # MENU 1 : GESTION DES ÉLÈVES
    # --------------------------------------
    if menu == "1. Gestion des Élèves":
        st.title("👨‍🎓 Inscription des Élèves")
        
        with st.form("ajout_eleve"):
            c1, c2, c3 = st.columns(3)
            nom = c1.text_input("Nom de famille").strip()
            prenom = c2.text_input("Prénom").strip()
            classe = c3.text_input("Classe", value="7-ème A")
            btn_ajouter = st.form_submit_button("Ajouter à la base")
            
            if btn_ajouter:
                if nom and prenom:
                    sauvegarder_eleve(None, nom, prenom, classe, {}, 0.0, 0.0)
                    st.success(f"Élève {prenom} {nom.upper()} inscrit avec succès !")
                    st.rerun()
                else:
                    st.error("Veuillez remplir le nom et le prénom.")

        st.divider()
        st.subheader("Effectif enregistré")
        eleves = charger_eleves()
        if eleves:
            df = pd.DataFrame(eleves)[["id", "nom", "prenom", "classe", "moyenne", "total_points"]]
            st.dataframe(df, use_container_width=True)

            # --- PARCELLE DE SUPPRESSION ---
            st.subheader("🗑️ Supprimer un élève")
            options_sup = {f"{e['nom'].upper()} {e['prenom']} (ID: {e['id']})": e['id'] for e in eleves}
            eleve_a_supprimer = st.selectbox("Sélectionner l'élève à retirer :", list(options_sup.keys()))
            
            if st.button("❌ Supprimer définitivement cet élève", type="primary"):
                id_target = options_sup[eleve_a_supprimer]
                if supprimer_eleve(id_target):
                    st.success("Élève supprimé avec succès.")
                    st.rerun()
        else:
            st.info("Aucun élève enregistré pour le moment.")

    # --------------------------------------
    # MENU 2 : SAISIE DES NOTES (PC)
    # --------------------------------------
    elif menu == "2. Saisie des Notes (PC)":
        st.title("📝 Saisie Centrale des Notes")
        eleves_data = charger_eleves()
        
        if not eleves_data:
            st.warning("Aucun élève disponible.")
        else:
            options_eleves = {f"{e['nom'].upper()} {e['prenom']} ({e['classe']})": e for e in eleves_data}
            choix = st.selectbox("Sélectionner l'élève :", list(options_eleves.keys()))
            eleve = options_eleves[choix]

            notes_existantes = eleve.get("notes") or {}
            nouvelles_notes = {}
            sum_points_coeff = 0.0

            with st.form("form_saisie_pc"):
                st.subheader(f"Saisie pour : {eleve['prenom']} {eleve['nom'].upper()}")
                for m in MATIERES:
                    st.markdown(f"**{m['nom']} (Coeff : {m['coef']})**")
                    col_c, col_e = st.columns(2)
                    
                    val_c_defaut = float(notes_existantes.get(m['code'], {}).get('classe', 10.0))
                    val_e_defaut = float(notes_existantes.get(m['code'], {}).get('compo', 10.0))

                    v_classe = col_c.number_input("Note Classe /20", min_value=0.0, max_value=20.0, value=val_c_defaut, step=0.5, key=f"pc_{m['code']}_c")
                    v_compo = col_e.number_input("Note Compo /40", min_value=0.0, max_value=40.0, value=val_e_defaut, step=0.5, key=f"pc_{m['code']}_e")

                    moy_matiere = ((v_classe / 20.0) + (v_compo / 40.0)) / 3.0 * 20.0
                    moy_coeff = moy_matiere * m['coef']
                    sum_points_coeff += moy_coeff

                    nouvelles_notes[m['code']] = {
                        "classe": v_classe,
                        "compo": v_compo,
                        "moyenne": round(moy_matiere, 2),
                        "moyenne_coeff": round(moy_coeff, 2),
                        "appreciation": obtenir_appreciation(moy_matiere)
                    }

                moyenne_generale = sum_points_coeff / TOTAL_COEFFS

                submitted = st.form_submit_button("💾 Calculer et Enregistrer")
                if submitted:
                    sauvegarder_eleve(
                        id_eleve=eleve["id"],
                        nom=eleve["nom"],
                        prenom=eleve["prenom"],
                        classe=eleve["classe"],
                        notes=nouvelles_notes,
                        total_points=round(sum_points_coeff, 2),
                        moyenne=round(moyenne_generale, 2)
                    )
                    st.success(f"Bulletin mis à jour ! Moyenne Générale : {moyenne_generale:.2f}/20")
                    st.rerun()

    # --------------------------------------
    # MENU 3 : CLASSEMENT & RÉSULTATS
    # --------------------------------------
    elif menu == "3. Classement & Résultats":
        st.title("🏆 Délibération et Classement Général")
        eleves = charger_eleves()
        if eleves:
            df = pd.DataFrame(eleves)
            if "moyenne" in df.columns and not df.empty:
                df = df.sort_values(by="moyenne", ascending=False).reset_index(drop=True)
                df["Rang"] = df.index + 1
                
                st.dataframe(
                    df[["Rang", "nom", "prenom", "classe", "moyenne", "total_points"]],
                    use_container_width=True
                )
            else:
                st.info("Aucune moyenne calculée pour le moment.")

    # --------------------------------------
    # MENU 4 : IMPRESSION BULLETINS
    # --------------------------------------
    elif menu == "4. Impression des Bulletins":
        st.title("📄 Aperçu et Impression des Bulletins")
        eleves_data = charger_eleves()
        if eleves_data:
            options_eleves = {f"{e['nom'].upper()} {e['prenom']} ({e['classe']})": e for e in eleves_data}
            choix = st.selectbox("Choisir le bulletin à imprimer :", list(options_eleves.keys()))
            eleve = options_eleves[choix]

            df_eleves = pd.DataFrame(eleves_data)
            df_sorted = df_eleves.sort_values(by="moyenne", ascending=False).reset_index(drop=True)
            rang_eleve = df_sorted[df_sorted['id'] == eleve['id']].index[0] + 1 if not df_sorted.empty else 1
            total_effectif = len(eleves_data)

            notes = eleve.get("notes") or {}
            
            rows_html = ""
            total_moy_coeff = 0.0

            for m in MATIERES:
                n_data = notes.get(m['code'], {})
                c_val = f"{n_data.get('classe', 0.0):.2f}"
                e_val = f"{n_data.get('compo', 0.0):.2f}"
                m_val = f"{n_data.get('moyenne', 0.0):.2f}"
                mc_val = f"{n_data.get('moyenne_coeff', 0.0):.2f}"
                app_val = n_data.get('appreciation', obtenir_appreciation(n_data.get('moyenne', 0.0)))
                
                total_moy_coeff += n_data.get('moyenne_coeff', 0.0)

                rows_html += f"""
                <tr>
                    <td style="border:1px solid #000; padding:5px; font-weight:bold;">{m['nom']}</td>
                    <td style="border:1px solid #000; padding:5px; text-align:right;">{c_val}</td>
                    <td style="border:1px solid #000; padding:5px; text-align:right;">{e_val}</td>
                    <td style="border:1px solid #000; padding:5px; text-align:right;">{m_val}</td>
                    <td style="border:1px solid #000; padding:5px; text-align:center;">{m['coef']}</td>
                    <td style="border:1px solid #000; padding:5px; text-align:right; font-weight:bold;">{mc_val}</td>
                    <td style="border:1px solid #000; padding:5px; text-align:left;">{app_val}</td>
                </tr>
                """

            moy_gen = eleve.get('moyenne', 0.0)
            app_generale = obtenir_appreciation(moy_gen)

            html_content = f"""
            <div style="border: 2px solid #000; padding: 25px; background-color: #fff; font-family: 'Times New Roman', Times, serif; max-width: 850px; margin: auto; color: #000;">
                <div style="display: flex; justify-content: space-between; font-size: 14px; font-weight: bold;">
                    <div>
                        <p style="margin: 2px;">CAP : Kalaban-Coro</p>
                        <p style="margin: 2px;">Ecole_Privée_ : Diaratigui Coulibaly</p>
                        <p style="margin: 2px;">Classe &nbsp;&nbsp;&nbsp; {eleve['classe']}</p>
                    </div>
                    <div style="text-align: right;">
                        <p style="margin: 2px;">ANNEE SCOLAIRE 2025-2026</p>
                    </div>
                </div>
                
                <h2 style="text-align: center; margin-top: 20px; margin-bottom: 25px; font-size: 20px; font-weight: bold; letter-spacing: 1px;">BULLETIN DU PREMIER TRIMESTRE</h2>
                
                <div style="font-size: 15px; margin-bottom: 15px;">
                    <p style="margin: 5px 0;"><strong>Prénom de L'élève</strong> &nbsp;&nbsp; {eleve['prenom']}</p>
                    <p style="margin: 5px 0;"><strong>Nom de l'élève</strong> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {eleve['nom'].upper()}</p>
                </div>

                <table style="width:100%; border-collapse:collapse; font-size:13px; border: 1px solid #000;">
                    <thead>
                        <tr style="background-color:#f2f2f2;">
                            <th style="border:1px solid #000; padding:6px; text-align:left;">Matière</th>
                            <th style="border:1px solid #000; padding:6px; width:85px; text-align:center;">Note classe/20</th>
                            <th style="border:1px solid #000; padding:6px; width:85px; text-align:center;">Note compo/40</th>
                            <th style="border:1px solid #000; padding:6px; width:85px; text-align:center;">Moyenne /Matière</th>
                            <th style="border:1px solid #000; padding:6px; width:45px; text-align:center;">Coeff</th>
                            <th style="border:1px solid #000; padding:6px; width:100px; text-align:center;">Moyenne coeff/Matière</th>
                            <th style="border:1px solid #000; padding:6px; width:110px; text-align:left;">Appréciation</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                        <tr style="font-weight:bold; background-color:#f9f9f9;">
                            <td style="border:1px solid #000; padding:6px;">Total</td>
                            <td style="border:1px solid #000; padding:6px;"></td>
                            <td style="border:1px solid #000; padding:6px;"></td>
                            <td style="border:1px solid #000; padding:6px;"></td>
                            <td style="border:1px solid #000; padding:6px; text-align:center;">{TOTAL_COEFFS}</td>
                            <td style="border:1px solid #000; padding:6px; text-align:right;">{total_moy_coeff:.2f}</td>
                            <td style="border:1px solid #000; padding:6px;"></td>
                        </tr>
                    </tbody>
                </table>

                <div style="margin-top: 25px; font-size: 14px; line-height: 1.8;">
                    <p style="margin: 3px 0;"><strong>Moyenne :</strong> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {moy_gen:.2f} / 20</p>
                    <p style="margin: 3px 0;"><strong>Rang :</strong> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {rang_eleve} {"ère" if rang_eleve == 1 else "ème"} / {total_effectif} élèves classés</p>
                    <p style="margin: 5px 0; font-weight: bold; letter-spacing: 0.5px;">
                        {"FELICITATIONS !" if moy_gen >= 14 else "ENCOURAGEMENTS !" if moy_gen >= 12 else "PASSABLE" if moy_gen >= 10 else "TRAVAIL INSUFFISANT"}
                    </p>
                    <p style="margin: 5px 0;"><strong>Appréciation</strong></p>
                    <p style="margin: 2px 0;">{app_generale} !</p>
                </div>

                <div style="margin-top: 30px; text-align: right; font-weight: bold; font-size: 13px;">
                    <p style="margin-right: 30px;">Signature du directeur</p>
                </div>
            </div>
            """
            
            st.components.v1.html(html_content, height=850, scrolling=True)
            st.info("💡 Appuyez sur `Ctrl + P` pour lancer l'impression directe du bulletin au format A4.")