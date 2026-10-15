#!/usr/bin/env python3
# E5 do mapa geral (v2): transforma a imagem de rótulos de cada mapa distinto em polígonos lon/lat que seguem as
# regras de borda do AGENTS.md (cobertura sem frestas nem sobreposição, borda comum única, só retas com o tremor de
# scripts/mapa/tremor.py, costa exata de frontend/mapa/mundo.json).
# Uso (na raiz do repositório):
#   PYTHONPATH=~/.cache/mapa-biblia-lib/lib python3 scripts/mapa-geral/vetorizar.py [id ...] [--amostra rapida|media|todos]
#                                                                                   [--forcar] [--adotar]
# Com cache (docs/mapa-geral-incremental.md): um mapa só é vetorizado de novo se mudou o conteúdo dos rótulos dele,
# a calibração, mundo.json, TOL_PX, PASSO_TREMOR ou a VERSAO. Manifesto em .cache/v2/e5/manifesto.json.
# Lê .cache/v2/rotulos/<id>.png e .json (E4), .cache/v2/calibracao.json (E3) e frontend/mapa/mundo.json.
# Grava .cache/v2/vetores/<id>.json:
#   {"regioes": {"<r>": {"tipo": "estado"|"sem-dono", "cor": [R,G,B], "aneis": [[[lon, lat], ...], ...]}},
#    "preenchidas": {"<r>": área em grau² recebida de terra de mundo.json que o vídeo deixa como mar}}
#   "aneis" segue a regra par-ímpar do site (o primeiro anel de cada parte é o exterior, os seguintes são buracos).
#   Regiões novas (r > maior r da E4) são terra de mundo.json que o vídeo não pinta (ilhas que ele não desenha): sem-dono.
#
# Passos:
#  1. Contornos exatos por pixel: as fronteiras entre rótulos viram segmentos nas arestas da grade de pixels
#     (não nos centros), quebrados onde o par de rótulos muda, e shapely.polygonize monta as faces. As faces já
#     formam uma cobertura perfeita em pixels (o mar, rótulo 0, também é face).
#  2. Pixel -> lon/lat com a calibração da E3 (cilíndrica de Miller): lon = (u + X0)/S - 180;
#     lat = (atan(exp(rad(y/1,25))) - 45°)/0,4, y = miller(80) - (v + Y0)/S. A transformação é monotônica e a
#     cobertura continua válida.
#  3. shapely.coverage_simplify com tolerância TOL_PX pixels (convertida para graus pela escala do mapa): tira a
#     escada dos pixels mantendo a borda comum idêntica nos dois vizinhos.
#  4. tremer() de scripts/mapa/tremor.py em cada anel, com passo de 0,25° (amplitude padrão 0,045°): o tremor
#     depende só do lado (não do sentido), então a borda comum continua com os mesmos pontos nos dois vizinhos.
#  5. Corte pela terra de mundo.json (anéis de terra em par-ímpar menos todos os lagos, como no site): a costa é a
#     de mundo.json. O mar (rótulo 0) sai. Terra de mundo.json que nenhuma região cobre (o vídeo a deixa como mar a
#     mais de 8 px da costa) vai para a região com a maior fronteira comum, ou vira região sem-dono se não tocar
#     nenhuma (ilha que o vídeo não desenha).
#  6. Longitudes cortadas em [-180, 180] (o quadro do mundo inteiro passa 0,1° de 180).
#  7. 5 casas decimais (o arredondamento para o site, 2 casas, é da E8). O arredondamento é o mesmo para o mesmo
#     vértice nos dois vizinhos; polígono que fique inválido é refeito com make_valid (só a parte poligonal).
import json, math, os, sys, time
from concurrent.futures import ProcessPoolExecutor

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/.cache/mapa-biblia-lib/lib"))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(AQUI, "..", "mapa"))
import numpy as np
import cv2
import shapely
from shapely.geometry import Polygon, MultiPolygon, box
from shapely.ops import unary_union
from tremor import tremer, chave_lado
import cache

