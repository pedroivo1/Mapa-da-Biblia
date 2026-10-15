#!/usr/bin/env python3
# Etapa 1b do mapa geral: limpa as leituras de ano (OCR) e escolhe os quadros-chave.
# Entrada: .cache/indice-bruto.json (extrair.py). Saída: .cache/indice.json e .cache/quadros-chave.json
# Convenção do projeto: a.C. positivo, d.C. negativo; a cronologia é decrescente (2500, ..., 1, -1, ..., -2025).
import json, os

AQUI = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(AQUI, ".cache")
QUEDA_MAX = 160          # anos que o vídeo pode avançar entre dois quadros (1 s)

# anos dos mapas atuais do site (a.C. positivo, d.C. negativo): ficam sempre entre os quadros-chave
ANOS_DOS_MAPAS = [2100, 2050, 2000, 1950, 1900, 1890, 1500, 1450, 1410, 1400, 1200, 1100, 1010, 970, 900, 860,
                  780, 735, 586, 458, 445, -30, -47, -49, -53, -59]


def limpar(leituras):
    bom = []
    ultimo = None
    for s, a in leituras:
        if a is None:
            bom.append(None); continue
        if ultimo is None or (ultimo - QUEDA_MAX <= a <= ultimo):
            bom.append(a); ultimo = a
        else:
            bom.append(None)
    # interpola os buracos linearmente entre leituras vizinhas
    n = len(bom)
    idx = [i for i, a in enumerate(bom) if a is not None]
    for i0, i1 in zip(idx, idx[1:]):
        for k in range(i0 + 1, i1):
            bom[k] = round(bom[i0] + (bom[i1] - bom[i0]) * (k - i0) / (i1 - i0))
    if idx:
        for k in range(0, idx[0]): bom[k] = bom[idx[0]]
        for k in range(idx[-1] + 1, n): bom[k] = bom[idx[-1]]
    return bom


def alvos():
    t = set(ANOS_DOS_MAPAS)
    t.update(range(2500, 1000, -100))
    t.update(range(1000, 0, -50))
    t.update([-x for x in range(1, 601, 50)])
    t.update([-x for x in range(600, 2001, 100)])
    t.add(-2025)
    return sorted(t, reverse=True)


def main():
    bruto = json.load(open(os.path.join(CACHE, "indice-bruto.json")))["segundos"]
    anos = limpar(bruto)
    indice = [[s, a] for (s, _), a in zip(bruto, anos)]
    json.dump({"segundos": indice}, open(os.path.join(CACHE, "indice.json"), "w"))
    chave = []
    for alvo in alvos():
        melhor = min(indice, key=lambda p: abs(p[1] - alvo))
        if abs(melhor[1] - alvo) <= 30:
            chave.append({"ano": alvo, "segundo": melhor[0], "ano_quadro": melhor[1]})
    # um quadro por segundo no máximo
    vistos, final = set(), []
    for c in chave:
        if c["segundo"] in vistos: continue
        vistos.add(c["segundo"]); final.append(c)
    json.dump(final, open(os.path.join(CACHE, "quadros-chave.json"), "w"), indent=1)
    print(len(indice), "segundos;", len(final), "quadros-chave")
    print("primeiro/último ano:", indice[0][1], indice[-1][1])


if __name__ == "__main__":
    main()
