#!/usr/bin/env python3
# E2 do mapa geral (v2): decodifica TODOS os quadros do vídeo principal (1920×960) e descobre o ano de cada um.
# Uso (na raiz do repositório):
#   PYTHONPATH=~/.cache/mapa-biblia-lib/lib python3 scripts/mapa-geral/quadros.py [passo]
#     passo "varrer"  : decodifica o vídeo todo e grava .cache/v2/varredura.npz + caixas/ (E2.1)
#     passo "ler"     : OCR das caixas de ano distintas (E2.2) -> .cache/v2/anos-lidos.json
#     passo "montar"  : sequência de anos, mapas distintos (PNG), anos.json (E2.3–E2.6)
#     (sem passo roda os três, em ordem)
# Lê o vídeo principal em vídeos/ (video(): prefere *hzWwp9JM7Hw*8k.mp4, 7680×3840; senão qualquer arquivo do id). Todo
# quadro é decodificado por decodificar(), que reduz com `scale=...:flags=area` para o tamanho pedido: a varredura
# (ano e mudança de mapa) é sempre em 1920×960, qualquer que seja a fonte. Os PNGs dos mapas distintos (1920, 4K e
# 8K, mediana de vários quadros) são do quadros_medios.py (E2.4), chamado por montar_anos.montar().
# Saídas em scripts/mapa-geral/.cache/v2/ (ignorada pelo git):
#   varredura.npz   por quadro: esquerda/direita da moldura do ano, hash da caixa, mudança do mapa em relação ao anterior
#   caixas.npz      imagens (cinza) das caixas de ano distintas, indexadas pelo hash
#   anos-lidos.json hash da caixa -> texto lido pelo OCR
#   mapas/<id>.png  um PNG sem perdas por mapa distinto (id = número da corrida de quadros iguais)
#   anos.json       {"<ano>": {"quadros": [i0, i1], "mapa": id, "zoom": bool, "meio": n}}  (a.C. positivo, d.C. negativo)
# O vídeo é AV1 com perda: o mesmo mapa aparece com ruído de ±poucos níveis entre quadros. Uma "mudança de mapa" é
# medida por alisamento 5×5 da diferença máxima por canal (ruído isolado some; uma fronteira que muda não).
# Dependências: ffmpeg, tesseract (eng), numpy, opencv, Pillow.
import glob, hashlib, json, os, subprocess, sys
from concurrent.futures import ProcessPoolExecutor

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/.cache/mapa-biblia-lib/lib"))
import numpy as np
import cv2

RAIZ = os.path.normpath(os.path.join(AQUI, "..", ".."))
CACHE = os.environ.get("MAPA_GERAL_CACHE") or os.path.join(AQUI, ".cache")
V2 = os.path.join(CACHE, "v2")
H, W = 960, 1920            # a varredura é sempre no quadro de referência (escala.W0 × escala.H0)
FPS = 30000 / 1001
N_QUADROS = 31280
# moldura do ano: faixa vertical (y) e limites de largura; a posição horizontal muda com o enquadramento
BANDA = (850, 910)
LARG_MOLDURA = (140, 240)
ORN_Y = (815, 945)        # altura do ornamento inteiro (flor-de-lis em cima e embaixo)
ORN_MARGEM = 22           # px de cada lado da moldura que também são ornamento
LIMIAR_MUDANCA = 12       # alisado 5×5 da diferença máxima por canal
MIN_PIXELS_MUDANCA = 10   # pixels acima do limiar para contar como mudança de mapa
N_PROC = 8


def video():
    """Arquivo do vídeo principal: o 8K (*8k.mp4) se existir, senão o primeiro arquivo com o id."""
    pasta = os.path.join(RAIZ, "vídeos")
    v = sorted(glob.glob(os.path.join(pasta, "*hzWwp9JM7Hw*8k.mp4")))
    if not v:
        v = sorted(f for f in glob.glob(os.path.join(pasta, "*hzWwp9JM7Hw*")) if not f.endswith(".part"))
    if not v:
        raise SystemExit("vídeo principal (id hzWwp9JM7Hw) não encontrado em vídeos/")
    return v[0]


