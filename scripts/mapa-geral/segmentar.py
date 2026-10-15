#!/usr/bin/env python3
# Etapa 3 do mapa geral: separa os estados de um quadro por cor e devolve os contornos em longitude/latitude.
# Cada estado é uma mancha de cor chapada sobre o mar (azul-acinzentado) e a terra sem dono (branco).
# Uso como módulo:  from segmentar import segmentar_quadro
import math, os
import cv2
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
MAR = np.array([237, 228, 218], np.int32)        # BGR
BRANCO = np.array([255, 255, 255], np.int32)
PASSO_COR = 12                                    # quantização das cores (níveis de 0..255)
TOL_COR = 44                                      # distância L1 para pertencer à mesma cor
AREA_MIN = 28                                     # px² (em quadros de 1280 px) para contar como estado


def pixel_para_lonlat(cal, u, v):
    """cal: {proj, S, X0, Y0}. (u, v) em pixels do quadro de 1280 px."""
    X = cal["X0"] + u
    Y = cal["Y0"] + v
    lon = -180.0 + X / cal["S"]
    ytopo = merc(80.0) if cal["proj"] == "mercator" else 80.0
    y = ytopo - Y / cal["S"]
    lat = inv_merc(y) if cal["proj"] == "mercator" else y
    return lon, lat


def merc(lat):
    return math.degrees(math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))


def inv_merc(y):
    return math.degrees(2 * math.atan(math.exp(math.radians(y))) - math.pi / 2)


def cores_do_quadro(img):
    """Cores (BGR) candidatas a estado, ordenadas por área: exclui mar, branco, texto e contornos."""
    h, w = img.shape[:2]
    suave = cv2.medianBlur(img, 3)
    q = (suave // PASSO_COR) * PASSO_COR + PASSO_COR // 2
    chaves = (q[:, :, 0].astype(np.int64) << 16) | (q[:, :, 1].astype(np.int64) << 8) | q[:, :, 2].astype(np.int64)
    vals, cont = np.unique(chaves, return_counts=True)
    cores = []
    for k, c in zip(vals, cont):
        if c < 60: continue
        b, g, r = (k >> 16) & 255, (k >> 8) & 255, k & 255
        cor = np.array([b, g, r], np.int32)
        if np.abs(cor - MAR).sum() < 70: continue          # mar e suas bordas suavizadas
        if np.abs(cor - BRANCO).sum() < 24: continue       # terra sem dono
        if max(b, g, r) < 110: continue                    # texto, contornos escuros
        if max(b, g, r) - min(b, g, r) < 45 and min(b, g, r) > 170: continue   # azuis/cinzas pálidos (mar, costa)
        cores.append((int(c), cor))
    cores.sort(key=lambda t: -t[0])
    # funde tons muito próximos (bordas suavizadas) no tom mais frequente
    fundidas = []
    for c, cor in cores:
        for i, (c2, cor2) in enumerate(fundidas):
            if np.abs(cor - cor2).sum() < 50:
                fundidas[i] = (c2 + c, cor2)
                break
        else:
            fundidas.append((c, cor))
    return fundidas


def segmentar_quadro(caminho, cal, max_estados=400):
    img = cv2.imread(caminho)
    h, w = img.shape[:2]
    # a caixa do ano e o rodapé não fazem parte do mapa
    img[int(h * 0.88):, int(w * 0.40):int(w * 0.60)] = MAR
    estados = []
    usado = np.zeros((h, w), bool)
    for c, cor in cores_do_quadro(img):
        dist = np.abs(img.astype(np.int32) - cor[None, None, :]).sum(axis=2)
        m = ((dist < TOL_COR) & ~usado).astype(np.uint8) * 255
        # fecha os buracos dos nomes escritos dentro do estado
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        n, rot, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
        for i in range(1, n):
            area = int(stats[i, cv2.CC_STAT_AREA])
            if area < AREA_MIN: continue
            comp = (rot == i).astype(np.uint8) * 255
            cs, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not cs: continue
            cnt = max(cs, key=cv2.contourArea)
            eps = 1.2                                     # px: fino o bastante para seguir as bordas do vídeo
            ap = cv2.approxPolyDP(cnt, eps, True)[:, 0, :]
            if len(ap) < 3: continue
            # cinzas e tons apagados também são estados em alguns períodos, mas o contorno da costa e os
            # respingos de antialiasing têm a mesma cor: exige área e "solidez" (área / casca convexa)
            pouco_saturado = int(cor.max() - cor.min()) < 40
            casca = cv2.contourArea(cv2.convexHull(cnt)) or 1.0
            solidez = cv2.contourArea(cnt) / casca
            if pouco_saturado and (area < 220 or solidez < 0.5): continue
            if not pouco_saturado and solidez < 0.2: continue
            aneis = [[round(v, 3) for v in pixel_para_lonlat(cal, float(u), float(v))] for u, v in ap]
            x, y, bw, bh = (int(stats[i, k]) for k in (cv2.CC_STAT_LEFT, cv2.CC_STAT_TOP, cv2.CC_STAT_WIDTH, cv2.CC_STAT_HEIGHT))
            estados.append({
                "cor": [int(cor[2]), int(cor[1]), int(cor[0])],   # RGB
                "area_px": area, "bbox": [x, y, bw, bh], "anel": aneis,
            })
            usado |= (rot == i)
        if len(estados) >= max_estados: break
    return estados
