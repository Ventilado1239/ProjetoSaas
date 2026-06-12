import { create } from 'zustand';
import api from '../services/api';
import { getTenantConfig, applyTenantTheme } from '../config/tenant';
import type { TenantConfig } from '../config/tenant';
import type {
  TabType,
  User,
  Servico,
  Atendimento,
  Cliente,
  Aprovacao,
  ListaEspera,
  Configuracoes,
  ROIStats,
  DashboardData
} from '../types';

type ApiError = { response?: { data?: { detail?: string } } };

export interface AppState {
  user: User | null;
  isAuthenticated: boolean;
  activeTab: TabType;
  tenant: TenantConfig;
  dashboard: DashboardData | null;
  aprovacoes: Aprovacao[];
  atendimentos: Atendimento[];
  clientes: Cliente[];
  servicos: Servico[];
  listaEspera: ListaEspera[];
  configuracoes: Configuracoes | null;
  roiStats: ROIStats | null;

  loading: {
    dashboard: boolean;
    clientes: boolean;
    atendimentos: boolean;
    aprovacoes: boolean;
    servicos: boolean;
    submit: boolean;
  };
  
  error: {
    dashboard: string | null;
    clientes: string | null;
    atendimentos: string | null;
    global: string | null;
  };

  setUser: (user: User | null) => void;
  setActiveTab: (tab: TabType) => void;
  setError: (msg: string | null) => void;
  
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<boolean>;
  
  fetchDashboard: () => Promise<void>;
  fetchDashboardHoje: () => Promise<void>;
  fetchROI: () => Promise<void>;
  fetchAprovacoes: () => Promise<void>;
  processarAprovacao: (id: string, aprovado: boolean) => Promise<void>;
  aprovarPedido: (id: string) => Promise<void>;
  recusarPedido: (id: string) => Promise<void>;
  
  fetchAtendimentos: (dataInicio?: string, dataFim?: string, status?: string, clienteId?: string) => Promise<void>;
  createAtendimento: (apptData: Record<string, unknown>) => Promise<void>;
  patchAtendimentoStatus: (id: string, update: { status?: string; pago?: boolean; compareceu?: boolean }) => Promise<void>;
  updateAtendimentoStatus: (id: string, status: string) => Promise<void>;
  
  fetchClientes: (search?: string, statusReativacao?: string) => Promise<void>;
  createCliente: (clienteData: Record<string, unknown>) => Promise<void>;
  deleteClienteLGPD: (id: string) => Promise<void>;
  
  fetchServicos: () => Promise<void>;
  createServico: (servicoData: Record<string, unknown>) => Promise<void>;
  updateServico: (id: string, servicoData: Record<string, unknown>) => Promise<void>;
  
  fetchListaEspera: () => Promise<void>;
  addListaEspera: (data: Record<string, unknown>) => Promise<void>;
  oferecerListaEspera: (id: string) => Promise<void>;
  deleteListaEspera: (id: string) => Promise<void>;
  
  fetchConfiguracoes: () => Promise<void>;
  updateConfiguracoes: (config: Record<string, unknown>) => Promise<void>;
  setTenantActive: (active: boolean) => Promise<void>;
}

