from django.db import models
from django.contrib.auth.models import Permission

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
    cpf = models.CharField(max_length=14, unique=True)
    ativo = models.BooleanField(default=True)
    telefone = models.CharField(max_length=11, blank=True, default="")
    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT, null=True, blank=True)

    def __str__(self):
        return self.nome

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
