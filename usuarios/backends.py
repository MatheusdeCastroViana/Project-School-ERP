from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

Usuario = get_user_model()

class UsuarioBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        # "username" já foi configurado antes como sendo email em USERNAME_FIELD = "email".

        email = username

        try:
            usuario = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            # Mensagem de erro sem dizer que o email não existe no banco.
            return None

        # Verifica bloqueio antes de checar a senha
        if usuario.bloqueado_ate is not None and usuario.bloqueado_ate > timezone.now():
            return None #Se tiver bloqueado, não retorna o usuario autenticado

        if usuario.check_password(password): # Senha correta
                
            # Testa se o usuário ainda tá ativo (pode ter sido demitido, mas acertou a senha)
            if not self.user_can_authenticate(usuario): 
                return None
            
            usuario.tentativas_login_falhas = 0
            usuario.bloqueado_ate = None
            usuario.save()
            return usuario # Retorna usuário autenticado
        else:
            usuario.tentativas_login_falhas += 1
            if usuario.tentativas_login_falhas >= settings.LOGIN_MAX_TENTATIVAS:
                usuario.bloqueado_ate = timezone.now() + timedelta(minutes=settings.LOGIN_BLOQUEIO_MINUTOS)
            usuario.save()
            return None