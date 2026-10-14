# Mapa da Bíblia

Site estático em HTML, CSS e JS puros, sem build. O login e o progresso de cada pessoa ficam no Supabase; o site é publicado na Vercel.

## Ver localmente

As páginas carregam JSON, então abra por um servidor local:

```
cd frontend
python -m http.server
```

e acesse `http://localhost:8000/`. Sem `compartilhado/js/config.js` preenchido, o mapa abre só para consulta.

## Organização

O repositório tem `frontend/` (o site publicado), `supabase/` (migrações) e `scripts/` (ferramentas). Dentro de `frontend/`, cada funcionalidade é uma pasta com tudo o que é dela: página (`index.html`), scripts, CSS e dados.
O que serve a mais de uma funcionalidade fica em `compartilhado/`.

| Pasta | O que é | Contém |
|---|---|---|
| `frontend/` (`index.html`, `inicio/`) | Página inicial | `inicio/inicio.css` |
| `biblia/` | Bíblia: leitor do texto (NVI), com livros, capítulos, tamanho da letra, voz e última posição. `?plano=id` segue a ordem de um plano; sem ele, a dos livros. Mostra os botões Leitura e Mapas do capítulo. | `biblia.js`, `biblia.css`, `nvi.json` |
| `plano-de-leitura/` | Planos de leitura (o primeiro é o Plano histórico): lista, ordem de cada um e plano padrão (exige conta). | `planos.json` |
| `linha-do-tempo/` | Colunas paralelas, com o tempo na vertical: eras, livros, reis e potências. | `lt-config.js`, `lt-filtros.js`, `lt-dados.js`, `lt-eixo.js`, `linha-do-tempo.js`, `reis.json`, `livros.json` |
| `mapas/` | Lista de mapas, por livro. Mapa novo entra sozinho. Os com `ano` aparecem como pontos na coluna Eras da linha do tempo. | `mapas.json` |
| `mapa/` | Um mapa aberto (`/mapa/?m=jo`): mapa-múndi em SVG próprio, com zoom, arrastar e lista de rotas. | `mapa.js`, `mapa-<id>.json`, `mundo.json` |
| `leitura/` | Leitura, aberta como popup no leitor: marcar livros, capítulos e versículos lidos e ver o progresso. | `leitura.js` |
| `conta/` | Entrar, criar conta, esqueci a senha e nova senha. | |
| `privacidade/` | O que é guardado. | |
| `compartilhado/` | Base de todas: `css/base.css` (tokens, nav, rodapé), `css/componentes.css` (cabeçalho, chips, popups), `js/` (`tema.js`, `config.js`, `util.js`, `conta.js`) e `dados/` (`canon.json`: 66 livros com os versículos de cada capítulo; `eras.json`). | |

Uma funcionalidade pode ler os arquivos de dados de outra (por exemplo, a linha do tempo lê `mapas/mapas.json`), mas não importa o JS dela.

### Dados

- `linha-do-tempo/reis.json`: reis, profetas e potências. Uma potência pode ter `periodos` (`id`, `nome`, `inicio`, `fim`, `nota`: dinastias, reis), mostrados dentro do bloco da potência.
- `linha-do-tempo/livros.json`: livros (com o período que cobrem ou a data de escrita) e líderes (patriarcas, juízes, apóstolos).
- `plano-de-leitura/planos.json`: cada plano é uma lista de épocas (`era` de `eras.json`) com trechos `{livro, de, ate, nota}`; todo capítulo da Bíblia aparece uma única vez.
- `mapas/mapas.json`: lista dos mapas e os capítulos a que se ligam (`capitulos`: `livro`, `de`, `ate`); `url` abre o mapa (com `?embutido` no popup do leitor).
- `mapa/mapa-<id>.json`: `lugares` (`id`, `nome`, `lon`, `lat`, `lado`, `incerto`) e `etapas` (`lugar`, `titulo`, `caminho` com a rota em longitude/latitude). `mapa/mundo.json` é a base comum (costas, lagos e rios do Natural Earth, domínio público, e nomes de regiões).

Anos: a.C. positivo e d.C. negativo (30 d.C. = `-30`). `inicio` é sempre o ano mais antigo. Cada trecho do eixo tem sua escala (`SEGMENTOS` em `linha-do-tempo.js`).

Adicionar um rei: copie um objeto em `reis` e ajuste `id`, `reino` (`juda`, `israel`, `unido`), `inicio` e `fim` (o `inicio` é o ano maior).
Adicionar um profeta: copie um objeto em `profetas`. Os reis contemporâneos saem das datas e do reino; use `citados` para os reis nomeados no próprio livro.

## Contas e progresso

- `compartilhado/js/config.js`: URL do projeto Supabase e chave publicável (pública; quem protege os dados é o RLS).
- `compartilhado/js/conta.js`: login (Google e e-mail/senha), menu da conta no topo e leitura/gravação do progresso. Expõe `window.Conta`.
- `conta/`: entrar, criar conta, esqueci a senha e nova senha. `privacidade/`: o que é guardado.
- `supabase/migrations/0001_progresso.sql`: tabela `progresso` (uma linha por usuário: `lido` e `versiculos` em JSONB) com RLS.
- `supabase/migrations/0002_configuracoes.sql`: tabela `configuracoes` (uma linha por usuário, `dados` em JSONB, com RLS). Chaves: `linha_do_tempo` (`desktop` e `mobile`: filtros de colunas e livros), `plano` (`padrao` e `pos`), `leitor` (livro, capítulo e tamanho da letra) e `tema`. Aplique no SQL Editor do Supabase.

Sem login, a Leitura só consulta: nada é marcado, e não há plano de leitura padrão (escolher o plano exige conta). Com login, cada marcação é salva na conta cerca de 1 s depois, e as configurações também. No primeiro login, o progresso antigo do navegador (`biblioteca-lido` e `biblioteca-versiculos`) sobe para a conta, se ela estiver vazia, e as chaves são apagadas.

Assim que a sessão é reconhecida, `js/conta.js` busca progresso e configurações em segundo plano e guarda uma cópia no navegador (`biblia-cache`, apagada ao sair). As páginas abrem com essa cópia na hora e o servidor só confirma ou atualiza; a Leitura mostra a cópia só para consulta e libera as marcações quando o servidor confirma (o envio substitui a linha inteira).

No navegador ficam o tema (`notas-theme`), os filtros da linha do tempo (`biblia-linha-do-tempo`, um conjunto para computador e outro para celular), a posição e o tamanho da letra do leitor (`biblia-leitor`), a posição em cada plano (`biblia-mapa`) e a cópia da conta (`biblia-cache`).

`scripts/verificar.mjs`: verificação de fumaça das páginas (`node scripts/verificar.mjs`).

Configuração do Supabase, do Google e da Vercel: veja `plan.md`.
