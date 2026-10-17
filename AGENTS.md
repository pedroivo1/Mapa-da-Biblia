# AGENTS.md

This file provides guidance to AI coding agents working in this repository.

Public static site ("Mapa da Bíblia") in plain HTML, CSS and JS. No build step, no package manager, no server code. The only check is `node scripts/verificar.mjs` (see Verifying). Deployed on Vercel as static files from `frontend/` (Root Directory setting); accounts and reading progress live in Supabase (see "Contas e progresso" in the README).

@README.md

## Running

- The pages fetch JSON, so they only work over HTTP: `cd frontend && python -m http.server` and open `http://localhost:8000/`. Supabase Auth redirects allow `http://localhost:8000/**`, so use port 8000 for login testing. VS Code Live Server is set to root `/frontend` in `.vscode/settings.json`; it must serve `frontend/` as `/`. All paths in HTML and JS are root-absolute (`/biblia/`, `/compartilhado/css/base.css`).

## Repository layout

- `frontend/`: the published site (everything below). `vercel.json` lives there too.
- `supabase/`: migrations (and Edge Functions, if any). Not published.
- `scripts/`: dev tools. Not published (Vercel serves only `frontend/`). `verificar.mjs`: smoke check. `mapa/`: Python generators (`territorios.py`, `roma.py`, `tremor.py`; need `shapely`) for `frontend/mapa/territorios-<ano>.json` and `roma.json`; hand-edited shapes go in `scripts/mapa/formas.json`. `mapa-geral/`: pipeline v2 that reads the reference video (frames, OCR of the year, calibration, labelling, vectorizing, tracking, OCR of state names) and builds `frontend/mapa-geral/dados/` year by year (`construir.py`; translations and hand corrections in `nomes.json`; tests in `testar.py e0…e8` and `testar-pagina.mjs`); needs numpy, opencv, shapely, tesserocr, rapidocr (in `~/.cache/mapa-biblia-lib/lib`); see `docs/mapa-geral-plano-2.md` and `docs/mapa-geral.md`. `mapa-geral/dados-cliopatria/`: the same map data (format 2) built from Cliopatria (Seshat, CC BY 4.0), kept here only as reference and never published, since the site reads only `frontend/mapa-geral/dados/`. `mapa-geral/painel.html` + `painel.py`: the local suite for the pipeline (never move it under `frontend/`); run `python3 scripts/mapa-geral/painel.py` (serves the repo root on 8001, 127.0.0.1 only) and open `/scripts/mapa-geral/painel.html`. Tabs: Mapa (video frame vs vectors year by year, casos/pares checks, variant selector and A/B comparison of two variants, click annotations — join / separate / problem — saved to `scripts/mapa-geral/anotacoes.json`, which the pipeline must honor as corrections and keep as tests), Mapas (grid with the state of every distinct map in every stage, computed with the same cache keys as the scripts), Versões (variants of the keyed store per stage: approve, revert, delete), Rodar (queue of pipeline runs with live log; one at a time), Andamento (manifests and logs), Revisão (review images) and Editor (`editor.html`, the local editor of the published map data: merge two states, rename pt/en, recolor, move/add/delete vertices, Adobe-style shortcuts; it saves every edit to `scripts/mapa-geral/edicoes.json`, applies it to `frontend/mapa-geral/dados/` at once, and `construir.py` re-applies the file after each regeneration). `escala.py`: the pipeline is written for 1920×960 frames; `MAPA_GERAL_ESCALA=2` runs the geometry on 3840×1920 frames and `MAPA_GERAL_ESCALA_OCR=4` reads the labels from the 7680×3840 frames (every pixel constant goes through `escala.px/area/it/impar`; scale 1 must stay byte-identical, `testar.py cache` proves it); a run in another scale uses another cache root (`MAPA_GERAL_CACHE`, e.g. `.cache-4k`, driven by `cadeia-4k.sh`). The videos live in `vídeos/` (git-ignored, never commit them; the main one is the 8K `*8k.mp4`). `editor-mapas.html`: local vertex editor for those shapes (`python3 -m http.server` at the repo root, open `/scripts/editor-mapas.html`); it must never be moved under `frontend/`.
- `docs/`: design notes (`mapa-geral.md`, `mapa-geral-plano.md`). Not published.

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
| (mapa aberto) | `mapa/` (`?m=id`) | `mapa.js`, `mapa.css` | `mapa-<id>.json`, `mundo.json` |
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
- Every page repeats the same `<head>` (fonts, favicon, theme-color) and `<header class="nav">`. Every page loads supabase-js (pinned CDN), `/compartilhado/js/config.js`, `util.js` and `conta.js`, which injects the account menu into the nav. A nav or head change must be made in each slice's `index.html`: `index.html`, `biblia/`, `plano-de-leitura/`, `versiculos/`, `linha-do-tempo/`, `mapas/`, `mapa/`, `mapa-geral/`, `leitura/`, `conta/`, `privacidade/`. Paths are root-absolute.
- Years: a.C. is positive and d.C. is negative. `inicio` is always the older (larger) year.
- Borders and territories (provinces in `mapa/roma.json`, peoples in `mapa/territorios-<ano>.json`, hand-drawn regions, states of `mapa-geral/`): two styles are allowed, and the choice is made per dataset. **Straight** (the historical rule, still used by `mapa/`): only straight segments, with a deterministic "tremor" for realism: every edge becomes a polyline of short straight segments (~0.35° each) displaced perpendicular by a small, repeatable amount (~0.045°). **Curved** (allowed since 2026-10-17, `vetorizar.py` with `CURVAS > 0`): each shared edge is smoothed by Chaikin corner cutting with its end nodes fixed, no tremor. In both styles the same edge must produce the same points in either direction, so neighbours share the border exactly; never smooth or buffer a polygon on its own. Where a territory meets the coast it follows the coast of `mundo.json` exactly (no simplifying, no gaps). When generating or editing these shapes with buffers, use mitre joins (`join_style=2`). Territories never overlap: where two peoples/provinces meet, one cuts the other by a fixed priority and the shared edge is drawn once.
