# Dados coletados

Inventário dos dados coletados.


## Funcionário

Grupo |	Dado | Titular | Finalidade|
| --- | --- | --- | --- |
Identificação	| nome, cpf	| Funcionário	| Identificação do colaborador (RF-02) |
Contato	| telefone |	Funcionário |	Comunicação | institucional |
Profissional	| cargo_id	| Funcionário	| Controle de acesso e permissões (RF-03, RF-04)| 
Profissional	| jornada (dia/hora)	| Funcionário	| Gestão administrativa da rotina |
Log Segurança	| email, funcionario_id, ativo, 2fa_ativo | Funcionário (usuário)	| Autenticação e controle de acesso |
Log Segurança	| tipo_evento, ip, data_hora	| Funcionário (usuário)	| Auditoria e rastreabilidade (RS 2.6/2.7) |
Log Segurança	| usuario_id, token_hash, datas, usado	| Funcionário (usuário)	| Recuperação de senha (RS 2.1–2.7) |

## Aluno

Módulo ainda não implementado.

Dado	| Titular	| Finalidade	| Grupo |
| --- | --- | --- | --- |
nome, cpf	| Aluno	| Identificação do titular / contrato	| Identificação |
apelido| 	Aluno	| Uso pedagógico (chamada em sala)	| Identificação |
telefone, endereco	| Aluno	| Comunicação / entrega de material	| Contato|
email	| Aluno	| Login no portal do aluno / comunicação	| Contato|
data_nascimento	| Aluno	| Validar maioridade e idade mínima para a turma	| Acadêmico|
matrícula, situação, notas	| Aluno	| Gestão da vida acadêmica	| Acadêmico|
contrato, valores, desconto	| Aluno (+ Responsável, quando aluno for menor de idade)	| Gestão contratual	| Financeiro|
cobranças, vencimento, pagamento	| Aluno (+ Responsável, quando aluno for menor de idade)	| Gestão de cobranças	| Financeiro|

## Responsável

Módulo ainda não implementado.

Dado	| Titular	| Finalidade	| Grupo |
| --- | --- | --- | --- |
nome, cpf	| Responsável	| Identificação / vínculo contratual	| Identificação|
data_nascimento	| Responsável	| Validar maioridade para assumir responsabilidade legal	| Identificação|
telefone, endereco	| Responsável	| Comunicação / cobrança	| Contato|
contrato, valores, desconto	| Aluno (+ Responsável, quando aluno for menor de idade)	| Gestão contratual	| Financeiro|
cobranças, vencimento, pagamento	| Aluno (+ Responsável, quando aluno for menor de idade)	| Gestão de cobranças	| Financeiro|
