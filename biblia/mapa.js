(function () {
  "use strict";

  var KEY_MAPA = "biblia-mapa"; // { padrao: id do mapa escolhido, pos: { id do mapa: "livro/cap" } }
  var raiz = document.getElementById("mapa");
  var mapas = [];
  var eras = {};
  var nomes = {};

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

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function referencia(tr) {
    var b = nomes[tr.livro];
    if (tr.de === 1 && tr.ate === b.n) return b.nome;
    return b.nome + " " + tr.de + (tr.ate > tr.de ? "–" + tr.ate : "");
  }

  function totalCaps(m) {
    var n = 0;
    m.etapas.forEach(function (e) {
      e.trechos.forEach(function (t) { n += t.ate - t.de + 1; });
    });
    return n;
  }

  function render() {
    var estado = ler(KEY_MAPA, {});
    var padrao = estado.padrao;
    var lista = mapas.slice().sort(function (a, b) {
      return (a.id === padrao ? 0 : 1) - (b.id === padrao ? 0 : 1);
    });
    var aberto = null;
    mapas.forEach(function (m) { if (location.hash === "#" + m.id) aberto = m; });
    var h = aberto ? '<p class="mapa-voltar hud"><a href="#">← Planos</a></p>' : "";
    lista.forEach(function (m) {
      if (aberto && m !== aberto) return;
      var escolhido = m.id === padrao;
      var guardado = estado.pos && estado.pos[m.id];
      var g = guardado && /^([a-z0-9]+)\/(\d+)$/.exec(guardado);
      var primeiro = m.etapas[0].trechos[0];
      h += '<article class="mapa-card' + (escolhido ? " escolhido" : "") + (aberto ? "" : " abrivel") + '"' +
        (aberto ? "" : ' data-abrir="' + esc(m.id) + '" tabindex="0" role="link" aria-label="Abrir ' + esc(m.nome) + '"') + ">" +
        '<h2 class="item-nome">' + esc(m.nome) + (escolhido ? ' <span class="hud faint">· seu plano padrão</span>' : "") + "</h2>" +
        '<p class="muted">' + esc(m.resumo) + "</p>" +
        '<p class="hud faint">' + m.etapas.length + " épocas · " + totalCaps(m) + " capítulos</p>" +
        '<p class="mapa-acoes">' +
        '<a class="chip" href="ler.html?mapa=' + esc(m.id) + (g && nomes[g[1]] ? "" : "#" + primeiro.livro + "/" + primeiro.de) + '">' +
        (g && nomes[g[1]] ? "Continuar a Bíblia · " + esc(nomes[g[1]].nome) + " " + g[2] : "Ler a Bíblia") + "</a> " +
        (g ? '<a class="chip" href="ler.html?mapa=' + esc(m.id) + "#" + primeiro.livro + "/" + primeiro.de + '">Do início</a> ' : "") +
        '<button type="button" class="chip" data-padrao="' + esc(m.id) + '" aria-pressed="' + escolhido + '">' +
        (escolhido ? "✓ Meu plano padrão" : "Definir como meu plano") + "</button></p></article>";
    });

    var ativo = aberto;
    if (!ativo) {
      raiz.innerHTML = h;
      return;
    }
    h += '<div class="mapa-ordem"><p class="l-secao hud">Ordem do ' + esc(ativo.nome.toLowerCase()) + "</p>";
    ativo.etapas.forEach(function (et) {
      var era = eras[et.era] || { nome: et.era };
      h += '<section class="mapa-era"><header><h3>' + esc(era.nome) + '</h3><span class="hud faint">' + esc(era.periodo || "") + "</span></header>";
      if (era.resumo) h += '<p class="muted mapa-resumo">' + esc(era.resumo) + "</p>";
      if (!et.trechos.length) h += '<p class="hud faint mapa-vazio">Sem livros do cânon protestante neste período.</p>';
      h += '<ol class="mapa-trechos">';
      et.trechos.forEach(function (tr) {
        h += '<li><a href="ler.html?mapa=' + esc(ativo.id) + "#" + tr.livro + "/" + tr.de + '">' + esc(referencia(tr)) + "</a>" +
          (tr.nota ? '<span class="hud faint">' + esc(tr.nota) + "</span>" : "") + "</li>";
      });
      h += "</ol></section>";
    });
    h += "</div>";
    raiz.innerHTML = h;
  }

  function abrir(id) {
    location.hash = id;
    window.scrollTo(0, 0);
  }

  raiz.addEventListener("click", function (ev) {
    var t = ev.target.closest && ev.target.closest("[data-padrao]");
    if (!t) {
      var card = ev.target.closest && ev.target.closest("[data-abrir]");
      if (card && !ev.target.closest("a")) abrir(card.getAttribute("data-abrir"));
      return;
    }
    var estado = ler(KEY_MAPA, {});
    var id = t.getAttribute("data-padrao");
    estado.padrao = estado.padrao === id ? null : id;
    gravar(KEY_MAPA, estado);
    render();
  });

  raiz.addEventListener("keydown", function (ev) {
    var card = ev.target.getAttribute && ev.target.hasAttribute("data-abrir") ? ev.target : null;
    if (card && (ev.key === "Enter" || ev.key === " ")) {
      ev.preventDefault();
      abrir(card.getAttribute("data-abrir"));
    }
  });

  window.addEventListener("hashchange", function () {
    if (mapas.length) render();
  });

  Promise.all([
    fetch("dados/mapas.json").then(function (r) { return r.json(); }),
    fetch("dados/eras.json").then(function (r) { return r.json(); }),
    fetch("dados/canon.json").then(function (r) { return r.json(); })
  ]).then(function (r) {
    mapas = r[0].mapas;
    r[1].eras.forEach(function (e) { eras[e.id] = e; });
    r[2].forEach(function (b) { nomes[b.id] = { nome: b.nome, n: b.v.length }; });
    render();
  }, function () {
    raiz.innerHTML = '<p class="vazio">Não consegui carregar o plano. Abra por um servidor local (<code>python -m http.server</code>).</p>';
  });
})();
