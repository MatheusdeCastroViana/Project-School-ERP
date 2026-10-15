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

from .models_recuperacao import TokenRecuperacaoSenha
from .forms_recuperacao import SolicitarRecuperacaoForm, NovaSenhaForm
from usuarios.audit import (
    registrar_evento_recuperacao_senha,
    registrar_resultado_recuperacao_senha,
)

Usuario = get_user_model()


def _enviar_email_recuperacao(usuario, token, link_recuperacao):
    contexto = {
        'usuario': usuario,
        'link_recuperacao': link_recuperacao,
        'expira_em': token.expira_em,
    }
    
    html_message = render_to_string(
        'usuarios/email/recuperacao_senha.html',
        contexto
    )

    # versão de texto puro caso o usuário não suporte html
    plain_message = strip_tags(
        render_to_string(
            'usuarios/email/recuperacao_senha.txt',
            contexto
        )
    )
    
    assunto = 'Recuperação de Senha - ERP Escola Profissionalizante'
    remetente = getattr(settings, 'EMAIL_FROM', 'noreply@escolaprofissionalizante.com.br')
    destinatarios = [usuario.email]
    
    # Envia o e-mail
    send_mail(
        subject=assunto,
        message=plain_message,
        from_email=remetente,
        recipient_list=destinatarios,
        html_message=html_message,
        fail_silently=False,  # (para debug)
    )
    
    # Em desenvolvimento, também exibe no console para facilitar testes
    if settings.DEBUG:
        print(f"\n{'='*60}")
        print(f"LINK DE RECUPERAÇÃO DE SENHA (Ambiente de Desenvolvimento)")
        print(f"{'='*60}")
        print(f"Usuário: {usuario.email}")
        print(f"Token: {token.token}")
        print(f"Expira em: {token.expira_em}")
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

            # Registrando a tentativa mesmo que não ache o usuário
            registrar_evento_recuperacao_senha(
                email=form.cleaned_data['email'],
                encontrado=bool(usuario),
                ip_address=ip_address,
            )

            if usuario:
                # Gerando novo token de recuperação
                token = TokenRecuperacaoSenha.objects.create(
                    usuario=usuario,
                    ip_solicitacao=ip_address,
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )

                # Constrói o link completo de recuperação
                link_recuperacao = request.build_absolute_uri(
                    f'/usuarios/recuperar-senha/{token.token}/'
                )

                # Enviando o e-mail de recuperação
                try:
                    _enviar_email_recuperacao(usuario, token, link_recuperacao)
                except Exception as e:
                    # Em produção, loga o erro mas não expõe ao usuário
                    import logging
                    logger = logging.getLogger('auditoria_seguranca')
                    logger.error(
                        f"Falha ao enviar e-mail de recuperação | "
                        f"Usuário: {usuario.email} | "
                        f"Erro: {str(e)}"
                    )

            # Mensagem genérica
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

    # Buscando o token no banco de dados
    try:
        token_obj = TokenRecuperacaoSenha.objects.get(token=token)
    except TokenRecuperacaoSenha.DoesNotExist:
        registrar_resultado_recuperacao_senha(
            usuario=None,
            sucesso=False,
            motivo="token inexistente",
        )
        messages.error(
            request,
            'Link de recuperação inválido ou expirado. '
            'Por favor, solicite um novo link.'
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
            'Link de recuperação inválido ou expirado. '
            'Por favor, solicite um novo link.'
        )
        return redirect('usuarios:solicitar_recuperacao')

    if request.method == 'POST':
        form = NovaSenhaForm(request.POST)

        if form.is_valid():
            usuario = token_obj.usuario
            usuario.set_password(form.cleaned_data['senha1'])
            usuario.save()

            token_obj.marcar_como_utilizado()

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