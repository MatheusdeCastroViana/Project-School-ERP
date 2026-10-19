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

TLS garante confidencialidade (conteúdo cifrado), integridade (alteração em trânsito é detectada) e autenticidade (o certificado comprova a identidade do servidor). A LGPD (art. 46) exige medidas técnicas de segurança para proteger dados pessoais, o que inclui o transporte.

### Evidências

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

- **`SECURE_SSL_REDIRECT`:** toda requisição HTTP recebe redirecionamento permanente (301) para HTTPS.
- **HSTS:** o cabeçalho `Strict-Transport-Security` instrui o navegador a usar sempre HTTPS pelo prazo configurado (padrão de 1 ano, ajustável por variável de ambiente). Previne ataques de downgrade. A inclusão na lista de preload dos navegadores depende de o domínio ser registrado nessa lista; a diretiva fica habilitada para quando o sistema for publicado em domínio próprio.
- **Cookies seguros:** `sessionid` e `csrftoken` só são enviados em conexões HTTPS.
- **`SECURE_CONTENT_TYPE_NOSNIFF`:** impede o navegador de reinterpretar o tipo MIME declarado.
- **`SECURE_REFERRER_POLICY = 'same-origin'`:** o endereço de origem só é enviado a páginas do mesmo site.

O bloqueio é feito em duas camadas: a aplicação (redirecionamento e HSTS, acima) e a infraestrutura (a plataforma de hospedagem expõe o serviço por HTTPS e encaminha a porta 80 para a 443).

### Justificativa técnica

O redirecionamento sozinho deixa a primeira requisição HTTP exposta; o HSTS fecha essa janela nas visitas seguintes. Cookies com a flag `Secure` impedem o sequestro de sessão por interceptação em redes abertas.

### Evidências

- **Configuração:** `config/settings.py`
- **Teste de redirecionamento:** `curl -I http://<dominio>/` deve responder `301` com `Location: https://<dominio>/`.
- **Teste do HSTS:** `curl -I https://<dominio>/` deve incluir o cabeçalho `Strict-Transport-Security`.

---

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

## Histórico de alterações

| Versão | Data | Alteração | Responsável |
|---|---|---|---|
| 1.0 | 13/10/2026 | Criação do documento, cobrindo os requisitos de criptografia e comunicação segura | Matheus de Castro Viana |
| 1.1 | 18/10/2026 | Revisão: configuração real de produção (proxy, HSTS configurável), remoção de opção inexistente, verificação por certificado e captura | Marcos Antônio Ferreira de Araújo e Matheus de Castro Viana |

## Referências

- Django Documentation — Security: https://docs.djangoproject.com/en/6.1/topics/security/
- OWASP Transport Layer Protection Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html
- Mozilla SSL Configuration Generator: https://ssl-config.mozilla.org/
- RFC 8446 — The Transport Layer Security (TLS) Protocol Version 1.3
- RFC 6797 — HTTP Strict Transport Security (HSTS)
- Lei nº 13.709/2018 (LGPD) — Art. 46 (Medidas de Segurança)