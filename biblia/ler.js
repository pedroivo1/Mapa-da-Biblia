(function () {
  "use strict";

  var KEY = "biblia-leitor";
  var KEY_MAPA = "biblia-mapa"; // { padrao: id do mapa escolhido, pos: { id do mapa: "livro/cap" } }
  var TAM_MIN = 0.9;
  var TAM_MAX = 2;
  var raiz = document.getElementById("leitor");
  var canon = [];
  var texto = [];
  var pos = { i: 0, c: 1 };
  var tam = 1.2;
  var dlg = null;
  var dlgLeitura = null;
  var dlgApoio = null;
  var materiais = [];
  var voz = window.speechSynthesis || null;
  var falando = false;
  // modo mapa: só quando aberto pelo botão do mapa (?mapa=id); pela aba Bíblia segue a ordem dos livros
  var mapa = null;
  var eras = {};
  var ordem = [];
  var indice = {};

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

  function doHash() {
    var m = /^#([a-z0-9]+)\/(\d+)$/.exec(location.hash);
    if (!m) return null;
    for (var i = 0; i < canon.length; i++) {
      if (canon[i].id === m[1]) {
        var c = Number(m[2]);
        if (c >= 1 && c <= texto[i].chapters.length) return { i: i, c: c };
      }
    }
    return null;
  }

  function ir(i, c, mantemVoz) {
    if (!mantemVoz) parar();
    pos = { i: i, c: c };
    gravar(KEY, { livro: canon[i].id, cap: c, tam: tam });
    if (mapa) {
      var m = ler(KEY_MAPA, {});
      m.pos = m.pos || {};
      m.pos[mapa.id] = canon[i].id + "/" + c;
      gravar(KEY_MAPA, m);
    }
    history.replaceState(null, "", "#" + canon[i].id + "/" + c);
    render();
    window.scrollTo(0, 0);
  }

  function noMapa(delta) {
    var n = indice[pos.i + ":" + pos.c];
    return n == null ? null : ordem[n + delta] || null;
  }

  function anterior() {
    if (mapa) return noMapa(-1);
    if (pos.c > 1) return { i: pos.i, c: pos.c - 1 };
    if (pos.i > 0) return { i: pos.i - 1, c: texto[pos.i - 1].chapters.length };
    return null;
  }
  function proximo() {
    if (mapa) return noMapa(1);
    if (pos.c < texto[pos.i].chapters.length) return { i: pos.i, c: pos.c + 1 };
    if (pos.i < canon.length - 1) return { i: pos.i + 1, c: 1 };
    return null;
  }

  // leitura em voz alta (Web Speech API do navegador)
  function melhorVoz() {
    var lista = voz.getVoices().filter(function (x) { return /^pt/i.test(x.lang); });
    var nota = function (x) {
      var n = /^pt[-_]BR/i.test(x.lang) ? 10 : 0;
      if (/natural|neural|online/i.test(x.name)) n += 5;
      if (/google/i.test(x.name)) n += 3;
      if (/luciana|francisca|thalita|antonio|camila|vit[oó]ria/i.test(x.name)) n += 1;
      return n;
    };
    lista.sort(function (a, b) { return nota(b) - nota(a); });
    return lista[0] || null;
  }

  function parar() {
    if (!voz || !falando) return;
    falando = false;
    voz.cancel();
    atualizarOuvir();
  }

  function atualizarOuvir() {
    var bt = raiz.querySelector("[data-ouvir]");
    if (bt) bt.textContent = falando ? "Parar" : "Ouvir";
  }

  // um trecho por versículo: o Chrome corta falas muito longas
  function ouvir() {
    var versos = texto[pos.i].chapters[pos.c - 1];
    var v = melhorVoz();
    var fim = pos.i + ":" + pos.c;
    avisarVoz("");
    voz.cancel();
    falando = true;
    atualizarOuvir();
    if (!v) avisarVoz("Nenhuma voz em português encontrada neste navegador; tentando a voz padrão.");
    versos.forEach(function (frase, k) {
      var u = new SpeechSynthesisUtterance(frase.replace(/["‘’“”]/g, ""));
      u.lang = v ? v.lang : "pt-BR";
      if (v) u.voice = v;
      u.rate = 0.95;
      u.onerror = function (ev) {
        var motivo = ev && ev.error;
        if (motivo === "interrupted" || motivo === "canceled") return;
        if (falando && fim === pos.i + ":" + pos.c) {
          falando = false;
          atualizarOuvir();
          avisarVoz("Não consegui falar (" + (motivo || "erro") + "). Seu navegador ou sistema pode não ter voz em português instalada.");
        }
      };
      if (k === versos.length - 1) {
        u.onend = function () {
          if (!falando || fim !== pos.i + ":" + pos.c) return;
          var prox = proximo();
          if (!prox) {
            falando = false;
            return atualizarOuvir();
          }
          ir(prox.i, prox.c, true);
          ouvir();
        };
      }
      // o Chrome descarta speak() logo depois de cancel(): a fila entra na volta seguinte
      setTimeout(function () {
        if (falando && fim === pos.i + ":" + pos.c) voz.speak(u);
      }, 60);
    });
  }

  function avisarVoz(msg) {
    var el = raiz.querySelector(".leitor-aviso");
    if (!el) return;
    el.textContent = msg;
    el.hidden = !msg;
  }

  // texto corrido; quebra de linha só onde uma fala começa ou termina
  // (aspas retas " abrem e fecham a fala; ‘ ’ são falas dentro de falas)
  function paragrafos(versos) {
    var h = "";
    var aberta = false;
    var fechouAgora = false;
    for (var v = 0; v < versos.length; v++) {
      var aspas = (versos[v].match(/"/g) || []).length;
      var abre = !aberta && aspas > 0;
      if (v === 0) h += "<p>";
      else if (abre || fechouAgora) h += "</p><p>";
      else h += " ";
      h += "<sup>" + (v + 1) + "</sup>" + esc(versos[v]);
      aberta = ((aberta ? 1 : 0) + aspas) % 2 === 1;
      fechouAgora = aspas > 0 && !aberta;
    }
    return h + "</p>";
  }

  function bannerMapa() {
    var n = indice[pos.i + ":" + pos.c];
    var p = n == null ? null : ordem[n];
    if (!p) return "";
    var etapa = mapa.etapas[p.e];
    var era = eras[etapa.era] || {};
    var tr = etapa.trechos[p.t];
    var sai = location.pathname.replace(/[^\/]*$/, "") + "ler.html" + location.hash;
    return '<div class="leitor-mapa"><p class="hud muted"><strong>' + esc(mapa.nome) + "</strong> · " + esc(era.nome || "") +
      (era.periodo ? " (" + esc(era.periodo) + ")" : "") + " · " + (n + 1) + "/" + ordem.length + "</p>" +
      (tr.nota ? '<p class="hud faint">' + esc(tr.nota) + "</p>" : "") +
      '<p class="hud"><a href="mapa.html">Ver o mapa</a> · <a href="' + esc(sai) + '">Sair do mapa (ordem dos livros)</a></p></div>';
  }

  // materiais de apoio ligados ao capítulo que está na tela
  function materiaisDoCapitulo() {
    var b = canon[pos.i];
    return materiais.filter(function (m) {
      return m.capitulos.some(function (r) {
        return r.livro === b.id && pos.c >= r.de && pos.c <= r.ate;
      });
    });
  }

  function render() {
    var b = canon[pos.i];
    var apoio = materiaisDoCapitulo();
    var versos = texto[pos.i].chapters[pos.c - 1];
    var ant = anterior();
    var prox = proximo();
    var h = '<div class="leitor-barra">' +
      '<button type="button" data-escolher aria-haspopup="dialog"><span class="leitor-ref">' + esc(b.nome) + " " + pos.c + "</span> ▾</button>" +
      '<span class="leitor-fonte">' +
      (apoio.length ? '<button type="button" data-apoio aria-haspopup="dialog">Apoio (' + apoio.length + ")</button>" : "") +
      (voz ? '<button type="button" data-ouvir>' + (falando ? "Parar" : "Ouvir") + "</button>" : "") +
      '<button type="button" data-leitura aria-haspopup="dialog">Marcar leitura</button>' +
      '<button type="button" data-fonte="-1" aria-label="Diminuir letra"' + (tam <= TAM_MIN ? " disabled" : "") + ">A−</button>" +
      '<button type="button" data-fonte="1" aria-label="Aumentar letra"' + (tam >= TAM_MAX ? " disabled" : "") + ">A+</button>" +
      "</span></div>";
    if (mapa) h += bannerMapa();
    h += '<p class="leitor-aviso hud muted" role="status" hidden></p>';
    h += '<article class="leitor-texto"><h1>' + esc(b.nome) + " " + pos.c + "</h1>";
    h += paragrafos(versos) + "</article>";
    h += '<div class="leitor-fim">' +
      '<button type="button" data-nav="ant"' + (ant ? "" : " disabled") + ">← Anterior</button>" +
      '<button type="button" data-nav="prox"' + (prox ? "" : " disabled") + ">Próximo →</button></div>";
    raiz.innerHTML = h;
    raiz.style.setProperty("--leitor-fonte", tam + "rem");
    document.title = b.nome + " " + pos.c + " — Bíblia NVI — Mapa da Bíblia";
  }

  function abrirEscolha(livro) {
    if (!dlg) {
      dlg = document.createElement("dialog");
      dlg.className = "leitor-dlg";
      dlg.addEventListener("click", function (ev) {
        if (ev.target === dlg || ev.target.closest("[data-fechar]")) return dlg.close();
        var l = ev.target.closest("[data-livro]");
        if (l) return abrirEscolha(Number(l.getAttribute("data-livro")));
        var c = ev.target.closest("[data-cap]");
        if (c) {
          dlg.close();
          ir(Number(c.getAttribute("data-i")), Number(c.getAttribute("data-cap")));
        }
        if (ev.target.closest("[data-voltar]")) abrirEscolha(null);
      });
      document.body.appendChild(dlg);
    }
    var h = "";
    if (livro == null) {
      h += '<div class="leitor-dlg-topo"><span class="hud muted">Livros</span><button type="button" data-fechar>Fechar</button></div>';
      [["AT", "Antigo Testamento"], ["NT", "Novo Testamento"]].forEach(function (ta) {
        h += '<p class="l-secao hud">' + ta[1] + '</p><div class="leitor-dlg-lista">';
        canon.forEach(function (b, i) {
          if (b.ta !== ta[0]) return;
          h += '<button type="button" data-livro="' + i + '"' + (i === pos.i ? ' aria-current="true"' : "") + ">" + esc(b.nome) + "</button>";
        });
        h += "</div>";
      });
    } else {
      h += '<div class="leitor-dlg-topo"><button type="button" data-voltar>← Livros</button><span class="hud muted">' + esc(canon[livro].nome) + '</span><button type="button" data-fechar>Fechar</button></div>';
      h += '<div class="l-grade">';
      for (var c = 1; c <= texto[livro].chapters.length; c++) {
        h += '<button type="button" data-i="' + livro + '" data-cap="' + c + '"' + (livro === pos.i && c === pos.c ? ' aria-current="true"' : "") + ">" + c + "</button>";
      }
      h += "</div>";
    }
    dlg.innerHTML = h;
    if (!dlg.open) dlg.showModal();
  }

  // a página Leitura inteira, dentro de um popup (mesma conta, mesmo progresso)
  function abrirLeitura() {
    // a cada abertura recarrega, para cair no livro que está sendo lido
    var url = "leitura.html?embutido&_=" + Date.now() + "#" + canon[pos.i].id + "/" + pos.c;
    if (!dlgLeitura) {
      dlgLeitura = document.createElement("dialog");
      dlgLeitura.className = "leitor-dlg leitor-dlg-leitura";
      dlgLeitura.innerHTML =
        '<div class="leitor-dlg-topo"><span class="hud muted">Leitura</span><button type="button" data-fechar>Fechar</button></div>' +
        '<iframe title="Leitura"></iframe>';
      dlgLeitura.addEventListener("click", function (ev) {
        if (ev.target === dlgLeitura || ev.target.closest("[data-fechar]")) dlgLeitura.close();
      });
      document.body.appendChild(dlgLeitura);
    }
    var quadro = dlgLeitura.querySelector("iframe");
    quadro.setAttribute("src", url);
    if (!dlgLeitura.open) dlgLeitura.showModal();
  }

  // popup com os materiais do capítulo: troca de um para outro sem fechar
  function mostrarApoio(lista, k) {
    dlgApoio.setAttribute("data-k", k);
    var ant = dlgApoio.querySelector('[data-apoio-passo="-1"]');
    var prox = dlgApoio.querySelector('[data-apoio-passo="1"]');
    ant.disabled = k === 0;
    prox.disabled = k === lista.length - 1;
    var quadro = dlgApoio.querySelector("iframe");
    var m = lista[k];
    var abas = dlgApoio.querySelectorAll("[data-aba]");
    for (var j = 0; j < abas.length; j++) {
      if (j === k) abas[j].setAttribute("aria-current", "true");
      else abas[j].removeAttribute("aria-current");
    }
    var cams = dlgApoio.querySelector(".apoio-camadas");
    if (cams) {
      cams.hidden = !m.camadas;
      cams.querySelector('[data-camada="apoio"]').setAttribute("aria-pressed", "true");
      cams.querySelector('[data-camada="curio"]').setAttribute("aria-pressed", "false");
    }
    dlgApoio.querySelector(".apoio-resumo").textContent = m.tipo + " · " + m.ref + " — " + m.resumo;
    quadro.setAttribute("title", m.titulo);
    quadro.setAttribute("src", m.url + (m.url.indexOf("?") < 0 ? "?" : "&") + "embutido&cap=" + pos.c);
  }

  function abrirApoio() {
    var lista = materiaisDoCapitulo();
    if (!lista.length) return;
    if (!dlgApoio) {
      dlgApoio = document.createElement("dialog");
      dlgApoio.className = "leitor-dlg leitor-dlg-leitura leitor-dlg-apoio";
      document.body.appendChild(dlgApoio);
    }
    var h = '<div class="leitor-dlg-topo"><span class="hud muted">Material de apoio</span><button type="button" data-fechar>Fechar</button></div>' +
      '<div class="apoio-abas" role="tablist">';
    lista.forEach(function (m, k) {
      h += '<button type="button" data-aba="' + k + '">' + esc(m.titulo) + "</button>";
    });
    if (lista.some(function (m) { return m.camadas; })) {
      h += '<span class="apoio-camadas" hidden>' +
        '<button type="button" data-camada="apoio" aria-pressed="true" title="Rota e etapas">Apoio</button>' +
        '<button type="button" data-camada="curio" aria-pressed="false">Curiosidades</button></span>';
    }
    h += '<span class="apoio-passos">' +
      '<button type="button" data-apoio-passo="-1">← Anterior</button>' +
      '<button type="button" data-apoio-passo="1">Próximo →</button></span>';
    h += '</div><p class="apoio-resumo hud muted"></p><iframe></iframe>';
    dlgApoio.innerHTML = h;
    dlgApoio.onclick = function (ev) {
      if (ev.target === dlgApoio || ev.target.closest("[data-fechar]")) return dlgApoio.close();
      var aba = ev.target.closest("[data-aba]");
      if (aba) return mostrarApoio(lista, Number(aba.getAttribute("data-aba")));
      var cam = ev.target.closest("[data-camada]");
      if (cam) {
        var quadro = dlgApoio.querySelector("iframe");
        if (quadro.contentWindow) quadro.contentWindow.postMessage({ tipo: "apoio-camada", camada: cam.getAttribute("data-camada") }, location.origin);
        return;
      }
      var passo = ev.target.closest("[data-apoio-passo]");
      if (passo && !passo.disabled) {
        var k = Number(dlgApoio.getAttribute("data-k")) + Number(passo.getAttribute("data-apoio-passo"));
        if (k >= 0 && k < lista.length) mostrarApoio(lista, k);
      }
    };
    mostrarApoio(lista, 0);
    if (!dlgApoio.open) dlgApoio.showModal();
  }

  // o mapa avisa quando liga ou desliga uma camada
  window.addEventListener("message", function (ev) {
    if (ev.origin !== location.origin || !ev.data || ev.data.tipo !== "apoio-estado" || !dlgApoio) return;
    var cams = dlgApoio.querySelector(".apoio-camadas");
    if (!cams) return;
    cams.querySelector('[data-camada="apoio"]').setAttribute("aria-pressed", String(!!ev.data.apoio));
    cams.querySelector('[data-camada="curio"]').setAttribute("aria-pressed", String(!!ev.data.curiosidades));
  });

  raiz.addEventListener("click", function (ev) {
    var t = ev.target.closest && ev.target.closest("button");
    if (!t || t.disabled) return;
    if (t.hasAttribute("data-apoio")) return abrirApoio();
    if (t.hasAttribute("data-leitura")) return abrirLeitura();
    if (t.hasAttribute("data-ouvir")) return falando ? parar() : ouvir();
    if (t.hasAttribute("data-escolher")) return abrirEscolha(pos.i);
    if (t.hasAttribute("data-fonte")) {
      tam = Math.min(TAM_MAX, Math.max(TAM_MIN, Math.round((tam + Number(t.getAttribute("data-fonte")) * 0.1) * 10) / 10));
      gravar(KEY, { livro: canon[pos.i].id, cap: pos.c, tam: tam });
      return render();
    }
    var alvo = t.getAttribute("data-nav") === "ant" ? anterior() : t.getAttribute("data-nav") === "prox" ? proximo() : null;
    if (alvo) ir(alvo.i, alvo.c);
  });

  document.addEventListener("keydown", function (ev) {
    if (!canon.length || (dlg && dlg.open) || (dlgLeitura && dlgLeitura.open) || (dlgApoio && dlgApoio.open) || ev.altKey || ev.ctrlKey || ev.metaKey) return;
    var alvo = ev.key === "ArrowLeft" ? anterior() : ev.key === "ArrowRight" ? proximo() : null;
    if (alvo) ir(alvo.i, alvo.c);
  });

  window.addEventListener("hashchange", function () {
    var p = doHash();
    if (p && (p.i !== pos.i || p.c !== pos.c)) {
      parar();
      pos = p;
      render();
      window.scrollTo(0, 0);
    }
  });

  window.addEventListener("beforeunload", function () {
    if (voz) voz.cancel();
  });

  function montarMapa(lista, listaEras) {
    var id = (/[?&]mapa=([a-z0-9-]+)/.exec(location.search) || [])[1];
    if (!id || !lista) return;
    var porId = {};
    canon.forEach(function (b, i) { porId[b.id] = i; });
    (lista.mapas || []).forEach(function (m) { if (m.id === id) mapa = m; });
    if (!mapa) return;
    (listaEras.eras || []).forEach(function (e) { eras[e.id] = e; });
    mapa.etapas.forEach(function (et, e) {
      et.trechos.forEach(function (tr, t) {
        for (var c = tr.de; c <= tr.ate; c++) {
          indice[porId[tr.livro] + ":" + c] = ordem.length;
          ordem.push({ i: porId[tr.livro], c: c, e: e, t: t });
        }
      });
    });
  }

  function iniciar(listaCanon, biblia, mapas, listaEras) {
    canon = listaCanon;
    texto = biblia;
    montarMapa(mapas, listaEras);
    var salvo = ler(KEY, {});
    if (typeof salvo.tam === "number" && salvo.tam >= TAM_MIN && salvo.tam <= TAM_MAX) tam = salvo.tam;
    var p = doHash();
    if (mapa && !p) {
      var guardado = (ler(KEY_MAPA, {}).pos || {})[mapa.id];
      var m = guardado && /^([a-z0-9]+)\/(\d+)$/.exec(guardado);
      var s = 0;
      for (var k = 0; m && k < canon.length; k++) {
        if (canon[k].id === m[1] && indice[k + ":" + m[2]] != null) s = indice[k + ":" + m[2]];
      }
      p = ordem[s];
    }
    if (!p && !mapa && salvo.livro) {
      for (var i = 0; i < canon.length; i++) {
        if (canon[i].id === salvo.livro && salvo.cap >= 1 && salvo.cap <= texto[i].chapters.length) p = { i: i, c: salvo.cap };
      }
    }
    pos = p || { i: 0, c: 1 };
    render();
  }

  var comMapa = /[?&]mapa=/.test(location.search);
  Promise.all([
    fetch("dados/canon.json").then(function (r) { return r.json(); }),
    fetch("../data/nvi.json").then(function (r) { return r.json(); }),
    comMapa ? fetch("dados/mapas.json").then(function (r) { return r.json(); }) : null,
    comMapa ? fetch("dados/eras.json").then(function (r) { return r.json(); }) : null,
    fetch("dados/materiais.json").then(function (r) { return r.json(); }).catch(function () { return { materiais: [] }; })
  ]).then(function (r) {
    materiais = r[4].materiais || [];
    iniciar(r[0], r[1], r[2], r[3]);
  }, function () {
    raiz.innerHTML = '<p class="vazio">Não consegui carregar o texto. Abra por um servidor local (<code>python -m http.server</code>).</p>';
  });
})();
