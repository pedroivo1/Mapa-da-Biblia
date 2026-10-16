# Mapa geral v2: execução incremental (cache por etapa)

> Complemento de `docs/mapa-geral-plano-2.md`. Objetivo: quando uma regra muda, recalcular **só o que depende dela**,
> com resultado **idêntico** ao de recalcular tudo. Escrito em 2026-10-15, durante a E4 (quinta rotulagem completa,
> ~37 min cada, porque `rotular.py` refaz tudo para mudar só as uniões).

## 1. Cache perde qualidade?

**Não, se a chave do cache for certa.** Um cache guarda o resultado exato de uma etapa determinística. Reusar esse
resultado é igual, byte a byte, a recalcular. O risco não é de qualidade, é de **cache velho**: reaproveitar um
resultado calculado com uma regra antiga. Isso se evita com:

1. chave = hash de **tudo** de que a etapa depende (arquivos de entrada, parâmetros, versão do código da etapa);
2. um teste que recalcula do zero uma amostra e compara com o cache (T-C1).

O que **perderia** qualidade (e não deve ser feito): aproximações disfarçadas de cache, como reaproveitar o rótulo de
um mapa vizinho "parecido", baixar a resolução ou pular mapas para ganhar tempo.

## 2. Princípios

1. **Etapa = função pura**: `(entradas, parâmetros, VERSAO) → artefato`. Nada de estado escondido (data, ordem de
   processamento, aleatório sem semente).
2. **Chave por item** (por mapa distinto, por par de regiões, por caixa de texto):
   `sha1(json.dumps({"versao": VERSAO_ETAPA, "params": PARAMS_ETAPA, "entradas": [hash de cada arquivo de entrada]},
   sort_keys=True))`.
   - `PARAMS_ETAPA`: dicionário com **só** os parâmetros que a etapa usa (ex.: `LIM_BORDA`, `RAIO_TEXTO`).
   - `VERSAO_ETAPA`: inteiro no topo do script, **incrementado sempre que a lógica muda** (não a cada comentário).
   - Hash das entradas = hash do **conteúdo** do artefato anterior, não da data do arquivo.
3. **Corte antecipado**: se uma etapa recalcula e o resultado sai idêntico ao anterior (mesmo hash de conteúdo), as
   etapas seguintes não são invalidadas.
4. **As partes mais instáveis vêm por último** e ficam baratas: o que muda toda hora (uniões, fusão de pequenas,
   tipo) roda sobre artefatos já gravados e, quando possível, sobre **tabelas** em vez de pixels.
5. **Gravação atômica** (`arquivo.tmp` → `os.replace`) e **retomada**: uma rodada interrompida continua de onde parou.

## 3. Como dividir cada etapa

### E4 (rotular) — a que mais pesa hoje

Hoje `rotular.py` faz tudo de uma vez por mapa (~9 s/mapa/processo). Dividir em sub-etapas com artefato próprio em
`.cache/v2/e4/<sub>/<id>.*` (a ordem exata segue o código; a regra é pôr antes o que é estável):

| Sub-etapa | Faz | Depende de | Artefato |
|---|---|---|---|
| E4a | zonas planas + classificação (mar / texto / semente) | mapa PNG, paleta, `LIM_BORDA`, `LIM_MAR`, `RAIO_TEXTO`, `AREA_TEXTO`, `FRACAO_VIZINHA` | `a/<id>.npz` (rótulos de zona int32 + classe por zona, comprimido) |
| E4b | watershed (partição sem frestas) | E4a, `AREA_SEMENTE` | `b/<id>.png` (16 bits) |
| E4c | costa (expansão sobre o mar onde `mundo.json` é terra) | E4b, calibração do mapa, `EXPANSAO_COSTA` | `c/<id>.png` |
| E4d | **estatísticas** de regiões e de pares vizinhos: cor mediana, área, borda comum em px, % de letra, % de linha, % de outro, gargalo, caixas de texto | E4c, E4a | `d/<id>.json` |
| E4e | **regras**: uniões, fusão de pequenas, ilhas, tipo, candidatos | E4c + E4d, parâmetros das regras | `rotulos/<id>.png` + `<id>.json` (formato atual) |

A E4e precisa de pixels só para **aplicar** a decisão (renumerar rótulos). A **decisão** sai da tabela da E4d. Então:

- mudar uma regra de união = refazer só a E4e, que é renumeração (≪ 1 s/mapa), em vez de 37 min;
- **testar** uma regra nova nem precisa de pixels: roda sobre `d/*.json` e sobre os 88 pares rotulados à mão
  (`pares.json`) em segundos. É assim que regras devem ser comparadas (como a tabela "≥ 70 % de letra / + veto…").

### E5 (vetorizar)

