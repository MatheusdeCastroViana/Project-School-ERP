from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import mark_safe
from django.utils.timezone import localtime
from .models import Usuario, LogAuditoria
from .models_2fa import Configuracao2FA
from .models_recuperacao import TokenRecuperacaoSenha


class ERPModelAdmin(admin.ModelAdmin):
    class Media:
        css = {
            'all': ('admin/css/base_custom.css',)
        }


@admin.register(Usuario)
class UsuarioAdmin(ERPModelAdmin, UserAdmin):
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


@admin.register(Configuracao2FA)
class Configuracao2FAAdmin(ERPModelAdmin):
    list_display = ('usuario', 'ativado', 'criado_em', 'ultimo_uso')
    list_filter = ('ativado',)
    search_fields = ('usuario__email',)
    readonly_fields = ('chave_secreta', 'criado_em')


@admin.register(TokenRecuperacaoSenha)
class TokenRecuperacaoSenhaAdmin(ERPModelAdmin):
    list_display = ('usuario', 'criado_em', 'expira_em', 'utilizado', 'ip_solicitacao')
    list_filter = ('utilizado', 'criado_em')
    search_fields = ('usuario__email', 'token')
    readonly_fields = ('token', 'criado_em')
    
    fieldsets = (
        ('Informações do Token', {
            'fields': ('usuario', 'token', 'criado_em', 'expira_em')
        }),
        ('Status', {
            'fields': ('utilizado', 'utilizado_em')
        }),
        ('Auditoria', {
            'fields': ('ip_solicitacao', 'user_agent')
        }),
    )


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(ERPModelAdmin):
   
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

    def has_view_permission(self, request, obj=None):
        return request.user.is_authenticated