RAIZ = os.path.normpath(os.path.join(AQUI, "..", ".."))
CACHE = os.environ.get("MAPA_GERAL_CACHE") or os.path.join(AQUI, ".cache")
V2 = os.path.join(CACHE, "v2")
MUNDO = os.path.join(RAIZ, "frontend", "mapa", "mundo.json")
TOL_PX = 1.0            # tolerância do coverage_simplify, em pixels do quadro (0,6 deixava a escada dos pixels nas diagonais)
CASAS = 5               # casas decimais do vetor da E5 (~1 m); o arredondamento do site (2 casas) é feito na E8
RAIO_SEM_TREMOR = 0.15  # graus: em volta de um cruzamento causado pelo tremor, os lados ficam retos
PASSO_TREMOR = 0.25     # graus: com o passo padrão (0,35) um lado de até 0,7° ficava sem quebrar; 0,25 garante <= 0,5°
LAT_TOPO = 80.0


def miller(lat):
    return 1.25 * math.degrees(math.log(math.tan(math.pi / 4 + 0.4 * math.radians(lat))))


def carregar_terra():
    """Terra de mundo.json: anéis de terra em par-ímpar menos os lagos (o que o site desenha)."""
    w = json.load(open(MUNDO))
    terra = None
    for f in w["fundo"]:
        if f["tipo"] != "terra":
            continue
        for a in f["aneis"]:
            if len(a) < 3:
                continue
            p = Polygon(a)
            p = p if p.is_valid else p.buffer(0)
            terra = p if terra is None else terra.symmetric_difference(p)
    lagos = [Polygon(f["pontos"]).buffer(0) for f in w["fundo"] if f["tipo"] == "mar" and len(f["pontos"]) >= 3]
    return terra.difference(unary_union(lagos)), unary_union(lagos)


def segmentos(reg):
    """Arestas da grade entre pixels de rótulos diferentes (borda da imagem incluída), em coordenadas de canto de
    pixel, juntadas em corridas enquanto o par de rótulos dos dois lados não muda."""
    H, W = reg.shape
    r = np.full((H + 2, W + 2), -1, np.int64)
    r[1:-1, 1:-1] = reg
    segs = []
    # horizontais: entre a linha y-1 e y (y = 0..H), x de 0..W-1
    cima, baixo = r[:-1, 1:-1], r[1:, 1:-1]          # (H+1) × W
    dif = cima != baixo
    par = cima * 70000 + baixo
    for y in range(H + 1):
        d = dif[y]
        if not d.any():
            continue
        p = par[y]
        quebra = np.ones(W, bool)
        quebra[1:] = (p[1:] != p[:-1]) | ~d[:-1]
        ini = np.where(d & quebra)[0]
        fim_mask = np.ones(W, bool)
        fim_mask[:-1] = (p[1:] != p[:-1]) | ~d[1:]
        fim = np.where(d & fim_mask)[0]
        for a, b in zip(ini, fim):
            segs.append(((a, y), (b + 1, y)))
    # verticais: entre a coluna x-1 e x (x = 0..W), y de 0..H-1
    esq, dir_ = r[1:-1, :-1], r[1:-1, 1:]           # H × (W+1)
    dif = (esq != dir_).T                              # (W+1) × H
    par = (esq * 70000 + dir_).T
    for x in range(W + 1):
        d = dif[x]
        if not d.any():
            continue
        p = par[x]
        quebra = np.ones(H, bool)
        quebra[1:] = (p[1:] != p[:-1]) | ~d[:-1]
        ini = np.where(d & quebra)[0]
        fim_mask = np.ones(H, bool)
        fim_mask[:-1] = (p[1:] != p[:-1]) | ~d[1:]
        fim = np.where(d & fim_mask)[0]
        for a, b in zip(ini, fim):
            segs.append(((x, a), (x, b + 1)))
    return segs


