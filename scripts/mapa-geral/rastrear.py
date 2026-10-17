#!/usr/bin/env python3
# E6 do mapa geral (v2): dá a cada estado um id que dura toda a vida dele (entidade), ano a ano.
# Uso (na raiz do repositório):  PYTHONPATH=~/.cache/mapa-biblia-lib/lib python3 scripts/mapa-geral/rastrear.py
#                                  [--variante <nome>] [--forcar] [--fonte e7u]
# Loja por chave (cache.py): o resultado fica em .cache/v2/obj/e6/<chave>.json; entidades.json é um apontador para a
# variante aprovada. A chave sai dos parâmetros, de anos.json e das chaves dos vetores (E5) usados.
# Lê .cache/v2/anos.json (mapa de cada ano) e .cache/v2/vetores/<id>.json (E5) ou, com --fonte e7u, os vetores com as
# uniões da E7 (.cache/v2/vetores-e7/<id>.json; a E6 é refeita depois das uniões da E7).
# Grava .cache/v2/entidades.json:
#   {"entidades": {"<ent>": {"anos": [de, ate], "cor": "#rrggbb", "trechos": [[ano_de, ano_ate, mapa, [r, ...]], ...]}},
#    "por_ano": [[ano_de, ano_ate, mapa, {"<r>": "<ent>"}], ...],     (corridas de anos com o mesmo mapa)
#    "eventos": {...}}                                                 (recolorações, divisões, fusões, contagens)
# Ids "e00001"... na ordem em que aparecem (2500 a.C. -> 2025 d.C.); a E7 dá os nomes.
#
# Regras (docs/mapa-geral-plano-2.md, E6):
#  - Anos seguidos com o mesmo mapa: mesmas regiões, mesmos ids.
#  - Mapa novo: as regiões de estado dos dois mapas são rasterizadas numa grade comum de 0,1° (equiretangular) e
#    casadas pela sobreposição: pares (região antiga, região nova) ordenados pela área comum, cada um casado no
#    máximo uma vez (o maior pedaço de uma divisão herda o id; numa fusão, herda o id da maior sobreposição). O par
#    só vale se a cor bater (L1 <= LIM_COR) ou se a forma for quase a mesma (IoU >= 0,8: o vídeo recoloriu o estado;
#    registrado). Só herda id quem existia no mapa anterior: uma cor reaproveitada séculos depois vira id novo.
#  - Antimeridiano: no mundo inteiro o quadro corta a Rússia/Alasca em ±180°; duas regiões de estado da mesma cor
#    (L1 <= 20) que tocam as duas bordas do quadro (oeste e leste) na mesma faixa de latitude são a mesma entidade.
import json, os, sys, time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/.cache/mapa-biblia-lib/lib"))
import numpy as np
import cv2
sys.path.insert(0, AQUI)
import cache

CACHE = os.environ.get("MAPA_GERAL_CACHE") or os.path.join(AQUI, ".cache")
V2 = os.path.join(CACHE, "v2")
PASSO = 0.1                 # graus por célula da grade comum
LON0, LAT1 = -180.0, 90.0
GW, GH = int(360 / PASSO), int(150 / PASSO)    # lon -180..180, lat 90..-60
LIM_COR = 60                # L1 entre as cores para herdar id (o vídeo varia poucos níveis; antialias)
IOU_RECOLOR = 0.8
MIN_CELULAS = 3             # sobreposição mínima (células de 0,1°) para casar
VERSAO = 1


FONTE = "e5"


def params():
    p = {"versao": VERSAO, "PASSO": PASSO, "LIM_COR": LIM_COR, "IOU_RECOLOR": IOU_RECOLOR, "MIN_CELULAS": MIN_CELULAS}
    if FONTE != "e5":
        p["FONTE"] = FONTE
    return p


def rasterizar(vet):
    """Grade int32 com o número da região de estado em cada célula (0 = mar/sem dono), regra par-ímpar por região."""
    g = np.zeros((GH, GW), np.int32)
    for r, d in vet["regioes"].items():
        if d["tipo"] != "estado":
            continue
        pol = []
        for a in d["aneis"]:
            a = np.asarray(a, np.float64)
            x = (a[:, 0] - LON0) / PASSO
            y = (LAT1 - a[:, 1]) / PASSO
            pol.append(np.round(np.stack([x, y], 1) * 16).astype(np.int32))
        t = np.zeros((GH, GW), np.uint8)
        cv2.fillPoly(t, pol, 1, shift=4)       # anéis no mesmo fillPoly: par-ímpar
        g[t > 0] = int(r)
    return g


