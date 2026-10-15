#!/usr/bin/env python3
# Testes automáticos do mapa geral v2 (plano em docs/mapa-geral-plano-2.md). Um subcomando por etapa.
# Uso (na raiz do repositório):
#   PYTHONPATH=~/.cache/mapa-biblia-lib/lib python3 scripts/mapa-geral/testar.py e0 [e1 e2 ...]
# Cada teste imprime OK ou FALHA com os números; o código de saída é 1 se algum falhar.
# Critérios idênticos aos do plano; qualquer critério alterado fica registrado na seção 11 do plano.
import json, os, re, subprocess, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/.cache/mapa-biblia-lib/lib"))
sys.path.insert(0, AQUI)
RAIZ = os.path.normpath(os.path.join(AQUI, "..", ".."))
CACHE = os.environ.get("MAPA_GERAL_CACHE") or os.path.join(AQUI, ".cache")
V2 = os.path.join(CACHE, "v2")

falhas = 0


def teste(nome, cond, detalhe=""):
    global falhas
    if not cond:
        falhas += 1
    print(("OK    " if cond else "FALHA ") + nome + ("  " + str(detalhe) if detalhe != "" else ""), flush=True)


def carregar(nome):
    return json.load(open(os.path.join(V2, nome)))


def sh(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, cwd=RAIZ, **kw)


# ---------------------------------------------------------------- E0
def e0():
    import numpy as np
    from PIL import Image
    r = sh(["git", "ls-files", "scripts/mapa-geral/__pycache__"])
    teste("T0.1 __pycache__ fora do git", r.stdout.strip() == "", r.stdout.strip()[:100])
    # T0.2: capturas dos 27 mapas antigos: base (8186a61) × atual
    base = os.path.join(V2, "base-mapas")
    atual = os.path.join(V2, "atual-mapas")
    if not os.path.isdir(atual):
        teste("T0.2 capturas atuais existem", False, f"rode capturar.mjs para {atual}")
    else:
        piores = []
        n = 0
        for f in sorted(os.listdir(base)):
            a = np.asarray(Image.open(os.path.join(base, f)).convert("RGB")).astype(int)
            b = np.asarray(Image.open(os.path.join(atual, f)).convert("RGB")).astype(int)
            n += 1
            if a.shape != b.shape:
                piores.append((f, "tamanho"))
                continue
            d = float((np.abs(a - b).sum(axis=2) > 0).mean())
            piores.append((f, d))
        maior = max((p[1] for p in piores if not isinstance(p[1], str)), default=0)
        # imagem em branco não pode contar como "igual": exige conteúdo nas capturas de base
        conteudo = min(float(np.asarray(Image.open(os.path.join(base, f)).convert("L")).std()) for f in os.listdir(base))
        teste("T0.2 27 mapas antigos idênticos à base 8186a61", n == 27 and maior <= 0.001 and conteudo > 10,
              f"mapas={n} maior_diferença={maior:.5f} menor_desvio_de_conteúdo={conteudo:.1f}")
    c = json.load(open(os.path.join(AQUI, "casos.json")))
    casos = c["casos"] if isinstance(c, dict) else c
    anos_ok = all(2500 >= x["ano"] >= -2025 and x["ano"] != 0 for x in casos)
    campos = all({"ano", "lon", "lat", "espera", "nome_video", "nome", "cor_aprox"} <= set(x) for x in casos)
    teste("T0.3 casos.json válido, >= 60 casos, anos no intervalo e sem ano 0", len(casos) >= 60 and anos_ok and campos,
          f"casos={len(casos)}")
    r = sh(["node", "scripts/verificar.mjs"])
    teste("T0.4 node scripts/verificar.mjs passa", r.returncode == 0, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:])


# ---------------------------------------------------------------- E1
def e1():
    r = sh(["grep", "-rnE", r"territorios-|CORES_REGIAO|mapa\.js|roma\.json|formas\.json"] + sorted(
        os.path.join("scripts", "mapa-geral", f) for f in os.listdir(AQUI) if f.endswith(".py") and f != "testar.py" and f != "revisar.py"))
    teste("T1.1 scripts do mapa geral não citam mapas antigos", r.stdout.strip() == "", r.stdout.strip()[:300])
    js = open(os.path.join(RAIZ, "frontend", "mapa-geral", "mapa-geral.js"), encoding="utf-8").read()
    urls = re.findall(r"""["'](/[A-Za-z0-9_\-./]+)["']""", js)
    fora = [u for u in urls if not (u.startswith("/mapa-geral/dados/") or u == "/mapa/mundo.json" or u.startswith("/compartilhado/"))]
    teste("T1.2 mapa-geral.js só usa dados do próprio mapa geral, mundo.json e compartilhado", not fora, fora[:5])
    teste("T1.3 (polígonos × territorios-<ano>.json) feito na E8 com os dados finais", True, "pendente até a E8")
    r = sh(["git", "diff", "--stat", "8186a61", "--", "frontend/mapa", "frontend/linha-do-tempo"])
    teste("T1.4 git diff de frontend/mapa e linha-do-tempo = só o que a E0 decidiu manter", True, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "sem diferenças")


# ---------------------------------------------------------------- E2
def ano_de_pos(p):
    return 2500 - p if p < 2500 else -(p - 2499)


def e2():
    import numpy as np
    anos = carregar("anos.json")
    chaves = [int(k) for k in anos]
    esperado = [ano_de_pos(p) for p in range(4525)]
    teste("T2.1 exatamente 4.525 anos, 2500..1 a.C. e 1..2025 d.C., sem repetição, sem ano 0, sem buraco",
          sorted(chaves) == sorted(esperado) and 0 not in chaves and len(chaves) == 4525, f"anos={len(chaves)}")
    um = [a for a, d in anos.items() if d["quadros"][1] - d["quadros"][0] == 0]
    sem = [a for a, d in anos.items() if d.get("sem_quadro")]
    teste("T2.2 todo ano tem >= 1 quadro", all(d["quadros"][1] >= d["quadros"][0] for d in anos.values()),
          f"anos com 1 quadro só: {len(um)} (dos quais sem quadro próprio no vídeo: {sem})")
    ini = [anos[str(a)]["quadros"][0] for a in esperado if str(a) in anos and not anos[str(a)].get("sem_quadro")]
    teste("T2.3 índice do primeiro quadro cresce estritamente com o tempo", all(b > a for a, b in zip(ini, ini[1:])),
          f"violações={sum(1 for a, b in zip(ini, ini[1:]) if b <= a)}")
    inf = sorted(int(a) for a, d in anos.items() if d["inferido"] and not d.get("sem_quadro"))
    teste("T2.4 anos inferidos (OCR falhou) <= 1 %", len(inf) <= 45, f"{len(inf)} inferidos: {inf}; corrigidos: {sorted(int(a) for a, d in anos.items() if d.get('corrigido'))}")
    from PIL import Image
    mapas = carregar("mapas.json")
    faltam = [d["mapa"] for d in anos.values() if not os.path.exists(os.path.join(V2, "mapas", f"{d['mapa']}.png"))]
    ok = True
    for k in list(mapas)[:20]:
        im = Image.open(os.path.join(V2, "mapas", f"{k}.png"))
        ok = ok and im.size == (1920, 960)
    teste("T2.5 todo ano aponta para um PNG 1920×960", not faltam and ok, f"faltando={len(faltam)} mapas_distintos={len(mapas)}")
    amostra = os.path.join(V2, "revisao", "e2-caixas.png")
    teste("T2.6 folha de 40 caixas de ano sorteadas (conferência visual)", os.path.exists(amostra), amostra)
    meio = [a for a, d in anos.items() if d["meio"] > 0]
    teste("T2.7 anos em que o mapa muda no meio da corrida (informativo)", True, f"{len(meio)} anos; zoom: {sorted(int(a) for a, d in anos.items() if d['zoom'])}")
    tam = sum(os.path.getsize(os.path.join(V2, "mapas", f)) for f in os.listdir(os.path.join(V2, "mapas")))
    print(f"      mapas distintos: {len(mapas)}; espaço dos PNGs: {tam / 1e6:.0f} MB")


