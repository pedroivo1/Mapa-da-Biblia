# AGENTS.md

This file provides guidance to AI coding agents working in this repository.

Public static site ("Mapa da Bíblia") in plain HTML, CSS and JS. No build step, no package manager, no server code. The only check is `node scripts/verificar.mjs` (see Verifying). Deployed on Vercel as static files from `frontend/` (Root Directory setting); accounts and reading progress live in Supabase (see "Contas e progresso" in the README).

@README.md

## Running

- The pages fetch JSON, so they only work over HTTP: `cd frontend && python -m http.server` and open `http://localhost:8000/`. Supabase Auth redirects allow `http://localhost:8000/**`, so use port 8000 for login testing. VS Code Live Server is set to root `/frontend` in `.vscode/settings.json`; it must serve `frontend/` as `/`. All paths in HTML and JS are root-absolute (`/biblia/`, `/compartilhado/css/base.css`).

## Repository layout

- `frontend/`: the published site (everything below). `vercel.json` lives there too.
- `supabase/`: migrations (and Edge Functions, if any). Not published.
- `scripts/`: dev tools (`verificar.mjs`). Not published.
- `AGENTS.md`, `README.md`: docs.

## Architecture: vertical slices (inside `frontend/`)

The site is about the Bible. Each feature is a folder under `frontend/` (a slice) holding everything it owns: `index.html`, its scripts, its CSS and its data. Slices never import each other's JS; shared code lives in `compartilhado/`. A slice may fetch another slice's JSON file (a public data contract), e.g. `linha-do-tempo` reads `/mapas/mapas.json`.

| Nav tab | Slice (URL) | Files | Data it owns |
|---|---|---|---|
| (home) | `index.html`, `inicio/` | `inicio/inicio.css` | |
| Bíblia | `biblia/` (`/biblia/`, `?plano=id`) | `biblia.js`, `biblia.css` | `nvi.json` |
| Plano de leitura | `plano-de-leitura/` | `plano-de-leitura.js`, `.css` | `planos.json` |
| Linha do tempo | `linha-do-tempo/` | `lt-config.js`, `lt-filtros.js`, `lt-dados.js`, `lt-eixo.js`, `linha-do-tempo.js`, `.css` | `reis.json`, `livros.json` |
| Mapas | `mapas/` | `mapas.js`, `mapas.css` | `mapas.json` (catalog) |
| (mapa aberto) | `mapa/` (`?m=id`) | `mapa.js`, `mapa.css` | `mapa-<id>.json`, `mundo.json` |
| (popup do leitor) | `leitura/` | `leitura.js`, `leitura.css` | |
| (login) | `conta/` | inline script | |
| (privacidade) | `privacidade/` | | |
| shared kernel | `compartilhado/` | `css/base.css`, `css/componentes.css`, `js/{tema,config,util,conta}.js` | `dados/canon.json`, `dados/eras.json` |

- Add a feature: create a new folder with `index.html` (copy the `<head>` and `<header class="nav">` from another slice), the script and the CSS. Put in `compartilhado/` only what a second slice needs, and add the page to `scripts/verificar.mjs`.
- CSS: `base.css` (tokens, nav, footer) loads everywhere, `componentes.css` on pages of the Bible features, then the slice's own file. Class prefixes match the slice: `.lt-*`/`.regua-*`/`.filtro-*` (timeline), `.leitor-*`, `.plano-*`, `.mapa-*` (open map), `.mapas-*` (list). A rule used by two slices goes in `componentes.css`; do not copy it.
- Timeline scripts load in this order and share the global `LT` (no modules): `lt-config.js` (constants: time axis `SEGMENTOS`, names, `MARCOS`), `lt-filtros.js` (column/book filters, desktop vs mobile, saved in the account), `lt-dados.js` (`preparar`, detail panel text), `lt-eixo.js` (`Y(ano)`, ruler, smooth scroll), `linha-do-tempo.js` (drawing in `vistaFaixas`, events, startup). `LT.colunas` and `LT.dados` are single objects filled in place; never reassign them.
- `compartilhado/js/util.js` (`Util.ler/gravar/apagar/esc`): shared localStorage and HTML escaping. Do not copy these into slice scripts.
- `compartilhado/js/conta.js` (`window.Conta`): login, progress, settings, local cache. `tema.js`: theme toggle and nav menu button. `config.js`: Supabase URL and publishable key.
- Each script starts with a header comment saying what it does and which data it reads; read it before editing.
- Account data: `progresso` (read/mark progress) and `configuracoes` (JSON keys `linha_do_tempo` {desktop, mobile}, `plano`, `leitor`, `tema`). Slices read settings through `Conta.config()` and write with `Conta.salvarConfig(chave, valor)`; they keep a localStorage copy for logged-out use.

## Verifying

`node scripts/verificar.mjs` serves the repo, opens each page in headless Chrome at 1280 and 360 px, and fails on a missing render, a console error or sideways scroll. Run it after any change to HTML, CSS or JS, and add the new page to its `PAGINAS` list when you create one.

## Conventions

- All user-facing text, identifiers, comments and file names are in Portuguese (pt-BR). Keep it that way.
- JS is ES5 inside an IIFE (`var`, `function`, no arrow functions, no `let`/`const`, no modules). Match it. Exception: `scripts/verificar.mjs` is a dev tool (Node 22), not shipped.
- Wrap all `localStorage` access in try/catch (use `Util.ler`/`Util.gravar`/`Util.apagar` from `compartilhado/js/util.js`; the only raw uses are `compartilhado/js/tema.js`, which loads before it, and the theme string in `conta.js`). Keys: `notas-theme`, `biblia-linha-do-tempo`, `biblia-leitor`, `biblia-mapa`, `biblia-cache`; `biblioteca-colunas`, `biblioteca-lido` / `biblioteca-versiculos` are legacy, read only to import into the account on first login.
- Reading progress is saved only through `Conta.salvar(lido, leitura)` (`compartilhado/js/conta.js`). Marking must stay disabled when `conectado` is false in `leitura/leitura.js`, and progress must never be saved after a failed load, since the upsert replaces the whole row.
- The `progresso` table shape (`lido`, `versiculos` JSONB) mirrors the `lido` / `leitura` objects in `leitura/leitura.js`. Schema changes go in a new file in `supabase/migrations/`, and any new table needs RLS.
- `compartilhado/js/config.js` holds only the publishable key. Never put the secret / service_role key in the site.
- Colors are CSS variables in `compartilhado/css/base.css` with `[data-theme="light"]` / `[data-theme="dark"]` blocks. New colors need both. `compartilhado/js/tema.js` sets `data-theme` on `<html>`.
- Every page repeats the same `<head>` (fonts, favicon, theme-color) and `<header class="nav">`. Every page loads supabase-js (pinned CDN), `/compartilhado/js/config.js`, `util.js` and `conta.js`, which injects the account menu into the nav. A nav or head change must be made in each slice's `index.html`: `index.html`, `biblia/`, `plano-de-leitura/`, `linha-do-tempo/`, `mapas/`, `mapa/`, `leitura/`, `conta/`, `privacidade/`. Paths are root-absolute.
- Years: a.C. is positive and d.C. is negative. `inicio` is always the older (larger) year.
