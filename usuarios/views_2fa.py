from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.utils import timezone
from .models_2fa import Configuracao2FA
from .audit import registrar_evento_2fa

Usuario = get_user_model()


@login_required
def ativar_2fa(request):
    """View para ativar o 2FA do usuário logado."""
    try:
        config = request.user.config_2fa
    except Configuracao2FA.DoesNotExist:
        config = Configuracao2FA.objects.create(usuario=request.user)

    if request.method == 'POST':
        token = request.POST.get('token', '').strip()
        
        if config.verify_token(token):
            config.ativado = True
            config.save()
            
            registrar_evento_2fa(
                usuario=request.user,
                evento='ativacao',
                sucesso=True,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, '2FA ativado com sucesso! Seu login agora está mais seguro.')
            return redirect('usuarios:dashboard')
        else:
            registrar_evento_2fa(
                usuario=request.user,
                evento='ativacao',
                sucesso=False,
                ip_address=request.META.get('REMOTE_ADDR'),
                detalhes='Token inválido durante ativação'
            )
            messages.error(request, 'Código inválido. Verifique o código no seu aplicativo e tente novamente.')

    context = {
        'config': config,
        'qr_code': config.get_qrcode_base64(),
        'chave_secreta': config.chave_secreta,
    }
    return render(request, 'usuarios/ativar_2fa.html', context)


@login_required
def desativar_2fa(request):
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
            
            messages.success(request, '2FA desativado com sucesso.')
            return redirect('usuarios:dashboard')
        except Configuracao2FA.DoesNotExist:
            messages.error(request, '2FA não está configurado para sua conta.')
    
    return render(request, 'usuarios/desativar_2fa.html')


def verificar_2fa(request):
    usuario_id = request.session.get('usuario_pendente_2fa')
    
    if not usuario_id:
        return redirect('account_login')
    
    if request.method == 'POST':
        token = request.POST.get('token', '').strip()
        
        try:
            usuario = Usuario.objects.get(id=usuario_id)
            config = usuario.config_2fa
            
            if config.verify_token(token):
                login(request, usuario, backend='usuarios.backends.UsuarioBackend')
                
                if 'usuario_pendente_2fa' in request.session:
                    del request.session['usuario_pendente_2fa']
                
                config.ultimo_uso = timezone.now()
                config.save()
                
                registrar_evento_2fa(
                    usuario=usuario,
                    evento='verificacao_sucesso',
                    sucesso=True,
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, 'Autenticação 2FA concluída com sucesso!')
                return redirect('usuarios:dashboard')
            else:
                registrar_evento_2fa(
                    usuario=usuario,
                    evento='verificacao_falha',
                    sucesso=False,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    detalhes='Token inválido durante verificação'
                )
                messages.error(request, 'Código 2FA inválido. Tente novamente.')
                
        except Usuario.DoesNotExist:
            messages.error(request, 'Erro na verificação. Faça login novamente.')
            return redirect('account_login')
        except Configuracao2FA.DoesNotExist:
            messages.error(request, 'Erro na configuração 2FA. Contate o administrador.')
            return redirect('account_login')
    
    return render(request, 'usuarios/verificar_2fa.html')


@login_required
def dashboard(request):
    context = {
        'usuario': request.user,
        'config_2fa': getattr(request.user, 'config_2fa', None),
    }
    return render(request, 'usuarios/dashboard.html', context)