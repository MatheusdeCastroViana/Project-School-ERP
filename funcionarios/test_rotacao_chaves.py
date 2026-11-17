from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth import get_user_model

from config.criptografia import cifrar, decifrar, ErroDecifragem, indice_cego
from config.test_criptografia import chaves, gerar_chave
from funcionarios.models import Funcionario, Setor, Cargo, somente_digitos
from usuarios.models_2fa import Configuracao2FA


class RotacaoChavesTests(TestCase):
    """Teste do Item 3.7: rotacao de chaves.

    Cifra com a chave antiga, roda o comando de rotacao e confere que
    depois so a chave nova consegue decifrar.
    """

    def setUp(self):
        self.chave_antiga = gerar_chave()
        self.chave_nova = gerar_chave()

        self.setor = Setor.objects.create(nome="Administrativo")
        self.cargo = Cargo.objects.create(nome="Estagiario", setor=self.setor)

        # Cifra os dados com a chave antiga (simulando dados ja existentes)
        with chaves(self.chave_antiga):
            self.funcionario = Funcionario.objects.create(
                nome="Ana Silva",
                cpf=cifrar("12345678900"),
                telefone=cifrar("11999998888"),
                cargo=self.cargo,
                ativo=True,
            )

        Usuario = get_user_model()
        self.usuario = Usuario.objects.create_user(
            email="ana@exemplo.com",
            password="senha123",
            funcionario=self.funcionario,
        )

        with chaves(self.chave_antiga):
            self.totp = Configuracao2FA.objects.create(
                usuario=self.usuario,
                chave_secreta=cifrar("SECRETO123456"),
                ativado=True,
            )

    def _decifra_com(self, lista_chaves, texto_cifrado):
        with chaves(*lista_chaves):
            return decifrar(texto_cifrado)

    def test_depois_de_rotacionar_decifra_somente_com_chave_nova(self):
        # --- PRE-CONDICAO: dados so decifram com a chave antiga ---
        with chaves(self.chave_antiga):
            f = Funcionario.objects.get(pk=self.funcionario.pk)
            self.assertEqual(
                self._decifra_com([self.chave_antiga], f.cpf), "12345678900"
            )
            self.assertEqual(
                self._decifra_com([self.chave_antiga], f.telefone), "11999998888"
            )
            totp = Configuracao2FA.objects.get(pk=self.totp.pk)
            self.assertEqual(
                self._decifra_com([self.chave_antiga], totp.chave_secreta),
                "SECRETO123456",
            )

            # com a chave nova sozinha, nada deve decifrar ainda
            with self.assertRaises(ErroDecifragem):
                self._decifra_com([self.chave_nova], f.cpf)
            with self.assertRaises(ErroDecifragem):
                self._decifra_com([self.chave_nova], totp.chave_secreta)

        # --- ROTACAO: roda o comando com [nova, antiga] ---
        with chaves(self.chave_nova, self.chave_antiga):
            call_command("rotacionar_chaves")

        # --- POS-CONDICAO: dados so decifram com a chave nova ---
        with chaves(self.chave_nova, self.chave_antiga):
            f = Funcionario.objects.get(pk=self.funcionario.pk)
            self.assertEqual(
                self._decifra_com([self.chave_nova], f.cpf), "12345678900"
            )
            self.assertEqual(
                self._decifra_com([self.chave_nova], f.telefone), "11999998888"
            )
            totp = Configuracao2FA.objects.get(pk=self.totp.pk)
            self.assertEqual(
                self._decifra_com([self.chave_nova], totp.chave_secreta), "SECRETO123456"
            )

            # com a chave antiga sozinha, nada deve decifrar mais
            with self.assertRaises(ErroDecifragem):
                self._decifra_com([self.chave_antiga], f.cpf)
            with self.assertRaises(ErroDecifragem):
                self._decifra_com([self.chave_antiga], totp.chave_secreta)

            # cpf_indice deve bater com o indice do cpf decifrado com a chave nova
            cpf_decifrado = self._decifra_com([self.chave_nova], f.cpf)
            self.assertEqual(
                f.cpf_indice, indice_cego(somente_digitos(cpf_decifrado))
            )

            # busca por CPF deve funcionar apos a rotacao
            encontrado = Funcionario.objects.por_cpf("12345678900")
            self.assertTrue(encontrado.exists())
            self.assertEqual(encontrado.first().pk, self.funcionario.pk)
