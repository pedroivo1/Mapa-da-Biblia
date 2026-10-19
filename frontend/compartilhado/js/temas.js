// Temas e marcações dos versículos, comuns ao leitor (biblia/) e à página Versículos (versiculos/):
// nome do tema, lista em ordem, chips de tema dos popups, referência ("João 3:16-18") e
// leitura/gravação das marcações da conta (Conta.carregarMarcacoes, Conta.salvarMarcacoes, tabela marcacoes).
// Carregue depois de compartilhado/js/util.js e conta.js. Expõe window.Temas.
(function () {
  "use strict";

  var esc = Util.esc;

  // espaços repetidos viram um só, sem espaço nas pontas
  function normalizar(nome) {
    return String(nome || "").replace(/\s+/g, " ").trim();
  }

  // ordena (no lugar) os nomes em ordem alfabética do português
  function ordenar(nomes) {
    return nomes.sort(function (a, b) { return a.localeCompare(b, "pt-BR"); });
  }

  // chips (caixas de marcar) da lista de temas dos popups; marcado(nome) diz quais vêm marcados
  function chips(nomes, marcado) {
    return nomes.map(function (t) {
      return '<label class="chip"><input type="checkbox" value="' + esc(t) + '"' + (marcado(t) ? " checked" : "") + "><span>" + esc(t) + "</span></label>";
    }).join("");
  }

  // o tema digitado no campo do popup: marca o chip de mesmo nome (sem diferença de maiúsculas)
  // ou cria um chip novo, já marcado; limpa o campo e, com foco, volta a ele
  function adicionarNoPopup(dlg, foco) {
    var campo = dlg.querySelector('input[name="tema"]');
    var nome = normalizar(campo.value);
    if (!nome) return;
    var lista = dlg.querySelector(".leitor-temas-lista");
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
    if (foco) campo.focus();
  }

  // os temas marcados no popup
  function marcadosNoPopup(dlg) {
    var r = [];
    var caixas = dlg.querySelectorAll(".leitor-temas-lista input");
    for (var k = 0; k < caixas.length; k++) if (caixas[k].checked) r.push(caixas[k].value);
    return r;
  }

  // "João 3:16-18" ou "João 3:1, 5-6"; versos em ordem crescente
  function ref(nome, cap, versos) {
    var partes = [];
    for (var k = 0; k < versos.length; k++) {
      var ini = versos[k], fim = ini;
      while (k + 1 < versos.length && versos[k + 1] === fim + 1) fim = versos[++k];
      partes.push(ini === fim ? String(ini) : ini + "-" + fim);
    }
    return nome + " " + cap + ":" + partes.join(", ");
  }

  // a cópia guardada chega na hora (aoChegar(lista, false)) e a do servidor em seguida (aoChegar(lista, true)),
  // se o usuário ainda for o mesmo; sem login, aoChegar([], false). aoFalhar se o servidor não responder
  function carregar(aoChegar, aoFalhar) {
    var u = Conta.usuario();
    if (!u) return aoChegar([], false);
    aoChegar(Conta.marcacoesGuardadas() || [], false);
    Conta.carregarMarcacoes().then(function (lista) {
      if (!Conta.usuario() || Conta.usuario().id !== u.id) return;
      aoChegar(lista, true);
    }, aoFalhar);
  }

  // manda as marcações para a conta; se falhar, chama aoFalhar e depois aoVoltar(lista do servidor)
  function salvar(lista, aoFalhar, aoVoltar) {
    Conta.salvarMarcacoes(lista).catch(function () {
      aoFalhar();
      Conta.carregarMarcacoes().then(aoVoltar, function () {});
    });
  }

  window.Temas = {
    normalizar: normalizar, ordenar: ordenar, chips: chips,
    adicionarNoPopup: adicionarNoPopup, marcadosNoPopup: marcadosNoPopup,
    ref: ref, carregar: carregar, salvar: salvar
  };
})();
