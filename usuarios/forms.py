from django import forms
from allauth.account.forms import ResetPasswordForm, ResetPasswordKeyForm, UserTokenForm
from django.contrib.auth import get_user_model
from usuarios.audit import registrar_evento_recuperacao_senha, registrar_resultado_recuperacao_senha

Usuario = get_user_model()


class CustomResetPasswordForm(ResetPasswordForm): # Herda os atributos da classe ResetPasswordForm do allauth
    def clean_email(self):
        email = self.cleaned_data["email"]

        # Se o usuário for criado no admin ou no shell, ele não tem EmailAddress, mas tem Usuario.email
        # Então já busca direto Usuario.email ao invés de EmailAddress do allauth
        self.users = list(
            Usuario.objects.filter(email__iexact=email, is_active=True)
        )

        return email


    def save(self, request, **kwargs):
        ip_address = request.META.get("REMOTE_ADDR") if request else None

        registrar_evento_recuperacao_senha(
            email=self.cleaned_data["email"],
            encontrado=bool(self.users), # Não mostra qual é o usuário
            ip_address=ip_address,
        )

        return super().save(request, **kwargs)

class CustomUserTokenForm(UserTokenForm):
    def clean(self):
        try:
            return super().clean()
        except forms.ValidationError: # Aqui é onde pega a falha de recuperação para adicionar no log
            registrar_resultado_recuperacao_senha(
                usuario=getattr(self, "reset_user", None),
                sucesso=False,
                motivo="token inválido, expirado ou já utilizado",
            )
            raise

class CustomResetPasswordKeyForm(ResetPasswordKeyForm):
    def save(self): 
        # Aqui é onde pega o sucesso de recuperação para adicionar no log
        super().save()
        registrar_resultado_recuperacao_senha(usuario=self.user, sucesso=True)