import streamlit as st
import pandas as pd
from supabase import create_client, Client
import json

# ==========================================
# 1. CONFIGURATION DE LA PAGE & SUPABASE
# ==========================================
st.set_page_config(
    page_title="Gestion des Bulletins - École Privée Diaratigui Coulibaly",
    page_icon="🎓",
    layout="wide"
)

# Initialisation de Supabase
@st.cache_resource
def init_supabase() -> Client:
    # Récupération des identifiants depuis secrets.toml ou st.secrets
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    st.error("Erreur de connexion à la base de données Supabase. Vérifiez vos secrets.")
    st.stop()

# ==========================================
# 2. DONNÉES DE CONFIGURATION (MATIÈRES & COEFS)
# ==========================================
MATIERES_COEFS = {
    "Rédaction / Composition": 2,
    "Dictée / Questions": 1,
    "Lecture / Explication": 1,
    "Étude de texte": 2,
    "Mathématiques": 4,
    "Physique - Chimie": 2,
    "Sciences de la Vie et de la Terre (SVT)": 2,
    "Histoire - Géographie": 2,
    "Anglais": 2,
    "Éducation Civique et Morale (ECM)": 1,
    "Éducation Physique et Sportive (EPS)": 1,
    "Dessin / Travaux Pratiques": 1
}

TOTAL_COEFFICIENTS = sum(MATIERES_COEFS.values()) # 22

CLASSES = ["7-ème A", "7-ème B", "8-ème A", "8-ème B", "9-ème Année"]

# ==========================================
# 3. FONCTIONS DE CALCUL ET FONCTIONNELLES
# ==========================================
def calculer_moyenne_matiere(note_classe, note_compo):
    """
    Note Classe /20
    Note Compo /40
    Moyenne Matière (/20) = (Note_Classe + Note_Compo) / 3
    """
    if note_classe is None or note_compo is None:
        return 0.0
    moyenne = (float(note_classe) + float(note_compo)) / 3.0
    return round(moyenne, 2)

def calculer_bilan_eleve(notes_dict):
    """
    Calcule le total des points et la moyenne générale
    """
    total_points = 0.0
    for matiere, coef in MATIERES_COEFS.items():
        m_notes = notes_dict.get(matiere, {})
        nc = m_notes.get("classe", 0.0)
        np = m_notes.get("compo", 0.0)
        moy_mat = calculer_moyenne_matiere(nc, np)
        total_points += moy_mat * coef
        
    moyenne_generale = total_points / TOTAL_COEFFICIENTS if TOTAL_COEFFICIENTS > 0 else 0.0
    return round(total_points, 2), round(moyenne_generale, 2)

def attribuer_appreciation(moyenne):
    if moyenne >= 16:
        return "Excellent"
    elif moyenne >= 14:
        return "Très Bien"
    elif moyenne >= 12:
        return "Bien"
    elif moyenne >= 10:
        return "Passable"
    elif moyenne >= 8:
        return "Insuffisant"
    else:
        return "Médiocre"

def charger_eleves_db():
    response = supabase.table("eleves").select("*").execute()
    return response.data

def sauvegarder_eleve_db(id_eleve, nom, prenom, classe, notes_dict):
    total_pts, moy_gen = calculer_bilan_eleve(notes_dict)
    data = {
        "nom": nom,
        "prenom": prenom,
        "classe": classe,
        "notes": notes_dict,
        "total_points": total_pts,
        "moyenne": moy_gen
    }
    if id_eleve:
        supabase.table("eleves").update(data).eq("id", id_eleve).execute()
    else:
        supabase.table("eleves").insert(data).execute()

# ==========================================
# 4. GESTION DU MODE DE NAVIGATION
# ==========================================
# Détection automatique du paramètre URL ?mode=saisie
query_params = st.query_params
mode_mobile = query_params.get("mode") == "saisie"

