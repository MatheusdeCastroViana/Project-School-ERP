# Documentação — Segurança de Transporte (HTTPS/TLS)

**Projeto:** ERP Escola Profissionalizante  
**Autores:** Marcos Antônio Ferreira de Araújo e Matheus de Castro Viana  
**Versão do Documento de Requisitos:** 1.1  
**Data da implementação:** 13 de outubro de 2026  
**Entrega:** Projeto Integrador - Criptografia e Comunicação Segura

---

## Introdução

A segurança de transporte é um pilar fundamental da proteção de dados em aplicações web. Sem criptografia no canal de comunicação entre cliente e servidor, todas as informações trafegam em texto puro, incluindo credenciais de acesso, tokens de autenticação e dados pessoais sensíveis. Este documento descreve a estratégia de implementação de HTTPS/TLS no sistema ERP Escola Profissionalizante, atendendo aos requisitos de segurança de transporte e conformidade com a LGPD.

---

## Evidência de Tráfego Cifrado

### O que é HTTPS/TLS?

HTTPS (HTTP Secure) é a versão segura do protocolo HTTP, que utiliza TLS (Transport Layer Security) para criptografar a comunicação entre o navegador do usuário e o servidor web. O TLS garante:

1. **Confidencialidade:** Os dados trafegados são criptografados, impedindo que terceiros interceptem e leiam o conteúdo.
2. **Integridade:** Qualquer alteração nos dados durante o transporte é detectada, prevenindo ataques de homem-no-meio (Man-in-the-Middle).
3. **Autenticidade:** O certificado SSL/TLS verifica a identidade do servidor, garantindo que o usuário está se comunicando com o servidor legítimo.

### Implementação no Django

O Django oferece suporte nativo para HTTPS através de configurações no `settings.py`. No ERP Escolar, implementamos as seguintes medidas:

#### 1. Redirecionamento Forçado de HTTP para HTTPS

```python
SECURE_SSL_REDIRECT = True
```

Esta configuração garante que qualquer requisição recebida via HTTP seja automaticamente redirecionada para HTTPS, com código de status HTTP 301 (Moved Permanently). Isso impede que usuários acessem o sistema por conexões não seguras.

#### 2. HSTS (HTTP Strict Transport Security)

```python
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)  # padrão: 1 ano; ajustável por variável de ambiente
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

O HSTS é um cabeçalho de resposta HTTP que instrui o navegador a sempre acessar o site via HTTPS, mesmo que o usuário digite http:// na barra de endereços. Isso previne ataques de downgrade SSL, onde um atacante força a conexão a usar HTTP.

- SECURE_HSTS_SECONDS: Por quanto tempo o navegador deve lembrar de usar HTTPS. O padrão do código é 31536000 (1 ano), mas o valor é lido da variável de ambiente `SECURE_HSTS_SECONDS`, o que permite implantar o HSTS de forma gradual: a documentação do Django recomenda começar com um valor baixo e aumentá-lo depois de validar que tudo funciona sobre HTTPS. No deploy atual (Render) a variável está definida em 300 segundos (veja "Em Ambiente de Produção").
- SECURE_HSTS_INCLUDE_SUBDOMAINS = True: Aplica HSTS a todos os subdomínios.
- SECURE_HSTS_PRELOAD = True: Permite que o domínio seja incluído na lista de preload do HSTS, mantida pelos principais navegadores.

#### 3. Cookies Seguros

```python
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

Essas configurações garantem que os cookies de sessão (sessionid) e CSRF (csrftoken) só sejam enviados em conexões HTTPS. Isso previne o roubo de sessão via ataques de interceptação de tráfego.

#### 4. Proteções Adicionais

```python
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
```

- SECURE_CONTENT_TYPE_NOSNIFF: Impede que o navegador interprete arquivos como um tipo MIME diferente do declarado, prevenindo ataques de drive-by download.
- SECURE_REFERRER_POLICY = 'same-origin': Controla qual informação de referer é enviada, protegendo a privacidade do usuário.

## Bloqueio de Conexões Não Seguras

### Estratégia de Implementação

O bloqueio de conexões não seguras é implementado em duas camadas:

#### Camada 1: Aplicação (Django)

No ambiente de produção (DEBUG = False), o Django redireciona automaticamente todas as requisições HTTP para HTTPS. Se um usuário tentar acessar http://erp.escola.com.br/login/, será imediatamente redirecionado para https://erp.escola.com.br/login/.

#### Camada 2: Infraestrutura (Servidor Web)

Em um ambiente de produção real, o bloqueio é reforçado pelo servidor web, que:

1. Escuta apenas na porta 443 (HTTPS) para tráfego externo.
2. Redireciona a porta 80 (HTTP) para HTTPS com código 301.
3. Possui certificado SSL/TLS válido.

No deploy atual (Render), essa camada é executada pela borda da plataforma.

