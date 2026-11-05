import json
import hashlib

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.timezone import now
from django.views.decorators.http import require_POST

from .audit import (
    registrar_consentimento,
    registrar_exportacao_dados,
    registrar_solicitacao_exclusao,
    registrar_evento_lgpd,
    _gravar_no_banco,
)
from .models import ConsentimentoLGPD, VersaoTextoConsentimento, SolicitacaoExclusao
from funcionarios.mascaras import mascarar_cpf, mascarar_telefone
from config.criptografia import indice_cego
from funcionarios.models import JornadaTrabalho, somente_digitos

from .models_2fa import Configuracao2FA
from .models_recuperacao import TokenRecuperacaoSenha

# Lista de dados que ficam retidos por obrigação legal/contratual (não são anonimizados).
# Todos os demais dados pessoais do titular são anonimizados/apagados na exclusão.
CAMPOS_PROTEGIDOS = [
    {
        'dado': 'Logs de auditoria (LogAuditoria)',
        'motivo': 'Imutáveis por obrigação de segurança e rastreabilidade (LGPD art. 16).',
    },
    {
        'dado': 'Consentimentos LGPD (ConsentimentoLGPD)',
        'motivo': 'Prova de consentimento do titular (LGPD art. 8º, §2º).',
    },
    {
        'dado': 'Solicitação de exclusão (SolicitacaoExclusao)',
        'motivo': 'Prova do atendimento ao direito do titular (LGPD art. 18).',
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
    Permite ao titular solicitar a exclusão de seus dados pessoais (LGPD - RF 4.10).
    Apenas cria uma SolicitacaoExclusao com status PENDENTE.
    Nenhum dado é excluído aqui; a Gestão decide no admin.
    """
    if request.method == 'POST':
        # Impede segunda solicitação enquanto houver uma pendente
        ja_pendente = SolicitacaoExclusao.objects.filter(
            usuario=request.user, status='PENDENTE'
        ).exists()
        if ja_pendente:
            messages.warning(
                request,
                'Você já tem uma solicitação de exclusão pendente de análise.',
            )
            return redirect('usuarios:solicitar_exclusao')

        solicitacao = SolicitacaoExclusao.objects.create(
            usuario=request.user,
            status='PENDENTE',
        )
        registrar_solicitacao_exclusao(
            usuario=request.user,
            campos_removidos=[],
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        messages.success(
            request,
            'Solicitação de exclusão registrada com sucesso.',
        )
        return redirect('usuarios:solicitar_exclusao')

    context = {'campos_protegidos': CAMPOS_PROTEGIDOS}
    return render(request, 'usuarios/solicitar_exclusao.html', context)


def executar_exclusao(solicitacao):
    """
    Anonimiza os dados do titular e executa a exclusão aprovada.

    Dentro de transaction.atomic(): se qualquer passo falhar, nada é gravado.
    Recusa a execução se o status não for APROVADA ou se já foi executada.
    """
    # Recusa se não estiver aprovada ou já executada
    if solicitacao.status != 'APROVADA':
        raise ValueError(
            f'Solicitação {solicitacao.pk} não está aprovada (status: {solicitacao.status}).'
        )
    if solicitacao.executado_em is not None:
        raise ValueError(
            f'Solicitação {solicitacao.pk} já foi executada em {solicitacao.executado_em}.'
        )

    usuario = solicitacao.usuario
    funcionario = getattr(usuario, 'funcionario', None)

    with transaction.atomic():
        # --- Anonimiza dados do Funcionario ---
        if funcionario:
            # Nome -> valor não identificável
            funcionario.nome = f'Titular anonimizado #{funcionario.pk}'
            # CPF -> valor não identificável (será cifrado pelo CampoCifrado)
            funcionario.cpf = f'anonimizado-{funcionario.pk}'
            # cpf_indice é unique: usar índice cego de valor não identificável e único por id
            funcionario.cpf_indice = indice_cego(
                somente_digitos(f'anonimizado-{funcionario.pk}')
            )
            # Telefone -> vazio
            funcionario.telefone = ''
            # Funcionario fica inativo (linha mantida por FKs PROTECT)
            funcionario.ativo = False
            funcionario.save()

            # Jornadas -> apagar
            funcionario.jornadas.all().delete()

        # --- Anonimiza dados do Usuario ---
        usuario_email_anonimo = f'anonimizado-{usuario.pk}@invalido.local'
        usuario.email = usuario_email_anonimo
        usuario.set_unusable_password()
        usuario.is_active = False
        usuario.save(update_fields=['email', 'password', 'is_active'])

        # --- Invalida chave TOTP (apaga) ---
        try:
            config_2fa = usuario.config_2fa
            Configuracao2FA.objects.filter(pk=config_2fa.pk).update(
                chave_secreta='', ativado=False
            )
        except Configuracao2FA.DoesNotExist:
            pass

        # --- Apaga tokens de recuperação de senha (têm IP/user-agent) ---
        TokenRecuperacaoSenha.objects.filter(usuario=usuario).delete()

        # --- Marca a solicitação como executada ---
        solicitacao.executado_em = now()
        solicitacao.save(update_fields=['executado_em'])

        # --- Registra no LogAuditoria (apenas id, sem dados pessoais) ---
        _gravar_no_banco(
            usuario=None,
            tipo_evento='exclusao_dados',
            sucesso=True,
            mensagem=(
                f'Exclusão de dados executada | Usuário ID: {usuario.pk} | '
                f'Solicitação ID: {solicitacao.pk}'
            ),
            ip_address=None,
            detalhes={'usuario_id': usuario.pk, 'solicitacao_id': solicitacao.pk},
        )


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

        ConsentimentoLGPD.objects.create(
            usuario=request.user, tipo=tipo, versao=versao, texto_hash=texto_hash,
            status='aceito' if aceitou else 'recusado', ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            url_origem=request.META.get('HTTP_REFERER', '')[:200], detalhes={'origem': 'popup_pos_login'}
        )
        registrar_consentimento(usuario=request.user, tipo=tipo, versao=versao, aceitou=aceitou, ip_address=request.META.get('REMOTE_ADDR'))
        return JsonResponse({'success': True, 'tipo': tipo, 'versao': versao, 'aceitou': aceitou})
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception:
        return JsonResponse({'error': 'Erro interno ao processar consentimento'}, status=500)


@login_required
def gerenciar_consentimentos(request):
    consentimentos = ConsentimentoLGPD.objects.filter(usuario=request.user).order_by('-data_consentimento')
    return render(request, 'usuarios/gerenciar_consentimentos.html', {'consentimentos': consentimentos})


@require_POST
@login_required
def revogar_consentimento(request, consentimento_id):
    try:
        consentimento = ConsentimentoLGPD.objects.get(id=consentimento_id, usuario=request.user)
        vigente = ConsentimentoLGPD.obter_ultimo_consentimento(request.user, consentimento.tipo)
        if consentimento.status == 'revogado':
            messages.info(request, 'Este consentimento já foi revogado anteriormente.')
        elif consentimento.status != 'aceito':
            # Só um consentimento aceito pode ser revogado (recusa não é revogável).
            messages.info(request, 'Apenas consentimentos aceitos podem ser revogados.')
        elif vigente is None or vigente.pk != consentimento.pk:
            # Impede revogar registros antigos já substituídos (evita revogações duplicadas na trilha).
            messages.info(request, 'Este registro não é o consentimento vigente para esta finalidade.')
        else:
            consentimento.revogar(ip_address=request.META.get('REMOTE_ADDR'))
            registrar_evento_lgpd(usuario=request.user, evento='revogacao_consentimento', sucesso=True, ip_address=request.META.get('REMOTE_ADDR'), detalhes={'tipo': consentimento.tipo})
            messages.success(request, f'Consentimento de "{consentimento.get_tipo_display()}" revogado com sucesso.')
            if consentimento.tipo == 'tratamento_dados':
                # O ConsentimentoMiddleware passa a bloquear todas as telas do sistema para este
                # usuário até que um novo consentimento seja dado: o tratamento é interrompido.
                messages.warning(request, 'O tratamento dos seus dados foi interrompido: seu acesso ao sistema permanece suspenso até que você dê um novo consentimento.')
    except ConsentimentoLGPD.DoesNotExist:
        messages.error(request, 'Consentimento não encontrado.')
    return redirect('usuarios:gerenciar_consentimentos')


@login_required
def consentir_obrigatorio(request):
    if ConsentimentoLGPD.verificar_consentimento_ativo(request.user, 'tratamento_dados'):
        return redirect('dashboard:home')
    versao_ativa = VersaoTextoConsentimento.objects.filter(tipo='tratamento_dados', ativa=True).first()
    return render(request, 'usuarios/consentir_obrigatorio.html', {'versao_ativa': versao_ativa})


def politica_privacidade(request):
    return render(request, 'usuarios/politica_privacidade.html')

def termos_uso(request):
    return render(request, 'usuarios/termos_uso.html')

        