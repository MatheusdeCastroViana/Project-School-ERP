# Documentação — Segurança de Transporte (HTTPS/TLS)

**Projeto:** ERP Escola Profissionalizante
**Autores:** Marcos Antônio Ferreira de Araújo e Matheus de Castro Viana
**Versão do Documento:** 1.1
**Entrega:** Projeto Integrador — Criptografia e Comunicação Segura

---

## Introdução

Sem criptografia no canal entre cliente e servidor, credenciais, códigos 2FA, tokens e dados pessoais trafegam em texto puro. Este documento descreve como o ERP Escola Profissionalizante protege o transporte com HTTPS/TLS e atende aos requisitos RS 3.1, 3.2 e 3.3.

O comportamento depende do ambiente, controlado pela variável `DEBUG`: em desenvolvimento (`DEBUG=True`) as proteções de transporte ficam desligadas para permitir testes em `http://127.0.0.1:8000/`; em produção (`DEBUG=False`) todas ficam ativas.

---

## Comunicação protegida por TLS/HTTPS (RS 3.1)

**Requisito:** A comunicação entre cliente e servidor deverá ser protegida por TLS, utilizando HTTPS em ambientes de acesso real.

### Decisão adotada

A aplicação é publicada na plataforma Render, que termina o TLS no seu proxy e entrega a requisição à aplicação Django por HTTP interno, acrescentando o cabeçalho `X-Forwarded-Proto`. O Django é configurado para reconhecer esse cabeçalho:

```python
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

Sem essa configuração, o Django consideraria toda requisição insegura e entraria em laço de redirecionamento.

### Justificativa técnica

```python
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)  # padrão: 1 ano; ajustável por variável de ambiente
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```
TLS garante confidencialidade (conteúdo cifrado), integridade (alteração em trânsito é detectada) e autenticidade (o certificado comprova a identidade do servidor). A LGPD (art. 46) exige medidas técnicas de segurança para proteger dados pessoais, o que inclui o transporte.

### Evidências

- SECURE_HSTS_SECONDS: Por quanto tempo o navegador deve lembrar de usar HTTPS. O padrão do código é 31536000 (1 ano), mas o valor é lido da variável de ambiente `SECURE_HSTS_SECONDS`, o que permite implantar o HSTS de forma gradual: a documentação do Django recomenda começar com um valor baixo e aumentá-lo depois de validar que tudo funciona sobre HTTPS. No deploy atual (Render) a variável está definida em 300 segundos (veja "Em Ambiente de Produção").
- SECURE_HSTS_INCLUDE_SUBDOMAINS = True: Aplica HSTS a todos os subdomínios.
- SECURE_HSTS_PRELOAD = True: Permite que o domínio seja incluído na lista de preload do HSTS, mantida pelos principais navegadores.
- **Configuração:** `config/settings.py` (bloco `if not DEBUG`)
- **Verificação do certificado:** `openssl s_client -connect <dominio>:443 -servername <dominio>` mostra a cadeia de certificados, a versão do TLS e o cifrador negociado; o cadeado do navegador exibe o emissor e a validade.

---

## Bloqueio de conexões não seguras (RS 3.2)

**Requisito:** O sistema deverá bloquear ou redirecionar conexões não seguras para uma conexão protegida, conforme o ambiente de implantação.

### Decisão adotada

Em produção, `config/settings.py` ativa:

```python
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
```

- SECURE_CONTENT_TYPE_NOSNIFF: Impede que o navegador interprete arquivos como um tipo MIME diferente do declarado, prevenindo ataques de drive-by download.
- SECURE_REFERRER_POLICY = 'same-origin': Controla qual informação de referer é enviada, protegendo a privacidade do usuário.

## Bloqueio de Conexões Não Seguras

### Estratégia de Implementação

O bloqueio de conexões não seguras é implementado em duas camadas:

O bloqueio é feito em duas camadas: a aplicação (redirecionamento e HSTS, acima) e a infraestrutura (a plataforma de hospedagem expõe o serviço por HTTPS e encaminha a porta 80 para a 443).

### Justificativa técnica

O redirecionamento sozinho deixa a primeira requisição HTTP exposta; o HSTS fecha essa janela nas visitas seguintes. Cookies com a flag `Secure` impedem o sequestro de sessão por interceptação em redes abertas.

### Evidências

- **Configuração:** `config/settings.py`
- **Teste de redirecionamento:** `curl -I http://<dominio>/` deve responder `301` com `Location: https://<dominio>/`.
- **Teste do HSTS:** `curl -I https://<dominio>/` deve incluir o cabeçalho `Strict-Transport-Security`.

