# Autenticação e Gestão de Credenciais

## 1. Visão geral

A autenticação foi implementada com um backend customizado (`usuarios/backends.py`), um modelo de usuário próprio com login por e-mail (`usuarios/models.py`) e um hasher de senha com os parâmetros customizados baseado em Argon2id (`usuarios/hashers.py`).

## 3. Requisitos detalhados

### RS 1.1 — Hash criptográfico seguro para senhas

**Requisito:** O sistema deverá utilizar hash criptográfico seguro para armazenar senhas, utilizando Argon2, bcrypt ou PBKDF2.

**Decisão adotada**
Foi criada uma subclasse `UsuarioArgon2PasswordHasher` (em `usuarios/hashers.py`), que usa o Argon2id como algoritmo principal. Em `config/settings.py`, o `PASSWORD_HASHERS` foi configurado colocando esse hasher customizado em primeiro lugar, com o `PBKDF2PasswordHasher` padrão do Django como fallback. O Django faz o upgrade automático do hash de PBKDF2 pra Argon2id assim que um usuário com hash antigo faz login com sucesso, sem precisar de ação manual.

**Justificativa técnica**
Argon2id é o algoritmo recomendado atualmente pela OWASP pra hash de senha, principalmente por ser resistente a ataques com GPU/ASIC (diferente do PBKDF2, que é mais vulnerável a esse tipo de aceleração). Manter o PBKDF2 como fallback garante que nenhum usuário fique impedido de logar caso já existisse com hash no formato antigo antes da mudança, e o próprio login resolve a migração dele automaticamente.

**Evidência**
- Teste automatizado: `usuarios/tests.py::test_hash_usa_argon2id`
- ![alt text](image-2.png)
- ![alt text](image-1.png)

---

### RS 1.2 — Parâmetros de custo do hash

**Requisito:** Os parâmetros de custo do algoritmo de hash deverão ser configurados de forma adequada ao ambiente do sistema.

**Decisão adotada**
Em `usuarios/hashers.py`, os parâmetros foram configurados como `time_cost = 5`, `memory_cost = 32768` (32 MiB) e `parallelism = 1`, sobrescrevendo os valores padrão do `Argon2PasswordHasher` do Django (que usa `parallelism = 8` por padrão).

**Justificativa técnica**
A OWASP recomenda, como configuração mínima do Argon2id, pelo menos 19 MiB de memória, 2 iterações e paralelismo igual a 1. Os valores escolhidos ficam acima desse mínimo (32 MiB, 5 iterações), dando margem extra de segurança. O `parallelism = 1` foi mantido conforme a recomendação, já que aumentar o paralelismo não necessariamente deixa o hash mais seguro, só consome mais núcleos de CPU ao mesmo tempo, o que atrapalha mais do que ajuda em um ambiente de hospedagem. O tempo de hash medido ficou em torno de 94ms por operação, um custo aceitável pra experiência do usuário sem enfraquecer a proteção.

**Evidência**
- Teste automatizado: `usuarios/tests.py::test_parametros_de_custo_configurados`
- - ![alt text](image.png)

---

### RS 1.3 — Salt criptográfico único por senha

**Requisito:** O sistema deverá utilizar um salt criptográfico único para cada senha ou usuário.

**Decisão adotada**
Nenhuma configuração manual foi necessária: tanto o Argon2id quanto o PBKDF2 (via `django.contrib.auth.hashers`) já geram um salt aleatório único a cada chamada de `set_password()`, e o salt fica armazenado junto com o hash no próprio campo `password`.

**Justificativa técnica**
Usar salt único por senha impede ataques de rainbow table e garante que duas senhas iguais gerem hashes diferentes no banco. Como isso já é padrão dos hashers do Django (e do Argon2id em geral), não foi necessário implementar nada customizado — só confirmar que a geração de salt não foi desabilitada em nenhum ponto da configuração.

**Evidência**
Dois usuários com a mesma senha (1234) com hashs diferentes.
- ![alt text](image-3.png)
---

### RS 1.4 — Armazenamento correto do hash e metadados

**Requisito:** O armazenamento deverá manter corretamente o hash e os metadados necessários, sem armazenar a senha original.

