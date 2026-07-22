# Product Roadmap — SaaS de Gestão via WhatsApp

> O agente de desenvolvimento deve marcar as tarefas como `- [x]` conforme forem concluídas.

**Status:** Completo (40/40 tarefas completas)
**Fase atual:** Concluído


---

## Build Philosophy

1. **Cada fase entrega algo testável e funcional.** Nenhuma fase deixa o sistema quebrado ou inutilizável.
2. **Backend antes do frontend.** A lógica de negócio e a segurança são construídas primeiro.
3. **Segurança não é opcional.** RLS, JWT e isolamento multi-tenant são implementados na Fase 1 — nunca depois.
4. **Mobile first no frontend.** Toda tela é validada em 390px antes de qualquer outra resolução.
5. **Testar o crítico primeiro.** Os fluxos de WhatsApp e o isolamento entre tenants têm testes antes de qualquer funcionalidade auxiliar.
6. **Dado clínico nunca no WhatsApp.** Esta regra é verificada em code review em todas as fases.

---

## Progresso por fase

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

## Phase 0: Infraestrutura 

> **Goal:** Banco de dados criado, N8N substituído por Python, Railway no ar.

- [x] **TASK-001** — Supabase criado com 8 tabelas (migrar para 10 tabelas na Phase 1)
  Notes: URL: https://rtysmuxbscxrgpwzqmwy.supabase.co — credenciais seguras geradas
  Verify: Table Editor mostra todas as tabelas criadas

- [x] **TASK-002** — N8N self-hosted no Railway deployado
  Notes: URL: https://primary-production-c64a8.up.railway.app — será substituído pelo backend Python
  Verify: Dashboard N8N acessível com login

---

## Phase 1: Backend Foundation

> **Goal:** Estrutura do projeto Python/FastAPI completa, banco com 10 tabelas e RLS, autenticação JWT funcionando, isolamento multi-tenant testado e comprovado.

**Seções de referência — ler antes de começar:**
- PRD: `§ 2. Technical Architecture > Chosen Stack`
- PRD: `§ 2. Technical Architecture > Repository Structure`
- PRD: `§ 3. Data Model > Entity Definitions`
- PRD: `§ 6. Functional Requirements > FR-003: Isolamento Multi-tenant`

**Phase prompt — passar para o agente:**
> "Leia docs/product-roadmap.md e encontre a Phase 1. Leia as seções de referência em docs/prd.md. Comece pela TASK-003. Marque cada tarefa como [x] ao concluir. Ao final da Phase 1, o servidor FastAPI deve rodar localmente, o banco deve ter 10 tabelas com RLS ativo e o teste de isolamento entre tenants deve passar."

- [x] **TASK-003** — Estrutura de pastas e configuração do projeto
  Files: `backend/app/main.py`, `backend/app/config.py`, `backend/requirements.txt`, `backend/Dockerfile`, `backend/railway.toml`, `backend/.env.example`
  Notes: Criar estrutura completa de pastas conforme PRD §2. Settings via pydantic-settings lendo do .env. FastAPI com CORS configurado apenas para domínios cadastrados. Health check em GET /health retornando status e versão. Dockerfile otimizado para Railway. Secrets nunca hardcoded.
  Verify: `uvicorn app.main:app --reload` sobe sem erros. GET /health retorna 200.

- [x] **TASK-004** — Conexão async com Supabase
  Files: `backend/app/database.py`
  Notes: SQLAlchemy 2.0 com asyncpg. Pool de conexões com limite máximo. Conexão sempre via SSL — rejeitar sem SSL. Função `get_db()` como dependency do FastAPI. Variáveis de ambiente: SUPABASE_URL e DATABASE_URL.
  Verify: `get_db()` abre e fecha sessão sem erros no startup.

- [x] **TASK-005** — Migrations Alembic com 10 tabelas completas
  Files: `backend/alembic/`, `backend/alembic/versions/001_initial.py`
  Notes: Criar migration inicial com as 10 tabelas: tenants, usuarios, clientes_pacientes, servicos_produtos, precos, atendimentos_pedidos, itens_atendimento, lista_espera, logs_mensagens, configuracoes. TODAS com tenant_id NOT NULL. Constraints de CHECK nos campos de status e tipo. Índices em tenant_id, whatsapp e data_atendimento.
  Verify: `alembic upgrade head` roda sem erros. Tabelas aparecem no Supabase.

