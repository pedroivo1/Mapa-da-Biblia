#!/usr/bin/env python3
# Confere os 7 casos apontados pelo usuário em 2026-10-16 numa variante (E6/E7u/E7 com o mesmo nome):
#   python3 scripts/mapa-geral/experimentos/casos_usuario.py <variante>     (ex.: e7c)
# Para cada caso, os pontos devem cair na MESMA entidade final (peças unidas) e o nome lido é mostrado.
import json, os, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/.cache/mapa-biblia-lib/lib"))
sys.path.insert(0, os.path.join(AQUI, ".."))
import cv2, cache
from calibrar import merc

var = sys.argv[1]
os.environ["MAPA_GERAL_EXP"] = var
V2 = cache.V2
et7, et6, et4 = cache.Etapa("e7"), cache.Etapa("e6"), cache.Etapa("e4e")
nl = json.load(open(et7.caminho("nomes-lidos", ".json", var)))
ent = json.load(open(et6.caminho("entidades", ".json", nl["e6"]["variante"])))
etv = cache.Etapa(nl["e6"]["fonte"])
var_v = nl["e6"]["variante"] if nl["e6"]["variante"] in etv.m["variantes"] else etv.m["aprovada"]
anos = json.load(open(os.path.join(V2, "anos.json")))
cal = json.load(open(cache.calibracao()))["por_mapa"] if hasattr(cache, "calibracao") else json.load(open(os.path.join(V2, "calibracao.json")))["por_mapa"]
ordem = [int(a) for a in anos]; pos = {a: i for i, a in enumerate(ordem)}

def corrida(ano):
    for c in ent["por_ano"]:
        if pos[c[0]] <= pos[ano] <= pos[c[1]]:
            return c

def final_em(ano, lon, lat):
    c = corrida(ano); p = cal[c[2]]
    reg = cv2.imread(et4.caminho(c[2], ".png"), cv2.IMREAD_UNCHANGED)
    u = int(round((lon + 180) * p["S"] - p["X0"])); v = int(round((merc(80.0) - merc(lat)) * p["S"] - p["Y0"]))
    r = str(int(reg[v, u]))
    vv = json.load(open(etv.caminho(c[2], ".json", var_v))).get("unidas", {})
    e = c[3].get(vv.get(r, r))
    f = nl["entidades"][e]["final"] if e else None
    nomes = [t[2] for t in nl["finais"][f]["trechos"] if pos[t[0]] <= pos[ano] <= pos[t[1]]] if f else []
    return f, nomes

CASOS = [
 ("Arábia Saudita 2025 (norte/sul)", -2025, [(42, 27), (46, 20)]),
 ("Afeganistão 2025 (norte/sul)", -2025, [(66, 36), (65, 32)]),
 ("Paquistão 2025 (norte/sul)", -2025, [(72, 32), (67, 26)]),
 ("Espanha 2025 (norte/sul)", -2025, [(-4, 41), (-4, 37.5)]),
 ("Vietnã 2025 (norte/centro/sul)", -2025, [(105.5, 21.5), (108.5, 15.5), (106, 10.5)]),
 ("Laos 2025", -2025, [(103, 18.5), (105.5, 16)]),
 ("Egito 2500 a.C. (delta/meio/sul)", 2500, [(31, 30.2), (31.5, 27), (32.6, 24.5)]),
 ("Ebla 2500 a.C.", 2500, [(38.2, 36.8)]),
 ("Kish / Uruk / Ur / Lagash 2500 a.C.", 2500, [(44.5, 32.5), (45.0, 31.3), (46.1, 30.9), (46.4, 31.4)]),
 ("Síria / Líbano / Israel / Jordânia / Iraque 2025", -2025, [(38, 35), (35.8, 34), (35, 31.5), (36.5, 31), (43.5, 33)]),
]
for nome, ano, pts in CASOS:
    res = [final_em(ano, lon, lat) for lon, lat in pts]
    unidos = len({r[0] for r in res}) == 1
    print(f"{nome}: " + ("UMA entidade" if unidos else f"{len({r[0] for r in res})} entidades") + " -> " + "; ".join(f"{f} {n}" for f, n in res))
