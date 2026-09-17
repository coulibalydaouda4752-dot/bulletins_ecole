import io
import os
import json
import hashlib
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

# Nom du fichier du logo
LOGO_FILENAME = "logo_epdc_cercle.png"

# ==========================================
# 1. CONFIGURATION DE LA PAGE & SUPABASE
# ==========================================
st.set_page_config(
    page_title="Bulletins - École Privée Diaratigui COULIBALY",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------
# Palette & typographie
# ------------------------------------------
COULEUR_FOND = "#0E2240"
COULEUR_MARINE = "#13294B"
COULEUR_OR = "#C89B3C"
COULEUR_VERT = "#1E6F50"
COULEUR_TEXTE = "#F2EFE6"
COULEUR_TEXTE_DOUX = "#B9C4D6"
COULEUR_BORDURE = "#2E4E7C"
COULEUR_TEXTE_CARTE = "#1C1C1C"
COULEUR_TEXTE_CARTE_DOUX = "#5B5B5B"


def injecter_css():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Lora:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
            color: {COULEUR_TEXTE};
        }}

        .stApp {{
            background-color: {COULEUR_FOND};
        }}

        h1, h2, h3 {{
            font-family: 'Lora', serif !important;
            color: {COULEUR_OR} !important;
            font-weight: 600 !important;
        }}

        section[data-testid="stSidebar"] {{
            background-color: {COULEUR_MARINE};
        }}
        section[data-testid="stSidebar"] * {{
            color: #F2EFE6 !important;
        }}
        section[data-testid="stSidebar"] .stRadio label,
        section[data-testid="stSidebar"] .stSelectbox label,
        section[data-testid="stSidebar"] .stTextInput label {{
            color: #D9CFAE !important;
            font-weight: 500;
        }}
        section[data-testid="stSidebar"] input,
        section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {{
            background-color: #1D3A63 !important;
            color: #F2EFE6 !important;
            border-color: #2E4E7C !important;
        }}

        .marque-ecole {{
            padding: 0.75rem 0 1.25rem 0;
            border-bottom: 1px solid #2E4E7C;
            margin-bottom: 1rem;
        }}
        .marque-ecole .nom {{
            font-family: 'Lora', serif;
            font-size: 1.15rem;
            font-weight: 700;
            color: #F2EFE6;
            line-height: 1.3;
        }}
        .marque-ecole .lieu {{
            font-size: 0.8rem;
            color: {COULEUR_OR};
            letter-spacing: 0.02em;
        }}

        .stButton > button {{
            background-color: {COULEUR_MARINE};
            color: #F2EFE6;
            border: 1px solid {COULEUR_MARINE};
            border-radius: 6px;
            font-weight: 500;
            padding: 0.5rem 1.1rem;
            transition: background-color 0.15s ease;
        }}
        .stButton > button:hover {{
            background-color: #1D3A63;
            border-color: #1D3A63;
            color: #F2EFE6;
        }}
        .stButton > button[kind="primary"] {{
            background-color: {COULEUR_OR};
            border-color: {COULEUR_OR};
            color: {COULEUR_MARINE};
            font-weight: 700;
        }}
        .stButton > button[kind="primary"]:hover {{
            background-color: #B78A2E;
            border-color: #B78A2E;
        }}

        .carte {{
            background-color: #FFFFFF;
            border: 1px solid {COULEUR_BORDURE};
            border-radius: 10px;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1rem;
        }}
        .carte, .carte p, .carte span, .carte label, .carte div {{
            color: {COULEUR_TEXTE_CARTE} !important;
        }}
        .carte h1, .carte h2, .carte h3 {{
            color: {COULEUR_MARINE} !important;
        }}

        .badge {{
            display: inline-block;
            padding: 0.15rem 0.65rem;
            border-radius: 5px;
            font-size: 0.82rem;
            font-weight: 600;
        }}

        .connexion-carte {{
            max-width: 420px;
            margin: 4rem auto 0 auto;
            background-color: #FFFFFF;
            border: 1px solid {COULEUR_BORDURE};
            border-radius: 12px;
            padding: 2.25rem 2rem;
        }}
        .connexion-titre {{
            font-family: 'Lora', serif;
            font-size: 1.5rem;
            font-weight: 700;
            color: {COULEUR_MARINE};
            text-align: center;
            margin-bottom: 0.15rem;
        }}
        .connexion-sous {{
            text-align: center;
            color: {COULEUR_TEXTE_CARTE_DOUX};
            font-size: 0.9rem;
            margin-bottom: 1.5rem;
        }}

        div[data-testid="stDataFrame"] {{
            border: 1px solid {COULEUR_BORDURE};
            border-radius: 8px;
        }}

        hr {{ border-color: {COULEUR_BORDURE} !important; }}

        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        </style>
        """,
        unsafe_allow_html=True
    )


injecter_css()

# Initialisation de Supabase
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception:
    st.error("⚠️ Erreur de connexion à la base de données Supabase. Vérifiez la configuration des secrets (SUPABASE_URL / SUPABASE_KEY).")
    st.stop()

# ==========================================
# 2. AUTHENTIFICATION ADMINISTRATION
# ==========================================
def hacher_mdp(mdp: str) -> str:
    return hashlib.sha256(mdp.encode("utf-8")).hexdigest()


def obtenir_utilisateurs_autorises() -> dict:
    try:
        return dict(st.secrets["admin_users"])
    except Exception:
        return {}


def verifier_identifiants(nom_utilisateur: str, mdp: str) -> bool:
    utilisateurs = obtenir_utilisateurs_autorises()
    if not utilisateurs:
        return False
    hash_attendu = utilisateurs.get(nom_utilisateur)
    if not hash_attendu:
        return False
    return hacher_mdp(mdp) == hash_attendu


def formulaire_connexion():
    st.markdown('<div class="connexion-carte">', unsafe_allow_html=True)
    st.markdown('<div class="connexion-titre">🎓 Espace Administration</div>', unsafe_allow_html=True)
    st.markdown('<div class="connexion-sous">École Privée Diaratigui COULIBALY — Accès réservé au personnel</div>', unsafe_allow_html=True)

    with st.form("form_connexion"):
        nom_utilisateur = st.text_input("Identifiant")
        mdp = st.text_input("Mot de passe", type="password")
        valider = st.form_submit_button("Se connecter", use_container_width=True, type="primary")

    if valider:
        if not obtenir_utilisateurs_autorises():
            st.error("Aucun compte administrateur n'est configuré. Contactez la personne responsable du déploiement.")
        elif verifier_identifiants(nom_utilisateur.strip(), mdp):
            st.session_state["authentifie"] = True
            st.session_state["utilisateur"] = nom_utilisateur.strip()
            st.rerun()
        else:
            st.error("Identifiant ou mot de passe incorrect.")

    st.markdown('</div>', unsafe_allow_html=True)


def exiger_authentification():
    if "authentifie" not in st.session_state:
        st.session_state["authentifie"] = False
    if not st.session_state["authentifie"]:
        formulaire_connexion()
        st.stop()


def bouton_deconnexion():
    st.sidebar.markdown(
        f'<div style="font-size:0.85rem; color:#D9CFAE; margin-bottom:0.4rem;">Connecté : '
        f'<b>{st.session_state.get("utilisateur", "")}</b></div>',
        unsafe_allow_html=True
    )
    if st.sidebar.button("🔒 Se déconnecter", use_container_width=True):
        st.session_state["authentifie"] = False
        st.session_state.pop("utilisateur", None)
        st.rerun()


exiger_authentification()

# ==========================================
# 3. DONNÉES DE CONFIGURATION & CITATIONS
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

TOTAL_COEFFICIENTS = sum(MATIERES_COEFS.values())  # 22
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
# 4. FONCTIONS DE CALCUL ET FORMATAGE
# ==========================================
def fmt_num(val, decimals=2):
    if val is None or val == "":
        return ""
    try:
        formatted = f"{float(val):.{decimals}f}"
        return formatted.replace('.', ',')
    except (ValueError, TypeError):
        return str(val)


def calculer_moyenne_matiere(note_classe, note_compo):
    if note_classe is None or note_compo is None:
        return 0.0
    try:
        moyenne = (float(note_classe) + float(note_compo)) / 3.0
        return round(moyenne, 2)
    except (ValueError, TypeError):
        return 0.0


def calculer_bilan_eleve(notes_dict):
    total_points = 0.0
    for matiere, coef in MATIERES_COEFS.items():
        m_notes = notes_dict.get(matiere, {}) if notes_dict else {}
        nc = m_notes.get("classe")
        npt = m_notes.get("compo")
        moy_mat = calculer_moyenne_matiere(nc, npt)
        total_points += moy_mat * coef

    moyenne_generale = total_points / TOTAL_COEFFICIENTS if TOTAL_COEFFICIENTS > 0 else 0.0
    return round(total_points, 2), round(moyenne_generale, 2)


def attribuer_appreciation(moyenne):
    try:
        moyenne = float(moyenne)
    except (ValueError, TypeError):
        moyenne = 0.0
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


def couleur_appreciation(apprec):
    palette = {
        "Excellent": ("#E6F4EC", COULEUR_VERT),
        "Très-bien": ("#E6F4EC", COULEUR_VERT),
        "Bien": ("#EFF6E9", "#4C7A2E"),
        "Assez-bien": ("#FBF3DF", "#8A6A14"),
        "Passable": ("#FBF0DE", "#A66A1F"),
        "Insuffisant": ("#FCE9E5", "#B23A2E"),
        "Médiocre": ("#FCE9E5", "#B23A2E"),
    }
    return palette.get(apprec, ("#EEEEEE", COULEUR_TEXTE_CARTE_DOUX))


def normaliser_notes(valeur_brute):
    if isinstance(valeur_brute, dict):
        return valeur_brute
    if isinstance(valeur_brute, str) and valeur_brute.strip():
        try:
            return json.loads(valeur_brute)
        except json.JSONDecodeError:
            return {}
    return {}


def normaliser_eleve(eleve: dict) -> dict:
    e = dict(eleve)
    e["notes"] = normaliser_notes(e.get("notes"))
    try:
        e["moyenne"] = float(e.get("moyenne") or 0.0)
    except (ValueError, TypeError):
        e["moyenne"] = 0.0
    try:
        e["total_points"] = float(e.get("total_points") or 0.0)
    except (ValueError, TypeError):
        e["total_points"] = 0.0
    return e


# ==========================================
# 5. ACCÈS BASE DE DONNÉES
# ==========================================
def charger_eleves_db():
    try:
        response = supabase.table("eleves").select("*").execute()
        return [normaliser_eleve(e) for e in (response.data or [])]
    except Exception as e:
        st.error(f"❌ Impossible de charger les élèves depuis la base de données : {e}")
        return []


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
    try:
        if id_eleve:
            supabase.table("eleves").update(data).eq("id", id_eleve).execute()
        else:
            supabase.table("eleves").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"❌ Échec de l'enregistrement : {e}")
        return False


def modifier_infos_eleve_db(id_eleve, nom, prenom, classe):
    try:
        supabase.table("eleves").update({
            "nom": nom, "prenom": prenom, "classe": classe
        }).eq("id", id_eleve).execute()
        return True
    except Exception as e:
        st.error(f"❌ Échec de la modification : {e}")
        return False


def supprimer_eleve_db(id_eleve):
    try:
        supabase.table("eleves").delete().eq("id", id_eleve).execute()
        return True
    except Exception as e:
        st.error(f"❌ Échec de la suppression : {e}")
        return False


def reinitialiser_notes_classe_db(ids_eleves):
    notes_vides = {m: {"classe": None, "compo": None} for m in MATIERES_COEFS.keys()}
    try:
        for id_e in ids_eleves:
            supabase.table("eleves").update({
                "notes": notes_vides, "total_points": 0.0, "moyenne": 0.0
            }).eq("id", id_e).execute()
        return True
    except Exception as e:
        st.error(f"❌ Échec de la réinitialisation : {e}")
        return False


def deja_archive_db(annee_scolaire, trimestre, classe) -> bool:
    try:
        response = (
            supabase.table("historique_bulletins")
            .select("id")
            .eq("annee_scolaire", annee_scolaire)
            .eq("trimestre", trimestre)
            .eq("classe", classe)
            .limit(1)
            .execute()
        )
        return bool(response.data)
    except Exception:
        return False


def archiver_bulletins_db(df_classe, annee_scolaire, trimestre, ecraser=False):
    try:
        classe_cible = df_classe.iloc[0]["classe"] if not df_classe.empty else ""

        if ecraser:
            supabase.table("historique_bulletins").delete() \
                .eq("annee_scolaire", annee_scolaire) \
                .eq("trimestre", trimestre) \
                .eq("classe", classe_cible) \
                .execute()

        enregistrements = []
        for i, (_, eleve) in enumerate(df_classe.iterrows()):
            rang = i + 1
            notes = normaliser_notes(eleve.get("notes"))
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

        supabase.table("historique_bulletins").insert(enregistrements).execute()
        return True
    except Exception as e:
        st.error(f"❌ Échec de l'archivage : {e}")
        return False


def charger_historique_db(annee=None, trimestre=None, classe=None):
    try:
        query = supabase.table("historique_bulletins").select("*")
        if annee:
            query = query.eq("annee_scolaire", annee)
        if trimestre:
            query = query.eq("trimestre", trimestre)
        if classe:
            query = query.eq("classe", classe)
        response = query.order("created_at", desc=True).execute()
        return response.data or []
    except Exception as e:
        st.error(f"❌ Impossible de charger l'historique : {e}")
        return []


# ==========================================
# 6. GÉNÉRATION PDF MULTI-BULLETINS (REPORTLAB)
# ==========================================
def dessiner_cadre_page(canvas_obj, doc):
    canvas_obj.saveState()
    largeur, hauteur = A4
    marge_ext = 14

    canvas_obj.setStrokeColor(colors.HexColor(COULEUR_MARINE))
    canvas_obj.setLineWidth(1.1)
    canvas_obj.rect(marge_ext, marge_ext, largeur - 2 * marge_ext, hauteur - 2 * marge_ext)

    canvas_obj.setStrokeColor(colors.HexColor(COULEUR_OR))
    canvas_obj.setLineWidth(0.6)
    marge_int = marge_ext + 4
    canvas_obj.rect(marge_int, marge_int, largeur - 2 * marge_int, hauteur - 2 * marge_int)

    canvas_obj.setFont("Helvetica-Oblique", 7.5)
    canvas_obj.setFillColor(colors.HexColor("#6B7280"))
    texte_pied = "École Privée Diaratigui COULIBALY — CAP Kalaban-Coro — Document officiel à conserver"
    canvas_obj.drawCentredString(largeur / 2, marge_ext + 9, texte_pied)

    canvas_obj.restoreState()


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
    style_title = ParagraphStyle('Title', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=14, leading=17, alignment=TA_CENTER, textColor=colors.HexColor(COULEUR_MARINE))
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

        notes_actuelles = normaliser_notes(eleve_obj.get("notes"))

        if os.path.exists(LOGO_FILENAME):
            try:
                logo_img = Image(LOGO_FILENAME, width=60, height=60)
            except Exception:
                logo_img = Paragraph(f"<font size=12 color='{COULEUR_MARINE}'><b>EPDC</b></font>", style_cell_center_bold)
        else:
            logo_img = Paragraph(f"<font size=12 color='{COULEUR_MARINE}'><b>EPDC</b></font>", style_cell_center_bold)

        header_right_text = f"ANNÉE SCOLAIRE : {annee_scolaire}<br/><font color='{COULEUR_MARINE}'><b>{trimestre}</b></font>"

        header_data = [
            [
                Paragraph("CAP : Kalaban-Coro<br/><b>Ecole Privée : Diaratigui COULIBALY</b><br/>Classe : " + str(eleve_obj['classe']), style_header_left),
                logo_img,
                Paragraph(header_right_text, style_header_right)
            ]
        ]
        t_header = Table(header_data, colWidths=[210, 110, 210])
        t_header.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
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
            npt = m_data.get("compo")

            txt_nc = fmt_num(nc) if nc is not None else ""
            txt_np = fmt_num(npt) if npt is not None else ""

            if nc is not None and npt is not None:
                moy_m = calculer_moyenne_matiere(nc, npt)
                pts = round(moy_m * coef, 2)
                txt_moy = fmt_num(moy_m)
                txt_pts = fmt_num(pts)
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
            Paragraph(fmt_num(eleve_obj['total_points']), style_cell_center_bold),
            Paragraph("", style_cell)
        ])

        t_notes = Table(table_data, colWidths=[110, 65, 65, 65, 45, 80, 100])
        t_notes.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.8, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
        ]))
        story.append(t_notes)
        story.append(Spacer(1, 14))

        moy_gen = float(eleve_obj['moyenne'])
        apprec_gen = attribuer_appreciation(moy_gen)

        if moy_gen >= 14:
            mention = "FELICITATIONS !"
        elif moy_gen >= 12:
            mention = "ENCOURAGEMENTS !"
        else:
            mention = "PEUT MIEUX FAIRE"

        story.append(Paragraph(f"<b>Moyenne :</b> &nbsp;&nbsp;&nbsp;&nbsp; {fmt_num(moy_gen)} / 20", style_body))
        story.append(Paragraph(f"<b>Rang :</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {rang} {suffix_rang} / {total_eleves} élèves classés", style_body))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>{mention}</b>", style_body_bold))
        story.append(Paragraph(f"<b>Appréciation :</b> {apprec_gen} !", style_body))

        story.append(Spacer(1, 12))
        style_obs_titre = ParagraphStyle('ObsTitre', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9.5, leading=12, textColor=colors.HexColor(COULEUR_MARINE))
        story.append(Paragraph("Observations du Professeur Principal :", style_obs_titre))
        story.append(Spacer(1, 5))
        t_observations = Table([[""]], colWidths=[530], rowHeights=[50])
        t_observations.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#9AA5B1')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(t_observations)
        story.append(Spacer(1, 16))

        t_signatures = Table(
            [[
                Paragraph("_________________________<br/><b>Visa du Parent / Tuteur</b>", style_body),
                Paragraph("_________________________<br/><b>Signature du Directeur</b>", style_header_right)
            ]],
            colWidths=[265, 265]
        )
        t_signatures.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(t_signatures)
        story.append(Spacer(1, 14))

        citation = CITATIONS_EDUCATIVES[i % len(CITATIONS_EDUCATIVES)]
        t_citation = Table([[Paragraph(f"💡 <i>{citation}</i>", style_citation)]], colWidths=[530])
        t_citation.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.HexColor('#CBD5E1')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_citation)

        if i < total_eleves - 1:
            story.append(PageBreak())

    doc.build(story, onFirstPage=dessiner_cadre_page, onLaterPages=dessiner_cadre_page)
    buffer.seek(0)
    return buffer.getvalue()


# ==========================================
# 7. GESTION DU MODE DE NAVIGATION STREAMLIT
# ==========================================
query_params = st.query_params
mode_mobile = query_params.get("mode") == "saisie"

if mode_mobile:
    bouton_deconnexion()
    st.title("📱 Saisie des Notes")
    st.caption("Interface optimisée pour smartphones — accès réservé au personnel administratif")

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

    notes_actuelles = normaliser_notes(eleve_obj.get("notes"))

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
                npt = st.number_input("Compo /40", min_value=0.0, max_value=40.0, value=val_co, step=0.5, key=f"m_cp_{mat}")

            if nc is not None and npt is not None:
                moy_m = calculer_moyenne_matiere(nc, npt)
                st.caption(f"Moyenne : {fmt_num(moy_m)} / 20")
            else:
                st.caption("Moyenne : -- / 20")

            st.markdown("---")
            nouv_notes[mat] = {"classe": nc, "compo": npt}

        btn_valider = st.form_submit_button("Enregistrer toutes les notes 💾", use_container_width=True)

    if btn_valider:
        champs_incomplets = [m for m, v in nouv_notes.items() if v["classe"] is None or v["compo"] is None]
        if champs_incomplets:
            st.error(f"❌ Veuillez remplir toutes les notes avant d'enregistrer. Matières incomplètes : {', '.join(champs_incomplets)}")
        else:
            if sauvegarder_eleve_db(eleve_obj["id"], eleve_obj["nom"], eleve_obj["prenom"], eleve_obj["classe"], nouv_notes):
                st.success("Toutes les notes ont été enregistrées avec succès !")
                st.rerun()

else:
    if os.path.exists(LOGO_FILENAME):
        col_logo, col_nom = st.sidebar.columns([1, 2.2])
        with col_logo:
            st.image(LOGO_FILENAME, use_container_width=True)
        with col_nom:
            st.markdown(
                '<div style="padding-top:0.4rem; font-family:\'Lora\',serif; font-size:1.02rem; '
                'font-weight:700; color:#F2EFE6; line-height:1.25;">École Privée<br/>Diaratigui COULIBALY</div>',
                unsafe_allow_html=True
            )
        st.sidebar.markdown(
            '<div style="font-size:0.8rem; color:#C89B3C; letter-spacing:0.02em; '
            'padding:0.2rem 0 1rem 0; border-bottom:1px solid #2E4E7C; margin-bottom:1rem;">'
            'CAP Kalaban-Coro · Administration</div>',
            unsafe_allow_html=True
        )
    else:
        st.sidebar.markdown(
            '<div class="marque-ecole"><div class="nom">🎓 École Privée<br/>Diaratigui COULIBALY</div>'
            '<div class="lieu">CAP Kalaban-Coro · Administration</div></div>',
            unsafe_allow_html=True
        )
    bouton_deconnexion()

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

    # ------------------------------------------------------------
    # 1. GESTION DES ÉLÈVES
    # ------------------------------------------------------------
    if menu == "1. Gestion des Élèves":
        st.header("👤 Inscription et Gestion des Élèves")

        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown('<div class="carte">', unsafe_allow_html=True)
            with st.form("form_inscript"):
                st.subheader("Nouvel Élève")
                nom = st.text_input("Nom de famille :")
                prenom = st.text_input("Prénom :")
                classe = st.selectbox("Classe :", CLASSES)
                btn_ajouter = st.form_submit_button("Ajouter à la base", type="primary", use_container_width=True)

                if btn_ajouter:
                    if not nom.strip() or not prenom.strip():
                        st.error("Le nom et le prénom sont obligatoires.")
                    else:
                        notes_vides = {m: {"classe": None, "compo": None} for m in MATIERES_COEFS.keys()}
                        if sauvegarder_eleve_db(None, nom.strip().upper(), prenom.strip().title(), classe, notes_vides):
                            st.success("Élève inscrit avec succès !")
                            st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.subheader("Effectif enregistré")
            if eleves_data:
                df = pd.DataFrame(eleves_data)
                st.dataframe(df[["id", "nom", "prenom", "classe", "moyenne", "total_points"]], use_container_width=True)

                st.markdown("---")
                st.subheader("✏️ Modifier / 🗑️ Supprimer un élève")

                eleve_map = {f"{row['nom']} {row['prenom']} ({row['classe']})": row for _, row in df.iterrows()}
                eleve_label = st.selectbox("Sélectionner un élève :", list(eleve_map.keys()), key="sel_modif")
                eleve_cible = eleve_map[eleve_label]

                with st.expander("✏️ Modifier les informations de cet élève"):
                    with st.form("form_modif_eleve"):
                        nv_nom = st.text_input("Nom", value=eleve_cible["nom"])
                        nv_prenom = st.text_input("Prénom", value=eleve_cible["prenom"])
                        nv_classe = st.selectbox("Classe", CLASSES, index=CLASSES.index(eleve_cible["classe"]) if eleve_cible["classe"] in CLASSES else 0)
                        btn_modif = st.form_submit_button("Enregistrer les modifications", type="primary")

                    if btn_modif:
                        if modifier_infos_eleve_db(eleve_cible["id"], nv_nom.strip().upper(), nv_prenom.strip().title(), nv_classe):
                            st.success("Informations mises à jour.")
                            st.rerun()

                cle_confirmation = "confirmer_suppression_id"
                if st.button("❌ Supprimer définitivement cet élève"):
                    st.session_state[cle_confirmation] = eleve_cible["id"]

                if st.session_state.get(cle_confirmation) == eleve_cible["id"]:
                    st.warning(f"Confirmer la suppression définitive de **{eleve_cible['nom']} {eleve_cible['prenom']}** ? Cette action est irréversible.")
                    c_oui, c_non = st.columns(2)
                    with c_oui:
                        if st.button("✅ Oui, supprimer", type="primary", use_container_width=True):
                            if supprimer_eleve_db(eleve_cible["id"]):
                                st.session_state.pop(cle_confirmation, None)
                                st.success("L'élève a été supprimé de la base de données.")
                                st.rerun()
                    with c_non:
                        if st.button("Annuler", use_container_width=True):
                            st.session_state.pop(cle_confirmation, None)
                            st.rerun()
            else:
                st.info("Aucun élève enregistré.")

    # ------------------------------------------------------------
    # 2. SAISIE DES NOTES (PC)
    # ------------------------------------------------------------
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

        notes_actuelles = normaliser_notes(eleve_obj.get("notes"))

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
                npt = c3.number_input(f"cp_{mat}", min_value=0.0, max_value=40.0, value=val_co, step=0.5, label_visibility="collapsed")

                if nc is not None and npt is not None:
                    moy_m = calculer_moyenne_matiere(nc, npt)
                    c4.write(f"**{fmt_num(moy_m)}**")
                else:
                    c4.write("--")

                nouv_notes[mat] = {"classe": nc, "compo": npt}

            btn_save = st.form_submit_button("Enregistrer toutes les notes 💾", type="primary")

        if btn_save:
            champs_incomplets = [m for m, v in nouv_notes.items() if v["classe"] is None or v["compo"] is None]
            if champs_incomplets:
                st.error(f"❌ Veuillez remplir toutes les notes avant d'enregistrer. Matières incomplètes : {', '.join(champs_incomplets)}")
            else:
                if sauvegarder_eleve_db(eleve_obj["id"], eleve_obj["nom"], eleve_obj["prenom"], eleve_obj["classe"], nouv_notes):
                    st.success("Toutes les notes ont été mises à jour !")
                    st.rerun()

    # ------------------------------------------------------------
    # 3. CLASSEMENT & RÉSULTATS
    # ------------------------------------------------------------
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

            moy_classe = df_classe["moyenne"].mean()
            c1, c2, c3 = st.columns(3)
            c1.metric("Effectif", len(df_classe))
            c2.metric("Moyenne de classe", fmt_num(moy_classe))
            c3.metric("Meilleure moyenne", fmt_num(df_classe["moyenne"].max()))

            st.dataframe(
                df_classe[["Rang", "nom", "prenom", "total_points", "moyenne", "Appréciation"]],
                use_container_width=True
            )

    # ------------------------------------------------------------
    # 4. IMPRESSION DES BULLETINS
    # ------------------------------------------------------------
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

        col_dl, col_arch = st.columns(2)
        with col_dl:
            st.download_button(
                label=f"📄 Télécharger TOUS les bulletins ({classe_sel}) — {trimestre_input}",
                data=pdf_data,
                file_name=f"Bulletins_{classe_sel.replace(' ', '_')}_{trimestre_input.replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        deja_present = deja_archive_db(annee_scolaire_input, trimestre_input, classe_sel)
        with col_arch:
            if deja_present:
                st.warning(f"⚠️ Un archivage existe déjà pour {classe_sel} — {trimestre_input} ({annee_scolaire_input}).")
                if st.button("🔁 Écraser l'archivage existant", use_container_width=True):
                    if archiver_bulletins_db(df_classe, annee_scolaire_input, trimestre_input, ecraser=True):
                        st.success("✅ Archivage mis à jour (l'ancien a été remplacé).")
            else:
                if st.button("🗄️ Archiver dans l'historique", type="primary", use_container_width=True):
                    if archiver_bulletins_db(df_classe, annee_scolaire_input, trimestre_input, ecraser=False):
                        st.success("✅ Bulletins archivés avec succès !")

        with st.expander("🔄 Clôturer ce trimestre pour cette classe (réinitialise les notes)"):
            st.caption("À utiliser une fois les bulletins archivés, pour repartir sur des notes vierges au trimestre suivant. Cette action ne supprime pas l'historique déjà archivé.")
            if st.button("Réinitialiser les notes de cette classe", key="reset_trim"):
                st.session_state["confirmer_reset"] = classe_sel

            if st.session_state.get("confirmer_reset") == classe_sel:
                st.error(f"Confirmer la réinitialisation des notes de **{classe_sel}** ? Cette action est irréversible.")
                c_oui, c_non = st.columns(2)
                with c_oui:
                    if st.button("✅ Oui, réinitialiser", type="primary", key="reset_oui"):
                        if reinitialiser_notes_classe_db(df_classe["id"].tolist()):
                            st.session_state.pop("confirmer_reset", None)
                            st.success("Notes réinitialisées pour la classe.")
                            st.rerun()
                with c_non:
                    if st.button("Annuler", key="reset_non"):
                        st.session_state.pop("confirmer_reset", None)
                        st.rerun()

        st.markdown("---")
        st.subheader("Aperçu individuel à l'écran")

        eleve_options = {f"{row['nom']} {row['prenom']}": (i, row) for i, row in df_classe.iterrows()}
        nom_sel = st.selectbox("Choisir un élève pour visualiser :", list(eleve_options.keys()))
        idx_eleve, eleve_obj = eleve_options[nom_sel]
        rang_eleve = idx_eleve + 1

        notes_actuelles = normaliser_notes(eleve_obj.get("notes"))

        rows_html = ""
        for mat, coef in MATIERES_COEFS.items():
            m_data = notes_actuelles.get(mat, {})
            nc = m_data.get("classe")
            npt = m_data.get("compo")

            txt_nc = fmt_num(nc) if nc is not None else ""
            txt_np = fmt_num(npt) if npt is not None else ""

            if nc is not None and npt is not None:
                moy_m = calculer_moyenne_matiere(nc, npt)
                pts = round(moy_m * coef, 2)
                txt_moy = fmt_num(moy_m)
                txt_pts = fmt_num(pts)
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

        apprec_generale = attribuer_appreciation(eleve_obj['moyenne'])
        suffix_rang = "ère" if rang_eleve == 1 else "ème"
        citation_apercu = CITATIONS_EDUCATIVES[idx_eleve % len(CITATIONS_EDUCATIVES)]
        moy_gen_val = float(eleve_obj['moyenne'])
        mention = "FELICITATIONS !" if moy_gen_val >= 14 else "ENCOURAGEMENTS !" if moy_gen_val >= 12 else "PEUT MIEUX FAIRE"

        bulletin_html = textwrap.dedent(f"""
        <div style="background-color: #ffffff; color: #000000; padding: 25px; border: 1px solid #ccc; border-radius: 6px; font-family: 'Times New Roman', Times, serif; max-width: 800px; margin: auto;">
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 13px; font-weight: bold; margin-bottom: 15px;">
                <div style="width: 38%; text-align: left; line-height: 1.4;">
                    CAP : Kalaban-Coro<br>
                    Ecole Privée : Diaratigui COULIBALY<br>
                    Classe : {eleve_obj['classe']}
                </div>
                <div style="width: 24%; text-align: center;">
                    <img src="logo_epdc_cercle.png" style="max-width: 70px; height: auto;" alt="Logo EPDC" onerror="this.style.display='none'; document.getElementById('alt-logo').style.display='block';">
                    <div id="alt-logo" style="display:none; font-size: 22px; color: {COULEUR_MARINE}; font-weight: bold;">EPDC</div>
                </div>
                <div style="width: 38%; text-align: right; line-height: 1.4;">
                    ANNÉE SCOLAIRE : {annee_scolaire_input}<br>
                    <span style="color: {COULEUR_MARINE};">{trimestre_input}</span>
                </div>
            </div>

            <div style="text-align: center; font-size: 18px; font-weight: bold; text-decoration: underline; margin: 20px 0; color: {COULEUR_MARINE};">
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
                        <td style="text-align: center; padding: 6px; border-left: 1px solid #ccc;">{fmt_num(eleve_obj['total_points'])}</td>
                        <td style="border-left: 1px solid #ccc;"></td>
                    </tr>
                </tbody>
            </table>

            <div style="margin-top: 20px; font-size: 14px; line-height: 1.6;">
                <div><b>Moyenne :</b> &nbsp;&nbsp;&nbsp;&nbsp; {fmt_num(eleve_obj['moyenne'])} / 20</div>
                <div><b>Rang :</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {rang_eleve} {suffix_rang} / {len(df_classe)} élèves classés</div>
                <div style="margin-top: 8px; font-weight: bold;">{mention}</div>
                <div style="margin-top: 4px;"><b>Appréciation :</b> {apprec_generale} !</div>
            </div>

            <div style="text-align: right; margin-top: -30px; margin-bottom: 70px; font-weight: bold; font-size: 13px;">
                Signature du directeur
            </div>

            <div style="margin-top: 20px; border-top: 1px solid #cbd5e1; padding-top: 8px; text-align: center; font-style: italic; font-size: 12px; color: #4b5563;">
                💡 {citation_apercu}
            </div>
        </div>
        """)

        components.html(bulletin_html, height=850, scrolling=True)

    # ------------------------------------------------------------
    # 5. HISTORIQUE DES BULLETINS
    # ------------------------------------------------------------
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
