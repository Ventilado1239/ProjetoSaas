# Senior Frontend AI Architect & Product Engineering Swarm
## Missão: Refinamento Estético Avançado, Performance e Modernização Completa
### SaaS de Gestão via WhatsApp — Elevação para Nível Premium

---

## Contexto do Produto

Este é um SaaS multi-tenant de gestão operacional via WhatsApp para clínicas médicas e lojas de personalizados. O frontend foi gerado nas fases anteriores com React 18 + Vite + TypeScript + Tailwind. O objetivo desta missão é transformar o produto em uma aplicação premium com visual e performance dignos de grandes players do mercado como Vercel, Linear, Supabase e Attio.

**Regra absoluta:** Dado clínico (diagnóstico, resultado, medicamento) nunca aparece em nenhuma tela ou log. Verificar em 100% dos componentes que renderizam dados de pacientes.

---

## Orchestração de Subagentes — Executar em Paralelo

### Subagente 1 — Aesthetics, Typography & Motion Design

**Missão:** Elevar o visual de todas as telas ao nível de produto premium. Zero compromisso estético.

#### Tipografia
- Instalar e configurar a fonte **Inter** via `@fontsource/inter` (não Google Fonts — evitar requisição externa)
- Pesos utilizados: 400 (body), 500 (medium), 600 (semibold), 700 (bold)
- Aplicar `font-feature-settings: "cv11", "ss01"` para ativar variantes tipográficas modernas da Inter
- `letter-spacing: -0.011em` em headings para visual contemporâneo
- `text-rendering: optimizeLegibility` global
- Hierarquia tipográfica: display 30px / h1 24px / h2 20px / h3 16px / body 14px / caption 12px

#### Paleta de Cores com Variáveis HSL
Implementar sistema dual de temas via CSS variables no `index.css`:

```css
/* Modo Clínica */
[data-theme="clinica"] {
  --color-accent: 221 83% 53%;        /* #2563eb */
  --color-accent-hover: 221 83% 45%;
  --color-accent-light: 214 100% 97%;
  --color-success: 142 71% 45%;
  --color-warning: 38 92% 50%;
  --color-danger: 0 72% 51%;
  --color-bg: 240 5% 96%;             /* #f4f4f5 */
  --color-surface: 0 0% 100%;
  --color-border: 240 6% 90%;
  --color-text-primary: 240 10% 4%;
  --color-text-secondary: 240 4% 46%;
}

/* Modo Loja */
[data-theme="loja"] {
  --color-accent: 262 83% 58%;        /* roxo vibrante */
  --color-accent-hover: 262 83% 50%;
  --color-accent-light: 262 100% 97%;
  --color-success: 142 71% 45%;
  --color-warning: 38 92% 50%;
  --color-danger: 0 72% 51%;
  --color-bg: 240 5% 96%;
  --color-surface: 0 0% 100%;
  --color-border: 240 6% 90%;
  --color-text-primary: 240 10% 4%;
  --color-text-secondary: 240 4% 46%;
}
```

O tema é injetado automaticamente no `<html>` baseado em `VITE_TENANT_TIPO` — sem interação do usuário.

#### Micro-animações e Motion Design
Implementar usando **apenas CSS transitions e keyframes** — sem bibliotecas de animação para manter bundle enxuto:

```css
/* Transições globais */
* { transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1); }

/* Hover em cards */
.card { transition: box-shadow 150ms, transform 150ms; }
.card:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.08); }

/* Fade-in de telas */
.page-enter { animation: fadeIn 200ms ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

/* Shimmer de carregamento */
.shimmer { background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* Sidebar item hover */
.sidebar-item { transition: background-color 120ms, color 120ms; }

/* Botão loading */
.btn-loading { transition: opacity 150ms; opacity: 0.7; pointer-events: none; }

/* Badge pulse para aprovações pendentes */
.badge-urgent { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
```

#### Componentes Visuais — Refinar Cada Um

**Cards do Dashboard:**
- Gradiente sutil no fundo: `background: linear-gradient(135deg, hsl(var(--color-surface)) 0%, hsl(var(--color-accent-light)) 100%)`
- Ícone colorido no canto superior direito de cada card com fundo pastel
- Valor principal em `font-size: 32px; font-weight: 700; letter-spacing: -0.02em`
- Label em caption com text-secondary
- Variação percentual em relação ao dia anterior (verde se positivo, vermelho se negativo)
- Shimmer animado durante loading — nunca mostrar zero ou undefined

