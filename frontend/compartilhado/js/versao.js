// Versão da Bíblia escolhida (leitor e plano de leitura): lista das versões, a escolhida e o carregamento do texto.
// Fica no navegador (biblia-versao) e na conta ("versao"); vale como padrão em toda página. Texto: biblia/versoes/<id>.json.
// Carregue depois de util.js e conta.js. Expõe window.Versao.
(function () {
  "use strict";

  var KEY = "biblia-versao";
  var Conta = window.Conta;
  var LISTA = [
    { id: "nvi", sigla: "NVI", nome: "Nova Versão Internacional" },
    { id: "ara", sigla: "ARA", nome: "Almeida Revista e Atualizada" },
    { id: "arc", sigla: "ARC", nome: "Almeida Revista e Corrigida" },
    { id: "naa", sigla: "NAA", nome: "Nova Almeida Atualizada" },
    { id: "ntlh", sigla: "NTLH", nome: "Nova Tradução na Linguagem de Hoje" },
    { id: "nvt", sigla: "NVT", nome: "Nova Versão Transformadora" },
    { id: "nbv", sigla: "NBV", nome: "Nova Bíblia Viva" },
    { id: "acf", sigla: "ACF", nome: "Almeida Corrigida Fiel" },
    { id: "aa", sigla: "AA", nome: "Almeida Revisada Imprensa Bíblica" },
    { id: "tb", sigla: "TB", nome: "Tradução Brasileira" },
    { id: "kjf", sigla: "KJF", nome: "King James Fiel" }
  ];
  var PADRAO = "nvi";

  function existe(id) {
    return LISTA.some(function (v) { return v.id === id; });
  }
  function achar(id) {
    return LISTA.filter(function (v) { return v.id === id; })[0] || LISTA[0];
  }

  // a conta vale quando há login; senão, o navegador
  function atual() {
    var id = Conta && Conta.usuario() && Conta.config().versao;
    if (!existe(id)) id = Util.ler(KEY, null);
    return existe(id) ? id : PADRAO;
  }

  function definir(id) {
    if (!existe(id)) return;
    Util.gravar(KEY, id);
    if (Conta) Conta.salvarConfig("versao", id);
  }

  function carregar(id) {
    return fetch("/biblia/versoes/" + id + ".json").then(function (r) { return r.json(); });
  }

  // popup com as versões; ao escolher, grava e chama `aoEscolher(id, anterior)` (a página troca o texto)
  var dlg = null;
  var retorno = null;
  function popup(aoEscolher) {
    retorno = aoEscolher;
    if (!dlg) {
      dlg = Util.dialogo("leitor-dlg versao-dlg", function (ev) {
        var b = ev.target.closest("[data-versao-id]");
        if (!b) return;
        var anterior = atual();
        var id = b.getAttribute("data-versao-id");
        dlg.close();
        if (id === anterior) return;
        definir(id);
        if (retorno) retorno(id, anterior);
      });
    }
    var ativa = atual();
    dlg.innerHTML = '<div class="leitor-dlg-topo"><span class="hud muted">Versão da Bíblia</span>' + Util.botaoFechar() + '</div>' +
      '<div class="versao-busca"><input type="search" placeholder="Pesquisar versão" aria-label="Pesquisar versão" autocomplete="off" /></div>' +
      '<div class="versao-lista">' + LISTA.map(function (v) {
        return '<button type="button" data-versao-id="' + v.id + '" data-busca="' + Util.esc((v.sigla + " " + v.nome).toLowerCase()) + '"' + (v.id === ativa ? ' aria-current="true"' : "") + "><strong>" + v.sigla + "</strong><span>" + Util.esc(v.nome) + "</span></button>";
      }).join("") + '<p class="versao-vazio hud faint" hidden>Nenhuma versão encontrada.</p></div>';
    var campo = dlg.querySelector("input");
    campo.addEventListener("input", function () {
      var q = campo.value.trim().toLowerCase();
      var achou = 0;
      Array.prototype.forEach.call(dlg.querySelectorAll("[data-versao-id]"), function (b) {
        var ok = !q || b.getAttribute("data-busca").indexOf(q) !== -1;
        b.hidden = !ok;
        if (ok) achou++;
      });
      dlg.querySelector(".versao-vazio").hidden = achou > 0;
    });
    Util.mostrar(dlg);
    dlg.querySelector("input").focus();
  }

  window.Versao = { lista: LISTA, achar: achar, atual: atual, definir: definir, carregar: carregar, popup: popup };
})();
