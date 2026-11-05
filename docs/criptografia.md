# Documentação — Criptografia de Dados em Repouso

**Projeto:** ERP Escola Profissionalizante
**Autores:** Marcos Antônio Ferreira de Araújo e Matheus de Castro Viana
**Versão do Documento:** 1.1
**Entrega:** Projeto Integrador — Criptografia e Comunicação Segura

---

## Dados protegidos (RS 3.4)

**Requisito:** Dados sensíveis armazenados em repouso deverão ser criptografados quando o risco e a natureza do dado justificarem essa proteção.

| Dado | Onde fica | Proteção | Justificativa |
|---|---|---|---|
| Senha do usuário | `Usuario.password` | Hash Argon2id com salt único (não reversível) | Senha nunca precisa ser recuperada |
| CPF do funcionário | `Funcionario.cpf` | Cifrado com Fernet (`CampoCifrado`) | Identificador pessoal de alto valor |
| Telefone do funcionário | `Funcionario.telefone` | Cifrado com Fernet (`CampoCifrado`) | Dado pessoal de contato |
| Chave secreta TOTP | `Configuracao2FA.chave_secreta` | Cifrada com Fernet (`CampoCifrado`) | Quem a obtém consegue gerar códigos 2FA |
| Token de recuperação de senha | `TokenRecuperacaoSenha.token` | Somente o hash SHA-256 é gravado | O token original só existe no link enviado |
| Índice de busca do CPF | `Funcionario.cpf_indice` | HMAC-SHA256 com chave própria | Permite busca e unicidade sem decifrar |

Os campos cifrados não aceitam filtros de comparação, nem `unique`, nem `db_index` (`config/campos.py`); a configuração inválida é barrada pelas verificações do Django (`campo_cifrado.E001` e `E002`).

---

## Algoritmo, modo e biblioteca (RS 3.5)

**Requisito:** A criptografia de dados em repouso deverá utilizar algoritmo criptográfico adequado, como AES em modo seguro ou mecanismo equivalente.

### Decisão adotada

Foi adotado o **Fernet**, da biblioteca `cryptography`, implementado em `config/criptografia.py`. O Fernet utiliza **AES-128 em modo CBC** com autenticação **HMAC-SHA256** (criptografia autenticada) e um IV aleatório por operação. Os modelos usam o campo personalizado `CampoCifrado` (`config/campos.py`), que cifra o valor ao gravar (`get_prep_value`) e decifra ao ler (`from_db_value`).

As migrações `usuarios/0007_cifrar_chave_secreta.py` e `funcionarios/0008_cifrar_cpf_telefone.py` cifram os dados que já existiam em texto legível.

### Justificativa técnica

O Fernet fornece confidencialidade e integridade: um valor adulterado no banco é rejeitado na leitura (`ErroDecifragem`), e um texto puro gravado diretamente no banco também não é aceito. Como o IV é aleatório, o mesmo texto cifrado duas vezes gera tokens diferentes. As mensagens de erro não expõem a chave nem o conteúdo.

### Evidências

- **Código:** `config/criptografia.py`, `config/campos.py`
- **Testes automatizados:** `config/test_criptografia.py`, `config/test_campos.py`, `funcionarios/test_cifrado.py` e `usuarios/test_2fa_cifrado.py`
- **Saída da execução:** `docs/evidencias/saida_testes_criptografia.txt`

---

## Proteção das chaves (RS 3.6)

**Requisito:** As chaves criptográficas deverão ser protegidas, não podendo ser armazenadas diretamente no código-fonte ou em repositórios públicos.

### Decisão adotada

As chaves são lidas de variáveis de ambiente por `python-decouple` em `config/settings.py`:

- `FIELD_ENCRYPTION_KEYS`: lista de chaves Fernet separadas por vírgula.
- `BLIND_INDEX_KEY`: chave do HMAC do índice cego, com no mínimo 32 caracteres (verificado em tempo de execução).
- `SECRET_KEY`, credenciais do banco e do serviço de e-mail seguem o mesmo padrão.

O arquivo `.env` não é versionado (`.gitignore`); o repositório contém apenas `.env.example` com valores de exemplo e os comandos para gerar cada chave. Em produção os valores são cadastrados como variáveis de ambiente da hospedagem. Se `FIELD_ENCRYPTION_KEYS` estiver ausente ou inválida, a aplicação levanta `ImproperlyConfigured` sem revelar a chave.

