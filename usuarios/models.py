from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import AbstractUser, PermissionsMixin
from django.db import models
from django.conf import settings

class UsuarioManager(BaseUserManager):

    def create_user(self, email, password=None, funcionario=None, **extra_fields):
        if not email:
            raise ValueError("O usuário precisa de um e-mail.")

        is_superuser = extra_fields.get("is_superuser", False)
        if funcionario is None and not is_superuser:
            raise ValueError("Todo usuário precisa estar vinculado a um Funcionario.")

        email = self.normalize_email(email)
        usuario = self.model(email=email, funcionario=funcionario, **extra_fields)
        usuario.set_password(password)
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
        on_delete=models.PROTECT,
        related_name="usuario",
        null=True,
        blank=True,
    )

    tentativas_login_falhas = models.IntegerField(default=0)
    bloqueado_ate = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  

    objects = UsuarioManager()

    def __str__(self):
        return self.email

class LogAuditoria(models.Model):
    TIPO_EVENTO = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('login_falha', 'Falha de Login'),
        ('login_bloqueado', 'Login Bloqueado'),
        ('2fa_ativacao', 'Ativação 2FA'),
        ('2fa_verificacao_sucesso', 'Verificação 2FA - Sucesso'),
        ('2fa_verificacao_falha', 'Verificação 2FA - Falha'),
        ('2fa_desativacao', 'Desativação 2FA'),
        ('recuperacao_senha_solicitacao', 'Recuperação de Senha - Solicitação'),
        ('recuperacao_senha_sucesso', 'Recuperação de Senha - Sucesso'),
        ('recuperacao_senha_falha', 'Recuperação de Senha - Falha'),
        ('exclusao_dados', 'Exclusão de Dados'),
        ('consentimento_lgpd', 'Consentimento LGPD'),
        ('outro', 'Outro'),
    ]
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs_auditoria',
        verbose_name='Usuário'
    )
    tipo_evento = models.CharField(max_length=50, choices=TIPO_EVENTO, db_index=True)
    data_hora = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    sucesso = models.BooleanField(default=True)
    detalhes = models.JSONField(null=True, blank=True, help_text='Detalhes adicionais em formato JSON')
    mensagem = models.TextField(help_text='Mensagem descritiva do evento')
    
    class Meta:
        ordering = ['-data_hora']
        verbose_name = 'Log de Auditoria'
        verbose_name_plural = 'Logs de Auditoria'
        indexes = [
            models.Index(fields=['-data_hora']),
            models.Index(fields=['usuario', '-data_hora']),
            models.Index(fields=['tipo_evento', '-data_hora']),
        ]
    
    def __str__(self):
        usuario_str = self.usuario.email if self.usuario else 'Sistema'
        return f"{self.data_hora.strftime('%d/%m/%Y %H:%M')} - {usuario_str} - {self.get_tipo_evento_display()}"