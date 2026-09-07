import io
import json
import pandas as pd
import streamlit as st
from supabase import Client, create_client

# Importations ReportLab pour la génération du PDF multi-pages
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

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
# 2. DONNÉES DE CONFIGURATION
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
# 3. FONCTIONS DE CALCUL
# ==========================================
def calculer_moyenne_matiere(note_classe, note_compo):
    if note_classe is None or note_compo is None:
        return 0.0
    moyenne = (float(note_classe) + float(note_compo)) / 3.0
    return round(moyenne, 2)

def calculer_bilan_eleve(notes_dict):
    total_points = 0.0
    for matiere, coef in MATIERES_COEFS.items():
        m_notes = notes_dict.get(matiere, {})
        nc = m_notes.get("classe")
        np = m_notes.get("compo")
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
# 4. GÉNÉRATION PDF MULTI-BULLETINS (REPORTLAB)
# ==========================================
def generer_pdf_bulletins_classe(df_classe):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    story = []
    styles = getSampleStyleSheet()

    # Styles personnalisés
    style_header_left = ParagraphStyle('HLeft', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=13)
    style_header_right = ParagraphStyle('HRight', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=13, alignment=TA_RIGHT)
    style_title = ParagraphStyle('Title', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=15, leading=18, alignment=TA_CENTER)
    style_body = ParagraphStyle('Body', parent=styles['Normal'], fontName='Helvetica', fontSize=11, leading=15)
    style_body_bold = ParagraphStyle('BodyBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=15)
    
    style_cell = ParagraphStyle('Cell', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=11)
    style_cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=11)
    style_cell_center = ParagraphStyle('CellCenter', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=11, alignment=TA_CENTER)
    style_cell_center_bold = ParagraphStyle('CellCenterBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=TA_CENTER)

    total_eleves = len(df_classe)

    for i, (_, eleve_obj) in enumerate(df_classe.iterrows()):
        rang = i + 1
        suffix_rang = "ère" if rang == 1 else "ème"
        
        notes_actuelles = eleve_obj.get("notes") or {}
        if isinstance(notes_actuelles, str):
            notes_actuelles = json.loads(notes_actuelles)

        # En-tête
        header_data = [
            [
                Paragraph("CAP : Kalaban-Coro<br/>Ecole Privée : Diaratigui Coulibaly<br/>Classe : " + str(eleve_obj['classe']), style_header_left),
                Paragraph("ANNEE SCOLAIRE 2025-2026", style_header_right)
            ]
        ]
        t_header = Table(header_data, colWidths=[300, 230])
        t_header.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
        story.append(t_header)
        story.append(Spacer(1, 15))

        # Titre Bulletin
        story.append(Paragraph("<u>BULLETIN DU PREMIER TRIMESTRE</u>", style_title))
        story.append(Spacer(1, 15))

        # Infos Élève
        story.append(Paragraph(f"<b>Prénom de L'élève :</b> {eleve_obj['prenom']}", style_body))
        story.append(Paragraph(f"<b>Nom de l'élève :</b> {eleve_obj['nom']}", style_body))
        story.append(Spacer(1, 12))

        # Tableau des Notes
        table_data = [
            [
                Paragraph("Matière", style_cell_center_bold),
                Paragraph("Note<br/>classe/20", style_cell_center_bold),
                Paragraph("Note<br/>compo/40", style_cell_center_bold),
                Paragraph("Moyenne<br/>/Matière", style_cell_center_bold),
                Paragraph("Coeff", style_cell_center_bold),
                Paragraph("Moyenne<br/>coeff/Matière", style_cell_center_bold),
                Paragraph("Appréciation", style_cell_center_bold)
            ]
        ]

        for mat, coef in MATIERES_COEFS.items():
            m_data = notes_actuelles.get(mat, {})
            nc = m_data.get("classe")
            np = m_data.get("compo")

            txt_nc = f"{float(nc):.2f}" if nc is not None else ""
            txt_np = f"{float(np):.2f}" if np is not None else ""

            if nc is not None and np is not None:
                moy_m = calculer_moyenne_matiere(nc, np)
                pts = round(moy_m * coef, 2)
                txt_moy = f"{moy_m:.2f}"
                txt_pts = f"{pts:.2f}"
                apprec_mat = attribuer_appreciation(moy_m)
            else:
                txt_moy = ""
                txt_pts = ""
                apprec_mat = ""

            table_data.append([
                Paragraph(mat, style_cell_bold),
                Paragraph(txt_nc, style_cell_center),
                Paragraph(txt_np, style_cell_center),
                Paragraph(txt_moy, style_cell_center),
                Paragraph(str(coef), style_cell_center),
                Paragraph(txt_pts, style_cell_center_bold),
                Paragraph(apprec_mat, style_cell)
            ])

        # Ligne Total
        table_data.append([
            Paragraph("Total", style_cell_bold),
            Paragraph("", style_cell),
            Paragraph("", style_cell),
            Paragraph("", style_cell),
            Paragraph(str(TOTAL_COEFFICIENTS), style_cell_center_bold),
            Paragraph(f"{eleve_obj['total_points']:.2f}", style_cell_center_bold),
            Paragraph("", style_cell)
        ])

        t_notes = Table(table_data, colWidths=[110, 65, 65, 65, 45, 80, 100])
        t_notes.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.8, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_notes)
        story.append(Spacer(1, 15))

        # Bilan de fin de bulletin
        moy_gen = float(eleve_obj['moyenne'])
        apprec_gen = attribuer_appreciation(moy_gen)
        
        if moy_gen >= 14:
            mention = "FELICITATIONS !"
        elif moy_gen >= 12:
            mention = "ENCOURAGEMENTS !"
        else:
            mention = "PEUT MIEUX FAIRE"

        story.append(Paragraph(f"<b>Moyenne :</b> &nbsp;&nbsp;&nbsp;&nbsp; {moy_gen:.2f} / 20", style_body))
        story.append(Paragraph(f"<b>Rang :</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {rang} {suffix_rang} / {total_eleves} élèves classés", style_body))
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"<b>{mention}</b>", style_body_bold))
        story.append(Paragraph("<b>Appréciation</b>", style_body))
        story.append(Paragraph(f"<b>{apprec_gen} !</b>", style_body_bold))
        story.append(Spacer(1, 15))

        # Signature
        story.append(Paragraph("Signature du directeur", style_header_right))

        # Saut de page pour le bulletin suivant (sauf pour le dernier élève)
        if i < total_eleves - 1:
            story.append(PageBreak())

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# ==========================================
# 5. GESTION DU MODE DE NAVIGATION STREAMLIT
# ==========================================
query_params = st.query_params
mode_mobile = query_params.get("mode") == "saisie"