def decodificar(i0, n, largura=W, altura=H, threads=2, pix="bgr24"):
    """Gera os quadros i0 .. i0+n-1 do vídeo, reduzidos a largura×altura (filtro area, exato para múltiplos
    inteiros), como arrays uint8 (altura, largura, 3) ou (altura, largura) em cinza. Começa meio quadro antes do
    instante de i0, para o corte cair no quadro certo (mesma convenção em toda a E2)."""
    ss = max(0.0, (i0 - 0.5) / FPS)
    cmd = ["ffmpeg", "-v", "error", "-threads", str(threads), "-ss", f"{ss:.4f}", "-i", video(), "-frames:v", str(n),
           "-vf", f"scale={largura}:{altura}:flags=area", "-f", "rawvideo", "-pix_fmt", pix, "-"]
    canais = 1 if pix == "gray" else 3
    tam = altura * largura * canais
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    try:
        k = 0
        while k < n:
            b = p.stdout.read(tam)
            if len(b) < tam:
                break
            f = np.frombuffer(b, np.uint8)
            yield f.reshape(altura, largura) if canais == 1 else f.reshape(altura, largura, 3)
            k += 1
    finally:
        p.stdout.close()
        p.kill()
        p.wait()


def tarefas():
    """Partição do vídeo em N_PROC trechos (i0, n), a mesma da varredura: o primeiro quadro de cada trecho é
    marcado como mudança (mud = -1), então nenhuma corrida de mapa atravessa um limite."""
    por = N_QUADROS // N_PROC + 1
    return [(i, min(por, N_QUADROS - i)) for i in range(0, N_QUADROS, por)]


def moldura(g):
    """(esquerda, direita) das duas bordas verticais da moldura do ano, em px de 1920; None se não achar."""
    esc = (g[BANDA[0]:BANDA[1], :] < 80).mean(axis=0)
    cols = np.where(esc > 0.85)[0]
    if len(cols) < 2:
        return None
    # agrupa colunas vizinhas; as bordas são linhas finas
    grupos, ini = [], cols[0]
    for i in range(1, len(cols)):
        if cols[i] - cols[i - 1] > 3:
            grupos.append((ini, cols[i - 1])); ini = cols[i]
    grupos.append((ini, cols[-1]))
    finos = [g_ for g_ in grupos if g_[1] - g_[0] <= 6]
    for (a0, a1), (b0, b1) in zip(finos, finos[1:]):
        w = b1 - a0
        if LARG_MOLDURA[0] <= w <= LARG_MOLDURA[1] and 600 < (a0 + b1) / 2 < 1400:
            return a0, b1
    return None


def mascarar(f, lr):
    """Cópia do quadro com o ornamento zerado (a moldura se desloca; o que está por baixo não é mapa)."""
    m = f.copy()
    if lr is None:
        m[ORN_Y[0]:ORN_Y[1], 600:1400] = 0
    else:
        m[ORN_Y[0]:ORN_Y[1], max(0, lr[0] - ORN_MARGEM):lr[1] + ORN_MARGEM] = 0
    return m


def caixa_ano(g, lr):
    """Recorte (cinza) do interior da moldura com os dígitos; None se não há moldura."""
    if lr is None:
        return None
    return g[BANDA[0] + 4:BANDA[1] - 4, lr[0] + 6:lr[1] - 5]


