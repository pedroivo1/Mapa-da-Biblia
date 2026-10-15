// Mapa geral (mapa-geral/index.html): povos e impérios do mundo, ano a ano, com linha do tempo.
// Dados: /mapa/mundo.json (costa), dados/indice.json (anos e metadados dos estados) e dados/<ano>.json
// (contornos do ano, carregados sob demanda). Projeção: compartilhado/js/projecao.js (Equal Earth).
// Arquivos de ano: a<N>.json para N a.C. e d<N>.json para N d.C.
(function () {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";
  var P = Projecao.criar(3600, 80, -58);
  var L = P.largura;
  var A = P.altura;

  var contSvg = document.getElementById("geral-svg");
  var cartao = document.getElementById("geral-cartao");
  var slider = document.getElementById("geral-ano");
  var rotulo = document.getElementById("geral-rotulo");
  var nota = document.getElementById("geral-nota");

  var svgEl = null;
  var gEstados = null;
  var gNomes = null;
  var vb = { x: 0, y: 0, w: L, h: A };
  var anos = [];
  var meta = {}; // id -> {nome, cor, desde, ate, nota}
  var cache = {}; // ano -> estados
  var atual = 0;
  var reproduzindo = null;
  var ativo = null;

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

  function rotuloAno(a) {
    return a > 0 ? a + " a.C." : (-a) + " d.C.";
  }

  function arquivoAno(a) {
    return "/mapa-geral/dados/" + (a > 0 ? "a" + a : "d" + (-a)) + ".json";
  }

  function caminho(aneis) {
    var d = "";
    for (var i = 0; i < aneis.length; i++) {
      var r = aneis[i];
      for (var j = 0; j < r.length; j++) {
        var q = P.proj(r[j][0], r[j][1]);
        d += (j === 0 ? "M" : "L") + q[0].toFixed(1) + "," + q[1].toFixed(1);
      }
      d += "Z";
    }
    return d;
  }

  /* ---------- janela (zoom e arrastar) ---------- */

  function razao() {
    var r = svgEl.getBoundingClientRect();
    return r.height / (r.width || 1);
  }

  function limitar(v, a, b) {
    return Math.max(a, Math.min(b, v));
  }

  function aplicar() {
    vb.w = limitar(vb.w, L / 160, L);
    vb.h = vb.w * razao();
    vb.x = limitar(vb.x, -vb.w * 0.3, L - vb.w * 0.7);
    vb.y = limitar(vb.y, -vb.h * 0.3, A - vb.h * 0.7);
    svgEl.setAttribute("viewBox", vb.x + " " + vb.y + " " + vb.w + " " + vb.h);
    ajustarNomes();
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
    cartao.innerHTML =
      '<button type="button" class="geral-cartao-fechar" aria-label="Fechar">×</button>' +
      "<h2>" + esc(m.nome || "Estado sem nome identificado") + "</h2>" +
      (periodo ? '<p class="hud faint">' + esc(periodo) + "</p>" : "") +
      (m.nota ? "<p>" + esc(m.nota) + "</p>" : "");
    cartao.hidden = false;
  }

  var rotulos = []; // {el, x, y, larg}: nome, posição no SVG e largura do estado em unidades do SVG

  function ajustarNomes() {
    if (!svgEl) return;
    var r = svgEl.getBoundingClientRect();
    var k = vb.w / (r.width || 1);
    for (var i = 0; i < rotulos.length; i++) {
      var t = rotulos[i];
      var larguraTela = t.larg / k;
      var cabe = larguraTela > 30 + t.chars * 5.2;
      t.el.style.display = cabe ? "" : "none";
      if (cabe) t.el.setAttribute("transform", "translate(" + t.x.toFixed(1) + "," + t.y.toFixed(1) + ") scale(" + k.toFixed(4) + ")");
    }
  }

  function desenharAno(estados) {
    gEstados.textContent = "";
    gNomes.textContent = "";
    rotulos = [];
    estados.sort(function (a, b) { return (b.area || 0) - (a.area || 0); });
    estados.forEach(function (e) {
      var m = meta[e.id] || { nome: e.id, cor: "#888888" };
      var p = el("path", {
        "class": "geral-estado" + (e.id === ativo ? " ativo" : ""),
        d: caminho(e.aneis), fill: m.cor, stroke: m.cor, "fill-rule": "evenodd", "data-id": e.id
      }, gEstados);
      p.setAttribute("data-id", e.id);
      // nome no centro do maior anel
      var maior = e.aneis[0];
      for (var i = 1; i < e.aneis.length; i++) if (e.aneis[i].length > maior.length) maior = e.aneis[i];
      var xs = 0, ys = 0, mn = 1e9, mx = -1e9;
      for (var j = 0; j < maior.length; j++) {
        var q = P.proj(maior[j][0], maior[j][1]);
        xs += q[0]; ys += q[1];
        if (q[0] < mn) mn = q[0];
        if (q[0] > mx) mx = q[0];
      }
      if (!m.nome) return;
      var g = el("g", {}, gNomes);
      var t = el("text", { "class": "geral-nome" }, g);
      t.textContent = m.nome;
      rotulos.push({ el: g, x: xs / maior.length, y: ys / maior.length, larg: mx - mn, chars: m.nome.length });
    });
    ajustarNomes();
  }

  function carregarAno(a) {
    if (cache[a]) return Promise.resolve(cache[a]);
    return fetch(arquivoAno(a)).then(function (r) {
      if (!r.ok) throw new Error("http " + r.status);
      return r.json();
    }).then(function (d) {
      cache[a] = d.estados || [];
      return cache[a];
    });
  }

  function irPara(i) {
    atual = limitar(i, 0, anos.length - 1);
    slider.value = String(atual);
    var a = anos[atual];
    rotulo.textContent = rotuloAno(a);
    carregarAno(a).then(function (est) {
      if (anos[atual] !== a) return;
      desenharAno(est.slice());
      if (ativo && !gEstados.querySelector('[data-id="' + ativo + '"]')) mostrar(null);
    }).catch(function () {
      nota.textContent = "Não foi possível carregar os dados de " + rotuloAno(a) + ".";
    });
    if (anos[atual + 1] != null) carregarAno(anos[atual + 1]).catch(function () {});
  }

  function parar() {
    if (reproduzindo) clearInterval(reproduzindo);
    reproduzindo = null;
    document.getElementById("geral-play").innerHTML = "&#9654;";
  }

  function alternarPlay() {
    if (reproduzindo) return parar();
    if (atual >= anos.length - 1) irPara(0);
    document.getElementById("geral-play").innerHTML = "&#10073;&#10073;";
    reproduzindo = setInterval(function () {
      if (atual >= anos.length - 1) return parar();
      irPara(atual + 1);
    }, 700);
  }

  function ligarControles() {
    slider.addEventListener("input", function () { parar(); irPara(parseInt(slider.value, 10)); });
    document.getElementById("geral-ant").addEventListener("click", function () { parar(); irPara(atual - 1); });
    document.getElementById("geral-prox").addEventListener("click", function () { parar(); irPara(atual + 1); });
    document.getElementById("geral-play").addEventListener("click", alternarPlay);
    cartao.addEventListener("click", function (ev) {
      if (ev.target.closest && ev.target.closest(".geral-cartao-fechar")) mostrar(null);
    });
    document.addEventListener("keydown", function (ev) {
      if (/INPUT|TEXTAREA|SELECT/.test((ev.target.tagName || ""))) return;
      if (ev.key === "ArrowLeft") { parar(); irPara(atual - 1); }
      else if (ev.key === "ArrowRight") { parar(); irPara(atual + 1); }
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
    fetch("/mapa-geral/dados/indice.json").then(function (r) { return r.json(); })
  ]).then(function (r) {
    anos = r[1].anos || [];
    meta = r[1].estados || {};
    nota.textContent = r[1].fonte || "";
    if (!anos.length) return falha("Ainda não há dados no mapa geral.");
    base(r[0]);
    slider.max = String(anos.length - 1);
    ligarControles();
    // abre perto do tempo dos patriarcas, se existir, ou no primeiro ano
    var ini = 0;
    for (var i = 0; i < anos.length; i++) if (anos[i] <= 1010) { ini = i; break; }
    // ?ano=-30 abre em 30 d.C. (a.C. positivo, d.C. negativo): o quadro-chave mais próximo
    var pedido = /[?&]ano=(-?\d+)/.exec(location.search);
    if (pedido) {
      var alvo = parseInt(pedido[1], 10);
      for (var k = 0; k < anos.length; k++) if (Math.abs(anos[k] - alvo) < Math.abs(anos[ini] - alvo)) ini = k;
    }
    irPara(ini);
  }).catch(function () {
    falha("Não foi possível carregar o mapa geral. Abra por um servidor local (python -m http.server).");
  });
})();
