#!/usr/bin/env python3
# E2.4 do mapa geral (v2): o PNG de cada mapa distinto, em três tamanhos, como MEDIANA de vários quadros da corrida.
# O vídeo é AV1 com perda: o mesmo mapa aparece com ruído de ±poucos níveis entre quadros. A mediana pixel a pixel de
# até N_MAX quadros espaçados por igual na corrida (os quadros com o mesmo id de mapa, até o quadro escolhido pela E2,
# antes de fade/zoom) tira esse ruído sem borrar; é mediana e não média para que um quadro divergente (mudança miúda que
# o limiar da varredura não pegou) não vire fantasma. Corrida de 1 ou 2 quadros usa só o quadro escolhido.
# Lê o vídeo pela quadros.decodificar() (8K nativo, 7680×3840) numa passada sequencial por trecho (a mesma partição da
# varredura: nenhuma corrida atravessa um limite), sem busca por quadro. Grava, por mapa distinto:
#   .cache/v2/mapas-8k/<id>.png   7680×3840 (OCR das etiquetas, E7a com MAPA_GERAL_ESCALA_OCR=4)
#   .cache/v2/mapas-4k/<id>.png   3840×1920 (geometria com MAPA_GERAL_ESCALA=2; redução INTER_AREA, exata)
#   .cache/v2/mapas/<id>.png      1920×960  (geometria com escala 1, visualizador do painel, testes T2)
# e em mapas.json: "mediana": {"quadros": [...], "n", "dif_max_1920"} (maior diferença média, em níveis, entre cada
# quadro usado e a mediana, medida em 1920: acima de LIMIAR_MUDANCA indica corrida com mapas diferentes; é só aviso).
# Retomada: cada mapa gravado deixa também mapas-7k/<id>.json com o registro; ao começar, gerar() passa esses registros
# para mapas.json, e mapa com os três PNGs e o registro é pulado (--forcar refaz). Atômico (.tmp.png -> os.replace).
# Memória (medida em 2026-10-16): cada processo chega a ~3,5 GB de pico (ffmpeg decodificando AV1 8K ≈ 2,5 GB + pilha de
# 9 quadros 8K ≈ 0,8 GB), por isso o padrão é 2 processos (MAPA_GERAL_PROCS_E2 muda); com 4 numa máquina de 16 GB o
# systemd-oomd matou o terminal inteiro. Rode a cadeia num serviço à parte (ver cadeia-4k.sh).
# Uso (na raiz do repositório):  PYTHONPATH=~/.cache/mapa-biblia-lib/lib python3 scripts/mapa-geral/quadros_medios.py
#                                  [--forcar] [--procs 4] [id ...]
import json, os, sys, time
from concurrent.futures import ProcessPoolExecutor

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/.cache/mapa-biblia-lib/lib"))
sys.path.insert(0, AQUI)
import numpy as np
import cv2
import quadros
import escala

V2 = quadros.V2
N_MAX = 9                                   # quadros por mediana (ímpar)
ESCALAS = (1, 2, 4)                         # 1920, 3840, 7680
W8, H8 = escala.W0 * 4, escala.H0 * 4
COMPRESSAO = {1: 1, 2: 1, 4: 3}             # PNG: o 8K comprimido um pouco mais (~10 MB em vez de ~25)
FAIXA = 480                                 # linhas por faixa na ordenação (limita a memória da mediana)
PROCS = int(os.environ.get("MAPA_GERAL_PROCS_E2", "2"))   # 2 processos × ~3,5 GB de pico (ver cabeçalho)


def pasta(e):
    p = os.path.join(V2, escala.nome_pasta(e))
    os.makedirs(p, exist_ok=True)
    return p


def corridas():
    """{id: (primeiro, último)} dos quadros de cada id de mapa (id_mapa = cumsum(muda), como em montar_anos.py)."""
    import montar_anos
    mud = np.load(os.path.join(V2, "varredura.npz"))["mud"]
    muda = (mud >= montar_anos.MIN_PIXELS_MUDANCA) | (mud < 0)
    ids = np.cumsum(muda)
    corte = np.flatnonzero(ids[1:] != ids[:-1]) + 1
    inis = np.concatenate([[0], corte])
    fins = np.concatenate([corte - 1, [len(ids) - 1]])
    return {int(ids[a]): (int(a), int(b)) for a, b in zip(inis, fins)}