def antimeridiano(vet):
    """Pares de regiões (oeste, leste) da mesma cor que tocam as duas bordas do quadro: a mesma entidade."""
    q = vet["metricas"]["quadro"]
    if q[2] - q[0] < 340:
        return []
    oeste, leste = [], []
    for r, d in vet["regioes"].items():
        if d["tipo"] != "estado":
            continue
        xs = np.concatenate([np.asarray(a)[:, 0] for a in d["aneis"]])
        ys = np.concatenate([np.asarray(a)[:, 1] for a in d["aneis"]])
        if xs.min() <= q[0] + 0.3:
            oeste.append((r, d["cor"], ys.min(), ys.max()))
        if xs.max() >= min(180.0, q[2]) - 0.3:
            leste.append((r, d["cor"], ys.min(), ys.max()))
    pares = []
    for ro, co, y0o, y1o in oeste:
        for rl, cl, y0l, y1l in leste:
            if ro != rl and sum(abs(a - b) for a, b in zip(co, cl)) <= 20 and min(y1o, y1l) > max(y0o, y0l):
                pares.append((ro, rl))
    return pares


def casar(ga, gb, va, vb):
    """{r_novo: r_antigo} e registro dos casamentos (área comum, IoU, recoloração)."""
    m = (ga > 0) & (gb > 0)
    if not m.any():
        return {}, []
    chave = ga[m].astype(np.int64) * 100000 + gb[m]
    u, c = np.unique(chave, return_counts=True)
    area_a = dict(zip(*np.unique(ga[ga > 0], return_counts=True)))
    area_b = dict(zip(*np.unique(gb[gb > 0], return_counts=True)))
    pares = []
    for kk, n in zip(u.tolist(), c.tolist()):
        ra, rb = divmod(kk, 100000)
        if n < MIN_CELULAS:
            continue
        iou = n / float(area_a[ra] + area_b[rb] - n)
        ca, cb = va["regioes"][str(ra)]["cor"], vb["regioes"][str(rb)]["cor"]
        dc = sum(abs(x - y) for x, y in zip(ca, cb))
        if dc <= LIM_COR or iou >= IOU_RECOLOR:
            pares.append((n, ra, rb, iou, dc))
    pares.sort(reverse=True)
    usados_a, usados_b, casou, reg = set(), set(), {}, []
    for n, ra, rb, iou, dc in pares:
        if ra in usados_a or rb in usados_b:
            continue
        usados_a.add(ra)
        usados_b.add(rb)
        casou[rb] = ra
        reg.append({"de": ra, "para": rb, "celulas": n, "iou": round(iou, 3), "dif_cor": dc, "recolor": dc > LIM_COR})
    return casou, reg


def hexa(c):
    return "#%02x%02x%02x" % tuple(int(v) for v in c)


