#!/usr/bin/env python3
# E4 do mapa geral (v2): um rótulo por pixel para cada mapa distinto do vídeo (partição da terra em regiões).
# Uso (na raiz do repositório):
#   PYTHONPATH=~/.cache/mapa-biblia-lib/lib python3 scripts/mapa-geral/rotular.py [id ...] [--amostra rapida|media|todos]
#                                                                                 [--forcar] [--forcar-e] [--so-chaves]
#                                                                                 [--variante <nome>]
# A E4e grava na loja por chave (.cache/v2/obj/e4e/<chave>.png e .json; cache.py); rotulos/<id>.* são apontadores
# para a variante aprovada. Sem --variante roda a aprovada; com --variante (ou MAPA_GERAL_EXP) é um experimento
# que não toca no aprovado. Parâmetros de um experimento: MAPA_GERAL_PARAMS='{"COR_UNIAO": 19}'.
# Sub-etapas com cache (docs/mapa-geral-incremental.md): cada uma só é recalculada se a chave dela mudou (versão,
# parâmetros, hash do conteúdo das entradas). Artefatos em .cache/v2/e4/<sub>/ e manifesto.json por sub-etapa:
#   E4a  zonas planas, classificação, vãos de letra, fragmentos -> marcadores       e4/a/<id>.npz
#   E4b  watershed (partição sem frestas)                                              e4/b/<id>.png (16 bits)
#   E4d  tabela dos pares vizinhos (fronteira, letra, preenchimento, linha; áreas)     e4/d/<id>.json
#   E4e  regras (uniões pela tabela, ilhas, costa, fragmentos, minúsculas), numeração  rotulos/<id>.png e .json
# Mudar só uma regra de união refaz só a E4e. decidir_unioes() roda sobre a tabela, sem pixels.
# Lê .cache/v2/mapas/<id>.png (E2), a calibração da E3 (cache.calibracao(): calibracao.json ou a variante
# MAPA_GERAL_EXP) e frontend/mapa/mundo.json (costa).
# Grava .cache/v2/rotulos/<id>.png (16 bits; 0 = mar, 1..N = regiões de terra) e <id>.json:
#   {"regioes": [{"r": 1, "tipo": "estado"|"sem-dono", "cor": [R,G,B], "area_px", "caixa": [x0,y0,x1,y1],
#                 "texto": [[x,y,w,h], ...]}], "ornamento": [x0,y0,x1,y1]}
#
# Método ("zonas planas", medido na paleta do vídeo; ver .cache/v2/paleta.json):
#  1. A imagem é cortada em zonas planas: pixels cuja diferença máxima por canal para os vizinhos de 4 conexões é
#     <= 8 (o ruído do AV1 fica em ±3; creme 254,248,238 × branco 255,255,255 difere 17; linhas de contorno cinza
#     entre estados cremes e a antialias das bordas ficam como "borda").
#  2. Cada zona plana é classificada:
#       mar    = cor a <= 24 (L1) de 216,225,237 (RGB). Inclui os Grandes Lagos.
#       texto  = zona fina (raio inscrito <= 5,5 px, área < 4000 px) de cor quase preta (máx. canal <= 80) ou quase
#                branca (mín. canal >= 246; o creme tem mín. ~237) cuja vizinhança é >= 85 % de UMA outra zona. Letras e buracos de letras
#                (a cor do estado dentro de "o", "e") não são sementes. O ornamento do ano é mascarado.
#       semente = qualquer outra zona com área >= 25 px (estado colorido, creme, escuro, ou terra sem dono).
#     Nada é descartado por brilho: cinza-escuro, verde-petróleo e marrom são estados.
#  3. cv2.watershed com as sementes (e o mar) sobre a imagem espalha os rótulos pelas bordas, linhas e letras:
#     partição sem frestas. As cristas de gradiente seguem a fronteira real.
#  4. Tipo da região = cor mediana: branco puro (mín. canal >= 246) = "sem-dono"; o resto = "estado"
#     (inclui creme: mín. canal ~238).
#  5. Costa: onde o mar do vídeo é terra em mundo.json (máscara renderizada com a calibração) e a distância à região
#     mais próxima é <= 8 px, o rótulo dela se estende sobre o mar (a costa exata fica para a E5).
#  6. Regiões < 40 px que tocam outra região são fundidas na vizinha de maior borda comum; as que só tocam o mar são
#     ilhas e ficam.
import glob, json, os, sys, time
from concurrent.futures import ProcessPoolExecutor

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/.cache/mapa-biblia-lib/lib"))
sys.path.insert(0, AQUI)
import numpy as np
import cv2
import cache

CACHE = os.environ.get("MAPA_GERAL_CACHE") or os.path.join(AQUI, ".cache")
V2 = os.path.join(CACHE, "v2")
H, W = 960, 1920
MAR_RGB = np.array([216, 225, 237], np.int32)
LIM_BORDA = 8          # diferença máxima por canal entre vizinhos dentro de uma zona plana
LIM_MAR = 24
AREA_SEMENTE = 25
RAIO_TEXTO = 5.5
AREA_TEXTO = 4000
FRACAO_VIZINHA = 0.85
EXPANSAO_COSTA = 8
AREA_MINIMA = 40
AREA_MIOLO = 1000         # px: regiões menores que isso, cercadas por um vizinho, são testadas como miolo de letra
COR_UNIAO = 20            # L1 máxima entre "mesma cor" (ruído ±3 por canal + antialias; creme × branco >= 25)


def ornamento(g):
    """(x0, x1) da moldura do ano no quadro (cinza), como em quadros.py; None se não achar."""
    from quadros import moldura
    return moldura(g)


def zonas_planas(im):
    f = im.astype(np.int16)
    gx = np.abs(f[:, 1:] - f[:, :-1]).max(axis=2) > LIM_BORDA
    gy = np.abs(f[1:, :] - f[:-1, :]).max(axis=2) > LIM_BORDA
    borda = np.zeros(im.shape[:2], bool)
    borda[:, 1:] |= gx
    borda[:, :-1] |= gx
    borda[1:, :] |= gy
    borda[:-1, :] |= gy
    plano = (~borda).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(plano, connectivity=4)
    return n, lab, st


def evidencia_letra(px, cor):
    """Pixels que são letra sobre uma região de cor `cor` (arrays H×W×3, RGB int): texto branco (todos os canais
    puxados >= 25 % do caminho até o branco: pega a antialias das letras finas, ex. 224,155,166 sobre 140,38,57) sobre
    região colorida (mín. canal < 200), ou texto preto (máx. canal <= 80, com 1 px em volta) sobre região clara
    (máx. canal > 150). A linha cinza entre estados cremes (máx. canal ~120–160) não é letra."""
    branco = np.all(px >= cor + 0.25 * (255 - cor), axis=2) & (px.min(axis=2) > cor.min(axis=2) + 25) & (cor.min(axis=2) < 200)
    nucleo = (px.max(axis=2) <= 80).astype(np.uint8)
    preto = cv2.dilate(nucleo, np.ones((3, 3), np.uint8)).astype(bool) & (cor.max(axis=2) > 150)
    return branco | preto


def indices_por_rotulo(arr):
    """{rótulo: índices planos dos pixels} para todos os rótulos de arr, numa passada (argsort estável; em uint16 o
    numpy usa radix sort, ~10x mais rápido)."""
    plano = arr.ravel()
    if plano.min() >= 0 and plano.max() < 65536:
        plano = plano.astype(np.uint16)
    ordem = np.argsort(plano, kind="stable")
    ordenado = plano[ordem]
    ini = np.concatenate([[0], np.flatnonzero(ordenado[1:] != ordenado[:-1]) + 1])   # sem um segundo sort (np.unique)
    vals = ordenado[ini]
    fim = np.append(ini[1:], len(plano))
    return {int(v): ordem[a:b] for v, a, b in zip(vals.tolist(), ini.tolist(), fim.tolist())}


