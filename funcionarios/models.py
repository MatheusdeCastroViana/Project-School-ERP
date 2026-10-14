from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models

from config.campos import CampoCifrado
from config.criptografia import indice_cego


def somente_digitos(texto):
    return "".join(caractere for caractere in texto if caractere.isdigit())


class FuncionarioQuerySet(models.QuerySet):
    def por_cpf(self, cpf):
        return self.filter(cpf_indice=indice_cego(somente_digitos(cpf)))

class Setor(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.CharField(max_length=150, blank=True) # Blank permite criar setor sem descrição

    # Trocar o nome do plural de Setor pra Setores no admin (ficava escrito Setors)
    class Meta:
        verbose_name = "Setor"
        verbose_name_plural = "Setores"

    # Função pra mostrar o nome no admin ao invés de <Setor: Setor object (1)>
    def __str__(self):
        return self.nome
    
# Relacionamento 1:n = ForeignKey
# Relacionamento n:n = ManyToManyField
class Cargo(models.Model):
    nome = models.CharField(max_length=200, unique=True)
    setor = models.ForeignKey(Setor, on_delete=models.PROTECT) # Não deixa apagar um setor que tem cargos vinculados
    permissoes = models.ManyToManyField(Permission, blank=True) # Blank permite criar um cargo sem permissões

    def __str__(self):
            return self.nome

# Talvez adicionar data de admissão mais pra frente
class Funcionario(models.Model):
    nome = models.CharField(max_length=150)
    cpf = CampoCifrado(validators=[MaxLengthValidator(14)])
    cpf_indice = models.CharField(max_length=64, unique=True, editable=False) #hmac pra garantir que o cpf seja único
    ativo = models.BooleanField(default=True)
    telefone = CampoCifrado(blank=True, default="", validators=[MaxLengthValidator(11)])
    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT, null=True, blank=True)

    objects = FuncionarioQuerySet.as_manager()

    def __str__(self):
        return self.nome

    def clean(self):
        super().clean()
        if not self.cpf:
            return
        duplicados = Funcionario.objects.por_cpf(self.cpf).exclude(pk=self.pk)
        if duplicados.exists():
            raise ValidationError({"cpf": "Já existe um funcionário com este CPF."})

    def save(self, *args, **kwargs):
        self.cpf_indice = indice_cego(somente_digitos(self.cpf))
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "cpf" in update_fields:
            kwargs["update_fields"] = [*update_fields, "cpf_indice"]
        super().save(*args, **kwargs)

class JornadaTrabalho(models.Model):
    class DiaSemana(models.IntegerChoices):
        SEGUNDA = 0, "Segunda-feira"
        TERCA = 1, "Terça-feira"
        QUARTA = 2, "Quarta-feira"
        QUINTA = 3, "Quinta-feira"
        SEXTA = 4, "Sexta-feira"
        SABADO = 5, "Sábado"
        DOMINGO = 6, "Domingo"

    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name="jornadas")
    dia_semana = models.IntegerField(choices=DiaSemana.choices)
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()

    class Meta:
        unique_together = ("funcionario", "dia_semana")
        verbose_name = "Jornada de Trabalho"
        verbose_name_plural = "Jornadas de Trabalho"

    def __str__(self):
        return f"{self.funcionario.nome} - {self.get_dia_semana_display()}"
