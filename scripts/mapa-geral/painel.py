#!/usr/bin/env python3
# Painel local do mapa geral v2 (ferramenta de desenvolvimento; nunca publicada, nunca mover para frontend/).
# Um servidor só para o painel.html (visualizador do cache, grade de mapas, versões, rodadas, andamento, revisão e o
# editor.html embutido). Serve a raiz do repositório em 127.0.0.1 e responde:
#   POST /scripts/mapa-geral/anotacoes.json   grava as anotações do visualizador (como fazia o visualizar.py)
#   POST /scripts/mapa-geral/edicoes.json     grava as edições do editor e aplica em frontend/mapa-geral/dados/
#                                             (como fazia o editor.py; a mesma função que construir.py usa)
#   GET  /api/versoes                         manifestos da loja por chave (cache.py): variantes, aprovada, anterior,
#                                             itens, tempo, espaço; sub-etapas E4a/b/d; dados publicados e arquivos de mão
#   POST /api/aprovar {etapa, variante}       troca os apontadores para a variante (cache.Etapa.aprovar)
#   POST /api/apagar-variante {etapa, variante}   limpar_cache.py --variante <etapa> <nome> --apagar
#   GET  /api/mapas                           estado de cada mapa distinto em cada etapa (ok = pronto na aprovada e com
#                                             a chave atual; velho = chave mudou, vai recalcular; falta; espera = a
#                                             etapa anterior não está pronta); calculado numa thread, com a mesma
#                                             fórmula de chave dos scripts (rotular.chave_sub, vetorizar.chave_mapa,
#                                             nomear.chave_mapa)
#   POST /api/mapas/recalcular                recalcula esse estado (também recalcula sozinho ao fim de uma rodada)
#   GET  /api/rodadas · POST /api/rodar {script, args, env} · POST /api/parar {id} · GET /api/log?id=&de=
#                                             fila de rodadas dos scripts do pipeline (uma por vez, log em
#                                             .cache/v2/painel/, retomada segura: o cache por chave continua de onde parou)
# Uso (de qualquer pasta):  python3 scripts/mapa-geral/painel.py [porta]   (padrão 8001)
# e abra http://localhost:8001/scripts/mapa-geral/painel.html
import functools, http.server, json, os, re, signal, subprocess, sys, threading, time, urllib.parse

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, "..", ".."))
LIB = os.path.expanduser("~/.cache/mapa-biblia-lib/lib")
sys.path.insert(0, LIB)
sys.path.insert(0, AQUI)
import cache
import construir

V2 = cache.V2
PAINEL = os.path.join(V2, "painel")
ANOTACOES = os.path.join(AQUI, "anotacoes.json")
CAMINHO_ANOTACOES = "/scripts/mapa-geral/anotacoes.json"
CAMINHO_EDICOES = "/scripts/mapa-geral/edicoes.json"
TIPOS_NOTA = {"mesmo_estado", "estados_diferentes", "problema"}
TIPOS_EDICAO = {"nome", "cor", "unir", "forma"}
MUNDO = os.path.join(RAIZ, "frontend", "mapa", "mundo.json")

# scripts que o painel pode rodar e os argumentos aceitos (sem shell; cada argumento é uma palavra simples)
SCRIPTS = {"rotular", "vetorizar", "rastrear", "nomear", "construir", "calibrar", "transicoes", "testar", "revisar",
           "limpar_cache", "quadros", "amostras", "cache", "testar-pagina"}
ARG_OK = re.compile(r"^[A-Za-z0-9_.:,=+\-]{1,80}$")
ENV_OK = {"MAPA_GERAL_EXP": re.compile(r"^[A-Za-z0-9_\-]{1,40}$"), "MAPA_GERAL_PROCS": re.compile(r"^\d{1,2}$"),
          "AMOSTRA": re.compile(r"^(rapida|media|todos)$"), "MAPA_GERAL_PARAMS": None}


def json_ler(caminho, padrao=None):
    try:
        return json.load(open(caminho))
    except (OSError, ValueError):
        return padrao


def gravar_json(caminho, obj, **kw):
    tmp = caminho + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, **kw)
        f.write("\n")
    os.replace(tmp, caminho)


