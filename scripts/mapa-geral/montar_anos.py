# E2 (parte 3) do mapa geral v2: monta a sequência de anos a partir da varredura e do OCR das caixas.
# Chamado por quadros.py (passo "montar"). Lê .cache/v2/varredura.npz e anos-lidos.json; grava
#   anos.json         {"<ano>": {"quadros": [i0, i1], "quadros_mapa": [i0, q], "quadro_mapa": q, "mapa": id, "zoom": bool,
#                      "meio": n, "inferido": bool, "corrigido": bool, "sem_quadro"?: true}}
#   mapas.json        {"<id>": {"quadro": q, "anos": [todos os anos do mapa], "mediana": {...}}}  (PNGs por quadros_medios.py)
#   montagem.json     resumo (contagens, anos inferidos, anos com mapa que muda no meio)
# Posição na sequência: 0 = 2500 a.C. ... 2499 = 1 a.C., 2500 = 1 d.C. ... 4524 = 2025 d.C. (não existe ano 0).
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.expanduser("~/.cache/mapa-biblia-lib/lib"))
import numpy as np
import cv2

AQUI = os.path.dirname(os.path.abspath(__file__))
CACHE = os.environ.get("MAPA_GERAL_CACHE") or os.path.join(AQUI, ".cache")
V2 = os.path.join(CACHE, "v2")
N_ANOS = 4525
MIN_PIXELS_MUDANCA = 10


def pos_de_ano(ano):
    """ano (a.C. positivo, d.C. negativo) -> posição 0..4524."""
    return 2500 - ano if ano > 0 else 2499 + (-ano)


def ano_de_pos(p):
    return 2500 - p if p < 2500 else -(p - 2499)


def rotulo(ano):
    return f"{ano} a.C." if ano > 0 else f"{-ano} d.C."


def interpretar(txt):
    """Texto do OCR -> posição ou None. Aceita '326', '584 BC', '584BC', '5 84 BC'."""
    t = txt.upper().replace(" ", "")
    m = re.fullmatch(r"(\d{1,4})(BC|B|C)?", t)
    if not m:
        return None
    n = int(m.group(1))
    if n < 1:
        return None
    if m.group(2):
        if n > 2500:
            return None
        return 2500 - n
    if n > 2025:
        return None
    return 2499 + n