- [x] **TASK-006** — Row Level Security (RLS) em todas as tabelas
  Files: `backend/alembic/versions/002_rls.sql` (rodar no SQL Editor do Supabase)
  Notes: Ativar RLS em todas as 10 tabelas. Política: `USING (tenant_id = current_setting('app.tenant_id')::uuid)`. Criar função `set_tenant_id(uuid)` que faz SET LOCAL. O middleware do FastAPI chamará essa função a cada requisição antes de qualquer query.
  Verify: Com RLS ativo, query sem SET app.tenant_id retorna zero rows — não erro, zero rows.

- [x] **TASK-007** — Autenticação JWT completa
  Files: `backend/app/utils/security.py`, `backend/app/routers/auth.py`, `backend/app/schemas/auth.py`
  Notes: POST /auth/login valida email+senha, retorna access_token (1h) e refresh_token (7 dias) em httpOnly cookie. POST /auth/refresh valida refresh token, invalida o anterior (rotation) e emite novo par. POST /auth/logout invalida o refresh token. Blacklist de tokens revogados no Supabase. Senha com bcrypt. JWT com python-jose.
  Verify: Login retorna tokens. Refresh funciona. Logout invalida. Token expirado retorna 401.

- [x] **TASK-008** — Middleware de tenant e dependency injection
  Files: `backend/app/dependencies.py`, `backend/app/middleware/tenant.py`
  Notes: `get_current_user` extrai usuário do JWT. `get_tenant_id` extrai tenant_id do usuário. Middleware chama `set_tenant_id(tenant_id)` antes de toda query. Nenhuma rota pode executar query sem tenant_id injetado. Perfis: dono vê tudo, recepcionista sem financeiro, funcionário só tarefas do dia.
  Verify: Request com token do tenant A, tentando acessar /clientes, retorna apenas clientes do tenant A. Impossível obter dados de outro tenant.

- [x] **TASK-009** — Testes de isolamento multi-tenant (CRÍTICO)
  Files: `backend/tests/test_rls.py`, `backend/tests/test_auth.py`
  Notes: Criar dois tenants A e B com dados distintos. Fazer login no tenant A. Tentar acessar todos os endpoints com token do tenant A e confirmar que nenhum retorna dado do tenant B — nem mesmo injetando tenant_id manualmente no body. Este teste deve passar antes de qualquer outra funcionalidade ser desenvolvida.
  Verify: `pytest tests/test_rls.py -v` — todos os testes passam. Zero dados do tenant B visíveis com token do tenant A.

---

## Phase 2: WhatsApp Core

> **Goal:** Webhook do WhatsApp funcionando, fluxo conversacional de registro de pedido/consulta completo, comportamento humano implementado.

**Seções de referência — ler antes de começar:**
- PRD: `§ 6. Functional Requirements > FR-002: Comportamento Humano`
- PRD: `§ 6. Functional Requirements > FR-004: Fluxo Conversacional`
- PRD: `§ 6. Functional Requirements > FR-005: Cálculo de Preço`
- PRD: `§ 11. Edge Cases > Cliente envia áudio`

**Phase prompt — passar para o agente:**
> "Leia docs/product-roadmap.md e encontre a Phase 2. Leia as seções de referência em docs/prd.md e docs/design.md. Comece pela TASK-010. Ao final da Phase 2, o sistema deve receber uma mensagem real no WhatsApp, guiar o cliente pelo pedido e salvar no Supabase."

- [x] **TASK-010** — Serviço de envio WhatsApp com comportamento humano
  Files: `backend/app/services/whatsapp_service.py`, `backend/app/utils/mensagens.py`
  Notes: Função `enviar_mensagem(tenant_id, numero, mensagem)` que: (1) ativa indicador de digitação via Evolution API, (2) aguarda randint(3, 8) segundos, (3) seleciona aleatoriamente entre as 4 variações da mensagem, (4) envia via POST na Evolution API com httpx async. Função `enviar_fila(lista_numeros, mensagem)` com intervalo de randint(30, 60) segundos entre cada envio. Nunca enviar simultâneo.
  Verify: Enviar mensagem de teste — no WhatsApp aparece "digitando..." antes da mensagem chegar. Delay visível.

