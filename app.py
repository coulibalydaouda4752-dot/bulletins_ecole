import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
import reportlab
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ------------------------------------------------------------
# CONFIGURATION STREAMLIT
# ------------------------------------------------------------
st.set_page_config(
    page_title="Gestionnaire de Bulletin Scolaire",
    page_icon="🎓",
    layout="wide"
)

# ------------------------------------------------------------
# CONSTANTES & DONNÉES DE BASE
# ------------------------------------------------------------
CLASSES = ["6ème", "5ème", "4ème", "3ème", "2nde", "1ère", "Tle"]

CITATIONS_EDUCATIVES = [
    "« L'éducation est l'arme la plus puissante qu'on puisse utiliser pour changer le monde. » – Nelson Mandela",
    "« Le savoir est la seule matière qui s'accroît quand on la partage. » – Socrate",
    "« Apprendre sans réfléchir est vain ; réfléchir sans apprendre est dangereux. » – Confucius",
    "« L'apprentissage est un trésor qui suivra son propriétaire partout. » – Proverbe chinois",
    "« La connaissance s'acquiert par l'expérience. » – Albert Einstein",
    "« Les racines de l'éducation sont amères, mais ses fruits sont doux. » – Aristote",
    "« Enseigner, c'est apprendre deux fois. » – Joseph Joubert",
    "« L'esprit n'est pas un vase qu'on remplit, mais un feu qu'on allume. » – Plutarque",
    "« L'éducation est la clé pour ouvrir la porte d'or de la liberté. » – George Washington Carver",
    "« Investir dans le savoir paie toujours les meilleurs intérêts. » – Benjamin Franklin",
    "« Ce que l'on conçoit bien s'énonce clairement, et les mots pour le dire arrivent aisément. » – Nicolas Boileau",
    "« Le but de l'éducation est de remplacer un esprit vide par un esprit ouvert. » – Malcolm Forbes",
    "« La culture est ce qui reste quand on a tout oublié. » – Émile Chartier (Alain)",
    "« On apprend peu par la victoire, mais beaucoup par la défaite. » – Proverbe arabe",
    "« L'école doit développer la curiosité d'esprit et l'envie d'apprendre. » – Albert Jacquard",
    "« Tu me dis, j'oublie. Tu m'enseignes, je me rappelle. Tu m'impliques, j'apprends. » – Benjamin Franklin",
    "« L'éducation ne consiste pas à gaver des crânes, mais à éveiller des âmes. » – Michel de Montaigne",
    "« Il n'y a pas de problème que la lecture et l'effort ne puissent résoudre. » – Victor Hugo",
    "« Le travail éloigne de nous trois grands maux : l'ennui, le vice et le besoin. » – Voltaire",
    "« La rigueur et le travail sont les compagnons indispensables du succès. » – Louis Pasteur",
    "« N'aie pas peur d'avancer lentement, aie seulement peur de t'arrêter. » – Proverbe chinois",
    "« C'est en forgeant qu'on devient forgeron. » – Proverbe français",
    "« L'éducation est le passeport pour l'avenir, car demain appartient à ceux qui s'y préparent aujourd'hui. » – Malcolm X",
    "« Le succès est la somme de petits efforts, répétés jour après jour. » – Robert Collier",
    "« Il faut cultiver notre jardin. » – Voltaire",
    "« L'érudition est la mémoire des faits, la sagesse est leur compréhension. » – Denis Diderot",
    "« Rien de grand ne s'est accompli dans le monde sans passion. » – Friedrich Hegel",
    "« La patience est amère, mais son fruit est doux. » – Jean-Jacques Rousseau",
    "« La Discipline est le pont entre les objectifs et les réalisations. » – Jim Rohn",
    "« L'éducation est le plus grand bien que l'homme puisse laisser à la jeunesse. » – Pythagoras"
]

# ------------------------------------------------------------
# INITIALIZATION DE LA SESSION STATE
# ------------------------------------------------------------
if "eleves" not in st.session_state:
    st.session_state.eleves = [
        {
            "id": 1,
            "nom": "KOUASSI",
            "prenom": "Jean",
            "classe": "3ème",
            "mathematiques": 14.5,
            "francais": 12.0,
            "anglais": 15.0,
            "histoire_geo": 11.5,
            "physique_chimie": 13.0,
            "moyenne": 13.2
        },
        {
            "id": 2,
            "nom": "DIABATE",
            "prenom": "Aminata",
            "classe": "3ème",
            "mathematiques": 18.0,
            "francais": 16.5,
            "anglais": 17.0,
            "histoire_geo": 14.0,
            "physique_chimie": 19.0,
            "moyenne": 16.9
        }
    ]

