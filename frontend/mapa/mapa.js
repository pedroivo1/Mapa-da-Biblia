// Mapa aberto (mapa/index.html?m=id): mapa-múndi em SVG próprio com zoom e arrastar.
// Dados: mapa-<id>.json (lugares e etapas com rotas) sobre mundo.json (costas e rios).
// Sem ?m= abre mapa-abraao.json. Com ?embutido roda dentro do popup (sem nav nem rodapé).
(function () {
  "use strict";

  var esc = Util.esc;

  var NS = "http://www.w3.org/2000/svg";
  var raiz = document.getElementById("mapa");
  var dados = null;
  var lugares = {};
  var L = 0; // largura do mapa em unidades do SVG
  var A = 0; // altura
  var vb = { x: 0, y: 0, w: 0 }; // janela visível; a altura segue a proporção do mapa
  var svgEl = null;
  var escalaveis = []; // elementos que mantêm o tamanho na tela ao ampliar
  var rotas = [];
  var geo = []; // por etapa com rota: { pts, faixas, seta, poli, ent }
  var lugaresNoMapa = []; // [{el, etapas: [índices]}], um por lugar
  var ZOOM_MAX = 160; // quantas vezes se pode ampliar a partir do mapa inteiro
  var etapasLigadas = []; // por etapa: a rota aparece no mapa? (começam todas ligadas)

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
    redesenharRotas(k);
    escalaveis.forEach(function (e) {
      e.el.setAttribute("transform", "translate(" + e.x.toFixed(1) + " " + e.y.toFixed(1) + ") scale(" + k.toFixed(4) + ")");
    });
    filtrarLugares();
  }

  /* rotas lado a lado: trechos que seguem o mesmo caminho ganham faixas paralelas, em pixels de tela */

  var FAIXA = 10; // distância entre faixas, em pixels

  function distSeg(p, a, b) {
    var dx = b[0] - a[0];
    var dy = b[1] - a[1];
    var t = dx || dy ? limitar(((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy), 0, 1) : 0;
    return Math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy);
  }

  function faixaPx(f) {
    return f === 0 ? 0 : (f % 2 ? 1 : -1) * Math.ceil(f / 2) * FAIXA;
  }

  // normal de um trecho, sempre do mesmo lado do eixo para trechos em sentidos opostos
  function normal(a, b) {
    var dx = b[0] - a[0];
    var dy = b[1] - a[1];
    var d = Math.hypot(dx, dy) || 1;
    dx /= d;
    dy /= d;
    if (dx < 0 || (dx === 0 && dy < 0)) {
      dx = -dx;
      dy = -dy;
    }
    return [-dy, dx];
  }

  // faixa de cada trecho: a menor ainda não usada pelas rotas anteriores que passam pelo mesmo lugar
  function calcularFaixas() {
    var TOL = 1.4; // unidades do mapa (cerca de 0,14 grau)
    var anteriores = [];
    geo.forEach(function (g) {
      if (!g) return;
      g.faixas = [];
      for (var j = 0; j < g.pts.length - 1; j++) {
        var a = g.pts[j];
        var b = g.pts[j + 1];
        var len = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
        var usadas = {};
        anteriores.forEach(function (o) {
          for (var q = 0; q < o.pts.length - 1; q++) {
            var c = o.pts[q];
            var d = o.pts[q + 1];
            var ld = Math.hypot(d[0] - c[0], d[1] - c[1]) || 1;
            var par = Math.abs(((b[0] - a[0]) * (d[0] - c[0]) + (b[1] - a[1]) * (d[1] - c[1])) / (len * ld));
            if (par < 0.6) continue;
            for (var t = 0.2; t < 0.9; t += 0.3) {
              var p = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
              if (distSeg(p, c, d) < TOL) {
                usadas[o.faixas[q]] = true;
                break;
              }
            }
          }
        });
        var f = 0;
        while (usadas[f]) f++;
        g.faixas.push(f);
      }
      anteriores.push(g);
    });
  }

  function redesenharRotas(k) {
    var N = 12; // pontos intermediários por trecho, para a curva afastar-se suavemente
    var rampa = 40 * k;
    geo.forEach(function (g) {
      if (!g) return;
      var n = g.pts.length;
      var seg = [];
      for (var j = 0; j < n - 1; j++) {
        var nv = normal(g.pts[j], g.pts[j + 1]);
        var o = faixaPx(g.faixas[j]);
        seg.push([nv[0] * o, nv[1] * o]);
      }
      // deslocamento de cada vértice: média dos trechos vizinhos
      var V = g.pts.map(function (p, v) {
        var a = seg[Math.max(0, v - 1)];
        var b = seg[Math.min(seg.length - 1, v)];
        return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
      });
      var P = [];
      var D = [];
      var acum = 0;
      for (j = 0; j < n - 1; j++) {
        var a = g.pts[j];
        var b = g.pts[j + 1];
        var l = Math.hypot(b[0] - a[0], b[1] - a[1]);
        for (var s = 0; s < N; s++) {
          var t = s / N;
          P.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, V[j][0] + (V[j + 1][0] - V[j][0]) * t, V[j][1] + (V[j + 1][1] - V[j][1]) * t]);
          D.push(acum + l * t);
        }
        acum += l;
      }
      P.push([g.pts[n - 1][0], g.pts[n - 1][1], V[n - 1][0], V[n - 1][1]]);
      D.push(acum);
      var R = P.map(function (p, i) {
        var m = limitar(Math.min(D[i], acum - D[i]) / rampa, 0, 1);
        return [p[0] + p[2] * k * m, p[1] + p[3] * k * m];
      });
      g.poli.setAttribute("points", R.map(function (p) { return p[0].toFixed(2) + "," + p[1].toFixed(2); }).join(" "));
      // seta no meio do último trecho
      var i = (n - 2) * N + N / 2;
      var ang = (Math.atan2(R[i + 1][1] - R[i - 1][1], R[i + 1][0] - R[i - 1][0]) * 180) / Math.PI;
      g.ent.x = R[i][0];
      g.ent.y = R[i][1];
      g.seta.setAttribute("transform", "rotate(" + ang.toFixed(1) + ")");
    });
  }

  // com o mapa afastado, só os lugares mais citados cabem; ao ampliar, os outros aparecem
  function filtrarLugares() {
    var k = svgEl.clientWidth / vb.w;
    var h = vb.w * razao();
    var ocupados = [];
    var ordem = lugaresNoMapa.slice().sort(function (a, b) {
      return b.etapas.length - a.etapas.length || a.ordem - b.ordem;
    });
    ordem.forEach(function (p) {
      var x = (p.x - vb.x) * k;
      var y = (p.y - vb.y) * k;
      var fora = p.x < vb.x || p.x > vb.x + vb.w || p.y < vb.y || p.y > vb.y + h;
      var larg = p.nome.length * 7.2 + 16;
      var c = { x0: p.esq ? x - 10 - larg : x - 3, x1: p.esq ? x + 3 : x + 10 + larg, y0: y - 10, y1: y + 10 };
      var cabe = !fora && p.ligado;
      if (cabe) {
        for (var i = 0; i < ocupados.length; i++) {
          var o = ocupados[i];
          if (c.x0 < o.x1 && c.x1 > o.x0 && c.y0 < o.y1 && c.y1 > o.y0) {
            cabe = false;
            break;
          }
        }
      }
      if (cabe) ocupados.push(c);
      p.el.style.visibility = cabe || fora || !p.ligado ? "" : "hidden";
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
      "class": "mapa-svg",
      viewBox: "0 0 " + L + " " + A,
      role: "img",
      "aria-label": dados.aria || "Mapa-múndi"
    });
    // base de terra; mares, lagos e rios são desenhados por cima
    var base = svg("g", {}, svgEl);
    svg("rect", { "class": "mapa-agua fundo", x: 0, y: 0, width: L, height: A }, base);
    dados.fundo.forEach(function (f) {
      if (f.tipo === "terra") {
        // vários anéis num só caminho: os de dentro (mares interiores) ficam vazados
        var d = f.aneis.map(function (a) { return "M" + pontos(a) + "Z"; }).join("");
        svg("path", { "class": "mapa-terra", d: d.replace(/ /g, "L"), "fill-rule": "evenodd" }, base);
      } else if (f.tipo === "mar") {
        svg("polygon", { "class": "mapa-agua", points: pontos(f.pontos) }, base);
      } else {
        svg("polyline", { "class": "mapa-rio", points: pontos(f.pontos), fill: "none" }, base);
      }
    });

    dados.rotulos.forEach(function (r) {
      var q = proj([r.lon, r.lat]);
      var t = svg("text", { "class": "mapa-rotulo " + r.tipo, "text-anchor": "middle" }, svgEl);
      t.textContent = r.texto;
      escalaveis.push({ el: t, x: q[0], y: q[1] });
    });


    // rotas tracejadas, com uma seta no meio do último trecho para mostrar o sentido
    dados.etapas.forEach(function (e) {
      if (!e.caminho || e.caminho.length < 2) {
        rotas.push(null);
        return;
      }
      var grupo = svg("g", { "class": "mapa-rota" }, svgEl);
      var poli = svg("polyline", { points: pontos(e.caminho), fill: "none" }, grupo);
      var m = svg("g", {}, svgEl);
      var seta = svg("path", { "class": "mapa-seta", d: "M-7,-6 L7,0 L-7,6 Z" }, m);
      var ent = { el: m, x: 0, y: 0 };
      escalaveis.push(ent);
      geo[rotas.length] = { pts: e.caminho.map(proj), poli: poli, seta: seta, ent: ent };
      grupo.seta = m;
      rotas.push(grupo);
    });

    calcularFaixas();

    // um ponto por lugar, só com o nome
    var porLugar = {};
    dados.etapas.forEach(function (e, i) {
      (porLugar[e.lugar] = porLugar[e.lugar] || []).push(i);
    });
    Object.keys(porLugar).forEach(function (id) {
      var lg = lugares[id];
      var q = proj([lg.lon, lg.lat]);
      var g = svg("g", { "class": "mapa-lugar" }, svgEl);
      svg("circle", { r: 5, cx: 0, cy: 0 }, g);
      // o nome vai para a esquerda perto da borda direita, ou onde o lugar pedir (lado: "esq" ou "dir")
      var esquerda = lg.lado ? lg.lado === "esq" : q[0] > L * 0.7;
      // localização desconhecida ou debatida: nome com sublinhado tracejado
      var nome = svg("text", { "class": "mapa-nome" + (lg.incerto ? " incerto" : ""), x: esquerda ? -10 : 10, y: 4, "text-anchor": esquerda ? "end" : "start" }, g);
      nome.textContent = lg.nome;
      escalaveis.push({ el: g, x: q[0], y: q[1] });
      lugaresNoMapa.push({ el: g, etapas: porLugar[id], x: q[0], y: q[1], nome: lg.nome, esq: esquerda, ordem: lugaresNoMapa.length, ligado: true });
    });
  }

  /* lista de rotas (caixas de seleção) */

  // lugar mais próximo de um ponto (longitude, latitude)
  function lugarPerto(p) {
    var melhor = null;
    var d0 = 1e9;
    dados.lugares.forEach(function (l) {
      var d = Math.pow(l.lon - p[0], 2) + Math.pow(l.lat - p[1], 2);
      if (d < d0) {
        d0 = d;
        melhor = l;
      }
    });
    return melhor;
  }

  // "Origem → Destino", pelos extremos do caminho
  function nomeDaRota(e) {
    var a = lugarPerto(e.caminho[0]);
    var b = lugarPerto(e.caminho[e.caminho.length - 1]);
    return a && b && a !== b ? a.nome + " → " + b.nome : e.titulo;
  }

  // só as etapas que têm rota entram na lista
  function construirBarra() {
    var h = '<details class="mapa-grupo" data-grupo="mapa"><summary>' +
      '<input type="checkbox" data-mestre="mapa" aria-label="Mostrar ou esconder todas as rotas">' +
      '<span class="mapa-grupo-nome">Rotas</span><span class="hud faint" data-contagem="mapa"></span></summary><div class="mapa-itens">';
    dados.etapas.forEach(function (e, i) {
      if (rotas[i]) h += '<label class="mapa-item"><input type="checkbox" data-etapa="' + i + '"><span>' + esc(nomeDaRota(e)) + "</span></label>";
    });
    h += "</div></details>";
    var barra = document.getElementById("mapa-barra");
    barra.innerHTML = h;
    barra.hidden = !rotas.some(function (r) { return r; });
  }

  // põe cada caixa no estado certo (marcada, desmarcada ou "alguns") e atualiza a contagem
  function sincronizarBarra() {
    var barraEl = document.getElementById("mapa-barra");
    var n = 0;
    var total = 0;
    dados.etapas.forEach(function (e, i) {
      if (!rotas[i]) return;
      total++;
      if (etapasLigadas[i]) n++;
      var c = barraEl.querySelector('[data-etapa="' + i + '"]');
      if (c) c.checked = !!etapasLigadas[i];
    });
    var mestre = barraEl.querySelector('[data-mestre="mapa"]');
    if (mestre) {
      mestre.checked = total > 0 && n === total;
      mestre.indeterminate = n > 0 && n < total;
    }
    var ca = barraEl.querySelector('[data-contagem="mapa"]');
    if (ca) ca.textContent = n + "/" + total;
  }

  function marcar() {
    rotas.forEach(function (r, i) {
      if (!r) return;
      r.style.display = etapasLigadas[i] ? "" : "none";
      r.seta.style.display = etapasLigadas[i] ? "" : "none";
    });
    // um lugar some só quando todas as suas rotas estão desligadas
    lugaresNoMapa.forEach(function (p) {
      var visivel = p.etapas.some(function (i) { return !rotas[i] || etapasLigadas[i]; });
      p.el.style.display = visivel ? "" : "none";
      p.ligado = visivel;
    });
    filtrarLugares();
    sincronizarBarra();
  }

  function ligar() {
    var barraEl = document.getElementById("mapa-barra");
    barraEl.addEventListener("change", function (ev) {
      var cx = ev.target;
      if (!cx || cx.type !== "checkbox") return;
      if (cx.hasAttribute("data-mestre")) dados.etapas.forEach(function (e, i) { etapasLigadas[i] = cx.checked; });
      else etapasLigadas[parseInt(cx.getAttribute("data-etapa"), 10)] = cx.checked;
      marcar();
    });

    // a lista se sobrepõe ao mapa: fecha ao tocar fora ou com Esc
    document.addEventListener("click", function (ev) {
      if (ev.target.closest && ev.target.closest(".mapa-grupo")) return;
      var abertas = document.querySelectorAll("#mapa-barra .mapa-grupo[open]");
      for (var i = 0; i < abertas.length; i++) abertas[i].open = false;
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key !== "Escape") return;
      var abertas = document.querySelectorAll("#mapa-barra .mapa-grupo[open]");
      for (var i = 0; i < abertas.length; i++) abertas[i].open = false;
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
  }

  function iniciar() {
    dados.lugares.forEach(function (l) {
      lugares[l.id] = l;
    });
    desenhar();
    raiz.innerHTML =
      '<div class="mapa-quadro"><div class="mapa-barra" id="mapa-barra"></div><div id="mapa-svg"></div></div>';
    document.getElementById("mapa-svg").appendChild(svgEl);
    dados.etapas.forEach(function (e, i) { etapasLigadas[i] = true; });
    construirBarra();
    ligar();
    aplicar();
    marcar();
    vistaInicial();
  }

  // ?m=jo abre mapa-jo.json; sem parâmetro, mapa-abraao.json (viagem de Abrão)
  function carregar(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error("http " + r.status);
      return r.json();
    });
  }

  var qual = /[?&]m=([a-z0-9-]+)/.exec(location.search);
  carregar(qual ? "/mapa/mapa-" + qual[1] + ".json" : "/mapa/mapa-abraao.json")
    .then(function (d) {
      // a base do mundo (costas, rios e nomes) é comum a todos os materiais
      return carregar("/mapa/" + (d.mundo || "mundo.json")).then(function (w) {
        d.mapa = w.mapa;
        d.fundo = w.fundo;
        d.rotulos = w.rotulos;
        return d;
      });
    })
    .then(function (d) {
      dados = d;
      var h1 = document.getElementById("mapa-titulo");
      if (h1) h1.innerHTML = esc(d.titulo) + " <em>" + esc(d.destaque) + "</em>";
      var sub = document.getElementById("mapa-sub");
      if (sub) sub.textContent = d.subtitulo;
      document.title = d.titulo + " " + d.destaque.replace(/\.$/, "") + " — Mapa da Bíblia";
      iniciar();
    })
    .catch(function () {
      raiz.innerHTML =
        '<p class="vazio hud faint">Não foi possível carregar o mapa. Abra por um servidor local (python -m http.server).</p>';
    });
})();