def escolher(ini, fim, cap=None, n_max=N_MAX):
    """Índices dos quadros da mediana: até n_max (ímpar), espaçados por igual em [ini, min(fim, cap)], sempre com o
    último (o quadro escolhido pela E2). Corrida curta: todos os quadros (número ímpar; com 2, só o último)."""
    if cap is not None:
        fim = min(fim, cap)
        ini = min(ini, fim)
    n = fim - ini + 1
    if n <= n_max:
        if n % 2 == 0:
            ini += 1
            n -= 1
        return list(range(ini, fim + 1))
    if n_max % 2 == 0:
        n_max -= 1
    return sorted({int(round(x)) for x in np.linspace(ini, fim, n_max)})


def mediana(stack):
    """Mediana pixel a pixel de stack (n, H, W, 3) uint8, n ímpar, por faixas de linhas (ordenação em cópia pequena)."""
    n = stack.shape[0]
    if n == 1:
        return stack[0]
    med = np.empty(stack.shape[1:], np.uint8)
    for r0 in range(0, stack.shape[1], FAIXA):
        s = np.ascontiguousarray(stack[:, r0:r0 + FAIXA])
        s.sort(axis=0)
        med[r0:r0 + FAIXA] = s[n // 2]
    return med


def gravar_mapa(k, stack):
    """Grava as três cópias do mapa k a partir do stack de quadros 8K; devolve o registro para mapas.json."""
    med8 = mediana(stack)
    med4 = cv2.resize(med8, (escala.W0 * 2, escala.H0 * 2), interpolation=cv2.INTER_AREA)
    med1 = cv2.resize(med8, (escala.W0, escala.H0), interpolation=cv2.INTER_AREA)
    ref = med1.astype(np.int16)
    difs = [float(np.abs(cv2.resize(f, (escala.W0, escala.H0), interpolation=cv2.INTER_AREA).astype(np.int16) - ref).mean())
            for f in stack]
    for e, im in ((1, med1), (2, med4), (4, med8)):
        alvo = os.path.join(pasta(e), f"{k}.png")
        tmp = os.path.join(pasta(e), f"{k}.tmp.png")
        cv2.imwrite(tmp, im, [cv2.IMWRITE_PNG_COMPRESSION, COMPRESSAO[e]])
        os.replace(tmp, alvo)
    return {"n": int(stack.shape[0]), "dif_max_1920": round(max(difs), 2)}


def pronto(k):
    return all(os.path.exists(os.path.join(V2, escala.nome_pasta(e), f"{k}.png")) for e in ESCALAS)


def registro_caminho(k):
    return os.path.join(pasta(4), f"{k}.json")


def gravar_registro(k, reg):
    """Registro do mapa ao lado do PNG 8K (retomada: sobrevive a uma morte antes do fim do trecho)."""
    tmp = registro_caminho(k) + ".tmp"
    json.dump(reg, open(tmp, "w"))
    os.replace(tmp, registro_caminho(k))


def recolher_registros(mapas):
    """Passa para mapas.json os registros gravados pelos processos (mapas-7k/<id>.json) que ainda não estão lá."""
    n = 0
    for k, m in mapas.items():
        if not m.get("mediana") and pronto(k) and os.path.exists(registro_caminho(k)):
            try:
                m["mediana"] = json.load(open(registro_caminho(k)))
                n += 1
            except ValueError:
                pass
    return n


def trecho(args):
    """Um trecho do vídeo: decodifica do primeiro ao último quadro pedido (8K, sequencial) e, assim que o último quadro
    de um mapa chega, grava a mediana dele. Só um stack vive por vez (as corridas são contíguas)."""
    (i0, n), pedidos = args
    if not pedidos:
        return {}, []
    cv2.setNumThreads(2)
    quer = {}
    for k, qs in pedidos.items():
        for j, q in enumerate(qs):
            quer[q] = (k, j)
    ult = {k: qs[-1] for k, qs in pedidos.items()}
    primeiro = min(qs[0] for qs in pedidos.values())
    ultimo = max(ult.values())
    stacks, out, avisos = {}, {}, []
    t0 = time.time()
    q = primeiro
    for f in quadros.decodificar(primeiro, ultimo - primeiro + 1, W8, H8, threads=4):
        if q in quer:
            k, j = quer[q]
            if k not in stacks:
                stacks[k] = np.empty((len(pedidos[k]), H8, W8, 3), np.uint8)
            stacks[k][j] = f
            if q == ult[k]:
                reg = gravar_mapa(k, stacks.pop(k))
                reg["quadros"] = pedidos[k]
                gravar_registro(k, reg)
                out[k] = reg
                if len(out) % 25 == 0:
                    print(f"trecho {i0}: {len(out)}/{len(pedidos)} mapas  {time.time() - t0:.0f} s", flush=True)
        q += 1
    for k in stacks:
        avisos.append(f"mapa {k}: o vídeo acabou antes do quadro {ult[k]} (não gravado)")
    return out, avisos


def gerar(ids=None, forcar=False, procs=PROCS):
    anos = json.load(open(os.path.join(V2, "anos.json")))
    mapas = json.load(open(os.path.join(V2, "mapas.json")))
    if not forcar and recolher_registros(mapas):
        tmp = os.path.join(V2, "mapas.json.tmp")
        json.dump(mapas, open(tmp, "w"))
        os.replace(tmp, os.path.join(V2, "mapas.json"))
    corr = corridas()
    pedidos = {}
    for k, m in mapas.items():
        if ids and k not in ids:
            continue
        if not forcar and pronto(k) and m.get("mediana"):
            continue
        cap = max(anos[str(a)]["quadro_mapa"] for a in m["anos"] if str(a) in anos) if m.get("anos") else m["quadro"]
        ini, fim = corr.get(int(k), (m["quadro"], m["quadro"]))
        pedidos[k] = escolher(ini, fim, cap)
    trechos = quadros.tarefas()
    por_trecho = {t: {} for t in trechos}
    for k, qs in pedidos.items():
        t = next(t for t in trechos if t[0] <= qs[0] < t[0] + t[1])
        if qs[-1] >= t[0] + t[1]:
            qs = [q for q in qs if q < t[0] + t[1]] or [qs[0]]          # não deve acontecer (mud = -1 nos limites)
            if len(qs) % 2 == 0:
                qs = qs[1:]
        por_trecho[t][k] = qs
    print(f"quadros medianos: {len(pedidos)} mapas a gravar ({len(mapas) - len(pedidos)} prontos), "
          f"{sum(len(q) for q in pedidos.values())} quadros 8K a decodificar, {procs} processos", flush=True)
    t0 = time.time()
    feitos, avisos = {}, []
    with ProcessPoolExecutor(procs) as ex:
        for out, av in ex.map(trecho, [(t, por_trecho[t]) for t in trechos if por_trecho[t]]):
            feitos.update(out)
            avisos.extend(av)
            # registra o que já saiu (retomada): relê o mapas.json para não perder nada gravado por outro passo
            mapas = json.load(open(os.path.join(V2, "mapas.json")))
            recolher_registros(mapas)
            for k, reg in out.items():
                mapas[k]["mediana"] = reg
            tmp = os.path.join(V2, "mapas.json.tmp")
            json.dump(mapas, open(tmp, "w"))
            os.replace(tmp, os.path.join(V2, "mapas.json"))
    suspeitos = sorted(((r["dif_max_1920"], k) for k, r in feitos.items() if r["dif_max_1920"] > quadros.LIMIAR_MUDANCA), reverse=True)
    print(f"gravados {len(feitos)} mapas em {time.time() - t0:.0f} s; quadros por mediana: "
          f"mediana {int(np.median([r['n'] for r in feitos.values()])) if feitos else 0}; "
          f"{len(suspeitos)} com diferença > {quadros.LIMIAR_MUDANCA} entre quadros: {suspeitos[:10]}")
    for a in avisos:
        print("AVISO:", a)
    return feitos


def gravar_de_corrida(k, ini, fim, cap=None):
    """Para transicoes.py: a mediana dos quadros [ini, min(fim, cap)] de um mapa (busca única no vídeo)."""
    qs = escolher(ini, fim, cap)
    stack = np.empty((len(qs), H8, W8, 3), np.uint8)
    j = 0
    for q, f in zip(range(qs[0], qs[-1] + 1), quadros.decodificar(qs[0], qs[-1] - qs[0] + 1, W8, H8, threads=8)):
        if q == qs[j]:
            stack[j] = f
            j += 1
            if j == len(qs):
                break
    reg = gravar_mapa(k, stack[:j] if j else stack[:1])
    reg["quadros"] = qs[:j]
    gravar_registro(k, reg)
    return reg


if __name__ == "__main__":
    args = sys.argv[1:]
    procs = PROCS
    if "--procs" in args:
        i = args.index("--procs")
        procs = int(args[i + 1])
        del args[i:i + 2]
    forcar = "--forcar" in args
    ids = [a for a in args if not a.startswith("--")]
    gerar(ids or None, forcar, procs)
