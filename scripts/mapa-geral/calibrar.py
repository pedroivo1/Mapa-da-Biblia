#!/usr/bin/env python3
# Etapa 2 do mapa geral: descobre, para cada quadro, como pixel do vídeo vira longitude/latitude.
# O enquadramento do vídeo muda ao longo do tempo (zoom e deslocamento), então a calibração é por quadro.
# Método: a máscara de terra do quadro (tudo que não é a cor do mar) é comparada com a terra de
# frontend/mapa/mundo.json renderizada na projeção candidata (equiretangular ou Mercator), por correlação
# (cv2.matchTemplate) em várias escalas; o melhor par escala/posição vence e é refinado.
# Uso:  python3 scripts/mapa-geral/calibrar.py 10 300 600 900     # segundos do vídeo
import json, math, os, sys
import cv2
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, "..", ".."))
CACHE = os.path.join(AQUI, ".cache")
MUNDO = os.path.join(RAIZ, "frontend", "mapa", "mundo.json")

MAR = np.array([237, 228, 218], dtype=np.int32)   # cor do mar nos quadros, em BGR (azul-acinzentado claro)


def terra_aneis():
    w = json.load(open(MUNDO))
    out = []
    for f in w["fundo"]:
        if f["tipo"] == "terra":
            out.extend(f["aneis"])
    return out


def merc(lat):
    lat = max(-85.0, min(85.0, lat))
    return math.degrees(math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))


def renderizar(aneis, proj, escala, lon0=-180.0, lat_topo=80.0, lat_base=-58.0):
    """Mundo renderizado com 'escala' px por grau de longitude. Devolve (imagem, função lon/lat->px)."""
    ytopo = merc(lat_topo) if proj == "mercator" else lat_topo
    ybase = merc(lat_base) if proj == "mercator" else lat_base
    W = int(round(360 * escala)); H = int(round((ytopo - ybase) * escala))
    def px(lon, lat):
        y = merc(lat) if proj == "mercator" else lat
        return (lon - lon0) * escala, (ytopo - y) * escala
    img = np.zeros((H, W), np.uint8)
    # anéis em XOR (mesma regra par-ímpar do site): desenha cada um e inverte
    for a in aneis:
        pts = np.array([px(p[0], p[1]) for p in a], np.float32).round().astype(np.int32)
        if len(pts) < 3: continue
        tmp = np.zeros_like(img)
        cv2.fillPoly(tmp, [pts], 255)
        img = cv2.bitwise_xor(img, tmp)
    return img, px


def mascara_quadro(caminho, largura=320):
    im = cv2.imread(caminho)
    if im is None: raise SystemExit("quadro não encontrado: " + caminho)
    h, w = im.shape[:2]
    pequeno = cv2.resize(im, (largura, int(h * largura / w)), interpolation=cv2.INTER_AREA).astype(np.int32)
    dist = np.abs(pequeno - MAR[None, None, :]).sum(axis=2)
    terra = (dist > 40).astype(np.uint8) * 255
    # apaga o rodapé (ano) e o cabeçalho (ranking), que não fazem parte do mapa
    terra[int(terra.shape[0] * 0.85):, :] = 0
    return terra


ESCALAS = [round(0.5 + 0.04 * i, 2) for i in range(0, 80)]   # px por grau de longitude, em quadros de 320 px


def ajustar_varios(masks, aneis, projs=("equirect", "mercator"), escalas=ESCALAS):
    """masks: {id: máscara}. Renderiza o mundo uma vez por (projeção, escala) e testa todas as máscaras."""
    melhores = {k: [] for k in masks}
    for proj in projs:
        for e in escalas:
            mundo, px = renderizar(aneis, proj, e)
            for k, m in masks.items():
                h, w = m.shape
                if mundo.shape[0] < h or mundo.shape[1] < w: continue
                r = cv2.matchTemplate(mundo, m, cv2.TM_CCOEFF_NORMED)
                _, v, _, loc = cv2.minMaxLoc(r)
                melhores[k].append((float(v), proj, e, loc))
    for k in melhores:
        melhores[k].sort(reverse=True)
    return melhores


def main():
    if sys.argv[1:2] == ["todos"]:
        calibrar_todos(int(sys.argv[2]) if len(sys.argv) > 2 else 6)
        return
    segs = [int(x) for x in sys.argv[1:]] or [10, 300, 600, 900]
    aneis = terra_aneis()
    masks = {s: mascara_quadro(os.path.join(CACHE, "quadros", "%04d.jpg" % s)) for s in segs}
    res = ajustar_varios(masks, aneis)
    for s in segs:
        print("segundo", s)
        for v, proj, e, loc in res[s][:3]:
            print("   %.4f  %-9s  %.2f px/grau  desloc=%s" % (v, proj, e, loc))


def refinar(caminho, aneis, proj, e320, loc320):
    """Refina em quadros de 1280 px. Devolve {proj, S (px/grau), X0, Y0, nota}: pixel (u, v) do quadro de
    1280 px -> mundo (X0+u, Y0+v) -> lon = -180 + X/S; Mercator: y = ytopo - Y/S (graus de Mercator)."""
    mask = mascara_quadro(caminho, 1280)
    h, w = mask.shape
    melhor = None
    for f in (0.97, 0.98, 0.99, 1.0, 1.01, 1.02, 1.03):
        S = e320 * 4 * f
        mundo, _ = renderizar(aneis, proj, S)
        x0 = max(0, int(loc320[0] * 4 * f - 60)); y0 = max(0, int(loc320[1] * 4 * f - 60))
        x1 = min(mundo.shape[1], x0 + w + 120); y1 = min(mundo.shape[0], y0 + h + 120)
        janela = mundo[y0:y1, x0:x1]
        if janela.shape[0] < h or janela.shape[1] < w: continue
        r = cv2.matchTemplate(janela, mask, cv2.TM_CCOEFF_NORMED)
        _, v, _, loc = cv2.minMaxLoc(r)
        if melhor is None or v > melhor[0]:
            melhor = (float(v), S, x0 + loc[0], y0 + loc[1])
    if melhor is None: return None
    v, S, X0, Y0 = melhor
    return {"proj": proj, "S": round(S, 3), "X0": int(X0), "Y0": int(Y0), "escore": round(v, 4)}


def calibrar_todos(passo=6, saida=None):
    arqs = sorted(f for f in os.listdir(os.path.join(CACHE, "quadros")) if f.endswith(".jpg"))
    segs = list(range(5, len(arqs) + 1, passo))
    aneis = terra_aneis()
    masks = {s: mascara_quadro(os.path.join(CACHE, "quadros", "%04d.jpg" % s)) for s in segs}
    res = ajustar_varios(masks, aneis)
    out = {}
    for s in segs:
        if not res[s]: continue
        v, proj, e, loc = res[s][0]
        r = refinar(os.path.join(CACHE, "quadros", "%04d.jpg" % s), aneis, proj, e, loc)
        if r: out[str(s)] = r
        print(s, r, flush=True)
    json.dump(out, open(saida or os.path.join(CACHE, "calibracao.json"), "w"))
    return out


if __name__ == "__main__":
    main()
