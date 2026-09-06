(function () {
  "use strict";
  // essa parte vai evitar duplo envio do formulário (duplo clique / duplo POST) okay?
  document.querySelectorAll(".auth-form").forEach(function (form) {
    form.addEventListener("submit", function () {
      var submitBtn = form.querySelector('button[type="submit"]');
      if (!submitBtn || submitBtn.classList.contains("auth-btn--loading")) return;
      submitBtn.classList.add("auth-btn--loading");
      submitBtn.disabled = true;
    });
  });
})();

 // Marcos, isso daqui está alternando a visibilidade dos campos de senha
document.addEventListener('DOMContentLoaded', function() {
    const toggleButtons = document.querySelectorAll('[data-toggle-password]');

    toggleButtons.forEach(button => {
        function revealPassword() {
            const input = button.parentElement.querySelector('input');
            if (input) {
                input.type = 'text';
                button.setAttribute('aria-label', 'Senha visível - solte para ocultar');
            }
        }

        function hidePassword() {
            const input = button.parentElement.querySelector('input');
            if (input) {
                input.type = 'password';
                button.setAttribute('aria-label', 'Segure para mostrar senha');
            }
        }

        button.addEventListener('mousedown', function(e) {
            e.preventDefault(); 
            revealPassword();
        });
        
        button.addEventListener('mouseup', hidePassword);
        button.addEventListener('mouseleave', hidePassword);

        button.addEventListener('touchstart', function(e) {
            e.preventDefault(); 
            revealPassword();
        }, { passive: false });
        
        button.addEventListener('touchend', hidePassword);
        button.addEventListener('touchcancel', hidePassword);
    });
});