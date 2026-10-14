// Linha do tempo (linha-do-tempo/index.html): colunas paralelas com o tempo na vertical.
// Lê reis.json e livros.json (aqui), eras.json (compartilhado) e mapas.json (slice mapas). Ordem dos scripts: lt-config, lt-filtros, lt-dados,
// lt-eixo e este; eles se ligam pelo objeto global LT. Aqui: vistaFaixas() (layout e desenho),
// renderizar(), abrir() (painel de detalhe), abrirMapa() (popup) e os manipuladores de eventos.
(function () {
  "use strict";

  var LT = (window.LT = window.LT || {});
  var Conta = window.Conta;
  var ALTURA = LT.ALTURA;
  var AXIS_FIM = LT.AXIS_FIM;
  var AXIS_INICIO = LT.AXIS_INICIO;
  var COLUNAS = LT.COLUNAS;
  var MARCOS = LT.MARCOS;
  var MODOS = LT.MODOS;
  var REGUA_Y = LT.REGUA_Y;
  var REINO = LT.REINO;
  var Y = LT.Y;
  var ano = LT.ano;
  var carregarDados = LT.carregarDados;
  var colunas = LT.colunas;
  var corpo = LT.corpo;
  var dados = LT.dados;
  var grupoDe = LT.grupoDe;
  var grupoLigado = LT.grupoLigado;
  var gruposAtuais = LT.gruposAtuais;
  var guardarColunas = LT.guardarColunas;
  var guardarPerfisLocal = LT.guardarPerfisLocal;
  var itens = LT.itens;
  var livrosAtivos = LT.livrosAtivos;
  var mexeu = LT.mexeu;
  var periodo = LT.periodo;
  var recarregarFiltros = LT.recarregarFiltros;
  var reguaAtiva = LT.reguaAtiva;
  var reguaDeRolagem = LT.reguaDeRolagem;
  var rolarSuave = LT.rolarSuave;
  var rotuloPeriodo = LT.rotuloPeriodo;
  var svg = LT.svg;
  var telaMudou = LT.telaMudou;
  var trocarPerfil = LT.trocarPerfil;

  var raiz = document.getElementById("vista");
  var painel = null;

  function vistaFaixas() {
    var RULER = 0; // sem coluna de anos à esquerda: a régua de rolagem, à direita, mostra as datas
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
    var livrosVisiveis = dados.livros.filter(function (l) {
      return grupoLigado(grupoDe(l));
    });
    [["livros", livrosVisiveis], ["potencias", dados.potencias]].forEach(function (c) {
      blocos[c[0]] = blocosDe(c[1].slice());
      n[c[0]] = empacotar(blocos[c[0]]);
    });

    // ajusta as larguras ao espaço disponível, para o mapa caber sem rolagem lateral
    var larguraEra = 116;
    var flex = (colunas.eras ? larguraEra : 0) +
      (livrosAtivos() ? n.livros * SUB.livros : 0) +
      (colunas.reis ? 2 * (BAR + GUT) : 0) +
      (colunas.potencias ? n.potencias * SUB.potencias : 0);
    // a régua de rolagem fica ao lado do mapa e tira a sua largura do espaço
    var disponivel = (raiz.clientWidth || 1100) - 2 - (reguaAtiva() ? REGUA_Y : 0);
    // a margem dos rótulos de marcos encolhe aos poucos abaixo de 1200px, até sumir em 700px
    MARGEM = Math.floor(108 * Math.max(0, Math.min(1, (disponivel - 626) / 500)));
    var f = Math.min(3, Math.max(0.3, (disponivel - RULER - MARGEM) / flex));
    // a coluna das eras não precisa crescer com a tela: passa de ERA_MAX, o resto vai para as outras
    var ERA_MAX = 150;
    var eraFixa = false;
    function ajustarEra() {
      var so = colunas.eras ? larguraEra : 0;
      eraFixa = so > 0 && flex > so && so * f > ERA_MAX;
      if (eraFixa) f = Math.min(3, Math.max(0.3, (disponivel - RULER - MARGEM - ERA_MAX) / (flex - so)));
    }
    ajustarEra();
    // faixas largas o bastante para o nome inteiro dos livros, se o resto das colunas aguentar o aperto
    var medidor = document.createElement("canvas").getContext("2d");
    medidor.font = "500 " + (window.innerWidth <= 720 ? 10 : 11) + "px Archivo, sans-serif";
    var MARGEM_NOME = 14; // bloco (4), margens internas (6) e folga
    if (livrosAtivos() && n.livros) {
      var larguras = [];
      livrosVisiveis.forEach(function (l) {
        if (l.nome) larguras.push(Math.ceil(medidor.measureText(l.nome).width));
      });
      larguras.sort(function (a, b) {
        return a - b;
      });
      var flexAntes = flex, fAntes = f, subAntes = SUB.livros, eraAntes = eraFixa;
      // tenta caber o maior nome; se apertar demais as outras colunas, o do percentil 85, e assim por diante
      [1, 0.85, 0.7, 0.55].some(function (q) {
        if (!larguras.length) return true;
        var subLargo = larguras[Math.min(larguras.length - 1, Math.floor(larguras.length * q))] + MARGEM_NOME;
        if (q === 1) subLargo = larguras[larguras.length - 1] + MARGEM_NOME;
        if (subAntes * fAntes >= subLargo) return true; // já cabe sem mexer
        flex = flexAntes + n.livros * (subLargo - subAntes);
        SUB.livros = subLargo;
        f = Math.min(3, (disponivel - RULER - MARGEM) / flex);
        eraFixa = eraAntes;
        ajustarEra();
        if (f >= 0.75) return true;
        flex = flexAntes;
        f = fAntes;
        SUB.livros = subAntes;
        eraFixa = eraAntes;
        return false;
      });
    }
    // arredonda para baixo: arredondar para cima pode estourar a largura e criar rolagem lateral
    BAR = Math.floor(BAR * f);
    GUT = Math.floor(GUT * f);
    SUB.livros = Math.floor(SUB.livros * f);
    SUB.potencias = Math.floor(SUB.potencias * f);
    larguraEra = eraFixa ? ERA_MAX : Math.floor(larguraEra * f);
    var curto = MARGEM < 100;

    var cols = [];
    var x = RULER;
    function col(id, nome, w) {
      var c = { id: id, nome: nome, x: x, w: w };
      cols.push(c);
      x += w;
      return c;
    }
    var cEra = colunas.eras ? col("era", "Eras", larguraEra) : null;
    var cLiv = livrosAtivos() ? col("livros", "Livros", n.livros * SUB.livros) : null;
    // Judá e Israel dividem uma só coluna, a Terra prometida, em duas faixas lado a lado
    var cTerra = colunas.reis ? col("terra", "Terra prometida", 2 * (BAR + GUT)) : null;
    var cJuda = cTerra ? { x: cTerra.x } : null;
    var cIsrael = cTerra ? { x: cTerra.x + BAR + GUT } : null;
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

    // linhas verticais entre as colunas, de ponta a ponta, e entre as faixas de Judá e Israel
    cols.forEach(function (c) {
      s.appendChild(svg("line", { x1: c.x + 0.5, y1: 0, x2: c.x + 0.5, y2: H, class: "col-sep" }));
    });
    if (cols.length) {
      var ultima = cols[cols.length - 1];
      s.appendChild(svg("line", { x1: ultima.x + ultima.w - 0.5, y1: 0, x2: ultima.x + ultima.w - 0.5, y2: H, class: "col-sep" }));
    }
    if (cIsrael) {
      s.appendChild(svg("line", { x1: cIsrael.x + 0.5, y1: 0, x2: cIsrael.x + 0.5, y2: H, class: "col-sep sub" }));
    }

    // linhas de grade, nos anos redondos
    var marcas = [];
    var a;
    for (a = 2100; a >= 1500; a -= 100) marcas.push(a);
    for (a = 1450; a >= 450; a -= 50) marcas.push(a);
    for (a = 400; a >= 50; a -= 50) marcas.push(a);
    marcas.push(-1, -25, -50, -75);
    marcas.forEach(function (m) {
      var gy = Y(m);
      s.appendChild(svg("line", { x1: RULER, y1: gy, x2: x, y2: gy, class: "grade" }));
    });

    function grupo(item, cls) {
      var g = svg("g", {
        class: "barra " + cls,
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
    function rotulo(g, bx, w, y1, y2, nome, quebra, sub) {
      rotulos.push({ x: bx, w: w, y1: y1, h: y2 - y1, nome: nome, sub: sub, quebra: !!quebra, key: g.getAttribute("data-abrir") });
    }

    // eras
    (cEra ? dados.eras : []).forEach(function (e) {
      var y1 = Y(e.inicio), y2 = Y(e.fim);
      var g = grupo(e, "era");
      rect(g, cEra.x + 3, y1 + 1, cEra.w - 6, y2 - y1 - 2);
      rotulo(g, cEra.x + 3, cEra.w - 6, y1 + 1, y2 - 1, e.nome, true);
      s.appendChild(g);
    });

    // pontos dos mapas, na coluna das eras
    var pontosMapa = [];
    if (cEra) {
      dados.mapas.forEach(function (m) {
        pontosMapa.push({ m: m, x: cEra.x + cEra.w - 15, y: Y(m.ano) });
      });
    }

    // livros e líderes (blocos empacotados)
    function desenhar(lista, c, sub, cls, nomeDe) {
      lista.forEach(function (b) {
        var bx = c.x + b.sub * sub;
        var g = grupo(b.item, cls + (b.item.grupo ? " g-" + grupoDe(b.item) : "") + (b.item.incerta ? " incerta" : ""));
        rect(g, bx + 2, b.y1, sub - 4, b.y2 - b.y1);
        rotulo(g, bx + 2, sub - 4, b.y1, b.y2, nomeDe(b.item));
        s.appendChild(g);
      });
    }
    // com espaço na coluna, o nome inteiro do livro; sem espaço, a abreviação
    var larguraDoNome = SUB.livros - MARGEM_NOME;
    if (cLiv) {
      desenhar(blocos.livros, cLiv, SUB.livros, "livro", function (i) {
        return i.nome && medidor.measureText(i.nome).width <= larguraDoNome ? i.nome : i.abrev;
      });
    }

    // potências, com marcos dos eventos
    if (cPot) {
      blocos.potencias.forEach(function (b) {
        var bx = cPot.x + b.sub * SUB.potencias;
        var g = grupo(b.item, "potencia");
        rect(g, bx + 2, b.y1, SUB.potencias - 4, b.y2 - b.y1);
        var periodos = b.item.periodos || [];
        if (!periodos.length) {
          rotulo(g, bx + 2, SUB.potencias - 4, b.y1, b.y2, b.item.nome);
          s.appendChild(g);
          return;
        }
        s.appendChild(g);
        // um bloco só: cada período leva o nome da potência e, abaixo, o seu próprio nome
        var ate = b.item.inicio;
        periodos.forEach(function (q) {
          // vão entre períodos: fica só o nome da potência
          if (q.inicio < ate) rotulo(g, bx + 2, SUB.potencias - 4, Y(ate), Y(q.inicio), b.item.nome, true);
          ate = q.fim;
          var qy1 = Y(q.inicio);
          var qy2 = Math.max(Y(q.fim), qy1 + 8);
          var gq = grupo(q, "periodo");
          rect(gq, bx + 2, qy1, SUB.potencias - 4, qy2 - qy1);
          if (q.inicio !== b.item.inicio) gq.appendChild(svg("line", { x1: bx + 2, y1: qy1, x2: bx + SUB.potencias - 2, y2: qy1, class: "divisor" }));
          var baixo = qy2 - qy1 < 30;
          rotulo(gq, bx + 2, SUB.potencias - 4, qy1, qy2, baixo ? q.nome : b.item.nome, true, baixo ? null : q.nome);
          s.appendChild(gq);
        });
      });
    }

    // reis: barra à esquerda e nomes curtos ao lado
    if (cJuda) {
      var pendentes = { juda: [], israel: [] };
      // depois da queda de Israel a faixa do norte fica vazia: os nomes de Judá podem avançar por ela
      var fimIsrael = 1e9;
      dados.reis.forEach(function (r) {
        if (r.reino === "israel" && r.fim < fimIsrael) fimIsrael = r.fim;
      });
      dados.reis.forEach(function (r) {
        var y1 = Y(r.inicio);
        var y2 = Math.max(Y(r.fim), y1 + 5);
        var h = y2 - y1;
        if (r.reino === "unido") {
          var gu = grupo(r, "rei unido");
          var duasU = h >= 30;
          rect(gu, cJuda.x + 3, y1, cIsrael.x + BAR - cJuda.x - 3, h);
          // o reino unido também se chama Israel: "Israel" em cima e o rei embaixo
          rotulo(gu, cJuda.x + 3, cIsrael.x + BAR - cJuda.x - 3, y1, y2, duasU ? "Israel" : r.nome, duasU, duasU ? r.nome : null);
          s.appendChild(gu);
          return;
        }
        var c = r.reino === "juda" ? cJuda : cIsrael;
        var g = grupo(r, "rei " + r.reino + (r.cor ? " " + r.cor : ""));
        rect(g, c.x + 3, y1, BAR - 3, h);
        if (h >= 16) {
          // o reino em cima e o rei embaixo, como nas potências (Judá / Roboão)
          var duas = h >= 30;
          rotulo(g, c.x + 3, BAR - 3, y1, y2, duas ? r.regime || REINO[r.reino] : r.nome, duas, duas ? r.nome : null);
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
          var livre = p.r.reino === "juda" && p.r.inicio <= fimIsrael;
          var maxs = Math.max(2, Math.floor((livre ? BAR + 2 * GUT - 14 : GUT - 6) / 6.2));
          var nomeCurto = livre ? p.r.nome : p.r.curto || p.r.nome;
          texto(p.g, bx + 10, ly, nomeCurto.length > maxs ? nomeCurto.slice(0, maxs - 1) + "…" : nomeCurto, "fora");
        });
      });
    }

    // marcos (linhas horizontais clicáveis)
    MARCOS.forEach(function (m) {
      var my = Y(m.ano);
      var g = svg("g", { class: "marco-g", "data-abrir": m.key, role: "button", tabindex: 0 });
      g.setAttribute("aria-label", ano(m.ano) + " · " + m.nome);
      g.appendChild(svg("line", { x1: RULER, y1: my, x2: x + 6, y2: my, class: "marco-hit" }));
      g.appendChild(svg("line", { x1: RULER, y1: my, x2: x + 6, y2: my, class: "marco-linha" }));
      // sem espaço para o ano inteiro, a margem fica só com a marca
      if (MARGEM >= 54) {
        var t = svg("text", { x: x + 10, y: my + 4, class: "marco-rot" });
        if (MARGEM < 70) t.setAttribute("style", "font-size:8px");
        t.textContent = ano(m.ano) + (curto ? "" : " · " + m.nome);
        g.appendChild(t);
      }
      s.appendChild(g);
    });

    // contorno do hover: um retângulo fino desenhado por último, para ficar acima de tudo
    var contorno = svg("rect", { class: "contorno", visibility: "hidden" });
    s.appendChild(contorno);
    // blocos mínimos (5px: reinados de meses, como Zinri e Salum): só uma linha de 1px
    var linhaHover = svg("line", { class: "contorno-linha", visibility: "hidden" });
    s.appendChild(linhaHover);
    function esconderHover() {
      contorno.setAttribute("visibility", "hidden");
      linhaHover.setAttribute("visibility", "hidden");
    }

    // cabeçalho das colunas (fixo ao rolar, acompanha a rolagem horizontal)
    var cab = document.createElement("div");
    cab.className = "lt-cab";
    var cabIn = document.createElement("div");
    cabIn.className = "lt-cab-in";
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
    scroll.className = "lt-scroll";
    var corpoMapa = document.createElement("div");
    corpoMapa.className = "lt-corpo";
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
      if (r.sub) {
        t.style.fontWeight = "600";
        var sub = document.createElement("span");
        sub.className = "rot-sub";
        sub.textContent = r.sub;
        t.appendChild(sub);
      }
      if (r.key) t.setAttribute("data-abrir", r.key);
      bloco.appendChild(t);
      corpoMapa.appendChild(bloco);
    });
    pontosMapa.forEach(function (p) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "era-mapa";
      b.style.left = p.x - 9 + "px";
      b.style.top = p.y - 9 + "px";
      b.setAttribute("data-mapa", p.m.id);
      b.setAttribute("aria-label", "Mapa: " + p.m.titulo + " · " + ano(p.m.ano));
      b.setAttribute("data-dica", p.m.titulo + " · " + ano(p.m.ano));
      corpoMapa.appendChild(b);
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
      if (rh < 6) {
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
      if (c.id === "livros") {
        var gs = gruposAtuais();
        var n = gs.filter(function (g) {
          return grupoLigado(g.id);
        }).length;
        tog += '<details class="filtro"><summary><span class="amostra c-livro"></span>Livros <span class="faint">' +
          n + "/" + gs.length + '</span></summary><div class="filtro-menu"><div class="filtro-modos" role="group" aria-label="Classificação">';
        Object.keys(MODOS).forEach(function (m) {
          tog += '<button type="button" data-modo="' + m + '"' + (colunas.modo === m ? ' aria-pressed="true"' : "") + ">" + MODOS[m].nome + "</button>";
        });
        tog += "</div>";
        tog += '<button type="button" class="filtro-todos" data-todos="' + (n === gs.length ? "0" : "1") + '">' +
          (n === gs.length ? "Desmarcar todos" : "Marcar todos") + "</button>";
        var ta = "";
        gs.forEach(function (g) {
          if (g.ta !== ta) {
            ta = g.ta;
            tog += '<p class="filtro-ta">' + ta + "</p>";
          }
          tog += '<label><input type="checkbox" data-grupo="' + g.id + '"' + (grupoLigado(g.id) ? " checked" : "") +
            '><span class="amostra g-' + g.id + '"></span>' + g.nome + "</label>";
        });
        tog += "</div></details>";
        return;
      }
      tog += '<label><input type="checkbox" data-coluna="' + c.id + '"' + (colunas[c.id] ? " checked" : "") +
        '><span class="amostra c-' + c.cor + '"></span>' + c.nome + "</label>";
    });
    tog += "</div>";
    cont.innerHTML = tog;
    cont.appendChild(cab);
    var vistaMapa = document.createElement("div");
    vistaMapa.className = "lt-vista";
    vistaMapa.appendChild(scroll);
    vistaMapa.appendChild(reguaDeRolagem(scroll));
    cont.appendChild(vistaMapa);
    painel = document.createElement("section");
    painel.className = "detalhe";
    painel.setAttribute("aria-live", "polite");
    painel.hidden = true;
    cont.appendChild(painel);
    return cont;
  }

  /* ---------- eventos ---------- */

  function renderizar() {
    var antigo = raiz.querySelector(".lt-scroll");
    var esq = antigo ? antigo.scrollLeft : 0;
    // refazer a vista zera a rolagem: guarda a posição e devolve depois
    var topo = antigo ? antigo.scrollTop : 0;
    larguraAnterior = raiz.clientWidth;
    reguaAnterior = reguaAtiva();
    raiz.innerHTML = "";
    raiz.appendChild(vistaFaixas());
    var novo = raiz.querySelector(".lt-scroll");
    if (novo) {
      if (esq) novo.scrollLeft = esq;
      if (topo) novo.scrollTop = topo;
    }
    var leg = raiz.querySelector(".colunas");
    if (leg) document.documentElement.style.setProperty("--colunas-h", leg.offsetHeight + "px");
  }

  function abrir(key) {
    var item = itens[key];
    if (!item || !painel) return;
    painel.innerHTML = '<button type="button" class="fechar" data-fechar aria-label="Fechar">×</button>' + corpo(item);
    painel.dataset.key = key;
    painel.hidden = false;
  }

  /* mapa do período, num popup */

  var dlgMapa = null;

  function abrirMapa(id) {
    var m = null;
    dados.mapas.forEach(function (x) {
      if (x.id === id) m = x;
    });
    if (!m) return;
    if (!dlgMapa) {
      dlgMapa = document.createElement("dialog");
      dlgMapa.className = "leitor-dlg leitor-dlg-leitura leitor-dlg-mapas";
      dlgMapa.innerHTML = '<div class="leitor-dlg-topo"><span class="hud muted" data-mapa-info></span><button type="button" data-fechar-mapa>Fechar</button></div><iframe></iframe>';
      dlgMapa.onclick = function (ev) {
        if (ev.target === dlgMapa || ev.target.closest("[data-fechar-mapa]")) dlgMapa.close();
      };
      dlgMapa.addEventListener("close", function () {
        dlgMapa.querySelector("iframe").removeAttribute("src");
      });
      document.body.appendChild(dlgMapa);
    }
    dlgMapa.querySelector("[data-mapa-info]").textContent = m.titulo + " · " + ano(m.ano) + " · " + m.ref;
    var quadro = dlgMapa.querySelector("iframe");
    quadro.setAttribute("title", m.titulo);
    quadro.setAttribute("src", m.url + (m.url.indexOf("?") < 0 ? "?" : "&") + "embutido");
    if (!dlgMapa.open) dlgMapa.showModal();
  }

  function fechar() {
    if (!painel) return;
    painel.hidden = true;
    delete painel.dataset.key;
  }

  document.addEventListener("click", function (ev) {
    var todos = ev.target.closest && ev.target.closest("[data-todos]");
    if (todos) {
      var ligar = todos.getAttribute("data-todos") === "1";
      gruposAtuais().forEach(function (g) {
        colunas.grupos[g.id] = ligar;
      });
      colunas.livros = livrosAtivos();
      guardarColunas();
      var abertoTodos = painel && !painel.hidden && painel.dataset.key;
      renderizar();
      var ft = document.querySelector(".filtro");
      if (ft) ft.open = true;
      if (abertoTodos) abrir(abertoTodos);
      return;
    }
    var modo = ev.target.closest && ev.target.closest("[data-modo]");
    if (modo) {
      colunas.modo = modo.getAttribute("data-modo");
      guardarColunas();
      var painelAberto = painel && !painel.hidden && painel.dataset.key;
      renderizar();
      var fm = document.querySelector(".filtro");
      if (fm) fm.open = true;
      if (painelAberto) abrir(painelAberto);
      return;
    }
    var filtro = document.querySelector(".filtro");
    if (filtro && filtro.open && !ev.target.closest(".filtro")) filtro.open = false;
    var pm = ev.target.closest && ev.target.closest("[data-mapa]");
    if (pm) return abrirMapa(pm.getAttribute("data-mapa"));
    var alvo = ev.target.closest && ev.target.closest("[data-abrir]");
    if (alvo) abrir(alvo.getAttribute("data-abrir"));
    else if (ev.target.closest && ev.target.closest("[data-fechar]")) fechar();
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
    if (t.hasAttribute("data-grupo")) {
      colunas.grupos[t.getAttribute("data-grupo")] = t.checked;
      colunas.livros = livrosAtivos();
      guardarColunas();
      var abertoPainel = painel && !painel.hidden && painel.dataset.key;
      renderizar();
      var f = document.querySelector(".filtro");
      if (f) f.open = true;
      if (abertoPainel) abrir(abertoPainel);
    } else if (t.hasAttribute("data-coluna")) {
      colunas[t.getAttribute("data-coluna")] = t.checked;
      guardarColunas();
      var aberto = painel && painel.dataset.key;
      renderizar();
      if (aberto) abrir(aberto);
    }
  });

  // a página não rola: a roda do mouse em qualquer lugar da tela rola o mapa
  // (menos nos painéis que têm rolagem própria, nos menus e nos popups)
  document.addEventListener(
    "wheel",
    function (ev) {
      if (ev.ctrlKey || ev.metaKey || ev.defaultPrevented) return;
      var rolagem = raiz.querySelector(".lt-scroll");
      if (!rolagem) return;
      if (rolagem.contains(ev.target)) {
        // rolagem nativa do mapa: para a animação para os dois não brigarem
        if (rolagemQuadro !== null) {
          cancelAnimationFrame(rolagemQuadro);
          rolagemQuadro = null;
        }
        return;
      }
      if (ev.target.closest && ev.target.closest(".detalhe, .filtro-menu, dialog, .regua-y")) return;
      var f = ev.deltaMode === 1 ? 16 : ev.deltaMode === 2 ? rolagem.clientHeight : 1;
      rolarSuave(rolagem, ev.deltaY * f);
      ev.preventDefault();
    },
    { passive: false }
  );

  var temporizador = null;
  var larguraAnterior = 0;
  var reguaAnterior = true;
  window.addEventListener("resize", function () {
    clearTimeout(temporizador);
    temporizador = setTimeout(function () {
      if (telaMudou()) trocarPerfil();
      if (!dados.reis || (raiz.clientWidth === larguraAnterior && reguaAtiva() === reguaAnterior)) return;
      var aberto = painel && !painel.hidden && painel.dataset.key;
      renderizar();
      if (aberto) abrir(aberto);
    }, 150);
  });

  Promise.all(
    ["/linha-do-tempo/reis.json", "/linha-do-tempo/livros.json", "/compartilhado/dados/eras.json", "/mapas/mapas.json"].map(function (url) {
      return fetch(url).then(function (r) {
        return r.json();
      });
    })
  ).then(
    function (res) {
      carregarDados(res[0], res[1], res[2], res[3]);
      // com a sessão (rápida) já valem os filtros guardados da conta; o servidor confirma depois
      return (Conta ? Conta.pronto() : Promise.resolve()).then(function () {
        if (!mexeu()) recarregarFiltros();
        renderizar();
        if (!Conta) return;
        Conta.aoConfig(function (cfg) {
          if (mexeu() || !cfg.linha_do_tempo) return;
          var antes = JSON.stringify(colunas);
          recarregarFiltros();
          guardarPerfisLocal();
          if (JSON.stringify(colunas) === antes) return;
          var aberto = painel && !painel.hidden && painel.dataset.key;
          renderizar();
          if (aberto) abrir(aberto);
        });
      });
    },
    function () {
      raiz.innerHTML =
        '<p class="vazio">Não consegui carregar os dados. Abra por um servidor local (<code>python -m http.server</code>); o navegador bloqueia JSON via <code>file://</code>.</p>';
    }
  );
})();