def poligonos_pixel(reg):
    """{rótulo: (Multi)Polygon em coordenadas de pixel}, cobertura exata da imagem."""
    segs = segmentos(reg)
    linhas = shapely.linestrings(np.array(segs, np.float64))
    faces = shapely.get_parts(shapely.polygonize(linhas))
    pts = shapely.get_coordinates(shapely.point_on_surface(faces))
    H, W = reg.shape
    xs = np.clip(np.floor(pts[:, 0]).astype(int), 0, W - 1)
    ys = np.clip(np.floor(pts[:, 1]).astype(int), 0, H - 1)
    rot = reg[ys, xs]
    por = {}
    for f, r in zip(faces, rot.tolist()):
        por.setdefault(int(r), []).append(f)
    return {r: (fs[0] if len(fs) == 1 else MultiPolygon(fs)) for r, fs in por.items()}


def para_lonlat(g, cal):
    S, X0, Y0 = cal["S"], cal["X0"], cal["Y0"]
    m80 = miller(LAT_TOPO)

    def f(c):
        lon = (c[:, 0] + X0) / S - 180.0
        y = m80 - (c[:, 1] + Y0) / S
        t = np.exp(np.radians(y / 1.25))
        lat = np.degrees((np.arctan(t) - np.pi / 4) / 0.4)
        return np.stack([lon, lat], axis=1)
    return shapely.transform(g, f)


def tremer_poligono(p, sem_tremor=None):
    """tremer() em cada anel de um Polygon (os lados de sem_tremor ficam retos)."""
    ext = tremer(list(p.exterior.coords)[:-1], passo=PASSO_TREMOR, sem_tremor=sem_tremor)
    if len(set(ext)) < 3:
        return Polygon()            # parte degenerada (2 vértices depois da simplificação)
    furos = [tremer(list(i.coords)[:-1], passo=PASSO_TREMOR, sem_tremor=sem_tremor) for i in p.interiors]
    return Polygon(ext, [h for h in furos if len(set(h)) >= 3])


def tremer_cobertura(simp):
    """Tremor em todos os polígonos da cobertura. Onde o tremor faz um polígono se cruzar (as duas margens de um
    canal ou de uma península fina), os lados do polígono simplificado a até RAIO_SEM_TREMOR graus do cruzamento
    ficam retos — em TODOS os polígonos, pela chave do lado — e repete. Assim a borda comum continua idêntica nos
    dois vizinhos; consertar cada polígono com make_valid a quebraria."""
    sem = set()
    lados = []      # (chave, x0, y0, x1, y1) de todos os lados da cobertura simplificada
    for g in simp:
        for p in partes(g):
            for anel in [p.exterior] + list(p.interiors):
                c = list(anel.coords)
                for a, b in zip(c[:-1], c[1:]):
                    lados.append((chave_lado(a, b), a[0], a[1], b[0], b[1]))
    seg = np.array([[l[1], l[2], l[3], l[4]] for l in lados]) if lados else np.zeros((0, 4))
    for _rodada in range(20):
        tremidos = []
        cruzamentos = []
        for g in simp:
            ps = [q for q in (tremer_poligono(p, sem) for p in partes(g)) if not q.is_empty]
            t = MultiPolygon(ps) if len(ps) > 1 else (ps[0] if ps else Polygon())
            if not t.is_valid:
                motivo = shapely.is_valid_reason(t)
                if "[" in motivo:
                    xy = motivo[motivo.index("[") + 1:motivo.index("]")].split()
                    cruzamentos.append((float(xy[0]), float(xy[1])))
            tremidos.append(t)
        if not cruzamentos:
            return tremidos, len(sem)
        antes = len(sem)
        for x, y in cruzamentos:
            # distância do ponto a cada lado
            ax, ay, bx, by = seg[:, 0], seg[:, 1], seg[:, 2], seg[:, 3]
            dx, dy = bx - ax, by - ay
            t_ = np.clip(((x - ax) * dx + (y - ay) * dy) / np.maximum(dx * dx + dy * dy, 1e-18), 0, 1)
            d = np.hypot(ax + t_ * dx - x, ay + t_ * dy - y)
            for j in np.where(d <= RAIO_SEM_TREMOR)[0]:
                sem.add(lados[j][0])
        if len(sem) == antes:
            break           # nada novo a desligar: sai e deixa valido() consertar (não deve acontecer)
    return [valido(t) for t in tremidos], len(sem)


