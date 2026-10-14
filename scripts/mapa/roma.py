# Gera mapa/roma.json (províncias e fronteira do Império Romano por período).
# Uso (na raiz do repositório):  python3 scripts/mapa/roma.py
# Precisa de shapely (pip install shapely). Regras de fronteira: AGENTS.md. Formas editadas à mão (editor-mapas.html)
# entram por scripts/mapa/formas.json ("provincias": {id: [anéis]}) e valem no lugar do polígono-base.
import sys, json, os
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from tremor import tremer
from shapely.geometry import Polygon, MultiPolygon, box
from shapely.ops import unary_union

DEST = os.path.normpath(os.path.join(AQUI, "..", "..", "frontend", "mapa"))
try:
    FORMAS = json.load(open(os.path.join(AQUI, "formas.json")))
except Exception:
    FORMAS = {}

# ------------------------------------------------------------ terra (para recortar ao litoral)
w = json.load(open(DEST + "/mundo.json"))
caixa = box(-14, 20, 46, 58)
terra = None
for f in w["fundo"]:
    if f["tipo"] != "terra": continue
    for a in f["aneis"]:
        if len(a) < 3: continue
        p = Polygon(a)
        p = p if p.is_valid else p.buffer(0)
        if p.intersects(caixa):
            terra = p if terra is None else terra.symmetric_difference(p)
mares = [Polygon(f["pontos"]).buffer(0) for f in w["fundo"] if f["tipo"] == "mar"]
terra = terra.intersection(caixa).difference(unary_union([m for m in mares if m.intersects(caixa)]))
costa = terra.boundary.buffer(0.04)

