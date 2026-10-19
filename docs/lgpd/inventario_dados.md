# Inventário de dados coletados

Lista dos dados pessoais coletados pelo sistema e dos dados de segurança gerados por ele. Os módulos de Aluno e Responsável ainda não foram implementados. Quando um novo dado for coletado, ele será adicionado à tabela correspondente e a alteração será registrada no histórico ao final do documento.

Os dados e as finalidades foram definidos segundo o princípio da minimização, evitando a coleta de informações desnecessárias.

## Funcionário (usuário do sistema)

| Grupo | Dado | Titular | Finalidade | Acesso | Proteção |
| --- | --- | --- | --- | --- | --- |
| Identificação | nome | Funcionário | Identificação do colaborador | Gestão; próprio funcionário | Acesso controlado |
| Identificação | cpf | Funcionário | Identificação do colaborador | Gestão; próprio funcionário (mascarado) | Cifrado em repouso; índice HMAC para busca |
| Contato | telefone (opcional) | Funcionário | Comunicação institucional | Gestão; próprio funcionário (mascarado) | Cifrado em repouso |
| Contato | email | Funcionário (usuário) | Login e comunicação do sistema | Administradores do sistema; próprio funcionário | Acesso controlado |
| Profissional | cargo, setor | Funcionário | Controle de acesso e permissões | Gestão; administradores do sistema | Acesso controlado |
| Profissional | jornada (dia/hora) | Funcionário | Gestão administrativa da rotina | Gestão | Acesso controlado |

## Segurança e auditoria (gerados pelo sistema)

| Grupo | Dado | Titular | Finalidade | Acesso | Proteção |
| --- | --- | --- | --- | --- | --- |
| Credencial | senha | Funcionário (usuário) | Autenticação | Ninguém (não reversível) | Hash Argon2id com salt único |
| Credencial | chave secreta TOTP, status do 2FA, último uso, tentativas de código inválidas | Funcionário (usuário) | Autenticação em dois fatores | Sistema; o status é visível ao próprio funcionário | Chave cifrada em repouso |
| Controle de acesso | tentativas de login falhas, bloqueado até | Funcionário (usuário) | Proteção contra força bruta | Administradores do sistema | Acesso controlado |
| Recuperação de senha | hash do token, datas de criação, expiração e uso, IP e user-agent da solicitação | Funcionário (usuário) | Recuperação de senha e rastreabilidade | Administradores do sistema | Token armazenado somente como hash SHA-256 |
| Log de auditoria | tipo de evento, data e hora, resultado, IP, mensagem e detalhes do evento | Funcionário (usuário) | Auditoria, segurança e rastreabilidade | Administradores do sistema | Registros imutáveis |
| Log de auditoria | e-mail digitado em tentativas de login ou recuperação de senha com e-mail inexistente | Quem digitou o e-mail | Detecção de tentativas de acesso suspeitas | Administradores do sistema | Registros imutáveis |
| Consentimento | tipo, versão, decisão, data e hora, IP | Funcionário (usuário) | Comprovação do consentimento | Administradores do sistema; no navegador, o próprio titular | Registros imutáveis |

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

## Responsável

> Módulo ainda não implementado.

| Grupo | Dado | Titular | Finalidade | Acesso |
| --- | --- | --- | --- | --- |
| Identificação | nome, cpf | Responsável | Identificação / vínculo contratual | Gestão, Secretaria, Financeiro |
| Identificação | data_nascimento | Responsável | Validar maioridade para assumir responsabilidade legal | Gestão, Secretaria |
| Contato | telefone, endereco | Responsável | Comunicação / cobrança | Gestão, Financeiro |
| Financeiro | contrato, valores, desconto | Aluno (+ Responsável, quando aluno for menor de idade) | Gestão contratual | Financeiro/Fiscal, Gestão |
| Financeiro | cobranças, vencimento, pagamento | Aluno (+ Responsável, quando aluno for menor de idade) | Gestão de cobranças | Financeiro/Fiscal, Gestão |

## O que é excluído de fato (RLGPD 4.10)

Como a maioria dos dados do funcionário está protegida por vínculos técnicos (`on_delete=PROTECT`) ou é necessária para o funcionamento do sistema enquanto o vínculo estiver ativo, a exclusão hoje é parcial. A tela deixa isso explícito ao titular antes da confirmação.

| Dado | Pode ser excluído? | Motivo |
| --- | --- | --- |
| Telefone | Sim | Não possui vínculo com outros dados do sistema. |
| Nome, CPF | Não | Necessários para identificação funcional e obrigações trabalhistas enquanto o vínculo estiver ativo. |
| E-mail e senha da conta | Não | Necessários para o funcionamento do login; excluir inviabilizaria o acesso ao sistema. |
| Cargo | Não | Controla as permissões de acesso ao sistema. |
| Jornada de trabalho | Não | Dado administrativo vinculado ao funcionário enquanto estiver ativo. |

Toda solicitação de exclusão é registrada na auditoria (`usuarios/audit.py`, função `registrar_solicitacao_exclusao`), mesmo quando nenhum dado é efetivamente removido.

## Histórico de alterações

| Versão | Data | Alteração | Responsável |
|---|---|---|---|
| 1.0 | 12/09/2026 | Primeira versão do documento | Marcos Antônio Ferreira de Araújo |
| 1.1 | 12/09/2026 | Documentadas as funcionalidades de consulta, exportação e exclusão de dados (RLGPD 4.8, 4.9, 4.10) | Marcos Antônio Ferreira de Araújo |
| 1.2 | 18/10/2026 | Inclusão dos dados de segurança, auditoria e consentimento, da coluna de proteção (cifragem, hash) e do mascaramento na consulta | Marcos Antônio Ferreira de Araújo e Matheus de Castro Viana |