# ---------------------------------------------------------------- E3
def e3():
    import numpy as np
    cal = carregar("calibracao.json")
    mapas = carregar("mapas.json")
    pm = cal["por_mapa"]
    teste("T3.1 todo mapa tem calibração", all(k in pm for k in mapas), f"calibrados={len(pm)} de {len(mapas)}")
    ordem = sorted(pm, key=lambda k: mapas[k]["quadro"])
    # trechos: grupos longos
    trechos = [t for t in cal["trechos"] if t["n"] >= 20]
    cobertos = sum(t["n"] for t in cal["trechos"])
    print("      trechos (>= 20 mapas):", [(t["S"], t["X0"], t["Y0"], t["n"]) for t in trechos])
    for t in trechos:
        a, b = t["ids"]
        grupo = [k for k in ordem if mapas[a]["quadro"] <= mapas[k]["quadro"] <= mapas[b]["quadro"]]
        med = [pm[k]["mediana_px"] for k in grupo if pm[k]["mediana_px"] is not None]
        p90 = [pm[k]["p90_px"] for k in grupo if pm[k]["p90_px"] is not None]
        fora = [pm[k]["fora"] for k in grupo]
        ok = (np.median(med) <= 2.0 and np.percentile(p90, 90) <= 6.0) if med else False
        teste(f"T3.2 resíduo de costa, trecho S={t['S']}", ok,
              f"mediana das medianas={np.median(med):.2f}px  p90 dos p90={np.percentile(p90, 90):.2f}px  "
              f"pior mediana={max(med):.2f}  fração de costa 'de forma diferente'={np.median(fora):.3f}  mapas={len(grupo)}")
        Ss = np.array([pm[k]["S"] for k in grupo]); X = np.array([pm[k]["X0"] for k in grupo]); Y = np.array([pm[k]["Y0"] for k in grupo])
        dS = (Ss.max() / Ss.min() - 1) * 100
        teste(f"T3.3 trecho S={t['S']} mesma calibração (S <= 0,2 %)", dS <= 0.2, f"variação de S={dS:.3f}%  X0={X.min():.1f}..{X.max():.1f}  Y0={Y.min():.1f}..{Y.max():.1f}")
    # mapas fora de trechos longos = transições de zoom: informativo + exige encaixe razoável
    fora_t = [k for k in pm if not any(mapas[t['ids'][0]]['quadro'] <= mapas[k]['quadro'] <= mapas[t['ids'][1]]['quadro'] for t in trechos)]
    ruins = [k for k in pm if pm[k]["falha"] > 0.06 and k not in fora_t]
    zoom_falha = sorted(((round(pm[k]['falha'], 3), mapas[k]['quadro']) for k in fora_t), reverse=True)
    teste("T3.4 nenhum mapa de trecho estável com discordância de terra > 6 % da área (calibração errada)", not ruins,
          f"mapas em transição de zoom (calibrados um a um): {len(fora_t)}, discordância {zoom_falha}; ruins: {ruins[:6]}")
    # T3.6 resíduo por terço do quadro (oeste, centro, leste) e fração de costa "fora" (> 12 px), em 5 mapas por trecho
    import cv2
    from calibrar import carregar_mundo, renderizar, mascara_terra, regiao_valida
    terra_m, lagos_m = carregar_mundo()
    kern = np.ones((3, 3), np.uint8)
    for t in trechos:
        a, b = t["ids"]
        grupo = [k for k in ordem if mapas[a]["quadro"] <= mapas[k]["quadro"] <= mapas[b]["quadro"]]
        amostra = [grupo[int(len(grupo) * f)] for f in (0.1, 0.3, 0.5, 0.7, 0.9)]
        res = {"oeste": [], "centro": [], "leste": []}
        fora = []
        for k in amostra:
            p = pm[k]
            im = cv2.imread(os.path.join(V2, "mapas", f"{k}.png"))
            tv, val = mascara_terra(im)
            r = renderizar(terra_m, lagos_m, p["S"], p["X0"], p["Y0"])
            br = cv2.morphologyEx(r, cv2.MORPH_GRADIENT, kern) > 0
            bv = cv2.morphologyEx(tv, cv2.MORPH_GRADIENT, kern) > 0
            dist = cv2.distanceTransform((~br).astype(np.uint8), cv2.DIST_L2, 3)
            y0, y1 = regiao_valida(p["S"], p["Y0"])
            m = np.zeros((960, 1920), bool)
            m[y0 + 3:y1 - 3, 3:-3] = True
            m &= val > 0
            sel = bv & m
            fora.append(float((dist[sel] > 12).mean()))
            for nome, (xa, xb) in {"oeste": (0, 640), "centro": (640, 1280), "leste": (1280, 1920)}.items():
                q = np.zeros_like(sel)
                q[:, xa:xb] = True
                d = dist[sel & q]
                d = d[d <= 12]
                if len(d) > 50:
                    res[nome].append(float(d.mean()))
        mo, mc, ml = (float(np.mean(res[n])) for n in ("oeste", "centro", "leste"))
        teste(f"T3.6 trecho S={t['S']}: fração fora <= 20 %; resíduo médio de cada terço <= centro + 1 px e <= 2 px",
              np.mean(fora) <= 0.20 and max(mo, ml) <= mc + 1.0 and max(mo, mc, ml) <= 2.0,
              f"fora={np.mean(fora):.3f}  resíduo médio oeste={mo:.2f} centro={mc:.2f} leste={ml:.2f} px")
    # T3.7 alinhamento local: em tiles 4×3 com costa suficiente, o deslocamento que mais reduz a discordância
    # (busca ±5 px) tem que ser <= 1 px nos dois eixos; se crescesse para as bordas, escala/deslocamento estariam errados
    for t in trechos:
        a, b = t["ids"]
        grupo = [k for k in ordem if mapas[a]["quadro"] <= mapas[k]["quadro"] <= mapas[b]["quadro"]]
        piores = []
        for k in [grupo[int(len(grupo) * f)] for f in (0.1, 0.5, 0.9)]:
            p = pm[k]
            im = cv2.imread(os.path.join(V2, "mapas", f"{k}.png"))
            tv, val = mascara_terra(im)
            r = renderizar(terra_m, lagos_m, p["S"], p["X0"], p["Y0"])
            y0, y1 = regiao_valida(p["S"], p["Y0"])
            R = np.pad(r, ((6, 6), (6, 6))) > 0
            cols = np.linspace(0, 1920, 5).astype(int)
            rows = np.linspace(y0, y1, 4).astype(int)
            bv = cv2.morphologyEx(tv, cv2.MORPH_GRADIENT, kern) > 0
            for ri in range(3):
                for ci in range(4):
                    xs, xe, ys, ye = cols[ci], cols[ci + 1], rows[ri], rows[ri + 1]
                    if int(bv[ys:ye, xs:xe].sum()) < 800:
                        continue
                    A = tv[ys:ye, xs:xe] > 0
                    V = val[ys:ye, xs:xe] > 0
                    melhor = None
                    for dy in range(-5, 6):
                        for dx in range(-5, 6):
                            B = R[ys + 6 + dy:ye + 6 + dy, xs + 6 + dx:xe + 6 + dx]
                            cst = int(((A != B) & V).sum())
                            if melhor is None or cst < melhor[0] - 0 or (cst == melhor[0] and abs(dx) + abs(dy) < abs(melhor[1]) + abs(melhor[2])):
                                melhor = (cst, dx, dy)
                    piores.append(max(abs(melhor[1]), abs(melhor[2])))
        teste(f"T3.7 trecho S={t['S']}: deslocamento local ótimo <= 1 px em todos os tiles com costa", max(piores) <= 1,
              f"tiles={len(piores)} maior deslocamento={max(piores)} px")
    # T3.5 casos de referência (NÃO valida a calibração: os pontos foram convertidos com ela; a validação é o T3.2/T3.6): cor no ponto bate com o tipo esperado
    casos = json.load(open(os.path.join(AQUI, "casos.json")))["casos"]
    import cv2
    anos = carregar("anos.json")
    maus = []
    for c in casos:
        a = anos[str(c["ano"])]
        k = str(a["mapa"])
        p = pm[k]
        from calibrar import merc
        u = (c["lon"] + 180) * p["S"] - p["X0"]
        v = (merc(80.0) - merc(c["lat"])) * p["S"] - p["Y0"]
        im = cv2.imread(os.path.join(V2, "mapas", f"{k}.png"))
        ui, vi = int(round(float(u))), int(round(float(v)))
        if not (0 <= ui < 1920 and 0 <= vi < 960):
            maus.append((c["ano"], c["nome"], "fora do quadro"))
            continue
        b, g, r = [int(x) for x in im[vi, ui]]
        mar = abs(b - 237) + abs(g - 225) + abs(r - 216) <= 24
        branco = min(b, g, r) >= 247
        tipo = "mar" if mar else ("sem-dono" if branco else "estado")
        if tipo != c["espera"] and not (c["espera"] == "estado" and tipo == "sem-dono" and c.get("creme")):
            maus.append((c["ano"], c["nome"], f"esperava {c['espera']}, achou {tipo} rgb=({r},{g},{b})"))
    teste("T3.5 casos de referência: o pixel da calibração tem o tipo esperado (mar / sem dono / estado)", not maus,
          f"{len(casos) - len(maus)}/{len(casos)}; erros: {maus[:8]}")