export const useStore = create<AppState>((set, get) => {
  // Apply initial theme based on tenant type
  const initialTenant = getTenantConfig();
  applyTenantTheme(initialTenant.tipo);

  // Auth failure listener to clear auth state
  if (typeof window !== 'undefined' && !(window as unknown as Record<string, boolean>).__authFailedListenerAdded) {
    (window as unknown as Record<string, boolean>).__authFailedListenerAdded = true;
    window.addEventListener('auth-failed', () => {
      set({ user: null, isAuthenticated: false });
    });
  }

  return {
    user: JSON.parse(localStorage.getItem('saas_user') || 'null'),
    isAuthenticated: localStorage.getItem('saas_auth') === 'true',
    activeTab: 'dashboard',
    tenant: initialTenant,
    dashboard: null,
    aprovacoes: [],
    atendimentos: [],
    clientes: [],
    servicos: [],
    listaEspera: [],
    configuracoes: null,
    roiStats: null,

    loading: {
      dashboard: false,
      clientes: false,
      atendimentos: false,
      aprovacoes: false,
      servicos: false,
      submit: false
    },

    error: {
      dashboard: null,
      clientes: null,
      atendimentos: null,
      global: null
    },

    setUser: (user) => {
      if (user) {
        localStorage.setItem('saas_user', JSON.stringify(user));
        localStorage.setItem('saas_auth', 'true');
        set({ user, isAuthenticated: true });
      } else {
        localStorage.removeItem('saas_user');
        localStorage.removeItem('saas_auth');
        set({ user: null, isAuthenticated: false });
      }
    },
    
    setActiveTab: (activeTab) => set((state) => ({ activeTab, error: { ...state.error, global: null } })),
    setError: (msg) => set((state) => ({ error: { ...state.error, global: msg } })),

    login: async (email, password) => {
      set((state) => ({ 
        loading: { ...state.loading, submit: true }, 
        error: { ...state.error, global: null } 
      }));
      try {
        const res = await api.post('/auth/login', { email, password });
        const user = res.data.user;
        
        get().setUser(user);
        
        try {
          await get().fetchConfiguracoes();
        } catch {
          // Ignore if configurations fetch fails initially
        }

        set((state) => ({ loading: { ...state.loading, submit: false } }));
        return true;
      } catch (err: unknown) {
        set((state) => ({ 
          loading: { ...state.loading, submit: false }, 
          error: { 
            ...state.error, 
            global: (err as ApiError).response?.data?.detail || 'Erro ao realizar login. Verifique suas credenciais.' 
          } 
        }));
        return false;
      }
    },

    logout: async () => {
      set((state) => ({ loading: { ...state.loading, submit: true } }));
      try {
        await api.post('/auth/logout');
      } catch {
        // Ignore errors on logout
      } finally {
        get().setUser(null);
        set(() => ({ 
          loading: {
            dashboard: false,
            clientes: false,
            atendimentos: false,
            aprovacoes: false,
            servicos: false,
            submit: false
          }, 
          dashboard: null,
          aprovacoes: [],
          atendimentos: [],
          clientes: [],
          servicos: [],
          listaEspera: [],
          configuracoes: null,
          roiStats: null,
          activeTab: 'dashboard'
        }));
      }
    },

    checkAuth: async () => {
      if (!get().isAuthenticated) return false;
      try {
        await get().fetchConfiguracoes();
        return true;
      } catch {
        get().setUser(null);
        return false;
      }
    },

    fetchDashboard: async () => {
      set((state) => ({ 
        loading: { ...state.loading, dashboard: true },
        error: { ...state.error, dashboard: null }
      }));
      try {
        const res = await api.get('/dashboard/hoje');
        // Structure formatting for backwards compatibility
        const resData = res.data;
        if (resData) {
          resData.atendimentos_total = resData.atendimentos_hoje;
          resData.atendimentos_confirmados = resData.confirmados;
          resData.receita_total = resData.receita_dia;
          resData.receita_paga = resData.receita_paga || 0;
          resData.receita_pendente = resData.receita_pendente || 0;
        }
        set((state) => ({ 
          dashboard: resData, 
          loading: { ...state.loading, dashboard: false } 
        }));
      } catch (err: unknown) {
        set((state) => ({ 
          loading: { ...state.loading, dashboard: false }, 
          error: { 
            ...state.error, 
            dashboard: (err as ApiError).response?.data?.detail || 'Erro ao carregar resumo do dia.' 
          } 
        }));
      }
    },

    fetchDashboardHoje: async () => {
      await get().fetchDashboard();
    },

    fetchROI: async () => {
      set((state) => ({ 
        loading: { ...state.loading, dashboard: true }, 
        error: { ...state.error, global: null } 
      }));
      try {
        const res = await api.get('/dashboard/roi');
        set((state) => ({ roiStats: res.data, loading: { ...state.loading, dashboard: false } }));
      } catch (err: unknown) {
        set((state) => ({ 
          loading: { ...state.loading, dashboard: false }, 
          error: { 
            ...state.error, 
            global: (err as ApiError).response?.data?.detail || 'Erro ao carregar ROI.' 
          } 
        }));
      }
    },

    fetchAprovacoes: async () => {
      set((state) => ({ 
        loading: { ...state.loading, aprovacoes: true }, 
        error: { ...state.error, global: null } 
      }));
      try {
        const res = await api.get('/atendimentos/aprovacoes');
        set((state) => ({ aprovacoes: res.data, loading: { ...state.loading, aprovacoes: false } }));
      } catch (err: unknown) {
        set((state) => ({ 
          loading: { ...state.loading, aprovacoes: false }, 
          error: { 
            ...state.error, 
            global: (err as ApiError).response?.data?.detail || 'Erro ao carregar aprovações.' 
          } 
        }));
      }
    },

    processarAprovacao: async (id, aprovado) => {
      set((state) => ({ 
        loading: { ...state.loading, submit: true }, 
        error: { ...state.error, global: null } 
      }));
      try {
        await api.post(`/atendimentos/aprovacoes/${id}/processar`, { aprovado });
        set((state) => ({ loading: { ...state.loading, submit: false } }));
        await get().fetchAprovacoes();
        await get().fetchDashboard();
      } catch (err: unknown) {
        set((state) => ({ 
          loading: { ...state.loading, submit: false }, 
          error: { 
            ...state.error, 
            global: (err as ApiError).response?.data?.detail || 'Erro ao processar aprovação.' 
          } 
        }));
      }
    },

    aprovarPedido: async (id) => {
      await get().processarAprovacao(id, true);
    },

    recusarPedido: async (id) => {
      await get().processarAprovacao(id, false);
    },

    fetchAtendimentos: async (dataInicio, dataFim, status, clienteId) => {
      set((state) => ({ 
        loading: { ...state.loading, atendimentos: true }, 
        error: { ...state.error, atendimentos: null } 
      }));
      try {
        const params: Record<string, string> = {};
        if (dataInicio) params.data_inicio = dataInicio;
        if (dataFim) params.data_fim = dataFim;
        if (status) params.status = status;
        if (clienteId) params.cliente_id = clienteId;
        
        const res = await api.get('/atendimentos', { params });
        set((state) => ({ atendimentos: res.data, loading: { ...state.loading, atendimentos: false } }));
      } catch (err: unknown) {
        set((state) => ({ 
          loading: { ...state.loading, atendimentos: false }, 
          error: { 
            ...state.error, 
            atendimentos: (err as ApiError).response?.data?.detail || 'Erro ao carregar atendimentos.' 
          } 
        }));
      }
    },

    createAtendimento: async (apptData) => {
      set((state) => ({ 
        loading: { ...state.loading, submit: true }, 
        error: { ...state.error, atendimentos: null } 
      }));
      try {
        await api.post('/atendimentos', apptData);
        set((state) => ({ loading: { ...state.loading, submit: false } }));
        await get().fetchDashboard();
      } catch (err: unknown) {
        set((state) => ({ 
          loading: { ...state.loading, submit: false }, 
          error: { 
            ...state.error, 
            atendimentos: (err as ApiError).response?.data?.detail || 'Erro ao agendar atendimento.' 
          } 
        }));
        throw err;
      }
    },

    patchAtendimentoStatus: async (id, update) => {
      set((state) => ({ 
        loading: { ...state.loading, submit: true }, 
        error: { ...state.error, atendimentos: null } 
      }));
      try {
        await api.patch(`/atendimentos/${id}/status`, update);
        set((state) => ({ loading: { ...state.loading, submit: false } }));
        await get().fetchDashboard();
        const act = get().activeTab;
        if (act === 'agenda') {
          await get().fetchAtendimentos();
        }
      } catch (err: unknown) {
        set((state) => ({ 
          loading: { ...state.loading, submit: false }, 
          error: { 
            ...state.error, 
            atendimentos: (err as ApiError).response?.data?.detail || 'Erro ao atualizar status.' 
          } 
        }));
      }
    },

    updateAtendimentoStatus: async (id, status) => {
      await get().patchAtendimentoStatus(id, { status });
    },

    fetchClientes: async (search, statusReativacao) => {
      set((state) => ({ 
        loading: { ...state.loading, clientes: true }, 
        error: { ...state.error, clientes: null } 
      }));
      try {
        const params: Record<string, string> = {};
        if (search) params.search = search;
        if (statusReativacao) params.status_reativacao = statusReativacao;
        
        const res = await api.get('/clientes', { params });
        set((state) => ({ clientes: res.data, loading: { ...state.loading, clientes: false } }));
      } catch (err: unknown) {
        set((state) => ({ 
          loading: { ...state.loading, clientes: false }, 
          error: { 
            ...state.error, 
            clientes: (err as ApiError).response?.data?.detail || 'Erro ao carregar clientes.' 
          } 
        }));
      }
    },

    createCliente: async (clienteData) => {
      set((state) => ({ 
        loading: { ...state.loading, submit: true }, 
        error: { ...state.error, clientes: null } 
      }));
      try {
        await api.post('/clientes', clienteData);
        set((state) => ({ loading: { ...state.loading, submit: false } }));
        await get().fetchClientes();
      } catch (err: unknown) {
        set((state) => ({ 
          loading: { ...state.loading, submit: false }, 
          error: { 
            ...state.error, 
            clientes: (err as ApiError).response?.data?.detail || 'Erro ao cadastrar cliente.' 
          } 
        }));
        throw err;
      }
    },

    deleteClienteLGPD: async (id) => {
      set((state) => ({ 
        loading: { ...state.loading, submit: true }, 
        error: { ...state.error, clientes: null } 
      }));
      try {
        await api.delete(`/clientes/${id}/lgpd`);
        set((state) => ({ loading: { ...state.loading, submit: false } }));
        await get().fetchClientes();
      } catch (err: unknown) {
        set((state) => ({ 
          loading: { ...state.loading, submit: false }, 
          error: { 
            ...state.error, 
            clientes: (err as ApiError).response?.data?.detail || 'Erro ao excluir dados do cliente (LGPD).' 
          } 
        }));
      }
    },

    fetchServicos: async () => {
      set((state) => ({ 
        loading: { ...state.loading, servicos: true }, 
        error: { ...state.error, global: null } 
      }));
      try {
        const res = await api.get('/servicos');
        set((state) => ({ servicos: res.data, loading: { ...state.loading, servicos: false } }));
      } catch (err: unknown) {
        set((state) => ({ 
          loading: { ...state.loading, servicos: false }, 
          error: { 
            ...state.error, 
            global: (err as ApiError).response?.data?.detail || 'Erro ao carregar serviços.' 
          } 
        }));
      }
    },

    createServico: async (servicoData) => {
      set((state) => ({ 
        loading: { ...state.loading, submit: true }, 
        error: { ...state.error, global: null } 
      }));
      try {
        await api.post('/servicos', servicoData);
        set((state) => ({ loading: { ...state.loading, submit: false } }));
        await get().fetchServicos();
      } catch (err: unknown) {
        set((state) => ({ 
          loading: { ...state.loading, submit: false }, 
          error: { 
            ...state.error, 
            global: (err as ApiError).response?.data?.detail || 'Erro ao cadastrar serviço.' 
          } 
        }));
        throw err;
      }
    },

    updateServico: async (id, servicoData) => {
      set((state) => ({ 
        loading: { ...state.loading, submit: true }, 
        error: { ...state.error, global: null } 
      }));
      try {
        await api.put(`/servicos/${id}`, servicoData);
        set((state) => ({ loading: { ...state.loading, submit: false } }));
        await get().fetchServicos();
      } catch (err: unknown) {
        set((state) => ({ 
          loading: { ...state.loading, submit: false }, 
          error: { 
            ...state.error, 
            global: (err as ApiError).response?.data?.detail || 'Erro ao atualizar serviço.' 
          } 
        }));
        throw err;
      }
    },

    fetchListaEspera: async () => {
      set((state) => ({ 
        loading: { ...state.loading, servicos: true }, 
        error: { ...state.error, global: null } 
      }));
      try {
        const res = await api.get('/lista-espera');
        set((state) => ({ listaEspera: res.data, loading: { ...state.loading, servicos: false } }));
      } catch (err: unknown) {
        set((state) => ({ 
          loading: { ...state.loading, servicos: false }, 
          error: { 
            ...state.error, 
            global: (err as ApiError).response?.data?.detail || 'Erro ao carregar lista de espera.' 
          } 
        }));
      }
    },

    addListaEspera: async (data) => {
      set((state) => ({ 
        loading: { ...state.loading, submit: true }, 
        error: { ...state.error, global: null } 
      }));
      try {
        await api.post('/lista-espera', data);
        set((state) => ({ loading: { ...state.loading, submit: false } }));
        await get().fetchListaEspera();
      } catch (err: unknown) {
        set((state) => ({ 
          loading: { ...state.loading, submit: false }, 
          error: { 
            ...state.error, 
            global: (err as ApiError).response?.data?.detail || 'Erro ao cadastrar na lista de espera.' 
          } 
        }));
        throw err;
      }
    },

    oferecerListaEspera: async (id) => {
      set((state) => ({ 
        loading: { ...state.loading, submit: true }, 
        error: { ...state.error, global: null } 
      }));
      try {
        await api.post(`/lista-espera/${id}/oferecer`);
        set((state) => ({ loading: { ...state.loading, submit: false } }));
        await get().fetchListaEspera();
      } catch (err: unknown) {
        set((state) => ({ 
          loading: { ...state.loading, submit: false }, 
          error: { 
            ...state.error, 
            global: (err as ApiError).response?.data?.detail || 'Erro ao enviar oferta de horário.' 
          } 
        }));
      }
    },

    deleteListaEspera: async (id) => {
      set((state) => ({ 
        loading: { ...state.loading, submit: true }, 
        error: { ...state.error, global: null } 
      }));
      try {
        await api.delete(`/lista-espera/${id}`);
        set((state) => ({ loading: { ...state.loading, submit: false } }));
        await get().fetchListaEspera();
      } catch (err: unknown) {
        set((state) => ({ 
          loading: { ...state.loading, submit: false }, 
          error: { 
            ...state.error, 
            global: (err as ApiError).response?.data?.detail || 'Erro ao excluir da lista de espera.' 
          } 
        }));
      }
    },

    fetchConfiguracoes: async () => {
      set((state) => ({ 
        loading: { ...state.loading, servicos: true }, 
        error: { ...state.error, global: null } 
      }));
      try {
        const res = await api.get('/configuracoes');
        set((state) => ({ 
          configuracoes: res.data, 
          tenant: { ...state.tenant, sistemaAtivo: res.data.sistema_ativo },
          loading: { ...state.loading, servicos: false } 
        }));
      } catch (err: unknown) {
        set((state) => ({ 
          loading: { ...state.loading, servicos: false }, 
          error: { 
            ...state.error, 
            global: (err as ApiError).response?.data?.detail || 'Erro ao carregar configurações.' 
          } 
        }));
      }
    },

    updateConfiguracoes: async (config) => {
      set((state) => ({ 
        loading: { ...state.loading, submit: true }, 
        error: { ...state.error, global: null } 
      }));
      try {
        const res = await api.put('/configuracoes', config);
        set((state) => ({ 
          configuracoes: res.data, 
          tenant: { ...state.tenant, sistemaAtivo: res.data.sistema_ativo },
          loading: { ...state.loading, submit: false } 
        }));
      } catch (err: unknown) {
        set((state) => ({ 
          loading: { ...state.loading, submit: false }, 
          error: { 
            ...state.error, 
            global: (err as ApiError).response?.data?.detail || 'Erro ao atualizar configurações.' 
          } 
        }));
      }
    },

    setTenantActive: async (active) => {
      set((state) => ({ 
        loading: { ...state.loading, submit: true }, 
        error: { ...state.error, global: null } 
      }));
      try {
        const res = await api.put('/configuracoes', { sistema_ativo: active });
        set((state) => ({
          tenant: { ...state.tenant, sistemaAtivo: active },
          configuracoes: res.data,
          loading: { ...state.loading, submit: false }
        }));
      } catch (err: unknown) {
        set((state) => ({ 
          loading: { ...state.loading, submit: false }, 
          error: { 
            ...state.error, 
            global: (err as ApiError).response?.data?.detail || 'Erro ao alterar estado de funcionamento do sistema.' 
          } 
        }));
        throw err;
      }
    }
  };
});
