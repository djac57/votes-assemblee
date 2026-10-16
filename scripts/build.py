"""Construit site/data.js à partir de l'open data de l'Assemblée (17e législature).

    python3 scripts/build.py <dossier_brut>   # le dossier rempli par fetch.py

Calculs :
- pour chaque scrutin et chaque groupe : décompte pour / contre / abstention (tel que publié) ;
- thème du scrutin (themes.py, mots-clés sur le titre du texte) ;
- carte des députés : axes de clivage tirés des positions des groupes (décomposition en
  valeurs singulières de la matrice groupes x scrutins), puis chaque député est placé
  d'après ses propres votes sur ces axes — un député qui vote comme son groupe tombe
  sur lui, un « frondeur » s'en écarte ;
- accords entre députés : part des scrutins communs où ils ont voté pareil
  (pour / contre / abstention), calculée avec des masques de bits.
"""
import datetime
import glob
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import themes as T  # noqa: E402

RAW = sys.argv[1] if len(sys.argv) > 1 else "raw"
OUT = os.path.join(HERE, "..", "site", "data.js")
EPOCH = datetime.date(2024, 1, 1)

# Ordre d'affichage, de la gauche vers la droite ; couleurs politiques usuelles
GROUPS = [
    ("LFI-NFP", "La France insoumise – NFP", "#d4232b"),
    ("GDR", "Gauche démocrate et républicaine", "#9e1b21"),
    ("ECOS", "Écologiste et social", "#2fa84f"),
    ("SOC", "Socialistes et apparentés", "#e8579a"),
    ("LIOT", "Libertés, indépendants, outre-mer et territoires", "#b3a46a"),
    ("DEM", "Les Démocrates", "#ee7d22"),
    ("EPR", "Ensemble pour la République", "#f2b100"),
    ("HOR", "Horizons & indépendants", "#1ba5b3"),
    ("DR", "Droite républicaine", "#3c8fd6"),
    ("UDR", "Union des droites pour la République", "#5b6fc2"),
    ("RN", "Rassemblement national", "#2c3f8f"),
    ("NI", "Non inscrits", "#9a9a94"),
]
GKEY = {k: i for i, (k, _, _) in enumerate(GROUPS)}
ALIASES = {"UDDPLR": "UDR"}  # l'UDR a changé d'identifiant en septembre 2025
NG = len(GROUPS)
MIN_VOTES_MAP = 30  # votes minimum (dans le thème) pour placer un député sur la carte


def as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------- Groupes ----------
organ_group = {}


def group_of(ref):
    if ref in organ_group:
        return organ_group[ref]
    path = os.path.join(RAW, "amo", "json", "organe", ref + ".json")
    g = None
    if os.path.exists(path):
        o = load_json(path)["organe"]
        if o.get("codeType") == "GP":
            k = o.get("libelleAbrev") or ""
            g = GKEY.get(ALIASES.get(k, k))
    organ_group[ref] = g
    return g


# ---------- Scrutins ----------
files = glob.glob(os.path.join(RAW, "scrutins", "json", "*.json"))
raw_scrutins = []
for f in files:
    s = load_json(f)["scrutin"]
    raw_scrutins.append(s)
raw_scrutins.sort(key=lambda s: (s["dateScrutin"], int(s["numero"])))

texts, text_idx = [], {}
S = {"n": [], "d": [], "th": [], "r": [], "ty": [], "tx": [], "ti": [], "g": []}
theme_keys = [k for k, _ in T.labels()]
dep_votes = defaultdict(dict)  # acteur -> {indice scrutin: (valeur, groupe)}
TYPES = {"SPO": 0, "SPS": 1, "MOC": 2}
VAL = {"pours": 1, "contres": -1, "abstentions": 0}

