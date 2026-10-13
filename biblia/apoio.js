(function () {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";
  var raiz = document.getElementById("apoio");
  var dados = null;
  var lugares = {};
  var L = 0; // largura do mapa em unidades do SVG
  var A = 0; // altura
  var vb = { x: 0, y: 0, w: 0 }; // janela visível; a altura segue a proporção do mapa
  var atual = -1; // índice da etapa com o cartão aberto
  var svgEl = null;
  var escalaveis = []; // elementos que mantêm o tamanho na tela ao ampliar
  var rotas = [];
  var marcadores = [];
  var embutido = /[?&]embutido/.test(location.search); // aberto no popup do leitor
  var ZOOM_MAX = 64; // quantas vezes se pode ampliar a partir do mapa inteiro
  var etapasLigadas = []; // por etapa: aparece no mapa? (começam todas ligadas)
  var curiosLigadas = {}; // por curiosidade: aparece no mapa? (começam desligadas)
  var curioAtual = -1; // curiosidade escolhida
  var curioMarcadores = []; // [{el, i}], um por curiosidade que tem lugar no mapa

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function svg(tag, attrs, pai) {
    var el = document.createElementNS(NS, tag);
    for (var k in attrs) if (attrs.hasOwnProperty(k)) el.setAttribute(k, attrs[k]);
    if (pai) pai.appendChild(el);
    return el;
  }

  // projeção Mercator (a do mapa-múndi comum): x em graus de longitude, y em "latitude esticada"
  function merc(lat) {
    return Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
  }

  function proj(p) {
    var m = dados.mapa;
    var k = m.largura / (2 * Math.PI);
    return [((p[0] - m.lon[0]) * Math.PI / 180) * k, (merc(m.lat[1]) - merc(p[1])) * k];
  }

  function pontos(lista) {
    return lista
      .map(function (p) {
        var q = proj(p);
        return q[0].toFixed(1) + "," + q[1].toFixed(1);
      })
      .join(" ");
  }

  function limitar(v, a, b) {
    return Math.max(a, Math.min(b, v));
  }

  /* janela do mapa (zoom e arrastar) */

  // altura do quadro em relação à largura: o mapa preenche o quadro, seja ele largo ou alto
  function razao() {
    return svgEl.clientWidth && svgEl.clientHeight ? svgEl.clientHeight / svgEl.clientWidth : A / L;
  }

  function aplicar() {
    var r = razao();
    vb.w = limitar(vb.w, L / ZOOM_MAX, Math.min(L, A / r));
    var h = vb.w * r;
    vb.x = limitar(vb.x, 0, L - vb.w);
    vb.y = limitar(vb.y, 0, A - h);
    svgEl.setAttribute("viewBox", vb.x.toFixed(1) + " " + vb.y.toFixed(1) + " " + vb.w.toFixed(1) + " " + h.toFixed(1));
    var k = vb.w / (svgEl.clientWidth || L);
    escalaveis.forEach(function (e) {
      e.el.setAttribute("transform", "translate(" + e.x.toFixed(1) + " " + e.y.toFixed(1) + ") scale(" + k.toFixed(4) + ")");
    });
  }

  function zoomEm(fator, cx, cy) {
    var nw = limitar(vb.w * fator, L / ZOOM_MAX, Math.min(L, A / razao()));
    var r = nw / vb.w;
    var h = vb.w * razao();
    if (cx == null) {
      cx = vb.x + vb.w / 2;
      cy = vb.y + h / 2;
    }
    vb.x = cx - (cx - vb.x) * r;
    vb.y = cy - (cy - vb.y) * r;
    vb.w = nw;
    aplicar();
  }

  function pontosDaEtapa(e) {
    return e.caminho && e.caminho.length ? e.caminho : [[lugares[e.lugar].lon, lugares[e.lugar].lat]];
  }

  // vista inicial: a região por onde passam todas as etapas, um pouco mais perto que o mapa inteiro
  function vistaInicial() {
    var pts = [];
    if (dados.vista) pts = dados.vista; // o material pode escolher o enquadramento de abertura
    else
      dados.etapas.forEach(function (e) {
        pts = pts.concat(pontosDaEtapa(e));
      });
    focarPontos(pts);
  }

  function focarEtapa(i) {
    focarPontos(pontosDaEtapa(dados.etapas[i]));
  }

  function focarPontos(pts, folga) {
    var xs = [];
    var ys = [];
    pts.forEach(function (p) {
      var q = proj(p);
      xs.push(q[0]);
      ys.push(q[1]);
    });
    var x0 = Math.min.apply(null, xs);
    var x1 = Math.max.apply(null, xs);
    var y0 = Math.min.apply(null, ys);
    var y1 = Math.max.apply(null, ys);
    // folga proporcional ao tamanho da região, para mapas de uma cidade ou de um continente
    var pad = folga || Math.max(20, 0.12 * Math.max(x1 - x0, y1 - y0));
    var w = Math.max(x1 - x0 + 2 * pad, (y1 - y0 + 2 * pad) / razao(), L / ZOOM_MAX);
    vb.w = limitar(w, L / ZOOM_MAX, Math.min(L, A / razao()));
    vb.x = (x0 + x1) / 2 - vb.w / 2;
    vb.y = (y0 + y1) / 2 - (vb.w * razao()) / 2;
    aplicar();
  }

  /* desenho do mapa */

  function desenhar() {
    var m = dados.mapa;
    L = m.largura;
    A = (merc(m.lat[1]) - merc(m.lat[0])) * m.largura / (2 * Math.PI);
    vb.x = 0;
    vb.y = 0;
    vb.w = L;

    svgEl = svg("svg", {
      "class": "apoio-svg",
      viewBox: "0 0 " + L + " " + A,
      role: "img",
      "aria-label": dados.aria || "Mapa-múndi"
    });
    // base de terra; mares, lagos e rios são desenhados por cima
    var base = svg("g", {}, svgEl);
    svg("rect", { "class": "apoio-agua fundo", x: 0, y: 0, width: L, height: A }, base);
    dados.fundo.forEach(function (f) {
      if (f.tipo === "terra") {
        // vários anéis num só caminho: os de dentro (mares interiores) ficam vazados
        var d = f.aneis.map(function (a) { return "M" + pontos(a) + "Z"; }).join("");
        svg("path", { "class": "apoio-terra", d: d.replace(/ /g, "L"), "fill-rule": "evenodd" }, base);
      } else if (f.tipo === "mar") {
        svg("polygon", { "class": "apoio-agua", points: pontos(f.pontos) }, base);
      } else {
        svg("polyline", { "class": "apoio-rio", points: pontos(f.pontos), fill: "none" }, base);
      }
    });

    dados.rotulos.forEach(function (r) {
      var q = proj([r.lon, r.lat]);
      var t = svg("text", { "class": "apoio-rotulo " + r.tipo, "text-anchor": "middle" }, svgEl);
      t.textContent = r.texto;
      escalaveis.push({ el: t, x: q[0], y: q[1] });
    });

    dados.etapas.forEach(function (e, i) {
      if (!e.caminho || e.caminho.length < 2) {
        rotas.push(null);
        return;
      }
      rotas.push(svg("polyline", { "class": "apoio-rota" + (e.incerto ? " incerto" : ""), points: pontos(e.caminho), fill: "none" }, svgEl));
    });

    // etapas no mesmo lugar (Hebrom, por exemplo) ficam lado a lado, e só a primeira leva o nome
    var porLugar = {};
    dados.etapas.forEach(function (e, i) {
      (porLugar[e.lugar] = porLugar[e.lugar] || []).push(i);
    });

    dados.etapas.forEach(function (e, i) {
      var lg = lugares[e.lugar];
      var q = proj([lg.lon, lg.lat]);
      var grupo = porLugar[e.lugar];
      var pos = grupo.indexOf(i);
      var meio = ((grupo.length - 1) * 26) / 2;
      var dx = pos * 26 - meio; // deslocamento em pixels de tela; o grupo é escalado por escalaveis
      var g = svg("g", { "class": "apoio-marcador", tabindex: 0, role: "button", "data-i": i, "aria-label": (i + 1) + ". " + lg.nome + ", " + e.ref }, svgEl);
      svg("circle", { r: 11, cx: dx, cy: 0 }, g);
      var n = svg("text", { "class": "apoio-num", "text-anchor": "middle", x: dx, y: 4 }, g);
      n.textContent = i + 1;
      // o nome vai para a esquerda perto da borda direita, ou onde o lugar pedir (lado: "esq" ou "dir")
      var direita = lg.lado ? lg.lado === "esq" : q[0] > L * 0.7;
      if (pos === 0) {
        var nome = svg("text", { "class": "apoio-nome", x: direita ? -meio - 16 : meio + 16, y: 4, "text-anchor": direita ? "end" : "start" }, g);
        nome.textContent = lg.nome;
      }
      escalaveis.push({ el: g, x: q[0], y: q[1] });
      marcadores.push(g);
    });

    // curiosidades: aparecem só quando o painel delas está aberto
    (dados.curiosidades || []).forEach(function (c, i) {
      if (c.lon == null) return;
      var q = proj([c.lon, c.lat]);
      var g = svg("g", { "class": "apoio-curio-pt", tabindex: 0, role: "button", "data-ci": i, "aria-label": c.titulo + ", " + c.quando }, svgEl);
      svg("rect", { x: -6, y: -6, width: 12, height: 12, transform: "rotate(45)" }, g);
      svg("title", {}, g).textContent = c.titulo + " · " + c.quando;
      g.style.display = "none";
      escalaveis.push({ el: g, x: q[0], y: q[1] });
      curioMarcadores.push({ el: g, i: i });
    });
  }

  /* cartão de texto, caixas de seleção (apoio e curiosidades) e interação */

  function cartao() {
    var el = document.getElementById("apoio-cartao");
    var h = "";
    if (atual >= 0) {
      var e = dados.etapas[atual];
      h += '<p class="hud muted">' + (atual + 1) + " de " + dados.etapas.length + " · " + esc(e.ref) + "</p>";
      h += "<h2>" + esc(e.titulo) + "</h2><p>" + esc(e.texto) + "</p>";
      if (!embutido) h += '<p><a class="btn" href="ler.html#' + dados.livro + "/" + e.cap + '">Ler ' + esc(dados.livroNome) + " " + e.cap + "</a></p>";
    } else if (curioAtual >= 0) {
      var c = dados.curiosidades[curioAtual];
      h += '<p class="hud muted">' + esc(c.regiao) + " · " + esc(c.quando) + "</p>";
      h += "<h2>" + esc(c.titulo) + "</h2><p>" + esc(c.texto) + "</p>";
    }
    el.hidden = !h;
    el.innerHTML = h ? '<button type="button" class="apoio-fechar" data-fechar aria-label="Fechar">×</button>' + h : "";
  }

  // dois grupos recolhíveis, cada um com uma caixa "tudo" e uma caixa por item
  function construirBarra() {
    var curios = dados.curiosidades || [];
    var h = '<details class="apoio-grupo" data-grupo="apoio"><summary>' +
      '<input type="checkbox" data-mestre="apoio" aria-label="Mostrar ou esconder todas as etapas">' +
      '<span class="apoio-grupo-nome">Apoio</span><span class="hud faint" data-contagem="apoio"></span></summary><div class="apoio-itens">';
    dados.etapas.forEach(function (e, i) {
      h += '<label class="apoio-item"><input type="checkbox" data-etapa="' + i + '"><span class="apoio-n hud">' + (i + 1) + "</span><span>" + esc(e.titulo) + "</span></label>";
    });
    h += "</div></details>";
    if (curios.length) {
      var regioes = [];
      curios.forEach(function (c) {
        if (regioes.indexOf(c.regiao) < 0) regioes.push(c.regiao);
      });
      h += '<details class="apoio-grupo" data-grupo="curio"><summary>' +
        '<input type="checkbox" data-mestre="curio" aria-label="Mostrar ou esconder todas as curiosidades">' +
        '<span class="apoio-grupo-nome">Curiosidades</span><span class="hud faint" data-contagem="curio"></span></summary><div class="apoio-itens">';
      regioes.forEach(function (r) {
        h += '<label class="apoio-item regiao"><input type="checkbox" data-regiao-grupo="' + esc(r) + '"><strong>' + esc(r) + "</strong></label>";
        curios.forEach(function (c, i) {
          if (c.regiao === r) h += '<label class="apoio-item sub"><input type="checkbox" data-curio="' + i + '"><span>' + esc(c.titulo) + "</span></label>";
        });
      });
      h += "</div></details>";
    }
    document.getElementById("apoio-barra").innerHTML = h;
  }

  // põe cada caixa no estado certo (marcada, desmarcada ou "alguns") e atualiza as contagens
  function sincronizarBarra() {
    var barraEl = document.getElementById("apoio-barra");
    function estado(caixa, n, total) {
      if (!caixa) return;
      caixa.checked = total > 0 && n === total;
      caixa.indeterminate = n > 0 && n < total;
    }
    var nE = 0;
    dados.etapas.forEach(function (e, i) {
      if (etapasLigadas[i]) nE++;
      var c = barraEl.querySelector('[data-etapa="' + i + '"]');
      if (c) c.checked = !!etapasLigadas[i];
    });
    estado(barraEl.querySelector('[data-mestre="apoio"]'), nE, dados.etapas.length);
    var ca = barraEl.querySelector('[data-contagem="apoio"]');
    if (ca) ca.textContent = nE + "/" + dados.etapas.length;

    var curios = dados.curiosidades || [];
    var nC = 0;
    var porRegiao = {};
    curios.forEach(function (c, i) {
      var on = !!curiosLigadas[i];
      if (on) nC++;
      var r = (porRegiao[c.regiao] = porRegiao[c.regiao] || { n: 0, total: 0 });
      r.total++;
      if (on) r.n++;
      var cx = barraEl.querySelector('[data-curio="' + i + '"]');
      if (cx) cx.checked = on;
    });
    Object.keys(porRegiao).forEach(function (r) {
      var cx = barraEl.querySelector('[data-regiao-grupo="' + r.replace(/"/g, '\\"') + '"]');
      estado(cx, porRegiao[r].n, porRegiao[r].total);
    });
    estado(barraEl.querySelector('[data-mestre="curio"]'), nC, curios.length);
    var cc = barraEl.querySelector('[data-contagem="curio"]');
    if (cc) cc.textContent = nC + "/" + curios.length;
  }

  function marcar() {
    marcadores.forEach(function (g, i) {
      g.setAttribute("class", "apoio-marcador" + (i === atual ? " ativo" : ""));
      g.style.display = etapasLigadas[i] ? "" : "none";
    });
    rotas.forEach(function (r, i) {
      if (!r) return;
      var e = dados.etapas[i];
      r.setAttribute("class", "apoio-rota" + (e.incerto ? " incerto" : "") + (i === atual ? " ativa" : ""));
      r.style.display = etapasLigadas[i] ? "" : "none";
    });
    // a etapa selecionada fica por cima das outras
    if (atual >= 0) {
      if (rotas[atual]) svgEl.insertBefore(rotas[atual], marcadores[0]);
      svgEl.appendChild(marcadores[atual]);
    }
    curioMarcadores.forEach(function (m) {
      m.el.style.display = curiosLigadas[m.i] ? "" : "none";
      m.el.setAttribute("class", "apoio-curio-pt" + (m.i === curioAtual ? " atual" : ""));
    });
    sincronizarBarra();
    cartao();
  }

  // enquadra no mapa as curiosidades que estão ligadas
  function enquadrarCurio() {
    var pts = [];
    curioMarcadores.forEach(function (m) {
      var c = dados.curiosidades[m.i];
      if (curiosLigadas[m.i]) pts.push([c.lon, c.lat]);
    });
    if (pts.length) focarPontos(pts, 130);
  }

  function limparHash() {
    if (location.hash) history.replaceState(null, "", location.pathname + location.search);
  }

  function fecharCartao() {
    atual = -1;
    curioAtual = -1;
    limparHash();
    marcar();
  }

  function abrirEtapa(i, focar) {
    atual = limitar(i, 0, dados.etapas.length - 1);
    curioAtual = -1;
    etapasLigadas[atual] = true;
    marcar();
    if (focar) focarEtapa(atual);
  }

  function abrirCurio(i) {
    if (i === curioAtual) return fecharCartao();
    atual = -1;
    curioAtual = i;
    limparHash();
    marcar();
    var c = dados.curiosidades[i];
    if (c.lon != null) focarPontos([[c.lon, c.lat]]);
  }

  // caixa marcada ou desmarcada na barra
  function mudouCaixa(cx) {
    var barraEl = document.getElementById("apoio-barra");
    var on = cx.checked;
    var curios = dados.curiosidades || [];
    var ligouCuriosidades = false;
    if (cx.hasAttribute("data-mestre")) {
      if (cx.getAttribute("data-mestre") === "apoio") dados.etapas.forEach(function (e, i) { etapasLigadas[i] = on; });
      else {
        curios.forEach(function (c, i) { curiosLigadas[i] = on; });
        ligouCuriosidades = on;
      }
    } else if (cx.hasAttribute("data-etapa")) {
      etapasLigadas[parseInt(cx.getAttribute("data-etapa"), 10)] = on;
    } else if (cx.hasAttribute("data-regiao-grupo")) {
      var r = cx.getAttribute("data-regiao-grupo");
      curios.forEach(function (c, i) { if (c.regiao === r) curiosLigadas[i] = on; });
      ligouCuriosidades = on;
    } else if (cx.hasAttribute("data-curio")) {
      curiosLigadas[parseInt(cx.getAttribute("data-curio"), 10)] = on;
    }
    // o cartão aberto some junto com o que foi desligado
    if (atual >= 0 && !etapasLigadas[atual]) atual = -1;
    if (curioAtual >= 0 && !curiosLigadas[curioAtual]) curioAtual = -1;
    if (atual < 0) limparHash();
    marcar();
    if (ligouCuriosidades) enquadrarCurio();
  }

  function indiceDoHash() {
    var id = decodeURIComponent((location.hash || "").slice(1));
    for (var i = 0; i < dados.etapas.length; i++) if (dados.etapas[i].id === id) return i;
    return -1;
  }

  function ir(i) {
    if (i === atual) return fecharCartao();
    var id = dados.etapas[limitar(i, 0, dados.etapas.length - 1)].id;
    if (location.hash === "#" + id) abrirEtapa(i, true);
    else location.hash = id;
  }

  function ligar() {
    raiz.addEventListener("click", function (ev) {
      if (ev.target.closest("[data-fechar]")) return fecharCartao();
      var ci = ev.target.closest("[data-ci]");
      if (ci && raiz.contains(ci)) return abrirCurio(parseInt(ci.getAttribute("data-ci"), 10));
      var b = ev.target.closest("[data-i]");
      if (b && raiz.contains(b)) return ir(parseInt(b.getAttribute("data-i"), 10));
    });

    // as listas se sobrepõem ao mapa: só uma aberta por vez, e fecham ao tocar fora ou com Esc
    document.getElementById("apoio-barra").addEventListener("toggle", function (ev) {
      var d = ev.target;
      if (!d.open) return;
      var todas = document.querySelectorAll("#apoio-barra .apoio-grupo");
      for (var i = 0; i < todas.length; i++) if (todas[i] !== d) todas[i].open = false;
    }, true);
    document.addEventListener("click", function (ev) {
      if (ev.target.closest && ev.target.closest(".apoio-grupo")) return;
      var abertas = document.querySelectorAll("#apoio-barra .apoio-grupo[open]");
      for (var i = 0; i < abertas.length; i++) abertas[i].open = false;
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key !== "Escape") return;
      var abertas = document.querySelectorAll("#apoio-barra .apoio-grupo[open]");
      for (var i = 0; i < abertas.length; i++) abertas[i].open = false;
    });

    raiz.addEventListener("change", function (ev) {
      var cx = ev.target;
      if (cx && cx.type === "checkbox") mudouCaixa(cx);
    });

    raiz.addEventListener("keydown", function (ev) {
      if (ev.key !== "Enter" && ev.key !== " ") return;
      var g = ev.target.closest && ev.target.closest(".apoio-marcador");
      if (g) {
        ev.preventDefault();
        return ir(parseInt(g.getAttribute("data-i"), 10));
      }
      var cp = ev.target.closest && ev.target.closest(".apoio-curio-pt");
      if (cp) {
        ev.preventDefault();
        abrirCurio(parseInt(cp.getAttribute("data-ci"), 10));
      }
    });

    // arrastar com um dedo (ou o mouse), pinça com dois, toque duplo para ampliar
    var dedos = {}; // pointerId -> { x, y }
    var arrasto = null;
    var pinca = null;
    var ultimoToque = null;

    function nDedos() {
      return Object.keys(dedos).length;
    }

    function iniciarPinca() {
      var ids = Object.keys(dedos);
      var a = dedos[ids[0]];
      var b = dedos[ids[1]];
      var r = svgEl.getBoundingClientRect();
      var mx = (a.x + b.x) / 2;
      var my = (a.y + b.y) / 2;
      var k = vb.w / r.width;
      pinca = {
        d0: Math.max(1, Math.hypot(a.x - b.x, a.y - b.y)),
        w0: vb.w,
        wx: vb.x + (mx - r.left) * k, // ponto do mapa sob os dedos, que deve ficar sob eles
        wy: vb.y + (my - r.top) * k
      };
      arrasto = null;
    }

    svgEl.addEventListener("pointerdown", function (ev) {
      dedos[ev.pointerId] = { x: ev.clientX, y: ev.clientY };
      if (nDedos() === 2) {
        iniciarPinca();
        svgEl.classList.add("arrastando");
        return;
      }
      if (ev.target.closest(".apoio-marcador, .apoio-curio-pt")) return;
      arrasto = { x: ev.clientX, y: ev.clientY, vx: vb.x, vy: vb.y, t: Date.now(), mexeu: false };
      svgEl.setPointerCapture(ev.pointerId);
      svgEl.classList.add("arrastando");
    });

    svgEl.addEventListener("pointermove", function (ev) {
      if (!dedos[ev.pointerId]) return;
      dedos[ev.pointerId] = { x: ev.clientX, y: ev.clientY };
      if (pinca && nDedos() >= 2) {
        var ids = Object.keys(dedos);
        var a = dedos[ids[0]];
        var b = dedos[ids[1]];
        var r = svgEl.getBoundingClientRect();
        var d = Math.max(1, Math.hypot(a.x - b.x, a.y - b.y));
        var h = r.height / r.width;
        vb.w = pinca.w0 * (pinca.d0 / d);
        aplicar(); // limita a janela; o centro volta para baixo dos dedos
        var k = vb.w / r.width;
        vb.x = pinca.wx - ((a.x + b.x) / 2 - r.left) * k;
        vb.y = pinca.wy - ((a.y + b.y) / 2 - r.top) * k;
        aplicar();
        return;
      }
      if (!arrasto) return;
      var kk = vb.w / svgEl.clientWidth;
      if (Math.abs(ev.clientX - arrasto.x) + Math.abs(ev.clientY - arrasto.y) > 6) arrasto.mexeu = true;
      vb.x = arrasto.vx - (ev.clientX - arrasto.x) * kk;
      vb.y = arrasto.vy - (ev.clientY - arrasto.y) * kk;
      aplicar();
    });

    function soltar(ev) {
      var a = arrasto;
      delete dedos[ev.pointerId];
      if (pinca) {
        if (nDedos() < 2) {
          pinca = null;
          // o dedo que sobrou continua arrastando a partir de onde está
          var resto = Object.keys(dedos)[0];
          if (resto != null) arrasto = { x: dedos[resto].x, y: dedos[resto].y, vx: vb.x, vy: vb.y, t: 0, mexeu: true };
          else svgEl.classList.remove("arrastando");
        }
        return;
      }
      arrasto = null;
      svgEl.classList.remove("arrastando");
      // toque duplo no mapa (fora dos marcadores) amplia nesse ponto
      if (ev.type === "pointerup" && a && !a.mexeu && a.t && Date.now() - a.t < 300) {
        var agora = Date.now();
        if (ultimoToque && agora - ultimoToque.t < 350 && Math.abs(ev.clientX - ultimoToque.x) + Math.abs(ev.clientY - ultimoToque.y) < 30) {
          var r = svgEl.getBoundingClientRect();
          var k = vb.w / r.width;
          zoomEm(0.5, vb.x + (ev.clientX - r.left) * k, vb.y + (ev.clientY - r.top) * k);
          ultimoToque = null;
        } else {
          ultimoToque = { t: agora, x: ev.clientX, y: ev.clientY };
        }
      }
    }
    svgEl.addEventListener("pointerup", soltar);
    svgEl.addEventListener("pointercancel", soltar);

    // a roda do mouse sobre o mapa amplia e reduz
    svgEl.addEventListener(
      "wheel",
      function (ev) {
        ev.preventDefault();
        var r = svgEl.getBoundingClientRect();
        var k = vb.w / r.width;
        zoomEm(ev.deltaY < 0 ? 0.8 : 1.25, vb.x + (ev.clientX - r.left) * k, vb.y + (ev.clientY - r.top) * k);
      },
      { passive: false }
    );

    window.addEventListener("resize", aplicar);
    window.addEventListener("hashchange", function () {
      var i = indiceDoHash();
      if (i >= 0) abrirEtapa(i, true);
    });
  }

  function iniciar() {
    dados.lugares.forEach(function (l) {
      lugares[l.id] = l;
    });
    desenhar();
    raiz.innerHTML =
      '<div class="apoio-barra" id="apoio-barra"></div>' +
      '<div class="apoio-mapa">' +
      '<div id="apoio-svg"></div>' +
      '<div class="apoio-cartao" id="apoio-cartao" aria-live="polite" hidden></div>' +
      "</div>" +
      "";
    document.getElementById("apoio-svg").appendChild(svgEl);
    dados.etapas.forEach(function (e, i) { etapasLigadas[i] = true; });
    construirBarra();
    ligar();
    var i = indiceDoHash();
    aplicar();
    marcar();
    if (i >= 0) abrirEtapa(i, true);
    else vistaInicial();
  }

  // ?m=jo abre dados/apoio-jo.json; sem parâmetro, dados/apoio.json (viagem de Abrão)
  function carregar(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error("http " + r.status);
      return r.json();
    });
  }

  var qual = /[?&]m=([a-z0-9-]+)/.exec(location.search);
  carregar(qual ? "dados/apoio-" + qual[1] + ".json" : "dados/apoio.json")
    .then(function (d) {
      // a base do mundo (costas, rios, nomes e curiosidades da época) é comum a todos os materiais
      return carregar("dados/" + (d.mundo || "mundo.json")).then(function (w) {
        d.mapa = w.mapa;
        d.fundo = w.fundo;
        d.rotulos = w.rotulos;
        d.curiosidades = (w.curiosidades || []).concat(d.curiosidades || []);
        return d;
      });
    })
    .then(function (d) {
      dados = d;
      var h1 = document.getElementById("apoio-titulo");
      if (h1) h1.innerHTML = esc(d.titulo) + " <em>" + esc(d.destaque) + "</em>";
      var sub = document.getElementById("apoio-sub");
      if (sub) sub.textContent = d.subtitulo;
      document.title = d.titulo + " " + d.destaque.replace(/\.$/, "") + " — Mapa da Bíblia";
      iniciar();
    })
    .catch(function () {
      raiz.innerHTML =
        '<p class="vazio hud faint">Não foi possível carregar o mapa. Abra por um servidor local (python -m http.server).</p>';
    });
})();
