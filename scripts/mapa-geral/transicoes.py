#!/usr/bin/env python3
# E2/E3 (correção): anos cujo mapa é um quadro de transição de zoom (fade entre dois enquadramentos).
# Um mapa é suspeito quando a escala dele (calibracao.json) não bate com nenhum trecho longo (diferença > 0,2 %): a
# calibração de um quadro de transição cai num mínimo falso. Para cada ano com mapa suspeito, os quadros do próprio ano
# são decodificados e comparados (discordância de terra) com a calibração do trecho do ano anterior e do seguinte; o
# último quadro que se encaixa num trecho (discordância <= 1,5 × a do mapa vizinho no mesmo trecho, mín. 0,04) vira o
# mapa do ano: o PNG em mapas/<id>.png é regravado e a calibração do mapa vira a do trecho, refinada (ajustar). Sem
# quadro bom, o ano passa a usar o mapa do ano anterior (no tempo do vídeo).
# Uso: PYTHONPATH=~/.cache/mapa-biblia-lib/lib python3 scripts/mapa-geral/transicoes.py [--so-listar]
# Grava .cache/v2/transicoes.json com o que foi feito; anos.json ganha "transicao": {...} nos anos corrigidos.
import glob, json, os, subprocess, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/.cache/mapa-biblia-lib/lib"))
sys.path.insert(0, AQUI)
import numpy as np
import cv2
import calibrar as c

V2 = c.V2
FPS = 30000 / 1001


def trechos_longos(cal):
    return [t for t in cal["trechos"] if t["n"] >= 20]


def suspeitos(cal, mapas):
    longos = trechos_longos(cal)
    out = []
    for k, p in cal["por_mapa"].items():
        if not any(abs(p["S"] / t["S"] - 1) <= 0.002 for t in longos):
            out.append(k)
    return sorted(out, key=lambda k: mapas[k]["quadro"])


def quadros(i0, i1):
    video = glob.glob(os.path.join(AQUI, "..", "..", "vídeos", "*hzWwp9JM7Hw*.webm"))[0]
    b = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{(i0 - 0.5) / FPS:.4f}", "-i", video, "-frames:v",
                        str(i1 - i0 + 1), "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    n = len(b) // (960 * 1920 * 3)
    return [np.frombuffer(b[j * 960 * 1920 * 3:(j + 1) * 960 * 1920 * 3], np.uint8).reshape(960, 1920, 3) for j in range(n)]


def falha(im, terra, lagos, p):
    tv, val = c.mascara_terra(im)
    return c.custo(tv, val, terra, lagos, (p["S"], p["X0"], p["Y0"])) / float((val > 0).sum())


def main():
    cal = json.load(open(os.path.join(V2, "calibracao.json")))
    mapas = json.load(open(os.path.join(V2, "mapas.json")))
    anos = json.load(open(os.path.join(V2, "anos.json")))
    terra, lagos = c.carregar_mundo()
    sus = suspeitos(cal, mapas)
    print("mapas com escala fora dos trechos:", [(k, cal["por_mapa"][k]["S"], mapas[k]["anos"]) for k in sus])
    if "--so-listar" in sys.argv:
        return
    ordem_anos = list(anos)              # já na ordem do tempo (2500 a.C. -> 2025 d.C.)
    relatorio = []
    for k in sus:
        for ano in mapas[k]["anos"]:
            pos = ordem_anos.index(str(ano))
            vizinhos = []
            for d in (-1, 1):
                j = pos + d
                while 0 <= j < len(ordem_anos) and str(anos[ordem_anos[j]]["mapa"]) in sus:
                    j += d
                if 0 <= j < len(ordem_anos):
                    kv = str(anos[ordem_anos[j]]["mapa"])
                    vizinhos.append((kv, cal["por_mapa"][kv]))
            i0, i1 = anos[str(ano)]["quadros"]
            fs = quadros(i0, i1)
            escolhido = None
            for jj in range(len(fs) - 1, -1, -1):
                for kv, pv in vizinhos:
                    ref = max(0.04, 1.5 * pv["falha"])
                    fa = falha(fs[jj], terra, lagos, pv)
                    if fa <= ref:
                        escolhido = (i0 + jj, kv, pv, fa)
                        break
                if escolhido:
                    break
            if escolhido:
                q, kv, pv, fa = escolhido
                p_ref, cu = c.ajustar(*c.mascara_terra(fs[q - i0]), terra, lagos, (pv["S"], pv["X0"], pv["Y0"]), dX0=1.0)
                cv2.imwrite(os.path.join(V2, "mapas", f"{k}.png"), fs[q - i0], [cv2.IMWRITE_PNG_COMPRESSION, 1])
                tv, val = c.mascara_terra(fs[q - i0])
                r = c.renderizar(terra, lagos, *p_ref)
                med, p90, n, fora = c.residuo_costa(tv, val, r, p_ref)
                cal["por_mapa"][k] = {"S": round(p_ref[0], 4), "X0": round(p_ref[1], 2), "Y0": round(float(p_ref[2]), 2),
                                      "falha": round(cu / float((val > 0).sum()), 5), "mediana_px": med, "p90_px": p90,
                                      "n_costa": n, "fora": round(fora, 4), "corrigido_de_transicao": True}
                mapas[k]["quadro"] = q
                anos[str(ano)]["quadro_mapa"] = q
                anos[str(ano)]["transicao"] = {"acao": "outro quadro do ano", "quadro": q, "trecho_de": kv,
                                               "discordancia": round(fa, 4)}
                relatorio.append({"ano": ano, "mapa": k, "acao": "outro quadro do ano", "quadro": q,
                                  "S": cal["por_mapa"][k]["S"], "discordancia": round(fa, 4)})
            else:
                ant = ordem_anos[pos - 1]
                ka = anos[ant]["mapa"]
                anos[str(ano)]["mapa"] = ka
                anos[str(ano)]["transicao"] = {"acao": "mapa do ano anterior", "ano_anterior": int(ant)}
                mapas[str(ka)]["anos"].append(ano)
                relatorio.append({"ano": ano, "mapa": k, "acao": "mapa do ano anterior", "usa": ka})
    ids = sorted(cal["por_mapa"], key=lambda k: mapas[k]["quadro"])
    cal["trechos"] = c.montar_trechos(ids, cal["por_mapa"])
    json.dump(cal, open(os.path.join(V2, "calibracao.json"), "w"))
    json.dump(mapas, open(os.path.join(V2, "mapas.json"), "w"))
    json.dump(anos, open(os.path.join(V2, "anos.json"), "w"), indent=0)
    json.dump(relatorio, open(os.path.join(V2, "transicoes.json"), "w"), indent=1)
    for r in relatorio:
        print(r)


if __name__ == "__main__":
    main()
