# Gera mapa/territorios-<ano>.json (povos e reinos ao redor, sem sobreposição, com fronteiras comuns).
# Uso (na raiz do repositório):  python3 scripts/mapa/territorios.py
# Precisa de shapely (pip install shapely). Regras de fronteira: AGENTS.md. Formas editadas à mão (editor-mapas.html)
# entram por scripts/mapa/formas.json e valem no lugar do polígono-base daquele ano.
import sys, json, os
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from tremor import tremer
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

DEST = os.path.normpath(os.path.join(AQUI, "..", "..", "frontend", "mapa"))
try:
    FORMAS = json.load(open(os.path.join(AQUI, "formas.json")))
except Exception:
    FORMAS = {}
w = json.load(open(DEST + "/mundo.json"))
caixa = box(20, 5, 75, 50)
terra = None
for f in w["fundo"]:
    if f["tipo"] != "terra": continue
    for a in f["aneis"]:
        if len(a) < 3: continue
        p = Polygon(a); p = p if p.is_valid else p.buffer(0)
        if p.intersects(caixa):
            terra = p if terra is None else terra.symmetric_difference(p)
mares = [Polygon(f["pontos"]).buffer(0) for f in w["fundo"] if f["tipo"] == "mar"]
terra = terra.intersection(caixa).difference(unary_union([m for m in mares if m.intersects(caixa)]))
costa = terra.boundary.buffer(0.04)

# desde / ate: anos a.C. (positivo; desde é o mais antigo)
from shapely.geometry import LineString
_nilo = [f["pontos"] for f in w["fundo"] if f["id"] == "nile"]
NILO_C = [p for p in _nilo if p[0] == [32.88, 23.99] and len(p) > 6][0]          # Cairo -> Assuã
NILO_A = [p for p in _nilo if p[0] == [32.88, 23.99] and len(p) <= 6][0]         # Assuã -> 2ª catarata
NILO_B = [p for p in _nilo if p[0] == [32.49, 15.63]][0]                         # sul da 2ª catarata
def faixa(pontos, larg):
    # corredor do rio, só com linhas retas (cantos em quina, pontas retas)
    return LineString(pontos).buffer(larg, cap_style=2, join_style=2, mitre_limit=2.0)