# ------------------------------------------------------------
# FONCTIONS UTILITAIRES
# ------------------------------------------------------------
def fmt_num(valeur, decimales=2):
    """Formate un nombre avec le nombre de décimales spécifié."""
    if valeur is None:
        return "-"
    return f"{valeur:.{decimales}f}"

def attribuer_appreciation(moyenne):
    """Retourne une appréciation basée sur la moyenne générale."""
    if moyenne >= 16:
        return "Très Bien"
    elif moyenne >= 14:
        return "Bien"
    elif moyenne >= 12:
        return "Assez Bien"
    elif moyenne >= 10:
        return "Passable"
    else:
        return "Insuffisant"

def calculer_moyenne(row):
    """Calcule la moyenne des notes présentes."""
    matieres = ["mathematiques", "francais", "anglais", "histoire_geo", "physique_chimie"]
    notes = [row[m] for m in matieres if row[m] is not None]
    return sum(notes) / len(notes) if notes else 0.0

def creer_graphique_donut(labels, valeurs, couleurs, titre, sous_titre_centre=""):
    """Génère un graphique circulaire de type Donut via Plotly."""
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=valeurs,
        hole=0.6,
        marker=dict(colors=couleurs),
        textinfo='percent+label'
    )])
    fig.update_layout(
        title_text=titre,
        annotations=[dict(text=sous_titre_centre, x=0.5, y=0.5, font_size=16, showarrow=False)]
    )
    return fig

