import logging
from django.utils import timezone
from .models import LogAuditoria

logger_seguranca = logging.getLogger('auditoria_seguranca')


def registrar_evento_2fa(usuario, evento, sucesso, ip_address=None, detalhes=None):
    email_usuario = usuario.email if hasattr(usuario, 'email') else str(usuario)
    
    mensagem = (
        f"Evento 2FA | Usuário: {email_usuario} | "
        f"Evento: {evento} | Sucesso: {sucesso} | "
        f"IP: {ip_address or 'N/A'}"
    )
    
    if detalhes:
        mensagem += f" | Detalhes: {detalhes}"
    
    if sucesso:
        logger_seguranca.info(mensagem)
    else:
        logger_seguranca.warning(mensagem)


def registrar_evento_autenticacao(usuario, evento, sucesso, ip_address=None):
    email_usuario = usuario.email if usuario and hasattr(usuario, 'email') else 'Desconhecido'
    
    mensagem = (
        f"Autenticação | Usuário: {email_usuario} | "
        f"Evento: {evento} | Sucesso: {sucesso} | "
        f"IP: {ip_address or 'N/A'}"
    )
    
    if sucesso:
        logger_seguranca.info(mensagem)
    else:
        logger_seguranca.warning(mensagem)


def registrar_evento_recuperacao_senha(email, encontrado, ip_address=None):
    mensagem = (
        f"Recuperação de senha solicitada | Email: {email} | "
        f"Usuário encontrado: {encontrado} | "
        f"IP: {ip_address or 'N/A'}"
    )
    
    if encontrado:
        logger_seguranca.info(mensagem)
    else:
        logger_seguranca.warning(mensagem)


def registrar_resultado_recuperacao_senha(usuario, sucesso, motivo=None):
    email_usuario = usuario.email if usuario and hasattr(usuario, 'email') else 'Desconhecido'
    
    mensagem = (
        f"Recuperação de senha finalizada | "
        f"Usuário: {email_usuario} | "
        f"Sucesso: {sucesso}"
    )
    
    if motivo:
        mensagem += f" | Motivo: {motivo}"
    
    if sucesso:
        logger_seguranca.info(mensagem)
    else:
        logger_seguranca.warning(mensagem)


def registrar_solicitacao_exclusao(usuario, campos_removidos, ip_address=None):
    mensagem = (
        f"Solicitação de exclusão de dados | Usuário: {usuario.email} | "
        f"Campos removidos: {', '.join(campos_removidos) if campos_removidos else 'nenhum'} | "
        f"IP: {ip_address or 'N/A'}"
    )
    
    logger_seguranca.info(mensagem)


def registrar_consentimento(usuario, tipo, versao, aceitou, ip_address=None):
    status = "Aceito" if aceitou else "Recusado"
    
    mensagem = (
        f"Consentimento LGPD | Usuário: {usuario.email} | "
        f"Tipo: {tipo} | Versão: {versao} | "
        f"Status: {status} | "
        f"IP: {ip_address or 'N/A'}"
    )
    
    if aceitou:
        logger_seguranca.info(mensagem)
    else:
        logger_seguranca.warning(mensagem)

# Função para registrar eventos de autenticação no modelo LogAuditoria:
def registrar_evento_autenticacao(usuario, evento, sucesso, ip_address=None):
    tipo_map = {
        'login': 'login',
        'logout': 'logout',
        'login_falha_senha': 'login_falha',
        'login_bloqueado': 'login_bloqueado',
    }
    
    tipo_evento = tipo_map.get(evento, 'outro')
    
    LogAuditoria.objects.create(
        usuario=usuario if usuario and hasattr(usuario, 'id') else None,
        tipo_evento=tipo_evento,
        ip_address=ip_address,
        sucesso=sucesso,
        mensagem=f"Autenticação - Evento: {evento} | Sucesso: {sucesso}"
    )