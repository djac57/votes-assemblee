# Qui vote avec qui ?

Visualisation des scrutins publics de l'Assemblée nationale (17e législature) : positions des groupes par thème, accords de vote entre groupes, carte des députés d'après leurs votes, discipline de groupe et grands votes.

En ligne : https://djac57.github.io/votes-assemblee/

## Mise à jour automatique

Le workflow GitHub Actions (`.github/workflows/update.yml`) tourne chaque lundi et à chaque push : il retélécharge l'open data, régénère `site/data.js`, committe s'il y a du nouveau et déploie `site/` sur GitHub Pages. Lancement manuel : onglet **Actions** → « Run workflow ».

## Reconstruire les données

```sh
python3 scripts/fetch.py /chemin/vers/dossier_brut   # ~40 Mo d'archives, ~320 Mo décompressés
python3 scripts/build.py /chemin/vers/dossier_brut   # -> site/data.js (~2 Mo)
open site/index.html
```

Bibliothèque standard Python uniquement.

## Sources

- Scrutins : https://data.assemblee-nationale.fr/static/openData/repository/17/loi/scrutins/Scrutins.json.zip
- Acteurs, mandats, organes (historique) : https://data.assemblee-nationale.fr/static/openData/repository/17/amo/tous_acteurs_mandats_organes_xi_legislature/AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip

## Les 7 boussoles (scripts/axes.py)

Écologie, Social, Responsabilité budgétaire, Dynamisme économique, Simplification administrative, Restriction migratoire, Sécurité. Pour chaque axe, une liste de textes dont l'intitulé indique clairement le sens (+1 : adopter le texte va dans le sens de l'axe). Scrutins retenus : ensemble, article premier/unique (même sens), motions de rejet (sens inverse), amendements de suppression dans les textes courts (sens inverse) ; votes tactiques exclus à la main (EXCLUDE). Score = moyenne de sens × vote (pour +1, contre −1, abstention 0) ramenée sur 0–100. Choix éditoriaux, contestables : la page liste chaque scrutin retenu.

## Méthode

- **Thèmes** (`scripts/themes.py`) : mots-clés appliqués au nom du texte extrait du titre du scrutin, règles évaluées par ordre de priorité, plus quelques exceptions explicites. ~1 % des scrutins restent « Autres ».
- **Position par thème** : premier axe d'une décomposition en valeurs singulières de la matrice groupes × scrutins (position nette (pour − contre) / exprimés, centrée, pondérée par la taille des groupes), orienté pour que LFI soit négatif, normalisé à [−1, 1].
- **Accord entre groupes** : part des scrutins où leurs positions majoritaires (pour / contre / abstention) coïncident.
- **Carte des députés** : chaque député est projeté sur les deux axes des groupes d'après ses propres votes (au moins 30 votes dans le thème).
- **Proximité entre députés** : part des scrutins communs (au moins 100) où ils ont voté pareil.
- **Loyauté** : part des votes conformes à la position majoritaire de son groupe au moment du vote.
