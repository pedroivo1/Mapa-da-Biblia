#!/usr/bin/env python3
# Etapa 3b do mapa geral: lê o nome de cada estado no próprio quadro (OCR com tesseract, só inglês).
# Dois caminhos, porque o vídeo escreve o nome de duas formas:
#   1) texto branco DENTRO da mancha: aparece como "buracos" na máscara da cor do estado;
#   2) texto preto FORA/ao lado da mancha: palavras do OCR do quadro inteiro, associadas pela proximidade.
import os, re, subprocess, tempfile
import cv2
import numpy as np

ALFABETO = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'.- "


def _tesseract(png, psm="6"):
    out = subprocess.run(
        ["tesseract", png, "stdout", "--psm", psm, "-c", "tessedit_char_whitelist=" + ALFABETO],
        capture_output=True, text=True, timeout=30).stdout
    return " ".join(out.split())


def _limpo(t):
    t = re.sub(r"[^A-Za-z'.\- ]", "", t).strip(" .-'")
    return t if len(re.sub(r"[^A-Za-z]", "", t)) >= 3 else ""


def nome_por_buracos(img, estado):
    """Texto branco dentro da mancha: pixels não-cor dentro do contorno preenchido."""
    x, y, w, h = estado["bbox"]
    pad = 3
    x0, y0 = max(0, x - pad), max(0, y - pad)
    crop = img[y0:y + h + pad, x0:x + w + pad]
    cor = np.array(estado["cor"][::-1], np.int32)             # RGB -> BGR
    dist = np.abs(crop.astype(np.int32) - cor[None, None, :]).sum(axis=2)
    dentro = (dist < 60).astype(np.uint8) * 255
    cont, _ = cv2.findContours(cv2.morphologyEx(dentro, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)),
                               cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cont: return ""
    preench = np.zeros_like(dentro)
    cv2.drawContours(preench, cont, -1, 255, -1)
    minimo = crop.min(axis=2)
    maximo = crop.max(axis=2)
    claro = ((preench > 0) & (minimo > 205)).astype(np.uint8) * 255      # texto branco
    escuro = ((preench > 0) & (maximo < 90)).astype(np.uint8) * 255      # texto preto
    texto = claro if claro.sum() >= escuro.sum() else escuro
    # tira respingos (bordas suavizadas) e mantém só o que parece letra
    n, rot, st, _ = cv2.connectedComponentsWithStats(texto, connectivity=8)
    limpo = np.zeros_like(texto)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] >= 4 and st[i, cv2.CC_STAT_HEIGHT] >= 4:
            limpo[rot == i] = 255
    texto = limpo
    if texto.sum() < 255 * 24: return ""
    im = cv2.resize(255 - texto, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    im = cv2.copyMakeBorder(im, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        cv2.imwrite(f.name, im)
        try: return _limpo(_tesseract(f.name, "6"))
        finally: os.unlink(f.name)


def composto(img, estados):
    """Imagem para o OCR: fundo branco, texto escuro em preto e texto BRANCO dentro das manchas também em preto."""
    h, w = img.shape[:2]
    escuro = img.max(axis=2) < 110
    texto = escuro.copy()
    branco = img.min(axis=2) > 215
    for e in estados:
        x, y, bw, bh = e["bbox"]
        x0, y0 = max(0, x - 3), max(0, y - 3)
        crop = img[y0:y + bh + 3, x0:x + bw + 3]
        cor = np.array(e["cor"][::-1], np.int32)
        dist = np.abs(crop.astype(np.int32) - cor[None, None, :]).sum(axis=2)
        dentro = (dist < 60).astype(np.uint8) * 255
        cont, _ = cv2.findContours(cv2.morphologyEx(dentro, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)),
                                   cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cont: continue
        pre = np.zeros_like(dentro)
        cv2.drawContours(pre, cont, -1, 255, -1)
        sub = texto[y0:y + bh + 3, x0:x + bw + 3]
        limiar = max(int(cor.min()) + 45, 170)            # texto branco é bem mais claro que a cor do estado
        sub |= (pre > 0) & (crop.min(axis=2) > limiar)
    return np.where(texto, 0, 255).astype(np.uint8)


def palavras_do_quadro(img, estados):
    """Palavras do quadro inteiro: [(x, y, w, h, texto)] em pixels do quadro de 1280 px."""
    g = composto(img, estados)
    g = cv2.resize(g, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        cv2.imwrite(f.name, g)
        try:
            out = subprocess.run(["tesseract", f.name, "stdout", "--psm", "11", "tsv"],
                                 capture_output=True, text=True, timeout=180).stdout
        finally:
            os.unlink(f.name)
    pal = []
    for linha in out.splitlines()[1:]:
        c = linha.split("\t")
        if len(c) < 12 or not c[11].strip(): continue
        try: conf = float(c[10])
        except ValueError: continue
        t = _limpo(c[11])
        if conf < 45 or not t: continue
        x, y, w, h = (float(c[i]) / 2.5 for i in (6, 7, 8, 9))
        pal.append((x, y, w, h, t))
    return pal


def nomear(img, estados):
    """Preenche estado['nome_en'] ('' se não achar): as palavras vão ao estado cuja mancha está mais perto e
    palavras vizinhas na mesma linha se juntam (ex.: "Indus" + "Valley")."""
    pal = sorted(palavras_do_quadro(img, estados), key=lambda p: (round(p[1] / 8), p[0]))
    por_estado = {}
    for (x, y, w, h, t) in pal:
        cx, cy = x + w / 2, y + h / 2
        melhor, md = None, 1e9
        for i, e in enumerate(estados):
            bx, by, bw, bh = e["bbox"]
            dx = max(bx - cx, 0, cx - (bx + bw)); dy = max(by - cy, 0, cy - (by + bh))
            d = (dx * dx + dy * dy) ** 0.5
            if d < md: melhor, md = i, d
        if melhor is not None and md <= 26:
            por_estado.setdefault(melhor, []).append(t)
    for i, e in enumerate(estados):
        e["nome_en"] = " ".join(por_estado.get(i, []))
    return estados
