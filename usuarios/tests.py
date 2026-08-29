from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from funcionarios.models import Funcionario
import time

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
        # Testa o tempo em ms que o hasher demora pra rodar com os parâmetros configurados.
        senha = "OutraSenhaTeste456!"

        inicio = time.perf_counter()
        Usuario.objects.create_user(
            email="teste_tempo@exemplo.com",
            password=senha,
            funcionario=Funcionario.objects.create(nome="Funcionário Tempo", cpf="111.111.111-11"),
        )
        fim = time.perf_counter()

        tempo_ms = (fim - inicio) * 1000
        print(f"\nTempo de hash (Argon2id, t=5, m=32768, p=1): {tempo_ms:.2f} ms")

        # Alerta se o hash ficar bem mais lento do que o normal
        self.assertLess(tempo_ms, 2000, "Hash demorou mais do que o esperado (>2s)")