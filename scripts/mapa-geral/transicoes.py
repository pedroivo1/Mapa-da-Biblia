#!/usr/bin/env python3
# E2/E3 (correção): anos cujo mapa é um quadro de transição de zoom (fade entre dois enquadramentos).
# Um mapa é suspeito quando a escala dele (calibracao.json) não bate com nenhum trecho longo (diferença > 0,2 %): a
# calibração de um quadro de transição cai num mínimo falso. Para cada ano com mapa suspeito, os quadros do próprio ano
# são decodificados e comparados (discordância de terra) com a calibração do trecho do ano anterior e do seguinte; o
# último quadro que se encaixa num trecho (discordância <= 1,5 × a do mapa vizinho no mesmo trecho, mín. 0,04) vira o
# mapa do ano: os PNGs do mapa (1920, 4K e 8K; quadros_medios.py) são regravados e a calibração do mapa vira a do
# trecho, refinada (ajustar). Sem
# quadro bom, o ano passa a usar o mapa do ano anterior (no tempo do vídeo). A calibração corrigida vai para a loja da
# E3 (cache.py) como variante "<aprovada>-transicoes", que passa a ser a aprovada; a anterior continua na loja.
# Uso: PYTHONPATH=~/.cache/mapa-biblia-lib/lib python3 scripts/mapa-geral/transicoes.py [--so-listar]
# Grava .cache/v2/transicoes.json com o que foi feito; anos.json ganha "transicao": {...} nos anos corrigidos.
import glob, json, os, subprocess, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/.cache/mapa-biblia-lib/lib"))
sys.path.insert(0, AQUI)
import numpy as np
import cv2
import calibrar as c
import escala

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
    """Gera os quadros i0..i1 do ano no quadro da geometria (escala.W × escala.H), um por vez (um ano pode ter
    centenas de quadros; em 4K cada um tem 22 MB)."""
    import quadros as q
    return q.decodificar(i0, i1 - i0 + 1, escala.W, escala.H, threads=8)


def falha(im, terra, lagos, p):
    tv, val = c.mascara_terra(im)
    return c.custo(tv, val, terra, lagos, (p["S"], p["X0"], p["Y0"])) / float((val > 0).sum())


def main():
    import cache
    et3 = cache.Etapa("e3")
    cal = json.load(open(cache.calibracao()))
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
            # o ÚLTIMO quadro do ano que se encaixa num trecho vizinho (varre em fluxo, guardando só o melhor até aqui)
            escolhido = None
            for jj, f in enumerate(quadros(i0, i1)):
                for kv, pv in vizinhos:
                    ref = max(0.04, 1.5 * pv["falha"])
                    fa = falha(f, terra, lagos, pv)
                    if fa <= ref:
                        escolhido = (i0 + jj, kv, pv, fa)
                        break
            if escolhido:
                q, kv, pv, fa = escolhido
                # as três cópias do mapa passam a ser a mediana dos quadros estáveis do ano até q (quadros_medios.py)
                import quadros_medios
                corr = quadros_medios.corridas()
                ini_c, fim_c = corr.get(int(k), (q, q))
                mapas[k]["mediana"] = quadros_medios.gravar_de_corrida(k, max(ini_c, i0), fim_c, cap=q)
                fq = cv2.imread(os.path.join(V2, escala.pasta_mapas(), f"{k}.png"))
                p_ref, cu = c.ajustar(*c.mascara_terra(fq), terra, lagos, (pv["S"], pv["X0"], pv["Y0"]), dX0=escala.px(1.0))
                tv, val = c.mascara_terra(fq)
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
    # E3 na loja: a calibração corrigida é um objeto novo, numa variante "<aprovada>-transicoes" (aprovada em seguida)
    base = et3.m["aprovada"] or "base"
    var_t = base if base.endswith("-transicoes") else base + "-transicoes"
    p_base = dict(et3.m["variantes"][base]["params"]) if base in et3.m["variantes"] else {}
    et3.garantir(var_t, dict(p_base, transicoes=True))
    ch_base = (et3.itens(base).get("calibracao") or {}).get("chave")
    ch = cache.chave(1, {"transicoes": True}, [ch_base, cache.hash_obj(relatorio)])
    arq = et3.obj(ch, ".json")
    json.dump(cal, open(arq + ".tmp", "w"))
    os.replace(arq + ".tmp", arq)
    et3.m["variantes"][var_t]["itens"]["calibracao"] = {"chave": ch, "hash_saida": cache.hash_arquivo(arq), "segundos": None}
    et3.gravar()
    et3.aprovar(var_t)
    json.dump(mapas, open(os.path.join(V2, "mapas.json"), "w"))
    json.dump(anos, open(os.path.join(V2, "anos.json"), "w"), indent=0)
    json.dump(relatorio, open(os.path.join(V2, "transicoes.json"), "w"), indent=1)
    for r in relatorio:
        print(r)


if __name__ == "__main__":
    main()