- [x] **TASK-011** — Webhook de entrada do WhatsApp
  Files: `backend/app/routers/whatsapp.py`
  Notes: POST /whatsapp/webhook recebe payload da Evolution API. Identificar tenant pelo número da instância. Buscar ou criar cliente pelo número do remetente. Verificar `sistema_ativo` — se false, responder "Serviço indisponível" e retornar. Verificar horário de funcionamento — se fora, disparar Fluxo 7. Registrar mensagem em logs_mensagens. Responder em menos de 500ms (processar assincronamente).
  Verify: Enviar "Oi" no WhatsApp. Log aparece no Supabase. Sistema responde dentro de 500ms.

- [x] **TASK-012** — Fluxo conversacional de registro de pedido/consulta
  Files: `backend/app/services/fluxo_service.py`
  Notes: Estado da conversa salvo no banco por cliente. Etapas do fluxo: (1) boas-vindas + menu, (2) serviço/produto desejado, (3) quantidade/data, (4) personalização se aplicável, (5) cálculo automático do preço pela faixa correta, (6) confirmação do resumo, (7) registro no banco. Se quantidade > limite_pedido_grande: pausar e disparar alerta para lojista. Se cliente sair e voltar: retomar da etapa correta.
  Verify: Simular conversa completa. Pedido aparece no Supabase com valor calculado pela faixa correta.

- [x] **TASK-013** — Testes do fluxo WhatsApp
  Files: `backend/tests/test_whatsapp.py`
  Notes: Testar: recebimento de webhook, identificação de tenant, criação de cliente novo, fluxo completo de pedido, cálculo de preço por faixa, disparo de alerta de pedido grande, comportamento fora de horário.
  Verify: `pytest tests/test_whatsapp.py -v` — todos passam.

---

## Phase 3: Automações Críticas

> **Goal:** Os 5 fluxos mais críticos do negócio funcionando: confirmação 48h, pedido grande, lista de espera, reativação de inativos e kill switch.

**Seções de referência — ler antes de começar:**
- PRD: `§ 6. Functional Requirements > FR-006: Reativação Automática`
- PRD: `§ 6. Functional Requirements > FR-007: Lista de Espera`
- PRD: `§ 10. Payment Integration`

**Phase prompt — passar para o agente:**
> "Leia docs/product-roadmap.md e encontre a Phase 3. Leia as seções de referência em docs/prd.md. Comece pela TASK-014. Ao final, os 5 fluxos críticos devem estar funcionando com testes passando."

- [x] **TASK-014** — APScheduler configurado com timezone de Brasília
  Files: `backend/app/tasks/scheduler.py`
  Notes: Inicializar APScheduler no startup do FastAPI. Timezone: America/Sao_Paulo. Cada task registrada como CronTrigger. Log estruturado de início e fim de cada execução. Erro em uma task não derruba as outras.
  Verify: Scheduler inicia com o FastAPI. Logs aparecem nos horários configurados.

- [x] **TASK-015** — Fluxo 2A: Confirmação inteligente 48h antes
  Files: `backend/app/tasks/confirmacao_task.py`
  Notes: Roda 2x ao dia (08h e 14h). Busca atendimentos não confirmados com data em 48h. Envia mensagem via whatsapp_service com variações. Aguarda resposta. Sem resposta em 4h: lembrete final. Sem resposta em 8h: registro na tabela aprovacoes como pendente para a recepção ver na dashboard.
  Verify: Criar atendimento para daqui 48h. Rodar task manualmente. Mensagem chega no WhatsApp.

- [x] **TASK-016** — Fluxo 2B: Aprovação de pedido grande
  Files: `backend/app/services/aprovacao_service.py`
  Notes: Disparado quando quantidade > limite_pedido_grande do tenant. Pausa o fluxo (status: aguardando_aprovacao). Envia para WhatsApp do dono: nome do cliente, produto, quantidade, valor estimado. Aguarda resposta APROVAR ou RECUSAR. Sem resposta em 2h: renotifica. Sem resposta em 4h: alerta crítico na tabela aprovacoes. Aprovado: retoma fluxo e confirma para o cliente. Recusado: notifica cliente.
  Verify: Simular pedido acima do limite. Dono recebe alerta. Responder APROVAR. Cliente recebe confirmação.

