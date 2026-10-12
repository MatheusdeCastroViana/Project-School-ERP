# Documentação — Criptografia de Dados em Repouso

**Projeto:** ERP Escola Profissionalizante 
**Autores:** Marcos Antônio Ferreira de Araújo e Matheus de Castro Viana 
**Versão do Documento de Requisitos:** 1.1
**Data da implementação:** 12 de outubro de 2026  
**Entrega:** Projeto Integrador — Criptografia de Dados  

---

## Criptografia de Campos Sensíveis

**Requisito:** O sistema deverá garantir a confidencialidade dos dados em repouso no banco de dados.

### Decisão adotada
Foi implementado um sistema de encriptação utilizando os mecanismos configurados no ficheiro `config/criptografia.py`. Para integrar isto diretamente nos modelos de dados, foram definidos campos personalizados no ficheiro `config/campos.py`. Adicionalmente, as migrações `0008_cifrar_cpf_telefone.py` (na aplicação `funcionarios`) e `0007_cifrar_chave_secreta.py` (na aplicação `usuarios`) foram criadas para cifrar automaticamente os dados legíveis pré-existentes.

### Justificativa técnica
A encriptação dos dados em repouso é fundamental para proteger informações pessoais e chaves de segurança. Mesmo que ocorra uma fuga de dados, as informações permanecerão inacessíveis aos atacantes.

### Evidências
- **Código-fonte:** Ficheiros `config/criptografia.py` e `config/campos.py`.
- **Testes:** Validados através de testes automatizados nos ficheiros `config/test_criptografia.py`, `funcionarios/test_cifrado.py` e `usuarios/test_2fa_cifrado.py`.

---

## Índice Cego para Buscas em Campos Cifrados

**Requisito:** O sistema deverá permitir a realização de buscas eficientes (como a pesquisa por CPF) sem a necessidade de decifrar toda a tabela.

### Decisão adotada
Foi desenvolvida e integrada a lógica de índice cego (Blind Index), validada através do ficheiro `config/test_indice_cego.py`. Este processo é suportado pelas migrações recentes do modelo de Funcionário (como a `0007_funcionario_cpf_indice_alter_funcionario_cpf_and_more.py` e a `0009_alter_funcionario_cpf_alter_funcionario_cpf_indice_and_more.py`), que alocam colunas de índice dedicadas.

### Justificativa técnica
O índice cego resolve o problema de pesquisa em campos cifrados não determinísticos através da geração de um hash determinístico unidirecional, equilibrando alta performance de busca com segurança rigorosa.

### Evidências
- **Código e Testes:** Ficheiros de teste `config/test_indice_cego.py` e respectivo histórico de migrações da aplicação de funcionários.

---

## Histórico de alterações

| Versão | Data | Alteração | Responsável |
|---|---|---|---|
| 1.0 | 12/10/2026 | Criptografia dos dados em repouso | Marcos Antônio Ferreira de Araújo |