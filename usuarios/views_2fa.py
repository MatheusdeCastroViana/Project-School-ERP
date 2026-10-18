from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as django_logout
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import get_user_model, login
from django.conf import settings
from django.db import transaction
from datetime import timedelta
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
    registrar_evento_2fa(usuario=request.user, evento='desativacao', sucesso=False, ip_address=request.META.get('REMOTE_ADDR'), detalhes='Tentativa bloqueada: 2FA obrigatório')
    messages.error(request, 'O 2FA é obrigatório para todos os usuários e não pode ser desativado.')
    return redirect('usuarios:dashboard')


def _limpar_sessao_pendente_2fa(request):
    request.session.pop('usuario_pendente_2fa', None)
    request.session.pop('usuario_pendente_2fa_em', None)


def verificar_2fa(request):
    usuario_id = request.session.get('usuario_pendente_2fa')
    if not usuario_id:
        return redirect('account_login')

    iniciado_em = request.session.get('usuario_pendente_2fa_em')
    validade_segundos = settings.TWOFA_PENDENTE_MINUTOS * 60
    if iniciado_em is None or timezone.now().timestamp() - iniciado_em > validade_segundos:
        usuario_expirado = Usuario.objects.filter(id=usuario_id).first()
        if usuario_expirado:
            registrar_evento_2fa(usuario=usuario_expirado, evento='sessao_expirada', sucesso=False, ip_address=request.META.get('REMOTE_ADDR'), detalhes='Tempo para informar o código esgotado')
        _limpar_sessao_pendente_2fa(request)
        messages.error(request, 'O tempo para informar o código expirou. Faça login novamente.')
        return redirect('account_login')

    if request.method == 'POST':
        token = request.POST.get('token', '').strip()
        ip_address = request.META.get('REMOTE_ADDR')
        try:
            with transaction.atomic():
                config = Configuracao2FA.objects.select_for_update().select_related('usuario').get(usuario_id=usuario_id)
                usuario = config.usuario
                agora = timezone.now()

                if usuario.bloqueado_ate is not None and usuario.bloqueado_ate > agora:
                    resultado = 'bloqueado'
                elif config.verify_token(token):
                    config.tentativas_falhas = 0
                    config.ultimo_uso = agora
                    config.save(update_fields=['tentativas_falhas', 'ultimo_uso'])
                    resultado = 'sucesso'
                else:
                    config.tentativas_falhas += 1
                    if config.tentativas_falhas >= settings.TWOFA_MAX_TENTATIVAS:
                        usuario.bloqueado_ate = agora + timedelta(minutes=settings.LOGIN_BLOQUEIO_MINUTOS)
                        usuario.save(update_fields=['bloqueado_ate'])
                        config.tentativas_falhas = 0
                        resultado = 'bloqueou'
                    else:
                        resultado = 'falha'
                    config.save(update_fields=['tentativas_falhas'])
        except Configuracao2FA.DoesNotExist:
            _limpar_sessao_pendente_2fa(request)
            messages.error(request, 'Erro na verificação. Faça login novamente.')
            return redirect('account_login')

        if resultado == 'bloqueado':
            _limpar_sessao_pendente_2fa(request)
            messages.error(request, 'Conta temporariamente bloqueada. Tente novamente mais tarde.')
            return redirect('account_login')

        if resultado == 'sucesso':
            login(request, usuario, backend='usuarios.backends.UsuarioBackend')
            _limpar_sessao_pendente_2fa(request)
            registrar_evento_2fa(usuario=usuario, evento='verificacao_sucesso', sucesso=True, ip_address=ip_address)
            messages.success(request, 'Autenticação 2FA concluída com sucesso!')
            return redirect('dashboard:home')

        registrar_evento_2fa(usuario=usuario, evento='verificacao_falha', sucesso=False, ip_address=ip_address, detalhes='Token inválido')

        if resultado == 'bloqueou':
            registrar_evento_2fa(usuario=usuario, evento='bloqueio', sucesso=False, ip_address=ip_address, detalhes=f'{settings.TWOFA_MAX_TENTATIVAS} códigos inválidos seguidos; conta bloqueada por {settings.LOGIN_BLOQUEIO_MINUTOS} minutos')
            _limpar_sessao_pendente_2fa(request)
            messages.error(request, 'Muitas tentativas inválidas. Sua conta foi bloqueada temporariamente.')
            return redirect('account_login')

        messages.error(request, 'Código 2FA inválido. Tente novamente.')
    return render(request, 'usuarios/verificar_2fa.html')