# ------------------------------------------------------------------ edições do editor (antes em editor.py)
def aplicar_no_site(novas):
    dados = construir.SAIDA
    indice = json.load(open(os.path.join(dados, "indice.json")))
    pasta = os.path.join(dados, "blocos")
    nomes = sorted(f[:-5] for f in os.listdir(pasta) if f.endswith(".json"))
    memo, sujos = {}, set()

    def ler(nome):
        if nome not in memo:
            memo[nome] = json.load(open(os.path.join(pasta, nome + ".json")))
        return memo[nome]

    def gravar(nome, d):
        memo[nome] = d
        sujos.add(nome)
    n = construir.aplicar_edicoes(indice, ler, gravar, nomes, novas)
    for nome in sujos:
        gravar_json(os.path.join(pasta, nome + ".json"), memo[nome], separators=(",", ":"))
    gravar_json(os.path.join(dados, "indice.json"), indice, separators=(",", ":"), sort_keys=True)
    return n


def gravar_edicoes(novas):
    n = aplicar_no_site(novas)
    todas = (json_ler(construir.EDICOES) or {}).get("edicoes", [])
    todas.extend(novas)
    gravar_json(construir.EDICOES, {"_ajuda": "Edições feitas no editor.html (painel.py), aplicadas na ordem pelo construir.py "
                                    "depois de cada regeneração. Tipos: nome, cor, unir, forma (ver cabeçalho de construir.py).",
                                    "edicoes": todas}, indent=1)
    return n, len(todas)


# ------------------------------------------------------------------ versões (manifestos da loja)
def tamanho(caminhos):
    t = 0
    for c in caminhos:
        try:
            t += os.path.getsize(c)
        except OSError:
            pass
    return t


def versoes():
    out = {"etapas": {}, "hora": time.time()}
    for nome in cache.ETAPAS_LOJA:
        et = cache.Etapa(nome)
        chaves = {n: {e["chave"] for e in v["itens"].values()} for n, v in et.m["variantes"].items()}
        vs = {}
        for n, v in et.m["variantes"].items():
            outras = set().union(*[c for m, c in chaves.items() if m != n]) if len(chaves) > 1 else set()
            seg = [e.get("segundos") for e in v["itens"].values()]
            seg = [x for x in seg if isinstance(x, (int, float))]
            vs[n] = {"params": v["params"], "criada": v.get("criada"), "testes": v.get("testes", {}), "itens": len(v["itens"]),
                     "segundos": round(sum(seg)), "com_tempo": len(seg),
                     "mb": round(tamanho([et.obj(c, x) for c in chaves[n] for x in et.exts()]) / 1e6, 1),
                     "mb_so_dela": round(tamanho([et.obj(c, x) for c in chaves[n] - outras for x in et.exts()]) / 1e6, 1),
                     "faltam_objetos": sum(1 for c in chaves[n] if not et.existe(c))}
        out["etapas"][nome] = {"aprovada": et.m["aprovada"], "anterior": et.m["anterior"], "variantes": vs,
                               "publicos": [os.path.join(d, "*" + e) if d else NOME(nome) + e for d, e in cache.PUBLICOS[nome]]}
    for sub in "abd":
        m = cache.manifesto("e4/" + sub)
        seg = [e.get("segundos") or 0 for e in m.values()]
        out["etapas"]["e4" + sub] = {"formato": 1, "itens": len(m), "segundos": round(sum(seg)),
                                     "mb": round(tamanho([os.path.join(V2, "e4", sub, f) for f in os.listdir(os.path.join(V2, "e4", sub))]) / 1e6, 1)
                                     if os.path.isdir(os.path.join(V2, "e4", sub)) else 0}
    mapas = json_ler(os.path.join(V2, "mapas.json"), {})
    out["mapas"] = len(mapas)
    # dados publicados e arquivos de mão
    dados = construir.SAIDA
    ind = json_ler(os.path.join(dados, "indice.json"))
    blocos = os.path.join(dados, "blocos")
    nb = [f for f in os.listdir(blocos)] if os.path.isdir(blocos) else []
    out["publicado"] = {"indice": bool(ind), "estados": len(ind["estados"]) if ind else 0,
                        "com_nome": sum(1 for e in ind["estados"].values() if e.get("nome")) if ind else 0,
                        "blocos": len(nb), "mb": round(tamanho([os.path.join(blocos, f) for f in nb]) / 1e6, 1),
                        "quando": os.path.getmtime(os.path.join(dados, "indice.json")) if ind else None}
    ed = json_ler(construir.EDICOES) or {}
    an = json_ler(ANOTACOES) or {}
    nm = json_ler(os.path.join(AQUI, "nomes.json")) or {}
    out["mao"] = {"edicoes": len(ed.get("edicoes", [])), "anotacoes": len(an.get("anotacoes", [])),
                  "traducoes": len(nm.get("traducoes", {})), "entidades": len(nm.get("entidades", {})), "trocas": len(nm.get("trocas", []))}
    return out


