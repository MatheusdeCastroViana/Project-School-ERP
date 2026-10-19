document.addEventListener('DOMContentLoaded', function() {
    const btnAceitar = document.getElementById('lgpd-btn-aceitar');
    const popup = document.getElementById('lgpd-consent-popup');

    // Exibe o popup se ele existir na página (a página de consentir obrigatório força isso)
    if (popup) {
        popup.style.display = 'flex';
    }

    if (!btnAceitar) return;

    btnAceitar.addEventListener('click', async function(event) {
        event.preventDefault();
        
        // Lê os dados diretamente do HTML, garantindo que o tipo seja 'tratamento_dados'
        const tipo = this.getAttribute('data-tipo'); 
        const versao = this.getAttribute('data-versao');
        
        const payload = {
            tipo: tipo,
            versao: versao,
            aceitou: true 
        };

        const textoOriginal = btnAceitar.textContent;
        btnAceitar.disabled = true;
        btnAceitar.textContent = 'Processando...';
        btnAceitar.style.opacity = '0.7';

        try {
            const response = await fetch('/usuarios/api/consentimento/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (response.ok && data.success) {
                // Redireciona para o dashboard após sucesso
                window.location.href = '/dashboard/';
            } else {
                alert('Erro ao registrar consentimento: ' + (data.error || 'Tente novamente.'));
                btnAceitar.disabled = false;
                btnAceitar.textContent = textoOriginal;
                btnAceitar.style.opacity = '1';
            }
        } catch (error) {
            console.error('Erro de rede:', error);
            alert('Erro de conexão. Verifique sua internet e tente novamente.');
            btnAceitar.disabled = false;
            btnAceitar.textContent = textoOriginal;
            btnAceitar.style.opacity = '1';
        }
    });

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});