Chave por **hash do conteúdo** de `rotulos/<id>.png` + calibração do mapa + parâmetros (tolerância do
`coverage_simplify`, tremor, `mundo.json`). Se uma regra de união muda só 100 mapas, só esses 100 são vetorizados de
novo. A união de regiões já vetorizadas (decisão da E7) pode ser feita no vetor (união em cobertura) sem
revetorizar, mas a chave do vetor final precisa incluir a lista de uniões aplicadas.

### E7 (nomes)

O OCR é caro e as etiquetas se repetem por centenas de mapas (o mesmo "Byzantine Empire" no mesmo lugar). Fazer cache
**por recorte de texto**: chave = hash dos pixels do recorte + parâmetros do OCR. Etiquetas idênticas em mapas
diferentes são lidas uma vez só. A votação por entidade é barata e roda sempre.

### E2, E3, E6, E8

- E2 (quadros) e E3 (calibração) já estão prontas; basta gravar as chaves no manifesto para que mudanças nelas
  invalidem o que vem depois.
- E6 (rastreamento) e E8 (construir) são baratas: podem rodar inteiras, mas também usam chave para não regravar
  arquivos iguais (evita diffs falsos em `frontend/mapa-geral/dados/`).

## 4. Implementação

1. Módulo pequeno `scripts/mapa-geral/cache.py` (usado por todas as etapas):
   - `chave(versao, params, entradas) -> str`, `hash_arquivo(caminho) -> str` (com memória por `(caminho, mtime,
     tamanho)` para não reler arquivos grandes);
   - manifesto por etapa `.cache/v2/<etapa>/manifesto.json`: `{id: {"chave", "hash_saida", "segundos"}}`;
   - `precisa(etapa, id, chave) -> bool`, `gravar(etapa, id, chave, caminho_tmp)` (atômico, atualiza manifesto);
   - `--forcar` para ignorar o cache, e `--so-chaves` para listar o que seria recalculado sem rodar nada.
2. **Amostras fixas** (`scripts/mapa-geral/amostras.json`), usadas no ciclo de desenvolvimento:
   - `rapida` (~30 mapas): os 12 da revisão + os mapas dos 88 pares + mapas dos casos difíceis. Alvo: < 1 min.
   - `media` (~200 mapas): sorteio estratificado por trecho de enquadramento (semente fixa). Alvo: < 5 min.
   - `todos`: só quando a `rapida` e a `media` passam, e no portão da etapa.
   - Todos os scripts e o `testar.py` aceitam `--amostra rapida|media|todos`.
3. **Progresso e falhas**: log por mapa com tempo e estimativa de término (ETA); um mapa que falha é registrado e a
   rodada continua; ao fim, lista de falhas.
4. **Perfil**: medir o tempo de cada sub-etapa (o `rotulos-tempo.json` já existe) e atacar a maior. Alvos: rodada
   completa a frio da E4 ≤ 15 min; mudança só de regra (E4e) ≤ 2 min para os 1.965 mapas; rodada sem mudança
   nenhuma ≤ 1 min (só confere chaves).
5. **Arrumação do cache**: os scripts de experimento que estão em `.cache/v2/` (`exp_*.py`, `diag_*.py`, `terco.py`,
   `tiles.py`, `mk_casos.py`, etc.) vão para `scripts/mapa-geral/experimentos/` (o `.cache` deve ser descartável:
   apagar e regenerar não pode perder código). Um `limpar_cache.py` apaga artefatos que não estão em nenhum
   manifesto (versões antigas), mostrando o espaço que libera antes de apagar.

## 5. Testes (`testar.py cache`)

- **T-C1 Cache = recálculo**: para 20 ids sorteados de cada sub-etapa, recalcular do zero numa pasta temporária e
  comparar com o artefato do cache: **bytes idênticos** (rótulos e vetores) ou JSON igual. Pega `VERSAO` esquecida.
- **T-C2 Rodada vazia**: rodar de novo sem mudar nada → 0 itens recalculados, ≤ 1 min.
- **T-C3 Invalidação mínima**: mudar só um parâmetro de regra da E4e → a E4a–E4d recalculam 0 itens; a E5 recalcula
  só os mapas cujo `rotulos/<id>.png` mudou (comparar com a contagem do log).
- **T-C4 Retomada**: interromper uma rodada no meio (kill do processo) e rodar de novo → completa sem refazer o que
  já estava gravado e sem arquivo corrompido.
- **T-C5 Manifesto coerente**: todo artefato tem entrada no manifesto e vice-versa; nenhuma chave aponta para
  arquivo ausente.
- **T-C6 Refatoração sem mudança de resultado**: a primeira rodada completa com o código dividido (E4a–E4e) produz
  `rotulos/*` **idênticos** aos da rodada atual (a quinta), já que as regras não mudaram. É a prova de que dividir em
  etapas não mudou a qualidade.

