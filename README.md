# ERP Escola Profissionalizante

Sistema web para gestão integrada de escolas profissionalizantes e de formação complementar.

## 🌐 Acessar o sistema

Acesse a versão online: [Project School ERP](https://project-school-erp.onrender.com)

## Status do Projeto

Projeto desenvolvido como Projeto Integrador de Políticas de Segurança da Informação. O módulo de **Autenticação e Segurança** está implementado e inclui:

- hash de senha com Argon2id;
- 2FA (TOTP) obrigatório para todos os usuários, com bloqueio por tentativas inválidas;
- proteção contra força bruta no login;
- recuperação de senha com token de uso único e envio por e-mail;
- criptografia de dados sensíveis em repouso;
- HTTPS/HSTS e cookies seguros em produção;
- conformidade com a LGPD (consentimento, consulta, exportação e exclusão de dados);
- auditoria em banco de dados com registros imutáveis;
- autorização por setor.

A documentação técnica de cada requisito está na pasta [`docs/`](docs/).

## Documentação

| Documento | Conteúdo |
|---|---|
| [`docs/autenticacao.md`](docs/autenticacao.md) | Hash, 2FA, sessão, logout e força bruta |
| [`docs/recuperacao_senha.md`](docs/recuperacao_senha.md) | Recuperação de senha |
| [`docs/criptografia.md`](docs/criptografia.md) | Criptografia em repouso, chaves e índice cego |
| [`docs/https_tls.md`](docs/https_tls.md) | HTTPS/TLS e bloqueio de conexões inseguras |
| [`docs/lgpd.md`](docs/lgpd.md) | Conformidade com a LGPD |
| [`docs/lgpd/inventario_dados.md`](docs/lgpd/inventario_dados.md) | Inventário de dados pessoais |
| [`docs/auditoria_logs.md`](docs/auditoria_logs.md) | Auditoria e logs |
| [`docs/evidencias/`](docs/evidencias/) | Prints e saídas de testes |

## Stack Tecnológica

A aplicação é desenvolvida em Python com o framework Django e usa PostgreSQL como banco de dados.

| Categoria | Tecnologia | Versão |
| :--- | :--- | :--- |
| Linguagem de programação | Python | 3.14.6 |
| Framework web | Django | 6.1 |
| Banco de dados | PostgreSQL | 18.6 |
| Autenticação | `django-allauth` | 65.19.1 |
| Segundo fator (TOTP) | `django-otp` + `pyotp` + `qrcode` | 1.7.0 + 2.10.0 + 8.2 |
| Hash de senha | `argon2-cffi` | 25.1.0 |
| Criptografia em repouso | `cryptography` (Fernet) | 50.0.2 |
| Variáveis de ambiente | `python-decouple` | 3.8 |
| Arquivos estáticos | `whitenoise` | 6.12.0 |
| Servidor de produção | `gunicorn` | 26.0.0 |
| Envio de e-mail | `django-anymail[resend]` | 10.3 |

## Arquitetura da Aplicação

O sistema usa a arquitetura **MVT (Model, View, Template)** do Django:

- **Model:** entidades, campos, relacionamentos e regras de persistência no PostgreSQL.
- **View:** processa as requisições, aplica regras de negócio, consulta e altera os Models e encaminha dados aos Templates. Também aplica as permissões e validações de segurança.
- **Template:** apresentação (HTML, formulários, tabelas). Exibe apenas as funcionalidades compatíveis com o perfil do usuário, sem substituir as validações do backend.

## Organização por Aplicações (Apps)

```text
Project-School-ERP/
├── manage.py
├── config/                 # Configurações centrais (settings, urls, criptografia, campos cifrados)
│   └── templates/          # Templates globais (allauth e admin customizados)
├── usuarios/               # Autenticação, 2FA, recuperação de senha, LGPD e auditoria
├── funcionarios/           # Setores, cargos, funcionários e jornada (dados cifrados)
├── dashboard/              # Painéis por setor
├── static/                 # Arquivos estáticos (CSS, JS)
├── docs/                   # Documentação técnica e evidências
├── build.sh                # Script de build para a hospedagem
├── .env.example            # Exemplo de variáveis de ambiente
└── requirements.txt        # Dependências do projeto
```

### Princípios de organização

Cada app concentra Models, Views, URLs, formulários, administração, testes e demais componentes da sua responsabilidade, evitando concentrar o código em um único módulo. Os apps se relacionam por meio dos Models. As configurações gerais ficam em `config/`.

## Para rodar o projeto localmente

1. Clone o repositório:
```bash
git clone https://github.com/MatheusdeCastroViana/Project-School-ERP.git
cd Project-School-ERP
```

2. Crie e ative o ambiente virtual:
```bash
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Linux/Mac
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente. Copie o `.env.example` para `.env`:
```bash
copy .env.example .env    # Windows
cp .env.example .env      # Linux/Mac
```
Preencha no `.env`:
- as credenciais do PostgreSQL local (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`);
- `SECRET_KEY`;
- `FIELD_ENCRYPTION_KEYS` e `BLIND_INDEX_KEY`, obrigatórias: sem elas o sistema não consegue ler nem gravar CPF, telefone e chave do 2FA. Os comandos para gerá-las estão no `.env.example`;
- as variáveis de e-mail (`EMAIL_BACKEND` e as demais). Para ver o e-mail de recuperação de senha no terminal, use `django.core.mail.backends.console.EmailBackend`.

5. Certifique-se de que o banco de dados existe no PostgreSQL local, com nome, usuário e senha iguais aos do `.env`.

6. Aplique as migrações:
```bash
python manage.py migrate
```

7. Crie o primeiro usuário administrador. O cadastro público é fechado, então os demais usuários são criados pelo painel `/admin/`:
```bash
python manage.py createsuperuser
```

8. Rode o servidor:
```bash
python manage.py runserver
```

No primeiro login o sistema exige a configuração do 2FA com um aplicativo autenticador.

## Testes

```bash
python manage.py test
```