### Justificativa técnica

Variáveis de ambiente seguem a prática do 12-Factor App e mantêm segredos fora do controle de versão. Ter chaves separadas para cifragem, índice cego e sessão limita o impacto do vazamento de uma delas.

### Evidências

- **Inspeção:** `config/settings.py`, `.env.example` e `.gitignore`
- **Testes automatizados:** `config/test_criptografia.py::ConfiguracaoTests`

---

## Estratégia de criptografia e ciclo de vida das chaves (RS 3.7)

**Requisito:** O sistema deverá possuir uma estratégia de criptografia que defina os dados protegidos, o ciclo de vida das chaves, a rotação e a recuperação.

### Decisão adotada

- **Dados protegidos:** tabela da seção RS 3.4.
- **Geração:** `Fernet.generate_key()` para chaves de cifragem e `secrets.token_urlsafe(48)` para a chave do índice cego (comandos no `.env.example`).
- **Rotação de chaves de cifragem:** o sistema usa `MultiFernet`. A variável `FIELD_ENCRYPTION_KEYS` aceita várias chaves; a **primeira** da lista cifra os novos dados e todas as da lista servem para decifrar. Procedimento: (1) gerar uma nova chave e colocá-la na primeira posição, mantendo a antiga; (2) a função `rotacionar()` recifra um token com a chave mais nova; (3) após recifrar os dados existentes, remover a chave antiga da lista.
- **Rotação do índice cego:** exige recalcular `cpf_indice` de todos os funcionários, pois o HMAC muda com a chave.
- **Recuperação:** os dados cifrados só podem ser decifrados com as chaves de `FIELD_ENCRYPTION_KEYS`. A perda de todas as chaves torna irrecuperáveis o CPF, o telefone e a chave TOTP. Por isso as chaves devem ter cópia de segurança em local separado do banco e do repositório.
- **Comprometimento de chave:** a chave comprometida é substituída seguindo o procedimento de rotação acima.

### Evidências

- **Código:** `config/criptografia.py` (`MultiFernet`, `cifrar`, `decifrar`, `rotacionar`)
- **Testes automatizados:** `config/test_criptografia.py::RotacaoTests`

---

## Índice cego para busca em campos cifrados

**Requisito de apoio:** permitir busca eficiente, como a pesquisa por CPF, sem decifrar a tabela.

### Decisão adotada

O campo `Funcionario.cpf_indice` guarda o HMAC-SHA256 do CPF normalizado (somente dígitos), calculado com `BLIND_INDEX_KEY` (`config/criptografia.py::indice_cego`) e atualizado no `save()`. O campo é `unique=True` e `editable=False`. A busca é feita por `Funcionario.objects.por_cpf(cpf)`, que aceita o CPF com ou sem máscara, e o `clean()` do modelo recusa CPF duplicado. As migrações `funcionarios/0007` e `0009` criam e ajustam a coluna.

### Justificativa técnica

Como o Fernet não é determinístico, o mesmo CPF gera textos cifrados diferentes e não dá para buscar ou garantir unicidade pelo campo cifrado. O HMAC é determinístico e unidirecional, e a chave própria impede que alguém com acesso ao banco teste CPFs por dicionário sem conhecer `BLIND_INDEX_KEY`.

### Evidências

- **Testes automatizados:** `config/test_indice_cego.py` e `funcionarios/test_cifrado.py::BuscaEUnicidadePorCpfTests`

---

## Justificativa técnica das escolhas (RS 3.8)

| Escolha | Justificativa |
|---|---|
| Fernet (AES-128-CBC + HMAC-SHA256) | Criptografia autenticada de alto nível, difícil de usar incorretamente, com suporte nativo a rotação |
| Hash Argon2id para senhas | A senha não precisa ser recuperada; ver `autenticacao.md` |
| SHA-256 para o token de recuperação | O token já tem 384 bits de entropia, então um hash rápido é suficiente |
| HMAC-SHA256 com chave própria no índice | Busca e unicidade sem expor o CPF |
| Chaves em variáveis de ambiente | Segredos fora do repositório |
| TLS/HTTPS no transporte | Ver `https_tls.md` |

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
