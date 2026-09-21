from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as django_logout
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import get_user_model, login
from .models_2fa import Configuracao2FA
from .audit import registrar_evento_2fa, registrar_evento_autenticacao

Usuario = get_user_model()


@login_required
def dashboard(request):
    """
    View do Dashboard do usuário autenticado.
    Exibe informações básicas do usuário e o status de segurança (2FA).
    O decorator @login_required garante que apenas usuários autenticados 
    possam acessar esta tela (Requisito RF-04).
    """
    # Tenta obter a configuração de 2FA do usuário, se existir
    try:
        config_2fa = request.user.config_2fa
        tem_2fa = config_2fa.ativado
    except Configuracao2FA.DoesNotExist:
        tem_2fa = False

    context = {
        'usuario': request.user,
        'tem_2fa': tem_2fa,
    }
    return render(request, 'usuarios/dashboard.html', context)


@login_required
def logout_usuario(request):
    """
    View customizada de logout para garantir o registro em log de auditoria
    ANTES de destruir a sessão do usuário.
    
    Atende ao requisito RA-5.1: Registrar logs de logout.
    Atende ao requisito RS-1.10: Invalidação de sessão no logout.
    """
    # 1. Registra o evento de logout no log de auditoria de segurança
    registrar_evento_autenticacao(
        usuario=request.user,
        evento='logout',
        sucesso=True,
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    # 2. Invalida a sessão do Django (destrói os dados da sessão e o cookie sessionid)
    django_logout(request)
    
    # 3. Redireciona para a tela de login
    return redirect('account_login')


# --- Views de 2FA (Mantidas para funcionamento completo) ---

@login_required
def ativar_2fa(request):
    try:
        config = request.user.config_2fa
    except Configuracao2FA.DoesNotExist:
        config = Configuracao2FA.objects.create(usuario=request.user)

    if request.method == 'POST':
        token = request.POST.get('token', '').strip()
        if config.verify_token(token):
            config.ativado = True
            config.save()
            registrar_evento_2fa(usuario=request.user, evento='ativacao', sucesso=True, ip_address=request.META.get('REMOTE_ADDR'))
            messages.success(request, '2FA ativado com sucesso! Seu login agora está mais seguro.')
            return redirect('usuarios:dashboard')
        else:
            registrar_evento_2fa(usuario=request.user, evento='ativacao', sucesso=False, ip_address=request.META.get('REMOTE_ADDR'), detalhes='Token inválido')
            messages.error(request, 'Código inválido. Verifique o código no seu aplicativo e tente novamente.')

    context = {'config': config, 'qr_code': config.get_qrcode_base64(), 'chave_secreta': config.chave_secreta}
    return render(request, 'usuarios/ativar_2fa.html', context)


@login_required
def desativar_2fa(request):
    if request.method == 'POST':
        try:
            config = request.user.config_2fa
            config.ativado = False
            config.save()
            registrar_evento_2fa(usuario=request.user, evento='desativacao', sucesso=True, ip_address=request.META.get('REMOTE_ADDR'))
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
                registrar_evento_2fa(usuario=usuario, evento='verificacao_sucesso', sucesso=True, ip_address=request.META.get('REMOTE_ADDR'))
                messages.success(request, 'Autenticação 2FA concluída com sucesso!')
                return redirect('usuarios:dashboard')
            else:
                registrar_evento_2fa(usuario=usuario, evento='verificacao_falha', sucesso=False, ip_address=request.META.get('REMOTE_ADDR'), detalhes='Token inválido')
                messages.error(request, 'Código 2FA inválido. Tente novamente.')
        except (Usuario.DoesNotExist, Configuracao2FA.DoesNotExist):
            messages.error(request, 'Erro na verificação. Faça login novamente.')
            return redirect('account_login')
    return render(request, 'usuarios/verificar_2fa.html')