#!/usr/bin/env python3
# Etapa 1 do mapa geral: extrai quadros do vídeo e descobre o ano de cada quadro (OCR do rodapé).
# Uso (na raiz do repositório):
#   python3 scripts/mapa-geral/extrair.py            # usa o vídeo principal
# Saída (em scripts/mapa-geral/.cache/, ignorada pelo git):
#   quadros/NNNN.jpg   um quadro por segundo, 1280 px de largura
#   indice.json        {"segundos": [[s, ano], ...]}  (ano a.C. positivo, d.C. negativo)
# Dependências: ffmpeg, tesseract (eng), numpy, Pillow.
import glob, json, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageOps

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, "..", ".."))
CACHE = os.path.join(AQUI, ".cache")
VIDEO = glob.glob(os.path.join(RAIZ, "vídeos", "*hzWwp9JM7Hw*.webm"))[0]
QUADROS = os.path.join(CACHE, "quadros")

# faixa vertical onde fica o texto do ano (quadros de 1280 px); a caixa se desloca na horizontal conforme o
# enquadramento do vídeo, então ela é localizada pelas duas bordas verticais da moldura
BANDA = (574, 602)
ESCURO = 110


def extrair_quadros():
    os.makedirs(QUADROS, exist_ok=True)
    if glob.glob(os.path.join(QUADROS, "*.jpg")):
        return
    subprocess.check_call([
        "ffmpeg", "-v", "error", "-y", "-i", VIDEO,
        "-vf", "fps=1,scale=1280:-1", "-q:v", "3", os.path.join(QUADROS, "%04d.jpg"),
    ])


def recorte_texto(im):
    """Devolve a imagem (L) só com o texto do ano, ou None. Procura as bordas verticais da moldura na faixa."""
    import numpy as np
    g = np.asarray(im.convert("L"))
    faixa = g[BANDA[0]:BANDA[1], :]
    escuro = faixa < ESCURO
    col = escuro.mean(axis=0)            # fração de pixels escuros por coluna
    cheias = np.where(col > 0.85)[0]     # colunas quase totalmente escuras = bordas da moldura
    if len(cheias) < 2: return None
    # agrupa colunas vizinhas
    grupos, ini = [], cheias[0]
    for i in range(1, len(cheias)):
        if cheias[i] - cheias[i - 1] > 3:
            grupos.append((ini, cheias[i - 1])); ini = cheias[i]
    grupos.append((ini, cheias[-1]))
    melhor = None
    finos = [g for g in grupos if g[1] - g[0] <= 5]      # as bordas da moldura são linhas finas
    for (a0, a1), (b0, b1) in zip(finos, finos[1:]):
        w = b0 - a1
        if 60 <= w <= 170 and 300 < (a0 + b1) / 2 < 1000:
            melhor = (a1 + 3, b0 - 3)
            break
    if not melhor: return None
    return Image.fromarray(g[BANDA[0] - 2:BANDA[1] + 2, melhor[0]:melhor[1]])


def ler_ano(caminho):
    im = Image.open(caminho)
    rec = recorte_texto(im)
    if rec is None: return None
    rec = rec.resize((rec.width * 5, rec.height * 5), Image.LANCZOS)
    rec = rec.point(lambda v: 255 if v > 128 else 0)
    rec = ImageOps.expand(rec, border=30, fill=255)
    tmp = caminho + ".ocr.png"
    rec.save(tmp)
    try:
        out = subprocess.run(
            ["tesseract", tmp, "stdout", "--psm", "7", "-c", "tessedit_char_whitelist=0123456789BCAD "],
            capture_output=True, text=True, timeout=20).stdout
    finally:
        try: os.remove(tmp)
        except OSError: pass
    m = re.search(r"(\d{1,4})\s*(BC|AD|CE|BCE)?", out.replace("\n", " "))
    if not m: return None
    n = int(m.group(1))
    if m.group(2) in ("BC", "BCE"): return n    # a.C. positivo
    return -n                                   # sem sufixo = d.C. (negativo, convenção do projeto)


def main():
    extrair_quadros()
    arqs = sorted(glob.glob(os.path.join(QUADROS, "*.jpg")))
    print(len(arqs), "quadros")
    with ThreadPoolExecutor(max_workers=12) as ex:
        anos = list(ex.map(ler_ano, arqs))
    json.dump({"segundos": [[i + 1, a] for i, a in enumerate(anos)]}, open(os.path.join(CACHE, "indice-bruto.json"), "w"))
    lidos = sum(1 for a in anos if a is not None)
    print("anos lidos:", lidos, "de", len(anos))


if __name__ == "__main__":
    main()
