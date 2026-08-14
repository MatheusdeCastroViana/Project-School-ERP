# ERP Escola Profissionalizante

Sistema web para gestão integrada de escolas profissionalizantes e de formação complementar.

## Stack tecnológica

A aplicação será desenvolvida utilizando **Python** como linguagem principal e **Django** como framework web. O banco de dados utilizado será o **PostgreSQL**.

As versões específicas das tecnologias serão definidas posteriormente, durante a configuração do ambiente de desenvolvimento e a criação do projeto.

| Categoria | Tecnologia | Versão |
|---|---|---|
| Linguagem de programação | Python | 3.14.6 |
| Framework web | Django | 6.1 |
| Banco de dados | PostgreSQL | 18.6 |

## Arquitetura da aplicação

O sistema utilizará a arquitetura **MVT — Model, View e Template**, padrão do framework Django. Essa arquitetura organiza a aplicação em responsabilidades separadas, facilitando a manutenção, a evolução e a organização do código.

### Model

Os **Models** representam os dados e as regras relacionadas à persistência das informações. Eles serão responsáveis por definir as entidades do sistema, seus campos, relacionamentos e comportamentos associados ao banco de dados PostgreSQL.

Exemplos de entidades que poderão ser representadas por Models incluem alunos, funcionários, cursos, turmas, matrículas, contratos, mensalidades, notas e materiais.

### View

As **Views** serão responsáveis por processar as requisições, aplicar as regras de negócio, consultar ou alterar os Models e encaminhar os dados para os Templates apropriados.

As Views também deverão verificar as permissões dos usuários antes de permitir operações como cadastrar informações, lançar notas, consultar dados financeiros ou gerar relatórios.

### Template

Os **Templates** serão responsáveis pela apresentação das informações ao usuário. Neles serão construídas as páginas HTML, os formulários, as tabelas, os menus e os demais elementos da interface web.

Os Templates deverão exibir somente as funcionalidades compatíveis com o perfil de acesso do usuário, sem substituir as validações de segurança realizadas nas Views e nas demais camadas da aplicação.

## Organização por aplicações Django

O sistema será dividido em aplicações independentes, chamadas de **apps**, seguindo a organização recomendada pelo Django. Cada app deverá agrupar funcionalidades relacionadas a um determinado domínio do sistema.

A divisão final dos apps será definida durante o desenvolvimento, mas poderá seguir uma estrutura semelhante à apresentada abaixo:

```text
erp_escola/
├── manage.py
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── usuarios/
├── alunos/
├── funcionarios/
├── cursos/
├── turmas/
├── matriculas/
├── contratos/
├── financeiro/
├── pedagogico/
├── estoque/
├── relatorios/
├── templates/
├── static/
└── requirements.txt
```

A estrutura acima é uma referência inicial. Os nomes, a quantidade e a divisão dos apps poderão ser ajustados conforme a modelagem do sistema e a evolução do projeto.

## Princípios de organização

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