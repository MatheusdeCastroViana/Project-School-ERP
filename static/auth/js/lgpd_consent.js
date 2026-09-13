(function() {
    'use strict';
    
    const CONFIG = {
        CONSENT_VERSION: '1.0',
        STORAGE_KEY_PREFIX: 'lgpd_consentimento_v',
        DELAY_MS: 2000, 
        API_ENDPOINT: '/usuarios/api/consentimento/'
    };
    
    const STORAGE_KEY = CONFIG.STORAGE_KEY_PREFIX + CONFIG.CONSENT_VERSION;
    
    function hasConsent() {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (!stored) return false;
            
            const data = JSON.parse(stored);
            return data.versao === CONFIG.CONSENT_VERSION;
        } catch (error) {
            console.warn('LGPD: Erro ao verificar consentimento:', error);
            return false;
        }
    }

    function showPopup() {
        const popup = document.getElementById('lgpd-consent-popup');
        if (popup) {
            popup.classList.add('lgpd-consent-popup--visible');
        }
    }

    function hidePopup() {
        const popup = document.getElementById('lgpd-consent-popup');
        if (popup) {
            popup.classList.remove('lgpd-consent-popup--visible');
        }
    }
    
    function saveToLocalStorage(aceitou) {
        const dadosConsentimento = {
            versao: CONFIG.CONSENT_VERSION,
            aceitou: aceitou,
            data: new Date().toISOString(),
            url: window.location.href
        };
        
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(dadosConsentimento));
        } catch (error) {
            console.warn('LGPD: Erro ao salvar no localStorage:', error);
        }
    }
    
    function registerOnBackend(aceitou) {
        const usuarioLogado = document.querySelector('meta[name="usuario-logado"]');
        
        if (!usuarioLogado || !aceitou) {
            return; 
        }
        
        const csrfToken = getCookie('csrftoken');
        
        if (!csrfToken) {
            console.warn('LGPD: CSRF token não encontrado');
            return;
        }
        
        fetch(CONFIG.API_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                tipo: 'privacidade',
                versao: CONFIG.CONSENT_VERSION,
                aceitou: aceitou
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Erro na resposta do servidor');
            }
            return response.json();
        })
        .then(data => {
            console.log('LGPD: Consentimento registrado com sucesso:', data);
        })
        .catch(error => {
            console.error('LGPD: Erro ao registrar consentimento:', error);
        });
    }
    
    function handleConsent(aceitou) {
        saveToLocalStorage(aceitou);
        registerOnBackend(aceitou);
        hidePopup();
    }

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
    
    function init() {
 
        if (hasConsent()) {
            return;
        }

        setTimeout(showPopup, CONFIG.DELAY_MS);

        const btnAceitar = document.getElementById('lgpd-btn-aceitar');
        const btnRecusar = document.getElementById('lgpd-btn-recusar');
        
        if (btnAceitar) {
            btnAceitar.addEventListener('click', function() {
                handleConsent(true);
            });
        }
        
        if (btnRecusar) {
            btnRecusar.addEventListener('click', function() {
                handleConsent(false);
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();