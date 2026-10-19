import ipaddress

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.http import JsonResponse

from .models_2fa import Configuracao2FA
from .models import ConsentimentoLGPD


class Exigir2FAMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.path not in self._rotas_liberadas():
            if not Configuracao2FA.objects.filter(usuario=request.user, ativado=True).exists():
                messages.warning(request, 'O 2FA é obrigatório. Configure a autenticação de dois fatores para continuar.')
                return redirect('usuarios:ativar_2fa')
        return self.get_response(request)

    def _rotas_liberadas(self):
        return {
            reverse('usuarios:ativar_2fa'),
            reverse('usuarios:desativar_2fa'),
            reverse('usuarios:verificar_2fa'),
            reverse('usuarios:logout'),
            reverse('account_logout'),
            reverse('usuarios:politica_privacidade'),
            reverse('usuarios:termos_uso'),
            reverse('usuarios:registrar_consentimento'),
            reverse('usuarios:consentir_obrigatorio'),
            reverse('usuarios:gerenciar_consentimentos'),
        }


class IPClienteMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        cabecalho = getattr(settings, 'IP_CLIENTE_CABECALHO', None)
        if cabecalho:
            valor = request.META.get(cabecalho, '').strip()
            try:
                request.META['REMOTE_ADDR'] = str(ipaddress.ip_address(valor))
            except ValueError:
                pass
        return self.get_response(request)


class ConsentimentoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            rotas_liberadas = [
                '/usuarios/consentir/',
                '/usuarios/gerenciar_consentimentos/',
                '/usuarios/ativar-2fa/',
                '/usuarios/verify-2fa/',
                '/usuarios/desativar-2fa/',
                '/usuarios/logout/',
                '/accounts/logout/',
                '/usuarios/api/consentimento/',
                '/usuarios/politica-privacidade/',  
                '/usuarios/termos-uso/',            
                '/admin/', 
            ]
            
            if not any(request.path.startswith(rota) for rota in rotas_liberadas):
                tem_consentimento = ConsentimentoLGPD.verificar_consentimento_ativo(
                    request.user, 'tratamento_dados'
                )
                
                if not tem_consentimento:
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                        return JsonResponse({'error': 'Consentimento LGPD obrigatório pendente'}, status=403)
                    
                    return redirect('usuarios:consentir_obrigatorio')

        return self.get_response(request)