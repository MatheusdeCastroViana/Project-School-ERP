from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import AbstractUser, PermissionsMixin
from django.db import models

"""
O AbstractUser padrão do Django cria seta o username como a informação principal para o login, mas no
nosso caso o login será feito com o email e senha, que é mais comum em sistemas escolares.
Então é preciso criar essa outra classe UsuarioManager para criar os usuarios de forma mais customizada.
"""

class UsuarioManager(BaseUserManager):
    

    def create_user(self, email, password=None, funcionario=None, **extra_fields):
        if not email:
            raise ValueError("O usuário precisa de um e-mail.")
        if funcionario is None:
            raise ValueError("Todo usuário precisa estar vinculado a um Funcionario.")

        email = self.normalize_email(email)
        usuario = self.model(email=email, funcionario=funcionario, **extra_fields)
        usuario.set_password(password)  # O hash e salt ficam dentro de password (PBKDF2 com SHA256 padrão)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email, password=None, funcionario=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser precisa ter is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser precisa ter is_superuser=True.")

        return self.create_user(email, password, funcionario, **extra_fields)


class Usuario(AbstractUser):
    # Como o login será por email, não usaremos username.
    username = None

    email = models.EmailField(unique=True)

    funcionario = models.OneToOneField(
        "funcionarios.Funcionario",  
        on_delete=models.PROTECT,    # Não permite apagar um Funcionario que tenha login ativo
        related_name="usuario",
    )

    tentativas_login_falhas = models.IntegerField(default=0)
    bloqueado_ate = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # Campos extras exigidos no createsuperuser, além de email/password

    objects = UsuarioManager()

    def __str__(self):
        return self.email