if mode_mobile:
    # --------------------------------------
    # A. INTERFACE MOBILE (SAISIE DES NOTES)
    # --------------------------------------
    st.title("📱 Saisie Rapide des Notes")
    st.info("Interface optimisée pour smartphones - Assistants & Enseignants")

    eleves_data = charger_eleves_db()
    if not eleves_data:
        st.warning("Aucun élève enregistré dans la base de données.")
        st.stop()

    df_eleves = pd.DataFrame(eleves_data)
    
    # Sélection de la classe et de l'élève
    classe_sel = st.selectbox("Sélectionner la classe :", CLASSES)
    df_filtrer = df_eleves[df_eleves["classe"] == classe_sel]

    if df_filtrer.empty:
        st.warning(f"Aucun élève inscrit en {classe_sel}.")
        st.stop()

    eleve_options = {f"{row['nom']} {row['prenom']}": row for _, row in df_filtrer.iterrows()}
    nom_eleve_sel = st.selectbox("Sélectionner l'élève :", list(eleve_options.keys()))
    eleve_obj = eleve_options[nom_eleve_sel]

    # Récupération des notes existantes
    notes_actuelles = eleve_obj.get("notes") or {}
    if isinstance(notes_actuelles, str):
        notes_actuelles = json.loads(notes_actuelles)

    st.subheader(f"Élève : {eleve_obj['nom']} {eleve_obj['prenom']}")

    # Choix de la matière
    matiere_sel = st.selectbox("Choisir la matière :", list(MATIERES_COEFS.keys()))
    notes_mat = notes_actuelles.get(matiere_sel, {"classe": 0.0, "compo": 0.0})

    with st.form("form_saisie_mobile"):
        note_cl = st.number_input("Note de Classe (/20) :", min_value=0.0, max_value=20.0, value=float(notes_mat.get("classe", 0.0)), step=0.5)
        note_co = st.number_input("Note de Composition (/40) :", min_value=0.0, max_value=40.0, value=float(notes_mat.get("compo", 0.0)), step=0.5)
        
        moy_preview = calculer_moyenne_matiere(note_cl, note_co)
        st.write(f"**Moyenne estimée dans cette matière :** {moy_preview} / 20")

        btn_valider = st.form_submit_button("Enregistrer la note 💾")

    if btn_valider:
        notes_actuelles[matiere_sel] = {"classe": note_cl, "compo": note_co}
        sauvegarder_eleve_db(eleve_obj["id"], eleve_obj["nom"], eleve_obj["prenom"], eleve_obj["classe"], notes_actuelles)
        st.success(f"Notes enregistrées avec succès pour {matiere_sel} !")
        st.rerun()

