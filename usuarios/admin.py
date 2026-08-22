from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

'''
    Se fosse registrar o usuario da forma padrão igual funcionario, iria mostrar uma de texto normal
    com o hash puro, inclusive editável. Pra evitar isso usamos uma classe já pronta do Django (UserAdmin)
    que abre um form separado e usa o hash da forma correta. Mas como vamos llogar com email ao invés
    de username, foi preciso customizar.

'''
class UsuarioAdmin(UserAdmin):
    model = Usuario

    # Campos mostrados na tela de edição de um usuário existente
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Vínculo", {"fields": ("funcionario",)}),
        ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Controle de acesso", {"fields": ("tentativas_login_falhas", "bloqueado_ate")}),
    )

    # Campos mostrados na tela de CRIAR um usuário novo
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "funcionario", "password1", "password2"),
        }),
    )

    list_display = ("email", "funcionario", "is_staff", "is_active")
    search_fields = ("email",)
    ordering = ("email",)


admin.site.register(Usuario, UsuarioAdmin)