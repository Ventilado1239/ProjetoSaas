# Manual do Painel Master

## Acesso

- URL local: `http://localhost:5173/`
- Na tela de login, clique em `Entrar no Painel Master`.
- Credenciais de validação:
  - E-mail: `master@admin.com`
  - Senha: `master123`

## Fluxo para cadastrar uma clínica

1. Acesse `Painel Master`.
2. Clique em `Nova clínica`.
3. Preencha nome da clínica, WhatsApp comercial, WhatsApp do responsável, e-mail de acesso, senha inicial, plano, mensalidade e instância Evolution.
4. Ao criar, o sistema já provisiona:
   - tenant isolado;
   - usuário dono da clínica;
   - configuração operacional inicial;
   - serviços padrão;
   - credenciais para entregar ao cliente.
5. O cliente acessa o mesmo site em `http://localhost:5173/`, mas usando o login da clínica criada.

## Gestão dos clientes

No bloco `Clientes SaaS`, você consegue:

- buscar clínica por nome, responsável, e-mail ou WhatsApp;
- alterar status financeiro: `em_dia`, `atrasado`, `inadimplente`, `cancelado`;
- alterar etapa operacional: `onboarding`, `ativo`, `risco`, `cancelado`;
- suspender ou reativar o acesso da clínica;
- redefinir a senha do usuário dono;
- conferir instância Evolution e WhatsApp configurados;
- acompanhar uso por pacientes, usuários e atendimentos.

## CRM comercial

No bloco `CRM Comercial`, você consegue:

- cadastrar leads antes de virarem clientes;
- registrar responsável, e-mail, WhatsApp, valor potencial e próxima ação;
- mover a etapa do lead entre `lead`, `demo`, `proposta`, `negociacao`, `ganho` e `perdido`.

## Financeiro

Quando algum cliente fica como `atrasado` ou `inadimplente`, o painel exibe automaticamente o bloco `Atenção financeira` com os clientes que precisam de cobrança.

## Integração com o app principal

O Painel Master usa uma autenticação separada da clínica. Cada clínica criada entra no app principal com seu próprio usuário, tenant, marca, WhatsApp e instância Evolution. Isso mantém os clientes separados e evita misturar dados entre clínicas.

## Comandos úteis

Backend:

```powershell
cd C:\Users\Felpopo\Documents\ProjetoSaas\backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe seed_master.py
.\.venv\Scripts\python.exe seed_demo.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd C:\Users\Felpopo\Documents\ProjetoSaas\frontend
npm run dev
```
