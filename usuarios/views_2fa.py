"""
Essa são as views para gerenciamento e verificação do 2FA.
"""
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from .models_2fa import Configuracao2FA
from .audit import registrar_evento_2fa
import pyotp


@login_required
def ativar_2fa(request):
    """
    View para ativar o 2FA do usuário.
    Gera chave secreta e QR Code para configuração no Google Authenticator.
    """
    try:
        config = request.user.config_2fa
    except Configuracao2FA.DoesNotExist:
        config = Configuracao2FA.objects.create(usuario=request.user)

    if request.method == 'POST':
        token = request.POST.get('token')
        
        if config.verify_token(token):
            config.ativado = True
            config.save()
            
            registrar_evento_2fa(
                usuario=request.user,
                evento='ativacao',
                sucesso=True,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, '2FA ativado com sucesso!')
            return redirect('usuarios:dashboard')
        else:
            messages.error(request, 'Código inválido. Tente novamente.')
            registrar_evento_2fa(
                usuario=request.user,
                evento='ativacao',
                sucesso=False,
                ip_address=request.META.get('REMOTE_ADDR'),
                detalhes='Token inválido durante ativação'
            )

    context = {
        'config': config,
        'qr_code': config.get_qrcode_base64(),
        'chave_secreta': config.chave_secreta,
    }
    return render(request, 'usuarios/ativar_2fa.html', context)


@login_required
def desativar_2fa(request):
    """
    View para desativar o 2FA do usuário.
    """
    if request.method == 'POST':
        try:
            config = request.user.config_2fa
            config.ativado = False
            config.save()
            
            registrar_evento_2fa(
                usuario=request.user,
                evento='desativacao',
                sucesso=True,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, '2FA desativado.')
            return redirect('usuarios:dashboard')
        except Configuracao2FA.DoesNotExist:
            messages.error(request, '2FA não está configurado.')
    
    return render(request, 'usuarios/desativar_2fa.html')


def verificar_2fa(request):
    """
    View para verificar o código 2FA após login bem-sucedido.
    """
    if request.method == 'POST':
        token = request.POST.get('token')
        usuario_id = request.session.get('usuario_pendente_2fa')
        
        if not usuario_id:
            return redirect('account_login')
        
        from django.contrib.auth import get_user_model
        Usuario = get_user_model()
        
        try:
            usuario = Usuario.objects.get(id=usuario_id)
            config = usuario.config_2fa
            
            if config.verify_token(token):
                from django.contrib.auth import login
                login(request, usuario, backend='usuarios.backends.UsuarioBackend')
                
                del request.session['usuario_pendente_2fa']
                
                config.ultimo_uso = timezone.now()
                config.save()
                
                registrar_evento_2fa(
                    usuario=usuario,
                    evento='verificacao_sucesso',
                    sucesso=True,
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                return redirect('usuarios:dashboard')
            else:
                messages.error(request, 'Código 2FA inválido.')
                registrar_evento_2fa(
                    usuario=usuario,
                    evento='verificacao_falha',
                    sucesso=False,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    detalhes='Token inválido durante verificação'
                )
        except (Usuario.DoesNotExist, Configuracao2FA.DoesNotExist):
            messages.error(request, 'Erro na verificação.')
            return redirect('account_login')
    
    return render(request, 'usuarios/verificar_2fa.html')

@login_required
def dashboard(request):
    tem_2fa = False
    if hasattr(request.user, 'config_2fa'):
        tem_2fa = request.user.config_2fa.ativado

    status_2fa = "ATIVADO" if tem_2fa else "DESATIVADO"

    html = f"""
    <h1>Login Realizado com Sucesso!</h1>
    <p>Bem-vindo, <strong>{request.user.email}</strong>.</p>
    <p>Status do 2FA: <strong>{status_2fa}</strong></p>
    <hr>
    <ul>
        <li><a href="/usuarios/ativar-2fa/">Ativar 2FA</a></li>
        <li><a href="/accounts/logout/">Sair (Logout)</a></li>
    </ul>
    """
    return HttpResponse(html)