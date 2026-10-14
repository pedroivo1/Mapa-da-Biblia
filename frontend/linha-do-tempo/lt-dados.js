// Dados da linha do tempo: junta reis, livros, eras e mapas (preparar) e monta o texto do painel de
// detalhe (corpo). Expõe LT.dados e LT.itens (objetos únicos, preenchidos por carregarDados).
// Parte da linha do tempo (linha-do-tempo/index.html); ligada às outras pelo objeto global LT.
(function () {
  "use strict";

  var LT = (window.LT = window.LT || {});
  var esc = Util.esc;
  var AVALIACAO = LT.AVALIACAO;
  var GRUPO = LT.GRUPO;
  var MARCOS = LT.MARCOS;
  var REINO = LT.REINO;

  var dados = {}; // preenchido por carregarDados(); o objeto é o mesmo para todos os arquivos
  var itens = {};

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

  function preparar(reis, livros, eras, listaMapas) {
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
    reis.potencias.forEach(function (p) {
      (p.periodos || []).forEach(function (q) {
        q.tipo = "periodo";
        q.key = "periodo:" + q.id;
        q.potencia = p;
        lista.push(q);
      });
    });
    var mapas = listaMapas.mapas.filter(function (m) {
      return m.ano != null;
    });
    mapas.sort(function (a, b) {
      return b.ano - a.ano;
    });
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
      mapas: mapas,
      aviso: reis.aviso
    };
  }

  /* ---------- detalhe ---------- */

  function chip(item, extra) {
    return '<button type="button" class="chip" data-abrir="' + esc(item.key) + '">' + esc(item.nome) + (extra || "") + "</button>";
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
      h += '<p class="hud faint">' + esc(item.regime || REINO[item.reino]) + " · " + periodo(item.inicio, item.fim) + " · " + esc(item.duracao) + "</p>";
      if (item.avaliacao) h += '<p class="item-aval ' + item.avaliacao + '">' + AVALIACAO[item.avaliacao] + "</p>";
      h += '<p class="item-nota">' + esc(item.nota) + "</p>";
      h += '<dl class="refs">';
      if (item.refs.reis) h += "<dt>Reis / Samuel</dt><dd>" + esc(item.refs.reis) + "</dd>";
      if (item.refs.cronicas) h += "<dt>Crônicas e outros</dt><dd>" + esc(item.refs.cronicas) + "</dd>";
      if (item.refs.outros) h += "<dt>Leia</dt><dd>" + esc(item.refs.outros) + "</dd>";
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
    } else if (item.tipo === "periodo") {
      h += '<p class="hud faint">' + esc(item.potencia.nome) + " · " + periodo(item.inicio, item.fim) + "</p>";
      h += '<p class="item-nota">' + esc(item.nota) + "</p>";
      h += '<p class="chips">' + chip(item.potencia) + "</p>";
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
    return h;
  }

  function carregarDados(reis, livros, eras, listaMapas) {
    var d = preparar(reis, livros, eras, listaMapas);
    Object.keys(d).forEach(function (k) {
      dados[k] = d[k];
    });
  }

  LT.ano = ano;
  LT.carregarDados = carregarDados;
  LT.chip = chip;
  LT.corpo = corpo;
  LT.dados = dados;
  LT.itens = itens;
  LT.periodo = periodo;
  LT.preparar = preparar;
  LT.rotuloPeriodo = rotuloPeriodo;
})();
