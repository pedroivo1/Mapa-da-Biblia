// Verificação de fumaça: abre cada página num Chrome sem janela, em tela larga e em 360px,
// e confere que desenha o conteúdo, não dá erro no console e não rola para o lado.
//
//   node scripts/verificar.mjs          (Node 22+, Chrome ou Chromium instalado; sem dependências)
//   CHROME=/caminho/do/chrome node scripts/verificar.mjs
//
// Sobe um servidor local temporário (python3 -m http.server) numa porta livre.
import { spawn, execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

// o site publicado fica em frontend/; é essa pasta que o servidor local serve
const RAIZ = join(dirname(fileURLToPath(import.meta.url)), "..", "frontend");
const PORTA_SITE = 8765;
const PORTA_CDP = 9765;

// [caminho, expressão que deve dar um número > 0 quando a página desenhou]
const PAGINAS = [
  ["", 'document.querySelectorAll(".note-row").length'],
  ["conta/", 'document.querySelectorAll("form, button").length'],
  ["privacidade/", 'document.querySelectorAll("h2").length'],
  ["linha-do-tempo/", 'document.querySelectorAll(".marco-g, .barra").length'],
  ["biblia/", 'document.getElementById("leitor").innerText.length > 200 ? 1 : 0'],
  ["plano-de-leitura/", 'document.querySelectorAll(".plano-card").length'],
  ["mapas/", 'document.querySelectorAll(".mapas-livro li").length'],
  ["mapa/?m=jo", 'document.querySelectorAll(".mapa-lugar").length'],
  ["mapa/", 'document.querySelectorAll(".mapa-lugar").length']
];
const TELAS = [
  { nome: "1280", w: 1280, h: 800 },
  { nome: "360", w: 360, h: 740 }
];

const dorme = (ms) => new Promise((r) => setTimeout(r, ms));

function acharChrome() {
  if (process.env.CHROME) return process.env.CHROME;
  for (const n of ["google-chrome-stable", "google-chrome", "chromium", "chromium-browser"]) {
    try {
      execFileSync("which", [n], { stdio: "ignore" });
      return n;
    } catch {}
  }
  throw new Error("Chrome não encontrado: defina CHROME=/caminho");
}

const perfil = mkdtempSync(join(tmpdir(), "mapa-verificar-"));
const servidor = spawn("python3", ["-m", "http.server", String(PORTA_SITE), "--bind", "127.0.0.1"], { cwd: RAIZ, stdio: "ignore" });
const chrome = spawn(
  acharChrome(),
  ["--headless=new", "--disable-gpu", "--no-sandbox", `--remote-debugging-port=${PORTA_CDP}`, `--user-data-dir=${perfil}`, "about:blank"],
  { stdio: "ignore" }
);
const limpar = () => {
  servidor.kill();
  chrome.kill();
  try {
    rmSync(perfil, { recursive: true, force: true });
  } catch {}
};

async function conectar() {
  for (let i = 0; i < 40; i++) {
    try {
      const lista = await (await fetch(`http://127.0.0.1:${PORTA_CDP}/json`)).json();
      const aba = lista.find((t) => t.type === "page");
      if (aba) return aba.webSocketDebuggerUrl;
    } catch {}
    await dorme(250);
  }
  throw new Error("não consegui falar com o Chrome");
}

let falhas = 0;
try {
  const ws = new WebSocket(await conectar());
  await new Promise((r) => (ws.onopen = r));
  let id = 0;
  const espera = {};
  let erros = [];
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.id && espera[m.id]) {
      espera[m.id](m.result || {});
      delete espera[m.id];
    } else if (m.method === "Runtime.exceptionThrown") {
      erros.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
    } else if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") {
      erros.push(m.params.args.map((a) => a.value || a.description).join(" "));
    }
  };
  const enviar = (method, params = {}) =>
    new Promise((r) => {
      espera[++id] = r;
      ws.send(JSON.stringify({ id, method, params }));
    });
  await enviar("Runtime.enable");
  await enviar("Page.enable");

  console.log("página".padEnd(34), "tela".padEnd(5), "itens".padEnd(6), "rolagem-lateral".padEnd(16), "erros");
  for (const t of TELAS) {
    await enviar("Emulation.setDeviceMetricsOverride", { width: t.w, height: t.h, deviceScaleFactor: 1, mobile: t.w < 700 });
    for (const [caminho, expr] of PAGINAS) {
      erros = [];
      await enviar("Page.navigate", { url: `http://127.0.0.1:${PORTA_SITE}/${caminho}` });
      await dorme(2500);
      const r = await enviar("Runtime.evaluate", {
        expression: `JSON.stringify({ n: ${expr}, doc: document.documentElement.scrollWidth, vp: innerWidth })`,
        returnByValue: true
      });
      const v = JSON.parse(r.result?.value || "{}");
      // erros de rede de CDN/Supabase (offline) não são do site
      const meus = erros.filter((e) => !/Failed to load resource|ERR_|supabase|fonts\.g/i.test(e));
      const lateral = v.doc > v.vp;
      const ok = v.n > 0 && !lateral && !meus.length;
      if (!ok) falhas++;
      console.log(
        (ok ? "ok  " : "FALHA ") + caminho.padEnd(28),
        t.nome.padEnd(5),
        String(v.n).padEnd(6),
        (lateral ? `sim (${v.doc}>${v.vp})` : "não").padEnd(16),
        meus.length ? meus.join(" | ").slice(0, 160) : "-"
      );
    }
  }
} finally {
  limpar();
}
console.log(falhas ? `\n${falhas} falha(s)` : "\ntudo certo");
process.exit(falhas ? 1 : 0);
