# Mapa geral, versão 2: ano a ano, só o vídeo, bordas corretas

> Plano de execução para um agente de IA que **não viu** as conversas anteriores. Leia antes `AGENTS.md` (regras do
> projeto), `docs/mapa-geral.md` (como a versão 1 foi feita) e este arquivo inteiro. Idioma do projeto: **português do
> Brasil** (código, comentários, nomes de arquivo, textos, mensagens ao usuário).
>
> Este plano **substitui** `docs/mapa-geral-plano.md` (versão 1), que fica só como histórico.

## 0. Como usar este documento

- Execute as etapas **na ordem** (E0 → E10). Cada etapa tem: objetivo, tarefas, saídas, **testes automáticos com
  critério numérico**, **revisão visual** e um **portão**. Só passe para a próxima etapa quando todos os testes do
  portão passarem; se um critério não for atingido depois de duas tentativas honestas, **pare e pergunte ao usuário**
  (seção 9), mostrando números e imagens.
- Ao fim de cada etapa, mande ao usuário um relatório curto: o que mudou, saída de `testar.py <etapa>`, 2 a 4
  imagens de revisão e o que ficou pendente. Não diga "pronto" sem os testes e as imagens.
- Os testes moram em `scripts/mapa-geral/testar.py` (criado na E0 e ampliado a cada etapa). Um teste que falha é
  informação: não afrouxe um critério para fazê-lo passar sem avisar o usuário e registrar o motivo na seção 11.
- Revisão visual é obrigatória: **abra as imagens** geradas (ferramenta de leitura de imagem) e descreva o que viu.
  Não basta gerá-las.
- Não faça commit sem o usuário pedir. Não apague o cache do Chrome do usuário. Não use `pkill -f` (mata o próprio
  shell): use `kill PID`. Comandos longos: em segundo plano, com log.

## 1. O que deu errado na versão 1 (diagnóstico com evidências)

### 1.1 Não ficou ano a ano

- `extrair.py` tirou **1 quadro por segundo** (`fps=1`). O vídeo principal tem **29,97 fps** e avança até **~10 anos
  por segundo** no começo (2500–1000 a.C.), ~4 anos/s na era de Cristo e ~2 anos/s perto de hoje. Com 1 quadro/s, a
  maioria dos anos nunca foi vista.
- `indexar.py` escolheu só **79 quadros-chave** (a cada 100/50 anos + anos dos mapas antigos). O site mostra só esses
  79 anos.
- Verificado nesta sessão: **o vídeo mostra todos os anos**, cada um por ~3 quadros (ex.: segundo 50 → 2038, 2037,
  2036… BC, três quadros cada). E **o mapa não tem transição suave**: entre quadros, a área do mapa é idêntica
  pixel a pixel (diferença 0) e muda de uma vez quando alguma fronteira muda. Ou seja: dá para ter um mapa exato
  para cada ano, e anos sem mudança têm mapa idêntico.

### 1.2 Mapas antigos misturados com o vídeo

- `construir.py` lê `frontend/mapa/territorios-<ano>.json` (povos bíblicos **desenhados à mão** para os 27 mapas por
  história) e os põe **por cima** das manchas do vídeo, com prioridade, apagando o que o vídeo mostra (ids `israel`,
  `fenicia` e qualquer id igual).
- As cores vêm da tabela `CORES_REGIAO` de `frontend/mapa/mapa.js` e do campo `cor` de `nomes.json` (paleta dos mapas
  antigos), não do vídeo.
- Efeito, em 586 a.C.: no vídeo, a Babilônia é uma faixa **vermelha** em crescente e os Medos são uma mancha verde
  enorme. No site aparece uma **Babilônia azul e quadrada** cobrindo toda a Mesopotâmia (é a forma do mapa antigo),
  os Medos encolhidos e Elão e "Cuxe (Núbia)" com formas que não estão no quadro.
- O commit `9309aa0` também mexeu em `frontend/mapa/mapa.js` (passou a usar `compartilhado/js/projecao.js`). Isso
  precisa ser conferido: os 27 mapas por história **não podem mudar** (E0).

### 1.3 Bordas ruins

Causas encontradas em `segmentar.py` e `construir.py`:

1. Cada estado é um polígono **independente**: simplificado, tremido e **inflado 0,15°** (`buffer(0.15)`), depois
   as sobreposições são resolvidas com "o menor ganha". Vizinhos não dividem a mesma borda: ficam frestas,
   dentes e bordas deslocadas para dentro do estado maior.
2. O tremor é aplicado a cada polígono antes do recorte, então a borda comum não sai igual dos dois lados (fere a
   regra do AGENTS.md: "a borda comum é desenhada uma vez").
3. **Estados escuros são descartados como texto** (`max(b,g,r) < 110`): somem o Sacro Império (cinza-escuro em
   999 d.C.), os Otomanos (verde-petróleo escuro em 1799) e outros.
4. **Estados creme não são capturados.** No medieval, metade dos estados é creme (Caracânidas, Qocho, Yutian,
   Macúria…). O creme fica muito perto do branco da terra sem dono (ex.: Cuxe em 584 a.C. = RGB 254,248,238; terra
   sem dono = 255,255,255; distância L1 ≈ 24), e **estados creme vizinhos se separam só por linhas cinza finas**.
   Separar só pela cor não funciona: é preciso usar as linhas de contorno.
5. Os nomes escritos dentro dos estados (texto branco sobre cor, preto sobre creme) abrem **buracos**: o
   fechamento morfológico 5×5 não fecha letras grandes ("Byzantine Empire").
6. Os quadros foram reduzidos para 1280 px e salvos em **JPEG**, o que borra as bordas e cria cores falsas. O vídeo é
   1920×960.
7. No mundo inteiro (a partir de ~1500 d.C.), o vídeo mostra o Alasca nas duas pontas (**antimeridiano**); nada
   trata longitudes além de ±180°.
8. Anos com zoom/troca de enquadramento usam uma calibração "vizinha", às vezes errada.

## 2. Decisões do usuário (2026-10-14)

| Tema | Decisão |
|---|---|
| Fonte do mapa geral | **Só o vídeo selecionado** (`hzWwp9JM7Hw`). Nada de `territorios-<ano>.json`, `roma.json`, `formas.json` ou `CORES_REGIAO` entra no mapa geral. |
| Mapas antigos | Os 27 mapas por história (`frontend/mapa/`, `frontend/mapas/`) **continuam exatamente como estavam**. |
| Cores | **Cores do vídeo**: cada estado usa a cor que tem no vídeo, a mesma ao longo da vida dele. |
| Nomes | **Todas as épocas** (Antiguidade, medieval, moderna, hoje), em pt-BR. |
| Período e passo | **2500 a.C. – 2025 d.C., de ano em ano** (4.525 anos; não existe ano 0). |

## 3. Regras inegociáveis

1. Bordas só com **linhas retas** e o **tremor determinístico** de `scripts/mapa/tremor.py` (sem arcos nem buffers
   arredondados; buffers só com `join_style=2`).
2. **Sem sobreposição e sem frestas**: os estados de um ano formam uma **cobertura** (partição); a borda comum de dois
   vizinhos tem exatamente os mesmos pontos nos dois.
3. Onde toca o mar, a borda segue **a costa de `frontend/mapa/mundo.json`** exatamente.
4. JS do site em ES5 dentro de IIFE (`var`, `function`; sem `let`/`const`/arrow/módulos). Anos: **a.C. positivo,
   d.C. negativo**; não existe ano 0.
5. Nunca commitar vídeos, quadros ou o `.cache` (já ignorados por `vídeos/.gitignore` e
   `scripts/mapa-geral/.cache/.gitignore`).
6. **Não alterar** nada em `frontend/mapa/`, `frontend/mapas/` (exceto o link que já existe) e
   `frontend/linha-do-tempo/`.
7. Vídeos são de terceiros: usados como referência (formas e nomes), com créditos em `docs/mapa-geral.md` e em
   `indice.json`. Nenhum quadro é publicado.
8. `node scripts/verificar.mjs` passa ao fim de toda etapa que mexe em `frontend/`.

## 4. Ambiente

- Linux, 16 núcleos, 15 GB de RAM, ~110 GB livres em `/data`. Shell padrão do usuário: fish (use `bash -c` para
  sintaxe bash).
- Há `ffmpeg`, `tesseract` 5.5 (só `eng`), `node`, `google-chrome-stable`, `uv`. **Não há `pip`**; o Python do sistema
  (3.14) não tem bibliotecas. Elas estão em `~/.cache/mapa-biblia-lib/lib` (numpy 2.5, opencv 5.0, shapely 2.2
  com GEOS 3.14, Pillow). Use `PYTHONPATH=~/.cache/mapa-biblia-lib/lib python3 ...`. Se faltar algo:
  `uv pip install --target ~/.cache/mapa-biblia-lib/lib <pacote>`.
- GEOS 3.14 traz `shapely.coverage_simplify`, `shapely.coverage_is_valid` e `shapely.coverage_invalid_edges`
  (simplificação e validação de **coberturas** que preservam a borda comum). Use-os.
- Chrome headless: **sempre** `--user-data-dir=<tmp novo>` **e** `--disk-cache-dir=<tmp novo>` (o Chrome desta
  máquina tem cache HTTP compartilhado em `/dev/shm` e pode servir arquivo velho mesmo com perfil novo). Use uma
  porta de servidor diferente de 8765 (a do `verificar.mjs`).
- Servidor local: `cd frontend && python3 -m http.server <porta> --bind 127.0.0.1`. O Service Worker
  (`frontend/sw.js`) guarda tudo que a página busca; ao mudar dados, troque `VERSAO` em `sw.js`.
- Vídeo principal: `vídeos/History of the World： Every Year [hzWwp9JM7Hw].webm` (AV1, 1920×960, 29,97 fps,
  1043,7 s). Use `glob('*hzWwp9JM7Hw*.webm')`, o nome tem caracteres especiais.
- O `.cache` atual (`scripts/mapa-geral/.cache/`, 102 MB: quadros de 1 s em JPEG, calibração, estados dos 79 anos)
  pode ser reaproveitado só como referência; a v2 gera o seu próprio cache em subpastas novas.

## 5. Arquitetura da versão 2

```
vídeo (1920×960, todos os quadros)
  E2 quadros.py    → .cache/v2/anos.json (ano → quadros, hash do mapa)  + .cache/v2/mapas/<hash>.png (mapas distintos)
  E3 calibrar.py   → .cache/v2/calibracao.json (por hash/trecho de enquadramento)
  E4 rotular.py    → .cache/v2/rotulos/<hash>.png (rótulo por pixel, 16 bits) + <hash>.json (regiões, cor, tipo)
  E5 vetorizar.py  → .cache/v2/vetores/<hash>.json (cobertura em lon/lat, por região)
  E6 rastrear.py   → .cache/v2/entidades.json (id persistente de cada região em cada ano)
  E7 nomear.py     → .cache/v2/nomes-lidos.json (OCR votado) + scripts/mapa-geral/nomes.json (tradução pt-BR, à mão)
  E8 construir.py  → frontend/mapa-geral/dados/indice.json + dados/blocos/<a|d><ano>.json
  E9 página        → frontend/mapa-geral/ (passo de 1 ano)
  testar.py e0…e10 → testes automáticos;  revisar.py → imagens de revisão em .cache/v2/revisao/
```

Execução incremental (cache por etapa, chaves, amostras `rapida`/`media`, testes T-C1–T-C6):
**`docs/mapa-geral-incremental.md`**.

Princípio central: **o trabalho é feito por mapa distinto, não por ano.** Como o mapa só muda quando uma fronteira
muda, vários anos seguidos têm o mesmo hash; cada hash é calibrado, rotulado e vetorizado uma vez, e anos com o
mesmo hash recebem **geometria idêntica** (sem tremedeira na animação, e os dados ficam pequenos).

Scripts da v1 que serão substituídos e apagados na E10: `extrair.py`, `indexar.py`, `gerar.py`, `segmentar.py`,
`agrupar.py`, `folha.py` (e `__pycache__/`). `calibrar.py`, `nomear.py`, `nomes.json` e `construir.py` são reescritos.

## 6. Etapas

### E0. Preparação e linha de base

**Objetivo:** garantir que nada fora do mapa geral muda, e ter a estrutura de testes.

Tarefas:
1. Remover `scripts/mapa-geral/__pycache__/` do git (foi commitado por engano: `git rm -r --cached`) e criar
   `.gitignore` na raiz com `__pycache__/`.
