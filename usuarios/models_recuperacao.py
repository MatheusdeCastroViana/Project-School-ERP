from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import secrets
import hashlib


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

    def save(self, *args, **kwargs):
        if not self.token:
            # Gera string aleatória de 64 caracteres e faz hash SHA256
            string_aleatoria = secrets.token_urlsafe(64)
            self.token = hashlib.sha256(string_aleatoria.encode()).hexdigest()
        
        if not self.expira_em:
            self.expira_em = timezone.now() + timedelta(hours=24)
        
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
        return f"Token {self.token[:8]}... - {self.usuario.email} ({status})"