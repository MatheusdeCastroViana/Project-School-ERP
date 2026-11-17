from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from config.criptografia import indice_cego

CHAVE_A = "a" * 40
CHAVE_B = "b" * 40


class IndiceCegoTests(SimpleTestCase):
    @override_settings(BLIND_INDEX_KEY=CHAVE_A)
    def test_mesmo_valor_gera_mesmo_indice(self):
        self.assertEqual(indice_cego("12345678909"), indice_cego("12345678909"))

    @override_settings(BLIND_INDEX_KEY=CHAVE_A)
    def test_valores_diferentes_geram_indices_diferentes(self):
        self.assertNotEqual(indice_cego("12345678909"), indice_cego("98765432100"))

    @override_settings(BLIND_INDEX_KEY=CHAVE_A)
    def test_formato_e_hexadecimal_de_64_caracteres(self):
        self.assertRegex(indice_cego("12345678909"), r"^[0-9a-f]{64}$")

    @override_settings(BLIND_INDEX_KEY=CHAVE_A)
    def test_indice_nao_contem_o_valor_original(self):
        self.assertNotIn("12345678909", indice_cego("12345678909"))

    def test_chaves_diferentes_geram_indices_diferentes(self):
        with override_settings(BLIND_INDEX_KEY=CHAVE_A):
            primeiro = indice_cego("12345678909")
        with override_settings(BLIND_INDEX_KEY=CHAVE_B):
            segundo = indice_cego("12345678909")
        self.assertNotEqual(primeiro, segundo)

    @override_settings(BLIND_INDEX_KEY="")
    def test_sem_chave_levanta_erro_de_configuracao(self):
        with self.assertRaises(ImproperlyConfigured):
            indice_cego("12345678909")

    @override_settings(BLIND_INDEX_KEY="curta")
    def test_chave_curta_levanta_erro_sem_expor_a_chave(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            indice_cego("12345678909")
        self.assertNotIn("curta", str(ctx.exception))