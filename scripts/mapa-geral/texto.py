# Texto dos mapas do vídeo (E7): detecção das etiquetas e leitura de cada recorte.
# Usado por nomear.py. Precisa (fora do repositório, em ~/.cache/mapa-biblia-lib/):
#   lib/       rapidocr-onnxruntime, tesserocr (com o tesseract do sistema), numpy, opencv, Pillow
#   tessdata/  eng.traineddata do tessdata_best (github.com/tesseract-ocr/tessdata_best)
#   fontes/    a fonte usada para conferir as leituras (FONTE; ver abaixo)
#
# Detecção (com os rótulos da E4e, a letra clara só vale dentro de região colorida): as letras do vídeo são neutras (cinza-escuro sobre fundo claro, ou brancas sobre estado colorido); as
# regiões são coloridas ou lisas. Pixel de letra escura: mediana local (15×15) − cinza > 30, cinza ≤ 150, croma ≤ 60;
# letra clara: cinza − mediana local > 20, cinza ≥ 140. As partes grossas da máscara (abertura 5×5: terra, manchas)
# saem. Componentes com forma de letra viram palavras quando estão na mesma linha (sobreposição vertical ≥ 50 %) e
# com vão ≤ 0,7 × altura; uma letra sozinha (com ou sem ponto: "A", "K.") também vale. Uma caixa só fica se tiver
# tinta forte (≥ 4 px com cinza ≤ 60 na escura; ≥ 40 acima da mediana local ou ≥ 240 na clara): isso tira os pedaços
# de litoral (cinza médio). Traço fino e comprido (enchimento < 18 % da caixa) não é letra. Sobram caixas falsas de
# terra branca fina (penínsulas, ilhas); o OCR as descarta.
#
# Leitura: o recorte passa por 6 variantes de OCR (RapidOCR e Tesseract, em escalas e margens diferentes; se as 2
# primeiras não derem nada com nota ≥ 0,45, a caixa é falsa e para por aí); cada
# leitura vira candidata e a escolhida é a que, desenhada com uma fonte sem serifa parecida com a do vídeo (a do
# vídeo é a Myriad Pro, que não é livre), melhor explica o recorte: correlação normalizada com o texto cercado de uma
# margem vazia, no melhor tamanho e na melhor posição de subpixel. Além das leituras, entram variações baratas de cada
# uma (sem o ponto final, inicial maiúscula, sem uma letra solta no começo ou no fim). As candidatas e as notas
# ficam guardadas: a E7 junta as leituras de toda a vida de uma entidade e reavalia.
# Os parâmetros são de três grupos (detecção, OCR, nota); nomear.py guarda o OCR bruto e as notas em caches por
# recorte separados, para que mudar só a nota não exija rodar o OCR de novo.
import os, re

os.environ.setdefault("OMP_THREAD_LIMIT", "1")      # tesseract: uma thread por processo (nomear.py usa 8 processos)
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

LIB = os.path.expanduser("~/.cache/mapa-biblia-lib")
FONTE = os.path.join(LIB, "fontes", "sarabun.ttf")
TESSDATA = os.path.join(LIB, "tessdata")

PARAMS = {
    "versao": 2,
    "MEDIANA": 15, "CONTRASTE": 30, "ESCURO_MAX": 150, "CROMA_MAX": 60, "CONTRASTE_CLARO": 20, "CLARO_MIN": 140,
    "GROSSO": 5, "VAO": 0.7, "TINTA_FORTE": 4, "LETRA_SO": 1,
    "OCR": [[2, 6, "tess"], [1, 5, "rapid"], [1, 3, "rapid"], [2, 8, "rapid"], [2, 3, "rapid"], [2, 4, "tess-otsu"]],
    "OCR_CEDO": 2, "NOTA_CEDO": 0.45,
    "FONTE": os.path.basename(FONTE), "SS": 4, "MARGEM_REC": 6, "VARIACOES": 2, "FAIXA_TAM": 0.5,
}
GRUPOS = {
    "det": ["MEDIANA", "CONTRASTE", "ESCURO_MAX", "CROMA_MAX", "CONTRASTE_CLARO", "CLARO_MIN", "GROSSO", "VAO",
            "TINTA_FORTE", "LETRA_SO"],
    "ocr": ["OCR", "OCR_CEDO", "NOTA_CEDO", "FONTE", "SS", "MARGEM_REC"],
    "nota": ["OCR", "OCR_CEDO", "NOTA_CEDO", "FONTE", "SS", "MARGEM_REC", "VARIACOES", "FAIXA_TAM"],
}