**Card de Aprovação Pendente:**
- Borda esquerda sólida de 3px na cor warning como indicador visual
- Fundo `warning-light` com opacidade 50%
- Badge pulsante "URGENTE" quando tempo de espera > 2 horas
- Botões APROVAR e RECUSAR em largura total no mobile — altura mínima 52px

**Tabelas:**
- Header com `background: hsl(var(--color-bg))` e `font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em`
- Linhas com hover sutil `background: hsl(var(--color-bg))`
- Rolagem horizontal nativa em mobile — nunca clipping
- Empty state elegante com ícone SVG inline + mensagem contextual

**Badges de Status:**
- Cantos `border-radius: 9999px`
- Fundo pastel + texto na cor semântica correspondente
- Font-size: 11px; font-weight: 500; padding: 2px 8px
- Status mapping completo: aguardando→azul, confirmado→verde, em_producao→âmbar, pronto→azul-royal, entregue→verde-escuro, falta→vermelho, abandonado→cinza

**Inputs e Forms:**
- Focus ring: `box-shadow: 0 0 0 3px hsl(var(--color-accent) / 0.15)` — nunca outline padrão do browser
- Borda muda para accent color no focus
- Placeholder em text-secondary com opacidade 0.6
- Label sempre acima do input — nunca placeholder como label
- Mensagem de erro inline em danger color com ícone de alerta

**Sidebar Desktop:**
- Logo do tenant no topo com fallback de iniciais se logo_url for null
- Separador visual entre grupos de navegação
- Badge numérico vermelho nas aprovações pendentes — atualizar em tempo real
- Footer com nome do usuário logado, perfil e botão de logout
- Largura: 240px fixo — nunca colapsar no desktop

**Bottom Navigation Mobile:**
- Altura: 64px com safe-area-inset-bottom para iPhones com notch
- Ícones: 22px com label de 10px abaixo
- Item ativo: cor accent + escala 1.05 com transition
- Badge de aprovações pendentes no ícone correspondente

---

### Subagente 2 — Performance, State Management & API Layer

**Missão:** Eliminar renders desnecessários, otimizar chamadas de API, implementar tratamento de erro robusto e garantir experiência fluida mesmo em conexões lentas.

#### Zustand — Migração para Seletores Estritos

**Problema atual:** Componentes desestruturando todo o store causam re-renders em cascata.

**Solução obrigatória:**

```typescript
// ❌ PROIBIDO — causa re-render em qualquer mudança do store
const { clientes, loading, error } = useStore()

// ✅ CORRETO — re-render apenas quando clientes muda
const clientes = useStore(state => state.clientes)
const loading = useStore(state => state.loading.clientes)
const error = useStore(state => state.error.clientes)
```

Auditar 100% dos componentes e migrar para seletores estritos. Criar arquivo `src/store/selectors.ts` com todos os seletores tipados e memoizados.

#### Estrutura do Store Otimizada

```typescript
// src/store/useStore.ts — estrutura obrigatória
interface StoreState {
  // Data
  dashboard: DashboardData | null
  clientes: Cliente[]
  atendimentos: Atendimento[]
  aprovacoes: Aprovacao[]
  servicos: Servico[]
  listaEspera: ListaEspera[]

  // Loading granular — nunca um loading global
  loading: {
    dashboard: boolean
    clientes: boolean
    atendimentos: boolean
    aprovacoes: boolean
    servicos: boolean
    submit: boolean      // loading específico de botões de ação
  }

  // Error granular
  error: {
    dashboard: string | null
    clientes: string | null
    atendimentos: string | null
    global: string | null
  }

  // Actions
  fetchDashboard: () => Promise<void>
  fetchClientes: (query?: string) => Promise<void>
  updateAtendimentoStatus: (id: string, status: string) => Promise<void>
  aprovarPedido: (id: string) => Promise<void>
  recusarPedido: (id: string) => Promise<void>
}
```

#### API Layer — `src/services/api.ts`

**Problema crítico a resolver:** Race condition no refresh de token. Se múltiplas requisições recebem 401 simultâneo, podem ocorrer múltiplos refreshes ou logout incorreto.

**Solução com fila de refresh:**

```typescript
// Implementar exatamente este padrão
let isRefreshing = false
let failedQueue: Array<{resolve: Function, reject: Function}> = []

const processQueue = (error: Error | null, token: string | null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    error ? reject(error) : resolve(token)
  })
  failedQueue = []
}

// Interceptor de response
api.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(() => api(originalRequest))
      }
      originalRequest._retry = true
      isRefreshing = true
      try {
        await refreshToken()
        processQueue(null, null)
        return api(originalRequest)
      } catch (err) {
        processQueue(err as Error, null)
        logout()
        return Promise.reject(err)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  }
)
```

