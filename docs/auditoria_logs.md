## Proteção por trigger no banco de dados (PostgreSQL)

**Requisito:** A tabela de logs de auditoria deve ser protegida no nível do banco de dados, impedindo alterações ou exclusões mesmo que alguém consiga burlar as camadas de aplicação.

### Decisão adotada

A proteção foi implementada no próprio PostgreSQL, com `migrations.RunSQL` na migration `usuarios.0013_bloquear_alteracao_logauditoria`, que cria:

1. **Função PL/pgSQL `usuarios_bloquear_alteracao_logauditoria()`**: dispara `RAISE EXCEPTION` sempre que é chamada.
2. **Trigger `usuarios_trigger_bloquear_alteracao_logauditoria`**: `BEFORE UPDATE OR DELETE OR TRUNCATE` em nível de statement (`FOR EACH STATEMENT`) na tabela `usuarios_logauditoria`, vinculado à função acima.

Com isso, qualquer `UPDATE`, `DELETE` ou `TRUNCATE` via SQL cru é recusado pelo banco, inclusive quando a instrução não afeta nenhuma linha. O `INSERT` continua permitido, pois é o que grava os novos logs. O `TRUNCATE` é coberto pelo próprio trigger de tabela, sem exigir privilégio de superusuário.

### Ajuste no campo `usuario` da model

O campo `usuario` de `LogAuditoria` usava `on_delete=models.SET_NULL`. Isso faria o Django executar um `UPDATE` na tabela de logs para zerar a chave estrangeira ao excluir um usuário, o que conflitaria com o trigger.

**Decisão:** o campo passou a usar `on_delete=models.PROTECT` (migration `usuarios.0014_alter_logauditoria_usuario`). Um usuário que possui logs não pode ser excluído: o Django recusa a operação com `ProtectedError`, e o histórico continua íntegro e vinculado ao usuário. O desligamento de um usuário deve ser feito por inativação, nunca por exclusão.

### Limitações de segurança

- O dono (owner) da tabela ou um superusuário do banco ainda pode executar `DROP TRIGGER` e remover a proteção. O trigger protege contra alterações acidentais ou maliciosas feitas por usuários comuns da aplicação, mas não substitui controles de acesso no nível do banco (revogação de privilégios, auditoria de superusuários).
- Como o `TRUNCATE` na tabela é bloqueado, comandos que esvaziam todas as tabelas, como `manage.py flush` e `TransactionTestCase`, também são bloqueados. O projeto usa apenas `TestCase`, que não é afetado.

### Simulação de erro ao tentar alterar a tabela

```sql
-- Tentativa de UPDATE via SQL cru
UPDATE usuarios_logauditoria SET mensagem = 'tentativa de alteracao' WHERE id = 1;
-- ERRO:  Operação não permitida na tabela usuarios_logauditoria: logs de auditoria são imutáveis.

-- Tentativa de DELETE via SQL cru
DELETE FROM usuarios_logauditoria WHERE id = 1;
-- ERRO:  Operação não permitida na tabela usuarios_logauditoria: logs de auditoria são imutáveis.

-- Tentativa de TRUNCATE via SQL cru
TRUNCATE TABLE usuarios_logauditoria;
-- ERRO:  Operação não permitida na tabela usuarios_logauditoria: logs de auditoria são imutáveis.
```

### Evidências

- **Código:** `usuarios/migrations/0013_bloquear_alteracao_logauditoria.py` (função e trigger via `migrations.RunSQL`).
- **Código:** `usuarios/models.py` (campo `usuario` de `LogAuditoria` com `on_delete=models.PROTECT`) e `usuarios/migrations/0014_alter_logauditoria_usuario.py`.
- **Teste:** `usuarios/test_trigger_logauditoria.py`, que dispara `UPDATE`, `DELETE` e `TRUNCATE` por SQL cru e exige a mensagem de bloqueio do banco, confere que novos logs ainda podem ser inseridos e que um usuário com logs não pode ser excluído.
- **Comando:** `python manage.py test usuarios.test_trigger_logauditoria -v 2`
---