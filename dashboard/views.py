from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from usuarios.context_processors import _normalizar


@login_required(login_url='account_login')
def dashboard_view(request):
    funcionario = getattr(request.user, 'funcionario', None)
    cargo = funcionario.cargo if funcionario else None
    setor_ativo = _normalizar(cargo.setor.nome) if cargo and cargo.setor else None

    context = {
        'setor_ativo': setor_ativo,
        'data_atual': timezone.now(),
    }
    return render(request, 'base_dashboard.html', context)


@login_required
def dashboard_gestao_view(request):
    context = {'setor_ativo': 'gestao', 'titulo': 'Painel de Gestão'}
    return render(request, 'base_dashboard.html', context)


@login_required
def dashboard_pedagogico_view(request):
    context = {'setor_ativo': 'pedagogico', 'titulo': 'Painel Pedagógico'}
    return render(request, 'base_dashboard.html', context)


@login_required
def dashboard_financeiro_view(request):
    context = {'setor_ativo': 'financeiro', 'titulo': 'Painel Financeiro'}
    return render(request, 'base_dashboard.html', context)