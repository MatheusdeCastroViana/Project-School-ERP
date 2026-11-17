from django import forms
from django.test import SimpleTestCase

from config.campos import CampoCifrado
from config.criptografia import ErroDecifragem, decifrar
from config.test_criptografia import chaves, gerar_chave


def novo_campo(**kwargs):
    campo = CampoCifrado(**kwargs)
    campo.set_attributes_from_name("campo")
    return campo


class TipoEFormularioTests(SimpleTestCase):
    def test_tipo_interno_e_textfield(self):
        self.assertEqual(novo_campo().get_internal_type(), "TextField")

    def test_formfield_nao_usa_textarea(self):
        widget = novo_campo().formfield().widget
        self.assertIsInstance(widget, forms.TextInput)
        self.assertNotIsInstance(widget, forms.Textarea)


class CifraEDecifraTests(SimpleTestCase):
    def test_gravacao_cifra_o_valor(self):
        with chaves(gerar_chave()):
            token = novo_campo().get_prep_value("11999998888")
            self.assertNotEqual(token, "11999998888")
            self.assertNotIn("11999998888", token)
            self.assertEqual(decifrar(token), "11999998888")

    def test_ida_e_volta_pelos_ganchos(self):
        with chaves(gerar_chave()):
            campo = novo_campo()
            token = campo.get_prep_value("João Álvares")
            self.assertEqual(campo.from_db_value(token, None, None), "João Álvares")

    def test_none_passa_inalterado_nos_dois_sentidos(self):
        with chaves(gerar_chave()):
            campo = novo_campo()
            self.assertIsNone(campo.get_prep_value(None))
            self.assertIsNone(campo.from_db_value(None, None, None))

    def test_string_vazia_passa_inalterada_nos_dois_sentidos(self):
        with chaves(gerar_chave()):
            campo = novo_campo()
            self.assertEqual(campo.get_prep_value(""), "")
            self.assertEqual(campo.from_db_value("", None, None), "")

    def test_leitura_de_texto_puro_levanta_erro(self):
        with chaves(gerar_chave()):
            with self.assertRaises(ErroDecifragem):
                novo_campo().from_db_value("123.456.789-09", None, None)

    def test_to_python_nao_decifra(self):
        with chaves(gerar_chave()):
            campo = novo_campo()
            token = campo.get_prep_value("segredo")
            self.assertEqual(campo.to_python(token), token)
            self.assertEqual(campo.to_python("segredo"), "segredo")
            self.assertIsNone(campo.to_python(None))


class LookupsTests(SimpleTestCase):
    def test_lookups_de_comparacao_sao_proibidos(self):
        campo = novo_campo()
        for nome in ("exact", "iexact", "in", "contains", "icontains",
                     "startswith", "gt", "lt", "gte", "lte", "regex"):
            with self.subTest(lookup=nome):
                self.assertIsNone(campo.get_lookup(nome))

    def test_isnull_continua_permitido(self):
        self.assertIsNotNone(novo_campo().get_lookup("isnull"))


class ChecksTests(SimpleTestCase):
    def test_configuracao_padrao_nao_tem_erros(self):
        self.assertEqual(novo_campo().check(), [])

    def test_unique_gera_erro(self):
        ids = [e.id for e in novo_campo(unique=True).check()]
        self.assertIn("campo_cifrado.E001", ids)

    def test_db_index_gera_erro(self):
        ids = [e.id for e in novo_campo(db_index=True).check()]
        self.assertIn("campo_cifrado.E002", ids)