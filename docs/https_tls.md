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
SECURE_HSTS_SECONDS = 31536000  # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

O HSTS é um cabeçalho de resposta HTTP que instrui o navegador a sempre acessar o site via HTTPS, mesmo que o usuário digite http:// na barra de endereços. Isso previne ataques de downgrade SSL, onde um atacante força a conexão a usar HTTP.

- SECURE_HSTS_SECONDS = 31536000: O navegador deve lembrar de usar HTTPS por 1 ano.
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
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = 'same-origin'
```

- SECURE_CONTENT_TYPE_NOSNIFF: Impede que o navegador interprete arquivos como um tipo MIME diferente do declarado, prevenindo ataques de drive-by download.
- SECURE_BROWSER_XSS_FILTER: Ativa o filtro XSS nativo do navegador.
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

Será definido após a realização do deploy.

| Versão | Data | Alteração | Responsável |
|---|---|---|---|
| 1.0 | 13/10/2026 | Criação do documento, cobrindo os requisitos de criptografia e comunicação segura | Matheus de Castro Viana |

#  Referências

- Django Documentation — Security: https://docs.djangoproject.com/en/6.1/topics/security/
- OWASP Transport Layer Protection Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html
- Mozilla SSL Configuration Generator: https://ssl-config.mozilla.org/
- Let's Encrypt Documentation: https://letsencrypt.org/docs/
- RFC 5246 — The Transport Layer Security (TLS) Protocol Version 1.2
- RFC 8446 — The Transport Layer Security (TLS) Protocol Version 1.3
- Lei nº 13.709/2018 (LGPD) — Art. 46 (Medidas de Segurança)