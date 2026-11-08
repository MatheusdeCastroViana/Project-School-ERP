from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from config.test_criptografia import chaves, gerar_chave
from funcionarios.mascaras import mascarar_cpf, mascarar_telefone
from funcionarios.models import Funcionario
from usuarios.models import ConsentimentoLGPD, LogAuditoria
from usuarios.models_2fa import Configuracao2FA

Usuario = get_user_model()

CHAVE_INDICE = "c" * 40


@override_settings(BLIND_INDEX_KEY=CHAVE_INDICE)
class AjustesDeSegurancaBase(TestCase):
    def setUp(self):
        self.enterContext(chaves(gerar_chave()))
        funcionario = Funcionario.objects.create(
            nome="Ana Souza", cpf="123.456.789-09", telefone="11987654321"
        )
        self.usuario = Usuario.objects.create_user(
            email="ana@exemplo.com", password="SenhaTeste123!", funcionario=funcionario
        )
        if not ConsentimentoLGPD.verificar_consentimento_ativo(self.usuario, "tratamento_dados"):
            ConsentimentoLGPD.objects.create(
                usuario=self.usuario,
                tipo="tratamento_dados",
                versao="1.0",
                texto_hash="0" * 64,
                status="aceito",
            )


class CadastroPublicoFechadoTests(AjustesDeSegurancaBase):
    def test_tela_de_login_nao_oferece_cadastro(self):
        resposta = self.client.get(reverse("account_login"))
        self.assertEqual(resposta.status_code, 200)
        self.assertNotContains(resposta, reverse("account_signup"))
        self.assertNotContains(resposta, "cadastre-se")

    def test_url_de_cadastro_exibe_pagina_de_cadastro_fechado(self):
        resposta = self.client.get(reverse("account_signup"))
        self.assertTemplateUsed(resposta, "account/signup_closed.html")

    def test_post_de_cadastro_nao_cria_usuario(self):
        antes = Usuario.objects.count()
        self.client.post(
            reverse("account_signup"),
            {"email": "invasor@exemplo.com", "password1": "SenhaTeste123!", "password2": "SenhaTeste123!"},
        )
        self.assertEqual(Usuario.objects.count(), antes)


