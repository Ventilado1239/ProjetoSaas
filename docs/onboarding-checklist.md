# Checklist de Onboarding de Clientes Piloto (Tenants)

Este guia orienta o administrador na configuração passo a passo para colocar um novo cliente piloto (Tenant) em operação no SaaS.

---

## 1. Configuração de Infraestrutura e Variáveis de Ambiente

### Backend (Railway)
Certifique-se de configurar as seguintes variáveis no painel do Railway do novo Tenant:
- `DATABASE_URL`: URI de conexão segura PostgreSQL (Supabase).
- `JWT_SECRET`: Chave secreta de criptografia para tokens JWT e criptografia `pgcrypto`.
- `JWT_ALGORITHM`: Algoritmo JWT (geralmente `HS256`).
- `ENVIRONMENT`: `production` para habilitar HSTS, HTTPS obrigatório e ocultar stack traces.
- `EVOLUTION_API_URL`: URL base do servidor Evolution API (ex: `https://evo.meuservico.com`).
- `EVOLUTION_API_KEY`: API Key mestre para autenticação na Evolution API.
- `ASAAS_API_URL`: URL do gateway Asaas (`https://www.asaas.com/api/v3` em produção ou `https://sandbox.asaas.com/api/v3` para testes).
- `ASAAS_API_KEY`: Chave de API gerada no painel do Asaas do Tenant.
- `ASAAS_WEBHOOK_SECRET`: Token gerado na configuração do webhook de cobranças do Asaas.

### Frontend (Vercel)
As variáveis necessárias para compilar o app mobile-first na Vercel:
- `VITE_API_URL`: URL de produção do backend hospedado no Railway (ex: `https://backend-production.up.railway.app`).
- `VITE_TENANT_ID`: UUID do Tenant criado no banco de dados.
- `VITE_TENANT_NOME`: Nome da Marca/Clínica/Loja a ser renderizado na dashboard.
- `VITE_TENANT_TIPO`: Tipo do Tenant (`clinica` ou `loja`).
- `VITE_TENANT_COR_PRIMARIA`: Cor hexadecimal customizada do Tenant para personalização visual (ex: `#db2777` para rosa escuro, `#2563eb` para azul).

---

## 2. Provisionamento no Banco de Dados (Supabase)

Execute o seguinte script no SQL Editor do Supabase para registrar o novo Tenant e o primeiro usuário com perfil `dono`:

```sql
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
  '5511999999999', -- WhatsApp Comercial (DDI + DDD + Número)
  'pro', -- plano contratado
  true,
  '08:00',
  '18:00',
  5, -- pedidos com quantidade maior que 5 requerem aprovação
  '#db2777' -- Cor temática
);

-- 3. Inserir o Usuário Dono (Senha inicial gerada com bcrypt hash)
-- Exemplo de hash para a senha 'senha123': '$2b$12$z2SjRUXlVwXGf6kZg4r9uO/vYfNqR14kL6V1WwA7S2W1K3'
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
  '$2b$12$z2SjRUXlVwXGf6kZg4r9uO/vYfNqR14kL6V1WwA7S2W1K3', -- Substituir pelo hash correto
  'dono',
  true
);

END;
```

---

## 3. Configuração do Gateway Asaas

1. Acesse a conta Asaas do Cliente/Tenant.
2. Acesse **Configurações da Conta** > **Integrações** e gere a **Chave de API (Token)**. Salve como `ASAAS_API_KEY` no Railway.
3. Acesse **Configurações** > **Webhooks** > **Webhook de Cobranças**:
   - Defina a URL como: `https://<seu-backend-railway>/webhooks/asaas`.
   - Adicione os seguintes eventos obrigatórios:
     - `PAYMENT_RECEIVED` (recebimento confirmado).
     - `PAYMENT_OVERDUE` (vencimento/inadimplência).
   - Defina o token de segurança secreto e configure a variável `ASAAS_WEBHOOK_SECRET` no Railway correspondente.

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

### ⚠️ Aquecimento de Chip (Importante para evitar Ban do WhatsApp)
O WhatsApp pode banir números novos que começam a disparar muitas mensagens repentinamente. Siga este protocolo de aquecimento na primeira semana:
- **Dia 1 e 2**: Limite de 20 conversas ativas. Envie apenas para amigos/família e peça para que respondam para gerar histórico de conversa bidirecional legítimo.
- **Dia 3 e 4**: Limite de 50 conversas. Intercale mensagens ativas e receptivas de clientes selecionados.
- **Dia 5 em diante**: Aumente gradativamente até 100 mensagens/dia.
- **Dica**: Utilize o delay embutido no `whatsapp_service.py` (randint 3-8s de digitação) que simula digitação humana para evitar detecção automatizada de bots.

---

## 5. Monitoramento com UptimeRobot

Crie monitores gratuitos no UptimeRobot com checagens a cada 5 minutos:
1. **API Backend**: Monitor tipo HTTP(s) apontando para `https://<seu-backend-railway>/health`. Espera código `200 OK`.
2. **Evolution API**: Monitor HTTP(s) apontando para a rota `/health` ou status da Evolution API.
3. **Supabase**: Monitor da porta de conexão direta PostgreSQL ou a API REST do Supabase.
4. **Configuração de Alertas**: Adicione o e-mail/WhatsApp do administrador para receber notificações de queda imediatas.
