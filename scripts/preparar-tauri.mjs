// Monta src-tauri/dist/ a partir de frontend/ para o app Tauri funcionar sem internet:
// copia o site, troca o supabase-js do CDN e as Google Fonts por cópias locais (scripts/tauri-vendor/)
// e esvazia o service worker. O site publicado em frontend/ não é alterado.
// Uso: node scripts/preparar-tauri.mjs  (o tauri.conf.json chama antes de dev e build)
import { cpSync, rmSync, mkdirSync, readFileSync, writeFileSync, readdirSync, statSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const raiz = join(dirname(fileURLToPath(import.meta.url)), "..");
const origem = join(raiz, "frontend");
const destino = join(raiz, "src-tauri", "dist");
const vendor = join(raiz, "scripts", "tauri-vendor");

rmSync(destino, { recursive: true, force: true });
cpSync(origem, destino, { recursive: true });
cpSync(vendor, join(destino, "vendor"), { recursive: true });

function arquivos(dir) {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? arquivos(p) : [p];
  });
}

let paginas = 0;
for (const p of arquivos(destino).filter((f) => f.endsWith(".html"))) {
  let h = readFileSync(p, "utf8");
  h = h.replace(/<script[^>]*src="https:\/\/cdn\.jsdelivr\.net\/npm\/@supabase\/[^"]*"[^>]*><\/script>/g, '<script src="/vendor/supabase.js"></script>');
  let pus = false;
  h = h.replace(/[ \t]*<link[^>]*fonts\.(googleapis|gstatic)\.com[^>]*>[ \t]*\n?/g, (l) => {
    if (pus || !/rel="stylesheet"/.test(l)) return "";
    pus = true;
    return '    <link rel="stylesheet" href="/vendor/fontes.css" />\n';
  });
  writeFileSync(p, h);
  paginas++;
}

// no app os arquivos já são locais: o service worker só serviria cópia velha
writeFileSync(join(destino, "sw.js"), "// Tauri: sem service worker\n");

const sobras = arquivos(destino)
  .filter((f) => /\.(html|css)$/.test(f) && !f.includes("/vendor/"))
  .filter((f) => /jsdelivr|googleapis|gstatic/.test(readFileSync(f, "utf8")));
if (sobras.length) {
  console.error("Ainda há recursos externos em:\n" + sobras.join("\n"));
  process.exit(1);
}
console.log(`src-tauri/dist pronto (${paginas} páginas)`);
