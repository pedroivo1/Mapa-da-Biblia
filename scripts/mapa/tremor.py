import math, hashlib

def _h(chave):
    # número determinístico em [-1, 1] a partir da chave (o mesmo em qualquer execução)
    d = hashlib.md5(repr(chave).encode()).digest()
    return (int.from_bytes(d[:4], "big") / 2147483647.5) - 1.0

def tremer(pts, passo=0.35, amp=0.045):
    """Borda só com linhas retas e um 'tremor': cada lado vira uma poligonal de segmentos retos curtos,
    deslocados de forma determinística. O mesmo lado (em qualquer sentido) gera os mesmos pontos,
    então vizinhos que dividem a borda ficam coladinhos."""
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
        nx, ny = -dy / L, dx / L
        meio = []
        for j in range(1, k):
            t = j / k
            off = _h((p, q, j)) * amp
            meio.append((p[0] + dx * t + nx * off, p[1] + dy * t + ny * off))
        saida.extend(reversed(meio) if inv else meio)
    return saida
