#!/usr/bin/env python3
# Arrumação do cache do mapa geral v2 (docs/mapa-geral-incremental.md): lista os artefatos das etapas com manifesto
# (.cache/v2/e4/<sub>/, .cache/v2/e5/) que não estão em nenhum manifesto (versões antigas, sobras .tmp) e as pastas
# de cache obsoletas da própria v2 (rotulos-pre/: cache da fase 1 antes da divisão em E4a–E4e; antes-miolo/: cópia
# dos rótulos antes da regra dos miolos de letra, referência do T4.9 já aprovado), com o espaço que
# liberam. Só apaga com --apagar. O cache da v1 (.cache/quadros, .cache/estados...) não é tocado aqui.
# Uso: PYTHONPATH=~/.cache/mapa-biblia-lib/lib python3 scripts/mapa-geral/limpar_cache.py [--apagar]
import json, os, shutil, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.join(os.environ.get("MAPA_GERAL_CACHE") or os.path.join(AQUI, ".cache"), "v2")
OBSOLETAS = ["rotulos-pre", "antes-miolo", "referencia-e4"]


def tamanho(c):
    if os.path.isdir(c):
        return sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(c) for f in fs)
    return os.path.getsize(c)


lixo = []
for etapa in ("e4/a", "e4/b", "e4/d", "e5"):
    pasta = os.path.join(V2, etapa)
    if not os.path.isdir(pasta):
        continue
    man_arq = os.path.join(pasta, "manifesto.json")
    ids = set(json.load(open(man_arq))) if os.path.exists(man_arq) else set()
    for f in os.listdir(pasta):
        if f == "manifesto.json":
            continue
        ident = f.split(".")[0]
        if ".tmp" in f or ident not in ids:
            lixo.append(os.path.join(pasta, f))
for o in OBSOLETAS:
    c = os.path.join(V2, o)
    if os.path.exists(c):
        lixo.append(c)
total = sum(tamanho(c) for c in lixo)
for c in lixo[:20]:
    print("  ", os.path.relpath(c, V2), f"{tamanho(c) / 1e6:.1f} MB")
if len(lixo) > 20:
    print(f"   ... e mais {len(lixo) - 20}")
print(f"{len(lixo)} itens, {total / 1e6:.0f} MB")
if "--apagar" in sys.argv:
    for c in lixo:
        shutil.rmtree(c) if os.path.isdir(c) else os.remove(c)
    print("apagados")
else:
    print("(nada apagado; use --apagar)")
