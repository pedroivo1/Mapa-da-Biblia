# Mapa geral a partir de vídeos — plano, estado atual e instruções para um agente novo

> Documento de passagem de bastão. Escrito para quem não viu a conversa anterior. Leia também `AGENTS.md`
> (regras do projeto) antes de mexer em qualquer coisa. Idioma do projeto: **português do Brasil** (código,
> comentários, nomes de arquivo, textos).

> **Estado em 2026-10-14 (segunda sessão):** etapas 3, 5, 6 e 7 do pipeline feitas para a **Antiguidade**.
> `segmentar.py` agora simplifica o contorno com 1,2 px (antes ~0,4 % do perímetro, grosseiro demais);
> `nomes.json` + `construir.py` geram `frontend/mapa-geral/dados/` (79 anos, 2,3 MB); a página abre com dados reais e
> passa em `verificar.mjs`; `mapa.js` usa `projecao.js`; link em `mapas/`; documentação em `docs/mapa-geral.md`.
> **Falta:** nomes do medieval, moderno e hoje; cremes/pálidos; período 3400–2500 a.C.; reduzir o tamanho dos anos
> recentes (~150 KB); revisão com o usuário por etapa. O quadro de 2500 a.C. é válido (mantido). Veja `docs/mapa-geral.md`.

## 1. Objetivo

Criar um **mapa geral com linha do tempo** (mundo todo, de 2500 a.C. até 2025 d.C.; o vídeo principal começa em
2500 a.C.), desenhado a partir de vídeos de "história mundial ano a ano" que o usuário baixou, e **documentar em
`docs/mapa-geral.md`** como os vídeos foram usados. No futuro o mapa geral substitui os 27 mapas por história, mas
**por enquanto eles ficam como estão** (decisão do usuário).

Decisões já tomadas com o usuário:

| Tema | Decisão |
|---|---|
| Cobertura | Mundo todo, do período mais antigo até hoje |
| Integração | Nova página `frontend/mapa-geral/`; **não** remover os mapas atuais |
| Documentação final | `docs/mapa-geral.md` (explica fontes, extração, calibração, limites, como regenerar) |
| Etapas | Pode separar em etapas; entregar por partes (antigo → medieval → moderno → hoje) |
| Vídeos | Só **referência** (são de terceiros): formas e nomes próprios, créditos no `.md` |

## 2. Regras do projeto que valem aqui (resumo; a fonte é `AGENTS.md`)

- **Bordas/territórios: só linhas retas, nunca curvas**, com **tremor determinístico** (cada lado vira poligonal
  de segmentos curtos ~0,35°, deslocados ~0,045°; mesmo lado → mesmos pontos nos dois sentidos).
  Implementação: `scripts/mapa/tremor.py`. Buffers sempre com junção em quina (`join_style=2`).
- **Territórios nunca se sobrepõem**: prioridade fixa; a borda comum é desenhada uma vez.
- Onde toca o mar, segue a costa de `frontend/mapa/mundo.json` exatamente.
- **Cor fixa por território/província** (tabela `CORES_REGIAO` em `frontend/mapa/mapa.js`; egito = `#d9a21e`).
- JS do site em **ES5 dentro de IIFE** (sem `let/const`/arrow/módulos). Anos: **a.C. positivo, d.C. negativo**.
- `scripts/` e `docs/` **não são publicados** (a Vercel serve só `frontend/`). A pasta `vídeos/` está na raiz do
  repositório e é ignorada pelo git (`vídeos/.gitignore` com `*`); nunca commitar vídeos nem quadros.
- Verificação: `node scripts/verificar.mjs` (smoke test das páginas em 1280 e 360 px). Adicionar a página nova
  na lista `PAGINAS` desse script.
- Não existe build, nem gerenciador de pacotes no site. O Service Worker (`frontend/sw.js`) usa
  "mostra o cache e atualiza depois": ao testar, recarregue duas vezes ou troque `VERSAO` em `sw.js`.

## 3. Ambiente (descobertas práticas)

- Há `ffmpeg`, `tesseract` (só `eng`), ImageMagick (`magick`), `node`, Chrome (`google-chrome-stable`) e `uv`.
  **Não há `pip`**. Python 3.14 do sistema **sem** numpy/OpenCV/Pillow/shapely.