def varrer_trecho(args):
    i0, n = args
    esq = np.full(n, -1, np.int16); dir_ = np.full(n, -1, np.int16)
    hcx = np.zeros(n, "S16"); mud = np.zeros(n, np.int32); mud_ru = np.zeros(n, np.int32)
    caixas = {}
    prev = None
    k = 0
    for f in decodificar(i0, n, W, H, threads=2):
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        lr = moldura(g)
        if lr:
            esq[k], dir_[k] = lr
            cx = caixa_ano(g, lr)
            h = hashlib.md5(cx.tobytes() + bytes(cx.shape)).hexdigest()[:16]
            hcx[k] = h.encode()
            if h not in caixas:
                caixas[h] = cx.copy()
        m = mascarar(f, lr)
        if prev is not None:
            d = np.abs(m.astype(np.int16) - prev).max(axis=2).astype(np.float32)
            bl = cv2.boxFilter(d, -1, (5, 5))
            mud[k] = int((bl > LIMIAR_MUDANCA).sum())
            mud_ru[k] = int((d > 0).sum())
        prev = m.astype(np.int16)
        k += 1
    return i0, k, esq[:k], dir_[:k], hcx[:k], mud[:k], mud_ru[:k], caixas


def varrer():
    os.makedirs(V2, exist_ok=True)
    trechos = tarefas()
    esq = np.full(N_QUADROS, -1, np.int16); dir_ = esq.copy()
    hcx = np.zeros(N_QUADROS, "S16"); mud = np.zeros(N_QUADROS, np.int32); mud_ru = mud.copy()
    caixas = {}
    lidos = 0
    with ProcessPoolExecutor(N_PROC) as ex:
        for i0, k, e, d, h, m, mr, cx in ex.map(varrer_trecho, trechos):
            esq[i0:i0 + k], dir_[i0:i0 + k], hcx[i0:i0 + k] = e, d, h
            mud[i0:i0 + k], mud_ru[i0:i0 + k] = m, mr
            caixas.update(cx)
            lidos += k
            print(f"trecho {i0}: {k} quadros", flush=True)
    # a mudança do primeiro quadro de cada trecho não tem anterior: refeita na junção (compara com o último do trecho
    # anterior só se for preciso; aqui é marcada como "sem medida" = -1 e tratada como mudança pela montagem)
    for i0, _ in trechos[1:]:
        mud[i0] = -1
    print("quadros lidos:", lidos)
    np.savez_compressed(os.path.join(V2, "varredura.npz"), esq=esq, dir=dir_, hcx=hcx, mud=mud, mud_ru=mud_ru)
    chaves = sorted(caixas)
    np.savez_compressed(os.path.join(V2, "caixas.npz"), **{c: caixas[c] for c in chaves})
    print("caixas distintas:", len(chaves))


def ocr_uma(args):
    chave, arr = args
    import tempfile
    from PIL import Image
    im = Image.fromarray(arr)
    im = im.resize((im.width * 3, im.height * 3), Image.LANCZOS)
    a = np.asarray(im)
    # texto preto sobre claro: binariza e põe margem branca
    _, bw = cv2.threshold(a, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bw = cv2.copyMakeBorder(bw, 14, 14, 14, 14, cv2.BORDER_CONSTANT, value=255)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "c.png")
        cv2.imwrite(p, bw)
        r = subprocess.run(["tesseract", p, "-", "--psm", "7", "-c", "tessedit_char_whitelist=0123456789BC ",
                            "--dpi", "150"], capture_output=True, text=True)
    return chave, " ".join(r.stdout.split())


def ler():
    z = np.load(os.path.join(V2, "caixas.npz"))
    itens = [(c, z[c]) for c in z.files]
    saida = {}
    with ProcessPoolExecutor(N_PROC) as ex:
        for c, t in ex.map(ocr_uma, itens, chunksize=32):
            saida[c] = t
    json.dump(saida, open(os.path.join(V2, "anos-lidos.json"), "w"), indent=0)
    print("caixas lidas:", len(saida))


if __name__ == "__main__":
    passo = sys.argv[1] if len(sys.argv) > 1 else "tudo"
    if passo in ("varrer", "tudo"):
        varrer()
    if passo in ("ler", "tudo"):
        ler()
    if passo in ("montar", "tudo"):
        import montar_anos
        montar_anos.montar()
