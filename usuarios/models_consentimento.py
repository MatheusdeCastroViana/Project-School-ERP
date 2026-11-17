from django.db import models
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.utils import timezone


class VersaoTextoConsentimento(models.Model):
    """
    Armazena as versões dos textos de consentimento apresentados aos usuários.
    Cada versão é imutável após criação.
    """
    TIPO_CONSENTIMENTO = [
        ('cookies_essenciais', 'Cookies Essenciais'),
        ('tratamento_dados', 'Tratamento de Dados Pessoais'),
        ('finalidades_administrativas', 'Finalidades Administrativas'),
        ('comunicacao_institucional', 'Comunicação Institucional'),
        ('politica_privacidade', 'Política de Privacidade'),
        ('termos_uso', 'Termos de Uso'),
    ]
    
    tipo = models.CharField(
        max_length=50, 
        choices=TIPO_CONSENTIMENTO,
        db_index=True
    )
    versao = models.CharField(max_length=20, help_text="Ex: 1.0, 1.1, 2.0")
    texto_apresentado = models.TextField(
        help_text="Texto completo apresentado ao usuário"
    )
    resumo = models.TextField(
        blank=True,
        help_text="Resumo das finalidades"
    )
    data_publicacao = models.DateTimeField(auto_now_add=True)
    ativa = models.BooleanField(
        default=True,
        help_text="Versão atualmente em vigor"
    )
    
    class Meta:
        verbose_name = 'Versão de Texto de Consentimento'
        verbose_name_plural = 'Versões de Texto de Consentimento'
        ordering = ['-data_publicacao']
        unique_together = ['tipo', 'versao']
        indexes = [
            models.Index(fields=['tipo', '-versao']),
            models.Index(fields=['tipo', 'ativa']),
        ]
    
    def __str__(self):
        return f"{self.get_tipo_display()} - v{self.versao}"
    
    def save(self, *args, **kwargs):
        # Se esta versão está sendo marcada como ativa, desativar as outras
        if self.ativa:
            VersaoTextoConsentimento.objects.filter(
                tipo=self.tipo, 
                ativa=True
            ).exclude(
                pk=self.pk
            ).update(ativa=False)
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        raise PermissionDenied('Versões de consentimento não podem ser excluídas.')


class ConsentimentoLGPDQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise PermissionDenied('Registros de consentimento são imutáveis.')
    
    def delete(self):
        raise PermissionDenied('Registros de consentimento são imutáveis.')


class ConsentimentoLGPD(models.Model):
    """
    Registro imutável de consentimentos LGPD.
    Cada consentimento é vinculado a um usuário ou a um identificador anônimo.
    """
    STATUS_CONSENTIMENTO = [
        ('aceito', 'Aceito'),
        ('recusado', 'Recusado'),
        ('revogado', 'Revogado'),
    ]
    
    TIPO_CONSENTIMENTO = [
        ('cookies_essenciais', 'Cookies Essenciais'),
        ('tratamento_dados', 'Tratamento de Dados Pessoais'),
        ('finalidades_administrativas', 'Finalidades Administrativas'),
        ('comunicacao_institucional', 'Comunicação Institucional'),
        ('politica_privacidade', 'Política de Privacidade'),
        ('termos_uso', 'Termos de Uso'),
    ]
    
    # Usuário (pode ser null para consentimentos anônimos pré-login)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consentimentos_lgpd',
        verbose_name='Usuário'
    )
    
    # Identificador para consentimentos anônimos (ex: hash de sessão)
    identificador_anonimo = models.CharField(
        max_length=100,
        blank=True,
        help_text="Identificador para consentimentos pré-login"
    )
    
    # Tipo e versão do consentimento
    tipo = models.CharField(
        max_length=50,
        choices=TIPO_CONSENTIMENTO,
        db_index=True
    )
    versao = models.CharField(max_length=20)
    
    # Texto apresentado (hash para auditoria)
    texto_hash = models.CharField(
        max_length=64,
        help_text="Hash SHA-256 do texto apresentado"
    )
    
    # Status do consentimento
    status = models.CharField(
        max_length=20,
        choices=STATUS_CONSENTIMENTO,
        db_index=True
    )
    
    # Dados de contexto
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    user_agent = models.TextField(blank=True)
    url_origem = models.URLField(
        blank=True,
        help_text="URL onde o consentimento foi dado"
    )
    
    # Timestamps
    data_consentimento = models.DateTimeField(auto_now_add=True, db_index=True)
    data_revogacao = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data da revogação (se aplicável)"
    )
    
    # Detalhes adicionais
    detalhes = models.JSONField(
        null=True,
        blank=True,
        help_text="Detalhes adicionais em formato JSON"
    )
    
    objects = ConsentimentoLGPDQuerySet.as_manager()
    
    class Meta:
        verbose_name = 'Consentimento LGPD'
        verbose_name_plural = 'Consentimentos LGPD'
        ordering = ['-data_consentimento']
        indexes = [
            models.Index(fields=['usuario', '-data_consentimento']),
            models.Index(fields=['tipo', '-data_consentimento']),
            models.Index(fields=['status', '-data_consentimento']),
            models.Index(fields=['identificador_anonimo', '-data_consentimento']),
        ]
        constraints = [
            # Garante que cada usuário tenha apenas um consentimento ativo por tipo
            models.UniqueConstraint(
                fields=['usuario', 'tipo', 'status'],
                name='unique_consentimento_por_tipo',
                condition=models.Q(status__in=['aceito', 'recusado'])
            ),
        ]
    
    def __str__(self):
        usuario_str = self.usuario.email if self.usuario else f"Anônimo ({self.identificador_anonimo})"
        return f"{usuario_str} - {self.get_tipo_display()} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise PermissionDenied('Registros de consentimento são imutáveis.')
        
        # Se estiver revogando, preencher data_revogacao
        if self.status == 'revogado' and not self.data_revogacao:
            self.data_revogacao = timezone.now()
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        raise PermissionDenied('Registros de consentimento são imutáveis.')
    
    def revogar(self, ip_address=None):
        """
        Revoga este consentimento.
        Cria um novo registro com status 'revogado'.
        """
        if self.status == 'revogado':
            raise ValueError('Este consentimento já está revogado.')
        
        # Cria novo registro de revogação
        ConsentimentoLGPD.objects.create(
            usuario=self.usuario,
            identificador_anonimo=self.identificador_anonimo,
            tipo=self.tipo,
            versao=self.versao,
            texto_hash=self.texto_hash,
            status='revogado',
            ip_address=ip_address,
            user_agent=self.user_agent,
            url_origem=self.url_origem,
            detalhes={
                'consentimento_original_id': self.pk,
                'data_consentimento_original': self.data_consentimento.isoformat(),
                'motivo': 'Revogação pelo titular'
            }
        )
    
    @classmethod
    def verificar_consentimento_ativo(cls, usuario, tipo):
        """
        Verifica se o usuário tem um consentimento ativo (aceito) para o tipo.
        Retorna True se houver consentimento aceito e não revogado.
        """
        ultimo_consentimento = cls.objects.filter(
            usuario=usuario,
            tipo=tipo
        ).order_by('-data_consentimento').first()
        
        if not ultimo_consentimento:
            return False
        
        return ultimo_consentimento.status == 'aceito'
    
    @classmethod
    def obter_ultimo_consentimento(cls, usuario, tipo):
        """
        Retorna o último consentimento do usuário para um tipo específico.
        """
        return cls.objects.filter(
            usuario=usuario,
            tipo=tipo
        ).order_by('-data_consentimento').first()