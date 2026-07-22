# Checklist de Onboarding de Clientes Piloto (Tenants)

Este guia orienta o administrador na configuração passo a passo para colocar um novo cliente piloto (Tenant) em operação no SaaS.

---

## 1. Configuração de Infraestrutura e Variáveis de Ambiente

### Backend (Railway)
Certifique-se de configurar as seguintes variáveis no painel do Railway do novo Tenant:
- `DATABASE_URL`: URI de conexão segura PostgreSQL (Supabase), usando um papel sem privilégios administrativos.
- `MIGRATION_DATABASE_URL`: URI administrativa usada somente no início do deploy para `alembic upgrade head`; o entrypoint a remove antes de iniciar a API.
- `DATABASE_APP_ROLE`: papel usado pela aplicação (por exemplo, `saas_app_user`). Nunca use `postgres` no runtime.
- `JWT_SECRET`: chave aleatória exclusiva para assinatura dos tokens JWT (mínimo de 32 caracteres).
- `DATA_ENCRYPTION_KEY`: chave aleatória separada para criptografia de PII (mínimo de 32 caracteres e diferente de `JWT_SECRET`).
- `JWT_ALGORITHM`: Algoritmo JWT (geralmente `HS256`).
- `ENVIRONMENT`: `production` para habilitar HSTS, HTTPS obrigatório e ocultar stack traces.
- `CORS_ORIGINS`: somente os domínios HTTPS reais do frontend, separados por vírgula.
- `ALLOWED_HOSTS`: hosts públicos exatos da API, separados por vírgula. No Railway, inclua também `healthcheck.railway.app`.
- `EVOLUTION_API_URL`: URL base do servidor Evolution API (ex: `https://evo.meuservico.com`).
- `EVOLUTION_API_KEY`: API Key mestre para autenticação na Evolution API.
- `EVOLUTION_WEBHOOK_SECRET`: segredo aleatório enviado no header `X-Webhook-Secret` ou no parâmetro `webhook_secret` da URL configurada na Evolution.
- `ASAAS_API_URL`: `https://api.asaas.com/v3` em produção ou `https://api-sandbox.asaas.com/v3` em homologação.
- `ASAAS_API_KEY`: chave da conta Asaas usada pelo SaaS para criar clientes e assinaturas.
- `ASAAS_BILLING_ENABLED`: mantenha `false` até o Sandbox passar; use `true` para habilitar a criação automática.
- `ASAAS_WEBHOOK_SECRET`: token exclusivo do webhook, com no mínimo 32 caracteres e diferente da API key.
- `BACKUP_DIR`: caminho absoluto de um volume persistente, fora do repositório.
- `BACKUP_ENCRYPTION_KEY`: chave exclusiva para criptografia autenticada dos backups.

Em produção, a aplicação recusa iniciar quando uma dessas proteções obrigatórias está ausente ou insegura.

### Frontend (Vercel)
Variável necessária para compilar o app mobile-first na Vercel:
- `VITE_API_URL`: URL de produção do backend hospedado no Railway (ex: `https://backend-production.up.railway.app`).

Nome, tipo, logo e cor do tenant são obtidos pela API depois do login; não coloque identificadores de tenant no bundle público.

### Webhooks

- Evolution API: configure a URL como `https://api.seudominio.com/whatsapp/webhook?webhook_secret=SEU_SEGREDO` caso o seu proxy não consiga adicionar `X-Webhook-Secret`.
- Asaas: configure `https://api.seudominio.com/webhooks/asaas` e use exatamente o token de `ASAAS_WEBHOOK_SECRET` no header `asaas-access-token`.
- Nunca coloque `tenant_id` manualmente na URL do webhook. O tenant é resolvido pela instância autenticada.

---

## 2. Provisionamento no Banco de Dados (Supabase)

Use o **Painel Master > Nova clínica** para registrar o tenant e o primeiro usuário. O painel aplica validação de senha, normaliza dados e registra auditoria. Não faça inserts manuais no SQL Editor durante a operação normal.

