(function () {
  "use strict";

  // Conta do usuário (Supabase Auth) e progresso salvo na tabela "progresso".
  // Precisa de supabase-js (CDN) e de js/config.js carregados antes.

  var BASE = new URL("..", document.currentScript.src).href; // raiz do site
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

  function pronto() {
    if (!sb) return Promise.resolve(null);
    if (!iniciado) {
      iniciado = sb.auth.getSession().then(function (r) {
        usuario = r.data.session ? r.data.session.user : null;
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
    return BASE + "entrar.html?volta=" + encodeURIComponent(location.pathname);
  }

  /* ---------- progresso ---------- */

  function carregar() {
    if (!sb || !usuario) return Promise.resolve(null);
    return sb
      .from("progresso")
      .select("lido, versiculos")
      .maybeSingle()
      .then(function (r) {
        if (r.error) throw r.error;
        if (!r.data) return { lido: {}, versiculos: {}, vazio: true };
        return { lido: r.data.lido || {}, versiculos: r.data.versiculos || {}, vazio: false };
      });
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

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

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
    var naPaginaEntrar = /\/entrar\.html$/.test(location.pathname);
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
      redirectTo: BASE + "entrar.html?nova-senha=1"
    }).then(resultado);
  }
  function novaSenha(senha) {
    return exigir() || sb.auth.updateUser({ password: senha }).then(resultado);
  }
  function sair() {
    if (!sb) return Promise.resolve();
    // tenta mandar o que falta antes de perder a sessão
    return enviar()
      .catch(function () {})
      .then(function () {
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

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { pronto().then(montarNav); });
  else pronto().then(montarNav);
})();