def NOME(etapa):
    return cache.NOME_PUBLICO_UNICO.get(etapa, "<id>")


# ------------------------------------------------------------------ estado dos mapas (grade)
_mapas = {"pronto": False, "calculando": False, "erro": None, "hora": None, "dados": None, "resumo": None}
_trava_mapas = threading.Lock()


def calcular_mapas():
    import rotular, vetorizar, nomear
    rotular._E4E[:] = []            # manifestos sempre relidos (o servidor fica horas no ar)
    vetorizar.E4E = None
    mapas = json_ler(os.path.join(V2, "mapas.json"), {})
    cal = json_ler(cache.calibracao(), {}).get("por_mapa", {})
    mans = {s: cache.manifesto("e4/" + s) for s in "abd"}
    et_e, et5, et7a, et7u = cache.Etapa("e4e"), cache.Etapa("e5"), cache.Etapa("e7a"), cache.Etapa("e7u")
    ap = {"e4e": et_e.m["aprovada"], "e5": et5.m["aprovada"], "e7a": et7a.m["aprovada"], "e7u": et7u.m["aprovada"]}
    mundo_h = cache.hash_arquivo(MUNDO)
    notas = rotular.notas_por_mapa(cal)
    falhas = {}
    for arq, et in (("rotulos-tempo.json", "e4"), ("vetores-tempo.json", "e5")):
        for k, msg in (json_ler(os.path.join(V2, arq)) or {}).get("falhas", {}).items():
            falhas.setdefault(k, {})[et] = msg
    ETAPAS = ["e4a", "e4b", "e4d", "e4e", "e5", "e7a", "e7u"]
    saida, resumo = {}, {e: {"ok": 0, "velho": 0, "falta": 0, "espera": 0} for e in ETAPAS}

    def fmt1(sub, k, ch, caminho):
        e = mans[sub].get(k)
        if not e or not os.path.exists(caminho):
            return "falta", None
        if e.get("chave") != ch:
            return "velho", None
        return "ok", cache.hash_de(mans[sub], k, caminho)

    def loja(et, var, k, ch):
        it = et.itens(var).get(k) if var else None
        if not it or not et.existe(it["chave"]):
            return "falta", it
        return ("ok" if it["chave"] == ch else "velho"), it

    for k in sorted(mapas, key=lambda x: mapas[x]["quadro"]):
        m = mapas[k]
        r = {"quadro": m.get("quadro"), "anos": [m["anos"][0], m["anos"][-1]] if m.get("anos") else None, "n_anos": len(m.get("anos", [])),
             "cal": bool(cal.get(k)), "nota": bool(notas.get(k)), "falhas": falhas.get(k), "s": {}}
        png = os.path.join(V2, "mapas", f"{k}.png")
        if not os.path.exists(png):
            for e in ETAPAS:
                r[e] = "falta"
            r["png"] = False
            saida[k] = r
            continue
        h_png = cache.hash_arquivo(png)
        arq = rotular.arquivos(k)
        r["e4a"], h_a = fmt1("a", k, rotular.chave_sub("a", h_png), arq["a"])
        r["e4b"], h_b = fmt1("b", k, rotular.chave_sub("b", h_png, h_a), arq["b"]) if h_a else ("espera", None)
        r["e4d"], h_d = fmt1("d", k, rotular.chave_sub("d", h_png, h_a, h_b), arq["d"]) if h_b else ("espera", None)
        if h_d and cal.get(k):
            r["e4e"], it = loja(et_e, ap["e4e"], k, rotular.chave_sub("e", h_png, h_a, h_b, h_d, cal[k], mundo_h, notas.get(k)))
        else:
            r["e4e"], it = "espera", None
        if it:
            r["s"]["e4e"] = it.get("segundos")
        if r["e4e"] == "ok":
            try:
                r["e5"], it5 = loja(et5, ap["e5"], k, vetorizar.chave_mapa(k, cal[k], mundo_h))
            except (OSError, ValueError, KeyError):
                r["e5"], it5 = "espera", None
            try:
                r["e7a"], it7 = loja(et7a, ap["e7a"], k, nomear.chave_mapa(k, et_e))
            except (OSError, ValueError, KeyError):
                r["e7a"], it7 = "espera", None
        else:
            r["e5"], it5, r["e7a"], it7 = "espera", None, "espera", None
        if it5:
            r["s"]["e5"] = it5.get("segundos")
        if it7:
            r["s"]["e7a"] = it7.get("segundos")
        itu = et7u.itens(ap["e7u"]).get(k) if ap["e7u"] else None
        r["e7u"] = "ok" if itu and et7u.existe(itu["chave"]) else ("falta" if r["e5"] == "ok" else "espera")
        saida[k] = r
    for r in saida.values():
        for e in ETAPAS:
            resumo[e][r[e]] += 1
    return saida, resumo, ap