2. **Linha de base dos 27 mapas antigos:** com `git worktree add <tmp> 8186a61` (commit anterior à v1 do mapa geral),
   servir o worktree e o diretório atual em portas diferentes e capturar `/mapa/?m=<id>` de **todos** os mapas de
   `frontend/mapas/mapas.json` em 1280×800 (Chrome headless, perfil e cache novos). Comparar par a par
   (diferença de pixels).
   - Se houver diferença por causa da troca para `projecao.js` em `mapa.js`: corrigir até ficar idêntico ou, se não
     for trivial, **restaurar** `frontend/mapa/mapa.js` e `frontend/mapa/index.html` da versão `8186a61` (decisão do
     usuário: mapas antigos como estavam). Registrar o que foi feito.
   - Guardar as capturas de referência em `.cache/v2/base-mapas/` para a E10.
3. Criar `scripts/mapa-geral/testar.py` com subcomandos `e0` … `e10` (cada um imprime `OK`/`FALHA` por teste, com
   números, e sai com código ≠ 0 se algo falhar) e `scripts/mapa-geral/revisar.py` (gera imagens de revisão).
4. Criar `scripts/mapa-geral/casos.json`: **casos de referência** (ponto conhecido → o que deve estar lá), usados em
   E4, E5, E6, E7 e E8. Cada caso: `{"ano", "lon", "lat", "espera": "estado"|"sem-dono"|"mar", "nome_video",
   "nome", "cor_aprox"}`. Comece com estes (coordenadas **aproximadas**: confirme cada uma no quadro e ajuste antes
   de usar) e amplie para **≥ 60 casos**, cobrindo as 5 épocas de enquadramento, estados escuros, creme, pequenos e
   o antimeridiano:

   | Ano | Lon, lat | Esperado (vídeo) |
   |---|---|---|
   | 584 a.C. | 44,4, 32,5 | Babylon (vermelho) |
   | 584 a.C. | 52, 36 | Medes (verde) |
   | 584 a.C. | 30, 39 | Lydia (laranja) |
   | 584 a.C. | 31, 27 | Egypt (amarelo) |
   | 584 a.C. | 32,5, 18 | Kush (creme) |
   | 584 a.C. | 25, 5 | sem dono |
   | 999 d.C. | 10, 50 | Holy Roman Empire (cinza-escuro) |
   | 999 d.C. | 32, 39 | Byzantine Empire (roxo) |
   | 999 d.C. | 72, 42 | Qarakhanids (creme, separado de Qocho/Yutian só por linha) |
   | 999 d.C. | 113, 30 | Song (vermelho) |
   | 1799 d.C. | 33, 39 | Ottomans (verde-petróleo escuro) |
   | 1799 d.C. | 90, 60 | Russia (amarelo) |
   | 1799 d.C. | −150, 64 | Russian America (antimeridiano) |
   | 1799 d.C. | −50, −10 | Brazil (verde) |

Testes `testar.py e0`:
- T0.1 `git ls-files scripts/mapa-geral/__pycache__` vazio.
- T0.2 Os 27 mapas: diferença de pixels entre base (`8186a61`) e atual **= 0** (ou ≤ 0,1 % dos pixels, só
  antialiasing, com a imagem de diferença examinada).
- T0.3 `casos.json` válido, ≥ 60 casos, todos com ano dentro de 2500…−2025, nenhum com ano 0.
- T0.4 `node scripts/verificar.mjs` passa.

Portão: T0.1–T0.4 OK; relatório ao usuário com o resultado da comparação dos mapas antigos.

### E1. Separar o mapa geral dos mapas antigos

**Objetivo:** cortar já, e de forma testável, qualquer dependência do mapa geral em relação aos mapas antigos.
(As etapas seguintes reescrevem `construir.py`; esta etapa garante a regra desde o começo.)

Tarefas:
1. Em `construir.py` (e em qualquer script de `scripts/mapa-geral/`): remover a leitura de `territorios-*.json`,
   de `frontend/mapa/mapa.js` (`cores_regiao`/`CORES_REGIAO`), de `roma.json` e de `scripts/mapa/formas.json`, e o
   tratamento especial de `israel`/`fenicia`. A única coisa de `frontend/mapa/` que o mapa geral pode ler é
   **`mundo.json`** (costa). `scripts/mapa/tremor.py` continua sendo usado (é a regra de borda, não um mapa).
2. Remover o campo `cor` de `nomes.json` (a cor passa a vir do vídeo; ver E7).
3. Rodar a versão atual de `construir.py` (ainda 79 anos) para ter um "antes/depois" rápido e mostrar ao usuário
   586 a.C. e 1000 a.C. já sem os mapas antigos.

Testes `testar.py e1`:
- T1.1 `grep -rnE "territorios-|CORES_REGIAO|mapa\.js|roma\.json|formas\.json" scripts/mapa-geral/*.py` **vazio**.
- T1.2 Em `frontend/mapa-geral/mapa-geral.js`, nenhuma URL fora de `/mapa-geral/dados/`, `/mapa/mundo.json` e
  `/compartilhado/`.
- T1.3 Para cada arquivo de ano gerado, nenhum polígono é igual ou quase igual (IoU ≥ 0,9) a um polígono de
  `frontend/mapa/territorios-<ano>.json` do mesmo ano (detecta cópia dos mapas antigos).
- T1.4 `git diff --stat 8186a61 -- frontend/mapa frontend/linha-do-tempo` só mostra o que a E0 decidiu manter
  (idealmente nada).

Portão: T1.1–T1.4 OK; capturas de 586 a.C. (antes/depois) ao usuário.

### E2. Quadros de ano a ano

**Objetivo:** para cada um dos 4.525 anos, saber quais quadros o mostram e ter **um mapa exato** desse ano.

Tarefas (`scripts/mapa-geral/quadros.py`):
1. Decodificar o vídeo **inteiro, em resolução nativa (1920×960), todos os quadros**, por pipe
   (`ffmpeg -f rawvideo -pix_fmt bgr24 -`), sem gravar 31 mil imagens em disco. Para cada quadro:
   - recortar a caixa do ano (no quadro de 1920 px a faixa é ~y 861–903; a caixa se desloca na horizontal conforme
     o enquadramento: localize pelas bordas verticais da moldura, como `recorte_texto` de `extrair.py`, com
     coordenadas ×1,5);
   - calcular o **hash da área do mapa** (quadro inteiro com a caixa do ano e o ornamento mascarados; ex.: SHA-1 dos
     bytes) e o **hash da caixa do ano**.
2. OCR **só nas caixas distintas** (o texto muda a cada ~3 quadros, ~4.600 caixas distintas no total, não 31 mil):
   tesseract `--psm 7` com lista de caracteres `0123456789BC `, como em `extrair.py`. Alternativa mais robusta
   (recomendada se o OCR errar > 1 %): montar modelos dos dígitos da própria fonte do vídeo e casar por
   template.
3. Montar a sequência: corrida de quadros com a mesma caixa = um ano. Corrigir leituras isoladas pela sequência
   (os anos descem de 1 em 1: 2500 BC, 2499 BC, …, 1 BC, 1, 2, …, 2025; "sem sufixo" = d.C.). Verificar como o
   vídeo passa de 1 a.C. para 1 d.C. (se mostrar "0", descartar esse ano e registrar).
4. Mapa de cada ano: o mapa do **último quadro** da corrida do ano (estado no fim do ano). Registrar os anos em que
   o mapa muda **no meio** da corrida (contagem) e anos cujos quadros estão em **animação de zoom** (hash muda a
   cada quadro, ver E3).
5. Gravar cada **mapa distinto** uma única vez, em PNG sem perdas: `.cache/v2/mapas/<hash>.png`. Gravar
   `.cache/v2/anos.json`: `{"<ano>": {"quadros": [i0, i1], "hash": "...", "zoom": false, "meio": false}}`.
6. Primeiros e últimos segundos (introdução, fade, créditos): identificar e excluir; o primeiro ano útil deve ser
   2500 a.C. e o último 2025 d.C.

Saída esperada: 4.525 anos, provavelmente 1.000–4.000 mapas distintos (meça e informe), poucos GB em PNG.

Testes `testar.py e2`:
- T2.1 Exatamente **4.525 anos**: 2500…1 (a.C.) e −1…−2025 (d.C.), sem repetição, sem ano 0, sem buraco.
- T2.2 Todo ano tem ≥ 1 quadro; listar anos com 1 quadro só (aceitável, mas informar quantos).
- T2.3 Sequência monotônica: o índice do primeiro quadro cresce estritamente com o tempo.
- T2.4 Anos inferidos (OCR falhou, ano deduzido pela sequência) ≤ 1 %; listar todos.
- T2.5 Todo `hash` de `anos.json` tem PNG em `.cache/v2/mapas/`, com 1920×960.
- T2.6 Folha de contato com **40 caixas de ano sorteadas** (imagem da caixa + ano lido): abrir e conferir; 0 erros.
- T2.7 Anos em que o mapa muda no meio da corrida: contagem informada; folha com 5 exemplos (primeiro × último
  quadro).

Revisão visual: `revisar.py e2` → folha das caixas (T2.6) e gráfico "anos por segundo de vídeo" (deve bater com
~9–10 anos/s no início e ~2 anos/s no fim).

Portão: T2.1–T2.7 OK; informar ao usuário quantos mapas distintos existem e o espaço usado.

### E3. Calibração por enquadramento

**Objetivo:** para cada mapa distinto, a transformação exata pixel → (lon, lat).

Tarefas (reescrever `scripts/mapa-geral/calibrar.py`):
1. O vídeo usa a **cilíndrica de Miller** (medido na E3; a v1 supunha Mercator) e o enquadramento é constante por
   trechos (5 trechos; a tabela de `docs/mapa-geral.md` é só o ponto de partida: escalas da v1 ×1,5 para 1920 px,
   com Y0 reconvertido para Miller). Modelo: `u = (lon+180)·S − X0`, `v = (miller(80) − miller(lat))·S − Y0`,
   `miller(lat) = 1,25·ln tan(45° + 0,4·lat)` em graus. Detectar os trechos pela **máscara de mar** dos mapas
   distintos (ela só muda quando o enquadramento muda).
2. Por trecho: calibração fina em 1920 px (casamento da máscara de terra do vídeo com a terra de `mundo.json`
   renderizada em **Miller**; refinar escala e deslocamento com subpixel; a mudança de escala mantém fixo o
   ponto sob o centro do quadro). Só os Grandes Lagos de `mundo.json` entram na máscara (os outros lagos não são
   desenhados no vídeo). Conferir que os mapas do trecho dão o mesmo resultado.
3. Mapas de **animação de zoom** (E2): calibração por mapa (busca de escala/deslocamento a partir dos trechos
   vizinhos). Se um ano só existir em animação, usar o quadro da corrida com melhor escore.
4. **Antimeridiano:** quando o quadro mostra mais de 360° de longitude ou passa de ±180°, registrar o intervalo de
   longitude do quadro; a conversão deve produzir longitudes contínuas, que a E5 normaliza.
5. Gravar `.cache/v2/calibracao.json`: `{"trechos": [...], "por_hash": {"<hash>": {"S", "X0", "Y0", "escore",
   "residuo_px"}}}`.

Testes `testar.py e3`:
- T3.1 Todo hash tem calibração.
- T3.2 **Resíduo de costa**: para cada trecho (e para 20 mapas de zoom sorteados), distância entre as bordas de costa
  do vídeo (borda da máscara de mar) e a costa de `mundo.json` projetada com a calibração: **mediana ≤ 2 px e
  percentil 90 ≤ 6 px** (em 1920 px). Informar os valores por trecho.
- T3.3 Escala e deslocamento iguais (diferença ≤ 0,2 %) entre mapas do mesmo trecho.
- T3.4 Nenhum hash com escore abaixo do mínimo do seu trecho − 0,05 sem estar marcado como zoom.

Revisão visual: `revisar.py e3` → para cada trecho, o quadro com a costa de `mundo.json` desenhada por cima em
vermelho, com recortes ampliados do Mediterrâneo, do Golfo Pérsico e de uma costa recortada (Grécia ou Noruega).
Abrir e conferir o alinhamento.

Portão: T3.1–T3.4 OK.

### E4. Rotulagem: um rótulo por pixel (partição do mapa do vídeo)

**Objetivo:** para cada mapa distinto, uma imagem de rótulos em que **todo pixel de terra** pertence a exatamente uma
região (estado ou "sem dono"), incluindo estados creme, escuros e cinza, sem buracos de texto e sem frestas de linha.

Tarefas (`scripts/mapa-geral/rotular.py`):
1. **Medir a paleta antes de codificar** (`.cache/v2/paleta.json`, com a evidência): em 6 mapas de épocas
   diferentes, amostrar e registrar as cores exatas de mar, lagos, terra sem dono (branco), estados creme (vários),
   linhas de contorno (cinza), costa, texto preto, texto branco e a caixa do ano. Já medido nesta sessão (1920 px):
   mar = RGB 216,225,237; sem dono = 255,255,255 (com variações 253–255); Cuxe 584 a.C. = 254,248,238; Sacro Império
   999 d.C. ≈ 77,83,91. Confirme e complete.
