from django.test import TestCase, override_settings
from django.db import connection
from usuarios.models import LogAuditoria


@override_settings(DEBUG=False)
class TriggerLogAuditoriaImutabilidadeTest(TestCase):
    """Valida que o trigger do PostgreSQL bloqueia UPDATE, DELETE e TRUNCATE
    na tabela usuarios_logauditoria, mesmo quando disparado via SQL cru."""

    def setUp(self):
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
        with self.assertRaises(Exception) as ctx:
            self._executar_sql_cru(
                "UPDATE usuarios_logauditoria SET mensagem = 'tentativa de alteracao' WHERE id = %s",
                [self.log.id],
            )
        self.assertIn('não permitida', str(ctx.exception))

    def test_bloqueia_delete_via_sql_cru(self):
        with self.assertRaises(Exception) as ctx:
            self._executar_sql_cru(
                "DELETE FROM usuarios_logauditoria WHERE id = %s",
                [self.log.id],
            )
        self.assertIn('não permitida', str(ctx.exception))

    def test_bloqueia_truncate_via_sql_cru(self):
        with self.assertRaises(Exception) as ctx:
            self._executar_sql_cru("TRUNCATE TABLE usuarios_logauditoria;")
        mensagem = str(ctx.exception)
        self.assertTrue(
            'TRUNCATE' in mensagem and ('não permitida' in mensagem or 'gatilho pendentes' in mensagem or 'pendentes' in mensagem),
            f"Esperava erro de bloqueio de TRUNCATE, recebeu: {mensagem}",
        )
