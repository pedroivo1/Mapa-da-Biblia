#!/usr/bin/env python3
# E3 do mapa geral (v2): para cada mapa distinto, a transformação exata pixel -> (lon, lat) do vídeo.
# Uso (na raiz do repositório):
#   PYTHONPATH=~/.cache/mapa-biblia-lib/lib python3 scripts/mapa-geral/calibrar.py
# Lê .cache/v2/mapas.json e .cache/v2/mapas/<id>.png (E2) e frontend/mapa/mundo.json (costa).
# Grava .cache/v2/calibracao.json: {"trechos": [...], "por_mapa": {"<id>": {"S","X0","Y0","falha","mediana_px","p90_px"}}}.
#
# Modelo (cilíndrica de Miller, medida no vídeo: com Mercator o ajuste pedia escala vertical 0,98 e deixava 2× mais
# erro; com Miller a razão vertical/horizontal sai 0,999; quadro de 1920×960):
#     u = (lon + 180) * S - X0            (px)
#     v = (miller(80) - miller(lat)) * S - Y0 (px),  miller(lat) = deg(1,25 · ln tan(45° + 0,4·lat))
# O mundo pode aparecer repetido (±360° de longitude) nos quadros que passam do antimeridiano.
# Método: a máscara de terra do quadro (tudo que não é a cor do mar) é comparada com a terra de mundo.json
# renderizada com (S, X0, Y0); descida de coordenadas com passo decrescente minimiza os pixels discordantes.
# Cada mapa é ajustado sozinho (a partir do vizinho anterior no tempo, ou da tabela da v1); os "trechos" são os
# grupos de mapas consecutivos com a mesma calibração (diferença <= 0,2 %).
import json, math, os, sys
from concurrent.futures import ProcessPoolExecutor

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/.cache/mapa-biblia-lib/lib"))
import numpy as np
import cv2

RAIZ = os.path.normpath(os.path.join(AQUI, "..", ".."))
CACHE = os.environ.get("MAPA_GERAL_CACHE") or os.path.join(AQUI, ".cache")
V2 = os.path.join(CACHE, "v2")
MUNDO = os.path.join(RAIZ, "frontend", "mapa", "mundo.json")
H, W = 960, 1920
MAR_BGR = np.array([237, 225, 216], np.int32)   # mar do vídeo (medido: RGB 216,225,237)
LIM_MAR = 24                                      # distância L1 máxima à cor do mar
LAT_TOPO = 80.0


def merc(lat):
    """y da cilíndrica de Miller em graus (o nome é histórico: a v1 supunha Mercator)."""
    lat = np.clip(lat, -85.0, 85.0)
    return 1.25 * np.degrees(np.log(np.tan(np.pi / 4 + 0.4 * np.radians(lat))))


def merc_puro(lat):
    return np.degrees(np.log(np.tan(np.pi / 4 + np.radians(np.clip(lat, -85.0, 85.0)) / 2)))


# tabela da v1 (quadros de 1280 px, supunha Mercator), ×1,5 para 1920 px: (S, X0, Y0). Y0 é convertido para Miller
# mantendo a linha da latitude 40 no mesmo pixel.
def _iniciais():
    out = []
    for S, X0, Y0 in [(11.28, 2174, 919), (8.40, 1397, 577), (7.049, 1045, 419), (4.673, 248, 203), (3.60, 16, 87)]:
        S, X0, Y0 = S * 1.5, X0 * 1.5, Y0 * 1.5
        v40 = (merc_puro(80.0) - merc_puro(40.0)) * S - Y0
        out.append((S, X0, (merc(80.0) - merc(40.0)) * S - v40))
    return out


INICIAIS = _iniciais()


# Dos 29 lagos de mundo.json o vídeo só desenha os Grandes Lagos (conferido pela cor do mar no centro de cada lago em
# 7 mapas): Baikal, Vitória, Balkhash etc. são terra no vídeo. Carvar os outros piora o ajuste (discordância 10 % maior).
LAGOS_NO_VIDEO = {"lago-erie", "lago-michigan", "lago-superior", "lago-huron", "lago-ontario"}


def carregar_mundo():
    d = json.load(open(MUNDO))
    aneis, lagos = [], []
    for f in d["fundo"]:
        if f["tipo"] == "terra":
            aneis += f["aneis"]
        elif f["tipo"] == "mar" and f["id"] in LAGOS_NO_VIDEO:
            lagos.append(f["pontos"])
    def prep(a):
        a = np.asarray(a, np.float64)
        return np.stack([a[:, 0] + 180.0, merc(LAT_TOPO) - merc(a[:, 1])], axis=1)
    return [prep(a) for a in aneis], [prep(a) for a in lagos]


