# Documentação — Conformidade com a LGPD (RLGPD 4.1 a RLGPD 4.11)

**Projeto:** ERP Escola Profissionalizante  
**Autores:** Marcos Antônio Ferreira de Araújo e Matheus de Castro Viana  
**Versão do Documento de Requisitos:** 1.1  
**Data da implementação:** 13 de setembro de 2026  
**Entrega:** Projeto Integrador - Conformidade com a LGPD  

---

## Listagem completa dos dados pessoais coletados

**Requisito:** O projeto deverá apresentar uma listagem completa dos dados pessoais coletados pelo sistema.

### Decisão adotada

O inventário de dados pessoais foi documentado no arquivo `docs/lgpd/inventario_dados.md`, organizado por grupo de dados (Funcionário, Aluno, Responsável) e contendo as seguintes colunas para cada dado:

- **Grupo:** Categoria do dado (Identificação, Contato, Profissional, Acadêmico, Financeiro, Logs de Segurança)
- **Dado:** Campo específico coletado
- **Titular:** Pessoa a quem o dado se refere
- **Finalidade:** Razão pela qual o dado é coletado
- **Acesso:** Perfis de usuário que podem visualizar o dado

O inventário está versionado e inclui um histórico de alterações, permitindo rastreabilidade de modificações futuras conforme novos módulos forem implementados.

### Justificativa técnica

A organização em grupos de dados facilita a compreensão do escopo de coleta e permite que cada área (Administrativa, Pedagógica, Financeira) identifique rapidamente quais dados estão sob sua responsabilidade. A inclusão da coluna "Acesso" atende ao princípio de necessidade (art. 6º, III da LGPD), demonstrando que o acesso aos dados é restrito aos perfis com necessidade funcional.

### Evidências

- **Arquivo:** `docs/lgpd/inventario_dados.md`
- **Tabelas:** Funcionário (Usuário), Aluno (módulo futuro), Responsável (módulo futuro)
- **Histórico de alterações:** Versionamento documentado no final do arquivo

---

## Associação de cada dado a uma finalidade

**Requisito:** Cada dado pessoal deverá estar associado a uma finalidade de tratamento documentada.

### Decisão adotada

Cada dado listado no inventário (`docs/lgpd/inventario_dados.md`) possui a coluna **Finalidade** explicitamente preenchida, descrevendo a razão específica para a coleta. Exemplos:

- **Nome e CPF:** "Identificação do colaborador"
- **Telefone:** "Comunicação institucional"
- **Cargo:** "Controle de acesso e permissões"
- **Jornada:** "Gestão administrativa da rotina"
- **Email (logs):** "Autenticação e controle de acesso"
- **IP (logs):** "Auditoria e rastreabilidade"

### Justificativa técnica

A associação explícita entre dado e finalidade atende ao **princípio da finalidade** (art. 6º, I da LGPD), que exige que o tratamento de dados pessoais seja realizado para propósitos legítimos, específicos e explícitos. Isso também facilita a resposta a solicitações de titulares que questionem por que determinado dado está sendo coletado.

### Evidências

- **Arquivo:** `docs/lgpd/inventario_dados.md` (coluna "Finalidade" preenchida para todos os dados)

---

## Evidência de minimização de dados

**Requisito:** O projeto deverá apresentar evidência de minimização de dados, justificando a necessidade dos campos coletados.

### Decisão adotada

A minimização de dados foi aplicada em duas frentes:

1. **No inventário:** A seção "O que é excluído de fato (RF 4.10)" do `inventario_dados.md` documenta explicitamente quais dados **não podem** ser excluídos e por quê.

2. **Na implementação:** O sistema coleta apenas os campos estritamente necessários para cada funcionalidade:
   - **Login:** Apenas e-mail e senha (não solicitamos nome de usuário, data de nascimento, etc.)
   - **Cadastro de funcionário:** Nome, CPF, telefone, cargo e setor são essenciais para identificação única, controle de acesso e comunicação
   - **Auditoria:** IP e user-agent são mínimos necessários para investigação de incidentes

3. **Dados NÃO coletados:**
   - **Data de nascimento:** Não é necessária para as funcionalidades atuais
   - **Endereço residencial:** Sem finalidade definida no escopo atual
   - **RG ou outros documentos:** CPF é suficiente para identificação fiscal
   - **Foto ou biometria:** Sem necessidade para autenticação (2FA via TOTP é suficiente)
   - **Dados bancários:** Serão tratados apenas no módulo financeiro futuro, com criptografia adicional

