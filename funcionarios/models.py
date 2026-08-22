from django.db import models

# Classse mínima. Essa classe ainda terá vários outros atributos com referências à outras tabelas.
class Funcionario(models.Model):
    nome = models.CharField(max_length=150)
    cpf = models.CharField(max_length=14, unique=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome
