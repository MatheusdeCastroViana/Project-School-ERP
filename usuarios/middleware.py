from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from .models_2fa import Configuracao2FA


class Exigir2FAMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.path not in self._rotas_liberadas():
            if not Configuracao2FA.objects.filter(usuario=request.user, ativado=True).exists():
                messages.warning(
                    request,
                    'O 2FA é obrigatório. Configure a autenticação de dois fatores para continuar.',
                )
                return redirect('usuarios:ativar_2fa')
        return self.get_response(request)

    def _rotas_liberadas(self):
        return {
            reverse('usuarios:ativar_2fa'),
            reverse('usuarios:logout'),
            reverse('account_logout'),
            reverse('usuarios:politica_privacidade'),
            reverse('usuarios:termos_uso'),
            reverse('usuarios:registrar_consentimento'),
        }