for j, s in enumerate(raw_scrutins):
    title = re.sub(r"\s+", " ", s["titre"]).strip()
    text = T.text_of(title)
    if text:
        text = text[0].upper() + text[1:]
        if text not in text_idx:
            text_idx[text] = len(texts)
            texts.append(text)
    # Objet du vote, sans le nom du texte : « l'amendement n° 12 de M. X après l'article 3 »
    obj = re.split(r"\s+(?:du|de la|de l'|d'une?)\s+(?:projet|proposition) de", title, maxsplit=1)[0]
    obj = obj[0].upper() + obj[1:] if obj else title
    d = (datetime.date.fromisoformat(s["dateScrutin"]) - EPOCH).days
    counts = [0] * (NG * 4)
    for grp in as_list(s["ventilationVotes"]["organe"]["groupes"]["groupe"]):
        g = group_of(grp["organeRef"])
        if g is None:
            continue
        dv = grp["vote"]["decompteVoix"]
        base = g * 4
        counts[base] += int(dv.get("pour") or 0)
        counts[base + 1] += int(dv.get("contre") or 0)
        counts[base + 2] += int(dv.get("abstentions") or 0)
        counts[base + 3] += int(grp.get("nombreMembresGroupe") or 0)
        nom = grp["vote"].get("decompteNominatif") or {}
        for key, val in VAL.items():
            block = nom.get(key) or {}
            for v in as_list(block.get("votant")):
                dep_votes[v["acteurRef"]][j] = (val, g)
    S["n"].append(int(s["numero"]))
    S["d"].append(d)
    S["th"].append(theme_keys.index(T.theme_of(title)))
    S["r"].append(1 if s["sort"]["code"].startswith("adopt") else 0)
    S["ty"].append(TYPES.get(s["typeVote"]["codeTypeVote"], 0))
    S["tx"].append(text_idx[text] if text else -1)
    S["ti"].append(obj[:110])
    S["g"].append(counts)
NS = len(raw_scrutins)
print(f"{NS} scrutins, {len(dep_votes)} députés ayant voté, {len(texts)} textes")


# ---------- Algèbre légère (stdlib) ----------
def jacobi_eigen(a, iters=100):
    """Valeurs et vecteurs propres d'une petite matrice symétrique (méthode de Jacobi)."""
    n = len(a)
    a = [row[:] for row in a]
    v = [[1.0 if i == k else 0.0 for k in range(n)] for i in range(n)]
    for _ in range(iters):
        off = sum(a[i][k] ** 2 for i in range(n) for k in range(n) if i != k)
        if off < 1e-12:
            break
        for p in range(n):
            for q in range(p + 1, n):
                if abs(a[p][q]) < 1e-15:
                    continue
                theta = (a[q][q] - a[p][p]) / (2 * a[p][q])
                t = (1 if theta >= 0 else -1) / (abs(theta) + math.sqrt(theta * theta + 1))
                c = 1 / math.sqrt(t * t + 1)
                sn = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p] = c * akp - sn * akq
                    a[k][q] = sn * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k] = c * apk - sn * aqk
                    a[q][k] = sn * apk + c * aqk
                for k in range(n):
                    vkp, vkq = v[k][p], v[k][q]
                    v[k][p] = c * vkp - sn * vkq
                    v[k][q] = sn * vkp + c * vkq
    vals = [a[i][i] for i in range(n)]
    order = sorted(range(n), key=lambda i: -vals[i])
    return [vals[i] for i in order], [[v[k][i] for k in range(n)] for i in order]


def group_net(j):
    """Position nette de chaque groupe au scrutin j : (pour - contre) / exprimés, ou None."""
    c = S["g"][j]
    out = []
    for g in range(NG):
        p, n, a = c[4 * g], c[4 * g + 1], c[4 * g + 2]
        out.append((p - n) / (p + n + a) if p + n + a else None)
    return out


seats = [0] * NG
for j in range(NS - 1, -1, -1):  # effectifs au dernier scrutin où le groupe apparaît
    for g in range(NG):
        if not seats[g] and S["g"][j][4 * g + 3]:
            seats[g] = S["g"][j][4 * g + 3]
