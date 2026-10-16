#!/usr/bin/env python3
# E7 do mapa geral (v2): nomes dos estados, lidos nas etiquetas do próprio vídeo.
# Uso (na raiz do repositório):
#   PYTHONPATH=~/.cache/mapa-biblia-lib/lib python3 scripts/mapa-geral/nomear.py textos [id ...]
#       [--amostra rapida|media|todos] [--variante <nome>] [--forcar]
#
# E7a "textos": para cada mapa distinto, as etiquetas (texto.detectar) e as leituras de cada uma (texto.ler).
#   Loja por chave (cache.py): .cache/v2/obj/e7a/<chave>.json, apontador .cache/v2/textos/<id>.json; a chave sai de
#   texto.PARAMS, do hash do PNG do mapa e dos rótulos da E4e (a letra clara só vale dentro de região colorida).
#   Formato: {"caixas": [[tipo, x, y, w, h, hash_recorte, [[texto, nota, tam],
#   ...]], ...]}.
#   Caches por recorte (hash = sha1 dos pixels do recorte, caixa + MARGEM_REC px, + tipo), em .cache/v2/e7/:
#   ocr/<chave do grupo "ocr">.jsonl  {"h", "r": [leituras brutas]}   (o caro: os motores de OCR)
#   nota/<chave do grupo "nota">.jsonl {"h", "r": [[texto, nota, tam], ...]}   (a conferência por renderização)
#   Mudar só a nota relê o cache do OCR. Um rótulo que não muda de um mapa para o seguinte (o caso comum) é lido uma
#   vez só.
# Lê .cache/v2/mapas.json e .cache/v2/mapas/<id>.png.
import hashlib, json, os, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/.cache/mapa-biblia-lib/lib"))
sys.path.insert(0, AQUI)
import numpy as np
import cv2
cv2.setNumThreads(1)
import cache
import texto

V2 = cache.V2
VERSAO_A = 1
PROCS = int(os.environ.get("MAPA_GERAL_PROCS", "4"))      # processos em paralelo (8 derrubavam a máquina: ~1 GB cada)
_MEM = {"ocr": {}, "nota": {}}      # hash do recorte -> resultado (cada processo carrega ao iniciar e só lê)


def arq_mem(qual):
    p = os.path.join(V2, "e7", qual)
    os.makedirs(p, exist_ok=True)
    return os.path.join(p, cache.chave(VERSAO_A, texto.grupo(qual), [])[:16] + ".jsonl")


def carregar_mem():
    for qual in _MEM:
        a = arq_mem(qual)
        if os.path.exists(a):
            for linha in open(a):
                try:
                    d = json.loads(linha)
                except ValueError:
                    continue            # linha cortada por uma rodada interrompida
                _MEM[qual][d["h"]] = d["r"]


def hash_recorte(im, caixa):
    tipo, x, y, w, h = caixa
    c = texto.recorte(im, x, y, w, h, texto.PARAMS["MARGEM_REC"])
    return hashlib.sha1(tipo.encode() + str(c.shape).encode() + c.tobytes()).hexdigest()[:20]


def chave_mapa(k, et4):
    rot = et4.caminho(k, ".png")
    return cache.chave(VERSAO_A, texto.PARAMS, [cache.hash_arquivo(os.path.join(V2, "mapas", f"{k}.png")),
                                                cache.hash_arquivo(os.path.realpath(rot)),
                                                cache.hash_arquivo(os.path.realpath(et4.caminho(k, ".json")))])


BRANCA = 235            # região com todos os canais >= 235 (branca, creme): não leva letra clara


def rotulos(k, et4):
    rot = cv2.imread(et4.caminho(k, ".png"), cv2.IMREAD_UNCHANGED)
    info = json.load(open(et4.caminho(k, ".json")))
    return rot, info, {q["r"] for q in info["regioes"] if min(q["cor"]) >= BRANCA}


def tarefa_textos(args):
    ids, et_m, variante, forcar = args
    et = cache.Etapa.__new__(cache.Etapa)
    et.nome, et.m = "e7a", et_m
    novas, novos, n_rec, n_cache = {}, {"ocr": {}, "nota": {}}, 0, 0
    et4 = cache.Etapa("e4e")
    for k in ids:
        t0 = time.time()
        ch = chave_mapa(k, et4)
        achado = None if forcar else et.procurar(k, ch)
        if achado:
            if et.itens(variante).get(k) != achado:
                novas[k] = achado
            continue
        im = cv2.imread(os.path.join(V2, "mapas", f"{k}.png"))
        rot, _, brancas = rotulos(k, et4)
        caixas = []
        for cx in texto.detectar(im, texto.PARAMS, rot, brancas):
            h = hash_recorte(im, cx)
            lidos = _MEM["ocr"].get(h, novos["ocr"].get(h))
            if lidos is None:
                lidos = novos["ocr"][h] = texto.ler_bruto(im, cx)
                n_rec += 1
            else:
                n_cache += 1
            cands = _MEM["nota"].get(h, novos["nota"].get(h))
            if cands is None:
                cands = novos["nota"][h] = texto.pontuar(im, cx, lidos)
            caixas.append(list(cx) + [h, cands])
        arq = et.obj(ch, ".json")
        json.dump({"caixas": caixas}, open(arq + ".tmp", "w"), separators=(",", ":"), ensure_ascii=False)
        os.replace(arq + ".tmp", arq)
        novas[k] = {"chave": ch, "hash_saida": cache.hash_arquivo(arq), "segundos": round(time.time() - t0, 2)}
    return novas, novos, n_rec, n_cache


