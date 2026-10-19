// Funções comuns a todas as páginas: localStorage seguro, escape de HTML, setas, JSON, anos, SVG e URL.
// Carregue antes de js/conta.js e dos scripts da página. Expõe window.Util.
(function () {
  "use strict";

  // lê um JSON do localStorage; devolve `padrao` se faltar, estiver inválido ou o acesso falhar
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

  function apagar(chave) {
    try {
      localStorage.removeItem(chave);
    } catch (e) {}
  }

  // a seta do projeto (a do leitor, que passa capítulos): SVG de traço, herda a cor do texto.
  // dir: "esq", "dir", "cima" ou "baixo"; tam em px; cls é opcional
  var SETAS = {
    esq: "M19 12H5M11 6l-6 6 6 6",
    dir: "M5 12h14M13 6l6 6-6 6",
    cima: "M12 19V5M6 11l6-6 6 6",
    baixo: "M12 5v14M6 13l6 6 6-6"
  };
  function seta(dir, tam, cls) {
    return '<svg class="seta' + (cls ? " " + cls : "") + '" viewBox="0 0 24 24" width="' + (tam || 18) + '" height="' + (tam || 18) +
      '" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="' + SETAS[dir] + '"/></svg>';
  }

  // botão de fechar dos popups: só o X
  function botaoFechar() {
    return '<button type="button" data-fechar aria-label="Fechar"><svg class="seta" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg></button>';
  }

  // texto seguro para pôr dentro de HTML (conteúdo ou atributo)
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // busca um JSON; rejeita se a resposta não for 2xx
  function json(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error("http " + r.status);
      return r.json();
    });
  }

  // aviso de dados que não carregaram (quase sempre: página aberta por file://)
  function falha(raiz, oque, cls) {
    raiz.innerHTML = '<p class="vazio' + (cls ? " " + cls : "") + '">Não consegui carregar ' + oque +
      '. Abra por um servidor local (<code>python -m http.server</code>).</p>';
  }

  // ano do projeto em texto: positivo é a.C., negativo é d.C.
  function ano(a) {
    return a > 0 ? a + " a.C." : -a + " d.C.";
  }

  // "Gênesis" se o trecho cobre o livro todo (total capítulos), senão "Gênesis 3–5"
  function trecho(nome, de, ate, total) {
    if (de === 1 && ate === total) return nome;
    return nome + " " + de + (ate > de ? "–" + ate : "");
  }

  function limitar(v, a, b) {
    return Math.max(a, Math.min(b, v));
  }

  // elemento SVG com atributos, opcionalmente posto dentro de `pai`
  var NS = "http://www.w3.org/2000/svg";
  function svg(tag, attrs, pai) {
    var el = document.createElementNS(NS, tag);
    for (var k in attrs) if (Object.prototype.hasOwnProperty.call(attrs, k)) el.setAttribute(k, attrs[k]);
    if (pai) pai.appendChild(el);
    return el;
  }

  // valor de ?nome= na URL: o texto, "" se vier sem valor (?embutido) ou null se faltar
  function param(nome) {
    var m = new RegExp("[?&]" + nome + "(?:=([^&#]*))?(?:[&#]|$)").exec(location.search);
    return m ? decodeURIComponent((m[1] || "").replace(/\+/g, " ")) : null;
  }

  // acrescenta "p" (ex.: "embutido" ou "cap=3") à query de uma URL
  function comParam(url, p) {
    return url + (url.indexOf("?") < 0 ? "?" : "&") + p;
  }

  // chama fn quando a página some (troca de aba, fechar, ir para outra página)
  function aoSair(fn) {
    window.addEventListener("pagehide", fn);
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "hidden") fn();
    });
  }

  // <dialog> de popup, criado uma vez e posto no body: fecha ao clicar fora ou em [data-fechar];
  // os outros cliques vão para aoClicar(ev, dlg)
  function dialogo(classe, aoClicar) {
    var dlg = document.createElement("dialog");
    dlg.className = classe;
    dlg.addEventListener("click", function (ev) {
      if (ev.target === dlg || ev.target.closest("[data-fechar]")) return dlg.close();
      if (aoClicar) aoClicar(ev, dlg);
    });
    document.body.appendChild(dlg);
    return dlg;
  }

  // abre o popup como modal, se ainda não estiver aberto
  function mostrar(dlg) {
    if (!dlg.open) dlg.showModal();
  }

  // pergunta de confirmação no estilo do site (no lugar do confirm do navegador); chama aoConfirmar se a pessoa aceitar
  var dlgConfirmar = null;
  var aoConfirmarAtual = null;
  function confirmar(titulo, mensagem, rotuloOk, aoConfirmar) {
    if (!dlgConfirmar) {
      dlgConfirmar = dialogo("leitor-dlg dlg-confirmar", function (ev, dlg) {
        if (!ev.target.closest("[data-ok]")) return;
        var f = aoConfirmarAtual;
        dlg.close();
        if (f) f();
      });
    }
    aoConfirmarAtual = aoConfirmar;
    dlgConfirmar.innerHTML = '<div class="leitor-dlg-topo"><span class="hud muted">' + esc(titulo) + "</span>" + botaoFechar() + "</div>" +
      '<div class="dlg-confirmar-corpo"><p>' + esc(mensagem) + '</p><div class="dlg-confirmar-acoes">' +
      '<button type="button" class="btn" data-ok>' + esc(rotuloOk || "Confirmar") + '</button>' +
      '<button type="button" class="chip" data-fechar>Cancelar</button></div></div>';
    mostrar(dlgConfirmar);
  }

  window.Util = {
    ler: ler, gravar: gravar, apagar: apagar, esc: esc, seta: seta, botaoFechar: botaoFechar,
    dialogo: dialogo, mostrar: mostrar, confirmar: confirmar,
    json: json, falha: falha, ano: ano, trecho: trecho, limitar: limitar, NS: NS, svg: svg,
    param: param, comParam: comParam, aoSair: aoSair
  };
})();