**Decisão adotada**
O campo `password`, herdado de `AbstractUser`, armazena a string completa gerada pelo hasher (algoritmo, parâmetros de custo, salt e hash), no formato `argon2$argon2id$v=19$m=32768,t=5,p=1$...`. Em nenhum momento a senha em texto puro é persistida — o método `set_password()` do `UsuarioManager` já converte a senha em hash antes de qualquer `save()`.

**Justificativa técnica**
Guardar os metadados junto com o hash (em vez de num campo separado) é o padrão adotado pelo Django e evita inconsistência entre o algoritmo registrado e o hash de fato usado — se um dia os parâmetros de custo mudarem, os hashes antigos continuam sendo verificáveis corretamente porque os parâmetros usados na hora da criação ficam registrados na própria string.

**Evidência**
- Teste automatizado: `usuarios/tests.py::test_senha_correta_autentica` e `test_senha_incorreta_nao_autentica`
- ![alt text](image-4.png)

---

### RS 1.5 — Autenticação de dois fatores (2FA)

**Requisito:** O sistema deverá implementar autenticação de dois fatores (2FA) para os perfis definidos como obrigatórios pelo projeto.


**Decisão planejada**


**Evidência**
- [Inserir print da tela de 2FA quando disponível]

---

### RS 1.6 — Validação do 2FA após a autenticação primária

**Requisito:** O sistema deverá validar o segundo fator somente após a validação da autenticação primária.

**Decisão planejada**


**Evidência**
- [Inserir teste de fluxo: senha incorreta, código incorreto, código correto, tentativa de acesso direto sem 2FA]

---

### RS 1.7 — Fluxo completo de autenticação

**Requisito:** O fluxo de autenticação deverá funcionar corretamente desde a entrada das credenciais até a criação da sessão autorizada.


**Decisão adotada (parte pronta)**
O `UsuarioBackend.authenticate()` já implementa toda a lógica de validação: busca por e-mail, checagem de bloqueio antes da senha, verificação da senha, checagem de `is_active` depois da senha (`user_can_authenticate`), reset do contador de tentativas falhas em caso de sucesso. Falta a view que chama `django.contrib.auth.login()` pra de fato criar a sessão a partir de um usuário autenticado por esse backend.

**Justificativa técnica**
Checar o bloqueio antes da senha evita gastar o custo computacional do Argon2 (proposital e caro) numa conta já bloqueada. Já o `user_can_authenticate()` é verificado só depois da senha correta de propósito: se fosse checado antes, um atacante poderia usar a mensagem de erro (ou o tempo de resposta) pra descobrir se uma conta desativada existe no sistema, mesmo sem saber a senha.

**Evidência**
- [Inserir print do fluxo completo funcionando: login → sessão criada → acesso à tela pós-login]

---

### RS 1.8 — Evidências funcionais da autenticação

**Requisito:** O projeto deverá apresentar evidências funcionais da autenticação, como prints, logs controlados ou testes automatizados.

**Decisão adotada**
Foram escritos testes automatizados em `usuarios/tests.py` cobrindo: algoritmo de hash usado, parâmetros de custo aplicados, autenticação com senha correta, autenticação com senha incorreta e tempo de hash dentro do esperado.

**Justificativa técnica**
Testes automatizados garantem que a evidência seja reproduzível a qualquer momento (por exemplo, antes de cada entrega), e não dependem de um print estático que pode ficar desatualizado se o código mudar. Ainda assim, como a instrução da entrega exige teste via front-end, essa evidência automatizada precisa ser complementada com prints da aplicação rodando de fato.

**Evidência**
- Comando de execução: `python manage.py test usuarios -v 2`
- [Inserir prints do fluxo pelo front-end quando disponível]

---

### RS 1.9 — Expiração de sessão

**Requisito:** As sessões autenticadas deverão possuir tempo de expiração configurado.

**Decisão adotada**
Em `config/settings.py`, foi configurado `SESSION_COOKIE_AGE = 1800` (30 minutos) junto com `SESSION_SAVE_EVERY_REQUEST = True`. Com essa combinação, a sessão não expira num horário fixo desde o login — a contagem de 30 minutos é renovada a cada requisição. A sessão só expira de fato se o usuário ficar 30 minutos sem realizar nenhuma ação.

