from django.contrib import admin
from .mascaras import mascarar_cpf, mascarar_telefone
from .models import Funcionario, Setor, Cargo, JornadaTrabalho


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
        return mascarar_telefone(obj.telefone)


admin.site.register(Setor)
admin.site.register(Cargo)
admin.site.register(JornadaTrabalho)