- Dependências Python foram instaladas **fora do repositório** com `uv`:
  `uv pip install --target <DIR>/lib numpy pillow opencv-python-headless shapely` e usadas com
  `PYTHONPATH=<DIR>/lib python3 ...`. Na sessão anterior `<DIR>` era o diretório temporário da sessão; um agente
  novo deve criar o seu (por exemplo `~/.cache/mapa-biblia-lib`).
- Servidor local para ver páginas: `cd frontend && python3 -m http.server 8000` (ou, na raiz do repo, para o editor
  de formas). Capturas headless: `google-chrome-stable --headless=new --no-sandbox --disable-gpu
  --user-data-dir=<tmp-limpo> --window-size=1200,800 --virtual-time-budget=9000 --screenshot=out.png URL`
  (use `user-data-dir` novo a cada captura: o Service Worker e o cache confundem testes).
- **Cuidado:** `pkill -f ...` pode matar o próprio shell (padrão aparece na linha de comando). Use `kill PID`.
- O usuário rejeitou uma vez rodar `verificar.mjs`/capturas sem aviso; avise o que vai rodar. Comandos longos:
  rode em segundo plano (`nohup ... &`) e consulte o log.

## 4. Os vídeos (pasta `vídeos/`, raiz do repositório; links em `videos.txt`)

| Arquivo (id do YouTube) | Resolução | Duração | Papel |
|---|---|---|---|
| `Every Year [hzWwp9JM7Hw]` | 1920×960 | 17 min 24 s | **Fonte principal das formas**: mapa claro, estados em cores chapadas, ano no rodapé, começa em 2500 a.C. |
| `Every Year (3400 BCE – 2026) [4BzUDJDiE8c]` | 1920×1080 | 17 min | Mapa escuro com relevo; ranking dos "maiores estados" e contagem; confere nomes e o período 3400–2500 a.C. (que o vídeo principal não tem) |
| `World history 3500 BCE – PRESENT [pWP0Z9XLxH8]` | 1920×1080 | 20 min 30 s | Muito denso (etiquetas por cima); só contexto/validação |

Propriedades do vídeo principal (já verificadas):
- **Mar** = azul-acinzentado (RGB ≈ 218,228,237; em BGR do OpenCV 237,228,218). **Terra sem dono = branco**.
  **Estados = cores chapadas** (algumas pálidas/creme, algumas cinza). Contornos finos cinza na costa.
- **Projeção: Mercator.** O enquadramento muda por trechos (zoom abre com o tempo). Calibração por trechos
  (escala `S` em px/grau em quadros de 1280 px; `X0`,`Y0` = canto do quadro no mundo renderizado):

  | Segundos do vídeo | Anos aproximados | S (px/°) | X0 | Y0 |
  |---|---|---|---|---|
  | 2–148 | 2500 a.C. – 1000 a.C. | 11.28 | 2174 | 919 |
  | 149–~555 | ~1000 a.C. – ~800 d.C. | 8.40 | 1397 | 577 |
  | ~565–~800 | ~800 – ~1500 d.C. | 7.049 | 1045 | 419 |
  | ~805–905 | ~1500 – ~1790 d.C. | 4.673 | 248 | 203 |
  | ~925–1043 | ~1790 – 2025 d.C. | 3.60 | 16 | 87 |
  (o arquivo completo está em `scripts/mapa-geral/.cache/calibracao.json`; pontos de transição têm escore baixo
  e são tratados trocando para um segundo vizinho — ver `gerar.py`).
- Escala de tempo **irregular** (≈9 anos/s no início, bem menos depois). O ano vem do rodapé por OCR.
- Quadros 1–2 e o último são intro/fade; o primeiro ano lido é 2500 a.C. (s=2) e o último 2025 d.C. (s≈1036).

## 5. Pipeline (todos os scripts em `scripts/mapa-geral/`; cache em `scripts/mapa-geral/.cache/`, ignorado)

