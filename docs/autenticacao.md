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
- ![Print da execução do teste hash Argon2id](evidencias/teste_autenticacao.png)
- ![Print do hash no banco](evidencias/argon2id.png)

---

### RS 1.2 — Parâmetros de custo do hash

**Requisito:** Os parâmetros de custo do algoritmo de hash deverão ser configurados de forma adequada ao ambiente do sistema.

**Decisão adotada**
Em `usuarios/hashers.py`, os parâmetros foram configurados como `time_cost = 5`, `memory_cost = 32768` (32 MiB) e `parallelism = 1`, sobrescrevendo os valores padrão do `Argon2PasswordHasher` do Django (que usa `parallelism = 8` por padrão).

**Justificativa técnica**
A OWASP recomenda, como configuração mínima do Argon2id, pelo menos 19 MiB de memória, 2 iterações e paralelismo igual a 1. Os valores escolhidos ficam acima desse mínimo (32 MiB, 5 iterações), dando margem extra de segurança. O `parallelism = 1` foi mantido conforme a recomendação, já que aumentar o paralelismo não necessariamente deixa o hash mais seguro, só consome mais núcleos de CPU ao mesmo tempo, o que atrapalha mais do que ajuda em um ambiente de hospedagem. O tempo de hash medido ficou em torno de 94ms por operação, um custo aceitável pra experiência do usuário sem enfraquecer a proteção.

**Evidência**
- Teste automatizado: `usuarios/tests.py::test_parametros_de_custo_configurados`
- ![Print da execução do teste de velocidade do hash](evidencias/tempo_hash.png)

---

### RS 1.3 — Salt criptográfico único por senha

**Requisito:** O sistema deverá utilizar um salt criptográfico único para cada senha ou usuário.

**Decisão adotada**
Nenhuma configuração manual foi necessária: tanto o Argon2id quanto o PBKDF2 (via `django.contrib.auth.hashers`) já geram um salt aleatório único a cada chamada de `set_password()`, e o salt fica armazenado junto com o hash no próprio campo `password`.

**Justificativa técnica**
Usar salt único por senha impede ataques de rainbow table e garante que duas senhas iguais gerem hashes diferentes no banco. Como isso já é padrão dos hashers do Django (e do Argon2id em geral), não foi necessário implementar nada customizado — só confirmar que a geração de salt não foi desabilitada em nenhum ponto da configuração.

**Evidência**
- ![Print do banco com dois usuários que possuem a mesma senha (1234)](evidencias/teste_salt.png)
---

### RS 1.4 — Armazenamento correto do hash e metadados

**Requisito:** O armazenamento deverá manter corretamente o hash e os metadados necessários, sem armazenar a senha original.

**Decisão adotada**
O campo `password`, herdado de `AbstractUser`, armazena a string completa gerada pelo hasher (algoritmo, parâmetros de custo, salt e hash), no formato `argon2$argon2id$v=19$m=32768,t=5,p=1$...`. Em nenhum momento a senha em texto puro é persistida — o método `set_password()` do `UsuarioManager` já converte a senha em hash antes de qualquer `save()`.

**Justificativa técnica**
Guardar os metadados junto com o hash (em vez de num campo separado) é o padrão adotado pelo Django e evita inconsistência entre o algoritmo registrado e o hash de fato usado — se um dia os parâmetros de custo mudarem, os hashes antigos continuam sendo verificáveis corretamente porque os parâmetros usados na hora da criação ficam registrados na própria string.

**Evidência**
- Teste automatizado: `usuarios/tests.py::test_senha_correta_autentica` e `test_senha_incorreta_nao_autentica`
- ![Print da execução dos testes](evidencias/teste_autenticacao.png)

---

### RS 1.5 — Autenticação de dois fatores (2FA)

**Requisito:** O sistema deverá implementar autenticação de dois fatores (2FA) para os perfis definidos como obrigatórios pelo projeto.

**Decisão adotada**
 Implementado 2FA baseado em TOTP (RFC 6238) via a biblioteca `pyotp`, compatível com apps como Google Authenticator. O modelo `Configuracao2FA` (`usuarios/models_2fa.py`) guarda a chave secreta por usuário (`chave_secreta`, gerada automaticamente no `save()` com `pyotp.random_base32()` se ainda não existir), o status `ativado` e o horário do último uso (`ultimo_uso`). A ativação acontece na view `ativar_2fa`: o usuário escaneia um QR Code (gerado em `get_qrcode_base64()`, a partir da URI de provisionamento do `pyotp`) e confirma digitando um token válido antes de `ativado` virar `True`. Existe também `desativar_2fa` pra desligar o 2FA da conta.

**Justificativa técnica**
TOTP foi escolhido por ser um padrão aberto e amplamente suportado (não depende de SMS, que tem custo e é vulnerável a SIM swap). Exigir a confirmação de um token válido antes de marcar `ativado = True` evita que o usuário fique bloqueado pra sempre por ter escaneado um QR Code errado ou de outro app.

**Evidência**
- Migração: `usuarios/migrations/0003_configuracao2fa.py`
- [Inserir print da tela de ativação de 2FA com QR Code]

---

### RS 1.6 — Validação do 2FA após a autenticação primária

