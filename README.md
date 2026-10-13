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
- `data/nvi.json`: texto da Bíblia (NVI), na mesma ordem de `canon.json`.
- `biblia/dados/mapas.json`: mapas de leitura. Cada mapa é uma lista de épocas (`era` de `eras.json`) com trechos `{livro, de, ate, nota}`; todo capítulo da Bíblia aparece uma única vez.
- `biblia/mapa.html` e `biblia/mapa.js`: página Mapa: lista os mapas, deixa escolher o mapa padrão e abre a leitura no modo mapa.
- `biblia/ler.html` e `biblia/ler.js`: leitor do texto, com livros, capítulos, tamanho da letra e última posição. Aberto pela aba Bíblia, o Próximo segue a ordem dos livros; aberto pelo botão do mapa (`ler.html?mapa=historico`), segue a ordem do mapa.
- `biblia/apoio.html` e `biblia/apoio.js`: material de apoio. O primeiro é o mapa da viagem de Abrão (Gn 11:27 – 12:9), em SVG próprio, que ocupa a tela toda, com zoom e arrastar. Os botões Apoio (rota e números das etapas) e Curiosidades (losangos da época, com filtro por região) ligam e desligam camadas; o texto de cada etapa ou curiosidade aparece num cartão ao tocar no número ou no losango. Os dados ficam em `biblia/dados/apoio.json` (contornos e lugares em longitude/latitude, rotas por etapa e `curiosidades` da época, com `lon`/`lat` quando cabem no mapa). O mapa é um mapa-múndi (projeção Mercator, de 58° S a 80° N); qualquer curiosidade com `lon`/`lat` aparece nele. Costas, lagos e rios são simplificados do Natural Earth (domínio público), com mais detalhe da Europa ao Oriente Médio.
- `biblia/dados/mundo.json`: base comum dos mapas de apoio (mapa-múndi, nomes e curiosidades da época). `biblia/dados/apoio.json` (viagem de Abrão) e `apoio-jo.json` (lugares de Jó) trazem só `lugares` e `etapas`; `apoio.html?m=jo` abre o segundo.
- `biblia/guia.html` e `biblia/guia.js`: guias de texto (esboço, personagens, listas) a partir de `biblia/dados/guia-*.json`; `guia.html?m=jo-esboco` abre `guia-jo-esboco.json`. Com `&cap=N`, destaca o que corresponde ao capítulo.
- `biblia/dados/materiais.json`: lista dos materiais de apoio e os capítulos a que se ligam (`capitulos`: `livro`, `de`, `ate`). Quando o capítulo aberto no leitor tem materiais, aparece o botão Apoio, que abre um popup com abas para trocar de material (a `url` abre com `?embutido`).
- `biblia/leitura.html` e `biblia/leitura.js`: Leitura, aberta como popup (botão Leitura) no leitor, onde se marca livros, capítulos e versículos lidos e se vê o progresso.

Anos: a.C. positivo e d.C. negativo (30 d.C. = `-30`). `inicio` é sempre o ano mais antigo. Cada trecho do eixo tem sua escala (`SEGMENTOS` em `biblia.js`).

Adicionar um rei: copie um objeto em `reis` e ajuste `id`, `reino` (`juda`, `israel`, `unido`), `inicio` e `fim` (o `inicio` é o ano maior).
Adicionar um profeta: copie um objeto em `profetas`. Os reis contemporâneos saem das datas e do reino; use `citados` para os reis nomeados no próprio livro.

## Contas e progresso

- `js/config.js`: URL do projeto Supabase e chave publicável (pública; quem protege os dados é o RLS).
- `js/conta.js`: login (Google e e-mail/senha), menu da conta no topo e leitura/gravação do progresso. Expõe `window.Conta`.
- `entrar.html`: entrar, criar conta, esqueci a senha e nova senha. `privacidade.html`: o que é guardado.
- `supabase/migrations/0001_progresso.sql`: tabela `progresso` (uma linha por usuário: `lido` e `versiculos` em JSONB) com RLS.

Sem login, a Leitura só consulta: nada é marcado. Com login, cada marcação é salva na conta cerca de 1 s depois. No primeiro login, o progresso antigo do navegador (`biblioteca-lido` e `biblioteca-versiculos`) sobe para a conta, se ela estiver vazia, e as chaves são apagadas.

No navegador ficam só o tema (`notas-theme`) as colunas visíveis (`biblioteca-colunas`) a posição e o tamanho da letra do leitor (`biblia-leitor`) e o mapa padrão e a posição em cada mapa (`biblia-mapa`).

Configuração do Supabase, do Google e da Vercel: veja `plan.md`.
