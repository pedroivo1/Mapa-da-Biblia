# AGENTS.md

This file provides guidance to AI coding agents working in this repository.

Public static site ("Mapa da Bíblia") in plain HTML, CSS and JS. No build step, no package manager, no server code. The only check is `node scripts/verificar.mjs` (see Verifying). Deployed on Vercel as static files from `frontend/` (Root Directory setting); accounts and reading progress live in Supabase (see "Contas e progresso" in the README).

@README.md

## Running

- The pages fetch JSON, so they only work over HTTP: `cd frontend && python -m http.server` and open `http://localhost:8000/`. Supabase Auth redirects allow `http://localhost:8000/**`, so use port 8000 for login testing. VS Code Live Server is set to root `/frontend` in `.vscode/settings.json`; it must serve `frontend/` as `/`. All paths in HTML and JS are root-absolute (`/biblia/`, `/compartilhado/css/base.css`).

## Repository layout

- `frontend/`: the published site (everything below). `vercel.json` lives there too.
- `supabase/`: migrations (and Edge Functions, if any). Not published.
- `scripts/`: dev tools of the site. Not published (Vercel serves only `frontend/`). `verificar.mjs`: smoke check. `preparar-tauri.mjs`, `instalar-tauri.sh`, `tauri-vendor/`: Tauri app. Everything that generates the map data (video pipeline, `previas.mjs`, map generators, editors, `docs/mapa-geral*.md`, `vídeos/`) lives in the sibling repository `../Mapa-da-Biblia-Mapas`, which writes everything it generates into its own `saida/` folder (same layout as `frontend/`); rerun it there after changing a map, its territories or the colors, then copy `saida/` over `frontend/` (`sh scripts/publicar.sh` there) and commit here.
- App Tauri (`src-tauri/`): `scripts/preparar-tauri.mjs` monta `src-tauri/dist/` (git-ignored) a partir de `frontend/`, trocando o supabase-js do CDN e as Google Fonts pelas cópias de `scripts/tauri-vendor/`; o `tauri.conf.json` roda o script antes de dev e build. No app (`window.__TAURI_INTERNALS__`), `compartilhado/js/conta.js` guarda cópia local da conta e uma fila offline (`pendProgresso`, `pendMarcacoes`, `pend` em `biblia-cache`) que sobe ao voltar a rede; no site comum esse código não roda.

## Architecture: vertical slices (inside `frontend/`)

The site is about the Bible. Each feature is a folder under `frontend/` (a slice) holding everything it owns: `index.html`, its scripts, its CSS and its data. Slices never import each other's JS; shared code lives in `compartilhado/`. A slice may fetch another slice's JSON file (a public data contract), e.g. `linha-do-tempo` reads `/mapas/mapas.json`.

| Nav tab | Slice (URL) | Files | Data it owns |
|---|---|---|---|
| (home) | `index.html`, `inicio/` | `inicio/inicio.css` | |
| Bíblia | `biblia/` (`/biblia/`, `?plano=id`) | `biblia.js`, `biblia.css` | `nvi.json` |
| Plano de leitura | `plano-de-leitura/` | `plano-de-leitura.js`, `.css` | `planos.json` |
| Versículos | `versiculos/` | `versiculos.js`, `versiculos.css` | (reads `marcacoes` through `Conta`) |
| Linha do tempo | `linha-do-tempo/` | `lt-config.js`, `lt-filtros.js`, `lt-dados.js`, `lt-eixo.js`, `linha-do-tempo.js`, `.css` | `reis.json`, `livros.json` |
| Mapas | `mapas/` | `mapas.js`, `mapas.css` | `mapas.json` (catalog) |
| (mapa aberto) | `mapa/` (`?m=id`) | `mapa.js`, `mapa.css` | `mapa-<id>.json`, `geral-<ano>.json` (estados do mapa geral no ano do mapa, gerados por `scripts/mapa/geral.py`), `mundo.json` |
| (mapa geral) | `mapa-geral/` (`?ano=-30`) | `mapa-geral.js`, `mapa-geral.css` | `dados/indice.json`, `dados/blocos/<a\|d><ano>.json` (um por 25 anos) |
| (popup do leitor) | `leitura/` | `leitura.js`, `leitura.css` | |
| (login) | `conta/` | inline script | |
| (privacidade) | `privacidade/` | | |
| shared kernel | `compartilhado/` | `css/base.css`, `css/componentes.css`, `js/{tema,config,util,conta,projecao}.js` | `dados/canon.json`, `dados/eras.json` |