weights = [math.sqrt(max(1, s)) for s in seats]


def axes(scope):
    """Deux axes de clivage sur un ensemble de scrutins : loadings par scrutin + coordonnées des groupes."""
    nets, means = {}, {}
    for j in scope:
        x = group_net(j)
        num = sum(seats[g] * x[g] for g in range(NG) if x[g] is not None)
        den = sum(seats[g] for g in range(NG) if x[g] is not None)
        if not den:
            continue
        means[j] = num / den
        nets[j] = x
    js = list(nets)
    if len(js) < 10:
        return None
    Y = [[(weights[g] * (nets[j][g] - means[j]) if nets[j][g] is not None else 0.0) for j in js] for g in range(NG)]
    K = [[sum(a * b for a, b in zip(Y[g], Y[h])) for h in range(NG)] for g in range(NG)]
    vals, vecs = jacobi_eigen(K)
    load = []
    for k in range(2):
        sig = math.sqrt(max(vals[k], 1e-12))
        load.append({j: sum(Y[g][i] * vecs[k][g] for g in range(NG)) / sig for i, j in enumerate(js)})
    # Orientation : LFI à gauche sur l'axe 1, RN en haut sur l'axe 2
    def coord(g, k):
        num = sum((nets[j][g] - means[j]) * load[k][j] for j in js if nets[j][g] is not None)
        den = sum(load[k][j] ** 2 for j in js if nets[j][g] is not None)
        return num / den if den else 0.0
    if coord(GKEY["LFI-NFP"], 0) > 0:
        load[0] = {j: -v for j, v in load[0].items()}
    if coord(GKEY["RN"], 1) < 0:
        load[1] = {j: -v for j, v in load[1].items()}
    explained = [vals[k] / sum(max(v, 0) for v in vals) for k in range(2)]
    gcoords = [[round(coord(g, 0), 3), round(coord(g, 1), 3)] for g in range(NG)]
    return load, means, gcoords, explained


# ---------- Députés ----------
def deputy_info(ref):
    path = os.path.join(RAW, "amo", "json", "acteur", ref + ".json")
    if not os.path.exists(path):
        return None
    a = load_json(path)["acteur"]
    ident = a["etatCivil"]["ident"]
    dept, circo, starts, ends = "", "", [], []
    for m in as_list(a.get("mandats", {}).get("mandat")):
        if m.get("legislature") == "17" and m.get("typeOrgane") == "ASSEMBLEE":
            starts.append(m.get("dateDebut"))
            ends.append(m.get("dateFin"))  # None : mandat en cours
            lieu = (m.get("election") or {}).get("lieu") or {}
            dept, circo = lieu.get("departement") or dept, lieu.get("numCirco") or circo
    start = min((x for x in starts if x), default=None)
    end = None if not ends or None in ends else max(ends)
    return {"name": f"{ident['prenom']} {ident['nom']}", "civ": ident.get("civ", ""), "dept": dept, "circo": circo,
            "start": start, "end": end}


deps = []
for ref, votes in dep_votes.items():
    info = deputy_info(ref) or {"name": ref, "civ": "", "dept": "", "circo": "", "start": None, "end": None}
    last_j = max(votes)
    info.update(ref=ref, group=votes[last_j][1], votes=votes)
    deps.append(info)
deps.sort(key=lambda d: (d["group"], d["name"]))
print(f"{len(deps)} députés")

# Masques de bits par député (pour / contre / abstention) et par thème
for d in deps:
    p = c = a = 0
    for j, (v, _) in d["votes"].items():
        bit = 1 << j
        if v == 1:
            p |= bit
        elif v == -1:
            c |= bit
        else:
            a |= bit
    d["P"], d["C"], d["A"] = p, c, a
    d["V"] = p | c | a
