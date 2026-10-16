"""Télécharge l'open data de l'Assemblée nationale (17e législature).

    python3 scripts/fetch.py <dossier_brut>

- Scrutins.json.zip : un fichier JSON par scrutin public, avec le vote nominatif ;
- AMO30 (historique acteurs/mandats/organes) : députés, groupes politiques, y compris
  les députés partis en cours de législature.
Les archives sont décompressées dans <dossier_brut>/scrutins et <dossier_brut>/amo.
"""
import os
import sys
import urllib.request
import zipfile

BASE = "https://data.assemblee-nationale.fr/static/openData/repository/17"
FILES = {
    "scrutins": BASE + "/loi/scrutins/Scrutins.json.zip",
    "amo": BASE + "/amo/tous_acteurs_mandats_organes_xi_legislature/AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip",
}


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "raw"
    os.makedirs(out, exist_ok=True)
    for name, url in FILES.items():
        path = os.path.join(out, name + ".zip")
        print("téléchargement", url)
        req = urllib.request.Request(url, headers={"User-Agent": "votes-assemblee-viz/1.0"})
        with urllib.request.urlopen(req, timeout=300) as r, open(path, "wb") as fh:
            fh.write(r.read())
        dest = os.path.join(out, name)
        with zipfile.ZipFile(path) as z:
            for member in z.namelist():  # protection contre les chemins sortant du dossier
                target = os.path.realpath(os.path.join(dest, member))
                if not target.startswith(os.path.realpath(dest) + os.sep):
                    raise RuntimeError(f"chemin suspect dans l'archive : {member}")
            z.extractall(dest)
        print(f"  {name} : {sum(len(f) for _, _, f in os.walk(dest))} fichiers")


if __name__ == "__main__":
    main()
