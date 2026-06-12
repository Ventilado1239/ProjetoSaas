# PRD — SaaS de Gestão via WhatsApp

## 1. Overview

### Product Summary
Sistema SaaS multi-tenant de gestão operacional via WhatsApp para clínicas médicas, odontológicas e lojas de personalizados. Automatiza atendimento, agendamento, confirmações, reativação de clientes inativos, relatórios e fechamento do dia — tudo de forma autônoma, segura e escalável.

### Objective
Este PRD descreve os requisitos funcionais e técnicos do produto real, pronto para ser vendido a R$397–997/mês por cliente. Não é um protótipo — é a base de um negócio recorrente com meta de 3 clientes novos por mês.

### Market Differentiation
Bots de WhatsApp viraram commodity a R$50/mês. Este produto se posiciona como **sistema de retenção e reativação que gera ROI mensurável**. O cliente vê em reais quanto o sistema gerou no mês. Clínica com 25% de falta que reduz para 10% recupera R$10.560/mês — o sistema custa R$997. ROI de 10x impossível de cancelar.

### Magic Moment
O dono da clínica acessa o dashboard segunda-feira às 8h e vê: "O sistema reativou 12 pacientes inativos esse mês e gerou R$8.400 em consultas." Esse relatório mensal de ROI é o momento que garante a renovação do contrato.

### Success Criteria
- Sistema rodando 24h com comportamento indistinguível de atendente humano no WhatsApp
- Taxa de bloqueio de número zero após 30 dias de operação
- Primeiro cliente piloto (loja de personalizados) validado em 6 semanas
- Dashboard acessível em menos de 1 segundo no celular

---

## 2. Technical Architecture

### Architecture Overview

```
[WhatsApp do cliente/paciente]
           ↓
    [Evolution API]
           ↓
    [Backend Python — FastAPI]  ← ÚNICO BACKEND PARA TODOS OS TENANTS
           ↓
    [Supabase — PostgreSQL]     ← ÚNICO BANCO PARA TODOS OS TENANTS
           ↓
    [Frontend React + Tailwind] ← UM DEPLOY POR CLIENTE (mesma base, config diferente)
```

### Multi-tenancy
- Cada cliente é um `tenant` isolado por `tenant_id` em todas as tabelas
- Row Level Security (RLS) no Supabase: tenant A nunca vê dados do tenant B
- Frontend: mesmo código React, deploy separado no Vercel com variáveis de ambiente do tenant
- Novo cliente = criar tenant no banco + configurar deploy do front. Zero novo backend.

### Chosen Stack

| Layer | Escolha | Motivo |
|---|---|---|
| Backend | Python 3.12 + FastAPI | Async, rápido, tipado, excelente para automações |
| ORM | SQLAlchemy 2.0 async + asyncpg | Performance máxima com PostgreSQL |
| Validação | Pydantic v2 | Segurança nos inputs, serialização automática |
| Auth | JWT + refresh token rotation | Seguro, stateless, padrão de mercado |
| Agendamento | APScheduler | Cron jobs para as 13 automações |
| WhatsApp | Evolution API via httpx async | Self-hosted, sem custo de API oficial |
| PDF | ReportLab | Geração de relatórios diários e mensais |
| Logs | structlog (JSON) | Auditoria completa para LGPD |
| Frontend | React 18 + Vite + Tailwind | Velocidade de desenvolvimento + mobile-first |
| Gráficos | Recharts | Integrado no ecossistema React |
| Estado | Zustand | Leve e simples |
| Banco | Supabase (PostgreSQL 15+) | RLS nativo, grátis até escalar, São Paulo |
| Infra backend | Railway | Self-hosted, R$25/mês |
| Infra frontend | Vercel | Grátis por deploy, CDN global |
| Monitoramento | UptimeRobot | Alertas a cada 5 minutos |
| Cobrança | Asaas | Kill switch automático por inadimplência |
| Contrato | ClickSign | Assinatura digital antes de qualquer instalação |
| Testes | pytest + pytest-asyncio | Cobertura completa |

### Repository Structure

