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
    var button = document.querySelector("[data-theme-toggle]");
    if (!button) return;
    button.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      localStorage.setItem("notas-theme", next);
    });
  });
})();
