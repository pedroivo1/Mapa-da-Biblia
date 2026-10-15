// Captura de telas (PNG) de páginas do site num Chrome sem janela, com perfil e cache novos.
//   node scripts/mapa-geral/capturar.mjs <pasta-frontend> <pasta-saida> <largura> <altura> <espera-ms> <caminho>...
// Cada caminho (ex.: "mapa/?m=jo") vira <pasta-saida>/<caminho com / ? = trocados por _>.png.
// Sobe um servidor local temporário (python3 -m http.server) numa porta livre. Ferramenta de desenvolvimento.
import { spawn, execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createServer } from "node:net";

const [pasta, saida, W, H, ESPERA, ...caminhos] = process.argv.slice(2);
const dorme = (ms) => new Promise((r) => setTimeout(r, ms));
const portaLivre = () =>
  new Promise((res) => {
    const s = createServer();
    s.listen(0, "127.0.0.1", () => {
      const p = s.address().port;
      s.close(() => res(p));
    });
  });

const PS = await portaLivre();
const PC = await portaLivre();
const perfil = mkdtempSync(join(tmpdir(), "mapa-cap-"));
mkdirSync(saida, { recursive: true });
const servidor = spawn("python3", ["-m", "http.server", String(PS), "--bind", "127.0.0.1"], { cwd: pasta, stdio: "ignore" });
let chromeBin = process.env.CHROME || "google-chrome-stable";
const chrome = spawn(
  chromeBin,
  ["--headless=new", "--disable-gpu", "--no-sandbox", `--remote-debugging-port=${PC}`, `--user-data-dir=${perfil}`, `--disk-cache-dir=${join(perfil, "cache-http")}`, "about:blank"],
  { stdio: "ignore" }
);
const limpar = () => {
  servidor.kill();
  chrome.kill();
  try { rmSync(perfil, { recursive: true, force: true }); } catch {}
};
try {
  let url;
  for (let i = 0; i < 60 && !url; i++) {
    try {
      const l = await (await fetch(`http://127.0.0.1:${PC}/json`)).json();
      const a = l.find((t) => t.type === "page");
      if (a) url = a.webSocketDebuggerUrl;
    } catch {}
    if (!url) await dorme(250);
  }
  const ws = new WebSocket(url);
  await new Promise((r) => (ws.onopen = r));
  let id = 0;
  const espera = {};
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.id && espera[m.id]) { espera[m.id](m.result || {}); delete espera[m.id]; }
  };
  const enviar = (method, params = {}) => new Promise((r) => { espera[++id] = r; ws.send(JSON.stringify({ id, method, params })); });
  await enviar("Page.enable");
  await enviar("Emulation.setDeviceMetricsOverride", { width: +W, height: +H, deviceScaleFactor: 1, mobile: +W < 700 });
  for (const c of caminhos) {
    await enviar("Page.navigate", { url: `http://127.0.0.1:${PS}/${c}` });
    await dorme(+ESPERA);
    const r = await enviar("Page.captureScreenshot", { format: "png" });
    const nome = (c || "inicio").replace(/[\/?=&]/g, "_") + ".png";
    writeFileSync(join(saida, nome), Buffer.from(r.data, "base64"));
    console.log(nome);
  }
} finally {
  limpar();
}
process.exit(0);