def grupo(nome, p=PARAMS):
    return {"versao": p["versao"], **{k: p[k] for k in GRUPOS[nome]}}


# ------------------------------------------------------------------ detecção
def mascaras(im, p=PARAMS):
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    ch = im.max(2).astype(np.int16) - im.min(2)
    med = cv2.medianBlur(g, p["MEDIANA"]).astype(np.int16)
    gi = g.astype(np.int16)
    out = {"escuro": (med - gi > p["CONTRASTE"]) & (g <= p["ESCURO_MAX"]) & (ch <= p["CROMA_MAX"]),
           "claro": (gi - med > p["CONTRASTE_CLARO"]) & (g >= p["CLARO_MIN"])}
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (p["GROSSO"], p["GROSSO"]))
    for n, m in out.items():
        grosso = cv2.dilate(cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, k), np.ones((3, 3), np.uint8))
        out[n] = m & (grosso == 0)
    return g, out, med


ENCHIMENTO = 0.18


def letras(b):
    n, _, st, _ = cv2.connectedComponentsWithStats(b.astype(np.uint8), connectivity=8)
    out = []
    for i in range(1, n):
        x, y, w, h, a = (int(v) for v in st[i])
        if (2 <= h <= 34 and w <= 300 and a <= (0.92 * w * h + 4 if w <= 1.5 * h else 0.7 * w * h)
                and (max(w, h) < 8 or a >= ENCHIMENTO * w * h)):      # traço fino e comprido (fronteira) não é letra
            out.append((x, y, w, h))
    return out


def agrupar(L, vao, letra_so=1):
    L = sorted(L)
    pai = list(range(len(L)))

    def raiz(i):
        while pai[i] != i:
            pai[i] = pai[pai[i]]
            i = pai[i]
        return i
    for i, (x, y, w, h) in enumerate(L):
        for j in range(i + 1, len(L)):
            x2, y2, w2, h2 = L[j]
            if x2 > x + w + 40:
                break
            gap = x2 - (x + w)
            if gap > vao * max(h, h2, 6):
                continue
            ov = min(y + h, y2 + h2) - max(y, y2)
            if (ov >= 0.5 * min(h, h2) and max(h, h2) <= 2.2 * max(3, min(h, h2))) or (min(h, h2) <= 3 and ov >= 0):
                pai[raiz(j)] = raiz(i)
    grupos = {}
    for i in range(len(L)):
        grupos.setdefault(raiz(i), []).append(L[i])
    out = []
    for m in grupos.values():
        x0 = min(t[0] for t in m)
        y0 = min(t[1] for t in m)
        x1 = max(t[0] + t[2] for t in m)
        y1 = max(t[1] + t[3] for t in m)
        hm = sorted(t[3] for t in m)[len(m) // 2]
        altas = [t for t in m if t[3] >= 4]
        if ((sum(1 for t in m if t[3] >= 3) >= 2 or (len(m) == 1 and m[0][2] >= 2 * m[0][3]))
                and 3 <= hm <= 30 and y1 - y0 >= 5 and x1 - x0 >= 1.2 * (y1 - y0)):
            out.append((x0, y0, x1 - x0, y1 - y0))
        elif letra_so and len(altas) == 1 and 5 <= altas[0][3] <= 16 and 0.4 * altas[0][3] <= altas[0][2] <= 1.4 * altas[0][3]:
            # etiqueta de uma letra ("A", "K.", "D"): uma letra, com ou sem ponto
            out.append((x0, y0, x1 - x0, y1 - y0))
    return out


def detectar(im, p=PARAMS, rot=None, brancas=None):
    """[(tipo, x, y, w, h)], tipo 'escuro' ou 'claro'. Com os rótulos da E4e (rot, imagem de regiões) e o conjunto das
    regiões brancas/creme, a letra clara só vale dentro de região colorida: a terra branca vizinha não gruda nela."""
    g, ms, med = mascaras(im, p)
    if rot is not None and brancas:
        ms["claro"] &= ~np.isin(rot, list(brancas))
    out = []
    for tipo, b in ms.items():
        for x, y, w, h in agrupar(letras(b), p["VAO"], p["LETRA_SO"]):
            c = g[y:y + h, x:x + w].astype(np.int16)
            forte = (c <= 60).sum() if tipo == "escuro" else ((c - med[y:y + h, x:x + w] >= 40) | (c >= 240)).sum()
            if forte >= p["TINTA_FORTE"]:
                out.append((tipo, x, y, w, h))
    return out


def recorte(im, x, y, w, h, P):
    H, W = im.shape[:2]
    return im[max(0, y - P):min(H, y + h + P), max(0, x - P):min(W, x + w + P)]


# ------------------------------------------------------------------ OCR
_ocr = {}


def _rapid():
    if "rapid" not in _ocr:
        import logging
        from rapidocr_onnxruntime import RapidOCR
        _ocr["rapid"] = RapidOCR(intra_op_num_threads=1, inter_op_num_threads=1)
        logging.getLogger("RapidOCR").setLevel(logging.ERROR)
    return _ocr["rapid"]


def _tess():
    if "tess" not in _ocr:
        import tesserocr
        api = tesserocr.PyTessBaseAPI(path=TESSDATA, lang="eng", psm=tesserocr.PSM.SINGLE_LINE)
        for v in ("load_system_dawg", "load_freq_dawg"):
            api.SetVariable(v, "F")
        api.SetVariable("tessedit_char_whitelist", "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .-'")
        _ocr["tess"] = api
    return _ocr["tess"]


def preparar(crop, claro, E):
    """Cinza com fundo branco e letra preta, esticado (fundo = mediana), ampliado E vezes."""
    g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).astype(np.float32)
    med = float(np.median(g))
    if claro:
        g = 255 - g
        med = 255 - med
    g = np.clip((g - g.min()) / max(1.0, med - g.min()) * 255, 0, 255).astype(np.uint8)
    return cv2.resize(g, None, fx=E, fy=E, interpolation=cv2.INTER_CUBIC)


