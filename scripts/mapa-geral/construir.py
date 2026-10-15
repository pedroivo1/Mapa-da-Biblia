#!/usr/bin/env python3
# Etapa 5 do mapa geral: transforma os estados segmentados dos quadros-chave nos dados do site.
# Entrada: .cache/estados/*.json (gerar.py), nomes.json (regras de nome) e frontend/mapa/mundo.json (só a costa).
#          Nada dos mapas por história entra aqui: formas e cores vêm só do vídeo.
# Saída:   frontend/mapa-geral/dados/<a|d><ano>.json  {"ano", "estados": [{"id", "area", "aneis"}]}
#          frontend/mapa-geral/dados/indice.json      {"anos", "estados": {id: {nome, cor, desde, ate, nota}}, "fonte"}
# Regras de borda (AGENTS.md): só linhas retas com tremor determinístico (scripts/mapa/tremor.py), quinas em
# mitre, costa exata de mundo.json, sem sobreposição (o menor estado fica com a terra disputada).
# Uso (na raiz do repositório, com shapely no PYTHONPATH):  python3 scripts/mapa-geral/construir.py [ano ...]
import glob, json, math, os, sys
from collections import Counter, defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, os.path.join(AQUI, "..", "mapa"))
from tremor import tremer
import shapely
from shapely.geometry import Polygon
from shapely.ops import unary_union

CACHE = os.path.join(AQUI, ".cache")
MUNDO = os.path.join(RAIZ, "frontend", "mapa", "mundo.json")
SAIDA = os.path.join(RAIZ, "frontend", "mapa-geral", "dados")
FONTE = ("Formas e nomes lidos de vídeos de história mundial ano a ano (\"Every Year\" e similares, de terceiros), "
         "usados só como referência; contornos recalculados sobre a costa do Natural Earth (domínio público).")


def nome_arquivo(ano):
    return ("a%d" % ano) if ano >= 0 else ("d%d" % -ano)


def so_poligonos(g):
    if g.is_empty: return Polygon()
    if g.geom_type in ("Polygon", "MultiPolygon"): return g
    ps = [x for x in getattr(g, "geoms", []) if x.geom_type in ("Polygon", "MultiPolygon")]
    return unary_union(ps) if ps else Polygon()


def carregar_terra():
    w = json.load(open(MUNDO))
    terra = None
    for f in w["fundo"]:
        if f["tipo"] != "terra": continue
        for a in f["aneis"]:
            if len(a) < 3: continue
            p = Polygon(a)
            p = p if p.is_valid else p.buffer(0)
            terra = p if terra is None else terra.symmetric_difference(p)
    lagos = [Polygon(f["pontos"]).buffer(0) for f in w["fundo"] if f["tipo"] == "mar" and len(f["pontos"]) >= 3]
    return terra.difference(unary_union(lagos))


def na_terra(terra, g):
    """g recortado pela terra (costa exata). Só o pedaço da terra sob a caixa de g entra na interseção."""
    x0, y0, x1, y1 = g.bounds
    parte = shapely.clip_by_rect(terra, x0 - 0.01, y0 - 0.01, x1 + 0.01, y1 + 0.01)
    return so_poligonos(g.intersection(parte))


def hexa(c):
    return "#%02x%02x%02x" % tuple(int(v) for v in c)


class Regras:
    def __init__(self, caminho):
        self.lista = json.load(open(caminho))["regras"]

    def casa(self, cor, cx, cy, ano):
        for r in self.lista:
            if not (r["anos"][0] >= ano >= r["anos"][1]): continue
            b = r["caixa"]
            if not (b[0] <= cx <= b[2] and b[1] <= cy <= b[3]): continue
            if min(sum(abs(a - b2) for a, b2 in zip(cor, c)) for c in r["cores"]) <= r.get("tol", 36):
                return r
        return None


def poligono_estado(anel):
    p = Polygon([tuple(q) for q in anel])
    if not p.is_valid: p = p.buffer(0)
    s = p.simplify(0.05)
    if s.is_empty or s.geom_type != "Polygon": s = p
    if s.geom_type != "Polygon": return None
    t = Polygon(tremer(list(s.exterior.coords)[:-1]))
    if not t.is_valid: t = t.buffer(0)
    return t.buffer(0.15, join_style=2, mitre_limit=3)


