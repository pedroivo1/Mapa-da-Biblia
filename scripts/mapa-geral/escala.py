# Fator de escala do pipeline do mapa geral v2 (docs/mapa-geral-plano-2.md §11, 2026-10-16).
# O pipeline foi escrito para quadros de 1920×960. Com a fonte em 8K (vídeos/*8k.mp4) a geometria (E3 calibração,
# E4 rótulos, E5 vetores) pode rodar sobre quadros 3840×1920 (E = 2) e o OCR das etiquetas (E7a) sobre os quadros
# 7680×3840 (E_OCR = 4). Toda constante em pixels dos scripts passa por aqui:
#   px(v)    comprimento (raio, distância, janela, largura de fronteira)          × E
#   area(v)  área ou contagem de pixels de uma região / de um anel                × E²
#   it(n)    iterações de dilatação/erosão com núcleo 3×3 (n·E iterações = quadrado de 2nE+1: exato)
#   impar(v) tamanho ímpar de núcleo (medianBlur, abertura)                       v·E arredondado a ímpar
# Limiares de cor e valores em graus não mudam. Com E = 1 cada função devolve o valor recebido, sem conversão de
# tipo, e params() é vazio: as chaves de cache de hoje não mudam (testar.py cache, T-C1/T-C2, é a prova).
# Ambiente: MAPA_GERAL_ESCALA (padrão 1), MAPA_GERAL_ESCALA_OCR (padrão = ESCALA; 4 lê os recortes do 8K).
import os

E = int(os.environ.get("MAPA_GERAL_ESCALA", "1"))
E_OCR = int(os.environ.get("MAPA_GERAL_ESCALA_OCR", str(E)))
if E < 1 or E_OCR < E or E_OCR % E:
    raise SystemExit(f"escala: MAPA_GERAL_ESCALA={E} e MAPA_GERAL_ESCALA_OCR={E_OCR} inválidos (E >= 1, E_OCR múltiplo de E)")
W0, H0 = 1920, 960              # quadro de referência (a E2 detecta ano e mudança de mapa sempre nele)
W, H = W0 * E, H0 * E           # quadro da geometria


def px(v):
    return v * E


def area(v):
    return v * E * E


def it(n):
    return n * E


def impar(v):
    return v if E == 1 else (v * E) | 1


def nome_pasta(e):
    """Pasta dos PNGs de cada escala em .cache/v2/: mapas (1920), mapas-4k (3840), mapas-8k (7680)."""
    return "mapas" if e == 1 else f"mapas-{W0 * e // 1000}k"


def pasta_mapas():
    return nome_pasta(E)


def pasta_ocr():
    return nome_pasta(E_OCR)


def params():
    """Entra nos parâmetros (e nas chaves) só quando a escala não é a de referência."""
    return {} if E == 1 else {"ESCALA": E}


def params_ocr():
    return {} if E_OCR == 1 else {"ESCALA_OCR": E_OCR}