```
saas-gestao/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, middlewares, routers
│   │   ├── config.py                # Settings via pydantic-settings
│   │   ├── database.py              # Conexão async Supabase
│   │   ├── dependencies.py          # get_current_user, get_tenant_id
│   │   ├── models/                  # SQLAlchemy models (10 tabelas)
│   │   ├── schemas/                 # Pydantic schemas request/response
│   │   ├── routers/                 # Endpoints da API
│   │   ├── services/                # Lógica de negócio
│   │   ├── tasks/                   # APScheduler — 13 automações
│   │   └── utils/                   # Segurança, mensagens, formatadores
│   ├── alembic/                     # Migrations
│   ├── tests/                       # pytest
│   ├── .env.example
│   ├── requirements.txt
│   ├── Dockerfile
│   └── railway.toml
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── BottomNav.tsx        # Mobile navigation
│   │   │   ├── Dashboard.tsx        # Visão do dia
│   │   │   ├── Agenda.tsx           # Consultas/pedidos
│   │   │   ├── Clientes.tsx         # CRM de clientes/pacientes
│   │   │   ├── ListaEspera.tsx
│   │   │   ├── Servicos.tsx         # CRUD de serviços e preços
│   │   │   ├── Relatorios.tsx       # ROI e exportações
│   │   │   ├── Aprovacoes.tsx       # Pedidos grandes pendentes
│   │   │   ├── Configuracoes.tsx
│   │   │   └── KillSwitchBanner.tsx # Alerta de sistema pausado
│   │   ├── context/
│   │   │   └── AuthContext.tsx
│   │   ├── config/
│   │   │   └── tenant.ts            # Config injetada no deploy
│   │   ├── hooks/
│   │   ├── services/
│   │   │   └── api.ts               # Axios com interceptors JWT
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── .env.example
│   └── vite.config.ts
└── docs/
    ├── design.md
    ├── prd.md
    └── product-roadmap.md
```

### Infrastructure & Deployment

- **Backend**: Railway — `railway up` — URL pública automática
- **Frontend**: Vercel — `vercel --prod` — um projeto por cliente com variáveis de ambiente
- **Banco**: Supabase já criado — `https://rtysmuxbscxrgpwzqmwy.supabase.co`
- **Monitoramento**: UptimeRobot verificando backend, evolution API e Supabase a cada 5 minutos

### Security Considerations

- JWT com expiração de 1h + refresh token de 7 dias com rotation
- RLS ativo em todas as 10 tabelas — tenant A jamais acessa dados do tenant B
- Service role key do Supabase apenas no backend — nunca no frontend
- Rate limiting: 100 req/min por IP, 1000 req/min por tenant
- CORS: apenas domínios cadastrados dos clientes
- Dado clínico (diagnóstico, resultado) NUNCA trafega pelo WhatsApp
- Headers de segurança: HSTS, X-Frame-Options, CSP, X-Content-Type-Options
- Logs de auditoria para conformidade LGPD

### Cost Estimate por cliente

| Item | Custo mensal |
|---|---|
| Evolution API | ~R$80 |
| Railway (rateado) | ~R$25 |
| Supabase | Grátis |
| Vercel | Grátis |
| **Total** | **~R$105/mês** |

Margem com mensalidade de R$397: ~R$292/mês por cliente.

---

## 3. Data Model

### Entity Definitions

