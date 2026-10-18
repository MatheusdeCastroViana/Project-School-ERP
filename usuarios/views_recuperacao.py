from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
import logging

from .models_recuperacao import TokenRecuperacaoSenha, hash_token
from .forms_recuperacao import SolicitarRecuperacaoForm, NovaSenhaForm
from usuarios.audit import (
    registrar_evento_recuperacao_senha,
    registrar_resultado_recuperacao_senha,
)

Usuario = get_user_model()
logger = logging.getLogger('auditoria_seguranca')


def _enviar_email_recuperacao(usuario, token_obj, token_cru, link_recuperacao):
    """
    Envia o e-mail de recuperação.
    
    Args:
        usuario: Objeto do usuário
        token_obj: Objeto TokenRecuperacaoSenha (para pegar expira_em)
        token_cru: String do token sem hash (para o link e debug)
        link_recuperacao: URL completa de recuperação
    """
    contexto = {
        'usuario': usuario,
        'link_recuperacao': link_recuperacao,
        'expira_em': token_obj.expira_em,
    }
    
    html_message = render_to_string(
        'usuarios/email/recuperacao_senha.html',
        contexto
    )

    plain_message = strip_tags(
        render_to_string(
            'usuarios/email/recuperacao_senha.txt',
            contexto
        )
    )
    
    assunto = 'Recuperação de Senha - ERP Escola Profissionalizante'
    # CORREÇÃO: Usar DEFAULT_FROM_EMAIL, que é o padrão do Django e do Resend
    remetente = getattr(settings, 'DEFAULT_FROM_EMAIL', 'onboarding@resend.dev')
    destinatarios = [usuario.email]
    
    try:
        send_mail(
            subject=assunto,
            message=plain_message,
            from_email=remetente,
            recipient_list=destinatarios,
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        logger.error(f"Falha ao enviar e-mail de recuperação | Usuário: {usuario.email} | Erro: {str(e)}")
        raise
    
    # Em desenvolvimento, exibe no console para facilitar testes
    if settings.DEBUG:
        print(f"\n{'='*60}")
        print(f"LINK DE RECUPERAÇÃO DE SENHA (Ambiente de Desenvolvimento)")
        print(f"{'='*60}")
        print(f"Usuário: {usuario.email}")
        print(f"Token Cru (para URL): {token_cru}")
        print(f"Expira em: {token_obj.expira_em}")
        print(f"Link: {link_recuperacao}")
        print(f"{'='*60}\n")


@csrf_protect
@never_cache
def solicitar_recuperacao(request):
    if request.method == 'POST':
        form = SolicitarRecuperacaoForm(request.POST)

        if form.is_valid():
            usuario = form.usuario_encontrado
            ip_address = request.META.get('REMOTE_ADDR')

            registrar_evento_recuperacao_senha(
                email=form.cleaned_data['email'],
                encontrado=bool(usuario),
                ip_address=ip_address,
            )

            if usuario:
                # CORREÇÃO: Usar o método gerar() que retorna a tupla (objeto, token_cru)
                token_obj, token_cru = TokenRecuperacaoSenha.gerar(
                    usuario=usuario,
                    ip_solicitacao=ip_address,
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )

                # O link DEVE usar token_cru (string), não o hash
                link_recuperacao = request.build_absolute_uri(
                    f'/usuarios/recuperar-senha/{token_cru}/'
                )

                # Passamos o objeto E a string para a função de e-mail
                _enviar_email_recuperacao(usuario, token_obj, token_cru, link_recuperacao)

            messages.success(
                request,
                'Se o e-mail informado estiver cadastrado no sistema, '
                'você receberá um link para recuperação de senha.'
            )
            return redirect('usuarios:solicitar_recuperacao')
    else:
        form = SolicitarRecuperacaoForm()

    context = {'form': form}
    return render(request, 'usuarios/solicitar_recuperacao.html', context)


@csrf_protect
@never_cache
def confirmar_recuperacao(request, token):
    """
    View para validar token e permitir definição de nova senha.
    """
    try:
        # O token da URL é cru, precisamos hashear para buscar no banco
        token_obj = TokenRecuperacaoSenha.objects.get(token=hash_token(token))
    except TokenRecuperacaoSenha.DoesNotExist:
        registrar_resultado_recuperacao_senha(
            usuario=None,
            sucesso=False,
            motivo="token inexistente",
        )
        messages.error(
            request,
            'Link de recuperação inválido ou expirado. Por favor, solicite um novo link.'
        )
        return redirect('usuarios:solicitar_recuperacao')

    if not token_obj.is_valido():
        motivo = "token já utilizado" if token_obj.utilizado else "token expirado"
        registrar_resultado_recuperacao_senha(
            usuario=token_obj.usuario,
            sucesso=False,
            motivo=motivo,
        )
        messages.error(
            request,
            'Link de recuperação inválido ou expirado. Por favor, solicite um novo link.'
        )
        return redirect('usuarios:solicitar_recuperacao')

    if request.method == 'POST':
        form = NovaSenhaForm(request.POST)

        if form.is_valid():
            usuario = token_obj.usuario
            usuario.set_password(form.cleaned_data['senha1'])
            usuario.tentativas_login_falhas = 0
            usuario.bloqueado_ate = None
            usuario.save()

            token_obj.marcar_como_utilizado()
            TokenRecuperacaoSenha.objects.filter(
                usuario=usuario, utilizado=False
            ).update(utilizado=True, utilizado_em=timezone.now())

            registrar_resultado_recuperacao_senha(usuario=usuario, sucesso=True)

            messages.success(
                request,
                'Senha alterada com sucesso! Você já pode fazer login com a nova senha.'
            )
            return redirect('account_login')
    else:
        form = NovaSenhaForm()

    context = {
        'form': form,
        'token': token,
        'expira_em': token_obj.expira_em
    }
    return render(request, 'usuarios/confirmar_recuperacao.html', context)