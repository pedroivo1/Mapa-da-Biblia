# Mapa da Bíblia

Site estático em HTML, CSS e JS puros. Sem build, sem servidor.

## Ver localmente

A linha do tempo carrega JSON, então abra por um servidor local:

```
python -m http.server
```

e acesse `http://localhost:8000/`. As notas abrem direto do arquivo.

## Linha do tempo bíblica (`biblia/`)

- `biblia/dados/reis.json`: reis, profetas e potências.
- `biblia/dados/livros.json`: livros (com o período que cobrem ou a data de escrita) e líderes (patriarcas, juízes, apóstolos).
- `biblia/dados/eras.json`: eras, com livros e ordem de leitura.
- `biblia/dados/canon.json`: os 66 livros com o número de versículos de cada capítulo (Almeida Corrigida Fiel), usado no popup de leitura.
- `biblia/biblia.js`: mapa em colunas paralelas, com o tempo na vertical, e progresso.

Anos: a.C. positivo e d.C. negativo (30 d.C. = `-30`). `inicio` é sempre o ano mais antigo. Cada trecho do eixo tem sua escala (`SEGMENTOS` em `biblia.js`).

Adicionar um rei: copie um objeto em `reis` e ajuste `id`, `reino` (`juda`, `israel`, `unido`), `inicio` e `fim` (o `inicio` é o ano maior).
Adicionar um profeta: copie um objeto em `profetas`. Os reis contemporâneos saem das datas e do reino; use `citados` para os reis nomeados no próprio livro.

O progresso fica no `localStorage`, neste navegador: capítulos e versículos em `biblioteca-versiculos` (botão "Marcar leitura") e reis e eras em `biblioteca-lido`.
