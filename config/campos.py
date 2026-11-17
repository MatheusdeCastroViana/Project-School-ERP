from django import forms
from django.core import checks
from django.db import models

from config.criptografia import cifrar, decifrar


class CampoCifrado(models.TextField):
    def get_internal_type(self):
        return "TextField"

    def check(self, **kwargs):
        erros = super().check(**kwargs)
        if self.unique:
            erros.append(
                checks.Error(
                    "CampoCifrado não pode ser unique.",
                    hint="Tokens cifrados nunca se repetem; use um blind index para unicidade.",
                    obj=self,
                    id="campo_cifrado.E001",
                )
            )
        if self.db_index:
            erros.append(
                checks.Error(
                    "CampoCifrado não pode ter db_index.",
                    hint="Índice sobre texto cifrado não acelera nenhuma busca.",
                    obj=self,
                    id="campo_cifrado.E002",
                )
            )
        return erros

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None or value == "":
            return value
        return cifrar(value)

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value
        return decifrar(value)

    def to_python(self, value):
        if value is None:
            return value
        return str(value)

    def get_lookup(self, lookup_name):
        if lookup_name != "isnull":
            return None
        return super().get_lookup(lookup_name)

    def formfield(self, **kwargs):
        defaults = {"widget": forms.TextInput}
        defaults.update(kwargs)
        return super().formfield(**defaults)