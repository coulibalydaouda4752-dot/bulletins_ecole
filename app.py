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
    """ Formate un nombre en remplaçant le point décimal par une virgule. """
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


def obtenir_suffixe_rang(rang, sexe):
    """ Retourne 'er' ou 'ère' si rang==1 selon le sexe, et 'ème' pour les suivants. """
    if rang == 1:
        return "ère" if str(sexe).upper() == "F" else "er"
    return "ème"


def normaliser_notes(valeur_brute):
    """ Garantit que 'notes' est toujours un dict Python exploitable. """
    if isinstance(valeur_brute, dict):
        return valeur_brute
    if isinstance(valeur_brute, str) and valeur_brute.strip():
        try:
            return json.loads(valeur_brute)
        except json.JSONDecodeError:
            return {}
    return {}


def normaliser_eleve(eleve: dict) -> dict:
    """ Force les types numériques et valeurs par défaut. """
    e = dict(eleve)
    e["notes"] = normaliser_notes(e.get("notes"))
    e["sexe"] = str(e.get("sexe") or "M").upper()
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
        st.warning("⚠️ Connexion momentanément indisponible avec la base de données. Veuillez rafraîchir la page.")
        st.error(f"Détails : {e}")
        return []


def sauvegarder_eleve_db(id_eleve, nom, prenom, classe, sexe, notes_dict):
    total_pts, moy_gen = calculer_bilan_eleve(notes_dict)
    data = {
        "nom": nom,
        "prenom": prenom,
        "classe": classe,
        "sexe": sexe,
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


def modifier_infos_eleve_db(id_eleve, nom, prenom, classe, sexe):
    try:
        supabase.table("eleves").update({
            "nom": nom, "prenom": prenom, "classe": classe, "sexe": sexe
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
                "sexe": eleve.get("sexe", "M"),
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

    # Bordures extérieure et intérieure
    canvas_obj.setStrokeColor(colors.HexColor(COULEUR_MARINE))
    canvas_obj.setLineWidth(1.1)
    canvas_obj.rect(marge_ext, marge_ext, largeur - 2 * marge_ext, hauteur - 2 * marge_ext)

    canvas_obj.setStrokeColor(colors.HexColor(COULEUR_OR))
    canvas_obj.setLineWidth(0.6)
    marge_int = marge_ext + 4
    canvas_obj.rect(marge_int, marge_int, largeur - 2 * marge_int, hauteur - 2 * marge_int)

    # --- Citation dynamique en pied de page ---
    page_num = canvas_obj.getPageNumber()
    citation = CITATIONS_EDUCATIVES[(page_num - 1) % len(CITATIONS_EDUCATIVES)]
    
    canvas_obj.setFont("Helvetica-Oblique", 7.5)
    canvas_obj.setFillColor(colors.HexColor("#334155"))
    canvas_obj.drawCentredString(largeur / 2, marge_ext + 18, f"💡 {citation}")

    # --- Ligne institutionnelle ---
    canvas_obj.setFont("Helvetica", 7)
    canvas_obj.setFillColor(colors.HexColor("#6B7280"))
    texte_pied = "École Privée Diaratigui COULIBALY — CAP Kalaban-Coro — Document officiel à conserver"
    canvas_obj.drawCentredString(largeur / 2, marge_ext + 8, texte_pied)

    canvas_obj.restoreState()


def generer_pdf_bulletins_classe(df_classe, annee_scolaire, trimestre):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=25,
        bottomMargin=35
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

    # Style pour Tableau d'honneur aligné à gauche
    style_th = ParagraphStyle('TableauHonneur', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=14, alignment=TA_LEFT, textColor=colors.HexColor(COULEUR_VERT))

    total_eleves = len(df_classe)

    for i, (_, eleve_obj) in enumerate(df_classe.iterrows()):
        rang = i + 1
        sexe_eleve = eleve_obj.get('sexe', 'M')
        suffix_rang = obtenir_suffixe_rang(rang, sexe_eleve)

        notes_actuelles = normaliser_notes(eleve_obj.get("notes"))

        LOGO_PATH = "logo.png"
        if os.path.exists(LOGO_PATH):
            try:
                logo_img = Image(LOGO_PATH, width=50, height=50)
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

        # --- Mention Tableau d'honneur alignée à gauche sous l'appréciation ---
        if moy_gen >= 15.0:
            story.append(Spacer(1, 4))
            story.append(Paragraph("<b>🎖️ Tableau d'honneur</b>", style_th))

        story.append(Spacer(1, 16))

        # --- Signature du Directeur uniquement à droite ---
        t_signatures = Table(
            [[
                Paragraph("", style_body),
                Paragraph("_________________________<br/><b>Signature du Directeur</b>", style_header_right)
            ]],
            colWidths=[265, 265]
        )
        t_signatures.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(t_signatures)

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
            if sauvegarder_eleve_db(eleve_obj["id"], eleve_obj["nom"], eleve_obj["prenom"], eleve_obj["classe"], eleve_obj.get("sexe", "M"), nouv_notes):
                st.success("Toutes les notes ont été enregistrées avec succès !")
                st.rerun()

else:
    if os.path.exists("logo.png"):
        col_logo, col_nom = st.sidebar.columns([1, 2.2])
        with col_logo:
            st.image("logo.png", use_container_width=True)
        with col_nom:
            st.markdown(
                '<div style="padding-top:0.4rem; font-family:\'Lora\',serif; font-size:1.02rem; '
                'font-weight:700; color:#F2EFE6; line-height:1.25;">École Privée<br/>Diaratigui COULIBALY</div>',
                unsafe_allow_html=True
            )
    else:
        st.sidebar.markdown(
            '<div class="marque-ecole"><div class="nom">École Privée<br/>Diaratigui COULIBALY</div>'
            '<div class="lieu">CAP Kalaban-Coro</div></div>',
            unsafe_allow_html=True
        )

    bouton_deconnexion()

    st.sidebar.title("Navigation")
    menu = st.sidebar.radio(
        "Menu principal",
        ["Gestion des Élèves", "Saisie des Notes", "Génération Bulletins", "Historique", "Statistiques"]
    )

    eleves_data = charger_eleves_db()
    df_eleves = pd.DataFrame(eleves_data) if eleves_data else pd.DataFrame()

    # ------------------------------------------
    # ONGLET 1 : GESTION DES ÉLÈVES
    # ------------------------------------------
    if menu == "Gestion des Élèves":
        st.title("👨‍🎓 Gestion des Élèves")

        tab_ajout, tab_liste, tab_modif = st.tabs(["Ajouter un élève", "Liste des élèves", "Modifier / Supprimer"])

        with tab_ajout:
            st.subheader("Inscrire un nouvel élève")
            with st.form("form_ajout_eleve"):
                col1, col2 = st.columns(2)
                with col1:
                    nom = st.text_input("Nom de l'élève").strip().upper()
                    prenom = st.text_input("Prénom de l'élève").strip().title()
                with col2:
                    classe = st.selectbox("Classe", CLASSES)
                    sexe = st.selectbox("Sexe", ["M", "F"])

                btn_ajouter = st.form_submit_button("Enregistrer l'élève", type="primary")

                if btn_ajouter:
                    if not nom or not prenom:
                        st.error("Le nom et le prénom sont obligatoires.")
                    else:
                        notes_vides = {m: {"classe": None, "compo": None} for m in MATIERES_COEFS.keys()}
                        if sauvegarder_eleve_db(None, nom, prenom, classe, sexe, notes_vides):
                            st.success(f"Élève {prenom} {nom} ajouté avec succès !")
                            st.rerun()

        with tab_liste:
            st.subheader("Effectif global")
            if df_eleves.empty:
                st.info("Aucun élève enregistré.")
            else:
                classe_filtre = st.selectbox("Filtrer par classe :", ["Toutes"] + CLASSES)
                df_aff = df_eleves if classe_filtre == "Toutes" else df_eleves[df_eleves["classe"] == classe_filtre]
                
                st.write(f"Total : **{len(df_aff)}** élève(s)")
                st.dataframe(
                    df_aff[["nom", "prenom", "classe", "sexe"]],
                    use_container_width=True,
                    hide_index=True
                )

        with tab_modif:
            st.subheader("Modifier ou supprimer un élève")
            if df_eleves.empty:
                st.info("Aucun élève à modifier.")
            else:
                eleve_dict = {f"{r['nom']} {r['prenom']} ({r['classe']})": r for _, r in df_eleves.iterrows()}
                choix = st.selectbox("Sélectionner l'élève :", list(eleve_dict.keys()))
                e_sel = eleve_dict[choix]

                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    n_nom = st.text_input("Nom", value=e_sel["nom"]).strip().upper()
                    n_prenom = st.text_input("Prénom", value=e_sel["prenom"]).strip().title()
                with col_m2:
                    n_classe = st.selectbox("Classe", CLASSES, index=CLASSES.index(e_sel["classe"]) if e_sel["classe"] in CLASSES else 0)
                    n_sexe = st.selectbox("Sexe", ["M", "F"], index=0 if e_sel.get("sexe") == "M" else 1)

                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("Mettre à jour ✏️", use_container_width=True):
                        if modifier_infos_eleve_db(e_sel["id"], n_nom, n_prenom, n_classe, n_sexe):
                            st.success("Informations mises à jour !")
                            st.rerun()
                with col_b2:
                    if st.button("Supprimer l'élève ❌", use_container_width=True):
                        if supprimer_eleve_db(e_sel["id"]):
                            st.success("Élève supprimé !")
                            st.rerun()

    # ------------------------------------------
    # ONGLET 2 : SAISIE DES NOTES
    # ------------------------------------------
    elif menu == "Saisie des Notes":
        st.title("📝 Saisie des Notes")

        if df_eleves.empty:
            st.warning("Veuillez d'abord ajouter des élèves dans la section 'Gestion des Élèves'.")
        else:
            classe_saisie = st.selectbox("Choisir la classe :", CLASSES)
            df_c = df_eleves[df_eleves["classe"] == classe_saisie]

            if df_c.empty:
                st.info(f"Aucun élève en {classe_saisie}.")
            else:
                eleves_options = {f"{r['nom']} {r['prenom']}": r for _, r in df_c.iterrows()}
                eleve_nom = st.selectbox("Choisir l'élève :", list(eleves_options.keys()))
                eleve_courant = eleves_options[eleve_nom]

                st.markdown(f"### Élève : **{eleve_courant['nom']} {eleve_courant['prenom']}**")

                notes_act = normaliser_notes(eleve_courant.get("notes"))

                with st.form("form_saisie_notes_desktop"):
                    nouvelles_notes = {}
                    st.markdown("---")

                    for mat, coef in MATIERES_COEFS.items():
                        m_data = notes_act.get(mat, {})
                        v_cl = float(m_data.get("classe")) if m_data.get("classe") is not None else None
                        v_co = float(m_data.get("compo")) if m_data.get("compo") is not None else None

                        col_mat, col_cl, col_co = st.columns([2, 1, 1])
                        with col_mat:
                            st.markdown(f"**{mat}** *(Coef {coef})*")
                        with col_cl:
                            nc = st.number_input(f"Classe /20 ({mat})", min_value=0.0, max_value=20.0, value=v_cl, step=0.5, label_visibility="collapsed")
                        with col_co:
                            npt = st.number_input(f"Compo /40 ({mat})", min_value=0.0, max_value=40.0, value=v_co, step=0.5, label_visibility="collapsed")

                        nouvelles_notes[mat] = {"classe": nc, "compo": npt}

                    btn_sauvegarder = st.form_submit_button("Enregistrer les notes 💾", type="primary")

                    if btn_sauvegarder:
                        if sauvegarder_eleve_db(eleve_courant["id"], eleve_courant["nom"], eleve_courant["prenom"], eleve_courant["classe"], eleve_courant.get("sexe", "M"), nouvelles_notes):
                            st.success("Notes enregistrées avec succès !")
                            st.rerun()

    # ------------------------------------------
    # ONGLET 3 : GÉNÉRATION BULLETINS
    # ------------------------------------------
    elif menu == "Génération Bulletins":
        st.title("📄 Génération des Bulletins")

        if df_eleves.empty:
            st.warning("Aucun élève disponible.")
        else:
            col_a1, col_a2, col_a3 = st.columns(3)
            with col_a1:
                annee_scolaire = st.text_input("Année scolaire", value="2025-2026")
            with col_a2:
                trimestre = st.selectbox("Trimestre", ["1er Trimestre", "2ème Trimestre", "3ème Trimestre"])
            with col_a3:
                classe_bulletin = st.selectbox("Classe", CLASSES)

            df_cb = df_eleves[df_eleves["classe"] == classe_bulletin].copy()

            if df_cb.empty:
                st.info(f"Aucun élève enregistré pour la classe {classe_bulletin}.")
            else:
                # Recalcul et tri par moyenne décroissante
                df_cb["moyenne"] = df_cb["notes"].apply(lambda n: calculer_bilan_eleve(n)[1])
                df_cb["total_points"] = df_cb["notes"].apply(lambda n: calculer_bilan_eleve(n)[0])
                df_cb = df_cb.sort_values(by="moyenne", ascending=False).reset_index(drop=True)

                st.subheader(f"Classement provisoire — {classe_bulletin}")
                st.dataframe(
                    df_cb[["nom", "prenom", "sexe", "total_points", "moyenne"]],
                    use_container_width=True
                )

                st.markdown("---")
                col_b1, col_b2 = st.columns(2)

                with col_b1:
                    pdf_bytes = generer_pdf_bulletins_classe(df_cb, annee_scolaire, trimestre)
                    st.download_button(
                        label="📥 Télécharger le PDF de la classe",
                        data=pdf_bytes,
                        file_name=f"Bulletins_{classe_bulletin}_{trimestre.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )

                with col_b2:
                    if st.button("📦 Archiver ces bulletins", use_container_width=True):
                        deja = deja_archive_db(annee_scolaire, trimestre, classe_bulletin)
                        if deja:
                            st.warning("Des bulletins pour cette période existent déjà dans l'historique.")
                            if st.button("Écraser et ré-archiver", key="btn_ecraser"):
                                if archiver_bulletins_db(df_cb, annee_scolaire, trimestre, ecraser=True):
                                    st.success("Archivage mis à jour avec succès !")
                        else:
                            if archiver_bulletins_db(df_cb, annee_scolaire, trimestre, ecraser=False):
                                st.success("Bulletins archivés avec succès !")

    # ------------------------------------------
    # ONGLET 4 : HISTORIQUE
    # ------------------------------------------
    elif menu == "Historique":
        st.title("📚 Historique des Bulletins")

        col_h1, col_h2, col_h3 = st.columns(3)
        with col_h1:
            h_annee = st.text_input("Année scolaire (ex: 2025-2026)", value="")
        with col_h2:
            h_trim = st.selectbox("Trimestre", ["Tous", "1er Trimestre", "2ème Trimestre", "3ème Trimestre"])
        with col_h3:
            h_classe = st.selectbox("Classe", ["Toutes"] + CLASSES)

        f_trim = None if h_trim == "Tous" else h_trim
        f_classe = None if h_classe == "Toutes" else h_classe
        f_annee = h_annee.strip() if h_annee.strip() else None

        historique = charger_historique_db(annee=f_annee, trimestre=f_trim, classe=f_classe)

        if not historique:
            st.info("Aucun enregistrement d'historique trouvé pour ces critères.")
        else:
            df_hist = pd.DataFrame(historique)
            st.write(f"Total des registres trouvés : **{len(df_hist)}**")
            st.dataframe(
                df_hist[["annee_scolaire", "trimestre", "classe", "nom", "prenom", "rang", "moyenne", "total_points"]],
                use_container_width=True,
                hide_index=True
            )

    # ------------------------------------------
    # ONGLET 5 : STATISTIQUES
    # ------------------------------------------
    elif menu == "Statistiques":
        st.title("📊 Statistiques et Indicateurs Clés")

        if df_eleves.empty:
            st.warning("Aucune donnée disponible pour établir des statistiques.")
        else:
            st.subheader("1. Vue Globale de l'Établissement")
            
            # Recalcul des moyennes pour tous les élèves
            df_stats = df_eleves.copy()
            df_stats["moyenne"] = df_stats["notes"].apply(lambda n: calculer_bilan_eleve(n)[1])
            
            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            
            with col_s1:
                st.metric("Total Élèves", len(df_stats))
            with col_s2:
                nb_m = len(df_stats[df_stats["sexe"] == "M"])
                st.metric("Garçons (M)", nb_m)
            with col_s3:
                nb_f = len(df_stats[df_stats["sexe"] == "F"])
                st.metric("Filles (F)", nb_f)
            with col_s4:
                moy_globale = df_stats["moyenne"].mean() if not df_stats.empty else 0.0
                st.metric("Moyenne Générale", f"{moy_globale:.2f} / 20")

            st.markdown("---")
            st.subheader("2. Répartition par Genre")
            
            # Graphique de répartition des sexes
            genre_counts = df_stats["sexe"].value_counts().reset_index()
            genre_counts.columns = ["Sexe", "Nombre"]
            genre_counts["Sexe"] = genre_counts["Sexe"].map({"M": "Garçons", "F": "Filles"})
            
            st.bar_chart(data=genre_counts.set_index("Sexe"), use_container_width=True)

            st.markdown("---")
            st.subheader("3. Performances Moyennes par Classe")
            
            # Moyenne générale par classe
            moyennes_classe = df_stats.groupby("classe")["moyenne"].mean().reset_index()
            moyennes_classe.columns = ["Classe", "Moyenne Générale"]
            
            st.dataframe(
                moyennes_classe.style.format({"Moyenne Générale": "{:.2f}"}),
                use_container_width=True,
                hide_index=True
            )
            
            st.bar_chart(data=moyennes_classe.set_index("Classe"), use_container_width=True)

            st.markdown("---")
            st.subheader("4. Taux de Réussite par Classe (Moyenne >= 10/20)")
            
            taux_reussite = []
            for c in CLASSES:
                df_c = df_stats[df_stats["classe"] == c]
                tot = len(df_c)
                if tot > 0:
                    admis = len(df_c[df_c["moyenne"] >= 10.0])
                    pct = (admis / tot) * 100
                else:
                    admis = 0
                    pct = 0.0
                taux_reussite.append({"Classe": c, "Total Élèves": tot, "Admis (>=10)": admis, "Taux de Réussite (%)": round(pct, 2)})

            df_taux = pd.DataFrame(taux_reussite)
            st.dataframe(
                df_taux.style.format({"Taux de Réussite (%)": "{:.2f}%"}),
                use_container_width=True,
                hide_index=True
            )
