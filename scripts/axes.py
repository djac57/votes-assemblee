"""Les 7 axes de score : textes de référence et sens codé à la main.

CHOIX ÉDITORIAUX, CONTESTABLES PAR NATURE. Chaque axe est orienté : pour chaque texte retenu,
`sens = +1` signifie qu'ADOPTER le texte va dans le sens de l'axe, `-1` dans le sens contraire.
Un texte n'est retenu que si son intitulé suffit à dire dans quel sens il va ; les textes
ambigus (budgets « fourre-tout », textes mêlant mesures opposées…) sont écartés.

Les scrutins de référence sont ensuite déduits automatiquement (build.py) :
- vote sur l'ensemble, l'article premier, l'article unique, ou la résolution elle-même : même sens que le texte ;
- motion de rejet préalable ou de renvoi en commission : sens inverse (la voter, c'est refuser le texte) ;
- amendement de suppression d'un article : sens inverse (le voter, c'est retirer une partie du texte),
  seulement dans les textes courts (voir MAX_SCRUTINS_FOR_SUPPRESSIONS) ;
- scrutins listés dans EXCLUDE : écartés (votes tactiques).
Les amendements ordinaires ne sont jamais utilisés : leur intitulé ne dit pas ce qu'ils font.

Chaque axe est BIPOLAIRE : deux pôles nommés (`plus` et `minus`), aussi légitimes l'un que l'autre.
`side` indique de quel côté le pôle `plus` est dessiné (« left » ou « right ») ; cet ordre est une
convention de lecture, pas un classement.

Position d'un groupe ou d'un député : moyenne de (sens × vote), avec pour = +1, contre = −1,
abstention = 0, absent ignoré ; stockée sur [0, 100] (50 = au centre), affichée comme un écart au centre.

Biais « soutien au gouvernement » : build.py mesure, pour chaque axe, la part des scrutins de
référence portant sur des textes du Gouvernement et le lien avec la proximité au bloc gouvernemental.
Les listes ont été complétées (octobre 2026) par des textes d'initiative d'opposition, transpartisans
ou sénatoriaux, pour qu'aucun axe ne repose majoritairement sur des textes du Gouvernement.
Les budgets (lois de finances, de financement de la Sécurité sociale, de fin de gestion, approbation
des comptes) ne sont plus des références : les voter, c'est d'abord soutenir ou non le Gouvernement ;
ce soutien est mesuré à part (« Proximité avec le gouvernement »).
"""

# Scrutins écartés à la main, avec la raison (numéro de scrutin de l'Assemblée)
EXCLUDE = {
    2105: "motion de rejet déposée par les auteurs du texte (loi « Duplomb ») pour l'envoyer en CMP : vote tactique",
    6133: "motion de rejet adoptée sur le travail le 1er mai, déposée par le bloc central : sens incertain",
    2208: "motion de rejet adoptée sur l'A69 : usage tactique possible, sens incertain",
}
# Amendements de suppression retenus seulement dans les textes courts : dans un texte « fourre-tout »
# (budget, simplification…), l'article supprimé peut aller contre l'esprit du texte.
MAX_SCRUTINS_FOR_SUPPRESSIONS = 60