- [x] **TASK-017** — Fluxo 3: Lista de espera inteligente
  Files: `backend/app/services/lista_espera_service.py`
  Notes: Disparado quando atendimento muda para cancelado ou falta. Busca próximo da lista_espera para aquele serviço. Envia oferta do horário em até 30 segundos. Aguarda 15 minutos. Se aceitar: agenda e confirma. Se recusar ou não responder: oferece para o próximo. Registrar todo o chain de notificações.
  Verify: Criar lista de espera. Cancelar um atendimento. Próximo da fila recebe oferta em 30s.

- [x] **TASK-018** — Fluxo 4: CRM de reativação de inativos
  Files: `backend/app/tasks/reativacao_task.py`
  Notes: Roda toda segunda-feira às 09h. Busca clientes por faixa de inatividade: 3 meses (mensagem leve), 6 meses (urgência preventiva), 12 meses (reconquista). Envia com delay de 45-60s entre cada cliente. Sorteia variação da mensagem. Aguarda resposta. Respondeu: inicia fluxo de agendamento. Não respondeu: marca como notificado, nova tentativa em 30 dias. Atualiza status_reativacao no banco.
  Verify: Criar cliente com última consulta há 4 meses. Rodar task. Mensagem de reativação chega.

- [x] **TASK-019** — Fluxo 12: Kill switch por inadimplência
  Files: `backend/app/routers/webhooks.py`, `backend/app/services/asaas_service.py`
  Notes: POST /webhooks/asaas recebe eventos do Asaas. PAYMENT_OVERDUE após 5 dias: SET sistema_ativo = false + WhatsApp para o dono com link de pagamento. PAYMENT_RECEIVED: SET sistema_ativo = true + WhatsApp de confirmação de reativação. Validar o token do webhook do Asaas antes de processar.
  Verify: Simular webhook de inadimplência. sistema_ativo = false no banco. WhatsApp de bloqueio enviado. Simular pagamento. Sistema reativa automaticamente.

- [x] **TASK-020** — Testes das automações críticas
  Files: `backend/tests/test_automacoes.py`
  Notes: Testar: confirmação 48h, aprovação de pedido grande, lista de espera, reativação de inativos, kill switch (ativar e desativar). Cada teste com dados de tenant isolado.
  Verify: `pytest tests/test_automacoes.py -v` — todos passam.

---

## Phase 4: Automações de Suporte

> **Goal:** Completar os 8 fluxos restantes — lembrete diário, avisos pós-atendimento, horário, retomada, PDF, ROI mensal, cliente sumido e backup.

**Phase prompt — passar para o agente:**
> "Leia docs/product-roadmap.md e encontre a Phase 4. Leia PRD §4 (API Specification) e §11 (Edge Cases). Comece pela TASK-021. Cada fluxo deve ter pelo menos um teste associado."

- [x] **TASK-021** — Fluxo 5: Lembrete diário para o dono às 7h
  Files: `backend/app/tasks/lembrete_task.py`
  Notes: Para cada tenant ativo com horario_abertura = agora (+/- 30min). Busca todos os atendimentos do dia. Monta resumo: total, confirmados, pendentes de confirmação, aprovações pendentes. Envia para WhatsApp do dono com lista de nomes e horários.
  Verify: Criar atendimentos para hoje. Rodar task. Dono recebe resumo completo.

- [x] **TASK-022** — Fluxo 6: Aviso pós-atendimento concluído
  Files: `backend/app/services/pos_atendimento_service.py`
  Notes: Disparado quando status muda para realizado ou entregue. Aguarda 30 minutos. Para clínicas: envia agradecimento + sugestão de retorno baseada no serviço. Para lojas: solicita avaliação em 1 palavra. Atualiza ultima_consulta no cliente.
  Verify: Marcar atendimento como realizado. Após 30min, cliente recebe mensagem de agradecimento.

- [x] **TASK-023** — Fluxo 7 e 8: Fora de horário e retomada na abertura
  Files: `backend/app/services/horario_service.py`, `backend/app/tasks/retomada_task.py`
  Notes: Fluxo 7: mensagem fora do horário → registra com status aguardando_abertura + responde "retornamos às Xh". Fluxo 8: task no horário de abertura de cada tenant → notifica dono sobre mensagens noturnas + retoma conversa com cada cliente.
  Verify: Enviar mensagem às 23h. Receber resposta de fora de horário. Às 8h, retomada automática.

