(function () {
  "use strict";

  // Marcos, isso daqui está alternando a visibilidade dos campos de senha
  document.querySelectorAll("[data-toggle-password]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var wrap = btn.closest(".auth-input-wrap");
      var input = wrap ? wrap.querySelector("input") : null;
      if (!input) return;

      var isHidden = input.type === "password";
      input.type = isHidden ? "text" : "password";
      btn.setAttribute("aria-label", isHidden ? "Ocultar senha" : "Mostrar senha");
      btn.classList.toggle("is-active", isHidden);
    });
  });

  // Já essa parte vai evitar duplo envio do formulário (duplo clique / duplo POST) okay?
  document.querySelectorAll(".auth-form").forEach(function (form) {
    form.addEventListener("submit", function () {
      var submitBtn = form.querySelector('button[type="submit"]');
      if (!submitBtn || submitBtn.classList.contains("auth-btn--loading")) return;
      submitBtn.classList.add("auth-btn--loading");
      submitBtn.disabled = true;
    });
  });
})();