```text
-- 1. Gerar UUIDs para o novo Tenant e Usuário
-- (Substitua por novos UUIDs gerados ou use gen_random_uuid())
DECLARE 
  new_tenant_id UUID := 'seu-uuid-de-tenant-aqui';
  new_user_id UUID := 'seu-uuid-de-usuario-aqui';
BEGIN

-- 2. Inserir o Tenant
INSERT INTO tenants (
  id, 
  nome, 
  tipo, 
  whatsapp_numero,
  owner_whatsapp,
  evolution_instance_name,
  plano, 
  sistema_ativo, 
  horario_abertura, 
  horario_fechamento, 
  limite_pedido_grande, 
  cor_primaria
) VALUES (
  new_tenant_id,
  'Nome do Piloto (Ex: Loja de Personalizados)',
  'loja', -- 'loja' ou 'clinica'
  '5511999999999', -- WhatsApp Comercial (DDI + DDD + Numero)
  '5511888888888', -- WhatsApp do dono/responsavel por alertas
  'tenant_loja_personalizados', -- Nome exato da instancia na Evolution API
  'pro', -- plano contratado
  true,
  '08:00',
  '18:00',
  5, -- pedidos com quantidade maior que 5 requerem aprovação
  '#db2777' -- Cor temática
);

-- 3. Inserir o Usuário Dono (gere uma senha forte e o hash bcrypt com provision_tenant.py)
INSERT INTO usuarios (
  id, 
  tenant_id, 
  nome, 
  email, 
  senha_hash, 
  perfil, 
  ativo
) VALUES (
  new_user_id,
  new_tenant_id,
  'Nome do Dono',
  'dono@email.com',
  'HASH_BCRYPT_GERADO_PELO_PROVISIONAMENTO', -- Nunca reutilize hashes ou senhas de exemplos
  'dono',
  true
);

END;
```

O bloco acima fica apenas como referência histórica e não deve ser executado em produção.

---

## 3. Configuração do Gateway Asaas

1. Configure primeiro uma conta Sandbox do Asaas e execute todo o roteiro de homologação.
2. Gere a chave de API e salve-a somente no gerenciador de variáveis do Railway.
3. Acesse **Configurações** > **Webhooks** > **Webhook de Cobranças**:
   - Defina a URL como: `https://<seu-backend-railway>/webhooks/asaas`.
   - Adicione os seguintes eventos obrigatórios:
     - `PAYMENT_RECEIVED` (recebimento confirmado).
     - `PAYMENT_OVERDUE` (vencimento/inadimplência).
   - Defina o token de segurança secreto e configure a variável `ASAAS_WEBHOOK_SECRET` no Railway correspondente.
4. No Painel Master, abra **Cobrança** no cliente para criar a assinatura. O CPF/CNPJ é enviado diretamente ao Asaas e não é persistido pelo SaaS.

---

## 4. Configuração do WhatsApp (Evolution API)

1. **Criar Instância**: Crie uma nova instância dedicada para o Tenant utilizando a Evolution API.
   - Endpoint: `POST /instance/create`
   - Payload:
     ```json
     {
       "instanceName": "tenant_loja_personalizados",
       "token": "token_opcional_seguro",
       "qrcode": true
     }
     ```
2. **Pareamento QR Code**: Acesse o retorno do endpoint anterior (ou use o endpoint `/instance/connect`) para renderizar o QR Code no navegador e escaneie pelo WhatsApp comercial do cliente.
3. **Registrar Webhook**: Configure o webhook da instância Evolution para enviar eventos de mensagens para o backend da aplicação.
   - Endpoint: `POST /webhook/set/tenant_loja_personalizados`
   - Payload:
     ```json
     {
       "enabled": true,
       "url": "https://<seu-backend-railway>/whatsapp/webhook",
       "events": [
         "MESSAGES_UPSERT"
       ]
     }
     ```

### Uso responsável do WhatsApp

- Envie mensagens somente a contatos com base legal e consentimento quando aplicável.
- Respeite opt-out, frequência razoável e as políticas vigentes do WhatsApp.
- Não use automação para contornar mecanismos anti-spam. Para escala comercial e menor risco de bloqueio, planeje a migração para a API oficial do WhatsApp Business.

---

## 5. Monitoramento com UptimeRobot

Crie monitores gratuitos no UptimeRobot com checagens a cada 5 minutos:
1. **API Backend**: Monitor tipo HTTP(s) apontando para `https://<seu-backend-railway>/health`. Espera código `200 OK`.
2. **Evolution API**: Monitor HTTP(s) apontando para a rota `/health` ou status da Evolution API.
3. **Supabase**: Monitor da porta de conexão direta PostgreSQL ou a API REST do Supabase.
4. **Configuração de Alertas**: Adicione o e-mail/WhatsApp do administrador para receber notificações de queda imediatas.