def caixa_de(idx):
    ys, xs = np.divmod(idx, W)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def e4a(im):
    """E4a: zonas planas, classificação (mar / texto / semente), vãos de letra, grupos de fragmentos -> marcadores
    do watershed e o que as etapas seguintes precisam (texto, cor de cada marcador, caixas de texto, ornamento)."""
    n, lab, st = zonas_planas(im)
    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    lr = ornamento(gray)
    orn = np.zeros((H, W), bool)
    if lr:
        orn[815:945, max(0, lr[0] - 22):lr[1] + 22] = True
    else:
        orn[815:945, 600:1400] = True
    rgb = im[:, :, ::-1]
    # cor mediana e raio inscrito de cada zona (nas caixas)
    classe = np.zeros(n, np.int8)       # 0 = nada, 1 = mar, 2 = texto candidato, 3 = semente
    cores = np.zeros((n, 3), np.int32)
    areas = st[:, cv2.CC_STAT_AREA]
    for i in range(1, n):
        a = areas[i]
        if a < 3:
            continue
        x, y, w, h = st[i, 0], st[i, 1], st[i, 2], st[i, 3]
        m = lab[y:y + h, x:x + w] == i
        px = rgb[y:y + h, x:x + w][m]
        c = np.median(px, axis=0).astype(np.int32)
        cores[i] = c
        if a < 12:
            continue            # só a cor (para os fragmentos de estados cobertos pelo nome)
        if np.abs(c - MAR_RGB).sum() <= LIM_MAR:
            classe[i] = 1
            continue
        if a < AREA_SEMENTE:
            continue
        # zona do ornamento não é mapa
        if orn[y:y + h, x:x + w][m].mean() > 0.5:
            continue
        pretoebranco = c.max() <= 80 or c.min() >= 246
        if pretoebranco and a < AREA_TEXTO:
            dt = cv2.distanceTransform(np.pad(m.astype(np.uint8), 1), cv2.DIST_L2, 3)
            if dt.max() <= RAIO_TEXTO:
                classe[i] = 2
                continue
        classe[i] = 3
    # vizinhança dos candidatos a texto: a zona de semente/mar que domina o anel de 4 px
    texto = np.zeros(n, bool)
    cand = np.where(classe == 2)[0]
    k = np.ones((3, 3), np.uint8)
    dono_texto = {}
    for i in cand:
        x, y, w, h = st[i, 0], st[i, 1], st[i, 2], st[i, 3]
        x0, y0, x1, y1 = max(0, x - 5), max(0, y - 5), min(W, x + w + 5), min(H, y + h + 5)
        sub = lab[y0:y1, x0:x1]
        m = (sub == i).astype(np.uint8)
        anel = cv2.dilate(m, k, iterations=4).astype(bool) & ~(m > 0)
        ids = sub[anel]
        ids = ids[(classe[ids] == 1) | (classe[ids] == 3)]
        if len(ids) == 0:
            classe[i] = 3
            continue
        u, c = np.unique(ids, return_counts=True)
        j = c.argmax()
        if cores[i].min() >= 246 and classe[u[j]] == 1:
            classe[i] = 3           # branco cercado de mar: ilha sem dono (não existe texto branco sobre o mar)
        elif c[j] / float((sub[anel] > 0).sum() + 1e-9) >= FRACAO_VIZINHA:
            texto[i] = True
            dono_texto[i] = int(u[j])
        else:
            classe[i] = 3           # branco/preto fino mas entre várias zonas: faixa real
    # buraco ou vão de letra: pedaço cercado (anel de 6 px) em >= 85 % por UMA semente de cor parecida (L1 <= 60: o
    # vão entre letras brancas fica tingido) e com a borda imediata (2 px) >= 50 % de pixels de letra (preto <= 80,
    # ou branco >= 246 sobre cor). Um estado creme de verdade dentro de terra branca tem borda de linha cinza (~135),
    # não de letra, e fica.
    def buraco_de_letra(ids_zona, cor):
        mg_full = np.isin(lab, ids_zona)
        ys, xs = np.where(mg_full)
        x0, y0, x1, y1 = max(0, xs.min() - 8), max(0, ys.min() - 8), min(W, xs.max() + 9), min(H, ys.max() + 9)
        mg = mg_full[y0:y1, x0:x1].astype(np.uint8)
        sub = lab[y0:y1, x0:x1]
        anel = cv2.dilate(mg, k, iterations=6).astype(bool) & (mg == 0)
        ids = sub[anel]
        ids = ids[((classe[ids] == 1) | (classe[ids] == 3)) & ~np.isin(ids, ids_zona)]
        if len(ids) < 8:
            return False
        u, c = np.unique(ids, return_counts=True)
        j = c.argmax()
        if c[j] / float(len(ids)) < FRACAO_VIZINHA or np.abs(cores[u[j]] - cor).sum() > 60 or areas[u[j]] <= mg.sum():
            return False
        borda = cv2.dilate(mg, k, iterations=2).astype(bool) & (mg == 0)
        jan = rgb[y0:y1, x0:x1].astype(np.int32)
        letra = evidencia_letra(jan, np.broadcast_to(np.asarray(cor, np.int32), jan.shape))
        return letra[borda].mean() >= 0.5

    for i in np.where(classe == 3)[0]:
        if areas[i] < 500 and buraco_de_letra([i], cores[i]):
            classe[i] = 0
    # estados quase cobertos pelo próprio nome ("K.", "M."): sobram só fragmentos < 25 px da cor do estado entre as
    # letras. Fragmentos de 3..24 px da mesma cor (L1 <= COR_UNIAO), a <= 10 px uns dos outros, somando >= 20 px e
    # que não sejam vão de letra de outra semente (buraco_de_letra), viram uma semente só.
    grupos = []
    peq = np.where((classe == 0) & (areas >= 3) & (areas < AREA_SEMENTE))[0]
    peq = [i for i in peq if not (cores[i].max() <= 80 or cores[i].min() >= 246) and not orn[st[i, 1], st[i, 0]]]
    if peq:
        classes_cor = []
        restantes = list(peq)
        while restantes:
            i0 = restantes[0]
            mesma = [i for i in restantes if np.abs(cores[i] - cores[i0]).sum() <= COR_UNIAO]
            classes_cor.append(mesma)
            restantes = [i for i in restantes if i not in set(mesma)]
        for ids_c in classes_cor:
            if sum(areas[i] for i in ids_c) < 20:
                continue
            m = np.isin(lab, ids_c).astype(np.uint8)
            ng, lg = cv2.connectedComponents(cv2.dilate(m, k, iterations=5), connectivity=8)
            for g in range(1, ng):
                membros = [i for i in ids_c if (lg[st[i, 1]:st[i, 1] + st[i, 3], st[i, 0]:st[i, 0] + st[i, 2]][
                    lab[st[i, 1]:st[i, 1] + st[i, 3], st[i, 0]:st[i, 0] + st[i, 2]] == i] == g).any()]
                if sum(areas[i] for i in membros) < 20:
                    continue
                if buraco_de_letra(membros, cores[membros[0]]):
                    continue
                grupos.append(membros)
    # marcadores do watershed: 0 = desconhecido; 1 = mar; 2.. = sementes
    marc = np.zeros((H, W), np.int32)
    sem_ids = np.where(classe == 3)[0]
    nova = {int(i): 2 + j for j, i in enumerate(sem_ids)}
    prox = 2 + len(sem_ids)
    for membros in grupos:
        for i in membros:
            nova[int(i)] = prox
        prox += 1
    tabela = np.zeros(n, np.int32)
    tabela[classe == 1] = 1
    for i, v in nova.items():
        tabela[i] = v
    marc = tabela[lab]
    marc[orn & (marc == 0)] = 0
    caixas = []
    for i in cand:
        if texto[i]:
            caixas.append([int(v) for v in st[i, :4]])
    cor_marc = {int(v): cores[i].astype(np.int32) for i, v in nova.items()}
    return {"marc": marc.astype(np.int32), "texto_px": texto[lab], "cor_marc": cor_marc, "caixas": caixas,
            "orn": orn, "lr": (list(map(int, lr)) if lr else None)}


def e4b(im, a):
    """E4b: watershed a partir dos marcadores da E4a (partição sem frestas); linhas do watershed vão para o vizinho."""
    ws = cv2.watershed(im, a["marc"].astype(np.int32))
    # linhas de watershed (-1): vizinho mais próximo
    inval = ws <= 0
    if inval.any():
        ok = (~inval).astype(np.uint8)
        _, lbl = cv2.distanceTransformWithLabels(1 - ok, cv2.DIST_L2, 3, labelType=cv2.DIST_LABEL_PIXEL)
        ys, xs = np.where(ok > 0)
        ids_pix = np.zeros(lbl.max() + 1, np.int32)
        ids_pix[lbl[ys, xs]] = ws[ys, xs]
        ws = np.where(inval, ids_pix[lbl], ws)
    return ws.astype(np.int32)


def rotular_mapa(im, terra_mundo=None):
    """Todas as sub-etapas de uma vez, sem cache (referência para os testes de cache)."""
    a = e4a(im)
    ws = e4b(im, a)
    d = e4d(im, ws, a)
    return e4e(im, ws, a, d, terra_mundo)


