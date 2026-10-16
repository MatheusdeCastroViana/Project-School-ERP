from django.contrib import admin
from .models import Funcionario, Setor, Cargo, JornadaTrabalho


def mascarar_cpf(cpf):
    digitos = "".join(c for c in cpf if c.isdigit())
    if len(digitos) != 11:
        return "***"
    return f"***.{digitos[3:6]}.{digitos[6:9]}-**"


@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cargo', 'ativo', 'cpf_mascarado')

    def get_exclude(self, request, obj=None):
        if obj is None:
            return ()
        return ('cpf', 'telefone')

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ()
        return ('cpf_mascarado', 'telefone_mascarado')

    @admin.display(description='CPF')
    def cpf_mascarado(self, obj):
        return mascarar_cpf(obj.cpf) if obj.cpf else '—'

    @admin.display(description='Telefone')
    def telefone_mascarado(self, obj):
        if not obj.telefone:
            return '—'
        return '*' * max(len(obj.telefone) - 4, 0) + obj.telefone[-4:]


admin.site.register(Setor)
admin.site.register(Cargo)
admin.site.register(JornadaTrabalho)