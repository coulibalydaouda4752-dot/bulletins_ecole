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
    "Rédaction": 3,
    "Dictée-Questions": 2,
    "Mathématique": 3,
    "Physique-chimie": 3,
    "Anglais": 2,
    "Science Nat": 2,
    "Hist-Géo": 2,
    "Ed civ. Morale": 1,
    "Ed Physique": 1,
    "Lecture": 1,
    "Récitation": 1,
    "Conduite": 1
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
query_params = st.query_params
mode_mobile = query_params.get("mode") == "saisie"

if mode_mobile:
    # --------------------------------------
    # A. INTERFACE MOBILE (SAISIE DES NOTES COMPLETE)
    # --------------------------------------
    st.title("📱 Saisie des Notes")
    st.info("Interface optimisée pour smartphones")

    eleves_data = charger_eleves_db()
    if not eleves_data:
        st.warning("Aucun élève enregistré dans la base de données.")
        st.stop()

    df_eleves = pd.DataFrame(eleves_data)
    
    classe_sel = st.selectbox("Sélectionner la classe :", CLASSES)
    df_filtrer = df_eleves[df_eleves["classe"] == classe_sel]

    if df_filtrer.empty:
        st.warning(f"Aucun élève inscrit en {classe_sel}.")
        st.stop()

    eleve_options = {f"{row['nom']} {row['prenom']}": row for _, row in df_filtrer.iterrows()}
    nom_eleve_sel = st.selectbox("Sélectionner l'élève :", list(eleve_options.keys()))
    eleve_obj = eleve_options[nom_eleve_sel]

    notes_actuelles = eleve_obj.get("notes") or {}
    if isinstance(notes_actuelles, str):
        notes_actuelles = json.loads(notes_actuelles)

    st.subheader(f"Élève : {eleve_obj['nom']} {eleve_obj['prenom']}")

    # Formulaire affichant toutes les matières à la suite (sans menu déroulant pour les matières)
    with st.form("form_saisie_mobile_complet"):
        nouv_notes = {}
        
        for mat, coef in MATIERES_COEFS.items():
            m_data = notes_actuelles.get(mat, {"classe": 0.0, "compo": 0.0})
            
            st.markdown(f"**{mat}** *(Coef: {coef})*")
            col_cl, col_co = st.columns(2)
            
            with col_cl:
                nc = st.number_input(
                    "Classe /20", 
                    min_value=0.0, 
                    max_value=20.0, 
                    value=float(m_data.get("classe", 0.0)), 
                    step=0.5, 
                    key=f"m_cl_{mat}"
                )
            with col_co:
                np = st.number_input(
                    "Compo /40", 
                    min_value=0.0, 
                    max_value=40.0, 
                    value=float(m_data.get("compo", 0.0)), 
                    step=0.5, 
                    key=f"m_cp_{mat}"
                )
            
            moy_m = calculer_moyenne_matiere(nc, np)
            st.caption(f"Moyenne : {moy_m:.2f} / 20")
            st.markdown("---")
            
            nouv_notes[mat] = {"classe": nc, "compo": np}

        btn_valider = st.form_submit_button("Enregistrer toutes les notes 💾", use_container_width=True)

    if btn_valider:
        sauvegarder_eleve_db(eleve_obj["id"], eleve_obj["nom"], eleve_obj["prenom"], eleve_obj["classe"], nouv_notes)
        st.success("Toutes les notes ont été enregistrées avec succès !")
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

        # Construction du tableau HTML exact au modèle physique
        rows_html = ""
        for mat, coef in MATIERES_COEFS.items():
            m_data = notes_actuelles.get(mat, {"classe": 0.0, "compo": 0.0})
            nc = float(m_data.get("classe", 0.0))
            np = float(m_data.get("compo", 0.0))
            moy_m = calculer_moyenne_matiere(nc, np)
            pts = round(moy_m * coef, 2)
            apprec_mat = attribuer_appreciation(moy_m)

            rows_html += f"""
            <tr>
                <td style="padding: 4px 8px; font-weight: bold;">{mat}</td>
                <td style="text-align: center; padding: 4px;">{nc:.2f}</td>
                <td style="text-align: center; padding: 4px;">{np:.2f}</td>
                <td style="text-align: center; padding: 4px;">{moy_m:.2f}</td>
                <td style="text-align: center; padding: 4px;">{coef}</td>
                <td style="text-align: center; padding: 4px; font-weight: bold;">{pts:.2f}</td>
                <td style="padding: 4px 8px;">{apprec_mat}</td>
            </tr>
            """

        apprec_generale = attribuer_appreciation(float(eleve_obj['moyenne']))
        suffix_rang = "ère" if rang == 1 else "ème"

        # Rendu du Bulletin A4 répliqué
        st.markdown("---")
        st.markdown(f"""
        <div style="background-color: #ffffff; color: #000000; padding: 30px; border: 1px solid #ccc; font-family: 'Times New Roman', Times, serif; max-width: 800px; margin: auto;">
            
            <!-- EN-TÊTE -->
            <div style="display: flex; justify-content: space-between; font-size: 14px; font-weight: bold; margin-bottom: 5px;">
                <div>CAP : Kalaban-Coro</div>
                <div>ANNEE SCOLAIRE 2025-2026</div>
            </div>
            <div style="font-size: 14px; font-weight: bold; margin-bottom: 5px;">
                Ecole Privée : Diaratigui Coulibaly
            </div>
            <div style="font-size: 14px; font-weight: bold; margin-bottom: 20px;">
                Classe &nbsp;&nbsp;&nbsp; {eleve_obj['classe']}
            </div>

            <div style="text-align: center; font-size: 20px; font-weight: bold; text-decoration: underline; margin-bottom: 25px;">
                BULLETIN DU PREMIER TRIMESTRE
            </div>

            <!-- INFOS ÉLÈVE -->
            <div style="font-size: 15px; margin-bottom: 8px;">
                <span style="font-weight: bold; display: inline-block; width: 160px;">Prénom de L'élève</span> : {eleve_obj['prenom']}
            </div>
            <div style="font-size: 15px; margin-bottom: 20px;">
                <span style="font-weight: bold; display: inline-block; width: 160px;">Nom de l'élève</span> : {eleve_obj['nom']}
            </div>

            <!-- TABLEAU DES NOTES -->
            <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 14px;">
                <thead>
                    <tr style="border-bottom: 1px solid #000;">
                        <th style="border-right: 1px solid #000; padding: 6px; text-align: left; width: 25%;">Matière</th>
                        <th style="border-right: 1px solid #000; padding: 6px; text-align: center;">Note<br>classe/20</th>
                        <th style="border-right: 1px solid #000; padding: 6px; text-align: center;">Note<br>compo/40</th>
                        <th style="border-right: 1px solid #000; padding: 6px; text-align: center;">Moyenne<br>/Matière</th>
                        <th style="border-right: 1px solid #000; padding: 6px; text-align: center;">Coeff</th>
                        <th style="border-right: 1px solid #000; padding: 6px; text-align: center;">Moyenne<br>coeff/Matière</th>
                        <th style="padding: 6px; text-align: left;">Appréciation</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                    <tr style="border-top: 1px solid #000; font-weight: bold;">
                        <td style="border-right: 1px solid #000; padding: 6px;">Total</td>
                        <td style="border-right: 1px solid #000;"></td>
                        <td style="border-right: 1px solid #000;"></td>
                        <td style="border-right: 1px solid #000;"></td>
                        <td style="border-right: 1px solid #000; text-align: center; padding: 6px;">{TOTAL_COEFFICIENTS}</td>
                        <td style="border-right: 1px solid #000; text-align: center; padding: 6px;">{eleve_obj['total_points']:.2f}</td>
                        <td></td>
                    </tr>
                </tbody>
            </table>

            <!-- BILAN BAS DE PAGE -->
            <div style="margin-top: 30px; font-size: 15px; line-height: 1.8;">
                <div><b>Moyenne :</b> &nbsp;&nbsp;&nbsp;&nbsp; {eleve_obj['moyenne']:.2f} / 20</div>
                <div><b>Rang :</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {rang} {suffix_rang} / {len(df_classe)} élèves classés</div>
                <div style="font-weight: bold; text-transform: uppercase; margin-top: 10px; font-size: 16px;">
                    {"FELICITATIONS !" if eleve_obj['moyenne'] >= 14 else "ENCOURAGEMENTS !" if eleve_obj['moyenne'] >= 12 else "PEUT MIEUX FAIRE"}
                </div>
                <div style="margin-top: 10px;"><b>Appréciation</b></div>
                <div style="font-weight: bold; font-size: 16px;">{apprec_generale} !</div>
            </div>

            <!-- SIGNATURE -->
            <div style="margin-top: 40px; text-align: right; font-weight: bold; font-size: 14px; padding-right: 20px;">
                Signature du directeur
            </div>

        </div>
        """, unsafe_allow_html=True)