def recalcular_mapas():
    with _trava_mapas:
        if _mapas["calculando"]:
            return
        _mapas["calculando"] = True

    def rodar():
        try:
            dados, resumo, ap = calcular_mapas()
            _mapas.update(pronto=True, erro=None, dados=dados, resumo=resumo, aprovadas=ap, hora=time.time())
        except Exception as e:          # mostra o erro no painel em vez de derrubar o servidor
            _mapas.update(erro=f"{type(e).__name__}: {e}", hora=time.time())
        finally:
            _mapas["calculando"] = False
    threading.Thread(target=rodar, daemon=True).start()


# ------------------------------------------------------------------ rodadas (fila de scripts)
_rodadas = {"lista": [], "proximo": 1}
_trava = threading.Lock()
_acorda = threading.Event()
_processo = {"p": None, "id": None}
ARQ_RODADAS = os.path.join(PAINEL, "rodadas.json")


def gravar_rodadas():
    os.makedirs(PAINEL, exist_ok=True)
    gravar_json(ARQ_RODADAS, {"proximo": _rodadas["proximo"], "lista": _rodadas["lista"][-200:]}, indent=0)


def carregar_rodadas():
    d = json_ler(ARQ_RODADAS)
    if not d:
        return
    _rodadas["proximo"] = d.get("proximo", 1)
    for r in d.get("lista", []):
        if r["estado"] in ("fila", "rodando"):
            r["estado"] = "interrompida"
            r["fim"] = r.get("fim") or time.time()
    _rodadas["lista"] = d.get("lista", [])


def validar_rodada(corpo):
    script = corpo.get("script")
    if script not in SCRIPTS:
        raise ValueError("script desconhecido: %r" % script)
    args = corpo.get("args") or []
    if not isinstance(args, list) or not all(isinstance(a, str) and ARG_OK.match(a) for a in args):
        raise ValueError("argumentos inválidos (uma palavra por argumento, sem espaços nem barras)")
    env = corpo.get("env") or {}
    if not isinstance(env, dict):
        raise ValueError("env inválido")
    for k, v in env.items():
        if k not in ENV_OK or not isinstance(v, str):
            raise ValueError("variável não permitida: %r" % k)
        if ENV_OK[k] is None:
            json.loads(v)
        elif not ENV_OK[k].match(v):
            raise ValueError("valor inválido para %s" % k)
    return script, args, {k: v for k, v in env.items() if v}


def enfileirar(script, args, env, titulo=""):
    with _trava:
        rid = _rodadas["proximo"]
        _rodadas["proximo"] += 1
        nome = "%s-%03d-%s" % (time.strftime("%Y%m%d-%H%M%S"), rid, script)
        r = {"id": rid, "script": script, "args": args, "env": env, "titulo": titulo or (script + " " + " ".join(args)).strip(),
             "estado": "fila", "criada": time.time(), "inicio": None, "fim": None, "codigo": None, "log": "painel/" + nome + ".log"}
        _rodadas["lista"].append(r)
        gravar_rodadas()
    _acorda.set()
    return r


def ultimas_linhas(caminho, n=4):
    try:
        with open(caminho, "rb") as f:
            f.seek(0, 2)
            tam = f.tell()
            f.seek(max(0, tam - 6000))
            texto = f.read().decode("utf-8", "replace")
    except OSError:
        return [], None
    linhas = [l for l in re.split(r"\r?\n|\r", texto) if l.strip()]
    eta = None
    for l in reversed(linhas):
        m = re.search(r"faltam ~(\d+) s", l)
        if m:
            eta = int(m.group(1))
            break
    return linhas[-n:], eta


