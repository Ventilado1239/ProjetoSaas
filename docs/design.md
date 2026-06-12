---
version: alpha
name: gestao-saas-design
description: Design system moderno, limpo e premium em Light Mode para o SaaS de Gestão via WhatsApp, inspirado em interfaces contemporâneas como Linear, Vercel e Attio. Mobile-first obrigatório — o lojista e o médico usam no celular durante a operação.

colors:
  background: "#f4f4f5"
  surface: "#ffffff"
  border: "#e4e4e7"
  text-primary: "#09090b"
  text-secondary: "#71717a"
  accent: "#2563eb"
  accent-hover: "#1d4ed8"
  accent-light: "#eff6ff"
  success: "#16a34a"
  success-light: "#f0fdf4"
  warning: "#d97706"
  warning-light: "#fffbeb"
  danger: "#dc2626"
  danger-light: "#fef2f2"
  info: "#3b82f6"
  info-light: "#eff6ff"

typography:
  display:
    fontFamily: "system-ui, -apple-system, sans-serif"
    fontSize: "30px"
    fontWeight: "700"
    lineHeight: "1.2"
    letterSpacing: "-0.02em"
  h1:
    fontFamily: "system-ui, -apple-system, sans-serif"
    fontSize: "24px"
    fontWeight: "600"
    lineHeight: "1.3"
    letterSpacing: "-0.015em"
  h2:
    fontFamily: "system-ui, -apple-system, sans-serif"
    fontSize: "20px"
    fontWeight: "600"
    lineHeight: "1.3"
  h3:
    fontFamily: "system-ui, -apple-system, sans-serif"
    fontSize: "16px"
    fontWeight: "600"
    lineHeight: "1.4"
  body:
    fontFamily: "system-ui, -apple-system, sans-serif"
    fontSize: "14px"
    fontWeight: "400"
    lineHeight: "1.5"
  caption:
    fontFamily: "system-ui, -apple-system, sans-serif"
    fontSize: "12px"
    fontWeight: "400"
    lineHeight: "1.4"
  mono:
    fontFamily: "monospace"
    fontSize: "12px"
    fontWeight: "400"
    lineHeight: "1.4"

rounded:
  small: "4px"
  medium: "6px"
  large: "10px"
  full: "9999px"

spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"

components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    typography: "{typography.body}"
    rounded: "{rounded.medium}"
    padding: "8px 16px"
  button-danger:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.surface}"
    typography: "{typography.body}"
    rounded: "{rounded.medium}"
    padding: "8px 16px"
  button-success:
    backgroundColor: "{colors.success}"
    textColor: "{colors.surface}"
    typography: "{typography.body}"
    rounded: "{rounded.medium}"
    padding: "8px 16px"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    border: "1px solid {colors.border}"
    typography: "{typography.body}"
    rounded: "{rounded.medium}"
    padding: "8px 16px"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    border: "1px solid {colors.border}"
    rounded: "{rounded.large}"
    padding: "16px"
    shadow: "0 1px 3px 0 rgba(0,0,0,0.05)"
  input-text:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    border: "1px solid {colors.border}"
    typography: "{typography.body}"
    rounded: "{rounded.medium}"
    padding: "8px 12px"
  badge-aguardando:
    backgroundColor: "{colors.info-light}"
    textColor: "{colors.info}"
    typography: "{typography.caption}"
    rounded: "{rounded.full}"
    padding: "4px 8px"
  badge-confirmado:
    backgroundColor: "{colors.success-light}"
    textColor: "{colors.success}"
    typography: "{typography.caption}"
    rounded: "{rounded.full}"
    padding: "4px 8px"
  badge-producao:
    backgroundColor: "{colors.warning-light}"
    textColor: "{colors.warning}"
    typography: "{typography.caption}"
    rounded: "{rounded.full}"
    padding: "4px 8px"
  badge-pronto:
    backgroundColor: "{colors.accent-light}"
    textColor: "{colors.accent}"
    typography: "{typography.caption}"
    rounded: "{rounded.full}"
    padding: "4px 8px"
  badge-entregue:
    backgroundColor: "{colors.success-light}"
    textColor: "{colors.success}"
    typography: "{typography.caption}"
    rounded: "{rounded.full}"
    padding: "4px 8px"
  badge-falta:
    backgroundColor: "{colors.danger-light}"
    textColor: "{colors.danger}"
    typography: "{typography.caption}"
    rounded: "{rounded.full}"
    padding: "4px 8px"
  badge-aprovacao-pendente:
    backgroundColor: "{colors.warning-light}"
    textColor: "{colors.warning}"
    typography: "{typography.caption}"
    fontWeight: "600"
    rounded: "{rounded.full}"
    padding: "4px 8px"
  sidebar-item:
    backgroundColor: "transparent"
    textColor: "{colors.text-secondary}"
    typography: "{typography.body}"
    rounded: "{rounded.medium}"
    padding: "8px 12px"
  sidebar-item-active:
    backgroundColor: "{colors.accent-light}"
    textColor: "{colors.accent}"
    typography: "{typography.body}"
    rounded: "{rounded.medium}"
    padding: "8px 12px"
  alert-kill-switch:
    backgroundColor: "{colors.danger-light}"
    textColor: "{colors.danger}"
    border: "1px solid {colors.danger}"
    rounded: "{rounded.large}"
    padding: "16px"
