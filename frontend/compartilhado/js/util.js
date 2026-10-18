// Funções comuns a todas as páginas: localStorage seguro e escape de HTML.
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

  // texto seguro para pôr dentro de HTML (conteúdo ou atributo)
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  window.Util = { ler: ler, gravar: gravar, apagar: apagar, esc: esc, seta: seta };
})();
