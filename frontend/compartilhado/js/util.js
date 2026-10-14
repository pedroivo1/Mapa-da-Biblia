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

  // texto seguro para pôr dentro de HTML (conteúdo ou atributo)
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  window.Util = { ler: ler, gravar: gravar, apagar: apagar, esc: esc };
})();