def ocr(g, motor):
    if motor == "rapid":
        g3 = cv2.cvtColor(cv2.copyMakeBorder(g, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255), cv2.COLOR_GRAY2BGR)
        out, _ = _rapid()(g3, use_det=False, use_cls=False, use_rec=True)
        return out[0][0] if out else ""
    if motor == "tess-otsu":
        g = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    api = _tess()
    from PIL import Image as _I
    api.SetImage(_I.fromarray(cv2.copyMakeBorder(g, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)))
    return api.GetUTF8Text().strip()


def limpa(s):
    s = s.replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z.' -]", "", s)).strip(" -'")


def valido(s):
    """Maiúscula só no começo da palavra (ou palavra toda maiúscula), ponto só no fim, sem palavra vazia."""
    if not s:
        return False
    for w in s.split(" "):
        if not w or w[0] in ".'-":
            return False
        if any(c.isupper() for c in w[1:]) and not w.isupper():
            return False
        if "." in w[:-1]:
            return False
    return True


# ------------------------------------------------------------------ conferência por renderização
_fontes, _rend = {}, {}


def _fonte(tam_ss):
    if tam_ss not in _fontes:
        _fontes[tam_ss] = ImageFont.truetype(FONTE, tam_ss)
    return _fontes[tam_ss]


