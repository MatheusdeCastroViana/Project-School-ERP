# Documentação - Módulo de Auditoria e Logs

**Projeto:** ERP Escola Profissionalizante  
**Autores:** Marcos Antônio Ferreira de Araújo e Matheus de Castro Viana  
**Versão do Documento de Requisitos:** 1.1  
**Data da implementação:** 20 de setembro de 2026  
**Entrega:** Projeto Integrador — Auditoria e Logs  

---

## Introdução

O módulo de Auditoria e Logs foi projetado para garantir a rastreabilidade, a responsabilização e a detecção de incidentes de segurança no sistema ERP Escola Profissionalizante. Em sua versão final, o sistema migrou do registro em arquivos de texto para uma **tabela dedicada no banco de dados PostgreSQL** (`usuarios_logauditoria`), o que permite consultas relacionais, filtros avançados e maior integridade dos dados.

A lógica de geração de logs foi centralizada no arquivo `usuarios/audit.py`, garantindo que todos os eventos críticos sejam registrados de forma padronizada, sem expor dados sensíveis.

---

## Logs de autenticação registrados

**Requisito:** O sistema deverá registrar logs de autenticação, incluindo sucesso, falha, logout, bloqueio e eventos relevantes de sessão.

### Decisão adotada

Foi criado o modelo `LogAuditoria` no banco de dados, contendo os campos:
- `usuario` (ForeignKey para o modelo de usuário, permitindo nulo para tentativas de login com e-mail inexistente).
- `tipo_evento` (CharField com escolhas pré-definidas: `login`, `logout`, `login_falha`, `login_bloqueado`, etc.).
- `data_hora` (DateTimeField com preenchimento automático no momento da criação).
- `ip_address` (GenericIPAddressField para registrar a origem da requisição).
- `sucesso` (BooleanField indicando o resultado da operação).

A função `registrar_evento_autenticacao` no arquivo `usuarios/audit.py` é invocada automaticamente pelo `UsuarioBackend` (durante o login) e pela view `logout_usuario` (durante o encerramento de sessão).

### Justificativa técnica

O registro centralizado no banco de dados, em vez de arquivos de texto soltos, atende ao princípio de **integridade e disponibilidade** da informação. O uso de `GenericIPAddressField` e a indexação do campo `data_hora` otimizam as consultas forenses, permitindo que administradores filtrem rapidamente eventos por período ou origem de rede.

### Evidências

- **Código:** `usuarios/models.py` (Modelo `LogAuditoria`), `usuarios/audit.py` (Função `registrar_evento_autenticacao`).
- **Print:** `docs/evidencias/logs_registrados.png` (Tela do admin mostrando a grade de logs com diferentes tipos de eventos de autenticação).

---

## Logs de falhas e 2FA sem expor dados sensíveis

**Requisito:** O sistema deverá registrar logs de falhas de autenticação e eventos relacionados ao 2FA, sem registrar senhas ou códigos completos.

### Decisão adotada

Em estrita conformidade com a **Regra de Negócio RN-10** (*"Credenciais, tokens completos e códigos 2FA não deverão ser registrados em logs"*), as funções `registrar_evento_2fa` e `registrar_evento_recuperacao_senha` foram implementadas para registrar apenas o **contexto** da falha, e nunca o segredo em si.

Exemplo de log gerado em caso de falha no 2FA:
> `"Evento 2FA | Usuário: teste@email.com | Evento: verificacao_falha | Sucesso: False | IP: 127.0.0.1 | Detalhes: Token inválido"`

O campo `detalhes` (JSONField) é utilizado para armazenar metadados adicionais (como "Token expirado" ou "Senha incorreta"), mas o sistema possui travas lógicas que impedem o salvamento de strings contendo os códigos TOTP de 6 dígitos ou os tokens de recuperação de senha.

### Justificativa técnica

A exposição de códigos 2FA ou tokens de recuperação em logs representaria uma vulnerabilidade crítica . Ao registrar apenas o resultado booleano e uma mensagem genérica de erro, o sistema mantém sua capacidade de auditoria sem comprometer a confidencialidade das credenciais, mesmo que um atacante obtenha acesso de leitura ao banco de dados de logs.

### Evidências

- **Código:** `usuarios/audit.py` (Funções `registrar_evento_2fa` e `registrar_resultado_recuperacao_senha`).
- **Print:** `docs/evidencias/logs_registrados.png`.

---

## Proteção contra alteração dos logs

**Requisito:** Os logs deverão possuir proteção contra alteração ou exclusão indevida, por meio de controle de acesso, armazenamento protegido, integridade ou mecanismo equivalente.

### Decisão adotada

A interface de visualização dos logs no Django Admin (`LogAuditoriaAdmin`) foi rigidamente configurada para garantir a **imutabilidade** dos registros:

1. **Bloqueio de Criação Manual:** Logs só podem ser gerados pelo código da aplicação.
2. **Bloqueio de Edição:** Nenhum usuário, incluindo superusuários, pode alterar o conteúdo de um log existente.
3. **Bloqueio de Exclusão:** A exclusão de logs é proibida para preservar o histórico forense.
4. **Campos Somente Leitura:** Todos os campos do da lista de detalhes estão bloqueados para edição.

### Justificativa técnica

A imutabilidade dos logs é um pilar fundamental da segurança da informação e da conformidade com normas e a LGPD. Ao impedir que administradores do sistema apaguem ou editem logs, o ERP garante que, em caso de investigação de um incidente interno ou externo, as evidências permaneçam intactas e confiáveis.

### Evidências

- **Código:** `usuarios/admin.py` (Classe `LogAuditoriaAdmin` e sobrescrita dos métodos de permissão).
- **Print:** `docs/evidencias/logs_registrados.png`.

---

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

## Exemplo de análise de logs apresentado

**Requisito:** O projeto deverá apresentar um exemplo de análise de logs, demonstrando como identificar uma sequência de falhas, um bloqueio ou uma tentativa de acesso suspeita.

### Decisão adotada

O painel administrativo foi estruturado para funcionar como uma ferramenta de análise forense, utilizando os recursos nativos do Django Admin:
- **Filtro por Usuário:** Dropdown lateral para isolar a atividade de um usuário específico.
- **Filtro por Tipo de Evento:** Permite visualizar apenas "Falha de Login" ou "Login Bloqueado".
- **Filtro por Sucesso:** Isola tentativas mal-sucedidas.
- **Filtro por IP:** Campo de pesquisa para rastrear acessos de origens suspeitas.

## Histórico de alterações

| Versão | Data | Alteração | Responsável |
|---|---|---|---|
| 1.0 | 20/09/2026 | Primeira versão do documento | Marcos Antônio Ferreira de Araújo e Matheus de Castro Viana |
| 1.1 | 03/11/2026 | Proteção por trigger no banco de dados | Marcos Antônio Ferreira de Araújo |

---