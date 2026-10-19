// Tema: preferência "light", "dark" ou "system" (guardada em notas-theme e na conta);
// data-theme na <html> é sempre o tema efetivo (claro ou escuro). O botão do topo abre um menu com as três opções.
(function () {
  var root = document.documentElement;
  var escuro = matchMedia("(prefers-color-scheme: dark)");
  var pref = "system";
  try {
    var stored = localStorage.getItem("notas-theme");
    if (stored === "light" || stored === "dark") pref = stored;
  } catch (e) {}

  function efetivo() {
    return pref === "system" ? (escuro.matches ? "dark" : "light") : pref;
  }
  function aplicar() {
    root.setAttribute("data-theme", efetivo());
    root.setAttribute("data-theme-pref", pref);
  }
  aplicar();
  // ?embutido (popup do leitor, mapa na linha do tempo): sem topo, nav nem rodapé; antes do primeiro desenho
  if (/[?&]embutido/.test(location.search)) root.classList.add("embutido");
  escuro.addEventListener("change", function () {
    if (pref === "system") aplicar();
  });

  // a conta chama isto quando o tema guardado nela vale ("light", "dark" ou "system")
  window.TemaPref = {
    ler: function () {
      return pref;
    },
    definir: function (valor) {
      if (valor !== "light" && valor !== "dark" && valor !== "system") return;
      pref = valor;
      try {
        if (valor === "system") localStorage.removeItem("notas-theme");
        else localStorage.setItem("notas-theme", valor);
      } catch (e) {}
      aplicar();
      if (window.TemaPref.aoMudar) window.TemaPref.aoMudar();
    }
  };

  var ICONES = {
    light: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><circle cx="12" cy="12" r="4"></circle><path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5 5l1.6 1.6M17.4 17.4 19 19M19 5l-1.6 1.6M6.6 17.4 5 19"></path></svg>',
    dark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="M21 14.5A8.5 8.5 0 1 1 9.5 3 7 7 0 0 0 21 14.5z"></path></svg>',
    // sistema: um monitor (desktop)
    system: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="12" rx="1"></rect><path d="M8 20h8M12 16v4"></path></svg>'
  };
  var NOMES = { light: "Claro", dark: "Escuro", system: "Sistema" };

  document.addEventListener("DOMContentLoaded", function () {
    var nav = document.querySelector(".nav");
    var inner = document.querySelector(".nav-inner");
    if (nav && inner) {
      var menu = document.createElement("button");
      menu.type = "button";
      menu.className = "nav-menu-btn";
      menu.setAttribute("aria-label", "Abrir menu");
      menu.setAttribute("aria-expanded", "false");
      menu.innerHTML =
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="M3 6h18M3 12h18M3 18h18"></path></svg>';
      inner.appendChild(menu);
      menu.addEventListener("click", function () {
        var aberto = nav.classList.toggle("aberto");
        menu.setAttribute("aria-expanded", aberto ? "true" : "false");
      });
    }
    var button = document.querySelector("[data-theme-toggle]");
    if (!button || !inner) return;
    var lista = document.createElement("div");
    lista.className = "tema-opcoes";
    lista.setAttribute("role", "menu");
    lista.hidden = true;
    ["light", "dark", "system"].forEach(function (v) {
      var o = document.createElement("button");
      o.type = "button";
      o.className = "hud";
      o.setAttribute("role", "menuitemradio");
      o.setAttribute("data-tema", v);
      o.innerHTML = ICONES[v] + "<span>" + NOMES[v] + "</span>";
      lista.appendChild(o);
    });
    inner.appendChild(lista);
    button.setAttribute("aria-haspopup", "menu");
    button.setAttribute("aria-expanded", "false");

    function atualizar() {
      button.innerHTML = ICONES[pref];
      button.setAttribute("aria-label", "Tema: " + NOMES[pref]);
      button.title = "Tema: " + NOMES[pref];
      Array.prototype.forEach.call(lista.children, function (o) {
        o.setAttribute("aria-checked", o.getAttribute("data-tema") === pref ? "true" : "false");
      });
    }
    function fechar() {
      lista.hidden = true;
      button.setAttribute("aria-expanded", "false");
    }
    function abrir() {
      lista.hidden = false;
      lista.style.top = button.offsetTop + button.offsetHeight + "px";
      lista.style.right = Math.max(0, inner.clientWidth - button.offsetLeft - button.offsetWidth) + "px";
      button.setAttribute("aria-expanded", "true");
    }
    atualizar();
    window.TemaPref.aoMudar = atualizar;

    button.addEventListener("click", function (ev) {
      ev.stopPropagation();
      if (lista.hidden) abrir();
      else fechar();
    });
    lista.addEventListener("click", function (ev) {
      var o = ev.target.closest("[data-tema]");
      if (!o) return;
      var v = o.getAttribute("data-tema");
      window.TemaPref.definir(v);
      fechar();
      if (window.Conta) window.Conta.salvarConfig("tema", v);
    });
    document.addEventListener("click", function (ev) {
      if (!lista.hidden && !lista.contains(ev.target)) fechar();
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && !lista.hidden) {
        fechar();
        button.focus();
      }
    });
  });
})();
