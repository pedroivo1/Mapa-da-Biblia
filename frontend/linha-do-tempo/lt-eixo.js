// Eixo vertical do tempo: Y(ano) e anoDeY(y), rolagem suave e a régua de tempo (reguaDeRolagem).
// Parte da linha do tempo (linha-do-tempo/index.html); ligada às outras pelo objeto global LT.
(function () {
  "use strict";

  var LT = (window.LT = window.LT || {});
  var AXIS_FIM = LT.AXIS_FIM;
  var AXIS_INICIO = LT.AXIS_INICIO;
  var NS = LT.NS;
  var SEGMENTOS = LT.SEGMENTOS;
  var TOP = LT.TOP;
  var ano = LT.ano;

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

  // o início do eixo (Origens, Gn 1–11) não tem data: a régua não conta anos ali
  var SEM_DATA_ATE = SEGMENTOS[0].ate;

  // rolagem suave para a roda do mouse fora do mapa: soma o deslocamento num alvo e anda até ele,
  // em vez de pular de uma vez (o que dava a sensação de rolagem "dura")
  var rolagemAlvo = 0;
  var rolagemQuadro = null;
  function rolarSuave(el, delta) {
    if (rolagemQuadro === null) rolagemAlvo = el.scrollTop;
    rolagemAlvo = Math.max(0, Math.min(el.scrollHeight - el.clientHeight, rolagemAlvo + delta));
    if (rolagemQuadro !== null) return;
    function passo() {
      var d = rolagemAlvo - el.scrollTop;
      if (Math.abs(d) < 1) {
        el.scrollTop = rolagemAlvo;
        rolagemQuadro = null;
        return;
      }
      el.scrollTop += d > 0 ? Math.max(1, d * 0.2) : Math.min(-1, d * 0.2);
      rolagemQuadro = requestAnimationFrame(passo);
    }
    rolagemQuadro = requestAnimationFrame(passo);
  }

  // inverso de Y: o ano que está numa altura do mapa (null no trecho sem data)
  function anoDeY(y) {
    if (y < Y(SEM_DATA_ATE)) return null;
    for (var i = 0; i < SEGMENTOS.length; i++) {
      var s = SEGMENTOS[i];
      var a0 = TOP + s.off;
      var a1 = a0 + (s.de - s.ate) * s.px;
      if (y <= a1) return s.de - Math.max(0, y - a0) / s.px;
    }
    return AXIS_FIM;
  }

  var REGUA_Y = 72; // largura da régua de rolagem, em px

  // no celular (até 720 px) a régua some e o mapa usa a largura toda
  function reguaAtiva() {
    return window.innerWidth > 720;
  }

  function rotuloAno(a) {
    if (a === null) return "sem data";
    a = Math.round(a);
    return a > 0 ? a + " a.C." : a === 0 ? "0" : -a + " d.C.";
  }

  // a barra de rolagem vira uma régua de tempo, dinâmica como a do Artcraft:
  // parada, mostra as datas na escala do mapa, andando junto com ele, com o ano do centro da tela;
  // com o cursor em cima, mostra o mapa inteiro, a janela visível e o ano sob o cursor.
  // As mesmas marcas se movem de uma visão para a outra (p vai de 0 a 1), sem corte.
  function reguaDeRolagem(rolagem) {
    var regua = document.createElement("div");
    regua.className = "regua-y";
    regua.setAttribute("aria-hidden", "true");
    var area = document.createElement("div");
    area.className = "regua-marcas";
    var tr = document.createElement("div");
    tr.className = "regua-tr";
    area.appendChild(tr);
    var janela = document.createElement("div");
    janela.className = "regua-janela";
    var centro = document.createElement("div");
    centro.className = "regua-centro";
    var centroAno = document.createElement("span");
    centro.appendChild(centroAno);
    var guia = document.createElement("div");
    guia.className = "regua-guia";
    guia.hidden = true;
    var guiaAno = document.createElement("span");
    guia.appendChild(guiaAno);
    regua.appendChild(area);
    regua.appendChild(janela);
    regua.appendChild(centro);
    regua.appendChild(guia);

    var LARG = { g: 16, m: 10, p: 5, s: 0 };
    var marcas = []; // { el, rot, y, visL, visG, rotL, rotG, tipoL, tipoG }
    var p = 0; // 0: na escala do mapa; 1: mapa inteiro
    var alvo = 0;
    var quadro = null;
    var aplicado = -1; // última visão pintada por inteiro (0 ou 1)
    var sujo = true;

    function trilha() {
      return { h: rolagem.clientHeight, total: rolagem.scrollHeight };
    }

    function construir() {
      var t = trilha();
      if (!t.h || !t.total) return;
      var k = t.h / t.total;
      tr.innerHTML = "";
      tr.style.height = t.total + "px";
      marcas = [];
      var ultimo = -100;
      // trecho sem data: um rótulo no meio, sem marcas de ano
      var sd = document.createElement("i");
      var sdRot = document.createElement("b");
      sdRot.textContent = "sem data";
      sd.appendChild(sdRot);
      marcas.push({ el: sd, rot: sdRot, y: (TOP + Y(SEM_DATA_ATE)) / 2, visL: 1, visG: 1, rotL: 1, rotG: 1, tipoL: "s", tipoG: "s" });
      tr.appendChild(sd);
      for (var a = SEM_DATA_ATE; a >= AXIS_FIM; a -= 5) {
        var y = Y(a);
        var seculo = a % 100 === 0;
        var el = document.createElement("i");
        var rot = null;
        if (seculo && a !== SEM_DATA_ATE) {
          rot = document.createElement("b");
          rot.textContent = rotuloAno(a);
          el.appendChild(rot);
        }
        var m = {
          el: el,
          rot: rot,
          y: y,
          visL: a % 10 === 0 ? 1 : 0,
          visG: a % 25 === 0 ? 1 : 0,
          rotL: rot ? 1 : 0,
          rotG: 0,
          tipoL: seculo ? "g" : a % 50 === 0 ? "m" : "p",
          tipoG: a % 500 === 0 ? "g" : seculo ? "m" : "p"
        };
        // na visão geral só rotula o século que cabe
        if (rot && (a % 500 === 0 || y * k - ultimo >= 26)) {
          m.rotG = 1;
          ultimo = y * k;
        }
        marcas.push(m);
        tr.appendChild(el);
      }
      sujo = true;
    }

    // põe cada marca entre a posição da escala do mapa e a da visão geral
    function pintar(q, st, k) {
      for (var i = 0; i < marcas.length; i++) {
        var m = marcas[i];
        var y = q === 0 ? m.y : q === 1 ? m.y * k : (m.y - st) * (1 - q) + m.y * k * q;
        var tipo = q < 0.5 ? m.tipoL : m.tipoG;
        var el = m.el;
        el.style.top = y.toFixed(1) + "px";
        el.style.width = LARG[m.tipoL] + (LARG[m.tipoG] - LARG[m.tipoL]) * q + "px";
        el.style.opacity = (m.visL * (1 - q) + m.visG * q).toFixed(2);
        el.className = tipo;
        if (m.rot) m.rot.style.opacity = (m.rotL * (1 - q) + m.rotG * q).toFixed(2);
      }
    }

    function posicionar() {
      var t = trilha();
      if (!t.h || !t.total) return;
      var k = t.h / t.total;
      var st = rolagem.scrollTop;
      var meioDoc = st + t.h / 2;
      if (p === 0) {
        if (aplicado !== 0 || sujo) pintar(0, st, k);
        tr.style.transform = "translateY(" + -st + "px)";
        aplicado = 0;
      } else if (p === 1) {
        if (aplicado !== 1 || sujo) pintar(1, st, k);
        tr.style.transform = "none";
        aplicado = 1;
      } else {
        pintar(p, st, k);
        tr.style.transform = "none";
        aplicado = -1;
      }
      sujo = false;
      janela.style.top = st * k + "px";
      janela.style.height = Math.max(3, t.h * k) + "px";
      janela.style.opacity = p;
      // o ano do centro da tela: parada, a linha fica no meio da régua; na visão geral, acompanha a janela
      centro.style.top = t.h / 2 + (meioDoc * k - t.h / 2) * p + "px";
      centroAno.textContent = rotuloAno(anoDeY(meioDoc));
    }

    function animar() {
      var inicio = p;
      var t0 = null;
      var duracao = 240;
      if (quadro) cancelAnimationFrame(quadro);
      function passo(agora) {
        if (t0 === null) t0 = agora;
        var f = Math.min(1, (agora - t0) / duracao);
        var e = 1 - Math.pow(1 - f, 3);
        p = f >= 1 ? alvo : inicio + (alvo - inicio) * e;
        posicionar();
        quadro = f < 1 ? requestAnimationFrame(passo) : null;
      }
      quadro = requestAnimationFrame(passo);
    }

    function visaoGeral(sim) {
      var novo = sim ? 1 : 0;
      if (alvo === novo) return;
      alvo = novo;
      if (!sim) guia.hidden = true;
      if (window.requestAnimationFrame) animar();
      else {
        p = alvo;
        posicionar();
      }
    }

    function aPartirDoPonteiro(ev) {
      var r = regua.getBoundingClientRect();
      var t = trilha();
      var y = Math.min(Math.max(ev.clientY - r.top, 0), r.height);
      return { y: y, doc: (y / r.height) * t.total };
    }

    var arrastando = false;
    function levar(ev) {
      var q = aPartirDoPonteiro(ev);
      rolagem.scrollTop = q.doc - rolagem.clientHeight / 2;
      // segurando e arrastando: o ano sob o cursor vai junto para o mapa geral e a linha de foco
      if (LT.aoEscolherAno) LT.aoEscolherAno(anoDeY(q.doc));
    }
    regua.addEventListener("pointerenter", function () {
      visaoGeral(true);
    });
    regua.addEventListener("pointerdown", function (ev) {
      visaoGeral(true);
      arrastando = true;
      regua.setPointerCapture(ev.pointerId);
      levar(ev);
      ev.preventDefault();
    });
    regua.addEventListener("pointermove", function (ev) {
      var q = aPartirDoPonteiro(ev);
      guia.hidden = alvo === 0;
      guia.style.top = q.y + "px";
      guiaAno.textContent = rotuloAno(anoDeY(q.doc));
      if (arrastando) levar(ev);
    });
    function soltar() {
      arrastando = false;
    }
    regua.addEventListener("pointerup", soltar);
    regua.addEventListener("pointercancel", soltar);
    regua.addEventListener("pointerleave", function () {
      if (!arrastando) visaoGeral(false);
    });
    // a roda do mouse sobre a régua rola o mapa
    regua.addEventListener(
      "wheel",
      function (ev) {
        rolarSuave(rolagem, ev.deltaY);
        ev.preventDefault();
      },
      { passive: false }
    );

    rolagem.addEventListener("scroll", posicionar);
    function atualizar() {
      construir();
      posicionar();
    }
    if (window.ResizeObserver) new ResizeObserver(atualizar).observe(rolagem);
    else window.addEventListener("resize", atualizar);
    return regua;
  }

  LT.REGUA_Y = REGUA_Y;
  LT.SEM_DATA_ATE = SEM_DATA_ATE;
  LT.Y = Y;
  LT.anoDeY = anoDeY;
  LT.reguaAtiva = reguaAtiva;
  LT.reguaDeRolagem = reguaDeRolagem;
  LT.rolarSuave = rolarSuave;
  LT.rotuloAno = rotuloAno;
  LT.svg = svg;
})();
