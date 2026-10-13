# Mapa da Bíblia

Site estático em HTML, CSS e JS puros, sem build. O login e o progresso de cada pessoa ficam no Supabase; o site é publicado na Vercel.

## Ver localmente

A linha do tempo carrega JSON, então abra por um servidor local:

```
python -m http.server
```

e acesse `http://localhost:8000/`. Sem `js/config.js` preenchido, o mapa abre só para consulta.

## Linha do tempo bíblica (`biblia/`)

- `biblia/dados/reis.json`: reis, profetas e potências.
- `biblia/dados/livros.json`: livros (com o período que cobrem ou a data de escrita) e líderes (patriarcas, juízes, apóstolos).
- `biblia/dados/eras.json`: eras, com livros e ordem de leitura.
- `biblia/dados/canon.json`: os 66 livros com o número de versículos de cada capítulo (Almeida Corrigida Fiel), usado na página Leitura.
- `biblia/biblia.js`: mapa em colunas paralelas, com o tempo na vertical.
- `biblia/leitura.html` e `biblia/leitura.js`: página Leitura, onde se marca livros, capítulos e versículos lidos e se vê o progresso.

Anos: a.C. positivo e d.C. negativo (30 d.C. = `-30`). `inicio` é sempre o ano mais antigo. Cada trecho do eixo tem sua escala (`SEGMENTOS` em `biblia.js`).

Adicionar um rei: copie um objeto em `reis` e ajuste `id`, `reino` (`juda`, `israel`, `unido`), `inicio` e `fim` (o `inicio` é o ano maior).
Adicionar um profeta: copie um objeto em `profetas`. Os reis contemporâneos saem das datas e do reino; use `citados` para os reis nomeados no próprio livro.

## Contas e progresso

- `js/config.js`: URL do projeto Supabase e chave publicável (pública; quem protege os dados é o RLS).
- `js/conta.js`: login (Google e e-mail/senha), menu da conta no topo e leitura/gravação do progresso. Expõe `window.Conta`.
- `entrar.html`: entrar, criar conta, esqueci a senha e nova senha. `privacidade.html`: o que é guardado.
- `supabase/migrations/0001_progresso.sql`: tabela `progresso` (uma linha por usuário: `lido` e `versiculos` em JSONB) com RLS.

Sem login, a página Leitura só consulta: nada é marcado. Com login, cada marcação é salva na conta cerca de 1 s depois. No primeiro login, o progresso antigo do navegador (`biblioteca-lido` e `biblioteca-versiculos`) sobe para a conta, se ela estiver vazia, e as chaves são apagadas.

No navegador ficam só o tema (`notas-theme`) e as colunas visíveis (`biblioteca-colunas`).

Configuração do Supabase, do Google e da Vercel: veja `plan.md`.
