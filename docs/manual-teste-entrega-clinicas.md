# Manual de Teste e Entrega para Clínicas

Este manual descreve o fluxo seguro para testar sem arriscar WhatsApp pessoal, cadastrar clínicas separadas e entregar o sistema com nome, dados e acesso próprios.

## 1. Teste sem risco usando mock

O backend já entra em modo mock quando estas variáveis estão vazias ou ausentes:

```env
EVOLUTION_API_URL=
EVOLUTION_API_KEY=
```

Nesse modo:
- Nenhuma mensagem real é enviada pelo WhatsApp.
- O painel funciona normalmente.
- Aprovações, agenda, lista de espera, relatórios e configurações podem ser testados.
- O backend registra os envios simulados como `[MOCK WHATSAPP]` no terminal/log.

Fluxo recomendado de teste:
1. Subir banco, backend e frontend.
2. Rodar `python seed_demo.py`.
3. Entrar com `admin@demo.com` / `DemoSeguro2026` (somente no ambiente local de demonstração).
4. Testar:
   - Aprovar e recusar solicitações.
   - Confirmar atendimento na agenda.
   - Marcar falta/cancelamento.
   - Oferecer vaga na lista de espera.
   - Salvar configurações.
   - Criar e desativar um operador em **Usuários & Perfis** e confirmar que a sessão dele é revogada.
   - Ativar/suspender o Kill Switch.

## 2. Como cada clínica fica separada

Cada clínica é um `tenant`.

O isolamento acontece por:
- `tenant_id` em todas as tabelas principais.
- RLS no PostgreSQL.
- Login do usuário vinculado ao `tenant_id`.
- Webhook do WhatsApp resolvendo o tenant pela `evolution_instance_name`.

Na prática:
- Clínica A tem `tenant_id` A, usuários A e pacientes A.
- Clínica B tem `tenant_id` B, usuários B e pacientes B.
- O usuário de uma clínica não deve acessar dados de outra.

## 3. Criar uma nova clínica

Use o script:

```powershell
cd C:\Users\Felpopo\Documents\ProjetoSaas\backend
.\.venv\Scripts\python.exe provision_tenant.py `
  --nome "Clínica Sorriso" `
  --tipo clinica `
  --whatsapp 5511999999999 `
  --owner-whatsapp 5511888888888 `
  --instance-name clinica_sorriso `
  --admin-nome "Dra. Ana" `
  --admin-email ana@clinicasorriso.com `
  --admin-password SenhaForte123 `
  --plano pro `
  --cor "#2563eb"
```

O script imprime:
- `TENANT_ID`
- login do dono
- nome da instância Evolution
- variáveis `VITE_TENANT_*` para personalizar frontend/deploy.

## 4. Importar clientes da clínica

Modelo de CSV:

```csv
nome,whatsapp,data_nascimento,convenio
Maria Silva,11999999999,1988-05-20,Unimed
Joao Santos,5511988887777,15/03/1979,Particular
```

Arquivo modelo: `docs/modelo-clientes.csv`.

Importar:

```powershell
cd C:\Users\Felpopo\Documents\ProjetoSaas\backend
.\.venv\Scripts\python.exe import_clients.py `
  --tenant-id "TENANT_ID_DA_CLINICA" `
  --csv "C:\caminho\clientes.csv" `
  --update-existing
```

Regras:
- `whatsapp` pode vir como `11999999999` ou `5511999999999`.
- O script adiciona `55` quando vier só DDD+número.
- Clientes duplicados pelo mesmo WhatsApp são ignorados, ou atualizados com `--update-existing`.
- Cada importação entra apenas no `tenant_id` informado.

## 5. Entregar com nome da clínica

Para piloto simples, crie um deploy/frontend por clínica com:

```env
VITE_API_URL=https://seu-backend.com
VITE_TENANT_ID=TENANT_ID_DA_CLINICA
VITE_TENANT_NOME=Clínica Sorriso
VITE_TENANT_TIPO=clinica
VITE_TENANT_COR_PRIMARIA=#2563eb
```

Depois do login, o painel também puxa os dados reais do tenant pelo backend.

## 6. Teste com WhatsApp real sem arriscar número principal

Use sempre número dedicado.

Checklist:
1. Comprar chip ou usar número secundário.
2. Criar instância Evolution com o mesmo `--instance-name`.
3. Parear QR Code.
4. Testar com 2 a 3 contatos próprios.
5. Não importar lista real ainda.
6. Não disparar mensagens em massa.
7. Só usar clientes com consentimento.

## 7. Antes de vender como produção

Obrigatório fechar:
- Evolution real testado.
- Asaas sandbox/produção testado.
- Backup externo real.
- Monitoramento do backend e Evolution.
- Contrato, política de privacidade e termo LGPD.
- Roteiro de suporte para a primeira semana.
