# Cache por etapa do mapa geral v2 (docs/mapa-geral-incremental.md). Usado por rotular.py (E4a–E4e) e
# vetorizar.py (E5).
#
# Cada etapa é uma função pura (entradas, parâmetros, VERSAO) -> artefato. A chave de um item (um mapa distinto) é
#   sha1(json.dumps({"versao", "params", "entradas": [hash do conteúdo de cada entrada]}, sort_keys=True))
# e fica no manifesto da etapa, .cache/v2/<etapa>/manifesto.json: {id: {"chave", "hash_saida", "segundos"}}.
# Se a chave guardada é a mesma e o artefato existe com o mesmo hash de conteúdo, o item não é recalculado.
# O hash de saída é do CONTEÚDO (arrays de um .npz, bytes de um PNG, JSON canônico), não da data do arquivo: se uma
# etapa recalcula e o resultado sai igual, as seguintes não são invalidadas (corte antecipado).
# Gravação atômica (arquivo .tmp -> os.replace) e manifesto regravado depois de cada lote: uma rodada interrompida
# continua de onde parou.
import hashlib, io, json, os, zipfile

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
CACHE = os.environ.get("MAPA_GERAL_CACHE") or os.path.join(AQUI, ".cache")
V2 = os.path.join(CACHE, "v2")

_memo = {}


def sha1(b):
    return hashlib.sha1(b).hexdigest()


def chave(versao, params, entradas):
    return sha1(json.dumps({"versao": versao, "params": params, "entradas": entradas}, sort_keys=True,
                           ensure_ascii=False).encode())


def hash_npz(caminho):
    """Hash dos arrays de um .npz (nome, dtype, forma e bytes), independente da data gravada no zip."""
    h = hashlib.sha1()
    with zipfile.ZipFile(caminho) as z:
        for nome in sorted(z.namelist()):
            a = np.load(io.BytesIO(z.read(nome)), allow_pickle=False)
            h.update(nome.encode())
            h.update(str(a.dtype).encode())
            h.update(str(a.shape).encode())
            h.update(np.ascontiguousarray(a).tobytes())
    return h.hexdigest()


def hash_arquivo(caminho):
    """Hash do conteúdo, com memória por (caminho, mtime, tamanho) para não reler arquivos grandes."""
    st = os.stat(caminho)
    k = (caminho, st.st_mtime_ns, st.st_size)
    if k in _memo:
        return _memo[k]
    if caminho.endswith(".npz"):
        h = hash_npz(caminho)
    else:
        with open(caminho, "rb") as f:
            h = sha1(f.read())
    _memo[k] = h
    return h


def hash_obj(obj):
    """Hash de um objeto JSON (parâmetros de calibração de um mapa, por exemplo)."""
    return sha1(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode())


def pasta(etapa):
    p = os.path.join(V2, etapa)
    os.makedirs(p, exist_ok=True)
    return p


def manifesto(etapa):
    arq = os.path.join(pasta(etapa), "manifesto.json")
    if os.path.exists(arq):
        return json.load(open(arq))
    return {}


def gravar_manifesto(etapa, m):
    arq = os.path.join(pasta(etapa), "manifesto.json")
    tmp = arq + ".tmp"
    json.dump(m, open(tmp, "w"), sort_keys=True)
    os.replace(tmp, arq)


def assinatura(*caminhos):
    """(mtime em ns, tamanho) de cada arquivo: se não mudou desde a gravação, o hash do manifesto vale sem reler."""
    out = []
    for c in caminhos:
        st = os.stat(c)
        out.append([st.st_mtime_ns, st.st_size])
    return out


def entrada(ch, hash_saida, segundos, *caminhos):
    return {"chave": ch, "hash_saida": hash_saida, "segundos": segundos, "stat": assinatura(*caminhos)}


def hash_conhecido(e, *caminhos):
    """O hash de saída do manifesto, se os arquivos estão como foram gravados (mesmo mtime e tamanho); senão None.
    (O T-C1 confere, recalculando do zero, que o conteúdo bate.)"""
    if not e or "stat" not in e:
        return None
    try:
        return e["hash_saida"] if assinatura(*caminhos) == e["stat"] else None
    except FileNotFoundError:
        return None


def precisa(man, ident, ch, caminho, hash_fn=None):
    """True se o item precisa ser recalculado: chave diferente, artefato ausente ou conteúdo diferente do manifesto."""
    e = man.get(ident)
    if not e or e.get("chave") != ch or not os.path.exists(caminho):
        return True
    if hash_conhecido(e, caminho) is not None:
        return False
    return (hash_fn or hash_arquivo)(caminho) != e.get("hash_saida")