def executar(r):
    os.makedirs(PAINEL, exist_ok=True)
    script = os.path.join(AQUI, r["script"] + (".mjs" if r["script"].endswith("-pagina") else ".py"))
    cmd = (["node", script] if script.endswith(".mjs") else [sys.executable, script]) + r["args"]
    env = dict(os.environ, PYTHONPATH=LIB + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else ""),
               PYTHONUNBUFFERED="1", **r["env"])
    log = os.path.join(V2, r["log"])
    with open(log, "w") as f:
        f.write("$ " + " ".join(("%s=%s " % (k, v)) for k, v in r["env"].items()) + " ".join(cmd) + "\n")
        f.flush()
        try:
            p = subprocess.Popen(cmd, cwd=RAIZ, env=env, stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
        except OSError as e:
            f.write("não iniciou: %s\n" % e)
            return 127
        _processo["p"], _processo["id"] = p, r["id"]
        codigo = p.wait()
        _processo["p"], _processo["id"] = None, None
        return codigo


def laco_rodadas():
    while True:
        _acorda.wait(5)
        _acorda.clear()
        while True:
            with _trava:
                prox = next((r for r in _rodadas["lista"] if r["estado"] == "fila"), None)
                if prox:
                    prox["estado"], prox["inicio"] = "rodando", time.time()
                    gravar_rodadas()
            if not prox:
                break
            codigo = executar(prox)
            with _trava:
                prox["fim"], prox["codigo"] = time.time(), codigo
                if prox["estado"] == "rodando":
                    prox["estado"] = "ok" if codigo == 0 else "erro"
                gravar_rodadas()
            if _mapas["pronto"] or _mapas["calculando"]:
                recalcular_mapas()


def parar(rid):
    with _trava:
        r = next((x for x in _rodadas["lista"] if x["id"] == rid), None)
        if not r:
            raise ValueError("rodada %s não existe" % rid)
        if r["estado"] == "fila":
            r["estado"], r["fim"] = "interrompida", time.time()
            gravar_rodadas()
            return "retirada da fila"
        if r["estado"] != "rodando" or _processo["id"] != rid or not _processo["p"]:
            raise ValueError("a rodada %s não está rodando" % rid)
        r["estado"] = "interrompida"
        gravar_rodadas()
        p = _processo["p"]
    # SIGTERM ao grupo inteiro (o script e os processos do ProcessPoolExecutor; com SIGINT o pool fica pendurado).
    # A gravação é atômica e o manifesto é regravado a cada lote, então a próxima rodada continua de onde parou (T-C4).
    try:
        os.killpg(os.getpgid(p.pid), signal.SIGTERM)
    except OSError:
        pass

    def forcar():
        time.sleep(15)
        if p.poll() is None:
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            except OSError:
                pass
    threading.Thread(target=forcar, daemon=True).start()
    return "interrompida (SIGTERM ao grupo de processos; SIGKILL em 15 s se não parar)"


def rodadas():
    with _trava:
        lista = [dict(r) for r in _rodadas["lista"]]
    for r in lista:
        fim, eta = ultimas_linhas(os.path.join(V2, r["log"]))
        r["fim_log"], r["eta"] = fim, (eta if r["estado"] == "rodando" else None)
    lista.sort(key=lambda r: -r["id"])
    return {"lista": lista, "rodando": _processo["id"], "hora": time.time()}


def log(rid, de):
    with _trava:
        r = next((x for x in _rodadas["lista"] if x["id"] == rid), None)
    if not r:
        raise ValueError("rodada %s não existe" % rid)
    caminho = os.path.join(V2, r["log"])
    try:
        with open(caminho, "rb") as f:
            f.seek(0, 2)
            tam = f.tell()
            de = max(0, min(de, tam))
            if tam - de > 400000:
                de = tam - 400000
            f.seek(de)
            texto = f.read().decode("utf-8", "replace")
    except OSError:
        return {"texto": "", "ate": 0, "estado": r["estado"]}
    return {"texto": texto, "ate": de + len(texto.encode("utf-8")), "estado": r["estado"], "tamanho": tam}


# ------------------------------------------------------------------ servidor
class Manipulador(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        linha = str(args[0]) if args else ""
        if "/api/" in linha and "/api/rodadas" not in linha and "/api/log" not in linha:
            super().log_message(fmt, *args)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        if self.path.split("?")[0] == CAMINHO_ANOTACOES:
            self.send_header("X-Grava-Anotacoes", "1")
        super().end_headers()

    def responder(self, obj, codigo=200):
        corpo = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def corpo_json(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n)) if n else {}

    def do_HEAD(self):
        if self.path.split("?")[0] == CAMINHO_ANOTACOES and not os.path.exists(ANOTACOES):
            self.send_response(204)
            self.end_headers()
            return
        super().do_HEAD()

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if not u.path.startswith("/api/"):
            return super().do_GET()
        q = urllib.parse.parse_qs(u.query)
        try:
            if u.path == "/api/versoes":
                return self.responder(versoes())
            if u.path == "/api/mapas":
                if not _mapas["pronto"] and not _mapas["calculando"] and not _mapas["erro"]:
                    recalcular_mapas()
                return self.responder({k: v for k, v in _mapas.items() if k != "dados"} | {"mapas": _mapas["dados"] if _mapas["pronto"] else None})
            if u.path == "/api/rodadas":
                return self.responder(rodadas())
            if u.path == "/api/log":
                return self.responder(log(int(q.get("id", ["0"])[0]), int(q.get("de", ["0"])[0])))
            if u.path == "/api/estado":
                return self.responder({"painel": True, "rodando": _processo["id"], "mapas_pronto": _mapas["pronto"], "hora": time.time()})
            self.responder({"erro": "rota desconhecida"}, 404)
        except (ValueError, OSError) as e:
            self.responder({"erro": str(e)}, 400)
        except SystemExit as e:
            self.responder({"erro": str(e)}, 400)

    def do_POST(self):
        caminho = self.path.split("?")[0]
        try:
            corpo = self.corpo_json()
            if caminho == CAMINHO_ANOTACOES:
                notas = corpo["anotacoes"]
                if not (isinstance(notas, list) and all(n.get("tipo") in TIPOS_NOTA and "ano" in n and "mapa" in n for n in notas)):
                    raise ValueError("anotações inválidas")
                gravar_json(ANOTACOES, corpo, indent=1)
                return self.responder({"ok": True})
            if caminho == CAMINHO_EDICOES:
                novas = corpo["edicoes"]
                if not (isinstance(novas, list) and novas and all(e.get("tipo") in TIPOS_EDICAO for e in novas)):
                    raise ValueError("edições inválidas")
                n, total = gravar_edicoes(novas)
                return self.responder({"ok": True, "aplicadas": n, "total": total})
            if caminho == "/api/aprovar":
                et = cache.Etapa(corpo["etapa"])
                trocados = et.aprovar(corpo["variante"])
                recalcular_mapas()
                return self.responder({"ok": True, "apontadores_trocados": trocados, "aprovada": et.m["aprovada"], "anterior": et.m["anterior"]})
            if caminho == "/api/apagar-variante":
                if corpo["etapa"] not in cache.ETAPAS_LOJA or not re.match(r"^[A-Za-z0-9_\-]+$", corpo["variante"]):
                    raise ValueError("etapa ou variante inválida")
                r = subprocess.run([sys.executable, os.path.join(AQUI, "limpar_cache.py"), "--variante", corpo["etapa"], corpo["variante"], "--apagar"],
                                   cwd=RAIZ, env=dict(os.environ, PYTHONPATH=LIB), capture_output=True, text=True, timeout=600)
                return self.responder({"ok": r.returncode == 0, "saida": (r.stdout + r.stderr).strip()[-2000:]}, 200 if r.returncode == 0 else 400)
            if caminho == "/api/mapas/recalcular":
                recalcular_mapas()
                return self.responder({"ok": True})
            if caminho == "/api/rodar":
                script, args, env = validar_rodada(corpo)
                return self.responder({"ok": True, "rodada": enfileirar(script, args, env, corpo.get("titulo", ""))})
            if caminho == "/api/parar":
                return self.responder({"ok": True, "mensagem": parar(int(corpo["id"]))})
            self.responder({"erro": "rota desconhecida"}, 404)
        except (KeyError, TypeError, ValueError, OSError, subprocess.TimeoutExpired) as e:
            self.responder({"erro": "%s: %s" % (type(e).__name__, e)}, 400)
        except SystemExit as e:          # cache.Etapa recusa com SystemExit (variante inexistente, etc.)
            self.responder({"erro": str(e)}, 400)


if __name__ == "__main__":
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    os.makedirs(PAINEL, exist_ok=True)
    carregar_rodadas()
    threading.Thread(target=laco_rodadas, daemon=True).start()
    servidor = http.server.ThreadingHTTPServer(("127.0.0.1", porta), functools.partial(Manipulador, directory=RAIZ))
    print("http://localhost:%d/scripts/mapa-geral/painel.html" % porta)
    print("anotações em %s · edições em %s · rodadas em %s" % (ANOTACOES, construir.EDICOES, PAINEL))
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
