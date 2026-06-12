import random
from typing import Dict, List

MESSAGES: Dict[str, List[str]] = {
    "welcome_clinica": [
        "Olá, {nome}! Seja muito bem-vindo(a) à {tenant_nome}. Como posso te ajudar hoje?\n\n1. Agendar uma consulta/procedimento\n2. Ver meus agendamentos\n3. Falar com a recepção",
        "Oi, {nome}! Tudo bem? Aqui é o assistente virtual da {tenant_nome}. Escolha uma das opções abaixo:\n\n1. Marcar nova consulta\n2. Consultar meus horários\n3. Falar com um atendente",
        "Olá, {nome}, é um prazer falar com você na {tenant_nome}! Digite o número correspondente à sua opção:\n\n1. Agendamento de consultas\n2. Meus horários marcados\n3. Suporte da recepção",
        "Seja bem-vindo(a) à {tenant_nome}, {nome}! Como posso te auxiliar?\n\n1. Realizar novo agendamento\n2. Checar meus agendamentos ativos\n3. Falar com a nossa equipe"
    ],
    "welcome_loja": [
        "Olá, {nome}! Seja muito bem-vindo(a) à {tenant_nome}. Selecione uma opção para começar seu pedido:\n\n{produtos_menu}\n\nOutras opções:\nC. Ver meus pedidos em aberto\nS. Falar com o suporte",
        "Oi, {nome}! É um prazer receber você na {tenant_nome}. O que você deseja pedir hoje? Escolha pelo número:\n\n{produtos_menu}\n\nOutras opções:\nC. Ver meus pedidos ativos\nS. Falar com suporte humano",
        "Olá, {nome}! Boas-vindas à {tenant_nome}. Escolha um dos nossos produtos abaixo:\n\n{produtos_menu}\n\nVocê também pode digitar:\nC. Meus pedidos em aberto\nS. Falar com o atendimento",
        "Oi, {nome}! Tudo bem? Seja bem-vindo(a) à {tenant_nome}. Para iniciar seu pedido, escolha o produto pelo número correspondente:\n\n{produtos_menu}\n\nOu digite:\nC. Consultar meus pedidos\nS. Falar com a equipe de suporte"
    ],
    "ask_quantity": [
        "Ótima escolha! Quantas unidades de {produto} você gostaria de pedir?",
        "Perfeito! Me informe a quantidade de {produto} que deseja solicitar.",
        "Excelente! Qual a quantidade desejada de {produto}?",
        "Muito bom! Digite a quantidade de {produto} que você precisa."
    ],
    "ask_date_time": [
        "Para agendar {servico}, qual o dia e horário de sua preferência? (Exemplo: 10/06 às 14:00)",
        "Excelente! Que dia e horário ficaria melhor para seu atendimento de {servico}? (Exemplo: Amanhã às 10:00)",
        "Certo! Qual a sua preferência de data e hora para a realização de {servico}?",
        "Perfeito! Digite o dia e horário desejados para {servico}."
    ],
    "ask_personalization": [
        "Como deseja personalizar seu {produto}? Digite os detalhes (nomes, cores, tema) abaixo:",
        "Por favor, descreva como gostaria da personalização de seu {produto} (texto, tema, cores):",
        "Agora me conta: quais detalhes você quer na arte do seu {produto}?",
        "Digite as informações de personalização para seu {produto} (tema, nome, cor de preferência):"
    ],
    "confirm_loja": [
        "Confirme os detalhes do seu pedido:\n\n📦 Produto: {produto}\n🔢 Quantidade: {qtd} unidades\n🎨 Personalização: {personalizacao}\n💵 Valor total: R$ {total}\n\nEstá tudo correto?\n1. Sim, confirmar pedido\n2. Não, quero alterar algo\n3. Cancelar pedido",
        "Por favor, revise o resumo da sua solicitação:\n\n📦 Item: {produto}\n🔢 Qtd: {qtd}\n🎨 Detalhes: {personalizacao}\n💵 Preço Total: R$ {total}\n\nPodemos confirmar?\n1. Sim, confirmar\n2. Não, prefiro corrigir\n3. Cancelar",
        "Aqui está o resumo do seu pedido para validação:\n\n📦 Produto: {produto}\n🔢 Quantidade: {qtd}\n🎨 Personalização: {personalizacao}\n💵 Valor: R$ {total}\n\nConfirma as informações?\n1. Sim, confirmar\n2. Não, fazer alterações\n3. Cancelar",
        "Tudo pronto! Veja se está tudo certinho:\n\n📦 Item: {produto}\n🔢 Quantidade: {qtd} un\n🎨 Personalização: {personalizacao}\n💵 Total: R$ {total}\n\nPodemos enviar para aprovação?\n1. Sim, está correto\n2. Não, quero editar\n3. Cancelar"
    ],
    "confirm_clinica": [
        "Confirme os detalhes do seu agendamento:\n\n📅 Serviço: {servico}\n⏱️ Data/Hora: {data_hora}\n\nEstá tudo correto?\n1. Sim, confirmar agendamento\n2. Não, quero alterar\n3. Cancelar",
        "Revise as informações da sua consulta:\n\n📅 Atendimento: {servico}\n⏱️ Horário: {data_hora}\n\nPodemos agendar?\n1. Sim, confirmar\n2. Não, prefiro corrigir\n3. Cancelar",
        "Confirma seu agendamento com os seguintes dados:\n\n📅 Serviço: {servico}\n⏱️ Data e hora: {data_hora}\n\nEstá correto?\n1. Sim, confirmar\n2. Não, alterar detalhes\n3. Cancelar",
        "Veja se as informações de agendamento estão corretas:\n\n📅 Serviço: {servico}\n⏱️ Agendado para: {data_hora}\n\nPodemos prosseguir?\n1. Sim, está certo\n2. Não, quero mudar\n3. Cancelar"
    ],
    "order_created_loja": [
        "Perfeito! Seu pedido de {produto} foi registrado com sucesso. Entraremos em contato em breve com os próximos passos! 👍",
        "Feito! Seu pedido de {produto} já está no nosso sistema. Muito obrigado pela preferência! 😊",
        "Sucesso! Registramos seu pedido de {produto}. Em breve você receberá atualizações sobre a produção.",
        "Maravilha! Seu pedido de {produto} foi cadastrado. Agradecemos o contato!"
    ],
    "appointment_created_clinica": [
        "Tudo certo! Seu agendamento para {servico} foi confirmado no dia {data_hora}. Te aguardamos! 🩺",
        "Consulta agendada com sucesso! Seu atendimento de {servico} ficou marcado para {data_hora}.",
        "Perfeito! Seu horário para {servico} em {data_hora} foi reservado com sucesso. Até logo!",
        "Confirmado! Agendamos {servico} para {data_hora}. Enviamos lembretes antes do seu horário."
    ],
    "out_of_hours": [
        "Olá! No momento estamos fechados. Nosso horário de atendimento é das {horario_abertura} às {horario_fechamento}. Retornaremos seu contato assim que abrirmos! 😴",
        "Oi! Recebemos sua mensagem, mas nosso expediente é das {horario_abertura} às {horario_fechamento}. Entraremos em contato no início do próximo expediente.",
        "Olá, obrigado pelo contato! Funcionamos de segunda a sexta, das {horario_abertura} às {horario_fechamento}. Responderemos sua mensagem em breve.",
        "Olá! Nossos atendentes e o sistema automático estão descansando agora. Nosso horário de funcionamento é das {horario_abertura} às {horario_fechamento}. Até mais!"
    ],
    "large_order_hold": [
        "Seu pedido excede o limite automático para mensagens rápidas. Ele foi encaminhado para a aprovação especial do gerente e entraremos em contato em breve! ⏳",
        "Como a quantidade solicitada é alta, encaminhamos seu pedido para validação direta de nossa gerência. Entraremos em contato para finalizar!",
        "Identificamos que seu pedido é de grande porte. Um de nossos atendentes irá analisar as condições especiais e entrará em contato com você.",
        "Por se tratar de um volume grande, seu pedido passará por aprovação manual do lojista para garantirmos a disponibilidade. Retornaremos em breve!"
    ],
    "audio_error": [
        "Desculpe, no momento não consigo ouvir áudios. Poderia me enviar em formato de texto? ✍️",
        "Não consigo processar mensagens de voz por aqui. Pode digitar para mim, por favor?",
        "Ops! Infelizmente não posso escutar áudio neste momento. Se puder mandar em texto, agradeço!",
        "Poxa, não consigo ouvir mensagens de áudio por este canal. Por favor, envie em texto."
    ],
    "media_error": [
        "Recebi seu arquivo, mas no momento só consigo processar mensagens de texto. Poderia digitar sua solicitação?",
        "Não consigo analisar imagens ou arquivos agora. Pode escrever em texto o que você precisa?",
        "Ops! Recebi um anexo, mas no momento funciono apenas via texto. Escreva sua mensagem, por favor.",
        "Olá! Arquivos de mídia não são aceitos nesta etapa. Por favor, digite o que precisa em formato de texto."
    ],
    "cancelado": [
        "Pedido/agendamento cancelado com sucesso. Se precisar de algo mais, é só chamar! 👍",
        "Sua solicitação foi cancelada. Caso queira recomeçar, basta enviar uma nova mensagem.",
        "Cancelamento realizado. Obrigado e tenha um ótimo dia!",
        "Tudo bem, solicitação cancelada. Quando quiser falar conosco novamente, basta mandar um 'Oi'."
    ],
    "invalid_option": [
        "Desculpe, não entendi. Escolha uma das opções válidas digitando o número correspondente.",
        "Opção inválida. Por favor, digite apenas o número da opção desejada.",
        "Ops! Essa opção não existe. Digite o número correto da lista acima.",
        "Por favor, escolha digitando apenas o número correspondente às opções enviadas."
    ],
    "ask_confirmacao_48h": [
        "Olá, {nome}! Confirmamos sua consulta de {servico} para {data_hora}? \n\n1. Sim, confirmar\n2. Não, preciso cancelar",
        "Oi, {nome}! Tudo bem? Passando para confirmar seu horário para {servico} no dia {data_hora}. Podemos confirmar?\n\n1. Sim\n2. Não",
        "Olá, {nome}! Seu agendamento de {servico} está marcado para {data_hora}. Confirma sua presença?\n\n1. Sim, confirmo\n2. Não, quero cancelar",
        "Oi, {nome}! Você tem um agendamento de {servico} no dia {data_hora}. Responda com a opção desejada:\n\n1. Sim, está confirmado\n2. Não, preciso desmarcar"
    ],
    "lembrete_final_48h": [
        "Olá, {nome}! Ainda não recebemos sua resposta sobre o agendamento de {servico} para {data_hora}. Por favor, confirme se irá comparecer:\n\n1. Sim, confirmar\n2. Não, cancelar",
        "Oi! Precisamos da sua confirmação para o horário de {servico} no dia {data_hora}. Responda:\n\n1. Sim, vou comparecer\n2. Não vou",
        "Lembrete importante: confirma seu horário de {servico} em {data_hora}?\n\n1. Sim\n2. Não",
        "Olá! Por favor, responda se vai conseguir vir no dia {data_hora} para {servico}:\n\n1. Sim\n2. Não"
    ],
    "confirmacao_sucesso": [
        "Ótimo! Seu agendamento foi confirmado com sucesso. Te aguardamos! 😊",
        "Perfeito! Confirmamos sua presença. Até lá! 👍",
        "Tudo certo! Presença confirmada no sistema. Obrigado!",
        "Confirmado! Nos vemos no horário agendado. Tenha um ótimo dia!"
    ],
    "confirmacao_cancelado": [
        "Pedido/agendamento cancelado com sucesso. Se precisar de algo mais, é só chamar! 👍",
        "Sua solicitação foi cancelada. Caso queira recomeçar, basta enviar uma nova mensagem.",
        "Cancelamento realizado. Obrigado e tenha um ótimo dia!",
        "Tudo bem, solicitação cancelada. Quando quiser falar conosco novamente, basta mandar um 'Oi'."
    ],
    "crm_reactivate_3m": [
        "Olá, {nome}! Sentimos sua falta na {tenant_nome}. Que tal agendar um horário conosco? 😊",
        "Oi, {nome}! Faz um tempo que não vemos você na {tenant_nome}. Gostaria de agendar seu próximo atendimento?",
        "Olá, {nome}! Passando para saber se está tudo bem e se gostaria de agendar uma nova visita na {tenant_nome}?",
        "Oi, {nome}! Tudo bem? Que tal aproveitar a semana para marcar seu atendimento na {tenant_nome}?"
    ],
    "crm_reactivate_6m": [
        "Oi, {nome}! Faz 6 meses desde sua última consulta na {tenant_nome}. É muito importante manter sua rotina de cuidados preventiva. Deseja agendar um horário? 🩺",
        "Olá, {nome}! Já se passaram 6 meses desde seu último atendimento na {tenant_nome}. Que tal agendar um retorno preventivo?",
        "Oi, {nome}! Passando para lembrar que já faz 6 meses desde a sua última visita na {tenant_nome}. Vamos cuidar da sua saúde?",
        "Olá, {nome}! Para manter seu bem-estar em dia, recomendamos um retorno a cada 6 meses. Vamos agendar seu horário na {tenant_nome}?"
    ],
    "crm_reactivate_12m": [
        "Olá, {nome}! Quanto tempo! Temos condições especiais de retorno para você na {tenant_nome}. Vamos marcar seu horário? Esperamos você!",
        "Oi, {nome}! Já faz um ano desde sua última consulta na {tenant_nome}. Sentimos sua falta! Que tal aproveitar este mês para retornar?",
        "Olá, {nome}! Que tal retornar à {tenant_nome} com um desconto especial de reativação? Responda se tem interesse!",
        "Oi, {nome}! Um ano se passou e queremos muito te ver de novo na {tenant_nome}. Vamos agendar uma consulta de retorno?"
    ]
}

def get_message(key: str, **kwargs) -> str:
    """Returns a formatted, randomized message variation for a given key."""
    if key not in MESSAGES:
        return f"Mensagem indisponível ({key})"
    variation = random.choice(MESSAGES[key])
    try:
        return variation.format(**kwargs)
    except KeyError as e:
        # Fallback to unformatted if keys mismatch
        return variation
