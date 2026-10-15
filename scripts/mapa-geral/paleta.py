#!/usr/bin/env python3
# E4.1: mede a paleta do vídeo em 6 mapas de épocas diferentes e grava .cache/v2/paleta.json (evidência dos limiares
# de rotular.py). Uso: PYTHONPATH=~/.cache/mapa-biblia-lib/lib python3 scripts/mapa-geral/paleta.py
import json, os, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/.cache/mapa-biblia-lib/lib"))
import numpy as np
import cv2

CACHE = os.environ.get("MAPA_GERAL_CACHE") or os.path.join(AQUI, ".cache")
V2 = os.path.join(CACHE, "v2")
anos = json.load(open(os.path.join(V2, "anos.json")))
saida = {"mapas": {}, "limiares": {"borda_plana": 8, "mar_L1": 24, "branco_min_canal": 246, "texto_preto_max": 80,
                                      "texto_branco_min": 235}}
for ano in (1200, 584, -31, -999, -1598, -1914):
    k = str(anos[str(ano)]["mapa"])
    im = cv2.imread(os.path.join(V2, "mapas", f"{k}.png"))[:, :, ::-1].astype(np.int32)
    reg = cv2.imread(os.path.join(V2, "rotulos", f"{k}.png"), cv2.IMREAD_UNCHANGED)
    info = json.load(open(os.path.join(V2, "rotulos", f"{k}.json")))["regioes"]
    mar = im[reg == 0]
    mar = mar[np.abs(mar - [216, 225, 237]).sum(axis=1) <= 24]
    brancos = [r for r in info if r["tipo"] == "sem-dono"]
    cremes = [r["cor"] for r in info if r["tipo"] == "estado" and min(r["cor"]) >= 225]
    escuros = [r["cor"] for r in info if max(r["cor"]) <= 100]
    gray = np.abs(np.diff(im, axis=1)).max(axis=2) > 8
    saida["mapas"][str(ano)] = {
        "mar_mediana": np.median(mar, axis=0).tolist() if len(mar) else None,
        "mar_desvio_max": float(mar.std(axis=0).max()) if len(mar) else None,
        "sem_dono_mediana": np.median(np.concatenate([im[reg == r["r"]] for r in brancos]), axis=0).tolist() if brancos else None,
        "cremes": cremes, "escuros": escuros,
        "pixels_texto_preto": int(((im.max(axis=2) <= 60)).sum()),
    }
json.dump(saida, open(os.path.join(V2, "paleta.json"), "w"), indent=1)
print(json.dumps(saida["mapas"], indent=0)[:1500])