def hash_de(man, ident, caminho):
    """Hash do conteúdo de um artefato do manifesto, sem reler se a assinatura bate."""
    return hash_conhecido(man.get(ident), caminho) or hash_arquivo(caminho)


def atomico(caminho):
    """Caminho temporário para gravar; depois chamar os.replace(tmp, caminho). Mantém a extensão (cv2/np precisam)."""
    base, ext = os.path.splitext(caminho)
    return base + ".tmp" + ext


def tmp_pendentes(etapa):
    return [f for f in os.listdir(pasta(etapa)) if ".tmp" in f]


# ------------------------------------------------------------------ loja por chave e variantes (formato 2)
# Cada resultado de uma etapa versionada (E3, E4e, E5, E6, E7) fica num arquivo com o nome da sua chave:
#   .cache/v2/obj/<etapa>/<chave><ext>             (imutável: a mesma chave é sempre o mesmo conteúdo)
# Os arquivos "públicos" que as outras etapas, os testes e o visualizador leem são só APONTADORES (links
# simbólicos relativos) para os objetos da variante APROVADA:
#   e3: calibracao.json    e4e: rotulos/<id>.png e rotulos/<id>.json    e5: vetores/<id>.json    e6: entidades.json
#   e7a: textos/<id>.json (etiquetas lidas de cada mapa)    e7u: vetores-e7/<id>.json (vetores da E5 com as uniões
#   da E7)    e7: nomes-lidos.json
# O manifesto da etapa (formato 2) guarda o histórico:
#   {"formato": 2, "aprovada": "<variante>", "anterior": "<variante>|null",
#    "variantes": {"<nome>": {"params": {...}, "criada": "...", "testes": {...}, "itens": {id: entrada}}}}
#   entrada = {"chave", "hash_saida", "segundos", "stat"}
# Regras: um experimento grava com a própria variante e nunca mexe nos apontadores; só `aprovar` troca os
# apontadores (instantâneo, sem recalcular). Uma variante nova com a mesma chave de um objeto já existente (voltar a
# uma lógica antiga) reaproveita o objeto. A chave vem da lógica (VERSAO só muda quando o código muda de um jeito que
# os parâmetros não descrevem) e dos parâmetros reais.
import datetime

OBJ = os.path.join(V2, "obj")
PUBLICOS = {"e3": [("", ".json")], "e4e": [("rotulos", ".png"), ("rotulos", ".json")], "e5": [("vetores", ".json")],
            "e6": [("", ".json")], "e7a": [("textos", ".json")], "e7u": [("vetores-e7", ".json")],
            "e7": [("", ".json")]}
NOME_PUBLICO_UNICO = {"e3": "calibracao", "e6": "entidades", "e7": "nomes-lidos"}
PASTA_MANIFESTO = {"e3": "e3", "e4e": "e4/e", "e5": "e5", "e6": "e6", "e7a": "e7/a", "e7u": "e7/u", "e7": "e7"}
ETAPAS_LOJA = ("e3", "e4e", "e5", "e6", "e7a", "e7u", "e7")


def calibracao():
    """Caminho da calibração (E3) a ler: o objeto da variante MAPA_GERAL_EXP, se a E3 a tem; senão o apontador
    calibracao.json (a aprovada, ou o arquivo antigo, de antes da loja)."""
    return Etapa("e3").caminho("calibracao", ".json")


def exp_atual():
    """Variante pedida pelo ambiente (MAPA_GERAL_EXP) ou None (= a aprovada)."""
    return os.environ.get("MAPA_GERAL_EXP") or None


