# AGENTS.md

This file provides guidance to AI coding agents working in this repository.

Public static site ("Mapa da Bíblia") in plain HTML, CSS and JS. No build step, no package manager, no tests, no server code. Deployed on Vercel as static files from the repo root; accounts and reading progress live in Supabase (see "Contas e progresso" in the README).

@README.md

## Running

- `biblia/` fetches JSON, so it only works over HTTP: `python -m http.server` and open `http://localhost:8000/`. Supabase Auth redirects allow `http://localhost:8000/**`, so use port 8000 for login testing.

## Conventions

- All user-facing text, identifiers, comments and file names are in Portuguese (pt-BR). Keep it that way.
- JS is ES5 inside an IIFE (`var`, `function`, no arrow functions, no `let`/`const`, no modules). Match it.
- Wrap all `localStorage` access in try/catch (see `ler`/`gravar` in `biblia/biblia.js`). Keys: `notas-theme`, `biblioteca-colunas`, `biblia-leitor`, `biblia-mapa`; `biblioteca-lido` / `biblioteca-versiculos` are legacy, read only to import into the account on first login.
- Reading progress is saved only through `Conta.salvar(lido, leitura)` (`js/conta.js`). Marking must stay disabled when `conectado` is false in `biblia/leitura.js`, and progress must never be saved after a failed load, since the upsert replaces the whole row.
- The `progresso` table shape (`lido`, `versiculos` JSONB) mirrors the `lido` / `leitura` objects in `biblia/leitura.js`. Schema changes go in a new file in `supabase/migrations/`, and any new table needs RLS.
- `js/config.js` holds only the publishable key. Never put the secret / service_role key in the site.
- Colors are CSS variables in `css/global.css` with `[data-theme="light"]` / `[data-theme="dark"]` blocks. New colors need both. `js/theme.js` sets `data-theme` on `<html>`.
- Every page repeats the same `<head>` (fonts, favicon, theme-color) and `<header class="nav">`. Every page loads supabase-js (pinned CDN), `js/config.js` and `js/conta.js`, which injects the account menu into the nav. A nav or head change must be made in each HTML file: `index.html`, `biblia/index.html`, `biblia/mapa.html`, `biblia/ler.html`, `biblia/apoio.html`, `biblia/guia.html`, `entrar.html`, `privacidade.html`. Paths in subfolders use `../`.
- Years: a.C. is positive and d.C. is negative. `inicio` is always the older (larger) year.