### Justificativa técnica

O **princípio da necessidade** (art. 6º, III da LGPD) exige que o tratamento de dados pessoais seja limitado ao mínimo necessário para a realização de suas finalidades. Ao documentar explicitamente quais dados são coletados e por quê, e ao justificar a não-coleta de outros dados, o sistema demonstra conformidade com este princípio e reduz o risco de tratamento excessivo ou inadequado.

### Evidências

- **Arquivo:** `docs/lgpd/inventario_dados.md` (seção "O que é excluído de fato")
- **Implementação:** Formulários de cadastro e login coletam apenas campos essenciais
- **Código:** `usuarios/models.py` (modelo Usuario com campos mínimos: email, funcionario, tentativas_login_falhas, bloqueado_ate)

---

## Registro explícito de consentimento

**Requisito:** Quando o consentimento for utilizado como base aplicável, o sistema deverá registrar o consentimento de forma explícita.

### Decisão adotada

Implementado um **popup de consentimento de cookies e tratamento de dados** que é exibido na parte inferior da tela quando o usuário acessa o sistema pela primeira vez (ou quando a versão da política é atualizada).

O popup oferece duas opções:
1. **Aceitar:** Registra o consentimento no `localStorage` do navegador e, se o usuário estiver logado, envia uma requisição POST para a API `/usuarios/api/consentimento/` que registra o evento no log de auditoria.
2. **Recusar:** Registra apenas no `localStorage` (sem enviar ao servidor), respeitando a decisão do usuário de não ser rastreado.

O JavaScript do popup (`static/auth/js/lgpd_consent.js`) utiliza uma versão de consentimento (`CONSENT_VERSION = '1.0'`) que pode ser incrementada quando a política de privacidade for atualizada, forçando o usuário a consentir novamente.

### Justificativa técnica

O registro explícito de consentimento atende ao **art. 8º da LGPD**, que exige que o consentimento seja fornecido por escrito ou por outro meio que demonstre a manifestação de vontade do titular. O uso de `localStorage` com versionamento garante que o consentimento seja rastreável e que o usuário seja notificado de alterações na política.

### Evidências

- **Arquivos:** `usuarios/templates/usuarios/consentimento_popup.html`, `static/auth/js/lgpd_consent.js`
- **Print:** `docs/evidencias/popup-de-consentimento.png`
- **Log de auditoria:** `logs/auditoria_seguranca.log` (registra eventos de consentimento quando usuário está logado)

---

## Consentimento associado à finalidade

**Requisito:** O consentimento deverá estar associado à finalidade específica apresentada ao titular.

### Decisão adotada

O popup de consentimento exibe explicitamente as finalidades do tratamento de dados:

> "Ao continuar navegando, você consente com o tratamento de dados para: **autenticação, segurança, auditoria e melhoria da experiência**."

Além disso, o popup inclui links diretos para a **Política de Privacidade** e **Termos de Uso**, onde cada finalidade é detalhada em seções específicas (ex: "2. Dados Coletados", "3. Finalidade do Tratamento").

No backend, a API de consentimento (`registrar_consentimento_view`) recebe o parâmetro `tipo` (ex: 'privacidade', 'termos', 'marketing'), permitindo que diferentes finalidades sejam registradas separadamente.

### Justificativa técnica

A associação entre consentimento e finalidade atende ao **art. 8º, §1º da LGPD**, que exige que o consentimento seja precedido de informações claras e completas sobre a finalidade do tratamento. Ao apresentar as finalidades de forma resumida no popup e detalhada na política, o sistema garante transparência e consente informado.

### Evidências

- **Arquivo:** `usuarios/templates/usuarios/consentimento_popup.html` (texto do popup)
- **Arquivo:** `usuarios/templates/usuarios/politica_privacidade.html` (seção "3. Finalidade do Tratamento")
- **Código:** `usuarios/views_lgpd.py::registrar_consentimento_view` (parâmetro `tipo`)

---

## Possibilidade de revogação do consentimento

**Requisito:** O sistema deverá permitir o registro da revogação do consentimento quando o tratamento estiver fundamentado nessa hipótese.

### Decisão adotada