LIM_COR_TABELA = 60     # a tabela da E4d guarda caixas e pontos das partes de pares com cor a até 60 (L1)


def e4d(im, ws, a):
    """E4d: estatísticas dos pares de regiões vizinhas do watershed (tabela usada pelas regras da E4e):
    pares [chave, fronteira_px, letra, preenchimento, linha] na ordem de descoberta, área de cada rótulo, e caixa e
    ponto interior das partes de pares com cor parecida."""
    k = np.ones((3, 3), np.uint8)
    rgb = im[:, :, ::-1]
    cor_marc = a["cor_marc"]
    # estados cortados pelo próprio nome (as letras separam o estado em duas zonas da mesma cor): estatísticas da
    # fronteira entre regiões vizinhas de cor quase igual (L1 <= COR_UNIAO): letra, preenchimento, linha
    tpx = cv2.dilate(a["texto_px"].astype(np.uint8), k, iterations=1).astype(bool)
    # evidência de letra: pixel branco sobre região colorida, ou escuro sobre região clara (as letras finas não formam
    # zona plana própria; só aparecem como pixels de borda)
    cor_lab = np.zeros((ws.max() + 1, 3), np.int32)
    for v, c_m in cor_marc.items():
        cor_lab[v] = c_m
    cl = cor_lab[np.maximum(ws, 0)]
    pxr = rgb.astype(np.int32)
    # (preto <= 80: a linha cinza entre estados cremes tem máximo de canal ~120–160, mediana 135, medido em 999 d.C.;
    # a evidência vale só no próprio pixel da fronteira, sem dilatação, para que uma fronteira que corre ao lado de
    # um rótulo não conte como letra)
    tpx |= evidencia_letra(pxr, cl)
    # "sem linha": os DOIS pixels do par têm a cor de preenchimento (L1 <= 24 da cor da sua região). Estados vizinhos
    # de mesma cor sempre têm linha de contorno entre eles (cinza ~135 nos cremes); sem linha, a quebra entre as duas
    # zonas planas é só degrau de compressão (bloco do AV1) dentro do mesmo estado.
    # Também vale a mistura da cor da região com o mar (gargalo fino na costa: istmo da Baja Califórnia, faixa da
    # Flórida no golfo), medida como distância L1 <= 40 ao segmento cor -> mar, só a <= 2 px do mar (senão a linha
    # cinza clara entre dois cremes passaria por "mistura").
    seg = (MAR_RGB - cl).astype(np.float32)
    tt_ = np.clip(((pxr - cl) * seg).sum(axis=2) / np.maximum((seg * seg).sum(axis=2), 1.0), 0, 1)
    resid = np.abs(pxr - (cl + tt_[:, :, None] * seg)).sum(axis=2)
    junto_mar = cv2.dilate((ws == 1).astype(np.uint8), k, iterations=2).astype(bool)
    preench = (np.abs(pxr - cl).sum(axis=2) <= 24) | ((resid <= 40) & junto_mar)
    # linha de contorno: cinza sem saturação (máx. canal 100..215, saturação < 20) longe (> 1 px) de núcleo de letra
    nucleo_l = cv2.dilate((pxr.max(axis=2) <= 80).astype(np.uint8), k, iterations=1).astype(bool)
    sat_l = pxr.max(axis=2) - pxr.min(axis=2)
    linha = (sat_l < 20) & (pxr.max(axis=2) >= 100) & (pxr.max(axis=2) <= 215) & ~nucleo_l
    pares = {}
    for a, b, t, f, l_ in ((ws[:, :-1], ws[:, 1:], tpx[:, :-1] | tpx[:, 1:], preench[:, :-1] & preench[:, 1:], linha[:, :-1] | linha[:, 1:]),
                           (ws[:-1, :], ws[1:, :], tpx[:-1, :] | tpx[1:, :], preench[:-1, :] & preench[1:, :], linha[:-1, :] | linha[1:, :])):
        d = (a != b) & (a >= 2) & (b >= 2)
        lo = np.minimum(a[d], b[d]).astype(np.int64)
        hi = np.maximum(a[d], b[d]).astype(np.int64)
        chave = lo * 100000 + hi
        u_k, inv_k = np.unique(chave, return_inverse=True)
        tt_ = t[d]
        cnt = np.bincount(inv_k)
        c_t = np.bincount(inv_k, weights=tt_)
        c_f = np.bincount(inv_k, weights=f[d] & ~tt_)
        c_l = np.bincount(inv_k, weights=l_[d])
        for kk, n0, n1, n2, n3 in zip(u_k.tolist(), cnt.tolist(), c_t.tolist(), c_f.tolist(), c_l.tolist()):
            e = pares.setdefault(kk, [0, 0, 0, 0])
            e[0] += int(n0)
            e[1] += int(n1)
            e[2] += int(n2)
            e[3] += int(n3)
    area_marc = np.bincount(np.maximum(ws, 0).ravel())
    idx_ws = indices_por_rotulo(ws)
    partes_ = set()
    for kk in pares:
        a_, b_ = divmod(kk, 100000)
        if np.abs(cor_marc[a_] - cor_marc[b_]).sum() <= LIM_COR_TABELA:
            partes_ |= {a_, b_}
    caixa, ponto = {}, {}
    for v in sorted(partes_):
        x0, y0, x1, y1 = caixa_de(idx_ws[v])
        caixa[v] = [x0, y0, x1, y1]
        m = (ws[y0:y1 + 1, x0:x1 + 1] == v).astype(np.uint8)
        dt = cv2.distanceTransform(np.pad(m, 1), cv2.DIST_L2, 3)[1:-1, 1:-1]
        y_, x_ = np.unravel_index(int(dt.argmax()), dt.shape)
        ponto[v] = [int(x_ + x0), int(y_ + y0)]
    return {"pares": [[kk] + e for kk, e in pares.items()], "area": area_marc.tolist(),
            "caixa": {str(v): c for v, c in caixa.items()}, "ponto": {str(v): p for v, p in ponto.items()}}


def decidir_unioes(pares, cor_marc, area):
    """Regras de união sobre a tabela da E4d (sem pixels). Devolve (uniões [(a, b, registro)], candidatos [registro]).
    Pura: a mesma tabela dá sempre o mesmo resultado, e serve para testar regras novas em segundos."""
    unioes, candidatos = [], []
    for kk, tot, tt, ff, ll in pares:
        a, b = divmod(kk, 100000)
        dc = int(np.abs(cor_marc[a] - cor_marc[b]).sum())
        if tot < 2 or dc > COR_UNIAO:
            continue
        outro = (tot - tt - ff) / tot
        claro = min(cor_marc[a].min(), cor_marc[b].min()) >= 200
        tipo_u = None
        if tot < 6:
            if not claro and min(area[a], area[b]) < 1500 and (tt + ff) / tot >= 0.7:
                tipo_u = "gargalo"
        elif claro and ll / tot >= 0.15:
            tipo_u = None
        elif tt / tot >= 0.9 and outro <= 0.1:
            tipo_u = "letra"
        elif not claro and (tt + ff) / tot >= 0.9 and outro <= 0.1:
            tipo_u = "sem-linha"
        reg_u = {"a": int(a), "b": int(b), "fracao_letra": round(tt / tot, 3), "fracao_sem_linha": round(ff / tot, 3),
                 "fracao_linha": round(ll / tot, 3), "fracao_outro": round(outro, 3), "fronteira_px": int(tot),
                 "dif_cor": dc, "areas": [int(area[a]), int(area[b])]}
        if tipo_u is None:
            candidatos.append(reg_u)
        else:
            reg_u["tipo"] = tipo_u
            unioes.append(reg_u)
    return unioes, candidatos