theme_mask = defaultdict(int)
for j in range(NS):
    theme_mask[S["th"][j]] |= 1 << j
day_of = S["d"]

# Participation : votes exprimés / scrutins tenus pendant le mandat
for d in deps:
    s0 = (datetime.date.fromisoformat(d["start"]) - EPOCH).days if d["start"] else min(day_of[j] for j in d["votes"])
    e0 = (datetime.date.fromisoformat(d["end"]) - EPOCH).days if d["end"] else 10 ** 6
    held = sum(1 for x in day_of if s0 <= x <= e0)
    d["part"] = round(len(d["votes"]) / held, 4) if held else 0

# Loyauté : part des votes conformes à la position majoritaire de son groupe du moment
def majority(j, g):
    c = S["g"][j]
    p, n, a = c[4 * g], c[4 * g + 1], c[4 * g + 2]
    if p + n + a == 0:
        return None
    best = max(p, n, a)
    if [p, n, a].count(best) > 1:
        return None  # égalité : pas de consigne lisible
    return 1 if best == p else (-1 if best == n else 0)


for d in deps:
    same = tot = 0
    by_theme = Counter(), Counter()
    for j, (v, g) in d["votes"].items():
        m = majority(j, g)
        if m is None:
            continue
        tot += 1
        same += v == m
    d["loyal"] = round(same / tot, 4) if tot else None
    # Accord avec chaque groupe (position majoritaire), tous scrutins
    agree = []
    for g in range(NG):
        s_ = t_ = 0
        for j, (v, _) in d["votes"].items():
            m = majority(j, g)
            if m is None:
                continue
            t_ += 1
            s_ += v == m
        agree.append(round(s_ / t_, 3) if t_ >= 20 else None)
    d["gagree"] = agree

# Cartes : axes de clivage par thème (et « tous »), puis projection des députés
maps, gmaps, explained = {}, {}, {}
scopes = {"all": range(NS)}
for ti, k in enumerate(theme_keys):
    scopes[k] = [j for j in range(NS) if S["th"][j] == ti]
for name, scope in scopes.items():
    res = axes(scope)
    if not res:
        continue
    load, means, gco, expl = res
    gmaps[name], explained[name] = gco, [round(e, 3) for e in expl]
    coords = []
    for d in deps:
        js = [j for j in d["votes"] if j in means]
        if len(js) < MIN_VOTES_MAP:
            coords.append(None)
            continue
        xy = []
        for k in range(2):
            num = sum((d["votes"][j][0] - means[j]) * load[k][j] for j in js)
            den = sum(load[k][j] ** 2 for j in js)
            xy.append(round(num / den, 3) if den else 0)
        coords.append(xy)
    maps[name] = coords
    print(f"  carte {name} : {len(scope)} scrutins, {sum(c is not None for c in coords)} députés placés, axes {explained[name]}")

# Députés les plus proches (accord sur au moins 100 scrutins communs)
for i, d in enumerate(deps):
    best = []
    for k, e in enumerate(deps):
        if k == i:
            continue
        common = (d["V"] & e["V"]).bit_count()
        if common < 100:
            continue
        same = ((d["P"] & e["P"]) | (d["C"] & e["C"]) | (d["A"] & e["A"])).bit_count()
        best.append((same / common, k, common))
    best.sort(reverse=True)
    other = [b for b in best if deps[b[1]]["group"] != d["group"]]
    d["close"] = [[k, round(r, 3)] for r, k, _ in best[:5]]
    d["closeOut"] = [[k, round(r, 3)] for r, k, _ in other[:3]]
    d["far"] = [[k, round(r, 3)] for r, k, _ in best[-3:][::-1]]

# ---------- Origine des textes (projet du Gouvernement / proposition d'un groupe / du Sénat) ----------
import unicodedata  # noqa: E402


def _norm(t):
    t = unicodedata.normalize("NFD", t.lower().replace("’", "'"))
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in t if not unicodedata.combining(c))).strip()