A revogação do consentimento pode ser realizada de duas formas:

1. **Via navegador:** O usuário pode limpar o `localStorage` do navegador (chave `lgpd_consentimento_v1.0`), o que fará o popup aparecer novamente na próxima visita, permitindo que ele recuse o consentimento.

2. **Via solicitação formal:** O usuário pode entrar em contato com o encarregado de dados (DPO) através do e-mail (informado na Política de Privacidade) para solicitar a revogação do consentimento registrado no backend.

A função `registrar_consentimento` no `audit.py` aceita o parâmetro `aceitou` (booleano), permitindo registrar tanto o consentimento quanto a revogação no log de auditoria.

### Justificativa técnica

O **art. 8º, §5º da LGPD** estabelece que o titular pode revogar o consentimento a qualquer momento, mediante manifestação expressa. Ao fornecer múltiplos canais para revogação (navegador e contato direto com DPO), o sistema garante que o titular tenha controle efetivo sobre seus dados.

### Evidências

- **Código:** `static/auth/js/lgpd_consent.js` 
- **Código:** `usuarios/audit.py::registrar_consentimento` (parâmetro `aceitou`)
- **Arquivo:** `usuarios/templates/usuarios/politica_privacidade.html` (seção "10. Contato" com e-mail do DPO)

---

## Registro de data e versão do consentimento

**Requisito:** O sistema deverá registrar a data, hora, versão do texto e contexto do consentimento ou da revogação.

### Decisão adotada

O JavaScript do popup (`lgpd_consent.js`) armazena no `localStorage` um objeto JSON contendo:

```javascript
{
    versao: '1.0',
    aceitou: true,
    data: '2026-09-13T18:00:00.000Z',
    url: 'http://127.0.0.1:8000/accounts/login/'
}
```

No backend, a função registrar_consentimento no audit.py registra no log de auditoria:
INFO 2026-09-13 18:00:00,000 audit Consentimento LGPD | Usuário: usuario@email.com | Tipo: privacidade | Versão: 1.0 | Status: Aceito | IP: 127.0.0.1

A versão do consentimento (CONSENT_VERSION = '1.0') está definida como constante no JavaScript e pode ser incrementada quando a política for atualizada.

### Justificativa técnica

O registro de data, hora e versão atende ao art. 8º, §2º da LGPD, que exige que o consentimento seja documentado de forma que possa ser comprovado posteriormente. O versionamento permite que o sistema identifique quais usuários consentiram com qual versão da política, facilitando a gestão de atualizações.

### Evidências

- **Código:** `static/auth/js/lgpd_consent.js` (objeto dadosConsentimento)
- **Código:** `usuarios/audit.py::registrar_consentimento` (registro no log)
- **Log:** `logs/auditoria_seguranca.log` (exemplo de registro de consentimento)

## Funcionalidade de consulta aos dados do titular

**Requisito:** O sistema deverá disponibilizar funcionalidade de consulta aos dados pessoais do titular, conforme o perfil e o procedimento definido.

### Decisão adotada

Implementada a view consultar_dados (usuarios/views_lgpd.py) acessível via /usuarios/meus-dados/, que exibe todos os dados pessoais do usuário logado organizados em seções:

- **Dados da Conta:** E-mail, data de criação, status do 2FA
- **Dados Funcionais:** Nome, CPF, telefone, cargo, setor (se aplicável)
- **Jornada de Trabalho:** Dias e horários (se aplicável)

A view é protegida pelo decorator @login_required, garantindo que apenas o próprio titular (ou um administrador com permissões específicas) possa acessar os dados.

### Justificativa técnica

A funcionalidade de consulta atende ao art. 18, I da LGPD, que garante ao titular o direito de confirmar a existência de tratamento e acessar seus dados pessoais. A organização em seções facilita a compreensão do titular sobre quais dados estão sendo tratados.

### Evidências

- **Arquivo:** `usuarios/templates/usuarios/consultar_dados.html`
- **Código:** `usuarios/views_lgpd.py::consultar_dados`

## Funcionalidade de exportação dos dados

**Requisito:** O sistema deverá disponibilizar funcionalidade de exportação dos dados pessoais do titular em formato estruturado ou em formato definido pelo projeto.

### Decisão adotada

