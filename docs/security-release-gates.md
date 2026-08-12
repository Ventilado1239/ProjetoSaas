# Gates de Segurança para Produção

Nenhuma versão deve receber clientes reais enquanto algum item P0/P1 estiver aberto.

## Antes de cada deploy

- [ ] `npm audit --omit=dev` retorna zero vulnerabilidades.
- [ ] `python -m pip_audit -r requirements.txt` retorna zero vulnerabilidades conhecidas.
- [ ] Build, lint, testes de autenticação, master, RLS, segurança, webhooks, automações e jornadas Playwright passam.
- [ ] `alembic upgrade head` foi validado primeiro em cópia ou banco descartável.
- [ ] `MIGRATION_DATABASE_URL` está separada de `DATABASE_URL`; o runtime inicia pelo `docker-entrypoint.sh` e não mantém a credencial administrativa.
- [ ] O runtime usa papel PostgreSQL não-superuser e o banco não possui porta pública desnecessária.
- [ ] `ENVIRONMENT=production`, CORS e hosts contêm apenas domínios HTTPS reais.
- [ ] JWT, PII, backup, Evolution e Asaas usam segredos diferentes, aleatórios e armazenados no cofre da plataforma.
- [ ] Backup é gravado em volume persistente criptografado e um restore foi testado.
- [ ] Logs não contêm senhas, tokens, mensagens completas ou números completos de WhatsApp.

## Antes do primeiro cliente pagante

- [ ] Remover com procedimento seguro os backups legados em `backend/backups/` após confirmar retenção e necessidade legal.
- [ ] Configurar alertas de erro, disponibilidade, fila de tarefas e falha de backup.
- [ ] Documentar encarregado/canal LGPD, política de privacidade, termos, retenção e resposta a incidentes.
- [ ] Executar teste externo de intrusão e revisão jurídica LGPD. Testes automatizados não substituem essas avaliações.
- [ ] Trocar o rate limit em memória por armazenamento compartilhado (Redis) antes de escalar para múltiplas réplicas.
- [ ] Definir rotação de segredos e procedimento de revogação de sessões.

## Incidente

1. Revogar o segredo afetado e bloquear integrações suspeitas.
2. Preservar logs de auditoria sem copiar PII para canais inseguros.
3. Avaliar impacto por tenant e janela temporal.
4. Restaurar somente de backup verificado.
5. Cumprir comunicação contratual e regulatória aplicável.