| Etapa | Script | Entrada → saída | Estado |
|---|---|---|---|
| 1. Quadros + ano | `extrair.py` | vídeo → `quadros/NNNN.jpg` (1 por segundo, 1280 px) e `indice-bruto.json` (OCR do ano; caixa localizada pelas bordas verticais da moldura, faixa y 574–602) | **feito** (1040 de 1044 anos lidos) |
| 1b. Limpeza + quadros-chave | `indexar.py` | `indice-bruto.json` → `indice.json`, `quadros-chave.json` (79 quadros: a cada 100 anos até 1000 a.C., 50 depois, 100 d.C. em diante a cada 100, mais os anos dos mapas atuais) | **feito** |
| 2. Calibração | `calibrar.py` | máscara de terra do quadro × costa de `mundo.json` renderizada (`cv2.matchTemplate`, `TM_CCOEFF_NORMED`) → `calibracao.json` (`python3 calibrar.py todos 20`) | **feito** (escore ≈ 0,72–0,79) |
| 3. Segmentação + nomes | `gerar.py` (usa `segmentar.py`, `nomear.py`) | quadro-chave → `.cache/estados/<a|d><ano>.json` com `{cor, area_px, bbox, anel (lon/lat), nome_en}` | **feito** para os 79 quadros (a2500 removido: é intro) |
| 4. Entidades | `agrupar.py` | agrupa estados entre quadros por cor+posição → `entidades.json` e grava `entidade` em cada estado | feito, **qualidade média** (ver §6) |
| 5. Dados do site | **a fazer** (`construir.py`) | estados + `nomes.json` → `frontend/mapa-geral/dados/` | pendente |
| 6. Página | `frontend/mapa-geral/{index.html,mapa-geral.js,mapa-geral.css}` | já escritos, **ainda não testados** (faltam dados) | escrito |
| 7. Documentação | `docs/mapa-geral.md` | — | pendente |

Convenção dos arquivos de ano: `a<N>.json` = N a.C.; `d<N>.json` = N d.C. (ex.: `d51.json` = 51 d.C.).
Cada quadro-chave tem o campo `ano` (positivo a.C., negativo d.C.) e `segundo` (pode ser vizinho do pedido,
quando o quadro cai numa transição).

Comandos (na raiz do repositório, com `PYTHONPATH` apontando para as bibliotecas):
```
python3 scripts/mapa-geral/extrair.py            # quadros + OCR dos anos
python3 scripts/mapa-geral/indexar.py            # limpa anos, escolhe quadros-chave
python3 scripts/mapa-geral/calibrar.py todos 20  # calibração a cada 20 s (≈5–10 min)
python3 scripts/mapa-geral/gerar.py [ano ...]    # segmenta e nomeia (≈7 min para os 79)
python3 scripts/mapa-geral/agrupar.py            # entidades
```

## 6. Achados importantes e problemas conhecidos

1. **Segmentação por cor funciona bem** para estados saturados (conferido visualmente em 2000, 1700, 1450, 1200,
   1000, 800, 650 a.C.: Egito, Assíria, Babilônia, Elão, Hititas, Mitani, Micenas, Lídia, Urartu, Fenícios etc.).
   Filtros atuais em `segmentar.py`: exclui mar (distância L1 < 70 do tom do mar), branco, escuros (texto),
   cinzas/azuis pálidos; para cores pouco saturadas exige área ≥ 220 px e "solidez" ≥ 0,5 (corta contorno de costa).
2. **Estados creme/pálidos (Frígia, Magã, Anshan, Kush, Lídia clara) NÃO são capturados.** Tentativa: aceitar tons
   amarelados claros (R>B, min>200, L1 ao branco ≥ 24). Resultado: o tom (246,246,234) englobou terra sem dono
   inteira (componente de 565 mil px) — **a tentativa foi revertida** em `segmentar.py`. Próximo passo sugerido:
   pegar cremes só como componentes pequenos/compactos (área < ~15 000 px, solidez > 0,6) e/ou distinguir do
   branco de terra por uma máscara de "terra sem dono" (branco puro 253–255) fechada, ou nomear à mão pelas
   etiquetas (ver 4).
3. **OCR dos nomes é ruidoso** (tesseract `eng`): texto branco sobre cor e letras pequenas falham ("Egyt",
   "Mycenr"). `nomear.py` compõe uma imagem só com texto preto e associa palavras ao estado mais próximo
   (≤ 26 px). Serve como *dica*, não como verdade. **A votação entre quadros ajuda** (mesma entidade em vários anos).
4. **A mesma cor é reutilizada por estados diferentes em épocas diferentes** (ex.: verde (72,192,96) = Elão e
   depois Aquemênida/Pártia). O `agrupar.py` (cor + proximidade do centro) mistura alguns e fragmenta outros
   (1087 entidades, ~91 relevantes na região bíblica). **Recomendado:** nomear por regras
   `{cor aprox., região (caixa lon/lat), faixa de anos} → {id, nome pt-BR}` em `scripts/mapa-geral/nomes.json`,
   olhando recortes dos quadros (técnica usada: recortar a região e montar folhas de contato com `cv2`; ver
   exemplos de cores/nomes abaixo).
