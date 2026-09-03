from django.test import TestCase, override_settings
from django.core import mail
from django.urls import reverse
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from funcionarios.models import Funcionario
from django.contrib.auth.hashers import make_password
import time
import re

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
        # Cria o usuário como o admin faria (create_user), sem o EmailAdress do allauth
        self.senha_antiga = "SenhaAntiga123!"
        self.senha_nova = "SenhaNova456!"

        #Cria funcionario
        self.funcionario = Funcionario.objects.create(
            nome="Funcionário Recuperação",
            cpf="111.111.111-11",
        )
        #Cria o usuario
        self.usuario = Usuario.objects.create_user(
            email="recuperacao@exemplo.com",
            password=self.senha_antiga,
            funcionario=self.funcionario,
        )

    def solicitar_recuperacao(self, email):
        url = reverse("account_reset_password") # Converte o nome da URL na URL de verdade /accounts/password/reset/...
        return self.client.post(url, {"email": email})

    def extrair_uidb36_e_key(self, email_enviado):
        # O template manda {{ password_reset_url }}, que tem o formato:
        # /accounts/password/reset/key/<uidb36>-<key>/
        padrao = r"/accounts/password/reset/key/([0-9A-Za-z]+)-([^/\s]+)/" #regex
        match = re.search(padrao, email_enviado.body)
        self.assertIsNotNone(match, "Link de reset não encontrado no e-mail")
        return match.group(1), match.group(2)

    def url_formulario_nova_senha(self, uidb36):
        # Depois que o token é validado, o allauth troca a "key" real
        # por essa palavra fixa "set-password" na URL guardada em sessão.
        return reverse(
            "account_reset_password_from_key",
            kwargs={"uidb36": uidb36, "key": "set-password"},
        )

    # Mensagem genérica pra e-mail inexistente

    def test_email_inexistente_nao_revela_informacao(self):
        resposta_real = self.solicitar_recuperacao(self.usuario.email)
        mail.outbox = []  # Limpa antes do segundo request pra não confundir
        resposta_falso = self.solicitar_recuperacao("naoexiste@exemplo.com")

        # A resposta HTTP tem que ser idêntica nos dois casos, é isso
        # que impede alguém de descobrir quais e-mails estão cadastrados.
        self.assertEqual(resposta_real.status_code, resposta_falso.status_code)
        self.assertEqual(resposta_real.url, resposta_falso.url)

    # Versão nova do teste de EmailAddress 

    def test_usuario_sem_emailaddress_consegue_solicitar_recuperacao(self):
        # Confirma se o usuário NÃO tem EmailAddress,já que foi criado via create_user (igual o admin faz).
        self.assertFalse(
            EmailAddress.objects.filter(user=self.usuario).exists()
        )

        resposta = self.solicitar_recuperacao(self.usuario.email)

        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.usuario.email, mail.outbox[0].to)

    # Token é gerado e vai no e-mail

    def test_email_contem_link_com_token(self):
        self.solicitar_recuperacao(self.usuario.email)
        uidb36, key = self.extrair_uidb36_e_key(mail.outbox[0])
        self.assertTrue(uidb36)
        self.assertTrue(key)

    # Token expira 

    def test_token_expira_apos_tempo_configurado(self):
        with override_settings(PASSWORD_RESET_TIMEOUT=1): # Não altera o PASSWORD_RESET_TIMEOUT do settings.
            self.solicitar_recuperacao(self.usuario.email)
            uidb36, key = self.extrair_uidb36_e_key(mail.outbox[0])

            time.sleep(2)  # espera o token vencer (timeout = 1s)

            url_reset = reverse(
                "account_reset_password_from_key",
                kwargs={"uidb36": uidb36, "key": key},
            )
            resposta = self.client.get(url_reset)

            # Quando o token é inválido/expirado, o allauth renderiza a
            # mesma página com token_fail=True, e o template mostra "Token inválido".
            self.assertContains(resposta, "Token inválido")

    # Token não pode ser reutilizado

    def test_token_nao_pode_ser_reutilizado(self):
        self.solicitar_recuperacao(self.usuario.email)
        uidb36, key = self.extrair_uidb36_e_key(mail.outbox[0])

        url_reset = reverse(
            "account_reset_password_from_key",
            kwargs={"uidb36": uidb36, "key": key},
        )
        url_form = self.url_formulario_nova_senha(uidb36)

        # 1ª vez: token válido, acessa o link e preenche a senha nova
        resposta_get = self.client.get(url_reset)
        self.assertEqual(resposta_get.status_code, 302)

        resposta_post = self.client.post(url_form, {
            "password1": self.senha_nova,
            "password2": self.senha_nova,
        })
        self.assertEqual(resposta_post.status_code, 302)  # sucesso

        # 2ª vez: mesmo link, token já usado tem que falhar
        resposta_reuso = self.client.get(url_reset)
        self.assertContains(resposta_reuso, "Token inválido")