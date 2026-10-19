import hashlib
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import AbstractUser, PermissionsMixin
from django.db import models
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.utils import timezone


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


class LogAuditoriaQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise PermissionDenied('Logs de auditoria são imutáveis e não podem ser alterados.')

    def delete(self):
        raise PermissionDenied('Logs de auditoria são imutáveis e não podem ser excluídos.')


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
        ('2fa_bloqueio', 'Bloqueio 2FA'),
        ('2fa_sessao_expirada', 'Sessão 2FA Expirada'),
        ('recuperacao_senha_solicitacao', 'Recuperação de Senha - Solicitação'),
        ('recuperacao_senha_sucesso', 'Recuperação de Senha - Sucesso'),
        ('recuperacao_senha_falha', 'Recuperação de Senha - Falha'),
        ('exclusao_dados', 'Exclusão de Dados'),
        ('consentimento_lgpd', 'Consentimento LGPD'),
        ('exportacao_dados', 'Exportação de Dados'),
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

    objects = LogAuditoriaQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise PermissionDenied('Logs de auditoria são imutáveis e não podem ser alterados.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied('Logs de auditoria são imutáveis e não podem ser excluídos.')

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

# MODELOS DE CONSENTIMENTO LGPD (Adicionados para atender requisitos 4.4 a 4.7)

class VersaoTextoConsentimento(models.Model):
    """Armazena as versões dos textos de consentimento. Imutável após criação."""
    TIPO_CONSENTIMENTO = [
        ('cookies_essenciais', 'Cookies Essenciais'),
        ('tratamento_dados', 'Tratamento de Dados Pessoais'),
        ('finalidades_administrativas', 'Finalidades Administrativas'),
        ('politica_privacidade', 'Política de Privacidade'),
        ('termos_uso', 'Termos de Uso'),
    ]
    
    tipo = models.CharField(max_length=50, choices=TIPO_CONSENTIMENTO, db_index=True)
    versao = models.CharField(max_length=20, help_text="Ex: 1.0, 1.1")
    texto_apresentado = models.TextField(help_text="Texto completo apresentado ao usuário")
    data_publicacao = models.DateTimeField(auto_now_add=True)
    ativa = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Versão de Texto de Consentimento'
        verbose_name_plural = 'Versões de Texto de Consentimento'
        ordering = ['-data_publicacao']
        unique_together = ['tipo', 'versao']

    def __str__(self):
        return f"{self.get_tipo_display()} - v{self.versao}"
    
    def save(self, *args, **kwargs):
        # Se esta versão está sendo marcada como ativa, desativar as outras do mesmo tipo
        if self.ativa:
            VersaoTextoConsentimento.objects.filter(tipo=self.tipo, ativa=True).exclude(pk=self.pk).update(ativa=False)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied('Versões de consentimento não podem ser excluídas.')


class ConsentimentoLGPDQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise PermissionDenied('Registros de consentimento são imutáveis.')
    
    def delete(self):
        raise PermissionDenied('Registros de consentimento são imutáveis.')


class ConsentimentoLGPD(models.Model):
    """Registro imutável de consentimentos LGPD pós-login."""
    STATUS_CONSENTIMENTO = [('aceito', 'Aceito'), ('recusado', 'Recusado'), ('revogado', 'Revogado')]
    TIPO_CONSENTIMENTO = VersaoTextoConsentimento.TIPO_CONSENTIMENTO
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='consentimentos_lgpd', 
        verbose_name='Usuário'
    )
    tipo = models.CharField(max_length=50, choices=TIPO_CONSENTIMENTO, db_index=True)
    versao = models.CharField(max_length=20)
    texto_hash = models.CharField(max_length=64, help_text="Hash SHA-256 do texto apresentado")
    status = models.CharField(max_length=20, choices=STATUS_CONSENTIMENTO, db_index=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    url_origem = models.URLField(blank=True, max_length=200)
    
    data_consentimento = models.DateTimeField(auto_now_add=True, db_index=True)
    data_revogacao = models.DateTimeField(null=True, blank=True)
    detalhes = models.JSONField(null=True, blank=True)
    
    objects = ConsentimentoLGPDQuerySet.as_manager()
    
    class Meta:
        verbose_name = 'Consentimento LGPD'
        verbose_name_plural = 'Consentimentos LGPD'
        ordering = ['-data_consentimento']
        indexes = [
            models.Index(fields=['usuario', '-data_consentimento']),
            models.Index(fields=['tipo', '-data_consentimento']),
        ]
    
    def __str__(self):
        usuario_str = self.usuario.email if self.usuario else 'Anônimo'
        return f"{usuario_str} - {self.get_tipo_display()} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise PermissionDenied('Registros de consentimento são imutáveis.')
        if self.status == 'revogado' and not self.data_revogacao:
            self.data_revogacao = timezone.now()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied('Registros de consentimento são imutáveis.')
    
    def revogar(self, ip_address=None):
        """Cria um novo registro marcando como revogado (padrão LGPD)."""
        if self.status == 'revogado':
            raise ValueError('Já revogado.')
        ConsentimentoLGPD.objects.create(
            usuario=self.usuario, 
            tipo=self.tipo, 
            versao=self.versao,
            texto_hash=self.texto_hash, 
            status='revogado',
            ip_address=ip_address, 
            user_agent=self.user_agent,
            detalhes={'original_id': self.pk, 'motivo': 'Revogação pelo titular'}
        )

    @classmethod
    def verificar_consentimento_ativo(cls, usuario, tipo):
        """Verifica se o usuário tem um consentimento ativo (aceito) para o tipo."""
        ultimo = cls.objects.filter(usuario=usuario, tipo=tipo).order_by('-data_consentimento').first()
        return ultimo is not None and ultimo.status == 'aceito'

    @classmethod
    def obter_ultimo_consentimento(cls, usuario, tipo):
        """Retorna o último consentimento do usuário para um tipo específico."""
        return cls.objects.filter(usuario=usuario, tipo=tipo).order_by('-data_consentimento').first()