```typescript
// Tenant — cada cliente do SaaS
interface Tenant {
  id: string;
  nome: string;
  tipo: 'clinica' | 'loja';
  whatsapp_numero: string;
  plano: 'starter' | 'pro' | 'premium';
  sistema_ativo: boolean;          // KILL SWITCH
  horario_abertura: string;
  horario_fechamento: string;
  limite_pedido_grande: number;
  cor_primaria: string;            // Personalização visual do front
  logo_url?: string;
}

// Cliente/Paciente
interface ClientePaciente {
  id: string;
  tenant_id: string;
  nome: string;
  whatsapp: string;                // unique por tenant
  data_nascimento?: string;
  convenio?: string;               // para clínicas
  total_atendimentos: number;
  ticket_medio: number;
  ultima_consulta?: string;
  status_reativacao: 'ativo' | 'inativo_3m' | 'inativo_6m' | 'inativo_12m' | 'reativado';
}

// Serviço/Produto
interface ServicoProduto {
  id: string;
  tenant_id: string;
  nome: string;
  categoria?: string;
  duracao_minutos?: number;        // para clínicas
  ativo: boolean;
}

// Faixa de Preço
interface Preco {
  id: string;
  tenant_id: string;
  servico_id: string;
  qtd_min: number;
  qtd_max: number;
  preco_particular: number;
  preco_convenio?: number;
  convenio?: string;
}

// Atendimento/Pedido
interface AtendimentoPedido {
  id: string;
  tenant_id: string;
  cliente_id: string;
  data_agendamento: string;
  data_atendimento?: string;
  data_entrega?: string;           // para lojas
  status: 'aguardando' | 'confirmado' | 'em_producao' | 'pronto' | 'realizado' | 'entregue' | 'cancelado' | 'falta' | 'abandonado';
  confirmado: boolean;
  compareceu?: boolean;
  total: number;
  pago: boolean;
  lojista_aprovado: boolean;
  origem: 'whatsapp' | 'dashboard';
}

// Item do Atendimento
interface ItemAtendimento {
  id: string;
  tenant_id: string;
  atendimento_id: string;
  servico_id: string;
  quantidade: number;
  preco_unitario: number;
  personalizacao?: string;
  arquivo_arte_url?: string;
  status_arte: 'aguardando' | 'enviado' | 'aprovado' | 'reprovado';
}

// Lista de Espera
interface ListaEspera {
  id: string;
  tenant_id: string;
  cliente_id: string;
  servico_id?: string;
  data_preferida?: string;
  status: 'aguardando' | 'notificado' | 'agendado' | 'expirado';
}

// Log de Mensagens
interface LogMensagem {
  id: string;
  tenant_id: string;
  cliente_whatsapp: string;
  direcao: 'entrada' | 'saida';
  mensagem: string;
  tipo: 'texto' | 'audio' | 'imagem' | 'documento';
  criado_em: string;
}
```

---

## 4. API Specification

### Design Philosophy

REST com FastAPI. Todas as rotas protegidas por JWT. Middleware injeta `tenant_id` no contexto da requisição automaticamente. Nenhuma rota pode retornar dados de outro tenant.

### Principais Endpoints

```
POST   /auth/login                    → JWT + refresh token
POST   /auth/refresh                  → Novo access token
POST   /auth/logout                   → Invalida refresh token

GET    /dashboard/hoje                → Resumo do dia para o tenant
GET    /dashboard/roi                 → Relatório de ROI do mês

GET    /clientes                      → Lista com paginação e filtros
POST   /clientes                      → Cadastrar cliente/paciente
GET    /clientes/{id}                 → Perfil completo + histórico
PUT    /clientes/{id}                 → Atualizar dados

GET    /atendimentos                  → Lista com filtros de data e status
POST   /atendimentos                  → Criar atendimento/pedido
PATCH  /atendimentos/{id}/status      → Atualizar status
GET    /atendimentos/aprovacoes       → Pendentes de aprovação do lojista

GET    /servicos                      → Lista de serviços/produtos
POST   /servicos                      → Cadastrar
PUT    /servicos/{id}                 → Editar
GET    /precos/{servico_id}           → Faixas de preço

GET    /lista-espera                  → Fila por serviço
POST   /lista-espera/{id}/oferecer    → Ofertar horário liberado

POST   /whatsapp/webhook              → Receber mensagem da Evolution API

GET    /relatorios/pdf/dia            → PDF do fechamento diário
GET    /relatorios/pdf/mensal         → PDF de ROI mensal

GET    /configuracoes                 → Config do tenant
PUT    /configuracoes                 → Atualizar config

POST   /webhooks/asaas                → Pagamento confirmado/atrasado
```

---

## 5. User Stories

### Epic: Operação do Dia

**US-001: Ver resumo do dia**
Como dono da loja/clínica, quero abrir o app de manhã e ver imediatamente: quantos atendimentos tenho hoje, quais estão confirmados, quais têm aprovação pendente e quanto já faturei.
- Aceito quando: Dashboard carrega em menos de 1 segundo com dados do dia atual
- Aceito quando: Aprovações pendentes aparecem em destaque impossível de ignorar

**US-002: Aprovar pedido grande via dashboard**
Como lojista, quero receber pedidos grandes na dashboard com botões APROVAR e RECUSAR, para não precisar sair do WhatsApp pessoal.
- Aceito quando: Botão APROVAR atualiza status em tempo real e o sistema continua o fluxo com o cliente automaticamente