TOL_SAIDA = 0.03          # graus: simplificação final dos anéis (orçamento de tamanho)
AREA_SEM_NOME = 1.0       # graus²: estados sem nome menores que isso não entram


def aneis_de(g):
    ps = list(g.geoms) if hasattr(g, "geoms") else [g]
    out = []
    for p in ps:
        if p.geom_type != "Polygon" or p.area < 0.03: continue
        q = p.simplify(TOL_SAIDA)
        if q.is_empty or q.geom_type != "Polygon": q = p
        for r in [q.exterior] + [i for i in q.interiors if Polygon(i).area >= 0.03]:
            out.append([[round(x, 2), round(y, 2)] for x, y in list(r.coords)[:-1]])
    return out


def main():
    regras = Regras(os.path.join(AQUI, "nomes.json"))
    terra = carregar_terra()
    pedidos = {int(a) for a in sys.argv[1:]}
    quadros = []
    for f in glob.glob(os.path.join(CACHE, "estados", "*.json")):
        d = json.load(open(f))
        if pedidos and d["ano"] not in pedidos: continue
        quadros.append(d)
    quadros.sort(key=lambda d: -d["ano"])
    os.makedirs(SAIDA, exist_ok=True)

    meta = {}                     # id -> {nome, cor, desde, ate, nota}
    cores_vistas = defaultdict(Counter)
    anos_vistos = defaultdict(list)
    total = 0
    for q in quadros:
        ano = q["ano"]
        por_id = defaultdict(list)
        for est in q["estados"]:
            p = poligono_estado(est["anel"])
            if p is None or p.is_empty: continue
            c = p.centroid
            r = regras.casa(est["cor"], c.x, c.y, ano)
            if r:
                sid = r["id"]
            else:
                sid = "x-%02x%02x%02x-%d-%d" % (est["cor"][0] // 32 * 32, est["cor"][1] // 32 * 32,
                                                 est["cor"][2] // 32 * 32, math.floor(c.x / 10), math.floor(c.y / 10))
            g = na_terra(terra, p)
            if g.is_empty: continue
            por_id[sid].append(g)
            if r:
                m = meta.setdefault(sid, {"nome": r["nome"], "cor": hexa(est["cor"]),
                                          "desde": r["anos"][0], "ate": r["anos"][1], "nota": r.get("nota", "")})
                m["desde"] = max(m["desde"], r["anos"][0])
                m["ate"] = min(m["ate"], r["anos"][1])
            else:
                cores_vistas[sid][hexa(est["cor"])] += 1
            anos_vistos[sid].append(ano)

        geoms = [(sid, so_poligonos(unary_union(gs))) for sid, gs in por_id.items()]
        # sem sobreposição: do menor para o maior
        geoms.sort(key=lambda t: t[1].area)
        ocupado = None
        lista = []
        for sid, g in geoms:
            if g.is_empty: continue
            if ocupado is not None:
                g = so_poligonos(g.difference(ocupado))
            if g.is_empty or g.area < (AREA_SEM_NOME if sid.startswith("x-") else 0.05): continue
            ocupado = g if ocupado is None else unary_union([ocupado, g])
            lista.append((sid, g))
        saida = []
        for sid, g in lista:
            an = aneis_de(g)
            if not an: continue
            saida.append({"id": sid, "area": round(g.area, 1), "aneis": an})
        arq_saida = os.path.join(SAIDA, nome_arquivo(ano) + ".json")
        json.dump({"ano": ano, "estados": saida}, open(arq_saida, "w"), separators=(",", ":"))
        tam = os.path.getsize(arq_saida)
        total += tam
        print("ano %6d  estados=%3d  %5.1f KB" % (ano, len(saida), tam / 1024), flush=True)

    # estados sem regra: cor mais frequente e período observado
    for sid, cont in cores_vistas.items():
        if sid in meta: continue
        a = anos_vistos[sid]
        meta[sid] = {"nome": "", "cor": cont.most_common(1)[0][0], "desde": max(a), "ate": min(a), "nota": ""}
    if not pedidos:
        indice = {"anos": [q["ano"] for q in quadros], "estados": meta, "fonte": FONTE}
        json.dump(indice, open(os.path.join(SAIDA, "indice.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    print("total: %.0f KB em %d anos, %d estados no índice" % (total / 1024, len(quadros), len(meta)))


if __name__ == "__main__":
    main()
