#!/usr/bin/env python3
# E8 do mapa geral (v2): grava os 4.525 anos (2500 a.C. a 2025 d.C.) no formato do site, em blocos de 25 anos.
# Entrada (só .cache/v2/, nunca os mapas antigos): nomes-lidos.json (E7: entidades finais, nomes lidos, variantes da
#   E6 e dos vetores usadas), entidades.json da E6 (ids por região em cada corrida de mapa, cor do vídeo), os vetores
#   da E5/E7u (cobertura em lon/lat, já recortada na costa e com tremor) e nomes.json (traduções pt-BR, correções por
#   entidade {id da E7: {nome | nomes: [[de, ate, nome]], nota}}, trocas de nome aprovadas). Nomes lidos sem tradução
#   são publicados como lidos se parecem uma palavra (publicavel); pedaços de etiqueta de duas linhas (FRAGMENTOS)
#   e leituras curtas/abreviadas ficam sem rótulo.
# Saída: frontend/mapa-geral/dados/indice.json
#   {"versao": 2, "de": 2500, "ate": -2025, "bloco": 25, "fonte": "...",
#    "estados": {"<id>": {"nome", "nome_video", "cor", "desde", "ate", "nota", "nomes": [[de, ate, nome, nome_video], ...]?}}}
#   ("nomes" só quando o nome publicado muda ao longo da vida: trocas aprovadas em nomes.json; "nome" é o mais duradouro)
# e frontend/mapa-geral/dados/blocos/<a|d><ano>.json, um por bloco de 25 posições da sequência de anos
#   (2500…1, -1…-2025, sem ano 0; posição i = 0…4524; o bloco tem o nome do seu primeiro ano, ex.: a2500 = 2500–2476 a.C.):
#   {"anos": [de, ate], "formas": [{"id", "de", "ate", "aneis": [[x0, y0, dx1, dy1, dx2, dy2, ...], ...], "r": [lon, lat]}, ...]}
#   ("r" = ponto para o nome: polo de inacessibilidade do maior anel)
#   Cada forma vale de "de" a "ate" (inclusive, recortado ao bloco); uma forma nova só é gravada quando a geometria
#   muda. Coordenadas com 2 casas, gravadas como inteiros em centésimos de grau: o primeiro ponto absoluto (lon, lat)
#   e os seguintes como diferenças do ponto anterior (o tremor dá passos de ~0,25°, então os deltas são curtos).
#   Anéis abertos (a página fecha com Z; fill-rule evenodd para os furos, como na E5).
# Ids: slug do nome pt-BR mais duradouro da entidade (+ "-2", "-3"… se repetir, na ordem de aparição), e o id da E7
#   ("e01234") para entidades sem nome lido. Estáveis entre execuções (dependem só dos dados).
# Orçamento: <= 400 KB por bloco (<= 100 KB com gzip); se o total passar de 80 MB, para e pergunta (plano, §9).
# Uso (na raiz do repositório):  PYTHONPATH=~/.cache/mapa-biblia-lib/lib python3 scripts/mapa-geral/construir.py [--so-medir]
#   [--saida <pasta>]   (ou MAPA_GERAL_SAIDA; padrão frontend/mapa-geral/dados/. Uma rodada em outra cache, por exemplo
#   MAPA_GERAL_CACHE=.cache-4k, grava em --saida .cache-4k/dados para comparar antes de aprovar.)
import gzip, json, os, re, sys, time, unicodedata
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, os.path.expanduser("~/.cache/mapa-biblia-lib/lib"))
sys.path.insert(0, AQUI)
import cache

V2 = cache.V2
SAIDA = os.environ.get("MAPA_GERAL_SAIDA") or os.path.join(RAIZ, "frontend", "mapa-geral", "dados")   # ou --saida <pasta>
BLOCO = 25
CASAS = 2
FONTE = ("Formas, cores e nomes lidos de um vídeo de história mundial ano a ano (de terceiros), usado só como "
         "referência; contornos recalculados sobre a costa do Natural Earth (domínio público) e nomes traduzidos.")
LIMITE_TOTAL = 80 * 1024 * 1024
LIMITE_BLOCO, LIMITE_BLOCO_GZ = 400 * 1024, 100 * 1024