2. Máscaras por pixel:
   - **mar** (inclui lagos azul-claros): cor a ≤ L1 limiar do mar;
   - **linhas**: pixels finos, mais escuros que os vizinhos e de baixa saturação, que separam regiões (contornos de
     estados creme e costa). Detectar por cor + espessura (abertura morfológica / "top-hat" escuro), não só por cor;
   - **texto**: componentes pequenos de alto contraste (preto sobre claro, branco sobre cor), com formato de letra.
     Guardar as caixas de texto (vão para o OCR da E7);
   - **ornamentos**: caixa do ano e qualquer elemento fixo da tela (máscara fixa, medida uma vez).
3. **Regiões:** sobre o que não é mar, linha, texto nem ornamento, componentes conexos **de cor uniforme**
   (vizinho entra se a diferença de cor ≤ limiar medido na tarefa 1). Assim: estados coloridos vizinhos se separam
   pela cor; estados creme vizinhos se separam pela linha; creme e branco se separam pela cor (limiar fino) **e** pela
   linha.
   - **Nada de descartar escuros**: cinza-escuro, verde-escuro e marrom são estados. Só texto e linhas são removidos,
     e por forma, não por brilho.
   - Classificar cada região: `estado` (cor ≠ branco puro, ou branca/creme fechada por contorno e com nome dentro) ou
     `sem-dono` (branco puro, sem contorno próprio). Registre a regra exata no cabeçalho do script.
4. **Preencher linhas e texto:** cada pixel de linha/texto/ornamento que fica em terra recebe o rótulo da região mais
   próxima (expansão por distância ou `cv2.watershed` com as regiões como sementes). Resultado: partição sem frestas
   da terra do vídeo.
5. **Costa:** estender os rótulos, pela mesma expansão, por uma faixa de até N px (≈ 8 px em 1920) sobre o **mar do
   vídeo** que é **terra em `mundo.json`** (máscara de terra renderizada com a calibração). Isso substitui o
   `buffer(0.15)` da v1. O corte exato pela costa fica para a E5.
6. Regiões com menos de ~40 px (em 1920) que não sejam ilhas: fundir no vizinho com maior borda comum.
7. Gravar `.cache/v2/rotulos/<hash>.png` (16 bits) e `<hash>.json`:
   `{"regioes": [{"r": 1, "tipo": "estado"|"sem-dono", "cor": [R,G,B], "area_px", "caixa", "texto": [[x,y,w,h], ...]}]}`.
   Processar em paralelo (≤ 8 processos; ~1–3 s por mapa).

Testes `testar.py e4`:
- T4.1 **Cobertura**: nos pixels de terra do vídeo (não mar), 100 % têm rótulo; pixels de cor "de estado" (fora da
  paleta de mar/branco/linha/texto) que ficaram como `sem-dono`: **≤ 0,3 %** por mapa.
- T4.2 **Casos de referência** (`casos.json`, com a calibração da E3): no pixel do caso, o tipo bate (estado / sem
  dono / mar) em **100 %** dos casos, e os casos de estados diferentes no mesmo ano caem em regiões diferentes.
- T4.3 **Escuros e creme presentes**: Sacro Império 999, Otomanos 1799, Cuxe 584 a.C., Caracânidas/Qocho/Yutian 999
  existem como regiões **separadas** (três regiões diferentes para os três cremes vizinhos).
- T4.4 **Sem buracos de texto**: nenhuma região de estado tem buraco interno (anel interior) de área > 30 px que não
  seja outra região real.
- T4.5 **Estabilidade de cor**: a cor de cada região é a mediana dos seus pixels; desvio padrão interno ≤ limiar
  (detecta regiões que juntaram dois estados de cores próximas).
- T4.6 Desempenho: tempo total informado.

Revisão visual: `revisar.py e4` → para 12 mapas (2 por trecho de enquadramento + 584 a.C., 999 d.C., 1799 d.C.,
2025 d.C.): à esquerda o quadro, à direita as regiões coloridas com **cores aleatórias contrastantes** (para ver
divisões) e as bordas em preto; recortes ampliados do Oriente Médio, Europa e Ásia Central. Abrir todas e
listar defeitos.

Portão: T4.1–T4.6 OK e revisão sem defeito grave. **Mostrar ao usuário** 999 d.C. e 1799 d.C. (as épocas que mais
falharam na v1) antes de seguir.

### E5. Vetorização em cobertura (bordas corretas)

**Objetivo:** transformar a imagem de rótulos em polígonos lon/lat que seguem todas as regras de borda.

Tarefas (`scripts/mapa-geral/vetorizar.py`):
1. **Contornos exatos por pixel** de cada região (bordas entre pixels, não centros: `cv2.findContours` gera
   contornos que não coincidem entre vizinhos; prefira extrair a fronteira entre rótulos como arestas da grade de
   pixels, por exemplo com `rasterio.features.shapes` se instalar `rasterio`, ou uma rotina própria). Resultado:
   polígonos que já formam uma cobertura perfeita em pixels.
2. Converter vértices de pixel para lon/lat com a calibração (Miller inversa: `lat = (atan(exp(rad(y/1,25))) − 45°)/0,4`;
   `E3` guarda S, X0 e Y0 por mapa; `calibrar.py` tem a função direta). A cobertura continua válida (a
   transformação é monotônica).
3. **Simplificar como cobertura:** `shapely.coverage_simplify(polígonos, tolerância)` com tolerância ~0,4–0,8 px
   convertido para graus (medir o melhor valor na revisão). Isso substitui o Douglas-Peucker por polígono da v1 e
   mantém a borda comum idêntica.
4. **Tremor:** aplicar `tremer()` de `scripts/mapa/tremor.py` a cada anel. Como a borda comum tem os mesmos
   vértices nos dois polígonos e o tremor é determinístico por lado (independe do sentido), a borda continua
   idêntica. Testar (T5.3).
5. **Costa:** intersectar cada polígono com a terra de `mundo.json` (mesmo método de `carregar_terra()` da v1:
   soma par-ímpar dos anéis de `terra` menos os `mar`). Fica a costa exata. Pedaços de estado que caem no mar de
   `mundo.json` somem.
6. **Antimeridiano:** normalizar longitudes para [−180, 180]: cortar polígonos em ±180, deslocar ±360 e unir os
   pedaços da mesma região (o Alasca aparece nas duas pontas do quadro: unir as duas cópias e não duplicar).
7. Saída `.cache/v2/vetores/<hash>.json`: `{"regioes": {"<r>": {"tipo", "aneis"}}}` com 2 casas decimais.
   Arredondar **depois** de validar e conferir que o arredondamento não cria sobreposição (se criar, arredondar os
   vértices compartilhados uma vez só, por tabela de vértices).

Testes `testar.py e5` (em todos os hashes; números agregados + piores casos):
- T5.1 Todos os polígonos `is_valid`, sem anéis com < 4 pontos.
- T5.2 **Cobertura válida**: `shapely.coverage_is_valid` verdadeiro (antes do corte pela costa) e, depois do corte,
  soma das áreas = área da união (diferença ≤ 1e-6 grau²); interseção par a par com área ≤ 1e-6.
- T5.3 **Borda comum única**: para cada par de regiões vizinhas na imagem de rótulos, `a.intersection(b)` é linha
  (não área) com comprimento ≥ 80 % do comprimento da fronteira em pixels convertida para graus.
- T5.4 **Sem frestas**: buracos na união de todas as regiões (estados + sem dono) que estão em terra de `mundo.json`:
  nenhum com área > 0,01 grau².
- T5.5 **Costa exata**: `estado.difference(terra).area ≤ 1e-6` para todo estado; e todo vértice de estado a menos de
  0,05° da costa está exatamente sobre ela (distância ≤ 1e-6).
- T5.6 **Só retas**: maior segmento interno (fora da costa) ≤ 0,5°; nenhuma sequência de ≥ 8 vértices com curvatura
  constante (detector de arco). Não pode haver `buffer` com junção redonda no código (`grep` por `buffer(` sem
  `join_style=2`).
- T5.7 **Fidelidade ao vídeo**: rasterizar os polígonos de volta no espaço do quadro (calibração) e comparar com a
  imagem de rótulos (excluindo da comparação os pixels dos lagos de `mundo.json` que o vídeo não desenha: Baikal,
  Vitória, Balkhash etc.; eles viram buracos nos estados ao cortar pela costa, o que está certo porque o site desenha
  esses lagos): IoU por estado **≥ 0,92** para estados ≥ 2.000 px, **≥ 0,80** para 200–2.000 px; concordância
  global nos pixels que são terra nos dois (vídeo e `mundo.json`) **≥ 97 %**. Listar os 20 piores estados.
- T5.8 Longitudes todas em [−180, 180]; caso do Alasca (1799) é um estado só.
- T5.9 Casos de referência (`casos.json`): ponto dentro do polígono certo em 100 %.

Revisão visual: `revisar.py e5` → para os 12 mapas da E4: polígonos desenhados em **Equal Earth** (como no site)
com contorno fino preto e as cores do vídeo, e ao lado o quadro original no mesmo recorte. Recortes ampliados:
Levante e Mesopotâmia, Grécia/Egeu, Europa central, Índia, Ásia Central (creme), antimeridiano. Procurar frestas
brancas entre vizinhos, dentes, bordas duplas, buracos de texto, ilhas faltando.

Portão: T5.1–T5.9 OK, revisão limpa. **Mostrar ao usuário** recortes ampliados de 3 anos (um antigo, um medieval,
um moderno) lado a lado com o vídeo.

### E6. Rastreamento entre anos (ids persistentes) e estabilidade

**Objetivo:** dar a cada estado um id que dura toda a vida dele, e garantir que a animação não "treme".

Tarefas (`scripts/mapa-geral/rastrear.py`):
1. Percorrer os anos em ordem (2500 a.C. → 2025). Entre o mapa do ano N e o do ano seguinte: se o hash é o mesmo,
   as regiões são as mesmas (mesmos ids). Se mudou, casar regiões por **sobreposição** (IoU numa grade comum de
   0,1°) **e** cor (distância L1 ≤ limiar): a região do ano seguinte herda o id da região com maior sobreposição de
   mesma cor. Divisões: o maior pedaço herda o id, os outros ganham ids novos. Fusões: herda o id do maior.
   Mudança de cor com a mesma forma (o vídeo recolore um estado): mesmo id se IoU ≥ 0,8, registrar.
2. Uma mesma cor reutilizada por estados diferentes em épocas diferentes (ex.: verde de Elão e depois dos partas)
   **não** pode virar o mesmo id: só herda id quem existia no ano anterior.
3. Gravar `.cache/v2/entidades.json`: `{"<ent>": {"anos": [de, ate], "cor": "#rrggbb" (mediana da vida),
   "trechos": [[ano_de, ano_ate, hash, r], ...]}}`.
4. **Estabilidade de geometria:** como a geometria é por hash, anos com o mesmo hash já são idênticos. Além disso,
   quando o hash muda só por causa de uma região (ex.: uma fronteira na Índia), as outras regiões não devem mudar:
   se a região tem os mesmos pixels nos dois mapas (máscara idêntica), reutilizar o vetor anterior.
   Atenção: o reaproveitamento não pode quebrar a cobertura com o vizinho que mudou (se a borda comum mudou, os dois
   são recalculados).

Testes `testar.py e6`:
- T6.1 Nenhum ano tem dois estados com o mesmo id.
- T6.2 **Sem piscar**: nenhum id some num ano e volta no seguinte (ausente em N, presente em N−1 e N+1), salvo se o
  vídeo fizer isso (conferido por máscara); listar.
- T6.3 Entidades com vida < 3 anos: listar (esperado: poucas; conferir 10 numa folha).
- T6.4 **Estabilidade**: para todo par de anos seguidos, toda região cuja máscara de pixels não mudou tem geometria
  **idêntica** (mesmos números). 100 %.
- T6.5 Casos de referência: o mesmo estado em anos próximos (ex.: Bizâncio em 999 e 1000) tem o mesmo id; Elão
  (antes de 540 a.C.) e Pártia têm ids diferentes.
- T6.6 Contagem de entidades por século (informar; picos estranhos indicam fragmentação).

Revisão visual: `revisar.py e6` → "filme" de 12 quadros seguidos em 3 trechos (ex.: 1200–1189 a.C., 30–41 d.C.,
1914–1925) com o id escrito no centro de cada estado; conferir que ids não trocam.

Portão: T6.1–T6.6 OK.

### E7. Nomes (todas as épocas) e cores do vídeo

**Objetivo:** cada entidade com nome em pt-BR, tirado das etiquetas do próprio vídeo, e a cor do vídeo.

