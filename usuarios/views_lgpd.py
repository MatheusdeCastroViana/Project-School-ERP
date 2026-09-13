import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .audit import (
    registrar_consentimento,
    registrar_solicitacao_exclusao,
)
from .models_2fa import Configuracao2FA

CAMPOS_PROTEGIDOS = [
    {
        'dado': 'Nome e CPF',
        'motivo': 'Necessários para identificação funcional e obrigações trabalhistas enquanto o vínculo estiver ativo.',
    },
    {
        'dado': 'E-mail e senha da conta',
        'motivo': 'Necessários para o funcionamento do login; excluir inviabilizaria o acesso ao sistema.',
    },
    {
        'dado': 'Cargo',
        'motivo': 'Controla as permissões de acesso ao sistema.',
    },
    {
        'dado': 'Jornada de trabalho',
        'motivo': 'Dado administrativo vinculado ao funcionário enquanto estiver ativo.',
    },
]


def obter_dados_pessoais(usuario):
    dados = {
        'conta': {
            'email': usuario.email,
            'data_criacao': usuario.date_joined,
            'dois_fatores_ativo': False,
        },
        'funcionario': None,
        'jornadas': [],
    }

    try:
        dados['conta']['dois_fatores_ativo'] = usuario.config_2fa.ativado
    except Configuracao2FA.DoesNotExist:
        pass

    funcionario = usuario.funcionario

    if funcionario:
        dados['funcionario'] = {
            'nome': funcionario.nome,
            'cpf': funcionario.cpf,
            'telefone': funcionario.telefone,
            'cargo': funcionario.cargo.nome if funcionario.cargo else None,
            'setor': funcionario.cargo.setor.nome if funcionario.cargo else None,
        }

        dados['jornadas'] = [
            {
                'dia_semana': jornada.get_dia_semana_display(),
                'hora_inicio': jornada.hora_inicio,
                'hora_fim': jornada.hora_fim,
            }
            for jornada in funcionario.jornadas.all().order_by('dia_semana')
        ]
    return dados

@login_required
def consultar_dados(request):
    dados = obter_dados_pessoais(request.user)
    return render(request, 'usuarios/consultar_dados.html', {'dados': dados})


@login_required
def exportar_dados(request):
    dados = obter_dados_pessoais(request.user)
    conteudo = json.dumps(dados, default=str, ensure_ascii=False, indent=2)

    resposta = HttpResponse(conteudo, content_type='application/json')
    resposta['Content-Disposition'] = 'attachment; filename="meus_dados.json"'
    return resposta


@login_required
def solicitar_exclusao(request):
    if request.method == 'POST':
        campos_removidos = []
        funcionario = request.user.funcionario

        if funcionario and funcionario.telefone:
            funcionario.telefone = ''
            funcionario.save(update_fields=['telefone'])
            campos_removidos.append('telefone')

        registrar_solicitacao_exclusao(
            usuario=request.user,
            campos_removidos=campos_removidos,
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        if campos_removidos:
            messages.success(
                request,
                'Seu telefone foi removido. Os demais dados são protegidos e não podem ser excluídos automaticamente.'
            )
        else:
            messages.info(
                request,
                'Não havia telefone cadastrado para remover. Os demais dados são protegidos e não podem ser excluídos automaticamente.'
            )

        return redirect('usuarios:solicitar_exclusao')

    context = {'campos_protegidos': CAMPOS_PROTEGIDOS}
    return render(request, 'usuarios/solicitar_exclusao.html', context)


@require_POST
@login_required
def registrar_consentimento_view(request):
    try:
        data = json.loads(request.body)
        tipo = data.get('tipo')
        versao = data.get('versao')
        aceitou = data.get('aceitou', False)
        
        if not tipo or not versao:
            return JsonResponse({'error': 'Dados inválidos'}, status=400)
        
        # Registra no log de auditoria
        registrar_consentimento(
            usuario=request.user,
            tipo=tipo,
            versao=versao,
            aceitou=aceitou,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': True,
            'tipo': tipo,
            'versao': versao,
            'aceitou': aceitou
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def politica_privacidade(request):
    return render(request, 'usuarios/politica_privacidade.html')


def termos_uso(request):
    return render(request, 'usuarios/termos_uso.html')