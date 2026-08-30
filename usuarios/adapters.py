from allauth.account.adapter import DefaultAccountAdapter
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models_2fa import Configuracao2FA


class Custom2FAAccountAdapter(DefaultAccountAdapter):    
    def pre_login(self, request, user, **kwargs):
        try:
            config_2fa = user.config_2fa
            if config_2fa.ativado:
                request.session['usuario_pendente_2fa'] = user.id
                return HttpResponseRedirect(reverse('usuarios:verificar_2fa'))
                
        except Configuracao2FA.DoesNotExist:
            pass
        except Exception:
            pass
        return None