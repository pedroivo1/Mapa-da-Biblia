import math, hashlib

def _h(chave):
    # número determinístico em [-1, 1] a partir da chave (o mesmo em qualquer execução)
    d = hashlib.md5(repr(chave).encode()).digest()
    return (int.from_bytes(d[:4], "big") / 2147483647.5) - 1.0

def chave_lado(a, b):
    """Chave canônica de um lado (a mesma nos dois sentidos), com a mesma precisão que tremer() usa."""
    a = (round(a[0], 4), round(a[1], 4))
    b = (round(b[0], 4), round(b[1], 4))
    return (b, a) if a > b else (a, b)


def tremer(pts, passo=0.35, amp=0.045, sem_tremor=None):
    """Borda só com linhas retas e um 'tremor': cada lado vira uma poligonal de segmentos retos curtos,
    deslocados de forma determinística. O mesmo lado (em qualquer sentido) gera os mesmos pontos,
    então vizinhos que dividem a borda ficam coladinhos. sem_tremor: conjunto de chave_lado() que ficam retos
    (onde o tremor faria as duas margens de um canal fino se cruzarem)."""
    n = len(pts)
    saida = []
    for i in range(n):
        a = (round(pts[i][0], 4), round(pts[i][1], 4))
        b = (round(pts[(i + 1) % n][0], 4), round(pts[(i + 1) % n][1], 4))
        saida.append(a)
        inv = a > b
        p, q = (b, a) if inv else (a, b)
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy)
        if L < 1e-9: continue
        k = max(1, int(L / passo))
        if k < 2: continue
        reto = bool(sem_tremor) and (p, q) in sem_tremor
        nx, ny = -dy / L, dx / L
        meio = []
        for j in range(1, k):
            t = j / k
            off = 0.0 if reto else _h((p, q, j)) * amp      # lado reto: mesmos pontos, sem deslocamento
            meio.append((p[0] + dx * t + nx * off, p[1] + dy * t + ny * off))
        saida.extend(reversed(meio) if inv else meio)
    return saida
