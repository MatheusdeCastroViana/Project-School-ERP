# Inventário de dados coletados

Lista dos dados coletados dos usuários do sistema. Alguns módulos ainda não foram implementados, portanto, este documento poderá ser atualizado conforme o desenvolvimento do sistema avançar. Sempre que um novo dado precisar ser coletado, ele será adicionado à tabela correspondente, e a alteração será registrada na tabela de alterações ao final do documento.

Os dados coletados e suas finalidades foram definidos com o objetivo de aplicar o princípio da minimização de dados, evitando a coleta de informações desnecessárias.


## Funcionário (Usuário)

| Grupo | Dado | Titular | Finalidade | Acesso |
| --- | --- | --- | --- | --- |
| Identificação | nome, cpf | Funcionário | Identificação do colaborador | Gestão; própio funcionário |
| Contato | telefone | Funcionário | Comunicação institucional | Gestão; próprio funcionário |
| Profissional | cargo_id | Funcionário | Controle de acesso e permissões | Gestão; Administradores do sistema |
| Profissional | jornada (dia/hora) | Funcionário | Gestão administrativa da rotina | Gestão|
| Logs de Segurança | email, funcionario_id, ativo, 2fa_ativo | Funcionário (usuário) | Autenticação e controle de acesso | Administradores do sistema; próprio funcionário |
| Logs de Segurança | tipo_evento, ip, data_hora | Funcionário (usuário) | Auditoria e rastreabilidade  | Administradores do sistema |
| Logs de Segurança | usuario_id, token_hash, datas, usado | Funcionário (usuário) | Recuperação de senha | Administradores do sistema |

## Aluno

> Módulo ainda não implementado.

| Grupo | Dado | Titular | Finalidade | Acesso |
| --- | --- | --- | --- | --- |
| Identificação | nome, cpf | Aluno | Identificação do titular / contrato | Gestão, Secretaria, setores autorizados |
| Identificação | apelido | Aluno | Uso pedagógico (chamada em sala) | Pedagógico, professores vinculados |
| Contato | telefone, endereco | Aluno | Comunicação / entrega de material | Gestão, Administrativo, setores autorizados |
| Contato | email | Aluno | Login no portal do aluno / comunicação | Aluno (autoconsulta), Gestão, Administrativo |
| Acadêmico | data_nascimento | Aluno | Validar maioridade e idade mínima para a turma | Gestão, Secretaria |
| Acadêmico | matrícula, situação, notas | Aluno | Gestão da vida acadêmica | Pedagógico, professores vinculados, Gestão |
| Financeiro | contrato, valores, desconto | Aluno (+ Responsável, quando aluno for menor de idade) | Gestão contratual | Financeiro/Fiscal, Gestão |
| Financeiro | cobranças, vencimento, pagamento | Aluno (+ Responsável, quando aluno for menor de idade) | Gestão de cobranças | Financeiro/Fiscal, Gestão |

> Observação: O portal do aluno será um sistema à parte, integrado à este sistema.

## Responsável

> Módulo ainda não implementado.

| Grupo | Dado | Titular | Finalidade | Acesso |
| --- | --- | --- | --- | --- |
| Identificação | nome, cpf | Responsável | Identificação / vínculo contratual | Gestão, Secretaria, Financeiro |
| Identificação | data_nascimento | Responsável | Validar maioridade para assumir responsabilidade legal | Gestão, Secretaria |
| Contato | telefone, endereco | Responsável | Comunicação / cobrança | Gestão, Financeiro |
| Financeiro | contrato, valores, desconto | Aluno (+ Responsável, quando aluno for menor de idade) | Gestão contratual | Financeiro/Fiscal, Gestão |
| Financeiro | cobranças, vencimento, pagamento | Aluno (+ Responsável, quando aluno for menor de idade) | Gestão de cobranças | Financeiro/Fiscal, Gestão |

## Histórico de alterações

| Versão | Data | Alteração | Responsável |
|---|---|---|---|
| 1.0 | 12/09/2026 | Primeira versão do documento | Marcos Antônio Ferreira de Araújo |