def main():
    global FONTE
    t0 = time.time()
    if "--fonte" in sys.argv:
        FONTE = sys.argv[sys.argv.index("--fonte") + 1]
    variante_ = sys.argv[sys.argv.index("--variante") + 1] if "--variante" in sys.argv else None
    et = cache.Etapa("e6")
    # sem --variante: a aprovada, se foi feita com estes parâmetros (mesma fonte); senão "base" (a aprovada pode ser a
    # da E7, com FONTE e7u, e uma rodada nova da E5 recomeça pela base)
    aprovada = et.m["aprovada"]
    mesma = aprovada is not None and et.m["variantes"].get(aprovada, {}).get("params") == params()
    variante = variante_ or cache.exp_atual() or (aprovada if mesma else "base")
    et.garantir(variante, params())
    e5 = cache.Etapa(FONTE)
    anos = json.load(open(os.path.join(V2, "anos.json")))
    # chave: parâmetros + anos.json + a chave do vetor (E5) de cada mapa usado
    usados = sorted({str(d["mapa"]) for d in anos.values()}, key=int)
    var_e5 = cache.exp_atual() if cache.exp_atual() in e5.m["variantes"] else e5.m["aprovada"]
    chaves_e5 = [e5.itens(var_e5)[k]["chave"] for k in usados]
    ch = cache.chave(VERSAO, params(), [cache.hash_arquivo(os.path.join(V2, "anos.json")), cache.hash_obj(chaves_e5)])
    achado = None if "--forcar" in sys.argv else et.procurar("entidades", ch)
    if achado:
        et.m["variantes"][variante]["itens"]["entidades"] = achado
        et.gravar()
        if variante == et.m["aprovada"] or et.m["aprovada"] is None:
            et.aprovar(variante)
        print(f"e6: nada a recalcular (chave {ch[:10]}); variante {variante}")
        return
    ordem = list(anos)      # 2500 a.C. -> 2025 d.C.
    corridas = []           # [ano_de, ano_ate, mapa]
    for a in ordem:
        k = str(anos[a]["mapa"])
        if corridas and corridas[-1][2] == k:
            corridas[-1][1] = int(a)
        else:
            corridas.append([int(a), int(a), k])
    proximo = [0]

    def novo_id():
        proximo[0] += 1
        return "e%05d" % proximo[0]
    por_ano, eventos = [], {"recoloracoes": [], "novos": 0, "mapas": len(corridas)}
    ent_info = {}
    anterior = None          # (grade, vet, {r: ent})
    for i, (a_de, a_ate, k) in enumerate(corridas):
        vet = json.load(open(e5.caminho(k, ".json", var_e5)))
        g = rasterizar(vet)
        ids = {}
        if anterior is not None:
            casou, reg = casar(anterior[0], g, anterior[1], vet)
            for rb, ra in casou.items():
                if str(ra) in anterior[2]:
                    ids[str(rb)] = anterior[2][str(ra)]
            for x in reg:
                if x["recolor"]:
                    eventos["recoloracoes"].append(dict(x, ano=a_de, mapa=k))
        # antimeridiano: o pedaço sem id herda o do outro (ou os dois ganham o mesmo id novo)
        for ro, rl in antimeridiano(vet):
            if ro in ids and rl not in ids:
                ids[rl] = ids[ro]
            elif rl in ids and ro not in ids:
                ids[ro] = ids[rl]
            elif ro not in ids and rl not in ids:
                ids[ro] = ids[rl] = novo_id()
                eventos["novos"] += 1
        for r, d in vet["regioes"].items():
            if d["tipo"] == "estado" and r not in ids:
                ids[r] = novo_id()
                eventos["novos"] += 1
        por_ano.append([a_de, a_ate, k, ids])
        n_anos = ordem.index(str(a_ate)) - ordem.index(str(a_de)) + 1
        for r, e in sorted(ids.items(), key=lambda t: int(t[0])):
            inf = ent_info.setdefault(e, {"anos": [a_de, a_ate], "cores": {}, "trechos": []})
            inf["anos"][1] = a_ate
            cor = hexa(vet["regioes"][r]["cor"])
            inf["cores"][cor] = inf["cores"].get(cor, 0) + n_anos
            if inf["trechos"] and inf["trechos"][-1][0] == a_de and inf["trechos"][-1][2] == k:
                inf["trechos"][-1][3].append(int(r))           # mesma entidade em duas regiões (antimeridiano)
            else:
                inf["trechos"].append([a_de, a_ate, k, [int(r)]])
        anterior = (g, vet, ids)
        if i % 200 == 0:
            print(f"mapas {i}/{len(corridas)}  entidades {proximo[0]}  {time.time() - t0:.0f} s", flush=True)
    ents = {}
    for e, inf in ent_info.items():
        cor = max(inf["cores"].items(), key=lambda t: t[1])[0]      # a cor mais frequente ao longo da vida
        ents[e] = {"anos": inf["anos"], "cor": cor, "trechos": inf["trechos"]}
    eventos["entidades"] = len(ents)
    arq = et.obj(ch, ".json")
    json.dump({"entidades": ents, "por_ano": por_ano, "eventos": eventos}, open(arq + ".tmp", "w"), separators=(",", ":"))
    os.replace(arq + ".tmp", arq)
    et.m["variantes"][variante]["itens"]["entidades"] = {"chave": ch, "hash_saida": cache.hash_arquivo(arq),
                                                         "segundos": round(time.time() - t0, 1)}
    et.gravar()
    if variante == et.m["aprovada"] or et.m["aprovada"] is None:
        et.aprovar(variante)
    print(f"entidades {len(ents)}  corridas de mapa {len(corridas)}  recolorações {len(eventos['recoloracoes'])}  "
          f"{time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
