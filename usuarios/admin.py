from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db import transaction
from django.utils.html import mark_safe
from django.utils.timezone import localtime, now
from django.contrib import messages
from .models import Usuario, LogAuditoria, SolicitacaoExclusao
from .models_2fa import Configuracao2FA
from .models_recuperacao import TokenRecuperacaoSenha
from .views_lgpd import executar_exclusao


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('email', 'is_staff', 'is_active', 'tentativas_login_falhas', 'bloqueado_ate')
    list_filter = ('is_staff', 'is_active')
    search_fields = ('email',)
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Vínculo', {'fields': ('funcionario',)}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Segurança', {'fields': ('tentativas_login_falhas', 'bloqueado_ate')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'funcionario', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        campos = super().get_readonly_fields(request, obj)
        if not request.user.is_superuser:
            campos = (*campos, 'is_superuser', 'is_staff', 'groups', 'user_permissions')
        return campos

@admin.register(Configuracao2FA)
class Configuracao2FAAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'ativado', 'criado_em', 'ultimo_uso')
    list_filter = ('ativado',)
    search_fields = ('usuario__email',)
    exclude = ('chave_secreta',)
    readonly_fields = ('usuario', 'criado_em', 'ultimo_uso')

    def has_add_permission(self, request):
        return False


@admin.register(TokenRecuperacaoSenha)
class TokenRecuperacaoSenhaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'criado_em', 'expira_em', 'utilizado', 'ip_solicitacao')
    list_filter = ('utilizado', 'criado_em')
    search_fields = ('usuario__email',)
    readonly_fields = (
        'usuario', 'criado_em', 'expira_em', 'utilizado',
        'utilizado_em', 'ip_solicitacao', 'user_agent',
    )
    
    fieldsets = (
        ('Informações do Token', {
            'fields': ('usuario', 'criado_em', 'expira_em')
        }),
        ('Status', {
            'fields': ('utilizado', 'utilizado_em')
        }),
        ('Auditoria', {
            'fields': ('ip_solicitacao', 'user_agent')
        }),
    )

    def has_add_permission(self, request):
        return False

@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
   
    list_display = ('data_hora_formatada', 'usuario', 'tipo_evento', 'sucesso_formatado', 'ip_address')
    list_display_links = ('data_hora_formatada',)
    list_filter = ('usuario', 'tipo_evento', 'sucesso', 'data_hora')
    search_fields = ('usuario__email', 'mensagem', 'ip_address')
    ordering = ('-data_hora',)
    date_hierarchy = 'data_hora'
    
    readonly_fields = (
        'usuario', 'tipo_evento', 'data_hora', 'ip_address', 
        'user_agent', 'sucesso', 'detalhes', 'mensagem'
    )
    
    fieldsets = (
        ('Informações do Evento', {
            'fields': ('data_hora', 'usuario', 'tipo_evento', 'sucesso'),
            'description': 'Registro imutável de auditoria - RA-5.3'
        }),
        ('Detalhes Técnicos', {
            'fields': ('ip_address', 'user_agent', 'mensagem', 'detalhes'),
            'classes': ('collapse',),
            'description': 'Informações técnicas do evento'
        }),
    )

    @admin.display(description='Data/Hora', ordering='data_hora')
    def data_hora_formatada(self, obj):
        return localtime(obj.data_hora).strftime('%d/%m/%Y %H:%M:%S')

    @admin.display(description='Status')
    def sucesso_formatado(self, obj):
        if obj.sucesso:
            return mark_safe('<span style="color: #15803D; font-weight: bold;">✓ Sucesso</span>')
        return mark_safe('<span style="color: #DC2626; font-weight: bold;">✗ Falha</span>')

    
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SolicitacaoExclusao)
class SolicitacaoExclusaoAdmin(admin.ModelAdmin):
    """Gestão de solicitações de exclusão (LGPD - RF 4.10)."""

    list_display = ('usuario', 'status', 'criado_em', 'decidido_em', 'decidido_por', 'executado_em')
    list_filter = ('status', 'criado_em', 'decidido_em')
    search_fields = ('usuario__email', 'justificativa')
    ordering = ('-criado_em',)
    readonly_fields = ('criado_em', 'usuario')

    def get_readonly_fields(self, request, obj=None):
        """
        Após a solicitação ser decidida (APROVADA/RECUSADA), campos de decisão
        e execução ficam somente leitura para impedir alteração manual.
        """
        campos = list(super().get_readonly_fields(request, obj))
        if obj and obj.status != 'PENDENTE':
            for campo in (
                'status', 'justificativa', 'decidido_em', 'decidido_por',
                'executado_em',
            ):
                if campo not in campos:
                    campos.append(campo)
        return campos

    def save_model(self, request, obj, form, change):
        """
        Se o status for alterado para APROVADA (pela action ou por edição
        manual), executa a exclusão dentro do mesmo transaction.atomic().
        Se falhar, o status volta para PENDENTE.
        """
        if change and 'status' in form.changed_data:
            if obj.status == 'APROVADA' and obj.executado_em is None:
                try:
                    with transaction.atomic():
                        obj.decidido_em = now()
                        obj.decidido_por = request.user
                        super().save_model(request, obj, form, change)
                        executar_exclusao(obj)
                except Exception as exc:
                    obj.status = 'PENDENTE'
                    obj.save()
                    raise
            elif obj.status == 'RECUSADA' and not obj.justificativa:
                from django.core.exceptions import ValidationError
                raise ValidationError(
                    'Justificativa é obrigatória para recusar.'
                )
        super().save_model(request, obj, form, change)

    actions = ['aprovar_solicitacoes', 'recusar_solicitacoes']

    @admin.action(description='Aprovar solicitações selecionadas')
    def aprovar_solicitacoes(self, request, queryset):
        pendentes = queryset.filter(status='PENDENTE')
        aprovadas = 0
        erros = 0
        for solicitacao in pendentes:
            try:
                with transaction.atomic():
                    solicitacao.status = 'APROVADA'
                    solicitacao.decidido_em = now()
                    solicitacao.decidido_por = request.user
                    solicitacao.save()
                    executar_exclusao(solicitacao)
                aprovadas += 1
            except Exception as exc:
                erros += 1
                self.message_user(
                    request,
                    f'Erro ao aprovar {solicitacao.usuario.email}: {exc}',
                    level=messages.ERROR,
                )
        if aprovadas:
            self.message_user(
                request,
                f'{aprovadas} solicitação(ões) aprovada(s) e executada(s).',
                level=messages.SUCCESS,
            )
        if erros:
            self.message_user(
                request,
                f'{erros} solicitação(ões) com erro na aprovação.',
                level=messages.ERROR,
            )

    @admin.action(description='Recusar solicitações selecionadas')
    def recusar_solicitacoes(self, request, queryset):
        pendentes = queryset.filter(status='PENDENTE')
        recusadas = 0
        puladas = 0
        for solicitacao in pendentes:
            if not solicitacao.justificativa:
                puladas += 1
                continue
            solicitacao.status = 'RECUSADA'
            solicitacao.decidido_em = now()
            solicitacao.decidido_por = request.user
            solicitacao.save()
            recusadas += 1
        if recusadas:
            self.message_user(
                request,
                f'{recusadas} solicitação(ões) recusada(s).',
                level=messages.SUCCESS,
            )
        if puladas:
            self.message_user(
                request,
                f'{puladas} solicitação(ões) puladas por falta de justificativa.',
                level=messages.WARNING,
            )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False