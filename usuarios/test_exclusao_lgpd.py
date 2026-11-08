from unittest.mock import patch

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.db import connection
from django.urls import reverse
from django.utils.timezone import now

from config.test_criptografia import chaves, gerar_chave
from config.criptografia import cifrar, decifrar

from funcionarios.models import Funcionario, Setor, Cargo, JornadaTrabalho, somente_digitos
from usuarios.models import SolicitacaoExclusao, VersaoTextoConsentimento, ConsentimentoLGPD, LogAuditoria
from usuarios.models_2fa import Configuracao2FA
from usuarios.models_recuperacao import TokenRecuperacaoSenha
from usuarios.admin import SolicitacaoExclusaoAdmin


def ler_valor_cru(tabela, pk, coluna):
    """Lê um valor direto da tabela do banco (bypassa o CampoCifrado)."""
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {coluna} FROM {tabela} WHERE id = %s", [pk])
        row = cursor.fetchone()
        return row[0] if row else None


def _fazer_login_superusuario(client):
    Usuario = get_user_model()
    su = Usuario.objects.create_superuser(
        email='gestao@exemplo.com', password='senha123'
    )
    client.force_login(su)
    return su


class ExclusaoLgpdTests(TestCase):
    """Testes do Item 4.10 (exclusão de dados do titular, LGPD)."""

    def setUp(self):
        self.chave_antiga = gerar_chave()
        self.factory = RequestFactory()

        self.setor = Setor.objects.create(nome="Administrativo")
        self.cargo = Cargo.objects.create(nome="Estagiário", setor=self.setor)

        # Cria Funcionario com texto puro dentro de chaves (sem cifrar() manual)
        with chaves(self.chave_antiga):
            self.funcionario = Funcionario.objects.create(
                nome="Ana Silva",
                cpf="12345678900",
                telefone="11999998888",
                cargo=self.cargo,
                ativo=True,
            )
            JornadaTrabalho.objects.create(
                funcionario=self.funcionario,
                dia_semana=0,
                hora_inicio="08:00",
                hora_fim="17:00",
            )

        Usuario = get_user_model()
        self.usuario = Usuario.objects.create_user(
            email="ana@exemplo.com",
            password="senha123",
            funcionario=self.funcionario,
        )

        with chaves(self.chave_antiga):
            self.totp = Configuracao2FA.objects.create(
                usuario=self.usuario,
                chave_secreta="SECRETO123456",
                ativado=True,
            )
            TokenRecuperacaoSenha.objects.create(
                usuario=self.usuario,
                token="tokenteste123",
                ip_solicitacao="127.0.0.1",
                user_agent="test-agent",
            )

        # Consentimento ativo (preservado após exclusão)
        versao, _ = VersaoTextoConsentimento.objects.get_or_create(
            tipo="tratamento_dados",
            versao="1.0",
            defaults={
                "texto_apresentado": "Texto de exemplo.",
                "ativa": True,
            },
        )
        ConsentimentoLGPD.objects.get_or_create(
            usuario=self.usuario,
            tipo="tratamento_dados",
            versao="1.0",
            defaults={
                "texto_hash": "abc",
                "status": "aceito",
            },
        )

        self.admin = SolicitacaoExclusaoAdmin(SolicitacaoExclusao, None)

        self.client.force_login(self.usuario)

        # Superusuário para as actions do admin
        Usuario = get_user_model()
        self.superusuario = Usuario.objects.create_superuser(
            email='gestao@exemplo.com', password='senha123'
        )

    # ---------------------------------------------------------------
    # Helper: chama a action do admin de verdade
    # ---------------------------------------------------------------
    def _chamar_action_admin(self, action_nome, solicitacoes):
        """Chama a action do admin (aprovar/recusar) de verdade."""
        request = self.factory.post('/admin/fake/')
        request.user = self.superusuario

        # Middlewares necessários para message_user do admin funcionar
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.messages.middleware import MessageMiddleware

        SessionMiddleware(lambda req: None).process_request(request)
        request.session.save()
        MessageMiddleware(lambda req: None).process_request(request)

        queryset = SolicitacaoExclusao.objects.filter(
            pk__in=[s.pk for s in solicitacoes]
        )
        action = getattr(self.admin, action_nome)
        # Envolve com chaves para permitir decifrar dados cifrados com a chave antiga
        with chaves(self.chave_antiga):
            action(request, queryset)

    # ------------------------------------------------------------------
    # 1. View do titular: só cria solicitação PENDENTE, não altera dados
    # ------------------------------------------------------------------
    def test_view_cria_solicitacao_pendente_e_nao_altera_dados(self):
        cpf_antes = ler_valor_cru("funcionarios_funcionario", self.funcionario.pk, "cpf")
        email_antes = ler_valor_cru("usuarios_usuario", self.usuario.pk, "email")

        resposta = self.client.post(reverse("usuarios:solicitar_exclusao"))
        self.assertEqual(resposta.status_code, 302)

        solicitacao = SolicitacaoExclusao.objects.get(usuario=self.usuario)
        self.assertEqual(solicitacao.status, "PENDENTE")
        self.assertIsNone(solicitacao.executado_em)

        # Dados não mudaram (banco cru)
        self.assertEqual(
            ler_valor_cru("funcionarios_funcionario", self.funcionario.pk, "cpf"),
            cpf_antes,
        )
        self.assertEqual(
            ler_valor_cru("usuarios_usuario", self.usuario.pk, "email"), email_antes
        )
        self.assertTrue(self.usuario.is_active)

    # ---------------------------------------------------------------
    # 2. Aprovada via action do admin: anonimiza tudo
    # ---------------------------------------------------------------
    def test_aprovada_via_admin_anonimiza_tudo(self):
        self.client.post(reverse("usuarios:solicitar_exclusao"))
        solicitacao = SolicitacaoExclusao.objects.get(usuario=self.usuario)
        self.assertEqual(solicitacao.status, "PENDENTE")

        # Chama a action do admin de verdade
        self._chamar_action_admin('aprovar_solicitacoes', [solicitacao])

        solicitacao.refresh_from_db()
        self.assertEqual(solicitacao.status, "APROVADA")
        self.assertIsNotNone(solicitacao.executado_em)

        # Usuário inativo (refresh_from_db antes de checar)
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.is_active)

        # E-mail anonimizado (banco cru)
        email_depois = ler_valor_cru("usuarios_usuario", self.usuario.pk, "email")
        self.assertEqual(
            email_depois, f"anonimizado-{self.usuario.pk}@invalido.local"
        )

        # Senha inutilizável
        self.assertTrue(self.usuario.password.startswith('!'))

        # Nome anonimizado (banco cru)
        nome_depois = ler_valor_cru(
            "funcionarios_funcionario", self.funcionario.pk, "nome"
        )
        self.assertEqual(nome_depois, f"Titular anonimizado #{self.funcionario.pk}")

        # CPF ainda cifrado e não é texto puro (banco cru)
        cpf_depois = ler_valor_cru("funcionarios_funcionario", self.funcionario.pk, "cpf")
        self.assertTrue(cpf_depois.startswith("gAAAA"), "CPF deve continuar cifrado")
        self.assertNotEqual(cpf_depois, "12345678900")

        # cpf_indice único não identificável (banco cru)
        indice_depois = ler_valor_cru(
            "funcionarios_funcionario", self.funcionario.pk, "cpf_indice"
        )
        self.assertIsNotNone(indice_depois)
        self.assertNotEqual(indice_depois, "")

        # Telefone vazio (banco cru)
        telefone_depois = ler_valor_cru(
            "funcionarios_funcionario", self.funcionario.pk, "telefone"
        )
        self.assertEqual(telefone_depois, "")

        # Funcionario inativo (refresh dentro de chaves para decifrar CPF)
        with chaves(self.chave_antiga):
            self.funcionario.refresh_from_db()
            self.assertFalse(self.funcionario.ativo)

        # Jornadas apagadas
        self.assertEqual(
            JornadaTrabalho.objects.filter(funcionario=self.funcionario).count(), 0
        )

        # TOTP invalidada (banco cru)
        chave_totp_depois = ler_valor_cru(
            "usuarios_configuracao2fa", self.totp.pk, "chave_secreta"
        )
        self.assertEqual(chave_totp_depois, "")
        totp_depois = Configuracao2FA.objects.get(pk=self.totp.pk)
        self.assertFalse(totp_depois.ativado)

        # Tokens de recuperação apagados
        self.assertEqual(
            TokenRecuperacaoSenha.objects.filter(usuario=self.usuario).count(), 0
        )

        # LogAuditoria preservado (não apagado)
        self.assertTrue(
            LogAuditoria.objects.filter(
                tipo_evento='exclusao_dados'
            ).exists()
        )

        # ConsentimentoLGPD preservado (prova de consentimento)
        self.assertTrue(
            ConsentimentoLGPD.objects.filter(
                usuario=self.usuario, tipo='tratamento_dados'
            ).exists()
        )

        # Log criado com apenas IDs (sem email)
        log = LogAuditoria.objects.filter(
            tipo_evento='exclusao_dados', sucesso=True
        ).latest('data_hora')
        self.assertNotIn(self.usuario.email, log.mensagem)
        self.assertIn(f'Usuário ID: {self.usuario.pk}', log.mensagem)

    # ---------------------------------------------------------------
    # 3. Recusada com justificativa: nada muda
    # ---------------------------------------------------------------
    def test_recusada_com_justificativa_nada_muda(self):
        self.client.post(reverse("usuarios:solicitar_exclusao"))
        solicitacao = SolicitacaoExclusao.objects.get(usuario=self.usuario)
        solicitacao.justificativa = "Vínculo empregatício ainda ativo."
        solicitacao.save()

        self._chamar_action_admin('recusar_solicitacoes', [solicitacao])

        solicitacao.refresh_from_db()
        self.assertEqual(solicitacao.status, "RECUSADA")
        self.assertEqual(solicitacao.justificativa, "Vínculo empregatício ainda ativo.")
        self.assertIsNone(solicitacao.executado_em)

        # Dados não alterados (banco cru - CPF ainda cifrado)
        cpf_depois = ler_valor_cru("funcionarios_funcionario", self.funcionario.pk, "cpf")
        with chaves(self.chave_antiga):
            self.assertEqual(decifrar(cpf_depois), "12345678900")
        email_depois = ler_valor_cru("usuarios_usuario", self.usuario.pk, "email")
        self.assertEqual(email_depois, "ana@exemplo.com")
        self.assertTrue(self.usuario.is_active)

    # ---------------------------------------------------------------
    # 4. Recusada SEM justificativa: não recusa
    # ---------------------------------------------------------------
    def test_recusada_sem_justificativa_nao_recusa(self):
        self.client.post(reverse("usuarios:solicitar_exclusao"))
        solicitacao = SolicitacaoExclusao.objects.get(usuario=self.usuario)
        # Sem justificativa

        self._chamar_action_admin('recusar_solicitacoes', [solicitacao])

        solicitacao.refresh_from_db()
        self.assertEqual(solicitacao.status, "PENDENTE")
        self.assertIsNone(solicitacao.decidido_em)

    # ---------------------------------------------------------------
    # 5. Falha na execução: status segue PENDENTE
    # ---------------------------------------------------------------
    def test_falha_execucao_status_permanece_pendente(self):
        self.client.post(reverse("usuarios:solicitar_exclusao"))
        solicitacao = SolicitacaoExclusao.objects.get(usuario=self.usuario)

        # Força exceção na execução
        with patch(
            'usuarios.admin.executar_exclusao',
            side_effect=Exception('erro forçado na execução'),
        ):
            self._chamar_action_admin('aprovar_solicitacoes', [solicitacao])

        solicitacao.refresh_from_db()
        self.assertEqual(solicitacao.status, "PENDENTE")
        self.assertIsNone(solicitacao.executado_em)

    # ---------------------------------------------------------------
    # 6. Segunda execução bloqueada
    # ---------------------------------------------------------------
    def test_segunda_execucao_bloqueada(self):
        self.client.post(reverse("usuarios:solicitar_exclusao"))
        solicitacao = SolicitacaoExclusao.objects.get(usuario=self.usuario)

        # Primeira execução (aprovação)
        self._chamar_action_admin('aprovar_solicitacoes', [solicitacao])
        solicitacao.refresh_from_db()
        self.assertEqual(solicitacao.status, "APROVADA")
        self.assertIsNotNone(solicitacao.executado_em)

        # Tentar aprovar de novo -> deve falhar (já executada)
        with patch(
            'usuarios.admin.executar_exclusao',
            side_effect=Exception('já executada'),
        ):
            self._chamar_action_admin('aprovar_solicitacoes', [solicitacao])

        solicitacao.refresh_from_db()
        self.assertEqual(solicitacao.status, "APROVADA")