# Comunicação Protegida por TLS/HTTPS

## Fluxo de Comunicação Segura

O fluxo de comunicação protegida no ERP Escolar segue estas etapas:

1. **Handshake TLS:** Quando o usuário acessa o sistema, o navegador e o servidor negociam os parâmetros de criptografia e trocam chaves públicas.
2. **Criptografia Simétrica:** Após o handshake, toda a comunicação é criptografada usando uma chave simétrica compartilhada, que é mais rápida que a criptografia assimétrica.
3. **Transmissão de Dados:** Credenciais, tokens 2FA, dados pessoais e todas as requisições/respostas trafegam criptografados.
4. **Validação de Certificado:** O navegador verifica se o certificado SSL/TLS é válido, emitido por uma autoridade certificadora confiável e não expirado.

## Justificativa Técnica

### Por que HTTPS é obrigatório?

1. **Proteção de Credenciais:** Sem HTTPS, senhas e tokens 2FA trafegam em texto puro, podendo ser interceptados por qualquer pessoa na mesma rede (ex: Wi-Fi público).
2. **Conformidade com LGPD:** O Art. 46 da LGPD exige que o controlador adote medidas de segurança para proteger os dados pessoais, incluindo a criptografia no transporte.
3. **Prevenção de Ataques Man-in-the-Middle:** HTTPS previne que atacantes interceptem e modifiquem requisições, como injetar scripts maliciosos ou alterar dados de formulários.
4. **Confiança do Usuário:** Navegadores modernos exibem avisos de "Não Seguro" para sites sem HTTPS, o que prejudica a credibilidade do sistema.

### Por que HSTS é necessário?

O HSTS complementa o HTTPS ao impedir que o usuário acesse o site via HTTP, mesmo que digite manualmente. Sem HSTS, um atacante em uma rede pública poderia interceptar a primeira requisição HTTP (antes do redirecionamento) e realizar um ataque de downgrade.

### Por que cookies seguros são importantes?

Cookies de sessão e CSRF contêm informações sensíveis que, se interceptados, permitem que um atacante sequestre a sessão do usuário ou realize ataques CSRF. A flag Secure garante que esses cookies só sejam enviados em conexões HTTPS.

## Evidências de Implementação

### Em Ambiente de Desenvolvimento

Em desenvolvimento (DEBUG = True), as configurações de HTTPS estão desativadas para facilitar os testes locais. O sistema roda em http://127.0.0.1:8000/ sem criptografia.

### Em Ambiente de Produção

Aplicação publicada em `https://project-school-erp.onrender.com`. As evidências abaixo foram coletadas em 03/11/2026 (relatório do SSL Labs) e em 04/11/2026 (comandos `curl`, executados em rede doméstica, sem proxy corporativo).

#### Onde o TLS é encerrado

As respostas trazem `Server: cloudflare` e, nas respostas da aplicação, `x-render-origin-server: gunicorn`. Ou seja, o TLS é encerrado na borda da plataforma e o Django (gunicorn) roda atrás dela. Por isso, a escolha de versões de protocolo e de cifras e a emissão/renovação do certificado são responsabilidade da plataforma. À aplicação cabe: reconhecer o cabeçalho `X-Forwarded-Proto` (`SECURE_PROXY_SSL_HEADER`), forçar HTTPS (`SECURE_SSL_REDIRECT`), enviar HSTS e marcar os cookies como `Secure`. O trecho interno entre a borda e o gunicorn é da plataforma e não foi avaliado neste projeto.

#### Evidência 1 — Avaliação independente do TLS (Qualys SSL Labs)

Relatórios: `docs/evidencias/evidencia-https-1.pdf` e `docs/evidencias/evidencia-https-2.pdf` (os dois endereços IP do domínio), avaliados em 03/11/2026.

| Item avaliado | Resultado |
|---|---|
| Nota geral | **A** (nos dois endereços) |
| Protocolos habilitados | TLS 1.3 e TLS 1.2 |
| Protocolos desabilitados | TLS 1.1, TLS 1.0, SSL 3 e SSL 2 |
| Suítes de cifras | Somente AEAD (AES-GCM e ChaCha20-Poly1305), todas com sigilo de encaminhamento (Forward Secrecy) |
| Troca de chaves | X25519, com suporte também à troca híbrida pós-quântica (X25519MLKEM768) |
| Certificado | Confiável (Mozilla, Apple, Android, Java, Windows), cadeia sem problemas, não revogado, com Certificate Transparency e política CAA; EC 256 bits (SHA256withECDSA) e RSA 2048 bits (SHA256withRSA); válido até 20/12/2026 |
| Vulnerabilidades conhecidas | Nenhuma detectada (Heartbleed, POODLE, ROBOT, CCS Injection, BEAST mitigado, compressão TLS desativada, entre outras) |
| Prevenção de downgrade | Suportada (`TLS_FALLBACK_SCSV`) |
| HSTS | Presente com `max-age=300; includeSubDomains; preload`; o SSL Labs sinaliza o valor como curto (menos de 180 dias) |
| Fluxo HTTP da aplicação | `https://project-school-erp.onrender.com/` responde 302 e `/accounts/login/` responde 200 |

