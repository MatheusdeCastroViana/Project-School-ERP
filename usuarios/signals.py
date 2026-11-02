from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver

from .audit import registrar_evento_autenticacao

# sinal pra registrar logout no log sem duplicação 
@receiver(user_logged_out, dispatch_uid='usuarios_registrar_logout')
def registrar_logout(sender, request, user, **kwargs):
    if user is None:
        return
    ip_address = request.META.get('REMOTE_ADDR') if request is not None else None
    registrar_evento_autenticacao(
        usuario=user,
        evento='logout',
        sucesso=True,
        ip_address=ip_address,
    )