No deploy atual (Render), essa camada é executada pela borda da plataforma.

# Comunicação Protegida por TLS/HTTPS

## Fluxo de Comunicação Segura

O fluxo de comunicação protegida no ERP Escolar segue estas etapas:

1. **Handshake TLS:** Quando o usuário acessa o sistema, o navegador e o servidor negociam os parâmetros de criptografia e trocam chaves públicas.
2. **Criptografia Simétrica:** Após o handshake, toda a comunicação é criptografada usando uma chave simétrica compartilhada, que é mais rápida que a criptografia assimétrica.
3. **Transmissão de Dados:** Credenciais, tokens 2FA, dados pessoais e todas as requisições/respostas trafegam criptografados.
4. **Validação de Certificado:** O navegador verifica se o certificado SSL/TLS é válido, emitido por uma autoridade certificadora confiável e não expirado.

## Justificativa Técnica

## Tráfego cifrado verificável (RS 3.3)

**Requisito:** O sistema deverá utilizar tráfego cifrado, verificável por inspeção do certificado ou captura controlada.

### Decisão adotada

A verificação é feita por inspeção do certificado (procedimento da seção RS 3.1) e por captura controlada do tráfego com as ferramentas de desenvolvedor do navegador (aba Rede e aba Segurança) ou com um analisador de pacotes. Na captura, o conteúdo das requisições de login e de 2FA aparece cifrado, sem exposição de credenciais ou dados pessoais.

### Fluxo da comunicação segura

1. **Handshake TLS:** navegador e servidor negociam os parâmetros de criptografia e o navegador valida o certificado (emissor confiável, validade e nome do servidor).
2. **Criptografia simétrica:** concluído o handshake, todo o tráfego é cifrado com uma chave simétrica de sessão.
3. **Transmissão:** credenciais, códigos 2FA, tokens de recuperação e dados pessoais trafegam cifrados.

---

## IP do cliente atrás do proxy

Atrás do proxy da hospedagem, o IP da conexão é o do proxy. Para que os logs de auditoria registrem o IP real, o `IPClienteMiddleware` copia o cabeçalho `IP_CLIENTE_CABECALHO` (`HTTP_TRUE_CLIENT_IP`) para `REMOTE_ADDR`, aceitando apenas valores que sejam endereços IP válidos. Em desenvolvimento o middleware fica desligado. Detalhes em `auditoria_logs.md`.

---

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

## Referências

- Django Documentation — Security: https://docs.djangoproject.com/en/6.1/topics/security/
- OWASP Transport Layer Protection Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html
- Mozilla SSL Configuration Generator: https://ssl-config.mozilla.org/
- Qualys SSL Labs — SSL Server Test: https://www.ssllabs.com/ssltest/
- Let's Encrypt Documentation: https://letsencrypt.org/docs/
- RFC 5246 — The Transport Layer Security (TLS) Protocol Version 1.2
- RFC 8446 — The Transport Layer Security (TLS) Protocol Version 1.3
- RFC 6797 — HTTP Strict Transport Security (HSTS)
- Lei nº 13.709/2018 (LGPD) — Art. 46 (Medidas de Segurança)