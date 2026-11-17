from django.contrib.auth import get_user_model
from django.db import DatabaseError, connection
from django.db.models import ProtectedError
from django.test import TestCase, override_settings

from config.test_criptografia import chaves, gerar_chave
from funcionarios.models import Funcionario
from usuarios.models import LogAuditoria

Usuario = get_user_model()


@override_settings(BLIND_INDEX_KEY="c" * 40)
class TriggerLogAuditoriaImutabilidadeTest(TestCase):
    """Valida que o trigger do PostgreSQL bloqueia UPDATE, DELETE e TRUNCATE
    na tabela usuarios_logauditoria, mesmo quando disparado via SQL cru."""

    def setUp(self):
        self.enterContext(chaves(gerar_chave()))
        self.log = LogAuditoria.objects.create(
            usuario=None,
            tipo_evento='login',
            ip_address='127.0.0.1',
            user_agent='teste',
            sucesso=True,
            detalhes={},
            mensagem='Log de teste para trigger de imutabilidade.',
        )

    def _executar_sql_cru(self, sql, params=None):
        with connection.cursor() as cursor:
            cursor.execute(sql, params or [])

    def test_bloqueia_update_via_sql_cru(self):
        with self.assertRaisesMessage(DatabaseError, 'imutáveis'):
            self._executar_sql_cru(
                "UPDATE usuarios_logauditoria SET mensagem = 'tentativa de alteracao' WHERE id = %s",
                [self.log.id],
            )

    def test_bloqueia_delete_via_sql_cru(self):
        with self.assertRaisesMessage(DatabaseError, 'imutáveis'):
            self._executar_sql_cru(
                "DELETE FROM usuarios_logauditoria WHERE id = %s",
                [self.log.id],
            )

    def test_bloqueia_truncate_via_sql_cru(self):
        self._executar_sql_cru("SET CONSTRAINTS ALL IMMEDIATE")
        with self.assertRaisesMessage(DatabaseError, 'imutáveis'):
            self._executar_sql_cru("TRUNCATE TABLE usuarios_logauditoria")

    def test_permite_inserir_novos_logs(self):
        LogAuditoria.objects.create(
            usuario=None,
            tipo_evento='login',
            ip_address='127.0.0.1',
            user_agent='teste',
            sucesso=True,
            detalhes={},
            mensagem='Novo log depois do trigger.',
        )
        self.assertEqual(LogAuditoria.objects.count(), 2)

    def test_usuario_com_log_nao_pode_ser_apagado(self):
        funcionario = Funcionario.objects.create(
            nome="Ana Souza", cpf="123.456.789-09", telefone="11987654321"
        )
        usuario = Usuario.objects.create_user(
            email="ana@exemplo.com", password="SenhaTeste123!", funcionario=funcionario
        )
        LogAuditoria.objects.create(
            usuario=usuario,
            tipo_evento='login',
            ip_address='127.0.0.1',
            user_agent='teste',
            sucesso=True,
            detalhes={},
            mensagem='Log vinculado a um usuario.',
        )
        with self.assertRaises(ProtectedError):
            usuario.delete()