(function () {
  "use strict";

  var raiz = document.getElementById("guia");
  var embutido = /[?&]embutido/.test(location.search); // aberto no popup do leitor
  var cap = parseInt((/[?&]cap=(\d+)/.exec(location.search) || [])[1], 10) || 0;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function atual(x) {
    return cap && x.de != null && cap >= x.de && cap <= x.ate;
  }

  function ref(d, x) {
    if (embutido || x.de == null) return esc(x.ref);
    return '<a href="ler.html#' + d.livro + "/" + x.de + '">' + esc(x.ref) + "</a>";
  }

  function render(d) {
    var h = "";
    if (d.intro) h += '<p class="guia-intro muted">' + esc(d.intro) + "</p>";
    d.secoes.forEach(function (s) {
      h += '<section class="guia-secao' + (atual(s) ? " atual" : "") + '">' +
        '<p class="hud faint">' + ref(d, s) + "</p><h2>" + esc(s.titulo) + "</h2>";
      if (s.texto) h += "<p>" + esc(s.texto) + "</p>";
      if (s.itens) {
        h += '<ul class="guia-itens">';
        s.itens.forEach(function (it) {
          h += '<li class="' + (atual(it) ? "atual" : "") + '"><span>' + esc(it.titulo) + '</span><span class="hud faint">' + ref(d, it) + "</span></li>";
        });
        h += "</ul>";
      }
      h += "</section>";
    });
    raiz.innerHTML = h;
    var primeiro = raiz.querySelector(".guia-secao.atual");
    if (primeiro && primeiro.scrollIntoView) primeiro.scrollIntoView({ block: "start" });
  }

  var qual = /[?&]m=([a-z0-9-]+)/.exec(location.search);
  fetch("dados/guia-" + (qual ? qual[1] : "") + ".json")
    .then(function (r) {
      if (!r.ok) throw new Error("http " + r.status);
      return r.json();
    })
    .then(function (d) {
      document.getElementById("guia-titulo").innerHTML = esc(d.titulo) + " <em>" + esc(d.destaque) + "</em>";
      document.getElementById("guia-sub").textContent = d.subtitulo;
      document.title = d.titulo + " " + d.destaque.replace(/\.$/, "") + " — Mapa da Bíblia";
      render(d);
    })
    .catch(function () {
      raiz.innerHTML = '<p class="vazio hud faint">Não foi possível carregar o material. Abra por um servidor local (python -m http.server).</p>';
    });
})();