if mode_mobile:
    # --------------------------------------
    # A. INTERFACE MOBILE (SAISIE DES NOTES)
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

    with st.form("form_saisie_mobile_complet"):
        nouv_notes = {}
        
        for mat, coef in MATIERES_COEFS.items():
            m_data = notes_actuelles.get(mat, {})
            val_cl = float(m_data.get("classe")) if m_data.get("classe") is not None else None
            val_co = float(m_data.get("compo")) if m_data.get("compo") is not None else None

            st.markdown(f"**{mat}** *(Coef: {coef})*")
            col_cl, col_co = st.columns(2)
            
            with col_cl:
                nc = st.number_input(
                    "Classe /20", 
                    min_value=0.0, 
                    max_value=20.0, 
                    value=val_cl, 
                    step=0.5, 
                    key=f"m_cl_{mat}"
                )
            with col_co:
                np = st.number_input(
                    "Compo /40", 
                    min_value=0.0, 
                    max_value=40.0, 
                    value=val_co, 
                    step=0.5, 
                    key=f"m_cp_{mat}"
                )
            
            if nc is not None and np is not None:
                moy_m = calculer_moyenne_matiere(nc, np)
                st.caption(f"Moyenne : {moy_m:.2f} / 20")
            else:
                st.caption("Moyenne : -- / 20")
                
            st.markdown("---")
            nouv_notes[mat] = {"classe": nc, "compo": np}

        btn_valider = st.form_submit_button("Enregistrer toutes les notes 💾", use_container_width=True)

    if btn_valider:
        champs_incomplets = [m for m, v in nouv_notes.items() if v["classe"] is None or v["compo"] is None]
        if champs_incomplets:
            st.error(f"❌ Veuillez remplir toutes les notes avant d'enregistrer. Matières incomplètes : {', '.join(champs_incomplets)}")
        else:
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
                    notes_vides = {m: {"classe": None, "compo": None} for m in MATIERES_COEFS.keys()}
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
                m_data = notes_actuelles.get(mat, {})
                val_cl = float(m_data.get("classe")) if m_data.get("classe") is not None else None
                val_co = float(m_data.get("compo")) if m_data.get("compo") is not None else None

                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                c1.write(f"{mat} (**{coef}**)")
                nc = c2.number_input(f"cl_{mat}", min_value=0.0, max_value=20.0, value=val_cl, step=0.5, label_visibility="collapsed")
                np = c3.number_input(f"cp_{mat}", min_value=0.0, max_value=40.0, value=val_co, step=0.5, label_visibility="collapsed")
                
                if nc is not None and np is not None:
                    moy_m = calculer_moyenne_matiere(nc, np)
                    c4.write(f"**{moy_m:.2f}**")
                else:
                    c4.write("--")
                
                nouv_notes[mat] = {"classe": nc, "compo": np}

            btn_save = st.form_submit_button("Enregistrer toutes les notes 💾")

        if btn_save:
            champs_incomplets = [m for m, v in nouv_notes.items() if v["classe"] is None or v["compo"] is None]
            if champs_incomplets:
                st.error(f"❌ Veuillez remplir toutes les notes avant d'enregistrer. Matières incomplètes : {', '.join(champs_incomplets)}")
            else:
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
        st.header("🖨️ Impression des Bulletins")
        if not eleves_data:
            st.warning("Aucun élève enregistré.")
            st.stop()

        df_eleves = pd.DataFrame(eleves_data)
        classe_sel = st.selectbox("Classe :", CLASSES, key="imp_cl")
        
        # Tri automatique par rang
        df_classe = df_eleves[df_eleves["classe"] == classe_sel].sort_values(by="moyenne", ascending=False).reset_index(drop=True)

        if df_classe.empty:
            st.info("Aucun élève dans cette classe.")
            st.stop()

        st.markdown("---")
        
        # BOUTON DE TÉLÉCHARGEMENT PDF UNIQUE POUR TOUTE LA CLASSE
        pdf_data = generer_pdf_bulletins_classe(df_classe)
        st.download_button(
            label=f"📄 Télécharger TOUS les bulletins de la classe {classe_sel} en PDF",
            data=pdf_data,
            file_name=f"Bulletins_{classe_sel.replace(' ', '_')}.pdf",
            mime="application/pdf",
            type="primary"
        )

        st.markdown("---")
        st.subheader("Aperçu individuel à l'écran")

        eleve_options = {f"{row['nom']} {row['prenom']}": (i+1, row) for i, row in df_classe.iterrows()}
        nom_sel = st.selectbox("Choisir un élève pour visualiser :", list(eleve_options.keys()))
        rang, eleve_obj = eleve_options[nom_sel]

        notes_actuelles = eleve_obj.get("notes") or {}
        if isinstance(notes_actuelles, str):
            notes_actuelles = json.loads(notes_actuelles)

        # Construction du tableau HTML pour aperçu écran
        rows_html = ""
        for mat, coef in MATIERES_COEFS.items():
            m_data = notes_actuelles.get(mat, {})
            nc = m_data.get("classe")
            np = m_data.get("compo")
            
            txt_nc = f"{float(nc):.2f}" if nc is not None else ""
            txt_np = f"{float(np):.2f}" if np is not None else ""
            
            if nc is not None and np is not None:
                moy_m = calculer_moyenne_matiere(nc, np)
                pts = round(moy_m * coef, 2)
                txt_moy = f"{moy_m:.2f}"
                txt_pts = f"{pts:.2f}"
                apprec_mat = attribuer_appreciation(moy_m)
            else:
                txt_moy = ""
                txt_pts = ""
                apprec_mat = ""

            rows_html += f"""
            <tr>
                <td style="padding: 4px 8px; font-weight: bold;">{mat}</td>
                <td style="text-align: center; padding: 4px;">{txt_nc}</td>
                <td style="text-align: center; padding: 4px;">{txt_np}</td>
                <td style="text-align: center; padding: 4px;">{txt_moy}</td>
                <td style="text-align: center; padding: 4px;">{coef}</td>
                <td style="text-align: center; padding: 4px; font-weight: bold;">{txt_pts}</td>
                <td style="padding: 4px 8px;">{apprec_mat}</td>
            </tr>
            """

        apprec_generale = attribuer_appreciation(float(eleve_obj['moyenne']))
        suffix_rang = "ère" if rang == 1 else "ème"

        # Rendu Aperçu
        st.markdown(f"""
        <div style="background-color: #ffffff; color: #000000; padding: 30px; border: 1px solid #ccc; font-family: 'Times New Roman', Times, serif; max-width: 800px; margin: auto;">
            
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

            <div style="font-size: 15px; margin-bottom: 8px;">
                <span style="font-weight: bold; display: inline-block; width: 160px;">Prénom de L'élève</span> : {eleve_obj['prenom']}
            </div>
            <div style="font-size: 15px; margin-bottom: 20px;">
                <span style="font-weight: bold; display: inline-block; width: 160px;">Nom de l'élève</span> : {eleve_obj['nom']}
            </div>

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

            <div style="margin-top: 30px; font-size: 15px; line-height: 1.8;">
                <div><b>Moyenne :</b> &nbsp;&nbsp;&nbsp;&nbsp; {eleve_obj['moyenne']:.2f} / 20</div>
                <div><b>Rang :</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {rang} {suffix_rang} / {len(df_classe)} élèves classés</div>
                <div style="font-weight: bold; text-transform: uppercase; margin-top: 10px; font-size: 16px;">
                    {"FELICITATIONS !" if eleve_obj['moyenne'] >= 14 else "ENCOURAGEMENTS !" if eleve_obj['moyenne'] >= 12 else "PEUT MIEUX FAIRE"}
                </div>
                <div style="margin-top: 10px;"><b>Appréciation</b></div>
                <div style="font-weight: bold; font-size: 16px;">{apprec_generale} !</div>
            </div>

            <div style="margin-top: 40px; text-align: right; font-weight: bold; font-size: 14px; padding-right: 20px;">
                Signature du directeur
            </div>

        </div>
        """, unsafe_allow_html=True)