def nome_arquivo(ano):
    return ("a%d" % ano) if ano > 0 else ("d%d" % -ano)


def slug(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


# pedaços de etiqueta de duas linhas ("Roman / Empire", "South / Africa") lidos sozinhos: não viram nome
FRAGMENTOS = {"empire", "kingdom", "union", "states", "state", "land", "coast", "river", "rive", "western", "westernl",
              "eastern", "northern", "southern", "southem", "central", "lower", "upper", "new", "great", "little", "east",
              "west", "south", "north", "nerth", "of", "de", "la", "dutch", "company", "colony", "territory", "teritory",
              "yeritory", "protectorate", "republics", "republic", "city states", "muslims", "berber", "indian", "africa",
              "arabia", "federst", "united", "confederation"}


def publicavel(nome):
    """Nome lido sem tradução: publica se parece uma palavra (>= 3 letras, com vogal, não só maiúsculas, sem ponto
    de abreviação) e não é um pedaço de etiqueta; senão a entidade fica sem rótulo."""
    n = nome.strip()
    letras = re.sub(r"[^A-Za-z]", "", n)
    if len(letras) < 3 or n.endswith(".") or not re.search(r"[aeiouyAEIOUY]", letras):
        return False
    if letras.isupper() or n.casefold() in FRAGMENTOS:
        return False
    return True


class Nomes:
    def __init__(self):
        self.j = json.load(open(os.path.join(AQUI, "nomes.json")))
        self.trad = self.j.get("traducoes", {})
        self.ent = self.j.get("entidades", {})

    def traduzir(self, lido):
        if lido in self.trad:
            return self.trad[lido]
        return lido.strip() if publicavel(lido) else ""


def arredondar(aneis):
    """Anéis em centésimos de grau (inteiros), sem pontos repetidos seguidos nem o ponto de fecho, codificados como
    [x0, y0, dx1, dy1, ...]; anéis com < 3 pontos somem."""
    out = []
    for a in aneis:
        pts = []
        for x, y in a:
            p = (int(round(float(x) * 10 ** CASAS)), int(round(float(y) * 10 ** CASAS)))
            if not pts or pts[-1] != p:
                pts.append(p)
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts.pop()
        if len(pts) >= 3:
            cod = [pts[0][0], pts[0][1]]
            for i in range(1, len(pts)):
                cod.append(pts[i][0] - pts[i - 1][0])
                cod.append(pts[i][1] - pts[i - 1][1])
            out.append(cod)
    return out


def decodificar(anel):
    """Inverso de arredondar: [x0, y0, dx1, dy1, ...] -> [[lon, lat], ...] em graus (2 casas)."""
    pts = []
    x, y = anel[0], anel[1]
    pts.append([x / 10 ** CASAS, y / 10 ** CASAS])
    for i in range(2, len(anel), 2):
        x += anel[i]
        y += anel[i + 1]
        pts.append([x / 10 ** CASAS, y / 10 ** CASAS])
    return pts


def carregar():
    """Tudo o que a E8 lê: corridas de mapa da E6 (com a variante registrada na E7), vetores, nomes."""
    nl = json.load(open(cache.Etapa("e7").caminho("nomes-lidos", ".json")))
    et6 = cache.Etapa("e6")
    var6 = nl["e6"]["variante"]
    ent = json.load(open(et6.caminho("entidades", ".json", var6)))
    etv = cache.Etapa(nl["e6"]["fonte"])
    var_v = var6 if var6 in etv.m["variantes"] else etv.m["aprovada"]
    anos = json.load(open(os.path.join(V2, "anos.json")))
    ordem = [int(a) for a in anos]
    return nl, ent, (etv, var_v), ordem


def formas_por_corrida(nl, ent, vet):
    """Para cada corrida de mapa [ano_de, ano_ate, mapa, {r: e6}] -> {id final: anéis arredondados} (regiões de
    estado de todos os ids da E6 que formam a entidade final, concatenadas)."""
    etv, var_v = vet
    final_de = {e: d["final"] for e, d in nl["entidades"].items()}
    saida = []
    for c in ent["por_ano"]:
        v = json.load(open(etv.caminho(c[2], ".json", var_v)))
        por_final = defaultdict(list)
        for r, e in sorted(c[3].items(), key=lambda kv: int(kv[0])):
            d = v["regioes"].get(r)
            if not d or d["tipo"] != "estado":
                continue
            por_final[final_de.get(e, e)].extend(arredondar(d["aneis"]))
        saida.append((c[0], c[1], c[2], {f: a for f, a in por_final.items() if a}))
    return saida


def final_em(corridas, pos, ano, lon, lat):
    """Entidade final cuja forma contém o ponto (lon, lat) no ano; None se nenhuma."""
    from shapely.geometry import Point, Polygon
    pt = Point(lon, lat)
    for a_de, a_ate, k, fs in corridas:
        if pos[a_de] <= pos.get(ano, -1) <= pos[a_ate]:
            for f, aneis in fs.items():
                for an in aneis:
                    try:
                        if Polygon(decodificar(an)).contains(pt):
                            return f
                    except Exception:
                        pass
            return None
    return None


def indice_estados(nl, ent, ordem, corridas, nomes):
    """Metadados de cada entidade final publicada: id legível, nome pt-BR (mais duradouro), nome do vídeo, cor da E6
    (do id mais longo), vida (dos anos em que aparece com geometria) e nomes por trecho quando mudam."""
    pos = {a: i for i, a in enumerate(ordem)}
    vida = {}
    for a_de, a_ate, k, fs in corridas:
        for f in fs:
            v = vida.setdefault(f, [a_de, a_ate])
            if pos[a_de] < pos[v[0]]: v[0] = a_de
            if pos[a_ate] > pos[v[1]]: v[1] = a_ate
    # correções de nomes.json "entidades": por localizador 'onde' [ano, lon, lat] (estável entre rodadas) ou pelo id da E7
    corr_por_final = {}
    for chave, corr in nomes.ent.items():
        f = None
        if corr.get("onde"):
            f = final_em(corridas, pos, corr["onde"][0], corr["onde"][1], corr["onde"][2])
        if f is None and chave in vida:
            f = chave
        if f is not None:
            corr_por_final[f] = corr
    estados, ids, usados = {}, {}, {}
    for f in sorted(vida, key=lambda f: (pos[vida[f][0]], f)):
        fin = nl["finais"][f]
        trechos = []
        for a_de, a_ate, lido, apoio, n in fin["trechos"]:
            nome = nomes.traduzir(lido)
            if nome:
                trechos.append([a_de, a_ate, nome, lido])
        corr = corr_por_final.get(f, {})
        lido_corr = corr.get("nome_video") or (trechos[0][3] if trechos else "")
        if corr.get("nomes"):      # nomes por período, conferidos à mão: [[de, ate, nome], ...]
            trechos = [[a_de, a_ate, nm, lido_corr] for a_de, a_ate, nm in corr["nomes"]]
        elif corr.get("nome"):
            trechos = [[vida[f][0], vida[f][1], corr["nome"], lido_corr]]
        peso = defaultdict(int)
        for a_de, a_ate, nome, lido in trechos:
            peso[nome] += pos[a_ate] - pos[a_de] + 1
        nome = max(peso, key=lambda n: (peso[n], n)) if peso else ""
        lido = next((t[3] for t in trechos if t[2] == nome), "")
        base = slug(nome) if nome else f
        n = usados.get(base, 0) + 1
        usados[base] = n
        ident = base if n == 1 else f"{base}-{n}"
        ids[f] = ident
        cor = max((ent["entidades"][e] for e in fin["ids"]), key=lambda d: (pos[d["anos"][1]] - pos[d["anos"][0]], d["cor"]))["cor"]
        e = {"nome": nome, "nome_video": lido, "cor": cor, "desde": vida[f][0], "ate": vida[f][1], "nota": corr.get("nota", "")}
        distintos = sorted({t[2] for t in trechos})
        if len(distintos) > 1:
            e["nomes"] = [[a_de, a_ate, nm, ld] for a_de, a_ate, nm, ld in trechos]
        estados[ident] = e
    return estados, ids


_memo_rotulo = {}


def ponto_rotulo(aneis):
    """[lon, lat] para o nome: polo de inacessibilidade do maior anel (fica dentro mesmo em formas curvas, como o
    Vietnã, onde o centro de massa cai fora)."""
    maior = max(aneis, key=len)
    ch = (maior[0], maior[1], len(maior), maior[-1])
    if ch in _memo_rotulo:
        return _memo_rotulo[ch]
    from shapely.geometry import Polygon
    from shapely.algorithms.polylabel import polylabel
    try:
        pol = Polygon(decodificar(maior))
        if not pol.is_valid:
            pol = pol.buffer(0)
            if pol.geom_type != "Polygon":
                pol = max(pol.geoms, key=lambda g: g.area)
        p = polylabel(pol, tolerance=0.05)
        out = [round(p.x, 2), round(p.y, 2)]
    except Exception:
        pts = decodificar(maior)
        out = [round(sum(q[0] for q in pts) / len(pts), 2), round(sum(q[1] for q in pts) / len(pts), 2)]
    _memo_rotulo[ch] = out
    return out


def blocos(ordem, corridas, ids):
    """Formas por bloco de 25 posições: uma forma por (id, geometria) enquanto a geometria não muda."""
    pos = {a: i for i, a in enumerate(ordem)}
    n_blocos = (len(ordem) + BLOCO - 1) // BLOCO
    saida = []
    corr_i = 0
    for b in range(n_blocos):
        p0, p1 = b * BLOCO, min((b + 1) * BLOCO, len(ordem)) - 1
        formas, abertas = [], {}
        while corr_i < len(corridas) and pos[corridas[corr_i][1]] < p0:
            corr_i += 1
        j = corr_i
        while j < len(corridas) and pos[corridas[j][0]] <= p1:
            a_de, a_ate, k, fs = corridas[j]
            de, ate = ordem[max(pos[a_de], p0)], ordem[min(pos[a_ate], p1)]
            for f, aneis in fs.items():
                ab = abertas.get(f)
                if ab is not None and ab["aneis"] == aneis and pos[ab["ate"]] == pos[de] - 1:
                    ab["ate"] = ate
                    continue
                forma = {"id": ids[f], "de": de, "ate": ate, "aneis": aneis, "r": ponto_rotulo(aneis)}
                formas.append(forma)
                abertas[f] = forma
            for f in list(abertas):
                if f not in fs:
                    del abertas[f]
            j += 1
        formas.sort(key=lambda x: (pos[x["de"]], x["id"]))
        saida.append((ordem[p0], ordem[p1], formas))
    return saida


EDICOES = os.path.join(AQUI, "edicoes.json")


def _pos(a):
    return 2500 - a if a > 0 else 2499 - a


def _ano(p):
    return 2500 - p if p < 2500 else -(p - 2499)


def unir_em_bloco(d, fica, some):
    """Dentro de um bloco, as formas de `some` passam a `fica`: nas posições em que os dois existem, os anéis são
    concatenados; novas formas de `fica` são cortadas onde a geometria muda."""
    fa = [f for f in d["formas"] if f["id"] == fica]
    fb = [f for f in d["formas"] if f["id"] == some]
    if not fb:
        return False
    resto = [f for f in d["formas"] if f["id"] not in (fica, some)]
    p0, p1 = _pos(d["anos"][0]), _pos(d["anos"][1])
    novas, aberta = [], None
    for i in range(p0, p1 + 1):
        aneis = []
        for f in fa + fb:
            if _pos(f["de"]) <= i <= _pos(f["ate"]):
                aneis = aneis + f["aneis"]
        if not aneis:
            aberta = None
            continue
        if aberta is not None and aberta["aneis"] == aneis:
            aberta["ate"] = _ano(i)
        else:
            aberta = {"id": fica, "de": _ano(i), "ate": _ano(i), "aneis": aneis}
            novas.append(aberta)
    d["formas"] = sorted(resto + novas, key=lambda x: (_pos(x["de"]), x["id"]))
    return True


def id_em(ler_bloco, nomes_blocos, ano, lon, lat):
    """Id (do site) da forma que contém o ponto no ano, lendo o bloco do ano; None se nenhuma."""
    from shapely.geometry import Point, Polygon
    nome = nome_arquivo(_ano((_pos(ano) // BLOCO) * BLOCO))
    if nome not in nomes_blocos:
        return None
    pt = Point(lon, lat)
    for f in ler_bloco(nome)["formas"]:
        if _pos(f["de"]) <= _pos(ano) <= _pos(f["ate"]):
            for an in f["aneis"]:
                try:
                    if Polygon(decodificar(an)).contains(pt):
                        return f["id"]
                except Exception:
                    pass
    return None


def aplicar_edicao(ed, indice, ler_bloco, gravar_bloco, nomes_blocos):
    """Aplica uma edição de edicoes.json ao índice (em memória) e aos blocos (ler_bloco(nome) -> dict,
    gravar_bloco(nome, dict)). Devolve True se algo mudou. Os ids do site mudam quando os dados são regenerados;
    por isso cada edição pode trazer 'onde' ([ano, lon, lat], ou uma lista deles em 'unir'): se o id não existe
    mais, a entidade é achada pelo ponto."""
    est = indice["estados"]
    t = ed.get("tipo")
    if t in ("nome", "cor", "forma") and ed.get("id") not in est and ed.get("onde"):
        novo = id_em(ler_bloco, nomes_blocos, *ed["onde"])
        if novo is None:
            return False
        ed = dict(ed, id=novo)
    if t == "unir" and ed.get("onde"):
        ids = list(ed["ids"])
        for i in (0, 1):
            if ids[i] not in est and ed["onde"][i]:
                ids[i] = id_em(ler_bloco, nomes_blocos, *ed["onde"][i]) or ids[i]
        ed = dict(ed, ids=ids)
    if t == "nome":
        e = est.get(ed["id"])
        if not e:
            return False
        feito = False
        if e.get("nomes") and ed.get("ano") is not None:
            for tr in e["nomes"]:
                if _pos(tr[0]) <= _pos(ed["ano"]) <= _pos(tr[1]):
                    tr[2], tr[3] = ed["nome"], ed.get("nome_video", tr[3])
                    feito = True
            if feito:
                maior = max(e["nomes"], key=lambda tr: _pos(tr[1]) - _pos(tr[0]))
                e["nome"], e["nome_video"] = maior[2], maior[3]
                return True
        e["nome"] = ed["nome"]
        e["nome_video"] = ed.get("nome_video", e.get("nome_video", ""))
        e.pop("nomes", None)
        return True
    if t == "cor":
        e = est.get(ed["id"])
        if not e or not re.fullmatch(r"#[0-9a-f]{6}", ed["cor"]):
            return False
        e["cor"] = ed["cor"]
        return True
    if t == "unir":
        fica, some = ed["ids"]
        if fica not in est or some not in est or fica == some:
            return False
        for nome in nomes_blocos:
            d = ler_bloco(nome)
            if unir_em_bloco(d, fica, some):
                gravar_bloco(nome, d)
        a, b = est[fica], est[some]
        a["desde"] = _ano(min(_pos(a["desde"]), _pos(b["desde"])))
        a["ate"] = _ano(max(_pos(a["ate"]), _pos(b["ate"])))
        if not a.get("nome") and b.get("nome"):
            a["nome"], a["nome_video"] = b["nome"], b.get("nome_video", "")
        a["nota"] = (a.get("nota", "") + " Unido a " + (b.get("nome") or some) + " no editor.").strip()
        del est[some]
        return True
    if t == "forma":
        if ed["bloco"] not in nomes_blocos:
            return False
        d = ler_bloco(ed["bloco"])
        for f in d["formas"]:
            if f["id"] == ed["id"] and (f["de"] == ed["de"] or (ed.get("onde") and _pos(f["de"]) <= _pos(ed["onde"][0]) <= _pos(f["ate"]))):
                f["aneis"] = arredondar(ed["aneis"])
                gravar_bloco(ed["bloco"], d)
                return True
        return False
    return False


def aplicar_edicoes(indice, ler_bloco, gravar_bloco, nomes_blocos, edicoes=None):
    """Aplica todas as edições (edicoes.json ou a lista dada) na ordem; devolve quantas valeram."""
    if edicoes is None:
        edicoes = json.load(open(EDICOES))["edicoes"] if os.path.exists(EDICOES) else []
    n = 0
    for ed in edicoes:
        try:
            n += bool(aplicar_edicao(ed, indice, ler_bloco, gravar_bloco, nomes_blocos))
        except (KeyError, TypeError, ValueError):
            pass
    return n


def main():
    global SAIDA
    if "--saida" in sys.argv:
        SAIDA = os.path.abspath(sys.argv[sys.argv.index("--saida") + 1])     # ex.: a cache 4K, antes de aprovar
    so_medir = "--so-medir" in sys.argv
    t0 = time.time()
    nl, ent, vet, ordem = carregar()
    nomes = Nomes()
    corridas = formas_por_corrida(nl, ent, vet)
    estados, ids = indice_estados(nl, ent, ordem, corridas, nomes)
    bl = blocos(ordem, corridas, ids)
    pasta = os.path.join(SAIDA, "blocos")
    os.makedirs(pasta, exist_ok=True)
    tam, tam_gz, maior = [], [], ("", 0)
    conteudos = {}
    for a_de, a_ate, formas in bl:
        s = json.dumps({"anos": [a_de, a_ate], "formas": formas}, separators=(",", ":"), ensure_ascii=False)
        b = s.encode()
        conteudos[nome_arquivo(a_de)] = b
        tam.append(len(b))
        tam_gz.append(len(gzip.compress(b, 9)))
        if len(b) > maior[1]:
            maior = (nome_arquivo(a_de), len(b))
    total = sum(tam)
    print(f"blocos {len(bl)}; estados {len(estados)} ({sum(1 for e in estados.values() if e['nome'])} com nome); "
          f"formas {sum(len(f) for _, _, f in bl)}; total {total / 1e6:.1f} MB ({sum(tam_gz) / 1e6:.1f} MB gzip); "
          f"maior bloco {maior[0]} {maior[1] / 1024:.0f} KB; média {total / len(tam) / 1024:.0f} KB "
          f"({sum(tam_gz) / len(tam) / 1024:.0f} KB gzip); {time.time() - t0:.0f} s")
    acima = [(n, t // 1024) for n, t in zip(conteudos, tam) if t > LIMITE_BLOCO]
    acima_gz = [(n, t // 1024) for n, t in zip(conteudos, tam_gz) if t > LIMITE_BLOCO_GZ]
    if acima or acima_gz:
        print(f"AVISO: {len(acima)} blocos acima de 400 KB ({len(acima_gz)} acima de 100 KB gzip): {acima[:5]}")
    if total > LIMITE_TOTAL:
        print("PARADA: o total passa de 80 MB; perguntar ao usuário (plano, §9) antes de gravar.")
        sys.exit(2)
    if so_medir:
        return
    indice = {"versao": 2, "de": ordem[0], "ate": ordem[-1], "bloco": BLOCO, "estados": estados, "fonte": FONTE}
    dados = {nome: json.loads(b) for nome, b in conteudos.items()}
    n_ed = aplicar_edicoes(indice, lambda nome: dados[nome], lambda nome, d: None, list(dados))
    if n_ed:
        print(f"edições à mão aplicadas (edicoes.json): {n_ed}")
        conteudos = {nome: json.dumps(d, separators=(",", ":"), ensure_ascii=False).encode() for nome, d in dados.items()}
    for f in os.listdir(SAIDA):
        if re.fullmatch(r"[ad]\d+\.json", f):
            os.remove(os.path.join(SAIDA, f))
    for f in os.listdir(pasta):
        if f.endswith(".json") and f[:-5] not in conteudos:
            os.remove(os.path.join(pasta, f))
    for nome, b in conteudos.items():
        open(os.path.join(pasta, nome + ".json"), "wb").write(b)
    json.dump(indice, open(os.path.join(SAIDA, "indice.json"), "w"), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    print("gravado em", os.path.relpath(SAIDA, RAIZ))


if __name__ == "__main__":
    main()
