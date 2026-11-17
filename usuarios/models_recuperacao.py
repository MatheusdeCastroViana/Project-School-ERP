from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import secrets
import hashlib

def hash_token(token_cru):
    return hashlib.sha256(token_cru.encode()).hexdigest()

class TokenRecuperacaoSenha(models.Model):    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tokens_recuperacao'
    )
    
    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True
    )
    
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Criado em'
    )
    expira_em = models.DateTimeField(
        verbose_name='Expira em'
    )
    
    utilizado = models.BooleanField(
        default=False,
        verbose_name='Token utilizado'
    )
    utilizado_em = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Utilizado em'
    )
    
    # Dados de auditoria (Marcos integrar com logs)
    ip_solicitacao = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP de solicitação'
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name='User-Agent'
    )
    
    class Meta:
        verbose_name = 'Token de Recuperação de Senha'
        verbose_name_plural = 'Tokens de Recuperação de Senha'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['token', 'utilizado']),
            models.Index(fields=['usuario', 'expira_em']),
        ]

    @classmethod
    def gerar(cls, usuario, ip_solicitacao=None, user_agent=''):
        token_cru = secrets.token_urlsafe(48)
        objeto = cls.objects.create(
            usuario=usuario,
            token=hash_token(token_cru),
            ip_solicitacao=ip_solicitacao,
            user_agent=user_agent,
        )
        return objeto, token_cru

    def save(self, *args, **kwargs):
        if not self.expira_em:
            horas = getattr(settings, 'TOKEN_RECUPERACAO_EXPIRACAO_HORAS', 24)
            self.expira_em = timezone.now() + timedelta(hours=horas)

        super().save(*args, **kwargs)

    def is_valido(self):
        if self.utilizado:
            return False
        
        if self.expira_em < timezone.now():
            return False
        
        return True

    def marcar_como_utilizado(self):
        self.utilizado = True
        self.utilizado_em = timezone.now()
        self.save(update_fields=['utilizado', 'utilizado_em'])

    def __str__(self):
        status = 'Utilizado' if self.utilizado else 'Válido'
        return f"Token de {self.usuario.email} ({status})"