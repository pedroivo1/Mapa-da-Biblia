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
  var camadaApoio = true; // rota e números da viagem
  var curiosidades = false; // losangos da mesma época
  var regiao = ""; // filtro das curiosidades ("" = todas)
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

  function verTudo() {
    vb.x = 0;
    vb.y = 0;
    vb.w = L;
    aplicar();
  }

  function pontosDaEtapa(e) {
    return e.caminho && e.caminho.length ? e.caminho : [[lugares[e.lugar].lon, lugares[e.lugar].lat]];
  }

  // vista inicial: a região por onde passam todas as etapas, um pouco mais perto que o mapa inteiro
  function vistaInicial() {
    var pts = [];
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
    var pad = folga || 70;
    var w = Math.max(x1 - x0 + 2 * pad, (y1 - y0 + 2 * pad) / razao(), L / 25);
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

    dados.etapas.forEach(function (e, i) {
      var lg = lugares[e.lugar];
      var q = proj([lg.lon, lg.lat]);
      var g = svg("g", { "class": "apoio-marcador", tabindex: 0, role: "button", "data-i": i, "aria-label": (i + 1) + ". " + lg.nome + ", " + e.ref }, svgEl);
      svg("circle", { r: 11, cx: 0, cy: 0 }, g);
      var n = svg("text", { "class": "apoio-num", "text-anchor": "middle", y: 4 }, g);
      n.textContent = i + 1;
      var direita = q[0] > L * 0.7; // perto da borda, o nome vai para a esquerda
      var nome = svg("text", { "class": "apoio-nome", x: direita ? -16 : 16, y: 4, "text-anchor": direita ? "end" : "start" }, g);
      nome.textContent = lg.nome;
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

  /* cartão de texto, barra de camadas e interação */

  function cartao() {
    var el = document.getElementById("apoio-cartao");
    var h = "";
    if (atual >= 0) {
      var e = dados.etapas[atual];
      h += '<p class="hud muted">' + (atual + 1) + " de " + dados.etapas.length + " · " + esc(e.ref) + "</p>";
      h += "<h2>" + esc(e.titulo) + "</h2><p>" + esc(e.texto) + "</p>";
      if (e.incerto) h += '<p class="apoio-nota hud"><strong>Traçado aproximado.</strong> ' + esc(e.nota || "") + "</p>";
      if (!embutido) h += '<p><a class="btn" href="ler.html#' + dados.livro + "/" + e.cap + '">Ler ' + esc(dados.livroNome) + " " + e.cap + "</a></p>";
    } else if (curioAtual >= 0) {
      var c = dados.curiosidades[curioAtual];
      h += '<p class="hud muted">' + esc(c.regiao) + " · " + esc(c.quando) + "</p>";
      h += "<h2>" + esc(c.titulo) + "</h2><p>" + esc(c.texto) + "</p>";
    }
    el.hidden = !h;
    el.innerHTML = h ? '<button type="button" class="apoio-fechar" data-fechar aria-label="Fechar">×</button>' + h : "";
  }

  function barra() {
    var curios = dados.curiosidades || [];
    var h = "";
    // no popup do leitor esses dois botões ficam na linha das abas, lá em cima
    if (!embutido) {
      h += '<button type="button" class="chip" data-camada="apoio" aria-pressed="' + camadaApoio + '" title="Rota e etapas da viagem">Apoio</button> ';
      if (curios.length) h += '<button type="button" class="chip" data-camada="curio" aria-pressed="' + curiosidades + '">Curiosidades</button>';
    }
    var f = "";
    if (curiosidades) {
      var regioes = [];
      curios.forEach(function (c) {
        if (regioes.indexOf(c.regiao) < 0) regioes.push(c.regiao);
      });
      f += '<span class="apoio-filtros">';
      [""].concat(regioes).forEach(function (r) {
        f += '<button type="button" class="chip" data-regiao="' + esc(r) + '"' + (r === regiao ? ' aria-pressed="true"' : "") + ">" + esc(r || "Todas") + "</button> ";
      });
      f += "</span>";
      var fora = curios.map(function (c, i) { return { c: c, i: i }; }).filter(function (x) {
        return x.c.lon == null && (!regiao || x.c.regiao === regiao);
      });
      if (fora.length) {
        f += '<span class="apoio-filtros"><span class="hud faint">Fora do mapa:</span> ';
        fora.forEach(function (x) {
          f += '<button type="button" class="chip" data-ci="' + x.i + '"' + (x.i === curioAtual ? ' aria-pressed="true"' : "") + ">" + esc(x.c.titulo) + "</button> ";
        });
        f += "</span>";
      }
    }
    var el = document.getElementById("apoio-barra");
    el.innerHTML = h + f;
    el.hidden = !(h || f);
  }

  // popup do leitor: os botões da linha das abas mandam mensagens e recebem o estado
  function alternarCamada(nome) {
    if (nome === "apoio") {
      camadaApoio = !camadaApoio;
      if (!camadaApoio && atual >= 0) {
        atual = -1;
        limparHash();
      }
      return marcar();
    }
    curiosidades = !curiosidades;
    if (!curiosidades) curioAtual = -1;
    marcar();
    if (curiosidades) enquadrarCurio();
  }

  function avisarPai() {
    if (!embutido || window.parent === window) return;
    window.parent.postMessage({ tipo: "apoio-estado", apoio: camadaApoio, curiosidades: curiosidades }, location.origin);
  }

  window.addEventListener("message", function (ev) {
    if (ev.origin !== location.origin || !ev.data || ev.data.tipo !== "apoio-camada" || !dados || !svgEl) return;
    alternarCamada(ev.data.camada === "curio" ? "curio" : "apoio");
  });

  function marcar() {
    marcadores.forEach(function (g, i) {
      g.setAttribute("class", "apoio-marcador" + (i === atual ? " ativo" : atual >= 0 && i < atual ? " feito" : ""));
      g.style.display = camadaApoio ? "" : "none";
    });
    rotas.forEach(function (r, i) {
      if (!r) return;
      var e = dados.etapas[i];
      r.setAttribute("class", "apoio-rota" + (e.incerto ? " incerto" : "") + (i === atual ? " ativa" : atual >= 0 && i < atual ? " feita" : ""));
      r.style.display = camadaApoio ? "" : "none";
    });
    // a etapa selecionada fica por cima das outras
    if (atual >= 0) {
      if (rotas[atual]) svgEl.insertBefore(rotas[atual], marcadores[0]);
      svgEl.appendChild(marcadores[atual]);
    }
    curioMarcadores.forEach(function (m) {
      var c = dados.curiosidades[m.i];
      var vis = curiosidades && (!regiao || c.regiao === regiao);
      m.el.style.display = vis ? "" : "none";
      m.el.setAttribute("class", "apoio-curio-pt" + (m.i === curioAtual ? " atual" : ""));
    });
    barra();
    cartao();
    avisarPai();
  }

  function enquadrarCurio() {
    var pts = [];
    curioMarcadores.forEach(function (m) {
      var c = dados.curiosidades[m.i];
      if (!regiao || c.regiao === regiao) pts.push([c.lon, c.lat]);
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
    camadaApoio = true;
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
      var cm = ev.target.closest("[data-camada]");
      if (cm) return alternarCamada(cm.getAttribute("data-camada"));
      var rg = ev.target.closest("[data-regiao]");
      if (rg) {
        regiao = rg.getAttribute("data-regiao");
        curioAtual = -1;
        marcar();
        return enquadrarCurio();
      }
      var ci = ev.target.closest("[data-ci]");
      if (ci && raiz.contains(ci)) return abrirCurio(parseInt(ci.getAttribute("data-ci"), 10));
      var b = ev.target.closest("[data-i]");
      if (b && raiz.contains(b)) return ir(parseInt(b.getAttribute("data-i"), 10));
      var z = ev.target.closest("[data-zoom]");
      if (!z) return;
      var a = z.getAttribute("data-zoom");
      if (a === "mais") zoomEm(0.65);
      else if (a === "menos") zoomEm(1 / 0.65);
      else verTudo();
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

    // arrastar para mover o mapa
    var arrasto = null;
    svgEl.addEventListener("pointerdown", function (ev) {
      if (ev.target.closest(".apoio-marcador, .apoio-curio-pt")) return;
      arrasto = { x: ev.clientX, y: ev.clientY, vx: vb.x, vy: vb.y };
      svgEl.setPointerCapture(ev.pointerId);
      svgEl.classList.add("arrastando");
    });
    svgEl.addEventListener("pointermove", function (ev) {
      if (!arrasto) return;
      var k = vb.w / svgEl.clientWidth;
      vb.x = arrasto.vx - (ev.clientX - arrasto.x) * k;
      vb.y = arrasto.vy - (ev.clientY - arrasto.y) * k;
      aplicar();
    });
    function soltar() {
      arrasto = null;
      svgEl.classList.remove("arrastando");
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
      (embutido
        ? ""
        : '<div class="apoio-ctrl">' +
          '<button type="button" class="btn secundario" data-zoom="mais" aria-label="Ampliar">+</button>' +
          '<button type="button" class="btn secundario" data-zoom="menos" aria-label="Reduzir">−</button>' +
          '<button type="button" class="btn secundario" data-zoom="tudo">Ver tudo</button>' +
          "</div>") +
      '<div id="apoio-svg"></div>' +
      '<div class="apoio-cartao" id="apoio-cartao" aria-live="polite" hidden></div>' +
      "</div>" +
      "";
    document.getElementById("apoio-svg").appendChild(svgEl);
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