_dossiers = []
for f in glob.glob(os.path.join(RAW, "dossiers", "json", "dossierParlementaire", "DLR5L1[67]*.json")):
    dp = load_json(f)["dossierParlementaire"]
    nt = _norm((dp.get("titreDossier") or {}).get("titre") or "")
    if len(nt) > 12:
        _dossiers.append((nt, set(nt.split()), dp))
SUFFIX = re.compile(r"\s*\((texte de la commission mixte paritaire|seconde délibération|première lecture|[^()]*lecture)\)|\)$", re.I)


_docs = {}  # titre normalisé du texte déposé -> (dossier, premier auteur)
for f in glob.glob(os.path.join(RAW, "dossiers", "json", "document", "*L1[67]*.json")):
    doc = load_json(f)["document"]
    nt = _norm((doc.get("titres") or {}).get("titrePrincipal") or "")
    auth = as_list((doc.get("auteurs") or {}).get("auteur"))
    act = next((x["acteur"]["acteurRef"] for x in auth if isinstance(x, dict) and x.get("acteur")), None)
    if nt and nt not in _docs:
        _docs[nt] = (doc.get("dossierRef"), act)


def author_of(text):
    nt = _norm(SUFFIX.sub("", text))
    if nt in _docs:
        return _docs[nt]
    hits = [(len(n), v) for n, v in _docs.items() if len(n) > 30 and (n in nt or nt in n)]
    return max(hits, key=lambda x: x[0])[1] if hits else (None, None)


def dossier_of(text):
    nt = _norm(SUFFIX.sub("", text))
    hits = [(len(n), dp) for n, _, dp in _dossiers if n in nt]
    if hits:
        return max(hits, key=lambda x: x[0])[1]
    words = set(nt.split())
    best = max(((len(w & words) / len(w | words), dp) for _, w, dp in _dossiers), key=lambda x: x[0], default=(0, None))
    return best[1] if best[0] >= .6 else None


def group_at(acteur, date):
    path = os.path.join(RAW, "amo", "json", "acteur", acteur + ".json")
    if not os.path.exists(path):
        return None, False
    ms = as_list(load_json(path)["acteur"].get("mandats", {}).get("mandat"))
    deputy = any(m.get("typeOrgane") == "ASSEMBLEE" and m.get("legislature") in ("16", "17") for m in ms)
    for m in ms:
        if m.get("typeOrgane") == "GP" and (m.get("dateDebut") or "") <= date <= (m.get("dateFin") or "9999"):
            g = group_of(m["organes"]["organeRef"])
            if g is not None:
                return g, True
    return None, deputy


first_date = {}
for j, s in enumerate(raw_scrutins):
    first_date.setdefault(S["tx"][j], s["dateScrutin"])
text_origin = []  # par texte : [type, groupe de l'auteur, uid du dossier] ; type : g = Gouvernement, a = député, s = Sénat
for t_i, text in enumerate(texts):
    dref, author = author_of(text)
    dp = dossier_of(text)
    uid = dref or (dp["uid"] if dp else "")
    if re.match(r"projet de loi", text, re.I):
        text_origin.append(["g", None, uid]); continue
    if re.search(r"adoptée par le Sénat", text, re.I):
        text_origin.append(["s", None, uid]); continue
    kind, g = "?", None
    if not author and dp:
        acts = as_list(((dp.get("initiateur") or {}).get("acteurs") or {}).get("acteur"))
        author = acts[0]["acteurRef"] if acts else None
    if author:
        g, deputy = group_at(author, first_date.get(t_i, "2025-01-01"))
        kind = "a" if deputy else "s"
    if re.match(r"motions de censure|déclarations? du gouvernement", text, re.I):
        kind = "x"
    text_origin.append([kind, g, uid])
print("  origine des textes : " + ", ".join(f"{k} {n}" for k, n in Counter(o[0] for o in text_origin).items()))

