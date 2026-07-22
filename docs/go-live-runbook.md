# Runbook de Go-Live

Este documento é o gate operacional para liberar vendas. Um item sem evidência deve ser tratado como pendente.

## 1. Infraestrutura

- Backend em um único replica Railway enquanto o agendador estiver embutido na API.
- PostgreSQL gerenciado com backups automáticos e recuperação point-in-time habilitados.
- Volume persistente montado no Railway e `BACKUP_DIR` apontando para ele (ex.: `/data/backups`).
- Frontend Vercel com `VITE_API_URL` apontando para a API HTTPS.
- Domínios e TLS válidos; `ALLOWED_HOSTS` inclui o host da API e `healthcheck.railway.app`.
- Monitor externo em `/health`, pois o healthcheck de deploy não substitui monitoramento contínuo.

## 2. Segredos

- Gere valores aleatórios e diferentes para `JWT_SECRET`, `DATA_ENCRYPTION_KEY`, `BACKUP_ENCRYPTION_KEY`, `EVOLUTION_WEBHOOK_SECRET` e `ASAAS_WEBHOOK_SECRET`.
- Armazene chaves somente no Railway/Vercel. Nunca em Git, documentação, tickets ou mensagens.
- Use uma conta PostgreSQL restrita em `DATABASE_URL`; reserve `MIGRATION_DATABASE_URL` para o entrypoint.
- Marque variáveis de produção como sensíveis e mantenha credenciais diferentes no staging.

## 3. Homologação Asaas

1. Use `https://api-sandbox.asaas.com/v3`, chave Sandbox e `ASAAS_BILLING_ENABLED=true` no staging.
2. Configure `/webhooks/asaas` com token exclusivo de 32 a 255 caracteres.
3. No Painel Master, crie uma assinatura de teste.
4. Confirme `PAYMENT_OVERDUE`: até quatro dias deve marcar atraso; com cinco dias deve suspender o tenant.
5. Confirme `PAYMENT_RECEIVED`: deve reativar e marcar `em_dia`.
6. Reenvie o mesmo evento: a resposta deve ser `duplicate` e não pode duplicar efeitos.
7. Somente depois troque para `https://api.asaas.com/v3` e para a chave de produção.

## 4. Homologação WhatsApp

1. Crie uma instância dedicada por tenant.
2. Configure apenas `MESSAGES_UPSERT` para `/whatsapp/webhook` com segredo autenticado.
3. Teste texto, áudio, imagem, documento, mensagem de grupo, mensagem enviada pelo próprio bot e evento repetido.
4. Teste dentro e fora do horário, suspensão financeira e retomada.
5. Obtenha consentimento, implemente o processo de opt-out e respeite as políticas vigentes do WhatsApp.

## 5. Recuperação e incidentes

- O CSV criptografado da aplicação é uma exportação por tenant, não substitui o backup integral do PostgreSQL.
- Execute um restore do backup gerenciado em um projeto PostgreSQL isolado e valide login, clientes, agenda, serviços e auditoria.
- Registre RPO/RTO obtidos, responsável pelo incidente e canal de escalonamento.
- Em vazamento de chave: revogue no provedor, gere outra, atualize o ambiente, redeploy e revise logs.

## 6. Liberação comercial

- Política de privacidade, termos de uso, contrato, cancelamento, suporte e contato de privacidade publicados e revisados por profissional qualificado.
- Nicho, planos, limites, preço, onboarding e canal de suporte definidos.
- Primeiro lote limitado a 3–5 clientes piloto, com acompanhamento diário na primeira semana.

## Evidências mínimas

- URL do deploy e horário do teste.
- Resultado da suíte automatizada.
- IDs de eventos Sandbox testados (sem chaves ou dados pessoais).
- Data do restore drill e duração.
- Nome do responsável que aprovou o go-live.