**Requisito:** O sistema deverá validar o segundo fator somente após a validação da autenticação primária.

**Decisão adotada**
A ordem é garantida pelo próprio ponto do pipeline do `allauth` onde a checagem de 2FA foi inserida. O `Custom2FAAccountAdapter` (`usuarios/adapters.py`) sobrescreve o hook `pre_login()`, que o allauth chama **depois** de validar as credenciais (e-mail/senha, via `UsuarioBackend` — incluindo a checagem de bloqueio por força bruta) e **antes** de criar a sessão autenticada. Se o usuário tem `Configuracao2FA.ativado = True`, o `pre_login()` guarda o id dele em `request.session['usuario_pendente_2fa']` e redireciona pra `verificar_2fa`, interrompendo o fluxo normal do allauth, então nenhuma sessão é criada nesse ponto. A sessão só é criada na view `verificar_2fa`, chamando `django.contrib.auth.login()` explicitamente, e só depois de `config.verify_token(token)` retornar `True` (com tolerância de 30s via `valid_window=1`).

**Justificativa técnica**
Colocar a checagem no `pre_login()` (em vez de, por exemplo, checar 2FA dentro da própria view de login) evita duas classes de erro: (1) criar a sessão antes da hora e só "fingir" bloquear o acesso via redirect (o que deixaria um cookie de sessão válido circulando antes da confirmação do segundo fator); e (2) esquecer de checar 2FA em algum ponto de entrada alternativo, já que o hook roda pra qualquer fluxo de login que passe pelo allauth. Os eventos de verificação (sucesso/falha) são registrados via `registrar_evento_2fa()` (`usuarios/audit.py`), sem nunca logar o token em si.

**Evidência**
- Arquivos: `usuarios/adapters.py`, `usuarios/views_2fa.py::verificar_2fa`, `usuarios/audit.py`
- [Inserir teste de fluxo completo, incluindo tentativa de acessar `dashboard` sem passar pelo `verificar_2fa`]

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
- ![Print da área de configurações de sessões](evidencias/session_cookie_age.png)
- [Inserir teste manual: sessão expirando após 30 minutos de inatividade]

---

### RS 1.10 — Logout invalida a sessão

**Requisito:** O logout deverá invalidar a sessão ativa e impedir sua reutilização.

**Decisão adotada**
Implementada uma view customizada de logout (`usuarios/views_2fa.py::logout_usuario`), acionada pelo botão "Sair do Sistema" no dashboard (`usuarios/templates/usuarios/dashboard.html`), via um `<form method="post">` com `{% csrf_token %}` apontando pra `usuarios:logout`. A view é decorada com `@login_required`, registra o evento de logout no log de auditoria (`registrar_evento_autenticacao`, em `usuarios/audit.py`) **antes** de destruir a sessão, e só então chama `django.contrib.auth.logout(request)` que invalida a sessão do lado do servidor (apaga os dados da sessão no banco/cache e expira o cookie `sessionid`) antes de redirecionar pra tela de login.

**Justificativa técnica**
Registrar o evento de auditoria antes de chamar `logout()` é necessário porque, depois do `logout()`, `request.user` deixa de estar associado ao usuário que estava logado (vira `AnonymousUser`) se a ordem fosse invertida, o log ficaria sem o e-mail do usuário que saiu. Usar POST (em vez de GET, como em implementações mais antigas/ingênuas de logout) evita que o logout aconteça sem intenção do usuário via prefetch de link, crawler ou CSRF de terceiros já que o form exige o token CSRF.

**Evidência**
- Reproduzido de forma isolada com o `Client` de testes do Django, simulando o fluxo completo (login forçado → GET no dashboard → POST no logout → nova tentativa de GET no dashboard):

---

### RS 1.11 — Proteção contra ataques de força bruta

**Requisito:** O sistema deverá possuir proteção contra ataques de força bruta por meio de limitação de tentativas, bloqueio temporário, atraso progressivo ou mecanismo equivalente.

**Decisão adotada**
No `UsuarioBackend.authenticate()`, cada tentativa de login com senha incorreta incrementa o campo `tentativas_login_falhas` do usuário. Quando esse contador atinge `settings.LOGIN_MAX_TENTATIVAS` (5), o campo `bloqueado_ate` é preenchido com o horário atual mais `settings.LOGIN_BLOQUEIO_MINUTOS` (15 minutos). Enquanto `bloqueado_ate` estiver no futuro, o login é recusado mesmo com a senha correta. Em caso de sucesso, o contador é zerado.

**Justificativa técnica**
Optamos por bloqueio temporário em vez de permanente porque um bloqueio permanente exigiria intervenção manual de um administrador toda vez que um usuário legítimo errasse a senha demais, prejudicando a disponibilidade do sistema sem necessidade. Zerar o contador só após login bem-sucedido (e não após qualquer tentativa) evita que o atacante consiga "resetar" o contador de propósito.

**Evidência**
- ![Print da execução dos testes](evidencias/5_logins_falhos.png)
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
| 1.1 | 30/08/2026 | Atualização das seções RS 1.5, 1.6 (2FA) e RS 1.10 (logout) | Marcos Antônio Ferreira de Araújo |