---

# Design System — SaaS de Gestão via WhatsApp

## Overview

O sistema de design adota Light Mode de alta fidelidade visual, focado na clareza operacional e no uso mobile. O lojista e o médico acessam o sistema pelo celular durante a operação — isso é uma regra, não uma preferência. Toda decisão de layout deve ser validada primeiro em viewport de 390px.

Inspirado em Linear, Vercel Dashboard e Attio. Fundo cinza claro, superfícies brancas puras, bordas sutis e sombras discretas. Tipografia limpa de sistema. Cores semânticas para status de pedidos e consultas.

Evita-se qualquer visual escuro pesado, neons ou gradientes excessivos. O objetivo é um dashboard que o dono da loja olha em 5 segundos e entende o dia inteiro.

## Colors

- **`background` (`#f4f4f5`)**: Fundo da aplicação — contraste perfeito para destacar os cards.
- **`surface` (`#ffffff`)**: Cards, tabelas, modais e sidebar.
- **`border` (`#e4e4e7`)**: Divisores sutis — nunca usar preto.
- **`accent` (`#2563eb`)**: Azul principal — botões de ação, abas ativas, links.
- **Status semânticos de atendimento/pedido:**
  - `aguardando`: Azul claro — recém chegado
  - `confirmado`: Verde — confirmou presença ou pedido
  - `em_producao`: Âmbar — em andamento
  - `pronto`: Azul — pronto para entrega/retirada
  - `entregue/realizado`: Verde — concluído
  - `falta/cancelado`: Vermelho — não compareceu ou cancelado
  - `aprovacao_pendente`: Âmbar forte — atenção imediata necessária

## Layout

### Mobile (390px — prioritário)
- Bottom navigation bar com 5 ícones substituindo a sidebar
- Cards empilhados em coluna única
- Botões de ação com altura mínima de 44px (touch target)
- Modais em full screen no mobile

### Desktop (1024px+)
- Sidebar fixa à esquerda com 240px
- Área de conteúdo com margem de 32px
- Cards em grid de 2 ou 3 colunas
- Modais centralizados com overlay

## Elevation & Depth

- Cards: `box-shadow: 0 1px 3px 0 rgba(0,0,0,0.05), 0 1px 2px -1px rgba(0,0,0,0.05)` + borda `1px` cinza
- Drawer lateral: `box-shadow: -4px 0 12px -2px rgba(0,0,0,0.08)`
- Modal: `box-shadow: 0 20px 60px -10px rgba(0,0,0,0.15)`
- Botão primário: sombra discreta para induzir clique

## Componentes críticos do produto

### Card de Atendimento/Pedido
Exibe em ordem de prioridade:
1. Nome do cliente (h3)
2. Serviço/produto (body, text-secondary)
3. Data e horário (caption)
4. Badge de status colorido
5. Botões de ação rápida (Confirmar, Pronto, Entregar)

### Card de Aprovação Pendente
Destaque visual máximo — borda âmbar + fundo warning-light.
Exibe: cliente, produto, quantidade, valor estimado, botões APROVAR / RECUSAR em tamanho grande.
Este card nunca pode ser ignorado — deve ser o primeiro elemento visível na tela do dia.

### Alerta Kill Switch
Quando `sistema_ativo = false`, substituir todo o conteúdo por um banner vermelho centralizado:
"Sistema pausado por falta de pagamento. Regularize para reativar."
Com link para o Asaas.

### Relatório de ROI (mensal)
Card especial com destaque em verde:
"Este mês o sistema gerou R$X.XXX de impacto para sua clínica."
Quebra o padrão neutro do design para criar momento de satisfação do cliente.

## Do's and Don'ts

### Do's
- **Mobile first sempre**: Valide em 390px antes de qualquer outra resolução
- **Botões de ação grandes**: Mínimo 44px de altura — dono usa com a mão suja ou com pressa
- **Status sempre visível**: Badge de status deve ser o elemento mais fácil de ler no card
- **Feedback imediato**: Qualquer ação deve ter resposta visual em menos de 100ms
- **Aprovações em destaque**: Cards com aprovação pendente devem ser impossíveis de ignorar

### Don'ts
- **Não use fundo escuro**: O sistema é usado à luz do dia, em loja ou clínica
- **Não esconda informações financeiras**: O dono quer ver o dinheiro do dia na primeira tela
- **Não use bordas pretas**: Sempre usar a variável `border`
- **Não crie fluxos de mais de 3 cliques**: Para marcar um pedido como pronto, máximo 2 toques
- **Não exponha dados clínicos no WhatsApp preview**: Qualquer campo de diagnóstico ou resultado deve ter máscara visual
