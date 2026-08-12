# 🚀 SaaS de Gestão via WhatsApp

Sistema SaaS multi-tenant de gestão operacional via WhatsApp para **clínicas médicas, odontológicas e lojas de personalizados**.

Automatiza atendimento, agendamento, confirmações, reativação de clientes inativos, relatórios e fechamento do dia — tudo de forma autônoma, segura e escalável.

---

## 📋 Sobre o Projeto

O mercado de bots de WhatsApp virou commodity. Este produto se posiciona como um **sistema de retenção e reativação que gera ROI mensurável** para o cliente.

**Cenário ilustrativo:** uma clínica que reduza faltas de 25% para 10% pode recuperar receita antes perdida. O impacto real depende de volume, ticket médio, adesão dos pacientes e custos de operação.

### ✨ Funcionalidades Principais

- **Atendimento automatizado via WhatsApp** — respostas contextuais, fluxos configuráveis e encaminhamento para atendimento humano
- **Agendamento inteligente** com confirmação e lembretes automáticos
- **Reativação de clientes inativos** — reconquista automática com mensagens personalizadas
- **Dashboard em tempo real** — métricas, agenda, relatórios e ROI mensal
- **Lista de espera** — preenchimento automático de cancelamentos
- **Fechamento do dia** — relatório automático enviado ao dono
- **Multi-tenant** — um único backend serve todos os clientes, isolados por RLS
- **LGPD compliance** — logs de auditoria, criptografia e consentimento

---

## 🏗️ Arquitetura

```
[WhatsApp do cliente/paciente]
           ↓
    [Evolution API]
           ↓
    [Backend Python — FastAPI]  ← Único backend para todos os tenants
           ↓
    [Supabase — PostgreSQL]     ← Único banco com RLS por tenant
           ↓
    [Frontend React + Tailwind] ← Deploy por cliente no Vercel
```

---

## 🛠️ Stack Técnica

| Camada | Tecnologia | Motivo |
|---|---|---|
| **Backend** | Python 3.12 + FastAPI | Async, tipado, excelente para automações |
| **ORM** | SQLAlchemy 2.0 async + asyncpg | Performance máxima com PostgreSQL |
| **Validação** | Pydantic v2 | Segurança nos inputs, serialização automática |
| **Auth** | JWT + refresh token rotation | Stateless, seguro, padrão de mercado |
| **Agendamento** | APScheduler | Cron jobs para automações |
| **WhatsApp** | Evolution API via httpx async | Self-hosted, sem custo de API oficial |
| **PDF** | ReportLab | Relatórios diários e mensais |
| **Logs** | structlog (JSON) | Auditoria completa para LGPD |
| **Frontend** | React 19 + Vite + Tailwind CSS 4 | Mobile-first, velocidade de desenvolvimento |
| **Gráficos** | Recharts | Integrado no ecossistema React |
| **Estado** | Zustand | Leve e simples |
| **Banco** | Supabase (PostgreSQL 15+) | RLS nativo, região São Paulo |
| **Infra Backend** | Railway | ~R$25/mês |
| **Infra Frontend** | Vercel | CDN global, grátis por deploy |
| **Testes** | pytest + pytest-asyncio | Cobertura dos fluxos críticos |

---

## 📁 Estrutura do Projeto

