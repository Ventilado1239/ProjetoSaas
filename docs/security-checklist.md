# Checklist de Segurança e LGPD — SaaS de Gestão via WhatsApp

Este documento resume as práticas de segurança e conformidade LGPD (Lei Geral de Proteção de Dados) implementadas no backend e banco de dados do SaaS.

---

## 1. Isolamento Multi-tenant (Row Level Security - RLS)

- [x] **RLS Ativo nas tabelas multi-tenant**: Row Level Security habilitado e forçado nas tabelas que contêm dados de clientes.
- [x] **Contexto de Conexão Seguro**: O middleware de autenticação define a variável de conexão `app.tenant_id` no PostgreSQL a cada requisição.
- [x] **Contexto Persistente por Sessão**: A função `set_tenant_id` foi otimizada para persistir o parâmetro por sessão (`is_local=false`), garantindo a propagação automática do RLS mesmo após operações de `COMMIT`/`ROLLBACK` e durante o ciclo de vida de `db.refresh` e pooling.
- [x] **Garantia de Isolamento**: Testes automatizados (`test_rls.py` e `test_security.py`) validam que um Tenant A não consegue realizar nenhuma operação de leitura, escrita ou atualização em dados do Tenant B.

---

## 2. Criptografia no Banco de Dados (`pgcrypto`)

- [x] **Criptografia de PII Sensíveis**: Os campos `nome` e `convenio` da tabela `clientes_pacientes` são gravados de forma criptografada usando PGP simétrico.
- [x] **Utilização do `pgcrypto`**: A criptografia ocorre de forma transparente na camada do banco de dados executando as funções nativas de PostgreSQL `pgp_sym_encrypt` e `pgp_sym_decrypt`.
- [x] **Separação de Chaves**: JWT usa `JWT_SECRET`, PII usa `DATA_ENCRYPTION_KEY` e backups usam `BACKUP_ENCRYPTION_KEY`.
- [x] **Preservação de Desempenho**: O número de telefone (`whatsapp`) é mantido em formato indexado sem PGP padrão para manter unicidade rápida e integridade com o webhook do WhatsApp.
- [x] **Backups Criptografados**: CSVs existem somente em memória e são persistidos como arquivos Fernet autenticados (`.csv.enc`) fora do repositório.

---

## 3. Conformidade LGPD & Direito ao Esquecimento

- [x] **Exclusão Definitiva (Right to be Forgotten)**: Endpoint dedicado `DELETE /clientes/{id}/lgpd` que remove completamente o registro do cliente.
- [x] **Cascata Automática**: Foreign Keys com `ON DELETE CASCADE` garantem a exclusão automática de agendamentos, lista de espera e estados de conversa vinculados.
- [x] **Limpeza de Logs de Mensagem**: O endpoint limpa explicitamente todos os logs históricos de mensagens do banco (`logs_mensagens`) vinculados ao número do cliente deletado.
- [x] **Anonimização de Logs de Auditoria**: Em conformidade com a LGPD, o log de auditoria da exclusão é marcado como `LGPD_DELETE` e as informações PII (como nome e whatsapp) são anonimizadas nos metadados do log de auditoria, retendo apenas o timestamp e o ID da operação para prova legal de conformidade sem retenção de dados pessoais.

---

## 4. Auditoria de Modificações (Logs de Transação)

- [x] **Tabela de Auditoria**: Tabela `logs_auditoria` mapeada com RLS ativo.
- [x] **Captura Automática (SQLAlchemy Event Listener)**: Um listener no evento `before_flush` do SQLAlchemy intercepta todas as inserções, atualizações e deleções de `clientes_pacientes` e `atendimentos_pedidos`.
- [x] **Identificação do Autor**: O listener consome a variável de contexto `current_user_var` (populada no dependency injection de rotas autenticadas) para registrar o email e ID do usuário responsável pela alteração.
- [x] **Histórico Completo**: Armazena no formato JSON o estado anterior (`valores_antigos`) e o novo estado (`valores_novos`) de cada linha mutada.
- [x] **Auditoria Master**: login, criação/alteração de tenants, leads e redefinição de senha são registrados sem armazenar senhas.

---

## 5. Proteção de Borda & Resiliência da API

- [x] **Headers de Segurança Injetados**:
  - `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload` (HSTS)
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'; base-uri 'none';`
  - `Referrer-Policy: no-referrer`
  - `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- [x] **Redirecionamento HTTPS**: Redireciona de forma compulsória requisições HTTP para HTTPS quando em ambiente de produção (Railway).
- [x] **Rate Limiting em Memória**:
  - Máximo de **100 requisições por minuto por IP** (evita brute force e negação de serviço geral).
  - Máximo de **1000 requisições por minuto por Tenant** (evita abusos de cota).
  - Máximo de **20 tentativas de login em 5 minutos por IP**.
- [x] **Proteção CSRF**: cookies `HttpOnly`, `Secure` em produção e `SameSite=Strict`, combinados com validação de origem em operações mutáveis.
- [x] **Webhooks**: autenticação obrigatória em produção, comparação constante de segredos, payload máximo de 1 MB e idempotência persistente.
- [x] **Validação de Entrada**: limites de tamanho, valores monetários não negativos, enums de status e rejeição de campos extras.
- [x] **Container sem Root**: imagem ignora `.env` e dados locais e executa com usuário dedicado sem privilégios.
- [x] **Ocultação de Stack Traces**: Tratador de exceção global configurado para registrar logs detalhados internamente, mas retornar apenas um código JSON limpo `500 Internal Server Error` sem tracebacks vazados em ambiente de produção.

---

## 6. Dados Clínicos e Médicos

- [x] **Dado Clínico Nunca no WhatsApp**: O SaaS é projetado para **não armazenar** nenhum prontuário, diagnóstico, receita médica, sintoma ou histórico de exames clínicos em seu modelo de dados (`models.py`). Toda interação é estritamente administrativa (agendamentos, aprovações de pedido, CRM e faturamento).
- [x] **Testagem**: O teste automatizado `test_no_clinical_data_in_database` analisa os mappers do SQLAlchemy e assegura que nenhum campo de dados clínicos sensíveis possa ser criado ou trafegado nas tabelas do sistema.