class DoisFatoresObrigatorioTests(AjustesDeSegurancaBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.usuario)

    def test_sem_2fa_qualquer_tela_redireciona_para_ativacao(self):
        for nome in ("dashboard:home", "usuarios:consultar_dados", "usuarios:dashboard"):
            with self.subTest(tela=nome):
                resposta = self.client.get(reverse(nome))
                self.assertRedirects(
                    resposta, reverse("usuarios:ativar_2fa"), fetch_redirect_response=False
                )

    def test_sem_2fa_admin_tambem_e_bloqueado(self):
        resposta = self.client.get("/admin/")
        self.assertRedirects(
            resposta, reverse("usuarios:ativar_2fa"), fetch_redirect_response=False
        )

    def test_sem_2fa_tela_de_ativacao_e_logout_continuam_acessiveis(self):
        self.assertEqual(self.client.get(reverse("usuarios:ativar_2fa")).status_code, 200)
        resposta = self.client.post(reverse("usuarios:logout"))
        self.assertRedirects(resposta, reverse("account_login"), fetch_redirect_response=False)

    def test_logout_por_get_nao_e_permitido_e_mantem_a_sessao(self):
        resposta = self.client.get(reverse("usuarios:logout"))
        self.assertEqual(resposta.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

    def test_logout_por_post_encerra_a_sessao(self):
        self.client.post(reverse("usuarios:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_com_2fa_ativo_o_acesso_e_liberado(self):
        Configuracao2FA.objects.create(usuario=self.usuario, ativado=True)
        resposta = self.client.get(reverse("usuarios:consultar_dados"))
        self.assertEqual(resposta.status_code, 200)

    def test_2fa_criado_mas_nao_confirmado_continua_bloqueando(self):
        Configuracao2FA.objects.create(usuario=self.usuario, ativado=False)
        resposta = self.client.get(reverse("usuarios:consultar_dados"))
        self.assertRedirects(
            resposta, reverse("usuarios:ativar_2fa"), fetch_redirect_response=False
        )

    def test_desativar_2fa_nao_e_permitido(self):
        Configuracao2FA.objects.create(usuario=self.usuario, ativado=True)
        resposta = self.client.post(reverse("usuarios:desativar_2fa"))
        self.assertRedirects(resposta, reverse("usuarios:dashboard"), fetch_redirect_response=False)
        self.assertTrue(Configuracao2FA.objects.get(usuario=self.usuario).ativado)


class MascarasTests(AjustesDeSegurancaBase):
    def test_mascara_de_cpf(self):
        self.assertEqual(mascarar_cpf("123.456.789-09"), "***.456.789-**")
        self.assertEqual(mascarar_cpf("12345678909"), "***.456.789-**")
        self.assertEqual(mascarar_cpf("123"), "***")
        self.assertEqual(mascarar_cpf(""), "")

    def test_mascara_de_telefone(self):
        self.assertEqual(mascarar_telefone("11987654321"), "*******4321")
        self.assertEqual(mascarar_telefone(""), "")

    def test_tela_mascara_mas_exportacao_continua_completa(self):
        Configuracao2FA.objects.create(usuario=self.usuario, ativado=True)
        self.client.force_login(self.usuario)

        tela = self.client.get(reverse("usuarios:consultar_dados"))
        self.assertContains(tela, 'id="valor-cpf" data-mascarado="***.456.789-**"')

        exportacao = self.client.get(reverse("usuarios:exportar_dados"))
        self.assertContains(exportacao, "123.456.789-09")
        self.assertContains(exportacao, "11987654321")


class LogoutInvalidaSessaoTests(AjustesDeSegurancaBase):
    def setUp(self):
        super().setUp()
        Configuracao2FA.objects.create(usuario=self.usuario, ativado=True)
        self.client.force_login(self.usuario)
        self.chave_sessao = self.client.cookies[settings.SESSION_COOKIE_NAME].value

    def _cliente_com_cookie_antigo(self):
        cliente = Client()
        cliente.cookies[settings.SESSION_COOKIE_NAME] = self.chave_sessao
        return cliente

    def test_cookie_da_sessao_funciona_antes_do_logout(self):
        resposta = self._cliente_com_cookie_antigo().get(reverse("usuarios:consultar_dados"))
        self.assertEqual(resposta.status_code, 200, resposta.get("Location"))

    def test_cookie_antigo_e_recusado_depois_do_logout(self):
        self.client.post(reverse("usuarios:logout"))
        resposta = self._cliente_com_cookie_antigo().get(reverse("usuarios:consultar_dados"))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn(reverse("account_login"), resposta.url)

    def test_sessao_e_apagada_do_banco_depois_do_logout(self):
        self.assertTrue(Session.objects.filter(session_key=self.chave_sessao).exists())
        self.client.post(reverse("usuarios:logout"))
        self.assertFalse(Session.objects.filter(session_key=self.chave_sessao).exists())

    def test_logout_pela_rota_do_allauth_tambem_invalida_o_cookie(self):
        self.client.post(reverse("account_logout"))
        resposta = self._cliente_com_cookie_antigo().get(reverse("usuarios:consultar_dados"))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn(reverse("account_login"), resposta.url)
        self.assertFalse(Session.objects.filter(session_key=self.chave_sessao).exists())


class LogoutRegistraAuditoriaTests(AjustesDeSegurancaBase):
    def setUp(self):
        super().setUp()
        Configuracao2FA.objects.create(usuario=self.usuario, ativado=True)
        self.client.force_login(self.usuario)

    def _logs_de_logout(self):
        return LogAuditoria.objects.filter(usuario=self.usuario, tipo_evento="logout")

    def test_logout_pela_view_do_sistema_gera_um_unico_log(self):
        self.client.post(reverse("usuarios:logout"))
        self.assertEqual(self._logs_de_logout().count(), 1)

    def test_logout_pela_rota_do_allauth_gera_um_unico_log(self):
        self.client.post(reverse("account_logout"))
        self.assertEqual(self._logs_de_logout().count(), 1)

    def test_logout_sem_usuario_autenticado_nao_gera_log(self):
        cliente = Client()
        cliente.post(reverse("account_logout"))
        self.assertEqual(LogAuditoria.objects.filter(tipo_evento="logout").count(), 0)