# Gera frontend/mapa/geral-<ano>.json: os territórios do mapa geral (frontend/mapa-geral/dados/) no ano de cada mapa
# da Bíblia, no formato lido por mapa.js: [{id, nome, aneis: [[lon, lat], ...], rotulo}].
# Também liga cada região citada no livro ("provincia" nos lugares dos mapas) ao estado de mesmo nome do mapa geral;
# a que não existe no mapa geral naquele ano é listada no fim e fica como região à mão (contorno tracejado).
# Uso (na raiz do repositório):  python3 scripts/mapa/geral.py
import glob, json, os, re, unicodedata

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
GERAL = os.path.join(RAIZ, "frontend", "mapa-geral", "dados")
MAPA = os.path.join(RAIZ, "frontend", "mapa")
CAIXA = (-30, 0, 90, 62)   # lon0, lat0, lon1, lat1: o mundo da Bíblia
# id da região citada nos mapas -> nomes (sem acento, minúsculos) do mapa geral que a representam
ALIAS = {
    "egito": ["egito"], "assiria": ["assiria"], "babilonia": ["babilonia"], "elao": ["elao"], "fenicia": ["fenicia"],
    "israel": ["israel", "israelitas"], "israel-unido": ["israel", "israelitas"], "juda": ["juda", "israelitas"], "persia": ["imperio aquemenida", "persia", "aquemenida"],
    "media": ["media"], "cuxe": ["cuxe"], "hititas": ["hititas", "imperio hitita"], "sumer": ["sumer"],
}


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    return re.sub(r"[^a-z0-9 ]", "", "".join(c for c in s if not unicodedata.combining(c)).lower()).strip()


def pos(a):
    return 2500 - a if a > 0 else 2499 - a


def decodificar(anel):
    x, y = anel[0], anel[1]
    pts = [[x / 100, y / 100]]
    for i in range(2, len(anel), 2):
        x += anel[i]; y += anel[i + 1]
        pts.append([x / 100, y / 100])
    return pts


def area(a):
    return abs(sum(a[i][0] * a[i - 1][1] - a[i - 1][0] * a[i][1] for i in range(len(a)))) / 2


def nome_em(est, ano):
    # anos d.C. são negativos: de >= ano >= ate vale para toda a sequência 2500 … -2025
    for de, ate, n in [x[:3] for x in est.get("nomes", [])]:
        if de >= ano >= ate:
            return n
    return est["nome"]


indice = json.load(open(os.path.join(GERAL, "indice.json")))["estados"]


def territorios(ano):
    p0 = pos(ano) // 25 * 25
    ini = 2500 - p0 if p0 <= 2499 else -(p0 - 2499)
    arq = ("a%d" % ini) if ini > 0 else ("d%d" % -ini)
    bloco = json.load(open(os.path.join(GERAL, "blocos", arq + ".json")))
    saida = []
    for f in bloco["formas"]:
        if not (f["de"] >= ano >= f["ate"]):
            continue
        aneis = [decodificar(a) for a in f["aneis"]]
        pts = [p for a in aneis for p in a]
        if not pts or max(p[0] for p in pts) < CAIXA[0] or min(p[0] for p in pts) > CAIXA[2] \
                or max(p[1] for p in pts) < CAIXA[1] or min(p[1] for p in pts) > CAIXA[3]:
            continue
        aneis.sort(key=area, reverse=True)
        saida.append({"id": f["id"], "nome": nome_em(indice[f["id"]], ano), "aneis": aneis, "rotulo": f.get("r")})
    return saida


TRACEJADAS = {"israel", "israel-unido"}   # citados nos livros: sempre com contorno tracejado, mesmo vindo do mapa geral
PROXIMO = 15                              # anos de folga para achar no mapa geral o estado de um ano vizinho


# Judá, Israel (Samaria) e Fenícia nos mapas de 735, 458 e 445 a.C.: o mapa geral não tem Israel nem a costa da Fenícia
# nesses anos, então os três vêm do último ano em que os estados vizinhos existem juntos (739 a.C.), para se encaixarem
ANO_FIXO = {735: 739, 458: 739, 445: 739}
FIXO_NOMES = {"israel": "israel", "samaria": "israel", "juda": "juda", "fenicia": "fenicia"}