def so_poligonos(g):
    if g.is_empty:
        return Polygon()
    if g.geom_type in ("Polygon", "MultiPolygon"):
        return g
    ps = [x for x in shapely.get_parts(g) if x.geom_type in ("Polygon", "MultiPolygon")]
    return unary_union(ps) if ps else Polygon()


def recorte(g, x0, y0, x1, y1):
    """clip_by_rect; em alguns retângulos o GEOS 3.14 falha ("LinearRing found 3") e a interseção com a caixa
    dá o mesmo recorte."""
    try:
        return shapely.clip_by_rect(g, x0, y0, x1, y1)
    except shapely.errors.GEOSException:
        return g.intersection(box(x0, y0, x1, y1))


def partes(g):
    return [x for x in shapely.get_parts(g) if x.geom_type == "Polygon" and not x.is_empty]


def aneis_de(g):
    out = []
    for p in partes(g):
        for anel in [p.exterior] + list(p.interiors):
            cs = [[round(x, CASAS), round(y, CASAS)] for x, y in list(anel.coords)[:-1]]
            if len({tuple(c) for c in cs}) >= 3 and Polygon(cs).area > 0:
                out.append(cs)
    return out


def valido(g):
    """Versão válida (só polígonos). make_valid "structure"; se o GEOS recusar (entrada de dimensão mista depois do
    arredondamento), conserta parte por parte e une."""
    if g.is_valid:
        return g
    try:
        return so_poligonos(shapely.make_valid(g, method="structure", keep_collapsed=False))
    except shapely.errors.GEOSException:
        ps = []
        for p in partes(g):
            try:
                ps.append(so_poligonos(shapely.make_valid(p, method="structure", keep_collapsed=False)))
            except shapely.errors.GEOSException:
                ps.append(so_poligonos(shapely.make_valid(Polygon(p.exterior))))
        return so_poligonos(unary_union([q for q in ps if not q.is_empty])) if ps else Polygon()


def arredondar(g):
    """CASAS casas decimais em todos os vértices; refaz como válido se precisar. Com 2 casas, os vértices que o
    corte pela costa cria sobre ela (o tremor cruza a costa várias vezes) saíam da costa em até 0,007° e formavam
    lascas fora da terra e sobreposições; o arredondamento do site fica para a E8, sobre a cobertura inteira."""
    return valido(shapely.transform(g, lambda c: np.round(c, CASAS)))