# ------------------------------------------------------------ províncias (aproximadas)
# desde = ano d.C. em que vira província; cliente_antes = antes disso é reino cliente;
# cliente = sempre reino cliente (não entra na fronteira de Roma)
PROV = [
 dict(id="hispania", nome="Hispânia", desde=-100, aneis=[[(-10, 44), (-10, 36), (-1, 36), (3.5, 41.5), (3.2, 43.0), (-2.0, 43.7)]]),
 dict(id="galia", nome="Gália", desde=-100, aneis=[[(-5.5, 48.8), (-2.0, 43.5), (3.2, 43.0), (7.5, 43.6), (7.0, 46.0), (7.6, 47.6), (7.6, 50.0), (6.0, 51.8), (4.0, 52.0), (1.5, 51.2), (-2.0, 49.7)]]),
 dict(id="britania", nome="Britânia", desde=43, aneis=[[(-6.0, 50.0), (-5.5, 52.5), (-3.5, 53.4), (-2.5, 54.0), (0.5, 53.5), (1.8, 52.8), (1.6, 51.0), (-1.0, 50.3)]]),
 dict(id="recia", nome="Récia e Nórico", desde=-100, aneis=[[(7.6, 47.6), (9.5, 47.5), (10.0, 48.4), (12.0, 48.8), (14.0, 48.4), (16.5, 48.1), (16.5, 46.5), (13.5, 46.5), (10.5, 46.2), (7.0, 46.0)]]),
 dict(id="panonia", nome="Panônia", desde=-100, aneis=[[(16.5, 48.1), (18.8, 47.8), (19.0, 47.2), (18.9, 45.9), (19.9, 45.2), (19.2, 44.7), (16.0, 45.0), (15.5, 46.2), (16.5, 46.5)]]),
 dict(id="dalmacia", nome="Dalmácia", desde=-100, aneis=[[(13.0, 45.4), (15.5, 46.2), (16.0, 45.0), (19.2, 44.7), (19.8, 43.0), (19.4, 41.8), (18.5, 41.0), (15.0, 42.5), (13.5, 44.0)]]),
 dict(id="italia", nome="Itália", desde=-100, aneis=[[(6.0, 43.5), (7.0, 46.0), (10.5, 46.2), (13.5, 46.5), (14.0, 45.7), (16.0, 43.0), (19.5, 40.0), (18.5, 38.8), (17.0, 37.6), (14.8, 37.8), (11.0, 41.0), (8.5, 43.0)]]),
 dict(id="sicilia", nome="Sicília", desde=-100, aneis=[[(12.2, 38.3), (15.8, 38.3), (15.7, 36.6), (12.4, 36.6)]]),
 dict(id="sardenha", nome="Sardenha e Córsega", desde=-100, aneis=[[(8.0, 41.4), (9.9, 41.4), (9.8, 38.8), (8.2, 38.8)], [(8.5, 43.1), (9.6, 43.1), (9.6, 41.5), (8.6, 41.5)]]),
 dict(id="mesia", nome="Mésia", desde=-100, aneis=[[(19.2, 44.7), (21.5, 44.8), (22.5, 44.5), (24.5, 43.7), (26.5, 44.0), (28.7, 44.2), (29.7, 45.2), (28.5, 42.0), (25.5, 42.5), (22.0, 42.0), (20.5, 43.0)]]),
 dict(id="tracia", nome="Trácia", desde=46, cliente_antes=True, aneis=[[(25.5, 42.5), (28.5, 42.0), (28.9, 41.2), (26.0, 40.9), (24.8, 41.5)]]),
 dict(id="macedonia", nome="Macedônia", desde=-100, aneis=[[(19.2, 40.0), (19.0, 41.8), (20.5, 43.0), (22.0, 42.0), (25.5, 42.5), (24.8, 41.5), (24.5, 40.8), (22.7, 39.7), (21.3, 40.2)]]),
 dict(id="acaia", nome="Acaia", desde=-100, aneis=[[(19.5, 39.8), (21.3, 40.2), (22.7, 39.7), (24.5, 38.8), (24.4, 37.2), (22.7, 36.2), (21.0, 36.3), (19.5, 38.5)]]),
 dict(id="asia", nome="Ásia", desde=-100, aneis=[[(26.0, 40.5), (28.0, 40.4), (30.5, 40.0), (31.2, 38.6), (30.3, 37.2), (28.8, 36.5), (26.8, 36.6), (26.0, 38.5)]]),
 dict(id="bitinia", nome="Bitínia e Ponto", desde=-100, aneis=[[(26.9, 40.7), (28.0, 40.4), (30.5, 40.0), (31.2, 40.0), (33.5, 40.5), (36.0, 40.0), (39.0, 40.0), (40.0, 40.6), (39.7, 41.4), (36.5, 42.0), (33.5, 42.2), (31.0, 41.5), (28.5, 41.5)]]),
 dict(id="galacia", nome="Galácia", desde=-100, aneis=[[(31.2, 40.0), (33.5, 40.5), (36.0, 40.0), (37.0, 39.0), (35.5, 38.0), (33.5, 37.5), (32.5, 37.2), (31.2, 38.3)]]),
 dict(id="licia", nome="Lícia e Panfília", desde=43, cliente_antes=True, aneis=[[(28.8, 36.5), (30.3, 37.2), (31.2, 38.0), (32.5, 37.2), (32.2, 36.2), (30.7, 36.0), (29.2, 36.0)]]),
 dict(id="capadocia", nome="Capadócia", desde=17, cliente_antes=True, aneis=[[(36.0, 40.0), (39.0, 40.0), (41.0, 39.5), (41.5, 38.0), (40.0, 37.3), (38.2, 37.0), (36.5, 37.4), (35.5, 38.0), (37.0, 39.0)]]),
 dict(id="cilicia", nome="Cilícia", desde=-100, aneis=[[(32.5, 37.2), (33.5, 37.5), (35.5, 38.0), (36.5, 37.4), (36.2, 36.4), (35.0, 36.4), (34.0, 36.2), (32.2, 36.2)]]),
 dict(id="chipre", nome="Chipre", desde=-100, aneis=[[(32.2, 35.1), (34.7, 35.7), (34.7, 34.6), (32.2, 34.6)]]),
 dict(id="siria", nome="Síria", desde=-100, aneis=[[(36.5, 37.4), (38.2, 37.0), (39.0, 36.0), (38.5, 34.0), (38.0, 33.0), (35.8, 33.0), (35.0, 33.1), (35.0, 34.5), (35.9, 36.0), (36.2, 36.4)]]),
 dict(id="judeia", nome="Judeia", desde=6, cliente_antes=True, aneis=[[(34.2, 32.4), (35.1, 32.7), (35.55, 32.3), (35.6, 31.5), (35.3, 30.9), (34.4, 31.0)]]),
 dict(id="tetrarquias", nome="Tetrarquias", desde=-100, cliente=True, aneis=[[(35.1, 33.1), (35.9, 33.4), (36.0, 32.4), (35.55, 32.3), (35.1, 32.7)]]),
 dict(id="nabateia", nome="Nabateia", desde=-100, cliente=True, aneis=[[(34.3, 31.0), (35.6, 31.5), (36.5, 31.0), (36.5, 28.0), (34.9, 28.5)]]),
 dict(id="egito", nome="Egito", desde=-100, aneis=[[(25.0, 32.2), (34.2, 32.0), (34.9, 29.5), (35.5, 24.0), (32.9, 24.1), (25.0, 22.0)]]),
 dict(id="cirene", nome="Cirenaica e Creta", desde=-100, aneis=[[(19.0, 33.4), (25.0, 33.4), (25.0, 29.5), (19.0, 29.5)], [(23.5, 35.7), (26.4, 35.7), (26.4, 34.9), (23.5, 34.9)]]),
 dict(id="africa", nome="África", desde=-100, aneis=[[(7.0, 38.0), (11.6, 38.0), (12.0, 35.5), (11.0, 33.2), (15.2, 32.3), (19.0, 30.8), (19.0, 29.5), (10.0, 30.2), (7.5, 32.0), (5.0, 34.5)]]),
 dict(id="mauritania", nome="Mauritânia", desde=44, cliente_antes=True, aneis=[[(-9.5, 36.5), (-1.0, 36.3), (5.0, 37.6), (5.0, 34.5), (-1.0, 32.0), (-8.0, 32.0)]]),
]

