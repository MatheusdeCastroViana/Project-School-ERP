import hashlib
from django.utils import timezone

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
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='consentimentos_lgpd', verbose_name='Usuário'
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
            usuario=self.usuario, tipo=self.tipo, versao=self.versao,
            texto_hash=self.texto_hash, status='revogado',
            ip_address=ip_address, user_agent=self.user_agent,
            detalhes={'original_id': self.pk, 'motivo': 'Revogação pelo titular'}
        )

    @classmethod
    def verificar_consentimento_ativo(cls, usuario, tipo):
        ultimo = cls.objects.filter(usuario=usuario, tipo=tipo).order_by('-data_consentimento').first()
        return ultimo is not None and ultimo.status == 'aceito'