Tarefas:
1. **OCR das etiquetas** (`scripts/mapa-geral/nomear.py`, reescrito): para cada mapa distinto, recortar as caixas de
   texto da E4, agrupar letras em palavras/linhas (etiquetas com 2 linhas, ex. "Holy / Roman / Empire"), ampliar
   (3–4×), binarizar (texto preto e texto branco tratados à parte) e rodar tesseract `eng --psm 7`. Associar cada
   etiqueta à região que contém o centro dela (ou a mais próxima, ≤ 30 px em 1920; etiquetas sobre o mar, como
   "Akbhazia", vão para a região mais próxima).
2. **Votação por entidade:** juntar as leituras de todos os anos da entidade. Como o nome pode mudar ao longo da vida
   (ex.: "Kingdom of X" → "X Empire"), votar por **trechos**: nome = leitura mais frequente numa janela, com
   correção ortográfica contra a lista de nomes já vistos (distância de edição ≤ 2). Abreviações do vídeo ("Eng.",
   "Scot.", "Cr.", "B.", "HRE") ficam marcadas para tradução manual.
3. `scripts/mapa-geral/nomes.json` (novo formato, editado à mão pelo agente, conferindo nos quadros):
   ```json
   {"_ajuda": "...",
    "traducoes": {"Byzantine Empire": "Império Bizantino", "Holy Roman Empire": "Sacro Império Romano-Germânico",
                  "HRE": "Sacro Império Romano-Germânico", "Medes": "Medos", "Babylon": "Babilônia", ...},
    "entidades": {"<ent>": {"nome": "...", "nota": "..."}}}
   ```
   `traducoes` resolve a maioria; `entidades` corrige casos específicos (OCR ruim, nome ambíguo, abreviação).
   Use exônimos consagrados em português (Babilônia, Império Aquemênida, Califado Abássida, Sacro Império
   Romano-Germânico, Império Otomano, Dinastia Song, Grão-Ducado de Moscou, Estados Unidos). Na dúvida entre nomes,
   use o que o vídeo mostra, traduzido, e anote em `nota`.
4. **Cores:** a cor de cada entidade = mediana da cor do vídeo ao longo da vida (E6). Não há paleta fixa nem cor dos
   mapas antigos. Conferir contraste no tema escuro do site (se precisar, a página ajusta opacidade, mas o tom é do
   vídeo).
5. Estados sem nome lido em lugar nenhum: nome vazio só se forem minúsculos (< 2 grau²); acima disso, procurar a
   etiqueta à mão (folha da região) e preencher em `entidades`.

Testes `testar.py e7`:
- T7.1 **Área nomeada**: por século, ≥ 98 % da área de estados ≥ 5 grau² tem nome; ≥ 90 % do número de estados
  ≥ 1 grau² tem nome. Informar por época.
- T7.2 **Português**: nenhum nome publicado contém palavras em inglês da lista (`Empire`, `Kingdom`, `of`,
  `Sultanate`, `Khanate`, `Dynasty`, `Republic`, `Caliphate`, `Emirate`, `Duchy`, `States`…) nem abreviação com
  ponto final.
- T7.3 Nenhum ano com dois estados de mesmo nome que não sejam o mesmo id (ex.: dois "Egito"), salvo exceções
  listadas em `nomes.json` com `nota`.
- T7.4 Casos de referência: nome bate em 100 %.
- T7.5 **Amostra conferida**: folha com 60 estados sorteados (recorte do vídeo com a etiqueta + nome atribuído);
  abrir e conferir; erros ≤ 2 e todos corrigidos antes do portão.
- T7.6 Cores: toda entidade tem `#rrggbb`; distância entre a cor publicada e a mediana do vídeo ≤ 6 (L1).

Portão: T7.1–T7.6 OK; mostrar ao usuário a lista de traduções (as 100 entidades mais duradouras) para aprovação.

### E8. Dados do site (formato ano a ano)

**Objetivo:** gravar os 4.525 anos num formato pequeno, carregado sob demanda.

Formato (versão 2):
- `frontend/mapa-geral/dados/indice.json`:
  ```json
  {"versao": 2, "de": 2500, "ate": -2025, "bloco": 25,
   "estados": {"<id>": {"nome": "Império Bizantino", "nome_video": "Byzantine Empire", "cor": "#5b3a7a",
               "desde": -395, "ate": -1453, "nota": ""}},
   "fonte": "texto de crédito"}
  ```
  A sequência de anos é implícita: 2500…1, −1…−2025 (sem 0), posição i = 0…4524.
- `frontend/mapa-geral/dados/blocos/<a|d><ano>.json`: um arquivo por bloco de 25 posições da sequência, com nome do
  primeiro ano do bloco (ex.: `a2500.json` = 2500–2476 a.C.).
  ```json
  {"anos": [2500, 2476],
   "formas": [{"id": "egito", "de": 2500, "ate": 2490, "aneis": [[[31.21, 30.05], ...]]}, ...]}
  ```
  Cada forma vale de `de` a `ate` (inclusive, `de` ≥ `ate`, recortado ao bloco). Uma forma nova só é gravada quando a
  geometria muda (E6 garante que geometria igual é idêntica). Os ids são os de `indice.json`.
- Apagar os arquivos `a<N>.json`/`d<N>.json` da v1.

Tarefas (`scripts/mapa-geral/construir.py`, reescrito; só lê `.cache/v2/`, `nomes.json` e `mundo.json`):
1. Montar as formas por bloco; 2 casas decimais; ids legíveis (`slug` do nome pt-BR + sufixo numérico se repetir,
   ex.: `egito`, `egito-2`), estáveis entre execuções.
2. Orçamento (medir e informar, sem e com gzip): **≤ 400 KB por bloco** (≤ 100 KB com gzip) e total razoável. Se o
   total passar de **80 MB** sem gzip, **parar e perguntar ao usuário** (opções: simplificar mais, blocos maiores,
   menos casas decimais em zoom distante).
3. Trocar `VERSAO` em `frontend/sw.js` (descarta o cache antigo dos dados da v1).

Testes `testar.py e8`:
- T8.1 Esquema: todo bloco existe para as 181 posições de bloco (4.525 / 25), anos corretos, nenhum ano 0; todo id
  das formas está em `indice.json`.
- T8.2 **Reconstrução**: para todo ano, as formas válidas naquele ano (via blocos) são exatamente as da E5/E6
  (mesmo conjunto de ids, mesma geometria após arredondamento).
- T8.3 Para todo ano: sem sobreposição entre formas (área ≤ 1e-6), formas válidas (repete T5.2 nos dados finais).
- T8.4 Casos de referência nos **dados finais**: 100 %.
- T8.5 Nenhum dado vindo dos mapas antigos (repete T1.3 em todos os anos que têm `territorios-<ano>.json`).
- T8.6 Tamanhos dentro do orçamento; informar total, maior bloco e média.

Portão: T8.1–T8.6 OK.

### E9. Página ano a ano

**Objetivo:** `frontend/mapa-geral/` navega de ano em ano, de 2500 a.C. a 2025 d.C.

Tarefas (`mapa-geral.js`, `index.html`, `mapa-geral.css`; ES5/IIFE; ler o cabeçalho do script antes de mexer):
1. Ler `indice.json` v2; a linha do tempo tem **4.525 posições** (uma por ano). Rótulo "586 a.C." / "30 d.C.".
2. Carregar o bloco do ano pedido (e pré-carregar o próximo durante a reprodução); manter um cache dos blocos já
   carregados (limite de ~20 blocos em memória).
3. Ao trocar de ano, **só atualizar o que mudou** (formas que começam/terminam; reaproveitar `<path>` com o mesmo
   id e geometria).
4. Controles: anterior/próximo = **1 ano**; teclado ←/→ (1 ano) e Shift+←/→ (10 anos); controle deslizante;
   campo para digitar um ano (aceita "586 a.C.", "-586", "30 d.C."); reprodução com velocidades (ex.: 5, 10, 25
   anos/s). `?ano=-30` abre **exatamente** em 30 d.C. e a URL acompanha o ano atual (sem encher o histórico).
5. Nomes e cartão de informação (nome pt-BR, período `desde`–`ate`, nota) como hoje; cores do vídeo.
6. Atualizar o cabeçalho do script (dados lidos, formato v2) e o texto da página (hoje diz "O mundo antigo";
   agora vai até 2025).
7. Acrescentar a `PAGINAS` de `scripts/verificar.mjs`: `mapa-geral/?ano=2500`, `mapa-geral/?ano=586`,
   `mapa-geral/?ano=-1000`, `mapa-geral/?ano=-2025` (verificação: `.geral-estado` > 0).
8. Criar `scripts/mapa-geral/testar-pagina.mjs` (mesma técnica de `verificar.mjs`, Chrome via CDP, perfil e cache
   novos) para os testes de interação abaixo.

Testes:
- T9.1 `node scripts/verificar.mjs` passa (1280 e 360 px, sem erro de console, sem rolagem lateral).
- T9.2 `testar-pagina.mjs`: `?ano=586` mostra "586 a.C."; → mostra "585 a.C."; `?ano=1` e → mostra "1 d.C.";
  `?ano=2500` e ← não sai do intervalo; `?ano=-2025` é o último; 30 anos sorteados abrem com o rótulo certo e
  `.geral-estado` > 0.
- T9.3 Reprodução por 5 s a 10 anos/s: o ano avança 45–55 anos, sem erro de console, sem ano pulado no rótulo
  (registrar a sequência).
- T9.4 Desempenho: troca de ano com bloco em cache ≤ 50 ms (mediana) em 1280 px; primeira abertura ≤ 2 s no servidor
  local.
- T9.5 Casos de referência no **navegador**: para 10 casos, `document.elementFromPoint` no ponto projetado acerta o
  estado esperado.
- T9.6 `git diff --stat` de `frontend/mapa`, `frontend/mapas`, `frontend/linha-do-tempo` sem mudanças novas.

Revisão visual: capturas em 1280 e 360 px de 2500 a.C., 1200 a.C., 586 a.C., 30 d.C., 999 d.C., 1500 d.C.,
1799 d.C., 2025 d.C., e as mesmas lado a lado com o quadro do vídeo. Abrir e conferir.

Portão: T9.1–T9.6 OK; capturas ao usuário.

### E10. Documentação, limpeza e revisão final por época

Tarefas:
1. Reescrever `docs/mapa-geral.md` para a v2: fontes e créditos, papel de cada script, paleta medida, calibração por
   trecho (com resíduos), regra de rotulagem (creme, escuros, linhas, texto), cobertura e tremor, rastreamento,
   nomes e traduções, formato dos dados, orçamento, como regenerar (comandos na ordem, tempo de cada etapa), limites
   conhecidos, checklist de revisão.
2. Atualizar `AGENTS.md` (linha do `mapa-geral/` na tabela: `dados/indice.json`, `dados/blocos/`; descrição de
   `scripts/mapa-geral/`) e `README.md` (tabela e a frase "Primeira etapa: Antiguidade com nomes", que deixa de
   valer).
3. Apagar os scripts da v1 que não são mais usados (seção 5) e o cache antigo da v1 (`.cache/quadros/`,
   `.cache/estados/`, etc.) **depois de perguntar ao usuário**.
4. Marcar `docs/mapa-geral-plano.md` (v1) como substituído, apontando para este arquivo.
5. Revisão final com o usuário **por época**: Antiguidade (2500 a.C.–500 d.C.), medieval (500–1500), moderna
   (1500–1900), contemporânea (1900–2025). Para cada uma, 4 anos lado a lado com o vídeo e a lista de pendências.

Testes `testar.py e10` (roda tudo):
- T10.1 `testar.py e0` … `e9` passam em sequência a partir do cache.
- T10.2 Regenerar do zero numa pasta de cache vazia (`MAPA_GERAL_CACHE=<tmp>`) produz dados **idênticos** (hash dos
  arquivos de `dados/`): o pipeline é determinístico.
- T10.3 Os 27 mapas antigos idênticos à linha de base da E0 (T0.2).
- T10.4 `node scripts/verificar.mjs` passa.

## 7. Resumo dos testes

| Etapa | O que prova | Testes-chave |
|---|---|---|
| E0 | Mapas antigos intactos; base de testes | T0.2 (diferença de pixels = 0) |
| E1 | Mapa geral não lê mapas antigos | T1.1 (grep), T1.3 (IoU com `territorios`) |
| E2 | Todo ano tem seu mapa | T2.1 (4.525 anos), T2.6 (folha de OCR) |
| E3 | Pixel → lon/lat correto | T3.2 (resíduo de costa) |
| E4 | Todo pixel de terra rotulado, creme/escuro incluídos | T4.1–T4.3 |
| E5 | Bordas corretas | T5.2–T5.7 (cobertura, borda única, sem fresta, costa, retas, IoU ≥ 0,92) |
| E6 | Ids estáveis, animação sem tremer | T6.2, T6.4 |
| E7 | Nomes pt-BR e cores do vídeo | T7.1, T7.2, T7.5 |
| E8 | Dados corretos e pequenos | T8.2 (reconstrução), T8.6 (orçamento) |
| E9 | Página ano a ano | T9.2, T9.3 |
| E10 | Reprodutível e documentado | T10.2 (determinismo) |

