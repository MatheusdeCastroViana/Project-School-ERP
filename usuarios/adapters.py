from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from .models_2fa import Configuracao2FA


class Custom2FAAccountAdapter(DefaultAccountAdapter):    
    def is_open_for_signup(self, request):
        return False

    def pre_login(self, request, user, **kwargs):
        try:
            config_2fa = user.config_2fa
            if config_2fa.ativado:
                request.session['usuario_pendente_2fa'] = user.id
                request.session['usuario_pendente_2fa_em'] = timezone.now().timestamp()
                return HttpResponseRedirect(reverse('usuarios:verificar_2fa'))
                
        except Configuracao2FA.DoesNotExist:
            pass
        except Exception:
            pass
        return None


class SocialAccountAdapterFechado(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        return False