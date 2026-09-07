import io
import os
import json
import textwrap
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from supabase import Client, create_client

# Importations ReportLab pour la génération du PDF multi-pages
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ==========================================
# 1. CONFIGURATION DE LA PAGE & SUPABASE
# ==========================================
st.set_page_config(
    page_title="Gestion des Bulletins - École Privée Diaratigui COULIBALY",
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
# 2. DONNÉES DE CONFIGURATION & CITATIONS
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

CITATIONS_EDUCATIVES = [
    "« L'éducation est l'arme la plus puissante qu'on puisse utiliser pour changer le monde. » – Nelson Mandela",
    "« Le savoir est la seule matière qui s'accroît quand on la partage. » – Socrate",
    "« Apprendre sans réfléchir est vain ; réfléchir sans apprendre est dangereux. » – Confucius",
    "« L'apprentissage est un trésor qui suivra son propriétaire partout. » – Proverbe chinois",
    "« La connaissance s'acquiert par l'expérience, tout le reste n'est que de l'information. » – Albert Einstein",
    "« L'éducation n'est pas le fait d'apprendre des faits, mais de former l'esprit à penser. » – Albert Einstein",
    "« Tu me dis, j'oublie. Tu m'enseignes, je me souviens. Tu m'impliques, j'apprends. » – Benjamin Franklin",
    "« Les racines de l'éducation sont amères, mais ses fruits sont doux. » – Aristote",
    "« Le succès est la somme de petits efforts, répétés jour après jour. » – Robert Collier",
    "« Ce n'est pas parce que les choses sont difficiles que nous n'osons pas, c'est parce que nous n'osons pas qu'elles sont difficiles. » – Sénèque",
    "« Il n'y a pas d'ascenseur pour le succès, il faut prendre l'escalier. » – Proverbe",
    "« La discipline est le pont entre les objectifs et les réalisations. » – Jim Rohn",
    "« Le seul endroit où le succès vient avant le travail, c'est dans le dictionnaire. » – Vidal Sassoon",
    "« Travaillez dur en silence, laissez votre succès faire du bruit. » – Frank Ocean",
    "« La patience et la persévérance ont un effet magique devant lequel les difficultés disparaissent. » – John Quincy Adams",
    "« Les grandes choses ne sont pas réalisées par la force, mais par la persévérance. » – Samuel Johnson",
    "« Il n'y a pas d'échec, il n'y a que de l'apprentissage. » – Nelson Mandela",
    "« Je ne perds jamais. Soit je gagne, soit j'apprends. » – Nelson Mandela",
    "« Le succès consiste à aller d'échec en échec sans perdre son enthousiasme. » – Winston Churchill",
    "« La plus grande gloire n'est pas de ne jamais tomber, mais de se relever à chaque chute. » – Confucius",
    "« L'erreur n'est pas l'opposé de la réussite, elle fait partie de la réussite. » – Arianna Huffington",
    "« Le futur appartient à ceux qui croient en la beauté de leurs rêves. » – Eleanor Roosevelt",
    "« Se former, c'est investir dans son propre avenir. »",
    "« Vis comme si tu devais mourir demain. Apprends comme si tu devais vivre toujours. » – Mahatma Gandhi",
    "« Le courage, c'est d'aller à l'idéal et de comprendre le réel. » – Jean Jaurès",
    "« Crois en tes rêves et ils se réaliseront peut-être. Crois en toi et ils se réaliseront sûrement. » – Martin Luther King",
    "« Ce que l'on fait avec passion se fait toujours bien. »",
    "« Ne limite pas tes défis, défie tes limites. »",
    "« Chaque jour est une nouvelle opportunité d'apprendre et de progresser. »",
    "« L'esprit est comme un parachute : il ne fonctionne que lorsqu'il est ouvert. » – Albert Einstein"
]

# ==========================================
# 3. FONCTIONS DE CALCUL ET BASE DE DONNÉES
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

def supprimer_eleve_db(id_eleve):
    supabase.table("eleves").delete().eq("id", id_eleve).execute()

# --- FONCTIONS HISTORIQUE DE BULLETINS ---
def archiver_bulletins_db(df_classe, annee_scolaire, trimestre):
    enregistrements = []
    for i, (_, eleve) in enumerate(df_classe.iterrows()):
        rang = i + 1
        notes = eleve.get("notes") or {}
        if isinstance(notes, str):
            try:
                notes = json.loads(notes)
            except json.JSONDecodeError:
                notes = {}
                
        rec = {
            "eleve_id": eleve.get("id"),
            "nom": eleve["nom"],
            "prenom": eleve["prenom"],
            "classe": eleve["classe"],
            "annee_scolaire": annee_scolaire,
            "trimestre": trimestre,
            "moyenne": float(eleve["moyenne"]),
            "total_points": float(eleve["total_points"]),
            "rang": rang,
            "notes": notes
        }
        enregistrements.append(rec)
    
    try:
        supabase.table("historique_bulletins").insert(enregistrements).execute()
    except Exception as e:
        st.warning(f"Note : Archivage : {e}")

def charger_historique_db(annee=None, trimestre=None, classe=None):
    query = supabase.table("historique_bulletins").select("*")
    if annee:
        query = query.eq("annee_scolaire", annee)
    if trimestre:
        query = query.eq("trimestre", trimestre)
    if classe:
        query = query.eq("classe", classe)
    
    response = query.order("created_at", desc=True).execute()
    return response.data

# ==========================================
# 4. GÉNÉRATION PDF MULTI-BULLETINS (REPORTLAB)
# ==========================================
def generer_pdf_bulletins_classe(df_classe, annee_scolaire, trimestre):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=25,
        bottomMargin=25
    )

    story = []
    styles = getSampleStyleSheet()

    style_header_left = ParagraphStyle('HLeft', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=12)
    style_header_right = ParagraphStyle('HRight', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=12, alignment=TA_RIGHT)
    style_title = ParagraphStyle('Title', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=14, leading=17, alignment=TA_CENTER, textColor=colors.HexColor('#0F2C59'))
    style_body = ParagraphStyle('Body', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=14)
    style_body_bold = ParagraphStyle('BodyBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=14)
    
    style_cell = ParagraphStyle('Cell', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=11)
    style_cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=11)
    style_cell_center = ParagraphStyle('CellCenter', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=11, alignment=TA_CENTER)
    style_cell_center_bold = ParagraphStyle('CellCenterBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=11, alignment=TA_CENTER)
    
    style_citation = ParagraphStyle('Citation', parent=styles['Italic'], fontName='Helvetica-Oblique', fontSize=8, leading=10, alignment=TA_CENTER, textColor=colors.HexColor('#4B5563'))

    total_eleves = len(df_classe)

    for i, (_, eleve_obj) in enumerate(df_classe.iterrows()):
        rang = i + 1
        suffix_rang = "ère" if rang == 1 else "ème"
        
        notes_actuelles = eleve_obj.get("notes") or {}
        if isinstance(notes_actuelles, str):
            try:
                notes_actuelles = json.loads(notes_actuelles)
            except json.JSONDecodeError:
                notes_actuelles = {}

        LOGO_PATH = "logo.png"
        if os.path.exists(LOGO_PATH):
            try:
                logo_img = Image(LOGO_PATH, width=50, height=50)
            except Exception:
                logo_img = Paragraph("<font size=12 color='#0F2C59'><b>EPDC</b></font>", style_cell_center_bold)
        else:
            logo_img = Paragraph("<font size=12 color='#0F2C59'><b>EPDC</b></font>", style_cell_center_bold)

        header_right_text = f"ANNÉE SCOLAIRE : {annee_scolaire}<br/><font color='#1E3A8A'><b>{trimestre}</b></font>"

        # En-tête avec COULIBALY en majuscule
        header_data = [
            [
                Paragraph("CAP : Kalaban-Coro<br/><b>Ecole Privée : Diaratigui COULIBALY</b><br/>Classe : " + str(eleve_obj['classe']), style_header_left),
                logo_img,
                Paragraph(header_right_text, style_header_right)
            ]
        ]
        t_header = Table(header_data, colWidths=[210, 110, 210])
        t_header.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (1,0), (1,0), 'CENTER'),
        ]))
        story.append(t_header)
        story.append(Spacer(1, 10))

        story.append(Paragraph(f"<u>BULLETIN DE NOTES - {trimestre}</u>", style_title))
        story.append(Spacer(1, 10))

        story.append(Paragraph(f"<b>Prénom de L'élève :</b> {eleve_obj['prenom']}", style_body))
        story.append(Paragraph(f"<b>Nom de l'élève :</b> {eleve_obj['nom']}", style_body))
        story.append(Spacer(1, 10))

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
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(t_notes)
        story.append(Spacer(1, 10))

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
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>{mention}</b>", style_body_bold))
        story.append(Paragraph("<b>Appréciation</b>", style_body))
        story.append(Paragraph(f"<b>{apprec_gen} !</b>", style_body_bold))
        
        # Réduction de l'espace avant la signature pour la remonter et laisser de la place au tampon
        story.append(Spacer(1, 2))
        story.append(Paragraph("Signature du directeur", style_header_right))
        story.append(Spacer(1, 45)) # Espace disponible sous la signature pour le cachet

        citation = CITATIONS_EDUCATIVES[i % len(CITATIONS_EDUCATIVES)]
        t_citation = Table([[Paragraph(f"💡 <i>{citation}</i>", style_citation)]], colWidths=[530])
        t_citation.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LINEABOVE', (0,0), (-1,0), 0.5, colors.HexColor('#CBD5E1')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_citation)

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
        try:
            notes_actuelles = json.loads(notes_actuelles)
        except json.JSONDecodeError:
            notes_actuelles = {}

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
                nc = st.number_input("Classe /20", min_value=0.0, max_value=20.0, value=val_cl, step=0.5, key=f"m_cl_{mat}")
            with col_co:
                np = st.number_input("Compo /40", min_value=0.0, max_value=40.0, value=val_co, step=0.5, key=f"m_cp_{mat}")
            
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
    st.sidebar.title("🏛️ Administration Centralisée")
    st.sidebar.write("École Privée Diaratigui COULIBALY")

    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Configuration Bulletins")
    annee_scolaire_input = st.sidebar.text_input("Année Scolaire", value="2025-2026")
    trimestre_input = st.sidebar.selectbox(
        "Période / Trimestre",
        ["1er TRIMESTRE", "2ème TRIMESTRE", "3ème TRIMESTRE"]
    )
    st.sidebar.markdown("---")

    menu = st.sidebar.radio(
        "Navigation :",
        [
            "1. Gestion des Élèves",
            "2. Saisie des Notes (PC)",
            "3. Classement & Résultats",
            "4. Impression des Bulletins",
            "5. Historique des Bulletins 📜"
        ]
    )

    eleves_data = charger_eleves_db()

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
                
                st.markdown("---")
                st.subheader("🗑️ Supprimer un élève")
                
                eleve_suppr_options = {f"{row['nom']} {row['prenom']} ({row['classe']})": row['id'] for _, row in df.iterrows()}
                eleve_a_supprimer_label = st.selectbox("Sélectionner l'élève à supprimer :", list(eleve_suppr_options.keys()))
                
                id_a_supprimer = eleve_suppr_options[eleve_a_supprimer_label]
                
                if st.button("❌ Supprimer définitivement cet élève", type="primary"):
                    supprimer_eleve_db(id_a_supprimer)
                    st.success("L'élève a été supprimé de la base de données.")
                    st.rerun()
            else:
                st.info("Aucun élève enregistré.")

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
            try:
                notes_actuelles = json.loads(notes_actuelles)
            except json.JSONDecodeError:
                notes_actuelles = {}

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

    elif menu == "4. Impression des Bulletins":
        st.header("🖨️ Impression des Bulletins")
        if not eleves_data:
            st.warning("Aucun élève enregistré.")
            st.stop()

        df_eleves = pd.DataFrame(eleves_data)
        classe_sel = st.selectbox("Classe :", CLASSES, key="imp_cl")
        
        df_classe = df_eleves[df_eleves["classe"] == classe_sel].sort_values(by="moyenne", ascending=False).reset_index(drop=True)

        if df_classe.empty:
            st.info("Aucun élève dans cette classe.")
            st.stop()

        st.markdown("---")
        
        pdf_data = generer_pdf_bulletins_classe(df_classe, annee_scolaire_input, trimestre_input)
        
        col_btn1, col_btn2 = st.columns([2, 1])
        with col_btn1:
            btn_dl = st.download_button(
                label=f"📄 Télécharger TOUS les bulletins ({classe_sel}) - {trimestre_input} en PDF",
                data=pdf_data,
                file_name=f"Bulletins_{classe_sel.replace(' ', '_')}_{trimestre_input.replace(' ', '_')}.pdf",
                mime="application/pdf",
                type="primary"
            )
        
        if btn_dl:
            archiver_bulletins_db(df_classe, annee_scolaire_input, trimestre_input)
            st.success("✅ Bulletins générés et archivés avec succès !")

        st.markdown("---")
        st.subheader("Aperçu individuel à l'écran")

        eleve_options = {f"{row['nom']} {row['prenom']}": (i, row) for i, row in df_classe.iterrows()}
        nom_sel = st.selectbox("Choisir un élève pour visualiser :", list(eleve_options.keys()))
        idx_eleve, eleve_obj = eleve_options[nom_sel]
        rang_eleve = idx_eleve + 1

        notes_actuelles = eleve_obj.get("notes") or {}
        if isinstance(notes_actuelles, str):
            try:
                notes_actuelles = json.loads(notes_actuelles)
            except json.JSONDecodeError:
                notes_actuelles = {}

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
            <tr style="border-bottom: 1px solid #ccc;">
                <td style="padding: 6px 8px; font-weight: bold;">{mat}</td>
                <td style="text-align: center; padding: 6px; border-left: 1px solid #ccc;">{txt_nc}</td>
                <td style="text-align: center; padding: 6px; border-left: 1px solid #ccc;">{txt_np}</td>
                <td style="text-align: center; padding: 6px; border-left: 1px solid #ccc;">{txt_moy}</td>
                <td style="text-align: center; padding: 6px; border-left: 1px solid #ccc;">{coef}</td>
                <td style="text-align: center; padding: 6px; border-left: 1px solid #ccc; font-weight: bold;">{txt_pts}</td>
                <td style="padding: 6px 8px; border-left: 1px solid #ccc;">{apprec_mat}</td>
            </tr>"""

        apprec_generale = attribuer_appreciation(float(eleve_obj['moyenne']))
        suffix_rang = "ère" if rang_eleve == 1 else "ème"
        citation_apercu = CITATIONS_EDUCATIVES[idx_eleve % len(CITATIONS_EDUCATIVES)]
        mention = "FELICITATIONS !" if eleve_obj['moyenne'] >= 14 else "ENCOURAGEMENTS !" if eleve_obj['moyenne'] >= 12 else "PEUT MIEUX FAIRE"

        bulletin_html = textwrap.dedent(f"""
        <div style="background-color: #ffffff; color: #000000; padding: 25px; border: 1px solid #ccc; border-radius: 6px; font-family: 'Times New Roman', Times, serif; max-width: 800px; margin: auto;">
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 13px; font-weight: bold; margin-bottom: 15px;">
                <div style="width: 38%; text-align: left; line-height: 1.4;">
                    CAP : Kalaban-Coro<br>
                    Ecole Privée : Diaratigui COULIBALY<br>
                    Classe : {eleve_obj['classe']}
                </div>
                <div style="width: 24%; text-align: center;">
                    <div style="font-size: 22px; color: #0F2C59; font-weight: bold;">EPDC</div>
                </div>
                <div style="width: 38%; text-align: right; line-height: 1.4;">
                    ANNÉE SCOLAIRE : {annee_scolaire_input}<br>
                    <span style="color: #1E3A8A;">{trimestre_input}</span>
                </div>
            </div>

            <div style="text-align: center; font-size: 18px; font-weight: bold; text-decoration: underline; margin: 20px 0; color: #0F2C59;">
                BULLETIN DE NOTES - {trimestre_input}
            </div>

            <div style="font-size: 15px; margin-bottom: 6px;">
                <span style="font-weight: bold; display: inline-block; width: 160px;">Prénom de L'élève</span> : {eleve_obj['prenom']}
            </div>
            <div style="font-size: 15px; margin-bottom: 20px;">
                <span style="font-weight: bold; display: inline-block; width: 160px;">Nom de l'élève</span> : {eleve_obj['nom']}
            </div>

            <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 13px;">
                <thead>
                    <tr style="border-bottom: 1px solid #000; background-color: #f2f2f2;">
                        <th style="border-right: 1px solid #000; padding: 6px; text-align: left; width: 28%;">Matière</th>
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
                    <tr style="border-top: 2px solid #000; font-weight: bold; background-color: #fdfdfd;">
                        <td style="padding: 6px 8px;">Total</td>
                        <td style="border-left: 1px solid #ccc;"></td>
                        <td style="border-left: 1px solid #ccc;"></td>
                        <td style="border-left: 1px solid #ccc;"></td>
                        <td style="text-align: center; padding: 6px; border-left: 1px solid #ccc;">{TOTAL_COEFFICIENTS}</td>
                        <td style="text-align: center; padding: 6px; border-left: 1px solid #ccc;">{eleve_obj['total_points']:.2f}</td>
                        <td style="border-left: 1px solid #ccc;"></td>
                    </tr>
                </tbody>
            </table>

            <div style="margin-top: 20px; font-size: 14px; line-height: 1.6;">
                <div><b>Moyenne :</b> &nbsp;&nbsp;&nbsp;&nbsp; {eleve_obj['moyenne']:.2f} / 20</div>
                <div><b>Rang :</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {rang_eleve} {suffix_rang} / {len(df_classe)} élèves classés</div>
                <div style="margin-top: 8px; font-weight: bold;">{mention}</div>
                <div style="margin-top: 4px;"><b>Appréciation :</b> {apprec_generale} !</div>
            </div>

            <!-- Ajustement de la marge haute pour remonter la signature et laisser un espace libre en dessous -->
            <div style="text-align: right; margin-top: 5px; margin-bottom: 55px; font-weight: bold; font-size: 13px;">
                Signature du directeur
            </div>

            <div style="margin-top: 20px; border-top: 1px solid #cbd5e1; padding-top: 8px; text-align: center; font-style: italic; font-size: 12px; color: #4b5563;">
                💡 {citation_apercu}
            </div>
        </div>
        """)

        components.html(bulletin_html, height=850, scrolling=True)

    elif menu == "5. Historique des Bulletins 📜":
        st.header("📜 Historique des Bulletins Archivés")
        
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            annee_h = st.text_input("Filtrer par année", value="")
        with col_f2:
            trimestre_h = st.selectbox("Filtrer par trimestre", ["Tous", "1er TRIMESTRE", "2ème TRIMESTRE", "3ème TRIMESTRE"])
        with col_f3:
            classe_h = st.selectbox("Filtrer par classe", ["Toutes"] + CLASSES)

        f_annee = annee_h if annee_h else None
        f_trimestre = trimestre_h if trimestre_h != "Tous" else None
        f_classe = classe_h if classe_h != "Toutes" else None

        historique_data = charger_historique_db(annee=f_annee, trimestre=f_trimestre, classe=f_classe)

        if historique_data:
            df_hist = pd.DataFrame(historique_data)
            st.dataframe(
                df_hist[["annee_scolaire", "trimestre", "classe", "nom", "prenom", "rang", "total_points", "moyenne", "created_at"]],
                use_container_width=True
            )
        else:
            st.info("Aucun historique trouvé pour ces critères.")