- [x] **TASK-024** — Fluxo 9: PDF de fechamento diário às 18h
  Files: `backend/app/tasks/pdf_task.py`, `backend/app/services/pdf_service.py`
  Notes: Para cada tenant ativo. Coleta dados do dia: atendimentos, realizados, faltas, receita total, recebida e a receber, pedidos em aberto, mensagens noturnas. Gera PDF com ReportLab incluindo logo do tenant (cor_primaria como tema). Envia para WhatsApp do dono. Salva no Google Drive. Se falhar: 3 tentativas com 10min de intervalo. Se falhar 3x: alerta manual para o dono.
  Verify: Rodar task manualmente. PDF chega no WhatsApp com dados do dia corretos.

- [x] **TASK-025** — Fluxo 10: Relatório mensal de ROI todo dia 1
  Files: `backend/app/tasks/roi_task.py`
  Notes: Calcular: taxa de comparecimento, receita total, receita perdida com faltas, pacientes reativados pelo sistema, consultas geradas pela lista de espera, ROI = impacto_total / mensalidade_do_plano. Gerar PDF executivo. Enviar para dono com mensagem de destaque: "O sistema gerou R$X de impacto esse mês."
  Verify: Rodar task com dados mockados de um mês. PDF gerado com ROI calculado corretamente.

- [x] **TASK-026** — Fluxo 11: Cliente sumiu no meio da conversa
  Files: Adicionar a `backend/app/services/fluxo_service.py`
  Notes: Se cliente não responde em 30min durante fluxo ativo: enviar "Oi! Ainda está por aí? 😊". Sem resposta em mais 1h: marcar atendimento como abandonado. Registrar no log. Notificar dono/recepcionista via tabela aprovacoes (tipo: cliente_sumiu).
  Verify: Iniciar fluxo e não responder. Após 30min, lembrete chega. Após 1h, status = abandonado no banco.

- [x] **TASK-027** — Fluxo 13: Backup diário às 23h
  Files: `backend/app/tasks/backup_task.py`, `backend/app/services/backup_service.py`
  Notes: Para cada tenant ativo. Exportar atendimentos, novos clientes e logs do dia em JSON. Comprimir em ZIP nomeado como backup_YYYY-MM-DD_tenant.zip. Salvar no Google Drive do tenant via API. Manter apenas últimos 90 dias (deletar mais antigos).
  Verify: Rodar task. Arquivo ZIP aparece no Google Drive com dados do dia.

---

## Phase 5: Frontend Dashboard

> **Goal:** Dashboard React completo, mobile-first, com 8 telas, autenticado, conectado ao backend real, multi-tenant via variáveis de ambiente.

**Seções de referência — ler antes de começar:**
- PRD: `§ 8. UI/UX Requirements`
- PRD: `§ 9. Auth Implementation`
- design.md: seção completa

**Phase prompt — passar para o agente:**
> "Leia docs/product-roadmap.md e encontre a Phase 5. Leia docs/prd.md §8 e §9, e o docs/design.md completo. Comece pela TASK-028. Mobile first obrigatório — validar em 390px antes de qualquer outra resolução. Ao final, todas as 8 telas devem estar funcionando com dados reais do backend."

- [x] **TASK-028** — Setup do projeto React e sistema de design
  Files: `frontend/src/index.css`, `frontend/src/config/tenant.ts`, `frontend/vite.config.ts`, `frontend/tailwind.config.js`
  Notes: Criar projeto React + Vite + TypeScript + Tailwind. Configurar variáveis CSS do design system (cores, espaçamentos, tipografia) conforme design.md. tenant.ts lê TENANT_ID, TENANT_NOME, TENANT_TIPO, TENANT_COR_PRIMARIA das variáveis de ambiente do Vite. Axios configurado com base URL do backend e interceptors JWT. Zustand store para estado global.
  Verify: `npm run dev` sobe sem erros. Variáveis de ambiente do tenant acessíveis.

- [x] **TASK-029** — Login e autenticação
  Files: `frontend/src/components/Login.tsx`, `frontend/src/context/AuthContext.tsx`
  Notes: Tela de login limpa com email e senha. JWT em httpOnly cookie (gerenciado pelo backend). AuthContext verifica token ao carregar o app. Redirect para dashboard se autenticado. Redirect para login se 401. Logout limpa cookies e estado.
  Verify: Login com credenciais corretas vai para dashboard. Login incorreto mostra erro. Refresh da página mantém sessão.