AXES = [
    {
        "k": "ecologie", "n": "Environnement ou activité",
        "plus": "Priorité à l'environnement", "minus": "Priorité à l'activité, moins de contraintes", "side": "left",
        "def": "Textes qui renforcent la protection de l'environnement et de la santé environnementale, ou au contraire allègent des contraintes environnementales pour l'activité (agriculture, transport, énergie).",
        "texts": [
            (+1, r"substances perfluoroalkylées"),                      # PFAS
            (+1, r"vaisselle en plastique"),
            (+1, r"contaminations au cadmium"),
            (+1, r"politique nationale d'adaptation au changement climatique"),
            (+1, r"transport maritime à propulsion vélique"),
            (+1, r"réaffirmer l.ambition climatique"),
            (+1, r"Parquet européen aux infractions à l.environnement"),
            (+1, r"centrales à charbon vers des combustibles moins émetteurs"),
            (+1, r"pour protéger l'eau potable"),                         # écologistes
            (+1, r"impact environnemental de l.industrie textile"),
            (-1, r"contraintes énergétiques pesant sur l.offre locative"),  # RN (DPE)
            (-1, r"lever dans les territoires d'outre-mer l'interdiction de recherche"),  # hydrocarbures
            (-1, r"lever les contraintes à l.exercice du métier d.agriculteur"),         # loi « Duplomb » (pesticides)
            (-1, r"liaison autoroutière entre Castres et Toulouse"),                      # A69
            (-1, r"cultures végétales à l'aide d'aéronefs télépilotés"),                  # épandage par drones
            (-1, r"abroger les zones à faibles émissions"),
        ],
    },
    {
        "k": "social", "n": "Protection sociale",
        "plus": "Plus de prestations et de protections", "minus": "Maîtrise des dépenses, flexibilité", "side": "left",
        "def": "Textes qui étendent des droits sociaux, des prestations ou des protections (salariés, retraités, familles, étudiants) ; voter contre peut traduire un souci de coût ou de flexibilité.",
        "texts": [
            (+1, r"retraite plus juste en annulant les dernières réformes"),
            (+1, r"abrogation de la retraite à 64 ans"),
            (+1, r"solidarité envers les retraités pauvres"),
            (+1, r"revalorisation des pensions de retraites agricoles"),
            (+1, r"bourses sur critères sociaux"),
            (+1, r"repas à 1 euro"),
            (+1, r"allocations familiales dès le premier enfant"),
            (+1, r"territoires zéro chômeur"),
            (+1, r"mineurs isolés et à lutter contre le sans-abrisme"),
            (+1, r"remboursement intégral des fauteuils roulants"),
            (+1, r"protection sociale complémentaire des agents publics"),
            (+1, r"mesures d'urgence contre la vie chère"),
            (+1, r"encadrement des loyers"),
            (+1, r"prestations familiales aux enfants placés"),
            (+1, r"gratuité des parkings d.hôpitaux|gratuité des parkings des hôpitaux"),
            (+1, r"parents d.enfants atteints d.un cancer|parents d.enfants atteints de cancers"),
            (-1, r"travailler le 1er mai"),
        ],
    },
    {
        "k": "budget", "n": "Finances publiques",
        "plus": "Rigueur, contrôle de la dépense", "minus": "Dépenses nouvelles", "side": "right",
        "no_suppression": True,  # supprimer un article budgétaire peut creuser comme réduire le déficit : ambigu
        "def": "Textes de contrôle de la dépense et de lutte contre la fraude, face à des propositions dont le coût budgétaire est central (plusieurs figurent aussi sur l'axe Protection sociale). Les budgets eux-mêmes ne sont pas retenus : leur vote mesure surtout le soutien au Gouvernement.",
        "texts": [
            (+1, r"lutte contre les fraudes sociales et fiscales"),          # Gouvernement
            (+1, r"contre toutes les fraudes aux aides publiques"),
            (+1, r"responsabilité financière des opérateurs de l'Etat"),
            (+1, r"gestion du patrimoine immobilier de l'État"),
            (+1, r"phénomène d.agencification de l.État"),                  # Droite républicaine
            (-1, r"allocations familiales dès le premier enfant"),          # environ 3 Md€ par an
            (-1, r"repas à 1 euro"),
            (-1, r"retraite plus juste en annulant les dernières réformes"),
            (-1, r"abrogation de la retraite à 64 ans"),
            (-1, r"revalorisation des pensions de retraites agricoles"),
        ],
    },
    {
        "k": "economie", "n": "Marché ou régulation",
        "plus": "Libéralisation, soutien à l'offre", "minus": "Régulation, intervention publique", "side": "right",
        "def": "Textes qui facilitent l'activité des entreprises et l'investissement, ou au contraire encadrent les acteurs économiques (banques, médias, démarchage, prix) et étendent l'intervention publique.",
        "texts": [
            (+1, r"simplification de la vie économique"),
            (+1, r"cadre fiscal stable, juste et lisible pour nos micro-entrepreneurs"),
            (+1, r"recouvrement des créances commerciales"),
            (+1, r"relancer les investissements dans le secteur de l.hydroélectricité"),
            (+1, r"compétitivité du secteur agroalimentaire"),
            (+1, r"transformation des bureaux et autres bâtiments en logements"),
            (+1, r"lever les contraintes à l.exercice du métier d.agriculteur"),
            (+1, r"travailler le 1er mai"),
            (-1, r"nationalisation d.ArcelorMittal"),
            (-1, r"impôt plancher de 2 % sur le patrimoine"),
            (+1, r"contraintes énergétiques pesant sur l.offre locative"),
            (-1, r"frais bancaires"),                                      # socialistes, GDR
            (-1, r"fermetures abusives de comptes bancaires"),
            (-1, r"démarchage téléphonique consenti"),
            (-1, r"monopoles économiques dans le secteur des médias"),
            (-1, r"régulation des meublés de tourisme"),
            (-1, r"réguler la concentration des acteurs économiques"),
        ],
    },
    {
        "k": "simplification", "n": "Normes et procédures",
        "plus": "Allègement des normes", "minus": "Maintien des règles et des contrôles", "side": "right",
        "def": "Textes qui allègent des normes et des procédures administratives ; voter contre peut traduire l'attachement aux règles, garanties ou contrôles qu'ils assouplissent.",
        "texts": [
            (+1, r"simplification de la vie économique"),
            (+1, r"simplification du droit de l'urbanisme et du logement"),
            (+1, r"simplifier le millefeuille territorial"),
            (+1, r"simplifier la gestion de la commande publique"),
            (+1, r"simplifiant l'ouverture des débits de boissons"),
            (+1, r"simplifier la sortie de l.indivision"),
            (+1, r"assouplir la gestion des compétences"),
            (+1, r"procédure simplifiée de recouvrement"),
            (+1, r"assouplir la procédure d'autorisation des établissements"),
            (+1, r"dérogation à la participation minimale pour la maîtrise d'ouvrage"),
            (+1, r"lever les contraintes à l.exercice du métier d.agriculteur"),
            (+1, r"faciliter la transformation des bureaux"),
            (+1, r"médecins diplômés au Royaume-Uni"),
            (+1, r"phénomène d.agencification de l.État"),
            (+1, r"contraintes énergétiques pesant sur l.offre locative"),
        ],
    },
    {
        "k": "immigration", "n": "Immigration",
        "plus": "Politique migratoire plus restrictive", "minus": "Politique migratoire plus ouverte", "side": "right",
        "def": "Textes qui durcissent ou assouplissent les conditions d'entrée, de séjour, d'éloignement ou d'accès à la nationalité des étrangers.",
        "texts": [
            (+1, r"accès à la nationalité française à Mayotte"),
            (+1, r"maintien en rétention des personnes condamnées"),
            (+1, r"la rétention administrative et la prévention des risques d.attentat"),
            (+1, r"assouplir les conditions d.expulsion des étrangers"),
            (+1, r"refonder l'espace Schengen"),
            (+1, r"lutter contre les mariages simulés ou arrangés"),
            (+1, r"rétablissement du délit de séjour irrégulier"),          # RN
            (+1, r"dénoncer les accords franco-algériens"),                # RN
            (-1, r"renouvellement automatique des titres de séjour"),
        ],
    },
    {
        "k": "securite", "n": "Sécurité et libertés",
        "plus": "Priorité à la fermeté pénale", "minus": "Priorité aux libertés et garanties", "side": "right",
        "def": "Textes qui renforcent les moyens policiers et judiciaires ou durcissent les sanctions, ou au contraire renforcent les droits et garanties (contrôle des lieux de privation de liberté, droits des détenus).",
        "texts": [
            (+1, r"piège du narcotrafic"),
            (+1, r"procureur de la République (national )?anti-criminalité organisée"),
            (+1, r"procureur national anti-stupéfiants"),
            (+1, r"phénomènes troublant l'ordre public"),
            (+1, r"présomption de légitime défense"),
            (+1, r"pénalisation de l.organisation de rave-parties"),
            (+1, r"exécuter les peines d.emprisonnement ferme"),
            (+1, r"sûreté dans les transports"),
            (+1, r"autorité de la justice à l'égard des mineurs délinquants"),
            (+1, r"justice criminelle et le respect des victimes"),
            (+1, r"renforcement des juridictions criminelles"),
            (+1, r"Agence de gestion et de recouvrement des avoirs saisis"),
            (+1, r"personnes ciblées par les réseaux de criminalité organisée"),
            (+1, r"homicide routier"),
            (-1, r"droit de visite des parlementaires et des bâtonniers"),
        ],
    },
]