def montar():
    z = np.load(os.path.join(V2, "varredura.npz"))
    hcx, mud, esq = z["hcx"], z["mud"], z["esq"]
    lidos = json.load(open(os.path.join(V2, "anos-lidos.json")))
    n = len(hcx)
    # 1. corridas de quadros com a mesma caixa
    corridas = []
    i = 0
    while i < n:
        j = i
        while j + 1 < n and hcx[j + 1] == hcx[i]:
            j += 1
        h = hcx[i].decode() if esq[i] >= 0 else None
        corridas.append([i, j, h])
        i = j + 1
    for c in corridas:
        c.append(interpretar(lidos.get(c[2], "")) if c[2] else None)  # posição lida
    # 2. une corridas vizinhas com a mesma posição lida (ruído parte a mesma caixa em duas)
    uni = []
    for c in corridas:
        if uni and c[3] is not None and uni[-1][3] == c[3] and c[0] == uni[-1][1] + 1:
            uni[-1][1] = c[1]
        else:
            uni.append(c[:])
    # 3. a sequência é +1 a cada corrida válida. Caminho mais longo e consistente (posição - índice constante).
    validas = [(k, c[3]) for k, c in enumerate(uni) if c[3] is not None]
    # maior subsequência com posição estritamente crescente (o vídeo pode pular anos; leituras fora de ordem = OCR errado)
    # programação dinâmica simples O(m^2) sobre as corridas válidas
    m = len(validas)
    melhor = [1] * m
    ant = [-1] * m
    for b in range(m):
        kb, pb = validas[b]
        for a in range(b):
            ka, pa = validas[a]
            dp, dk = pb - pa, kb - ka
            if dp > 0 and melhor[a] + 1 > melhor[b]:
                melhor[b] = melhor[a] + 1
                ant[b] = a
    fim = max(range(m), key=lambda x: melhor[x])
    cadeia = []
    while fim != -1:
        cadeia.append(validas[fim]); fim = ant[fim]
    cadeia.reverse()
    # 4. atribui posição a toda corrida entre a primeira e a última da cadeia por interpolação (inferidas)
    pos = [None] * len(uni)
    inferido = [False] * len(uni)
    for k, p in cadeia:
        pos[k] = p
    for (ka, pa), (kb, pb) in zip(cadeia, cadeia[1:]):
        meio = list(range(ka + 1, kb))
        if pb - pa - 1 == len(meio):
            for t, k in enumerate(meio):
                pos[k] = pa + 1 + t; inferido[k] = True
    # 4b. corridas ainda sem posição: o OCR às vezes insere um caractere ("555" lido "5585"). Tenta apagar um
    # caractere; vale a leitura que cai entre as posições dos vizinhos já atribuídos (pode igualar um vizinho).
    corrigido = [False] * len(uni)
    for k, c in enumerate(uni):
        if pos[k] is not None or not c[2]:
            continue
        t = lidos.get(c[2], "").replace(" ", "")
        anteriores = [pos[j] for j in range(k - 1, -1, -1) if pos[j] is not None][:1]
        seguintes = [pos[j] for j in range(k + 1, len(uni)) if pos[j] is not None][:1]
        if not anteriores or not seguintes:
            continue
        cand = {interpretar(t[:x] + t[x + 1:]) for x in range(len(t))} - {None}
        cand = [p for p in cand if anteriores[0] <= p <= seguintes[0]]
        if len(cand) == 1:
            pos[k] = cand[0]; corrigido[k] = True
    descartadas = [k for k, p in enumerate(pos) if p is None]
    # 5. quadros de cada ano
    anos = {}
    for k, c in enumerate(uni):
        if pos[k] is None:
            continue
        p = pos[k]
        a = ano_de_pos(p)
        anos.setdefault(a, {"quadros": [c[0], c[1]], "inferido": inferido[k], "corrigido": corrigido[k]})
        anos[a]["quadros"][0] = min(anos[a]["quadros"][0], c[0])
        anos[a]["quadros"][1] = max(anos[a]["quadros"][1], c[1])
        anos[a]["inferido"] = anos[a]["inferido"] and inferido[k]
        anos[a]["corrigido"] = anos[a]["corrigido"] and corrigido[k]
    # 5b. anos que o vídeo não mostra (a taxa de quadros pula o ano): herdam o último quadro do ano anterior no
    # tempo do vídeo, marcados com "sem_quadro"
    for p in range(N_ANOS):
        a = ano_de_pos(p)
        if a in anos:
            continue
        ant = ano_de_pos(p - 1) if p > 0 else None
        if ant is not None and ant in anos:
            q = anos[ant]["quadros"][1]
            anos[a] = {"quadros": [q, q], "inferido": False, "corrigido": False, "sem_quadro": True}
    # 6. mapas distintos: corridas de mapa = quadros cuja mudança em relação ao anterior é < limiar
    muda = (mud >= MIN_PIXELS_MUDANCA) | (mud < 0)
    id_mapa = np.cumsum(muda)             # id do mapa de cada quadro (muda no quadro em que a mudança aparece)
    # animação de zoom/fade: muitas mudanças seguidas
    seguidas = np.convolve(muda.astype(int), np.ones(5, int), mode="same")
    mapas = {}
    for a, d in anos.items():
        i0, i1 = d["quadros"]
        # fade final / animação de zoom no fim do ano: volta até o último quadro estável (não em mudança contínua)
        q = i1
        while q > i0 and muda[q] and muda[q - 1]:
            q -= 1
        if a == -2025:
            q = ultimo_quadro_sem_fade(i0, i1)
        d["quadros_mapa"] = [i0, q]
        ultimo = int(id_mapa[q])
        d["mapa"] = ultimo
        d["meio"] = int(len(set(id_mapa[i0:q + 1].tolist())) - 1)
        d["zoom"] = bool(seguidas[i0:i1 + 1].max() >= 4)
        d["quadro_mapa"] = int(q)
        mapas.setdefault(ultimo, {"quadro": int(q), "anos": []})["anos"].append(a)
    resumo = {
        "anos": len(anos), "esperados": N_ANOS,
        "faltando": [ano_de_pos(p) for p in range(N_ANOS) if ano_de_pos(p) not in anos],
        "sem_quadro": sorted(a for a, d in anos.items() if d.get("sem_quadro")),
        "corrigidos": sorted(a for a, d in anos.items() if d.get("corrigido")),
        "inferidos": sorted(a for a, d in anos.items() if d["inferido"] and not d.get("sem_quadro")),
        "corridas_descartadas": [uni[k][:3] + [lidos.get(uni[k][2], "") if uni[k][2] else ""] for k in descartadas][:200],
        "n_descartadas": len(descartadas),
        "mapas_distintos": len(mapas),
        "anos_meio": sorted(a for a, d in anos.items() if d["meio"] > 0),
        "anos_zoom": sorted(a for a, d in anos.items() if d["zoom"]),
    }
    json.dump({str(a): anos[a] for a in sorted(anos, key=pos_de_ano)}, open(os.path.join(V2, "anos.json"), "w"), indent=0)
    json.dump({str(k): v for k, v in mapas.items()}, open(os.path.join(V2, "mapas.json"), "w"))
    json.dump(resumo, open(os.path.join(V2, "montagem.json"), "w"), indent=1, ensure_ascii=False)
    print({k: (v if not isinstance(v, list) else len(v)) for k, v in resumo.items()})
    # 7. PNG de cada mapa distinto (1920, 4K e 8K; mediana dos quadros da corrida): quadros_medios.py (E2.4)
    import quadros_medios
    quadros_medios.gerar()


def ultimo_quadro_sem_fade(i0, i1):
    """O vídeo termina com um fade para o escuro dentro do último ano: último quadro com brilho ≥ 99,5 % do normal."""
    import quadros
    br = np.array([f.mean() for f in quadros.decodificar(i0, i1 - i0 + 1, 240, 120, threads=4, pix="gray")])
    n = len(br)
    ref = np.median(br[:max(5, n // 3)])
    ok = np.where(br >= 0.995 * ref)[0]
    return int(i0 + (ok[ok < n].max() if len(ok) else n - 1))


if __name__ == "__main__":
    montar()
