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
  var usuarioCarregado = null;
  var pronto = false; // o servidor confirmou a lista: só então remover

  function urlEntrar() {
    return Conta ? Conta.urlEntrar() : "/conta/";
  }

  function chaveTemas(temas) {
    return (temas || []).slice().sort(function (a, b) { return a.localeCompare(b, "pt-BR"); }).join("\n");
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
    return canon[it.i].nome + " " + it.cap + ":" + (it.de === it.ate ? it.de : it.de + "-" + it.ate);
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
    return Object.keys(t).sort(function (a, b) { return a.localeCompare(b, "pt-BR"); }).map(function (n) {
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
    nome = String(nome || "").replace(/\s+/g, " ").trim();
    if (!nome) return;
    var ja = temasTodos().filter(function (t) { return t.nome.toLowerCase() === nome.toLowerCase(); })[0];
    if (ja) nome = ja.nome;
    else Conta.salvarConfig("temas", temasCriados().concat([nome]));
    if (sel.indexOf(nome) < 0) sel.push(nome);
  }

  function htmlMenu(semTema) {
    var h = '<div class="versiculos-menu" role="group" aria-label="Filtrar por temas">' +
      '<form class="versiculos-tema-novo"><input type="text" name="tema" maxlength="40" placeholder="Adicionar tema" aria-label="Adicionar tema" autocomplete="off" />' +
      '<button type="submit" class="btn">Adicionar</button></form>';
    temasTodos().forEach(function (t) {
      h += '<label class="versiculos-menu-item"><input type="checkbox" data-tema="' + esc(t.nome) + '"' + (sel.indexOf(t.nome) >= 0 ? " checked" : "") + " /><span>" + esc(t.nome) + '</span><span class="faint">' + t.n + "</span></label>";
    });
    h += '<label class="versiculos-menu-item"><input type="checkbox" data-tema=""' + (sel.indexOf("") >= 0 ? " checked" : "") + " /><span>Sem tema</span><span class=\"faint\">" + semTema + "</span></label></div>";
    return h;
  }

  /* ---------- lista ---------- */

  function render() {
    if (!Conta || !Conta.usuario()) {
      raiz.innerHTML = '<p class="vazio">Entre na sua conta para salvar versículos e decorá-los. ' +
        '<a class="btn" href="' + esc(urlEntrar()) + '">Entrar</a></p>';
      return;
    }
    if (decorar) return renderDecorar();
    if (!itens.length) {
      raiz.innerHTML = '<p class="vazio">Você ainda não salvou nenhum versículo. Na Bíblia, toque num versículo e escolha Salvar. ' +
        '<a class="chip" href="/biblia/">Abrir a Bíblia</a></p>';
      return;
    }
    var lista = filtrados();
    var semTema = itens.filter(function (it) { return !it.temas.length; }).length;
    var h = '<div class="versiculos-filtros" role="group" aria-label="Temas">' +
      '<button type="button" class="btn" data-todos' + (sel.length ? ' aria-pressed="false"' : ' aria-pressed="true"') + ">Todos <span class=\"faint\">" + itens.length + "</span></button>" +
      '<span class="versiculos-temas"><button type="button" class="btn secundario" data-menu aria-haspopup="true" aria-expanded="' + menuAberto + '">Temas' + (sel.length ? " (" + sel.length + ")" : "") + " " + Util.seta("baixo", 12) + "</button>" +
      (menuAberto ? htmlMenu(semTema) : "") + "</span></div>";
    h += '<div class="versiculos-acoes"><button type="button" class="btn" data-decorar' + (lista.length ? "" : " disabled") + ">Decorar" +
      (sel.length ? " · " + esc(nomeFiltro()) : "") + "</button>" +
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

  function sairDecorar() {
    decorar = null;
    render();
  }

  function renderDecorar() {
    var it = decorar.lista[decorar.fila[decorar.k]];
    var h = '<section class="versiculos-decorar" aria-live="polite">' +
      '<p class="hud muted">Decorar · ' + esc(nomeFiltro()) + " · " + (decorar.k + 1) + "/" + decorar.fila.length + "</p>" +
      '<h2 class="versiculos-decorar-ref">' + esc(refDe(it)) + "</h2>" +
      '<p class="versiculos-decorar-texto"' + (decorar.mostrado ? "" : " hidden") + ">" + textoDe(it) + "</p>" +
      '<p class="versiculos-decorar-dica hud faint"' + (decorar.mostrado ? " hidden" : "") + ">Diga de cor e depois confira.</p>" +
      '<div class="versiculos-decorar-acoes">' +
      (decorar.mostrado
        ? '<button type="button" class="btn" data-proximo>Próximo</button>'
        : '<button type="button" class="btn" data-mostrar>Mostrar</button><button type="button" class="btn secundario" data-proximo>Pular</button>') +
      '<button type="button" class="chip" data-sair>Sair</button></div>' +
      '<p class="hud faint">Espaço mostra · seta para a direita avança · Esc sai</p>' +
      "</section>";
    raiz.innerHTML = h;
    var foco = raiz.querySelector("[data-mostrar], [data-proximo]");
    if (foco) foco.focus();
  }

  /* ---------- ações ---------- */

  function remover(it) {
    if (!pronto) return;
    var alvo = it.versos.map(function (x) {
      var m = null;
      linhas.forEach(function (l) {
        if (l.livro === it.livro && l.capitulo === it.cap && l.versiculo === x.v) m = l;
      });
      return { livro: it.livro, capitulo: it.cap, versiculo: x.v, grifo: m ? m.grifo : null, salvo: false, temas: [] };
    });
    aplicar(linhas.filter(function (l) {
      return !alvo.some(function (a) { return a.livro === l.livro && a.capitulo === l.capitulo && a.versiculo === l.versiculo; });
    }).concat(alvo.filter(function (a) { return a.grifo; })));
    render();
    Conta.salvarMarcacoes(alvo).catch(function () {
      aviso("Não consegui remover. Confira a conexão e tente de novo.");
      Conta.carregarMarcacoes().then(function (l) {
        aplicar(l);
        render();
      }, function () {});
    });
  }

  /* ---------- editar: temas do versículo ou tirar dos salvos ---------- */

  var dlgEditar = null;
  var editando = null;

  function abrirEditar(it) {
    editando = it;
    if (!dlgEditar) {
      dlgEditar = document.createElement("dialog");
      dlgEditar.className = "leitor-dlg versiculos-dlg";
      dlgEditar.addEventListener("click", function (ev) {
        if (ev.target === dlgEditar || ev.target.closest("[data-fechar]")) return dlgEditar.close();
        if (ev.target.closest("[data-remover-salvo]")) {
          dlgEditar.close();
          return remover(editando);
        }
        if (ev.target.closest("[data-salvar-temas]")) return salvarTemas();
      });
      dlgEditar.addEventListener("submit", function (ev) {
        ev.preventDefault();
        novoTemaNoDialogo();
      });
      document.body.appendChild(dlgEditar);
    }
    var h = '<div class="leitor-dlg-topo"><span class="hud muted">Editar · ' + esc(refDe(it)) + '</span><button type="button" data-fechar>Fechar</button></div>' +
      '<div class="leitor-temas"><p class="hud faint">Temas</p><div class="leitor-temas-lista">';
    temasTodos().forEach(function (t) {
      h += '<label class="chip"><input type="checkbox" value="' + esc(t.nome) + '"' + (it.temas.indexOf(t.nome) >= 0 ? " checked" : "") + " /><span>" + esc(t.nome) + "</span></label>";
    });
    h += '</div><form class="leitor-tema-novo"><input type="text" name="tema" maxlength="40" placeholder="Novo tema" aria-label="Novo tema" autocomplete="off" />' +
      '<button type="submit" class="btn secundario">Adicionar</button></form>' +
      '<div class="leitor-temas-acoes"><button type="button" class="btn" data-salvar-temas>Salvar</button>' +
      '<button type="button" class="chip" data-remover-salvo>Remover dos salvos</button></div></div>';
    dlgEditar.innerHTML = h;
    if (!dlgEditar.open) dlgEditar.showModal();
  }

  function novoTemaNoDialogo() {
    var campo = dlgEditar.querySelector('input[name="tema"]');
    var nome = campo.value.replace(/\s+/g, " ").trim();
    if (!nome) return;
    var caixas = dlgEditar.querySelectorAll(".leitor-temas-lista input");
    var achou = false;
    for (var k = 0; k < caixas.length; k++) {
      if (caixas[k].value.toLowerCase() === nome.toLowerCase()) {
        caixas[k].checked = true;
        achou = true;
      }
    }
    if (!achou) {
      var r = document.createElement("label");
      r.className = "chip";
      var c = document.createElement("input");
      c.type = "checkbox";
      c.value = nome;
      c.checked = true;
      var t = document.createElement("span");
      t.textContent = nome;
      r.appendChild(c);
      r.appendChild(t);
      dlgEditar.querySelector(".leitor-temas-lista").appendChild(r);
    }
    campo.value = "";
  }

  function salvarTemas() {
    novoTemaNoDialogo(); // o que ficou digitado também conta
    var it = editando;
    var novos = [];
    Array.prototype.forEach.call(dlgEditar.querySelectorAll(".leitor-temas-lista input"), function (c) {
      if (c.checked) novos.push(c.value);
    });
    dlgEditar.close();
    if (!pronto || !it) return;
    var alvo = it.versos.map(function (x) {
      var m = null;
      linhas.forEach(function (l) {
        if (l.livro === it.livro && l.capitulo === it.cap && l.versiculo === x.v) m = l;
      });
      return { livro: it.livro, capitulo: it.cap, versiculo: x.v, grifo: m ? m.grifo : null, salvo: true, temas: novos.slice() };
    });
    aplicar(linhas.filter(function (l) {
      return !alvo.some(function (a) { return a.livro === l.livro && a.capitulo === l.capitulo && a.versiculo === l.versiculo; });
    }).concat(alvo));
    render();
    Conta.salvarMarcacoes(alvo).catch(function () {
      aviso("Não consegui salvar os temas. Confira a conexão e tente de novo.");
      Conta.carregarMarcacoes().then(function (l) {
        aplicar(l);
        render();
      }, function () {});
    });
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
    if (t.hasAttribute("data-todos")) {
      sel = [];
      guardarFiltro();
      menuAberto = false;
      return render();
    }
    if (t.hasAttribute("data-menu")) {
      menuAberto = !menuAberto;
      return render();
    }
    if (t.hasAttribute("data-decorar")) return entrarDecorar();
    if (t.hasAttribute("data-mostrar")) {
      decorar.mostrado = true;
      return render();
    }
    if (t.hasAttribute("data-proximo")) return proximoDecorar();
    if (t.hasAttribute("data-sair")) return sairDecorar();
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
    if (ev.key === "Escape") return sairDecorar();
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
    pronto = false;
    decorar = null;
    var u = Conta && Conta.usuario();
    usuarioCarregado = u ? u.id : null;
    if (!u) {
      aplicar([]);
      return render();
    }
    var vista = Conta.lerVista("versiculos_vista");
    if (vista && vista.temas instanceof Array) sel = vista.temas.slice();
    aplicar(Conta.marcacoesGuardadas() || []);
    render();
    Conta.carregarMarcacoes().then(function (lista) {
      if (!Conta.usuario() || Conta.usuario().id !== u.id) return;
      aplicar(lista);
      pronto = true;
      render();
    }, function () {
      raiz.innerHTML = '<p class="vazio">Não consegui carregar seus versículos. Recarregue a página para tentar de novo.</p>';
    });
  }

  Promise.all([
    fetch("/compartilhado/dados/canon.json").then(function (r) { return r.json(); }),
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
    raiz.innerHTML = '<p class="vazio">Não consegui carregar o texto. Abra por um servidor local (<code>python -m http.server</code>).</p>';
  });
})();