def renderizar(terra, lagos, S, X0, Y0, cobertura=None):
    """Máscara de terra (uint8 0/255) 960×1920 com mundo.json em (S, X0, Y0); anéis em par-ímpar; cópias ±360°."""
    img = np.zeros((H, W), np.uint8)
    for k in (-1, 0, 1):
        dx = k * 360.0
        pol = []
        for a in terra:
            x = (a[:, 0] + dx) * S - X0
            if x.max() < -2 or x.min() > W + 2:
                continue
            y = a[:, 1] * S - Y0
            if y.max() < -2 or y.min() > H + 2:
                continue
            pol.append(np.round(np.stack([x, y], axis=1) * 16).astype(np.int32))
        if pol:
            tmp = np.zeros_like(img)
            cv2.fillPoly(tmp, pol, 255, lineType=cv2.LINE_8, shift=4)
            img = cv2.bitwise_xor(img, tmp)
    pol = []
    for k in (-1, 0, 1):
        for a in lagos:
            x = (a[:, 0] + k * 360.0) * S - X0
            if x.max() < -2 or x.min() > W + 2:
                continue
            pol.append(np.round(np.stack([x, a[:, 1] * S - Y0], axis=1) * 16).astype(np.int32))
    if pol:
        cv2.fillPoly(img, pol, 0, lineType=cv2.LINE_8, shift=4)
    return img


def mascara_terra(im):
    """Terra do vídeo = tudo que não é cor de mar. Devolve (terra 0/255, validos 0/1) sem o ornamento do ano."""
    d = np.abs(im.astype(np.int32) - MAR_BGR[None, None, :]).sum(axis=2)
    terra = ((d > LIM_MAR).astype(np.uint8)) * 255
    valido = np.ones((H, W), np.uint8)
    valido[815:945, 700:1100] = 0          # ornamento do ano (a posição horizontal varia; faixa generosa)
    return terra, valido


def regiao_valida(S, Y0):
    """Linhas do quadro cuja latitude está dentro de mundo.json (lat -56..78): evita comparar onde ele não cobre."""
    y_top = (merc(LAT_TOPO) - merc(78.0)) * S - Y0
    y_bot = (merc(LAT_TOPO) - merc(-56.0)) * S - Y0
    return int(max(0, math.ceil(y_top))), int(min(H, math.floor(y_bot)))


def custo(terra_v, valido, terra, lagos, p):
    S, X0, Y0 = p
    r = renderizar(terra, lagos, S, X0, Y0)
    y0, y1 = regiao_valida(S, Y0)
    if y1 - y0 < 0.4 * H:
        return 1e9      # a calibração deixaria menos de 40 % do quadro dentro da cobertura de mundo.json
    dif = (r[y0:y1] != terra_v[y0:y1]) & (valido[y0:y1] > 0)
    return float(dif.sum()) * H / (y1 - y0)     # normalizado para a altura inteira (regiões diferentes comparáveis)


def ajustar(terra_v, valido, terra, lagos, p0, dX0=8.0):
    """Descida de coordenadas em (S, X0, Y0). A mudança de escala mantém fixo o ponto do mundo sob o centro do
    quadro (senão uma variação de 0,3 % de S desloca a costa em ~10 px e a descida nunca aceita o passo: a v1 desta
    etapa parou 0,3 % abaixo do ótimo). Passos: X0/Y0 dX0 px; S 0,05 % por px de dX0; caem pela metade até 0,03 px."""
    cx, cy = W / 2.0, H / 2.0

    def com_escala(p, f):
        S = p[0] * f
        return [S, (cx + p[1]) / p[0] * S - cx, (cy + p[2]) / p[0] * S - cy]

    p = list(p0)
    c = custo(terra_v, valido, terra, lagos, p)
    dS, dX = 0.0005 * dX0, dX0
    while dX > 0.03:
        melhorou = True
        while melhorou:
            melhorou = False
            for i in (0, 1, 2):
                for sinal in (1, -1):
                    if i == 0:
                        q = com_escala(p, 1.0 + sinal * dS)
                    else:
                        q = list(p)
                        q[i] += sinal * dX
                    cq = custo(terra_v, valido, terra, lagos, q)
                    if cq < c - 0.5:
                        p, c, melhorou = q, cq, True
                        break
        dS /= 2
        dX /= 2
    return p, c


