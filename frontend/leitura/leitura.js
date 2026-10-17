// Leitura (leitura/index.html): marcar livros, capítulos e versículos lidos e ver o progresso.
// Só marca com login (conectado) e só depois do servidor confirmar o progresso: Conta.salvar
// substitui a linha inteira. Mostra antes a cópia guardada (Conta.progressoGuardado), só para consulta.
(function () {
  "use strict";

  var ler = Util.ler, esc = Util.esc;

  // progresso antigo, de quando era salvo só no navegador: sobe para a conta no primeiro login
  var KEY = "biblioteca-lido";
  var KEY_V = "biblioteca-versiculos";


  var lido = {};
  var leitura = {};
  var Conta = window.Conta;
  var conectado = false;
  var usuarioCarregado = null;
  var canon = [];
  var canonPorId = {};
  var raiz = document.getElementById("leitura");
  var nav = { nivel: "livros", livro: null, cap: null };
  var planos = [];
  var eras = {};

  function urlEntrar() {
    return Conta ? Conta.urlEntrar() : "/conta/";
  }

  function todosVersos(b, c) {
    var a = [];
    for (var i = 1; i <= b.v[c - 1]; i++) a.push(i);
    return a;
  }
  function lidosCap(b, c) {
    var x = leitura[b.id] && leitura[b.id][c];
    if (x === 1) return b.v[c - 1];
    return x ? x.length : 0;
  }
  function versoLido(b, c, v) {
    var x = leitura[b.id] && leitura[b.id][c];
    return x === 1 || (!!x && x.indexOf(v) >= 0);
  }
  function gravarCap(b, c, arr) {
    var m = (leitura[b.id] = leitura[b.id] || {});
    if (arr.length === 0) delete m[c];
    else if (arr.length === b.v[c - 1]) m[c] = 1;
    else m[c] = arr;
    if (!Object.keys(m).length) delete leitura[b.id];
  }
  function setVerso(b, c, v, on) {
    var x = leitura[b.id] && leitura[b.id][c];
    var arr = x === 1 ? todosVersos(b, c) : x ? x.slice() : [];
    var i = arr.indexOf(v);
    if (on && i < 0) {
      arr.push(v);
      arr.sort(function (p, q) { return p - q; });
    }
    if (!on && i >= 0) arr.splice(i, 1);
    gravarCap(b, c, arr);
  }
  function setCap(b, c, on) {
    gravarCap(b, c, on ? todosVersos(b, c) : []);
  }
  function setLivro(b, on) {
    for (var c = 1; c <= b.v.length; c++) setCap(b, c, on);
  }
  function capsCompletos(b) {
    var n = 0;
    for (var c = 1; c <= b.v.length; c++) if (lidosCap(b, c) === b.v[c - 1]) n++;
    return n;
  }
  function capsComAlgo(b) {
    var n = 0;
    for (var c = 1; c <= b.v.length; c++) if (lidosCap(b, c) > 0) n++;
    return n;
  }
  function totalVersos(b) {
    var n = 0;
    for (var c = 0; c < b.v.length; c++) n += b.v[c];
    return n;
  }
  // área colorida do quadrado = porcentagem de versículos lidos
  function pct(feitos, total) {
    return total ? Math.round((feitos / total) * 1000) / 10 : 0;
  }
  function livroCompleto(b) {
    return capsCompletos(b) === b.v.length;
  }
  function versosLidos(b) {
    var n = 0;
    for (var c = 1; c <= b.v.length; c++) n += lidosCap(b, c);
    return n;
  }
  function estado(feitos, total) {
    return feitos === 0 ? "" : feitos === total ? "feito" : "parcial";
  }

  function salvarProgresso() {
    if (conectado) Conta.salvar(lido, leitura);
  }

  function sincronizar(b) {
    if (livroCompleto(b)) lido[b.item] = true;
    else delete lido[b.item];
    salvarProgresso();
    atualizarProgresso();
  }

  function atualizarProgresso() {
    var livros = 0, caps = 0, totalCaps = 0, versos = 0, totalVersos = 0;
    canon.forEach(function (b) {
      var c = capsCompletos(b);
      caps += c;
      totalCaps += b.v.length;
      versos += versosLidos(b);
      for (var i = 0; i < b.v.length; i++) totalVersos += b.v[i];
      if (c === b.v.length) livros++;
    });
    [
      ["livro", "Livros", livros, canon.length],
      ["capitulo", "Capítulos", caps, totalCaps],
      ["versiculo", "Versículos", versos, totalVersos]
    ].forEach(function (p) {
      var bar = document.querySelector('[data-progresso="' + p[0] + '"]');
      if (!bar) return;
      bar.querySelector("progress").max = p[3] || 1;
      bar.querySelector("progress").value = p[2];
      bar.querySelector("span").textContent = p[1] + " " + p[2] + "/" + p[3];
    });
  }

  // o progresso é sempre mostrado na ordem de um plano: o padrão da conta, ou o histórico
  function planoAtual() {
    var c = Conta && Conta.usuario() && Conta.config().plano;
    var id = (c && c.padrao) || "historico";
    var achado = null;
    planos.forEach(function (m) { if (m.id === id) achado = m; });
    return achado || planos[0] || null;
  }
  function capsEm(b, de, ate) {
    var n = 0;
    for (var c = de; c <= ate; c++) if (lidosCap(b, c) === b.v[c - 1]) n++;
    return n;
  }
  function versosEm(b, de, ate) {
    var n = 0, t = 0;
    for (var c = de; c <= ate; c++) {
      n += lidosCap(b, c);
      t += b.v[c - 1];
    }
    return [n, t];
  }
  function nomeTrecho(b, tr) {
    if (tr.de === 1 && tr.ate === b.v.length) return b.nome;
    return b.nome + " " + tr.de + (tr.ate > tr.de ? "–" + tr.ate : "");
  }
  function trechoCompleto(b, tr) {
    return capsEm(b, tr.de, tr.ate) === tr.ate - tr.de + 1;
  }
  function htmlPlano(plano, off) {
    var h = '<p class="hud muted l-plano">Plano: ' + esc(plano.nome) + ' · <a href="/plano-de-leitura/" target="_top">trocar</a></p>';
    plano.etapas.forEach(function (et) {
      var era = eras[et.era] || { nome: et.nome || et.era, periodo: et.periodo };
      var feitos = 0, total = 0;
      et.trechos.forEach(function (tr) {
        var b = canonPorId[tr.livro];
        feitos += capsEm(b, tr.de, tr.ate);
        total += tr.ate - tr.de + 1;
      });
      h += '<p class="l-secao hud">' + esc(era.nome) + (era.periodo ? ' <span class="faint">' + esc(era.periodo) + "</span>" : "") +
        '<span class="faint">' + feitos + "/" + total + " cap.</span></p>";
      h += '<div class="l-livros">';
      et.trechos.forEach(function (tr) {
        var b = canonPorId[tr.livro];
        var n = tr.ate - tr.de + 1;
        var c = capsEm(b, tr.de, tr.ate);
        var vs = versosEm(b, tr.de, tr.ate);
        var st = c === n ? "feito" : vs[0] ? "parcial" : "";
        h += '<div class="l-livro ' + st + '">' +
          '<button type="button" class="l-check ' + st + '" style="--pct:' + pct(vs[0], vs[1]) + '%" data-l-trecho-tog="' + b.id + ":" + tr.de + ":" + tr.ate + '"' + off + ' aria-label="Marcar ' + esc(nomeTrecho(b, tr)) + '" title="Marcar este trecho inteiro"></button>' +
          '<button type="button" class="l-nome" data-l-abrir="' + b.id + '">' + esc(nomeTrecho(b, tr)) + "</button>" +
          '<span class="hud faint">' + c + "/" + n + " cap.</span>" +
          '<progress value="' + c + '" max="' + n + '"></progress></div>';
      });
      h += "</div>";
    });
    return h;
  }

  function render() {
    var corpoAnt = raiz.querySelector(".leitura-corpo");
    var rolagem = corpoAnt ? corpoAnt.scrollTop : 0;
    var b = nav.livro ? canonPorId[nav.livro] : null;
    var h = '<header class="leitura-topo"><nav class="trilha" aria-label="Onde estou">';
    h += '<button type="button" data-l-ir="livros"' + (nav.nivel === "livros" ? ' aria-current="true"' : "") + ">Livros</button>";
    if (b) h += "<span>›</span><button type=\"button\" data-l-ir=\"caps\"" + (nav.nivel === "caps" ? ' aria-current="true"' : "") + ">" + esc(b.nome) + "</button>";
    if (b && nav.nivel === "versos") h += '<span>›</span><button type="button" aria-current="true">Capítulo ' + nav.cap + "</button>";
    h += "</nav></header>";
    h += '<div class="leitura-corpo">';
    var off = "";

    var plano = nav.nivel === "livros" ? planoAtual() : null;
    if (plano) {
      h += htmlPlano(plano, off);
    } else if (nav.nivel === "livros") {
      [["AT", "Antigo Testamento"], ["NT", "Novo Testamento"]].forEach(function (ta) {
        var lista = canon.filter(function (x) { return x.ta === ta[0]; });
        var feitos = lista.filter(livroCompleto).length;
        h += '<p class="l-secao hud">' + ta[1] + '<span class="faint">' + feitos + "/" + lista.length + "</span></p>";
        h += '<div class="l-livros">';
        lista.forEach(function (x) {
          var c = capsCompletos(x);
          var st = c === x.v.length ? "feito" : capsComAlgo(x) ? "parcial" : "";
          h += '<div class="l-livro ' + st + '">' +
            '<button type="button" class="l-check ' + st + '" style="--pct:' + pct(versosLidos(x), totalVersos(x)) + '%" data-l-livro-tog="' + x.id + '"' + off + ' aria-label="Marcar ' + esc(x.nome) + ' inteiro" title="Marcar o livro inteiro"></button>' +
            '<button type="button" class="l-nome" data-l-abrir="' + x.id + '">' + esc(x.nome) + "</button>" +
            '<span class="hud faint">' + c + "/" + x.v.length + " cap.</span>" +
            '<progress value="' + c + '" max="' + x.v.length + '"></progress></div>';
        });
        h += "</div>";
      });
    } else if (nav.nivel === "caps") {
      var feitosCaps = capsCompletos(b);
      h += '<div class="l-acoes"><p class="hud muted">' + esc(b.nome) + " · " + feitosCaps + "/" + b.v.length + " capítulos</p>" +
        '<span><button type="button" class="chip" data-l-livro-set="1"' + off + ">Marcar livro inteiro</button> " +
        '<button type="button" class="chip" data-l-livro-set="0"' + off + ">Limpar</button></span></div>";
      h += '<div class="l-grade">';
      for (var c = 1; c <= b.v.length; c++) {
        var lc = lidosCap(b, c);
        var st = estado(lc, b.v[c - 1]);
        h += '<div class="l-cap ' + st + '"><button type="button" class="l-cap-num" style="--pct:' + pct(lc, b.v[c - 1]) + '%" data-l-cap="' + c + '" title="' + lc + "/" + b.v[c - 1] + ' versículos">' + c + "</button>" +
          '<button type="button" class="l-check ' + st + '" data-l-cap-tog="' + c + '"' + off + ' aria-label="Marcar capítulo ' + c + '" title="Marcar o capítulo inteiro"></button></div>';
      }
      h += "</div>";
    } else {
      var n = b.v[nav.cap - 1];
      var lv = lidosCap(b, nav.cap);
      h += '<div class="l-acoes"><p class="hud muted">' + esc(b.nome) + " " + nav.cap + " · " + lv + "/" + n + " versículos</p><span>" +
        '<button type="button" class="chip" data-l-cap-set="1"' + off + ">Marcar capítulo</button> " +
        '<button type="button" class="chip" data-l-cap-set="0"' + off + ">Limpar</button></span></div>";
      h += '<div class="l-grade versos">';
      for (var v = 1; v <= n; v++) {
        h += '<button type="button" class="l-verso ' + (versoLido(b, nav.cap, v) ? "feito" : "") + '" data-l-verso="' + v + '"' + off + ' aria-pressed="' + versoLido(b, nav.cap, v) + '">' + v + "</button>";
      }
      h += "</div>";
    }
    h += "</div>";
    raiz.innerHTML = h;
    var corpoNovo = raiz.querySelector(".leitura-corpo");
    if (corpoNovo) corpoNovo.scrollTop = rolagem;
    atualizarProgresso();
  }

  var aviso = null;
  function avisarLogin() {
    if (!aviso) {
      aviso = document.createElement("dialog");
      aviso.className = "aviso-dlg";
      aviso.addEventListener("click", function (ev) {
        if (ev.target === aviso || ev.target.closest("[data-fechar-aviso]")) aviso.close();
      });
      document.body.appendChild(aviso);
    }
    aviso.innerHTML =
      "<h2>Entre para marcar sua leitura</h2>" +
      "<p>Sem login você só consulta. Com uma conta, o que você marca fica salvo e acompanha você em qualquer aparelho.</p>" +
      '<p class="aviso-acoes"><a class="chip" href="' + esc(urlEntrar()) + '">Entrar</a> ' +
      '<button type="button" class="chip" data-fechar-aviso>Agora não</button></p>';
    if (!aviso.open) aviso.showModal();
  }

  raiz.addEventListener("click", function (ev) {
    var t = ev.target.closest && ev.target.closest("button");
    if (!t || t.disabled) return;
    var muda = t.hasAttribute("data-l-livro-tog") || t.hasAttribute("data-l-trecho-tog") || t.hasAttribute("data-l-livro-set") ||
      t.hasAttribute("data-l-cap-tog") || t.hasAttribute("data-l-cap-set") || t.hasAttribute("data-l-verso");
    // com a cópia guardada na tela, o servidor ainda não confirmou: aguarda, sem pedir login
    if (muda && !conectado) return Conta && Conta.usuario() ? undefined : avisarLogin();
    var b = nav.livro ? canonPorId[nav.livro] : null;
    if (t.hasAttribute("data-l-ir")) {
      nav.nivel = t.getAttribute("data-l-ir");
      if (nav.nivel === "livros") nav.livro = null;
    } else if (t.hasAttribute("data-l-abrir")) {
      nav.livro = t.getAttribute("data-l-abrir");
      nav.nivel = "caps";
    } else if (t.hasAttribute("data-l-livro-tog")) {
      var x = canonPorId[t.getAttribute("data-l-livro-tog")];
      setLivro(x, !livroCompleto(x));
      sincronizar(x);
    } else if (t.hasAttribute("data-l-trecho-tog")) {
      var tt = t.getAttribute("data-l-trecho-tog").split(":");
      var bt = canonPorId[tt[0]];
      var de = Number(tt[1]), ate = Number(tt[2]);
      var ligar = capsEm(bt, de, ate) !== ate - de + 1;
      for (var k = de; k <= ate; k++) setCap(bt, k, ligar);
      sincronizar(bt);
    } else if (t.hasAttribute("data-l-livro-set")) {
      setLivro(b, t.getAttribute("data-l-livro-set") === "1");
      sincronizar(b);
    } else if (t.hasAttribute("data-l-cap")) {
      nav.cap = Number(t.getAttribute("data-l-cap"));
      nav.nivel = "versos";
    } else if (t.hasAttribute("data-l-cap-tog")) {
      var c = Number(t.getAttribute("data-l-cap-tog"));
      setCap(b, c, lidosCap(b, c) !== b.v[c - 1]);
      sincronizar(b);
    } else if (t.hasAttribute("data-l-cap-set")) {
      setCap(b, nav.cap, t.getAttribute("data-l-cap-set") === "1");
      sincronizar(b);
    } else if (t.hasAttribute("data-l-verso")) {
      var v = Number(t.getAttribute("data-l-verso"));
      setVerso(b, nav.cap, v, !versoLido(b, nav.cap, v));
      sincronizar(b);
    } else return;
    render();
    if (t.hasAttribute("data-l-abrir") || t.hasAttribute("data-l-cap") || t.hasAttribute("data-l-ir")) {
      var corpo = raiz.querySelector(".leitura-corpo");
      if (corpo) corpo.scrollTop = 0;
    }
  });

  function normalizar() {
    canon.forEach(function (b) {
      if (lido[b.item] && !leitura[b.id]) setLivro(b, true);
      if (livroCompleto(b)) lido[b.item] = true;
      else delete lido[b.item];
    });
  }

  function carregarProgresso() {
    if (!Conta) return Promise.resolve(null);
    return Conta.pronto().then(function (u) {
      return u ? Conta.carregar() : null;
    });
  }

  function aplicarProgresso(p) {
    var u = Conta && Conta.usuario();
    usuarioCarregado = p && u ? u.id : null;
    conectado = !!usuarioCarregado;
    lido = p ? p.lido : {};
    leitura = p ? p.versiculos : {};
    if (!conectado) return;

    var antigoLido = ler(KEY, null);
    var antigoV = ler(KEY_V, null);
    var importar = p.vazio && (antigoLido || antigoV);
    if (importar) {
      lido = antigoLido || {};
      leitura = antigoV || {};
    }
    var antes = JSON.stringify([lido, leitura]);
    normalizar();
    if (importar) {
      Conta.salvarAgora(lido, leitura).then(function () {
        Util.apagar(KEY);
        Util.apagar(KEY_V);
      }, function () {});
    } else if (JSON.stringify([lido, leitura]) !== antes) {
      salvarProgresso();
    }
  }

  // #livro (ou #livro/cap) abre direto nos capítulos desse livro; vem do leitor
  function abrirDoHash() {
    var m = /^#([a-z0-9]+)(?:\/\d+)?$/.exec(location.hash);
    if (!m || !canonPorId[m[1]]) return false;
    nav.livro = m[1];
    nav.nivel = "caps";
    return true;
  }

  function mostrar() {
    render();
  }

  window.addEventListener("hashchange", function () {
    if (canon.length && abrirDoHash()) render();
  });

  function recarregarProgresso() {
    carregarProgresso().then(function (p) {
      aplicarProgresso(p);
      mostrar();
    }, function () {
      aplicarProgresso(null);
      raiz.innerHTML = '<p class="vazio">Não consegui carregar seu progresso. Recarregue a página para tentar de novo.</p>';
    });
  }

  if (Conta) {
    Conta.aoMudar(function (evento, u) {
      if (!canon.length) return;
      var id = u ? u.id : null;
      if (id !== usuarioCarregado) recarregarProgresso();
    });
  }

  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState !== "visible" || !conectado || Conta.temPendente()) return;
    recarregarProgresso();
  });

  // a ordem do progresso vem dos planos (dado de outra fatia); sem eles, cai na lista AT/NT
  var carregarPlanos = Promise.all([
    fetch("/plano-de-leitura/planos.json").then(function (r) { return r.json(); }),
    fetch("/compartilhado/dados/eras.json").then(function (r) { return r.json(); })
  ]).then(function (r) {
    planos = r[0].planos;
    r[1].eras.forEach(function (e) { eras[e.id] = e; });
  }, function () {});

  if (Conta) Conta.aoConfig(function () { if (canon.length) render(); });

  carregarPlanos.then(function () { return fetch("/compartilhado/dados/canon.json"); })
    .then(function (r) { return r.json(); })
    .then(function (lista) {
      canon = lista;
      canon.forEach(function (b) { canonPorId[b.id] = b; });
      abrirDoHash();
      // a cópia guardada neste navegador aparece na hora, só para consulta; marcar só depois
      // que o servidor confirmar o progresso (o envio substitui a linha inteira)
      var mostrouGuardado = (Conta ? Conta.pronto() : Promise.resolve(null)).then(function (u) {
        var g = u && Conta.progressoGuardado();
        if (!g) return;
        lido = g.lido;
        leitura = g.versiculos;
        conectado = false;
        usuarioCarregado = null;
        mostrar();
      });
      return mostrouGuardado.then(carregarProgresso).then(function (p) {
        aplicarProgresso(p);
        abrirDoHash();
        mostrar();
      }, function () {
        aplicarProgresso(null);
        raiz.innerHTML = '<p class="vazio">Não consegui carregar seu progresso. Recarregue a página para tentar de novo.</p>';
      });
    }, function () {
      raiz.innerHTML = '<p class="vazio">Não consegui carregar os livros. Abra por um servidor local (<code>python -m http.server</code>).</p>';
    });
})();
