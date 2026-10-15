#!/usr/bin/env python3
# Etapa 4 do mapa geral: junta os estados dos quadros-chave em ENTIDADES (o mesmo povo ao longo do tempo).
# Critério: mesma cor (distância L1 em RGB pequena) e posição parecida entre quadros consecutivos.
# Entrada: .cache/estados/*.json (gerar.py)   Saída: .cache/entidades.json
# Cada entidade traz os nomes lidos pelo OCR (votação entre os quadros), os anos em que aparece e o centro.
import glob, json, math, os
from collections import Counter

AQUI = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(AQUI, ".cache")


def area_graus(anel):
    a = 0.0
    for i in range(len(anel)):
        x1, y1 = anel[i]; x2, y2 = anel[(i + 1) % len(anel)]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2


def centro(anel):
    xs = [p[0] for p in anel]; ys = [p[1] for p in anel]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def dcor(a, b):
    return sum(abs(x - y) for x, y in zip(a, b))


def carregar():
    quadros = []
    for f in glob.glob(os.path.join(CACHE, "estados", "*.json")):
        d = json.load(open(f))
        quadros.append(d)
    quadros.sort(key=lambda d: -d["ano"])       # cronologia: do mais antigo (a.C. grande) ao mais novo
    return quadros


def main():
    quadros = carregar()
    entidades = []
    for q in quadros:
        ano = q["ano"]
        usados = set()
        for est in sorted(q["estados"], key=lambda e: -e["area_px"]):
            cx, cy = centro(est["anel"])
            area = area_graus(est["anel"])
            melhor, md = None, 1e9
            for i, ent in enumerate(entidades):
                if i in usados: continue
                if dcor(est["cor"], ent["cor"]) > 60: continue
                d = math.hypot(cx - ent["cx"], cy - ent["cy"])
                lim = max(4.0, 1.2 * math.sqrt(max(area, ent["area"])))
                if d < lim and d < md:
                    melhor, md = i, d
            if melhor is None:
                entidades.append({"id": "e%03d" % (len(entidades) + 1), "cor": est["cor"], "cx": cx, "cy": cy,
                                  "area": area, "anos": [], "nomes": Counter()})
                melhor = len(entidades) - 1
            ent = entidades[melhor]
            usados.add(melhor)
            est["entidade"] = ent["id"]
            ent["anos"].append(ano)
            ent["cx"], ent["cy"] = cx, cy
            ent["area"] = max(ent["area"] * 0.5, area)
            if est.get("nome_en"):
                ent["nomes"][est["nome_en"]] += 1
    saida = []
    for e in entidades:
        saida.append({
            "id": e["id"], "cor": e["cor"], "centro": [round(e["cx"], 2), round(e["cy"], 2)],
            "area_max": round(e["area"], 1), "anos": e["anos"],
            "nomes": [n for n, _ in e["nomes"].most_common(4)],
        })
    json.dump(saida, open(os.path.join(CACHE, "entidades.json"), "w"), ensure_ascii=False, indent=1)
    # grava de volta o id da entidade em cada estado dos quadros
    for q in quadros:
        nome = ("a%d" % q["ano"]) if q["ano"] >= 0 else ("d%d" % -q["ano"])
        json.dump(q, open(os.path.join(CACHE, "estados", nome + ".json"), "w"))
    print(len(saida), "entidades")


if __name__ == "__main__":
    main()
