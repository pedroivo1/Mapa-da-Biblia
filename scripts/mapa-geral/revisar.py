#!/usr/bin/env python3
# Imagens de revisão do mapa geral v2 (a revisão visual é obrigatória em cada etapa; abra as imagens).
# Uso (na raiz do repositório):
#   PYTHONPATH=~/.cache/mapa-biblia-lib/lib python3 scripts/mapa-geral/revisar.py e1|e2|e3 [argumentos]
# Saída: .cache/v2/revisao/*.png
import json, os, random, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/.cache/mapa-biblia-lib/lib"))
sys.path.insert(0, AQUI)
import numpy as np
import cv2

RAIZ = os.path.normpath(os.path.join(AQUI, "..", ".."))
CACHE = os.environ.get("MAPA_GERAL_CACHE") or os.path.join(AQUI, ".cache")
V2 = os.path.join(CACHE, "v2")
SAIDA = os.path.join(V2, "revisao")
os.makedirs(SAIDA, exist_ok=True)


def desenhar_dados(ano, largura=1280):
    """Desenha frontend/mapa-geral/dados/<a|d><ano>.json (equiretangular, lon -20..150, lat 70..-10) com as cores do índice."""
    nome = ("a%d" % ano) if ano > 0 else ("d%d" % -ano)
    d = json.load(open(os.path.join(RAIZ, "frontend", "mapa-geral", "dados", nome + ".json")))
    idx = json.load(open(os.path.join(RAIZ, "frontend", "mapa-geral", "dados", "indice.json")))["estados"]
    lon0, lon1, lat1, lat0 = -20, 150, 70, -10
    e = largura / (lon1 - lon0)
    h = int((lat1 - lat0) * e)
    img = np.full((h, largura, 3), (237, 225, 216), np.uint8)
    for st in d["estados"]:
        c = idx.get(st["id"], {}).get("cor", "#888888")
        cor = (int(c[5:7], 16), int(c[3:5], 16), int(c[1:3], 16))
        pol = [np.round(np.array([[(x - lon0) * e, (lat1 - y) * e] for x, y in a])).astype(np.int32) for a in st["aneis"]]
        t = np.zeros((h, largura), np.uint8)
        # par-ímpar entre anéis do mesmo estado
        cv2.fillPoly(t, pol, 255)
        img[t > 0] = cor
        cv2.polylines(img, pol, True, (30, 30, 30), 1, cv2.LINE_AA)
    cv2.putText(img, f"{ano} {'a.C.' if ano > 0 else 'd.C.'}  ({len(d['estados'])} estados)", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    return img


def e1(args):
    antes = os.path.join(V2, "antes")
    # "antes" = a pasta de dados da v1 salva antes da E1 (copiada para .cache/v2/antes/); se faltar, só mostra o depois
    for ano in (586, 1000):
        depois = desenhar_dados(ano)
        arq = os.path.join(antes, ("a%d" % ano) + ".json")
        partes = []
        if os.path.exists(arq):
            idx_antigo = os.path.join(antes, "indice.json")
            d = json.load(open(arq))
            idx = json.load(open(idx_antigo))["estados"] if os.path.exists(idx_antigo) else {}
            lon0, lon1, lat1, lat0 = -20, 150, 70, -10
            e = 1280 / (lon1 - lon0)
            h = int((lat1 - lat0) * e)
            img = np.full((h, 1280, 3), (237, 225, 216), np.uint8)
            for st in d["estados"]:
                c = idx.get(st["id"], {}).get("cor", "#888888")
                cor = (int(c[5:7], 16), int(c[3:5], 16), int(c[1:3], 16))
                pol = [np.round(np.array([[(x - lon0) * e, (lat1 - y) * e] for x, y in a])).astype(np.int32) for a in st["aneis"]]
                t = np.zeros((h, 1280), np.uint8); cv2.fillPoly(t, pol, 255); img[t > 0] = cor
                cv2.polylines(img, pol, True, (30, 30, 30), 1, cv2.LINE_AA)
            cv2.putText(img, f"ANTES (v1, com mapas antigos) {ano}", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
            partes.append(img)
        partes.append(depois)
        cv2.imwrite(os.path.join(SAIDA, f"e1-{ano}.png"), np.vstack(partes))
        print("e1:", os.path.join(SAIDA, f"e1-{ano}.png"))


def e2(args):
    """Folha com 40 caixas de ano sorteadas (imagem da caixa + ano lido) e gráfico de anos por segundo."""
    z = np.load(os.path.join(V2, "caixas.npz"))
    lidos = json.load(open(os.path.join(V2, "anos-lidos.json")))
    anos = json.load(open(os.path.join(V2, "anos.json")))
    chaves = z.files
    random.seed(7)
    amostra = random.sample(chaves, 40)
    cel_w, cel_h = 360, 90
    folha = np.full((cel_h * 10, cel_w * 4, 3), 255, np.uint8)
    for n, k in enumerate(amostra):
        r, c = divmod(n, 4)
        cx = cv2.cvtColor(cv2.resize(z[k], None, fx=1.4, fy=1.4), cv2.COLOR_GRAY2BGR)
        cx = cx[:cel_h, :cel_w - 140]
        folha[r * cel_h:r * cel_h + cx.shape[0], c * cel_w:c * cel_w + cx.shape[1]] = cx
        cv2.putText(folha, "OCR: " + lidos.get(k, "?"), (c * cel_w + 235, r * cel_h + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 200), 2)
    cv2.imwrite(os.path.join(SAIDA, "e2-caixas.png"), folha)
    # anos por segundo ao longo do vídeo
    fps = 30000 / 1001
    pontos = []
    for a, d in anos.items():
        if d.get("sem_quadro"):
            continue
        pontos.append((d["quadros"][0] / fps, int(a)))
    pontos.sort()
    taxa = {}
    for (t0, a0), (t1, a1) in zip(pontos, pontos[1:]):
        if t1 > t0:
            taxa.setdefault(int(t0 // 60), []).append(1.0 / (t1 - t0))
    print("e2: anos/s por minuto de vídeo:", {m: round(float(np.median(v)), 1) for m, v in sorted(taxa.items())})
    print("e2:", os.path.join(SAIDA, "e2-caixas.png"))


def e3(args):
    """Por trecho: quadro inteiro com a costa de mundo.json (vermelho, 1 px) e a costa do vídeo a > 12 px dela
    (magenta = "fora"), mais recortes ampliados (4x) nas bordas do quadro."""
    from calibrar import renderizar, carregar_mundo, merc, mascara_terra, regiao_valida
    cal = json.load(open(os.path.join(V2, "calibracao.json")))
    mapas = json.load(open(os.path.join(V2, "mapas.json")))
    terra, lagos = carregar_mundo()
    REGIOES = [("Coreia/China leste", 122, 36, 18), ("Filipinas/Japão", 130, 25, 18), ("Sri Lanka", 80.5, 8, 9), ("Américas (Caribe)", -80, 22, 18),
               ("Alasca", -150, 62, 18), ("Austrália", 145, -28, 20), ("Noruega/Islândia", 5, 63, 18)]
    kern = np.ones((3, 3), np.uint8)
    for t in [t for t in cal["trechos"] if t["n"] >= 20]:
        a, b = t["ids"]
        ids = sorted([k for k in mapas if mapas[a]["quadro"] <= mapas[k]["quadro"] <= mapas[b]["quadro"]], key=lambda k: mapas[k]["quadro"])
        k = ids[len(ids) // 2]
        p = cal["por_mapa"][k]
        im = cv2.imread(os.path.join(V2, "mapas", f"{k}.png"))
        tv, val = mascara_terra(im)
        r = renderizar(terra, lagos, p["S"], p["X0"], p["Y0"])
        br = cv2.morphologyEx(r, cv2.MORPH_GRADIENT, kern) > 0
        bv = cv2.morphologyEx(tv, cv2.MORPH_GRADIENT, kern) > 0
        dist = cv2.distanceTransform((~br).astype(np.uint8), cv2.DIST_L2, 3)
        fora = bv & (dist > 12) & (val > 0)
        out = im.copy()
        out[br] = (0, 0, 255)
        out[fora] = (255, 0, 255)
        cv2.imwrite(os.path.join(SAIDA, f"e3-trecho-S{t['S']}.png"), out)

        def px(lon, lat):
            return (lon + 180) * p["S"] - p["X0"], (merc(80.0) - merc(lat)) * p["S"] - p["Y0"]
        recs = []
        for nome, lon, lat, meia in REGIOES:
            u, v = px(lon, lat)
            u, v = int(u), int(v)
            if not (40 <= u < 1880 and 40 <= v < 920):
                continue
            hw = 80
            rec = out[max(0, v - 60):v + 60, max(0, u - hw):u + hw]
            rec = cv2.resize(rec, (480, 360), interpolation=cv2.INTER_NEAREST)
            cv2.putText(rec, nome, (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            recs.append(rec)
        if recs:
            while len(recs) % 2:
                recs.append(np.full_like(recs[0], 255))
            linhas = [np.hstack(recs[i:i + 2]) for i in range(0, len(recs), 2)]
            cv2.imwrite(os.path.join(SAIDA, f"e3-recortes-S{t['S']}.png"), np.vstack(linhas))
        print("e3:", t["S"], "mapa", k, "recortes:", len(recs))


# paleta de 20 cores bem separadas (Sasha Trubetskoy) para as imagens de rótulos; vizinhos nunca repetem cor
PALETA = [(230, 25, 75), (60, 180, 75), (255, 225, 25), (0, 130, 200), (245, 130, 48), (145, 30, 180), (70, 240, 240),
          (240, 50, 230), (210, 245, 60), (250, 190, 212), (0, 128, 128), (220, 190, 255), (170, 110, 40),
          (128, 0, 0), (170, 255, 195), (128, 128, 0), (255, 215, 180), (0, 0, 128), (128, 128, 128), (60, 60, 60)]


def vizinhos(reg):
    """Pares de regiões (> 0) que se tocam (4 conexões)."""
    pares = set()
    for a, b in ((reg[:, :-1], reg[:, 1:]), (reg[:-1, :], reg[1:, :])):
        d = (a != b) & (a > 0) & (b > 0)
        for x, y in set(zip(a[d].tolist(), b[d].tolist())):
            pares.add((min(x, y), max(x, y)))
    return pares


def colorir(reg, info):
    """Cor por região (BGR) com vizinhos sempre de cores diferentes da paleta; sem-dono em branco, mar em azul."""
    pares = vizinhos(reg)
    viz = {}
    for a, b in pares:
        viz.setdefault(a, set()).add(b)
        viz.setdefault(b, set()).add(a)
    cor = {}
    ordem = sorted(info["regioes"], key=lambda r: -r["area_px"])
    for r in ordem:
        if r["tipo"] == "sem-dono":
            cor[r["r"]] = (255, 255, 255)
            continue
        usadas = {cor[v] for v in viz.get(r["r"], ()) if v in cor}
        livre = [c for c in PALETA if c not in usadas]
        # entre as livres, a mais distante das cores dos vizinhos
        def dist_min(c):
            return min([sum(abs(x - y) for x, y in zip(c, u)) for u in usadas] or [999])
        cor[r["r"]] = max(livre, key=dist_min) if livre else (0, 0, 0)
    tab = np.zeros((reg.max() + 1, 3), np.uint8)
    tab[0] = (237, 225, 216)
    for k, c in cor.items():
        tab[k] = c[::-1]
    # distância mínima entre cores de vizinhos (estado × estado)
    dm = min([int(np.abs(tab[a].astype(int) - tab[b].astype(int)).sum()) for a, b in pares
              if info["regioes"][a - 1]["tipo"] == "estado" and info["regioes"][b - 1]["tipo"] == "estado"] or [999])
    return tab, dm


def imagem_rotulos(k, caixas_texto=True):
    reg = cv2.imread(os.path.join(V2, "rotulos", f"{k}.png"), cv2.IMREAD_UNCHANGED).astype(np.int32)
    info = json.load(open(os.path.join(V2, "rotulos", f"{k}.json")))
    tab, dm = colorir(reg, info)
    out = tab[reg]
    borda = np.zeros(reg.shape, bool)
    borda[:, 1:] |= reg[:, 1:] != reg[:, :-1]
    borda[1:, :] |= reg[1:, :] != reg[:-1, :]
    out[borda] = (0, 0, 0)
    if caixas_texto:
        for r in info["regioes"]:
            for x, y, w, h in r["texto"]:
                cv2.rectangle(out, (x, y), (x + w, y + h), (0, 0, 255), 1)
    return out, reg, info, dm


def e4(args):
    """Quadro | regiões (vizinhos com cores sempre diferentes, bordas pretas; quadradinhos vermelhos = caixas de
    texto guardadas para o OCR da E7). Anos dados ou os 12 padrão."""
    anos = json.load(open(os.path.join(V2, "anos.json")))
    lista = [int(a) for a in args] or [2000, 1200, 584, -31, -326, -700, -999, -1148, -1598, -1799, -1914, -2022]
    for ano in lista:
        k = str(anos[str(ano)]["mapa"])
        im = cv2.imread(os.path.join(V2, "mapas", f"{k}.png"))
        out, reg, info, dm = imagem_rotulos(k)
        cv2.imwrite(os.path.join(SAIDA, f"e4-{ano}.png"), np.hstack([im, out]))
        cv2.imwrite(os.path.join(SAIDA, f"e4-{ano}-regioes.png"), out)
        print("e4:", ano, "mapa", k, "regiões", len(info["regioes"]), "distância mínima entre cores vizinhas", dm)


def recorte(ano, lon0, lon1, lat0, lat1, nome, escala=3):
    """Quadro × rótulos, ampliado, numa caixa lon/lat."""
    from calibrar import merc
    anos = json.load(open(os.path.join(V2, "anos.json")))
    cal = json.load(open(os.path.join(V2, "calibracao.json")))["por_mapa"]
    k = str(anos[str(ano)]["mapa"])
    p = cal[k]
    def px(lon, lat):
        return int((lon + 180) * p["S"] - p["X0"]), int((merc(80.0) - merc(lat)) * p["S"] - p["Y0"])
    x0, y1 = px(lon0, lat0)
    x1, y0 = px(lon1, lat1)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(1920, x1), min(960, y1)
    im = cv2.imread(os.path.join(V2, "mapas", f"{k}.png"))
    out, reg, info, dm = imagem_rotulos(k)
    a = cv2.resize(im[y0:y1, x0:x1], None, fx=escala, fy=escala, interpolation=cv2.INTER_NEAREST)
    b = cv2.resize(out[y0:y1, x0:x1], None, fx=escala, fy=escala, interpolation=cv2.INTER_NEAREST)
    # número da região no centro de cada região visível (para conferir)
    for r in info["regioes"]:
        m = reg[y0:y1, x0:x1] == r["r"]
        if m.sum() < 30:
            continue
        ys, xs = np.where(m)
        j = len(ys) // 2
        cv2.putText(b, str(r["r"]), (int(xs[j]) * escala, int(ys[j]) * escala), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
    arq = os.path.join(SAIDA, f"e4-recorte-{nome}.png")
    sep = np.full((a.shape[0], 6, 3), 0, np.uint8)
    cv2.imwrite(arq, np.hstack([a, sep, b]))
    print("recorte:", arq, "mapa", k, "distância mínima entre cores vizinhas", dm)


def e4_recortes(args):
    recorte(-1799, -130, -60, 15, 55, "america-norte-1799")
    recorte(-1799, 0, 30, 43, 56, "europa-central-1799", escala=4)
    recorte(-1799, -18, 20, 4, 20, "sahel-1799", escala=3)


def e4_unioes(args):
    """Lista as uniões "estado cortado pelo nome" de todos os mapas e faz a folha: 20 sorteadas + 10 de maior área."""
    mapas = json.load(open(os.path.join(V2, "mapas.json")))
    so_anos = [int(a) for a in args if a.lstrip("-").isdigit()]
    if so_anos:
        anos_j = json.load(open(os.path.join(V2, "anos.json")))
        mapas = {str(anos_j[str(a)]["mapa"]): mapas[str(anos_j[str(a)]["mapa"])] for a in so_anos}
    todas = []
    por_mapa = {}
    for k in mapas:
        info = json.load(open(os.path.join(V2, "rotulos", f"{k}.json")))
        u = info.get("unioes", [])
        por_mapa[k] = len(u)
        for x in u:
            todas.append((k, x))
    cont = {}
    for n in por_mapa.values():
        cont[n] = cont.get(n, 0) + 1
    tipos = {}
    for _, x in todas:
        tipos[x.get("tipo", "letra")] = tipos.get(x.get("tipo", "letra"), 0) + 1
    print("uniões:", len(todas), tipos, "em", sum(1 for n in por_mapa.values() if n), "mapas; mapas por quantidade:", dict(sorted(cont.items())))
    if not so_anos:
        json.dump({"total": len(todas), "por_mapa": por_mapa, "unioes": [dict(x, mapa=k) for k, x in todas]},
                  open(os.path.join(SAIDA, "e4-unioes.json"), "w"))
    random.seed(11)
    if so_anos:
        # conferência de mapas específicos: as uniões entre partes claras (cremes) primeiro, depois as maiores
        claras = [t for t in todas if t[1].get("tipo") != "fragmento" and min(t[1]["areas"]) > 80]
        sorteio = sorted(claras, key=lambda t: -min(t[1]["areas"]))[:30]
        maiores = []
    else:
        sorteio = random.sample(todas, min(20, len(todas)))
        maiores = sorted(todas, key=lambda t: -sum(t[1]["areas"]))[:10]
    celulas = []
    for grupo, lista in (("sorteada", sorteio), ("maior", maiores)):
        for k, u in lista:
            im = cv2.imread(os.path.join(V2, "mapas", f"{k}.png"))
            reg = cv2.imread(os.path.join(V2, "rotulos", f"{k}.png"), cv2.IMREAD_UNCHANGED)
            x0, y0, x1, y1 = u["caixa_menor"]
            cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
            meia = max(40, (x1 - x0) // 2 + 25, (y1 - y0) // 2 + 25)
            xa, ya = max(0, cx - meia), max(0, cy - meia)
            xb, yb = min(1920, cx + meia), min(960, cy + meia)
            a = im[ya:yb, xa:xb].copy()
            m = reg[ya:yb, xa:xb] == u["r"]
            borda = m & ~cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
            b = a.copy()
            b[borda] = (0, 0, 255)
            cv2.rectangle(b, (x0 - xa, y0 - ya), (x1 - xa, y1 - ya), (255, 0, 255), 1)
            cel = np.hstack([cv2.resize(a, (240, 240), interpolation=cv2.INTER_NEAREST),
                             cv2.resize(b, (240, 240), interpolation=cv2.INTER_NEAREST)])
            anos_m = mapas[k]["anos"]
            cv2.putText(cel, f"{grupo} {anos_m[0]} {u.get('tipo', 'letra')} L={u['fracao_letra']} S={u.get('fracao_sem_linha', 0)} c={u['dif_cor']}", (4, 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1)
            celulas.append(cel)
    linhas = []
    for i in range(0, len(celulas), 3):
        fila = celulas[i:i + 3]
        while len(fila) < 3:
            fila.append(np.full_like(celulas[0], 255))
        linhas.append(np.hstack(fila))
    for n, i in enumerate(range(0, len(linhas), 5)):
        cv2.imwrite(os.path.join(SAIDA, f"e4-unioes-{n + 1}.png"), np.vstack(linhas[i:i + 5]))
    print("folhas:", (len(linhas) + 4) // 5)


def e4_pares(args):
    """Pares de regiões vizinhas de mesma cor (L1 <= 20) que ficaram separadas: folha para conferir se são estados
    diferentes (linha de contorno entre eles) ou um estado partido. Argumentos: anos (padrão 835 e 1927 d.C.)."""
    anos = json.load(open(os.path.join(V2, "anos.json")))
    celulas = []
    for ano in [int(a) for a in args] or [-835, -1927]:
        k = str(anos[str(ano)]["mapa"])
        im = cv2.imread(os.path.join(V2, "mapas", f"{k}.png"))
        reg = cv2.imread(os.path.join(V2, "rotulos", f"{k}.png"), cv2.IMREAD_UNCHANGED).astype(np.int32)
        info = json.load(open(os.path.join(V2, "rotulos", f"{k}.json")))["regioes"]
        pares = []
        for a, b in vizinhos(reg):
            ca, cb = np.array(info[a - 1]["cor"]), np.array(info[b - 1]["cor"])
            if np.abs(ca - cb).sum() <= 20 and info[a - 1]["tipo"] == info[b - 1]["tipo"] == "estado":
                pares.append((a, b))
        print("e4-pares:", ano, "pares de mesma cor separados:", len(pares))
        for a, b in pares:
            m = (reg == a) | (reg == b)
            ys, xs = np.where(m)
            cx, cy = int(np.median(xs)), int(np.median(ys))
            fr = np.zeros(reg.shape, bool)
            fr[:, 1:] |= ((reg[:, 1:] == a) & (reg[:, :-1] == b)) | ((reg[:, 1:] == b) & (reg[:, :-1] == a))
            fr[1:, :] |= ((reg[1:, :] == a) & (reg[:-1, :] == b)) | ((reg[1:, :] == b) & (reg[:-1, :] == a))
            fy, fx = np.where(fr)
            cx, cy = int(np.median(fx)), int(np.median(fy))
            meia = 45
            xa, ya, xb, yb = max(0, cx - meia), max(0, cy - meia), min(1920, cx + meia), min(960, cy + meia)
            o = im[ya:yb, xa:xb].copy()
            o2 = o.copy()
            bd = np.zeros(m.shape, bool)
            for v, cor in ((a, (0, 0, 255)), (b, (255, 0, 255))):
                mv = (reg == v).astype(np.uint8)
                e = mv.astype(bool) & ~cv2.erode(mv, np.ones((3, 3), np.uint8)).astype(bool)
                o2[e[ya:yb, xa:xb]] = cor
            cel = np.hstack([cv2.resize(o, (200, 200), interpolation=cv2.INTER_NEAREST),
                             cv2.resize(o2, (200, 200), interpolation=cv2.INTER_NEAREST)])
            cv2.putText(cel, f"{ano} {a}x{b}", (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
            celulas.append(cel)
    linhas = []
    for i in range(0, len(celulas), 4):
        fila = celulas[i:i + 4]
        while len(fila) < 4:
            fila.append(np.full_like(celulas[0], 255))
        linhas.append(np.hstack(fila))
    for n, i in enumerate(range(0, len(linhas), 5)):
        cv2.imwrite(os.path.join(SAIDA, f"e4-pares-{n + 1}.png"), np.vstack(linhas[i:i + 5]))
    print("folhas:", (len(linhas) + 4) // 5)


def equal_earth(lon, lat):
    """Equal Earth (como em compartilhado/js/projecao.js), em radianos de esfera unitária, y para o norte."""
    A1, A2, A3, A4 = 1.340264, -0.081106, 0.000893, 0.003796
    M = np.sqrt(3) / 2
    l = np.radians(lon)
    t = np.arcsin(M * np.sin(np.radians(lat)))
    t2 = t * t
    t6 = t2 * t2 * t2
    x = 2 * np.sqrt(3) * l * np.cos(t) / (3 * (A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2)))
    y = t * (A1 + A2 * t2 + t6 * (A3 + A4 * t2))
    return x, y


def desenhar_vetores(regioes, lon0, lon1, lat0, lat1, largura):
    """Polígonos (cor do vídeo, contorno preto fino) em Equal Earth, na caixa lon/lat dada."""
    xa, _ = equal_earth(np.array([lon0, lon1]), np.array([0.0, 0.0]))
    cx = (lon0 + lon1) / 2
    xs_c, ys_c = equal_earth(np.array([lon0, lon1, lon0, lon1, cx, cx]), np.array([lat0, lat0, lat1, lat1, lat0, lat1]))
    x_min, x_max, y_min, y_max = xs_c.min(), xs_c.max(), ys_c.min(), ys_c.max()
    esc = largura / (x_max - x_min)
    altura = int((y_max - y_min) * esc)
    img = np.full((altura, largura, 3), (237, 225, 216), np.uint8)
    contornos = []
    for r, d in regioes.items():
        pol = []
        for a in d["aneis"]:
            a = np.asarray(a, float)
            x, y = equal_earth(a[:, 0], a[:, 1])
            pol.append(np.round(np.stack([(x - x_min) * esc, (y_max - y) * esc], 1) * 16).astype(np.int32))
        if not pol:
            continue
        c = d["cor"]
        t = np.zeros(img.shape[:2], np.uint8)
        cv2.fillPoly(t, pol, 255, shift=4)
        img[t > 0] = (c[2], c[1], c[0])
        contornos += pol
    cv2.polylines(img, contornos, True, (20, 20, 20), 1, cv2.LINE_AA, shift=4)
    return img


def e5(args):
    """Para 12 anos: recortes (Levante/Mesopotâmia, Grécia/Egeu, Europa central, Índia, Ásia Central, antimeridiano)
    com o quadro do vídeo à esquerda e os polígonos finais (Equal Earth, cores do vídeo) à direita."""
    from calibrar import merc
    anos = json.load(open(os.path.join(V2, "anos.json")))
    cal = json.load(open(os.path.join(V2, "calibracao.json")))["por_mapa"]
    lista = [int(a) for a in args] or [2000, 1200, 584, -31, -326, -700, -999, -1148, -1598, -1799, -1914, -2022]
    RECORTES = [("Levante e Mesopotâmia", 30, 50, 27, 38), ("Grécia e Egeu", 19, 30, 34, 42),
                ("Europa central", 3, 25, 44, 56), ("Índia", 68, 92, 8, 30), ("Ásia Central", 55, 95, 34, 50),
                ("Antimeridiano (Alasca/Tchukotka)", -180, -140, 52, 72)]
    for ano in lista:
        k = str(anos[str(ano)]["mapa"])
        p = cal[k]
        im = cv2.imread(os.path.join(V2, "mapas", f"{k}.png"))
        vet = json.load(open(os.path.join(V2, "vetores", f"{k}.json")))["regioes"]
        linhas = []
        for nome, lo0, lo1, la0, la1 in RECORTES:
            u0 = int((lo0 + 180) * p["S"] - p["X0"])
            u1 = int((lo1 + 180) * p["S"] - p["X0"])
            v0 = int((merc(80.0) - merc(la1)) * p["S"] - p["Y0"])
            v1 = int((merc(80.0) - merc(la0)) * p["S"] - p["Y0"])
            if u0 < 0 or u1 > 1920 or v0 < 0 or v1 > 960 or u1 - u0 < 20:
                continue
            q = im[v0:v1, u0:u1]
            dir_ = desenhar_vetores(vet, lo0, lo1, la0, la1, 640)
            esq = cv2.resize(q, (640, int(q.shape[0] * 640 / q.shape[1])), interpolation=cv2.INTER_AREA)
            h = max(esq.shape[0], dir_.shape[0])
            pad = lambda x: np.vstack([x, np.full((h - x.shape[0], x.shape[1], 3), 255, np.uint8)])
            linha = np.hstack([pad(esq), np.full((h, 6, 3), 0, np.uint8), pad(dir_)])
            cv2.putText(linha, f"{ano} {nome}", (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
            linhas.append(linha)
        if linhas:
            cv2.imwrite(os.path.join(SAIDA, f"e5-{ano}.png"), np.vstack(linhas))
        print("e5:", ano, "mapa", k, "recortes", len(linhas))


def e6(args):
    """Filmes de 12 anos seguidos (3 trechos) com o id escrito no centro de cada estado, e folha das entidades
    curtas (< 3 anos)."""
    from calibrar import merc
    ent = json.load(open(os.path.join(V2, "entidades.json")))
    anos = json.load(open(os.path.join(V2, "anos.json")))
    cal = json.load(open(os.path.join(V2, "calibracao.json")))["por_mapa"]
    ordem = [int(a) for a in anos]
    pos = {a: i for i, a in enumerate(ordem)}
    corr_pos = {}
    for i, c in enumerate(ent["por_ano"]):
        for p in range(pos[c[0]], pos[c[1]] + 1):
            corr_pos[p] = i

    def quadro_ids(ano, caixa=None):
        c = ent["por_ano"][corr_pos[pos[ano]]]
        k = c[2]
        im = cv2.imread(os.path.join(V2, "mapas", f"{k}.png"))
        reg = cv2.imread(os.path.join(V2, "rotulos", f"{k}.png"), cv2.IMREAD_UNCHANGED).astype(np.int32)
        borda = np.zeros(reg.shape, bool)
        borda[:, 1:] |= reg[:, 1:] != reg[:, :-1]
        borda[1:, :] |= reg[1:, :] != reg[:-1, :]
        out = im.copy()
        out[borda] = (0, 0, 0)
        for r, e in c[3].items():
            m = reg == int(r)
            if m.sum() < 150:
                continue
            dt = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 3)
            y, x = np.unravel_index(int(dt.argmax()), dt.shape)
            cv2.putText(out, e[1:].lstrip("0"), (int(x) - 10, int(y) + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 2)
            cv2.putText(out, e[1:].lstrip("0"), (int(x) - 10, int(y) + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
        if caixa:
            p = cal[k]
            x0 = int((caixa[0] + 180) * p["S"] - p["X0"]); x1 = int((caixa[1] + 180) * p["S"] - p["X0"])
            y0 = int((merc(80.0) - merc(caixa[3])) * p["S"] - p["Y0"]); y1 = int((merc(80.0) - merc(caixa[2])) * p["S"] - p["Y0"])
            out = out[max(0, y0):y1, max(0, x0):x1]
        cv2.putText(out, f"{ano} {'a.C.' if ano > 0 else 'd.C.'}", (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 200), 2)
        return out
    filmes = [(1200, (20, 60, 22, 42), "1200-1189a"), (-30, (20, 60, 22, 45), "30-41d"), (-1914, (-15, 45, 30, 62), "1914-1925d")]
    for a0, caixa, nome in filmes:
        quadros = [quadro_ids(ordem[pos[a0] + i], caixa) for i in range(12)]
        h = max(q.shape[0] for q in quadros); w = max(q.shape[1] for q in quadros)
        quadros = [cv2.copyMakeBorder(q, 0, h - q.shape[0], 0, w - q.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for q in quadros]
        lin = [np.hstack(quadros[i:i + 4]) for i in range(0, 12, 4)]
        cv2.imwrite(os.path.join(SAIDA, f"e6-filme-{nome}.png"), np.vstack(lin))
        print("e6: filme", nome)
    # entidades curtas: 10 sorteadas
    curtas = [(e, d) for e, d in ent["entidades"].items() if pos[d["anos"][1]] - pos[d["anos"][0]] + 1 < 3]
    random.seed(3)
    cel = []
    for e, d in random.sample(curtas, min(10, len(curtas))):
        a_, a1, k, rs = d["trechos"][0]
        im = cv2.imread(os.path.join(V2, "mapas", f"{k}.png"))
        reg = cv2.imread(os.path.join(V2, "rotulos", f"{k}.png"), cv2.IMREAD_UNCHANGED)
        m = np.isin(reg, rs)
        ys, xs = np.where(m)
        cx, cy = int(np.median(xs)), int(np.median(ys))
        hh = max(30, (xs.max() - xs.min()) // 2 + 15, (ys.max() - ys.min()) // 2 + 15)
        sl = (slice(max(0, cy - hh), cy + hh), slice(max(0, cx - hh), cx + hh))
        c = im[sl].copy()
        mm = m[sl].astype(np.uint8)
        c[mm.astype(bool) & ~cv2.erode(mm, np.ones((3, 3), np.uint8)).astype(bool)] = (0, 220, 0)
        c = cv2.resize(c, (220, 220), interpolation=cv2.INTER_NEAREST)
        cv2.putText(c, f"{e} {d['anos'][0]}..{d['anos'][1]}", (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 200), 1)
        cel.append(c)
    if cel:
        while len(cel) % 5:
            cel.append(np.full_like(cel[0], 255))
        cv2.imwrite(os.path.join(SAIDA, "e6-curtas.png"), np.vstack([np.hstack(cel[i:i + 5]) for i in range(0, len(cel), 5)]))
    print("e6: curtas", len(curtas))


if __name__ == "__main__":
    {"e1": e1, "e2": e2, "e3": e3, "e4": e4, "e4-recortes": e4_recortes, "e4-unioes": e4_unioes, "e4-pares": e4_pares, "e5": e5, "e6": e6}[sys.argv[1]](sys.argv[2:])
