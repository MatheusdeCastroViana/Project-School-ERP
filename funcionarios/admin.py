from django.contrib import admin
from .models import Funcionario, Setor, Cargo

admin.site.register(Funcionario)
admin.site.register(Setor)
admin.site.register(Cargo)