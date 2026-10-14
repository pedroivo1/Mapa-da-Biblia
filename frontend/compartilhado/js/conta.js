// Conta (Supabase Auth) e tudo que é da conta: progresso (tabela progresso) e configurações
// (tabela configuracoes). Expõe window.Conta. Busca ambos em segundo plano assim que há sessão e
// guarda uma cópia no navegador (biblia-cache); salva com atraso e despeja ao fechar a aba.
// Precisa de compartilhado/js/util.js, supabase-js (CDN) e compartilhado/js/config.js carregados antes.
(function () {
  "use strict";

  // Conta do usuário (Supabase Auth) e progresso salvo na tabela "progresso".
  // Precisa de supabase-js (CDN) e de compartilhado/js/config.js carregados antes.

  var BASE = new URL("../..", document.currentScript.src).href; // raiz do site
  var cfg = window.CONFIG || {};
  var ativo = !!(window.supabase && cfg.SUPABASE_URL && cfg.SUPABASE_KEY && cfg.SUPABASE_URL.indexOf("SEU-REF") < 0);
  var saindo = false;
  var sb = ativo
    ? window.supabase.createClient(cfg.SUPABASE_URL, cfg.SUPABASE_KEY, {
        global: {
          // ao fechar a aba, o último salvamento precisa sobreviver ao fim da página
          fetch: function (url, opcoes) {
            opcoes = opcoes || {};
            if (saindo) opcoes.keepalive = true;
            return fetch(url, opcoes);
          }
        }
      })
    : null;

  var usuario = null;
  var iniciado = null;
  var ouvintes = [];
  var pendente = null;
  var temporizador = null;
  var enviando = null;

  // cópia local do que está na conta (progresso e configurações): a página abre com ela e
  // o servidor só confirma ou atualiza em segundo plano
  var KEY_CACHE = "biblia-cache";
  var TTL_CACHE = 5 * 60 * 1000; // cópia confirmada há menos que isso não reconsulta o banco
  var buscaProgresso = null;
  var buscaConfig = null;
  var buscaDe = null;
  var progressoLido = false; // o primeiro carregar() devolve a busca já em andamento
  var config = null;
  var alteradas = {};
  var temporizadorConfig = null;
  var ouvintesConfig = [];

  function cacheLer() {
    var c = Util.ler(KEY_CACHE, null);
    return c && usuario && c.u === usuario.id ? c : null;
  }
  function cacheGravar(parte) {
    if (!usuario) return;
    var c = cacheLer() || { u: usuario.id };
    Object.keys(parte).forEach(function (k) {
      c[k] = parte[k];
    });
    Util.gravar(KEY_CACHE, c);
  }
  function cacheLimpar() {
    Util.apagar(KEY_CACHE);
  }

  // o tema escolhido na conta vale em qualquer navegador
  function aplicarTema(c) {
    var t = c && c.tema;
    if (t !== "light" && t !== "dark") return;
    if (document.documentElement.getAttribute("data-theme") === t) return;
    document.documentElement.setAttribute("data-theme", t);
    try {
      localStorage.setItem("notas-theme", t);
    } catch (e) {}
  }

  function pronto() {
    if (!sb) return Promise.resolve(null);
    if (!iniciado) {
      iniciado = sb.auth.getSession().then(function (r) {
        usuario = r.data.session ? r.data.session.user : null;
        iniciarBusca();
        if (usuario) aplicarTema(configAtual());
        return usuario;
      });
    }
    return iniciado;
  }

  if (sb) {
    sb.auth.onAuthStateChange(function (evento, sessao) {
      var novo = sessao ? sessao.user : null;
      var mudou = (novo && novo.id) !== (usuario && usuario.id);
      usuario = novo;
      // não chamar o Supabase dentro deste callback: adia para depois
      setTimeout(function () {
        if (mudou) {
          pendente = null;
          alteradas = {};
          config = null;
          buscaDe = null;
          if (!usuario) cacheLimpar();
          iniciarBusca();
          montarNav();
        }
        ouvintes.forEach(function (cb) {
          cb(evento, usuario, mudou);
        });
      }, 0);
    });
  }

  function aoMudar(cb) {
    ouvintes.push(cb);
  }

  function urlEntrar() {
    return BASE + "conta/?volta=" + encodeURIComponent(location.pathname);
  }

  /* ---------- progresso ---------- */

  function lerProgresso() {
    return sb
      .from("progresso")
      .select("lido, versiculos")
      .maybeSingle()
      .then(function (r) {
        if (r.error) throw r.error;
        var p = r.data
          ? { lido: r.data.lido || {}, versiculos: r.data.versiculos || {}, vazio: false }
          : { lido: {}, versiculos: {}, vazio: true };
        if (!pendente && !enviando) cacheGravar({ progresso: { lido: p.lido, versiculos: p.versiculos }, tp: Date.now() });
        return p;
      });
  }

  function lerConfig() {
    return sb
      .from("configuracoes")
      .select("dados")
      .maybeSingle()
      .then(function (r) {
        if (r.error) throw r.error;
        var servidor = (r.data && r.data.dados) || {};
        // o que a pessoa mexeu nesta página e ainda não subiu vale mais que o servidor
        var nova = {};
        Object.keys(servidor).forEach(function (k) {
          nova[k] = servidor[k];
        });
        Object.keys(alteradas).forEach(function (k) {
          nova[k] = alteradas[k];
        });
        config = nova;
        cacheGravar({ config: nova, tc: Date.now() });
        aplicarTema(nova);
        ouvintesConfig.forEach(function (cb) {
          cb(nova);
        });
        return { servidor: servidor, config: nova };
      });
  }

  // começa a buscar assim que se sabe quem é a pessoa, antes de a página pedir
  function iniciarBusca() {
    if (!sb || !usuario || buscaDe === usuario.id) return;
    buscaDe = usuario.id;
    progressoLido = false;
    // cópia recém-confirmada: usa direto, sem ir ao banco (uma página nova a cada clique não custa consulta)
    var c = cacheLer();
    var agora = Date.now();
    if (c && c.progresso && c.config && !pendente && !enviando && agora - (c.tp || 0) < TTL_CACHE && agora - (c.tc || 0) < TTL_CACHE) {
      config = c.config;
      buscaProgresso = Promise.resolve({ lido: c.progresso.lido || {}, versiculos: c.progresso.versiculos || {}, vazio: false });
      buscaConfig = Promise.resolve({ servidor: c.config, config: c.config });
      return;
    }
    buscaProgresso = lerProgresso();
    buscaConfig = lerConfig();
    buscaProgresso.catch(function () {});
    buscaConfig.catch(function () {});
  }

  function carregar() {
    if (!sb || !usuario) return Promise.resolve(null);
    if (buscaProgresso && !progressoLido) {
      progressoLido = true;
      return buscaProgresso;
    }
    return lerProgresso();
  }

  // o que ficou guardado neste navegador (vale depois de pronto())
  function progressoGuardado() {
    var c = cacheLer();
    return c && c.progresso ? { lido: c.progresso.lido || {}, versiculos: c.progresso.versiculos || {}, vazio: false } : null;
  }

  function configAtual() {
    if (!usuario) return {};
    if (!config) {
      var c = cacheLer();
      config = (c && c.config) || {};
    }
    return config;
  }

  function aoConfig(cb) {
    ouvintesConfig.push(cb);
  }

  function carregarConfig() {
    if (!sb || !usuario) return Promise.resolve({});
    iniciarBusca();
    return buscaConfig.then(function (r) {
      return r.config;
    });
  }

  function enviarConfig() {
    clearTimeout(temporizadorConfig);
    if (!sb || !usuario || !Object.keys(alteradas).length) return Promise.resolve();
    var envio = alteradas;
    alteradas = {};
    // sem a cópia do servidor não dá para mesclar sem apagar o resto: espera a busca
    return buscaConfig
      .then(function (r) {
        var dados = {};
        Object.keys(r.servidor).forEach(function (k) {
          dados[k] = r.servidor[k];
        });
        Object.keys(envio).forEach(function (k) {
          dados[k] = envio[k];
        });
        return sb.from("configuracoes").upsert({ user_id: usuario.id, dados: dados, atualizado_em: new Date().toISOString() });
      })
      .then(function (r) {
        if (r.error) throw r.error;
        buscaConfig = Promise.resolve({ servidor: config || {}, config: config || {} });
      })
      .catch(function (e) {
        Object.keys(envio).forEach(function (k) {
          if (!(k in alteradas)) alteradas[k] = envio[k];
        });
        temporizadorConfig = setTimeout(enviarConfig, 8000);
        throw e;
      });
  }

  // chave: "linha_do_tempo", "plano", "leitor", "tema"…; vale o valor inteiro daquela chave
  function salvarConfig(chave, valor) {
    if (!usuario) return;
    configAtual()[chave] = valor;
    alteradas[chave] = valor;
    cacheGravar({ config: config });
    clearTimeout(temporizadorConfig);
    temporizadorConfig = setTimeout(function () {
      enviarConfig().catch(function () {});
    }, 800);
  }

  function enviar() {
    clearTimeout(temporizador);
    if (!pendente || !sb) return Promise.resolve();
    if (enviando) return enviando;
    var linha = pendente;
    pendente = null;
    enviando = sb
      .from("progresso")
      .upsert(linha)
      .then(function (r) {
        enviando = null;
        if (r.error) throw r.error;
        aviso("");
      })
      .catch(function (e) {
        enviando = null;
        // devolve para a fila, a não ser que algo mais novo já tenha chegado
        if (!pendente) pendente = linha;
        aviso("Não consegui salvar sua leitura. Tentando de novo…");
        temporizador = setTimeout(enviar, 5000);
        throw e;
      });
    return enviando;
  }

  function linhaDe(lido, versiculos) {
    cacheGravar({ progresso: { lido: lido, versiculos: versiculos } });
    return {
      user_id: usuario.id,
      lido: lido,
      versiculos: versiculos,
      atualizado_em: new Date().toISOString()
    };
  }

  // salva alguns instantes depois da última marcação
  function salvar(lido, versiculos) {
    if (!usuario) return;
    pendente = linhaDe(lido, versiculos);
    clearTimeout(temporizador);
    temporizador = setTimeout(function () {
      enviar().catch(function () {});
    }, 800);
  }

  function salvarAgora(lido, versiculos) {
    if (!usuario) return Promise.reject(new Error("sem usuário"));
    pendente = linhaDe(lido, versiculos);
    return enviar();
  }

  function temPendente() {
    return !!(pendente || enviando);
  }

  // o fetch do supabase-js sai de forma assíncrona, então "saindo" só volta a false quando a página reaparece
  function despejar() {
    saindo = true;
    if (pendente) enviar().catch(function () {});
    if (Object.keys(alteradas).length) enviarConfig().catch(function () {});
  }
  window.addEventListener("pagehide", despejar);
  window.addEventListener("pageshow", function () {
    saindo = false;
  });
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") despejar();
    else saindo = false;
  });

  var caixaAviso = null;
  function aviso(texto) {
    if (!texto) {
      if (caixaAviso) caixaAviso.hidden = true;
      return;
    }
    if (!caixaAviso) {
      caixaAviso = document.createElement("p");
      caixaAviso.className = "conta-aviso hud";
      caixaAviso.setAttribute("role", "status");
      document.body.appendChild(caixaAviso);
    }
    caixaAviso.textContent = texto;
    caixaAviso.hidden = false;
  }

  /* ---------- menu da conta na barra do topo ---------- */

  var esc = Util.esc;

  // sem js/config.js preenchido o botão Entrar aparece mesmo assim; a página de login explica o que falta
  function montarNav() {
    Array.prototype.forEach.call(document.querySelectorAll("[data-entrar]"), function (el) {
      el.hidden = !!usuario;
    });
    var nav = document.querySelector(".nav-inner");
    if (!nav) return;
    var caixa = nav.querySelector(".nav-conta");
    if (!caixa) {
      caixa = document.createElement("div");
      caixa.className = "nav-conta";
      nav.insertBefore(caixa, nav.querySelector(".theme-toggle"));
      caixa.addEventListener("click", function (ev) {
        if (!ev.target.closest("[data-sair]")) return;
        sair();
      });
    }
    var naPaginaEntrar = /^\/conta\/?(index\.html)?$/.test(location.pathname);
    if (usuario) {
      caixa.innerHTML =
        '<span class="nav-email hud faint" title="' + esc(usuario.email) + '">' + esc(usuario.email) + "</span>" +
        '<button type="button" class="nav-link hud" data-sair><span>Sair</span></button>';
    } else {
      caixa.innerHTML = naPaginaEntrar ? "" : '<a class="nav-link hud" href="' + esc(urlEntrar()) + '"><span>Entrar</span></a>';
    }
  }

  /* ---------- login ---------- */

  function exigir() {
    if (!sb) return Promise.reject(new Error("Login ainda não configurado (js/config.js)."));
    return null;
  }
  function resultado(r) {
    if (r.error) throw r.error;
    return r.data;
  }

  function entrarGoogle(volta) {
    return exigir() || sb.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: location.origin + volta }
    }).then(resultado);
  }
  function entrar(email, senha) {
    return exigir() || sb.auth.signInWithPassword({ email: email, password: senha }).then(resultado);
  }
  function criar(email, senha, volta) {
    return exigir() || sb.auth.signUp({
      email: email,
      password: senha,
      options: { emailRedirectTo: location.origin + volta }
    }).then(resultado);
  }
  function esqueci(email) {
    return exigir() || sb.auth.resetPasswordForEmail(email, {
      redirectTo: BASE + "conta/?nova-senha=1"
    }).then(resultado);
  }
  function novaSenha(senha) {
    return exigir() || sb.auth.updateUser({ password: senha }).then(resultado);
  }
  function sair() {
    if (!sb) return Promise.resolve();
    // tenta mandar o que falta antes de perder a sessão
    return Promise.all([enviar().catch(function () {}), enviarConfig().catch(function () {})]).then(function () {
      cacheLimpar();
      return sb.auth.signOut();
    });
  }

  window.Conta = {
    ativo: ativo,
    pronto: pronto,
    aoMudar: aoMudar,
    usuario: function () {
      return usuario;
    },
    urlEntrar: urlEntrar,
    carregar: carregar,
    progressoGuardado: progressoGuardado,
    config: configAtual,
    carregarConfig: carregarConfig,
    aoConfig: aoConfig,
    salvarConfig: salvarConfig,
    salvar: salvar,
    salvarAgora: salvarAgora,
    temPendente: temPendente,
    entrarGoogle: entrarGoogle,
    entrar: entrar,
    criar: criar,
    esqueci: esqueci,
    novaSenha: novaSenha,
    sair: sair
  };

  // Service Worker (sw.js na raiz): páginas e dados abrem do cache, o leitor funciona sem rede
  if ("serviceWorker" in navigator && location.protocol !== "file:") {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function () {});
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { pronto().then(montarNav); });
  else pronto().then(montarNav);
})();
