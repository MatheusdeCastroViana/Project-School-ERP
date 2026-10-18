from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from config.test_criptografia import chaves, gerar_chave
from funcionarios.models import Cargo, Funcionario, Setor
from usuarios.models_2fa import Configuracao2FA

Usuario = get_user_model()

CHAVE_INDICE = "c" * 40

PAINEIS = {
    "gestao": "dashboard:gestao",
    "pedagogico": "dashboard:pedagogico",
    "financeiro": "dashboard:financeiro",
}

NOMES_SETORES = {
    "gestao": "Gestão",
    "pedagogico": "Pedagógico",
    "financeiro": "Financeiro",
}


@override_settings(BLIND_INDEX_KEY=CHAVE_INDICE)
class AutorizacaoDosPaineisTests(TestCase):
    def setUp(self):
        self.enterContext(chaves(gerar_chave()))

    def criar_usuario(self, email, cpf, setor=None):
        cargo = None
        if setor:
            objeto_setor, _ = Setor.objects.get_or_create(nome=NOMES_SETORES[setor])
            cargo, _ = Cargo.objects.get_or_create(
                nome=f"Cargo {setor}", defaults={"setor": objeto_setor}
            )
        funcionario = Funcionario.objects.create(nome="Funcionário", cpf=cpf, cargo=cargo)
        usuario = Usuario.objects.create_user(
            email=email, password="SenhaTeste123!", funcionario=funcionario
        )
        Configuracao2FA.objects.create(usuario=usuario, ativado=True)
        return usuario

    def test_anonimo_e_redirecionado_para_o_login(self):
        for nome, rota in PAINEIS.items():
            with self.subTest(painel=nome):
                resposta = self.client.get(reverse(rota))
                self.assertEqual(resposta.status_code, 302)
                self.assertTrue(resposta.url.startswith(reverse("account_login")))

    def test_usuario_sem_cargo_recebe_403_em_todos_os_paineis(self):
        usuario = self.criar_usuario("semcargo@exemplo.com", "111.111.111-11")
        self.client.force_login(usuario)
        for nome, rota in PAINEIS.items():
            with self.subTest(painel=nome):
                self.assertEqual(self.client.get(reverse(rota)).status_code, 403)

    def test_cada_setor_so_acessa_o_proprio_painel(self):
        cpfs = {
            "gestao": "222.222.222-22",
            "pedagogico": "333.333.333-33",
            "financeiro": "444.444.444-44",
        }
        for setor_usuario, cpf in cpfs.items():
            usuario = self.criar_usuario(f"{setor_usuario}@exemplo.com", cpf, setor=setor_usuario)
            self.client.force_login(usuario)
            for painel, rota in PAINEIS.items():
                with self.subTest(usuario=setor_usuario, painel=painel):
                    esperado = 200 if painel == setor_usuario else 403
                    self.assertEqual(self.client.get(reverse(rota)).status_code, esperado)

    def test_superusuario_acessa_todos_os_paineis(self):
        admin = Usuario.objects.create_superuser(email="admin@exemplo.com", password="SenhaTeste123!")
        Configuracao2FA.objects.create(usuario=admin, ativado=True)
        self.client.force_login(admin)
        for nome, rota in PAINEIS.items():
            with self.subTest(painel=nome):
                self.assertEqual(self.client.get(reverse(rota)).status_code, 200)

    def test_home_continua_acessivel_para_usuario_sem_cargo(self):
        usuario = self.criar_usuario("home@exemplo.com", "555.555.555-55")
        self.client.force_login(usuario)
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 200)