Observação: no relatório do endereço 216.24.57.16, a etapa de requisição HTTP do teste falhou (o SSL Labs a marca como "Request failed"), por isso os campos de HSTS aparecem como desconhecidos nele; a avaliação do TLS (protocolos, cifras, certificado) foi concluída normalmente e é idêntica à do outro endereço. O relatório completo, com a etapa HTTP, é o do endereço 216.24.57.18.

#### Evidência 2 — Redirecionamento de HTTP para HTTPS

Arquivo: `docs/evidencias/saida_curl_https.txt`.

```text
curl.exe -sI http://project-school-erp.onrender.com
HTTP/1.1 301 Moved Permanently
Location: https://project-school-erp.onrender.com/
```

Uma requisição em HTTP recebe `301` apontando para a versão HTTPS, antes de qualquer dado de formulário ser enviado. A resposta a essa requisição não traz o cabeçalho `x-render-origin-server: gunicorn`, o que indica que o redirecionamento foi emitido pela borda da plataforma; o Django mantém `SECURE_SSL_REDIRECT = True` como segunda camada.

#### Evidência 3 — Cabeçalhos de segurança e cookies na tela de login

```text
curl.exe -sI https://project-school-erp.onrender.com/accounts/login/
HTTP/1.1 200 OK
strict-transport-security: max-age=300; includeSubDomains; preload
Set-Cookie: csrftoken=<valor omitido>; Max-Age=31449600; Path=/; SameSite=Lax; Secure
x-content-type-options: nosniff
x-frame-options: DENY
referrer-policy: same-origin
Cache-Control: max-age=0, no-cache, no-store, must-revalidate, private
```

- `strict-transport-security`: HSTS ativo, com `includeSubDomains` e `preload`.
- `Set-Cookie` do `csrftoken` com `Secure` (só trafega em HTTPS) e `SameSite=Lax`. O cookie de CSRF não tem `HttpOnly` porque esse é o padrão do Django para ele.
- O cookie `sessionid` só é emitido após a autenticação, por isso não aparece nesta requisição anônima. Seus atributos decorrem das configurações `SESSION_COOKIE_SECURE = True` (explícita) e de `HttpOnly` e `SameSite=Lax` (padrões do Django).
- `x-content-type-options`, `x-frame-options` e `referrer-policy` confirmam as proteções adicionais descritas acima. A tela de login não é armazenada em cache.

#### Valor do HSTS em produção

A variável de ambiente `SECURE_HSTS_SECONDS` está definida em 300 segundos (5 minutos) no deploy atual, o que reflete a adoção gradual do HSTS. Esse valor é menor que o padrão do código (1 ano) e que o mínimo exigido para inclusão na lista de preload dos navegadores (1 ano). Depois de validado o funcionamento sobre HTTPS, a variável deve ser elevada para `31536000`; basta alterá-la no painel da plataforma, sem mudança de código.

#### Limitação conhecida

Esta documentação ainda não inclui captura de pacotes (por exemplo, com Wireshark) do tráfego de login em produção. As evidências acima comprovam a configuração do canal (protocolos, cifras, certificado, HSTS, redirecionamento e cookies) e o comportamento do servidor, mas a verificação direta, por captura de rede, de que o corpo da requisição de login trafega cifrado ainda não foi anexada.

| Versão | Data | Alteração | Responsável |
|---|---|---|---|
| 1.0 | 13/10/2026 | Criação do documento, cobrindo os requisitos de criptografia e comunicação segura | Matheus de Castro Viana |
| 1.1 | 04/11/2026 | Evidências de produção (SSL Labs, redirecionamento, cabeçalhos e cookies), HSTS configurável por variável de ambiente e remoção de configuração inexistente (`SECURE_BROWSER_XSS_FILTER`) | Matheus de Castro Viana |

#  Referências

- Django Documentation — Security: https://docs.djangoproject.com/en/6.1/topics/security/
- OWASP Transport Layer Protection Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html
- Mozilla SSL Configuration Generator: https://ssl-config.mozilla.org/
- Qualys SSL Labs — SSL Server Test: https://www.ssllabs.com/ssltest/
- Let's Encrypt Documentation: https://letsencrypt.org/docs/
- RFC 5246 — The Transport Layer Security (TLS) Protocol Version 1.2
- RFC 8446 — The Transport Layer Security (TLS) Protocol Version 1.3
- Lei nº 13.709/2018 (LGPD) — Art. 46 (Medidas de Segurança)