**US-003: Ver ROI mensal**
Como dono de clínica, quero receber todo dia 1 um PDF mostrando quanto o sistema gerou de impacto financeiro real no mês anterior.
- Aceito quando: PDF inclui taxa de comparecimento, receita recuperada, pacientes reativados e ROI calculado em reais

### Epic: Automação WhatsApp

**US-004: Receber pedido pelo WhatsApp**
Como cliente da loja, quero enviar "Oi" no WhatsApp e ser guiado para fazer meu pedido sem precisar falar com ninguém.
- Aceito quando: Sistema coleta produto, quantidade, personalização e confirma com valor calculado pela faixa de preço correta

**US-005: Confirmar consulta automaticamente**
Como paciente, quero receber uma mensagem de confirmação 48h antes da minha consulta e poder confirmar com uma palavra.
- Aceito quando: Sistema detecta confirmação, atualiza status e para de enviar lembretes

---

## 6. Functional Requirements

**FR-001: Kill Switch Global**
Priority: P0
Antes de qualquer ação o sistema verifica `tenants.sistema_ativo`. Se `false`, o WhatsApp responde "Serviço indisponível" e a dashboard exibe banner de bloqueio com link de pagamento.

**FR-002: Comportamento Humano no WhatsApp**
Priority: P0
Todo envio de mensagem deve ter: delay de 3-8s antes de enviar, indicador de digitação ativado, seleção aleatória entre 4 variações de cada mensagem. Nunca enviar mensagens simultâneas — fila com 30-60s de intervalo.

**FR-003: Isolamento Multi-tenant**
Priority: P0
Toda query ao banco inclui `WHERE tenant_id = :tenant_id`. RLS no Supabase como segunda camada de proteção. Teste automatizado deve provar que token do tenant A não acessa dados do tenant B.

**FR-004: Fluxo Conversacional por Etapas**
Priority: P0
O estado da conversa de cada cliente é salvo no banco. Se o cliente sair no meio do pedido e voltar depois, o sistema retoma de onde parou.

**FR-005: Cálculo de Preço por Faixa**
Priority: P1
Ao registrar item, o sistema consulta a tabela `precos` pela quantidade e aplica o preço correto automaticamente. Nunca aceitar preço enviado pelo cliente.

**FR-006: Reativação Automática de Inativos**
Priority: P1
Todo segundo-feira o sistema identifica clientes inativos por faixa (3, 6, 12 meses) e envia mensagem personalizada para cada faixa. Deve sortear variação da mensagem para evitar detecção de spam.

**FR-007: Lista de Espera Inteligente**
Priority: P1
Cancelamento detectado → sistema oferta o horário para o próximo da lista em até 30 segundos. Se recusar ou não responder em 15 minutos, oferta para o próximo.

**FR-008: Relatório de ROI Mensal**
Priority: P1
Calculado todo dia 1: taxa de comparecimento, receita perdida com faltas, pacientes reativados, consultas geradas pela lista de espera, ROI em reais. Enviado por WhatsApp + PDF salvo no Drive.

---

## 7. Non-Functional Requirements

### Performance
- Webhook do WhatsApp: resposta em menos de 500ms
- Dashboard: carregamento em menos de 1 segundo
- Troca de abas no mobile: menos de 100ms

### Security
- JWT rotation a cada 1 hora
- RLS em todas as 10 tabelas
- Dado clínico nunca no WhatsApp
- Logs de auditoria para LGPD
- Rate limiting por IP e por tenant
- DPA assinado com cada cliente clínica antes da instalação

### Reliability
- UptimeRobot monitorando a cada 5 minutos
- Fluxo 9 (PDF) tenta 3x antes de alertar o dono
- Número reserva aquecido com chaveamento automático
- Backup diário às 23h para Google Drive

### Scalability
- Arquitetura multi-tenant suporta dezenas de clientes no mesmo backend
- Supabase grátis até 500MB — upgrade planejado quando necessário
- Railway escala horizontalmente conforme volume aumenta

---

## 8. UI/UX Requirements

Seguir design.md para tokens de cor, tipografia, espaçamentos e componentes.

