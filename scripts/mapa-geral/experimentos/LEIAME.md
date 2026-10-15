# Experimentos do mapa geral v2

Scripts de diagnóstico usados durante as etapas E3 e E4 (antes ficavam em `.cache/v2/`, que deve ser descartável).
Não fazem parte do caminho dos dados; alguns dependem de versões antigas de `rotular.py`.

| Script | Para quê |
|---|---|
| `mk_casos.py` | Gera `scripts/mapa-geral/casos.json` (pontos escolhidos no quadro, convertidos pela calibração da E3) |
| `marcar.py` | Desenha pontos lon/lat sobre o quadro de um ano |
| `exp_proj.py`, `aniso.py` | Comparação Mercator × Miller × outras; escala vertical separada (E3) |
| `tiles.py`, `terco.py`, `fora.py` | Resíduo e deslocamento local da calibração por região do quadro (E3, T3.6/T3.7) |
| `diag_mar.py` | Mudanças da máscara de mar entre mapas (trechos de enquadramento) |
| `exp_flat.py` | Primeiro teste das zonas planas (E4) |
| `pares_stats.py`, `dep.py`, `checar.py` | Estatísticas e conferência dos pares de mesma cor (E4, conjunto de `pares.json`) |
