from contextlib import contextmanager

from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from config.criptografia import (
    ErroDecifragem,
    _obter_fernet,
    cifrar,
    decifrar,
    rotacionar,
)


def gerar_chave():
    return Fernet.generate_key().decode()


@contextmanager
def chaves(*valores):
    _obter_fernet.cache_clear()
    try:
        with override_settings(FIELD_ENCRYPTION_KEYS=list(valores)):
            yield
    finally:
        _obter_fernet.cache_clear()


class ConfiguracaoTests(SimpleTestCase):
    def test_sem_chave_levanta_erro_de_configuracao(self):
        with chaves():
            with self.assertRaises(ImproperlyConfigured):
                cifrar("x")

    def test_chave_malformada_levanta_erro_de_configuracao(self):
        with chaves("isto-nao-e-uma-chave-fernet"):
            with self.assertRaises(ImproperlyConfigured):
                cifrar("x")

    def test_mensagem_de_erro_nao_expoe_a_chave(self):
        invalida = "isto-nao-e-uma-chave-fernet"
        with chaves(invalida):
            with self.assertRaises(ImproperlyConfigured) as ctx:
                cifrar("x")
        self.assertNotIn(invalida, str(ctx.exception))


class IdaEVoltaTests(SimpleTestCase):
    def test_ida_e_volta_texto_simples(self):
        with chaves(gerar_chave()):
            self.assertEqual(decifrar(cifrar("123.456.789-09")), "123.456.789-09")

    def test_ida_e_volta_com_acentos(self):
        with chaves(gerar_chave()):
            self.assertEqual(decifrar(cifrar("João Álvares")), "João Álvares")

    def test_token_difere_do_texto_e_nao_o_contem(self):
        with chaves(gerar_chave()):
            token = cifrar("11999998888")
        self.assertNotEqual(token, "11999998888")
        self.assertNotIn("11999998888", token)

    def test_mesmo_texto_gera_tokens_diferentes(self):
        with chaves(gerar_chave()):
            self.assertNotEqual(cifrar("mesmo valor"), cifrar("mesmo valor"))


class IntegridadeTests(SimpleTestCase):
    def test_token_adulterado_levanta_erro(self):
        with chaves(gerar_chave()):
            token = cifrar("valor sensivel")
            troca = "A" if token[20] != "A" else "B"
            adulterado = token[:20] + troca + token[21:]
            with self.assertRaises(ErroDecifragem):
                decifrar(adulterado)

    def test_chave_errada_levanta_erro(self):
        with chaves(gerar_chave()):
            token = cifrar("valor sensivel")
        with chaves(gerar_chave()):
            with self.assertRaises(ErroDecifragem):
                decifrar(token)

    def test_texto_puro_nao_e_aceito_como_token(self):
        with chaves(gerar_chave()):
            with self.assertRaises(ErroDecifragem):
                decifrar("123.456.789-09")

    def test_mensagem_de_erro_nao_expoe_token_nem_texto(self):
        with chaves(gerar_chave()):
            token = cifrar("valor sensivel")
            adulterado = token[:20] + ("A" if token[20] != "A" else "B") + token[21:]
            with self.assertRaises(ErroDecifragem) as ctx:
                decifrar(adulterado)
        self.assertNotIn(token, str(ctx.exception))
        self.assertNotIn("valor sensivel", str(ctx.exception))


class RotacaoTests(SimpleTestCase):
    def setUp(self):
        self.chave_antiga = gerar_chave()
        self.chave_nova = gerar_chave()

    def test_dado_antigo_continua_legivel_apos_adicionar_chave_nova(self):
        with chaves(self.chave_antiga):
            token_antigo = cifrar("segredo")
        with chaves(self.chave_nova, self.chave_antiga):
            self.assertEqual(decifrar(token_antigo), "segredo")

    def test_novos_dados_usam_a_chave_mais_nova(self):
        with chaves(self.chave_nova, self.chave_antiga):
            token = cifrar("segredo")
        with chaves(self.chave_nova):
            self.assertEqual(decifrar(token), "segredo")
        with chaves(self.chave_antiga):
            with self.assertRaises(ErroDecifragem):
                decifrar(token)

    def test_rotacionar_migra_o_token_para_a_chave_nova(self):
        with chaves(self.chave_antiga):
            token_antigo = cifrar("segredo")
        with chaves(self.chave_nova, self.chave_antiga):
            token_novo = rotacionar(token_antigo)
        with chaves(self.chave_nova):
            self.assertEqual(decifrar(token_novo), "segredo")
            with self.assertRaises(ErroDecifragem):
                decifrar(token_antigo)

    def test_rotacionar_token_invalido_levanta_erro(self):
        with chaves(self.chave_nova, self.chave_antiga):
            with self.assertRaises(ErroDecifragem):
                rotacionar("lixo")