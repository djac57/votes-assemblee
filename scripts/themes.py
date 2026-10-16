"""Classement des scrutins par grand thème, à partir du titre du texte voté.

Les règles sont évaluées dans l'ordre : la première qui correspond l'emporte
(« sécurité sociale » doit passer avant « sécurité », « nationalité à Mayotte »
avant « Mayotte »). Pour ajuster le classement, il suffit de modifier THEMES.
"""
import re

THEMES = [
    ("immigration", "Immigration & nationalité",
     r"nationalit|immigr|étranger|droit d'asile|\basile\b|rétention|titres? de séjour|droit du sol|frontière|aide médicale d'état|\bAME\b"),
    ("sante", "Santé & fin de vie",
     r"aide à mourir|fin de vie|soins palliatifs|santé|médic|hôpita|pharmac|maladie|soignant|déserts? médica|psychiatr|addiction|tabac|cancer|sanitaire|infirmi|cardio|médecin"),
    ("budget", "Budget & fiscalité",
     r"loi de finances|fin de gestion|impôt|fiscal|\btaxe|patrimoine des ultra|finances publiques|dette|règlement du budget|approbation des comptes|niches?"),
    ("social", "Social, travail & logement",
     r"sécurité sociale|retraite|emploi|salari|chômage|travail|titre-restaurant|fraudes? sociales|pouvoir d'achat|smic|minimum|pauvreté|logement|locati|habitat|hlm|handicap|autonomie|dépendance|aidants?|professionnalisation|apprentissage"),
    ("agriculture", "Agriculture & alimentation",
     r"agricol|agricult|agroalimentaire|alimentation|élevage|éleveur|pêche|forêt|viticult|monde rural"),
    ("ecologie", "Écologie & énergie",
     r"énerg|climat|hydroélectri|eau potable|\beau\b|environnement|biodiversit|nucléaire|pesticide|pollution|déchets|transition écologique|carbone|renouvelable|zéro artificialisation|\bZAN\b|zones? à faibles émissions|plastique|perfluoro|PFAS"),
    ("securite", "Sécurité & justice",
     r"ordre public|sécurité(?! sociale)|sûreté|narcotrafic|justice|peines?|pénal|légitime défense|rave-part|avoirs saisis|police|gendarm|terroris|délinquan|prison|détenu|criminel|victimes?|cybers|sécurité civile"),
    ("economie", "Économie & entreprises",
     r"vie économique|économique|nationalisation|arcelor|industri|commerç|entreprise|concurrence|consommat|banque|numérique|souveraineté industrielle|tourisme|artisan|médias|plateformes|bancaire|débits? de boissons"),
    ("societe", "Société, droits & éducation",
     r"violences|sexis|sexuel|antisémitisme|racisme|discrimin|égalité|enfant|mineur|scolaire|école|éducat|enseign|universit|jeunesse|famille|ivg|avortement|réseaux sociaux|état-civil|laïcit|culture|biens culturels|olympiques|sport|patrimoine|langues? régional|animal|animaux|étudiant|code noir|esclavage|mémoire|homosexualit|conjugal|audiovisuel public"),
    ("international", "International & défense",
     r"programmation militaire|militaire|défense|armées|ukraine|européenne|union européenne|traité|accord entre|convention entre|international|otan|israël|palestin|gaza|russie|coopération"),
    ("institutions", "Institutions & territoires",
     r"élu local|élus locaux|mode de scrutin|élection|électoral|constitution|corse|collectivit|millefeuille|territori|outre-mer|mayotte|nouvelle-calédonie|guadeloupe|martinique|guyane|réunion|polynésie|commune|montagne|motion de censure|déclaration du gouvernement|règlement de l'assemblée|référendum|parlement|service public|postal|fonction publique|transports?"),
]
OTHER = ("autres", "Autres sujets")

# Exceptions vérifiées sur les textes de la 17e législature, testées avant THEMES
OVERRIDES = [
    (r"adaptation au droit de l'union européenne", "economie"),
    (r"cultures végétales", "agriculture"),
    (r"médias", "economie"),
    (r"retraités", "social"),
    (r"service public postal", "institutions"),
    (r"fraudes? aux aides publiques|lois? de finances", "budget"),
]
_COMPILED = [(k, re.compile(p, re.I)) for p, k in OVERRIDES] + [(k, re.compile(p, re.I)) for k, _, p in THEMES]

# Nom du texte dans le titre du scrutin : « … du projet de loi de finances pour 2026 (première lecture) »
TEXT = re.compile(r"((?:projet|proposition) de (?:loi(?: organique| constitutionnelle)?|résolution(?: européenne)?)[^;]*?)(?:\s*\((?:première|deuxième|nouvelle|troisième|lecture définitive)[^)]*\))?\.?$", re.I)


def text_of(title):
    m = TEXT.search(title)
    if m:
        return m.group(1).strip()
    if re.search(r"motion de censure", title, re.I):
        return "Motions de censure"
    if re.search(r"déclaration du gouvernement", title, re.I):
        return "Déclarations du Gouvernement"
    return None


def theme_of(title):
    """Thème d'un scrutin : d'abord sur le nom du texte, sinon sur tout le titre."""
    text = text_of(title)
    for target in ([text] if text else []) + [title]:
        for key, rx in _COMPILED:
            if rx.search(target):
                return key
    return OTHER[0]


def labels():
    return [(k, l) for k, l, _ in THEMES] + [OTHER]
