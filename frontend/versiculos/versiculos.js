// Versículos salvos (versiculos/index.html): a lista do que a pessoa salvou no leitor, por tema,
// e o modo decorar (um versículo aleatório dos salvos, só a referência; um botão mostra o texto).
// Lê compartilhado/dados/canon.json (nomes), a versão escolhida em biblia/versoes/ (texto) e as marcações da conta
// (Conta.carregarMarcacoes, tabela marcacoes). Remover tira dos salvos e mantém o grifo. Exige login.
(function () {
  "use strict";

  var esc = Util.esc;
  var Conta = window.Conta;
  var raiz = document.getElementById("versiculos");
  var canon = [];
  var texto = [];
  var ordem = {}; // id do livro -> índice no canon
  var linhas = []; // marcações da conta, como vieram
  var itens = []; // salvos, agrupados: versículos seguidos do mesmo capítulo e com os mesmos temas viram um item
  var sel = []; // filtro por temas (vários): nomes dos temas marcados, "" = sem tema; vazio = todos
  var menuAberto = false; // o dropdown Temas
  var decorar = null; // { fila: [índices em filtrados], k, lista, mostrado }
  var pronto = false; // o servidor confirmou a lista: só então remover

  function chaveTemas(temas) {
    return Temas.ordenar((temas || []).slice()).join("\n");
  }

  function agrupar(lista) {
    var vs = [];
    lista.forEach(function (m) {
      var i = ordem[m.livro];
      if (!m.salvo || i == null || !texto[i] || !texto[i].chapters[m.capitulo - 1]) return;
      var t = texto[i].chapters[m.capitulo - 1][m.versiculo - 1];
      if (t == null) return;
      vs.push({ i: i, cap: m.capitulo, v: m.versiculo, t: t, temas: m.temas || [], chave: chaveTemas(m.temas) });
    });
    vs.sort(function (a, b) { return a.i - b.i || a.cap - b.cap || a.v - b.v; });
    var r = [];
    vs.forEach(function (x) {
      var u = r[r.length - 1];
      if (u && u.i === x.i && u.cap === x.cap && u.ate === x.v - 1 && u.chave === x.chave) {
        u.ate = x.v;
        u.versos.push(x);
      } else {
        r.push({ i: x.i, livro: canon[x.i].id, cap: x.cap, de: x.v, ate: x.v, temas: x.temas, chave: x.chave, versos: [x] });
      }
    });
    return r;
  }

  function refDe(it) {
    return Temas.ref(canon[it.i].nome, it.cap, it.versos.map(function (x) { return x.v; }));
  }

  function textoDe(it) {
    return it.versos.map(function (x) {
      return (it.versos.length > 1 ? "<sup>" + x.v + "</sup>" : "") + esc(x.t);
    }).join(" ");
  }

  // temas criados na página (ainda sem versículo) ficam na conta, em Conta.config().temas
  function temasCriados() {
    var c = Conta && Conta.config().temas;
    return c instanceof Array ? c : [];
  }

  function temasTodos() {
    var t = {};
    temasCriados().forEach(function (x) { t[x] = t[x] || 0; });
    itens.forEach(function (it) {
      it.temas.forEach(function (x) { t[x] = (t[x] || 0) + 1; });
    });
    return Temas.ordenar(Object.keys(t)).map(function (n) {
      return { nome: n, n: t[n] };
    });
  }

  function filtrados() {
    if (!sel.length) return itens;
    return itens.filter(function (it) {
      return sel.some(function (x) { return x === "" ? !it.temas.length : it.temas.indexOf(x) >= 0; });
    });
  }

  function nomeFiltro() {
    if (!sel.length) return "Todos";
    return sel.map(function (x) { return x === "" ? "Sem tema" : x; }).join(", ");
  }

  // o filtro de temas fica guardado (conta e navegador): a lista volta como a pessoa deixou
  function guardarFiltro() {
    if (Conta && Conta.usuario()) Conta.guardarVista("versiculos_vista", { temas: sel.slice() });
  }

  function adicionarTema(nome) {
    nome = Temas.normalizar(nome);
    if (!nome) return;
    var ja = temasTodos().filter(function (t) { return t.nome.toLowerCase() === nome.toLowerCase(); })[0];
    if (ja) nome = ja.nome;
    else Conta.salvarConfig("temas", temasCriados().concat([nome]));
    if (sel.indexOf(nome) < 0) sel.push(nome);
  }

  function htmlMenu(semTema) {
    var h = '<div class="versiculos-menu" role="group" aria-label="Filtrar por temas">' +
      '<form class="versiculos-tema-novo"><input type="text" name="tema" maxlength="40" placeholder="Adicionar tema" aria-label="Adicionar tema" autocomplete="off" />' +
      '<button type="submit" class="btn">Adicionar</button></form>' +
      '<div class="versiculos-menu-marcar"><button type="button" class="chip" data-marcar-todos>Todos</button><button type="button" class="chip" data-limpar>Limpar</button></div>';
    temasTodos().forEach(function (t) {
      h += '<label class="versiculos-menu-item"><input type="checkbox" data-tema="' + esc(t.nome) + '"' + (sel.indexOf(t.nome) >= 0 ? " checked" : "") + " /><span>" + esc(t.nome) + '</span><span class="faint">' + t.n + "</span></label>";
    });
    h += '<label class="versiculos-menu-item"><input type="checkbox" data-tema=""' + (sel.indexOf("") >= 0 ? " checked" : "") + " /><span>Sem tema</span><span class=\"faint\">" + semTema + "</span></label></div>";
    return h;
  }

  /* ---------- lista ---------- */

  // a lista fica sempre desenhada; o modo decorar abre por cima, num popup
  function render() {
    renderLista();
    if (decorar) renderDecorar();
    else if (dlgDecorar && dlgDecorar.open) dlgDecorar.close();
  }

  function renderLista() {
    if (!Conta || !Conta.usuario()) {
      raiz.innerHTML = '<p class="vazio">Entre na sua conta para salvar versículos e decorá-los. ' +
        '<a class="btn" href="' + esc(Conta.urlEntrar()) + '">Entrar</a></p>';
      return;
    }
    if (!itens.length) {
      raiz.innerHTML = '<p class="vazio">Você ainda não salvou nenhum versículo. Na Bíblia, toque num versículo e escolha Salvar. ' +
        '<a class="chip" href="/biblia/">Abrir a Bíblia</a></p>';
      return;
    }
    var lista = filtrados();
    var semTema = itens.filter(function (it) { return !it.temas.length; }).length;
    var h = '<div class="versiculos-filtros" role="group" aria-label="Temas">' +
      '<span class="versiculos-temas"><button type="button" class="btn secundario" data-menu aria-haspopup="true" aria-expanded="' + menuAberto + '">Temas' + (sel.length ? " (" + sel.length + ")" : "") + " " + Util.seta("baixo", 12) + "</button>" +
      (menuAberto ? htmlMenu(semTema) : "") + "</span>" +
      '<button type="button" class="btn" data-decorar' + (lista.length ? "" : " disabled") + ">Decorar</button>" +
      '<span class="hud faint">' + lista.length + (lista.length === 1 ? " versículo" : " versículos") + "</span></div>";
    h += '<ol class="versiculos-lista">';
    lista.forEach(function (it) {
      h += '<li class="versiculos-item">' +
        '<p class="versiculos-ref hud muted"><a href="/biblia/#' + esc(it.livro) + "/" + it.cap + '">' + esc(refDe(it)) + "</a>" +
        (it.temas.length ? ' <span class="faint">· ' + it.temas.map(esc).join(" · ") + "</span>" : "") + "</p>" +
        '<p class="versiculos-texto">' + textoDe(it) + "</p>" +
        '<p class="versiculos-item-acoes"><button type="button" class="chip" data-editar="' + itens.indexOf(it) + '"' + (pronto ? "" : " disabled") + ">Editar</button></p></li>";
    });
    h += "</ol>";
    raiz.innerHTML = h;
  }

  /* ---------- modo decorar ---------- */

  function embaralhar(n, evitar) {
    var a = [];
    for (var i = 0; i < n; i++) a.push(i);
    for (var j = a.length - 1; j > 0; j--) {
      var k = Math.floor(Math.random() * (j + 1));
      var t = a[j];
      a[j] = a[k];
      a[k] = t;
    }
    // não repete de cara o que acabou de aparecer
    if (n > 1 && a[0] === evitar) {
      a.push(a.shift());
    }
    return a;
  }

  function entrarDecorar() {
    var lista = filtrados();
    if (!lista.length) return;
    decorar = { lista: lista, fila: embaralhar(lista.length, -1), k: 0, mostrado: false };
    render();
  }

  function proximoDecorar() {
    decorar.k++;
    if (decorar.k >= decorar.fila.length) {
      decorar.fila = embaralhar(decorar.lista.length, decorar.fila[decorar.fila.length - 1]);
      decorar.k = 0;
    }
    decorar.mostrado = false;
    render();
  }

  var dlgDecorar = null;

  function renderDecorar() {
    if (!dlgDecorar) {
      dlgDecorar = Util.dialogo("leitor-dlg versiculos-dlg versiculos-dlg-decorar", function (ev) {
        if (ev.target.closest("[data-mostrar]")) {
          decorar.mostrado = true;
          return render();
        }
        if (ev.target.closest("[data-proximo]")) return proximoDecorar();
      });
      dlgDecorar.addEventListener("close", function () { decorar = null; });
    }
    var it = decorar.lista[decorar.fila[decorar.k]];
    var h = '<div class="leitor-dlg-topo"><span class="hud muted">Decorar · ' + esc(nomeFiltro()) + " · " + (decorar.k + 1) + "/" + decorar.fila.length + "</span>" + Util.botaoFechar() + "</div>" +
      '<section class="versiculos-decorar" aria-live="polite">' +
      '<h2 class="versiculos-decorar-ref">' + esc(refDe(it)) + "</h2>" +
      '<p class="versiculos-decorar-texto"' + (decorar.mostrado ? "" : " hidden") + ">" + textoDe(it) + "</p>" +
      '<p class="versiculos-decorar-dica hud faint"' + (decorar.mostrado ? " hidden" : "") + ">Diga de cor e depois confira.</p>" +
      '<div class="versiculos-decorar-acoes">' +
      (decorar.mostrado
        ? '<button type="button" class="btn" data-proximo>Próximo</button>'
        : '<button type="button" class="btn" data-mostrar>Mostrar</button><button type="button" class="btn secundario" data-proximo>Pular</button>') +
      "</div>" +
      '<p class="hud faint">Espaço mostra · seta para a direita avança · Esc sai</p>' +
      "</section>";
    dlgDecorar.innerHTML = h;
    Util.mostrar(dlgDecorar);
    var foco = dlgDecorar.querySelector("[data-mostrar], [data-proximo]");
    if (foco) foco.focus();
  }

  /* ---------- ações ---------- */

  // as marcações novas dos versículos do item (o grifo de cada um fica como está)
  function alvoDe(it, salvo, temas) {
    return it.versos.map(function (x) {
      var m = null;
      linhas.forEach(function (l) {
        if (l.livro === it.livro && l.capitulo === it.cap && l.versiculo === x.v) m = l;
      });
      return { livro: it.livro, capitulo: it.cap, versiculo: x.v, grifo: m ? m.grifo : null, salvo: salvo, temas: temas.slice() };
    });
  }

  // aplica na hora e manda para a conta; se falhar, avisa e volta ao que está no servidor.
  // Linha sem grifo e sem salvar some da lista
  function gravar(alvo, erro) {
    aplicar(linhas.filter(function (l) {
      return !alvo.some(function (a) { return a.livro === l.livro && a.capitulo === l.capitulo && a.versiculo === l.versiculo; });
    }).concat(alvo.filter(function (a) { return a.grifo || a.salvo; })));
    render();
    Temas.salvar(alvo, function () {
      aviso(erro);
    }, function (l) {
      aplicar(l);
      render();
    });
  }

  function remover(it) {
    if (!pronto) return;
    gravar(alvoDe(it, false, []), "Não consegui remover. Confira a conexão e tente de novo.");
  }

  /* ---------- editar: temas do versículo ou tirar dos salvos ---------- */

  var dlgEditar = null;
  var editando = null;

  function abrirEditar(it) {
    editando = it;
    if (!dlgEditar) {
      dlgEditar = Util.dialogo("leitor-dlg versiculos-dlg", function (ev) {
        if (ev.target.closest("[data-remover-salvo]")) {
          dlgEditar.close();
          return remover(editando);
        }
        if (ev.target.closest("[data-salvar-temas]")) return salvarTemas();
        var vb = ev.target.closest("[data-verso]");
        if (vb) vb.setAttribute("aria-pressed", vb.getAttribute("aria-pressed") === "true" ? "false" : "true");
      });
      dlgEditar.addEventListener("submit", function (ev) {
        ev.preventDefault();
        Temas.adicionarNoPopup(dlgEditar);
      });
    }
    var h = '<div class="leitor-dlg-topo"><span class="hud muted">Editar · ' + esc(refDe(it)) + '</span>' + Util.botaoFechar() + '</div>' +
      '<div class="versiculos-editar-versos"><p class="hud faint">Versículos do capítulo (marque ou desmarque)</p><div class="versiculos-versos">';
    var doCap = texto[it.i].chapters[it.cap - 1];
    for (var n = 1; n <= doCap.length; n++) {
      var noGrupo = it.versos.some(function (x) { return x.v === n; });
      h += '<button type="button" class="chip" data-verso="' + n + '" aria-pressed="' + noGrupo + '" title="' + esc(doCap[n - 1]) + '">' + n + "</button>";
    }
    h += '</div></div><div class="leitor-temas"><p class="hud faint">Temas</p><div class="leitor-temas-lista">';
    h += Temas.chips(temasTodos().map(function (t) { return t.nome; }), function (t) { return it.temas.indexOf(t) >= 0; });
    h += '</div><form class="leitor-tema-novo"><input type="text" name="tema" maxlength="40" placeholder="Novo tema" aria-label="Novo tema" autocomplete="off" />' +
      '<button type="submit" class="btn secundario">Adicionar</button></form>' +
      '<div class="leitor-temas-acoes"><button type="button" class="btn" data-salvar-temas>Salvar</button>' +
      '<button type="button" class="chip" data-remover-salvo>Remover dos salvos</button></div></div>';
    dlgEditar.innerHTML = h;
    Util.mostrar(dlgEditar);
  }

  function salvarTemas() {
    Temas.adicionarNoPopup(dlgEditar); // o que ficou digitado também conta
    var it = editando;
    var novos = Temas.marcadosNoPopup(dlgEditar);
    var marcados = [].slice.call(dlgEditar.querySelectorAll('[data-verso][aria-pressed="true"]')).map(function (b) {
      return Number(b.getAttribute("data-verso"));
    });
    if (!marcados.length) {
      return Util.confirmar("Remover dos salvos", "Nenhum versículo ficou marcado. Remover " + refDe(it) + " dos salvos?", "Remover", function () {
        dlgEditar.close();
        gravarEdicao(it, marcados, novos);
      });
    }
    dlgEditar.close();
    gravarEdicao(it, marcados, novos);
  }

  function gravarEdicao(it, marcados, novos) {
    if (!pronto || !it) return;
    var n = texto[it.i].chapters[it.cap - 1].length;
    var alvo = [];
    for (var v = 1; v <= n; v++) {
      var antes = it.versos.some(function (x) { return x.v === v; });
      var agora = marcados.indexOf(v) >= 0;
      if (!antes && !agora) continue;
      var m = null;
      linhas.forEach(function (l) {
        if (l.livro === it.livro && l.capitulo === it.cap && l.versiculo === v) m = l;
      });
      alvo.push({ livro: it.livro, capitulo: it.cap, versiculo: v, grifo: m ? m.grifo : null, salvo: agora, temas: agora ? novos.slice() : [] });
    }
    gravar(alvo, "Não consegui salvar os temas. Confira a conexão e tente de novo.");
  }

  function aviso(msg) {
    var el = document.createElement("p");
    el.className = "vazio hud muted";
    el.setAttribute("role", "status");
    el.textContent = msg;
    raiz.insertBefore(el, raiz.firstChild);
  }

  raiz.addEventListener("click", function (ev) {
    var t = ev.target.closest && ev.target.closest("button");
    if (!t || t.disabled) return;
    if (t.hasAttribute("data-marcar-todos")) {
      sel = temasTodos().map(function (x) { return x.nome; }).concat([""]);
      guardarFiltro();
      return render();
    }
    if (t.hasAttribute("data-limpar")) {
      sel = [];
      guardarFiltro();
      return render();
    }
    if (t.hasAttribute("data-menu")) {
      menuAberto = !menuAberto;
      return render();
    }
    if (t.hasAttribute("data-decorar")) return entrarDecorar();
    if (t.hasAttribute("data-editar")) {
      var it = itens[Number(t.getAttribute("data-editar"))];
      if (it) abrirEditar(it);
    }
  });

  raiz.addEventListener("change", function (ev) {
    var c = ev.target;
    if (!c.hasAttribute || !c.hasAttribute("data-tema")) return;
    var v = c.getAttribute("data-tema");
    var i = sel.indexOf(v);
    if (c.checked && i < 0) sel.push(v);
    if (!c.checked && i >= 0) sel.splice(i, 1);
    guardarFiltro();
    render();
  });

  raiz.addEventListener("submit", function (ev) {
    ev.preventDefault();
    adicionarTema(ev.target.elements.tema.value);
    guardarFiltro();
    render();
    var campo = raiz.querySelector('input[name="tema"]');
    if (campo) campo.focus();
  });

  // clicar fora fecha o dropdown
  document.addEventListener("click", function (ev) {
    if (!menuAberto || ev.target.closest(".versiculos-temas")) return;
    menuAberto = false;
    render();
  });

  document.addEventListener("keydown", function (ev) {
    if (menuAberto && ev.key === "Escape") {
      menuAberto = false;
      return render();
    }
    if (!decorar || ev.altKey || ev.ctrlKey || ev.metaKey) return;
    if (ev.key === " " || ev.key === "Enter") {
      if (ev.target && ev.target.tagName === "BUTTON" && ev.key === "Enter") return; // o botão já cuida
      ev.preventDefault();
      if (decorar.mostrado) return proximoDecorar();
      decorar.mostrado = true;
      return render();
    }
    if (ev.key === "ArrowRight") return proximoDecorar();
  });

  /* ---------- carga ---------- */

  function aplicar(lista) {
    linhas = lista || [];
    itens = agrupar(linhas);
    sel = sel.filter(function (x) { return x === "" || temasTodos().some(function (t) { return t.nome === x; }); });
    if (decorar) {
      // a lista mudou: recomeça com o que sobrou
      var lista2 = filtrados();
      decorar = lista2.length ? { lista: lista2, fila: embaralhar(lista2.length, -1), k: 0, mostrado: false } : null;
    }
  }

  // a cópia guardada aparece na hora; o servidor confirma em seguida
  function carregar() {
    decorar = null;
    if (Conta.usuario()) {
      var vista = Conta.lerVista("versiculos_vista");
      if (vista && vista.temas instanceof Array) sel = vista.temas.slice();
    }
    Temas.carregar(function (lista, confirmada) {
      aplicar(lista);
      pronto = confirmada;
      render();
    }, function () {
      raiz.innerHTML = '<p class="vazio">Não consegui carregar seus versículos. Recarregue a página para tentar de novo.</p>';
    });
  }

  Promise.all([
    Util.json("/compartilhado/dados/canon.json"),
    (Conta ? Conta.pronto() : Promise.resolve()).then(function () { return Versao.carregar(Versao.atual()); })
  ]).then(function (r) {
    canon = r[0];
    texto = r[1];
    canon.forEach(function (b, i) { ordem[b.id] = i; });
    return (Conta ? Conta.pronto() : Promise.resolve()).then(function () {
      carregar();
      if (Conta) {
        Conta.aoMudar(function (evento, u, mudou) {
          if (mudou) carregar();
        });
      }
    });
  }).catch(function () {
    Util.falha(raiz, "o texto");
  });
})();
