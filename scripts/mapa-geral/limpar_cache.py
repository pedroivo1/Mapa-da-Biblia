#!/usr/bin/env python3
# Arrumação do cache do mapa geral v2 (docs/mapa-geral-incremental.md).
# Uso: PYTHONPATH=~/.cache/mapa-biblia-lib/lib python3 scripts/mapa-geral/limpar_cache.py [--apagar]
#        [--variante <etapa> <nome>]
# Sem argumentos: lista, por etapa da loja (E3, E4e, E5, E6, E7), cada variante com o espaço que ocupa só ela, e o lixo:
#   objetos da loja que nenhuma variante registra, sobras .tmp, artefatos das sub-etapas E4a/E4b/E4d fora do
#   manifesto e pastas obsoletas. --apagar apaga só o lixo.
# --variante <etapa> <nome> --apagar: apaga uma variante (os objetos que só ela usa). Nunca apaga a aprovada nem a
#   anterior a ela; mostra antes o espaço liberado.
import json, os, shutil, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import cache

V2 = cache.V2
OBSOLETAS = ["rotulos-pre", "antes-miolo", "referencia-e4"]


def tamanho(c):
    if os.path.isdir(c):
        return sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(c) for f in fs)
    return os.path.getsize(c) if os.path.exists(c) else 0


def objetos(et, chs):
    return [et.obj(ch, x) for ch in chs for x in et.exts()]


apagar = "--apagar" in sys.argv
if "--variante" in sys.argv:
    i = sys.argv.index("--variante")
    et = cache.Etapa(sys.argv[i + 1])
    nome = sys.argv[i + 2]
    if nome in (et.m["aprovada"], et.m["anterior"]):
        raise SystemExit(f"{et.nome}: '{nome}' é a aprovada ou a anterior; não pode ser apagada")
    if nome not in et.m["variantes"]:
        raise SystemExit(f"{et.nome}: variante '{nome}' não existe")
    outras = {e["chave"] for n, v in et.m["variantes"].items() if n != nome for e in v["itens"].values()}
    so_dela = {e["chave"] for e in et.m["variantes"][nome]["itens"].values()} - outras
    arqs = objetos(et, so_dela)
    print(f"{et.nome}/{nome}: {len(so_dela)} objetos só dela, {sum(map(tamanho, arqs)) / 1e6:.0f} MB")
    if apagar:
        for a in arqs:
            if os.path.exists(a):
                os.remove(a)
        del et.m["variantes"][nome]
        et.gravar()
        print("apagada")
    else:
        print("(nada apagado; use --apagar)")
    sys.exit(0)

lixo = []
for nome in cache.ETAPAS_LOJA:
    if not os.path.isdir(os.path.join(cache.OBJ, nome)):
        continue
    et = cache.Etapa(nome)
    usadas, n_itens = {}, {}
    for n, v in et.m["variantes"].items():
        usadas[n] = {e["chave"] for e in v["itens"].values()}
        n_itens[n] = len(v["itens"])
    todas = set().union(*usadas.values()) if usadas else set()
    for n, chs in usadas.items():
        outras = set().union(*[c for m, c in usadas.items() if m != n]) if len(usadas) > 1 else set()
        marca = " (aprovada)" if n == et.m["aprovada"] else (" (anterior)" if n == et.m["anterior"] else "")
        print(f"{nome}/{n}{marca}: {n_itens[n]} itens ({len(chs)} objetos distintos: mapas idênticos dividem objeto), {sum(map(tamanho, objetos(et, chs))) / 1e6:.0f} MB "
              f"({sum(map(tamanho, objetos(et, chs - outras))) / 1e6:.0f} MB só dela)")
    for f in os.listdir(os.path.join(cache.OBJ, nome)):
        if ".tmp" in f or f.split(".")[0] not in todas:
            lixo.append(os.path.join(cache.OBJ, nome, f))
for etapa in ("e4/a", "e4/b", "e4/d"):
    pasta = os.path.join(V2, etapa)
    if not os.path.isdir(pasta):
        continue
    man_arq = os.path.join(pasta, "manifesto.json")
    ids = set(json.load(open(man_arq))) if os.path.exists(man_arq) else set()
    for f in os.listdir(pasta):
        if f != "manifesto.json" and (".tmp" in f or f.split(".")[0] not in ids):
            lixo.append(os.path.join(pasta, f))
for o in OBSOLETAS:
    c = os.path.join(V2, o)
    if os.path.exists(c):
        lixo.append(c)
total = sum(tamanho(c) for c in lixo)
for c in lixo[:20]:
    print("   lixo:", os.path.relpath(c, V2), f"{tamanho(c) / 1e6:.1f} MB")
if len(lixo) > 20:
    print(f"   ... e mais {len(lixo) - 20}")
print(f"lixo: {len(lixo)} itens, {total / 1e6:.0f} MB")
if apagar:
    for c in lixo:
        shutil.rmtree(c) if os.path.isdir(c) else os.remove(c)
    print("lixo apagado")
else:
    print("(nada apagado; use --apagar)")