# Position du bloc gouvernemental sur chaque scrutin : majorité des votants EPR + Démocrates + Horizons
BLOC = [GKEY["EPR"], GKEY["DEM"], GKEY["HOR"]]
CENSURE = {i for i, t in enumerate(texts) if re.match(r"motions de censure", t, re.I)}
S["gv"] = []
for j in range(NS):
    c4 = S["g"][j]
    p = sum(c4[g * 4] for g in BLOC); c = sum(c4[g * 4 + 1] for g in BLOC); a = sum(c4[g * 4 + 2] for g in BLOC)
    gv = 1 if p > c and p > a else -1 if c > p and c > a else 0
    S["gv"].append(0 if S["tx"][j] in CENSURE else gv)
# Proximité de chaque député avec le bloc : même vote = 1, abstention = ½, vote opposé = 0
for d in deps:
    num = den = 0
    for j, (v, _) in d["votes"].items():
        gv = S["gv"][j]
        if gv:
            den += 1; num += 1 if v == gv else .5 if v == 0 else 0
    d["gov"] = round(num / den, 3) if den >= 30 else None

# ---------- Les 7 scores orientés (axes.py) ----------
import axes as AX  # noqa: E402

SAME = re.compile(r"^(L['’]ensemble|L['’]article (premier|unique|1er)\b|La proposition de (loi|résolution)|Le projet de loi)", re.I)
REJECT = re.compile(r"^La motion de (rejet|renvoi)", re.I)
SUPPR = re.compile(r"amendements? de suppression", re.I)
dep_index = {d["ref"]: i for i, d in enumerate(deps)}
axes_out = []
for ax in AX.AXES:
    rules = [(sg, re.compile(rx, re.I)) for sg, rx in ax["texts"]]
    text_size = Counter(S["tx"])
    refs, used = [], Counter()
    for j in range(NS):
        if S["tx"][j] < 0:
            continue
        text = texts[S["tx"][j]]
        sg = next((sg for sg, rx in rules if rx.search(text)), None)
        if sg is None:
            continue
        obj = S["ti"][j]
        if S["n"][j] in AX.EXCLUDE:
            continue
        if SAME.search(obj):
            refs.append([j, sg, "t"])
        elif REJECT.search(obj):
            refs.append([j, -sg, "m"])
        elif SUPPR.search(obj) and not ax.get("no_suppression") and text_size[S["tx"][j]] <= AX.MAX_SCRUTINS_FOR_SUPPRESSIONS:
            refs.append([j, -sg, "s"])
        else:
            continue
        used[text] += 1
    # Scores : moyenne de sens × vote (pour +1, contre −1, abstention 0) -> 0-100
    gsum, gn, dsum, dn = [0.0] * NG, [0] * NG, defaultdict(float), Counter()
    gscr = [set() for _ in range(NG)]
    for d in deps:
        i = dep_index[d["ref"]]
        for j, sg, _ in refs:
            if j in d["votes"]:
                v, g = d["votes"][j]
                gsum[g] += sg * v; gn[g] += 1; gscr[g].add(j)
                dsum[i] += sg * v; dn[i] += 1
    ax_scores = [[round(50 * (1 + gsum[g] / gn[g]), 1), len(gscr[g])] if gn[g] else None for g in range(NG)]
    dep_scores = [[round(50 * (1 + dsum[i] / dn[i]), 1), dn[i]] if dn[i] >= 3 else None for i in range(len(deps))]
    # Part des textes du Gouvernement et lien avec le soutien au bloc gouvernemental
    ref_tx = [S["tx"][j] for j, _, _ in refs]
    gov_refs = sum(text_origin[t][0] == "g" for t in ref_tx)
    bloc_refs = sum(text_origin[t][0] == "a" and text_origin[t][1] in BLOC for t in ref_tx)
    tset = set(ref_tx)
    voted = [(sg, S["gv"][j]) for j, sg, _ in refs if S["gv"][j]]
    pairs = [(dep_scores[i][0], deps[i]["gov"]) for i in range(len(deps)) if dep_scores[i] and deps[i]["gov"] is not None]
    r = None
    if len(pairs) > 20:
        mx = sum(a for a, _ in pairs) / len(pairs); my = sum(b for _, b in pairs) / len(pairs)
        sxy = sum((a - mx) * (b - my) for a, b in pairs); sxx = sum((a - mx) ** 2 for a, _ in pairs); syy = sum((b - my) ** 2 for _, b in pairs)
        r = round(sxy / math.sqrt(sxx * syy), 2) if sxx and syy else None
    gstat = {"refs": len(refs), "govRefs": gov_refs, "blocRefs": bloc_refs, "texts": len(tset),
             "govTexts": sum(text_origin[t][0] == "g" for t in tset),
             "blocPlus": round(sum(sg * gv > 0 for sg, gv in voted) / len(voted), 2) if voted else None, "r": r}
    print(f"    {ax['k']} : {gov_refs}/{len(refs)} scrutins sur des textes du Gouvernement ({gstat['govTexts']}/{len(tset)} textes), "
          f"bloc côté « {ax.get('plus', '+')} » {gstat['blocPlus']}, r(proximité gouvernement) = {r}")
    axes_out.append({"k": ax["k"], "n": ax["n"], "def": ax["def"], "refs": refs, "groups": ax_scores, "deps": dep_scores, "gstat": gstat,
                     "plus": ax.get("plus", ""), "minus": ax.get("minus", ""), "side": ax.get("side", "right"),
                     "texts": len(used)})
    print(f"  axe {ax['n']} : {len(refs)} scrutins sur {len(used)} textes "
          f"({sum(r[2] == 't' for r in refs)} textes, {sum(r[2] == 'm' for r in refs)} motions, {sum(r[2] == 's' for r in refs)} suppressions)")
    missing = [rx for sg, rx in ax["texts"] if not any(re.search(rx, t, re.I) for t in used)]
    if missing:
        print("    sans scrutin exploitable :", missing)

