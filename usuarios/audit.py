import logging
from django.contrib.auth import get_user_model
from .models import LogAuditoria

logger_seguranca = logging.getLogger('auditoria_seguranca')

TIPOS_VALIDOS = {tipo for tipo, _ in LogAuditoria.TIPO_EVENTO}

TIPO_AUTENTICACAO = {
    'login': 'login',
    'login_sucesso': 'login',
    'logout': 'logout',
    'login_falha_senha': 'login_falha',
    'login_falha_usuario_inexistente': 'login_falha',
    'login_falha_conta_inativa': 'login_falha',
    'login_bloqueado': 'login_bloqueado',
}


def _gravar_no_banco(usuario, tipo_evento, sucesso, mensagem, ip_address=None, detalhes=None):
    try:
        LogAuditoria.objects.create(
            usuario=usuario if usuario is not None and getattr(usuario, 'pk', None) else None,
            tipo_evento=tipo_evento if tipo_evento in TIPOS_VALIDOS else 'outro',
            ip_address=ip_address or None,
            sucesso=sucesso,
            mensagem=mensagem,
            detalhes=detalhes or None,
        )
    except Exception:
        logger_seguranca.exception('Falha ao gravar o evento na tabela LogAuditoria')


def _gravar_no_arquivo(mensagem, sucesso):
    if sucesso:
        logger_seguranca.info(mensagem)
    else:
        logger_seguranca.warning(mensagem)


def registrar_evento_2fa(usuario, evento, sucesso, ip_address=None, detalhes=None):
    email_usuario = usuario.email if hasattr(usuario, 'email') else str(usuario)

    mensagem = (
        f"Evento 2FA | Usuário: {email_usuario} | "
        f"Evento: {evento} | Sucesso: {sucesso} | "
        f"IP: {ip_address or 'N/A'}"
    )

    if detalhes:
        mensagem += f" | Detalhes: {detalhes}"

    _gravar_no_arquivo(mensagem, sucesso)
    _gravar_no_banco(
        usuario=usuario,
        tipo_evento=f"2fa_{evento}",
        sucesso=sucesso,
        mensagem=mensagem,
        ip_address=ip_address,
        detalhes={'detalhes': detalhes} if detalhes else None,
    )


def registrar_evento_autenticacao(usuario, evento, sucesso, ip_address=None, detalhes=None):
    email_usuario = usuario.email if usuario and hasattr(usuario, 'email') else 'Desconhecido'

    mensagem = (
        f"Autenticação | Usuário: {email_usuario} | "
        f"Evento: {evento} | Sucesso: {sucesso} | "
        f"IP: {ip_address or 'N/A'}"
    )

    if detalhes:
        mensagem += f" | Detalhes: {detalhes}"

    _gravar_no_arquivo(mensagem, sucesso)
    _gravar_no_banco(
        usuario=usuario,
        tipo_evento=TIPO_AUTENTICACAO.get(evento, 'outro'),
        sucesso=sucesso,
        mensagem=mensagem,
        ip_address=ip_address,
        detalhes=detalhes,
    )


def registrar_evento_recuperacao_senha(email, encontrado, ip_address=None):
    mensagem = (
        f"Recuperação de senha solicitada | Email: {email} | "
        f"Usuário encontrado: {encontrado} | "
        f"IP: {ip_address or 'N/A'}"
    )

    _gravar_no_arquivo(mensagem, encontrado)

    usuario = get_user_model().objects.filter(email=email).first()
    _gravar_no_banco(
        usuario=usuario,
        tipo_evento='recuperacao_senha_solicitacao',
        sucesso=encontrado,
        mensagem=mensagem,
        ip_address=ip_address,
        detalhes={'email': str(email)[:254], 'usuario_encontrado': bool(encontrado)},
    )


def registrar_resultado_recuperacao_senha(usuario, sucesso, motivo=None):
    email_usuario = usuario.email if usuario and hasattr(usuario, 'email') else 'Desconhecido'

    mensagem = (
        f"Recuperação de senha finalizada | "
        f"Usuário: {email_usuario} | "
        f"Sucesso: {sucesso}"
    )

    if motivo:
        mensagem += f" | Motivo: {motivo}"

    _gravar_no_arquivo(mensagem, sucesso)
    _gravar_no_banco(
        usuario=usuario,
        tipo_evento='recuperacao_senha_sucesso' if sucesso else 'recuperacao_senha_falha',
        sucesso=sucesso,
        mensagem=mensagem,
        detalhes={'motivo': motivo} if motivo else None,
    )


def registrar_solicitacao_exclusao(usuario, campos_removidos, ip_address=None):
    mensagem = (
        f"Solicitação de exclusão de dados | Usuário: {usuario.email} | "
        f"Campos removidos: {', '.join(campos_removidos) if campos_removidos else 'nenhum'} | "
        f"IP: {ip_address or 'N/A'}"
    )

    _gravar_no_arquivo(mensagem, True)
    _gravar_no_banco(
        usuario=usuario,
        tipo_evento='exclusao_dados',
        sucesso=True,
        mensagem=mensagem,
        ip_address=ip_address,
        detalhes={'campos_removidos': list(campos_removidos or [])},
    )


def registrar_consentimento(usuario, tipo, versao, aceitou, ip_address=None):
    status = "Aceito" if aceitou else "Recusado"

    mensagem = (
        f"Consentimento LGPD | Usuário: {usuario.email} | "
        f"Tipo: {tipo} | Versão: {versao} | "
        f"Status: {status} | "
        f"IP: {ip_address or 'N/A'}"
    )

    _gravar_no_arquivo(mensagem, aceitou)
    _gravar_no_banco(
        usuario=usuario,
        tipo_evento='consentimento_lgpd',
        sucesso=True,
        mensagem=mensagem,
        ip_address=ip_address,
        detalhes={'tipo': tipo, 'versao': versao, 'aceitou': bool(aceitou)},
    )