DELTA = [(29.3, 31.6), (34.3, 31.4), (33.3, 30.1), (29.9, 30.1)]
VALE = faixa([(31.25, 30.2)] + [tuple(p) for p in reversed(NILO_C)], 1.0)
NUBIA_BAIXA = faixa(NILO_A, 0.8)
NUBIA_ALTA = faixa([p for p in NILO_B if p[1] >= 18.0], 0.8)
CUXE_ANTIGO = unary_union([faixa(NILO_A, 1.2), faixa(NILO_B, 1.2)])
CUXE_MEDIO = faixa(NILO_B, 1.2)
CUXE_NOVO = faixa([p for p in NILO_B if p[1] < 18.2], 1.2)
EGITO_NUCLEO = [(29.3, 31.6), (34.3, 31.4), (33.0, 30.0), (33.2, 28.0), (33.6, 26.5), (32.9, 24.0), (31.5, 24.0), (30.5, 26.0), (30.0, 28.5), (29.6, 30.2)]
SINAI = [(32.6, 30.2), (34.3, 31.35), (34.95, 29.5), (34.3, 27.8), (33.4, 28.0)]       # minas do Sinai (Serabit el-Khadim)
NUBIA_2 = [(30.9, 24.0), (33.3, 24.0), (33.3, 22.0), (30.9, 22.0)]   # Baixa Núbia até a 2ª catarata (Reino Médio)
NUBIA_4 = [(30.9, 24.0), (33.5, 24.0), (33.5, 18.0), (30.9, 18.0)]   # até a 4ª catarata (Reino Novo)
T = [
 ("egito#antigo", "Egito", 3100, 2055, [DELTA, VALE]),
 ("egito#medio", "Egito", 2054, 1650, [DELTA, VALE, SINAI, NUBIA_BAIXA]),
 ("egito#segundo", "Egito", 1649, 1550, [DELTA, VALE]),
 ("egito#novo", "Egito", 1549, 1070, [DELTA, VALE, SINAI, NUBIA_BAIXA, NUBIA_ALTA]),
 ("egito#tardio", "Egito", 1069, 30, [DELTA, VALE]),
 ("cuxe#antigo", "Cuxe (Núbia)", 3100, 2055, [CUXE_ANTIGO]),
 ("cuxe#medio", "Cuxe (Núbia)", 2054, 1650, [CUXE_MEDIO]),
 ("cuxe#segundo", "Cuxe (Núbia)", 1649, 1550, [CUXE_ANTIGO]),
 ("cuxe#novo", "Cuxe (Núbia)", 1549, 1070, [CUXE_NOVO]),
 ("cuxe#tardio", "Cuxe (Núbia)", 1069, 30, [CUXE_ANTIGO]),
 ("sumer", "Suméria e Acádia", 3100, 1895, [(43.3, 34.3), (46.0, 34.6), (48.7, 32.6), (48.4, 29.8), (46.0, 29.6), (43.8, 31.5)]),
 ("babilonia", "Babilônia", 1894, 627, [(43.3, 34.3), (46.0, 34.6), (48.7, 32.6), (48.4, 29.8), (46.0, 29.6), (43.8, 31.5)]),
 ("assiria#nucleo", "Assíria", 1400, 745, [(41.6, 37.4), (44.4, 37.4), (44.6, 35.2), (41.8, 35.2)]),
 ("assiria#imperio", "Assíria", 744, 609, [(38.0, 38.2), (45.5, 38.2), (48.0, 35.5), (48.7, 31.5), (47.5, 30.0), (44.0, 29.5), (40.0, 31.0), (36.0, 32.3), (34.4, 31.5), (34.4, 35.0), (35.9, 37.0)]),
 ("media", "Média", 700, 550, [(45.5, 38.6), (53.0, 38.6), (53.0, 33.5), (47.5, 33.3)]),
 ("babilonia#imperio", "Babilônia", 626, 539, [(38.0, 37.5), (44.5, 37.5), (47.5, 34.5), (48.7, 31.5), (47.5, 29.8), (44.0, 29.5), (39.0, 29.5), (35.0, 29.8), (34.3, 31.2), (34.3, 34.5), (35.8, 36.8)]),
 ("persia", "Pérsia", 550, 330, [(26.0, 41.0), (36.0, 41.5), (44.0, 40.0), (50.0, 40.0), (58.0, 38.0), (66.0, 37.5), (70.0, 33.0), (66.0, 26.0), (58.0, 25.0), (50.0, 26.5), (48.0, 29.5), (44.0, 29.5), (39.0, 29.5), (34.3, 29.8), (34.3, 36.0), (26.0, 36.5)]),
 ("juda#yehud", "Yehud (Judá)", 538, 332, [(34.5, 32.0), (35.6, 32.0), (35.6, 31.3), (34.5, 31.2)]),
 ("samaria", "Samaria", 721, 332, [(34.5, 32.75), (35.7, 32.75), (35.7, 32.0), (34.5, 32.0)]),
 ("elao", "Elão", 3100, 539, [(47.5, 33.0), (49.5, 32.8), (50.2, 31.0), (48.5, 30.4), (47.6, 31.5)]),
 ("aram-hara", "Padã-Arã", 2300, 1100, [(37.0, 37.3), (40.6, 37.3), (40.6, 35.8), (37.0, 35.8)]),
 ("aram", "Aram (Síria)", 1100, 732, [(35.9, 37.0), (39.0, 37.0), (39.0, 33.0), (36.1, 32.85)]),
 ("hititas", "Hati (hititas)", 1750, 1180, [(31.5, 40.4), (37.5, 40.4), (37.5, 37.6), (31.5, 37.6)]),
 ("canaa#livre", "Canaã", 2300, 1501, [(34.2, 34.0), (36.1, 34.0), (36.0, 31.0), (34.4, 30.6)]),
 ("canaa#egito", "Canaã (domínio egípcio)", 1500, 1150, [(34.2, 34.0), (36.1, 34.0), (36.0, 31.0), (34.4, 30.6)]),
 ("canaa#tardio", "Canaã", 1149, 1051, [(34.2, 34.0), (36.1, 34.0), (36.0, 31.0), (34.4, 30.6)]),
 ("israel-unido", "Israel", 1050, 931, [(34.5, 33.3), (36.0, 33.3), (36.0, 31.3), (34.5, 31.2)]),
 ("israel", "Israel (norte)", 930, 722, [(34.6, 33.3), (35.85, 33.3), (35.85, 32.0), (34.6, 32.0)]),
 ("juda", "Judá", 930, 586, [(34.5, 32.0), (35.45, 32.0), (35.5, 31.3), (34.6, 31.2)]),
 ("filistia", "Filístia", 1200, 600, [(34.1, 31.15), (34.6, 31.2), (34.85, 31.55), (34.95, 31.9), (34.85, 32.1), (34.1, 32.1)]),
 ("moabe", "Moabe", 1400, 580, [(35.55, 31.45), (35.85, 31.6), (36.3, 31.45), (36.35, 30.85), (35.75, 30.85), (35.55, 31.15)]),
 ("amom", "Amom", 1300, 580, [(35.95, 32.15), (36.45, 32.1), (36.5, 31.65), (36.05, 31.65)]),
 ("edom", "Edom", 1400, 500, [(35.1, 30.85), (35.75, 30.85), (36.3, 30.8), (36.2, 30.0), (35.5, 29.6), (35.1, 29.8)]),
 ("seir", "Seir", 2300, 1401, [(35.1, 30.85), (35.75, 30.85), (36.3, 30.8), (36.2, 30.0), (35.5, 29.6), (35.1, 29.8)]),
 ("midia", "Midiã", 1800, 1000, [(34.9, 29.2), (36.0, 29.0), (36.2, 27.6), (35.0, 27.4)]),
 ("fenicia", "Fenícia", 1500, 332, [(34.9, 34.2), (35.95, 34.2), (35.9, 33.0), (35.1, 33.0)]),
 ("basa", "Basã", 1500, 732, [(35.75, 33.1), (36.3, 33.15), (36.6, 32.9), (36.5, 32.5), (36.0, 32.45), (35.75, 32.7)]),
]