## 8. Ordem de grandeza (para planejar o tempo)

- Decodificar o vídeo inteiro em 1920 px: ~31 mil quadros, alguns minutos (AV1). OCR só das caixas distintas:
  ~4.600 chamadas ao tesseract, ~5 min em paralelo.
- Mapas distintos: medir na E2 (o mapa fica idêntico por vários anos seguidos). Rotular e vetorizar: ~1–3 s por
  mapa e por etapa, em 8 processos.
- Disco: PNG 1920×960 de mapa chapado ≈ 0,3–1 MB; alguns GB no total (cabe, ~110 GB livres).

## 9. Quando parar e perguntar ao usuário

- Um critério de teste não é atingido depois de duas tentativas (mostrar números e imagens).
- O vídeo não mostra algum ano (buraco real) ou mostra o ano 0.
- O orçamento de dados passa de 80 MB (E8).
- Um nome não tem tradução consagrada e há mais de uma opção razoável que muda o sentido (ex.: nomes de povos
  bíblicos).
- Qualquer mudança que mexeria nos 27 mapas antigos, na linha do tempo ou no nav das páginas.
- Antes de apagar o cache ou scripts da v1.

## 10. Riscos conhecidos e como tratar

| Risco | Tratamento |
|---|---|
| Creme quase igual ao branco | Medir a paleta (E4.1); usar linha de contorno + etiqueta; T4.3 com casos creme vizinhos |
| Linhas de contorno confundidas com texto | Classificar por forma (comprimento × espessura), não só por cor; revisão E4 |
| Etiquetas sobre fronteiras ou sobre o mar | Texto é removido e preenchido por expansão do vizinho; o OCR associa pela posição (E7) |
| Costa do vídeo diferente da de `mundo.json` | Faixa de expansão sobre o mar (E4.5) + corte pela costa exata (E5.5); T5.7 mede a perda |
| Ilhas pequenas (Egeu, Indonésia) somem na simplificação | Tolerância de `coverage_simplify` medida; T5.9 com casos de ilhas |
| Zoom no meio de um trecho | Calibração por mapa nos trechos de animação (E3.3) |
| Arredondamento a 2 casas cria sobreposição | Arredondar vértices compartilhados uma vez (E5.7); T8.3 |
| Muitos mapas distintos → dados grandes | Reuso por máscara (E6.4), blocos (E8), orçamento com parada |

## 11. Registro de desvios

(O agente preenche: cada critério alterado, cada decisão tomada sem o usuário, com data e motivo.)

**2026-10-15 (E0 a E3)**

- **E0:** os 27 mapas antigos ficaram com diferença de pixels **0** em relação a `8186a61`, mesmo com `mapa.js` usando
  `projecao.js`; nada foi restaurado. As capturas de referência estão em `.cache/v2/base-mapas/`.
- **E0, `casos.json`:** 97 casos. Os pontos foram escolhidos **no quadro** (pixel) e convertidos para lon/lat com a
  calibração da E3, com ajuste para um pixel de cor uniforme (7×7) que não é texto. Eles servem de teste de
  calibração (T3.5) e de entrada para as etapas E4 a E8.
- **E2, ano que o vídeo não mostra (§9):** o vídeo **pula 1199 a.C. e 899 d.C.** (a 10 anos/s com 30 quadros/s alguns
  anos ficam sem quadro; conferido na sequência de leituras: 1200 → 1198 e 898 → 900). Decisão tomada sem o usuário,
  para manter 4.525 anos: o ano ausente usa o mapa do ano anterior no tempo do vídeo e é marcado `sem_quadro: true`
  em `anos.json`. **O usuário deve confirmar.**
- **E2, definição de "mapa distinto":** o vídeo é AV1 com perda; "mesmo mapa" é diferença alisada 5×5 da diferença
  máxima por canal ≤ 12 em menos de 10 pixels (ruído isolado fica abaixo; mudança real de fronteira, acima).
- **E2, fade final:** o ano 2025 termina com fade para o escuro; o mapa usado é o último quadro com ≥ 99,5 % do
  brilho normal.
- **E2, OCR:** o tesseract às vezes insere um caractere ("555" lido "5585"); a leitura é corrigida apagando um
  caractere quando o resultado cai entre os vizinhos (2 anos: 555 d.C. e 1955 d.C.).
- **E3, projeção (texto de E3 e E5 atualizado para Miller):** o vídeo **não é Mercator, é cilíndrica de Miller** (`y = 1,25·ln tan(45° + 0,4·lat)`). Com
  Mercator o ajuste pedia escala vertical 0,98 e deixava o dobro de pixels discordantes; com Miller a razão
  vertical/horizontal sai 0,999. A tabela de `docs/mapa-geral.md` (Mercator) está superada.
- **E3, T3.2 (critério ajustado e revisado):** mediana ≤ 2 px e p90 ≤ 6 px são medidos sobre a parte da costa do
  vídeo a **até 12 px** da de `mundo.json`; o resto é registrado como `fora`. Revisão visual (aprovação do usuário
  pedida em 2026-10-15, imagens `e3-trecho-*.png` e `e3-recortes-*.png`): a parte `fora` é **texto de rótulo sobre o
  mar** ("Japan", "Philippines", "Polonnaruwa", "Bahamas"…) e **ilhotas minúsculas que `mundo.json` não tem**
  (Ryukyu, Bahamas, Aleutas, Ilhas Faroe, Pacífico). Sri Lanka, Luzon, Taiwan, Honshu, Hokkaido, Sumatra, Flórida,
  Cuba, Alasca, Austrália e Noruega estão no `mundo.json` e a costa dele cai sobre a do vídeo. Fração `fora` por
  trecho (5 mapas por trecho): S=16,99: 6,1 %; S=12,63: 11,9 %; S=10,65: 17,8 %; S=7,04: 14,2 %; S=5,41: 15,6 %.
  **Correção feita nesta revisão:** a descida da v1 desta etapa mudava `S` sem mover `X0`/`Y0`, o que deslocava a
  costa em ~10 px e fazia o passo nunca ser aceito; ela parou 0,39 % (S=16,92 em vez de 16,99) e 0,19 % abaixo do
  ótimo nos dois trechos de maior zoom, com erros de +3 px no oeste e −3 px no leste. Agora a escala varia com o
  centro do quadro fixo. Também só os 5 Grandes Lagos entram na máscara (os outros 24 lagos de `mundo.json` não
  são desenhados no vídeo; carvá-los aumentava a discordância em ~10 %).
- **E3, T3.6 (pedido pelo usuário) e T3.7:** fração `fora` ≤ 20 % passa nos 5 trechos. A razão resíduo médio
  leste/oeste ÷ centro ≤ 1,5 **falha em 4 trechos** (2,83; 2,01; 1,99; 1,52; o 5º dá 1,32), mas com deslocamento
  ótimo de **0 px** em todos os terços e de ≤ 1 px em todos os tiles 4×3 com costa (T3.7, 30–36 tiles por
  trecho): o leste é a costa recortada da China/Coreia/Japão/Indonésia, e o centro tem resíduo muito pequeno
  (0,5–1,0 px), então a razão explode com diferença absoluta de 0,5 a 0,9 px. Não alterei o critério; está
  em aberto com o usuário (proposta: leste/oeste ≤ centro + 1 px). **Decisão do usuário (2026-10-15):** o critério
  do T3.6 passa a ser "resíduo médio de cada terço ≤ centro + 1 px e ≤ 2 px" (mais fração `fora` ≤ 20 %).
- **E3, T3.5 não valida a calibração:** os casos de `casos.json` foram convertidos de pixel para lon/lat com a
  própria calibração, então só confirmam que o pixel tem a cor esperada. A validação da calibração é T3.2/T3.6/T3.7
  (costa do vídeo × `mundo.json`).
- **E3, T3.4:** a discordância de terra > 6 % só é aceita nos 2 mapas de **transição de zoom** (quadros 4418 e
  27651, calibrados um a um).
- **E1, T1.3:** adiado para a E8 (compara os dados finais com `territorios-<ano>.json`).

- **2026-10-16 (E7 aprovada em bloco; E8 e E9 feitas com autonomia):** o usuário pediu para aprovar tudo da E7 e seguir
  até ver o mapa no site, sem publicar (sem commit). Decisões tomadas sozinho, todas reversíveis:
  - **Resultado da E7 (rodada completa, variante det-d / e7 / v1):** 1.965 mapas lidos (108.506 recortes de OCR,
    321.993 do cache), E6 refeita sobre os vetores unidos (variante e7: 4.269 ids, 439 entidades curtas contra 448
    na base), 195 ids juntados pelo nome, 4.074 entidades finais (1.634 com nome lido), 1.134 trocas de nome em 444
    entidades. Testes: T7.0 99,1 %; T7.1 FALHA (43 de 46 séculos abaixo: muitos estados pequenos sem etiqueta
    legível); T7.4 76/91; T7.7 passou a OK com a lista aprovada; T7.8 37 soltos (0 erradas); T6.4 365 regiões
    diferentes (eram 136; as uniões da E7 mudam a vizinhança). Tudo aceito pelo usuário ("seguir mesmo com erros").
  - **`nomes.json` (formato 2):** `traducoes` (1.111 nomes lidos -> pt-BR, cobrindo 80 % dos anos-entidade com
    nome), `entidades` (27 correções à mão, conferidas pelo ano, pela posição e pelas leituras do OCR; aceita
    `nome` ou `nomes` por período) e `trocas` (as 1.134 com `decisao: "aprovada em bloco (2026-10-15)"`). Pedaços de
    etiqueta de duas linhas lidos sozinhos ("Empire", "Africa", "Eastern"…: `FRAGMENTOS` em `construir.py`) e
    leituras curtas ou abreviadas não viram nome (a entidade fica sem rótulo). Nomes sem tradução que parecem uma
    palavra são publicados como lidos (há ruído: "Aaa", "Hod"…).
  - **E8, formato dos dados (desvio registrado):** a primeira gravação deu 126 MB (36 MB gzip), acima dos 80 MB do
    §9. Medido: só 13 % das formas regravadas são ruído sub-pixel (Hausdorff <= 0,03°); o resto é mudança real ou a
    vizinhança re-simplificada (T6.4). Em vez de simplificar a geometria (o tremor exige ~1 vértice a cada 0,25°),
    mudou a codificação: anéis como inteiros em centésimos de grau, primeiro ponto absoluto e os demais como deltas
    (`[x0, y0, dx1, dy1, ...]`). Mesma geometria de 2 casas, 55,5 MB (15,4 MB gzip), 60.559 formas em 181 blocos.
    **T8.6 ajustado:** o limite por bloco (400 KB / 100 KB gzip) ficou informativo: 49 blocos passam (todos de 576
    d.C. em diante; o maior, d1901, tem 1,9 MB / 0,5 MB gzip), a média é 299 KB / 83 KB gzip e o total fica abaixo de
    80 MB. Blocos menores só nessas épocas exigiriam um índice de blocos; fica como melhoria.
  - **`indice.json`:** além do formato do plano, `estados[id].nomes = [[de, ate, nome, nome_video], ...]` quando o
    nome muda ao longo da vida (trocas aprovadas), e `nome` é o mais duradouro. Ids = slug do nome pt-BR (+ "-2",
    "-3"… na ordem de aparição); entidades sem nome usam o id da E7.
  - **T8.3 (critério ajustado):** o arredondamento para 2 casas e as uniões da E7 deixam frestas de sobreposição
    sub-pixel entre vizinhos (456 pares em 1.965 mapas, área ~3e-5 grau², ~0,005°) e anéis que se tocam num vértice
    (inválidos para o GEOS, ~3 % das formas; o par-ímpar da página desenha igual). O teste passou a exigir maior
    fresta <= 1e-3 grau² e inválidas <= 5 % das formas, em vez de 0 e 0.
  - **T8.4** compara o nome do vídeo (`nome_video` do ano) com `casos.json`, como o T7.4; o nome pt-BR do caso é só
    informativo (a tradução é escolha da E7, e `casos.json` trazia formas provisórias como "Shang", "Otomanos").
    Resultado 91/105: os 14 diferentes são os mesmos erros de leitura da E7 (T7.4: "Janapadas", "Goguryeoj", "Rome"
    em vez de "Roman Empire", etiquetas de vizinhos) e o Funan de 326 d.C. lido como Chenla. Aceito pelo usuário.
  - **E9:** `mapa-geral.js` reescrito para o formato 2 (4.525 posições, blocos sob demanda com cache de 20, só o
    que muda é redesenhado, pré-carga do bloco seguinte, ←/→ 1 ano, Shift 10, espaço reproduz, velocidades 5/10/25,
    campo "ir para", URL com `?ano=`); `testar-pagina.mjs` (T9.2–T9.5) e `verificar.mjs` com os 4 anos do plano.
    `sw.js` VERSAO v4. Capturas em `.cache/v2/revisao/e9-*.png`.