- Add a feature: create a new folder with `index.html` (copy the `<head>` and `<header class="nav">` from another slice), the script and the CSS. Put in `compartilhado/` only what a second slice needs, and add the page to `scripts/verificar.mjs`.
- CSS: `base.css` (tokens, nav, footer) loads everywhere, `componentes.css` on pages of the Bible features, then the slice's own file. Class prefixes match the slice: `.lt-*`/`.regua-*`/`.filtro-*` (timeline), `.leitor-*`, `.plano-*`, `.mapa-*` (open map), `.mapas-*` (list). A rule used by two slices goes in `componentes.css`; do not copy it.
- Timeline scripts load in this order and share the global `LT` (no modules): `lt-config.js` (constants: time axis `SEGMENTOS`, names, `MARCOS`), `lt-filtros.js` (column/book filters, desktop vs mobile, saved in the account), `lt-dados.js` (`preparar`, detail panel text), `lt-eixo.js` (`Y(ano)`, ruler, smooth scroll), `linha-do-tempo.js` (drawing in `vistaFaixas`, events, startup). `LT.colunas` and `LT.dados` are single objects filled in place; never reassign them.
- `compartilhado/js/util.js` (`Util.ler/gravar/apagar/esc`): shared localStorage and HTML escaping. Do not copy these into slice scripts.
- `compartilhado/js/conta.js` (`window.Conta`): login, progress, settings, verse markings (`carregarMarcacoes`, `marcacoesGuardadas`, `salvarMarcacoes`: one row per verse in table `marcacoes`, with `grifo`, `salvo`, `temas`; the reader `biblia/` writes them and `versiculos/` lists them), local cache. `tema.js`: theme toggle and nav menu button. `config.js`: Supabase URL and publishable key.
- Each script starts with a header comment saying what it does and which data it reads; read it before editing.
- Account data: `progresso` (read/mark progress) and `configuracoes` (JSON keys `linha_do_tempo` {desktop, mobile}, `plano`, `ritmo`, `leitor`, `tema`). Slices read settings through `Conta.config()` and write with `Conta.salvarConfig(chave, valor)`; they keep a localStorage copy for logged-out use.

## Verifying

`node scripts/verificar.mjs` serves the repo, opens each page in headless Chrome at 1280 and 360 px, and fails on a missing render, a console error or sideways scroll. Run it after any change to HTML, CSS or JS, and add the new page to its `PAGINAS` list when you create one.

## Conventions

- All user-facing text, identifiers, comments and file names are in Portuguese (pt-BR). Keep it that way.
- JS is ES5 inside an IIFE (`var`, `function`, no arrow functions, no `let`/`const`, no modules). Match it. Exception: `scripts/verificar.mjs` is a dev tool (Node 22), not shipped.
- Wrap all `localStorage` access in try/catch (use `Util.ler`/`Util.gravar`/`Util.apagar` from `compartilhado/js/util.js`; the only raw uses are `compartilhado/js/tema.js`, which loads before it, and the theme string in `conta.js`). Keys: `notas-theme`, `biblia-linha-do-tempo`, `biblia-leitor`, `biblia-mapa`, `biblia-ritmo`, `biblia-cache`; `biblioteca-colunas`, `biblioteca-lido` / `biblioteca-versiculos` are legacy, read only to import into the account on first login.
- Reading progress is saved only through `Conta.salvar(lido, leitura)` (`compartilhado/js/conta.js`). Marking must stay disabled when `conectado` is false in `leitura/leitura.js`, and progress must never be saved after a failed load, since the upsert replaces the whole row.
- The `progresso` table shape (`lido`, `versiculos` JSONB) mirrors the `lido` / `leitura` objects in `leitura/leitura.js`. Schema changes go in a new file in `supabase/migrations/`, and any new table needs RLS.
- `compartilhado/js/config.js` holds only the publishable key. Never put the secret / service_role key in the site.
- Colors are CSS variables in `compartilhado/css/base.css` with `[data-theme="light"]` / `[data-theme="dark"]` blocks. New colors need both. `compartilhado/js/tema.js` sets `data-theme` on `<html>`.
- Every page repeats the same `<head>` (fonts, favicon, theme-color) and `<header class="nav">`. Every page loads supabase-js (pinned CDN), `/compartilhado/js/config.js`, `util.js` and `conta.js`, which injects the account menu into the nav. A nav or head change must be made in each slice's `index.html`: `index.html`, `biblia/`, `plano-de-leitura/`, `versiculos/`, `linha-do-tempo/`, `mapas/`, `mapa/`, `mapa-geral/`, `leitura/`, `conta/`, `privacidade/`. Paths are root-absolute.
- Years: a.C. is positive and d.C. is negative. `inicio` is always the older (larger) year.
- Borders and territories (provinces in `mapa/roma.json`, peoples in `mapa/territorios-<ano>.json`, hand-drawn regions, states of `mapa-geral/`): two styles are allowed, and the choice is made per dataset. **Straight** (the historical rule, still used by `mapa/`): only straight segments, with a deterministic "tremor" for realism: every edge becomes a polyline of short straight segments (~0.35° each) displaced perpendicular by a small, repeatable amount (~0.045°). **Curved** (allowed since 2026-10-17, `vetorizar.py` with `CURVAS > 0`): each shared edge is smoothed by Chaikin corner cutting with its end nodes fixed, no tremor. In both styles the same edge must produce the same points in either direction, so neighbours share the border exactly; never smooth or buffer a polygon on its own. Where a territory meets the coast it follows the coast of `mundo.json` exactly (no simplifying, no gaps). When generating or editing these shapes with buffers, use mitre joins (`join_style=2`). Territories never overlap: where two peoples/provinces meet, one cuts the other by a fixed priority and the shared edge is drawn once.