class Etapa:
    def __init__(self, nome):
        self.nome = nome
        self.arq = os.path.join(pasta(PASTA_MANIFESTO[nome]), "manifesto.json")
        self.m = json.load(open(self.arq)) if os.path.exists(self.arq) else {}
        if self.m.get("formato") != 2:
            self.m = {"formato": 2, "aprovada": None, "anterior": None, "variantes": {}}
        os.makedirs(os.path.join(OBJ, nome), exist_ok=True)

    # --- variantes
    def variante(self, pedida=None):
        return pedida or exp_atual() or self.m["aprovada"]

    def garantir(self, nome, params):
        v = self.m["variantes"].get(nome)
        if v is None:
            v = self.m["variantes"][nome] = {"params": params, "criada": datetime.datetime.now().isoformat(timespec="seconds"),
                                             "testes": {}, "itens": {}}
        elif v["params"] != params:
            raise SystemExit(f"{self.nome}: a variante '{nome}' foi criada com outros parâmetros; use outro nome "
                             f"(--variante) para um experimento. Existentes: {sorted(self.m['variantes'])}")
        return v

    def itens(self, nome):
        return self.m["variantes"].get(nome, {}).get("itens", {})

    def gravar(self):
        tmp = self.arq + ".tmp"
        json.dump(self.m, open(tmp, "w"), sort_keys=True)
        os.replace(tmp, self.arq)

    # --- objetos
    def obj(self, ch, ext):
        return os.path.join(OBJ, self.nome, ch + ext)

    def exts(self):
        return [e for _, e in PUBLICOS[self.nome]]

    def existe(self, ch):
        return all(os.path.exists(self.obj(ch, e)) for e in self.exts())

    def procurar(self, ident, ch):
        """Entrada já registrada (em qualquer variante) para este item com esta chave e o objeto presente."""
        for v in self.m["variantes"].values():
            e = v["itens"].get(ident)
            if e and e["chave"] == ch and self.existe(ch):
                return e
        return None

    def publico(self, ident, ext):
        for d, e in PUBLICOS[self.nome]:
            if e == ext:
                nome = NOME_PUBLICO_UNICO.get(self.nome, ident)
                return os.path.join(V2, d, nome + ext) if d else os.path.join(V2, nome + ext)

    def caminho(self, ident, ext, variante=None):
        """Arquivo a ler para um item: o objeto da variante pedida (argumento ou MAPA_GERAL_EXP), se ela tem o item;
        senão o apontador público (a aprovada)."""
        v = variante or exp_atual()
        if v:
            e = self.itens(v).get(ident)
            if e:
                return self.obj(e["chave"], ext)
        return self.publico(ident, ext)

    # --- aprovação (troca de apontadores)
    def aprovar(self, nome, exigir_todos=None):
        v = self.m["variantes"].get(nome)
        if v is None:
            raise SystemExit(f"{self.nome}: variante '{nome}' não existe")
        if exigir_todos is not None:
            faltam = [i for i in exigir_todos if i not in v["itens"]]
            if faltam:
                raise SystemExit(f"{self.nome}: a variante '{nome}' não tem {len(faltam)} itens (ex.: {faltam[:5]})")
        trocados = 0
        for ident, e in v["itens"].items():
            for ext in self.exts():
                alvo = self.obj(e["chave"], ext)
                pub = self.publico(ident, ext)
                os.makedirs(os.path.dirname(pub), exist_ok=True)
                rel = os.path.relpath(alvo, os.path.dirname(pub))
                if os.path.islink(pub) and os.readlink(pub) == rel:
                    continue
                tmp = pub + ".lnk.tmp"
                if os.path.lexists(tmp):
                    os.remove(tmp)
                os.symlink(rel, tmp)
                os.replace(tmp, pub)
                trocados += 1
        if self.m["aprovada"] != nome:
            self.m["anterior"] = self.m["aprovada"]
            self.m["aprovada"] = nome
        self.gravar()
        return trocados


def adotar_publicos(nome_etapa, variante, params, entradas_por_item):
    """Migração: move os arquivos públicos atuais (já calculados com a lógica aprovada) para a loja, com a chave de
    cada item, e troca-os por apontadores. entradas_por_item: {id: entrada do manifesto antigo}."""
    et = Etapa(nome_etapa)
    v = et.garantir(variante, params)
    for ident, e in entradas_por_item.items():
        for ext in et.exts():
            pub = et.publico(ident, ext)
            alvo = et.obj(e["chave"], ext)
            if os.path.islink(pub):
                continue
            if os.path.exists(pub) and not os.path.exists(alvo):
                os.replace(pub, alvo)
        v["itens"][ident] = {k: e[k] for k in ("chave", "hash_saida", "segundos") if k in e}
    et.gravar()
    et.aprovar(variante)
    return et


if __name__ == "__main__":
    # python3 cache.py aprovar <etapa> <variante>   |   python3 cache.py listar <etapa>
    import sys
    acao, et_nome = sys.argv[1], sys.argv[2]
    et = Etapa(et_nome)
    if acao == "aprovar":
        print("apontadores trocados:", et.aprovar(sys.argv[3]))
    elif acao == "listar":
        for n, v in et.m["variantes"].items():
            marca = " (aprovada)" if n == et.m["aprovada"] else (" (anterior)" if n == et.m["anterior"] else "")
            print(f"{n}{marca}: {len(v['itens'])} itens, criada {v['criada']}, params {json.dumps(v['params'], ensure_ascii=False)[:200]}, testes {v['testes']}")