- [x] **TASK-030** — Navegação: Sidebar (desktop) e BottomNav (mobile)
  Files: `frontend/src/components/Sidebar.tsx`, `frontend/src/components/BottomNav.tsx`
  Notes: Desktop (1024px+): sidebar fixa 240px com logo do tenant, itens de navegação, badge de aprovações pendentes com contador. Mobile (<1024px): bottom navigation bar com 5 ícones. Ambas controlam a rota ativa. Item de aprovações com badge numérico vermelho quando houver pendentes.
  Verify: Em 390px aparece bottom nav. Em 1024px aparece sidebar. Navegação entre telas funciona.

- [x] **TASK-031** — Tela 1: Dashboard — Visão do Dia
  Files: `frontend/src/components/Dashboard.tsx`
  Notes: Busca GET /dashboard/hoje. Cards: atendimentos hoje, confirmados, aprovações pendentes (âmbar em destaque), receita do dia. Se aprovações pendentes > 0: banner âmbar no topo com botão ir para aprovações. Lista de atendimentos do dia com status colorido (badges do design system) e botões de ação rápida. Atualização automática a cada 30 segundos.
  Verify: Dados reais do backend aparecem. Banner de aprovações visível quando há pendentes. Atualiza a cada 30s.

- [x] **TASK-032** — Tela 2: Aprovações Pendentes
  Files: `frontend/src/components/Aprovacoes.tsx`
  Notes: Busca GET /atendimentos/aprovacoes. Card por aprovação pendente com: nome do cliente, produto/serviço, quantidade, valor estimado, tempo esperando (contador ao vivo em minutos). Botões APROVAR (verde grande) e RECUSAR (vermelho grande) — mínimo 44px altura. PATCH /atendimentos/{id}/status ao clicar. Tela vazia com mensagem "Nenhuma aprovação pendente 🎉" quando zerada.
  Verify: Aprovar pedido na tela. Status atualiza no banco. Cliente recebe confirmação no WhatsApp.

- [x] **TASK-033** — Tela 3: Agenda / Pedidos
  Files: `frontend/src/components/Agenda.tsx`
  Notes: Lista de atendimentos com filtros: data, status, serviço. Busca GET /atendimentos com query params. Cada item: nome do cliente, serviço, horário/data de entrega, badge de status, botões de ação contextual (Confirmar, Marcar como Pronto, Entregar, Cancelar) baseados no status atual. Modal de detalhes com histórico completo do cliente ao clicar.
  Verify: Filtrar por status "aguardando". Marcar como pronto. Status atualiza em tempo real.

- [x] **TASK-034** — Tela 4: Clientes / Pacientes
  Files: `frontend/src/components/Clientes.tsx`
  Notes: Lista com busca por nome ou WhatsApp. Filtros por status de reativação. Card do cliente: nome, WhatsApp (formatado), ticket médio, última visita, total de atendimentos, badge de status de reativação colorido. Tela de perfil ao clicar: histórico completo de atendimentos, link direto para WhatsApp.
  Verify: Buscar por nome. Filtrar por inativo_6m. Perfil do cliente mostra histórico correto.

- [x] **TASK-035** — Telas 5, 6 e 7: Serviços, Lista de Espera e Relatórios
  Files: `frontend/src/components/Servicos.tsx`, `frontend/src/components/ListaEspera.tsx`, `frontend/src/components/Relatorios.tsx`
  Notes: Serviços: CRUD completo de serviços/produtos + tabela de faixas de preço editável inline. Lista de espera: fila por serviço com botão de oferta rápida de horário. Relatórios: gráficos com Recharts (atendimentos por período, taxa de comparecimento, receita), card de ROI em destaque verde, botão de exportar PDF.
  Verify: Criar serviço com faixa de preço. Oferecer horário da lista de espera. Gráficos carregam com dados reais.

- [x] **TASK-036** — Tela 8: Configurações
  Files: `frontend/src/components/Configuracoes.tsx`
  Notes: Seções: horário de funcionamento (toggle por dia da semana + hora), mensagens padrão editáveis (boas-vindas, fora de horário, confirmação), limite de pedido grande (número editável), usuários e perfis (listar, adicionar, desativar). Kill switch: toggle visual grande apenas para perfil dono, com confirmação de segurança antes de desativar. Banner de sistema ativo/inativo no topo.
  Verify: Alterar horário de funcionamento. Salvar. Backend atualiza configuracoes no banco.


---

