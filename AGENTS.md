# AGENTS.md

This file provides guidance to AI coding agents working in this repository.

Personal static site ("Mapa da Bíblia") in plain HTML, CSS and JS. No build step, no package manager, no tests, no server code, not deployed. Not a git repo.

@README.md

## Running

- `biblia/` fetches JSON, so it only works over HTTP: `python -m http.server` and open `http://localhost:8000/`. Pages under `notas/` open fine from `file://`.

## Conventions

- All user-facing text, identifiers, comments and file names are in Portuguese (pt-BR). Keep it that way.
- JS is ES5 inside an IIFE (`var`, `function`, no arrow functions, no `let`/`const`, no modules). Match it.
- Wrap all `localStorage` access in try/catch (see `ler`/`gravar` in `biblia/biblia.js`). Existing keys: `notas-theme`, `biblioteca-lido`, `biblioteca-colunas`, `biblioteca-versiculos`. Don't rename them, since that would wipe the user's saved reading progress.
- Colors are CSS variables in `css/global.css` with `[data-theme="light"]` / `[data-theme="dark"]` blocks. New colors need both. `js/theme.js` sets `data-theme` on `<html>`.
- Every page repeats the same `<head>` (fonts, favicon, theme-color) and `<header class="nav">`. A nav or head change must be made in each HTML file: `index.html`, `biblia/index.html`, `notas/*.html`. Paths in subfolders use `../`.
- Years: a.C. is positive and d.C. is negative. `inicio` is always the older (larger) year.
