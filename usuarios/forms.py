from allauth.account.forms import ResetPasswordForm
from django.contrib.auth import get_user_model

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