5. Quadros de **transição** (fade/zoom) têm escore de calibração baixo (ex.: segundo 148). `gerar.py` troca para
   segundo vizinho; confira `escore` no log de `gerar.py`.
6. O vídeo desenha o **Egito imperial** (Núbia + faixa até Canaã) e agrupa povos; povos pequenos da Bíblia
   (Moabe, Amom, Edom, Filístia, Fenícia, Midiã, Basã, Aram, Yehud, Judá/Israel) **não aparecem como estados
   próprios** em geral: devem vir de `frontend/mapa/territorios-<ano>.json` (gerados por
   `scripts/mapa/territorios.py`, que aceita editar formas em `scripts/mapa/formas.json`) e de `roma.json`.

Exemplos de nomes/cores lidos nos quadros (RGB aprox.), para montar `nomes.json`:

| Estado (nome no vídeo) | Cor | Observação |
|---|---|---|
| Egypt (Old/Middle/New Kingdom) | (246,222,90) amarelo | faixa do Nilo; vira Egito imperial depois de ~1550 a.C. |
| Assyria | (78,138,150)/(66,125,150) azul-petróleo | ~2000–609 a.C. e núcleo antes |
| Babylon | (222,90,90) vermelho | ~1800–539 a.C. |
| Elam | (90,198,102) verde | 2400–~540 a.C. |
| Hittites | (126,210,138) verde-claro | ~1700–1180 a.C. |
| Mitanni | (144,96,120) mauve | ~1500–1300 a.C. |
| Mycenae / Minoa / Greeks | (48,120,168) azul | Grécia e Creta |
| Indus Valley | (66,138,198) azul | 2400–1700 a.C. |
| Urartu | (144,96,120) | ~850–600 a.C. |
| Lydia | (246,186,114) laranja | ~1100–546 a.C. |
| Phoenicians/Phoenicia | (144,96,168) lilás | costa e colônias |
| Rome (Roman Empire) | (126,30,30)/(120,24,24) vinho | ~750 a.C. em diante |
| Carthage | (186,138,42) ocre | ~814–146 a.C. |
| Kush/Axum, Saba | (234,138,138)/(222,162,162) rosados | sul do Egito / Arábia |

## 7. O que falta fazer (ordem sugerida)

1. **Nomes** (`scripts/mapa-geral/nomes.json`) para os estados da Antiguidade na região
   lon −15…80, lat 5…52 até 100 d.C. (o foco bíblico), por regras de cor+região+anos; depois o restante do
   mundo (pode ficar com `nome_en` do OCR ou nome genérico até revisão).
2. **`construir.py`** (novo): para cada quadro-chave
   - agrupar polígonos por `id` final (vários estados do vídeo podem virar o mesmo id);
   - recortar pela terra de `mundo.json` (copiar o método de `scripts/mapa/territorios.py`: soma par-ímpar dos
     anéis de `terra`, menos polígonos `mar`; polígono `.buffer(0.15, join_style=2)` ∩ terra);
   - simplificar (Douglas-Peucker ~0,05°) e aplicar `tremer()` de `scripts/mapa/tremor.py`;
   - sem sobreposição: ordenar por área crescente, cada polígono menos a união dos anteriores;
   - sobrepor os povos bíblicos de `territorios-<ano>.json` (gerar esses arquivos também para os anos-chave,
     parametrizando `territorios.py`), com prioridade sobre as manchas do vídeo;
   - gravar 2 casas decimais: `frontend/mapa-geral/dados/<a|d><ano>.json` =
     `{"ano": N, "estados": [{"id": "...", "area": graus², "aneis": [[[lon,lat],...]]}]}`;
   - `frontend/mapa-geral/dados/indice.json` = `{"anos": [2400, 2300, ..., -2025], "estados": {"<id>": {"nome":
     "Egito", "cor": "#d9a21e", "desde": 3100, "ate": 30, "nota": ""}}, "fonte": "texto de crédito"}`.
   - orçamento: ≤ ~60 KB por ano, ≤ ~3 MB no total.