def render(txt, tam, SS=PARAMS["SS"]):
    """O texto no tamanho `tam` (px), em SS×SS posições de subpixel (moldes já reduzidos para 1×)."""
    k = (txt, tam)
    if k in _rend:
        return _rend[k]
    f = _fonte(round(tam * SS * 4) / 4)
    l, t, r, b = f.getbbox(txt)
    im = Image.new("L", (max(1, r - l) + 2 * SS, max(1, b - t) + 2 * SS), 0)
    ImageDraw.Draw(im).text((SS - l, SS - t), txt, font=f, fill=255)
    a = np.asarray(im, np.float32) / 255
    moldes = []
    for oy in range(SS):
        for ox in range(SS):
            bb = a[oy:, ox:]
            H, W = bb.shape[0] // SS * SS, bb.shape[1] // SS * SS
            moldes.append(bb[:H, :W].reshape(H // SS, SS, W // SS, SS).mean((1, 3)))
    if len(_rend) > 3000:         # cada entrada guarda 16 moldes; 50 mil entradas chegavam a ~2 GB por processo
        _rend.clear()
    _rend[k] = moldes
    return moldes


def tinta(crop, claro):
    g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).astype(np.float32)
    med = float(np.median(g))
    t = (g - med) if claro else (med - g)
    return np.clip(t / max(1.0, float(t.max())), 0, 1)


def nota(ink, txt, tam):
    """Correlação normalizada entre o recorte e o texto desenhado, com margem vazia de ~1 letra dos lados e 1 px em
    cima/embaixo (letra que falta ou sobra conta contra; tinta longe não), na melhor posição."""
    if not txt.strip():
        return -1.0
    mx = max(2, int(round(0.55 * tam)))
    best = -1.0
    for m in render(txt, tam):
        t = cv2.copyMakeBorder(m, 1, 1, mx, mx, cv2.BORDER_CONSTANT, value=0)
        dy, dx = max(0, t.shape[0] - ink.shape[0]), max(0, t.shape[1] - ink.shape[1])
        i2 = cv2.copyMakeBorder(ink, dy, dy, dx, dx, cv2.BORDER_CONSTANT, value=0) if dy or dx else ink
        best = max(best, float(cv2.matchTemplate(i2, t, cv2.TM_CCOEFF_NORMED).max()))
    return best


def tamanhos(h):
    return [x / 4 for x in range(int(h * 0.85 * 4), int(h * 1.5 * 4) + 1)]


def notas(ink, h, cands):
    """{texto: [nota, tamanho]} de cada candidata, no melhor tamanho para a altura h da caixa."""
    out = {}
    tams = tamanhos(h)
    for c in cands:
        s, t = max((nota(ink, c, t), t) for t in tams)
        out[c] = [round(s, 4), t]
    return out


def ler_bruto(im, caixa, p=PARAMS):
    """As leituras do OCR (limpas e válidas), na ordem das variantes; para cedo numa caixa falsa."""
    tipo, x, y, w, h = caixa
    claro = tipo == "claro"
    ink = tinta(recorte(im, x, y, w, h, p["MARGEM_REC"]), claro)
    lidos, melhor = [], -1.0
    for i, (P, E, motor) in enumerate(p["OCR"]):
        s = limpa(ocr(preparar(recorte(im, x, y, w, h, P), claro, E), motor))
        if valido(s) and s not in lidos:
            lidos.append(s)
            if i < p["OCR_CEDO"]:
                melhor = max(melhor, notas(ink, h, [s])[s][0])
        if i == p["OCR_CEDO"] - 1 and melhor < p["NOTA_CEDO"]:
            break           # nada parecido com texto nas primeiras leituras: caixa falsa (terra fina, litoral)
    return lidos


def variacoes(s):
    out = {s, s.rstrip(".")}        # ponto a mais não: o desenho "acha" um ponto em qualquer ruído
    if s[0].islower():
        out.add(s[0].upper() + s[1:])
    pal = s.split(" ")
    if len(pal) > 1 and len(pal[0].rstrip(".")) <= 1:
        out.add(" ".join(pal[1:]))
    if len(pal) > 1 and len(pal[-1].rstrip(".")) <= 1:
        out.add(" ".join(pal[:-1]))
    return {v for v in out if valido(v)}


def pontuar(im, caixa, lidos, p=PARAMS):
    """[[texto, nota, tamanho], ...] (melhor primeiro): as leituras no tamanho que melhor as explica e as variações
    delas perto do tamanho da melhor leitura."""
    tipo, x, y, w, h = caixa
    if not lidos:
        return []
    ink = tinta(recorte(im, x, y, w, h, p["MARGEM_REC"]), tipo == "claro")
    ns = notas(ink, h, lidos)
    if p["VARIACOES"]:
        t0 = max(ns.values())[1]
        tams = [t0 + d / 4 for d in range(-int(p["FAIXA_TAM"] * 4), int(p["FAIXA_TAM"] * 4) + 1)]
        for c in sorted(set().union(*(variacoes(s) for s in lidos)) - set(ns)):
            sc, t = max((nota(ink, c, t), t) for t in tams)
            ns[c] = [round(sc, 4), t]
    return [[c, sc, t] for c, (sc, t) in sorted(ns.items(), key=lambda kv: (-kv[1][0], kv[0]))]


def ler(im, caixa, p=PARAMS):
    """Leitura de uma caixa: {"lidos": [...], "cands": [[texto, nota, tamanho], ...]}."""
    lidos = ler_bruto(im, caixa, p)
    return {"lidos": lidos, "cands": pontuar(im, caixa, lidos, p)}
