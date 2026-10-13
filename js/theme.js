(function () {
  var root = document.documentElement;
  try {
    var stored = localStorage.getItem("notas-theme");
    var theme =
      stored === "light" || stored === "dark"
        ? stored
        : matchMedia("(prefers-color-scheme: dark)").matches
          ? "dark"
          : "light";
    root.setAttribute("data-theme", theme);
  } catch (e) {}

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
    if (!button) return;
    button.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      localStorage.setItem("notas-theme", next);
    });
  });
})();