def vetorizar_mapa(reg, info, cal, terra, terra_prep_idx):
    """Devolve (regioes {r: geom lon/lat final}, preenchidas {r: área}, tipos, métricas)."""
    pol = poligonos_pixel(reg)
    ids = sorted(pol)
    geoms = [para_lonlat(pol[r], cal) for r in ids]
    tol = TOL_PX / cal["S"]
    simp = shapely.coverage_simplify(np.array(geoms, dtype=object), tol)
    # tremor (inclui o mar, para a fronteira terra/mar do vídeo ficar igual dos dois lados antes do corte)
    tremidos, n_retos = tremer_cobertura(list(simp))
    metricas = {"cobertura_simplificada": bool(shapely.coverage_is_valid(np.array(list(simp), dtype=object))),
                "cobertura_tremida": bool(shapely.coverage_is_valid(np.array(tremidos, dtype=object))),
                "lados_sem_tremor": n_retos}
    # corte pela terra de mundo.json (só a parte da terra sob a caixa de cada região)
    regioes = {}
    for r, g in zip(ids, tremidos):
        if r == 0 or g.is_empty:
            continue
        x0, y0, x1, y1 = g.bounds
        t = recorte(terra, x0 - 0.01, y0 - 0.01, x1 + 0.01, y1 + 0.01)
        c = so_poligonos(g.intersection(t))
        c = so_poligonos(recorte(c, -180.0, -90.0, 180.0, 90.0))
        if not c.is_empty:
            regioes[r] = c
    # terra de mundo.json dentro do quadro que nenhuma região cobre
    quadro = so_poligonos(unary_union(tremidos))
    xq0, yq0, xq1, yq1 = quadro.bounds
    terra_q = so_poligonos(recorte(terra, max(-180.0, xq0), yq0, min(180.0, xq1), yq1).intersection(quadro))
    cobertas = unary_union(list(regioes.values())) if regioes else Polygon()
    falta = so_poligonos(terra_q.difference(cobertas))
    preenchidas = {}
    novo = max([int(x["r"]) for x in info["regioes"]] + [0]) + 1
    tipos = {int(x["r"]): x["tipo"] for x in info["regioes"]}
    ordem = sorted(regioes)
    arvore = shapely.STRtree([regioes[r] for r in ordem])
    for pedaco in partes(falta):
        if pedaco.area < 1e-9:
            continue
        cand = arvore.query(pedaco, predicate="intersects")
        melhor, comp = None, 0.0
        for j in cand:
            r = ordem[j]
            L = pedaco.boundary.intersection(regioes[r].boundary).length
            if L > comp:
                melhor, comp = r, L
        if melhor is None:
            regioes[novo] = pedaco
            tipos[novo] = "sem-dono"
            preenchidas[novo] = pedaco.area
            novo += 1
        else:
            regioes[melhor] = so_poligonos(regioes[melhor].union(pedaco))
            preenchidas[melhor] = preenchidas.get(melhor, 0.0) + pedaco.area
    final = {r: arredondar(g) for r, g in regioes.items()}
    final = {r: g for r, g in final.items() if not g.is_empty}
    metricas["quadro"] = [round(v_, 4) for v_ in quadro.bounds]
    return final, preenchidas, tipos, metricas


VERSAO = 4      # incremente quando a lógica da E5 mudar (2: 5 casas, TOL_PX 1,0; 3: lados sem tremor nos cruzamentos;
                # 4: lado sem tremor quebrado em pedaços retos colineares de <= PASSO_TREMOR)


def chave_mapa(k, cal_k, mundo_h):
    """Chave da E5 para um mapa: conteúdo dos rótulos (png e json), calibração, mundo.json, parâmetros e VERSAO."""
    return cache.chave(VERSAO, {"TOL_PX": TOL_PX, "PASSO_TREMOR": PASSO_TREMOR, "CASAS": CASAS, "RAIO_SEM_TREMOR": RAIO_SEM_TREMOR},
                       [cache.hash_arquivo(os.path.join(V2, "rotulos", f"{k}.png")),
                        cache.hash_arquivo(os.path.join(V2, "rotulos", f"{k}.json")), cache.hash_obj(cal_k), mundo_h])


