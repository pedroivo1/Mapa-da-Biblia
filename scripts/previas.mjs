// Gera as prévias (WebP, tema claro e escuro) dos mapas: frontend/mapas/previas/<id>-<claro|escuro>.webp, uma por mapa
// de mapas/mapas.json, e frontend/inicio/previa-<linha|geral>-<claro|escuro>.webp (a linha do tempo; o mapa geral num ano). Usadas na página
// inicial e na lista de Mapas. Rode de novo quando um mapa, os territórios ou as cores mudarem.
//
//   node scripts/previas.mjs [id ... | geral | linha]      (Node 22+, Chrome ou Chromium e ImageMagick (magick); sem dependências npm)
//   CHROME=/caminho/do/chrome node scripts/previas.mjs
import { spawn, execFileSync } from "node:child_process";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const FRONT = join(dirname(fileURLToPath(import.meta.url)), "..", "frontend");
const PORTA_SITE = 8766;
const PORTA_CDP = 9766;
const ANO_GERAL = 586; // ano do mapa geral mostrado na página inicial (586 a.C., a época de Daniel)
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

const lista = JSON.parse(readFileSync(join(FRONT, "mapas", "mapas.json"), "utf8")).mapas.map((m) => {
  const q = /[?&]m=([a-z0-9-]+)/.exec(m.url);
  return q ? q[1] : "abraao";
});
const pedidos = process.argv.slice(2);
const soGeral = pedidos.includes("geral"); // só a prévia do mapa geral
const soLinha = pedidos.includes("linha"); // só a prévia da linha do tempo (a da página inicial)
const ids = soGeral || soLinha ? [] : pedidos.length ? lista.filter((i) => pedidos.includes(i)) : lista;

const perfil = mkdtempSync(join(tmpdir(), "mapa-previas-"));
mkdirSync(join(FRONT, "mapas", "previas"), { recursive: true });
const servidor = spawn("python3", ["-m", "http.server", String(PORTA_SITE), "--bind", "127.0.0.1"], { cwd: FRONT, stdio: "ignore" });
const chrome = spawn(
  acharChrome(),
  ["--headless=new", "--disable-gpu", "--no-sandbox", `--remote-debugging-port=${PORTA_CDP}`, `--user-data-dir=${perfil}`, "about:blank"],
  { stdio: "ignore" }
);
const limpar = () => {
  servidor.kill();
  chrome.kill();
  try { rmSync(perfil, { recursive: true, force: true }); } catch {}
};

async function conectar() {
  for (let i = 0; i < 40; i++) {
    try {
      const l = await (await fetch(`http://127.0.0.1:${PORTA_CDP}/json`)).json();
      const aba = l.find((t) => t.type === "page");
      if (aba) return aba.webSocketDebuggerUrl;
    } catch {}
    await dorme(250);
  }
  throw new Error("não consegui falar com o Chrome");
}

try {
  const ws = new WebSocket(await conectar());
  await new Promise((r) => (ws.onopen = r));
  let id = 0;
  const espera = {};
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.id && espera[m.id]) { espera[m.id](m.result || {}); delete espera[m.id]; }
  };
  const enviar = (method, params = {}) => new Promise((r) => { espera[++id] = r; ws.send(JSON.stringify({ id, method, params })); });
  const avaliar = async (expressao) => (await enviar("Runtime.evaluate", { expression: expressao, returnByValue: true })).result?.value;
  await enviar("Page.enable");
  await enviar("Emulation.setDeviceMetricsOverride", { width: 720, height: 460, deviceScaleFactor: 2, mobile: false });

  // abre a página no tema pedido, esconde o que não é mapa e fotografa o elemento do mapa
  async function fotografar(url, tema, seletor, esconder, saida, larg = 720, alt = 460, antes = "") {
    await enviar("Emulation.setDeviceMetricsOverride", { width: larg, height: alt, deviceScaleFactor: 2, mobile: false });
    await enviar("Page.navigate", { url: `http://127.0.0.1:${PORTA_SITE}/mapa/mapa.css` }); // mesma origem para gravar o tema
    await avaliar(`localStorage.setItem("notas-theme", "${tema}")`);
    await enviar("Page.navigate", { url: `http://127.0.0.1:${PORTA_SITE}${url}` });
    await dorme(3500);
    await avaliar(`(function(){var s=document.createElement("style");s.textContent=${JSON.stringify(esconder + "{display:none !important}")};document.head.appendChild(s);})()`);
    if (antes) { await avaliar(antes); await dorme(600); }
    const r = JSON.parse(await avaliar(`JSON.stringify((function(){var b=document.querySelector(${JSON.stringify(seletor)}).getBoundingClientRect();return{x:b.x,y:b.y,width:b.width,height:b.height};})())`));
    const png = (await enviar("Page.captureScreenshot", { format: "png", clip: { ...r, scale: 1 } })).data;
    const tmp = join(perfil, "p.png");
    writeFileSync(tmp, Buffer.from(png, "base64"));
    execFileSync("magick", [tmp, "-resize", "1440x", "-quality", "80", saida]);
    console.log("ok", saida.replace(FRONT, ""));
  }

  for (const tema of ["claro", "escuro"]) {
    const t = tema === "claro" ? "light" : "dark";
    for (const m of ids) {
      await fotografar(`/mapa/?m=${m}&embutido`, t, "#mapa-svg", ".mapa-barra, .mapa-legenda", join(FRONT, "mapas", "previas", `${m}-${tema}.webp`));
    }
    if (!pedidos.length || soLinha) {
      await fotografar("/linha-do-tempo/", t, "main.frame", ".nav, footer, .lt-mapa-geral", join(FRONT, "inicio", `previa-linha-${tema}.webp`), 1280, 960,
        "var r=document.querySelector('.lt-scroll');r.scrollTop=LT.Y(931)-r.clientHeight*0.4;");
    }
    if (soGeral) {
      await fotografar(`/mapa-geral/?ano=${ANO_GERAL}`, t, "#geral-svg", ".nav, .biblia-topo, .geral-controle, .geral-cartao, .geral-nota, footer", join(FRONT, "inicio", `previa-geral-${tema}.webp`), 1000, 1000);
    }
  }
} finally {
  limpar();
}
