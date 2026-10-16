#!/usr/bin/env python3
# Migração única (2026-10-15) para a loja por chave (cache.py, formato 2): os rótulos (E4e) e os vetores (E5)
# atuais, calculados com a lógica aprovada, vão para .cache/v2/obj/<etapa>/<chave>.* e rotulos/ e vetores/ viram
# apontadores. A variante aprovada se chama "base". A E6 é refeita depois com rastrear.py (já grava na loja).
# Uso: PYTHONPATH=~/.cache/mapa-biblia-lib/lib python3 scripts/mapa-geral/migrar_loja.py
import json, os, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/.cache/mapa-biblia-lib/lib"))
sys.path.insert(0, AQUI)
import cache
import rotular as rt
import vetorizar as vz

V2 = cache.V2

# E4e: o manifesto antigo ({id: entrada}) tem a chave de cada rótulo atual
arq_e = os.path.join(V2, "e4", "e", "manifesto.json")
antigo = json.load(open(arq_e))
if antigo.get("formato") != 2:
    et = cache.adotar_publicos("e4e", "base", {"versao": rt.VERSAO["e"], **rt.params("e")}, antigo)
    print("e4e: adotados", len(et.itens("base")))
else:
    print("e4e: já migrada")

# E5: chave nova (VERSAO 4 + params com SIMPLIFICACAO; a lógica dos vetores atuais é a 4)
et5 = cache.Etapa("e5")
if not et5.m["variantes"]:
    cal = json.load(open(os.path.join(V2, "calibracao.json")))["por_mapa"]
    mundo_h = cache.hash_arquivo(vz.MUNDO)
    mapas = json.load(open(os.path.join(V2, "mapas.json")))
    entradas = {}
    for k in mapas:
        arq = os.path.join(V2, "vetores", f"{k}.json")
        entradas[k] = {"chave": vz.chave_mapa(k, cal[k], mundo_h), "hash_saida": cache.hash_arquivo(arq), "segundos": None}
    et5 = cache.adotar_publicos("e5", "base", vz.params(), entradas)
    print("e5: adotados", len(et5.itens("base")))
else:
    print("e5: já migrada")
