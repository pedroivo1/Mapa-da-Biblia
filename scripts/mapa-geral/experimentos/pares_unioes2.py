#!/usr/bin/env python3
# Avalia um arquivo de uniões (.cache/v2/e7/unioes-<textos>-u<versão>.json) contra pares.json sem refazer a E6:
# erradas = par "estados diferentes" que ficou no mesmo grupo; soltos = par "mesmo estado" em grupos diferentes.
#   python3 scripts/mapa-geral/experimentos/pares_unioes2.py <arquivo de uniões>
import json, os, sys, cv2
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/.cache/mapa-biblia-lib/lib")); sys.path.insert(0, os.path.join(AQUI, ".."))
import cache
from calibrar import merc
un = json.load(open(sys.argv[1]))["mapas"]
pares = json.load(open(os.path.join(AQUI, "..", "pares.json")))["pares"]
anos = json.load(open(os.path.join(cache.V2, "anos.json")))
cal = json.load(open(cache.calibracao()))["por_mapa"]
et4 = cache.Etapa("e4e")
erradas, soltos = [], []
for pr in pares:
    k = str(anos[str(pr["ano"])]["mapa"]); p = cal[k]
    reg = cv2.imread(et4.caminho(k, ".png"), cv2.IMREAD_UNCHANGED)
    raiz = {}
    for a, b, _ in un.get(k, []):
        raiz[b] = a
    def r_(x):
        while x in raiz: x = raiz[x]
        return x
    rs = []
    for lon, lat in (pr["ponto_a"], pr["ponto_b"]):
        u = int(round((lon + 180) * p["S"] - p["X0"])); v = int(round((merc(80.0) - merc(lat)) * p["S"] - p["Y0"]))
        rs.append(r_(int(reg[v, u])))
    if pr["mesmo_estado"] and rs[0] != rs[1]: soltos.append(pr["id_folha"])
    if not pr["mesmo_estado"] and rs[0] == rs[1]: erradas.append(pr["id_folha"])
print(f"erradas={len(erradas)} {erradas}; soltos={len(soltos)} {soltos}; uniões={sum(len(v) for v in un.values())}")
