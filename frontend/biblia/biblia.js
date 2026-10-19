// Leitor da Bíblia (biblia/index.html): texto na versão escolhida (compartilhado/js/versao.js), livros, capítulos, tamanho da letra, voz.
// Aberto com ?plano=id segue a ordem do plano de leitura (plano-de-leitura/planos.json); sem ele, a dos livros.
// Posição e letra: navegador (biblia-leitor) e conta ("leitor"); posição por plano: "plano".
// Botões Leitura (popup leitura/index.html) e Mapas (popup com os mapas do capítulo, mapas/mapas.json).
// Tocar num versículo seleciona; a barra que aparece grifa (quatro cores) ou salva por temas
// (Conta.salvarMarcacoes, tabela marcacoes). Os salvos ficam em /versiculos/. Sem login, só lê.
(function () {
  "use strict";

  var ler = Util.ler, gravar = Util.gravar, esc = Util.esc;

  var KEY = "biblia-leitor";
  var KEY_PLANO = "biblia-mapa"; // { padrao: id do plano escolhido, pos: { id do plano: "livro/cap" } }
  var Conta = window.Conta;
  var TAM_MIN = 0.9;
  var TAM_MAX = 2;
  var raiz = document.getElementById("leitor");
  var canon = [];
  var texto = [];
  var pos = { i: 0, c: 1 };
  var tam = 1.2;
  var dlg = null;
  var grupos = {}; // id do livro -> grupo (cor), de linha-do-tempo/livros.json
  var dlgLeitura = null;
  var dlgMapas = null;
  var listaMapas = []; // os mapas do capítulo mostrados no popup Mapas
  var mapas = [];
  var voz = window.speechSynthesis || null;
  var falando = false;
  // modo plano: só quando aberto pelo botão do plano (?plano=id); pela aba Bíblia segue a ordem dos livros
  var plano = null;
  var eras = {};
  var ordem = [];
  var indice = {};
  // grifos e versículos salvos: chave "livro/cap/verso" (vem da conta; aqui só com login)
  var CORES = ["amarelo", "verde", "azul", "rosa"];
  var marc = {};
  var marcPronto = false; // o servidor confirmou a lista: só então grifar e salvar
  var selecao = []; // versículos selecionados no capítulo aberto, em ordem
  var barra = null;
  var dlgSalvar = null;

  // posição e letra do leitor, e o plano: ficam na conta quando há login, e no navegador sempre
  function guardarLeitor(v) {
    gravar(KEY, v);
    if (Conta) Conta.salvarConfig("leitor", v);
  }
  function estadoPlano() {
    var c = Conta && Conta.usuario() && Conta.config().plano;
    return c || ler(KEY_PLANO, {});
  }
  function guardarPlano(v) {
    gravar(KEY_PLANO, v);
    if (Conta) Conta.salvarConfig("plano", v);
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
    selecao = [];
    guardarLeitor({ livro: canon[i].id, cap: c, tam: tam });
    if (plano) {
      var m = estadoPlano();
      m.pos = m.pos || {};
      m.pos[plano.id] = canon[i].id + "/" + c;
      guardarPlano(m);
    }
    history.replaceState(null, "", "#" + canon[i].id + "/" + c);
    render();
    window.scrollTo(0, 0);
  }

  function noPlano(delta) {
    var n = indice[pos.i + ":" + pos.c];
    return n == null ? null : ordem[n + delta] || null;
  }

  function anterior() {
    if (plano) return noPlano(-1);
    if (pos.c > 1) return { i: pos.i, c: pos.c - 1 };
    if (pos.i > 0) return { i: pos.i - 1, c: texto[pos.i - 1].chapters.length };
    return null;
  }
  function proximo() {
    if (plano) return noPlano(1);
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
    if (!bt) return;
    bt.innerHTML = falando ? ICONE_PAUSA : ICONE_PLAY;
    bt.setAttribute("aria-label", falando ? "Parar" : "Ouvir");
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
      h += '<span class="leitor-v" data-v="' + (v + 1) + '"><sup>' + (v + 1) + "</sup>" + esc(versos[v]) + "</span>";
      aberta = ((aberta ? 1 : 0) + aspas) % 2 === 1;
      fechouAgora = aspas > 0 && !aberta;
    }
    return h + "</p>";
  }

  // mapas de apoio ligados ao capítulo que está na tela
  function mapasDoCapitulo() {
    var b = canon[pos.i];
    return mapas.filter(function (m) {
      return m.capitulos.some(function (r) {
        return r.livro === b.id && pos.c >= r.de && pos.c <= r.ate;
      });
    });
  }

  var ICONE_SVG = '<svg class="leitor-icone" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">';
  var ICONE_MAPA = ICONE_SVG + '<path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2z"/><path d="M9 4v14M15 6v14"/></svg>';
  var ICONE_CALENDARIO = ICONE_SVG + '<rect x="3" y="5" width="18" height="16" rx="1"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>';

  var ICONE_SETA_ESQ = Util.seta("esq", 20, "leitor-seta");
  var ICONE_SETA_DIR = Util.seta("dir", 20, "leitor-seta");
  var ICONE_PLAY = '<svg class="leitor-icone" viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true"><path d="M8 5.5v13a1 1 0 0 0 1.5.9l10.5-6.5a1 1 0 0 0 0-1.8L9.5 4.6A1 1 0 0 0 8 5.5z"/></svg>';
  var ICONE_PAUSA = '<svg class="leitor-icone" viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true"><rect x="6" y="5" width="4.5" height="14" rx="1"/><rect x="13.5" y="5" width="4.5" height="14" rx="1"/></svg>';

  // capítulo anterior, livro e capítulo (abre a escolha), próximo: no topo e na barra de baixo
  function passos(b, ant, prox) {
    return '<button type="button" data-nav="ant"' + (ant ? "" : " disabled") + ' aria-label="Capítulo anterior">' + ICONE_SETA_ESQ + "</button>" +
      '<button type="button" class="leitor-passo-ref" data-escolher aria-haspopup="dialog">' + esc(b.nome) + " " + pos.c + "</button>" +
      '<button type="button" data-nav="prox"' + (prox ? "" : " disabled") + ' aria-label="Próximo capítulo">' + ICONE_SETA_DIR + "</button>";
  }

  function render() {
    var b = canon[pos.i];
    var doCapitulo = mapasDoCapitulo();
    var versos = texto[pos.i].chapters[pos.c - 1];
    var ant = anterior();
    var prox = proximo();
    var h = '<div class="leitor-barra">' +
      '<span class="leitor-nav-topo">' + passos(b, ant, prox) + "</span>" +
      (plano ? '<a class="leitor-plano-link hud" href="/plano-de-leitura/#' + esc(plano.id) + '">' + esc(plano.nome) + "</a>" : "") +
      '<span class="leitor-fonte">' +
      (doCapitulo.length ? '<button type="button" data-mapas aria-haspopup="dialog" aria-label="Mapas (' + doCapitulo.length + ')" title="Mapas">' + ICONE_MAPA + '<span class="leitor-bt-n">' + doCapitulo.length + "</span></button>" : "") +
      '<button type="button" data-leitura aria-haspopup="dialog" aria-label="Leitura" title="Leitura">' + ICONE_CALENDARIO + "</button>" +
      '<button type="button" data-fonte="-1" aria-label="Diminuir letra"' + (tam <= TAM_MIN ? " disabled" : "") + ">A−</button>" +
      '<button type="button" data-fonte="1" aria-label="Aumentar letra"' + (tam >= TAM_MAX ? " disabled" : "") + ">A+</button>" +
      '<button type="button" data-versao aria-haspopup="dialog" title="' + esc(Versao.achar(Versao.atual()).nome) + '">' + Versao.achar(Versao.atual()).sigla + "</button>" +
      "</span></div>";
    h += '<p class="leitor-aviso hud muted" role="status" hidden></p>';
    h += '<article class="leitor-texto"><h1>' + esc(b.nome) + " " + pos.c + "</h1>";
    h += paragrafos(versos) + "</article>";
    // barra de baixo, como nos apps de leitura: capítulo anterior, livro e capítulo, próximo
    h += '<div class="leitor-rodape"><div class="leitor-rodape-in">' +
      '<div class="leitor-passo">' + passos(b, ant, prox) + "</div></div></div>";
    raiz.innerHTML = h;
    raiz.style.setProperty("--leitor-fonte", tam + "rem");
    document.title = b.nome + " " + pos.c + " — Bíblia " + Versao.achar(Versao.atual()).sigla + " — Mapa da Bíblia";
    atualizarOuvir();
    pintar();
  }

  /* ---------- grifar e salvar ---------- */

  function chave(livro, cap, v) {
    return livro + "/" + cap + "/" + v;
  }
  function chaveDe(v) {
    return chave(canon[pos.i].id, pos.c, v);
  }
  function aplicarMarcacoes(lista) {
    marc = {};
    (lista || []).forEach(function (m) {
      marc[chave(m.livro, m.capitulo, m.versiculo)] = m;
    });
  }
  function marcacaoDe(v) {
    return marc[chaveDe(v)] || { livro: canon[pos.i].id, capitulo: pos.c, versiculo: v, grifo: null, salvo: false, temas: [] };
  }
  function copiaMarcacao(m) {
    return { livro: m.livro, capitulo: m.capitulo, versiculo: m.versiculo, grifo: m.grifo || null, salvo: !!m.salvo, temas: (m.temas || []).slice() };
  }
  function temasTodos() {
    var t = {};
    Object.keys(marc).forEach(function (k) {
      (marc[k].temas || []).forEach(function (x) { t[x] = true; });
    });
    return Temas.ordenar(Object.keys(t));
  }

  // põe grifo, salvo e seleção nos versículos já desenhados, sem redesenhar o capítulo
  function pintar() {
    var spans = raiz.querySelectorAll(".leitor-v");
    for (var k = 0; k < spans.length; k++) {
      var v = Number(spans[k].getAttribute("data-v"));
      var m = marc[chaveDe(v)];
      if (m && m.grifo) spans[k].setAttribute("data-grifo", m.grifo);
      else spans[k].removeAttribute("data-grifo");
      if (m && m.salvo) spans[k].setAttribute("data-salvo", "");
      else spans[k].removeAttribute("data-salvo");
      spans[k].classList.toggle("sel", selecao.indexOf(v) >= 0);
    }
    atualizarBarra();
  }

  function alternarVerso(v) {
    var k = selecao.indexOf(v);
    if (k >= 0) selecao.splice(k, 1);
    else selecao.push(v);
    selecao.sort(function (a, b) { return a - b; });
    pintar();
  }

  // "João 3:16-18" ou "João 3:1, 5-6"
  function refSelecao() {
    return Temas.ref(canon[pos.i].nome, pos.c, selecao);
  }

  var ICONE_SALVAR = ICONE_SVG + '<path d="M6 3h12v18l-6-4-6 4z"/></svg>';

  // barra fixa embaixo, só enquanto há versículo selecionado
  function atualizarBarra() {
    if (!barra) {
      barra = document.createElement("div");
      barra.className = "leitor-acoes";
      barra.setAttribute("role", "toolbar");
      barra.setAttribute("aria-label", "Versículos selecionados");
      barra.addEventListener("click", clicarBarra);
      document.body.appendChild(barra);
    }
    if (!selecao.length) {
      barra.hidden = true;
      return;
    }
    var h = '<span class="leitor-acoes-ref hud">' + esc(refSelecao()) + "</span>";
    h += '<button type="button" data-cancelar aria-label="Desmarcar">×</button>';
    if (!Conta || !Conta.usuario()) {
      h += '<a class="leitor-acoes-entrar hud" href="' + esc(Conta.urlEntrar()) + '">Entre para grifar e salvar</a>';
    } else if (!marcPronto) {
      h += '<span class="leitor-acoes-fazer hud faint">Carregando…</span>';
    } else {
      var algumSalvo = selecao.some(function (v) { return marcacaoDe(v).salvo; });
      h += '<span class="leitor-acoes-fazer"><span class="leitor-cores">';
      CORES.forEach(function (c) {
        h += '<button type="button" class="leitor-cor" data-grifo="' + c + '" aria-label="Grifar de ' + c + '"></button>';
      });
      h += '<button type="button" class="leitor-cor sem" data-grifo="" aria-label="Tirar o grifo"></button></span>';
      h += '<button type="button" data-salvar aria-haspopup="dialog"' + (algumSalvo ? ' aria-pressed="true"' : "") + ">" + ICONE_SALVAR + (algumSalvo ? "Salvo" : "Salvar") + "</button></span>";
    }
    barra.innerHTML = h;
    barra.hidden = false;
  }

  function clicarBarra(ev) {
    var t = ev.target.closest("button");
    if (!t) return;
    if (t.hasAttribute("data-cancelar")) {
      selecao = [];
      return pintar();
    }
    if (t.hasAttribute("data-salvar")) return abrirSalvar();
    if (t.hasAttribute("data-grifo")) {
      var cor = t.getAttribute("data-grifo") || null;
      gravarMarcacoes(selecao.map(function (v) {
        var m = copiaMarcacao(marcacaoDe(v));
        m.grifo = cor;
        return m;
      }));
    }
  }

  // aplica na hora e manda para a conta; se falhar, avisa e volta ao que está no servidor
  function gravarMarcacoes(lista) {
    lista.forEach(function (m) {
      var k = chave(m.livro, m.capitulo, m.versiculo);
      if (m.grifo || m.salvo) marc[k] = m;
      else delete marc[k];
    });
    selecao = [];
    pintar();
    avisarVoz("");
    Temas.salvar(lista, function () {
      avisarVoz("Não consegui salvar a marcação. Confira a conexão e tente de novo.");
    }, function (l) {
      aplicarMarcacoes(l);
      pintar();
    });
  }

  // popup Salvar: escolhe os temas (ou cria um) e confirma; ou tira dos salvos
  function abrirSalvar() {
    if (!dlgSalvar) {
      dlgSalvar = Util.dialogo("leitor-dlg leitor-dlg-salvar", function (ev) {
        var t = ev.target.closest("button");
        if (!t) return;
        if (t.hasAttribute("data-confirmar")) return confirmarSalvar(true);
        if (t.hasAttribute("data-remover")) return confirmarSalvar(false);
      });
      // Enter no campo (ou o botão Adicionar) cria o tema
      dlgSalvar.addEventListener("submit", function (ev) {
        ev.preventDefault();
        adicionarTema();
      });
    }
    var temas = temasTodos();
    // já vêm marcados os temas de qualquer versículo selecionado que já esteja salvo
    var comuns = temas.filter(function (t) {
      return selecao.some(function (v) { return marcacaoDe(v).temas.indexOf(t) >= 0; });
    });
    var algumSalvo = selecao.some(function (v) { return marcacaoDe(v).salvo; });
    var h = '<div class="leitor-dlg-topo"><span class="hud muted">Salvar · ' + esc(refSelecao()) + '</span>' + Util.botaoFechar() + '</div>';
    h += '<div class="leitor-temas"><p class="hud faint">Temas</p><div class="leitor-temas-lista">';
    if (temas.length) {
      h += Temas.chips(temas, function (t) { return comuns.indexOf(t) >= 0; });
    } else {
      h += '<span class="leitor-temas-vazio hud faint">Nenhum tema ainda. Crie o primeiro abaixo ou salve sem tema.</span>';
    }
    h += "</div>";
    h += '<form class="leitor-tema-novo"><input type="text" name="tema" maxlength="40" placeholder="Novo tema (ex.: Fé)" autocomplete="off" aria-label="Novo tema"><button type="submit">Adicionar</button></form>';
    h += '<div class="leitor-temas-acoes"><button type="button" class="btn" data-confirmar>Salvar</button>' +
      (algumSalvo ? '<button type="button" class="btn secundario" data-remover>Remover dos salvos</button>' : "") + "</div></div>";
    dlgSalvar.innerHTML = h;
    Util.mostrar(dlgSalvar);
  }

  function adicionarTema() {
    Temas.adicionarNoPopup(dlgSalvar, true);
  }

  function confirmarSalvar(salvo) {
    adicionarTema(); // o que ficou digitado também conta
    var marcados = Temas.marcadosNoPopup(dlgSalvar);
    dlgSalvar.close();
    gravarMarcacoes(selecao.map(function (v) {
      var m = copiaMarcacao(marcacaoDe(v));
      m.salvo = salvo;
      m.temas = salvo ? marcados : [];
      return m;
    }));
  }

  // a cópia guardada aparece na hora; grifar e salvar só depois que o servidor confirmar
  function carregarMarcacoes() {
    selecao = [];
    Temas.carregar(function (lista, confirmada) {
      aplicarMarcacoes(lista);
      marcPronto = confirmada;
      pintar();
    }, function () {
      avisarVoz("Não consegui carregar seus grifos e versículos salvos. Recarregue a página para tentar de novo.");
    });
  }

  // um botão por capítulo do livro, marcando o que está aberto
  function botoesCapitulos(livro) {
    var h = "";
    for (var c = 1; c <= texto[livro].chapters.length; c++) {
      h += '<button type="button" data-i="' + livro + '" data-cap="' + c + '"' + (livro === pos.i && c === pos.c ? ' aria-current="true"' : "") + ">" + c + "</button>";
    }
    return h;
  }

  // abre os capítulos do livro numa seção logo abaixo da linha dele; só uma seção por vez
  function alternarCapitulos(bt) {
    var antiga = dlg.querySelector(".l-secao-caps");
    var mesmo = antiga && antiga.getAttribute("data-do-livro") === bt.getAttribute("data-livro");
    if (antiga) antiga.parentNode.removeChild(antiga);
    if (mesmo) return;
    var livro = Number(bt.getAttribute("data-livro"));
    var sec = document.createElement("div");
    sec.className = "l-grade l-secao-caps";
    sec.setAttribute("data-do-livro", String(livro));
    sec.innerHTML = botoesCapitulos(livro);
    var fim = bt;
    while (fim.nextElementSibling && fim.nextElementSibling.hasAttribute("data-livro") && fim.nextElementSibling.offsetTop === bt.offsetTop) fim = fim.nextElementSibling;
    fim.parentNode.insertBefore(sec, fim.nextSibling);
    sec.scrollIntoView({ block: "nearest" });
  }

  function abrirEscolha(livro) {
    if (!dlg) {
      dlg = Util.dialogo("leitor-dlg", function (ev) {
        var l = ev.target.closest("[data-livro]");
        if (l) return alternarCapitulos(l);
        var c = ev.target.closest("[data-cap]");
        if (c) {
          dlg.close();
          ir(Number(c.getAttribute("data-i")), Number(c.getAttribute("data-cap")));
        }
        if (ev.target.closest("[data-voltar]")) abrirEscolha(null);
      });
    }
    var h = "";
    if (livro == null) {
      h += '<div class="leitor-dlg-topo"><span class="hud muted">Livros</span>' + Util.botaoFechar() + '</div>';
      [["AT", "Antigo Testamento"], ["NT", "Novo Testamento"]].forEach(function (ta) {
        h += '<p class="l-secao l-testamento hud">' + ta[1] + '</p><div class="leitor-dlg-lista">';
        canon.forEach(function (b, i) {
          if (b.ta !== ta[0]) return;
          h += '<button type="button"' + (grupos[b.id] ? ' class="g-' + grupos[b.id] + '"' : "") + ' data-livro="' + i + '"' + (i === pos.i ? ' aria-current="true"' : "") + ">" + esc(b.nome) + "</button>";
        });
        h += "</div>";
      });
    } else {
      h += '<div class="leitor-dlg-topo"><button type="button" class="leitor-dlg-livros" data-voltar aria-label="Voltar para os livros">' + ICONE_SETA_ESQ + ' Livros</button><span class="hud muted">' + esc(canon[livro].nome) + '</span>' + Util.botaoFechar() + '</div>';
      h += '<div class="l-grade">' + botoesCapitulos(livro) + "</div>";
    }
    dlg.innerHTML = h;
    Util.mostrar(dlg);
  }

  // a página Leitura inteira, dentro de um popup (mesma conta, mesmo progresso)
  function abrirLeitura() {
    // a cada abertura recarrega, para cair no livro que está sendo lido
    var url = "/leitura/?embutido&_=" + Date.now() + "#" + canon[pos.i].id + "/" + pos.c;
    if (!dlgLeitura) {
      dlgLeitura = Util.dialogo("leitor-dlg leitor-dlg-leitura");
      dlgLeitura.innerHTML =
        '<div class="leitor-dlg-topo"><span class="hud muted">Leitura</span>' + Util.botaoFechar() + '</div>' +
        '<iframe title="Leitura"></iframe>';
    }
    var quadro = dlgLeitura.querySelector("iframe");
    quadro.setAttribute("src", url);
    Util.mostrar(dlgLeitura);
  }

  // popup com os mapas do capítulo: troca de um para outro sem fechar
  function mostrarApoio(lista, k) {
    dlgMapas.setAttribute("data-k", k);
    var ant = dlgMapas.querySelector('[data-mapas-passo="-1"]');
    var prox = dlgMapas.querySelector('[data-mapas-passo="1"]');
    ant.disabled = k === 0;
    prox.disabled = k === lista.length - 1;
    var quadro = dlgMapas.querySelector("iframe");
    var m = lista[k];
    var abas = dlgMapas.querySelectorAll("[data-aba]");
    for (var j = 0; j < abas.length; j++) {
      if (j === k) {
        abas[j].setAttribute("aria-current", "true");
        if (abas[j].scrollIntoView) abas[j].scrollIntoView({ block: "nearest", inline: "nearest" });
      } else abas[j].removeAttribute("aria-current");
    }
    dlgMapas.querySelector(".leitor-mapas-balao").hidden = true;
    quadro.setAttribute("title", m.titulo);
    quadro.setAttribute("src", Util.comParam(m.url, "embutido&cap=" + pos.c + "&livro=" + canon[pos.i].id));
  }

  // clicar no nome do mapa abre esse mapa e mostra, num balão, o que ele cobre; clicar de novo fecha
  function clicarAba(lista, aba) {
    var k = Number(aba.getAttribute("data-aba"));
    var balao = dlgMapas.querySelector(".leitor-mapas-balao");
    var igual = !balao.hidden && balao.getAttribute("data-k") === String(k);
    if (Number(dlgMapas.getAttribute("data-k")) !== k) mostrarApoio(lista, k);
    if (igual) {
      balao.hidden = true;
      return;
    }
    var m = lista[k];
    balao.textContent = m.tipo + " · " + m.ref + " — " + m.resumo;
    balao.setAttribute("data-k", String(k));
    balao.hidden = false;
    var d = dlgMapas.getBoundingClientRect();
    var a = aba.getBoundingClientRect();
    var esq = Math.max(8, Math.min(a.left - d.left, d.width - balao.offsetWidth - 8));
    balao.style.left = esq + "px";
    balao.style.top = a.bottom - d.top + 8 + "px";
  }

  function abrirMapas() {
    var lista = mapasDoCapitulo();
    if (!lista.length) return;
    listaMapas = lista;
    if (!dlgMapas) {
      dlgMapas = Util.dialogo("leitor-dlg leitor-dlg-leitura leitor-dlg-mapas", function (ev) {
        var aba = ev.target.closest("[data-aba]");
        if (aba) return clicarAba(listaMapas, aba);
        dlgMapas.querySelector(".leitor-mapas-balao").hidden = true;
        var passo = ev.target.closest("[data-mapas-passo]");
        if (passo && !passo.disabled) {
          var k = Number(dlgMapas.getAttribute("data-k")) + Number(passo.getAttribute("data-mapas-passo"));
          if (k >= 0 && k < listaMapas.length) mostrarApoio(listaMapas, k);
        }
      });
    }
    var h = '<div class="leitor-dlg-topo"><span class="hud muted">Mapas</span>' + Util.botaoFechar() + '</div>' +
      '<div class="leitor-mapas-abas"><div class="leitor-mapas-lista" role="tablist">';
    lista.forEach(function (m, k) {
      h += '<button type="button" data-aba="' + k + '">' + esc(m.titulo) + "</button>";
    });
    h += '</div><span class="leitor-mapas-passos">' +
      '<button type="button" data-mapas-passo="-1" aria-label="Mapa anterior">' + ICONE_SETA_ESQ + '</button>' +
      '<button type="button" data-mapas-passo="1" aria-label="Próximo mapa">' + ICONE_SETA_DIR + '</button></span>';
    h += '</div><div class="leitor-mapas-balao" role="status" hidden></div><iframe></iframe>';
    dlgMapas.innerHTML = h;
    mostrarApoio(lista, 0);
    Util.mostrar(dlgMapas);
  }

  // troca o texto da versão; se não carregar, volta à anterior
  function trocarVersao(id, anterior) {
    Versao.carregar(id).then(function (biblia) {
      texto = biblia;
      render();
    }, function () {
      Versao.definir(anterior);
    });
  }

  raiz.addEventListener("click", function (ev) {
    var verso = ev.target.closest && ev.target.closest(".leitor-v");
    if (verso) return alternarVerso(Number(verso.getAttribute("data-v")));
    var t = ev.target.closest && ev.target.closest("button");
    if (!t || t.disabled) return;
    if (t.hasAttribute("data-versao")) return Versao.popup(trocarVersao);
    if (t.hasAttribute("data-mapas")) return abrirMapas();
    if (t.hasAttribute("data-leitura")) return abrirLeitura();
    if (t.hasAttribute("data-ouvir")) return falando ? parar() : ouvir();
    if (t.hasAttribute("data-escolher")) return abrirEscolha(null);
    if (t.hasAttribute("data-fonte")) {
      tam = Math.min(TAM_MAX, Math.max(TAM_MIN, Math.round((tam + Number(t.getAttribute("data-fonte")) * 0.1) * 10) / 10));
      guardarLeitor({ livro: canon[pos.i].id, cap: pos.c, tam: tam });
      return render();
    }
    var alvo = t.getAttribute("data-nav") === "ant" ? anterior() : t.getAttribute("data-nav") === "prox" ? proximo() : null;
    if (alvo) ir(alvo.i, alvo.c);
  });

  // deslizar para o lado troca de capítulo (no celular), respeitando o modo plano
  var toqueIni = null;
  raiz.addEventListener("touchstart", function (ev) {
    if (ev.touches.length !== 1 || ev.target.closest("button, a")) return (toqueIni = null);
    toqueIni = { x: ev.touches[0].clientX, y: ev.touches[0].clientY, t: Date.now() };
  }, { passive: true });
  raiz.addEventListener("touchend", function (ev) {
    var ini = toqueIni;
    toqueIni = null;
    if (!ini || !ev.changedTouches.length || !canon.length) return;
    var dx = ev.changedTouches[0].clientX - ini.x;
    var dy = ev.changedTouches[0].clientY - ini.y;
    if (Date.now() - ini.t > 700 || Math.abs(dx) < 70 || Math.abs(dy) > Math.abs(dx) * 0.6) return;
    var alvo = dx > 0 ? anterior() : proximo();
    if (alvo) ir(alvo.i, alvo.c);
  }, { passive: true });

  document.addEventListener("keydown", function (ev) {
    if (!canon.length || (dlg && dlg.open) || (dlgLeitura && dlgLeitura.open) || (dlgMapas && dlgMapas.open) || (dlgSalvar && dlgSalvar.open) || ev.altKey || ev.ctrlKey || ev.metaKey) return;
    if (ev.key === "Escape" && selecao.length) {
      selecao = [];
      return pintar();
    }
    var alvo = ev.key === "ArrowLeft" ? anterior() : ev.key === "ArrowRight" ? proximo() : null;
    if (alvo) ir(alvo.i, alvo.c);
  });

  // as duas barras somem ao descer o texto e voltam ao subir
  var ultimoY = window.pageYOffset || 0;
  window.addEventListener("scroll", function () {
    var y = window.pageYOffset || 0;
    if (Math.abs(y - ultimoY) < 6) return;
    document.body.classList.toggle("leitor-rolou", y > ultimoY && y > 80);
    ultimoY = y;
  }, { passive: true });

  window.addEventListener("hashchange", function () {
    var p = doHash();
    if (p && (p.i !== pos.i || p.c !== pos.c)) {
      parar();
      pos = p;
      selecao = [];
      render();
      window.scrollTo(0, 0);
    }
  });

  window.addEventListener("beforeunload", function () {
    if (voz) voz.cancel();
  });

  // id do plano da URL (?plano=id; ?mapa=id é o nome antigo), ou "" sem plano
  var idPlano = Util.param("plano") || Util.param("mapa") || "";

  function montarPlano(lista, listaEras) {
    if (!idPlano || !lista) return;
    var porId = {};
    canon.forEach(function (b, i) { porId[b.id] = i; });
    (lista.planos || []).forEach(function (m) { if (m.id === idPlano) plano = m; });
    if (!plano) return;
    (listaEras.eras || []).forEach(function (e) { eras[e.id] = e; });
    plano.etapas.forEach(function (et, e) {
      et.trechos.forEach(function (tr, t) {
        for (var c = tr.de; c <= tr.ate; c++) {
          indice[porId[tr.livro] + ":" + c] = ordem.length;
          ordem.push({ i: porId[tr.livro], c: c, e: e, t: t });
        }
      });
    });
  }

  function iniciar(listaCanon, biblia, planos, listaEras) {
    canon = listaCanon;
    texto = biblia;
    montarPlano(planos, listaEras);
    var salvo = (Conta && Conta.usuario() && Conta.config().leitor) || ler(KEY, {});
    if (typeof salvo.tam === "number" && salvo.tam >= TAM_MIN && salvo.tam <= TAM_MAX) tam = salvo.tam;
    var p = doHash();
    if (plano && !p) {
      var guardado = (estadoPlano().pos || {})[plano.id];
      var m = guardado && /^([a-z0-9]+)\/(\d+)$/.exec(guardado);
      var s = 0;
      for (var k = 0; m && k < canon.length; k++) {
        if (canon[k].id === m[1] && indice[k + ":" + m[2]] != null) s = indice[k + ":" + m[2]];
      }
      p = ordem[s];
    }
    if (!p && !plano && salvo.livro) {
      for (var i = 0; i < canon.length; i++) {
        if (canon[i].id === salvo.livro && salvo.cap >= 1 && salvo.cap <= texto[i].chapters.length) p = { i: i, c: salvo.cap };
      }
    }
    pos = p || { i: 0, c: 1 };
    render();
    carregarMarcacoes();
    if (Conta) {
      Conta.aoMudar(function (evento, u, mudou) {
        if (mudou) carregarMarcacoes();
      });
    }
  }

  Promise.all([
    Util.json("/compartilhado/dados/canon.json"),
    idPlano ? Util.json("/plano-de-leitura/planos.json") : null,
    idPlano ? Util.json("/compartilhado/dados/eras.json") : null,
    Util.json("/mapas/mapas.json").catch(function () { return { mapas: [] }; }),
    Util.json("/linha-do-tempo/livros.json").catch(function () { return { livros: [] }; })
  ]).then(function (r) {
    mapas = r[3].mapas || [];
    (r[4].livros || []).forEach(function (l) { grupos[l.id] = l.grupo; });
    // a sessão vem do navegador (rápido): com ela, as configurações guardadas já valem (a versão escolhida também)
    return (Conta ? Conta.pronto() : Promise.resolve()).then(function () {
      return Versao.carregar(Versao.atual());
    }).then(function (biblia) {
      iniciar(r[0], biblia, r[1], r[2]);
    });
  }).catch(function () {
    Util.falha(raiz, "o texto");
  });
})();
