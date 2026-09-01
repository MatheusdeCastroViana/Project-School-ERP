# ERP Escola Profissionalizante

Sistema web para gestão integrada de escolas profissionalizantes e de formação complementar.

## Status do Projeto
Este projeto está em desenvolvimento ativo como parte de um Projeto Integrador. Atualmente, o módulo de **Autenticação e Segurança** está completo e em conformidade com os requisitos de segurança da informação, incluindo 2FA, proteção contra força bruta e logs de auditoria.

## Stack Tecnológica

A aplicação é desenvolvida utilizando Python como linguagem principal e Django como framework web. O banco de dados utilizado é o PostgreSQL.

| Categoria | Tecnologia | Versão |
| :--- | :--- | :--- |
| Linguagem de programação | Python | 3.14.6 |
| Framework web | Django | 6.1 |
| Banco de dados | PostgreSQL | 18.6 |
| Autenticação | `django-allauth` + `pyotp` | 65.19.1 + 2.10.0 |
| Variáveis de ambiente | `python-decouple` | 3.8 |

## Arquitetura da Aplicação

O sistema utiliza a arquitetura **MVT (Model, View, Template)**, padrão do framework Django. Essa arquitetura organiza a aplicação em responsabilidades separadas, facilitando a manutenção, a evolução e a organização do código.

- **Model:** Representam os dados e as regras de persistência. Definem as entidades, campos, relacionamentos e comportamentos no PostgreSQL.
- **View:** Processam as requisições, aplicam regras de negócio, consultam/alteram Models e encaminham dados aos Templates. Também gerenciam permissões e validações de segurança.
- **Template:** Responsáveis pela apresentação (HTML, formulários, tabelas). Exibem apenas funcionalidades compatíveis com o perfil do usuário, sem substituir as validações de backend.

## Organização por Aplicações (Apps)

O sistema é dividido em aplicações independentes, seguindo a organização recomendada pelo Django. 

### Estrutura Atual Implementada:
```text
Project-School-ERP/
├── manage.py
├── config/                 # Configurações centrais do projeto (settings, urls, wsgi)
│   ├── templates/          # Templates globais (ex: allauth customizado)
├── usuarios/               # App de autenticação, usuários, 2FA e auditoria
├── funcionarios/           # App de gestão de funcionários (vinculado ao usuário)
├── static/                 # Arquivos estáticos (CSS, JS, Imagens)
├── logs/                   # Logs de auditoria de segurança (gerado automaticamente)
├── .env                    # Variáveis de ambiente (não versionado)
├── .env.example            # Exemplo de variáveis de ambiente
└── requirements.txt        # Dependências do projeto
```
# Princípios de organização

Cada app deverá concentrar Models, Views, URLs, formulários, arquivos administrativos, testes e demais componentes relacionados à sua responsabilidade. O objetivo é evitar a concentração de todo o código em um único módulo.

Os relacionamentos entre os apps serão realizados por meio dos Models e das regras de negócio definidas no sistema. As configurações gerais do projeto, como banco de dados, URLs principais e configurações do Django, permanecerão em um módulo central de configuração.

A arquitetura deverá manter separação entre apresentação, processamento das requisições e persistência dos dados, respeitando o padrão MVT do Django.

## Para rodar o projeto

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

4. Configure as variáveis de ambiente:
   Copie o `.env.example` para `.env` e preencha com suas credenciais locais do PostgreSQL.
```bash
   copy .env.example .env    # Windows
   cp .env.example .env      # Linux/Mac
```

5. Certifique-se de que o banco de dados existe no seu PostgreSQL local (nome, usuário e senha compatíveis com o que você colocou no `.env`).

6. Aplique as migrações:
```bash
   python manage.py migrate
```

7. Rode o servidor:
```bash
   python manage.py runserver
```