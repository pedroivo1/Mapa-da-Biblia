#!/usr/bin/env python3
# Amostras fixas de mapas distintos para o ciclo de desenvolvimento (docs/mapa-geral-incremental.md):
#   rapida (~30): os 12 anos da revisão, os mapas dos pares rotulados à mão (pares.json), dos casos de referência
#                 (casos.json), de casos difíceis já vistos (Elam 1200 a.C., Bengala 1452, Ahmednagar 1602...), o
#                 primeiro e o último de cada trecho de enquadramento e os mapas de transição de zoom.
#   media (~200): a rápida + sorteio estratificado por trecho de enquadramento (semente fixa 42).
# Uso: PYTHONPATH=~/.cache/mapa-biblia-lib/lib python3 scripts/mapa-geral/amostras.py  -> .cache/v2/amostras.json (da cache ativa;
# os ids de mapa mudam quando a E2 é refeita). Os scripts leem por cache.amostras(), que cai no scripts/mapa-geral/amostras.json antigo.
import json, os, random, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import cache
V2 = os.path.join(os.environ.get("MAPA_GERAL_CACHE") or os.path.join(AQUI, ".cache"), "v2")
anos = json.load(open(os.path.join(V2, "anos.json")))
mapas = json.load(open(os.path.join(V2, "mapas.json")))
cal = json.load(open(cache.calibracao()))


def m(ano):
    return str(anos[str(ano)]["mapa"])


REVISAO = [2000, 1200, 584, -31, -326, -700, -999, -1148, -1598, -1799, -1914, -2022]
DIFICEIS = [1200, -1452, -835, -687, -1602, -1502, -824, -1927]   # Elam, K. de Bengala, Soma., C./Bav., Ahmed., Polônia, Frígia, Letônia
rap = [m(a) for a in REVISAO]
rap += [m(p["ano"]) for p in json.load(open(os.path.join(AQUI, "pares.json")))["pares"]]
rap += [m(c["ano"]) for c in json.load(open(os.path.join(AQUI, "casos.json")))["casos"]]
rap += [m(a) for a in DIFICEIS] + [m(2350)]      # (2350 a.C.: mapa 26 na E2 de 2026-10-15)
ordem = sorted(mapas, key=lambda k: mapas[k]["quadro"])
# primeiro e último mapa de cada trecho de enquadramento e os mapas de transição de zoom (fora dos trechos longos)
longos = [t for t in cal["trechos"] if t["n"] >= 20]
for t in longos:
    rap += list(t["ids"])
dentro = set()
for t in longos:
    a, b = t["ids"]
    dentro |= {k for k in ordem if mapas[a]["quadro"] <= mapas[k]["quadro"] <= mapas[b]["quadro"]}
rap += [k for k in ordem if k not in dentro]
rap = list(dict.fromkeys(rap))
random.seed(42)
media = list(rap)
alvo = 200
trechos = [t for t in cal["trechos"]]
total = sum(t["n"] for t in trechos)
for t in trechos:
    a, b = t["ids"]
    grupo = [k for k in ordem if mapas[a]["quadro"] <= mapas[k]["quadro"] <= mapas[b]["quadro"] and k not in media]
    n = max(1, round((alvo - len(rap)) * t["n"] / total))
    media += random.sample(grupo, min(n, len(grupo)))
media = list(dict.fromkeys(media))
saida = {"_ajuda": "Gerado por amostras.py; ids de mapas distintos (.cache/v2/mapas.json).",
         "rapida": {"ids": rap}, "media": {"ids": media}}
saida["_ajuda"] = "Gerado por amostras.py; ids de mapas distintos desta cache (mapas.json). Lido por cache.amostras()."
json.dump(saida, open(os.path.join(V2, "amostras.json"), "w"), indent=1)
print("rapida", len(rap), "media", len(media), "->", os.path.join(V2, "amostras.json"))
