#!/usr/bin/env python3
# Ferramenta de conferência (não gera dados): folha de contato de um quadro-chave.
# À esquerda o quadro original recortado numa região; à direita os estados segmentados com o número de cada um
# e, abaixo, a legenda (número, cor, centro, nome lido pelo OCR e id dado por nomes.json, se houver).
# Uso:  PYTHONPATH=<lib> python3 scripts/mapa-geral/folha.py <ano> [lon0 lat0 lon1 lat1] [saida.png]
#       (ano: a.C. positivo, d.C. negativo; região padrão: -12 8 75 52 = Oriente Médio e Mediterrâneo)
import json, math, os, sys
import cv2
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from segmentar import merc

CACHE = os.path.join(AQUI, ".cache")


def arquivo_ano(ano):
    return os.path.join(CACHE, "estados", ("a%d" % ano) if ano >= 0 else ("d%d" % -ano)) + ".json"


def para_pixel(cal, lon, lat):
    S = cal["S"]
    ytopo = merc(80.0)
    X = (lon + 180.0) * S
    Y = (ytopo - merc(lat)) * S
    return X - cal["X0"], Y - cal["Y0"]


def main():
    ano = int(sys.argv[1])
    reg = [float(v) for v in sys.argv[2:6]] if len(sys.argv) >= 6 else [-12, 8, 75, 52]
    saida = sys.argv[6] if len(sys.argv) >= 7 else sys.argv[-1] if sys.argv[-1].endswith(".png") else "/tmp/folha.png"
    d = json.load(open(arquivo_ano(ano)))
    cal = d["cal"]
    img = cv2.imread(os.path.join(CACHE, "quadros", "%04d.jpg" % d["segundo"]))
    x0, y1 = para_pixel(cal, reg[0], reg[1])
    x1, y0 = para_pixel(cal, reg[2], reg[3])
    x0, x1, y0, y1 = int(max(0, x0)), int(min(img.shape[1], x1)), int(max(0, y0)), int(min(img.shape[0], y1))
    rec = img[y0:y1, x0:x1].copy()
    esc = 2
    rec = cv2.resize(rec, None, fx=esc, fy=esc, interpolation=cv2.INTER_NEAREST)
    painel = np.full_like(rec, 255)
    nomes = {}
    try:
        nomes = json.load(open(os.path.join(AQUI, ".cache", "ids-%s.json" % ano)))
    except Exception:
        pass
    linhas = []
    for i, e in enumerate(sorted(d["estados"], key=lambda e: -e["area_px"])):
        pts = np.array([[(para_pixel(cal, p[0], p[1])[0] - x0) * esc, (para_pixel(cal, p[0], p[1])[1] - y0) * esc]
                        for p in e["anel"]], np.int32)
        cor = (int(e["cor"][2]), int(e["cor"][1]), int(e["cor"][0]))
        cv2.fillPoly(painel, [pts], cor)
        cv2.polylines(painel, [pts], True, (60, 60, 60), 1)
        cx, cy = pts[:, 0].mean(), pts[:, 1].mean()
        if 0 <= cx < painel.shape[1] and 0 <= cy < painel.shape[0]:
            cv2.putText(painel, str(i), (int(cx) - 6, int(cy) + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)
            cv2.putText(painel, str(i), (int(cx) - 6, int(cy) + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        xs = [p[0] for p in e["anel"]]; ys = [p[1] for p in e["anel"]]
        linhas.append("%2d rgb%s c=(%.0f,%.0f) a=%dpx %s %s" % (
            i, tuple(e["cor"]), sum(xs) / len(xs), sum(ys) / len(ys), e["area_px"], e.get("nome_en", ""),
            nomes.get(str(i), "")))
    topo = np.hstack([rec, painel])
    leg_h = 16 * min(len(linhas), 60) + 10
    leg = np.full((leg_h, topo.shape[1], 3), 255, np.uint8)
    for k, t in enumerate(linhas[:60]):
        col = k // 30
        cv2.putText(leg, t[:78], (6 + col * (topo.shape[1] // 2), 14 + 16 * (k % 30)), cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                    (0, 0, 0), 1)
    leg = leg[: 16 * 30 + 10]
    cv2.imwrite(saida, np.vstack([topo, leg]))
    print(saida, "ano", ano, "estados", len(d["estados"]), "escore", d["cal"]["escore"])


if __name__ == "__main__":
    main()
