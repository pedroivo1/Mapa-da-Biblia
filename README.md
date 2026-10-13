# Mapa da Bíblia

Site estático em HTML, CSS e JS puros, sem build. O login e o progresso de cada pessoa ficam no Supabase; o site é publicado na Vercel.

## Ver localmente

A linha do tempo carrega JSON, então abra por um servidor local:

```
python -m http.server
```

e acesse `http://localhost:8000/`. Sem `js/config.js` preenchido, o mapa abre só para consulta.

## Linha do tempo bíblica (`biblia/`)

- `biblia/dados/reis.json`: reis, profetas e potências. Uma potência pode ter `periodos` (`id`, `nome`, `inicio`, `fim`, `nota`: dinastias, reis), mostrados dentro do bloco da potência: cada período leva o nome da potência e, abaixo, o seu próprio nome.
- `biblia/dados/livros.json`: livros (com o período que cobrem ou a data de escrita) e líderes (patriarcas, juízes, apóstolos).
- `biblia/dados/eras.json`: eras, com livros e ordem de leitura.
- `biblia/dados/canon.json`: os 66 livros com o número de versículos de cada capítulo (Almeida Corrigida Fiel), usado na página Leitura.
- `biblia/biblia.js`: mapa em colunas paralelas, com o tempo na vertical.
- `data/nvi.json`: texto da Bíblia (NVI), na mesma ordem de `canon.json`.
- `biblia/dados/mapas.json`: planos de leitura (o primeiro é o Plano histórico). Cada mapa é uma lista de épocas (`era` de `eras.json`) com trechos `{livro, de, ate, nota}`; todo capítulo da Bíblia aparece uma única vez.
- `biblia/mapa.html` e `biblia/mapa.js`: página Plano de leitura: lista os planos, deixa escolher o plano padrão e abre a leitura no modo mapa.
- `biblia/ler.html` e `biblia/ler.js`: leitor do texto, com livros, capítulos, tamanho da letra e última posição. Aberto pela aba Bíblia, o Próximo segue a ordem dos livros; aberto pelo botão do mapa (`ler.html?mapa=historico`), segue a ordem do mapa.
- `biblia/apoio.html` e `biblia/apoio.js`: Mapas (material de apoio), um mapa-múndi em SVG próprio (projeção Mercator, de 58° S a 80° N) que ocupa a tela toda, com zoom e arrastar (roda do mouse, pinça, toque duplo). O mapa traz só o nome dos lugares e as rotas de viagem tracejadas, com uma seta no sentido do caminho: quem lê liga os pontos com o texto do leitor. Uma lista recolhível de caixas de seleção, Rotas ("Origem → Destino"), mostra ou esconde cada rota. Rotas que seguem o mesmo caminho correm lado a lado, em faixas paralelas de largura fixa na tela. Os nomes são filtrados pelo zoom: de longe ficam os lugares mais citados e, ao ampliar, os outros aparecem sem se sobrepor. Costas, lagos e rios são simplificados do Natural Earth (domínio público), com mais detalhe da Europa ao Oriente Médio.
- `biblia/dados/mundo.json`: base comum dos mapas de apoio (mapa-múndi e nomes de regiões). Cada material (`apoio.json`, `apoio-jo.json`, `apoio-jaco.json`...) traz só `lugares` (`id`, `nome`, `lon`, `lat`, `lado`) e `etapas` (`lugar`, `titulo`, `caminho` com a rota em longitude/latitude); `apoio.html?m=jo` abre o de Jó. Os campos `texto` e `ref` das etapas não aparecem no mapa por enquanto.
- `biblia/materiais.html` e `biblia/materiais.js`: aba Mapas, a lista dos materiais de `materiais.json`, por livro. Por enquanto só há mapas. Material novo entra ali sozinho.
- `biblia/dados/materiais.json`: lista dos materiais de apoio e os capítulos a que se ligam (`capitulos`: `livro`, `de`, `ate`). Os materiais com `ano` aparecem como pontos na coluna Eras da linha do tempo; o ponto abre o mapa num popup, com o ano e o texto da Bíblia no cabeçalho. Quando o capítulo aberto no leitor tem materiais, aparece o botão Mapas, que abre um popup com abas para trocar de material (a `url` abre com `?embutido`).
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

No navegador ficam só o tema (`notas-theme`) as colunas visíveis (`biblioteca-colunas`) a posição e o tamanho da letra do leitor (`biblia-leitor`) e o plano padrão e a posição em cada plano (`biblia-mapa`).

Configuração do Supabase, do Google e da Vercel: veja `plan.md`.
