// Mapas (mapas/index.html): lista, por livro, os mapas de mapas.json.
// Cada mapa abre em mapa/index.html?m=id. Mapa novo entra aqui sozinho, só editando o JSON.
(function () {
  "use strict";

  var esc = Util.esc;

  var raiz = document.getElementById("mapas");

  function render(mapas, canon) {
    var ordem = {};
    var nomes = {};
    canon.forEach(function (b, i) {
      ordem[b.id] = i;
      nomes[b.id] = b.nome;
    });

    // um grupo por livro, na ordem da Bíblia
    var grupos = {};
    mapas.forEach(function (m) {
      var livro = m.capitulos[0].livro;
      (grupos[livro] = grupos[livro] || []).push(m);
    });
    var livros = Object.keys(grupos).sort(function (a, b) { return ordem[a] - ordem[b]; });

    var h = "";
    livros.forEach(function (livro) {
      var lista = grupos[livro];
      h += '<section class="mapas-livro"><header><h2>' + esc(nomes[livro] || livro) + '</h2><span class="hud faint">' +
        lista.length + (lista.length === 1 ? " mapa" : " mapas") + "</span></header><ul>";
      lista.forEach(function (m) {
        h += '<li class="mapas-item"><p class="hud faint">' + esc(m.tipo) + " · " + esc(m.ref) + "</p>" +
          '<h3><a href="' + esc(m.url) + '">' + esc(m.titulo) + "</a></h3>" +
          '<p class="muted">' + esc(m.resumo) + "</p>" +
          '<p class="mapas-acoes"><a class="chip" href="' + esc(m.url) + '">Abrir</a> ' +
          '<a class="chip" href="/biblia/#' + esc(livro) + "/" + m.capitulos[0].de + '">Ler ' + esc(nomes[livro] || livro) + " " + m.capitulos[0].de + "</a></p></li>";
      });
      h += "</ul></section>";
    });
    raiz.innerHTML = h || '<p class="vazio hud faint">Ainda não há mapas.</p>';
  }

  Promise.all([
    fetch("/mapas/mapas.json").then(function (r) { return r.json(); }),
    fetch("/compartilhado/dados/canon.json").then(function (r) { return r.json(); })
  ]).then(function (r) {
    render(r[0].mapas, r[1]);
  }, function () {
    raiz.innerHTML = '<p class="vazio hud faint">Não foi possível carregar os mapas. Abra por um servidor local (python -m http.server).</p>';
  });
})();
