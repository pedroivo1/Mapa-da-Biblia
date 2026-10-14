// Plano de leitura (plano-de-leitura/index.html): lista os planos de planos.json,
// mostra a ordem de cada um e deixa escolher o plano padrão (exige login; fica em Conta "plano").
(function () {
  "use strict";

  var ler = Util.ler, gravar = Util.gravar, esc = Util.esc;

  var KEY_PLANO = "biblia-mapa"; // { padrao: id do plano escolhido, pos: { id do plano: "livro/cap" } }
  var Conta = window.Conta;
  var raiz = document.getElementById("plano");
  var planos = [];
  var eras = {};
  var nomes = {};


  // o plano padrão é da conta: sem login não há plano padrão
  function logado() {
    return !!(Conta && Conta.usuario());
  }
  function estadoPlano() {
    return (logado() && Conta.config().plano) || ler(KEY_PLANO, {});
  }
  function guardarPlano(v) {
    gravar(KEY_PLANO, v);
    if (logado()) Conta.salvarConfig("plano", v);
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
    var estado = estadoPlano();
    var padrao = logado() ? estado.padrao : null;
    var lista = planos.slice().sort(function (a, b) {
      return (a.id === padrao ? 0 : 1) - (b.id === padrao ? 0 : 1);
    });
    var aberto = null;
    planos.forEach(function (m) { if (location.hash === "#" + m.id) aberto = m; });
    var h = aberto ? '<p class="plano-voltar hud"><a href="#">← Planos</a></p>' : "";
    lista.forEach(function (m) {
      if (aberto && m !== aberto) return;
      var escolhido = m.id === padrao;
      var guardado = estado.pos && estado.pos[m.id];
      var g = guardado && /^([a-z0-9]+)\/(\d+)$/.exec(guardado);
      var primeiro = m.etapas[0].trechos[0];
      h += '<article class="plano-card' + (escolhido ? " escolhido" : "") + (aberto ? "" : " abrivel") + '"' +
        (aberto ? "" : ' data-abrir="' + esc(m.id) + '" tabindex="0" role="link" aria-label="Abrir ' + esc(m.nome) + '"') + ">" +
        '<h2 class="item-nome">' + esc(m.nome) + (escolhido ? ' <span class="hud faint">· seu plano padrão</span>' : "") + "</h2>" +
        '<p class="muted">' + esc(m.resumo) + "</p>" +
        '<p class="hud faint">' + m.etapas.length + " épocas · " + totalCaps(m) + " capítulos</p>" +
        '<p class="plano-acoes">' +
        '<a class="chip" href="/biblia/?plano=' + esc(m.id) + (g && nomes[g[1]] ? "" : "#" + primeiro.livro + "/" + primeiro.de) + '">' +
        (g && nomes[g[1]] ? "Continuar a Bíblia · " + esc(nomes[g[1]].nome) + " " + g[2] : "Ler a Bíblia") + "</a> " +
        (g ? '<a class="chip" href="/biblia/?plano=' + esc(m.id) + "#" + primeiro.livro + "/" + primeiro.de + '">Do início</a> ' : "") +
        (logado()
          ? '<button type="button" class="chip" data-padrao="' + esc(m.id) + '" aria-pressed="' + escolhido + '">' +
            (escolhido ? "✓ Meu plano padrão" : "Definir como meu plano") + "</button>"
          : '<a class="chip" href="' + esc(Conta ? Conta.urlEntrar() : "/conta/") + '">Entre para definir como seu plano</a>') +
        "</p></article>";
    });

    var ativo = aberto;
    if (!ativo) {
      raiz.innerHTML = h;
      return;
    }
    h += '<div class="plano-ordem"><p class="l-secao hud">Ordem do ' + esc(ativo.nome.toLowerCase()) + "</p>";
    ativo.etapas.forEach(function (et) {
      var era = eras[et.era] || { nome: et.era };
      h += '<section class="plano-era"><header><h3>' + esc(era.nome) + '</h3><span class="hud faint">' + esc(era.periodo || "") + "</span></header>";
      if (era.resumo) h += '<p class="muted plano-resumo">' + esc(era.resumo) + "</p>";
      if (!et.trechos.length) h += '<p class="hud faint plano-vazio">Sem livros do cânon protestante neste período.</p>';
      h += '<ol class="plano-trechos">';
      et.trechos.forEach(function (tr) {
        h += '<li><a href="/biblia/?plano=' + esc(ativo.id) + "#" + tr.livro + "/" + tr.de + '">' + esc(referencia(tr)) + "</a>" +
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
    if (!logado()) return;
    var estado = estadoPlano();
    var id = t.getAttribute("data-padrao");
    estado.padrao = estado.padrao === id ? null : id;
    guardarPlano(estado);
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
    if (planos.length) render();
  });

  Promise.all([
    fetch("/plano-de-leitura/planos.json").then(function (r) { return r.json(); }),
    fetch("/compartilhado/dados/eras.json").then(function (r) { return r.json(); }),
    fetch("/compartilhado/dados/canon.json").then(function (r) { return r.json(); })
  ]).then(function (r) {
    planos = r[0].planos;
    r[1].eras.forEach(function (e) { eras[e.id] = e; });
    r[2].forEach(function (b) { nomes[b.id] = { nome: b.nome, n: b.v.length }; });
    // com a sessão (rápida) a cópia guardada da conta já aparece; o servidor atualiza depois
    return (Conta ? Conta.pronto() : Promise.resolve()).then(function () {
      render();
      if (Conta) {
        Conta.aoConfig(function () { render(); });
        Conta.aoMudar(function (ev, u, mudou) { if (mudou) render(); });
      }
    });
  }).catch(function () {
    raiz.innerHTML = '<p class="vazio">Não consegui carregar o plano. Abra por um servidor local (<code>python -m http.server</code>).</p>';
  });
})();