- **2026-10-16 (revisão do usuário do mapa publicado; 7 casos):** peças de um estado quebradas pela etiqueta (Arábia
  Saudita, Afeganistão, Espanha, Vietnã/Laos, Egito 2500 a.C.), nomes trocados por causa disso (Mascate no Paquistão,
  Marrocos na Espanha), Ebla sem nome e Uruk lido como Lagash, Oriente Médio de 2025 com Síria/Líbano/Israel/Jordânia
  fundidos (cores quase iguais e linhas finas). Diagnóstico: no mapa de 2025 a E7 não fez **nenhuma** união, porque
  só unia duas peças da mesma cor com o mesmo nome lido, e uma etiqueta de duas linhas ("Saudi" / "Arabia") caía
  uma linha em cada peça. **Regra nova (`decidir_unioes`, VERSAO_U = 2):** fronteira feita de letras
  (`fracao_letra >= 0,5`, mesma cor) une mesmo com nomes diferentes e mesmo com linha; fresta sem linha nem letra
  (`SEM_LINHA_UNIAO`) une se só uma das peças tem nome. 55.625 uniões em 1.953 mapas (variante e7c): T7.8 caiu
  de 37 soltos para 2, mas com 15 uniões erradas (estados minúsculos de 999 e 1799 d.C., com etiquetas abreviadas
  que transbordam para o vizinho: a fronteira fica "de letras" sem ser cortada por etiqueta). As métricas da
  fronteira não separam os dois casos (tabela em experimentos/pares_unioes2.py). **Regra final (VERSAO_U = 5):**
  (a) mesmo nome e sem linha; (b) duas etiquetas empilhadas, linhas da mesma ("Saudi"/"Arabia", `empilhadas`);
  (c) uma etiqueta cobre as duas peças (>= 25 % da caixa sobre cada, `SOBRE_UNIAO`) e a fronteira é de letras;
  (d) fresta sem linha nem letra com só uma peça nomeada e a outra >= 5 % da área (o Nilo corta o Egito);
  (e) fronteira de letras entre peças grandes (>= 600 px cada, fronteira >= 40 px). Etiqueta deslocada (dada por
  proximidade) conta como peça sem nome. Resultado em pares.json: 3 erradas, 35 soltos (v1: 0/37); os casos do
  usuário (Arábia Saudita, Afeganistão, Paquistão, Marrocos, Egito 2500 a.C.) ficam unidos. O arquivo de decisões
  ganhou a versão no nome (`unioes-<textos>-u<versão>.json`). Obs.: pares.json tem o par 256/257 anotado dos dois
  jeitos.
- **Vídeo em 8K (pedido do usuário):** `vídeos/*8k.mp4` (7680×3840, AV1, 193 MB, formato 571 do yt-dlp). O quadro 8K
  tem texto e linhas nítidos (o 1080 é borrado). Refazer E2–E6 em 8K custaria dias; a leitura dos nomes, não:
  `quadros4k.py` grava o quadro de cada mapa distinto reduzido a 3840×1920 (`.cache/v2/mapas-4k/`, ~5 GB), e a E7a com
  `MAPA_GERAL_ESCALA=2` detecta as caixas no mapa 1080 mas lê os recortes no quadro 4K (variante det-4k; a chave
  inclui o quadro 4K). Amostra de 40 etiquetas de 2025: 1080 → 4K corrige "Cuos"→"Cuba", "Jomoka"→"Jamaica",
  "Sahaea"→"Sahara", "Yrindod"→"Trinidad", "Butis"→"Barbados"…; tempo por recorte ~1,2× (2025) a ~4× (etiquetas
  minúsculas). Cadeia noturna: det-4k → uniões → E6 (e7d) → nomes (e7d) → aprovar → construir → testes.
- **Correções e edições robustas a regenerações:** `nomes.json` "entidades" e `edicoes.json` passaram a trazer `onde`
  [ano, lon, lat]; o `construir.py` acha a entidade pelo ponto nesse ano (os ids da E7 e os slugs do site mudam quando
  a E6 é refeita). O editor grava o ponto do clique em cada edição.
- **Outro agente (2026-10-16, manhã):** moveu a E3 para a loja, trocou `visualizar.py`/`editor.py` pelo `painel.py`
  (porta 8001, com os mesmos endpoints) e fez o commit `b2da5e8`, já enviado ao `origin`.

## 12. Instruções para o agente (copie e cole)

> Você vai executar o plano `docs/mapa-geral-plano-2.md` no projeto "Mapa da Bíblia"
> (`/data/Documents/Programing/Mapa-da-Biblia`). Leia antes `AGENTS.md`, `docs/mapa-geral.md` e o plano inteiro.
> Responda sempre em português do Brasil.
>
> Objetivo: refazer o mapa geral (`frontend/mapa-geral/`) **ano a ano de 2500 a.C. a 2025 d.C.**, usando **só o
> vídeo** `hzWwp9JM7Hw` (nada dos mapas antigos, cores do vídeo), com **bordas em cobertura** (sem frestas, sem
> sobreposição, borda comum única, só retas com tremor, costa de `mundo.json`) e **nomes em pt-BR para todas as
> épocas**.
>
> Trabalhe **etapa por etapa (E0 → E10)**. Em cada etapa: implemente, rode `testar.py <etapa>`, gere e **abra** as
> imagens de revisão, corrija até o portão passar e mande ao usuário um relatório curto com números e imagens antes
> de seguir. Se um critério não for atingido depois de duas tentativas, pare e pergunte (seção 9). Nunca afrouxe
> um teste sem registrar na seção 11. Não mexa nos 27 mapas antigos, na linha do tempo nem no nav. Não faça commit
> sem o usuário pedir. Comandos longos em segundo plano com log; não use `pkill -f`; Chrome headless sempre com
> `--user-data-dir` e `--disk-cache-dir` novos.
>
> Comece pela E0.

**2026-10-15 (E4)**

- **Método (difere do texto do plano):** em vez de máscaras por cor + linhas, a rotulagem usa **zonas planas**
  (vizinhos de 4 conexões com diferença máxima por canal ≤ 8) como sementes e `cv2.watershed` para espalhar os
  rótulos por bordas, linhas e letras (cabeçalho de `rotular.py`). A paleta medida está em `.cache/v2/paleta.json`
  (`paleta.py`): mar 216,225,237 (desvio ≤ 0,9), terra sem dono 255,255,255, cremes 254,248,238 e 252,247,239,
  escuros como 77,83,91 (Sacro Império) e 69,113,117 (Otomanos).
- **Estados cortados pelo próprio nome:** as letras de um rótulo ("Elam") separam um estado em duas zonas de mesma
  cor; regiões vizinhas de cor quase igual (L1 ≤ 20) cuja fronteira tem ≥ 30 % de evidência de letra são unidas.
  Branco cercado de mar não é texto (é ilha sem dono: Svalbard, Ártico canadense).
- **T4.1/T4.5 reformulados:** cobertura e estabilidade de cor são medidas só em pixels "planos" (sem borda a 1 px) e
  sem letras/antialias de letras (3 px), porque a antialias da fronteira colorido/branco e as letras nunca são
  estado nem terra sem dono. Critério de cobertura: ≥ 99,7 % (medido 99,998 %); estados coloridos tratados
  como sem-dono: ≤ 0,3 % (medido 0,005 %).
