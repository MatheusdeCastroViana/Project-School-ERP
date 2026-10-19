import json
import hashlib

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .audit import (
    registrar_consentimento,
    registrar_exportacao_dados,
    registrar_solicitacao_exclusao,
    registrar_evento_lgpd,  # Nova função para eventos genéricos de LGPD (revogação)
)
from funcionarios.mascaras import mascarar_cpf, mascarar_telefone

from .models_2fa import Configuracao2FA
# Importando os novos modelos de consentimento
from .models import ConsentimentoLGPD, VersaoTextoConsentimento

# Lista de campos que não podem ser excluídos automaticamente por obrigação legal/contratual
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
    """
    Compila todos os dados pessoais do usuário (conta e funcionário) 
    para consulta ou exportação.
    """
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
    """View para exibir os dados pessoais do usuário na interface."""
    dados = obter_dados_pessoais(request.user)
    
    # Aplica máscaras para exibição segura na tela
    if dados['funcionario']:
        dados['funcionario']['cpf_mascarado'] = mascarar_cpf(dados['funcionario']['cpf'])
        dados['funcionario']['telefone_mascarado'] = mascarar_telefone(dados['funcionario']['telefone'])
        
    return render(request, 'usuarios/consultar_dados.html', {'dados': dados})


@login_required
def exportar_dados(request):
    """
    Exporta os dados pessoais do usuário em formato JSON (Portabilidade LGPD - Art. 18).
    Registra a ação nos logs de auditoria.
    """
    dados = obter_dados_pessoais(request.user)
    conteudo = json.dumps(dados, default=str, ensure_ascii=False, indent=2)

    grupos_exportados = ['conta']
    if dados['funcionario']:
        grupos_exportados.append('funcionario')
    if dados['jornadas']:
        grupos_exportados.append('jornadas')

    registrar_exportacao_dados(
        usuario=request.user,
        grupos_exportados=grupos_exportados,
        formato='json',
        ip_address=request.META.get('REMOTE_ADDR'),
    )

    resposta = HttpResponse(conteudo, content_type='application/json')
    resposta['Content-Disposition'] = 'attachment; filename="meus_dados.json"'
    return resposta


@login_required
def solicitar_exclusao(request):
    """
    Permite a exclusão de dados não essenciais (ex: telefone).
    Dados protegidos por obrigação legal são mantidos e justificados na interface.
    """
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

# CORREÇÕES E NOVAS VIEWS DE CONSENTIMENTO LGPD (Pós-Login)

@require_POST
@login_required
def registrar_consentimento_view(request):
    try:
        data = json.loads(request.body)
        tipo = data.get('tipo')
        versao = data.get('versao')
        
        aceitou_raw = data.get('aceitou')
        aceitou = str(aceitou_raw).lower() in ['true', '1', 'yes'] or aceitou_raw is True
        
        tipos_validos = [choice[0] for choice in ConsentimentoLGPD.TIPO_CONSENTIMENTO]
        if tipo not in tipos_validos:
            return JsonResponse({'error': 'Tipo de consentimento inválido'}, status=400)

        try:
            versao_obj = VersaoTextoConsentimento.objects.get(tipo=tipo, versao=versao, ativa=True)
        except VersaoTextoConsentimento.DoesNotExist:
            return JsonResponse({'error': 'Versão de consentimento inválida ou inativa'}, status=400)
        
        # Gera o hash SHA-256 do texto apresentado para garantir integridade na auditoria
        texto_hash = hashlib.sha256(versao_obj.texto_apresentado.encode('utf-8')).hexdigest()

        # Evita registros duplicados se o usuário clicar várias vezes no mesmo consentimento
        ultimo = ConsentimentoLGPD.obter_ultimo_consentimento(request.user, tipo)
        if ultimo and ultimo.status == 'aceito' and ultimo.versao == versao:
            return JsonResponse({'success': True, 'message': 'Consentimento já registrado'})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)