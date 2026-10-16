# Mapa geral: como foi feito

A página `frontend/mapa-geral/` mostra o mundo todo, ano a ano, de 2500 a.C. em diante, com uma linha do tempo
(controle deslizante, anterior/próximo e reprodução). As formas dos povos foram **lidas de vídeos de história mundial**
e depois recalculadas sobre a costa do projeto. Este documento explica a origem dos dados, o caminho que eles fazem
até o site, os limites do resultado e como regenerar tudo.

Estado (2026-10-16): **versão 2, ano a ano, de 2500 a.C. a 2025 d.C.**, feita pelo plano `docs/mapa-geral-plano-2.md`
(etapas E0–E9; desvios e decisões no §11 de lá). Todas as formas, cores e nomes vêm só do vídeo; os nomes são lidos por
OCR e traduzidos em `scripts/mapa-geral/nomes.json`. Estados sem etiqueta legível ficam sem rótulo ("Estado sem nome
lido"). Os 27 mapas por história continuam como estavam. Pendente: E10 (apagar os scripts da v1, revisão por época).

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

## 3. Formato dos dados do site (versão 2)

Gerados por `scripts/mapa-geral/construir.py` (cabeçalho do script tem o detalhe):

- `frontend/mapa-geral/dados/indice.json`: `{"versao": 2, "de": 2500, "ate": -2025, "bloco": 25, "estados": {id:
  {nome, nome_video, cor, desde, ate, nota, nomes?}}, "fonte"}`. A sequência de anos é implícita: 2500…1 a.C.,
  1…2025 d.C. (sem ano 0), posição `i` = 0…4524. `nomes` = `[[de, ate, nome, nome_video], ...]` quando o nome muda ao
  longo da vida (trocas aprovadas em `nomes.json`); `nome` é o mais duradouro. Ids são o slug do nome pt-BR (`egito`,
  `egito-2`…) ou o id interno (`e01234`) quando não há nome.
- `frontend/mapa-geral/dados/blocos/<a|d><ano>.json`: um arquivo por bloco de 25 posições, com o nome do primeiro ano
  (`a2500` = 2500–2476 a.C.): `{"anos": [de, ate], "formas": [{"id", "de", "ate", "aneis"}]}`. Cada forma vale de `de`
  a `ate` (inclusive) e só é gravada de novo quando a geometria muda. Anéis em centésimos de grau, o primeiro ponto
  absoluto e os seguintes como deltas (`[x0, y0, dx1, dy1, ...]`), abertos; a página fecha e desenha em par-ímpar
  (buracos são anéis). Total ≈ 55 MB (15 MB gzip), 181 blocos, média 300 KB (83 KB gzip).
- A página (`mapa-geral.js`) usa `Projecao` (Equal Earth), carrega o bloco do ano sob demanda (cache de 20 blocos,
  pré-carga do seguinte), redesenha só o que muda e aceita `?ano=-30` (30 d.C.); a URL acompanha o ano.

## 4. Regenerar

Dependências Python fora do repositório (o Python do sistema não traz nenhuma): numpy, shapely, pillow,
opencv-python-headless, tesserocr e rapidocr-onnxruntime em `~/.cache/mapa-biblia-lib/lib` (tessdata_best `eng` em
`~/.cache/mapa-biblia-lib/tessdata/`, fonte `sarabun.ttf` em `~/.cache/mapa-biblia-lib/fontes/`).

```
export PYTHONPATH=~/.cache/mapa-biblia-lib/lib
python3 scripts/mapa-geral/quadros.py            # E2: quadros e mapas distintos (.cache/v2/anos.json, mapas/)
python3 scripts/mapa-geral/calibrar.py           # E3: calibração por mapa
python3 scripts/mapa-geral/rotular.py            # E4: rótulo por pixel
python3 scripts/mapa-geral/vetorizar.py          # E5: cobertura em lon/lat
python3 scripts/mapa-geral/rastrear.py           # E6: ids persistentes
python3 scripts/mapa-geral/nomear.py textos --amostra todos --variante det-d   # E7a: OCR das etiquetas (≈1,5 h, 4 processos)
python3 scripts/mapa-geral/nomear.py unioes --variante-textos det-d           # E7: uniões de pedaços
python3 scripts/mapa-geral/nomear.py vetores --variante-textos det-d --variante e7
MAPA_GERAL_EXP=e7 python3 scripts/mapa-geral/rastrear.py --fonte e7u --variante e7   # E6 refeita sobre os vetores unidos
python3 scripts/mapa-geral/nomear.py nomes --variante-e6 e7 --variante-vetores e7 --variante-textos det-d --variante v1
python3 scripts/mapa-geral/cache.py aprovar e7 v1      # (e e7u e7, e6 e7)
python3 scripts/mapa-geral/construir.py          # E8: dados do site (≈40 s)
python3 scripts/mapa-geral/testar.py e8          # testes da E8 (≈15 min; e0…e7 para as etapas anteriores)
node scripts/verificar.mjs && node scripts/mapa-geral/testar-pagina.mjs   # E9
```

**Painel local** (tudo num lugar): `python3 scripts/mapa-geral/painel.py` e `http://localhost:8001/scripts/mapa-geral/painel.html`.
Abas: **Mapa** (quadro do vídeo × vetores ano a ano, casos e pares, seletor de variante e comparação A/B de duas variantes,
anotações por clique em `anotacoes.json`), **Mapas** (grade com o estado de cada mapa distinto em cada etapa: pronto na
aprovada, desatualizado, faltando, esperando; usa as mesmas chaves de cache dos scripts), **Versões** (variantes de cada
etapa da loja por chave, com aprovar, voltar e apagar; dados publicados e arquivos de mão), **Rodar** (fila de rodadas dos
scripts, uma por vez, log ao vivo, interromper), **Andamento** (manifestos e logs), **Revisão** (imagens) e **Editor**
(`editor.html`: unir dois estados, nome pt-BR e do vídeo, cor, mover/acrescentar/apagar vértices; atalhos no padrão Adobe:
V, A, P, H, Z, espaço, Ctrl+J, Ctrl+S, Ctrl+Z, Delete). As edições ficam em `scripts/mapa-geral/edicoes.json` e o
`construir.py` as reaplica depois de cada regeneração.

Cada etapa é incremental (cache por chave em `scripts/mapa-geral/.cache/v2/`, variantes e aprovação:
`docs/mapa-geral-incremental.md`; a calibração da E3 também fica na loja, e `calibracao.json` é o apontador para a
variante aprovada). Nomes: edite `scripts/mapa-geral/nomes.json` (`traducoes`, `entidades`, `trocas`) e rode só
`construir.py`.

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