## 6. Ordem de execução

1. **Não interromper a rodada atual** da E4: o resultado dela é válido e vira a referência do T-C6.
2. Rodar `testar.py e4` inteiro sobre ela (como já planejado).
3. Fazer a divisão da E4 (seção 3) + `cache.py` + amostras, **antes da E5**, para a E5 já nascer incremental.
4. Primeira rodada completa com o código novo → T-C6 (idêntico à referência) e T-C1…T-C5.
5. Seguir para a E5, já com chave por hash de rótulo. Na E7, cache de OCR por recorte.
6. Registrar no §11 de `docs/mapa-geral-plano-2.md` e acrescentar uma linha no §5 do plano apontando para este
   arquivo.

## 7. Loja por chave e variantes (decisão do usuário, 2026-10-15)

Motivo: um experimento na E5 (simplificação aresta por aresta) foi gravado por cima da versão aprovada e, ao falhar,
custou uma revetorização completa (~35 min) só para voltar ao que já existia.

1. **Um arquivo por chave, não por mapa.** As etapas versionadas (E4e, E5, E6 e, depois, E7) gravam cada resultado em
   `.cache/v2/obj/<etapa>/<chave>.<ext>` (imutável). `rotulos/<id>.png|json`, `vetores/<id>.json` e
   `entidades.json` são **apontadores** (links simbólicos relativos) para a variante aprovada. Trocar de versão é
   trocar os apontadores (`python3 scripts/mapa-geral/cache.py aprovar <etapa> <variante>`), sem recalcular.
2. **Experimento nunca sobrescreve o aprovado.** `--variante <nome>` (ou `MAPA_GERAL_EXP=<nome>`) grava só na loja e no
   manifesto; parâmetros de um experimento vão em `MAPA_GERAL_PARAMS='{"NOME": valor}'`. Uma variante só vira a
   aprovada depois de passar no portão inteiro. Rodar sem `--variante` com parâmetros diferentes dos da aprovada é
   recusado (pede um nome).
3. **Chave = lógica + parâmetros reais + conteúdo das entradas.** `VERSAO` muda só quando o código muda de um jeito
   que os parâmetros não descrevem (a simplificação aresta por aresta é a mesma lógica 4 da E5 com
   `SIMPLIFICACAO = "local"`). Voltar a uma lógica antiga dá a mesma chave: o objeto existente é reaproveitado
   (`Etapa.procurar` procura em todas as variantes).
4. **Manifesto com histórico** (`.cache/v2/<etapa>/manifesto.json`, formato 2): `aprovada`, `anterior` e
   `variantes` (cada uma com `params`, `criada`, `testes` e `itens` = {id: chave, hash, segundos}). O visualizador
   tem um seletor de variante que lê os objetos da loja.
5. **`limpar_cache.py`** lista o espaço de cada variante e apaga só o lixo (objetos sem variante, `.tmp`, pastas
   obsoletas). Uma variante só é apagada com `--variante <etapa> <nome> --apagar`, nunca a aprovada nem a anterior.
6. **Testes:** T-C5 confere loja, manifesto e apontadores; T-C3 roda o experimento numa variante e verifica que o
   aprovado não muda e que a rodada normal depois recalcula 0; **T-C7** troca o aprovado para a variante e volta:
   a volta recalcula 0 mapas e os arquivos são idênticos.
7. As sub-etapas E4a/E4b/E4d continuam com o manifesto por mapa (formato 1): são estáveis e caras de guardar em
   várias versões.
8. **E3 na loja (2026-10-16).** `calibrar.py` grava a calibração inteira como item da etapa `e3`
   (`.cache/v2/obj/e3/<chave>.json`; chave = `VERSAO` + parâmetros + `mapas.json` + `mundo.json` + conteúdo dos PNGs) e
   `calibracao.json` é o apontador para a variante aprovada; as etapas seguintes leem `cache.calibracao()` (honra
   `MAPA_GERAL_EXP`). Sem `--variante`, só roda sobre a aprovada se os parâmetros forem os mesmos; o arquivo de antes da
   loja foi adotado como variante `v1` (não recalculável: um cálculo novo sem nome vai para `base`). `transicoes.py`
   grava a calibração corrigida como variante `<aprovada>-transicoes` e a aprova; a anterior fica na loja.
9. **Painel** (`painel.py` + `painel.html`, no lugar de `visualizar.py` e `editor.py`): aba Versões (aprovar, voltar,
   apagar variantes), aba Mapas (estado de cada mapa por etapa, com as mesmas funções de chave dos scripts:
   `rotular.chave_sub`, `vetorizar.chave_mapa`, `nomear.chave_mapa`), aba Rodar (fila de rodadas, log, interromper) e
   comparação A/B de duas variantes na aba Mapa.