### Screen: Dashboard — Visão do Dia
- Cards: Atendimentos hoje / Confirmados / Aprovações pendentes / Receita do dia
- Aprovações pendentes: banner âmbar no topo, impossível de ignorar
- Lista de atendimentos do dia com status colorido e botões de ação
- Atualização automática a cada 30 segundos

### Screen: Aprovações Pendentes
- Tela dedicada — acessível direto pelo card de alerta
- Cada card mostra: cliente, produto/serviço, quantidade, valor estimado, tempo esperando
- Botões APROVAR (verde) e RECUSAR (vermelho) grandes — touch-friendly
- Contador de tempo esperando — urgência visual crescente

### Screen: Clientes/Pacientes
- Lista com busca por nome ou WhatsApp
- Filtro por status de reativação
- Card do cliente: ticket médio, última visita, total de atendimentos
- Badge de status de reativação colorido

### Screen: Configurações
- Horário de funcionamento com toggle de dias da semana
- Mensagens padrão editáveis inline
- Limite de pedido grande configurável
- Toggle visual do Kill Switch (apenas para admin da conta)
- Seção de usuários com perfis e permissões

---

## 9. Auth Implementation

### Perfis e permissões

| Perfil | Permissões |
|---|---|
| dono | Tudo — incluindo configurações, financeiro e kill switch |
| medico | Ver agenda, atualizar status de consulta, ver pacientes |
| recepcionista | Ver agenda, confirmar, ver clientes — sem financeiro |
| funcionario | Ver tarefas do dia, marcar como pronto — sem financeiro |

JWT armazenado em httpOnly cookie — nunca localStorage.

---

## 10. Payment Integration

### Asaas
- Cobrança automática na data de vencimento de cada tenant
- Webhook `payment.overdue` após 5 dias → `sistema_ativo = false` (kill switch)
- Webhook `payment.received` → `sistema_ativo = true` (reativação automática)
- Cliente recebe WhatsApp automático em ambos os casos

---

## 11. Edge Cases & Error Handling

| Cenário | Comportamento esperado | Prioridade |
|---|---|---|
| Evolution API bloqueada | Número reserva ativa automaticamente, dono recebe alerta | P0 |
| Supabase fora do ar | Fila de mensagens pendentes, retry em 30s, alerta no UptimeRobot | P0 |
| Cliente envia áudio | "Não consigo ouvir áudios. Pode me enviar em texto?" | P1 |
| Cliente envia imagem sem contexto | "Recebi sua imagem! Me conta o que você precisa?" | P1 |
| Lojista não responde aprovação em 4h | Alerta crítico na dashboard com destaque vermelho | P0 |
| PDF falha na geração | 3 tentativas com intervalo de 10min, depois alerta manual | P1 |
| Cliente sumiu no meio do pedido | Lembrete em 30min → abandona em 1h → dono notificado | P1 |
| Backup falha | Alerta no UptimeRobot + WhatsApp para o dono | P1 |

---

## 12. Dependencies & Integrations

### Backend
```
fastapi==0.115+
sqlalchemy==2.0+
asyncpg
pydantic==2.0+
python-jose[cryptography]
passlib[bcrypt]
apscheduler
httpx
reportlab
structlog
python-dotenv
alembic
pytest
pytest-asyncio
```

### Frontend
```
react: ^18
vite: ^5
typescript: ^5
tailwindcss: ^3
recharts
zustand
axios
react-router-dom: ^6
lucide-react
```

---

## 13. Out of Scope (v1)

- Claude API / IA conversacional (planejado para plano Premium v2)
- WhatsApp Business API oficial Meta (planejado após escala)
- Integração com sistemas de prontuário eletrônico (v3)
- App mobile nativo (o PWA mobile-first resolve v1)
- Multi-unidade / redes de clínicas (planejado para plano Premium)
- Integração com Instagram DM (v2)

---

## 14. Open Questions

1. **Drag & drop na agenda**: Usar botões rápidos de mudança de status na v1 para velocidade de entrega. Implementar drag & drop nativo na v2 se o piloto mostrar demanda.
2. **Áudio no WhatsApp**: Na v1 responder pedindo texto. Na v2 com Claude API implementar transcrição automática.
3. **Aprovação de arte**: Na v1 usar campo de link e texto. Na v2 implementar upload direto de arquivo via Supabase Storage.
