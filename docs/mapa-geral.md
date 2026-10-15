# Mapa geral: como foi feito

A página `frontend/mapa-geral/` mostra o mundo todo, ano a ano, de 2500 a.C. em diante, com uma linha do tempo
(controle deslizante, anterior/próximo e reprodução). As formas dos povos foram **lidas de vídeos de história mundial**
e depois recalculadas sobre a costa do projeto. Este documento explica a origem dos dados, o caminho que eles fazem
até o site, os limites do resultado e como regenerar tudo.

Estado: **primeira etapa (Antiguidade) entregue.** Os estados do período bíblico, de 2500 a.C. a 100 d.C., têm nome e cor
por regras. Do medieval em diante as formas existem, mas **ainda sem nome** (aparecem como manchas de cor, "Estado sem
nome identificado"). Os 27 mapas por história continuam como estavam; o mapa geral ainda não os substitui.

## 1. Fontes

Os vídeos são de terceiros e servem **só de referência** (formas e nomes próprios). Não são redistribuídos: a pasta
`vídeos/` está fora do git (`vídeos/.gitignore` com `*`) e nenhum quadro é publicado. Links em `videos.txt`.

| Vídeo | Resolução | Duração | Papel |
|---|---|---|---|
| "Every Year" (`hzWwp9JM7Hw`) | 1920×960 | 17 min 24 s | Fonte principal das formas: mapa claro, estados em cores chapadas, ano no rodapé, começa em 2500 a.C. |
| "Every Year (3400 BCE – 2026)" (`4BzUDJDiE8c`) | 1920×1080 | 17 min | Conferência de nomes e do período 3400–2500 a.C. (ainda não usado nos dados) |
| "World history 3500 BCE – PRESENT" (`pWP0Z9XLxH8`) | 1920×1080 | 20 min 30 s | Muito denso (rótulos por cima); só contexto |

Costa, lagos e rios: `frontend/mapa/mundo.json` (Natural Earth, domínio público). Povos da Bíblia desenhados à mão:
`frontend/mapa/territorios-<ano>.json` (gerados por `scripts/mapa/territorios.py`).

## 2. Caminho dos dados

Tudo em `scripts/mapa-geral/` (não publicado). Cache em `scripts/mapa-geral/.cache/` (ignorado pelo git).

| Etapa | Script | O que faz |
|---|---|---|
| 1 | `extrair.py` | 1 quadro por segundo (1280 px) e OCR do ano escrito no rodapé (`indice-bruto.json`) |
| 1b | `indexar.py` | Limpa os anos e escolhe os **quadros-chave** (79: a cada 100 anos até 1000 a.C., a cada 50 depois, 100 d.C. em diante a cada 100, mais os anos dos mapas atuais) |
| 2 | `calibrar.py` | Descobre a projeção do quadro: casa a máscara de terra do vídeo com a costa de `mundo.json` (`cv2.matchTemplate`) |
| 3 | `gerar.py` (`segmentar.py`, `nomear.py`) | Separa os estados por cor, tira o contorno (Douglas-Peucker de 1,2 px) e converte para longitude/latitude; OCR dos nomes como dica |
| 4 | `agrupar.py` | Junta estados entre quadros por cor e posição (`entidades.json`). Só diagnóstico: os dados do site não dependem dele |
| 5 | `nomes.json` + `construir.py` | Dá id e nome por **regras** (cor + região + anos), recorta pela terra e grava `frontend/mapa-geral/dados/` |
| (conferência) | `folha.py` | Folha de contato: quadro original ao lado dos estados segmentados, com número e legenda |

### Calibração

O vídeo usa Mercator e muda o enquadramento por trechos (o zoom abre com o tempo). Escala `S` em px/° (quadros de 1280 px):

| Segundos | Anos aproximados | S | X0 | Y0 |
|---|---|---|---|---|
| 2–148 | 2500–1000 a.C. | 11,28 | 2174 | 919 |
| 149–~555 | ~1000 a.C. – ~800 d.C. | 8,40 | 1397 | 577 |
| ~565–~800 | ~800 – ~1500 d.C. | 7,049 | 1045 | 419 |
| ~805–905 | ~1500 – ~1790 d.C. | 4,673 | 248 | 203 |
| ~925–1043 | ~1790 – 2025 d.C. | 3,60 | 16 | 87 |

O escore do casamento fica em 0,72–0,81 (menor nos quadros mais recentes, onde a costa do vídeo é mais simplificada).
Quadros de transição (fade/zoom) caem de escore e `gerar.py` troca para um segundo vizinho.

### Regras de nome (`nomes.json`)

Uma cor se repete em estados e épocas diferentes (o verde de Elão é depois o dos aquemênidas e dos partas), então o nome
não sai da cor sozinha. Cada regra tem `cores` (RGB lidas do vídeo, tolerância L1 `tol`), `caixa` (lon/lat do centro do
estado) e `anos` (`[de, ate]`, a.C. positivo e d.C. negativo). A primeira regra que casa vale. Uma regra nova entra assim:
abra `folha.py <ano>`, leia cor e centro do estado, acrescente a regra e rode `construir.py`. Estados sem regra recebem o
id `x-<cor>-<célula de 10°>` e ficam sem nome.

### Regras de forma (AGENTS.md)

- Só linhas retas, com o **tremor** de `scripts/mapa/tremor.py` (segmentos de ~0,35°, deslocamento de ~0,045°, igual nos
  dois sentidos do mesmo lado). O polígono de entrada é simplificado (0,05°), tremido e engrossado com
  `buffer(0.15, join_style=2)`; depois é cortado pela terra, então **a costa é a de `mundo.json`**.
- Sem sobreposição: os povos bíblicos de `territorios-<ano>.json` ficam primeiro (e substituem a mancha do vídeo de mesmo
  id, mais `israel` e `fenicia`); os demais entram do menor para o maior, cada um menos a união dos anteriores.
- Saída com 2 casas decimais e simplificação final de 0,03°; estados sem nome menores que 1 grau² são descartados.

## 3. Formato dos dados do site

- `frontend/mapa-geral/dados/<a|d><ano>.json`: `{"ano": N, "estados": [{"id", "area", "aneis"}]}`. `a<N>` é N a.C. e
  `d<N>` é N d.C. `aneis` são anéis em [lon, lat]; o desenho usa preenchimento par-ímpar (buracos entram como anéis).
- `frontend/mapa-geral/dados/indice.json`: `{"anos": [2500, 2400, ..., -2025], "estados": {id: {nome, cor, desde, ate,
  nota}}, "fonte"}`. `desde`/`ate` vêm da faixa de anos da regra (ou dos quadros em que o estado aparece).
- A página (`mapa-geral.js`) usa `Projecao` (Equal Earth, `compartilhado/js/projecao.js`), carrega o ano sob demanda e
  aceita `?ano=-30` para abrir no quadro-chave mais próximo.

## 4. Regenerar

Dependências Python fora do repositório (o Python do sistema não traz nenhuma):

```
uv pip install --target ~/.cache/mapa-biblia-lib/lib numpy shapely pillow opencv-python-headless
export PYTHONPATH=~/.cache/mapa-biblia-lib/lib
python3 scripts/mapa-geral/extrair.py            # quadros + OCR do ano
python3 scripts/mapa-geral/indexar.py            # limpa anos, quadros-chave
python3 scripts/mapa-geral/calibrar.py todos 20  # calibração a cada 20 s (5–10 min)
python3 scripts/mapa-geral/gerar.py [ano ...]    # segmenta e nomeia (≈7 min para todos)
python3 scripts/mapa-geral/construir.py [ano ...] # dados do site (≈30 s)
node scripts/verificar.mjs
```

Com `construir.py <ano>` só o arquivo do ano é regravado e `indice.json` não muda.

## 5. Limites conhecidos

1. **Estados cremes/pálidos não são capturados** (Frígia clara, Magã, Sabá, Catabã, Pandias, Anshan). Foram descartados
   porque o tom creme se confunde com a terra sem dono. Caminho: aceitar cremes só como componentes pequenos e compactos,
   ou desenhar à mão (`scripts/mapa/formas.json`, editor em `scripts/editor-mapas.html`).
2. **Nomes só para a Antiguidade** (região bíblica, Índia e China antigas). Medieval, moderno e hoje têm as formas, mas
   não os nomes; o OCR (`nome_en`) é ruidoso demais para publicar sem revisão.
3. **Povos pequenos da Bíblia** (Moabe, Amom, Edom, Filístia, Midiã, Basã, Judá/Israel) não aparecem como estados no vídeo;
   vêm de `territorios-<ano>.json`, que só existe para 21 anos. Nos outros anos, Israel é a mancha do vídeo ("Israel e
   Judá").
4. **O vídeo agrupa**: o Egito inclui a Núbia e a faixa até Canaã quando expande; os aquemênidas e o Egito têm a mesma cor.
5. **Datas** de `desde`/`ate` são as das regras, não as do vídeo. Revise antes de tratar como histórico.
6. **Tamanho**: 2,3 MB no total, mas os anos de 1500 d.C. em diante passam de 60 KB (até ~150 KB) por causa das centenas
   de formas sem nome. Ao nomear essas épocas, junte estados por id e simplifique mais.
7. **Período 3400–2500 a.C.** ainda não existe (o vídeo principal começa em 2500 a.C.; usar o vídeo escuro `4BzUDJDiE8c`).
8. Os mapas por história ainda usam os próprios arquivos; só a projeção (Equal Earth) é compartilhada.

## 6. Checklist de revisão por etapa

- [ ] Abrir `/mapa-geral/?ano=<ano>` em 3 a 5 anos do trecho e comparar com o quadro (`folha.py`).
- [ ] Nomes e datas das regras conferidos contra fonte histórica, não só contra o vídeo.
- [ ] Nenhuma sobreposição; costa seguindo `mundo.json`; só linhas retas.
- [ ] `node scripts/verificar.mjs` sem falhas (1280 e 360 px).
- [ ] Créditos (`fonte` em `indice.json`) e este documento atualizados.

## 7. Créditos

- Formas e nomes: vídeos "Every Year" e "World history 3500 BCE – PRESENT" (autores no YouTube; links em `videos.txt`),
  usados apenas como referência.
- Costas, lagos e rios: Natural Earth (domínio público).
- Projeção Equal Earth: Šavrič, Patterson e Jenny (2018).