def so_poligonos(g):
    if g.geom_type in ("Polygon", "MultiPolygon"): return g
    ps = [x for x in getattr(g, "geoms", []) if x.geom_type in ("Polygon", "MultiPolygon")]
    return unary_union(ps) if ps else Polygon()

def recorta(aneis):
    # cresce 0,3° antes do recorte, para os polígonos desenhados à mão alcançarem o litoral
    g = unary_union([Polygon(tremer(a)).buffer(0.3, join_style=2, mitre_limit=3) for a in aneis]).intersection(terra)
    return so_poligonos(g)

def linhas_de(g):
    l = g.boundary.difference(costa)
    if l.is_empty: return []
    ls = list(l.geoms) if hasattr(l, "geoms") else [l]
    return [[[round(x, 2), round(y, 2)] for x, y in s.coords] for s in ls if s.length > 0.05]

def aneis_de(g):
    # sem simplificar: o contorno da província é o mesmo litoral do mapa, inclusive nas ilhas pequenas
    ps = list(g.geoms) if hasattr(g, "geoms") else [g]
    out = []
    for p in ps:
        if p.geom_type != "Polygon" or p.area < 1e-5: continue
        out.append([[round(x, 3), round(y, 3)] for x, y in list(p.exterior.coords)[:-1]])
    return out

saida = {"provincias": [], "fronteiras": {}}
# 1) recorta cada província à terra; a que vem antes na lista ganha nas sobreposições
bruto = {}
vistas = None
for pr in PROV:
    ov = FORMAS.get("provincias", {}).get(pr["id"])
    if ov:   # forma editada à mão: vale como está (só recortada pela costa)
        g = so_poligonos(unary_union([Polygon(r).buffer(0) for r in ov]).intersection(terra))
    else:
        g = recorta(pr["aneis"])
    if vistas is not None and not pr.get("cliente"):
        g = g.difference(vistas)
    bruto[pr["id"]] = g
    if not pr.get("cliente"):
        vistas = g if vistas is None else unary_union([vistas, g])
# 2) fecha as frestas dentro do império: cada pedaço de terra solta vai para a província vizinha
#    com a qual divide mais fronteira, e as províncias passam a se tocar
emp = unary_union([bruto[p["id"]] for p in PROV if not p.get("cliente") and not bruto[p["id"]].is_empty])
fechado = emp.buffer(1.0, join_style=2, mitre_limit=3).buffer(-1.0, join_style=2, mitre_limit=3).intersection(terra)
frestas = fechado.difference(emp)
pecas = list(frestas.geoms) if hasattr(frestas, "geoms") else [frestas]
for peca in pecas:
    if peca.geom_type != "Polygon" or peca.area < 1e-7: continue
    melhor, mv = None, 0.0
    for p in PROV:
        if p.get("cliente") or bruto[p["id"]].is_empty: continue
        v = peca.buffer(0.03).intersection(bruto[p["id"]]).area
        if v > mv: melhor, mv = p["id"], v
    if not melhor:
        md = 1e9
        for p in PROV:
            if p.get("cliente") or bruto[p["id"]].is_empty: continue
            d = peca.distance(bruto[p["id"]])
            if d < md: melhor, md = p["id"], d
    if melhor:
        bruto[melhor] = unary_union([bruto[melhor], peca])