# ---------- Le jeu « Tu votes comme qui ? » (quiz.py) ----------
import quiz as QZ  # noqa: E402

num_to_j = {n: j for j, n in enumerate(S["n"])}
CODE = {1: "P", -1: "C", 0: "A"}
quiz_out = []
for q in QZ.QUIZ:
    j = num_to_j.get(q["n"])
    if j is None:
        print(f"  quiz : scrutin {q['n']} introuvable, question ignorée", file=sys.stderr)
        continue
    # Vote de chaque député (même ordre que la liste des députés) : P pour, C contre, A abstention, . absent
    votes = "".join(CODE[d["votes"][j][0]] if j in d["votes"] else "." for d in deps)
    raw = raw_scrutins[j]
    dc = raw["syntheseVote"]["decompte"]
    quiz_out.append({"j": j, "n": q["n"], "q": q["q"], "sens": q["sens"], "axes": q["axes"], "v": votes,
                     # Intitulé officiel, verbatim (espaces normalisés seulement)
                     "titre": re.sub(r"\s+", " ", raw["titre"]).strip(),
                     "date": raw["dateScrutin"], "sort": raw["sort"]["code"],
                     "dc": [int(dc.get("pour") or 0), int(dc.get("contre") or 0), int(dc.get("abstentions") or 0)],
                     "dossier": "" if q.get("dossier") == "none" else q.get("dossier") or (text_origin[S["tx"][j]][2] if S["tx"][j] >= 0 else ""),
                     # origine du texte (g Gouvernement, a député, s Sénat) et groupe de l'auteur, pour le tirage équilibré
                     "o": text_origin[S["tx"][j]][:2] if S["tx"][j] >= 0 else ["?", None],
                     "topic": q.get("topic") or (text_origin[S["tx"][j]][2] if S["tx"][j] >= 0 else str(q["n"])),
                     "contenu": q["contenu"], "pour": q["pour"], "contre": q["contre"], "suite": q["suite"],
                     "sources": q["sources"], "consulte": QZ.CONSULTED})