def tarefa(args):
    ids, man, forcar = args
    cal = json.load(open(os.path.join(V2, "calibracao.json")))["por_mapa"]
    mundo_h = cache.hash_arquivo(MUNDO)
    terra = None
    saida = os.path.join(V2, "vetores")
    os.makedirs(saida, exist_ok=True)
    tempos, novas = {}, {}
    for k in ids:
        ch = chave_mapa(k, cal[k], mundo_h)
        arq = os.path.join(saida, f"{k}.json")
        if not forcar and not cache.precisa(man, k, ch, arq):
            continue
        if terra is None:
            terra, _ = carregar_terra()
            shapely.prepare(terra)
        t0 = time.time()
        reg = cv2.imread(os.path.join(V2, "rotulos", f"{k}.png"), cv2.IMREAD_UNCHANGED)
        info = json.load(open(os.path.join(V2, "rotulos", f"{k}.json")))
        try:
            final, preenchidas, tipos, metricas = vetorizar_mapa(reg, info, cal[k], terra, None)
        except Exception as e:      # registra e segue; a lista de falhas sai no fim
            tempos[k] = {"falha": f"{type(e).__name__}: {e}"}
            continue
        cores = {int(x["r"]): x["cor"] for x in info["regioes"]}
        out = {"regioes": {str(r): {"tipo": tipos.get(r, "sem-dono"), "cor": cores.get(r, [255, 255, 255]),
                                    "aneis": aneis_de(g)} for r, g in sorted(final.items())},
               "preenchidas": {str(r): round(a, 4) for r, a in preenchidas.items()}, "metricas": metricas}
        tmp = os.path.join(saida, f"{k}.json.tmp")
        json.dump(out, open(tmp, "w"), separators=(",", ":"))
        os.replace(tmp, arq)
        tempos[k] = time.time() - t0
        novas[k] = {"chave": ch, "hash_saida": cache.hash_arquivo(arq), "segundos": round(tempos[k], 3)}
    return tempos, novas


def main():
    mapas = json.load(open(os.path.join(V2, "mapas.json")))
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    amostra = "todos"
    if "--amostra" in sys.argv:
        amostra = sys.argv[sys.argv.index("--amostra") + 1]
        args = [x for x in args if x != amostra]
    if args:
        ids = args
    elif amostra == "todos":
        ids = sorted(mapas, key=lambda k: mapas[k]["quadro"])
    else:
        ids = json.load(open(os.path.join(AQUI, "amostras.json")))[amostra]["ids"]
    man = cache.manifesto("e5")
    if "--adotar" in sys.argv:
        # registra no manifesto vetores JÁ gravados por esta VERSAO do código (sem recalcular). Usar só quando se
        # sabe que o arquivo saiu exatamente deste código e destes rótulos; o T-C1 confere uma amostra.
        cal = json.load(open(os.path.join(V2, "calibracao.json")))["por_mapa"]
        mundo_h = cache.hash_arquivo(MUNDO)
        for k in ids:
            arq = os.path.join(V2, "vetores", f"{k}.json")
            if os.path.exists(arq):
                man[k] = {"chave": chave_mapa(k, cal[k], mundo_h), "hash_saida": cache.hash_arquivo(arq), "segundos": None}
        cache.gravar_manifesto("e5", man)
        print("adotados:", len(ids))
        return
    t0 = time.time()
    lotes = [ids[i:i + 6] for i in range(0, len(ids), 6)]
    tempos = {}
    from concurrent.futures import as_completed
    n = 0
    with ProcessPoolExecutor(8) as ex:
        futs = [ex.submit(tarefa, (l, man, "--forcar" in sys.argv)) for l in lotes]
        for f in as_completed(futs):
            te, novas = f.result()
            tempos.update(te)
            if novas:
                man.update(novas)
                cache.gravar_manifesto("e5", man)
            n += 1
            if n % 20 == 0 or n == len(lotes):
                dec = time.time() - t0
                print(f"lotes {n}/{len(lotes)}  vetorizados={len(tempos)}  {dec:.0f} s, faltam ~{dec / n * (len(lotes) - n):.0f} s", flush=True)
    falhas = {k: v["falha"] for k, v in tempos.items() if isinstance(v, dict)}
    resumo = {"mapas": len(ids), "recalculados": len(tempos) - len(falhas), "segundos_total": round(time.time() - t0, 1),
              "falhas": falhas}
    json.dump(resumo, open(os.path.join(V2, "vetores-tempo.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in resumo.items() if k != "falhas"}))
    if falhas:
        print("FALHAS:", len(falhas), json.dumps(falhas, ensure_ascii=False)[:2000])


if __name__ == "__main__":
    main()
