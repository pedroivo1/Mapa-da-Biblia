(function () {
  "use strict";

  var KEY_COL = "biblioteca-colunas";
  // progresso antigo, de quando era salvo só no navegador: sobe para a conta no primeiro login
  var KEY = "biblioteca-lido";
  var KEY_V = "biblioteca-versiculos";
  var NS = "http://www.w3.org/2000/svg";

  // Anos: a.C. positivo, d.C. negativo. Cada trecho tem a sua escala (px por ano).
  var AXIS_INICIO = 2400;
  var AXIS_FIM = -100;
  var SEGMENTOS = [
    { de: 2400, ate: 2200, px: 0.8 },
    { de: 2200, ate: 1450, px: 1.5 },
    { de: 1450, ate: 1051, px: 2 },
    { de: 1051, ate: 420, px: 5 },
    { de: 420, ate: 63, px: 1.5 },
    { de: 63, ate: -100, px: 5 }
  ];
  var ESCALA = 1.4; // aumenta ou reduz a altura do mapa inteiro
  var TOP = 12;
  var ALTURA = TOP * 2;
  SEGMENTOS.forEach(function (s) {
    s.px *= ESCALA;
    s.off = ALTURA - TOP * 2;
    ALTURA += (s.de - s.ate) * s.px;
  });

  var REINO = { unido: "Reino unido", juda: "Judá", israel: "Israel", ambos: "Judá e Israel", nenhum: "—" };
  var AVALIACAO = { bom: "Fez o que era reto", mau: "Fez o que era mau", misto: "Misto" };
  var GRUPO = {
    lei: "Lei",
    historia: "Histórico",
    poesia: "Poético e sapiencial",
    evangelho: "Evangelho",
    atos: "Histórico (NT)",
    carta: "Carta",
    apocalipse: "Apocalíptico"
  };

  function ler(chave, padrao) {
    try {
      return JSON.parse(localStorage.getItem(chave) || "null") || padrao;
    } catch (e) {
      return padrao;
    }
  }
  function gravar(chave, valor) {
    try {
      localStorage.setItem(chave, JSON.stringify(valor));
    } catch (e) {}
  }

  var lido = {};
  var colunas = ler(KEY_COL, { livros: true, reis: true, potencias: true });
  var leitura = {}; // { livro: { capitulo: [versículos] | 1 (todos) } }
  var Conta = window.Conta;
  var conectado = false; // só marca leitura com login e progresso carregado
  var usuarioCarregado = null;
  var canon = [];
  var canonPorItem = {};
  var canonPorId = {};
  var dados = null;
  var itens = {};
  var raiz = document.getElementById("vista");
  var painel = null;

  function urlEntrar() {
    return Conta ? Conta.urlEntrar() : "../entrar.html";
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function ano(a) {
    return a > 0 ? a + " a.C." : -a + " d.C.";
  }
  function periodo(i, f) {
    if (i === f) return ano(i);
    if (i > 0 && f > 0) return i + "–" + f + " a.C.";
    if (i < 0 && f < 0) return -i + "–" + -f + " d.C.";
    return ano(i) + " – " + ano(f);
  }
  function rotuloPeriodo(item) {
    return item.periodo || periodo(item.inicio, item.fim);
  }

  /* ---------- dados ---------- */

  function preparar(reis, livros, eras) {
    var lista = [];
    function reg(arr, tipo) {
      arr.forEach(function (i) {
        i.tipo = tipo;
        i.key = tipo + ":" + i.id;
        lista.push(i);
      });
    }
    reg(reis.reis, "rei");
    reg(reis.profetas, "profeta");
    reg(reis.potencias, "potencia");
    reg(livros.livros, "livro");
    reg(livros.lideres, "lider");
    reg(eras.eras, "era");
    MARCOS.forEach(function (m) {
      m.tipo = "marco";
      m.key = "marco:" + m.ano;
      lista.push(m);
    });
    lista.forEach(function (i) {
      itens[i.key] = i;
    });

    // profetas contemporâneos de cada rei (sobreposição de datas ou citação no livro)
    var porRei = {};
    reis.profetas.forEach(function (p) {
      var ids = {};
      (p.citados || []).forEach(function (id) {
        ids[id] = true;
      });
      reis.reis.forEach(function (r) {
        var ok = p.reino === "ambos" ? r.reino === "juda" || r.reino === "israel" : r.reino === p.reino;
        if (ok && r.inicio > p.fim && r.fim < p.inicio) ids[r.id] = true;
      });
      p.reisIds = Object.keys(ids);
      p.reisIds.forEach(function (id) {
        (porRei[id] = porRei[id] || []).push(p);
      });
    });
    reis.reis.forEach(function (r) {
      r.profetas = porRei[r.id] || [];
    });

    return {
      reis: reis.reis,
      profetas: reis.profetas,
      potencias: reis.potencias,
      livros: livros.livros,
      lideres: livros.lideres,
      eras: eras.eras,
      aviso: reis.aviso
    };
  }

  /* ---------- detalhe ---------- */

  function chip(item, extra) {
    return '<button type="button" class="chip" data-abrir="' + esc(item.key) + '">' + esc(item.nome) + (extra || "") + "</button>";
  }

  function lidoBox(item) {
    if (!conectado) {
      return '<p class="lido-box"><a href="' + esc(urlEntrar()) + '">Entre</a> para marcar como lido.</p>';
    }
    return (
      '<label class="lido-box"><input type="checkbox" data-lido="' + esc(item.key) + '"' +
      (lido[item.key] ? " checked" : "") + "> Lido</label>"
    );
  }

  function corpo(item) {
    if (item.tipo === "marco") {
      return '<h3 class="item-nome">' + esc(item.nome) + "</h3>" +
        '<p class="hud faint">' + ano(item.ano) + "</p>" +
        '<p class="item-nota">' + esc(item.texto) + "</p>" +
        '<dl class="refs"><dt>Leia</dt><dd>' + esc(item.ref) + "</dd></dl>";
    }
    var h = '<h3 class="item-nome">' + esc(item.nome) + "</h3>";
    if (item.tipo === "rei") {
      h += '<p class="hud faint">' + esc(REINO[item.reino]) + " · " + periodo(item.inicio, item.fim) + " · " + esc(item.duracao) + "</p>";
      if (item.avaliacao) h += '<p class="item-aval ' + item.avaliacao + '">' + AVALIACAO[item.avaliacao] + "</p>";
      h += '<p class="item-nota">' + esc(item.nota) + "</p>";
      h += '<dl class="refs">';
      if (item.refs.reis) h += "<dt>Reis / Samuel</dt><dd>" + esc(item.refs.reis) + "</dd>";
      if (item.refs.cronicas) h += "<dt>Crônicas e outros</dt><dd>" + esc(item.refs.cronicas) + "</dd>";
      h += "</dl>";
      if (item.profetas.length) {
        h += '<p class="hud muted">Profetas na época (★ citado no livro)</p><p class="chips">';
        h += item.profetas.map(function (p) {
          return chip(p, (p.citados || []).indexOf(item.id) >= 0 ? " ★" : "");
        }).join("");
        h += "</p>";
      }
    } else if (item.tipo === "profeta") {
      h += '<p class="hud faint">' + (item.livro ? "Livro: " + esc(item.livro) : "Sem livro próprio") + " · " + periodo(item.inicio, item.fim) + (item.incerta ? " · data incerta" : "") + "</p>";
      h += '<p class="item-nota">' + esc(item.nota) + "</p>";
      h += '<dl class="refs"><dt>Leia</dt><dd>' + item.refs.map(esc).join(" · ") + "</dd><dt>Destino</dt><dd>" + esc(item.destino) + "</dd></dl>";
      var reisDele = dados.reis.filter(function (r) {
        return item.reisIds.indexOf(r.id) >= 0;
      });
      if (reisDele.length) {
        h += '<p class="hud muted">Reis na época (★ citado no livro)</p><p class="chips">';
        h += reisDele.map(function (r) {
          return chip(r, (item.citados || []).indexOf(r.id) >= 0 ? " ★" : "");
        }).join("");
        h += "</p>";
      }
    } else if (item.tipo === "potencia") {
      h += '<p class="hud faint">' + periodo(item.inicio, item.fim) + "</p>";
      h += '<p class="item-nota">' + esc(item.resumo) + "</p>";
      if (item.eventos.length) {
        h += '<ul class="eventos">' + item.eventos.map(function (e) {
          return "<li><strong>" + ano(e.ano) + "</strong> " + esc(e.texto) + ' <span class="faint">' + esc(e.ref) + "</span></li>";
        }).join("") + "</ul>";
      }
    } else if (item.tipo === "livro") {
      h += '<p class="hud faint">' + esc(GRUPO[item.grupo]) + " · " + esc(rotuloPeriodo(item)) + (item.incerta ? " · data incerta" : "") + "</p>";
      h += '<p class="item-nota">' + esc(item.nota) + "</p>";
      h += '<dl class="refs"><dt>Leia</dt><dd>' + esc(item.refs) + "</dd></dl>";
    } else if (item.tipo === "lider") {
      h += '<p class="hud faint">' + esc(rotuloPeriodo(item)) + (item.incerta ? " · datas aproximadas" : "") + "</p>";
      h += '<p class="item-nota">' + esc(item.nota) + "</p>";
      h += '<dl class="refs"><dt>Leia</dt><dd>' + item.refs.map(esc).join(" · ") + "</dd></dl>";
    } else if (item.tipo === "era") {
      h += '<p class="hud faint">' + esc(item.periodo) + "</p>";
      h += '<p class="item-nota">' + esc(item.resumo) + "</p>";
      h += '<p class="chips">' + item.livros.map(function (l) {
        return '<span class="chip estatico">' + esc(l) + "</span>";
      }).join("") + "</p>";
      h += '<p class="item-nota"><strong>Leitura:</strong> ' + esc(item.leitura) + "</p>";
    }
    var b = canonPorItem[item.key];
    if (b) h += '<p><button type="button" class="chip" data-leitura="' + b.id + '">Capítulos e versículos →</button></p>';
    if (item.tipo !== "potencia" && item.tipo !== "lider") h += lidoBox(item);
    return h;
  }

  /* ---------- mapa vertical (SVG) ---------- */

  function svg(tag, attrs) {
    var n = document.createElementNS(NS, tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }

  function Y(a) {
    a = Math.min(Math.max(a, AXIS_FIM), AXIS_INICIO);
    for (var i = 0; i < SEGMENTOS.length; i++) {
      var s = SEGMENTOS[i];
      if (a <= s.de && a >= s.ate) return TOP + s.off + (s.de - a) * s.px;
    }
    return TOP;
  }

  function larg(s) {
    return s.length * 6.2 + 8;
  }

  var MARCOS = [
    { ano: 2166, nome: "Abraão", texto: "Chamado de Abraão (data aproximada). Começa a linhagem dos patriarcas.", ref: "Gn 12:1-4" },
    { ano: 1876, nome: "Egito", texto: "Jacó e a família descem ao Egito, onde José governa.", ref: "Gn 46" },
    { ano: 1446, nome: "Êxodo", texto: "Israel sai do Egito sob Moisés e chega ao Sinai. A data do êxodo é debatida (c. 1446 ou c. 1270 a.C.).", ref: "Êx 12–19" },
    { ano: 1406, nome: "Canaã", texto: "Israel atravessa o Jordão sob Josué e entra em Canaã.", ref: "Js 3–4" },
    { ano: 1051, nome: "Monarquia", texto: "Saul torna-se o primeiro rei de Israel.", ref: "1Sm 9–11" },
    { ano: 931, nome: "Divisão", texto: "O reino se divide: Judá com Roboão e Israel com Jeroboão I.", ref: "1Rs 12" },
    { ano: 722, nome: "Samaria", texto: "A Assíria conquista Samaria e termina o reino do norte.", ref: "2Rs 17" },
    { ano: 586, nome: "Jerusalém", texto: "A Babilônia destrói Jerusalém e o templo; começa o exílio de Judá.", ref: "2Rs 25" },
    { ano: 538, nome: "Ciro", texto: "Decreto de Ciro: os exilados podem voltar a Jerusalém.", ref: "Ed 1" },
    { ano: 167, nome: "Macabeus", texto: "Antíoco IV profana o templo e começa a revolta macabeia.", ref: "Dn 11:31; 1Mc 1–4" },
    { ano: 5, nome: "Jesus", texto: "Nascimento de Jesus (data aproximada, entre 6 e 4 a.C.).", ref: "Mt 1–2; Lc 2" },
    { ano: -30, nome: "Cruz", texto: "Morte e ressurreição de Jesus e Pentecostes (c. 30 d.C.).", ref: "Mt 27–28; At 2" },
    { ano: -70, nome: "Templo", texto: "Tito destrói Jerusalém e o templo.", ref: "Mt 24:1-2" }
  ];

  var COLUNAS = [
    { id: "livros", nome: "Livros", cor: "livro" },
    { id: "reis", nome: "Reis", cor: "juda" },
    { id: "potencias", nome: "Potências", cor: "potencia" }
  ];

  function vistaFaixas() {
    var RULER = 52;
    var BAR = 96;
    var GUT = 52;
    var SUB = { livros: 44, potencias: 88 };
    var MARGEM = 108;
    var H = ALTURA;

    function blocosDe(lista) {
      return lista
        .filter(function (i) {
          return i.inicio > AXIS_FIM && i.fim < AXIS_INICIO;
        })
        .map(function (i) {
          var y1 = Y(i.inicio);
          var y2 = Math.max(Y(i.fim), y1 + 14);
          return { item: i, y1: y1, y2: y2, ocupa: y2 + 2 };
        });
    }
    function empacotar(blocos) {
      var fins = [];
      blocos.sort(function (a, b) {
        return a.y1 - b.y1;
      });
      blocos.forEach(function (b) {
        var r = 0;
        while (r < fins.length && fins[r] > b.y1) r++;
        fins[r] = b.ocupa;
        b.sub = r;
      });
      return fins.length;
    }

    var blocos = {};
    var n = {};
    [["livros", dados.livros], ["potencias", dados.potencias]].forEach(function (c) {
      blocos[c[0]] = blocosDe(c[1].slice());
      n[c[0]] = empacotar(blocos[c[0]]);
    });

    // ajusta as larguras ao espaço disponível, para o mapa caber sem rolagem lateral
    var larguraEra = 116;
    var flex = larguraEra +
      (colunas.livros ? n.livros * SUB.livros : 0) +
      (colunas.reis ? 2 * (BAR + GUT) : 0) +
      (colunas.potencias ? n.potencias * SUB.potencias : 0);
    var disponivel = (raiz.clientWidth || 1100) - 2;
    // a barra de rolagem da página ainda não existe nesta primeira medição
    if (window.innerWidth === document.documentElement.clientWidth) disponivel -= 14;
    if (disponivel < 600) MARGEM = 0;
    else if (disponivel < 900) MARGEM = 56;
    var f = Math.min(3, Math.max(0.3, (disponivel - RULER - MARGEM) / flex));
    BAR = Math.round(BAR * f);
    GUT = Math.round(GUT * f);
    SUB.livros = Math.round(SUB.livros * f);
    SUB.potencias = Math.round(SUB.potencias * f);
    larguraEra = Math.round(larguraEra * f);
    var curto = MARGEM < 100;

    var cols = [];
    var x = RULER;
    function col(id, nome, w) {
      var c = { id: id, nome: nome, x: x, w: w };
      cols.push(c);
      x += w;
      return c;
    }
    var cEra = col("era", "Eras", larguraEra);
    var cLiv = colunas.livros ? col("livros", "Livros", n.livros * SUB.livros) : null;
    var cJuda = colunas.reis ? col("juda", "Judá", BAR + GUT) : null;
    var cIsrael = colunas.reis ? col("israel", "Israel", BAR + GUT) : null;
    var cPot = colunas.potencias ? col("potencias", "Potências", n.potencias * SUB.potencias) : null;
    var W = x + MARGEM;

    var s = svg("svg", {
      width: W,
      height: H,
      viewBox: "0 0 " + W + " " + H,
      role: "img",
      "aria-label": "Linha do tempo bíblica em colunas paralelas, da criação ao fim do Novo Testamento"
    });

    cols.forEach(function (c, i) {
      s.appendChild(svg("rect", { x: c.x, y: 0, width: c.w, height: H, class: "col-fundo " + (i % 2 ? "b" : "a") }));
    });

    // régua
    var marcas = [];
    var a;
    for (a = 2100; a >= 1500; a -= 100) marcas.push(a);
    for (a = 1450; a >= 450; a -= 50) marcas.push(a);
    for (a = 400; a >= 50; a -= 50) marcas.push(a);
    marcas.push(-1, -25, -50, -75);
    marcas.forEach(function (m) {
      var gy = Y(m);
      s.appendChild(svg("line", { x1: RULER - 6, y1: gy, x2: x, y2: gy, class: "grade" }));
      var t = svg("text", { x: RULER - 10, y: gy + 4, class: "regua", "text-anchor": "end" });
      t.textContent = m > 0 ? m : -m + " d.C.";
      s.appendChild(t);
    });
    var sd = svg("text", { x: RULER - 4, y: Y(2300) + 4, class: "regua", "text-anchor": "end" });
    sd.textContent = "sem data";
    s.appendChild(sd);

    function grupo(item, cls) {
      var g = svg("g", {
        class: "barra " + cls + (lido[item.key] ? " lido" : ""),
        "data-abrir": item.key,
        "data-key": item.key,
        role: "button",
        tabindex: 0
      });
      g.setAttribute("aria-label", item.nome + " · " + (item.tipo === "era" ? item.periodo : rotuloPeriodo(item)));
      return g;
    }
    function rect(g, rx, ry, rw, rh) {
      g.appendChild(svg("rect", { x: rx, y: ry, width: rw, height: rh }));
    }
    function texto(g, tx, ty, str, cls, extra) {
      var t = svg("text", Object.assign({ x: tx, y: ty, class: "rot " + (cls || "") }, extra || {}));
      t.textContent = str;
      g.appendChild(t);
      return t;
    }
    // nomes dos blocos: camada HTML por cima do mapa, com position: sticky nativo
    var rotulos = [];
    function rotulo(g, bx, w, y1, y2, nome, quebra) {
      rotulos.push({ x: bx, w: w, y1: y1, h: y2 - y1, nome: nome, quebra: !!quebra, key: g.getAttribute("data-abrir") });
    }

    // eras
    dados.eras.forEach(function (e) {
      var y1 = Y(e.inicio), y2 = Y(e.fim);
      var g = grupo(e, "era");
      rect(g, cEra.x + 3, y1 + 1, cEra.w - 6, y2 - y1 - 2);
      rotulo(g, cEra.x + 3, cEra.w - 6, y1 + 1, y2 - 1, e.nome, true);
      s.appendChild(g);
    });

    // livros e líderes (blocos empacotados)
    function desenhar(lista, c, sub, cls, nomeDe) {
      lista.forEach(function (b) {
        var bx = c.x + b.sub * sub;
        var g = grupo(b.item, cls + (b.item.incerta ? " incerta" : ""));
        rect(g, bx + 2, b.y1, sub - 4, b.y2 - b.y1);
        rotulo(g, bx + 2, sub - 4, b.y1, b.y2, nomeDe(b.item));
        s.appendChild(g);
      });
    }
    if (cLiv) desenhar(blocos.livros, cLiv, SUB.livros, "livro", function (i) { return i.abrev; });

    // potências, com marcos dos eventos
    if (cPot) {
      blocos.potencias.forEach(function (b) {
        var bx = cPot.x + b.sub * SUB.potencias;
        var g = grupo(b.item, "potencia");
        rect(g, bx + 2, b.y1, SUB.potencias - 4, b.y2 - b.y1);
        rotulo(g, bx + 2, SUB.potencias - 4, b.y1, b.y2, b.item.nome);
        s.appendChild(g);
      });
    }

    // reis: barra à esquerda e nomes curtos ao lado
    if (cJuda) {
      var pendentes = { juda: [], israel: [] };
      dados.reis.forEach(function (r) {
        var y1 = Y(r.inicio);
        var y2 = Math.max(Y(r.fim), y1 + 5);
        var h = y2 - y1;
        if (r.reino === "unido") {
          var gu = grupo(r, "rei unido");
          rect(gu, cJuda.x + 3, y1, cIsrael.x + BAR - cJuda.x - 3, h);
          rotulo(gu, cJuda.x + 3, cIsrael.x + BAR - cJuda.x - 3, y1, y2, r.nome);
          s.appendChild(gu);
          return;
        }
        var c = r.reino === "juda" ? cJuda : cIsrael;
        var g = grupo(r, "rei " + r.reino);
        rect(g, c.x + 3, y1, BAR - 3, h);
        if (h >= 16) {
          rotulo(g, c.x + 3, BAR - 3, y1, y2, r.nome);
        }
        else {
          pendentes[r.reino].push({ g: g, r: r, c: c, y1: y1, h: h });
          // faixa de clique mais alta que a barra, que tem só poucos pixels
          g.appendChild(svg("rect", { x: c.x + 3, y: y1 + h / 2 - 7, width: BAR - 3, height: 14, style: "fill:transparent;stroke:none" }));
        }
        s.appendChild(g);
      });
      Object.keys(pendentes).forEach(function (k) {
        var ult = -1e9;
        pendentes[k].sort(function (p, q) {
          return p.y1 - q.y1;
        }).forEach(function (p) {
          var cy = p.y1 + p.h / 2;
          var ly = Math.max(cy + 4, ult + 12);
          ult = ly;
          var bx = p.c.x + BAR;
          p.g.appendChild(svg("polyline", { points: bx + "," + cy + " " + (bx + 4) + "," + cy + " " + (bx + 8) + "," + (ly - 4), class: "guia" }));
          var maxs = Math.max(2, Math.floor((GUT - 6) / 6.2));
          texto(p.g, bx + 10, ly, p.r.nome.length > maxs ? p.r.nome.slice(0, maxs - 1) + "…" : p.r.nome, "fora");
        });
      });
    }

    // marcos (linhas horizontais clicáveis)
    MARCOS.forEach(function (m) {
      var my = Y(m.ano);
      var g = svg("g", { class: "marco-g", "data-abrir": m.key, role: "button", tabindex: 0 });
      g.setAttribute("aria-label", ano(m.ano) + " · " + m.nome);
      g.appendChild(svg("line", { x1: RULER - 6, y1: my, x2: x + 6, y2: my, class: "marco-hit" }));
      g.appendChild(svg("line", { x1: RULER - 6, y1: my, x2: x + 6, y2: my, class: "marco-linha" }));
      if (MARGEM > 0) {
        var t = svg("text", { x: x + 10, y: my + 4, class: "marco-rot" });
        t.textContent = (m.ano > 0 ? m.ano : -m.ano + " d.C.") + (curto ? "" : " · " + m.nome);
        g.appendChild(t);
      }
      s.appendChild(g);
    });

    // contorno do hover: um retângulo fino desenhado por último, para ficar acima de tudo
    var contorno = svg("rect", { class: "contorno", visibility: "hidden" });
    s.appendChild(contorno);
    // blocos muito curtos (menos de 12px, como Acazias, Zinri e Salum): só uma linha de 1px
    var linhaHover = svg("line", { class: "contorno-linha", visibility: "hidden" });
    s.appendChild(linhaHover);
    function esconderHover() {
      contorno.setAttribute("visibility", "hidden");
      linhaHover.setAttribute("visibility", "hidden");
    }

    // cabeçalho das colunas (fixo ao rolar, acompanha a rolagem horizontal)
    var cab = document.createElement("div");
    cab.className = "mapa-cab";
    var cabIn = document.createElement("div");
    cabIn.className = "mapa-cab-in";
    cabIn.style.width = W + "px";
    cols.forEach(function (c) {
      var d = document.createElement("div");
      d.className = "hud c-" + c.id;
      d.style.left = c.x + "px";
      d.style.width = c.w + "px";
      d.textContent = c.nome;
      cabIn.appendChild(d);
    });
    cab.appendChild(cabIn);

    var scroll = document.createElement("div");
    scroll.className = "mapa-scroll";
    var corpoMapa = document.createElement("div");
    corpoMapa.className = "mapa-corpo";
    corpoMapa.style.width = W + "px";
    corpoMapa.style.height = H + "px";
    corpoMapa.appendChild(s);
    rotulos.forEach(function (r) {
      var bloco = document.createElement("div");
      bloco.className = "rot-bloco";
      bloco.style.cssText = "left:" + r.x + "px;top:" + r.y1 + "px;width:" + r.w + "px;height:" + r.h + "px";
      var t = document.createElement("div");
      t.className = "rot-txt" + (r.quebra ? " quebra" : "");
      if (r.h < 22) {
        // bloco baixo: o nome ocupa a altura toda, sem espaço acima
        t.className += " mini";
        t.style.lineHeight = r.h + "px";
      }
      t.textContent = r.nome;
      if (r.key) t.setAttribute("data-abrir", r.key);
      bloco.appendChild(t);
      corpoMapa.appendChild(bloco);
    });
    scroll.appendChild(corpoMapa);
    corpoMapa.addEventListener("mouseover", function (ev) {
      var el = ev.target.closest && ev.target.closest("[data-abrir]");
      var g = null;
      if (el) {
        g = el.tagName.toLowerCase() === "g" ? el : s.querySelector('g.barra[data-abrir="' + el.getAttribute("data-abrir") + '"]');
        if (g && !g.classList.contains("barra")) g = null;
      }
      var r = g && g.querySelector("rect");
      esconderHover();
      if (!r) return;
      var rx = Number(r.getAttribute("x")), ry = Number(r.getAttribute("y"));
      var rw = Number(r.getAttribute("width")), rh = Number(r.getAttribute("height"));
      if (rh < 12) {
        var ly = ry; // no vão que separa este período do anterior
        linhaHover.setAttribute("x1", rx);
        linhaHover.setAttribute("x2", rx + rw);
        linhaHover.setAttribute("y1", ly);
        linhaHover.setAttribute("y2", ly);
        linhaHover.setAttribute("visibility", "visible");
        return;
      }
      contorno.setAttribute("x", rx + 0.5);
      contorno.setAttribute("y", ry + 0.5);
      contorno.setAttribute("width", Math.max(0, rw - 1));
      contorno.setAttribute("height", Math.max(0, rh - 1));
      contorno.setAttribute("visibility", "visible");
    });
    corpoMapa.addEventListener("mouseleave", esconderHover);
    scroll.addEventListener("scroll", function () {
      cabIn.style.transform = "translateX(" + -scroll.scrollLeft + "px)";
    });

    var cont = document.createElement("div");
    var tog = '<div class="colunas hud" role="group" aria-label="Colunas visíveis">';
    COLUNAS.forEach(function (c) {
      tog += '<label><input type="checkbox" data-coluna="' + c.id + '"' + (colunas[c.id] ? " checked" : "") +
        '><span class="amostra c-' + c.cor + '"></span>' + c.nome + "</label>";
    });
    tog += '<button type="button" class="hud btn-leitura" data-leitura="">Marcar leitura</button>';
    tog += "</div>";
    cont.innerHTML = tog;
    var lat = document.createElement("div");
    lat.className = "leitura-lateral";
    lat.innerHTML = '<button type="button" class="hud btn-leitura" data-leitura="">Marcar leitura</button>';
    cont.appendChild(lat);
    cont.appendChild(cab);
    cont.appendChild(scroll);
    painel = document.createElement("section");
    painel.className = "detalhe";
    painel.setAttribute("aria-live", "polite");
    painel.hidden = true;
    cont.appendChild(painel);
    return cont;
  }

  /* ---------- progresso ---------- */

  function contar(prefixo) {
    var total = 0, feitos = 0;
    Object.keys(itens).forEach(function (k) {
      if (k.indexOf(prefixo + ":") === 0) {
        total++;
        if (lido[k]) feitos++;
      }
    });
    return [feitos, total];
  }

  function atualizarProgresso() {
    var livros = 0, caps = 0, totalCaps = 0;
    canon.forEach(function (b) {
      var c = capsCompletos(b);
      caps += c;
      totalCaps += b.v.length;
      if (c === b.v.length) livros++;
    });
    var r = contar("rei"), e = contar("era");
    [
      ["livro", "Livros", livros, canon.length],
      ["capitulo", "Capítulos", caps, totalCaps],
      ["rei", "Reis", r[0], r[1]],
      ["era", "Eras", e[0], e[1]]
    ].forEach(function (p) {
      var bar = document.querySelector('[data-progresso="' + p[0] + '"]');
      if (!bar) return;
      bar.querySelector("progress").max = p[3] || 1;
      bar.querySelector("progress").value = p[2];
      bar.querySelector("span").textContent = p[1] + " " + p[2] + "/" + p[3];
    });
  }

  /* ---------- leitura: capítulos e versículos ---------- */

  function todosVersos(b, c) {
    var a = [];
    for (var i = 1; i <= b.v[c - 1]; i++) a.push(i);
    return a;
  }
  function lidosCap(b, c) {
    var x = leitura[b.id] && leitura[b.id][c];
    if (x === 1) return b.v[c - 1];
    return x ? x.length : 0;
  }
  function versoLido(b, c, v) {
    var x = leitura[b.id] && leitura[b.id][c];
    return x === 1 || (!!x && x.indexOf(v) >= 0);
  }
  function gravarCap(b, c, arr) {
    var m = (leitura[b.id] = leitura[b.id] || {});
    if (arr.length === 0) delete m[c];
    else if (arr.length === b.v[c - 1]) m[c] = 1;
    else m[c] = arr;
    if (!Object.keys(m).length) delete leitura[b.id];
  }
  function setVerso(b, c, v, on) {
    var x = leitura[b.id] && leitura[b.id][c];
    var arr = x === 1 ? todosVersos(b, c) : x ? x.slice() : [];
    var i = arr.indexOf(v);
    if (on && i < 0) {
      arr.push(v);
      arr.sort(function (p, q) {
        return p - q;
      });
    }
    if (!on && i >= 0) arr.splice(i, 1);
    gravarCap(b, c, arr);
  }
  function setCap(b, c, on) {
    gravarCap(b, c, on ? todosVersos(b, c) : []);
  }
  function setLivro(b, on) {
    for (var c = 1; c <= b.v.length; c++) setCap(b, c, on);
  }
  function capsCompletos(b) {
    var n = 0;
    for (var c = 1; c <= b.v.length; c++) if (lidosCap(b, c) === b.v[c - 1]) n++;
    return n;
  }
  function capsComAlgo(b) {
    var n = 0;
    for (var c = 1; c <= b.v.length; c++) if (lidosCap(b, c) > 0) n++;
    return n;
  }
  function livroCompleto(b) {
    return capsCompletos(b) === b.v.length;
  }

  // mantém o mapa e os contadores em dia com o que foi marcado
  function sincronizar(b) {
    var on = livroCompleto(b);
    if (on) lido[b.item] = true;
    else delete lido[b.item];
    salvarProgresso();
    document.querySelectorAll('[data-key="' + b.item + '"]').forEach(function (n) {
      n.classList.toggle("lido", on);
    });
    document.querySelectorAll('input[data-lido="' + b.item + '"]').forEach(function (n) {
      n.checked = on;
    });
    atualizarProgresso();
  }

  var dlg = null;
  var nav = { nivel: "livros", livro: null, cap: null };

  function estado(feitos, total) {
    return feitos === 0 ? "" : feitos === total ? "feito" : "parcial";
  }

  function renderLeitura() {
    var corpoAnt = dlg.querySelector(".leitura-corpo");
    var rolagem = corpoAnt ? corpoAnt.scrollTop : 0;
    var b = nav.livro ? canonPorId[nav.livro] : null;
    var h = '<header class="leitura-topo"><nav class="trilha" aria-label="Onde estou">';
    h += '<button type="button" data-l-ir="livros"' + (nav.nivel === "livros" ? ' aria-current="true"' : "") + ">Livros</button>";
    if (b) h += "<span>›</span><button type=\"button\" data-l-ir=\"caps\"" + (nav.nivel === "caps" ? ' aria-current="true"' : "") + ">" + esc(b.nome) + "</button>";
    if (b && nav.nivel === "versos") h += '<span>›</span><button type="button" aria-current="true">Capítulo ' + nav.cap + "</button>";
    h += '</nav><button type="button" class="fechar-dlg" data-l-fechar aria-label="Fechar">×</button></header>';
    h += '<div class="leitura-corpo">';
    var off = conectado ? "" : " disabled";
    if (!conectado) {
      h += '<p class="l-aviso"><a href="' + esc(urlEntrar()) + '">Entre</a> para marcar sua leitura. Sem login, você só consulta.</p>';
    }

    if (nav.nivel === "livros") {
      [["AT", "Antigo Testamento"], ["NT", "Novo Testamento"]].forEach(function (ta) {
        var lista = canon.filter(function (x) {
          return x.ta === ta[0];
        });
        var feitos = lista.filter(livroCompleto).length;
        h += '<p class="l-secao hud">' + ta[1] + '<span class="faint">' + feitos + "/" + lista.length + "</span></p>";
        lista.forEach(function (x) {
          var c = capsCompletos(x);
          var st = c === x.v.length ? "feito" : capsComAlgo(x) ? "parcial" : "";
          h += '<div class="l-livro ' + st + '">' +
            '<button type="button" class="l-check ' + st + '" data-l-livro-tog="' + x.id + '"' + off + ' aria-label="Marcar ' + esc(x.nome) + ' inteiro" title="Marcar o livro inteiro"></button>' +
            '<button type="button" class="l-nome" data-l-abrir="' + x.id + '">' + esc(x.nome) + "</button>" +
            '<span class="hud faint">' + c + "/" + x.v.length + " cap.</span>" +
            '<progress value="' + c + '" max="' + x.v.length + '"></progress></div>';
        });
      });
    } else if (nav.nivel === "caps") {
      var feitosCaps = capsCompletos(b);
      h += '<div class="l-acoes"><p class="hud muted">' + esc(b.nome) + " · " + feitosCaps + "/" + b.v.length + " capítulos</p>" +
        '<span><button type="button" class="chip" data-l-livro-set="1"' + off + '>Marcar livro inteiro</button> ' +
        '<button type="button" class="chip" data-l-livro-set="0"' + off + '>Limpar</button></span></div>';
      h += '<div class="l-grade">';
      for (var c = 1; c <= b.v.length; c++) {
        var lc = lidosCap(b, c);
        var st = estado(lc, b.v[c - 1]);
        h += '<div class="l-cap ' + st + '"><button type="button" class="l-cap-num" data-l-cap="' + c + '" title="' + lc + "/" + b.v[c - 1] + ' versículos">' + c + "</button>" +
          '<button type="button" class="l-check ' + st + '" data-l-cap-tog="' + c + '"' + off + ' aria-label="Marcar capítulo ' + c + '" title="Marcar o capítulo inteiro"></button></div>';
      }
      h += "</div>";
    } else {
      var n = b.v[nav.cap - 1];
      var lv = lidosCap(b, nav.cap);
      h += '<div class="l-acoes"><p class="hud muted">' + esc(b.nome) + " " + nav.cap + " · " + lv + "/" + n + " versículos</p>" +
        "<span>" +
        '<button type="button" class="chip" data-l-nav="-1"' + (nav.cap <= 1 ? " disabled" : "") + ">← Anterior</button> " +
        '<button type="button" class="chip" data-l-nav="1"' + (nav.cap >= b.v.length ? " disabled" : "") + ">Próximo →</button> " +
        '<button type="button" class="chip" data-l-cap-set="1"' + off + '>Marcar capítulo</button> ' +
        '<button type="button" class="chip" data-l-cap-set="0"' + off + '>Limpar</button></span></div>';
      h += '<div class="l-grade versos">';
      for (var v = 1; v <= n; v++) {
        h += '<button type="button" class="l-verso ' + (versoLido(b, nav.cap, v) ? "feito" : "") + '" data-l-verso="' + v + '"' + off + ' aria-pressed="' + versoLido(b, nav.cap, v) + '">' + v + "</button>";
      }
      h += "</div>";
    }
    h += "</div>";
    dlg.innerHTML = h;
    var corpoNovo = dlg.querySelector(".leitura-corpo");
    if (corpoNovo) corpoNovo.scrollTop = rolagem;
  }

  function abrirLeitura(livroId, cap) {
    if (!canon.length) return;
    if (!dlg) {
      dlg = document.createElement("dialog");
      dlg.className = "leitura";
      dlg.setAttribute("aria-label", "Marcar leitura");
      document.body.appendChild(dlg);
      dlg.addEventListener("click", function (ev) {
        if (ev.target === dlg) return dlg.close();
        var t = ev.target.closest("button");
        if (!t || t.disabled) return;
        var b = nav.livro ? canonPorId[nav.livro] : null;
        var mudou = false;
        if (t.hasAttribute("data-l-fechar")) return dlg.close();
        if (t.hasAttribute("data-l-ir")) {
          nav.nivel = t.getAttribute("data-l-ir");
          if (nav.nivel === "livros") nav.livro = null;
        } else if (t.hasAttribute("data-l-abrir")) {
          nav.livro = t.getAttribute("data-l-abrir");
          nav.nivel = "caps";
          dlg.querySelector(".leitura-corpo").scrollTop = 0;
        } else if (t.hasAttribute("data-l-livro-tog")) {
          var x = canonPorId[t.getAttribute("data-l-livro-tog")];
          setLivro(x, !livroCompleto(x));
          sincronizar(x);
        } else if (t.hasAttribute("data-l-livro-set")) {
          setLivro(b, t.getAttribute("data-l-livro-set") === "1");
          sincronizar(b);
        } else if (t.hasAttribute("data-l-cap")) {
          nav.cap = Number(t.getAttribute("data-l-cap"));
          nav.nivel = "versos";
          dlg.querySelector(".leitura-corpo").scrollTop = 0;
        } else if (t.hasAttribute("data-l-cap-tog")) {
          var c = Number(t.getAttribute("data-l-cap-tog"));
          setCap(b, c, lidosCap(b, c) !== b.v[c - 1]);
          sincronizar(b);
        } else if (t.hasAttribute("data-l-cap-set")) {
          setCap(b, nav.cap, t.getAttribute("data-l-cap-set") === "1");
          sincronizar(b);
        } else if (t.hasAttribute("data-l-nav")) {
          nav.cap += Number(t.getAttribute("data-l-nav"));
          dlg.querySelector(".leitura-corpo").scrollTop = 0;
        } else if (t.hasAttribute("data-l-verso")) {
          var v = Number(t.getAttribute("data-l-verso"));
          setVerso(b, nav.cap, v, !versoLido(b, nav.cap, v));
          sincronizar(b);
        } else return;
        renderLeitura();
      });
    }
    if (livroId && canonPorId[livroId]) {
      nav.livro = livroId;
      nav.cap = cap || null;
      nav.nivel = cap ? "versos" : "caps";
    } else if (!nav.livro) {
      nav.nivel = "livros";
    }
    renderLeitura();
    if (!dlg.open) dlg.showModal();
  }

  /* ---------- eventos ---------- */

  function renderizar() {
    var antigo = raiz.querySelector(".mapa-scroll");
    var esq = antigo ? antigo.scrollLeft : 0;
    larguraAnterior = raiz.clientWidth;
    raiz.innerHTML = "";
    raiz.appendChild(vistaFaixas());
    var novo = raiz.querySelector(".mapa-scroll");
    if (novo && esq) novo.scrollLeft = esq;
    atualizarProgresso();
  }

  function abrir(key) {
    var item = itens[key];
    if (!item || !painel) return;
    painel.innerHTML = '<button type="button" class="fechar" data-fechar aria-label="Fechar">×</button>' + corpo(item);
    painel.dataset.key = key;
    painel.hidden = false;
  }

  function fechar() {
    if (!painel) return;
    painel.hidden = true;
    delete painel.dataset.key;
  }

  document.addEventListener("click", function (ev) {
    var alvo = ev.target.closest && ev.target.closest("[data-abrir]");
    if (alvo) abrir(alvo.getAttribute("data-abrir"));
    else if (ev.target.closest && ev.target.closest("[data-fechar]")) fechar();
    var leit = ev.target.closest && ev.target.closest("[data-leitura]");
    if (leit) abrirLeitura(leit.getAttribute("data-leitura") || null);
  });

  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") fechar();
    if (ev.key !== "Enter" && ev.key !== " ") return;
    var alvo = ev.target.closest && ev.target.closest("g[data-abrir]");
    if (alvo) {
      ev.preventDefault();
      abrir(alvo.getAttribute("data-abrir"));
    }
  });

  document.addEventListener("change", function (ev) {
    var t = ev.target;
    if (t.hasAttribute("data-lido")) {
      if (!conectado) {
        t.checked = !t.checked;
        return;
      }
      var key = t.getAttribute("data-lido");
      var cb = canonPorItem[key];
      if (cb) {
        setLivro(cb, t.checked);
        sincronizar(cb);
        return;
      }
      if (t.checked) lido[key] = true;
      else delete lido[key];
      salvarProgresso();
      document.querySelectorAll('[data-key="' + key + '"]').forEach(function (n) {
        n.classList.toggle("lido", !!lido[key]);
      });
      atualizarProgresso();
    } else if (t.hasAttribute("data-coluna")) {
      colunas[t.getAttribute("data-coluna")] = t.checked;
      gravar(KEY_COL, colunas);
      var aberto = painel && painel.dataset.key;
      renderizar();
      if (aberto) abrir(aberto);
    }
  });

  var temporizador = null;
  var larguraAnterior = 0;
  window.addEventListener("resize", function () {
    clearTimeout(temporizador);
    temporizador = setTimeout(function () {
      if (!dados || raiz.clientWidth === larguraAnterior) return;
      var aberto = painel && !painel.hidden && painel.dataset.key;
      renderizar();
      if (aberto) abrir(aberto);
    }, 150);
  });

  /* ---------- progresso da conta ---------- */

  function salvarProgresso() {
    if (conectado) Conta.salvar(lido, leitura);
  }

  // marcações antigas ("livro lido") viram leitura completa; depois o mapa passa a seguir os capítulos
  function normalizar() {
    canon.forEach(function (b) {
      if (lido[b.item] && !leitura[b.id]) setLivro(b, true);
      if (livroCompleto(b)) lido[b.item] = true;
      else delete lido[b.item];
    });
  }

  // null: sem login. Erro ao ler a conta: fica só para consulta, para não sobrescrever o que está salvo.
  function carregarProgresso() {
    if (!Conta) return Promise.resolve(null);
    return Conta.pronto().then(function (u) {
      return u ? Conta.carregar() : null;
    });
  }

  function aplicarProgresso(p) {
    var u = Conta && Conta.usuario();
    usuarioCarregado = p && u ? u.id : null;
    conectado = !!usuarioCarregado;
    lido = p ? p.lido : {};
    leitura = p ? p.versiculos : {};
    if (!conectado) return;

    var antigoLido = ler(KEY, null);
    var antigoV = ler(KEY_V, null);
    var importar = p.vazio && (antigoLido || antigoV);
    if (importar) {
      lido = antigoLido || {};
      leitura = antigoV || {};
    }
    var antes = JSON.stringify([lido, leitura]);
    normalizar();
    if (importar) {
      Conta.salvarAgora(lido, leitura).then(function () {
        try {
          localStorage.removeItem(KEY);
          localStorage.removeItem(KEY_V);
        } catch (e) {}
      }, function () {});
    } else if (JSON.stringify([lido, leitura]) !== antes) {
      salvarProgresso();
    }
  }

  function falhaProgresso() {
    aplicarProgresso(null);
    renderizar();
    raiz.insertAdjacentHTML(
      "afterbegin",
      '<p class="vazio">Não consegui carregar seu progresso. O mapa está só para consulta; recarregue a página para tentar de novo.</p>'
    );
  }

  // redesenha tudo com o progresso atual, mantendo o painel e o popup abertos
  function atualizarTudo() {
    var aberto = painel && !painel.hidden && painel.dataset.key;
    renderizar();
    if (aberto) abrir(aberto);
    if (dlg && dlg.open) renderLeitura();
  }

  function recarregarProgresso() {
    carregarProgresso().then(function (p) {
      aplicarProgresso(p);
      atualizarTudo();
    }, falhaProgresso);
  }

  if (Conta) {
    Conta.aoMudar(function (evento, u) {
      if (!dados) return;
      var id = u ? u.id : null;
      if (id !== usuarioCarregado) recarregarProgresso();
    });
  }

  // outra aba ou outro aparelho pode ter marcado algo: ao voltar para a página, busca de novo
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState !== "visible" || !conectado || Conta.temPendente()) return;
    recarregarProgresso();
  });

  Promise.all(
    ["reis", "livros", "eras", "canon"].map(function (n) {
      return fetch("dados/" + n + ".json").then(function (r) {
        return r.json();
      });
    })
  )
    .then(
      function (res) {
        dados = preparar(res[0], res[1], res[2]);
        canon = res[3];
        canon.forEach(function (b) {
          canonPorItem[b.item] = b;
          canonPorId[b.id] = b;
        });
        return carregarProgresso().then(function (p) {
          aplicarProgresso(p);
          renderizar();
        }, falhaProgresso);
      },
      function () {
        raiz.innerHTML =
          '<p class="vazio">Não consegui carregar os dados. Abra por um servidor local (<code>python -m http.server</code>); o navegador bloqueia JSON via <code>file://</code>.</p>';
      }
    );
})();