Implementada a view exportar_dados `(usuarios/views_lgpd.py)` acessível via `/usuarios/meus-dados/exportar/`, que gera um arquivo JSON contendo todos os dados pessoais do usuário:

```javascript
{
  "conta": {
    "email": "usuario@email.com",
    "data_criacao": "2026-09-13T18:00:00",
    "dois_fatores_ativo": true
  },
  "funcionario": {
    "nome": "João Silva",
    "cpf": "123.456.789-00",
    "telefone": "(11) 99999-9999",
    "cargo": "Professor",
    "setor": "Pedagógico"
  },
  "jornadas": [
    {
      "dia_semana": "Segunda-feira",
      "hora_inicio": "08:00",
      "hora_fim": "17:00"
    }
  ]
}
```
O arquivo é disponibilizado para download com o nome meus_dados_[email].json, em formato legível e estruturado.

### Justificativa técnica

A exportação em JSON atende ao art. 18, V da LGPD (portabilidade dos dados), permitindo que o titular transfira seus dados para outro sistema. O formato JSON é amplamente suportado e facilita a interoperabilidade entre sistemas.

### Evidências

- **Código:** `usuarios/views_lgpd.py::exportar_dados`

## Funcionalidade de exclusão dos dados pessoais

**Requisito:** O sistema deverá disponibilizar funcionalidade de exclusão dos dados pessoais quando houver fundamento e autorização para a exclusão, preservando registros que precisem ser mantidos por obrigação válida.

### Decisão adotada

Implementada a view solicitar_exclusao (usuarios/views_lgpd.py) acessível via /usuarios/meus-dados/exclusao/, que permite ao usuário solicitar a exclusão de seus dados pessoais. A tela exibe explicitamente:

- **Dados que serão excluídos:** Telefone (único dado que pode ser excluído automaticamente)
- **Dados que NÃO podem ser excluídos:** Nome, CPF, e-mail, senha, cargo, jornada (com justificativa para cada um)

Após a confirmação, o sistema:

- Remove o telefone do cadastro do funcionário (se existir)
- Registra a solicitação no log de auditoria via registrar_solicitacao_exclusao
- Exibe mensagem informando quais dados foram removidos e quais foram preservados

### Justificativa técnica

A exclusão parcial atende ao art. 18, VI da LGPD (eliminação dos dados pessoais tratados com o consentimento do titular), respeitando as exceções previstas no art. 16 (dados necessários para cumprimento de obrigação legal ou regulatória). A transparência sobre quais dados podem ou não ser excluídos evita frustração do titular e demonstra conformidade com a legislação.

### Evidências

- **Arquivo:** usuarios/templates/usuarios/solicitar_exclusao.html
- **Código:** usuarios/views_lgpd.py::solicitar_exclusao
- **Log:** logs/auditoria_seguranca.log (registro de solicitação de exclusão)

## Fluxo de atendimento aos direitos documentado

**Requisito:** O projeto deverá documentar o fluxo de atendimento aos direitos do titular, incluindo solicitação, validação, análise, resposta, exportação, correção, revogação e exclusão quando aplicável.

### Decisão adotada

O fluxo de atendimento aos direitos do titular está documentado no arquivo docs/lgpd/inventario_dados.md, na seção "O que é excluído de fato (RF 4.10)", e complementado pela Política de Privacidade (usuarios/templates/usuarios/politica_privacidade.html), seção "7. Direitos do Titular".

O fluxo completo inclui:

- Consulta de Dados (RLGPD 4.8)
- Exportação de Dados (RLGPD 4.9)
- Exclusão de Dados (RLGPD 4.10)
- Revogação de Consentimento (RLGPD 4.6)

### Justificativa técnica

A documentação do fluxo de atendimento atende ao art. 18 da LGPD e às diretrizes da ANPD (Autoridade Nacional de Proteção de Dados), que recomendam que os controladores de dados estabeleçam procedimentos claros e prazos definidos para resposta às solicitações dos titulares. A automação de consultas e exportações reduz o tempo de resposta e melhora a experiência do titular.

### Evidências

- **Arquivo:** `docs/lgpd/inventario_dados.md` (seção "O que é excluído de fato")
- **Arquivo:** `usuarios/templates/usuarios/politica_privacidade.html` (seção "7. Direitos do Titular")
- **Arquivo:** `usuarios/templates/usuarios/termos_uso.html` (seção "6. Privacidade")