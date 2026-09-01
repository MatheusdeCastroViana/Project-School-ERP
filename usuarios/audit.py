"""
Aqui vai atender ao requisito RA-5.2: Logs de falhas e 2FA sem expor códigos.
"""
import logging

# Aqui vai configurar logger específico para auditoria de segurança
logger_seguranca = logging.getLogger('auditoria_seguranca')


def registrar_evento_2fa(usuario, evento, sucesso, ip_address=None, detalhes=None):
   
    mensagem = (
        f"Evento 2FA | Usuário: {usuario.email} | "
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

    mensagem = (
        f"Autenticação | Usuário: {usuario.email if usuario else 'Desconhecido'} | "
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

    logger_seguranca.info(mensagem)

def registrar_resultado_recuperacao_senha(usuario, sucesso, motivo=None):
    mensagem = (
        f"Recuperação de senha finalizada | "
        f"Usuário: {usuario.email if usuario else 'Desconhecido'} | "
        f"Sucesso: {sucesso}"
    )

    if motivo:
        mensagem += f" | Motivo: {motivo}"

    if sucesso:
        logger_seguranca.info(mensagem)
    else:
        logger_seguranca.warning(mensagem)