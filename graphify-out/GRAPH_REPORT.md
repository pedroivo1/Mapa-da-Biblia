# Graph Report - frontend  (2026-10-19)

## Corpus Check
- Large corpus: 369 files · ~7,795,994 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 414 nodes · 922 edges · 18 communities (14 shown, 4 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 99 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Conta e Supabase
- Leitor da Bíblia
- Mapa Geral
- Mapa Aberto
- Linha do Tempo
- Plano de Leitura
- Popup de Leitura
- Versículos Salvos
- Eixo da Linha do Tempo
- Config e Tema
- Utilidades
- Filtros da Linha
- Páginas HTML e CSS
- Projeção Equal Earth
- Dados da Linha
- Versão da Bíblia
- Config Vercel

## God Nodes (most connected - your core abstractions)
1. `cacheLer()` - 15 edges
2. `reguaDeRolagem()` - 14 edges
3. `cacheGravar()` - 13 edges
4. `enviar()` - 13 edges
5. `render()` - 13 edges
6. `vistaFaixas()` - 13 edges
7. `render()` - 11 edges
8. `iniciarBusca()` - 10 edges
9. `enviarConfig()` - 10 edges
10. `aplicar()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `corpo()` --indirect_call--> `esc()`  [INFERRED]
  linha-do-tempo/lt-dados.js → compartilhado/js/util.js
- `renderLista()` --indirect_call--> `esc()`  [INFERRED]
  versiculos/versiculos.js → compartilhado/js/util.js
- `estadoVista()` --indirect_call--> `atual()`  [INFERRED]
  mapa-geral/mapa-geral.js → compartilhado/js/versao.js
- `irPara()` --indirect_call--> `atual()`  [INFERRED]
  mapa-geral/mapa-geral.js → compartilhado/js/versao.js
- `mostrar()` --indirect_call--> `atual()`  [INFERRED]
  mapa-geral/mapa-geral.js → compartilhado/js/versao.js

## Import Cycles
- None detected.

## Communities (18 total, 4 thin omitted)

### Community 0 - "Conta e Supabase"
Cohesion: 0.10
Nodes (51): agendarSincronia(), aplicarMarcacoes(), aplicarTema(), avisarOffline(), aviso(), cacheGravar(), cacheLer(), cacheLimpar() (+43 more)

### Community 1 - "Leitor da Bíblia"
Cohesion: 0.11
Nodes (42): abrirEscolha(), abrirMapas(), abrirSalvar(), adicionarTema(), alternarCapitulos(), alternarVerso(), anterior(), aplicarMarcacoes() (+34 more)

### Community 2 - "Mapa Geral"
Cohesion: 0.12
Nodes (35): atual(), agendarVista(), ajustarNomes(), ajustarRios(), alternarPlay(), anoDePos(), aplicar(), arquivoBloco() (+27 more)

### Community 3 - "Mapa Aberto"
Cohesion: 0.12
Nodes (37): alturaDoMapa(), aplicar(), aplicarCapitulos(), calcularFaixas(), citada(), construirBarra(), corRegiao(), dentro() (+29 more)

### Community 4 - "Linha do Tempo"
Cohesion: 0.12
Nodes (25): abrir(), anoNoCentro(), anoParaMapa(), aplicarMapaGeral(), arrastarColunas(), celulas(), soltar(), criarDivisor() (+17 more)

### Community 5 - "Plano de Leitura"
Cohesion: 0.16
Nodes (27): alternarPop(), capLido(), controleRitmo(), dataDe(), desenharCal(), diasDeLeitura(), dividir(), dividirSemMemo() (+19 more)

### Community 6 - "Popup de Leitura"
Cohesion: 0.17
Nodes (26): aplicarProgresso(), atualizarProgresso(), capsComAlgo(), capsCompletos(), capsEm(), carregarProgresso(), estado(), falhaProgresso() (+18 more)

### Community 7 - "Versículos Salvos"
Cohesion: 0.18
Nodes (25): abrirEditar(), adicionarTema(), agrupar(), alvoDe(), aplicar(), aviso(), carregar(), chaveTemas() (+17 more)

### Community 8 - "Eixo da Linha do Tempo"
Cohesion: 0.21
Nodes (16): anoDeY(), reguaDeRolagem(), animar(), passo(), aPartirDoPonteiro(), atualizar(), construir(), levar() (+8 more)

### Community 10 - "Utilidades"
Cohesion: 0.13
Nodes (6): botaoFechar(), confirmar(), dialogo(), esc(), json(), mostrar()

### Community 11 - "Filtros da Linha"
Cohesion: 0.19
Nodes (13): ajustarColunas(), colunasDoPerfil(), copia(), grupoLigado(), gruposAtuais(), guardarColunas(), livrosAtivos(), padraoColunas() (+5 more)

### Community 13 - "Projeção Equal Earth"
Cohesion: 0.32
Nodes (3): criar(), equalEarth(), inversa()

### Community 14 - "Dados da Linha"
Cohesion: 0.43
Nodes (6): carregarDados(), chip(), corpo(), periodo(), preparar(), rotuloPeriodo()

### Community 15 - "Versão da Bíblia"
Cohesion: 0.38
Nodes (3): definir(), existe(), popup()

## Knowledge Gaps
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `atual()` connect `Mapa Geral` to `Versão da Bíblia`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `reguaDeRolagem()` (e.g. with `atualizar()` and `posicionar()`) actually correct?**
  _`reguaDeRolagem()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `Conta e Supabase` be split into smaller, more focused modules?**
  _Cohesion score 0.09935064935064936 - nodes in this community are weakly interconnected._
- **Should `Leitor da Bíblia` be split into smaller, more focused modules?**
  _Cohesion score 0.113107822410148 - nodes in this community are weakly interconnected._
- **Should `Mapa Geral` be split into smaller, more focused modules?**
  _Cohesion score 0.12051282051282051 - nodes in this community are weakly interconnected._
- **Should `Mapa Aberto` be split into smaller, more focused modules?**
  _Cohesion score 0.12051282051282051 - nodes in this community are weakly interconnected._
- **Should `Linha do Tempo` be split into smaller, more focused modules?**
  _Cohesion score 0.11586452762923351 - nodes in this community are weakly interconnected._