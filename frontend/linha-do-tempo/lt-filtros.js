// Filtros de colunas e livros: um conjunto para computador e outro para celular, guardados no
// navegador e, com login, na conta (Conta.salvarConfig "linha_do_tempo"). Expõe LT.colunas (objeto único).
// Parte da linha do tempo (linha-do-tempo/index.html); ligada às outras pelo objeto global LT.
(function () {
  "use strict";

  var LT = (window.LT = window.LT || {});
  var ler = Util.ler, gravar = Util.gravar;
  var Conta = window.Conta;
  var JUNTA = LT.JUNTA;
  var JUNTA = LT.JUNTA;
  var MODOS = LT.MODOS;

  var KEY_COL = "biblioteca-colunas"; // antigo: um só conjunto de filtros
  var KEY_LT = "biblia-linha-do-tempo"; // { desktop: filtros, mobile: filtros }
  function grupoDe(livro) {
    if (colunas.modo !== "simples") return livro.grupo;
    // Gênesis e Êxodo são narrativa; a lei propriamente dita começa em Levítico
    if (livro.id === "genesis" || livro.id === "exodo") return "historia";
    return JUNTA[livro.grupo] || livro.grupo;
  }

  function gruposAtuais() {
    return MODOS[colunas.modo].grupos;
  }
  function grupoLigado(id) {
    return colunas.grupos[id] !== false;
  }


  // filtros guardados à parte para o computador e para o celular; na conta, valem em qualquer navegador
  function perfil() {
    return window.innerWidth <= 720 ? "mobile" : "desktop";
  }
  function padraoColunas(p) {
    // no celular, só os livros vêm marcados; depois vale o que a pessoa escolheu
    return p === "mobile"
      ? { eras: false, livros: true, reis: false, potencias: false }
      : { eras: true, livros: true, reis: true, potencias: true };
  }
  function copia(o) {
    return JSON.parse(JSON.stringify(o));
  }
  function perfisGuardados() {
    var conta = Conta && Conta.usuario() && Conta.config().linha_do_tempo;
    var local = ler(KEY_LT, null);
    if (!local) {
      // versão antiga: um só conjunto, que passa a valer para o tipo de tela atual
      var antigo = ler(KEY_COL, null);
      local = {};
      if (antigo) local[perfil()] = antigo;
    }
    var todos = {};
    ["desktop", "mobile"].forEach(function (p) {
      todos[p] = (conta && conta[p]) || local[p] || null;
    });
    return todos;
  }
  function ajustarColunas(c) {
    if (c.eras === undefined) c.eras = true;
    if (c.mapaGeral === undefined) c.mapaGeral = false; // mapa geral à direita da linha do tempo
    // filtro de livros por grupo; "livros" desligado (versão antiga) desliga todos
    if (!c.modo || !MODOS[c.modo]) c.modo = "almeida";
    if (!c.grupos) {
      c.grupos = {};
      if (c.livros === false) {
        Object.keys(JUNTA).concat(["lei", "historia", "poesia", "profeta", "historico-nt", "carta", "apocalipse"]).forEach(function (id) {
          c.grupos[id] = false;
        });
      }
    }
    return c;
  }
  // ordem das colunas na tela (a pessoa arrasta os títulos); ids que faltam entram no fim
  var ORDEM_PADRAO = ["era", "livros", "terra", "potencias"];
  function ordemColunas() {
    var o = (colunas.ordem || []).filter(function (id) {
      return ORDEM_PADRAO.indexOf(id) >= 0;
    });
    ORDEM_PADRAO.forEach(function (id) {
      if (o.indexOf(id) < 0) o.push(id);
    });
    return o;
  }
  var perfis = perfisGuardados();
  var perfilAtual = perfil();
  var colunas = ajustarColunas(copia(perfis[perfilAtual] || padraoColunas(perfilAtual)));
  var mexeuNosFiltros = false;
  function guardarColunas() {
    mexeuNosFiltros = true;
    perfis[perfilAtual] = copia(colunas);
    gravar(KEY_LT, perfis);
    if (Conta) Conta.salvarConfig("linha_do_tempo", perfis);
  }
  // a tela mudou de tipo (girou, redimensionou) ou chegou a cópia da conta: usa os filtros do tipo atual
  function trocarPerfil() {
    perfilAtual = perfil();
    var novo = ajustarColunas(copia(perfis[perfilAtual] || padraoColunas(perfilAtual)));
    // o objeto é o mesmo para todos os arquivos: troca o conteúdo, não a referência
    Object.keys(colunas).forEach(function (k) {
      delete colunas[k];
    });
    Object.keys(novo).forEach(function (k) {
      colunas[k] = novo[k];
    });
  }
  // a tela passou de computador para celular (ou o contrário)
  function telaMudou() {
    return perfil() !== perfilAtual;
  }
  function mexeu() {
    return mexeuNosFiltros;
  }
  // volta a ler os filtros guardados (navegador e conta) e aplica os do tipo de tela atual
  function recarregarFiltros() {
    perfis = perfisGuardados();
    trocarPerfil();
  }
  function guardarPerfisLocal() {
    gravar(KEY_LT, perfis);
  }
  function livrosAtivos() {
    return gruposAtuais().some(function (g) {
      return grupoLigado(g.id);
    });
  }

  LT.colunas = colunas;
  LT.grupoLigado = grupoLigado;
  LT.gruposAtuais = gruposAtuais;
  LT.grupoDe = grupoDe;
  LT.guardarColunas = guardarColunas;
  LT.guardarPerfisLocal = guardarPerfisLocal;
  LT.livrosAtivos = livrosAtivos;
  LT.ordemColunas = ordemColunas;
  LT.mexeu = mexeu;
  LT.recarregarFiltros = recarregarFiltros;
  LT.telaMudou = telaMudou;
  LT.trocarPerfil = trocarPerfil;
})();
