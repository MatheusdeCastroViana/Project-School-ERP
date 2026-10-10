from django.contrib.auth import get_user_model
from django.core.exceptions import FieldError, ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from config.criptografia import decifrar, indice_cego
from config.test_criptografia import chaves, gerar_chave
from funcionarios.models import Funcionario

Usuario = get_user_model()

PREFIXO_TOKEN = "gAAAA"
CHAVE_INDICE = "c" * 40
CPF = "123.456.789-09"
CPF_SEM_MASCARA = "12345678909"


def tabela():
    return connection.ops.quote_name(Funcionario._meta.db_table)


def ler_cru(pk, coluna):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {coluna} FROM {tabela()} WHERE id = %s", [pk])
        return cursor.fetchone()[0]


@override_settings(BLIND_INDEX_KEY=CHAVE_INDICE)
class FuncionarioCifradoNoBancoTests(TestCase):
    def setUp(self):
        self.enterContext(chaves(gerar_chave()))
        self.funcionario = Funcionario.objects.create(
            nome="Ana Souza", cpf=CPF, telefone="11999998888"
        )

    def test_cpf_e_telefone_estao_cifrados_no_banco(self):
        for coluna, original in (("cpf", CPF), ("telefone", "11999998888")):
            with self.subTest(coluna=coluna):
                cru = ler_cru(self.funcionario.pk, coluna)
                self.assertTrue(cru.startswith(PREFIXO_TOKEN))
                self.assertNotIn(original, cru)
                self.assertEqual(decifrar(cru), original)

    def test_leitura_pelo_model_devolve_os_valores_originais(self):
        recarregado = Funcionario.objects.get(pk=self.funcionario.pk)
        self.assertEqual(recarregado.cpf, CPF)
        self.assertEqual(recarregado.telefone, "11999998888")

    def test_indice_e_gravado_a_partir_do_cpf_normalizado(self):
        esperado = indice_cego(CPF_SEM_MASCARA)
        self.assertEqual(ler_cru(self.funcionario.pk, "cpf_indice"), esperado)

    def test_indice_nao_contem_o_cpf(self):
        indice = ler_cru(self.funcionario.pk, "cpf_indice")
        self.assertNotIn(CPF_SEM_MASCARA, indice)

    def test_telefone_vazio_continua_vazio_no_banco(self):
        outro = Funcionario.objects.create(nome="Sem Fone", cpf="987.654.321-00")
        self.assertEqual(ler_cru(outro.pk, "telefone"), "")

    def test_limpar_telefone_como_na_exclusao_lgpd(self):
        self.funcionario.telefone = ""
        self.funcionario.save(update_fields=["telefone"])
        self.assertEqual(ler_cru(self.funcionario.pk, "telefone"), "")
        self.assertEqual(ler_cru(self.funcionario.pk, "cpf_indice"), indice_cego(CPF_SEM_MASCARA))

    def test_salvar_de_novo_nao_cifra_duas_vezes(self):
        carregado = Funcionario.objects.get(pk=self.funcionario.pk)
        carregado.nome = "Ana Souza Lima"
        carregado.save()
        self.assertEqual(decifrar(ler_cru(self.funcionario.pk, "cpf")), CPF)

    def test_alterar_cpf_atualiza_o_indice(self):
        self.funcionario.cpf = "987.654.321-00"
        self.funcionario.save(update_fields=["cpf"])
        self.assertEqual(
            ler_cru(self.funcionario.pk, "cpf_indice"), indice_cego("98765432100")
        )

    def test_filtro_direto_pelo_cpf_e_proibido(self):
        with self.assertRaises(FieldError):
            list(Funcionario.objects.filter(cpf=CPF))


@override_settings(BLIND_INDEX_KEY=CHAVE_INDICE)
class BuscaEUnicidadePorCpfTests(TestCase):
    def setUp(self):
        self.enterContext(chaves(gerar_chave()))
        self.funcionario = Funcionario.objects.create(nome="Ana Souza", cpf=CPF)

    def test_por_cpf_encontra_com_e_sem_mascara(self):
        self.assertEqual(Funcionario.objects.por_cpf(CPF).get(), self.funcionario)
        self.assertEqual(
            Funcionario.objects.por_cpf(CPF_SEM_MASCARA).get(), self.funcionario
        )

    def test_por_cpf_nao_encontra_cpf_inexistente(self):
        self.assertFalse(Funcionario.objects.por_cpf("000.000.000-00").exists())

    def test_banco_recusa_cpf_duplicado_mesmo_com_formatacao_diferente(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Funcionario.objects.create(nome="Outra", cpf=CPF_SEM_MASCARA)

    def test_validacao_do_formulario_recusa_cpf_duplicado(self):
        duplicado = Funcionario(nome="Outra", cpf=CPF_SEM_MASCARA)
        with self.assertRaises(ValidationError) as ctx:
            duplicado.full_clean(exclude=["cpf_indice"])
        self.assertIn("cpf", ctx.exception.message_dict)

    def test_validacao_aceita_o_proprio_registro(self):
        self.funcionario.full_clean(exclude=["cpf_indice"])

    def test_validacao_mantem_limite_de_tamanho_do_cpf(self):
        longo = Funcionario(nome="Longo", cpf="1" * 15)
        with self.assertRaises(ValidationError) as ctx:
            longo.full_clean(exclude=["cpf_indice"])
        self.assertIn("cpf", ctx.exception.message_dict)

    def test_validacao_mantem_limite_de_tamanho_do_telefone(self):
        longo = Funcionario(nome="Longo", cpf="987.654.321-00", telefone="1" * 12)
        with self.assertRaises(ValidationError) as ctx:
            longo.full_clean(exclude=["cpf_indice"])
        self.assertIn("telefone", ctx.exception.message_dict)


@override_settings(BLIND_INDEX_KEY=CHAVE_INDICE)
class TelasLgpdComDadosCifradosTests(TestCase):
    def setUp(self):
        self.enterContext(chaves(gerar_chave()))
        funcionario = Funcionario.objects.create(
            nome="Carla Dias", cpf="555.555.555-55", telefone="11977776666"
        )
        self.usuario = Usuario.objects.create_user(
            email="carla@exemplo.com", password="SenhaTeste123!", funcionario=funcionario
        )
        self.client.force_login(self.usuario)

    def test_consulta_de_dados_mostra_cpf_e_telefone_originais(self):
        resposta = self.client.get(reverse("usuarios:consultar_dados"))
        self.assertContains(resposta, "555.555.555-55")
        self.assertContains(resposta, "11977776666")

    def test_exportacao_contem_cpf_e_telefone_originais(self):
        resposta = self.client.get(reverse("usuarios:exportar_dados"))
        self.assertContains(resposta, "555.555.555-55")
        self.assertContains(resposta, "11977776666")
        self.assertNotContains(resposta, PREFIXO_TOKEN)