CRESCE = {"juda#yehud": 0.0, "samaria": 0.0, "filistia": 0.0, "juda": 0.0, "israel": 0.0, "israel-unido": 0.0, "moabe": 0.1, "amom": 0.1,
          "edom": 0.1, "seir": 0.1, "basa": 0.1, "midia": 0.1, "fenicia": 0.05}

def so_poligonos(g):
    if g.geom_type in ("Polygon", "MultiPolygon"): return g
    ps = [x for x in getattr(g, "geoms", []) if x.geom_type in ("Polygon", "MultiPolygon")]
    return unary_union(ps) if ps else Polygon()

def aneis_de(g):
    ps = list(g.geoms) if hasattr(g, "geoms") else [g]
    out = []
    for p in ps:
        if p.geom_type != "Polygon" or p.area < 1e-5: continue
        out.append([[round(x, 2), round(y, 2)] for x, y in list(p.simplify(0.01).exterior.coords)[:-1]])
    return out

def linhas_de(g):
    l = g.boundary.difference(costa)
    if l.is_empty: return []
    ls = list(l.geoms) if hasattr(l, "geoms") else [l]
    return [[[round(x, 2), round(y, 2)] for x, y in s.coords] for s in ls if s.length > 0.05]

ANOS = [780, 735, 586, 458, 445, 2100, 2050, 2000, 1950, 1900, 1890, 1500, 1450, 1410, 1400, 1200, 1100, 1010, 970, 900, 860]
# do mais específico para o mais geral: onde dois povos se sobrepõem, o primeiro fica com a terra
ORDEM = ["filistia", "fenicia", "israel", "juda", "juda#yehud", "samaria", "israel-unido", "moabe", "amom", "edom", "seir",
         "midia", "basa", "aram", "canaa#livre", "canaa#egito", "canaa#tardio", "hititas",
         "egito#antigo", "egito#medio", "egito#segundo", "egito#novo", "egito#tardio",
         "cuxe#antigo", "cuxe#medio", "cuxe#segundo", "cuxe#novo", "cuxe#tardio",
         "assiria#nucleo", "assiria#imperio", "elao", "media", "babilonia#imperio", "babilonia", "sumer", "persia", "aram-hara"]
por_id = {t[0]: t for t in T}
OUTRO = None
saida = {"por_ano": {}}
for ano in ANOS:
    lista = []
    ocupado = None
    for tid in ORDEM:
        id, nome, desde, ate, pts = por_id[tid]
        if not (desde >= ano >= ate): continue
        ov = (FORMAS.get("territorios", {}).get(str(ano), {}) or {}).get(id.split("#")[0])
        if ov:   # forma editada à mão: vale como está (só recortada pela costa)
            g = so_poligonos(unary_union([Polygon(r).buffer(0) for r in ov]).intersection(terra))
        else:
            partes = pts if isinstance(pts, list) and pts and not isinstance(pts[0], (int, float)) and (hasattr(pts[0], "geom_type") or isinstance(pts[0][0], (list, tuple))) else [pts]
            blocos = []
            for q in partes:
                if hasattr(q, "geom_type"):   # geometria pronta (corredor do Nilo): só o tremor nas bordas
                    for pl in (list(q.geoms) if hasattr(q, "geoms") else [q]):
                        blocos.append(Polygon(tremer(list(pl.exterior.coords)[:-1])).buffer(0.02, join_style=2, mitre_limit=3))
                else:
                    blocos.append(Polygon(tremer(q)).buffer(CRESCE.get(id.split("#")[0], 0.3), join_style=2, mitre_limit=3))
            g = so_poligonos(unary_union(blocos).intersection(terra))
        if ocupado is not None:
            g = so_poligonos(g.difference(ocupado))
        if g.is_empty: continue
        ocupado = g if ocupado is None else unary_union([ocupado, g])
        pt = max((list(g.geoms) if hasattr(g, "geoms") else [g]), key=lambda x: x.area).representative_point()
        lista.append({"id": id.split("#")[0], "nome": nome, "aneis": aneis_de(g), "linhas": linhas_de(g),
                      "rotulo": [round(pt.x, 2), round(pt.y, 2)]})
    saida["por_ano"][str(ano)] = lista
import glob
for velho in glob.glob(DEST + "/territorios*.json"): os.remove(velho)
tot = 0
for ano, lista in saida["por_ano"].items():
    nome = DEST + "/territorios-" + ano + ".json"
    json.dump(lista, open(nome, "w"), ensure_ascii=False, separators=(",", ":"))
    tot += os.path.getsize(nome)
print("territorios-<ano>.json:", len(saida["por_ano"]), "arquivos,", tot, "bytes no total")
