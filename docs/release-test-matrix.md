# Matriz de Teste para Venda

| Área | Cenário | Resultado esperado |
|---|---|---|
| Autenticação | Login válido, inválido, refresh, logout | Cookies seguros, rotação e revogação funcionando |
| Autorização | Operador tenta função de dono/master | `403`, sem alteração de dados |
| Multi-tenant | Tenant A consulta IDs do Tenant B | Nenhum dado retornado ou alterado |
| Cadastro | Cliente, serviço, preço e atendimento | CRUD, validações e auditoria corretos |
| WhatsApp | Evento novo, duplicado, grupo e `fromMe` | Processamento único; grupos/saída ignorados |
| Horários | Mensagem dentro e fora do expediente | Fluxo ou aviso correto |
| Asaas | Overdue menor/maior que 5 dias | Aviso ou suspensão e status financeiro correto |
| Asaas | Received e reenvio do evento | Reativação única e idempotente |
| Backup | Exportação criptografada | Não contém texto puro e autentica ao descriptografar |
| Restore | Backup gerenciado em banco isolado | Login e dados críticos recuperados |
| Frontend | Desktop e mobile | Sem erros de console e fluxos principais completos |
| Deploy | Banco vazio, migração, health e rollback | Inicialização reproduzível e health `200` |
