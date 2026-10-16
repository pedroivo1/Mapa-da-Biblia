// Testes de interação da página do mapa geral (plano v2, E9: T9.2–T9.5). Mesma técnica de scripts/verificar.mjs:
// Chrome sem janela falando CDP, perfil e cache de disco novos, servidor local temporário servindo frontend/.
//
//   node scripts/mapa-geral/testar-pagina.mjs          (Node 22+, Chrome instalado; sem dependências)
//
// T9.2 navegação: ?ano=586 mostra "586 a.C."; → mostra "585 a.C."; ?ano=1 e → mostra "1 d.C."; ?ano=2500 e ← não
//      sai do intervalo; ?ano=-2025 é o último; 30 anos sorteados abrem com o rótulo certo e .geral-estado > 0.
// T9.3 reprodução por 5 s a 10 anos/s: avança 45–55 anos, sem erro de console, sem ano pulado no rótulo.
// T9.4 desempenho: troca de ano com bloco em cache <= 50 ms (mediana) em 1280 px; primeira abertura <= 2 s.
// T9.5 casos de referência no navegador: 10 casos (os maiores estados de casos.json) acertam com elementFromPoint.
import { spawn, execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const AQUI = dirname(fileURLToPath(import.meta.url));
const RAIZ = join(AQUI, "..", "..", "frontend");
const PORTA_SITE = 8766;
const PORTA_CDP = 9766;
const dorme = (ms) => new Promise((r) => setTimeout(r, ms));

function acharChrome() {
  if (process.env.CHROME) return process.env.CHROME;
  for (const n of ["google-chrome-stable", "google-chrome", "chromium", "chromium-browser"]) {
    try { execFileSync("which", [n], { stdio: "ignore" }); return n; } catch {}
  }
  throw new Error("Chrome não encontrado: defina CHROME=/caminho");
}

const perfil = mkdtempSync(join(tmpdir(), "mapa-geral-pagina-"));
const servidor = spawn("python3", ["-m", "http.server", String(PORTA_SITE), "--bind", "127.0.0.1"], { cwd: RAIZ, stdio: "ignore" });
const chrome = spawn(acharChrome(), ["--headless=new", "--disable-gpu", "--no-sandbox", `--remote-debugging-port=${PORTA_CDP}`,
  `--user-data-dir=${perfil}`, `--disk-cache-dir=${join(perfil, "cache-http")}`, "about:blank"], { stdio: "ignore" });
const limpar = () => { servidor.kill(); chrome.kill(); try { rmSync(perfil, { recursive: true, force: true }); } catch {} };

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
function teste(nome, cond, detalhe = "") {
  if (!cond) falhas++;
  console.log((cond ? "OK    " : "FALHA ") + nome + (detalhe !== "" ? "  " + detalhe : ""));
}

const rotuloAno = (a) => (a > 0 ? a + " a.C." : -a + " d.C.");

try {
  const ws = new WebSocket(await conectar());
  await new Promise((r) => (ws.onopen = r));
  let id = 0;
  const espera = {};
  let erros = [];
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.id && espera[m.id]) { espera[m.id](m.result || {}); delete espera[m.id]; }
    else if (m.method === "Runtime.exceptionThrown") erros.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
    else if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") erros.push(m.params.args.map((a) => a.value || a.description).join(" "));
  };
  const enviar = (method, params = {}) => new Promise((r) => { espera[++id] = r; ws.send(JSON.stringify({ id, method, params })); });
  const avaliar = async (expr) => {
    const r = await enviar("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
    return r.result ? r.result.value : undefined;
  };
  const errosDoSite = () => erros.filter((e) => !/Failed to load resource|ERR_|supabase|fonts\.g/i.test(e));
  await enviar("Runtime.enable");
  await enviar("Page.enable");
  await enviar("Emulation.setDeviceMetricsOverride", { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false });

  // abre a página e espera o primeiro desenho; devolve o tempo até ele (ms)
  async function abrir(ano) {
    erros = [];
    const t0 = Date.now();
    await enviar("Page.navigate", { url: `http://127.0.0.1:${PORTA_SITE}/mapa-geral/${ano != null ? "?ano=" + ano : ""}` });
    for (let i = 0; i < 200; i++) {
      const n = await avaliar('document.querySelectorAll(".geral-estado").length');
      if (n > 0) return Date.now() - t0;
      await dorme(50);
    }
    return Infinity;
  }
  const rotulo = () => avaliar('document.getElementById("geral-rotulo").textContent');
  const estados = () => avaliar('document.querySelectorAll(".geral-estado").length');
  async function tecla(key, shift = false) {
    const code = key === "ArrowLeft" ? 37 : 39;
    const mods = shift ? 8 : 0;
    await enviar("Input.dispatchKeyEvent", { type: "keyDown", key, code: key, windowsVirtualKeyCode: code, modifiers: mods });
    await enviar("Input.dispatchKeyEvent", { type: "keyUp", key, code: key, windowsVirtualKeyCode: code, modifiers: mods });
    await dorme(120);
  }

  // ---- T9.2
  const primeiro = await abrir(586);
  const r1 = await rotulo();
  await tecla("ArrowRight");
  const r2 = await rotulo();
  await tecla("ArrowRight", true);
  const r3 = await rotulo();
  await abrir(1);
  await tecla("ArrowRight");
  const r4 = await rotulo();
  await abrir(2500);
  await tecla("ArrowLeft");
  const r5 = await rotulo();
  await abrir(-2025);
  await tecla("ArrowRight");
  const r6 = await rotulo();
  let sorteio = 0;
  const anos = [];
  let semente = 20261015;
  const rnd = () => { semente = (semente * 1103515245 + 12345) % 2147483648; return semente / 2147483648; };
  for (let i = 0; i < 30; i++) {
    const p = Math.floor(rnd() * 4525);
    anos.push(p < 2500 ? 2500 - p : -(p - 2499));
  }
  const errados = [];
  for (const a of anos) {
    await abrir(a);
    const r = await rotulo();
    const n = await estados();
    if (r === rotuloAno(a) && n > 0) sorteio++;
    else errados.push([a, r, n]);
  }
  teste("T9.2 navegação: ?ano=586 -> 586 a.C.; -> 585 a.C.; Shift-> 575 a.C.; ?ano=1 -> 1 d.C.; 2500 a.C. não recua; " +
        "2025 d.C. não avança; 30 anos sorteados certos",
        r1 === "586 a.C." && r2 === "585 a.C." && r3 === "575 a.C." && r4 === "1 d.C." && r5 === "2500 a.C." && r6 === "2025 d.C." && sorteio === 30,
        `${r1} | ${r2} | ${r3} | ${r4} | ${r5} | ${r6} | sorteados certos ${sorteio}/30 ${JSON.stringify(errados.slice(0, 3))}`);

  // ---- T9.3 reprodução 5 s a 10 anos/s (velocidade padrão)
  await abrir(-1000);
  erros = [];
  await avaliar(`window.__seq = []; new MutationObserver(function () { window.__seq.push(document.getElementById("geral-rotulo").getAttribute("data-ano")); })
    .observe(document.getElementById("geral-rotulo"), { attributes: true, attributeFilter: ["data-ano"] }); 1`);
  await avaliar('document.getElementById("geral-play").click(); 1');
  await dorme(5000);
  await avaliar('document.getElementById("geral-play").click(); 1');
  const seq = (await avaliar("JSON.stringify(window.__seq)")) || "[]";
  const anosSeq = JSON.parse(seq).map(Number);
  let pulos = 0;
  for (let i = 1; i < anosSeq.length; i++) {
    const a = anosSeq[i - 1], b = anosSeq[i];
    const esperado = a === 1 ? -1 : a - 1;
    if (b !== esperado) pulos++;
  }
  const avanco = anosSeq.length ? Math.abs(anosSeq[anosSeq.length - 1] - anosSeq[0]) + (anosSeq[0] > 0 && anosSeq[anosSeq.length - 1] < 0 ? -1 : 0) : 0;
  teste("T9.3 reprodução 5 s a 10 anos/s: avança 45–55 anos, sem ano pulado, sem erro de console",
        avanco >= 45 && avanco <= 55 && pulos === 0 && errosDoSite().length === 0,
        `avanço ${avanco} anos (${anosSeq[0]} -> ${anosSeq[anosSeq.length - 1]}), pulos ${pulos}, erros ${errosDoSite().length}; sequência ${anosSeq.join(",")}`);

  // ---- T9.4 desempenho: troca de ano com bloco em cache (mediana de 20 trocas, medida na página)
  await abrir(-1500);
  await dorme(800); // bloco seguinte pré-carregado
  const tempos = JSON.parse(await avaliar(`(async function () {
    var svg = document.querySelector(".geral-svg svg");
    var out = [];
    for (var i = 0; i < 20; i++) {
      var t0 = performance.now();
      var fim = new Promise(function (r) {
        var mo = new MutationObserver(function () { mo.disconnect(); r(performance.now()); });
        mo.observe(svg, { childList: true, subtree: true, attributes: true });
        setTimeout(function () { mo.disconnect(); r(NaN); }, 1000);
      });
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
      var t1 = await fim;
      out.push(t1 - t0);
      await new Promise(function (r) { requestAnimationFrame(r); });
    }
    return JSON.stringify(out);
  })()`));
  const validos = tempos.filter((t) => !Number.isNaN(t)).sort((a, b) => a - b);
  const mediana = validos.length ? validos[Math.floor(validos.length / 2)] : Infinity;
  teste("T9.4 desempenho: troca de ano com bloco em cache <= 50 ms (mediana) e primeira abertura <= 2 s",
        mediana <= 50 && primeiro <= 2000,
        `mediana ${mediana.toFixed(1)} ms (${validos.length} medidas, máx ${validos.length ? validos[validos.length - 1].toFixed(1) : "-"}); primeira abertura ${primeiro} ms`);

  // ---- T9.5 casos de referência no navegador (os 10 primeiros casos com nome_video entre os estados grandes)
  const casos = JSON.parse(readFileSync(join(AQUI, "casos.json"), "utf8")).casos;
  const grandes = /^(Egypt|Babylon|Medes|Roman Empire|Parthia|Parthian Empire|Sasanian Empire|Han|Byzantine Empire|Song|Ottomans|Russia|Ming|Brazil|Canada|United States|Australia|China|India|Holy Roman Empire|Mughals|Safavids|France|Liao|Qing|Jin|Gupta|Zhou|Shang|Assyria|Kush|Mongols|Northern Yuan|New Spain|Rupert's Land|Sudan|Greenland)$/;
  const escolhidos = casos.filter((c) => c.espera === "estado" && grandes.test(c.nome_video || "")).slice(0, 10);
  const acertos = [], errosCasos = [];
  for (const c of escolhidos) {
    await abrir(c.ano);
    // afasta ao máximo para o ponto ficar na tela
    for (let i = 0; i < 40; i++) await enviar("Input.dispatchMouseEvent", { type: "mouseWheel", x: 640, y: 300, deltaX: 0, deltaY: 200 });
    await dorme(200);
    const r = await avaliar(`(function () {
      var svg = document.querySelector(".geral-svg svg");
      var P = Projecao.criar(3600, 80, -58);
      var q = P.proj(${c.lon}, ${c.lat});
      var pt = svg.createSVGPoint(); pt.x = q[0]; pt.y = q[1];
      var s = pt.matrixTransform(svg.getScreenCTM());
      var e = document.elementFromPoint(s.x, s.y);
      var id = e && e.getAttribute ? e.getAttribute("data-id") : null;
      return JSON.stringify({ id: id, x: s.x, y: s.y });
    })()`);
    const v = JSON.parse(r || "{}");
    const ind = JSON.parse(readFileSync(join(RAIZ, "mapa-geral", "dados", "indice.json"), "utf8"));
    const m = v.id ? ind.estados[v.id] : null;
    let nv = m ? m.nome_video : null;
    if (m && m.nomes) for (const t of m.nomes) { const p = (a) => (a > 0 ? 2500 - a : 2499 - a); if (p(t[0]) <= p(c.ano) && p(c.ano) <= p(t[1])) nv = t[3]; }
    const ok = nv && nv.toLowerCase().replace(/\./g, "") === c.nome_video.toLowerCase().replace(/\./g, "");
    (ok ? acertos : errosCasos).push([c.ano, c.nome_video, v.id, nv]);
  }
  teste("T9.5 casos de referência no navegador: 10 casos acertam o estado com elementFromPoint",
        escolhidos.length === 10 && errosCasos.length === 0,
        `acertos ${acertos.length}/${escolhidos.length}; erros ${JSON.stringify(errosCasos.slice(0, 5))}`);
} finally {
  limpar();
}
console.log(falhas ? `\n${falhas} falha(s)` : "\ntudo certo");
process.exit(falhas ? 1 : 0);
