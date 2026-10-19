// Projeção Equal Earth (Šavrič, Patterson e Jenny, 2018): preserva as áreas. Usada pelo mapa de uma história
// (mapa/mapa.js) e pelo mapa geral (mapa-geral/mapa-geral.js). Expõe window.Projecao.
//   var p = Projecao.criar(3600, 80, -58);   // largura do SVG, latitude do topo, latitude da base
//   p.proj(lon, lat)       -> [x, y] em unidades do SVG (x de -180° a 180°, y do topo à base)
//   p.inversa(x, y)        -> [lon, lat]
//   p.largura, p.altura    -> tamanho do mapa inteiro
//   Projecao.pontos(f, lista, sep) -> "x,y x,y ..." (uma casa decimal) com f([lon, lat]) -> [x, y]; sep padrão " "
(function () {
  "use strict";

  var A1 = 1.340264;
  var A2 = -0.081106;
  var A3 = 0.000893;
  var A4 = 0.003796;
  var M = Math.sqrt(3) / 2;
  var RAD = Math.PI / 180;

  // lon/lat em graus -> [x, y] da esfera unitária (x para leste, y para o norte)
  function equalEarth(lon, lat) {
    var l = lon * RAD;
    var t = Math.asin(M * Math.sin(lat * RAD));
    var t2 = t * t;
    var t6 = t2 * t2 * t2;
    var x = (2 * Math.sqrt(3) * l * Math.cos(t)) / (3 * (A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2)));
    var y = t * (A1 + A2 * t2 + t6 * (A3 + A4 * t2));
    return [x, y];
  }

  // [x, y] da esfera unitária -> lon/lat em graus (Newton sobre o ângulo auxiliar)
  function inversa(x, y) {
    var t = y / A1;
    for (var i = 0; i < 20; i++) {
      var t2 = t * t;
      var t6 = t2 * t2 * t2;
      var f = t * (A1 + A2 * t2 + t6 * (A3 + A4 * t2)) - y;
      t -= f / (A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2));
    }
    var u2 = t * t;
    var u6 = u2 * u2 * u2;
    var lon = (3 * x * (A1 + 3 * A2 * u2 + u6 * (7 * A3 + 9 * A4 * u2))) / (2 * Math.sqrt(3) * Math.cos(t));
    return [lon / RAD, Math.asin(Math.sin(t) / M) / RAD];
  }

  var XMAX = equalEarth(180, 0)[0];

  function criar(largura, latTopo, latBase) {
    var k = largura / (2 * XMAX);
    var yTopo = equalEarth(0, latTopo)[1];
    return {
      largura: largura,
      altura: (yTopo - equalEarth(0, latBase)[1]) * k,
      proj: function (lon, lat) {
        var q = equalEarth(lon, lat);
        return [(q[0] + XMAX) * k, (yTopo - q[1]) * k];
      },
      inversa: function (px, py) {
        return inversa(px / k - XMAX, yTopo - py / k);
      }
    };
  }

  // pontos [lon, lat] em texto para o SVG: "points" de polygon/polyline, ou sep "L" para o "d" de um path
  function pontos(f, lista, sep) {
    return lista
      .map(function (p) {
        var q = f(p);
        return q[0].toFixed(1) + "," + q[1].toFixed(1);
      })
      .join(sep || " ");
  }

  window.Projecao = { equalEarth: equalEarth, inversa: inversa, criar: criar, XMAX: XMAX, pontos: pontos };
})();
