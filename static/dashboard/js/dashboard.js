document.addEventListener("DOMContentLoaded", function () {
  var profileTrigger = document.querySelector("[data-dash-profile-trigger]");
  var profilePanel = document.querySelector("[data-dash-profile-panel]");
 
  var menuToggle = document.querySelector("[data-dash-menu-toggle]");
  var sidebar = document.querySelector("[data-dash-sidebar]");
 
  function fecharPerfil() {
    if (!profilePanel) return;
    profilePanel.classList.remove("is-open");
    profileTrigger.setAttribute("aria-expanded", "false");
  }
 
  function alternarPerfil(event) {
    event.stopPropagation();
    var estaAberto = profilePanel.classList.toggle("is-open");
    profileTrigger.setAttribute("aria-expanded", estaAberto ? "true" : "false");
  }
 
  function alternarSidebar() {
    if (!sidebar) return;
    sidebar.classList.toggle("is-open");
  }
 
  if (profileTrigger && profilePanel) {
    profileTrigger.addEventListener("click", alternarPerfil);
 
    // Fecha o dropdown se o usuário clicar fora dele
    document.addEventListener("click", function (event) {
      if (!profilePanel.contains(event.target) && event.target !== profileTrigger) {
        fecharPerfil();
      }
    });
 
    // Fecha o dropdown com a tecla Esc
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        fecharPerfil();
      }
    });
  }
 
  if (menuToggle && sidebar) {
    menuToggle.addEventListener("click", alternarSidebar);
  }
});