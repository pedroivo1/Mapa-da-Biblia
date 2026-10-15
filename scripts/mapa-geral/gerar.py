#!/usr/bin/env python3
# Etapa 3 do mapa geral: para cada quadro-chave, calibra, separa os estados por cor e lê os nomes (OCR).
# Entrada: .cache/quadros-chave.json (indexar.py), .cache/calibracao.json (calibrar.py todos 20)
# Saída:   .cache/estados/<ano>.json  -> {"ano", "segundo", "cal", "estados": [{cor, area_px, bbox, anel, nome_en}]}
# Uso:     python3 scripts/mapa-geral/gerar.py [ano ...]     (sem argumentos: todos os quadros-chave)
import json, os, sys
from concurrent.futures import ProcessPoolExecutor

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import cv2
import calibrar, segmentar, nomear

CACHE = os.path.join(AQUI, ".cache")
SAIDA = os.path.join(CACHE, "estados")


def calibracao_vizinha(seg, tabela):
    """Calibração grossa mais próxima no tempo (chaves = segundos como texto)."""
    if not tabela: return None
    k = min(tabela, key=lambda s: abs(int(s) - seg))
    return tabela[k]


def calibrar_quadro(seg, tabela, aneis):
    """Refina a calibração vizinha (enquadramento é constante por trechos). Se o quadro for de transição
    (fade/zoom) o escore cai: tenta segundos vizinhos; só em último caso faz a busca completa."""
    viz = calibracao_vizinha(seg, tabela)
    for delta in (0, 1, -1, 2, -2, 3, -3, 4, -4, 6, -6):
        s2 = seg + delta
        caminho = os.path.join(CACHE, "quadros", "%04d.jpg" % s2)
        if not os.path.exists(caminho): continue
        for v in ([viz] if viz else []):
            cal = calibrar.refinar(caminho, aneis, v["proj"], v["S"] / 4, (v["X0"] / 4, v["Y0"] / 4))
            if cal and cal["escore"] >= 0.65:
                return s2, cal
    caminho = os.path.join(CACHE, "quadros", "%04d.jpg" % seg)
    m = calibrar.mascara_quadro(caminho)
    r = calibrar.ajustar_varios({seg: m}, aneis)[seg][0]
    return seg, calibrar.refinar(caminho, aneis, r[1], r[2], r[3])


def processar(item):
    ano, seg0 = item["ano"], item["segundo"]
    tabela = json.load(open(os.path.join(CACHE, "calibracao.json")))
    aneis = calibrar.terra_aneis()
    seg, cal = calibrar_quadro(seg0, tabela, aneis)       # pode trocar para um segundo vizinho
    caminho = os.path.join(CACHE, "quadros", "%04d.jpg" % seg)
    est = segmentar.segmentar_quadro(caminho, cal)
    img = cv2.imread(caminho)
    nomear.nomear(img, est)
    os.makedirs(SAIDA, exist_ok=True)
    nome = ("a%d" % ano) if ano >= 0 else ("d%d" % -ano)
    json.dump({"ano": ano, "segundo": seg, "cal": cal, "estados": est},
              open(os.path.join(SAIDA, nome + ".json"), "w"))
    return ano, seg, cal["escore"], len(est)


def main():
    chave = json.load(open(os.path.join(CACHE, "quadros-chave.json")))
    if sys.argv[1:]:
        pedidos = {int(a) for a in sys.argv[1:]}
        chave = [c for c in chave if c["ano"] in pedidos]
    with ProcessPoolExecutor(max_workers=10) as ex:
        for ano, seg, esc, n in ex.map(processar, chave):
            print("ano %6d  s=%4d  escore=%.3f  estados=%d" % (ano, seg, esc, n), flush=True)


if __name__ == "__main__":
    main()