else:
    # --------------------------------------
    # B. INTERFACE PC (ADMINISTRATION COMPLETE)
    # --------------------------------------
    st.sidebar.title("🏛️ Administration Centralisée")
    st.sidebar.write("École Privée Diaratigui Coulibaly")

    menu = st.sidebar.radio(
        "Navigation :",
        [
            "1. Gestion des Élèves",
            "2. Saisie des Notes (PC)",
            "3. Classement & Résultats",
            "4. Impression des Bulletins"
        ]
    )

    eleves_data = charger_eleves_db()

    # --- MENU 1 : GESTION DES ÉLÈVES ---
    if menu == "1. Gestion des Élèves":
        st.header("👤 Inscription et Gestion des Élèves")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            with st.form("form_inscript"):
                st.subheader("Nouvel Élève")
                nom = st.text_input("Nom de famille :")
                prenom = st.text_input("Prénom :")
                classe = st.selectbox("Classe :", CLASSES)
                btn_ajouter = st.form_submit_button("Ajouter à la base")

                if btn_ajouter and nom and prenom:
                    notes_vides = {m: {"classe": 0.0, "compo": 0.0} for m in MATIERES_COEFS.keys()}
                    sauvegarder_eleve_db(None, nom.upper(), prenom.title(), classe, notes_vides)
                    st.success("Élève inscrit avec succès !")
                    st.rerun()

        with col2:
            st.subheader("Effectif enregistré")
            if eleves_data:
                df = pd.DataFrame(eleves_data)
                st.dataframe(df[["id", "nom", "prenom", "classe", "moyenne", "total_points"]], use_container_width=True)
            else:
                st.info("Aucun élève enregistré.")

    # --- MENU 2 : SAISIE DES NOTES (PC) ---
    elif menu == "2. Saisie des Notes (PC)":
        st.header("📝 Saisie Globale des Notes")
        if not eleves_data:
            st.warning("Veuillez d'abord inscrire des élèves.")
            st.stop()

        df_eleves = pd.DataFrame(eleves_data)
        classe_sel = st.selectbox("Filtrer par classe :", CLASSES)
        df_filtrer = df_eleves[df_eleves["classe"] == classe_sel]

        if df_filtrer.empty:
            st.warning("Aucun élève dans cette classe.")
            st.stop()

        eleve_options = {f"{row['nom']} {row['prenom']}": row for _, row in df_filtrer.iterrows()}
        nom_eleve_sel = st.selectbox("Choisir l'élève :", list(eleve_options.keys()))
        eleve_obj = eleve_options[nom_eleve_sel]

        notes_actuelles = eleve_obj.get("notes") or {}
        if isinstance(notes_actuelles, str):
            notes_actuelles = json.loads(notes_actuelles)

        st.subheader(f"Édition du bulletin : {eleve_obj['nom']} {eleve_obj['prenom']} ({classe_sel})")

        with st.form("form_saisie_pc"):
            nouv_notes = {}
            cols_h = st.columns([3, 2, 2, 2])
            cols_h[0].write("**Matière (Coef)**")
            cols_h[1].write("**Classe (/20)**")
            cols_h[2].write("**Compo (/40)**")
            cols_h[3].write("**Moyenne (/20)**")

            for mat, coef in MATIERES_COEFS.items():
                m_data = notes_actuelles.get(mat, {"classe": 0.0, "compo": 0.0})
                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                c1.write(f"{mat} (**{coef}**)")
                nc = c2.number_input(f"cl_{mat}", min_value=0.0, max_value=20.0, value=float(m_data.get("classe", 0.0)), step=0.5, label_visibility="collapsed")
                np = c3.number_input(f"cp_{mat}", min_value=0.0, max_value=40.0, value=float(m_data.get("compo", 0.0)), step=0.5, label_visibility="collapsed")
                moy_m = calculer_moyenne_matiere(nc, np)
                c4.write(f"**{moy_m:.2f}**")
                
                nouv_notes[mat] = {"classe": nc, "compo": np}

            btn_save = st.form_submit_button("Enregistrer toutes les notes 💾")

        if btn_save:
            sauvegarder_eleve_db(eleve_obj["id"], eleve_obj["nom"], eleve_obj["prenom"], eleve_obj["classe"], nouv_notes)
            st.success("Toutes les notes ont été mises à jour !")
            st.rerun()

    # --- MENU 3 : CLASSEMENT & RÉSULTATS ---
    elif menu == "3. Classement & Résultats":
        st.header("🏆 Classement Général par Classe")
        if not eleves_data:
            st.warning("Aucune donnée disponible.")
            st.stop()

        df_eleves = pd.DataFrame(eleves_data)
        classe_sel = st.selectbox("Sélectionner la classe :", CLASSES)
        df_classe = df_eleves[df_eleves["classe"] == classe_sel].copy()

        if df_classe.empty:
            st.info("Aucun élève dans cette classe.")
        else:
            # Tri par moyenne décroissante
            df_classe = df_classe.sort_values(by="moyenne", ascending=False).reset_index(drop=True)
            df_classe["Rang"] = df_classe.index + 1
            df_classe["Appréciation"] = df_classe["moyenne"].apply(attribuer_appreciation)

            st.dataframe(
                df_classe[["Rang", "nom", "prenom", "total_points", "moyenne", "Appréciation"]],
                use_container_width=True
            )

    # --- MENU 4 : IMPRESSION DES BULLETINS ---
    elif menu == "4. Impression des Bulletins":
        st.header("🖨️ Impression du Bulletin de Notes")
        if not eleves_data:
            st.warning("Aucun élève enregistré.")
            st.stop()

        df_eleves = pd.DataFrame(eleves_data)
        classe_sel = st.selectbox("Classe :", CLASSES, key="imp_cl")
        df_classe = df_eleves[df_eleves["classe"] == classe_sel].sort_values(by="moyenne", ascending=False).reset_index(drop=True)

        if df_classe.empty:
            st.info("Aucun élève dans cette classe.")
            st.stop()

        eleve_options = {f"{row['nom']} {row['prenom']}": (i+1, row) for i, row in df_classe.iterrows()}
        nom_sel = st.selectbox("Élève :", list(eleve_options.keys()))
        rang, eleve_obj = eleve_options[nom_sel]

        notes_actuelles = eleve_obj.get("notes") or {}
        if isinstance(notes_actuelles, str):
            notes_actuelles = json.loads(notes_actuelles)

        # Aperçu du bulletin A4 HTML
        st.markdown("---")
        st.markdown(f"""
        <div style="border:2px solid #000; padding:20px; font-family:Arial, sans-serif; background-color:#ffffff; color:#000000;">
            <div style="text-align:center;">
                <h2>ÉCOLE PRIVÉE DIARATIGUI COULIBALY</h2>
                <p><b>BULLETIN DE NOTES DU 1ER SEMESTRE</b></p>
                <hr>
            </div>
            <p><b>Nom & Prénom :</b> {eleve_obj['nom']} {eleve_obj['prenom']}<br>
            <b>Classe :</b> {eleve_obj['classe']} | <b>Rang :</b> {rang}e / {len(df_classe)}</p>
            
            <table style="width:100%; border-collapse:collapse; margin-top:15px;" border="1">
                <thead>
                    <tr style="background-color:#f2f2f2;">
                        <th>Matière</th>
                        <th>Coef</th>
                        <th>Note Cl. (/20)</th>
                        <th>Note Comp. (/40)</th>
                        <th>Moy. (/20)</th>
                        <th>Total Pts</th>
                    </tr>
                </thead>
                <tbody>
        """, unsafe_allow_html=True)

        for mat, coef in MATIERES_COEFS.items():
            m_data = notes_actuelles.get(mat, {"classe": 0.0, "compo": 0.0})
            nc = float(m_data.get("classe", 0.0))
            np = float(m_data.get("compo", 0.0))
            moy_m = calculer_moyenne_matiere(nc, np)
            pts = round(moy_m * coef, 2)

            st.markdown(f"""
                <tr>
                    <td style="padding:5px;">{mat}</td>
                    <td style="text-align:center;">{coef}</td>
                    <td style="text-align:center;">{nc:.2f}</td>
                    <td style="text-align:center;">{np:.2f}</td>
                    <td style="text-align:center;"><b>{moy_m:.2f}</b></td>
                    <td style="text-align:center;">{pts:.2f}</td>
                </tr>
            """, unsafe_allow_html=True)

        apprec = attribuer_appreciation(float(eleve_obj['moyenne']))
        st.markdown(f"""
                </tbody>
            </table>
            <br>
            <div style="display:flex; justify-scale:space-between;">
                <p><b>Total Coefficients :</b> {TOTAL_COEFFICIENTS}</p>
                <p><b>Total Points :</b> {eleve_obj['total_points']:.2f}</p>
                <p><b>Moyenne Générale :</b> <span style="font-size:18px;"><b>{eleve_obj['moyenne']:.2f} / 20</b></span></p>
            </div>
            <p><b>Appréciation globale :</b> {apprec}</p>
            <br><br>
            <div style="display:flex; justify-scale:space-between; text-align:center;">
                <div><b>L'Enseignant / Assistant</b></div>
                <div><b>Le Directeur</b></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