print(f"  quiz : {len(quiz_out)} questions")

data = {
    "quiz": quiz_out,
    "axes": axes_out,
    "epoch": EPOCH.isoformat(),
    "groups": [{"k": k, "n": n, "c": c, "seats": seats[i]} for i, (k, n, c) in enumerate(GROUPS)],
    "themes": [{"k": k, "n": l} for k, l in T.labels()],
    "texts": texts,
    "textOrigin": text_origin,
    "S": S,
    "deputies": [{
        "n": d["name"], "f": 1 if d["civ"].startswith("Mme") else 0, "g": d["group"], "dep": d["dept"], "c": d["circo"],
        "nv": len(d["votes"]), "part": d["part"], "loyal": d["loyal"], "ga": d["gagree"], "gov": d["gov"],
        "close": d["close"], "closeOut": d["closeOut"], "far": d["far"], "active": 0 if d["end"] else 1,
    } for d in deps],
    "maps": maps,
    "gmaps": gmaps,
    "explained": explained,
}
# ---------- Jeu « Présidentielle 2027 » (quiz2027.json -> site/data2027.js) ----------
Q27 = os.path.join(HERE, "quiz2027.json")
OUT27 = os.path.join(os.path.dirname(OUT), "data2027.js")
if os.path.exists(Q27):
    q27 = json.load(open(Q27, encoding="utf-8"))
    pkeys = {p["k"] for p in q27["props"]}
    for ck, pos in q27["positions"].items():
        for pk, cell in pos.items():
            assert pk in pkeys, f"quiz2027 : proposition inconnue {pk} ({ck})"
            assert cell["p"] in ("pour", "contre", "nuance"), f"quiz2027 : position invalide {ck}/{pk}"
            assert cell["s"] and all(x in q27["sources"] for x in cell["s"]), f"quiz2027 : source manquante {ck}/{pk}"
    for c in q27["candidates"]:
        c["known"] = len(q27["positions"].get(c["k"], {}))
    q27.pop("_lisez-moi", None)
    os.makedirs(os.path.dirname(OUT27), exist_ok=True)
    with open(OUT27, "w", encoding="utf-8") as fh:
        fh.write("window.DATA27=")
        json.dump(q27, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";")
    print("  2027 : " + ", ".join(f"{c['n']} {c['known']}/{len(q27['props'])}" for c in q27["candidates"]))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("window.DATA=")
    json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
    fh.write(";")
print(f"site/data.js : {os.path.getsize(OUT) // 1024} Ko")


# Empreinte de data.js dans la page : évite qu'un navigateur garde un vieux fichier en cache
import hashlib  # noqa: E402
_digest = hashlib.sha1(open(OUT, "rb").read()).hexdigest()[:10]
_page = os.path.join(os.path.dirname(OUT), "index.html")
if os.path.exists(_page):
    _src = open(_page, encoding="utf-8").read()
    _new = re.sub(r'src="data\.js(\?v=[\w-]+)?"', f'src="data.js?v={_digest}"', _src)
    if _new != _src:
        open(_page, "w", encoding="utf-8").write(_new)
if os.path.exists(OUT27):
    _page27 = os.path.join(os.path.dirname(OUT), "2027.html")
    _d27 = hashlib.sha1(open(OUT27, "rb").read()).hexdigest()[:10]
    if os.path.exists(_page27):
        _src = open(_page27, encoding="utf-8").read()
        _new = re.sub(r'src="data2027\.js(\?v=[\w-]+)?"', f'src="data2027.js?v={_d27}"', _src)
        if _new != _src:
            open(_page27, "w", encoding="utf-8").write(_new)
