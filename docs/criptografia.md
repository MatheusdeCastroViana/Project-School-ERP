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

## Procedimento Operacional — Rotação de Chaves

### Quem executa
O Analista de Segurança da Informação ou o desenvolvedor responsável pela aplicação, com acesso ao servidor de produção e ao cofre de senhas onde as chaves são guardadas.

### Quando executar
Sempre que houver suspeita de comprometimento de uma chave criptográfica, ou periodicamente como boa prática de segurança (por exemplo, a cada 6 ou 12 meses). Também sempre que uma nova chave for adicionada ao `FIELD_ENCRYPTION_KEYS` e quiser migrar os dados existentes para ela.

### Onde ficam as chaves e o backup
As chaves ficam armazenadas exclusivamente em variáveis de ambiente (`FIELD_ENCRYPTION_KEYS`), nunca no código-fonte nem no banco de dados.

- **Em desenvolvimento:** o arquivo `.env` (não versionado no Git) contém essas variáveis.
- **Em produção no Render:** as chaves ficam nas variáveis de ambiente do painel do Render, não num `.env`.

**Backup:** antes de qualquer alteração, faça backup do arquivo `.env` (ou exporte as variáveis do Render) **e** um dump do banco de dados. Guarde o backup do `.env`/variáveis em local separado do dump do banco — por exemplo, num cofre de senhas. Se as duas coisas ficarem juntas, quem tiver acesso ao backup terá acesso aos dados decifrados, anulando a criptografia. Se algo der errado, você restaura o backup e volta para a chave anterior.

> Atenção: se a chave antiga foi comprometida, backups e dumps antigos continuam decifráveis por ela. Considere rotacionar também os dados contidos nesses backups ou tratá-los como comprometidos.

### Como executar (passo a passo)

1. Gere uma nova chave Fernet:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

2. Faça backup do `.env` (ou exporte as variáveis do Render) **e** de um dump do banco de dados. Guarde o backup das chaves em local separado do dump do banco.

3. Adicione a nova chave no início da variável de ambiente `FIELD_ENCRYPTION_KEYS` (ela fica na primeira posição para ser usada nas novas cifragens), mantendo a chave antiga na lista para ainda poder decifrar dados antigos. Exemplo no `.env`:
   ```
   FIELD_ENCRYPTION_KEYS=<nova_chave>,<chave_antiga>
   ```

4. Reinicie a aplicação para carregar as novas variáveis de ambiente.

5. Rode o comando de rotação:
   ```bash
   python manage.py rotacionar_chaves
   ```
   O comando recifra CPF, telefone e chave TOTP de todos os registros com a chave mais nova e recalcula o `cpf_indice`.
   
   Use `--dry-run` para simular sem gravar alterações:
   ```bash
   python manage.py rotacionar_chaves --dry-run
   ```

6. Confira que os dados ainda estão acessíveis (login, 2FA, consulta de CPF funcionam).

   Atenção: o `cpf_indice` depende da `BLIND_INDEX_KEY`. Se essa chave também for trocada entre o passo 4 e o passo 5, as buscas por CPF podem falhar até que o comando de rotação seja rodado e recalcule os índices.

7. Depois de confirmar que tudo está funcionando, pode remover a chave antiga da lista (opcional). Se remover, dados cifrados apenas com ela não serão mais decifráveis — por isso o backup é importante.

### Evidências
- Teste automatizado: `funcionarios/test_rotacao_chaves.py`

### Comando disponível
`python manage.py rotacionar_chaves` recifra CPF, telefone e chave TOTP com a chave mais nova e recalcula o cpf_indice.

---

## Histórico de alterações

| Versão | Data | Alteração | Responsável |
|---|---|---|---|
| 1.0 | 12/10/2026 | Criptografia dos dados em repouso | Marcos Antônio Ferreira de Araújo |
| 1.1 | 03/11/2026 | Rotação de chaves Fernet | Marcos Antônio Ferreira de Araújo |