def forma_fixa(rid, ano):
    ref = ANO_FIXO.get(ano)
    if not ref or rid not in FIXO_NOMES:
        return None
    formas = [t for t in territorios(ref) if norm(t["nome"]) == FIXO_NOMES[rid]]
    if not formas:
        return None
    aneis = [a for t in formas for a in t["aneis"]]
    return {"id": rid, "nome": formas[0]["nome"], "aneis": aneis, "rotulo": formas[0]["rotulo"],
            "tracejado": not (rid == "juda" and ano == 735)}


def forma_proxima(rid, ano):
    """Estado do mapa geral que existe pouco antes ou depois de "ano" (ex.: Israel até 739 a.C. num mapa de 735)."""
    alvos = ALIAS.get(rid, [rid])
    for k in range(1, PROXIMO + 1):
        for a in (ano + k, ano - k):      # a.C. positivo: o ano anterior é o maior
            if a == 0 or a > 2500 or a < -2025:
                continue
            for t in territorios(a):
                if norm(t["nome"]) in alvos:
                    return {"id": rid, "nome": t["nome"], "aneis": t["aneis"], "rotulo": t["rotulo"], "tracejado": True}
    return None


def forma_antiga(d, ano, rid):
    """Região citada no livro que o mapa geral não tem naquele ano: usa a forma de territorios-<ano>.json ou de
    roma.json (marcada "tracejado": é desenhada como região à mão, com contorno tracejado)."""
    if ano < 0:
        fontes = json.load(open(os.path.join(MAPA, "roma.json")))["provincias"]
    else:
        fontes = json.load(open(os.path.join(MAPA, "territorios-%d.json" % ano)))
    for t in fontes:
        if t["id"] == rid:
            return {"id": rid, "nome": t["nome"], "aneis": t["aneis"], "rotulo": t.get("rotulo"), "tracejado": True}
    return None


def main():
    por_ano = {}
    for arq in sorted(glob.glob(os.path.join(MAPA, "mapa-*.json"))):
        d = json.load(open(arq))
        ano = d.get("geral") or d.get("territorios") or (-d["imperio"] if d.get("imperio") else None)
        if ano is None:
            continue
        por_ano.setdefault(ano, []).append((arq, d))
    for ano, mapas in sorted(por_ano.items(), reverse=True):
        lista = territorios(ano)
        for arq, d in mapas:
            for lg in d["lugares"]:
                pv = lg.get("provincia")
                if not pv or lg.get("area"):
                    continue
                rid = lg["id"] if pv is True else pv
                alvos = ALIAS.get(rid, [rid])
                fixa = forma_fixa(rid, ano)
                if fixa:
                    lista[:] = [t for t in lista if t["id"] != rid and norm(t["nome"]) not in alvos]
                    lista.append(fixa)
                    continue
                # um estado pode ter várias formas no mesmo ano (Fenícia: costa e Chipre): viram uma só região
                iguais = [t for t in lista if norm(t["nome"]) in alvos or t["id"] == rid]
                if iguais:
                    t = iguais[0]
                    for o in iguais[1:]:
                        t["aneis"] += o["aneis"]
                        lista.remove(o)
                    t["id"], t["ligado"] = rid, True
                    if rid in TRACEJADAS:
                        t["tracejado"] = True
                    continue
                if rid in TRACEJADAS:
                    for t in lista:
                        if t["id"] == rid:
                            t["tracejado"] = True
                if not any(t["id"] == rid for t in lista):
                    antigo = forma_proxima(rid, ano) or forma_antiga(d, ano, rid)
                    if antigo:
                        lista.append(antigo)
                    else:
                        print("sem forma nem no mapa geral nem na antiga: %s %s (%s)" % (os.path.basename(arq), rid, ano))
        for t in lista:
            t.pop("ligado", None)
            if t["id"] in TRACEJADAS or norm(t["nome"]) in ("israel", "israelitas"):
                t["tracejado"] = True
            if t["rotulo"] is None:
                t.pop("rotulo")
        saida = os.path.join(MAPA, "geral-%d.json" % ano)
        json.dump(lista, open(saida, "w"), ensure_ascii=False, separators=(",", ":"))
        print(ano, len(lista), "estados,", os.path.getsize(saida) // 1024, "KB")


main()
