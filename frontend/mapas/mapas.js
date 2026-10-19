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
        var q = /[?&]m=([a-z0-9-]+)/.exec(m.url);
        var previa = "/mapas/previas/" + (q ? q[1] : "abraao");
        h += '<li class="mapas-item"><a class="mapas-card" href="' + esc(m.url) + '">' +
          '<img class="previa-claro" src="' + previa + '-claro.webp" alt="" loading="lazy" width="720" height="450" />' +
          '<img class="previa-escuro" src="' + previa + '-escuro.webp" alt="" loading="lazy" width="720" height="450" />' +
          '<span class="mapas-card-texto"><span class="mapas-card-titulo">' + esc(m.titulo) + "</span>" +
          '<span class="hud faint">' + esc(m.ref) + "</span></span></a></li>";
      });
      h += "</ul></section>";
    });
    raiz.innerHTML = h || '<p class="vazio hud faint">Ainda não há mapas.</p>';
  }

  Promise.all([
    Util.json("/mapas/mapas.json"),
    Util.json("/compartilhado/dados/canon.json")
  ]).then(function (r) {
    render(r[0].mapas, r[1]);
  }, function () {
    Util.falha(raiz, "os mapas", "hud faint");
  });
})();
