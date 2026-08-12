export type TabType = 
  | 'dashboard'
  | 'aprovacoes'
  | 'agenda'
  | 'clientes'
  | 'servicos'
  | 'lista_espera'
  | 'relatorios'
  | 'configuracoes';

export type TenantTipo = 'clinica' | 'loja';
export type PerfilUsuario = 'dono' | 'medico' | 'recepcionista' | 'funcionario';

export type StatusAtendimento =
  | 'aguardando' | 'confirmado' | 'em_producao'
  | 'pronto' | 'realizado' | 'entregue'
  | 'cancelado' | 'falta' | 'abandonado';

export type StatusReativacao =
  | 'ativo' | 'inativo_3m' | 'inativo_6m' | 'inativo_12m' | 'reativado';

export interface Tenant {
  id: string;
  nome: string;
  tipo: TenantTipo;
  sistema_ativo: boolean;
  cor_primaria: string;
  logo_url: string | null;
  plano: 'starter' | 'pro' | 'premium';
}

export interface User {
  id: string;
  nome: string;
  email: string;
  perfil: PerfilUsuario;
  tenant_id: string;
}

export interface Preco {
  id?: string;
  qtd_min: number;
  qtd_max: number;
  preco_particular: number;
  preco_convenio?: number;
  convenio?: string;
}

export interface Servico {
  id: string;
  nome: string;
  categoria?: string;
  duracao_minutos?: number;
  ativo: boolean;
  precos: Preco[];
}

export interface ItemAtendimento {
  id: string;
  servico_id: string;
  quantidade: number;
  preco_unitario: number;
  personalizacao?: string;
  status_arte: string;
}

export interface ClientePaciente {
  id: string;
  tenant_id: string;
  nome: string;
  whatsapp: string;
  data_nascimento: string | null;
  convenio: string | null;
  total_atendimentos: number;
  ticket_medio: number;
  ultima_consulta: string | null;
  status_reativacao: StatusReativacao;
  criado_em: string;
}

// Keep Cliente alias for backwards compatibility
export interface Cliente {
  id: string;
  nome: string;
  whatsapp: string;
  data_nascimento?: string | null;
  convenio?: string | null;
  total_atendimentos: number;
  ticket_medio: number;
  ultima_consulta?: string | null;
  status_reativacao: StatusReativacao;
}

export interface AtendimentoPedido {
  id: string;
  tenant_id: string;
  cliente?: ClientePaciente;
  cliente_id: string;
  cliente_nome?: string;
  cliente_whatsapp?: string;
  data_agendamento: string;
  data_atendimento: string | null;
  data_entrega: string | null;
  status: StatusAtendimento;
  confirmado: boolean;
  compareceu: boolean | null;
  total: number;
  pago: boolean;
  lojista_aprovado: boolean;
  origem: 'whatsapp' | 'dashboard';
  itens: ItemAtendimento[];
}

// Keep Atendimento alias for backwards compatibility
export type Atendimento = AtendimentoPedido;

export interface Aprovacao {
  id: string;
  tipo: string;
  atendimento_id?: string;
  cliente_id?: string;
  detalhes?: string;
  status: string;
  criado_em: string;
  cliente_nome?: string;
  cliente_whatsapp?: string;
  atendimento_total?: number;
  atendimento_data?: string;
}

export interface ListaEsperaEntry {
  id: string;
  cliente_id: string;
  cliente_nome?: string;
  cliente_whatsapp?: string;
  servico_id?: string;
  servico_nome?: string;
  data_preferida?: string;
  status: string;
}

// Keep ListaEspera alias for compatibility
export type ListaEspera = ListaEsperaEntry;

export interface Configuracoes {
  id: string;
  tenant_nome?: string;
  tenant_tipo?: 'clinica' | 'loja';
  tenant_cor_primaria?: string;
  tenant_logo_url?: string;
  horario_funcionamento?: string;
  limite_pedido_grande: number;
  mensagem_boas_vindas?: string;
  mensagem_fora_horario?: string;
  mensagem_confirmacao?: string;
  mensagem_reativacao?: string;
  sistema_ativo: boolean;
  owner_whatsapp?: string;
  evolution_instance_name?: string;
}

export interface ROIStats {
  taxa_comparecimento: number;
  receita_total: number;
  receita_perdida: number;
  reativados_count: number;
  lista_espera_agendados: number;
  impacto_total: number;
  mensalidade: number;
  roi: number;
}

export interface DashboardData {
  atendimentos_hoje: number;
  confirmados: number;
  aprovacoes_pendentes: number;
  receita_dia: number;
  variacao_atendimentos: number;  // % vs ontem
  variacao_receita: number;       // % vs ontem
  atendimentos: AtendimentoPedido[];
  
  // Backwards compatibility properties (old model)
  atendimentos_total?: number;
  atendimentos_confirmados?: number;
  receita_total?: number;
  receita_paga?: number;
  receita_pendente?: number;
}

export interface CardMetricaProps {
  label: string;
  valor: number | string;
  variacao?: number;
  icone: React.ReactNode;
  loading?: boolean;
  formato?: 'numero' | 'moeda' | 'percentual';
}