#### React Query — Implementar para Cache e Sincronização

Instalar `@tanstack/react-query`. Migrar todas as chamadas de dados para queries com cache:

```typescript
// Exemplo — Dashboard
const { data: dashboard, isLoading } = useQuery({
  queryKey: ['dashboard', 'hoje'],
  queryFn: () => api.get('/dashboard/hoje').then(r => r.data),
  refetchInterval: 30_000,     // atualiza a cada 30s automaticamente
  staleTime: 20_000,           // considera fresco por 20s
  retry: 2,
})

// Exemplo — Mutação com feedback
const aprovarMutation = useMutation({
  mutationFn: (id: string) => api.patch(`/atendimentos/${id}/status`, { status: 'confirmado' }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['aprovacoes'] })
    queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    toast.success('Pedido aprovado!')
  },
  onError: () => toast.error('Erro ao aprovar. Tente novamente.'),
})
```

#### Debounce na Busca de Clientes

```typescript
// src/hooks/useDebounce.ts
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debouncedValue
}

// Uso no componente Clientes.tsx
const [busca, setBusca] = useState('')
const buscaDebounced = useDebounce(busca, 300)

useEffect(() => {
  if (buscaDebounced) fetchClientes(buscaDebounced)
}, [buscaDebounced])
```

#### Performance — Lazy Loading de Rotas

```typescript
// App.tsx — code splitting por rota
const Dashboard = lazy(() => import('./components/Dashboard'))
const Agenda = lazy(() => import('./components/Agenda'))
const Clientes = lazy(() => import('./components/Clientes'))
const Relatorios = lazy(() => import('./components/Relatorios'))

// Envolver com Suspense + skeleton
<Suspense fallback={<PageSkeleton />}>
  <Dashboard />
</Suspense>
```

#### Otimizações de Bundle

No `vite.config.ts`:
```typescript
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        vendor: ['react', 'react-dom'],
        charts: ['recharts'],
        store: ['zustand'],
        query: ['@tanstack/react-query'],
      }
    }
  }
}
```

---

### Subagente 3 — TypeScript Strict & Code Quality

**Missão:** Zero erros de TypeScript, zero `any`, zero warnings de ESLint.

#### Tipos Centralizados — `src/types/index.ts`

Criar e manter todos os tipos em um único arquivo:

```typescript
export type TenantTipo = 'clinica' | 'loja'
export type PerfilUsuario = 'dono' | 'medico' | 'recepcionista' | 'funcionario'

export type StatusAtendimento =
  | 'aguardando' | 'confirmado' | 'em_producao'
  | 'pronto' | 'realizado' | 'entregue'
  | 'cancelado' | 'falta' | 'abandonado'

export type StatusReativacao =
  | 'ativo' | 'inativo_3m' | 'inativo_6m' | 'inativo_12m' | 'reativado'

export interface Tenant {
  id: string
  nome: string
  tipo: TenantTipo
  sistema_ativo: boolean
  cor_primaria: string
  logo_url: string | null
  plano: 'starter' | 'pro' | 'premium'
}

export interface ClientePaciente {
  id: string
  tenant_id: string
  nome: string
  whatsapp: string
  data_nascimento: string | null
  convenio: string | null
  total_atendimentos: number
  ticket_medio: number
  ultima_consulta: string | null
  status_reativacao: StatusReativacao
  criado_em: string
}

export interface AtendimentoPedido {
  id: string
  tenant_id: string
  cliente: ClientePaciente
  data_agendamento: string
  data_atendimento: string | null
  data_entrega: string | null
  status: StatusAtendimento
  confirmado: boolean
  compareceu: boolean | null
  total: number
  pago: boolean
  lojista_aprovado: boolean
  origem: 'whatsapp' | 'dashboard'
}

export interface DashboardData {
  atendimentos_hoje: number
  confirmados: number
  aprovacoes_pendentes: number
  receita_dia: number
  variacao_atendimentos: number  // % vs ontem
  variacao_receita: number       // % vs ontem
  atendimentos: AtendimentoPedido[]
}

// Props de componentes sempre tipadas
export interface CardMetricaProps {
  label: string
  valor: number | string
  variacao?: number
  icone: React.ReactNode
  loading?: boolean
  formato?: 'numero' | 'moeda' | 'percentual'
}
```

#### Configuração TypeScript Strict

```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "noImplicitReturns": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "exactOptionalPropertyTypes": true
  }
}
```

#### ESLint — Configuração Completa

