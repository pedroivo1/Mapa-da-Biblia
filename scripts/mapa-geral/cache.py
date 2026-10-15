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


def precisa(man, ident, ch, caminho):
    """True se o item precisa ser recalculado: chave diferente, artefato ausente ou conteúdo diferente do manifesto."""
    e = man.get(ident)
    if not e or e.get("chave") != ch or not os.path.exists(caminho):
        return True
    return hash_arquivo(caminho) != e.get("hash_saida")


def atomico(caminho):
    """Caminho temporário para gravar; depois chamar os.replace(tmp, caminho). Mantém a extensão (cv2/np precisam)."""
    base, ext = os.path.splitext(caminho)
    return base + ".tmp" + ext


def tmp_pendentes(etapa):
    return [f for f in os.listdir(pasta(etapa)) if ".tmp" in f]