# 2b) ilhas: tudo o que está dentro de cada caixa vai para a província indicada
ILHAS = [
    ("hispania", (1.0, 38.4, 4.6, 40.3)),            # Baleares
    ("sardenha", (7.9, 38.6, 10.0, 43.2)),           # Sardenha e Córsega
    ("sicilia", (14.0, 35.7, 14.7, 36.2)),           # Malta
    ("sicilia", (11.9, 36.6, 12.1, 36.9)),           # Pantelária
    ("sicilia", (12.2, 37.8, 12.4, 38.1)),           # Egadi
    ("dalmacia", (14.3, 42.3, 19.0, 45.4)),          # ilhas da Dalmácia
    ("acaia", (19.2, 36.7, 21.4, 39.9)),             # ilhas Jônicas
    ("acaia", (22.8, 36.0, 25.3, 39.6)),             # Cíclades e Eubeia
    ("macedonia", (24.4, 40.2, 26.0, 40.82)),        # Tasos, Samotrácia
    ("asia", (25.3, 35.8, 28.6, 39.8)),              # ilhas do Egeu oriental
    ("chipre", (32.0, 34.4, 34.9, 35.9)),            # Chipre inteiro
]
for pid, (x0, y0, x1, y1) in ILHAS:
    # só ilhas: componentes pequenos de terra (os continentes e a Itália inteira ficam de fora da caixa)
    cx = box(x0, y0, x1, y1)
    parte = unary_union([c.intersection(cx) for c in (list(terra.geoms) if hasattr(terra, "geoms") else [terra]) if c.area < 6])
    if parte.is_empty: continue
    for p in PROV:
        if p["id"] != pid and not bruto[p["id"]].is_empty and not p.get("cliente"):
            bruto[p["id"]] = bruto[p["id"]].difference(parte)
    bruto[pid] = unary_union([bruto[pid], parte])
# 2c) ilhas que sobraram: componentes pequenos de terra perto do império vão para a província mais próxima
EXCLUIR = [box(-11.5, 50.5, -5.2, 56.0), box(30.0, 12.0, 46.0, 28.0)]   # Irlanda, mar Vermelho
emp2 = unary_union([bruto[p["id"]] for p in PROV if not p.get("cliente") and not bruto[p["id"]].is_empty])
comps = list(terra.geoms) if hasattr(terra, "geoms") else [terra]
for comp in comps:
    if comp.area > 40 or comp.is_empty: continue
    if any(comp.intersects(x) for x in EXCLUIR): continue
    if comp.intersection(emp2).area > 0.8 * comp.area: continue
    if comp.distance(emp2) > 1.6: continue
    resto = comp.difference(emp2)
    if resto.is_empty: continue
    melhor, md = None, 1e9
    for p in PROV:
        if p.get("cliente") or bruto[p["id"]].is_empty: continue
        d = comp.distance(bruto[p["id"]])
        if d < md: melhor, md = p["id"], d
    if melhor:
        bruto[melhor] = unary_union([bruto[melhor], resto])
# reinos clientes não cobrem o que é província
for p in PROV:
    if p.get("cliente"):
        bruto[p["id"]] = bruto[p["id"]].difference(emp)
geos = {}
for pr in PROV:
    g = so_poligonos(bruto[pr["id"]])
    geos[pr["id"]] = g
    if g.is_empty:
        print("SEM TERRA", pr["id"]); continue
    pt = max((list(g.geoms) if hasattr(g, "geoms") else [g]), key=lambda x: x.area).representative_point()
    d = {"id": pr["id"], "nome": pr["nome"], "desde": pr["desde"],
         "aneis": aneis_de(g), "linhas": linhas_de(g), "rotulo": [round(pt.x, 2), round(pt.y, 2)]}
    if pr.get("cliente"): d["cliente"] = True
    if pr.get("cliente_antes"): d["cliente_antes"] = True
    saida["provincias"].append(d)

# fronteira externa de Roma em cada período (só os trechos em terra: Reno, Danúbio, Eufrates, deserto)
for ano in (30, 47):
    uni = unary_union([geos[p["id"]] for p in PROV if not p.get("cliente") and p["desde"] <= ano and not geos[p["id"]].is_empty])
    # fecha as frestas entre polígonos desenhados à mão, para sobrar só o contorno externo
    uni = uni.buffer(0.25, join_style=2, mitre_limit=3).buffer(-0.25, join_style=2, mitre_limit=3)
    # tapa os buracos internos (mares cercados, vãos entre polígonos): só importa o contorno externo
    pols = list(uni.geoms) if hasattr(uni, "geoms") else [uni]
    uni = unary_union([Polygon(p.exterior) for p in pols if p.geom_type == "Polygon"]).intersection(terra)
    uni = so_poligonos(uni)
    longe = uni.boundary.difference(terra.boundary.buffer(0.15))
    ls = list(longe.geoms) if hasattr(longe, "geoms") else [longe]
    # só os trechos longos: arcos curtos perto da costa são artefatos do desenho à mão
    saida["fronteiras"][str(ano)] = [[[round(x, 2), round(y, 2)] for x, y in l.coords] for l in ls if l.length >= 2.5]
    print("fronteira", ano, len(saida["fronteiras"][str(ano)]), "trechos")

json.dump(saida, open(DEST + "/roma.json", "w"), ensure_ascii=False, separators=(",", ":"))
import os
print("roma.json", os.path.getsize(DEST + "/roma.json"), "bytes;", len(saida["provincias"]), "províncias")