## Phase 6: Segurança e LGPD

> **Goal:** Auditoria completa de segurança, conformidade LGPD documentada, testes de penetração básicos, rate limiting e headers de segurança.

**Phase prompt — passar para o agente:**
> "Leia docs/product-roadmap.md e encontre a Phase 6. Leia PRD §7 (Non-Functional Requirements). Comece pela TASK-037. Ao final, o sistema deve estar pronto para receber dados reais de pacientes."

- [x] **TASK-037** — Headers de segurança e rate limiting
  Files: `backend/app/main.py`, `backend/app/middleware/security.py`
  Notes: Headers obrigatórios: HSTS, X-Content-Type-Options: nosniff, X-Frame-Options: DENY, CSP restritivo. Rate limiting: 100 req/min por IP, 1000 req/min por tenant (usar slowapi ou middleware custom). Respostas de erro sem stack trace em produção. HTTPS redirect obrigatório.
  Verify: curl -I no endpoint retorna todos os headers. Rate limit dispara 429 após limite.

- [x] **TASK-038** — Logs de auditoria LGPD e endpoint de exclusão
  Files: `backend/app/middleware/auditoria.py`, `backend/app/routers/clientes.py`
  Notes: Log de auditoria: toda alteração em atendimentos_pedidos e clientes_pacientes registra quem alterou, o quê e quando. DELETE /clientes/{id}/lgpd: exclusão completa e irreversível de todos os dados do paciente (direito ao esquecimento) com log de auditoria da exclusão. Criptografia de campos sensíveis com pgcrypto no Supabase.
  Verify: Alterar dados de um cliente. Log de auditoria registra a alteração com usuário e timestamp. DELETE LGPD remove todos os dados.

- [x] **TASK-039** — Testes finais e documentação de segurança
  Files: `backend/tests/test_security.py`, `docs/security-checklist.md`
  Notes: Testes: headers de segurança presentes, rate limiting funciona, token expirado retorna 401, refresh rotation funciona, dado clínico nunca aparece em log de mensagem do WhatsApp, isolamento entre tenants é inviolável. Documentar checklist de segurança para auditoria LGPD.
  Verify: `pytest tests/test_security.py -v` — todos passam. Checklist aprovado.

---

## Phase 7: Produção e Piloto

> **Goal:** Sistema em produção, primeiro cliente piloto (loja de personalizados) rodando, dados reais fluindo, ajustes baseados em uso real.

**Phase prompt — passar para o agente:**
> "Leia docs/product-roadmap.md e encontre a Phase 7. Execute a TASK-040 e prepare tudo para o deploy final de produção."

- [x] **TASK-040** — Deploy de produção e onboarding do piloto
  Files: `backend/railway.toml`, `frontend/vercel.json`, `docs/onboarding-checklist.md`
  Notes: Backend: `railway up` com variáveis de ambiente de produção. Frontend: `vercel --prod` com variáveis do tenant piloto (loja de personalizados). UptimeRobot: monitorar backend, Evolution API, Supabase — alertas por WhatsApp. Asaas: cadastrar tenant piloto (plano gratuito para piloto). Evolution API: conectar número dedicado da loja. Aquecimento do número: semana 1 máximo 50 conversas/dia. Criar onboarding-checklist.md com passos para novos clientes.
  Verify: Enviar "Oi" no WhatsApp da loja. Sistema responde com comportamento humano. Pedido aparece na dashboard. Dono recebe PDF às 18h.

---

## Agent Session Guide

### Como usar este Roadmap com o Agente

1. **Início de sessão**: Passe o phase prompt da fase atual para o agente
2. **Leitura seletiva**: O agente lê apenas as seções de referência da fase para economizar contexto
3. **Marcar progresso**: Agente atualiza `- [ ]` para `- [x]` ao concluir cada task
4. **Verificação obrigatória**: O campo `Verify` de cada task deve ser validado antes de marcar como concluída
5. **Fim de fase**: Sistema deve estar em estado executável e estável antes de avançar
6. **Regra de ouro**: Dado clínico nunca no WhatsApp — verificar em toda task que envolve mensagens

### Contatos do projeto
- Banco: https://rtysmuxbscxrgpwzqmwy.supabase.co
- Backend: https://primary-production-c64a8.up.railway.app (substituir pelo FastAPI)
- Stack: Python 3.12 + FastAPI + Supabase + React + Evolution API