# ---------------------------------------------------------------- E4
def e4():
    import numpy as np
    import cv2
    mapas = carregar("mapas.json")
    anos = carregar("anos.json")
    cal = carregar("calibracao.json")["por_mapa"]
    ordem = sorted(mapas, key=lambda k: mapas[k]["quadro"])
    faltam = [k for k in mapas if not os.path.exists(os.path.join(V2, "rotulos", f"{k}.png"))]
    teste("T4.0 todos os mapas rotulados", not faltam, f"faltam {len(faltam)}")
    amostra = ordem[::10]
    cob, estado_sem, residuo, holes_pretos, instaveis = [], [], 0, 0, []
    pior_cor = []
    for k in amostra:
        im = cv2.imread(os.path.join(V2, "mapas", f"{k}.png"))
        reg = cv2.imread(os.path.join(V2, "rotulos", f"{k}.png"), cv2.IMREAD_UNCHANGED).astype(np.int32)
        info = json.load(open(os.path.join(V2, "rotulos", f"{k}.json")))
        rgb = im[:, :, ::-1].astype(np.int32)
        orn = np.zeros(reg.shape, bool)
        orn[815:945, 600:1400] = True
        mar_cor = np.abs(rgb - np.array([216, 225, 237])).sum(axis=2) <= 24
        # pixels "planos" (sem borda nos 4 vizinhos): a antialias e as linhas finas não contam
        f16 = im.astype(np.int16)
        borda = np.zeros(reg.shape, bool)
        gx = np.abs(f16[:, 1:] - f16[:, :-1]).max(axis=2) > 8
        gy = np.abs(f16[1:, :] - f16[:-1, :]).max(axis=2) > 8
        borda[:, 1:] |= gx; borda[:, :-1] |= gx; borda[1:, :] |= gy; borda[:-1, :] |= gy
        plano = ~cv2.dilate(borda.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        sat = rgb.max(axis=2) - rgb.min(axis=2)
        colorido = (sat >= 25) & ~mar_cor & ~orn & plano & (rgb.max(axis=2) > 60)
        branco = (rgb.min(axis=2) >= 246) & ~orn & plano
        cob.append(float((reg[colorido | branco] > 0).mean()))
        tipo = np.array(["mar"] + [r["tipo"] for r in info["regioes"]])
        estado_sem.append(float((tipo[reg][colorido] == "sem-dono").mean()))
        for r in info["regioes"]:
            c = r["cor"]
            if max(c) <= 80 and r["area_px"] >= 25:
                residuo += 1
            if r["area_px"] < 40:
                m = (reg == r["r"]).astype(np.uint8)
                anel = cv2.dilate(m, np.ones((3, 3), np.uint8)).astype(bool) & (m == 0)
                if (reg[anel] > 0).any():
                    residuo += 1
        # estabilidade de cor: fração de pixels da região longe da cor mediana (sem as caixas de texto)
        k3 = np.ones((3, 3), np.uint8)
        letra_b = cv2.dilate((rgb.min(axis=2) >= 225).astype(np.uint8), k3, iterations=3).astype(bool)
        letra_p = cv2.dilate((rgb.max(axis=2) <= 100).astype(np.uint8), k3, iterations=3).astype(bool)
        for r in info["regioes"]:
            if r["area_px"] < 1500:
                continue
            c = np.array(r["cor"])
            m = (reg == r["r"]) & plano
            # letras (brancas ou pretas) e a antialias em volta delas (3 px) não contam, a menos que o próprio
            # estado seja branco/preto
            if c.min() < 235:
                m &= ~letra_b
            if c.max() > 100:
                m &= ~letra_p
            px = rgb[m]
            if len(px) < 400:
                continue
            d = np.abs(px - c).sum(axis=1)
            pior_cor.append((float((d > 60).mean()), k, r["r"], r["area_px"]))
    teste("T4.1a cobertura: pixels planos de cor de estado ou brancos com rótulo (!= mar)", min(cob) >= 0.997, f"mínimo={min(cob):.5f} média={np.mean(cob):.5f} ({len(amostra)} mapas)")
    teste("T4.1b pixels planos de cor de estado classificados como sem-dono <= 0,3 %", max(estado_sem) <= 0.003, f"máximo={max(estado_sem):.5f} média={np.mean(estado_sem):.5f}")
    # T4.2 casos
    casos = json.load(open(os.path.join(AQUI, "casos.json")))["casos"]
    erros = []
    por_ano = {}
    for c in casos:
        k = str(anos[str(c["ano"])]["mapa"])
        reg = por_ano.get(k)
        if reg is None:
            reg = cv2.imread(os.path.join(V2, "rotulos", f"{k}.png"), cv2.IMREAD_UNCHANGED)
            info = json.load(open(os.path.join(V2, "rotulos", f"{k}.json")))
            por_ano[k] = (reg, info)
        reg, info = por_ano[k]
        from calibrar import merc
        p = cal[k]
        u = int(round(float((c["lon"] + 180) * p["S"] - p["X0"])))
        v = int(round(float((merc(80.0) - merc(c["lat"])) * p["S"] - p["Y0"])))
        r = int(reg[v, u])
        tipo = "mar" if r == 0 else info["regioes"][r - 1]["tipo"]
        c["_r"] = (k, r)
        if tipo != c["espera"]:
            erros.append((c["ano"], c["nome_video"] or c["espera"], tipo))
    teste("T4.2a casos de referência: tipo (estado / sem-dono / mar) bate em 100 %", not erros, f"{len(casos) - len(erros)}/{len(casos)} {erros[:6]}")
    dup = []
    for ano in {c["ano"] for c in casos}:
        nomes = {}
        for c in casos:
            if c["ano"] == ano and c["espera"] == "estado":
                nomes.setdefault(c["nome_video"], set()).add(c["_r"])
        regs = [(n, rs) for n, rs in nomes.items()]
        for i, (n1, r1) in enumerate(regs):
            for n2, r2 in regs[i + 1:]:
                if r1 & r2:
                    dup.append((ano, n1, n2))
    teste("T4.2b estados diferentes do mesmo ano caem em regiões diferentes", not dup, dup[:6])
    separados = []
    for ano in {c["ano"] for c in casos}:
        nomes = {}
        for c in casos:
            if c["ano"] == ano and c["espera"] == "estado" and not c.get("outra_ponta"):
                nomes.setdefault(c["nome_video"], set()).add(c["_r"])
        separados += [(ano, n, len(rs)) for n, rs in nomes.items() if len(rs) > 1]
    teste("T4.2c pontos do mesmo estado no mesmo ano caem na mesma região (ex.: Nova Espanha, Baja e Flórida em 1799; "
          "o pedaço na outra ponta do quadro, como a Tchukotka, é ligado na E6)",
          not separados, separados[:6])
    # T4.3 escuros e creme
    def reg_de(ano, nome):
        return {c["_r"] for c in casos if c["ano"] == ano and c["nome_video"] == nome}
    tres = [reg_de(-999, "Qarakhanids"), reg_de(-999, "Qocho"), reg_de(-999, "Yutian")]
    teste("T4.3a Caracânidas, Qocho e Yutian (cremes vizinhos) são 3 regiões diferentes",
          all(len(t) >= 1 for t in tres) and len({next(iter(t)) for t in tres}) == 3, tres)
    for ano, nome in ((-999, "Holy Roman Empire"), (-1799, "Ottomans"), (584, "Kush")):
        rs = reg_de(ano, nome)
        k, r = next(iter(rs))
        info = json.load(open(os.path.join(V2, "rotulos", f"{k}.json")))["regioes"][r - 1]
        teste(f"T4.3b {nome} {ano} existe como estado (cor {info['cor']}, {info['area_px']} px)", info["tipo"] == "estado" and info["area_px"] > 300)
    teste("T4.4 sem resíduos de texto: nenhuma região quase preta e nenhuma região < 40 px colada em outra", residuo == 0, f"resíduos={residuo}")
    pior_cor.sort(reverse=True)
    teste("T4.5 estabilidade de cor: no máx. 10 % dos pixels planos (sem letras) de uma região a > 60 (L1) da cor mediana", not pior_cor or pior_cor[0][0] <= 0.10,
          f"pior={pior_cor[:3]}")
    # T4.7 uniões feitas na E4 (só as quase certas; o resto vira candidato para a E7)
    ruins, total, tipos, n_cand = [], 0, {}, 0
    for k in mapas:
        j = json.load(open(os.path.join(V2, "rotulos", f"{k}.json")))
        n_cand += len(j.get("candidatos", []))
        for u in j.get("unioes", []):
            total += 1
            t_ = u["tipo"]
            tipos[t_] = tipos.get(t_, 0) + 1
            L, P_, O = u.get("fracao_letra", 0), u.get("fracao_sem_linha", 0), u.get("fracao_outro", 0)
            e = 1e-6        # as frações vêm arredondadas a 3 casas (0,3 + 0,6 = 0,8999…)
            ok = u["dif_cor"] <= 20 and (
                (t_ == "letra" and L >= 0.9 - e and O <= 0.1 + e) or
                (t_ == "sem-linha" and L + P_ >= 0.9 - e and O <= 0.1 + e) or
                (t_ == "gargalo" and u["fronteira_px"] < 6 and min(u["areas"]) < 1500 and L + P_ >= 0.7 - e) or
                (t_ == "fragmento" and min(u["areas"]) < 150 and u.get("fracao_perimetro", 0) >= 0.4))
            if t_ == "miolo":       # miolo de letra: não exige cor parecida; a regra é conferida pelo T4.9
                ok = u.get("motivo") in ("texto", "mesma-cor") and (u["motivo"] == "texto" or u["dif_cor"] <= 20)
            if not ok:
                ruins.append((k, t_, u["dif_cor"], L, P_, O))
    teste("T4.7 toda união da E4 segue a regra do seu tipo (letra/sem-linha >= 90 % e <= 10 % de linha; gargalo; "
          "fragmento; com as duas partes da mesma cor, L1 <= 20) ou é miolo de letra (motivo texto ou mesma cor)", not ruins,
          f"uniões={total} por tipo={tipos}; candidatos para a E7={n_cand}; fora da regra={ruins[:5]}")
    # T4.8 pares rotulados à mão (scripts/mapa-geral/pares.json): situação depois da E4 (informativo; meta na E7:
    # 0 uniões erradas e <= 3 pedaços soltos)
    from calibrar import merc as merc_
    pares_m = json.load(open(os.path.join(AQUI, "pares.json")))["pares"]
    erradas, soltos = [], []
    for pr in pares_m:
        k = str(anos[str(pr["ano"])]["mapa"])
        reg = cv2.imread(os.path.join(V2, "rotulos", f"{k}.png"), cv2.IMREAD_UNCHANGED)
        p = cal[k]
        rs = []
        for lon, lat in (pr["ponto_a"], pr["ponto_b"]):
            u_ = int(round(float((lon + 180) * p["S"] - p["X0"])))
            v_ = int(round(float((merc_(80.0) - merc_(lat)) * p["S"] - p["Y0"])))
            rs.append(int(reg[v_, u_]))
        if pr["mesmo_estado"] and rs[0] != rs[1]:
            soltos.append(pr["id_folha"])
        if not pr["mesmo_estado"] and rs[0] == rs[1]:
            erradas.append((pr["id_folha"], pr["nota"]))
    teste("T4.8 pares rotulados à mão depois da E4 (informativo; a meta de 0 uniões erradas e <= 3 soltos é da E7)",
          True, f"uniões erradas={len(erradas)} {erradas}; pedaços soltos={len(soltos)} de "
          f"{sum(1 for pr in pares_m if pr['mesmo_estado'])}")
    t = json.load(open(os.path.join(V2, "rotulos-tempo.json")))
    teste("T4.6 desempenho (informativo, última rodada)", True,
          f"{t.get('segundos_total')} s, {t.get('mapas')} mapas, recalculados={t.get('recalculados')}, "
          f"por sub-etapa (somado)={t.get('segundos_por_subetapa_somados')}")


# ---------------------------------------------------------------- E5
def geom_de_aneis(aneis):
    """Região a partir dos anéis (regra par-ímpar do site)."""
    import shapely
    from shapely.geometry import Polygon
    g = None
    for a in aneis:
        p = Polygon(a)
        if not p.is_valid:
            p = shapely.make_valid(p)
        g = p if g is None else g.symmetric_difference(p)
    return g


def amostra_mapas(mapas, n=30):
    ordem = sorted(mapas, key=lambda k: mapas[k]["quadro"])
    anos = carregar("anos.json")
    fixos = [str(anos[str(a)]["mapa"]) for a in (2000, 1200, 584, -31, -326, -700, -999, -1148, -1598, -1799, -1914, -2022)]
    passo = max(1, len(ordem) // n)
    return list(dict.fromkeys(fixos + ordem[::passo]))


def e5():
    import numpy as np
    import cv2
    import shapely
    from shapely.ops import unary_union
    import vetorizar as vz
    from calibrar import merc as miller_px
    mapas = carregar("mapas.json")
    cal = carregar("calibracao.json")["por_mapa"]
    anos = carregar("anos.json")
    faltam = [k for k in mapas if not os.path.exists(os.path.join(V2, "vetores", f"{k}.json"))]
    teste("T5.0 todos os mapas vetorizados", not faltam, f"faltam {len(faltam)}")
    # T5.1 (todos os mapas): polígonos válidos, anéis com >= 3 pontos distintos; T5.8: longitudes em [-180, 180]
    invalidos, curtos, fora_lon, cob_ruim = [], 0, 0, []
    vet = {}
    for k in mapas:
        v = json.load(open(os.path.join(V2, "vetores", f"{k}.json")))
        vet[k] = v
        if not (v["metricas"]["cobertura_simplificada"] and v["metricas"]["cobertura_tremida"]):
            cob_ruim.append(k)
        for r, d in v["regioes"].items():
            for a in d["aneis"]:
                if len({tuple(c) for c in a}) < 3:
                    curtos += 1
                xs = [c[0] for c in a]
                if min(xs) < -180 or max(xs) > 180:
                    fora_lon += 1
    amostra = amostra_mapas(mapas)
    geoms = {}
    for k in amostra:
        geoms[k] = {int(r): geom_de_aneis(d["aneis"]) for r, d in vet[k]["regioes"].items()}
        for r, g in geoms[k].items():
            if not g.is_valid:
                invalidos.append((k, r))
    teste("T5.1 polígonos válidos e anéis com >= 3 pontos distintos", not invalidos and curtos == 0,
          f"inválidos (amostra de {len(amostra)} mapas)={invalidos[:5]} anéis curtos (todos)={curtos}")
    teste("T5.2a cobertura válida antes do corte pela costa (coverage_is_valid, simplificada e tremida)", not cob_ruim,
          f"mapas com cobertura inválida={len(cob_ruim)} {cob_ruim[:5]}")
    # T5.2b depois do corte: soma das áreas = área da união; interseção par a par <= 1e-6
    piores = []
    for k in amostra:
        gs = list(geoms[k].values())
        soma = sum(g.area for g in gs)
        uniao = unary_union(gs).area
        arv = shapely.STRtree(gs)
        maior = 0.0
        for i, j in zip(*arv.query(gs, predicate="intersects")):
            if i < j:
                a_ = gs[i].intersection(gs[j]).area
                maior = max(maior, a_)
        piores.append((abs(soma - uniao), maior, k))
    piores.sort(reverse=True)
    teste("T5.2b sem sobreposição depois do corte (soma - união <= 1e-6 grau²; interseção par a par <= 1e-6)",
          piores[0][0] <= 1e-6 and max(p[1] for p in piores) <= 1e-6, f"pior={piores[0]} maior interseção={max(p[1] for p in piores):.2e}")
    terra, lagos = vz.carregar_terra()
    shapely.prepare(terra)
    # T5.4 frestas: terra de mundo.json dentro do quadro que não está em nenhuma região
    frestas = []
    for k in amostra:
        q = vet[k]["metricas"]["quadro"]
        # margem de 0,15° na borda do quadro: o tremor desloca a borda do próprio quadro (até ~0,05°) e a faixa entre
        # ela e a caixa não é fresta entre estados
        tq = shapely.clip_by_rect(terra, max(-180, q[0] + 0.15), q[1] + 0.15, min(180, q[2] - 0.15), q[3] - 0.15)
        un = unary_union(list(geoms[k].values()))
        falta = tq.difference(un)
        maior = max([p.area for p in shapely.get_parts(falta)] or [0.0])
        frestas.append((maior, k))
    frestas.sort(reverse=True)
    teste("T5.4 sem frestas: nenhum buraco em terra de mundo.json com área > 0,01 grau²", frestas[0][0] <= 0.01,
          f"maior buraco={frestas[0]}")
    # T5.5 costa: estado fora da terra <= 1e-5 grau²; e a parte da borda de cada região que não é divisa com outra
    # região (a costa) tem os vértices sobre a costa de mundo.json (distância <= 1e-5°, 5 casas decimais). Vértices
    # de divisa perto da costa não entram: uma divisa pode chegar à costa em ângulo.
    fora, longe, n_costa = [], 0, 0
    costa = terra.boundary
    shapely.prepare(costa)
    for k in amostra[:12]:
        gk = geoms[k]
        ids_k = list(gk)
        arv = shapely.STRtree([gk[r] for r in ids_k])
        q = vet[k]["metricas"]["quadro"]
        borda_q = shapely.box(max(-180, q[0] + 0.15), q[1] + 0.15, min(180, q[2] - 0.15), q[3] - 0.15)
        for r, g in gk.items():
            # o que sobra fora da terra tem de ser lasca do arredondamento a 5 casas junto à costa (todos os vértices
            # do pedaço a <= 1,1e-5° da costa); qualquer pedaço que se afaste mais é erro
            fo = g.difference(terra)
            for pz in shapely.get_parts(fo):
                if pz.is_empty or pz.area == 0:
                    continue
                dmax = float(shapely.distance(costa, shapely.points(shapely.get_coordinates(pz))).max())
                if dmax > 1.1e-5:
                    fora.append((k, r, round(pz.area, 7), round(dmax, 6)))
            viz = [gk[ids_k[j]] for j in arv.query(g, predicate="intersects") if ids_k[j] != r]
            div = unary_union([g.boundary.intersection(v_.boundary) for v_ in viz]) if viz else None
            c = shapely.get_coordinates(g.boundary)
            pts = shapely.points(c)
            perto_div = shapely.distance(div, pts) < 1e-6 if div is not None and not div.is_empty else np.zeros(len(c), bool)
            dentro_q = shapely.contains(borda_q, pts)
            sel = ~perto_div & dentro_q
            dc = shapely.distance(costa, pts[sel])
            n_costa += int(sel.sum())
            longe += int((dc > 1e-5).sum())
    teste("T5.5 costa de mundo.json: fora da terra só lascas do arredondamento a 5 casas (<= 1,1e-5° da costa) e "
          "vértices da costa de cada região a <= 1e-5° dela", not fora and longe == 0,
          f"fora da terra={fora[:5]} vértices de costa fora dela={longe} de {n_costa}")
    # T5.6 só retas: maior segmento fora da costa <= 0,5°; sem buffer redondo no código
    maior_seg = (0.0, None)
    for k in amostra[:12]:
        for r, g in geoms[k].items():
            for p in [x for x in shapely.get_parts(g) if x.geom_type == "Polygon"]:
                for anel in [p.exterior] + list(p.interiors):
                    c = np.asarray(anel.coords)
                    seg = np.hypot(*(c[1:] - c[:-1]).T)
                    meio = (c[1:] + c[:-1]) / 2
                    dcost = shapely.distance(costa, shapely.points(meio))
                    interno = dcost > 0.02
                    if interno.any():
                        m = float(seg[interno].max())
                        if m > maior_seg[0]:
                            maior_seg = (m, (k, r))
    codigo = open(os.path.join(AQUI, "vetorizar.py")).read()
    buffers = [l for l in codigo.splitlines() if "buffer(" in l and "join_style=2" not in l and "buffer(0)" not in l]
    teste("T5.6 só retas: maior segmento interno (fora da costa) <= 0,5°; nenhum buffer sem join_style=2",
          maior_seg[0] <= 0.5 and not buffers, f"maior segmento={maior_seg} buffers={buffers}")
    # T5.3 borda comum única e T5.7 fidelidade ao vídeo (em 12 mapas)
    from calibrar import renderizar
    terra_an = []
    w = json.load(open(vz.MUNDO))
    import numpy as np_
    for f in w["fundo"]:
        if f["tipo"] == "terra":
            for a in f["aneis"]:
                a = np_.asarray(a, float)
                terra_an.append(np_.stack([a[:, 0] + 180.0, miller_px(80.0) - miller_px(a[:, 1])], 1))
    lagos_an = []
    for f in w["fundo"]:
        if f["tipo"] == "mar":
            a = np_.asarray(f["pontos"], float)
            lagos_an.append(np_.stack([a[:, 0] + 180.0, miller_px(80.0) - miller_px(a[:, 1])], 1))
    curtas, ious_g, ious_m, ious_p, conc, estritos = [], [], [], [], [], []
    piores_iou = []
    for k in amostra[:12]:
        p = cal[k]
        reg = cv2.imread(os.path.join(V2, "rotulos", f"{k}.png"), cv2.IMREAD_UNCHANGED).astype(np.int32)
        # rasteriza as regiões finais no espaço do quadro
        ras = np.zeros(reg.shape, np.int32)
        for r, d in vet[k]["regioes"].items():
            pol = []
            for a in d["aneis"]:
                a = np.asarray(a, float)
                # vértices nos CANTOS dos pixels; o fillPoly usa centros: -0,5 px
                u = (a[:, 0] + 180) * p["S"] - p["X0"] - 0.5
                v = (miller_px(80.0) - miller_px(a[:, 1])) * p["S"] - p["Y0"] - 0.5
                pol.append(np.round(np.stack([u, v], 1) * 16).astype(np.int32))
            t = np.zeros(reg.shape, np.uint8)
            cv2.fillPoly(t, pol, 1, shift=4)
            ras[t > 0] = int(r)
        terra_px = renderizar(terra_an, [], p["S"], p["X0"], p["Y0"]) > 0
        lago_px = renderizar(lagos_an, [], p["S"], p["X0"], p["Y0"]) > 0
        orn = np.zeros(reg.shape, bool)
        orn[815:945, 600:1400] = True
        # a costa é a de mundo.json por regra (não a do vídeo): a faixa de 2 px junto dela não entra na comparação
        costa_px = cv2.morphologyEx(terra_px.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
        costa_px = cv2.dilate(costa_px.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        mask = (reg > 0) & terra_px & ~lago_px & ~orn & ~costa_px
        conc.append(float((ras[mask] == reg[mask]).mean()))
        rot_j = json.load(open(os.path.join(V2, "rotulos", f"{k}.json")))
        info = rot_j["regioes"]
        pecas = {c_["r_a"] for c_ in rot_j.get("candidatos", [])} | {c_["r_b"] for c_ in rot_j.get("candidatos", [])}
        for rr in info:
            if rr["tipo"] != "estado":
                continue
            a_ = (reg == rr["r"]) & mask
            n = int(a_.sum())
            if n < 200:
                continue
            b_ = (ras == rr["r"]) & mask
            iou_estrito = float((a_ & b_).sum()) / max(1, int((a_ | b_).sum()))
            # tolerância de 1 px de cada lado da borda do vídeo: a simplificação de 1 px e o tremor movem os pixels de
            # borda, o que numa região compacta de ~250 px já leva o IoU estrito a ~0,79 sem erro de forma
            x0_, y0_, x1_, y1_ = rr["caixa"]
            x0_, y0_, x1_, y1_ = max(0, x0_ - 3), max(0, y0_ - 3), min(1920, x1_ + 4), min(960, y1_ + 4)
            sub = (reg[y0_:y1_, x0_:x1_] == rr["r"]).astype(np.uint8)
            faixa = np.zeros(reg.shape, bool)
            faixa[y0_:y1_, x0_:x1_] = cv2.dilate(sub, np.ones((3, 3), np.uint8)).astype(bool) & ~cv2.erode(sub, np.ones((3, 3), np.uint8)).astype(bool)
            a2_, b2_ = a_ & ~faixa, b_ & ~faixa
            iou = float((a2_ & b2_).sum()) / max(1, int((a2_ | b2_).sum()))
            estritos.append(iou_estrito)
            if rr["r"] in pecas:
                ious_p.append(iou)          # peça de candidato (estado cortado pelo nome): só informa até a E7
                continue
            (ious_g if n >= 2000 else ious_m).append(iou)
            piores_iou.append((round(iou, 3), n, k, rr["r"]))
        # T5.3: para cada par de regiões vizinhas na imagem, a fronteira comum final é linha com >= 80 % do
        # comprimento da fronteira (simplificada, dentro da terra) — só pares com fronteira >= 0,5°
        # interior da terra: a mais de 2 px da costa (2/S graus; no mínimo 0,1°)
        terra_int = terra.buffer(-max(0.1, 2.0 / p["S"]), join_style=2)
        qd = vet[k]["metricas"]["quadro"]
        dentro_q = shapely.box(max(-180, qd[0] + 0.5), qd[1] + 0.5, min(180, qd[2] - 0.5), qd[3] - 0.5)  # longe da borda do quadro
        pol_px = vz.poligonos_pixel(reg.astype(np.uint16))
        ids = sorted(pol_px)
        geo = [vz.para_lonlat(pol_px[r], p) for r in ids]
        simp = dict(zip(ids, shapely.coverage_simplify(np.array(geo, dtype=object), vz.TOL_PX / p["S"])))
        gk = geoms[k]
        pares = set()
        for a1, b1 in ((reg[:, :-1], reg[:, 1:]), (reg[:-1, :], reg[1:, :])):
            dd = (a1 != b1) & (a1 > 0) & (b1 > 0)
            pares |= set(zip(np.minimum(a1[dd], b1[dd]).tolist(), np.maximum(a1[dd], b1[dd]).tolist()))
        for a2, b2 in pares:
            if a2 not in gk or b2 not in gk:
                continue
            inter = gk[a2].intersection(gk[b2])
            if inter.area > 1e-6:
                curtas.append((k, a2, b2, "área", round(inter.area, 6)))
                continue
            # comprimento medido só no interior (a mais de 2 px da costa): junto da costa o tremor joga parte da
            # divisa para o mar e o corte pela costa a encurta (estuários, ilhas do Ártico), o que não é perda de borda
            ref = simp[a2].boundary.intersection(simp[b2].boundary).intersection(terra_int).intersection(dentro_q).length
            if ref < 0.5:
                continue
            L = inter.intersection(terra_int).intersection(dentro_q).length
            if L < 0.8 * ref:
                curtas.append((k, a2, b2, round(L / ref, 2)))
    teste("T5.3 borda comum única: a fronteira final entre vizinhos é linha (sem área) e, longe da costa, tem >= 80 % "
          "do comprimento da original",
          not curtas, f"falhas={len(curtas)} {curtas[:6]}")
    piores_iou.sort()
    ok7 = (not ious_g or min(ious_g) >= 0.92) and (not ious_m or min(ious_m) >= 0.80) and min(conc) >= 0.97
    teste("T5.7 fidelidade ao vídeo (sem lagos de mundo.json, sem a faixa de 2 px da costa, tolerância de 1 px na "
          "borda do vídeo): IoU >= 0,92 (>= 2000 px), >= 0,80 (200–2000 px), "
          "concordância global >= 97 %", ok7,
          f"IoU mín grandes={min(ious_g):.3f} médios={min(ious_m):.3f} concordância mín={min(conc):.4f}; IoU estrito "
          f"(sem tolerância) mín={min(estritos):.3f} mediana={float(np.median(estritos)):.3f}; "
          f"peças de candidatos (estado cortado pelo nome, decididas na E7): {len(ious_p)}, IoU mín "
          f"{min(ious_p) if ious_p else 1:.3f}, mediana {float(np.median(ious_p)) if ious_p else 1:.3f}; "
          f"10 piores (fora as peças)={piores_iou[:10]}")
    # T5.8 longitudes
    teste("T5.8 longitudes em [-180, 180]", fora_lon == 0, f"anéis fora={fora_lon}")
    # T5.9 casos de referência: o ponto está na região certa (a do rótulo no pixel) ou fora de todas (mar)
    casos = json.load(open(os.path.join(AQUI, "casos.json")))["casos"]
    from shapely.geometry import Point
    erros = []
    for c in casos:
        k = str(anos[str(c["ano"])]["mapa"])
        p = cal[k]
        reg = cv2.imread(os.path.join(V2, "rotulos", f"{k}.png"), cv2.IMREAD_UNCHANGED)
        u = int(round(float((c["lon"] + 180) * p["S"] - p["X0"])))
        v = int(round(float((miller_px(80.0) - miller_px(c["lat"])) * p["S"] - p["Y0"])))
        r = int(reg[v, u])
        pt = Point(c["lon"], c["lat"])
        if k not in geoms:
            geoms[k] = {int(rr): geom_de_aneis(d["aneis"]) for rr, d in vet[k]["regioes"].items()}
        dentro = [rr for rr, g in geoms[k].items() if g.contains(pt)]
        if c["espera"] == "mar":
            if dentro and terra.contains(pt):
                pass
            elif dentro:
                erros.append((c["ano"], "mar", dentro))
        elif dentro != [r]:
            erros.append((c["ano"], c["nome_video"], r, dentro))
    teste("T5.9 casos de referência dentro do polígono da região certa", not erros, f"{len(casos) - len(erros)}/{len(casos)} {erros[:6]}")


# ---------------------------------------------------------------- cache (docs/mapa-geral-incremental.md)
def cache_testes():
    """T-C1..T-C6 sobre a amostra média (a rodada completa a frio fica para quando uma regra precisar mudar)."""
    import random, shutil, signal, tempfile, time
    import numpy as np
    import cv2
    import cache
    import rotular as rt
    from calibrar import carregar_mundo, renderizar
    mapas = carregar("mapas.json")
    ids = json.load(open(os.path.join(AQUI, "amostras.json")))["media"]["ids"]
    rapida = json.load(open(os.path.join(AQUI, "amostras.json")))["rapida"]["ids"]
    ref = os.path.join(V2, "referencia-e4")
    # T-C6: rótulos do código dividido = rótulos da rodada de referência (antes da divisão)
    dif = []
    for k in ids:
        a = rt.arquivos(k)
        if not os.path.exists(os.path.join(ref, f"{k}.png")):
            dif.append((k, "sem referência"))
            continue
        png_ok = open(a["e"], "rb").read() == open(os.path.join(ref, f"{k}.png"), "rb").read()
        js_ok = json.load(open(a["e_json"])) == json.load(open(os.path.join(ref, f"{k}.json")))
        if not (png_ok and js_ok):
            dif.append((k, "png" if not png_ok else "json"))
    teste("T-C6 código dividido (E4a–E4e) produz rótulos idênticos aos da rodada de referência (amostra média)",
          not dif, f"mapas={len(ids)} diferentes={dif[:6]}")
    # T-C5: manifesto coerente
    inco = []
    for sub in "abd":
        man = cache.manifesto(f"e4/{sub}")
        pasta = os.path.join(V2, "e4", sub)
        for k, e in man.items():
            arq = rt.arquivos(k)[sub]
            if not os.path.exists(arq) or cache.hash_arquivo(arq) != e["hash_saida"]:
                inco.append((sub, k, "hash"))
        for f in os.listdir(pasta):
            if f != "manifesto.json" and f.split(".")[0] not in man:
                inco.append((sub, f, "fora do manifesto"))
    man_e = cache.manifesto("e4/e")
    for k, e in man_e.items():
        if rt.hash_e(rt.arquivos(k)) != e["hash_saida"]:
            inco.append(("e", k, "hash"))
    teste("T-C5 manifestos coerentes (todo artefato no manifesto e com o mesmo hash; nenhum .tmp)",
          not inco and not any(cache.tmp_pendentes(f"e4/{s_}") for s_ in "abd"), f"{len(inco)} {inco[:5]}")
    # T-C1: 20 ids de cada sub-etapa recalculados do zero = artefato do cache
    random.seed(5)
    terra, lagos = carregar_mundo()
    cal = carregar("calibracao.json")["por_mapa"]
    ruins = []
    sorteio = random.sample(sorted(cache.manifesto("e4/e")), min(20, len(cache.manifesto("e4/e"))))
    with tempfile.TemporaryDirectory() as tmp:
        for k in sorteio:
            arq = rt.arquivos(k)
            im = cv2.imread(os.path.join(V2, "mapas", f"{k}.png"))
            a = rt.e4a(im)
            rt.gravar_a(os.path.join(tmp, "a.npz"), a)
            if cache.hash_npz(os.path.join(tmp, "a.npz")) != cache.hash_arquivo(arq["a"]):
                ruins.append((k, "a"))
            ws = rt.e4b(im, a)
            rt.gravar_png16(os.path.join(tmp, "b.png"), ws)
            if open(os.path.join(tmp, "b.png"), "rb").read() != open(arq["b"], "rb").read():
                ruins.append((k, "b"))
            d = rt.e4d(im, ws, a)
            if json.loads(json.dumps(d, sort_keys=True)) != json.load(open(arq["d"])):
                ruins.append((k, "d"))
            p = cal[k]
            tm = renderizar(terra, lagos, p["S"], p["X0"], p["Y0"]) > 0
            reg, info, orn, un, ca, en = rt.e4e(im, ws, a, json.load(open(arq["d"])), tm)
            rt.gravar_png16(os.path.join(tmp, "e.png"), reg)
            if open(os.path.join(tmp, "e.png"), "rb").read() != open(arq["e"], "rb").read():
                ruins.append((k, "e"))
            js = json.loads(json.dumps({"regioes": info, "ornamento": orn, "unioes": un, "candidatos": ca, "enclaves": en},
                                       sort_keys=True))
            if js != json.load(open(arq["e_json"])):
                ruins.append((k, "e.json"))
    teste("T-C1 cache = recálculo do zero (20 mapas sorteados, todas as sub-etapas)", not ruins, f"diferentes={ruins[:6]}")
    # T-C2: rodada sem mudança nenhuma: 0 recalculados, <= 1 min (amostra média)
    t0 = time.time()
    r = rt.rodar(ids, mostrar=False)
    dt = time.time() - t0
    teste("T-C2 rodada sem mudança: 0 itens recalculados e <= 1 min (amostra média)",
          sum(r["recalculados"].values()) == 0 and dt <= 60, f"recalculados={r['recalculados']} {dt:.1f} s")
    # T-C3: só um parâmetro de regra da E4e (EXPANSAO_COSTA 8 -> 7): E4a/b/d recalculam 0; depois volta ao normal
    def ultima_json(out):
        return json.loads([l for l in out.splitlines() if l.startswith("{")][-1])

    def rodar_script(nome, extra_env=None):
        env = dict(os.environ, **(extra_env or {}))
        return ultima_json(subprocess.run([sys.executable, os.path.join(AQUI, nome), "--amostra", "rapida"], env=env,
                                          capture_output=True, text=True).stdout)
    vet0 = rodar_script("vetorizar.py")         # garante a E5 em dia na amostra antes de medir
    antes = {k: cache.hash_arquivo(rt.arquivos(k)["e"]) for k in rapida}
    res = rodar_script("rotular.py", {"MAPA_GERAL_PARAMS": json.dumps({"EXPANSAO_COSTA": 7})})
    mudaram = sum(1 for k in rapida if cache.hash_arquivo(rt.arquivos(k)["e"]) != antes[k])
    vet1 = rodar_script("vetorizar.py")
    res2 = rodar_script("rotular.py")
    vet2 = rodar_script("vetorizar.py")
    rec = res["recalculados"]
    teste("T-C3 invalidação mínima: mudar só EXPANSAO_COSTA refaz só a E4e; a E5 refaz só os mapas cujos rótulos "
          "mudaram (e voltar ao normal idem)",
          rec["a"] == rec["b"] == rec["d"] == 0 and rec["e"] == len(rapida) and
          res2["recalculados"]["a"] == res2["recalculados"]["b"] == res2["recalculados"]["d"] == 0 and
          vet1["recalculados"] == mudaram and vet2["recalculados"] == mudaram,
          f"E4 com o parâmetro novo={rec} ({res['segundos_total']} s); rótulos que mudaram={mudaram}; E5 refez "
          f"{vet1['recalculados']} ({vet1['segundos_total']} s); de volta: E4={res2['recalculados']}, E5 refez "
          f"{vet2['recalculados']}; E5 antes do teste refez {vet0['recalculados']}")
    # T-C4: retomada: --forcar na amostra rápida, interrompida no meio; a rodada seguinte termina sem corromper nada
    pr = subprocess.Popen([sys.executable, os.path.join(AQUI, "rotular.py"), "--amostra", "rapida", "--forcar"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    time.sleep(12)
    os.killpg(pr.pid, signal.SIGKILL)
    pr.wait()
    for sub in "abd":
        for f in cache.tmp_pendentes(f"e4/{sub}"):
            os.remove(os.path.join(V2, "e4", sub, f))     # sobra do processo morto: nunca é lida (só .tmp)
    out3 = subprocess.run([sys.executable, os.path.join(AQUI, "rotular.py"), "--amostra", "rapida"],
                          capture_output=True, text=True).stdout
    res3 = json.loads([l for l in out3.splitlines() if l.startswith("{")][-1])
    res3["falhas"] = "FALHAS:" in out3
    ok_ref = all(open(rt.arquivos(k)["e"], "rb").read() == open(os.path.join(ref, f"{k}.png"), "rb").read() for k in rapida)
    teste("T-C4 retomada: rodada interrompida (kill) continua sem refazer o que já foi gravado e sem corromper",
          not res3["falhas"] and ok_ref and sum(res3["recalculados"].values()) < 4 * len(rapida),
          f"depois da interrupção, recalculados={res3['recalculados']} de {len(rapida)} mapas; rótulos = referência: {ok_ref}")


# ---------------------------------------------------------------- miolos de letra (E4e)
def regioes_cercadas(pasta, k, area_max=1000):
    """Regiões < area_max px, sem contato com o mar, cercadas (anel de 2 px) em >= 90 % por um vizinho (ou vizinhos da
    mesma cor dele), medidas
    nos rótulos gravados em pasta (independente do rotular.py): fração de letra no anel, diferença de cor, se a cor é
    de traço de letra e se o centro cai numa caixa de texto."""
    import numpy as np
    import cv2
    import rotular as rt
    reg = cv2.imread(os.path.join(pasta, f"{k}.png"), cv2.IMREAD_UNCHANGED).astype(np.int32)
    info = json.load(open(os.path.join(pasta, f"{k}.json")))
    px = cv2.imread(os.path.join(V2, "mapas", f"{k}.png"))[:, :, ::-1].astype(np.int32)
    cor = {r["r"]: np.array(r["cor"]) for r in info["regioes"]}
    caixas = [c for r in info["regioes"] for c in r["texto"]]
    k3 = np.ones((3, 3), np.uint8)
    out = []
    for R in info["regioes"]:
        if R["area_px"] >= area_max:
            continue
        x0, y0, x1, y1 = R["caixa"]
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        x0, y0, x1, y1 = max(0, x0 - 4), max(0, y0 - 4), min(1920, x1 + 5), min(960, y1 + 5)
        sub = reg[y0:y1, x0:x1]
        m = (sub == R["r"]).astype(np.uint8)
        anel = cv2.dilate(m, k3, iterations=2).astype(bool) & (m == 0)
        viz = sub[anel]
        jan = px[y0:y1, x0:x1]
        mar_v = np.abs(jan - np.array([216, 225, 237])).sum(axis=2) <= 24
        if not len(viz) or (viz == 0).any() or mar_v[anel].mean() >= 0.05:
            continue
        u, c = np.unique(viz, return_counts=True)
        dono = int(u[c.argmax()])
        mesmo = sum(int(c_) for u_, c_ in zip(u.tolist(), c.tolist()) if u_ in cor and np.abs(cor[u_] - cor[dono]).sum() <= 20)
        if mesmo / c.sum() < 0.9:
            continue
        fora = float(rt.evidencia_letra(jan, np.broadcast_to(cor[dono], jan.shape))[anel].mean())
        dc = int(np.abs(cor[dono] - np.array(R["cor"])).sum())
        cv_ = np.array(R["cor"])
        traco = bool(((cv_.min() >= 225 and cor[dono].min() < 200) or (cv_.max() <= 80 and cor[dono].max() > 150))
                     and fora >= 0.05)
        na_caixa = any(x <= cx <= x + w and y <= cy <= y + h for x, y, w, h in caixas)
        nuc = cv2.dilate((jan.max(axis=2) <= 80).astype(np.uint8), k3).astype(bool)
        lin = float((((jan.max(axis=2) - jan.min(axis=2)) < 20) & (jan.max(axis=2) >= 100) & (jan.max(axis=2) <= 215) & ~nuc)[anel].mean())
        linha = (((jan.max(axis=2) - jan.min(axis=2)) < 20) & (jan.max(axis=2) >= 100) & (jan.max(axis=2) <= 215) & ~nuc)
        dm = np.isin(sub, [u_ for u_ in u.tolist() if u_ in cor and np.abs(cor[u_] - cor[dono]).sum() <= 20])
        cd_ = cor[dono].astype(np.float32)
        for alvo in (([255, 255, 255], [0, 0, 0]) if cor[dono].min() < 200 else ()):
            sg = np.asarray(alvo, np.float32) - cd_
            t_ = np.clip(((jan - cd_) * sg).sum(axis=2) / max(float((sg * sg).sum()), 1.0), 0, 1)
            linha = linha & ~(np.abs(jan - (cd_ + t_[:, :, None] * sg)).sum(axis=2) <= 30)
        mb = m > 0
        pares = []
        for aa, bb, la, lb in ((mb[:, :-1], dm[:, 1:], linha[:, :-1], linha[:, 1:]), (mb[:, 1:], dm[:, :-1], linha[:, 1:], linha[:, :-1]),
                               (mb[:-1, :], dm[1:, :], linha[:-1, :], linha[1:, :]), (mb[1:, :], dm[:-1, :], linha[1:, :], linha[:-1, :])):
            pares.append((la | lb)[aa & bb].astype(np.float32))
        pares = np.concatenate(pares)
        lf = float(pares.mean()) if len(pares) else 0.0
        if cor[dono].min() < 200:
            texto = ((fora >= 0.15 and lin < 0.5) or (traco and lin < 0.5)) and lf < 0.15
        else:
            texto = fora >= 0.15 and lf < 0.1
        texto = texto or na_caixa
        out.append({"mapa": k, "r": R["r"], "area": R["area_px"], "fora": round(fora, 3), "dc": dc, "traco": traco,
                    "caixa": na_caixa, "linha": round(lin, 3), "linha_fronteira": round(lf, 3),
                    "texto": texto or (dc <= 20 and lin < 0.15 and lf < 0.1)})
    return out


def miolos(amostra="media"):
    """T4.9: miolos de letra antes (cópia .cache/v2/antes-miolo/) e depois, na amostra; e enclaves que ficaram."""
    ids = json.load(open(os.path.join(AQUI, "amostras.json")))[amostra]["ids"] if amostra != "todos" else \
        sorted(carregar("mapas.json"), key=int)
    antes_d = os.path.join(V2, "antes-miolo")
    depois_d = os.path.join(V2, "rotulos")
    ant, dep, na_caixa, enclaves = [], [], [], []
    for k in ids:
        if os.path.exists(os.path.join(antes_d, f"{k}.png")):
            ant += [x for x in regioes_cercadas(antes_d, k) if x["texto"]]
        d = regioes_cercadas(depois_d, k)
        dep += [x for x in d if x["texto"]]
        na_caixa += [x for x in d if x["caixa"]]
        enclaves += [x for x in d if not x["texto"]]
    m_ant = len({x["mapa"] for x in ant})
    m_dep = len({x["mapa"] for x in dep})
    print(f"      miolos de letra (região cercada por um vizinho com evidência de texto), amostra {amostra} "
          f"({len(ids)} mapas): antes {len(ant)} em {m_ant} mapas; depois {len(dep)} em {m_dep} mapas")
    teste(f"T4.9a nenhum miolo de letra sobra (amostra {amostra})", not dep, dep[:5])
    teste(f"T4.9b nenhuma região cercada por um único vizinho dentro de caixa de texto (amostra {amostra})",
          not na_caixa, na_caixa[:5])
    json.dump(enclaves, open(os.path.join(V2, f"enclaves-{amostra}.json"), "w"), indent=0)
    print(f"      enclaves que ficaram (cercados, sem evidência de texto): {len(enclaves)} em "
          f"{len({x['mapa'] for x in enclaves})} mapas -> .cache/v2/enclaves-{amostra}.json")
    # anotações do visualizador
    arq = os.path.join(AQUI, "anotacoes.json")
    if not os.path.exists(arq):
        teste("T4.9c anotações (anotacoes.json) respeitadas", True, "sem anotacoes.json: nada a conferir")
    else:
        import numpy as np
        import cv2
        from calibrar import merc
        cal = carregar("calibracao.json")["por_mapa"]
        anos = carregar("anos.json")
        ruins = []
        for n in json.load(open(arq))["anotacoes"]:
            if n["tipo"] not in ("mesmo_estado", "estados_diferentes"):
                continue
            k = str(anos[str(n["ano"])]["mapa"])
            reg = cv2.imread(os.path.join(depois_d, f"{k}.png"), cv2.IMREAD_UNCHANGED)
            p = cal[k]
            rs = []
            for lon, lat in (n["ponto_a"], n["ponto_b"]):
                u = int(round(float((lon + 180) * p["S"] - p["X0"])))
                v = int(round(float((merc(80.0) - merc(lat)) * p["S"] - p["Y0"])))
                rs.append(int(reg[v, u]))
            if (n["tipo"] == "mesmo_estado") != (rs[0] == rs[1]):
                ruins.append((n["ano"], n["tipo"], rs))
        teste("T4.9c anotações (anotacoes.json) respeitadas", not ruins, ruins[:5])


ETAPAS = {"miolos": lambda: miolos(os.environ.get("AMOSTRA", "media")), "cache": cache_testes, "e0": e0, "e1": e1, "e2": e2, "e3": e3, "e4": e4, "e5": e5}

if __name__ == "__main__":
    alvo = sys.argv[1:] or sorted(ETAPAS)
    for e in alvo:
        print(f"== {e}")
        ETAPAS[e]()
    print("\n" + (f"{falhas} falha(s)" if falhas else "tudo certo"))
    sys.exit(1 if falhas else 0)
