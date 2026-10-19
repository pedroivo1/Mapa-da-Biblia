// Plano de leitura (plano-de-leitura/index.html): lista os planos de planos.json,
// mostra a ordem de cada um e deixa escolher o plano padrão (exige login; fica em Conta "plano").
// Ritmo de leitura: a pessoa diz em quanto tempo quer ler o plano e em quais dias da semana; a página divide
// os capítulos do plano pelos dias de leitura (versículos parecidos por dia, sem quebrar capítulos). Fica em Conta "ritmo".
(function () {
  "use strict";

  var ler = Util.ler, gravar = Util.gravar, esc = Util.esc;

  var KEY_RITMO = "biblia-ritmo"; // { plano, inicio: "AAAA-MM-DD", fim: "AAAA-MM-DD" (inclusive), dias: [0..6] (0 = domingo) }
  var DIAS = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];
  var KEY_PLANO = "biblia-mapa"; // { padrao: id do plano escolhido, pos: { id do plano: "livro/cap" } }
  var Conta = window.Conta;
  var raiz = document.getElementById("plano");
  var planos = [];
  var eras = {};
  var nomes = {};


  // o plano padrão é da conta: sem login não há plano padrão
  function logado() {
    return !!Conta.usuario();
  }
  function estadoPlano() {
    return (logado() && Conta.config().plano) || ler(KEY_PLANO, {});
  }
  function guardarPlano(v) {
    gravar(KEY_PLANO, v);
    if (logado()) Conta.salvarConfig("plano", v);
  }

  function ritmoAtual() {
    return (logado() && Conta.config().ritmo) || ler(KEY_RITMO, null);
  }
  function guardarRitmo(v) {
    if (v) gravar(KEY_RITMO, v);
    else Util.apagar(KEY_RITMO);
    if (logado()) Conta.salvarConfig("ritmo", v);
  }

  /* ---------- calendário do ritmo ---------- */

  function dataDe(txt) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(txt || "");
    return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : null;
  }
  function txtData(d) {
    function dois(n) { return (n < 10 ? "0" : "") + n; }
    return d.getFullYear() + "-" + dois(d.getMonth() + 1) + "-" + dois(d.getDate());
  }
  function rotuloData(d) {
    return d.toLocaleDateString("pt-BR", { weekday: "short", day: "numeric", month: "short" });
  }

  // último dia de leitura. Ritmos antigos guardavam duracao + unidade em vez de fim
  function fimDe(r) {
    if (r.fim) return dataDe(r.fim);
    var ini = dataDe(r.inicio);
    if (!ini || !(r.duracao > 0)) return null;
    var fim = new Date(ini.getTime());
    if (r.unidade === "meses") fim.setMonth(fim.getMonth() + r.duracao);
    else fim.setDate(fim.getDate() + r.duracao * 7);
    fim.setDate(fim.getDate() - 1);
    return fim;
  }

  // datas de leitura: dos dias marcados da semana, do início até o fim (inclusive)
  function diasDeLeitura(r) {
    var ini = dataDe(r.inicio), fim = fimDe(r);
    if (!ini || !fim) return [];
    var out = [];
    for (var d = new Date(ini.getTime()); d <= fim; d.setDate(d.getDate() + 1)) {
      if (r.dias.indexOf(d.getDay()) >= 0) out.push(new Date(d.getTime()));
    }
    return out;
  }

  // capítulos do plano em ordem, repartidos em `ndias` grupos seguidos sem quebrar capítulos. Programação
  // dinâmica: escolhe os cortes que minimizam a soma dos quadrados da diferença entre os versículos de cada dia
  // e a média (total ÷ dias), então todos os dias ficam o mais perto possível da mesma quantidade de versículos
  var memoDivisao = {};
  function dividir(plano, ndias) {
    var chave = plano.id + ":" + ndias;
    return memoDivisao[chave] || (memoDivisao[chave] = dividirSemMemo(plano, ndias));
  }
  function dividirSemMemo(plano, ndias) {
    var caps = [];
    plano.etapas.forEach(function (e) {
      e.trechos.forEach(function (t) {
        for (var c = t.de; c <= t.ate; c++) caps.push({ livro: t.livro, cap: c, v: nomes[t.livro].v[c - 1] });
      });
    });
    var n = caps.length;
    var dias = [], i, k;
    for (i = 0; i < ndias; i++) dias.push([]);
    if (ndias >= n) {      // mais dias que capítulos: um por dia, espaçados pelo período
      caps.forEach(function (c, q) { dias[Math.floor(((q + 0.5) * ndias) / n)].push(c); });
      return dias;
    }
    var soma = [0];
    caps.forEach(function (c) { soma.push(soma[soma.length - 1] + c.v); });
    var alvo = soma[n] / ndias;
    var maior = Math.max.apply(null, caps.map(function (c) { return c.v; }));
    var limite = alvo * 2 + maior;     // nenhum grupo razoável passa disso
    var custo = [], de = [];
    for (k = 0; k <= ndias; k++) {
      var linha = new Float64Array(n + 1);
      for (i = 0; i <= n; i++) linha[i] = Infinity;
      custo.push(linha);
      de.push(new Int32Array(n + 1));
    }
    custo[0][0] = 0;
    for (k = 1; k <= ndias; k++) {
      for (i = k; i <= n - (ndias - k); i++) {
        for (var j = i - 1; j >= k - 1; j--) {
          var v = soma[i] - soma[j];
          if (v > limite && j < i - 1) break;
          if (custo[k - 1][j] === Infinity) continue;
          var c = custo[k - 1][j] + (v - alvo) * (v - alvo);
          if (c < custo[k][i]) {
            custo[k][i] = c;
            de[k][i] = j;
          }
        }
      }
    }
    if (custo[ndias][n] === Infinity) {      // não deveria ocorrer; cai na divisão proporcional simples
      var antes = 0;
      caps.forEach(function (c) {
        dias[Math.min(ndias - 1, Math.floor(((antes + c.v / 2) * ndias) / soma[n]))].push(c);
        antes += c.v;
      });
      return dias;
    }
    var fim = n;
    for (k = ndias; k >= 1; k--) {
      var ini = de[k][fim];
      dias[k - 1] = caps.slice(ini, fim);
      fim = ini;
    }
    return dias;
  }

  function capLido(prog, c) {
    var x = prog && prog[c.livro] && prog[c.livro][c.cap];
    return x === 1 || (!!x && x.length === c.v);
  }

  function refDia(caps) {
    var partes = [], atual = null;
    caps.forEach(function (c) {
      if (atual && atual.livro === c.livro && atual.ate === c.cap - 1) atual.ate = c.cap;
      else {
        atual = { livro: c.livro, de: c.cap, ate: c.cap };
        partes.push(atual);
      }
    });
    return partes.map(referencia).join("; ");
  }

  // nome do trecho {livro, de, ate}: "Gênesis" se for o livro todo, senão "Gênesis 3–5"
  function referencia(tr) {
    var b = nomes[tr.livro];
    return Util.trecho(b.nome, tr.de, tr.ate, b.n);
  }

  // link do leitor seguindo o plano `id`, já escapado; com livro, abre nesse capítulo
  function linkBiblia(id, livro, cap) {
    return esc("/biblia/?plano=" + id + (livro ? "#" + livro + "/" + cap : ""));
  }

  // o plano aberto pelo #id da URL, ou null na lista
  function planoAberto() {
    var achado = null;
    planos.forEach(function (m) { if (location.hash === "#" + m.id) achado = m; });
    return achado;
  }

  // calendário próprio (no lugar do seletor de data nativo do navegador), usado no início e no fim do ritmo
  var MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
  var SETA = '<svg viewBox="0 0 12 12" width="10" height="10" aria-hidden="true"><path d="M2 4l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>';

  function htmlData(nome, v) {
    var d = dataDe(v);
    return '<span class="plano-data" data-data><input type="hidden" name="' + nome + '" value="' + esc(v) + '" />' +
      '<button type="button" class="plano-data-bt" data-data-abrir aria-haspopup="dialog" aria-expanded="false" aria-label="' + (nome === "fim" ? "Data final" : "Data de início") + '"><span>' + (d ? d.toLocaleDateString("pt-BR") : "escolher") + "</span>" +
      '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M2.5 3.5h11v10h-11zM2.5 6.5h11M5.5 2v3M10.5 2v3" fill="none" stroke="currentColor" stroke-width="1.3"/></svg></button>' +
      '<div class="plano-pop plano-cal" role="dialog" aria-label="Escolher data" hidden></div></span>';
  }
  function desenharCal(box, ano, mes) {
    var campo = box.parentNode.querySelector('input[type="hidden"]');
    var sel = dataDe(campo.value), hoje = txtData(new Date());
    box.setAttribute("data-ano", ano);
    box.setAttribute("data-mes", mes);
    var h = '<div class="plano-cal-topo"><button type="button" data-cal-mes="-1" aria-label="Mês anterior">' + Util.seta("esq", 14) + "</button>" +
      "<strong>" + MESES[mes] + " de " + ano + '</strong><button type="button" data-cal-mes="1" aria-label="Próximo mês">' + Util.seta("dir", 14) + "</button></div>" +
      '<div class="plano-cal-grade">';
    DIAS.forEach(function (n) { h += '<span class="plano-cal-sem">' + n.charAt(0).toUpperCase() + "</span>"; });
    var vazios = new Date(ano, mes, 1).getDay(), total = new Date(ano, mes + 1, 0).getDate(), i;
    for (i = 0; i < vazios; i++) h += "<span></span>";
    for (i = 1; i <= total; i++) {
      var t = txtData(new Date(ano, mes, i));
      h += '<button type="button" data-cal-dia="' + t + '"' + (t === hoje ? ' class="hoje"' : "") + (sel && t === txtData(sel) ? ' aria-pressed="true"' : "") + ">" + i + "</button>";
    }
    box.innerHTML = h + '</div><div class="plano-cal-pe"><button type="button" data-cal-dia="' + hoje + '">Hoje</button></div>';
  }
  function marcarPop(p, aberto) {
    p.hidden = !aberto;
    var bt = p.parentNode.querySelector("[aria-expanded]");
    if (bt) bt.setAttribute("aria-expanded", aberto ? "true" : "false");
  }
  function fecharPops() {
    Array.prototype.forEach.call(raiz.querySelectorAll(".plano-pop"), function (p) {
      if (!p.hidden) marcarPop(p, false);
    });
  }
  function alternarPop(pop) {
    var abrir = pop.hidden;
    fecharPops();
    if (abrir) marcarPop(pop, true);
  }
  function htmlRitmo(plano) {
    var r = ritmoAtual();
    var meu = r && r.plano === plano.id ? r : null;
    var hoje = new Date(), fim12 = new Date(hoje.getFullYear() + 1, hoje.getMonth(), hoje.getDate() - 1);
    var f = meu || { inicio: txtData(hoje), fim: txtData(fim12), dias: [0, 1, 2, 3, 4, 5, 6] };
    if (meu && !meu.fim) f = { inicio: meu.inicio, fim: txtData(fimDe(meu) || fim12), dias: meu.dias };
    var h = '<section class="plano-ritmo"><p class="l-secao hud">Ritmo de leitura</p>' +
      '<form data-ritmo-form><p class="muted">Quando você quer começar e terminar este plano, e em quais dias da semana?</p>' +
      '<div class="plano-ritmo-linha"><span class="plano-campo">De ' + htmlData("inicio", f.inicio) + '</span> ' +
      '<span class="plano-campo">até ' + htmlData("fim", f.fim) + '</span></div>' +
      '<p class="plano-ritmo-dias" role="group" aria-label="Dias da semana">';
    DIAS.forEach(function (n, i) {
      h += '<label class="plano-dia"><input type="checkbox" name="dia" value="' + i + '"' + (f.dias.indexOf(i) >= 0 ? " checked" : "") + " /><span>" + n + "</span></label>";
    });
    h += '</p><p class="plano-acoes"><button type="submit" class="btn">' + (meu ? "Refazer calendário" : "Montar calendário") + "</button>" +
      (meu ? ' <button type="button" class="chip" data-ritmo-apagar>Remover ritmo</button>' : "") + "</p>" +
      '<p class="hud faint plano-ritmo-erro" data-ritmo-erro hidden></p></form>';
    if (meu) h += htmlCalendario(plano, meu);
    return h + "</section>";
  }

  function htmlCalendario(plano, r) {
    var datas = diasDeLeitura(r);
    if (!datas.length) return '<p class="vazio">Nenhum dia de leitura nesse período.</p>';
    var dias = dividir(plano, datas.length);
    var g = logado() && Conta.progressoGuardado();
    var prog = g ? g.versiculos : null;
    var hoje = txtData(new Date());
    var itens = [];
    datas.forEach(function (d, i) {
      if (!dias[i].length) return;
      var feito = prog ? dias[i].every(function (c) { return capLido(prog, c); }) : false;
      itens.push({ d: d, txt: txtData(d), caps: dias[i], feito: feito });
    });
    var proximo = null, atrasados = 0;
    itens.forEach(function (it) {
      if (it.feito) return;
      if (it.txt < hoje) atrasados++;
      if (!proximo && it.txt >= hoje) proximo = it;
    });
    var alvo = null;
    if (!proximo) { var pend = itens.filter(function (it) { return !it.feito; }); alvo = pend[0] || null; }
    var foco = proximo || alvo;
    var media = Math.round(itens.reduce(function (n, it) { return n + it.caps.length; }, 0) / itens.length * 10) / 10;
    var h = '<p class="hud faint">' + itens.length + " dias de leitura · cerca de " + String(media).replace(".", ",") + " capítulos por dia" +
      (atrasados ? " · " + atrasados + (atrasados > 1 ? " dias atrasados" : " dia atrasado") : "") + "</p>";
    if (foco) {
      h += '<p class="plano-hoje"><span class="hud faint">' + (foco.txt === hoje ? "Hoje" : foco.txt < hoje ? "Em atraso" : "Próxima leitura") + " · " + esc(rotuloData(foco.d)) + "</span>" +
        '<a href="' + linkBiblia(plano.id, foco.caps[0].livro, foco.caps[0].cap) + '">' + esc(refDia(foco.caps)) + "</a></p>";
    } else {
      h += '<p class="plano-hoje"><span class="hud faint">Calendário concluído</span></p>';
    }
    h += '<details class="plano-cal"><summary class="hud">Ver o calendário inteiro</summary><ol class="plano-cal-lista">';
    itens.forEach(function (it) {
      h += '<li class="' + (it.feito ? "feito" : it.txt < hoje ? "atrasado" : "") + (it === foco ? " hoje" : "") + '"><span class="hud faint">' + esc(rotuloData(it.d)) + "</span>" +
        '<a href="' + linkBiblia(plano.id, it.caps[0].livro, it.caps[0].cap) + '">' + esc(refDia(it.caps)) + "</a>" +
        (it.feito ? '<span class="hud faint">✓ lido</span>' : "") + "</li>";
    });
    return h + "</ol></details>";
  }

  function totalCaps(m) {
    var n = 0;
    m.etapas.forEach(function (e) {
      e.trechos.forEach(function (t) { n += t.ate - t.de + 1; });
    });
    return n;
  }

  function render() {
    var estado = estadoPlano();
    var padrao = logado() ? estado.padrao : null;
    var lista = planos.slice().sort(function (a, b) {
      return (a.id === padrao ? 0 : 1) - (b.id === padrao ? 0 : 1);
    });
    var aberto = planoAberto();
    var h = "";
    lista.forEach(function (m) {
      if (aberto && m !== aberto) return;
      var escolhido = m.id === padrao;
      var guardado = estado.pos && estado.pos[m.id];
      var g = guardado && /^([a-z0-9]+)\/(\d+)$/.exec(guardado);
      var primeiro = m.etapas[0].trechos[0];
      h += '<article class="plano-card' + (escolhido ? " escolhido" : "") + (aberto ? "" : " abrivel") + '"' +
        (aberto ? "" : ' data-abrir="' + esc(m.id) + '" tabindex="0" role="link" aria-label="Abrir ' + esc(m.nome) + '"') + ">" +
        '<h2 class="item-nome">' + esc(m.nome) + (escolhido ? ' <span class="hud faint">· seu plano padrão</span>' : "") + "</h2>" +
        '<p class="muted">' + esc(m.resumo) + "</p>" +
        '<p class="hud faint">' + m.etapas.length + " épocas · " + totalCaps(m) + " capítulos</p>" +
        '<p class="plano-acoes">' +
        '<a class="chip" href="' + (g && nomes[g[1]] ? linkBiblia(m.id) : linkBiblia(m.id, primeiro.livro, primeiro.de)) + '">' +
        (g && nomes[g[1]] ? "Continuar a Bíblia · " + esc(nomes[g[1]].nome) + " " + g[2] : "Ler a Bíblia") + "</a> " +
        (g ? '<a class="chip" href="' + linkBiblia(m.id, primeiro.livro, primeiro.de) + '">Do início</a> ' : "") +
        (aberto ? "" : '<a class="chip" href="#' + esc(m.id) + '">Calendário de leitura</a> ') +
        (logado()
          ? '<button type="button" class="chip" data-padrao="' + esc(m.id) + '" aria-pressed="' + escolhido + '">' +
            (escolhido ? "✓ Meu plano padrão" : "Definir como meu plano") + "</button>"
          : '<a class="chip" href="' + esc(Conta.urlEntrar()) + '">Entre para definir como seu plano</a>') +
        "</p></article>";
    });

    var ativo = aberto;
    if (!ativo) {
      raiz.innerHTML = h;
      return;
    }
    h += htmlRitmo(ativo);
    h += '<div class="plano-ordem"><p class="l-secao hud">Ordem do ' + esc(ativo.nome.toLowerCase()) + "</p>";
    ativo.etapas.forEach(function (et) {
      var era = eras[et.era] || { nome: et.nome || et.era, periodo: et.periodo, resumo: et.resumo };
      h += '<section class="plano-era"><header><h3>' + esc(era.nome) + '</h3><span class="hud faint">' + esc(era.periodo || "") + "</span></header>";
      if (era.resumo) h += '<p class="muted plano-resumo">' + esc(era.resumo) + "</p>";
      if (!et.trechos.length) h += '<p class="hud faint plano-vazio">Sem livros neste período.</p>';
      h += '<ol class="plano-trechos">';
      et.trechos.forEach(function (tr) {
        h += '<li><a href="' + linkBiblia(ativo.id, tr.livro, tr.de) + '">' + esc(referencia(tr)) + "</a>" +
          (tr.nota ? '<span class="hud faint">' + esc(tr.nota) + "</span>" : "") + "</li>";
      });
      h += "</ol></section>";
    });
    h += "</div>";
    raiz.innerHTML = h;
  }

  function abrir(id) {
    location.hash = id;
    window.scrollTo(0, 0);
  }

  function controleRitmo(ev) {
    var t = ev.target.closest ? ev.target : ev.target.parentNode;
    var b;
    b = t.closest("[data-data-abrir]");
    if (b) {
      var cal = b.parentNode.querySelector(".plano-cal");
      if (cal.hidden) {
        var d = dataDe(b.parentNode.querySelector('input[type="hidden"]').value) || new Date();
        desenharCal(cal, d.getFullYear(), d.getMonth());
      }
      alternarPop(cal);
      return true;
    }
    b = t.closest("[data-cal-mes]");
    if (b) {
      var c = b.closest(".plano-cal");
      var m = Number(c.getAttribute("data-mes")) + Number(b.getAttribute("data-cal-mes")), a = Number(c.getAttribute("data-ano"));
      var nova = new Date(a, m, 1);
      desenharCal(c, nova.getFullYear(), nova.getMonth());
      ev.stopPropagation(); // o botão clicado saiu do DOM: o fechamento por clique fora o tomaria por "fora"
      return true;
    }
    b = t.closest("[data-cal-dia]");
    if (b) {
      var campo = b.closest("[data-data]");
      var dd = dataDe(b.getAttribute("data-cal-dia"));
      campo.querySelector('input[type="hidden"]').value = b.getAttribute("data-cal-dia");
      campo.querySelector(".plano-data-bt span").textContent = dd.toLocaleDateString("pt-BR");
      fecharPops();
      campo.querySelector(".plano-data-bt").focus();
      return true;
    }
    return false;
  }

  document.addEventListener("click", function (ev) {
    if (!ev.target.closest || !ev.target.closest(".plano-data")) fecharPops();
  });

  raiz.addEventListener("click", function (ev) {
    if (controleRitmo(ev)) return;
    if (ev.target.closest && ev.target.closest("[data-ritmo-apagar]")) {
      guardarRitmo(null);
      render();
      return;
    }
    var t = ev.target.closest && ev.target.closest("[data-padrao]");
    if (!t) {
      if (ev.target.closest && ev.target.closest(".plano-ritmo")) return;
      var card = ev.target.closest && ev.target.closest("[data-abrir]");
      if (card && !ev.target.closest("a")) abrir(card.getAttribute("data-abrir"));
      return;
    }
    if (!logado()) return;
    var estado = estadoPlano();
    var id = t.getAttribute("data-padrao");
    estado.padrao = estado.padrao === id ? null : id;
    guardarPlano(estado);
    render();
  });

  raiz.addEventListener("submit", function (ev) {
    var f = ev.target.closest && ev.target.closest("[data-ritmo-form]");
    if (!f) return;
    ev.preventDefault();
    var dias = [];
    Array.prototype.forEach.call(f.querySelectorAll('input[name="dia"]:checked'), function (c) { dias.push(Number(c.value)); });
    var plano = planoAberto();
    var r ={ plano: plano && plano.id, inicio: f.inicio.value, fim: f.fim.value, dias: dias };
    var erro = f.querySelector("[data-ritmo-erro]");
    var msg = !plano ? "Abra um plano primeiro." : !dias.length ? "Marque pelo menos um dia da semana." :
      !dataDe(r.inicio) || !dataDe(r.fim) ? "Escolha a data de início e a data final." :
      r.fim < r.inicio ? "A data final precisa ser depois da data de início." :
      !diasDeLeitura(r).length ? "Nenhum dia de leitura nesse período." : "";
    erro.hidden = !msg;
    erro.textContent = msg;
    if (msg) return;
    guardarRitmo(r);
    render();
  });

  raiz.addEventListener("keydown", function (ev) {
    var pop = ev.target.closest && ev.target.closest(".plano-pop");
    if (ev.key === "Escape" && pop) {
      var dono = pop.parentNode.querySelector("[aria-expanded]");
      fecharPops();
      dono.focus();
      return;
    }
    var card = ev.target.getAttribute && ev.target.hasAttribute("data-abrir") ? ev.target : null;
    if (card && (ev.key === "Enter" || ev.key === " ")) {
      ev.preventDefault();
      abrir(card.getAttribute("data-abrir"));
    }
  });

  window.addEventListener("hashchange", function () {
    if (planos.length) render();
  });

  Promise.all([
    Util.json("/plano-de-leitura/planos.json"),
    Util.json("/compartilhado/dados/eras.json"),
    Util.json("/compartilhado/dados/canon.json")
  ]).then(function (r) {
    planos = r[0].planos;
    r[1].eras.forEach(function (e) { eras[e.id] = e; });
    r[2].forEach(function (b) { nomes[b.id] = { nome: b.nome, n: b.v.length, v: b.v }; });
    // com a sessão (rápida) a cópia guardada da conta já aparece; o servidor atualiza depois
    return Conta.pronto().then(function () {
      render();
      Conta.aoConfig(function () { render(); });
      Conta.aoMudar(function (ev, u, mudou) { if (mudou) render(); });
    });
  }).catch(function () {
    Util.falha(raiz, "o plano");
  });
})();
