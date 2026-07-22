# Plano de Resposta a Incidentes

## Acionamento

Canal interno: [TELEFONE/E-MAIL]. Responsável primário: [NOME]. Substituto: [NOME]. Jurídico/privacidade: [CONTATO].

Trate como incidente qualquer evento confirmado que comprometa confidencialidade, integridade, disponibilidade ou autenticidade de dados pessoais.

## Primeira hora

1. Registrar horário, fonte, sistemas, tenants e categorias de dados possivelmente afetadas.
2. Preservar evidências e logs; não apagar ou alterar material necessário à investigação.
3. Conter o acesso: revogar chaves/sessões, isolar integração ou suspender fluxo afetado.
4. Não compartilhar dados pessoais em chats ou tickets não autorizados.
5. Comunicar o responsável por privacidade e iniciar avaliação de risco.

## Investigação e recuperação

- Determinar causa, janela, alcance, titulares, países, dados sensíveis e possibilidade de dano.
- Rotacionar credenciais afetadas e corrigir a causa antes de restaurar tráfego.
- Restaurar em ambiente isolado quando necessário e validar integridade.
- Registrar decisões, evidências, medidas e responsáveis em linha do tempo.

## Comunicação

O controlador decide e realiza a comunicação regulatória, com apoio do operador quando aplicável. Segundo a orientação atual da ANPD, incidentes confirmados com dados pessoais que possam gerar risco ou dano relevante devem ser comunicados à ANPD e aos titulares em três dias úteis, ressalvadas regras específicas. Validar o caso com assessoria jurídica.

A comunicação deve ser clara e incluir natureza/categorias afetadas, medidas de segurança, riscos, data do conhecimento, mitigação, justificativa de eventual atraso e contato responsável.

Procedimento oficial: [Comunicação de Incidente de Segurança — ANPD](https://www.gov.br/anpd/pt-br/canais_atendimento/agente-de-tratamento/comunicado-de-incidente-de-seguranca-cis).

## Encerramento

- Confirmar recuperação, monitorar recorrência e documentar causa raiz.
- Notificar clientes conforme contrato.
- Criar ações corretivas com proprietário e prazo.
- Atualizar controles, testes, runbook e treinamento.
- Manter o registro pelo prazo definido na política interna e na regulamentação aplicável.