```
ProjetoSaas/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, middlewares, routers
│   │   ├── config.py            # Settings via pydantic-settings
│   │   ├── database.py          # Conexão async Supabase
│   │   ├── dependencies.py      # get_current_user, get_tenant_id
│   │   ├── models/              # SQLAlchemy models (10 tabelas)
│   │   ├── routers/             # auth, dashboard, whatsapp, webhooks
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── services/            # Lógica de negócio
│   │   ├── tasks/               # APScheduler automações
│   │   ├── middleware/          # Tenant, security, auditoria
│   │   └── utils/               # Helpers
│   ├── alembic/                 # Migrações de banco
│   ├── tests/                   # Testes automatizados
│   ├── Dockerfile               # Build do container
│   ├── docker-compose.yml       # PostgreSQL local para dev
│   ├── requirements.txt         # Dependências Python
│   └── railway.toml             # Config de deploy Railway
├── frontend/
│   ├── src/
│   │   ├── components/          # Dashboard, Agenda, Clientes, etc.
│   │   ├── services/            # API client (axios)
│   │   ├── store/               # Zustand state management
│   │   ├── hooks/               # Custom React hooks
│   │   ├── types/               # TypeScript types
│   │   └── config/              # Configuração do app
│   ├── package.json
│   ├── vite.config.ts
│   └── vercel.json              # Config de deploy Vercel
└── docs/
    ├── prd.md                   # Product Requirements Document
    ├── design.md                # Design system e guidelines
    ├── product-roadmap.md       # Roadmap com todas as fases
    ├── security-checklist.md    # Checklist de segurança
    ├── onboarding-checklist.md  # Checklist de onboarding cliente
    └── guia-vendas-e-manual.md  # Guia de vendas e manual
```

---

## 🚀 Como Rodar Localmente

### Pré-requisitos

- Python 3.12+
- Node.js 20+
- Docker (opcional, para PostgreSQL local)

### Backend

```bash
# 1. Entrar no diretório
cd backend

# 2. Criar e ativar o virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# 3. Instalar dependências
pip install -r requirements-dev.txt

# 4. Configurar variáveis de ambiente
cp .env.example .env
# Editar o .env com suas credenciais

# 5. Subir o PostgreSQL local (opcional)
docker-compose up -d

# 6. Rodar as migrações
alembic upgrade head

# 7. Iniciar o servidor
uvicorn app.main:app --reload --port 8000
```

O backend estará disponível em `http://localhost:8000` com docs em `http://localhost:8000/docs`.

### Frontend

```bash
# 1. Entrar no diretório
cd frontend

# 2. Instalar dependências
npm install

# 3. Iniciar o servidor de desenvolvimento
npm run dev
```

O frontend estará disponível em `http://localhost:5173`.

---

## 🧪 Testes

```bash
cd backend
pytest --cov=app tests/
```

---

## 🌐 Deploy

| Serviço | Plataforma | Detalhes |
|---|---|---|
| Backend | Railway | Deploy via Dockerfile |
| Frontend | Vercel | Um deploy por tenant |
| Banco | Supabase | PostgreSQL com RLS |

---

## 📊 Status do Desenvolvimento

O roadmap está dividido em 8 fases. Confira o progresso completo em [`docs/product-roadmap.md`](docs/product-roadmap.md).

| Fase | Descrição | Status |
|---|---|---|
| Phase 0 | Infraestrutura | ✅ Completa |
| Phase 1 | Backend Foundation | ✅ Completa |
| Phase 2 | WhatsApp Core | ✅ Completa |
| Phase 3 | Automações Críticas | ✅ Completa |
| Phase 4 | Automações de Suporte | ✅ Completa |
| Phase 5 | Frontend Dashboard | ✅ Completa |
| Phase 6 | Segurança e LGPD | ✅ Completa |
| Phase 7 | Produção e Piloto | ✅ Completa |

---

## 📖 Documentação

- [PRD — Requisitos do Produto](docs/prd.md)
- [Design System](docs/design.md)
- [Roadmap Completo](docs/product-roadmap.md)
- [Checklist de Segurança](docs/security-checklist.md)
- [Checklist de Onboarding](docs/onboarding-checklist.md)
- [Guia de Vendas e Manual](docs/guia-vendas-e-manual.md)

---

## 🔒 Segurança

- **Multi-tenant com RLS** — isolamento total entre clientes
- **JWT com refresh token rotation** — sessões seguras
- **Rate limiting** — proteção contra abuse
- **LGPD compliance** — logs de auditoria, criptografia de dados sensíveis, controle de consentimento
- **Dados clínicos nunca trafegam pelo WhatsApp** — regra verificada em code review

---

## 👥 Time

Projeto em construção ativa. Contribuições internas via PR com code review.

---

## 📄 Licença

Projeto proprietário. Todos os direitos reservados.