3. **Página**: testar `frontend/mapa-geral/` com dados reais (`node scripts/verificar.mjs`; adicionar
   `["mapa-geral/", 'document.querySelectorAll(".geral-estado").length']` em `PAGINAS`); capturas em 3400/2500 a.C.,
   1000 a.C., 30 d.C., 1500 d.C., 2025. Ajustar legibilidade dos nomes e o cartão ao toque.
4. **Projeção compartilhada**: `frontend/compartilhado/js/projecao.js` já existe e a página nova a usa; falta
   fazer `frontend/mapa/mapa.js` usá-la (hoje tem cópia própria de Equal Earth) — trocar com cuidado e rodar
   `verificar.mjs`.
5. **Link de entrada** discreto na página `frontend/mapas/` (não alterar o nav das 9 páginas).
6. **Período 3400–2500 a.C.**: usar o vídeo `4BzUDJDiE8c` (escuro) ou aceitar começar em 2500 a.C.
7. **Documentação**: escrever `docs/mapa-geral.md` (fontes, papel de cada vídeo, OCR do ano, calibração e
   resíduos, segmentação, rastreamento, regras de forma, nomes/cores, limitações, como regenerar, créditos,
   checklist de revisão) e atualizar `AGENTS.md` (tabela de fatias, `scripts/mapa-geral/`) e `README.md`.
8. Ao final: revisar com o usuário por etapas (antigo → medieval → moderno → hoje), sem remover os 27 mapas.

## 8. Instruções para o agente novo (copie e cole)

> Você está continuando o projeto "Mapa da Bíblia" (site estático em `/data/Documents/Programing/Mapa-da-Biblia`).
> Leia primeiro `AGENTS.md` e este arquivo (`docs/mapa-geral-plano.md`). Responda sempre em português do Brasil.
>
> **Tarefa:** terminar o **mapa geral com linha do tempo** descrito na seção 7 deste documento. O pipeline de
> extração dos vídeos já foi executado (seção 5); os estados por quadro-chave estão em
> `scripts/mapa-geral/.cache/estados/` (se a pasta `.cache` tiver sumido, rode os scripts da seção 5 na ordem —
> instale antes numpy, Pillow, opencv-python-headless e shapely com `uv pip install --target <dir>/lib ...`).
>
> **Regras inegociáveis:** (1) bordas só com linhas retas + tremor determinístico (`scripts/mapa/tremor.py`),
> sem arcos; (2) territórios nunca se sobrepõem; (3) JS do site em ES5/IIFE; (4) a.C. positivo, d.C. negativo;
> (5) nunca commitar vídeos/quadros; (6) não remover os 27 mapas existentes; (7) vídeos são referência: formas e
> nomes próprios, com créditos no `.md`.
>
> **Como trabalhar:** faça por etapas e mostre capturas (Chrome headless, `user-data-dir` novo) antes de
> declarar pronto; rode `node scripts/verificar.mjs` ao final; comandos longos em segundo plano; não use
> `pkill -f`. Avise o usuário do que vai rodar. Se algo for ambíguo (por exemplo, quantos anos por quadro-chave
> ou como nomear estados pequenos), pergunte antes de gastar muito tempo.
>
> **Comece por:** (a) montar `scripts/mapa-geral/nomes.json` para a Antiguidade na região bíblica (use folhas de
> contato dos quadros, técnica da seção 6); (b) escrever e rodar `scripts/mapa-geral/construir.py`;
> (c) abrir `frontend/mapa-geral/` com os dados e ajustar; (d) escrever `docs/mapa-geral.md`.

## 9. Mapa dos arquivos

```
vídeos/                       vídeos baixados (ignorados pelo git; `videos.txt` na raiz tem os links)
scripts/mapa/                 geradores dos territórios (territorios.py, roma.py, tremor.py, formas.json opcional)
scripts/editor-mapas.html     editor local de vértices (servir a raiz do repo; NÃO é publicado)
scripts/mapa-geral/           extrair.py indexar.py calibrar.py segmentar.py nomear.py gerar.py agrupar.py
scripts/mapa-geral/.cache/    quadros/, indice*.json, calibracao.json, quadros-chave.json, estados/, entidades.json
frontend/mapa-geral/          página nova (index.html, mapa-geral.js, mapa-geral.css, dados/ vazio por enquanto)
frontend/compartilhado/js/projecao.js   Equal Earth compartilhada (window.Projecao)
frontend/mapa/                mapas por história (27), mundo.json, territorios-<ano>.json, roma.json, mapa.js
docs/                         este arquivo (e, no fim, mapa-geral.md)
```