```json
// .eslintrc.json
{
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/strict",
    "plugin:react-hooks/recommended",
    "plugin:jsx-a11y/recommended"
  ],
  "rules": {
    "@typescript-eslint/no-explicit-any": "error",
    "@typescript-eslint/no-unused-vars": "error",
    "react-hooks/exhaustive-deps": "warn",
    "no-console": ["warn", { "allow": ["error"] }]
  }
}
```

---

### Subagente 4 — UX & Accessibility

**Missão:** Tornar o produto intuitivo para donos de loja com baixa familiaridade tecnológica. Cada ação deve ser óbvia, cada erro deve ser recuperável.

#### Toast Notifications — `src/components/Toast.tsx`

Implementar sistema de toasts leve sem biblioteca externa:

```typescript
// Posição: top-right desktop, top-center mobile
// Tipos: success (verde), error (vermelho), warning (âmbar), info (azul)
// Auto-dismiss: 4 segundos
// Ação de fechar manual
// Máximo 3 toasts simultâneos — fila os demais
// Animação: slide-in da direita + fade-out
```

#### Estados de Loading Granulares

**Regra:** Nunca bloquear a tela inteira com loading. Cada elemento carrega de forma independente.

- Botão de ação: substituir texto por spinner inline + desabilitar durante requisição
- Tabela: shimmer por linha enquanto carrega — nunca tela em branco
- Card de métrica: shimmer no valor enquanto carrega — label sempre visível
- Modal: skeleton do conteúdo antes dos dados chegarem

#### Empty States Contextuais

Cada tela vazia deve ter mensagem específica e ação sugerida:

```
Dashboard sem atendimentos hoje:
→ Ícone de calendário + "Nenhum atendimento hoje. Que tal verificar a agenda de amanhã?"

Clientes sem resultado de busca:
→ Ícone de busca + "Nenhum cliente encontrado para '[termo]'. Verifique o número ou nome."

Aprovações zeradas:
→ Ícone de check verde + "Tudo em dia! Nenhuma aprovação pendente. 🎉"

Lista de espera vazia:
→ Ícone de lista + "Nenhum cliente na fila de espera para este serviço."
```

#### Confirmações Destrutivas

Qualquer ação irreversível (cancelar atendimento, excluir cliente, desativar serviço) deve exibir modal de confirmação com:
- Descrição clara do que será feito
- Nome/identificação do item afetado
- Botão de confirmação em vermelho com texto explícito ("Sim, cancelar atendimento")
- Botão de cancelamento em destaque secundário

#### Acessibilidade Mínima

- Todos os botões com `aria-label` descritivo
- Imagens com `alt` adequado
- Inputs com `id` e `htmlFor` no label correspondente
- Contraste mínimo WCAG AA em todas as combinações de cor
- Focus visible em todos os elementos interativos — nunca `outline: none` sem substituto

---

## Protocolo de Verificação Final

Executar na ordem exata e confirmar sucesso de cada etapa:

```bash
# 1. Verificar tipos
npx tsc --noEmit
# Resultado esperado: zero erros

# 2. Verificar qualidade de código
npm run lint
# Resultado esperado: zero warnings, zero errors

# 3. Build de produção
npm run build
# Resultado esperado: build completo sem warnings de chunk > 500kb

# 4. Preview local
npm run preview
# Validar visualmente as telas principais

# 5. Lighthouse audit (via browser DevTools)
# Targets: Performance > 90 | Accessibility > 95 | Best Practices > 95
```

### Screenshots obrigatórias ao final

Capturar e salvar em `docs/screenshots/`:
1. `dashboard-desktop.png` — Dashboard em 1440px com dados carregados
2. `dashboard-mobile.png` — Dashboard em 390px
3. `aprovacoes-pendentes.png` — Tela de aprovações com cards em destaque
4. `clientes-busca.png` — Tela de clientes com busca ativa
5. `agenda-modal.png` — Modal de detalhes de atendimento aberto

---

## Restrições Absolutas

- Nenhuma dependência nova que adicione mais de 50kb ao bundle sem justificativa explícita
- Nenhum `console.log` no código de produção
- Nenhum `any` em TypeScript — usar `unknown` + type guard quando necessário
- Nenhuma chamada de API sem tratamento de erro visível para o usuário
- Nenhuma tela sem estado de loading e empty state implementados
- Dado clínico (diagnóstico, resultado, medicamento) nunca renderizado em nenhum componente

---

## Resultado Esperado

Ao final desta missão, o frontend deve ser indistinguível visualmente de um produto SaaS de primeira linha, com performance de carregamento < 1 segundo, zero erros de TypeScript, código 100% tipado e experiência intuitiva para um dono de loja ou clínica que nunca usou um sistema antes.
