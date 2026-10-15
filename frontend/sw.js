// Service Worker: abre as páginas e os dados na hora, a partir do cache, e atualiza em segundo plano
// (stale-while-revalidate). O nvi.json (3,8 MB) fica guardado e o leitor funciona sem rede.
// Nunca toca em chamadas ao Supabase (login e progresso). Troque VERSAO para descartar o cache antigo.
var VERSAO = "v3";
var CACHE = "biblia-" + VERSAO;
var CDNS = ["cdn.jsdelivr.net", "fonts.googleapis.com", "fonts.gstatic.com"];

self.addEventListener("install", function (ev) {
  // o que é preciso para abrir o leitor sem rede; falha de um item não impede a instalação
  var essenciais = ["/", "/biblia/", "/biblia/nvi.json", "/compartilhado/dados/canon.json", "/compartilhado/css/base.css", "/compartilhado/css/componentes.css"];
  ev.waitUntil(
    caches.open(CACHE).then(function (c) {
      return Promise.all(essenciais.map(function (u) { return c.add(u).catch(function () {}); }));
    }).then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (ev) {
  ev.waitUntil(
    caches.keys().then(function (nomes) {
      return Promise.all(nomes.filter(function (n) { return n.indexOf("biblia-") === 0 && n !== CACHE; }).map(function (n) { return caches.delete(n); }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (ev) {
  var req = ev.request;
  if (req.method !== "GET") return;
  var url = new URL(req.url);
  var mesmaOrigem = url.origin === self.location.origin;
  if (!mesmaOrigem && CDNS.indexOf(url.hostname) < 0) return; // Supabase e o resto passam direto
  if (mesmaOrigem && url.pathname === "/sw.js") return;
  // código de login e retorno do OAuth: sempre da rede
  if (mesmaOrigem && url.pathname.indexOf("/conta/") === 0 && url.search) return;

  ev.respondWith(
    caches.open(CACHE).then(function (c) {
      return c.match(req, { ignoreSearch: false }).then(function (guardado) {
        var rede = fetch(req).then(function (r) {
          if (r && (r.ok || r.type === "opaque")) c.put(req, r.clone());
          return r;
        });
        if (guardado) {
          rede.catch(function () {}); // atualiza em segundo plano
          return guardado;
        }
        return rede.catch(function () {
          return req.mode === "navigate" ? c.match("/biblia/") : Response.error();
        });
      });
    })
  );
});