def ids_pedidos(args):
    mapas = json.load(open(os.path.join(V2, "mapas.json")))

    def opcao(nome):
        return sys.argv[sys.argv.index(nome) + 1] if nome in sys.argv else None
    amostra = opcao("--amostra") or "todos"
    soltos = [a for a in args if not a.startswith("--") and a not in (amostra, opcao("--variante"))]
    if soltos:
        return soltos
    if amostra == "todos":
        return sorted(mapas, key=lambda k: mapas[k]["quadro"])
    return json.load(open(os.path.join(AQUI, "amostras.json")))[amostra]["ids"]


def textos(args):
    ids = ids_pedidos(args)
    et = cache.Etapa("e7a")
    variante = (sys.argv[sys.argv.index("--variante") + 1] if "--variante" in sys.argv else None) \
        or cache.exp_atual() or et.m["aprovada"] or "base"
    et.garantir(variante, {"versao": VERSAO_A, **texto.PARAMS})
    t0 = time.time()
    tl = max(1, min(20, len(ids) // 16))   # lotes de mapas seguidos: o processo reaproveita os rótulos que não
                                           # mudam; até 20 mapas, para gravar o progresso com frequência
    lotes = [ids[i:i + tl] for i in range(0, len(ids), tl)]
    n_rec = n_cache = 0
    with open(arq_mem("ocr"), "a") as f_ocr, open(arq_mem("nota"), "a") as f_nota, ProcessPoolExecutor(PROCS, initializer=carregar_mem) as ex:
        futs = [ex.submit(tarefa_textos, (l, et.m, variante, "--forcar" in sys.argv)) for l in lotes]
        for i, fu in enumerate(as_completed(futs), 1):
            novas, novos, nr, nc = fu.result()
            n_rec += nr
            n_cache += nc
            for f, qual in ((f_ocr, "ocr"), (f_nota, "nota")):
                for h, r in novos[qual].items():
                    f.write(json.dumps({"h": h, "r": r}, ensure_ascii=False, separators=(",", ":")) + "\n")
                f.flush()
            if novas:
                et.m["variantes"][variante]["itens"].update(novas)
                et.gravar()
            if i % 10 == 0 or i == len(lotes):
                dec = time.time() - t0
                print(f"lotes {i}/{len(lotes)}  recortes lidos {n_rec}, do cache {n_cache}  {dec:.0f} s, "
                      f"faltam ~{dec / i * (len(lotes) - i):.0f} s", flush=True)
    if variante == et.m["aprovada"] or et.m["aprovada"] is None:
        et.aprovar(variante)
    print(f"e7a ({variante}): {len(ids)} mapas, {n_rec} recortes lidos, {n_cache} do cache, {time.time() - t0:.0f} s")


# ------------------------------------------------------------------ E7b: etiqueta -> região -> entidade
NOTA_MIN = 0.55         # leitura abaixo disso é descartada (caixa falsa ou ilegível)
NOTA_CURTA = 0.8        # leitura com até 2 letras ("A", "Ka.") precisa de nota maior (caixa falsa lê letra solta)
RAIO_PERTO = 30         # etiqueta sem região própria: estado sem etiqueta mais próximo até 30 px (1920×960)
FRACAO_REGIAO = 0.15    # região sob a etiqueta: a que cobre mais da caixa, se >= 15 % (estados pequenos: a caixa
                        # passa por vários)


def fracoes(rot, x, y, w, h, estados):
    sub = rot[y:y + h, x:x + w]
    vals, cnt = np.unique(sub, return_counts=True)
    return {int(v): int(n) / sub.size for v, n in zip(vals, cnt) if int(v) in estados}


LIGACOES = {"of", "de", "la", "the", "del", "and", "du", "des", "da", "do", "el", "al", "von", "und", "i", "y", "e",
            "en", "le", "les", "di", "der", "den", "am", "an", "on", "upon", "&"}


def nome_valido(t):
    """Etiqueta do vídeo: palavras com inicial maiúscula (fora as de ligação: "of", "de", "la"...), alguma com >= 2
    letras ou uma abreviação ("A.", "Ka."). Tira as leituras-lixo de caixas falsas ("ew v", "i", "J")."""
    pal = t.split(" ")
    if any(not (p[0].isupper() or p in LIGACOES) for p in pal):
        return False
    if pal[0] in LIGACOES or pal[-1] in LIGACOES:
        return False
    return any(sum(c.isalpha() for c in p) >= 2 for p in pal) or t.endswith(".")


def aparar(t):
    """Tira uma letra-lixo solta no começo ou no fim ("Bk Rome", "F Goguryeo", "Lydia j"): palavra de até 2 letras,
    sem ponto, ao lado de uma palavra de >= 4 letras."""
    pal = t.split(" ")
    while len(pal) > 1 and len(pal[0]) <= 2 and not pal[0].endswith(".") and pal[0] not in LIGACOES and len(pal[1]) >= 4:
        pal = pal[1:]
    while len(pal) > 1 and len(pal[-1]) <= 2 and not pal[-1].endswith(".") and pal[-1] not in LIGACOES and len(pal[-2]) >= 4:
        pal = pal[:-1]
    return " ".join(pal)


def sem_repetidas(caixas):
    """A mesma etiqueta às vezes sai em duas caixas (como texto claro e como escuro): fica a de maior nota."""
    boas = sorted((c for c in caixas if c[6]), key=lambda c: -c[6][0][1])
    out = []
    for c in boas:
        x, y, w, h = c[1:5]
        rep = False
        for d in out:
            ix = min(x + w, d[1] + d[3]) - max(x, d[1])
            iy = min(y + h, d[2] + d[4]) - max(y, d[2])
            if ix > 0 and iy > 0 and ix * iy >= 0.5 * min(w * h, d[3] * d[4]):
                rep = True
                break
        if not rep:
            out.append(c)
    return out


def pecas(caixas, rot, estados):
    """Leituras aceitas como peças [texto, nota, tam, x, y, w, h, {região: fração}]. Uma caixa que junta palavras de
    duas regiões ("W. M.", "Malwa Chandela") é dividida: cada palavra fica com a largura proporcional ao número de
    letras e com as frações da região sob ela."""
    out = []
    for cx in sem_repetidas(caixas):
        txt, nt, tam = cx[6][0]
        txt = aparar(txt)
        letras_ = sum(c.isalpha() for c in txt)
        if nt < NOTA_MIN or (letras_ <= 2 and nt < NOTA_CURTA) or not nome_valido(txt):
            continue
        tipo, x, y, w, h = cx[:5]
        fr = fracoes(rot, x, y, w, h, estados)
        fortes = [r for r, f in fr.items() if f >= FRACAO_REGIAO]
        pal = txt.split(" ")
        if len(fortes) > 1 and len(pal) > 1:
            tot = sum(len(p) for p in pal) + len(pal) - 1
            pos = 0
            for p in pal:
                x0 = x + int(w * pos / tot)
                x1 = x + max(int(w * (pos + len(p)) / tot), int(w * pos / tot) + 1)
                pos += len(p) + 1
                out.append([p, nt, tam, x0, y, x1 - x0, h, fracoes(rot, x0, y, x1 - x0, h, estados), tipo])
        else:
            out.append([txt, nt, tam, x, y, w, h, fr, tipo])
    return out


def regiao_forte(fr):
    r = max(fr, key=fr.get) if fr else None
    return r if r is not None and fr[r] >= FRACAO_REGIAO else None


def linhas_de_etiqueta(ps):
    """Junta peças que são linhas da mesma etiqueta ("Holy" / "Roman" / "Empire"): mesmo tamanho de letra (±20 %),
    uma logo abaixo da outra (vão <= 0,8 × altura), centradas (centros a <= metade da largura maior) e sobre a mesma
    região (dois estados pequenos empilhados, "Kaabu" / "Cacheu", não se juntam)."""
    ps = sorted(ps, key=lambda p: (p[4], p[3]))
    grupos = []
    for p in ps:
        for g in grupos:
            q = g[-1]
            if (abs(p[2] - q[2]) <= 0.2 * max(p[2], q[2]) and 0 <= p[4] - (q[4] + q[6]) <= 0.8 * max(p[6], q[6])
                    and abs((p[3] + p[5] / 2) - (q[3] + q[5] / 2)) <= 0.5 * max(p[5], q[5])
                    and regiao_forte(p[7]) is not None and regiao_forte(p[7]) == regiao_forte(q[7])):
                g.append(p)
                break
        else:
            grupos.append([p])
    out = []
    for g in grupos:
        x0 = min(p[3] for p in g)
        y0 = min(p[4] for p in g)
        x1 = max(p[3] + p[5] for p in g)
        y1 = max(p[4] + p[6] for p in g)
        fr = {}
        area = 0
        for p in g:
            a = p[5] * p[6]
            area += a
            for r, f in p[7].items():
                fr[r] = fr.get(r, 0) + f * a
        out.append({"texto": " ".join(p[0] for p in g), "nota": min(p[1] for p in g), "tam": max(p[2] for p in g),
                    "tipo": g[0][8], "linhas": len(g),
                    "caixa": [x0, y0, x1 - x0, y1 - y0], "fr": {r: v / area for r, v in fr.items()}})
    return out


def distancias(rot, caixa, candidatos):
    """{região: distância (px) da caixa até ela} para as regiões de `candidatos` a <= RAIO_PERTO px."""
    x, y, w, h = caixa
    H, W = rot.shape
    y0, y1, x0, x1 = max(0, y - RAIO_PERTO), min(H, y + h + RAIO_PERTO), max(0, x - RAIO_PERTO), min(W, x + w + RAIO_PERTO)
    jan = rot[y0:y1, x0:x1]
    m = np.isin(jan, list(candidatos))
    if not m.any():
        return {}
    yy, xx = np.nonzero(m)
    dx = np.maximum(0, np.maximum(x - (xx + x0), (xx + x0) - (x + w)))
    dy = np.maximum(0, np.maximum(y - (yy + y0), (yy + y0) - (y + h)))
    d = np.sqrt(dx * dx + dy * dy)
    rs = jan[yy, xx]
    out = {}
    for r in np.unique(rs):
        dm = float(d[rs == r].min())
        if dm <= RAIO_PERTO:
            out[int(r)] = dm
    return out


def associar(caixas, rot, estados):
    """{r: etiqueta} (texto, nota, tam, caixa) e as etiquetas que sobraram. Cada região fica com no máximo uma
    etiqueta: a que está sobre ela com a maior fração (desempate: letra maior). As outras etiquetas sobre ela (a de
    um estado pequeno escrita por cima do vizinho) e as que estão sobre o mar ou terra sem dono ("Kaabu", "Mane" ao
    lado da costa) vão para um estado SEM etiqueta a <= RAIO_PERTO px: primeiro os pares etiqueta–região mais perto."""
    ets = linhas_de_etiqueta(pecas(caixas, rot, estados))
    dono, sobra = {}, []
    for e in sorted(ets, key=lambda e: -max(e["fr"].values(), default=0) * 100 - e["tam"]):
        r = regiao_forte(e["fr"])
        if r is not None and r not in dono:
            dono[r] = e
        else:
            sobra.append(e)
    pares = []
    for i, e in enumerate(sobra):
        for r, d in distancias(rot, e["caixa"], estados - set(dono)).items():
            pares.append((d, -e["tam"], i, r))
    usadas = set()
    for d, _, i, r in sorted(pares):
        if i in usadas or r in dono:
            continue
        dono[r] = dict(sobra[i], deslocada=True)
        usadas.add(i)
    return dono, [e for i, e in enumerate(sobra) if i not in usadas]


def leituras_por_entidade(ent, var_e7a=None, unidas=None):
    """{ent: [[ano_de, ano_ate, mapa, texto, nota, tam, tipo, caixa, linhas], ...]} na ordem do tempo, dos mapas com
    textos (E7a). unidas: {mapa: {r_menor: r_maior}} (uniões da E7d: a etiqueta do pedaço vai para o estado unido)."""
    et7a = cache.Etapa("e7a")
    et4 = cache.Etapa("e4e")
    var = var_e7a or et7a.m["aprovada"]
    tem = et7a.itens(var)
    out = {}
    for a_de, a_ate, k, ids in ent["por_ano"]:
        if k not in tem:
            continue
        caixas = json.load(open(et7a.caminho(k, ".json", var)))["caixas"]
        rot, info, _ = rotulos(k, et4)
        estados = {q["r"] for q in info["regioes"] if q["tipo"] == "estado"}
        dono, _ = associar(caixas, rot, estados)
        un = (unidas or {}).get(k, {})
        por = {}
        for r, et_ in dono.items():
            r2 = un.get(str(r), str(r))
            if r2 not in por or et_["tam"] > por[r2]["tam"]:
                por[r2] = et_
        for r, e in ids.items():
            et_ = por.get(r)
            if et_:
                out.setdefault(e, []).append([a_de, a_ate, k, et_["texto"], et_["nota"], et_["tam"], et_["tipo"],
                                              et_["caixa"], et_["linhas"]])
    return out


# ------------------------------------------------------------------ E7c: votação por entidade, em trechos
PARECIDO = 0.8          # duas leituras são o mesmo nome se a semelhança (difflib, sem pontos e sem caixa) >= 0,8
TRECHO_MIN_ANOS = 15    # troca de nome que dura menos que isso e menos de 3 mapas é ruído de leitura
TRECHO_MIN_MAPAS = 3
REAV_CANDS = 6          # grafias de um trecho reavaliadas pelo desenho (as mais apoiadas)
REAV_RECORTES = 6       # recortes (mapas diferentes, etiqueta de uma linha, maior nota) usados na reavaliação
MARGEM_TROCA = 0.02     # troca de nome confirmada: cada lado explicado pelo próprio nome com folga média >= 0,02


class Reavaliador:
    """Escolhe, entre as grafias de um trecho, a que melhor explica vários recortes do vídeo de uma vez (soma das
    notas de texto.nota): um erro de OCR que se repete num recorte ("Jomaka") perde para a grafia que os outros
    recortes confirmam ("Jamaica"). Os mapas são lidos sob demanda e guardados (poucos por vez)."""

    def __init__(self):
        self.ims = {}
        self.feitas = 0
        self.conferidas = 0

    def im(self, k):
        if k not in self.ims:
            if len(self.ims) > 64:
                self.ims.clear()
            self.ims[k] = cv2.imread(os.path.join(V2, "mapas", f"{k}.png"))
        return self.ims[k]

    def recortes(self, obs):
        um = [o for o in obs if o[8] == 1]
        por_mapa = {}
        for o in sorted(um, key=lambda o: -o[4]):
            por_mapa.setdefault(o[2], o)
        return list(por_mapa.values())[:REAV_RECORTES]

    def somas(self, rec, cands):
        soma = {c: 0.0 for c in cands}
        for o in rec:
            x, y, w, h = o[7]
            ink = texto.tinta(texto.recorte(self.im(o[2]), x, y, w, h, texto.PARAMS["MARGEM_REC"]), o[6] == "claro")
            tams = [o[5] + d / 4 for d in range(-2, 3)]
            for c in cands:
                soma[c] += max(texto.nota(ink, c, t) for t in tams)
        return soma

    def __call__(self, nome, cands, obs):
        rec = self.recortes(obs)
        if not rec:
            return nome
        self.feitas += 1
        soma = self.somas(rec, cands)
        return max(cands, key=lambda c: (soma[c], c == nome))

    def troca_real(self, na, obs_a, nb, obs_b):
        """A troca de na para nb é real se, dos dois lados, o próprio nome explica melhor os recortes (média por
        recorte >= MARGEM_TROCA). Devolve True, ou o nome que vence nos dois lados juntos."""
        ra, rb = self.recortes(obs_a), self.recortes(obs_b)
        if not ra or not rb:
            return True
        self.conferidas += 1
        sa, sb = self.somas(ra, [na, nb]), self.somas(rb, [na, nb])
        if (sa[na] - sa[nb]) / len(ra) >= MARGEM_TROCA and (sb[nb] - sb[na]) / len(rb) >= MARGEM_TROCA:
            return True
        return na if sa[na] + sb[na] >= sa[nb] + sb[nb] else nb


def normal(s):
    return s.casefold().replace(".", "").replace("'", "").strip()


def parecido(a, b):
    import difflib
    return difflib.SequenceMatcher(None, normal(a), normal(b)).ratio() >= PARECIDO


def nomear_entidade(obs, pos, anos_ent, reavaliar=None):
    """obs: [[ano_de, ano_ate, mapa, texto, nota, tam]] na ordem do tempo. pos: ano -> posição na sequência.
    Devolve [[ano_de, ano_ate, nome, apoio, n_leituras]] cobrindo a vida da entidade (anos_ent = [de, ate])."""
    if not obs:
        return []

    def n_anos(o):
        return pos[o[1]] - pos[o[0]] + 1
    # grupos de leituras parecidas (a mais apoiada primeiro)
    apoio = {}
    for o in obs:
        apoio[o[3]] = apoio.get(o[3], 0.0) + n_anos(o) * o[4]
    grupos = []
    for t in sorted(apoio, key=lambda t: -apoio[t]):
        for g in grupos:
            if parecido(t, g[0]):
                g.append(t)
                break
        else:
            grupos.append([t])
    gid = {t: i for i, g in enumerate(grupos) for t in g}
    # corridas de mapas com o mesmo grupo
    corr = []
    for o in obs:
        g = gid[o[3]]
        if corr and corr[-1][0] == g:
            corr[-1][1].append(o)
        else:
            corr.append([g, [o]])

    def curta(c):
        return sum(n_anos(o) for o in c[1]) < TRECHO_MIN_ANOS and len(c[1]) < TRECHO_MIN_MAPAS
    while len(corr) > 1:
        curtas = [i for i, c in enumerate(corr) if curta(c)]
        if not curtas:
            break
        i = min(curtas, key=lambda i: sum(n_anos(o) for o in corr[i][1]))
        viz = [j for j in (i - 1, i + 1) if 0 <= j < len(corr)]
        j = max(viz, key=lambda j: sum(n_anos(o) for o in corr[j][1]))
        corr[j][1] = sorted(corr[j][1] + corr[i][1], key=lambda o: pos[o[0]])
        del corr[i]
        k = 0
        while k < len(corr) - 1:                 # junta corridas vizinhas do mesmo grupo
            if corr[k][0] == corr[k + 1][0]:
                corr[k][1] += corr[k + 1][1]
                del corr[k + 1]
            else:
                k += 1
    out = []
    for i, (g, os_) in enumerate(corr):
        ap = {}
        for o in os_:
            if gid[o[3]] == g:
                ap[o[3]] = ap.get(o[3], 0.0) + n_anos(o) * o[4]
        nome = max(ap, key=lambda t: (ap[t], t))
        if reavaliar and len(ap) > 1:
            nome = reavaliar(nome, sorted(ap, key=lambda t: -ap[t])[:REAV_CANDS], [o for o in os_ if gid[o[3]] == g])
        de = anos_ent[0] if i == 0 else os_[0][0]
        out.append([de, None, nome, round(sum(ap.values()), 1), len(os_)])
    # troca de nome conferida pelo desenho: senão os dois trechos viram um, com o nome que vence nos dois lados
    if reavaliar:
        i = 0
        while i < len(out) - 1:
            if normal(out[i][2]) != normal(out[i + 1][2]):
                r = reavaliar.troca_real(out[i][2], corr[i][1], out[i + 1][2], corr[i + 1][1])
                if r is not True:
                    out[i] = [out[i][0], None, r, out[i][3] + out[i + 1][3], out[i][4] + out[i + 1][4]]
                    corr[i] = [corr[i][0], corr[i][1] + corr[i + 1][1]]
                    del out[i + 1], corr[i + 1]
                    if i > 0:
                        i -= 1
                    continue
            elif out[i][2] == out[i + 1][2]:
                out[i] = [out[i][0], None, out[i][2], out[i][3] + out[i + 1][3], out[i][4] + out[i + 1][4]]
                corr[i] = [corr[i][0], corr[i][1] + corr[i + 1][1]]
                del out[i + 1], corr[i + 1]
                continue
            i += 1
    inv = {v: k for k, v in pos.items()}
    for i in range(len(out) - 1):
        out[i][1] = inv[pos[out[i + 1][0]] - 1]
    out[-1][1] = anos_ent[1]
    return out


GAP_JUNTAR = 10         # anos entre o fim de um id e o começo do outro, para juntar pelo nome
VERSAO_N = 1


def regioes_de(vet, rs):
    import rastrear
    return rastrear.rasterizar({"regioes": {r: vet["regioes"][r] for r in rs if r in vet["regioes"]}}) > 0


def juntar_por_nome(ent, trechos, pos, et_vet, var_vet):
    """Ids da E6 que são o mesmo estado: B começa até GAP_JUNTAR anos depois do fim de A, o último nome de A é o
    primeiro de B e as formas se sobrepõem (A no último mapa dele, B no primeiro; grade de 0,1°, >= MIN_CELULAS).
    Devolve {id: id_final} e a lista [[a, b, ano, nome, células]]."""
    import rastrear
    por_fim = {}
    for a, t in trechos.items():
        if t:
            por_fim.setdefault(normal(t[-1][2]), []).append(a)
    ini = {e: d["trechos"][0] for e, d in ent["entidades"].items()}
    fim = {e: d["trechos"][-1] for e, d in ent["entidades"].items()}
    vets = {}

    def vet(k):
        if k not in vets:
            if len(vets) > 40:
                vets.clear()
            vets[k] = json.load(open(et_vet.caminho(k, ".json", var_vet)))
        return vets[k]
    pai, juntadas = {}, []

    def raiz(x):
        while pai.get(x, x) != x:
            x = pai[x]
        return x
    for b, tb in sorted(trechos.items(), key=lambda kv: pos[ent["entidades"][kv[0]]["anos"][0]]):
        if not tb:
            continue
        nb = normal(tb[0][2])
        sb = ent["entidades"][b]["anos"][0]
        melhor = None
        for a in por_fim.get(nb, []):
            if a == b:
                continue
            ea = ent["entidades"][a]["anos"][1]
            if not (1 <= pos[sb] - pos[ea] <= GAP_JUNTAR):
                continue
            ka, ra = fim[a][2], [str(r) for r in fim[a][3]]
            kb, rb = ini[b][2], [str(r) for r in ini[b][3]]
            n = int((regioes_de(vet(ka), ra) & regioes_de(vet(kb), rb)).sum())
            if n >= rastrear.MIN_CELULAS and (melhor is None or n > melhor[1]):
                melhor = (a, n)
        if melhor:
            a, n = melhor
            pai[raiz(b)] = raiz(a)
            juntadas.append([a, b, sb, tb[0][2], n])
    final = {e: raiz(e) for e in ent["entidades"]}
    return final, juntadas


def costurar(trs):
    """Trechos de vários ids (em ordem de tempo) num só: junta vizinhos de mesmo nome."""
    out = []
    for t in trs:
        if out and normal(out[-1][2]) == normal(t[2]):
            out[-1] = [out[-1][0], t[1], out[-1][2] if out[-1][3] >= t[3] else t[2], round(out[-1][3] + t[3], 1),
                       out[-1][4] + t[4]]
        else:
            out.append(list(t))
    return out


def nomes(args):
    """E7 (nomes): leituras -> trechos por id da E6 (refeita sobre os vetores com as uniões) -> ids juntados pelo
    nome -> .cache/v2/obj/e7/<chave>.json, apontador .cache/v2/nomes-lidos.json:
      {"e6": {...}, "entidades": {id_e6: {"final", "trechos"}}, "finais": {id: {"ids", "anos", "trechos"}},
       "juntadas": [[a, b, ano, nome, células]], "trocas": [[id_final, ano, nome_antes, nome_depois]]}
    trechos = [[ano_de, ano_ate, nome, apoio, leituras]]; ano_de >= ano_ate (a.C. positivo)."""
    def opcao(nome, padrao=None):
        return sys.argv[sys.argv.index(nome) + 1] if nome in sys.argv else padrao
    et6 = cache.Etapa("e6")
    var6 = opcao("--variante-e6", et6.m["aprovada"])
    ent_arq = et6.caminho("entidades", ".json", var6)
    ent = json.load(open(ent_arq))
    fonte = et6.m["variantes"][var6]["params"].get("FONTE", "e5")
    et_vet = cache.Etapa(fonte)
    var_vet = opcao("--variante-vetores", et_vet.m["aprovada"])
    var_t = opcao("--variante-textos", cache.Etapa("e7a").m["aprovada"])
    un_arq = os.path.join(V2, "e7", f"unioes-{var_t}.json")
    unidas = {}
    if fonte == "e7u" and os.path.exists(un_arq):
        for k, lst in json.load(open(un_arq))["mapas"].items():
            unidas[k] = {str(rb): str(ra) for ra, rb, _ in lst}
    anos = json.load(open(os.path.join(V2, "anos.json")))
    pos = {int(a): i for i, a in enumerate(anos)}
    et7 = cache.Etapa("e7")
    variante = opcao("--variante", et7.m["aprovada"] or "base")
    params = {"versao": VERSAO_N, "PARECIDO": PARECIDO, "TRECHO_MIN_ANOS": TRECHO_MIN_ANOS,
              "TRECHO_MIN_MAPAS": TRECHO_MIN_MAPAS, "REAV_CANDS": REAV_CANDS, "REAV_RECORTES": REAV_RECORTES,
              "MARGEM_TROCA": MARGEM_TROCA, "GAP_JUNTAR": GAP_JUNTAR, **params_unioes()}
    et7.garantir(variante, params)
    et7a = cache.Etapa("e7a")
    ch = cache.chave(VERSAO_N, params, [et6.itens(var6)["entidades"]["chave"],
                                         cache.hash_obj(sorted((k, e["chave"]) for k, e in et7a.itens(var_t).items())),
                                         cache.hash_arquivo(un_arq) if unidas else None, cache.hash_arquivo(texto.FONTE)])
    t0 = time.time()
    lei = leituras_por_entidade(ent, var_t, unidas)
    reav = Reavaliador()
    trechos = {}
    for e, obs in lei.items():
        trechos[e] = nomear_entidade(obs, pos, ent["entidades"][e]["anos"], reav)
    final, juntadas = juntar_por_nome(ent, trechos, pos, et_vet, var_vet)
    grupos = {}
    for e, f in final.items():
        grupos.setdefault(f, []).append(e)
    finais, trocas = {}, []
    for f, es in grupos.items():
        es.sort(key=lambda e: pos[ent["entidades"][e]["anos"][0]])
        trs = costurar([t for e in es for t in trechos.get(e, [])])
        de = ent["entidades"][es[0]]["anos"][0]
        ate = max((ent["entidades"][e]["anos"][1] for e in es), key=lambda a: pos[a])
        if trs:
            trs[0][0], trs[-1][1] = de, ate
            for i in range(len(trs) - 1):
                trs[i][1] = list(anos)[pos[trs[i + 1][0]] - 1]
                trocas.append([f, trs[i + 1][0], trs[i][2], trs[i + 1][2]])
        finais[f] = {"ids": es, "anos": [de, ate], "trechos": [[int(t[0]), int(t[1])] + t[2:] for t in trs]}
    out = {"e6": {"variante": var6, "fonte": fonte}, "textos": var_t,
           "entidades": {e: {"final": final[e], "trechos": finais[final[e]]["trechos"]} for e in ent["entidades"]},
           "finais": finais, "juntadas": juntadas, "trocas": trocas,
           "leituras": {e: [o[:6] for o in obs] for e, obs in lei.items()}}
    arq = et7.obj(ch, ".json")
    json.dump(out, open(arq + ".tmp", "w"), ensure_ascii=False, separators=(",", ":"))
    os.replace(arq + ".tmp", arq)
    et7.m["variantes"][variante]["itens"]["nomes-lidos"] = {"chave": ch, "hash_saida": cache.hash_arquivo(arq),
                                                            "segundos": round(time.time() - t0, 1)}
    et7.gravar()
    if variante == et7.m["aprovada"] or et7.m["aprovada"] is None:
        et7.aprovar(variante)
    print(f"e7 ({variante}): {len(lei)} ids com leitura de {len(ent['entidades'])}; juntadas pelo nome {len(juntadas)}; "
          f"entidades finais {len(finais)}; trocas de nome {len(trocas)} em "
          f"{len({t[0] for t in trocas})} entidades; reavaliados {reav.feitas}, trocas conferidas {reav.conferidas}  "
          f"{time.time() - t0:.0f} s")


# ------------------------------------------------------------------ E7d: uniões dos pares candidatos da E4
# A E4 deixou como `candidatos` os pares de regiões vizinhas de mesma cor que ela não teve certeza de unir (rotulos/
# <id>.json). A E7 decide com as etiquetas (associar), de forma conservadora (pares.json: 0 uniões erradas):
#   - par com qualquer linha cinza na fronteira (fracao_linha > LINHA_UNIAO) ou cores diferentes (L1 > 20): separados;
#   - as duas partes com etiqueta: juntam só se for a mesma etiqueta;
#   - só uma parte com etiqueta (a outra é a "parte sem nome"): juntam se a fronteira for >= 50 % letra;
#   - nenhuma com etiqueta: ficam separadas (sem evidência; listadas).
# anotacoes.json "estados_diferentes" veta qualquer união que ponha os dois pontos na mesma região.
LINHA_UNIAO = 0.0
LETRA_UNIAO = 0.5
COR_UNIAO = 20
VERSAO_U = 1


def params_unioes():
    return {"versao": VERSAO_U, "LINHA_UNIAO": LINHA_UNIAO, "LETRA_UNIAO": LETRA_UNIAO, "COR_UNIAO": COR_UNIAO,
            "NOTA_MIN": NOTA_MIN, "NOTA_CURTA": NOTA_CURTA, "RAIO_PERTO": RAIO_PERTO, "FRACAO_REGIAO": FRACAO_REGIAO}


def decidir_unioes(info, dono, rot, notas):
    """[[r_maior, r_menor, motivo], ...] (fecho transitivo: cada r_menor aponta para a raiz do grupo)."""
    area = {q["r"]: q["area_px"] for q in info["regioes"]}
    linha = {}
    for c in info["candidatos"]:
        p = tuple(sorted((c["r_a"], c["r_b"])))
        d = linha.setdefault(p, {"linha": 0.0, "letra": 0.0, "cor": 0, "fronteira": 0})
        d["linha"] = max(d["linha"], c["fracao_linha"])
        d["cor"] = max(d["cor"], c["dif_cor"])
        if c["fronteira_px"] > d["fronteira"]:
            d["fronteira"], d["letra"] = c["fronteira_px"], c["fracao_letra"]
    pai = {}

    def raiz(x):
        while pai.get(x, x) != x:
            x = pai[x]
        return x
    diferentes = [(int(rot[n["px_a"][1], n["px_a"][0]]), int(rot[n["px_b"][1], n["px_b"][0]]))
                  for n in notas if n["tipo"] == "estados_diferentes"]

    def vetado(a, b):
        ra, rb = raiz(a), raiz(b)
        return any({raiz(x), raiz(y)} == {ra, rb} for x, y in diferentes)
    out = []
    for (a, b), d in sorted(linha.items(), key=lambda kv: -kv[1]["fronteira"]):
        if d["linha"] > LINHA_UNIAO or d["cor"] > COR_UNIAO or raiz(a) == raiz(b):
            continue
        ta, tb = dono.get(a), dono.get(b)
        if ta and tb:
            ok, mot = normal(ta["texto"]) == normal(tb["texto"]), "mesmo nome"
        elif ta or tb:
            ok, mot = d["letra"] >= LETRA_UNIAO, "parte sem nome"
        else:
            ok, mot = False, ""
        if ok and not vetado(a, b):
            ra, rb = raiz(a), raiz(b)
            if area.get(rb, 0) > area.get(ra, 0):
                ra, rb = rb, ra
            pai[rb] = ra
            out.append([ra, rb, mot])
    return [[raiz(rb), rb, mot] for _, rb, mot in out]


def unioes(args):
    """E7d: grava .cache/v2/e7/unioes-<variante dos textos>.json {mapa: [[r_maior, r_menor, motivo], ...]}."""
    et7a, et4 = cache.Etapa("e7a"), cache.Etapa("e4e")
    var = sys.argv[sys.argv.index("--variante-textos") + 1] if "--variante-textos" in sys.argv else et7a.m["aprovada"]
    import rotular
    cal = json.load(open(cache.calibracao()))["por_mapa"]
    notas = rotular.notas_por_mapa(cal)
    t0 = time.time()
    out, n = {}, 0
    for k in sorted(et7a.itens(var), key=int):
        rot, info, _ = rotulos(k, et4)
        estados = {q["r"] for q in info["regioes"] if q["tipo"] == "estado"}
        dono, _ = associar(json.load(open(et7a.caminho(k, ".json", var)))["caixas"], rot, estados)
        u = decidir_unioes(info, dono, rot, notas.get(k, []))
        if u:
            out[k] = u
            n += len(u)
    arq = os.path.join(V2, "e7", f"unioes-{var}.json")
    json.dump({"params": params_unioes(), "variante_textos": var, "mapas": out}, open(arq, "w"), separators=(",", ":"))
    print(f"uniões: {n} em {len(out)} mapas de {len(et7a.itens(var))}  {time.time() - t0:.0f} s -> {arq}")


def geom_de_aneis(aneis):
    import vetorizar as vz
    from shapely.geometry import Polygon
    g = Polygon()
    for a in aneis:
        g = g.symmetric_difference(Polygon(a))        # regra par-ímpar, como no desenho
    return vz.valido(g)


def tarefa_vetores(args):
    ids, et_m, variante, lista, e5_m, var_e5 = args
    import vetorizar as vz
    from shapely.ops import unary_union
    et = cache.Etapa.__new__(cache.Etapa)
    et.nome, et.m = "e7u", et_m
    e5 = cache.Etapa.__new__(cache.Etapa)
    e5.nome, e5.m = "e5", e5_m
    novas = {}
    for k in ids:
        t0 = time.time()
        u = lista.get(k, [])
        ch5 = e5.itens(var_e5)[k]["chave"]
        ch = cache.chave(VERSAO_U, params_unioes(), [ch5, u])
        achado = et.procurar(k, ch)
        if achado:
            if et.itens(variante).get(k) != achado:
                novas[k] = achado
            continue
        arq = et.obj(ch, ".json")
        base = e5.obj(ch5, ".json")
        if not u:
            if os.path.lexists(arq):
                os.remove(arq)
            os.link(base, arq)            # sem união: o mesmo arquivo da E5 (link físico, sem espaço a mais)
        else:
            v = json.load(open(base))
            grupos = {}
            for ra, rb, _ in u:
                grupos.setdefault(str(ra), []).append(str(rb))
            for ra, rbs in grupos.items():
                rs = [r for r in [ra] + rbs if r in v["regioes"]]
                if len(rs) < 2:
                    continue
                g = vz.arredondar(unary_union([geom_de_aneis(v["regioes"][r]["aneis"]) for r in rs]))
                v["regioes"][ra]["aneis"] = vz.aneis_de(g)
                for r in rs[1:]:
                    del v["regioes"][r]
            v["unidas"] = {str(rb): str(ra) for ra, rb, _ in u}
            json.dump(v, open(arq + ".tmp", "w"), separators=(",", ":"))
            os.replace(arq + ".tmp", arq)
        novas[k] = {"chave": ch, "hash_saida": cache.hash_arquivo(arq), "segundos": round(time.time() - t0, 2)}
    return novas


def vetores(args):
    """E7u: os vetores da E5 com as uniões da E7d (loja por chave; a chave inclui a lista de uniões do mapa)."""
    var_t = sys.argv[sys.argv.index("--variante-textos") + 1] if "--variante-textos" in sys.argv else cache.Etapa("e7a").m["aprovada"]
    lista = json.load(open(os.path.join(V2, "e7", f"unioes-{var_t}.json")))["mapas"]
    e5 = cache.Etapa("e5")
    var_e5 = e5.m["aprovada"]
    et = cache.Etapa("e7u")
    variante = (sys.argv[sys.argv.index("--variante") + 1] if "--variante" in sys.argv else None) or et.m["aprovada"] or "base"
    et.garantir(variante, params_unioes())
    ids = sorted(e5.itens(var_e5), key=int)
    lotes = [ids[i:i + 40] for i in range(0, len(ids), 40)]
    t0 = time.time()
    with ProcessPoolExecutor(PROCS) as ex:
        futs = [ex.submit(tarefa_vetores, (l, et.m, variante, {k: lista.get(k, []) for k in l}, e5.m, var_e5)) for l in lotes]
        for fu in as_completed(futs):
            novas = fu.result()
            if novas:
                et.m["variantes"][variante]["itens"].update(novas)
                et.gravar()
    if variante == et.m["aprovada"] or et.m["aprovada"] is None:
        et.aprovar(variante)
    print(f"e7u ({variante}): {len(ids)} mapas, {sum(1 for k in ids if lista.get(k))} com uniões  {time.time() - t0:.0f} s")


if __name__ == "__main__":
    for sub, fn in (("unioes", unioes), ("vetores", vetores)):
        if len(sys.argv) >= 2 and sys.argv[1] == sub:
            fn(sys.argv[2:])
            sys.exit(0)
    if len(sys.argv) >= 2 and sys.argv[1] == "nomes":
        nomes(sys.argv[2:])
        sys.exit(0)
    if len(sys.argv) < 2 or sys.argv[1] not in ("textos",):
        raise SystemExit(__doc__ or "uso: nomear.py textos [...]")
    textos(sys.argv[2:])
