# Documentação — Criptografia de Dados em Repouso

**Projeto:** ERP Escola Profissionalizante 
**Autores:** Marcos Antônio Ferreira de Araújo e Matheus de Castro Viana 
**Versão do Documento de Requisitos:** 1.1
**Data da implementação:** 12 de outubro de 2026  
**Entrega:** Projeto Integrador — Criptografia de Dados  

---

## Algoritmo, Modo e Biblioteca (Requisitos 3.5 e 3.6)

**Requisito:** O sistema deverá garantir a confidencialidade e a integridade dos dados em repouso no banco de dados utilizando criptografia forte.

### Decisão adotada
Foi implementado um sistema de criptografia utilizando os mecanismos configurados no arquivo `config/criptografia.py`. O sistema utiliza o algoritmo **Fernet**, que implementa internamente o **AES-128 no modo CBC (Cipher Block Chaining)** em conjunto com assinatura **HMAC-SHA256**. 

Para integrar isso diretamente nos modelos de dados, foram definidos campos personalizados no arquivo `config/campos.py`. Adicionalmente, as migrações `0008_cifrar_cpf_telefone.py` (na aplicação `funcionarios`) e `0007_cifrar_chave_secreta.py` (na aplicação `usuarios`) foram criadas para cifrar automaticamente os dados legíveis preexistentes.

### Justificativa técnica
O uso do Fernet (AES-128-CBC + HMAC-SHA256) oferece criptografia autenticada. A criptografia dos dados em repouso é fundamental para proteger informações pessoais e chaves de segurança. Mesmo que ocorra um vazamento de dados, as informações permanecerão inacessíveis e inalteráveis aos atacantes.

### Evidências
- **Inspeção do algoritmo, modo e biblioteca:** Código-fonte nos arquivos `config/criptografia.py` e `config/campos.py`.
- **Testes:** Validados por meio de testes automatizados nos arquivos `config/test_criptografia.py`, `funcionarios/test_cifrado.py` e `usuarios/test_2fa_cifrado.py`.

---

## Gestão e Ciclo de Vida das Chaves Criptográficas (Requisitos 3.7 e 3.8)

**Requisito:** O sistema deverá isolar o armazenamento das chaves criptográficas do código-fonte e gerenciar de forma segura o seu ciclo de vida.

### Decisão adotada
As chaves criptográficas utilizadas pelo algoritmo Fernet não são fixadas no código-fonte nem armazenadas no banco de dados. Elas ficam armazenadas e são injetadas na aplicação exclusivamente por meio de **variáveis de ambiente**. 

O ciclo de vida das chaves inclui suporte à rotação segura (*Key Rotation*). A biblioteca permite configurar múltiplas chaves simultâneas (em formato de lista nas variáveis de ambiente), de modo que a chave mais recente é utilizada para cifrar novos dados, enquanto as chaves antigas são mantidas para permitir a decifragem de registros anteriores, garantindo que nenhum dado seja perdido durante o processo de atualização.

### Justificativa técnica
Manter as chaves em variáveis de ambiente atende às boas práticas de segurança (como os preceitos do *12-Factor App*), impedindo a exposição de segredos em sistemas de controle de versão. A rotação de chaves permite a mitigação rápida de danos caso haja suspeita de comprometimento de alguma chave antiga.

### Evidências
- **Inspeção de variáveis de ambiente:** Arquivo `.env` (não versionado) e rotinas de inicialização/leitura no projeto (`settings.py` / `config/criptografia.py`).

---

## Índice Cego para Buscas em Campos Cifrados

**Requisito:** O sistema deverá permitir a realização de buscas eficientes (como a pesquisa por CPF) sem a necessidade de decifrar toda a tabela.

### Decisão adotada
Foi desenvolvida e integrada a lógica de índice cego (*Blind Index*), validada pelo arquivo `config/test_indice_cego.py`. Esse processo é suportado pelas migrações recentes do modelo de Funcionário (como a `0007_funcionario_cpf_indice_alter_funcionario_cpf_and_more.py` e a `0009_alter_funcionario_cpf_alter_funcionario_cpf_indice_and_more.py`), que alocam colunas de índice dedicadas.

### Justificativa técnica
Como o Fernet gera uma saída não determinística (cifrar o mesmo texto duas vezes gera resultados diferentes), a pesquisa direta no banco se torna inviável. O índice cego resolve esse problema por meio da geração de um *hash* determinístico unidirecional do campo (armazenado em uma coluna separada), equilibrando alta performance de busca exata com segurança rigorosa.

### Evidências
- **Código e Testes:** Arquivos de teste `config/test_indice_cego.py` e respectivo histórico de migrações da aplicação de funcionários.

---

## Histórico de alterações

| Versão | Data | Alteração | Responsável |
|---|---|---|---|
| 1.0 | 12/10/2026 | Criptografia dos dados em repouso | Marcos Antônio Ferreira de Araújo |