def residuo_costa(terra_v, valido, terra_r, p):
    """Distância (px) da borda de terra do vídeo à borda de mundo.json: (mediana, p90, n)."""
    S, X0, Y0 = p
    y0, y1 = regiao_valida(S, Y0)
    kern = np.ones((3, 3), np.uint8)
    borda_v = cv2.morphologyEx(terra_v, cv2.MORPH_GRADIENT, kern) > 0
    borda_r = cv2.morphologyEx(terra_r, cv2.MORPH_GRADIENT, kern) > 0
    dist = cv2.distanceTransform((~borda_r).astype(np.uint8), cv2.DIST_L2, 3)
    m = np.zeros((H, W), bool)
    m[y0 + 3:y1 - 3, 3:W - 3] = True
    m &= valido > 0
    sel = borda_v & m
    d = dist[sel]
    if len(d) < 100:
        return None, None, 0, 1.0
    # costa do vídeo a mais de 12 px da de mundo.json é diferença de forma (ilhas, lagos e detalhes que o mundo.json
    # não tem), não de alinhamento: fica fora da mediana e do p90, e a fração fora é registrada
    perto = d[d <= 12.0]
    fora = 1.0 - len(perto) / len(d)
    if len(perto) < 100:
        return None, None, int(len(d)), fora
    return float(np.median(perto)), float(np.percentile(perto, 90)), int(len(d)), float(fora)


def tarefa(args):
    ids, quadros, mapas_dir = args
    terra, lagos = carregar_mundo()
    saida = {}
    anterior = None
    for k, q in zip(ids, quadros):
        im = cv2.imread(os.path.join(mapas_dir, f"{k}.png"))
        if im is None:
            continue
        terra_v, valido = mascara_terra(im)
        area0 = float(((valido > 0)).sum())
        melhor = None
        if anterior is not None:
            p, cu = ajustar(terra_v, valido, terra, lagos, anterior, dX0=1.0)
            if cu / area0 < 0.04:
                melhor = (p, cu)
        if melhor is None:
            # sem vizinho bom (começo, zoom, fade): tenta cada calibração inicial da tabela e ajusta as duas melhores
            cands = ([anterior] if anterior is not None else []) + list(INICIAIS)
            pontuados = sorted((custo(terra_v, valido, terra, lagos, c_), c_) for c_ in cands)
            for _, c_ in pontuados[:2]:
                p, cu = ajustar(terra_v, valido, terra, lagos, c_)
                if melhor is None or cu < melhor[1]:
                    melhor = (p, cu)
        p, cu = melhor
        anterior = tuple(p)
        r = renderizar(terra, lagos, *p)
        med, p90, n, fora = residuo_costa(terra_v, valido, r, p)
        y0, y1 = regiao_valida(p[0], p[2])
        area = float((valido > 0).sum()) or 1.0
        saida[k] = {"S": round(p[0], 4), "X0": round(p[1], 2), "Y0": round(float(p[2]), 2),
                    "falha": round(cu / area, 5), "mediana_px": med, "p90_px": p90, "n_costa": n, "fora": round(fora, 4)}
    return saida


def main():
    mapas = json.load(open(os.path.join(V2, "mapas.json")))
    ids = sorted(mapas, key=lambda k: mapas[k]["quadro"])
    pedacos = np.array_split(np.arange(len(ids)), 16)
    tarefas = [([ids[i] for i in c], [mapas[ids[i]]["quadro"] for i in c], os.path.join(V2, "mapas")) for c in pedacos if len(c)]
    por_mapa = {}
    with ProcessPoolExecutor(8) as ex:
        for r in ex.map(tarefa, tarefas):
            por_mapa.update(r)
            print("mapas calibrados:", len(por_mapa), flush=True)
    json.dump({"trechos": montar_trechos(ids, por_mapa), "por_mapa": por_mapa}, open(os.path.join(V2, "calibracao.json"), "w"))


def montar_trechos(ids, por_mapa):
    """Trechos: mapas consecutivos (no tempo) com S, X0, Y0 iguais (S 0,2 %; X0 e Y0 até 4 px)."""
    trechos, atual = [], None
    for k in ids:
        c = por_mapa.get(k)
        if not c:
            continue
        if atual and abs(c["S"] / atual["S"] - 1) <= 0.002 and abs(c["X0"] - atual["X0"]) <= 4 and abs(c["Y0"] - atual["Y0"]) <= 4:
            atual["ids"].append(k)
        else:
            atual = {"S": c["S"], "X0": c["X0"], "Y0": c["Y0"], "ids": [k]}
            trechos.append(atual)
    print("trechos:", len(trechos), [(t["S"], t["X0"], t["Y0"], len(t["ids"])) for t in trechos if len(t["ids"]) > 20])
    return [{"S": t["S"], "X0": t["X0"], "Y0": t["Y0"], "n": len(t["ids"]), "ids": [t["ids"][0], t["ids"][-1]]} for t in trechos]


if __name__ == "__main__":
    main()
