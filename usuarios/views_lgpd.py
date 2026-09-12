from django.contrib.auth.decorators import login_required
from django.http import HttpResponse


@login_required
def consultar_dados(request):
    return HttpResponse("Consulta de dados pessoais.")


@login_required
def exportar_dados(request):
    return HttpResponse("Exportação de dados pessoais.")


@login_required
# Provavelmente anonimização da maioria dos dados
def solicitar_exclusao(request):
    return HttpResponse("Solicitação de exclusão de dados.")