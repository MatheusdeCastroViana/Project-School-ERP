import time

import pyotp
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldError
from django.db import connection
from django.test import TestCase
from django.urls import reverse

from config.criptografia import ErroDecifragem, decifrar
from config.test_criptografia import chaves, gerar_chave
from funcionarios.models import Funcionario
from usuarios.models_2fa import Configuracao2FA

Usuario = get_user_model()

PREFIXO_TOKEN = "gAAAA"


def tabela_2fa():
    return connection.ops.quote_name(Configuracao2FA._meta.db_table)


def ler_valor_cru(pk):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT chave_secreta FROM {tabela_2fa()} WHERE id = %s", [pk])
        return cursor.fetchone()[0]


def gravar_valor_cru(pk, valor):
    with connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {tabela_2fa()} SET chave_secreta = %s WHERE id = %s", [valor, pk]
        )


def criar_usuario(email, cpf):
    funcionario = Funcionario.objects.create(nome="Funcionário 2FA", cpf=cpf)
    return Usuario.objects.create_user(
        email=email, password="SenhaTeste123!", funcionario=funcionario
    )


def gerar_codigo_invalido(segredo):
    totp = pyotp.TOTP(segredo)
    agora = int(time.time())
    validos = {totp.at(agora + deslocamento) for deslocamento in (-30, 0, 30)}
    return next(f"{n:06d}" for n in range(1000000) if f"{n:06d}" not in validos)


class ChaveSecretaCifradaNoBancoTests(TestCase):
    def setUp(self):
        self.enterContext(chaves(gerar_chave()))
        self.usuario = criar_usuario("cifrado@exemplo.com", "222.222.222-22")
        self.segredo = pyotp.random_base32()
        self.config = Configuracao2FA.objects.create(
            usuario=self.usuario, chave_secreta=self.segredo, ativado=True
        )

    def test_valor_no_banco_esta_cifrado(self):
        cru = ler_valor_cru(self.config.pk)
        self.assertTrue(cru.startswith(PREFIXO_TOKEN))
        self.assertNotEqual(cru, self.segredo)
        self.assertNotIn(self.segredo, cru)

    def test_valor_cru_decifra_para_o_segredo_original(self):
        self.assertEqual(decifrar(ler_valor_cru(self.config.pk)), self.segredo)

    def test_leitura_pelo_model_devolve_o_segredo_original(self):
        recarregado = Configuracao2FA.objects.get(pk=self.config.pk)
        self.assertEqual(recarregado.chave_secreta, self.segredo)

    def test_save_gera_chave_automatica_e_grava_cifrada(self):
        outro = criar_usuario("automatico@exemplo.com", "333.333.333-33")
        nova = Configuracao2FA.objects.create(usuario=outro)
        self.assertEqual(len(nova.chave_secreta), 32)
        cru = ler_valor_cru(nova.pk)
        self.assertTrue(cru.startswith(PREFIXO_TOKEN))
        self.assertEqual(decifrar(cru), nova.chave_secreta)

    def test_salvar_de_novo_nao_cifra_duas_vezes(self):
        carregado = Configuracao2FA.objects.get(pk=self.config.pk)
        carregado.ativado = False
        carregado.save()
        self.assertEqual(decifrar(ler_valor_cru(self.config.pk)), self.segredo)

    def test_adulteracao_no_banco_e_detectada(self):
        cru = ler_valor_cru(self.config.pk)
        troca = "A" if cru[20] != "A" else "B"
        gravar_valor_cru(self.config.pk, cru[:20] + troca + cru[21:])
        with self.assertRaises(ErroDecifragem):
            Configuracao2FA.objects.get(pk=self.config.pk)

    def test_valor_em_texto_puro_no_banco_nao_e_aceito(self):
        gravar_valor_cru(self.config.pk, self.segredo)
        with self.assertRaises(ErroDecifragem):
            Configuracao2FA.objects.get(pk=self.config.pk)

    def test_filtro_pela_chave_cifrada_e_proibido(self):
        with self.assertRaises(FieldError):
            list(Configuracao2FA.objects.filter(chave_secreta=self.segredo))

    def test_verify_token_aceita_codigo_valido(self):
        carregado = Configuracao2FA.objects.get(pk=self.config.pk)
        self.assertTrue(carregado.verify_token(pyotp.TOTP(self.segredo).now()))

    def test_verify_token_rejeita_codigo_invalido(self):
        carregado = Configuracao2FA.objects.get(pk=self.config.pk)
        self.assertFalse(carregado.verify_token(gerar_codigo_invalido(self.segredo)))


class FluxoDoisFatoresComChaveCifradaTests(TestCase):
    def setUp(self):
        self.enterContext(chaves(gerar_chave()))
        self.usuario = criar_usuario("fluxo@exemplo.com", "444.444.444-44")

    def test_tela_de_ativacao_exibe_o_segredo_original(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse("usuarios:ativar_2fa"))
        self.assertEqual(resposta.status_code, 200)
        config = Configuracao2FA.objects.get(usuario=self.usuario)
        self.assertEqual(resposta.context["chave_secreta"], config.chave_secreta)
        self.assertEqual(decifrar(ler_valor_cru(config.pk)), config.chave_secreta)

    def test_ativacao_com_codigo_valido_ativa_o_2fa(self):
        self.client.force_login(self.usuario)
        self.client.get(reverse("usuarios:ativar_2fa"))
        segredo = Configuracao2FA.objects.get(usuario=self.usuario).chave_secreta
        resposta = self.client.post(
            reverse("usuarios:ativar_2fa"), {"token": pyotp.TOTP(segredo).now()}
        )
        self.assertRedirects(
            resposta, reverse("usuarios:dashboard"), fetch_redirect_response=False
        )
        self.assertTrue(Configuracao2FA.objects.get(usuario=self.usuario).ativado)

    def test_ativacao_com_codigo_invalido_nao_ativa_o_2fa(self):
        self.client.force_login(self.usuario)
        self.client.get(reverse("usuarios:ativar_2fa"))
        segredo = Configuracao2FA.objects.get(usuario=self.usuario).chave_secreta
        self.client.post(
            reverse("usuarios:ativar_2fa"), {"token": gerar_codigo_invalido(segredo)}
        )
        self.assertFalse(Configuracao2FA.objects.get(usuario=self.usuario).ativado)

    def test_login_com_segundo_fator_valido_autentica(self):
        config = Configuracao2FA.objects.create(usuario=self.usuario, ativado=True)
        sessao = self.client.session
        sessao["usuario_pendente_2fa"] = self.usuario.pk
        sessao.save()
        resposta = self.client.post(
            reverse("usuarios:verificar_2fa"),
            {"token": pyotp.TOTP(config.chave_secreta).now()},
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_com_segundo_fator_invalido_nao_autentica(self):
        config = Configuracao2FA.objects.create(usuario=self.usuario, ativado=True)
        sessao = self.client.session
        sessao["usuario_pendente_2fa"] = self.usuario.pk
        sessao.save()
        resposta = self.client.post(
            reverse("usuarios:verificar_2fa"),
            {"token": gerar_codigo_invalido(config.chave_secreta)},
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)