**Justificativa técnica**
Optamos por expiração por inatividade, e não por um tempo fixo desde o login, porque um tempo fixo obrigaria o usuário a logar de novo várias vezes ao longo do dia mesmo estando ativamente usando o sistema. Trinta minutos foi escolhido como equilíbrio entre reduzir o risco de sessão esquecida aberta e não interromper o trabalho de quem está de fato usando o sistema.

**Evidência**
- ![alt text](image-5.png)
- [Inserir teste manual: sessão expirando após 30 minutos de inatividade]

---

### RS 1.10 — Logout invalida a sessão

**Requisito:** O logout deverá invalidar a sessão ativa e impedir sua reutilização.

**Decisão planejada**
[A completar: uso de `django.contrib.auth.logout()`, que já invalida a sessão do lado do servidor por padrão.]

**Evidência**
- [Inserir teste de logout, reutilização do cookie de sessão e tentativa de acesso posterior]

---

### RS 1.11 — Proteção contra ataques de força bruta

**Requisito:** O sistema deverá possuir proteção contra ataques de força bruta por meio de limitação de tentativas, bloqueio temporário, atraso progressivo ou mecanismo equivalente.

**Decisão adotada**
No `UsuarioBackend.authenticate()`, cada tentativa de login com senha incorreta incrementa o campo `tentativas_login_falhas` do usuário. Quando esse contador atinge `settings.LOGIN_MAX_TENTATIVAS` (5), o campo `bloqueado_ate` é preenchido com o horário atual mais `settings.LOGIN_BLOQUEIO_MINUTOS` (15 minutos). Enquanto `bloqueado_ate` estiver no futuro, o login é recusado mesmo com a senha correta. Em caso de sucesso, o contador é zerado.

**Justificativa técnica**
Optamos por bloqueio temporário em vez de permanente porque um bloqueio permanente exigiria intervenção manual de um administrador toda vez que um usuário legítimo errasse a senha demais, prejudicando a disponibilidade do sistema sem necessidade. Zerar o contador só após login bem-sucedido (e não após qualquer tentativa) evita que o atacante consiga "resetar" o contador de propósito.

**Evidência**
- [Inserir teste com 5+ tentativas incorretas seguidas, mostrando o bloqueio sendo aplicado]
- [Inserir print da tentativa de login durante o período de bloqueio, mesmo com senha correta]

---

### RS 1.12 — Configurações coerentes documentadas

**Requisito:** O sistema deverá aplicar configurações coerentes para hash, 2FA, expiração de sessão e proteção contra força bruta.


**Decisão adotada**
Este documento (`autenticacao.md`) centraliza as decisões e justificativas dos RS 1.1 a 1.11, servindo como o registro exigido por este item. Ele será atualizado assim que a parte de 2FA (RS 1.5/1.6) estiver implementada pelo Matheus.

**Evidência**
- Este próprio documento, mais os arquivos de código referenciados em cada seção.

## 4. Arquivos relacionados

| Arquivo | Conteúdo |
|---|---|
| `usuarios/models.py` | Modelo `Usuario`, `UsuarioManager`, login por e-mail |
| `usuarios/backends.py` | `UsuarioBackend` — lógica de autenticação e bloqueio |
| `usuarios/hashers.py` | `UsuarioArgon2PasswordHasher` — parâmetros de custo |
| `usuarios/admin.py` | `UsuarioAdmin` customizado |
| `usuarios/tests.py` | Testes automatizados de hash e autenticação |
| `config/settings.py` | `PASSWORD_HASHERS`, `SESSION_COOKIE_AGE`, `LOGIN_MAX_TENTATIVAS` |

## 5. Histórico de alterações

| Versão | Data | Alteração | Responsável |
|---|---|---|---|
| 1.0 | 29/08/2026 | Criação do documento, cobrindo RS 1.1–1.12 para a primeira entrega. | Marcos Antônio Ferreira de Araújo |