def e4e(im, ws0, a, d, terra_mundo=None, notas=None):
    """E4e: regras (uniões da tabela da E4d, ilhas, costa, fragmentos, minúsculas), numeração final e informações."""
    k = np.ones((3, 3), np.uint8)
    rgb = im[:, :, ::-1]
    pxr = rgb.astype(np.int32)
    # canais por pixel calculados uma vez (em uint8/int16: max/min sobre o eixo de cor em int32 é lento)
    mx = np.maximum(np.maximum(im[:, :, 0], im[:, :, 1]), im[:, :, 2])
    mn = np.minimum(np.minimum(im[:, :, 0], im[:, :, 1]), im[:, :, 2])
    dmar = (np.abs(im[:, :, 2].astype(np.int16) - int(MAR_RGB[0])) + np.abs(im[:, :, 1].astype(np.int16) - int(MAR_RGB[1]))
            + np.abs(im[:, :, 0].astype(np.int16) - int(MAR_RGB[2])))
    ws = ws0.copy()
    orn = a["orn"]
    lr = a["lr"]
    cor_marc = a["cor_marc"]
    cor_lab = np.zeros((ws.max() + 1, 3), np.int32)
    for v, c_m in cor_marc.items():
        cor_lab[v] = c_m
    pai = {}

    def raiz(x):
        while pai.get(x, x) != x:
            x = pai[x]
        return x
    # anotações do visualizador (scripts/mapa-geral/anotacoes.json) deste mapa, em pixels: estados_diferentes veta
    # qualquer junção que ponha os dois pontos na mesma região (uniões, fragmentos, miolos, minúsculas);
    # mesmo_estado junta as duas regiões no fim; problema só é registrado
    notas = notas or []
    diferentes = [(n["px_a"], n["px_b"]) for n in notas if n["tipo"] == "estados_diferentes"]

    def vetado(rot, x_, y_):
        """True se juntar os rótulos x_ e y_ (rot(ponto) dá o rótulo atual de um ponto) une dois pontos marcados
        como estados diferentes."""
        for pa, pb in diferentes:
            la, lb = rot(pa), rot(pb)
            if {la, lb} == {x_, y_} and la != lb:
                return True
        return False
    rot_ws = lambda pt: raiz(int(ws0[pt[1], pt[0]]))
    rot_reg = lambda pt: int(reg[pt[1], pt[0]])
    vetos = []
    area = d["area"]
    unioes, candidatos = decidir_unioes(d["pares"], cor_marc, area)
    if diferentes:
        ok_u = []
        for u in unioes:
            if vetado(rot_ws, raiz(u["a"]), raiz(u["b"])):
                vetos.append({"etapa": "uniao", "a": u["a"], "b": u["b"]})
                candidatos.append({x_: y_ for x_, y_ in u.items() if x_ != "tipo"})
            else:
                pai[raiz(u["b"])] = raiz(u["a"])
                ok_u.append(u)
        unioes = ok_u
        pai.clear()
    # Uniões na E4: só as quase certas. Medido num conjunto rotulado à mão (88 pares de 999 e 1799,
    # scripts/mapa-geral/pares.json), as estatísticas da fronteira não separam "estado partido pelo próprio nome" de
    # "dois estados da mesma cor com o nome encostado na linha". Os demais pares de mesma cor viram "candidatos"
    # (gravados com as estatísticas) e são decididos na E7, com os nomes lidos e a evidência dos outros anos.
    #   letra:     >= 90 % da fronteira é letra e <= 10 % é outra coisa (linha)
    #   sem-linha: letra + preenchimento >= 90 % e <= 10 % de outra coisa (degrau de compressão, vão de letra)
    #   gargalo:   contato < 6 px, pedaço < 1.500 px, letra + preenchimento >= 70 % (istmo da Baja, faixa da Flórida)
    # Entre estados claros (creme/branco), só "letra": no conjunto rotulado, gargalo, sem-linha e fragmento uniram
    # cremes diferentes (Cr. × B., I. × Ma., Soma. × K.).
    for u in unioes:
        pai[raiz(u["b"])] = raiz(u["a"])
        menor = u["a"] if area[u["a"]] < area[u["b"]] else u["b"]
        u["caixa_menor"] = d["caixa"][str(menor)]
    for c_ in candidatos:
        c_["ponto_a"] = d["ponto"][str(c_["a"])]
        c_["ponto_b"] = d["ponto"][str(c_["b"])]
    if pai:
        tab = np.arange(ws.max() + 1, dtype=np.int32)
        for v in list(pai) + [x for x in pai.values()]:
            tab[v] = raiz(v)
        ws = tab[ws]
    # ilhas finas (Cuba, Jamaica, Bahamas na escala do mundo inteiro): quase só pixels de borda, sem zona plana que
    # sirva de semente, e o watershed as dá ao mar. Pixels rotulados como mar que não têm cor de mar e são coloridos
    # (saturação >= 25) ou brancos (mín. canal >= 246) formam componentes; >= 4 px viram terra: da região vizinha de
    # maior contato se tocar terra (antialias da costa), senão região nova (ilha). Texto preto sobre o mar (cinza,
    # saturação < 25) fica mar.
    sat = mx.astype(np.int16) - mn
    nao_mar = dmar > LIM_MAR
    # (o halo branco dos rótulos sobre o mar não é ilha: os pixels a <= 2 px do núcleo preto das letras saem)
    perto_letra = cv2.dilate((mx <= 80).astype(np.uint8), k, iterations=2).astype(bool)
    cand_ilha = (ws == 1) & nao_mar & ((sat >= 25) | (mn >= 246)) & ~orn & ~perto_letra
    ni, li, sti, _ = cv2.connectedComponentsWithStats(cand_ilha.astype(np.uint8), connectivity=8)
    maior_ws = int(ws.max())
    for c_ in range(1, ni):
        if sti[c_, cv2.CC_STAT_AREA] < 4:
            continue
        x, y, w, h = sti[c_, :4]
        x0, y0, x1, y1 = max(0, x - 2), max(0, y - 2), min(W, x + w + 2), min(H, y + h + 2)
        m = li[y0:y1, x0:x1] == c_
        cor_i = np.median(pxr[y0:y1, x0:x1][m], axis=0)
        anel = cv2.dilate(m.astype(np.uint8), k, iterations=1).astype(bool) & ~m
        viz = ws[y0:y1, x0:x1][anel]
        viz = viz[viz >= 2]
        alvo = None
        if len(viz):
            # toca terra: é a antialias da costa (ou um pedaço da ilha), vai para a vizinha de maior contato
            u_, c_c = np.unique(viz, return_counts=True)
            alvo = int(u_[c_c.argmax()])
        if alvo is None:
            alvo = max(maior_ws, len(cor_lab) - 1) + 1
            maior_ws = alvo
            cor_lab = np.vstack([cor_lab, np.zeros((alvo + 1 - len(cor_lab), 3), np.int32)])
            cor_lab[alvo] = cor_i.astype(np.int32)
        ws[y0:y1, x0:x1][m] = alvo
    mar = ws == 1
    # renumera regiões 2.. -> 1..N
    reg = ws.copy()
    reg[mar] = 0
    # ornamento sem dono: onde o ornamento cobre mar ou terra, o watershed espalhou o vizinho (aceito)
    # costa: estende regiões sobre o mar de vídeo que é terra em mundo.json, até EXPANSAO_COSTA px
    if terra_mundo is not None:
        terra_ok = (reg > 0).astype(np.uint8)
        dist, lbl = cv2.distanceTransformWithLabels(1 - terra_ok, cv2.DIST_L2, 3, labelType=cv2.DIST_LABEL_PIXEL)
        ys, xs = np.where(terra_ok > 0)
        ids_pix = np.zeros(lbl.max() + 1, np.int32)
        ids_pix[lbl[ys, xs]] = reg[ys, xs]
        ext = mar & terra_mundo & (dist <= EXPANSAO_COSTA)
        reg[ext] = ids_pix[lbl[ext]]
    # fragmentos: região < 150 px cuja vizinha de mesma cor (L1 <= COR_UNIAO) ocupa >= 40 % do seu perímetro é um
    # pedaço dela (vão de letra encostado na borda, ponta de faixa fina). Estado pequeno de verdade com rótulo próprio
    # passa de 150 px (o "K." de Bengala tem 386).
    idx_reg = indices_por_rotulo(reg)
    pxr_plano = pxr.reshape(-1, 3)
    cor_reg = {v: np.median(pxr_plano[ix], axis=0) for v, ix in idx_reg.items() if v > 0}
    cont_reg = {v: len(ix) for v, ix in idx_reg.items() if v > 0}
    caixa_reg = {v: caixa_de(ix) for v, ix in idx_reg.items() if v > 0}
    for v, c_ in sorted(cont_reg.items(), key=lambda t: t[1]):
        if c_ >= 150:
            continue
        x0, y0, x1, y1 = caixa_reg[v]
        x0, y0, x1, y1 = max(0, x0 - 1), max(0, y0 - 1), min(W, x1 + 2), min(H, y1 + 2)
        sub = reg[y0:y1, x0:x1]
        m = (sub == v).astype(np.uint8)
        if not m.any():
            continue
        anel = cv2.dilate(m, k, iterations=1).astype(bool) & (m == 0)
        viz = sub[anel]
        tot = len(viz)
        viz = viz[(viz > 0) & (viz != v)]
        if not len(viz) or tot == 0:
            continue
        u, cc = np.unique(viz, return_counts=True)
        j = cc.argmax()
        alvo = int(u[j])
        if cc[j] / tot >= 0.4 and np.abs(cor_reg[alvo] - cor_reg[v]).sum() <= COR_UNIAO and cor_reg[v].min() < 200 \
                and not (diferentes and vetado(rot_reg, alvo, v)):
            ys, xs = np.where(m > 0)
            unioes.append({"a": alvo, "b": int(v), "tipo": "fragmento", "fracao_letra": 0.0, "fracao_sem_linha": 0.0,
                           "fracao_perimetro": round(float(cc[j] / tot), 3), "fronteira_px": int(cc[j]),
                           "dif_cor": int(np.abs(cor_reg[alvo] - cor_reg[v]).sum()), "areas": [int(cont_reg[alvo]), int(c_)],
                           "caixa_menor": [int(xs.min() + x0), int(ys.min() + y0), int(xs.max() + x0), int(ys.max() + y0)], "_reg": alvo})
            sub[m > 0] = alvo
            cont_reg[alvo] = cont_reg.get(alvo, 0) + c_
            ca, cv_ = caixa_reg[alvo], caixa_reg[v]
            caixa_reg[alvo] = (min(ca[0], cv_[0]), min(ca[1], cv_[1]), max(ca[2], cv_[2]), max(ca[3], cv_[3]))
            for u2 in unioes:
                if u2.get("_reg") == v:
                    u2["_reg"] = alvo
    # miolos de letra: o miolo de "c", "Z", "o", "e" etc. vira região própria quando a suavização o tinge. Região
    # pequena (< AREA_MIOLO px), sem contato com o mar, cercada (anel de 2 px) em >= 90 % por UM vizinho, é absorvida
    # por ele quando há evidência de texto, sem exigir cor parecida:
    #   - vizinho colorido (mín. canal < 200; letras brancas): o anel de fora é >= 15 % letra (evidencia_letra com a
    #     cor do vizinho), < 50 % linha de contorno, e a fronteira comum < 15 % linha (sem contar a antialias das
    #     letras, que é mistura da cor do vizinho com branco ou preto);
    #   - vizinho claro (creme/branco; letras pretas): >= 15 % letra e < 10 % de linha de contorno na fronteira comum
    #     (pares de pixels região × vizinho). Um estado creme dentro de outro (Pr. em Lanna, Kandy em Kotte) é
    #     separado pela linha cinza; um pedaço do mesmo estado cortado pelo nome (Hausa, Malwa) não tem linha;
    #   - a cor da própria região é cor de letra (quase branca sobre colorido, quase preta sobre claro) e há >= 5 % de
    #     letra em volta (o traço da letra virou região: "n", "Bra");
    #   - o centro dela cai numa caixa de texto da E4a.
    #   - (sem texto) a cor é a mesma do vizinho (L1 <= COR_UNIAO) e não há linha de contorno (anel < 15 %, fronteira
    #     < 10 %).
    # Região que toca o mar (no rótulo ou na cor do vídeo, por causa da expansão da costa) nunca é miolo.
    # Enclaves reais (Luba, Incas, faixas amarelas, ilhas cercadas) têm o anel na cor do vizinho ou numa linha cinza,
    # sem letra, e ficam; os que ficam são gravados em "enclaves" para conferência.
    miolos = []
    caixas_txt = a["caixas"]
    # linha de contorno (cinza sem saturação, longe de núcleo de letra), como na E4d
    nucleo_m = cv2.dilate((mx <= 80).astype(np.uint8), k, iterations=1).astype(bool)
    linha_m = (sat < 20) & (mx >= 100) & (mx <= 215) & ~nucleo_m
    mar_video = dmar <= LIM_MAR
    # várias passadas: o miolo de um "B" fica cercado pelo traço da letra (que também virou região); quando o traço
    # é absorvido, o miolo passa a ser cercado pela cor do estado e cai na regra "mesma cor, sem linha"
    for _passada in range(4):
        enclaves = []
        mudou = False
        idx_reg = indices_por_rotulo(reg)
        cores_p = {}

        def cor_de(r_):
            if r_ not in cores_p:
                cores_p[r_] = np.median(pxr.reshape(-1, 3)[idx_reg[r_]], axis=0) if r_ in idx_reg else np.zeros(3)
            return cores_p[r_]
        for v, ix in sorted(idx_reg.items(), key=lambda t: len(t[1])):
            if v == 0 or len(ix) >= AREA_MIOLO:
                continue
            x0, y0, x1, y1 = caixa_de(ix)
            bx = [x0, y0, x1, y1]
            x0, y0, x1, y1 = max(0, x0 - 4), max(0, y0 - 4), min(W, x1 + 5), min(H, y1 + 5)
            sub = reg[y0:y1, x0:x1]
            m = (sub == v).astype(np.uint8)
            if not m.any():
                continue
            anel = cv2.dilate(m, k, iterations=2).astype(bool) & (m == 0)
            viz = sub[anel]
            # toca o mar (no rótulo ou na cor do vídeo: a expansão da costa pinta o mar perto da terra): ilha, fica
            # (>= 5 % do anel: a antialias de uma letra branca sobre vermelho dá, aqui e ali, um pixel cor de mar)
            if not len(viz) or (viz == 0).any() or mar_video[y0:y1, x0:x1][anel].mean() >= 0.05:
                continue
            u, cc = np.unique(viz, return_counts=True)
            j = cc.argmax()
            dono = int(u[j])
            cor_d = cor_de(dono)
            # vizinhos da mesma cor do dono contam como dono (o traço de um "B" cerca os miolos, que têm a cor do
            # estado de fora: anel = estado de fora + miolos)
            mesmo = sum(int(c_) for u_, c_ in zip(u.tolist(), cc.tolist())
                        if u_ == dono or np.abs(cor_de(u_) - cor_d).sum() <= COR_UNIAO)
            if mesmo / len(viz) < 0.9:
                continue
            jan = pxr[y0:y1, x0:x1]
            cor_v = np.median(jan[m > 0], axis=0)
            fora = float(evidencia_letra(jan, np.broadcast_to(cor_d.astype(np.int32), jan.shape))[anel].mean())
            lin = float(linha_m[y0:y1, x0:x1][anel].mean())
            dc = float(np.abs(cor_v - cor_d).sum())
            # o traço da letra virou região: cor quase branca sobre vizinho colorido (ou quase preta sobre claro), e
            # alguma letra em volta (>= 5 %: uma faixa branca de terra sem dono num estado colorido não tem)
            cor_letra = (cor_v.min() >= 225 and cor_d.min() < 200) or (cor_v.max() <= 80 and cor_d.max() > 150)
            # traço fino (raio inscrito <= 3,5 px: traço de letra de até 7 px) também é letra, mesmo sem letra em
            # volta (o "n" de Tang, o "J" de Jin, o "Y" de Yuan viravam enclave); um enclave creme/branco real
            # (o "A." em 1121 d.C.) é mais grosso
            raio = float(cv2.distanceTransform(np.pad(m, 1), cv2.DIST_L2, 3).max())
            traco = bool(cor_letra and (fora >= 0.05 or raio <= 3.5))
            cx, cy = (bx[0] + bx[2]) // 2, (bx[1] + bx[3]) // 2
            na_caixa = any(x <= cx <= x + w and y <= cy <= y + h for x, y, w, h in caixas_txt)
            dt = cv2.distanceTransform(np.pad(m, 1), cv2.DIST_L2, 3)[1:-1, 1:-1]
            py_, px_ = np.unravel_index(int(dt.argmax()), dt.shape)
            reg_m = {"r": int(v), "dono": dono, "area_px": int(len(ix)), "caixa": bx, "ponto": [int(px_ + x0), int(py_ + y0)],
                     "raio": round(raio, 1),
                     "fracao_letra": round(fora, 3),
                     "fracao_linha": round(lin, 3), "dif_cor": int(dc), "traco": traco, "caixa_texto": na_caixa}
            colorido = cor_d.min() < 200
            # fronteira comum (pares de pixels vizinhos região × dono): fração que é linha de contorno. Entre claros
            # (creme/branco) é o que separa dois estados; um pedaço do mesmo estado cortado pelo nome tem fronteira de
            # letra e de preenchimento, sem linha
            dono_m = np.isin(sub, [u_ for u_ in u.tolist() if u_ == dono or np.abs(cor_de(u_) - cor_d).sum() <= COR_UNIAO])
            # linha de contorno aqui: cinza que NÃO é mistura da cor do vizinho com o branco ou o preto (a antialias das
            # letras brancas sobre um estado acinzentado, como o bege dos Gaznévidas, também é cinza)
            def mistura(alvo):
                sg = (np.asarray(alvo, np.float32) - cor_d).astype(np.float32)
                t_ = np.clip(((jan - cor_d) * sg).sum(axis=2) / max(float((sg * sg).sum()), 1.0), 0, 1)
                return np.abs(jan - (cor_d + t_[:, :, None] * sg)).sum(axis=2) <= 30
            # (só com vizinho colorido: a linha cinza entre dois cremes É uma mistura de creme com escuro)
            lin_loc = linha_m[y0:y1, x0:x1]
            if cor_d.min() < 200:
                lin_loc = lin_loc & ~mistura([255, 255, 255]) & ~mistura([0, 0, 0])
            lin_f = []
            for aa, bb, la, lb in ((m[:, :-1] > 0, dono_m[:, 1:], lin_loc[:, :-1], lin_loc[:, 1:]),
                                   (m[:, 1:] > 0, dono_m[:, :-1], lin_loc[:, 1:], lin_loc[:, :-1]),
                                   (m[:-1, :] > 0, dono_m[1:, :], lin_loc[:-1, :], lin_loc[1:, :]),
                                   (m[1:, :] > 0, dono_m[:-1, :], lin_loc[1:, :], lin_loc[:-1, :])):
                par = aa & bb
                lin_f.append(((la | lb)[par]).astype(np.float32))
            lin_f = np.concatenate(lin_f)
            lin_front = float(lin_f.mean()) if len(lin_f) else 0.0
            reg_m["fracao_linha_fronteira"] = round(lin_front, 3)
            # nos dois casos a fronteira comum não pode ser linha de contorno (estados vizinhos da mesma cor, como
            # as 13 colônias em vermelho, são separados por linha cinza e o nome pode encostar nela)
            if colorido:
                texto = ((fora >= 0.15 and lin < 0.5) or (traco and lin < 0.5)) and lin_front < 0.15
            else:
                texto = fora >= 0.15 and lin_front < 0.1
            texto = texto or na_caixa
            mesma_cor = dc <= COR_UNIAO and lin < 0.15 and lin_front < 0.1
            if (texto or mesma_cor) and diferentes and vetado(rot_reg, dono, v):
                vetos.append({"etapa": "miolo", "r": int(v), "dono": dono})
                texto = mesma_cor = False
            if texto or mesma_cor:
                sub[m > 0] = dono
                reg_m["motivo"] = "texto" if texto else "mesma-cor"
                miolos.append(reg_m)
                mudou = True
            else:
                enclaves.append(reg_m)
        if not mudou:
            break
    # fusão de regiões minúsculas que tocam outra região
    # (repete: uma pequena pode se fundir em outra pequena já processada e o resultado continuar pequeno)
    for _passada in range(6):
        idx_reg = indices_por_rotulo(reg)
        pequenas = [v for v, ix in sorted(idx_reg.items(), key=lambda t: len(t[1])) if v > 0 and len(ix) < AREA_MINIMA]
        mudou = False
        for v in pequenas:
            x0, y0, x1, y1 = caixa_de(idx_reg[v])
            x0, y0, x1, y1 = max(0, x0 - 1), max(0, y0 - 1), min(W, x1 + 2), min(H, y1 + 2)
            sub = reg[y0:y1, x0:x1]
            m = (sub == v).astype(np.uint8)
            if not m.any():
                continue
            anel = cv2.dilate(m, k, iterations=1).astype(bool) & (m == 0)
            vizinhos = sub[anel]
            vizinhos = vizinhos[(vizinhos > 0) & (vizinhos != v)]
            if len(vizinhos):
                u, c = np.unique(vizinhos, return_counts=True)
                if diferentes and vetado(rot_reg, int(u[c.argmax()]), v):
                    continue
                sub[m > 0] = u[c.argmax()]
                mudou = True
        if not mudou:
            break
    # anotações "mesmo_estado": junta as regiões dos dois pontos (se forem terra e diferentes)
    for n in notas:
        if n["tipo"] != "mesmo_estado":
            continue
        la, lb = rot_reg(n["px_a"]), rot_reg(n["px_b"])
        if la and lb and la != lb:
            reg[reg == lb] = la
            unioes.append({"a": la, "b": lb, "tipo": "anotacao", "anotacao": n["id"], "ponto": n["px_b"],
                           "caixa_menor": [n["px_b"][0], n["px_b"][1], n["px_b"][0], n["px_b"][1]], "_reg": la})
    # compacta ids
    vals = np.unique(reg[reg > 0])
    mapa_id = np.zeros(int(reg.max()) + 1, np.int32)
    for j, v in enumerate(vals, 1):
        mapa_id[v] = j
    reg = mapa_id[reg].astype(np.uint16)
    # informações por região
    info = []
    idx_reg = indices_por_rotulo(reg)
    rgb_plano = rgb.reshape(-1, 3)
    for r in range(1, len(vals) + 1):
        ix = idx_reg[r]
        cor = np.median(rgb_plano[ix], axis=0).astype(int)
        tipo = "sem-dono" if cor.min() >= 246 else "estado"
        info.append({"r": r, "tipo": tipo, "cor": [int(c) for c in cor], "area_px": int(len(ix)),
                     "caixa": list(caixa_de(ix)), "texto": []})
    # uniões feitas (para conferência): região final, partes, caixa da fronteira
    idx_ws_final = indices_por_rotulo(ws)
    for u in unioes:
        if "_reg" in u:
            alvo = u.pop("_reg")
            u["r"] = int(mapa_id[alvo]) if alvo < len(mapa_id) else 0
            if u["r"] == 0:
                x0, y0, x1, y1 = u["caixa_menor"]
                u["r"] = int(reg[(y0 + y1) // 2, (x0 + x1) // 2])
            continue
        ix = idx_ws_final.get(raiz(u["a"]))
        u["r"] = int(np.bincount(reg.ravel()[ix]).argmax()) if ix is not None and len(ix) else 0
    cand_final = []
    for c_ in candidatos:
        ra = int(reg[c_["ponto_a"][1], c_["ponto_a"][0]])
        rb = int(reg[c_["ponto_b"][1], c_["ponto_b"][0]])
        if ra and rb and ra != rb:
            c_["r_a"], c_["r_b"] = ra, rb
            cand_final.append(c_)
    candidatos = cand_final
    # caixas de texto: zonas texto e zonas pretas/brancas finas, atribuídas à região do centro delas
    for x, y, w, h in a["caixas"]:
        cx, cy = x + w // 2, y + h // 2
        r = int(reg[cy, cx])
        if r > 0:
            info[r - 1]["texto"].append([x, y, w, h])
    # miolos (absorvidos) entram nas uniões, com a região final do dono; enclaves que ficaram, com a região final
    for mm in miolos:
        d_ = mm["dono"]
        unioes.append({"a": d_, "b": mm["r"], "tipo": "miolo", "motivo": mm["motivo"], "fracao_letra": mm["fracao_letra"],
                       "fracao_linha": mm["fracao_linha"], "dif_cor": mm["dif_cor"],
                       "traco": mm["traco"], "caixa_texto": mm["caixa_texto"], "areas": [0, mm["area_px"]],
                       "caixa_menor": mm["caixa"], "ponto": mm["ponto"], "r": int(reg[mm["ponto"][1], mm["ponto"][0]])})
    enc_final = []
    for e_ in enclaves:
        rr = int(mapa_id[e_["r"]]) if e_["r"] < len(mapa_id) else 0
        dd = int(mapa_id[e_["dono"]]) if e_["dono"] < len(mapa_id) else 0
        if rr and dd and rr != dd:
            enc_final.append(dict(e_, r=rr, dono=dd))
    anot = {"aplicadas": [n["id"] for n in notas if n["tipo"] in ("mesmo_estado", "estados_diferentes")],
            "vetos": vetos, "problemas": [{"id": n["id"], "ponto": n.get("px"), "comentario": n.get("comentario", "")}
                                          for n in notas if n["tipo"] == "problema"]}
    return reg, info, lr, unioes, candidatos, enc_final, anot


# ------------------------------------------------------------------ cache por sub-etapa (docs/mapa-geral-incremental.md)
# Incremente a VERSAO de uma sub-etapa sempre que a lógica dela mudar (não a cada comentário).
VERSAO = {"a": 1, "b": 1, "d": 1, "e": 14}     # e2: miolos de letra; e3: passadas + mesma cor sem linha; e4: anel por cor;
                                               # e5: limiar de letra conforme o vizinho (colorido / claro); e6: ponto do miolo;
                                               # e7: mar do vídeo no anel; linha na fronteira comum (claros);
                                               # e8: traço só com cor quase branca/preta e >= 5 % de letra;
                                               # e9: mar do vídeo só conta com >= 5 % do anel;
                                               # e10: linha na fronteira veta também com vizinho colorido;
                                               # e11/12: linha não conta a antialias (mistura vizinho × branco/preto) se o vizinho é colorido;
                                               # e14: traço fino (raio <= 3,5) é letra; anotações


def params(sub):
    if sub == "a":
        return {"LIM_BORDA": LIM_BORDA, "LIM_MAR": LIM_MAR, "AREA_SEMENTE": AREA_SEMENTE, "RAIO_TEXTO": RAIO_TEXTO,
                "AREA_TEXTO": AREA_TEXTO, "FRACAO_VIZINHA": FRACAO_VIZINHA, "COR_UNIAO": COR_UNIAO}
    if sub == "d":
        return {"LIM_COR_TABELA": LIM_COR_TABELA}
    if sub == "e":
        return {"COR_UNIAO": COR_UNIAO, "EXPANSAO_COSTA": EXPANSAO_COSTA, "AREA_MINIMA": AREA_MINIMA, "LIM_MAR": LIM_MAR,
                "AREA_MIOLO": AREA_MIOLO}
    return {}


def chave_sub(sub, h_png, h_a=None, h_b=None, h_d=None, cal_k=None, mundo_h=None, nota=None):
    """Chave de cache de uma sub-etapa para um mapa (a fórmula fica só aqui: processar() e o painel usam a mesma).
    E4a: PNG do mapa; E4b: + E4a; E4d: + E4b; E4e: + E4d, calibração do mapa, mundo.json, lagos e, se houver, a
    anotação do mapa (anotacoes.json; só entra na chave dos mapas anotados)."""
    if sub == "a":
        return cache.chave(VERSAO["a"], params("a"), [h_png])
    if sub == "b":
        return cache.chave(VERSAO["b"], params("b"), [h_png, h_a])
    if sub == "d":
        return cache.chave(VERSAO["d"], params("d"), [h_png, h_a, h_b])
    from calibrar import LAGOS_NO_VIDEO
    entradas = [h_png, h_a, h_b, h_d, cache.hash_obj(cal_k), mundo_h, sorted(LAGOS_NO_VIDEO)]
    if nota:
        entradas.append(cache.hash_obj(nota))
    return cache.chave(VERSAO["e"], params("e"), entradas)


def _sobrepor_params():
    """MAPA_GERAL_PARAMS='{"COR_UNIAO": 19}' muda parâmetros sem editar o código (usado pelo teste T-C3)."""
    extra = os.environ.get("MAPA_GERAL_PARAMS")
    if extra:
        for nome, v in json.loads(extra).items():
            if nome in globals():
                globals()[nome] = v


_sobrepor_params()


_E4E = []


def etapa_e():
    if not _E4E:
        _E4E.append(cache.Etapa("e4e"))
    return _E4E[0]


def arquivos(k, variante=None):
    """Artefatos de um mapa. "e"/"e_json": o rótulo final da variante pedida (argumento ou MAPA_GERAL_EXP) se ela o
    tem, senão o aprovado (apontador em rotulos/)."""
    e4 = os.path.join(V2, "e4")
    et = etapa_e()
    return {"a": os.path.join(e4, "a", f"{k}.npz"), "b": os.path.join(e4, "b", f"{k}.png"),
            "d": os.path.join(e4, "d", f"{k}.json"),
            "e": et.caminho(k, ".png", variante), "e_json": et.caminho(k, ".json", variante)}


def gravar_a(caminho, a):
    ids = np.array(sorted(a["cor_marc"]), np.int32)
    cores_m = np.array([a["cor_marc"][int(i)] for i in ids], np.int32).reshape(-1, 3)
    tmp = cache.atomico(caminho)
    np.savez_compressed(tmp, marc=a["marc"], texto=np.packbits(a["texto_px"]), orn=np.packbits(a["orn"]),
                        ids=ids, cores=cores_m, caixas=np.array(a["caixas"], np.int32).reshape(-1, 4),
                        lr=np.array(a["lr"] or [-1, -1], np.int32))
    os.replace(tmp, caminho)


def ler_a(caminho):
    z = np.load(caminho)
    n = H * W
    lr = z["lr"].tolist()
    return {"marc": z["marc"], "texto_px": np.unpackbits(z["texto"])[:n].reshape(H, W).astype(bool),
            "orn": np.unpackbits(z["orn"])[:n].reshape(H, W).astype(bool),
            "cor_marc": {int(i): c for i, c in zip(z["ids"].tolist(), z["cores"])},
            "caixas": z["caixas"].tolist(), "lr": None if lr[0] < 0 else lr}


def gravar_png16(caminho, arr):
    assert arr.min() >= 0 and arr.max() < 65536
    tmp = cache.atomico(caminho)
    cv2.imwrite(tmp, arr.astype(np.uint16))
    os.replace(tmp, caminho)


def gravar_json(caminho, obj):
    tmp = cache.atomico(caminho)
    json.dump(obj, open(tmp, "w"), sort_keys=True, separators=(",", ":"))
    os.replace(tmp, caminho)


def hash_e(arq):
    return cache.sha1((cache.hash_arquivo(arq["e"]) + cache.hash_arquivo(arq["e_json"])).encode())


ANOTACOES = os.path.join(AQUI, "anotacoes.json")


def notas_por_mapa(cal):
    """{mapa: [anotação com pontos em pixels]} a partir de scripts/mapa-geral/anotacoes.json (visualizar.html)."""
    import math
    if not os.path.exists(ANOTACOES):
        return {}
    m80 = 1.25 * math.degrees(math.log(math.tan(math.pi / 4 + 0.4 * math.radians(80.0))))

    def px(p, lonlat):
        lon, lat = lonlat
        y = 1.25 * math.degrees(math.log(math.tan(math.pi / 4 + 0.4 * math.radians(lat))))
        return [min(W - 1, max(0, int(round((lon + 180) * p["S"] - p["X0"])))),
                min(H - 1, max(0, int(round((m80 - y) * p["S"] - p["Y0"]))))]
    out = {}
    for n in json.load(open(ANOTACOES)).get("anotacoes", []):
        k = str(n["mapa"])
        if k not in cal:
            continue
        r = {"id": n["id"], "tipo": n["tipo"], "comentario": n.get("comentario", "")}
        if n["tipo"] == "problema":
            r["px"] = px(cal[k], n["ponto"])
        else:
            r["px_a"], r["px_b"] = px(cal[k], n["ponto_a"]), px(cal[k], n["ponto_b"])
        out.setdefault(k, []).append(r)
    return out


def processar(args):
    """Um lote de mapas: para cada um, cada sub-etapa só é recalculada se a chave mudou. Devolve as entradas novas
    dos manifestos, o que foi recalculado e o tempo de cada sub-etapa."""
    ids, mans, forcar, variante, man_e = args
    et_e = cache.Etapa.__new__(cache.Etapa)
    et_e.nome, et_e.m = "e4e", man_e
    cv2.setNumThreads(1)      # 8 processos em paralelo: threads do OpenCV dentro de cada um só disputam CPU
    forcar_e = forcar == "e"  # --forcar-e: refaz só a E4e (medir o tempo de uma mudança de regra)
    forcar = forcar is True
    from calibrar import carregar_mundo, renderizar, LAGOS_NO_VIDEO
    cal = json.load(open(cache.calibracao()))["por_mapa"]
    notas = notas_por_mapa(cal)
    mundo_h = cache.hash_arquivo(os.path.join(AQUI, "..", "..", "frontend", "mapa", "mundo.json"))
    terra = lagos = None
    novas = {s_: {} for s_ in "abde"}
    feitos = {s_: 0 for s_ in "abde"}
    tempos = {}
    falhas = {}
    for k in ids:
        try:
            t_mapa = {}
            arq = arquivos(k)
            png = os.path.join(V2, "mapas", f"{k}.png")
            h_png = cache.hash_arquivo(png)
            im = None
            dados = {}

            def imagem():
                nonlocal im
                if im is None:
                    im = cv2.imread(png)
                return im
            # E4a
            ch = chave_sub("a", h_png)
            if forcar or cache.precisa(mans["a"], k, ch, arq["a"]):
                t0 = time.time()
                dados["a"] = e4a(imagem())
                gravar_a(arq["a"], dados["a"])
                t_mapa["a"] = time.time() - t0
                novas["a"][k] = cache.entrada(ch, cache.hash_arquivo(arq["a"]), round(t_mapa["a"], 3), arq["a"])
                feitos["a"] += 1
            h_a = cache.hash_de(novas["a"] if k in novas["a"] else mans["a"], k, arq["a"])
            if k not in novas["a"] and "stat" not in mans["a"].get(k, {"stat": 1}):
                novas["a"][k] = dict(mans["a"][k], stat=cache.assinatura(arq["a"]))     # manifesto antigo

            def a_():
                if "a" not in dados:
                    dados["a"] = ler_a(arq["a"])
                return dados["a"]
            # E4b
            ch = chave_sub("b", h_png, h_a)
            if forcar or cache.precisa(mans["b"], k, ch, arq["b"]):
                t0 = time.time()
                dados["b"] = e4b(imagem(), a_())
                gravar_png16(arq["b"], dados["b"])
                t_mapa["b"] = time.time() - t0
                novas["b"][k] = cache.entrada(ch, cache.hash_arquivo(arq["b"]), round(t_mapa["b"], 3), arq["b"])
                feitos["b"] += 1
            h_b = cache.hash_de(novas["b"] if k in novas["b"] else mans["b"], k, arq["b"])
            if k not in novas["b"] and "stat" not in mans["b"].get(k, {"stat": 1}):
                novas["b"][k] = dict(mans["b"][k], stat=cache.assinatura(arq["b"]))     # manifesto antigo

            def b_():
                if "b" not in dados:
                    dados["b"] = cv2.imread(arq["b"], cv2.IMREAD_UNCHANGED).astype(np.int32)
                return dados["b"]
            # E4d
            ch = chave_sub("d", h_png, h_a, h_b)
            if forcar or cache.precisa(mans["d"], k, ch, arq["d"]):
                t0 = time.time()
                dados["d"] = e4d(imagem(), b_(), a_())
                gravar_json(arq["d"], dados["d"])
                t_mapa["d"] = time.time() - t0
                novas["d"][k] = cache.entrada(ch, cache.hash_arquivo(arq["d"]), round(t_mapa["d"], 3), arq["d"])
                feitos["d"] += 1
            h_d = cache.hash_de(novas["d"] if k in novas["d"] else mans["d"], k, arq["d"])
            if k not in novas["d"] and "stat" not in mans["d"].get(k, {"stat": 1}):
                novas["d"][k] = dict(mans["d"][k], stat=cache.assinatura(arq["d"]))     # manifesto antigo
            # E4e
            ch = chave_sub("e", h_png, h_a, h_b, h_d, cal[k], mundo_h, notas.get(k))
            achado = None if (forcar or forcar_e) else et_e.procurar(k, ch)
            if achado:
                if et_e.itens(variante).get(k) != achado:
                    novas["e"][k] = achado            # objeto já existe (outra variante, ou lógica antiga): reaproveita
            else:
                t0 = time.time()
                if "d" not in dados:
                    dados["d"] = json.load(open(arq["d"]))
                if terra is None:
                    terra, lagos = carregar_mundo()
                p = cal[k]
                tm = renderizar(terra, lagos, p["S"], p["X0"], p["Y0"]) > 0
                reg, info, orn, unioes, candidatos, enclaves, anot = e4e(imagem(), b_(), a_(), dados["d"], tm, notas.get(k))
                png_o, json_o = et_e.obj(ch, ".png"), et_e.obj(ch, ".json")
                gravar_png16(png_o, reg)
                # mesmo formato de antes da divisão (json.dump padrão, ordem de inserção)
                tmp = cache.atomico(json_o)
                saida_j = {"regioes": info, "ornamento": orn, "unioes": unioes, "candidatos": candidatos, "enclaves": enclaves}
                if notas.get(k):
                    saida_j["anotacoes"] = anot
                json.dump(saida_j, open(tmp, "w"))
                os.replace(tmp, json_o)
                t_mapa["e"] = time.time() - t0
                novas["e"][k] = {"chave": ch, "hash_saida": hash_e({"e": png_o, "e_json": json_o}),
                                 "segundos": round(t_mapa["e"], 3)}
                feitos["e"] += 1
            tempos[k] = t_mapa
        except Exception as ex_:          # registra e segue; a lista de falhas sai no fim
            falhas[k] = f"{type(ex_).__name__}: {ex_}"
    return novas, feitos, tempos, falhas


def amostra_ids(nome, mapas):
    if nome == "todos":
        return sorted(mapas, key=lambda k: mapas[k]["quadro"])
    return json.load(open(os.path.join(AQUI, "amostras.json")))[nome]["ids"]


def rodar(ids, forcar=False, nproc=8, lote=6, mostrar=True, variante=None):
    """Roda as sub-etapas para os ids (com cache) e atualiza os manifestos. Devolve o resumo da rodada."""
    t_ini = time.time()
    mans = {s_: cache.manifesto(f"e4/{s_}") for s_ in "abd"}
    mans["e"] = {}
    et = cache.Etapa("e4e")
    if variante is None:
        variante = cache.exp_atual() or et.m["aprovada"]
    et.garantir(variante, {"versao": VERSAO["e"], **params("e")})
    lotes = [ids[i:i + lote] for i in range(0, len(ids), lote)]
    feitos = {s_: 0 for s_ in "abde"}
    tempos, falhas = {}, {}
    from concurrent.futures import as_completed
    with ProcessPoolExecutor(nproc) as ex:
        futs = [ex.submit(processar, (l, mans, forcar, variante, et.m)) for l in lotes]
        n = 0
        for f in as_completed(futs):
            novas, fe, te, fa = f.result()
            for s_ in "abd":
                mans[s_].update(novas[s_])
                if novas[s_]:
                    cache.gravar_manifesto(f"e4/{s_}", mans[s_])
            for s_ in "abde":
                feitos[s_] += fe[s_]
            if novas["e"]:
                et.m["variantes"][variante]["itens"].update(novas["e"])
                et.gravar()
            tempos.update(te)
            falhas.update(fa)
            n += 1
            if mostrar and (n % 20 == 0 or n == len(lotes)):
                dec = time.time() - t_ini
                eta = dec / n * (len(lotes) - n)
                print(f"lotes {n}/{len(lotes)}  recalculados a={feitos['a']} b={feitos['b']} d={feitos['d']} "
                      f"e={feitos['e']}  {dec:.0f} s, faltam ~{eta:.0f} s", flush=True)
    trocados = et.aprovar(variante) if variante == et.m["aprovada"] else 0
    soma = {s_: round(sum(t.get(s_, 0) for t in tempos.values()), 1) for s_ in "abde"}
    resumo = {"variante": variante, "apontadores_trocados": trocados,
              "mapas": len(ids), "recalculados": feitos, "segundos_total": round(time.time() - t_ini, 1),
              "segundos_por_subetapa_somados": soma, "falhas": falhas}
    return resumo


def main():
    mapas = json.load(open(os.path.join(V2, "mapas.json")))
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    amostra = "todos"
    for i, a in enumerate(sys.argv):
        if a in ("--amostra", "--variante"):
            args = [x for x in args if x != sys.argv[i + 1]]
            if a == "--amostra":
                amostra = sys.argv[i + 1]
    ids = args or amostra_ids(amostra, mapas)
    if "--so-chaves" in sys.argv:
        # o que seria recalculado na E4a (as seguintes dependem do conteúdo das anteriores: "depois")
        mans = cache.manifesto("e4/a")
        n = sum(1 for k in ids if cache.precisa(mans, k, chave_sub("a",
            cache.hash_arquivo(os.path.join(V2, "mapas", f"{k}.png"))), arquivos(k)["a"]))
        print(f"E4a recalcularia {n} de {len(ids)}; E4b/E4d/E4e dependem do conteúdo das anteriores")
        return
    variante = sys.argv[sys.argv.index("--variante") + 1] if "--variante" in sys.argv else None
    resumo = rodar(ids, forcar="e" if "--forcar-e" in sys.argv else ("--forcar" in sys.argv), variante=variante)
    json.dump(resumo, open(os.path.join(V2, "rotulos-tempo.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in resumo.items() if k != "falhas"}, ensure_ascii=False))
    if resumo["falhas"]:
        print("FALHAS:", json.dumps(resumo["falhas"], ensure_ascii=False)[:2000])


if __name__ == "__main__":
    main()