def generer_pdf_bulletin(eleve, index_page=0):
    """Génère un PDF individuel pour le bulletin d'un élève."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    style_titre = ParagraphStyle('Titre', parent=styles['Heading1'], fontSize=18, alignment=1, textColor=colors.HexColor("#1E6F50"))
    style_normal = styles['Normal']
    style_citation = ParagraphStyle('Citation', parent=styles['Italic'], fontSize=9, alignment=1, textColor=colors.gray)

    elements = []

    # En-tête
    elements.append(Paragraph("BULLETIN DE NOTES", style_titre))
    elements.append(Spacer(1, 15))

    # Informations Élève
    info_text = f"<b>Nom & Prénom :</b> {eleve['nom']} {eleve['prenom']}<br/><b>Classe :</b> {eleve['classe']}"
    elements.append(Paragraph(info_text, style_normal))
    elements.append(Spacer(1, 15))

    # Tableau des notes
    data = [
        ["Matière", "Note / 20"],
        ["Mathématiques", fmt_num(eleve['mathematiques'])],
        ["Français", fmt_num(eleve['francais'])],
        ["Anglais", fmt_num(eleve['anglais'])],
        ["Histoire-Géographie", fmt_num(eleve['histoire_geo'])],
        ["Physique-Chimie", fmt_num(eleve['physique_chimie'])],
        ["Moyenne Générale", fmt_num(eleve['moyenne'])],
        ["Appréciation", attribuer_appreciation(eleve['moyenne'])]
    ]

    t = Table(data, colWidths=[250, 200])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor("#1E6F50")),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 6), (1, 6), colors.HexColor("#E8F5E9")),
        ('FONTNAME', (0, 6), (-1, 6), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(t)
    elements.append(Spacer(1, 30))

    # Rotation dynamique des 30 citations selon l'index de la page
    citation_index = index_page % len(CITATIONS_EDUCATIVES)
    citation = CITATIONS_EDUCATIVES[citation_index]
    elements.append(Paragraph(citation, style_citation))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# ------------------------------------------------------------
# BARRE DE NAVIGATION (SIDEBAR)
# ------------------------------------------------------------
st.sidebar.title("📌 Navigation")
menu = st.sidebar.radio("Aller vers :", [
    "1. Aperçu Général 📋",
    "2. Saisie / Modification ✍️",
    "3. Bulletins Individuels 📜",
    "4. Export PDF / Data 📥",
    "5. Paramètres ⚙️",
    "6. Statistiques & Analytics 📊"
])

eleves_data = st.session_state.eleves

# ------------------------------------------------------------
# 1. APERÇU GÉNÉRAL
# ------------------------------------------------------------
if menu == "1. Aperçu Général 📋":
    st.header("📋 Liste Globale des Élèves")

    if not eleves_data:
        st.info("Aucun élève enregistré pour le moment.")
    else:
        df = pd.DataFrame(eleves_data)
        
        # Filtre par classe
        classe_filtre = st.selectbox("Filtrer par classe :", ["Toutes"] + CLASSES)
        if classe_filtre != "Toutes":
            df = df[df["classe"] == classe_filtre]

        st.dataframe(df.drop(columns=["id"]), use_container_width=True)

# ------------------------------------------------------------
# 2. SAISIE / MODIFICATION
# ------------------------------------------------------------
elif menu == "2. Saisie / Modification ✍️":
    st.header("✍️ Gestion des Notes et Élèves")

    tab1, tab2 = st.tabs(["Ajouter un Élève", "Modifier un Élève"])

    with tab1:
        with st.form("form_ajout"):
            nom = st.text_input("Nom :")
            prenom = st.text_input("Prénom :")
            classe = st.selectbox("Classe :", CLASSES)
            
            c1, c2, c3 = st.columns(3)
            maths = c1.number_input("Mathématiques", 0.0, 20.0, 10.0, 0.5)
            francais = c2.number_input("Français", 0.0, 20.0, 10.0, 0.5)
            anglais = c3.number_input("Anglais", 0.0, 20.0, 10.0, 0.5)
            
            c4, c5 = st.columns(2)
            hg = c4.number_input("Histoire-Géo", 0.0, 20.0, 10.0, 0.5)
            pc = c5.number_input("Physique-Chimie", 0.0, 20.0, 10.0, 0.5)

            submitted = st.form_submit_button("Enregistrer l'élève")

            if submitted and nom and prenom:
                nouveau_id = max([e["id"] for e in eleves_data], default=0) + 1
                nouvel_eleve = {
                    "id": nouveau_id,
                    "nom": nom.upper(),
                    "prenom": prenom.capitalize(),
                    "classe": classe,
                    "mathematiques": maths,
                    "francais": francais,
                    "anglais": anglais,
                    "histoire_geo": hg,
                    "physique_chimie": pc,
                }
                nouvel_eleve["moyenne"] = calculer_moyenne(nouvel_eleve)
                st.session_state.eleves.append(nouvel_eleve)
                st.success(f"Élève {nom} {prenom} ajouté avec succès !")
                st.rerun()

    with tab2:
        if not eleves_data:
            st.warning("Aucun élève à modifier.")
        else:
            options_eleves = {f"{e['nom']} {e['prenom']} ({e['classe']})": e["id"] for e in eleves_data}
            choix = st.selectbox("Sélectionner un élève à modifier :", list(options_eleves.keys()))
            
            eleve_id = options_eleves[choix]
            eleve = next(e for e in eleves_data if e["id"] == eleve_id)

            with st.form("form_modif"):
                nom = st.text_input("Nom :", value=eleve["nom"])
                prenom = st.text_input("Prénom :", value=eleve["prenom"])
                classe = st.selectbox("Classe :", CLASSES, index=CLASSES.index(eleve["classe"]))

                c1, c2, c3 = st.columns(3)
                maths = c1.number_input("Mathématiques", 0.0, 20.0, float(eleve["mathematiques"]), 0.5)
                francais = c2.number_input("Français", 0.0, 20.0, float(eleve["francais"]), 0.5)
                anglais = c3.number_input("Anglais", 0.0, 20.0, float(eleve["anglais"]), 0.5)

                c4, c5 = st.columns(2)
                hg = c4.number_input("Histoire-Géo", 0.0, 20.0, float(eleve["histoire_geo"]), 0.5)
                pc = c5.number_input("Physique-Chimie", 0.0, 20.0, float(eleve["physique_chimie"]), 0.5)

                submit_update = st.form_submit_button("Mettre à jour")

                if submit_update:
                    eleve.update({
                        "nom": nom.upper(),
                        "prenom": prenom.capitalize(),
                        "classe": classe,
                        "mathematiques": maths,
                        "francais": francais,
                        "anglais": anglais,
                        "histoire_geo": hg,
                        "physique_chimie": pc,
                    })
                    eleve["moyenne"] = calculer_moyenne(eleve)
                    st.success("Données mises à jour !")
                    st.rerun()

# ------------------------------------------------------------
# 3. BULLETINS INDIVIDUELS
# ------------------------------------------------------------
elif menu == "3. Bulletins Individuels 📜":
    st.header("📜 Affichage du Bulletin")

    if not eleves_data:
        st.warning("Aucun élève enregistré.")
    else:
        options = {f"{e['nom']} {e['prenom']} ({e['classe']})": idx for idx, e in enumerate(eleves_data)}
        choix = st.selectbox("Choisir un élève :", list(options.keys()))
        
        index_eleve = options[choix]
        eleve = eleves_data[index_eleve]

        col_left, col_right = st.columns([2, 1])

        with col_left:
            st.subheader(f"Bulletin de {eleve['prenom']} {eleve['nom']}")
            st.write(f"**Classe :** {eleve['classe']}")
            
            df_notes = pd.DataFrame([
                {"Matière": "Mathématiques", "Note": fmt_num(eleve['mathematiques'])},
                {"Matière": "Français", "Note": fmt_num(eleve['francais'])},
                {"Matière": "Anglais", "Note": fmt_num(eleve['anglais'])},
                {"Matière": "Histoire-Géographie", "Note": fmt_num(eleve['histoire_geo'])},
                {"Matière": "Physique-Chimie", "Note": fmt_num(eleve['physique_chimie'])}
            ])
            st.table(df_notes)
            
            st.markdown(f"### **Moyenne Générale :** {fmt_num(eleve['moyenne'])} / 20")
            st.markdown(f"**Appréciation :** {attribuer_appreciation(eleve['moyenne'])}")

        with col_right:
            st.subheader("Générer le PDF")
            pdf_bytes = generer_pdf_bulletin(eleve, index_page=index_eleve)
            st.download_button(
                label="📥 Télécharger le Bulletin (PDF)",
                data=pdf_bytes,
                file_name=f"Bulletin_{eleve['nom']}_{eleve['prenom']}.pdf",
                mime="application/pdf"
            )

# ------------------------------------------------------------
# 4. EXPORT PDF / DATA
# ------------------------------------------------------------
elif menu == "4. Export PDF / Data 📥":
    st.header("📥 Exportations des Données")

    if eleves_data:
        df_export = pd.DataFrame(eleves_data)
        
        # Export CSV
        csv = df_export.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📄 Télécharger les données en CSV",
            data=csv,
            file_name="donnees_eleves.csv",
            mime="text/csv"
        )
    else:
        st.info("Aucune donnée disponible à exporter.")

# ------------------------------------------------------------
# 5. PARAMÈTRES
# ------------------------------------------------------------
elif menu == "5. Paramètres ⚙️":
    st.header("⚙️ Paramètres du Système")
    st.write("Gestion des options de l'application et réinitialisation.")

    if st.button("🔴 Réinitialiser les données d'exemple"):
        st.session_state.eleves = []
        st.success("Toutes les données ont été réinitialisées.")
        st.rerun()

# ------------------------------------------------------------
# 6. STATISTIQUES & ANALYTICS DYNAMIQUES
# ------------------------------------------------------------
elif menu == "6. Statistiques & Analytics 📊":
    st.header("📊 Statistiques et Indicateurs de Performance")

    if not eleves_data:
        st.warning("Aucune donnée disponible pour calculer les statistiques.")
        st.stop()

    df_stats = pd.DataFrame(eleves_data)
    classe_stat = st.selectbox("Sélectionner une classe à analyser :", ["Toutes les classes"] + CLASSES)

    if classe_stat != "Toutes les classes":
        df_stats = df_stats[df_stats["classe"] == classe_stat]

    total_eleves = len(df_stats)
    if total_eleves == 0:
        st.info("Aucun élève trouvé pour cette sélection.")
    else:
        col_m1, col_m2, col_m3 = st.columns(3)
        moyenne_classe = df_stats["moyenne"].mean()
        taux_reussite = (df_stats["moyenne"] >= 10.0).mean() * 100

        col_m1.metric("Effectif Total", f"{total_eleves} élèves")
        col_m2.metric("Moyenne Générale", f"{fmt_num(moyenne_classe)} / 20")
        col_m3.metric("Taux de Réussite (≥10)", f"{fmt_num(taux_reussite, 1)} %")

        st.markdown("---")
        
        # Répartition par tranches d'appréciation
        df_stats["Appreciation"] = df_stats["moyenne"].apply(attribuer_appreciation)
        repartition = df_stats["Appreciation"].value_counts()
        
        fig_donut = creer_graphique_donut(
            labels=repartition.index.tolist(),
            valeurs=repartition.values.tolist(),
            couleurs=["#1E6F50", "#C89B3C", "#2E4E7C", "#B9C4D6", "#991B1B"],
            titre="Répartition des Appréciations",
            sous_titre_centre=f"{total_eleves} Élèves"
        )
        st.plotly_chart(fig_donut, use_container_width=True)
