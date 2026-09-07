from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from funcionarios.models import Funcionario
from django.contrib.auth.hashers import make_password
import time

from usuarios.models_recuperacao import TokenRecuperacaoSenha

Usuario = get_user_model()

class UsuarioArgon2PasswordHasherTests(TestCase):
    def setUp(self):
        self.senha = "SenhaTeste123!"
        self.funcionario = Funcionario.objects.create(
            nome="Funcionário Teste",
            cpf="000.000.000-00",
        )
        self.usuario = Usuario.objects.create_user(
            email="teste@exemplo.com",
            password=self.senha,
            funcionario=self.funcionario,
        )

    def test_hash_usa_argon2id(self):
        #Confirma que o algoritmo usado é o Argon2id.
        self.assertTrue(self.usuario.password.startswith("argon2$argon2id$"))

    def test_parametros_de_custo_configurados(self):
        #Confirma que os parâmetros customizados foram aplicados.
        self.assertIn("m=32768", self.usuario.password)
        self.assertIn("t=5", self.usuario.password)
        self.assertIn("p=1", self.usuario.password)

    def test_senha_correta_autentica(self):
        self.assertTrue(check_password(self.senha, self.usuario.password))

    def test_senha_incorreta_nao_autentica(self):
        self.assertFalse(check_password("senha_errada", self.usuario.password))

    def test_tempo_de_hash_dentro_do_esperado(self):
            # Teste para medir a velocidade de geração do hash
            senha = "OutraSenhaTeste456!"
    
            inicio = time.perf_counter()
            hash_gerado = make_password(senha)
            fim = time.perf_counter()
    
            tempo_ms = (fim - inicio) * 1000
            print(f"\nTempo de hash (Argon2id, t=5, m=32768, p=1): {tempo_ms:.2f} ms")
    
            self.assertTrue(hash_gerado.startswith("argon2$argon2id$"))
            self.assertLess(tempo_ms, 2000, "Hash demorou mais do que o esperado (>2s)")

class RecuperacaoSenhaTests(TestCase):

    def setUp(self):
        self.senha_antiga = "SenhaAntiga123!"
        self.senha_nova = "SenhaNova456!"

        self.funcionario = Funcionario.objects.create(
            nome="Funcionário Recuperação",
            cpf="111.111.111-11",
        )
        self.usuario = Usuario.objects.create_user(
            email="recuperacao@exemplo.com",
            password=self.senha_antiga,
            funcionario=self.funcionario,
        )

    def solicitar_recuperacao(self, email):
        url = reverse("usuarios:solicitar_recuperacao")
        return self.client.post(url, {"email": email})

    def obter_token_gerado(self):
        return TokenRecuperacaoSenha.objects.latest('criado_em')

    def url_confirmacao(self, token):
        return reverse("usuarios:confirmar_recuperacao", kwargs={"token": token})

    def test_solicitacao_gera_token_para_email_existente(self):
        self.solicitar_recuperacao(self.usuario.email)
        self.assertTrue(
            TokenRecuperacaoSenha.objects.filter(usuario=self.usuario).exists()
        )

    def test_solicitacao_com_email_inexistente_nao_gera_token(self):
        self.solicitar_recuperacao("naoexiste@exemplo.com")
        self.assertFalse(TokenRecuperacaoSenha.objects.exists())

    def test_log_registrado_na_solicitacao_email_encontrado(self):
        with self.assertLogs("auditoria_seguranca", level="INFO") as logs:
            self.solicitar_recuperacao(self.usuario.email)
        self.assertTrue(any("Usuário encontrado: True" in m for m in logs.output))

    def test_log_registrado_na_solicitacao_email_nao_encontrado(self):
        with self.assertLogs("auditoria_seguranca", level="INFO") as logs:
            self.solicitar_recuperacao("naoexiste@exemplo.com")
        self.assertTrue(any("Usuário encontrado: False" in m for m in logs.output))

    def test_token_valido_permite_trocar_senha_e_loga_sucesso(self):
        self.solicitar_recuperacao(self.usuario.email)
        token_obj = self.obter_token_gerado()

        with self.assertLogs("auditoria_seguranca", level="INFO") as logs:
            resposta = self.client.post(self.url_confirmacao(token_obj.token), {
                "senha1": self.senha_nova,
                "senha2": self.senha_nova,
            })

        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(any("Sucesso: True" in m for m in logs.output))

        self.usuario.refresh_from_db()
        self.assertTrue(check_password(self.senha_nova, self.usuario.password))

    def test_token_reutilizado_falha_e_loga(self):
        self.solicitar_recuperacao(self.usuario.email)
        token_obj = self.obter_token_gerado()

        self.client.post(self.url_confirmacao(token_obj.token), {
            "senha1": self.senha_nova,
            "senha2": self.senha_nova,
        })

        with self.assertLogs("auditoria_seguranca", level="WARNING") as logs:
            resposta = self.client.get(self.url_confirmacao(token_obj.token))

        self.assertTrue(any("já utilizado" in m for m in logs.output))

    def test_token_expirado_falha_e_loga(self):
        self.solicitar_recuperacao(self.usuario.email)
        token_obj = self.obter_token_gerado()
        token_obj.expira_em = timezone.now() - timedelta(hours=1)
        token_obj.save(update_fields=['expira_em'])

        with self.assertLogs("auditoria_seguranca", level="WARNING") as logs:
            self.client.get(self.url_confirmacao(token_obj.token))

        self.assertTrue(any("expirado" in m for m in logs.output))

    def test_token_inexistente_loga_falha(self):
        with self.assertLogs("auditoria_seguranca", level="WARNING") as logs:
            self.client.get(self.url_confirmacao("token-que-nao-existe"))

        self.assertTrue(any("token inexistente" in m for m in logs.output))