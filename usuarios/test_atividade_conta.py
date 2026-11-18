from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from funcionarios.models import Funcionario
from usuarios.models import Usuario, LogAuditoria, ConsentimentoLGPD
from usuarios.models_2fa import Configuracao2FA
from usuarios.models import VersaoTextoConsentimento


class AtividadeContaTests(TestCase):
    def setUp(self):
        self.funcionario = Funcionario.objects.create(
            nome="Funcionário Atividade",
            cpf="222.222.222-22",
        )
        self.usuario = Usuario.objects.create_user(
            email="atividade@exemplo.com",
            password="SenhaTeste123!",
            funcionario=self.funcionario,
        )
        Configuracao2FA.objects.create(usuario=self.usuario, ativado=True)
        VersaoTextoConsentimento.objects.get_or_create(
            tipo="tratamento_dados",
            versao="1.0",
            defaults={"texto_apresentado": "texto de teste", "ativa": True},
        )
        ConsentimentoLGPD.objects.create(
            usuario=self.usuario,
            tipo="tratamento_dados",
            versao="1.0",
            texto_hash="hash",
            status="aceito",
        )

        self.outro_funcionario = Funcionario.objects.create(
            nome="Outro Funcionário",
            cpf="333.333.333-33",
        )
        self.outro_usuario = Usuario.objects.create_user(
            email="outro@exemplo.com",
            password="SenhaTeste123!",
            funcionario=self.outro_funcionario,
        )
        Configuracao2FA.objects.create(usuario=self.outro_usuario, ativado=True)
        ConsentimentoLGPD.objects.create(
            usuario=self.outro_usuario,
            tipo="tratamento_dados",
            versao="1.0",
            texto_hash="hash",
            status="aceito",
        )

        self.url = reverse("usuarios:dashboard")

    def _log(self, usuario, tipo_evento, sucesso=True, ip_address="127.0.0.1", mensagem="msg", detalhes=None):
        return LogAuditoria.objects.create(
            usuario=usuario,
            tipo_evento=tipo_evento,
            sucesso=sucesso,
            ip_address=ip_address,
            user_agent="teste",
            mensagem=mensagem,
            detalhes=detalhes or None,
        )

    def test_somente_eventos_do_usuario_logado_apeliam(self):
        self.client.force_login(self.usuario)

        self._log(self.usuario, "2fa_verificacao_sucesso", True)
        self._log(self.outro_usuario, "2fa_verificacao_sucesso", True)

        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 200)

        conteudo = resposta.content.decode("utf-8")
        self.assertIn("Login realizado", conteudo)
        # O evento do outro usuário não deve aparecer.
        self.assertEqual(conteudo.count("Login realizado"), 1)

    def test_eventos_fora_da_allowlist_nao_aparecem(self):
        self.client.force_login(self.usuario)

        self._log(self.usuario, "login", True)
        self._log(self.usuario, "logout", True)
        self._log(self.usuario, "exportacao_dados", True)
        self._log(self.usuario, "outro", True)
        self._log(self.usuario, "2fa_desativacao", True)
        self._log(self.usuario, "2fa_sessao_expirada", True)

        resposta = self.client.get(self.url)
        conteudo = resposta.content.decode("utf-8")

        self.assertNotIn("Login", conteudo)
        self.assertNotIn("Exportação", conteudo)
        self.assertNotIn("Outro", conteudo)

    def test_limite_de_10_e_ordem_mais_recente_primeiro(self):
        self.client.force_login(self.usuario)

        agora = timezone.now()
        for i in range(12):
            self._log(self.usuario, "2fa_verificacao_sucesso", True)

        resposta = self.client.get(self.url)
        conteudo = resposta.content.decode("utf-8")

        # Deve exibir exatamente 10 itens "Login realizado".
        self.assertEqual(conteudo.count("Login realizado"), 10)

    def test_2fa_verificacao_sucesso_aparece_como_login_realizado(self):
        self.client.force_login(self.usuario)

        self._log(self.usuario, "2fa_verificacao_sucesso", True)
        self._log(self.usuario, "login", True)

        resposta = self.client.get(self.url)
        conteudo = resposta.content.decode("utf-8")

        self.assertIn("Login realizado", conteudo)
        # O tipo 'login' está fora da allowlist, não deve aparecer.
        self.assertNotIn("Login realizado por senha", conteudo)
        self.assertEqual(conteudo.count("Login realizado"), 1)

    def test_ip_mensagem_e_detalhes_nao_aparecem_no_html(self):
        self.client.force_login(self.usuario)

        self._log(
            self.usuario,
            "login_falha",
            False,
            ip_address="200.200.200.200",
            mensagem="senha incorreta",
            detalhes={"tentativa": 1},
        )

        resposta = self.client.get(self.url)
        conteudo = resposta.content.decode("utf-8")

        self.assertNotIn("200.200.200.200", conteudo)
        self.assertNotIn("senha incorreta", conteudo)
        self.assertNotIn("secreto", conteudo)

    def test_estado_vazio_quando_sem_eventos(self):
        self.client.force_login(self.usuario)

        resposta = self.client.get(self.url)
        conteudo = resposta.content.decode("utf-8")

        self.assertIn("Nenhuma atividade recente registrada.", conteudo)
