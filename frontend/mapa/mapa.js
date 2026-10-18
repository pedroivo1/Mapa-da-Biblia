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
  var etapasLigadas = []; // por etapa: a rota aparece no mapa? (vem do capítulo ligado)
  var capitulos = []; // capítulos das etapas, em ordem
  var capLigado = {}; // capítulo -> aparece no mapa? (sem ?cap=, todos ligados)

  function svg(tag, attrs, pai) {
    var el = document.createElementNS(NS, tag);
    for (var k in attrs) if (attrs.hasOwnProperty(k)) el.setAttribute(k, attrs[k]);
    if (pai) pai.appendChild(el);
    return el;
  }

  // projeções: "mercator" ou "equal-earth" (Equal Earth está em compartilhado/js/projecao.js)
  function merc(lat) {
    return Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
  }

  var projEE = null; // Projecao.criar do mapa aberto (mesma largura e latitudes), guardada entre chamadas

  function equalEarthDe(m) {
    if (!projEE || projEE.largura !== m.largura || projEE.lat1 !== m.lat[1] || projEE.lat0 !== m.lat[0]) {
      projEE = Projecao.criar(m.largura, m.lat[1], m.lat[0]);
      projEE.lat1 = m.lat[1];
      projEE.lat0 = m.lat[0];
    }
    return projEE;
  }

  // [x, y] no SVG, com x de lon[0] a lon[1] e y de lat[1] (topo) a lat[0] (base)
  function proj(p) {
    var m = dados.mapa;
    if (m.proj === "equal-earth") return equalEarthDe(m).proj(p[0], p[1]);
    var km = m.largura / (2 * Math.PI);
    return [((p[0] - m.lon[0]) * Math.PI / 180) * km, (merc(m.lat[1]) - merc(p[1])) * km];
  }

  // altura do mapa inteiro
  function alturaDoMapa(m) {
    if (m.proj === "equal-earth") return equalEarthDe(m).altura;
    return (merc(m.lat[1]) - merc(m.lat[0])) * m.largura / (2 * Math.PI);
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
    clearTimeout(vistaTimer);
    vistaTimer = setTimeout(gravarVista, 600);
    var k = vb.w / (svgEl.clientWidth || L);
    redesenharRotas(k);
    escalaveis.forEach(function (e) {
      e.el.setAttribute("transform", "translate(" + e.x.toFixed(1) + " " + e.y.toFixed(1) + ") scale(" + k.toFixed(4) + ")");
    });
    filtrarLugares();
  }

  /* rotas lado a lado: trechos que seguem o mesmo caminho ganham faixas paralelas, em pixels de tela */

  var MAX_SETAS = 24; // setas reservadas por rota
  var ESPACO_SETAS = 130; // pixels entre setas
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
      // uma seta a cada ~ESPACO_SETAS pixels do caminho: mais setas ao ampliar, menos ao afastar
      var nSetas = limitar(Math.round(acum / k / ESPACO_SETAS), 1, MAX_SETAS);
      g.setas.forEach(function (st, q) {
        st.el.style.visibility = q < nSetas ? "" : "hidden";
        if (q >= nSetas) return;
        var alvo = (acum * (q + 1)) / (nSetas + 1);
        var i = 1;
        for (var w = 1; w < R.length - 1; w++) if (Math.abs(D[w] - alvo) < Math.abs(D[i] - alvo)) i = w;
        var ang = (Math.atan2(R[i + 1][1] - R[i - 1][1], R[i + 1][0] - R[i - 1][0]) * 180) / Math.PI;
        st.ent.x = R[i][0];
        st.ent.y = R[i][1];
        st.seta.setAttribute("transform", "rotate(" + ang.toFixed(1) + ")");
      });
    });
  }

  // com o mapa afastado, só os lugares mais citados cabem; ao ampliar, os outros aparecem
  function filtrarLugares() {
    var k = svgEl.clientWidth / vb.w;
    var h = vb.w * razao();
    var ocupados = [];
    var ordem = lugaresNoMapa.slice().sort(function (a, b) {
      // nomes de regiões têm preferência sobre os de cidades quando o espaço é curto
      return (b.poli ? 1 : 0) - (a.poli ? 1 : 0) || b.etapas.length - a.etapas.length || a.ordem - b.ordem;
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
    var filtrado = capitulos.some(function (c) { return !capLigado[c]; });
    // o material pode escolher o enquadramento de abertura (vale com todos os capítulos)
    if (dados.vista && !filtrado) pts = dados.vista;
    else
      dados.etapas.forEach(function (e, i) {
        if (!filtrado || etapasLigadas[i]) pts = pts.concat(pontosDaEtapa(e));
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

  /* territórios do mapa geral (geral-<ano>.json) no ano do mapa */

  var PALETA_PROVINCIAS = ["#d9a21e", "#6fa05a", "#3b82c4", "#a05cd0", "#c0652d", "#14a58a"];
  // cor fixa de cada território ou província (a mesma em qualquer mapa e em qualquer ano)
  var CORES_REGIAO = {
    egito: "#d9a21e", cuxe: "#b5753c", sumer: "#2563eb", babilonia: "#2563eb", assiria: "#7c3aed", elao: "#0ea5e9",
    hititas: "#6b7280", aram: "#3b82c4", "aram-hara": "#38bdf8", canaa: "#84cc16", "israel-unido": "#f97316",
    israel: "#f97316", juda: "#14a58a", filistia: "#c0652d", fenicia: "#a855f7", moabe: "#8b5cf6", amom: "#d23a4a",
    edom: "#d946ef", seir: "#d946ef", midia: "#b45309", basa: "#2e9e5b",
    media: "#65a30d", persia: "#7e22ce", samaria: "#c2410c",
    macedonia: "#3b82c4", acaia: "#d23a4a", asia: "#2e9e5b", galacia: "#8b5cf6", cilicia: "#e08a1e", chipre: "#14a58a"
  };

  function corRegiao(id) {
    if (CORES_REGIAO[id]) return CORES_REGIAO[id];
    var h = 0;
    for (var i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) % 9973;
    return PALETA_PROVINCIAS[h % PALETA_PROVINCIAS.length];
  }
  var provincias = []; // [{nome, aneis (no SVG), polys, texto, cor}] das desenhadas
  var provSel = null;

  function citada(pr) {
    return dados.lugares.some(function (lg) { return lg.provincia && (lg.provincia === true ? lg.id : lg.provincia) === pr.id; });
  }

  function listaTerritorios() {
    return dados.terr ? dados.terr.lista : null;
  }

  // estados do mapa geral no ano do mapa (geral-<ano>.json, gerado por scripts/mapa/geral.py); um caminho por estado,
  // com os furos vazados. Os "tracejado" são regiões citadas no livro que o mapa geral não tem naquele ano.
  function desenharTerritorios() {
    var g = svg("g", { "class": "mapa-roma" }, svgEl);
    (listaTerritorios() || []).forEach(function (pr) {
      if (citada(pr)) return; // a região destacada já desenha este contorno
      var d = pr.aneis.map(function (a) { return "M" + pontos(a).replace(/ /g, "L") + "Z"; }).join("");
      var polys = [svg("path", { "class": "mapa-provincia territorio" + (pr.tracejado ? " tracejado" : ""), d: d, "fill-rule": "evenodd" }, g)];
      var q = pr.rotulo ? proj(pr.rotulo) : null;
      var t = svg("text", { "class": "mapa-provincia-nome", "text-anchor": "middle" }, svgEl);
      t.textContent = pr.nome;
      t.style.display = "none";
      if (q) escalaveis.push({ el: t, x: q[0], y: q[1] });
      provincias.push({
        id: pr.id, nome: pr.nome, polys: polys, texto: t, cor: corRegiao(pr.id),
        aneis: pr.aneis.map(function (a) { return a.map(proj); }), citada: false
      });
    });
  }

  // toque numa província não citada: ela ganha cor própria e nome; outro toque (ou no mar) desfaz
  function marcarProvincia(pr) {
    if (provSel) {
      provSel.polys.forEach(function (el) {
        el.classList.remove("ativa");
        el.style.fill = "";
      });
      provSel.texto.style.display = "none";
    }
    provSel = pr && pr !== provSel ? pr : null;
    if (provSel) {
      provSel.polys.forEach(function (el) {
        el.classList.add("ativa");
        el.style.fill = provSel.cor;
      });
      provSel.texto.style.display = "";
    }
  }

  function provinciaSob(x, y) {
    var achada = null;
    provincias.forEach(function (pr) {
      if (achada || pr.citada) return;
      for (var i = 0; i < pr.aneis.length; i++) {
        if (dentro(x, y, pr.aneis[i])) {
          achada = pr;
          return;
        }
      }
    });
    return achada;
  }

  /* desenho do mapa */

  function desenhar() {
    var m = dados.mapa;
    L = m.largura;
    A = alturaDoMapa(m);
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
        if (dados.rios !== false) svg("polyline", { "class": "mapa-rio", points: pontos(f.pontos), fill: "none" }, base);
      }
    });

    if (dados.terr) desenharTerritorios();

    // base simples: sem os nomes do mundo.json ("rotulosBase": true no JSON do mapa os traz de volta);
    // os rios aparecem ("rios": false os esconde)
    (dados.rotulosBase ? dados.rotulos : []).forEach(function (r) {
      var q = proj([r.lon, r.lat]);
      var t = svg("text", { "class": "mapa-rotulo " + r.tipo, "text-anchor": "middle" }, svgEl);
      t.textContent = r.texto;
      escalaveis.push({ el: t, x: q[0], y: q[1] });
    });


    // regiões (terra, povo ou reino, não uma cidade): área colorida sobre o mapa, sob as rotas
    // região que é uma província romana usa o contorno de roma.json, para os dois desenhos baterem
    if (dados.terr) {
      var todas = listaTerritorios() || [];
      dados.lugares.forEach(function (lg) {
        if (!lg.provincia || lg.area) return;
        var pr = todas.filter(function (x) { return x.id === (lg.provincia === true ? lg.id : lg.provincia); })[0];
        if (!pr || !pr.aneis.length) return;
        var com = pr.aneis.filter(function (a) { return dentro(lg.lon, lg.lat, a); })[0];
        lg.tracejado = !!pr.tracejado;
        lg.area = com || pr.aneis.slice().sort(function (x, y) { return y.length - x.length; })[0];
        // as outras partes da província (ilhas) também ficam destacadas
        lg.extras = lg.soAnel ? [] : pr.aneis.filter(function (a) { return a !== lg.area; });
      });
    }
    var areas = {};
    dados.lugares.forEach(function (lg) {
      if (!lg.area) return;
      var cor = (lg.provincia && CORES_REGIAO[lg.provincia === true ? lg.id : lg.provincia]) || lg.cor || "#e0348c";
      // a região e as outras partes dela (ilhas) num só caminho; os furos (lagos) ficam vazados
      var d = [lg.area].concat(lg.extras || []).map(function (a) { return "M" + pontos(a).replace(/ /g, "L") + "Z"; }).join("");
      areas[lg.id] = svg("path", {
        "class": "mapa-regiao" + (lg.incerto ? " incerto" : "") + (!lg.provincia || lg.tracejado ? " tracejada" : ""),
        d: d,
        "fill-rule": "evenodd",
        fill: cor,
        stroke: cor
      }, svgEl);
    });

    // rotas tracejadas, com setas de direção (a quantidade acompanha o zoom)
    dados.etapas.forEach(function (e) {
      if (!e.caminho || e.caminho.length < 2) {
        rotas.push(null);
        return;
      }
      var grupo = svg("g", { "class": "mapa-rota" }, svgEl);
      var poli = svg("polyline", { points: pontos(e.caminho), fill: "none" }, grupo);
      // reserva de setas; a quantidade que aparece depende do tamanho do caminho na tela (redesenharRotas)
      var setas = [];
      for (var q = 0; q < MAX_SETAS; q++) {
        var m = svg("g", {}, svgEl);
        var seta = svg("path", { "class": "mapa-seta", d: "M-6,-5 L6,0 L-6,5 Z" }, m);
        var ent = { el: m, x: 0, y: 0 };
        escalaveis.push(ent);
        setas.push({ seta: seta, ent: ent, el: m });
      }
      geo[rotas.length] = { pts: e.caminho.map(proj), poli: poli, setas: setas };
      grupo.setas = setas;
      rotas.push(grupo);
    });

    calcularFaixas();

    // um ponto por lugar, só com o nome
    var porLugar = {};
    dados.etapas.forEach(function (e, i) {
      (porLugar[e.lugar] = porLugar[e.lugar] || []).push(i);
    });
    // região sem etapa própria (só o território): ganha o nome, sem texto
    dados.lugares.forEach(function (lg) {
      if ((lg.area || lg.sempre) && !porLugar[lg.id]) porLugar[lg.id] = [];
    });
    // região com "corte": além da área, um ponto com nome (onde ficava a corte do faraó, por exemplo)
    Object.keys(porLugar).forEach(function (id) {
      var r = lugares[id];
      if (!r || !r.area || !r.corte) return;
      lugares[id + "-corte"] = { id: id + "-corte", nome: r.corte.nome, lon: r.corte.lon, lat: r.corte.lat, incerto: r.corte.incerto, lado: r.corte.lado };
      porLugar[id + "-corte"] = porLugar[id];
    });
    Object.keys(porLugar).forEach(function (id) {
      var lg = lugares[id];
      var regiao = !!lg.area;
      // região: o nome fica dentro da área (centro, ou "rotulo" quando há outro lugar no meio)
      var q = proj(regiao && lg.rotulo ? lg.rotulo : [lg.lon, lg.lat]);
      var g = svg("g", { "class": "mapa-lugar" }, svgEl);
      if (regiao) {
        var nomeR = svg("text", { "class": "mapa-nome mapa-nome-regiao" + (lg.incerto ? " incerto" : ""), x: 0, y: 4, "text-anchor": "middle" }, g);
        nomeR.textContent = lg.nome;
        nomeR.style.fill = lg.cor || "";
        escalaveis.push({ el: g, x: q[0], y: q[1] });
        lugaresNoMapa.push({ el: g, area: areas[id], poli: lg.area.map(proj), etapas: porLugar[id], x: q[0], y: q[1], nome: lg.nome, esq: false, ordem: lugaresNoMapa.length, ligado: true });
        return;
      }
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

  /* texto do lugar ou da região, ao tocar nele */

  function dentro(x, y, poli) {
    var d = false;
    for (var i = 0, j = poli.length - 1; i < poli.length; j = i++) {
      var a = poli[i];
      var b = poli[j];
      if (a[1] > y !== b[1] > y && x < ((b[0] - a[0]) * (y - a[1])) / (b[1] - a[1]) + a[0]) d = !d;
    }
    return d;
  }

  // (x, y) em unidades do mapa; k = unidades por pixel (o ponto e o nome têm tamanho fixo na tela)
  function lugarSob(x, y, k) {
    var achado = null;
    var perto = 22 * k;
    lugaresNoMapa.forEach(function (p) {
      if (!p.ligado || p.poli || p.baixa) return;
      var alvoX = p.esq ? p.x - 30 * k : p.x + 30 * k;
      if (Math.abs(x - p.x) < perto && Math.abs(y - p.y) < perto) achado = achado || p;
      else if (Math.abs(x - alvoX) < 40 * k && Math.abs(y - p.y) < 9 * k) achado = achado || p;
    });
    if (achado) return achado;
    lugaresNoMapa.forEach(function (p) {
      if (p.ligado && p.poli && !achado && dentro(x, y, p.poli)) achado = p;
    });
    return achado;
  }

  var cartao = null;
  function mostrarLugar(p) {
    var quadro = document.querySelector(".mapa-quadro");
    if (!quadro) return;
    if (!cartao) {
      cartao = document.createElement("div");
      cartao.className = "mapa-cartao";
      cartao.setAttribute("role", "status");
      cartao.addEventListener("click", function (ev) {
        if (ev.target.closest("[data-fechar]")) cartao.hidden = true;
      });
      quadro.appendChild(cartao);
    }
    if (!p) {
      cartao.hidden = true;
      return;
    }
    var h = '<button type="button" class="mapa-cartao-fechar" data-fechar aria-label="Fechar">×</button>';
    var ligadas = p.etapas.filter(function (i) { return etapasLigadas[i]; });
    (ligadas.length ? ligadas : p.etapas).forEach(function (i) {
      var e = dados.etapas[i];
      if (!e || !e.texto) return;
      h += '<h2>' + esc(e.titulo) + (e.ref ? ' <span class="hud faint">' + esc(e.ref) + "</span>" : "") + "</h2><p>" + esc(e.texto) + "</p>";
    });
    if (h.indexOf("<h2>") < 0) {
      cartao.hidden = true;
      return;
    }
    cartao.innerHTML = h;
    cartao.hidden = false;
    cartao.scrollTop = 0;
  }

  /* lista de capítulos (caixas de seleção) */

  // a lista é por capítulo: cada um liga ou desliga as rotas e os lugares dele
  function construirBarra() {
    var h = '<details class="mapa-grupo" data-grupo="mapa"><summary>' +
      '<input type="checkbox" data-mestre="mapa" aria-label="Mostrar ou esconder todos os capítulos">' +
      '<span class="mapa-grupo-nome">Capítulos</span><span class="hud faint" data-contagem="mapa"></span></summary><div class="mapa-itens">';
    capitulos.forEach(function (c) {
      h += '<label class="mapa-item"><input type="checkbox" data-cap="' + c + '"><span>Capítulo ' + c + "</span></label>";
    });
    h += "</div></details>";
    var barra = document.getElementById("mapa-barra");
    barra.innerHTML = h;
    barra.hidden = capitulos.length < 2;
  }

  // põe cada caixa no estado certo (marcada, desmarcada ou "alguns") e atualiza a contagem
  function sincronizarBarra() {
    var barraEl = document.getElementById("mapa-barra");
    var n = 0;
    capitulos.forEach(function (c) {
      if (capLigado[c]) n++;
      var cx = barraEl.querySelector('[data-cap="' + c + '"]');
      if (cx) cx.checked = !!capLigado[c];
    });
    var total = capitulos.length;
    var mestre = barraEl.querySelector('[data-mestre="mapa"]');
    if (mestre) {
      mestre.checked = total > 0 && n === total;
      mestre.indeterminate = n > 0 && n < total;
    }
    var ca = barraEl.querySelector('[data-contagem="mapa"]');
    if (ca) ca.textContent = n + "/" + total;
  }

  function aplicarCapitulos() {
    dados.etapas.forEach(function (e, i) { etapasLigadas[i] = !!capLigado[e.cap]; });
  }

  function marcar() {
    rotas.forEach(function (r, i) {
      if (!r) return;
      r.style.display = etapasLigadas[i] ? "" : "none";
      r.setas.forEach(function (st) { st.el.style.display = etapasLigadas[i] ? "" : "none"; });
    });
    // cidades e regiões ficam sempre no mapa; o filtro de capítulos liga e desliga só as rotas
    filtrarLugares();
    sincronizarBarra();
  }

  function ligar() {
    var barraEl = document.getElementById("mapa-barra");
    barraEl.addEventListener("change", function (ev) {
      var cx = ev.target;
      if (!cx || cx.type !== "checkbox") return;
      if (cx.hasAttribute("data-mestre")) capitulos.forEach(function (c) { capLigado[c] = cx.checked; });
      else capLigado[cx.getAttribute("data-cap")] = cx.checked;
      aplicarCapitulos();
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
        var rt = svgEl.getBoundingClientRect();
        var kt = vb.w / rt.width;
        var mx = vb.x + (ev.clientX - rt.left) * kt;
        var my = vb.y + (ev.clientY - rt.top) * kt;
        var alvo = lugarSob(mx, my, kt);
        mostrarLugar(alvo);
        // sem lugar sob o toque: a província tocada é marcada; o mar ou outro toque desmarca
        marcarProvincia(alvo ? null : provinciaSob(mx, my));
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
    // capítulos do material; ?cap=N (o capítulo que a pessoa está lendo) abre só com ele
    dados.etapas.forEach(function (e, i) {
      if (rotas[i] && capitulos.indexOf(e.cap) < 0) capitulos.push(e.cap); // só capítulos que têm rota
    });
    capitulos.sort(function (a, b) { return a - b; });
    var pedido = /[?&]cap=(\d+)/.exec(location.search);
    // material cujos capítulos são de um livro só (ex.: Lucas) ignora ?cap= vindo de outro livro
    var deLivro = /[?&]livro=([a-z0-9]+)/.exec(location.search);
    if (pedido && dados.capSomenteLivro && deLivro && deLivro[1] !== dados.capSomenteLivro) pedido = null;
    var so = pedido && capitulos.indexOf(Number(pedido[1])) >= 0 ? Number(pedido[1]) : null;
    capitulos.forEach(function (c) { capLigado[c] = so === null || c === so; });
    aplicarCapitulos();
    construirBarra();
    ligar();
    aplicar();
    marcar();
    vistaInicial();
    restaurarVista();
  }

  // o zoom e a posição em que a pessoa deixou este mapa (por mapa; só quando abre com todos os capítulos)
  var vistaPronta = false;
  var vistaTimer = null;
  function chaveVista() {
    var q = /[?&]m=([a-z0-9-]+)/.exec(location.search);
    return q ? q[1] : "abraao";
  }
  function restaurarVista() {
    var embutidoNoLeitor = /[?&]cap=/.test(location.search);
    (window.Conta ? window.Conta.pronto() : Promise.resolve()).then(function () {
      var todas = window.Conta && window.Conta.lerVista("mapas_vista");
      var v = todas && todas[chaveVista()];
      if (!embutidoNoLeitor && v && v.length === 3 && v[2] > 0) {
        vb.x = v[0];
        vb.y = v[1];
        vb.w = v[2];
        aplicar();
      }
      vistaPronta = true;
    });
  }
  function gravarVista() {
    if (!vistaPronta || !window.Conta || /[?&]cap=/.test(location.search)) return;
    var todas = Object.assign({}, window.Conta.lerVista("mapas_vista") || {});
    todas[chaveVista()] = [Math.round(vb.x), Math.round(vb.y), Math.round(vb.w)];
    window.Conta.guardarVista("mapas_vista", todas);
  }
  window.addEventListener("pagehide", gravarVista);
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") gravarVista();
  });

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
      // "geral" (ano; a.C. positivo, d.C. negativo): territórios do mapa geral nesse ano
      var pedidos = [];
      if (d.geral) pedidos.push(carregar("/mapa/geral-" + d.geral + ".json").then(function (r) { d.terr = { lista: r }; }, function () {}));
      return Promise.all(pedidos).then(function () {
        return d;
      });
    })
    .then(function (d) {
      dados = d;
      var h1 = document.getElementById("mapa-titulo");
      if (h1) h1.innerHTML = esc(d.titulo) + " <em>" + esc(d.destaque) + "</em>";
      var sub = document.getElementById("mapa-sub");
      // o ano do mapa (o dos territórios) vai ao lado da referência do livro
      var ano = d.geral ? " · c. " + (d.geral > 0 ? d.geral + " a.C." : -d.geral + " d.C.") : "";
      if (sub) sub.textContent = d.subtitulo + ano;
      document.title = d.titulo + " " + d.destaque.replace(/\.$/, "") + " — Mapa da Bíblia";
      iniciar();
    })
    .catch(function () {
      raiz.innerHTML =
        '<p class="vazio hud faint">Não foi possível carregar o mapa. Abra por um servidor local (python -m http.server).</p>';
    });
})();