- **Mapas já rotulados:** 1.965, 692 s em 8 processos (≈ 2,8 s por mapa por processo).
- **Aviso (§0):** um `pkill -f` derrubou o shell uma vez durante esta etapa; nada foi perdido.
- **E4, uniões e mudança de ordem (decisão do usuário, 2026-10-15):** num conjunto de 88 pares de regiões vizinhas
  de mesma cor rotulados à mão em 999 e 1799 (`scripts/mapa-geral/pares.json`: 69 "o mesmo estado partido pelo
  próprio nome", 19 "dois estados de mesma cor com o nome encostado na linha"), nenhuma regra só com pixels da
  fronteira separou os dois casos (melhores: ≥ 70 % de letra = 10/19 uniões erradas e 11/69 pedaços soltos; com
  veto de linha = 6/19 e 30/69). Ficou assim:
  - **E4** faz só as uniões quase certas, registradas em `rotulos/<id>.json` (`unioes`, conferidas pelo T4.7):
    `letra` (≥ 90 % de letra e ≤ 10 % de linha na fronteira), `sem-linha` (letra + preenchimento ≥ 90 %, ≤ 10 % de
    linha: degrau de compressão do AV1), `gargalo` (contato < 6 px, pedaço < 1.500 px: istmo da Baja, faixa da
    Flórida; Nova Espanha × Nova Granada se tocam no Panamá sem linha e ficam separadas) e `fragmento` (< 150 px com
    a vizinha de mesma cor em ≥ 40 % do perímetro). Os outros pares de mesma cor viram `candidatos` (com as
    estatísticas, um ponto interior de cada parte e a região final de cada lado).
  - **E7** decide os candidatos, nesta ordem: (1) evidência temporal (via E6): se em algum ano as duas aparecem
    separadas por linha cinza, com cores diferentes ou cada uma com nome próprio, são dois estados; se em algum ano
    aparecem como uma região só, são um estado; (2) nomes: junta a "parte sem nome" só se ela tiver < 25 % da área
    da outra, a fronteira tiver ≥ 70 % de letra e nenhum ano indicar dois estados; senão ficam separadas e o caso é
    listado para revisão. Depois das uniões, a E6 (ids) é refeita e `testar.py e6` roda de novo; a E5 não precisa
    ser refeita (união de polígonos em cobertura). Meta da E7 em `pares.json`: 0 uniões erradas e ≤ 3 pedaços
    soltos (T4.8 informa a situação depois da E4).
  - **Revisão depois da 1ª rodada completa (T4.8):** gargalo, sem-linha e fragmento ainda uniam cremes
    diferentes (Cr. × B., I. × Ma., Soma. × K.); agora essas três regras valem só entre estados coloridos, e entre
    claros só a união por letra quase certa. O `rotular.py` foi dividido em fase 1 (zonas planas, sementes,
    watershed; gravada em `.cache/v2/rotulos-pre/<id>.npz`) e fase 2 (uniões, ilhas, costa, numeração);
    `rotular.py --uniao` refaz só a fase 2. A fase 2 foi vetorizada (ela varria a imagem inteira uma vez por
    região) e caiu de ~18 s para ~1,4 s por mapa; o resultado com e sem cache é idêntico (conferido em 4 mapas).
  - **Detecção de texto** é a primeira tarefa da E7 (hoje só as letras grandes, com miolo liso, geram caixa), com
    teste próprio: ≥ 95 % das etiquetas visíveis detectadas numa amostra conferida à mão.
  Correções feitas na mesma revisão: o limiar de "texto branco" (mín. canal ≥ 235) pegava o creme (mín. ~237) e
  apagava estados cremes cobertos pelo nome; agora é ≥ 246. Fragmentos < 25 px da mesma cor, a ≤ 10 px uns dos
  outros, viram uma semente (estado "K.", Bengala 1452, quase todo coberto pelo nome). Ilhas finas sem zona plana
  (Cuba, Jamaica, Bahamas no mundo inteiro) viravam mar; pixels coloridos ou brancos rotulados como mar, longe
  (> 2 px) do núcleo preto das letras (o halo branco dos rótulos), viram ilha. Imagem de rótulos: vizinhos nunca
  com a mesma cor (distância mínima medida: 259 em L1).
- **E5, T5.7:** a comparação exclui os pixels dos lagos de `mundo.json` que o vídeo não desenha (texto do T5.7
  atualizado).

**2026-10-15 (execução incremental, `docs/mapa-geral-incremental.md`)**

- `cache.py` (chave = versão + parâmetros + hash do conteúdo das entradas; manifesto por etapa; gravação atômica),
  `rotular.py` dividido em E4a (zonas → marcadores), E4b (watershed), E4d (tabela dos pares) e E4e (regras,
  numeração), com artefatos em `.cache/v2/e4/{a,b,d}/` e manifesto por sub-etapa; `decidir_unioes()` é pura e roda
  sobre a tabela da E4d. A ordem segue o código (costa e ilhas ficam na E4e, depois das uniões), porque mudar a ordem
  mudaria os rótulos (T-C6). `vetorizar.py` com cache por hash dos rótulos. Amostras fixas em `amostras.json`
  (`amostras.py`: rápida = 31 mapas, média = 200), testes T-C1–T-C6 em `testar.py cache`, `limpar_cache.py`, e os
  scripts de experimento saíram de `.cache/v2/` para `scripts/mapa-geral/experimentos/`.
- **Pedido do usuário: "construa, mas só rode tudo de novo se não tiver ficado bom".** A primeira rodada do código
  dividido foi feita na amostra média (200 mapas), não nos 1.965; o T-C6 compara essa amostra com a cópia dos rótulos
  da rodada de referência (`.cache/v2/referencia-e4/`). A rodada completa a frio fica para a próxima mudança de regra
  (E7), quando os caches da E4a–E4d serão preenchidos para todos os mapas.

**2026-10-15 (E5)**

- **Precisão:** o vetor da E5 tem 5 casas decimais (~1 m). Com 2 casas, os vértices que o corte pela costa cria
  sobre ela (o tremor cruza a costa várias vezes) saíam da costa em até 0,007° e formavam lascas fora da terra,
  sobreposições e anéis degenerados. O arredondamento do site (2 casas) passa para a E8, sobre a cobertura inteira.
- **T5.5 (critério ajustado):** mesmo com 5 casas o arredondamento deixa lascas fora da terra (até ~1,3e-6 grau²
  cada, ao longo de lados longos de costa); o teste aceita só pedaços fora da terra com todos os vértices a
  ≤ 1,1e-5° da costa, e exige os vértices de costa de cada região a ≤ 1e-5° dela (os de divisa perto da costa não
  contam: uma divisa chega à costa em ângulo).
- **Tremor e canais finos:** onde o tremor faz as duas margens de um canal ou península fina se cruzarem, os lados a
  ≤ 0,15° do cruzamento ficam retos (quebrados em pedaços colineares de ≤ 0,25°), em todos os polígonos pela chave
  do lado (`tremor.py` ganhou o parâmetro opcional `sem_tremor`; sem ele o resultado é o de antes). Consertar cada
  polígono com make_valid quebrava a borda comum (164 mapas com cobertura inválida).
- **Passo do tremor 0,25°** (o padrão 0,35 deixava lados de até 0,7° sem quebrar; T5.6 pede ≤ 0,5°).
- **TOL_PX 1,0** (0,6 deixava a escada dos pixels nas diagonais, visível na revisão).
- **`clip_by_rect` do GEOS 3.14** falha em alguns retângulos ("LinearRing found 3"): troca pela interseção com a caixa.
- **T5.3:** comprimento medido a mais de 0,1° da costa e a mais de 0,5° da borda do quadro (junto delas o tremor
  joga parte da divisa para o mar ou para fora do quadro).
- **T5.4:** margem de 0,15° na borda do quadro (o tremor desloca a borda do próprio quadro).
- **T5.7 (critério ajustado; aprovado pelo usuário em 2026-10-15, a sobreposição estrita continua impressa):** o IoU passa a ignorar 1 px de cada lado da borda do vídeo.
  Numa região compacta de ~250 px, a simplificação de 1 px e o tremor movem metade dos pixels de borda e o IoU
  estrito cai para ~0,79 sem erro de forma; com a tolerância, IoU mín 0,993 (médios) e 0,999 (grandes). O IoU
  estrito continua no relatório do teste (mín 0,787, mediana 0,950).
- **T5.7:** rasterização com −0,5 px (vértices nos cantos dos pixels); a faixa de 2 px junto da costa de
  `mundo.json` não entra (a costa é a de `mundo.json` por regra); as peças de candidatos (estados cortados pelo
  nome, ~840 na amostra, IoU mediana 0,92 e mínima 0,79 por causa do "pente" das letras) só informam até a E7.
- **Sobrescrita de `rotulos/` (2026-10-15, 12:43–12:44):** a primeira rodada do código dividido na amostra média foi
  interrompida depois de ~45 mapas; a E4e grava em `rotulos/` (é o artefato final da etapa) e reescreveu esses 45.
  Todos saíram idênticos à referência (PNG byte a byte, JSON com o mesmo conteúdo), mas o JSON estava em outra
  formatação (chaves ordenadas), o que mudaria o hash usado pela chave da E5. Os 45 foram restaurados de
  `.cache/v2/referencia-e4/` (cópia feita antes da rodada, que é a referência do T-C6) e a E4e voltou a gravar o
  JSON no formato de antes (bytes idênticos).

**2026-10-15 (E4e: miolos de letra)**

- **Defeito (relatado pelo usuário):** o miolo das letras dos nomes ("c" de Achaemenid, "Z" de Zhou em 511 a.C.,
  mapa 265) virava uma região própria, cercada pelo estado. O `buraco_de_letra` da E4a não pegava porque exige cor
  parecida (L1 ≤ 60) e a antialias tinge o miolo.
- **Regra nova na E4e (VERSAO e = 13; só a E4e é refeita):** região < 1.000 px, sem contato com o mar (no rótulo ou
  ≥ 5 % do anel com cor de mar no vídeo), cercada em ≥ 90 % do anel de 2 px por um vizinho (ou vizinhos da mesma
  cor dele), é absorvida pelo vizinho quando há evidência de texto, sem exigir cor parecida:
  - vizinho colorido (letras brancas): ≥ 15 % de letra no anel, < 50 % de linha de contorno no anel e < 15 % de linha
    na fronteira comum (sem contar a antialias das letras = mistura da cor do vizinho com branco ou preto); ou a cor
    da própria região é de traço de letra (quase branca) com ≥ 5 % de letra em volta;
  - vizinho claro (creme/branco, letras pretas): ≥ 15 % de letra e < 10 % de linha cinza na fronteira comum;
  - ou o centro cai numa caixa de texto da E4a;
  - sem texto: a mesma cor do vizinho (L1 ≤ 20) e sem linha de contorno (anel < 15 %, fronteira < 10 %).
  Até 4 passadas (o miolo de um "B" fica cercado pelo traço, que também é absorvido). Cada absorção vira união
  `tipo: "miolo"` (com `motivo`, frações e ponto) em `rotulos/<id>.json`; os enclaves que ficaram vão em `enclaves`.
- **Enclaves preservados (conferidos nas folhas `revisao/enclaves-*.png`):** estados cremes dentro de cremes
  separados por linha cinza (Malwa, Ka., G., Ratn., Pr. em Lanna, Kandy em Kotte, Hausa/Igala, Assa., Ga.), Penn. e
  as 13 colônias (mesmo vermelho, linha entre elas), Incas, Luba, ilhas e faixas. Os que sobram com "letra" são do
  mapa 2020 (1779 d.C.), um quadro de **transição de zoom** borrado: limite conhecido, a revisar quando a E2/E3
  escolherem outro quadro para esse ano.
- **Testes novos (`testar.py miolos`, com `AMOSTRA=rapida|media|todos`):** T4.9a nenhum miolo sobra; T4.9b nenhuma
  região cercada por um único vizinho dentro de caixa de texto; T4.9c `anotacoes.json` respeitadas; contagem antes
  (cópia `.cache/v2/antes-miolo/`) e depois. Amostra média: antes 356 miolos em 150 de 200 mapas (o relato do usuário
  era 44 de 60), depois 0; 568 enclaves listados em `.cache/v2/enclaves-media.json`.
- A medição da "linha" mudou várias vezes nesta rodada (VERSAO e de 2 a 13), sempre na amostra rápida e média; a
  rodada completa só no portão.
- **Aprovação visual do usuário (2026-10-15):** miolos sumiram em 511 a.C., 31 e 999 d.C.; estados pequenos
  continuam com contorno próprio (Bengala 1452, Sacro Império 1703, 1712 e 1799); folhas de absorvidos e enclaves
  corretas. Correção dos miolos de letra aprovada.

**2026-10-15 (antes da E6: transições, enclaves, visualizador, velocidade, anotações)**

- **Quadros de transição de zoom (`transicoes.py`, teste T3.8):** só dois mapas tinham escala fora dos trechos
  (S ≈ 24,7): 125 (1000 a.C.) e 2020 (1779 d.C.). Não eram anos sem quadro bom: o PNG gravado na E2 era o primeiro
  quadro do fade (a busca do ffmpeg por tempo pode cair um quadro antes ou depois) e a calibração dele caiu num
  mínimo falso. Os dois anos agora usam o último quadro estável do próprio ano (4416 e 27651), com a calibração do
  trecho refinada; `anos.json` registra `transicao`. Nenhum ano precisou do mapa do ano anterior. 1779 d.C. passou
  de 40 para 3 enclaves.
- **Enclaves suspeitos (< 300 px, linha na fronteira < 30 %):** eram 122 em 105 mapas (o usuário contou 141 antes
  da correção das transições). Padrão de erro achado: traços finos de letra brancos sobre estado colorido ("n" de
  Tang, "J" de Jin, "Y" de Yuan) com pouca "letra" em volta. Regra nova na E4e: cor de letra e raio inscrito
  ≤ 3,5 px também é traço (VERSAO e = 14). Sobram 70 em 61 mapas, todos conferidos na folha
  `revisao/enclaves-suspeitos-*.png` e reais (enclave vermelho em azul 679–688 d.C., creme em verde 1013–1028,
  faixa branca "A." 1121–1132, vermelho em azul 1259–1289, Southern M. 1658, enclaves do Sacro Império 1703–1713).
- **Visualizador:** caixa "enclaves e miolos": enclaves em ciano tracejado, miolos absorvidos como pontos (amarelo =
  texto, verde-água = mesma cor), com as frações no título; painel com contagens e anotações aplicadas/vetos.
- **Velocidade:** a E4e caiu de ~0,84 para ~0,33 s por mapa num processo (canais de cor calculados uma vez em
  uint8, sort em uint16 sem o segundo sort do `np.unique`, máximo do watershed fora do laço das ilhas; resultado
  idêntico, conferido em 31 mapas). O manifesto guarda a assinatura (mtime, tamanho) dos artefatos e não relê
  conteúdo que não mudou: rodada sem mudança nos 1.965 mapas em 3 s (antes 13–24 s). A chave da E5 usa só o PNG
  dos rótulos e tipo/cor das regiões. **Rodada só de regra (E4e) nos 1.965 mapas: 4,9 min (antes ~8); o alvo de
  2 min não foi atingido** (16 processos não ajudam: limite de memória). Mover para a E4d as medições das regiões
  depois das uniões (miolos, fragmentos, minúsculas) exige reformulá-las sobre a partição antes das uniões; ver
  relatório ao usuário. As decisões de união da E7 podem ser aplicadas nos rótulos/vetores finais sem refazer a E4e.
- **Anotações (`anotacoes.json`) na E4e:** `estados_diferentes` veta qualquer junção que una os dois pontos
  (uniões da tabela, fragmentos, miolos, minúsculas); `mesmo_estado` junta as duas regiões no fim (união
  `tipo: "anotacao"`); `problema` é listado. Só mapas com anotação têm as anotações na chave da E4e. Teste T4.9c.
  Testado com um arquivo provisório (uma anotação de cada tipo no mapa 2053: veto de um miolo, junção de um
  candidato, problema listado) e apagado depois.
- **T5.7 aprovado** (tolerância de 1 px; IoU estrito continua impresso). `rotulos-pre/`, `antes-miolo/` e
  `referencia-e4/` apagados (`limpar_cache.py`, 372 MB). O T-C6 (prova única da refatoração) fica como concluído.
- **Decisões do usuário (2026-10-15, depois do relatório):** aprovado tudo (transições, enclaves, visualizador,
  velocidade, anotações). Os 4,9 min da rodada só de regra da E4e servem; a reestruturação da E4e fica para depois.
  Para a E7: (1) as uniões por nome são aplicadas nos vetores finais (junta a cobertura das duas regiões e remove a
  borda comum, sem refazer a E4e; a borda com os outros vizinhos não muda, nem o tremor); (2) a chave de cache do
  vetor final inclui a lista de uniões aplicadas no mapa; (3) a E7 respeita `anotacoes.json` ("estados diferentes"
  veta união por nome entre aqueles pontos) e o teste das anotações roda também depois da E7; (4) se a E7 precisar
  mudar a rotulagem com frequência, avisar e reavaliar a aceleração da E4e. Na E6: id de cada estado no
  visualizador (ao passar o mouse e colorir por id). Na E7, parar e mandar as traduções antes da E8.

**2026-10-15 (E6)**

- **`rastrear.py`:** grade comum de 0,1° (equiretangular), casamento por área comum (pares em ordem decrescente,
  cada região casada uma vez: divisão = o maior pedaço herda; fusão = herda a maior sobreposição), cor L1 ≤ 60 ou
  IoU ≥ 0,8 (recoloração, registrada), só herda quem existia no mapa anterior. Antimeridiano: duas regiões da mesma
  cor tocando as duas bordas do quadro do mundo inteiro, na mesma faixa de latitude, são uma entidade (o T6.1
  aceita esse par). Saída `entidades.json` (`entidades`, `por_ano` em corridas de anos com o mesmo mapa, `eventos`).
  Resultado: 4.392 entidades, 552 recolorações.
- **T6.2 (piscar)** medido por corrida de mapa: um id que some num mapa e volta no seguinte (o rastreamento nunca
  reusa id, então isto pega id pulado).
- **T6.3:** 448 entidades com vida < 3 anos. Causas (experimentos/curtas_causa.py): 198 com cor diferente do estado
  sobreposto antes (estado novo ou recoloração breve do vídeo), 181 sem sobreposição antes (estado novo), 69 que
  herdariam pela sobreposição mas perderam o id para uma região maior (divisão/fusão de peças ainda não unidas: os
  candidatos da E7 resolvem a maior parte, e a E6 é refeita depois da E7).
- **T6.4 (critério ajustado):** "mesma máscara de pixels" não basta: se um vizinho muda, a borda comum muda nos
  dois. O teste exige também a mesma vizinhança (anel de 3 px com os mesmos ids). Com isso sobraram 136 de 240.038
  regiões com geometria diferente: o `coverage_simplify` do GEOS decide cada aresta olhando arestas vizinhas num
  raio de 6–20 px. **Tentativa de correção na E5 (VERSAO 5):** simplificação própria aresta por aresta
  (`simplificar_local`, Douglas–Peucker em cada cadeia entre nós, forma canônica, cadeias que se cruzam voltam ao
  original). Os 5 casos conferidos passaram a sair idênticos, mas na rodada completa: cobertura inválida em 51
  mapas (T5.2a), 12 bordas comuns curtas (T5.3), 1 vértice de costa fora (T5.5) e ainda 93 regiões diferentes no
  T6.4. **Revertida** (VERSAO 6 = mesma lógica da 4, com `coverage_simplify`; `simplificar_local` fica como opção
  `SIMPLIFICACAO = "local"`). Duas tentativas sem atingir o critério do T6.4: pergunta ao usuário (§9).
- **Visualizador:** id da entidade ao passar o mouse e no painel da região (com a vida dela); modo "cor por id"
  (cor estável derivada do id) para ver a continuidade entre os anos.
- **Decisão do usuário (2026-10-15) sobre o T6.4:** aceitas por enquanto as 136 diferenças (0,06 %, sub-pixel, vindas
  do `coverage_simplify`). **Reverter não era o caminho:** a tentativa devia ficar ao lado da versão aprovada.
  Antes da E7 o cache passou a ser uma loja por chave com variantes e apontadores (detalhes em
  `docs/mapa-geral-incremental.md`, §7): `cache.py` (Etapa, aprovar, procurar), `migrar_loja.py` (os rótulos e os
  vetores atuais viraram a variante "base"), `rotular.py`/`vetorizar.py`/`rastrear.py` com `--variante`,
  `limpar_cache.py` que nunca apaga a aprovada nem a anterior, seletor de variante no visualizador e o teste T-C7.
  A simplificação aresta por aresta, se for tentada de novo, roda como variante (rápida, média, todos) sem tocar na
  aprovada.

**2026-10-15 (E7: texto, nomes, uniões)**

- **Detecção de texto (`texto.py`, T7.0):** as letras do vídeo são neutras (cinza-escuro ou branco) e as regiões são
  coloridas: máscara por contraste com a mediana local (15×15), croma baixo na letra escura, sem as partes grossas
  (abertura 5×5), componentes com forma de letra agrupados em palavras (mesma linha, vão ≤ 0,7 × altura), letra
  sozinha com ou sem ponto ("A", "K."), e a letra clara só dentro de região colorida (rótulos da E4e: a terra branca
  vizinha não gruda nela). Amostra conferida à mão `texto-amostra.json` (220 etiquetas em recortes de 7 mapas, 2500
  a.C.–1900 d.C.): **98,2 %** detectadas.
- **Leitura:** a fonte do vídeo é a Myriad Pro (não é livre); nenhuma fonte livre testada (40) bate exatamente.
  Tesseract (tessdata_best) e RapidOCR leem mal a letra de 6 px (~40 % exatas sozinhos). O que funciona: 6
  variantes de OCR dão candidatas e o **desenho** de cada candidata (fonte Sarabun, correlação com margem vazia,
  melhor tamanho e subpixel) escolhe; 67 % exatas por recorte na amostra. A mesma conferência pelo desenho é usada
  por entidade: as grafias de um trecho são reavaliadas em até 6 recortes de mapas diferentes, e uma **troca de nome
  só fica se cada lado for mais bem explicado pelo próprio nome** (corrige "Brazi"→"Brazil", "Jomaka"→"Jamaica",
  "Fimor"→"Timor" e elimina trocas falsas).
- **Cache do OCR por recorte** (pedido do usuário): hash dos pixels do recorte + tipo; dois caches separados
  (`e7/ocr/` = leituras brutas, caro; `e7/nota/` = conferência pelo desenho), para mudar a nota sem refazer o OCR. Um
  rótulo que não muda entre mapas seguidos é lido uma vez (na rodada de 103 mapas: 36 mil do cache, 6,7 mil lidos).
  Etapa E7a na loja (`textos/<id>.json`, chave = parâmetros + PNG do mapa + rótulos da E4e).
- **Associação etiqueta → região:** cada região fica com no máximo uma etiqueta (a que está sobre ela com maior
  fração); etiquetas de estados pequenos escritas sobre o vizinho, o mar ou terra sem dono ("Kaabu", "Mane", "Benin")
  vão para o estado **sem etiqueta** mais próximo (≤ 30 px), os pares mais próximos primeiro. Linhas de uma etiqueta
  ("Holy / Roman / Empire") só se juntam se estiverem sobre a mesma região. Leituras-lixo saem pela forma do nome
  (inicial maiúscula, fora "of", "de", "la"...) e pela nota (≥ 0,55; ≥ 0,8 com até 2 letras).
- **Votação por entidade:** leituras parecidas (≥ 0,8) formam um grupo; trechos com outro nome que duram < 15 anos e
  < 3 mapas são ruído e voltam ao vizinho; o nome do trecho é a grafia que vence a reavaliação pelo desenho.
- **Uniões da E7 (pares candidatos da E4):** com a etiqueta, de forma conservadora: fronteira sem nenhuma linha cinza e
  mesma cor; as duas partes com etiqueta → juntam só se for o mesmo nome; só uma com etiqueta → juntam se a fronteira
  for ≥ 50 % letra; nenhuma → separadas. `anotacoes.json` "estados_diferentes" veta. Em `pares.json`: **0 uniões
  erradas, 36 pedaços soltos de 69** (antes da E7: 58). Tentativas: (1) etiqueta passando pelos dois pedaços: 4
  erradas/32 soltos; (2) regra em camadas com a associação: 5 erradas/21 soltos; (3) evidência temporal por pixels
  alinhados nos mapas vizinhos: quase nunca decide e erra metade quando decide. A meta "≤ 3 soltos" não foi atingida:
  pergunta ao usuário (§9). Os pares 256 e 257 de `pares.json` são as mesmas duas regiões com respostas opostas.
- **Uniões nos vetores finais (E7u):** loja `e7u` (`vetores-e7/<id>.json`): os vetores da E5 com as regiões unidas
  (união da cobertura das duas, a fronteira comum some, sem refazer a E4e) e `unidas` {menor: maior}; a chave inclui a
  lista de uniões do mapa; mapa sem união é um link físico para o objeto da E5 (sem espaço a mais). `rastrear.py
  --fonte e7u` refaz a E6 sobre eles (variante própria).
- **Junção de ids pelo nome:** B começa até 10 anos depois do fim de A, o último nome de A é o primeiro de B e as
  formas se sobrepõem (A no último mapa, B no primeiro) → um estado só. Ids com mais de um nome não são separados
  automaticamente: vão para a lista de trocas para o usuário decidir ("mesmo estado renomeado" ou "estados
  diferentes").
- **Testes `testar.py e7`:** T7.0 (detecção), T7.1, T7.3, T7.4, T7.6, T7.7 (nenhum id com dois nomes ao mesmo tempo e
  nenhuma troca fora da lista aprovada em `nomes.json`), T7.8 (pares depois da E7), T7.9 (anotações depois da E7) e
  T7.10 (Ebla e Mari em 2500 a.C. são estados diferentes: nos rótulos atuais já são regiões e ids separados).
- **Visualizador:** nome lido ao passar o mouse e no painel (trechos com anos e número de leituras); modo "cor por
  nome (E7)".

**2026-10-16 (painel e E3 na loja; decisão do usuário: "junte o que tem e adicione o que falta")**

- `scripts/mapa-geral/painel.py` + `painel.html` substituem `visualizar.py`/`visualizar.html` e `editor.py` (o
  `editor.html` continua, embutido na aba Editor): um servidor só (8001) com as abas Mapa (comparação A/B de variantes),
  Mapas (grade: estado de cada mapa em cada etapa pelas chaves de cache), Versões (aprovar, voltar, apagar), Rodar (fila
  de rodadas dos scripts com log ao vivo e interrupção por SIGINT ao grupo de processos), Andamento, Revisão e Editor.
- E3 na loja por chave (`e3`, item `calibracao`); `calibracao.json` vira apontador; `cache.calibracao()` para ler;
  `rotular.chave_sub` concentra a fórmula das chaves da E4 (rodada sem mudança: 0 recálculos na amostra rápida da E4 e
  da E5 depois da mudança). Detalhe em `docs/mapa-geral-incremental.md` §7, itens 8 e 9.

**2026-10-16 (qualidade máxima da extração: geometria em 4K, mediana por mapa, OCR em 8K; decisão do usuário)**

- Fonte: o vídeo principal em 7680×3840 (render nativo, conferido num quadro: letras e fronteiras limpas; o 1920 do
  YouTube tinha 205 kb/s). Decisão do usuário: qualidade máxima mesmo que leve um dia; dados do site podem crescer,
  ele decide vendo os números; tudo como variante/cache nova, aprovar só com testes iguais ou melhores.
- `escala.py` (fator E da geometria e E_OCR do OCR; `px`, `area`, `it`, `impar`, `pasta_mapas`, `pasta_ocr`): todas as
  constantes em pixels dos scripts passam por ele; E = 1 é byte a byte o de antes (T-C1 OK, 0 recálculos, OCR 0
  recortes lidos). Em `rotular.py` as funções são importadas como `_px/_area/_it` (há variáveis locais `px`/`area`).
- E2: `quadros.decodificar()` é o único decodificador (ffmpeg com `scale=...:flags=area`; a varredura continua em
  1920); `quadros_medios.py` grava cada mapa distinto em 1920, 4K e 8K como mediana de até 9 quadros da corrida (até
  o `quadro_mapa`), numa passada sequencial por trecho (4 processos, ~1 GB cada); `montar_anos.gravar_pngs` saiu;
  `transicoes.py` lê em fluxo e regrava pelo `quadros_medios`. O `quadros4k.py` (busca por quadro, 14 divergências)
  foi substituído.
- E3: `INICIAIS`, passos e limiares em pixels seguem a escala (o passo relativo de S não); `calibracao.json` ganha
  `"escala"`; o painel divide S, X0, Y0 por ela ao desenhar. Recalibração em escala 1 comparada à adotada: 95 mapas
  diferem em até 0,07 px / 0,01 % de S, todos encadeados depois dos dois mapas que `transicoes.py` trocou (a descida
  parte do mapa anterior): não é efeito da refatoração.
- E7a: detecção, caixas, hash e nota no quadro da geometria (as caixas ficam na escala dos rótulos, que a E7b indexa);
  os motores leem o recorte no quadro do OCR com a ampliação de cada variante medida em relação a 1920 (um recorte de
  8K é reduzido à mesma altura de letra de antes, mas de pixels nativos). `Reavaliador` passou a ler a mesma imagem
  da nota (antes pontuava `tam` de 4K sobre o quadro 1080). `RAIO_PERTO`, `AREA_GRANDE`, `FRONTEIRA_GRANDE` escalados.
- `construir.py --saida`; `cache.amostras()` (amostras na cache); `cadeia-4k.sh` roda tudo em `.cache-4k`; painel na
  8003 para essa cache (`translate_path` troca `.cache/` pela cache ativa). Medidas prévias: E4 em 4K 44 s/mapa e
  0,9 GB por processo (8 cabem), E5 8–11 s/mapa com `TOL_PX` 1 px de 4K (+50 % de vértices; variante `tol2`
  reproduz a tolerância de hoje), decodificar o 8K inteiro 43–55 fps.
