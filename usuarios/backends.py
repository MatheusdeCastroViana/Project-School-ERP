from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from .audit import registrar_evento_autenticacao

from .models_2fa import Configuracao2FA

Usuario = get_user_model()


class UsuarioBackend(ModelBackend):
    def authenticate(self, request, username=None, email=None, password=None, **kwargs):
        email = email or username

        if email is None or password is None:
            return None

        try:
            usuario = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:

            return None

        if usuario.bloqueado_ate is not None and usuario.bloqueado_ate > timezone.now():
            registrar_evento_autenticacao(
                usuario=usuario,
                evento='login_bloqueado',
                sucesso=False,
                ip_address=request.META.get('REMOTE_ADDR') if request else None
            )
            return None

        if usuario.check_password(password):
            if not self.user_can_authenticate(usuario):
                return None

            usuario.tentativas_login_falhas = 0
            usuario.bloqueado_ate = None
            usuario.save()

            try:
                config_2fa = usuario.config_2fa
                if config_2fa.ativado:

                    if request:
                        request.session['usuario_pendente_2fa'] = usuario.id
                    
                    return None
            except Configuracao2FA.DoesNotExist:
                pass
            except AttributeError:
                pass

            registrar_evento_autenticacao(
                usuario=usuario,
                evento='login_sucesso',
                sucesso=True,
                ip_address=request.META.get('REMOTE_ADDR') if request else None
            )

            return usuario
        else:
            usuario.tentativas_login_falhas += 1
            
            if usuario.tentativas_login_falhas >= settings.LOGIN_MAX_TENTATIVAS:
                usuario.bloqueado_ate = timezone.now() + timedelta(
                    minutes=settings.LOGIN_BLOQUEIO_MINUTOS
                )
            
            usuario.save()

            registrar_evento_autenticacao(
                usuario=usuario,
                evento='login_falha_senha',
                sucesso=False,
                ip_address=request.META.get('REMOTE_ADDR') if request else None
            )

            return None