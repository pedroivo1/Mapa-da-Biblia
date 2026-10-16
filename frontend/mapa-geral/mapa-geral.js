// Mapa geral (mapa-geral/index.html): o mundo ano a ano, de 2500 a.C. a 2025 d.C., com linha do tempo.
// Dados (formato 2, gerados por scripts/mapa-geral/construir.py):
//   /mapa/mundo.json (costa), dados/indice.json ({versao: 2, de, ate, bloco, estados: {id: {nome, nome_video, cor,
//   desde, ate, nota, nomes?: [[de, ate, nome], ...]}}, fonte}) e dados/blocos/<a|d><ano>.json ({anos: [de, ate],
//   formas: [{id, de, ate, aneis, r}]}), um por bloco de 25 anos, carregados sob demanda (até 20 blocos em memória).
//   "r" = [lon, lat] onde o nome é escrito (ponto interno da forma).
//   Anéis em centésimos de grau, primeiro ponto absoluto e os seguintes como deltas: [x0, y0, dx1, dy1, ...].
// Anos: a.C. positivo, d.C. negativo, sem ano 0; posição i = 0…4524 (2500 a.C. -> 2025 d.C.). ?ano=-30 abre em
// 30 d.C. e a URL acompanha o ano. Projeção: compartilhado/js/projecao.js (Equal Earth).
// O cartão do estado mostra também o nome original e o link da Wikipédia, se o índice trouxer os campos
//   opcionais nome_original e wiki. (Os dados do Cliopatria, no mesmo formato, ficam fora do site, em
//   scripts/mapa-geral/dados-cliopatria/.)
(function () {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";
  var P = Projecao.criar(3600, 80, -58);
  var L = P.largura;
  var A = P.altura;
  var MAX_BLOCOS = 20;
  var DADOS = "/mapa-geral/dados/";
  var ANO0 = 2500; // ano (a.C.) da posição 0; vem do "de" do índice

  var contSvg = document.getElementById("geral-svg");
  var cartao = document.getElementById("geral-cartao");
  var slider = document.getElementById("geral-ano");
  var rotulo = document.getElementById("geral-rotulo");
  var nota = document.getElementById("geral-nota");
  var botaoPlay = document.getElementById("geral-play");
  var seletorVel = document.getElementById("geral-vel");
  var campoAno = document.getElementById("geral-ir");

  var svgEl = null;
  var gEstados = null;
  var gNomes = null;
var gRios = null;
  var vb = { x: 0, y: 0, w: L, h: A };
  var meta = {}; // id -> {nome, nome_video, cor, desde, ate, nota, nomes}
  var BLOCO = 25;
  var N = 0; // quantidade de anos
  var blocos = {}; // índice do bloco -> {formas, uso}
  var pendentes = {}; // índice do bloco -> Promise
  var uso = 0;
  var atual = 0;
  var reproduzindo = null;
  var ativo = null;
  var desenhados = {}; // id -> {path, forma, g, texto, rot}
  var urlTimer = null;

  function el(nome, attrs, pai) {
    var e = document.createElementNS(NS, nome);
    for (var k in attrs) if (Object.prototype.hasOwnProperty.call(attrs, k)) e.setAttribute(k, attrs[k]);
    if (pai) pai.appendChild(e);
    return e;
  }

  function esc(t) {
    return String(t).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  /* ---------- anos e blocos ---------- */

  function anoDePos(i) {
    return i < ANO0 ? ANO0 - i : -(i - (ANO0 - 1));
  }

  function posDeAno(a) {
    return a > 0 ? ANO0 - a : ANO0 - 1 - a;
  }

  function rotuloAno(a) {
    return a > 0 ? a + " a.C." : (-a) + " d.C.";
  }

  function nomeArquivo(a) {
    return a > 0 ? "a" + a : "d" + (-a);
  }

  function arquivoBloco(b) {
    return DADOS + "blocos/" + nomeArquivo(anoDePos(b * BLOCO)) + ".json";
  }

  // "586 a.C.", "586", "-586", "30 d.C." -> ano (a.C. positivo, d.C. negativo); null se não for um ano válido
  function lerAno(texto) {
    var m = /^\s*(-?\d+)\s*(a\.?\s*c\.?|d\.?\s*c\.?)?\s*$/i.exec(texto || "");
    if (!m) return null;
    var n = parseInt(m[1], 10);
    if (!n) return null;
    if (m[2] && /^d/i.test(m[2])) n = -Math.abs(n);
    else if (m[2]) n = Math.abs(n);
    return n;
  }

  function limitar(v, a, b) {
    return Math.max(a, Math.min(b, v));
  }

  function carregarBloco(b) {
    if (blocos[b]) {
      blocos[b].uso = ++uso;
      return Promise.resolve(blocos[b].formas);
    }
    if (pendentes[b]) return pendentes[b];
    pendentes[b] = fetch(arquivoBloco(b)).then(function (r) {
      if (!r.ok) throw new Error("http " + r.status);
      return r.json();
    }).then(function (d) {
      delete pendentes[b];
      blocos[b] = { formas: d.formas || [], uso: ++uso };
      podarBlocos();
      return blocos[b].formas;
    }, function (e) {
      delete pendentes[b];
      throw e;
    });
    return pendentes[b];
  }

  function podarBlocos() {
    var chaves = Object.keys(blocos);
    if (chaves.length <= MAX_BLOCOS) return;
    chaves.sort(function (a, b) { return blocos[a].uso - blocos[b].uso; });
    for (var i = 0; i < chaves.length - MAX_BLOCOS; i++) delete blocos[chaves[i]];
  }

  /* ---------- geometria ---------- */

  function decodificar(anel) {
    var pts = [];
    var x = anel[0], y = anel[1];
    pts.push([x / 100, y / 100]);
    for (var i = 2; i < anel.length; i += 2) {
      x += anel[i];
      y += anel[i + 1];
      pts.push([x / 100, y / 100]);
    }
    return pts;
  }

  // caminho SVG, posição do nome e tamanho (calculados uma vez por forma e guardados nela)
  function preparar(f) {
    if (f._d) return;
    var d = "";
    var maior = null, maiorN = 0;
    var area = 0;
    for (var i = 0; i < f.aneis.length; i++) {
      var r = decodificar(f.aneis[i]);
      var xs = 0, ys = 0, mn = 1e9, mx = -1e9, yn = 1e9, yx = -1e9;
      for (var j = 0; j < r.length; j++) {
        var q = P.proj(r[j][0], r[j][1]);
        d += (j === 0 ? "M" : "L") + q[0].toFixed(1) + "," + q[1].toFixed(1);
        xs += q[0]; ys += q[1];
        if (q[0] < mn) mn = q[0];
        if (q[0] > mx) mx = q[0];
        if (q[1] < yn) yn = q[1];
        if (q[1] > yx) yx = q[1];
      }
      d += "Z";
      var a = (mx - mn) * (yx - yn);
      area += a;
      if (r.length > maiorN) {
        maiorN = r.length;
        maior = { x: xs / r.length, y: ys / r.length, larg: mx - mn };
      }
    }
    f._d = d;
    if (f.r) { var qr = P.proj(f.r[0], f.r[1]); maior = { x: qr[0], y: qr[1], larg: maior ? maior.larg : 0 }; }
    f._rot = maior;
    f._area = area;
  }

  /* ---------- janela (zoom e arrastar) ---------- */

  function razao() {
    var r = svgEl.getBoundingClientRect();
    return r.height / (r.width || 1);
  }

  function aplicar() {
    vb.w = limitar(vb.w, L / 160, L);
    vb.h = vb.w * razao();
    vb.x = limitar(vb.x, -vb.w * 0.3, L - vb.w * 0.7);
    vb.y = limitar(vb.y, -vb.h * 0.3, A - vb.h * 0.7);
    svgEl.setAttribute("viewBox", vb.x + " " + vb.y + " " + vb.w + " " + vb.h);
    ajustarRios();
    ajustarNomes();
  }

  // rios: somem quando o mapa está muito longe (vb.w perto de L) e engrossam de 1 px até 2 px ao chegar bem perto
  function ajustarRios() {
    if (!gRios) return;
    var w = vb.w;
    var sumir = limitar((L * 0.65 - w) / (L * 0.2), 0, 1); // 1 até 45% da largura, 0 a partir de 65%
    var t = limitar((Math.log(900) - Math.log(w)) / (Math.log(900) - Math.log(150)), 0, 1); // 0 na vista inicial, 1 bem perto
    gRios.style.display = sumir > 0 ? "" : "none";
    gRios.style.opacity = String(sumir);
    gRios.style.setProperty("--rio-largura", (1 + t).toFixed(2) + "px");
  }

  function vistaInicial() {
    var a = P.proj(-12, 50);
    var b = P.proj(75, 8);
    vb.x = a[0];
    vb.y = a[1];
    vb.w = b[0] - a[0];
    aplicar();
  }

  function zoomEm(f, cx, cy) {
    var nw = limitar(vb.w * f, L / 160, L);
    var r = nw / vb.w;
    vb.x = cx - (cx - vb.x) * r;
    vb.y = cy - (cy - vb.y) * r;
    vb.w = nw;
    aplicar();
  }

  function ligarGestos() {
    var dedos = {};
    var arrasto = null;
    var pinca = null;
    var alvoInicial = null;

    function ponto(ev) {
      var r = svgEl.getBoundingClientRect();
      var k = vb.w / r.width;
      return [vb.x + (ev.clientX - r.left) * k, vb.y + (ev.clientY - r.top) * k];
    }
    function n() { return Object.keys(dedos).length; }

    svgEl.addEventListener("pointerdown", function (ev) {
      dedos[ev.pointerId] = { x: ev.clientX, y: ev.clientY };
      if (n() === 2) {
        var ids = Object.keys(dedos);
        var a = dedos[ids[0]], b = dedos[ids[1]];
        var m = ponto({ clientX: (a.x + b.x) / 2, clientY: (a.y + b.y) / 2 });
        pinca = { d0: Math.max(1, Math.hypot(a.x - b.x, a.y - b.y)), w0: vb.w, mx: m[0], my: m[1] };
        arrasto = null;
        return;
      }
      alvoInicial = ev.target;
      arrasto = { x: ev.clientX, y: ev.clientY, vx: vb.x, vy: vb.y, mexeu: false };
      svgEl.classList.add("arrastando");
    });

    svgEl.addEventListener("pointermove", function (ev) {
      if (!dedos[ev.pointerId]) return;
      dedos[ev.pointerId] = { x: ev.clientX, y: ev.clientY };
      if (pinca && n() >= 2) {
        var ids = Object.keys(dedos);
        var a = dedos[ids[0]], b = dedos[ids[1]];
        var d = Math.max(1, Math.hypot(a.x - b.x, a.y - b.y));
        var r = svgEl.getBoundingClientRect();
        vb.w = limitar(pinca.w0 * (pinca.d0 / d), L / 160, L);
        var k = vb.w / r.width;
        vb.x = pinca.mx - ((a.x + b.x) / 2 - r.left) * k;
        vb.y = pinca.my - ((a.y + b.y) / 2 - r.top) * k;
        aplicar();
        return;
      }
      if (!arrasto) return;
      var kk = vb.w / svgEl.getBoundingClientRect().width;
      if (Math.abs(ev.clientX - arrasto.x) + Math.abs(ev.clientY - arrasto.y) > 6) arrasto.mexeu = true;
      vb.x = arrasto.vx - (ev.clientX - arrasto.x) * kk;
      vb.y = arrasto.vy - (ev.clientY - arrasto.y) * kk;
      aplicar();
    });

    function soltar(ev) {
      var a = arrasto;
      delete dedos[ev.pointerId];
      if (pinca) {
        if (n() < 2) pinca = null;
        return;
      }
      arrasto = null;
      svgEl.classList.remove("arrastando");
      if (ev.type === "pointerup" && a && !a.mexeu) {
        var id = alvoInicial && alvoInicial.getAttribute ? alvoInicial.getAttribute("data-id") : null;
        mostrar(id);
      }
    }
    svgEl.addEventListener("pointerup", soltar);
    svgEl.addEventListener("pointercancel", soltar);
    svgEl.addEventListener("wheel", function (ev) {
      ev.preventDefault();
      var p = ponto(ev);
      zoomEm(ev.deltaY < 0 ? 0.8 : 1.25, p[0], p[1]);
    }, { passive: false });
    window.addEventListener("resize", aplicar);
  }

  /* ---------- estados ---------- */

  // nome publicado do estado no ano (trocas de nome aprovadas ficam em "nomes")
  function nomeNoAno(id, ano) {
    var m = meta[id];
    if (!m) return id;
    var p = posDeAno(ano);
    var lista = m.nomes || [];
    for (var i = 0; i < lista.length; i++) {
      if (posDeAno(lista[i][0]) <= p && p <= posDeAno(lista[i][1])) return lista[i][2];
    }
    return m.nome || "";
  }

  function mostrar(id) {
    var antes = gEstados.querySelectorAll(".ativo");
    for (var i = 0; i < antes.length; i++) antes[i].setAttribute("class", "geral-estado");
    ativo = id && meta[id] ? id : null;
    if (!ativo) {
      cartao.hidden = true;
      return;
    }
    var todos = gEstados.querySelectorAll('[data-id="' + ativo + '"]');
    for (var j = 0; j < todos.length; j++) todos[j].setAttribute("class", "geral-estado ativo");
    var m = meta[ativo];
    var periodo = m.desde != null ? rotuloAno(m.desde) + " – " + rotuloAno(m.ate) : "";
    var nome = nomeNoAno(ativo, anoDePos(atual));
    cartao.innerHTML =
      '<button type="button" class="geral-cartao-fechar" aria-label="Fechar">×</button>' +
      "<h2>" + esc(nome || "Estado sem nome lido") + "</h2>" +
      (m.nome_original && m.nome_original !== nome ? '<p class="hud faint">' + esc(m.nome_original) + "</p>" : "") +
      (periodo ? '<p class="hud faint">' + esc(periodo) + "</p>" : "") +
      (m.nota ? "<p>" + esc(m.nota) + "</p>" : "") +
      (m.wiki ? '<p><a href="https://en.wikipedia.org/wiki/' + encodeURI(m.wiki.replace(/ /g, "_")) +
        '" target="_blank" rel="noopener">Wikipédia (em inglês)</a></p>' : "");
    cartao.hidden = false;
  }

  function ajustarNomes() {
    if (!svgEl) return;
    var r = svgEl.getBoundingClientRect();
    var k = vb.w / (r.width || 1);
    for (var id in desenhados) {
      if (!Object.prototype.hasOwnProperty.call(desenhados, id)) continue;
      var t = desenhados[id];
      if (!t.g) continue;
      var rot = t.forma._rot;
      var larguraTela = rot.larg / k;
      var cabe = larguraTela > 30 + t.chars * 5.2;
      t.g.style.display = cabe ? "" : "none";
      if (cabe) t.g.setAttribute("transform", "translate(" + rot.x.toFixed(1) + "," + rot.y.toFixed(1) + ") scale(" + k.toFixed(4) + ")");
    }
  }

  function porNome(t, nome) {
    if (!nome) {
      if (t.g) { gNomes.removeChild(t.g); t.g = null; }
      return;
    }
    if (!t.g) {
      t.g = el("g", {}, gNomes);
      t.texto = el("text", { "class": "geral-nome" }, t.g);
    }
    if (t.texto.textContent !== nome) t.texto.textContent = nome;
    t.chars = nome.length;
  }

  // só o que mudou: formas que começam ou terminam no ano; <path> com o mesmo id e a mesma geometria fica como está
  function desenharAno(formas, i) {
    var ano = anoDePos(i);
    var vistos = {};
    var novos = false;
    for (var n = 0; n < formas.length; n++) {
      var f = formas[n];
      if (!(posDeAno(f.de) <= i && i <= posDeAno(f.ate))) continue;
      vistos[f.id] = true;
      var m = meta[f.id] || { nome: f.id, cor: "#888888" };
      var t = desenhados[f.id];
      preparar(f);
      if (!t) {
        var p = el("path", { "class": "geral-estado" + (f.id === ativo ? " ativo" : ""), d: f._d, fill: m.cor, stroke: m.cor,
          "fill-rule": "evenodd", "data-id": f.id }, gEstados);
        t = desenhados[f.id] = { path: p, forma: f, g: null, texto: null, chars: 0 };
        novos = true;
      } else if (t.forma !== f) {
        t.path.setAttribute("d", f._d);
        if (t.forma._area !== f._area) novos = true;
        t.forma = f;
      }
      porNome(t, nomeNoAno(f.id, ano));
    }
    for (var id in desenhados) {
      if (Object.prototype.hasOwnProperty.call(desenhados, id) && !vistos[id]) {
        var d = desenhados[id];
        gEstados.removeChild(d.path);
        if (d.g) gNomes.removeChild(d.g);
        delete desenhados[id];
      }
    }
    if (novos) {
      // maiores por baixo, para os pequenos continuarem clicáveis
      var lista = [];
      for (var k in desenhados) if (Object.prototype.hasOwnProperty.call(desenhados, k)) lista.push(desenhados[k]);
      lista.sort(function (a, b) { return b.forma._area - a.forma._area; });
      for (var q = 0; q < lista.length; q++) gEstados.appendChild(lista[q].path);
    }
    ajustarNomes();
    if (ativo && !vistos[ativo]) mostrar(null);
    else if (ativo && !cartao.hidden) {
      var h2 = cartao.querySelector("h2");
      var nomeAtivo = nomeNoAno(ativo, ano) || "Estado sem nome lido";
      if (h2 && h2.textContent !== nomeAtivo) h2.textContent = nomeAtivo;
    }
  }

  function atualizarUrl(a) {
    if (urlTimer) clearTimeout(urlTimer);
    urlTimer = setTimeout(function () {
      urlTimer = null;
      try {
        if (history.replaceState) history.replaceState(null, "", "?ano=" + a);
      } catch (e) {}
    }, 300);
  }

  function irPara(i) {
    atual = limitar(i, 0, N - 1);
    slider.value = String(atual);
    var a = anoDePos(atual);
    rotulo.textContent = rotuloAno(a);
    rotulo.setAttribute("data-ano", String(a));
    atualizarUrl(a);
    var b = Math.floor(atual / BLOCO);
    carregarBloco(b).then(function (formas) {
      if (Math.floor(atual / BLOCO) !== b) return;
      desenharAno(formas, atual);
    }).catch(function () {
      nota.textContent = "Não foi possível carregar os dados de " + rotuloAno(a) + ".";
    });
    // pré-carrega o bloco seguinte (e o anterior, perto da borda)
    if ((b + 1) * BLOCO < N) carregarBloco(b + 1).catch(function () {});
    if (b > 0 && atual % BLOCO < 3) carregarBloco(b - 1).catch(function () {});
  }

  /* ---------- reprodução e controles ---------- */

  function velocidade() {
    var v = parseInt(seletorVel && seletorVel.value, 10);
    return v > 0 ? v : 10;
  }

  function parar() {
    if (reproduzindo) clearInterval(reproduzindo);
    reproduzindo = null;
    botaoPlay.innerHTML = "&#9654;";
    botaoPlay.setAttribute("aria-label", "Reproduzir");
  }

  function tocar() {
    if (reproduzindo) clearInterval(reproduzindo);
    botaoPlay.innerHTML = "&#10073;&#10073;";
    botaoPlay.setAttribute("aria-label", "Pausar");
    reproduzindo = setInterval(function () {
      if (atual >= N - 1) return parar();
      irPara(atual + 1);
    }, 1000 / velocidade());
  }

  function alternarPlay() {
    if (reproduzindo) return parar();
    if (atual >= N - 1) irPara(0);
    tocar();
  }

  function ligarControles() {
    slider.addEventListener("input", function () { parar(); irPara(parseInt(slider.value, 10)); });
    document.getElementById("geral-ant").addEventListener("click", function () { parar(); irPara(atual - 1); });
    document.getElementById("geral-prox").addEventListener("click", function () { parar(); irPara(atual + 1); });
    botaoPlay.addEventListener("click", alternarPlay);
    if (seletorVel) seletorVel.addEventListener("change", function () { if (reproduzindo) tocar(); });
    if (campoAno) {
      campoAno.form.addEventListener("submit", function (ev) {
        ev.preventDefault();
        var a = lerAno(campoAno.value);
        if (a == null) { campoAno.setCustomValidity("Escreva um ano, como 586 a.C. ou 30 d.C."); campoAno.reportValidity(); return; }
        campoAno.setCustomValidity("");
        parar();
        irPara(posDeAno(a));
        campoAno.value = "";
        campoAno.blur();
      });
      campoAno.addEventListener("input", function () { campoAno.setCustomValidity(""); });
    }
    cartao.addEventListener("click", function (ev) {
      if (ev.target.closest && ev.target.closest(".geral-cartao-fechar")) mostrar(null);
    });
    document.addEventListener("keydown", function (ev) {
      if (/INPUT|TEXTAREA|SELECT/.test((ev.target.tagName || ""))) return;
      var passo = ev.shiftKey ? 10 : 1;
      if (ev.key === "ArrowLeft") { ev.preventDefault(); parar(); irPara(atual - passo); }
      else if (ev.key === "ArrowRight") { ev.preventDefault(); parar(); irPara(atual + passo); }
      else if (ev.key === " ") { ev.preventDefault(); alternarPlay(); }
      else if (ev.key === "Escape") mostrar(null);
    });
  }

  /* ---------- início ---------- */

  function base(mundo) {
    svgEl = el("svg", { "class": "geral-svg-el", viewBox: "0 0 " + L + " " + A, role: "img",
      "aria-label": "Mapa-múndi com os povos e impérios de cada ano" });
    var g = el("g", {}, svgEl);
    mundo.fundo.forEach(function (f) {
      if (f.tipo === "terra") {
        var d = f.aneis.map(function (a) {
          return "M" + a.map(function (p) { var q = P.proj(p[0], p[1]); return q[0].toFixed(1) + "," + q[1].toFixed(1); }).join("L") + "Z";
        }).join("");
        el("path", { "class": "geral-terra", d: d }, g);
      } else if (f.tipo === "mar") {
        var pts = f.pontos.map(function (p) { var q = P.proj(p[0], p[1]); return q[0].toFixed(1) + "," + q[1].toFixed(1); }).join(" ");
        el("polygon", { "class": "geral-agua", points: pts }, g);
      }
    });
    gEstados = el("g", {}, svgEl);
    // rios (mundo.json, tipo "rio"): por cima dos estados, sem pegar o clique
    gRios = el("g", { "class": "geral-rios" }, svgEl);
    mundo.fundo.forEach(function (f) {
      if (f.tipo !== "rio") return;
      var pts = f.pontos.map(function (p) { var q = P.proj(p[0], p[1]); return q[0].toFixed(1) + "," + q[1].toFixed(1); }).join(" ");
      el("polyline", { "class": "geral-rio", points: pts, fill: "none" }, gRios);
    });
    gNomes = el("g", {}, svgEl);
    contSvg.textContent = "";
    contSvg.appendChild(svgEl);
    ligarGestos();
    vistaInicial();
  }

  function falha(msg) {
    contSvg.innerHTML = '<p class="vazio hud faint">' + esc(msg) + "</p>";
  }

  Promise.all([
    fetch("/mapa/mundo.json").then(function (r) { return r.json(); }),
    fetch(DADOS + "indice.json").then(function (r) { return r.json(); })
  ]).then(function (r) {
    var ind = r[1];
    if (ind.versao !== 2 || ind.de == null || ind.ate == null) return falha("Ainda não há dados no mapa geral.");
    meta = ind.estados || {};
    ANO0 = ind.de;
    BLOCO = ind.bloco || 25;
    N = posDeAno(ind.ate) - posDeAno(ind.de) + 1;
    nota.textContent = ind.fonte || "";
    base(r[0]);
    slider.max = String(N - 1);
    ligarControles();
    // abre no ano pedido (?ano=-30 = 30 d.C.) ou em 1010 a.C.
    var ini = posDeAno(1010);
    var pedido = /[?&]ano=(-?\d+)/.exec(location.search);
    if (pedido) {
      var alvo = parseInt(pedido[1], 10);
      if (alvo) ini = posDeAno(alvo);
    }
    irPara(ini);
  }).catch(function () {
    falha("Não foi possível carregar o mapa geral. Abra por um servidor local (python -m http.server).");
  });
})();
