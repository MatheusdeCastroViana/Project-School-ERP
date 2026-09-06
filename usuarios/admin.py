from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario
from .models_2fa import Configuracao2FA
from .models_recuperacao import TokenRecuperacaoSenha


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('email', 'is_staff', 'is_active', 'tentativas_login_falhas', 'bloqueado_ate')
    list_filter = ('is_staff', 'is_active')
    search_fields = ('email',)
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Segurança', {'fields': ('tentativas_login_falhas', 'bloqueado_ate')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )


@admin.register(Configuracao2FA)
class Configuracao2FAAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'ativado', 'criado_em', 'ultimo_uso')
    list_filter = ('ativado',)
    search_fields = ('usuario__email',)
    readonly_fields = ('chave_secreta', 'criado_em')


@admin.register(TokenRecuperacaoSenha)
class TokenRecuperacaoSenhaAdmin(admin.ModelAdmin):
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