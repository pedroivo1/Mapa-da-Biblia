// Leitor da Bíblia (biblia/index.html): texto NVI, livros, capítulos, tamanho da letra, voz.
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
  var dlgLeitura = null;
  var dlgMapas = null;
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
      h += '<span class="leitor-v" data-v="' + (v + 1) + '"><sup>' + (v + 1) + "</sup>" + esc(versos[v]) + "</span>";
      aberta = ((aberta ? 1 : 0) + aspas) % 2 === 1;
      fechouAgora = aspas > 0 && !aberta;
    }
    return h + "</p>";
  }

  function bannerPlano() {
    var n = indice[pos.i + ":" + pos.c];
    var p = n == null ? null : ordem[n];
    if (!p) return "";
    var etapa = plano.etapas[p.e];
    var era = eras[etapa.era] || { nome: etapa.nome, periodo: etapa.periodo };
    var tr = etapa.trechos[p.t];
    var sai = "/biblia/" + location.hash;
    return '<div class="leitor-plano"><p class="hud muted"><strong>' + esc(plano.nome) + "</strong> · " + esc(era.nome || "") +
      (era.periodo ? " (" + esc(era.periodo) + ")" : "") + " · " + (n + 1) + "/" + ordem.length + "</p>" +
      (tr.nota ? '<p class="hud faint">' + esc(tr.nota) + "</p>" : "") +
      '<p class="hud"><a href="/plano-de-leitura/">Ver o plano</a> · <a href="' + esc(sai) + '">Sair do plano (ordem dos livros)</a></p></div>';
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

  var ICONE_SETA = '<svg class="leitor-seta" viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">';
  var ICONE_SETA_ESQ = ICONE_SETA + '<path d="M19 12H5M11 6l-6 6 6 6"/></svg>';
  var ICONE_SETA_DIR = ICONE_SETA + '<path d="M5 12h14M13 6l6 6-6 6"/></svg>';

  function render() {
    var b = canon[pos.i];
    var doCapitulo = mapasDoCapitulo();
    var versos = texto[pos.i].chapters[pos.c - 1];
    var ant = anterior();
    var prox = proximo();
    var h = '<div class="leitor-barra">' +
      '<button type="button" data-escolher aria-haspopup="dialog"><span class="leitor-ref">' + esc(b.nome) + " " + pos.c + "</span> ▾</button>" +
      '<span class="leitor-fonte">' +
      (doCapitulo.length ? '<button type="button" data-mapas aria-haspopup="dialog" aria-label="Mapas (' + doCapitulo.length + ')">' + ICONE_MAPA + '<span class="leitor-bt-txt">Mapas</span> (' + doCapitulo.length + ")</button>" : "") +
      '<button type="button" data-leitura aria-haspopup="dialog" aria-label="Leitura">' + ICONE_CALENDARIO + '<span class="leitor-bt-txt">Leitura</span></button>' +
      '<button type="button" data-fonte="-1" aria-label="Diminuir letra"' + (tam <= TAM_MIN ? " disabled" : "") + ">A−</button>" +
      '<button type="button" data-fonte="1" aria-label="Aumentar letra"' + (tam >= TAM_MAX ? " disabled" : "") + ">A+</button>" +
      "</span></div>";
    if (plano) h += bannerPlano();
    h += '<p class="leitor-aviso hud muted" role="status" hidden></p>';
    h += '<article class="leitor-texto"><h1>' + esc(b.nome) + " " + pos.c + "</h1>";
    h += paragrafos(versos) + "</article>";
    h += '<div class="leitor-fim">' +
      '<button type="button" data-nav="ant"' + (ant ? "" : " disabled") + ' aria-label="Capítulo anterior">' + ICONE_SETA_ESQ + "</button>" +
      '<button type="button" data-nav="prox"' + (prox ? "" : " disabled") + ' aria-label="Próximo capítulo">' + ICONE_SETA_DIR + "</button></div>";
    raiz.innerHTML = h;
    raiz.style.setProperty("--leitor-fonte", tam + "rem");
    document.title = b.nome + " " + pos.c + " — Bíblia NVI — Mapa da Bíblia";
    pintar();
  }

  /* ---------- grifar e salvar ---------- */

  function chaveDe(v) {
    return canon[pos.i].id + "/" + pos.c + "/" + v;
  }
  function aplicarMarcacoes(lista) {
    marc = {};
    (lista || []).forEach(function (m) {
      marc[m.livro + "/" + m.capitulo + "/" + m.versiculo] = m;
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
    return Object.keys(t).sort(function (a, b) { return a.localeCompare(b, "pt-BR"); });
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
    var partes = [];
    for (var k = 0; k < selecao.length; k++) {
      var ini = selecao[k], fim = ini;
      while (k + 1 < selecao.length && selecao[k + 1] === fim + 1) fim = selecao[++k];
      partes.push(ini === fim ? String(ini) : ini + "-" + fim);
    }
    return canon[pos.i].nome + " " + pos.c + ":" + partes.join(", ");
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
      h += '<a class="leitor-acoes-entrar hud" href="' + esc(Conta ? Conta.urlEntrar() : "/conta/") + '">Entre para grifar e salvar</a>';
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
      var k = m.livro + "/" + m.capitulo + "/" + m.versiculo;
      if (m.grifo || m.salvo) marc[k] = m;
      else delete marc[k];
    });
    selecao = [];
    pintar();
    avisarVoz("");
    Conta.salvarMarcacoes(lista).catch(function () {
      avisarVoz("Não consegui salvar a marcação. Confira a conexão e tente de novo.");
      Conta.carregarMarcacoes().then(function (l) {
        aplicarMarcacoes(l);
        pintar();
      }, function () {});
    });
  }

  // popup Salvar: escolhe os temas (ou cria um) e confirma; ou tira dos salvos
  function abrirSalvar() {
    if (!dlgSalvar) {
      dlgSalvar = document.createElement("dialog");
      dlgSalvar.className = "leitor-dlg leitor-dlg-salvar";
      dlgSalvar.addEventListener("click", function (ev) {
        if (ev.target === dlgSalvar || ev.target.closest("[data-fechar]")) return dlgSalvar.close();
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
      document.body.appendChild(dlgSalvar);
    }
    var temas = temasTodos();
    // já vêm marcados os temas de qualquer versículo selecionado que já esteja salvo
    var comuns = temas.filter(function (t) {
      return selecao.some(function (v) { return marcacaoDe(v).temas.indexOf(t) >= 0; });
    });
    var algumSalvo = selecao.some(function (v) { return marcacaoDe(v).salvo; });
    var h = '<div class="leitor-dlg-topo"><span class="hud muted">Salvar · ' + esc(refSelecao()) + '</span><button type="button" data-fechar>Fechar</button></div>';
    h += '<div class="leitor-temas"><p class="hud faint">Temas</p><div class="leitor-temas-lista">';
    if (temas.length) {
      temas.forEach(function (t) {
        h += '<label class="chip"><input type="checkbox" value="' + esc(t) + '"' + (comuns.indexOf(t) >= 0 ? " checked" : "") + "><span>" + esc(t) + "</span></label>";
      });
    } else {
      h += '<span class="leitor-temas-vazio hud faint">Nenhum tema ainda. Crie o primeiro abaixo ou salve sem tema.</span>';
    }
    h += "</div>";
    h += '<form class="leitor-tema-novo"><input type="text" name="tema" maxlength="40" placeholder="Novo tema (ex.: Fé)" autocomplete="off" aria-label="Novo tema"><button type="submit">Adicionar</button></form>';
    h += '<div class="leitor-temas-acoes"><button type="button" class="btn" data-confirmar>Salvar</button>' +
      (algumSalvo ? '<button type="button" class="btn secundario" data-remover>Remover dos salvos</button>' : "") + "</div></div>";
    dlgSalvar.innerHTML = h;
    if (!dlgSalvar.open) dlgSalvar.showModal();
  }

  function adicionarTema() {
    var campo = dlgSalvar.querySelector('input[name="tema"]');
    var nome = campo.value.replace(/\s+/g, " ").trim();
    if (!nome) return;
    var lista = dlgSalvar.querySelector(".leitor-temas-lista");
    var caixas = lista.querySelectorAll("input");
    var existe = false;
    for (var k = 0; k < caixas.length; k++) {
      if (caixas[k].value.toLowerCase() === nome.toLowerCase()) {
        caixas[k].checked = true;
        existe = true;
      }
    }
    if (!existe) {
      var vazio = lista.querySelector(".leitor-temas-vazio");
      if (vazio) lista.removeChild(vazio);
      var rotulo = document.createElement("label");
      rotulo.className = "chip";
      var caixa = document.createElement("input");
      caixa.type = "checkbox";
      caixa.value = nome;
      caixa.checked = true;
      var txt = document.createElement("span");
      txt.textContent = nome;
      rotulo.appendChild(caixa);
      rotulo.appendChild(txt);
      lista.appendChild(rotulo);
    }
    campo.value = "";
    campo.focus();
  }

  function confirmarSalvar(salvo) {
    adicionarTema(); // o que ficou digitado também conta
    var marcados = [];
    var caixas = dlgSalvar.querySelectorAll(".leitor-temas-lista input");
    for (var k = 0; k < caixas.length; k++) if (caixas[k].checked) marcados.push(caixas[k].value);
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
    marcPronto = false;
    selecao = [];
    if (!Conta || !Conta.usuario()) {
      aplicarMarcacoes([]);
      return pintar();
    }
    aplicarMarcacoes(Conta.marcacoesGuardadas() || []);
    pintar();
    var u = Conta.usuario().id;
    Conta.carregarMarcacoes().then(function (lista) {
      if (!Conta.usuario() || Conta.usuario().id !== u) return;
      aplicarMarcacoes(lista);
      marcPronto = true;
      pintar();
    }, function () {
      avisarVoz("Não consegui carregar seus grifos e versículos salvos. Recarregue a página para tentar de novo.");
    });
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
      h += '<div class="leitor-dlg-topo"><button type="button" data-voltar aria-label="Voltar para os livros">' + ICONE_SETA_ESQ + '</button><span class="hud muted">' + esc(canon[livro].nome) + '</span><button type="button" data-fechar>Fechar</button></div>';
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
    var url = "/leitura/?embutido&_=" + Date.now() + "#" + canon[pos.i].id + "/" + pos.c;
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
      if (j === k) abas[j].setAttribute("aria-current", "true");
      else abas[j].removeAttribute("aria-current");
    }
    dlgMapas.querySelector(".leitor-mapas-balao").hidden = true;
    quadro.setAttribute("title", m.titulo);
    quadro.setAttribute("src", m.url + (m.url.indexOf("?") < 0 ? "?" : "&") + "embutido&cap=" + pos.c + "&livro=" + canon[pos.i].id);
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
    if (!dlgMapas) {
      dlgMapas = document.createElement("dialog");
      dlgMapas.className = "leitor-dlg leitor-dlg-leitura leitor-dlg-mapas";
      document.body.appendChild(dlgMapas);
    }
    var h = '<div class="leitor-dlg-topo"><span class="hud muted">Mapas</span><button type="button" data-fechar>Fechar</button></div>' +
      '<div class="leitor-mapas-abas" role="tablist">';
    lista.forEach(function (m, k) {
      h += '<button type="button" data-aba="' + k + '">' + esc(m.titulo) + "</button>";
    });
    h += '<span class="leitor-mapas-passos">' +
      '<button type="button" data-mapas-passo="-1" aria-label="Mapa anterior">' + ICONE_SETA_ESQ + '</button>' +
      '<button type="button" data-mapas-passo="1" aria-label="Próximo mapa">' + ICONE_SETA_DIR + '</button></span>';
    h += '</div><div class="leitor-mapas-balao" role="status" hidden></div><iframe></iframe>';
    dlgMapas.innerHTML = h;
    dlgMapas.onclick = function (ev) {
      if (ev.target === dlgMapas || ev.target.closest("[data-fechar]")) return dlgMapas.close();
      var aba = ev.target.closest("[data-aba]");
      if (aba) return clicarAba(lista, aba);
      dlgMapas.querySelector(".leitor-mapas-balao").hidden = true;
      var passo = ev.target.closest("[data-mapas-passo]");
      if (passo && !passo.disabled) {
        var k = Number(dlgMapas.getAttribute("data-k")) + Number(passo.getAttribute("data-mapas-passo"));
        if (k >= 0 && k < lista.length) mostrarApoio(lista, k);
      }
    };
    mostrarApoio(lista, 0);
    if (!dlgMapas.open) dlgMapas.showModal();
  }

  raiz.addEventListener("click", function (ev) {
    var verso = ev.target.closest && ev.target.closest(".leitor-v");
    if (verso) return alternarVerso(Number(verso.getAttribute("data-v")));
    var t = ev.target.closest && ev.target.closest("button");
    if (!t || t.disabled) return;
    if (t.hasAttribute("data-mapas")) return abrirMapas();
    if (t.hasAttribute("data-leitura")) return abrirLeitura();
    if (t.hasAttribute("data-ouvir")) return falando ? parar() : ouvir();
    if (t.hasAttribute("data-escolher")) return abrirEscolha(pos.i);
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

  function montarPlano(lista, listaEras) {
    var id = (/[?&](?:plano|mapa)=([a-z0-9-]+)/.exec(location.search) || [])[1];
    if (!id || !lista) return;
    var porId = {};
    canon.forEach(function (b, i) { porId[b.id] = i; });
    (lista.planos || []).forEach(function (m) { if (m.id === id) plano = m; });
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

  var comPlano = /[?&](?:plano|mapa)=/.test(location.search);
  Promise.all([
    fetch("/compartilhado/dados/canon.json").then(function (r) { return r.json(); }),
    fetch("/biblia/nvi.json").then(function (r) { return r.json(); }),
    comPlano ? fetch("/plano-de-leitura/planos.json").then(function (r) { return r.json(); }) : null,
    comPlano ? fetch("/compartilhado/dados/eras.json").then(function (r) { return r.json(); }) : null,
    fetch("/mapas/mapas.json").then(function (r) { return r.json(); }).catch(function () { return { mapas: [] }; })
  ]).then(function (r) {
    mapas = r[4].mapas || [];
    // a sessão vem do navegador (rápido): com ela, as configurações guardadas já valem
    return (Conta ? Conta.pronto() : Promise.resolve()).then(function () {
      iniciar(r[0], r[1], r[2], r[3]);
    });
  }).catch(function () {
    raiz.innerHTML = '<p class="vazio">Não consegui carregar o texto. Abra por um servidor local (<code>python -m http.server</code>).</p>';
  });
})();
