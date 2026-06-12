/* eslint-disable react-hooks/set-state-in-effect */
import React, { useEffect, useState } from 'react';
import { useStore } from '../store/useStore';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Configuracoes as ConfigType } from '../types';
import api from '../services/api';
import toast from '../services/toast';
import { 
  selectFetchConfiguracoes,
  selectUpdateConfiguracoes,
  selectSetTenantActive,
  selectUser, 
  selectTenant 
} from '../store/selectors';
import { 
  Clock, 
  MessageSquare, 
  AlertOctagon, 
  Users, 
  ShieldAlert,
  Save,
  Trash2,
  X
} from 'lucide-react';

export const Configuracoes: React.FC = () => {
  const queryClient = useQueryClient();
  const fetchConfiguracoesStore = useStore(selectFetchConfiguracoes);
  const updateConfiguracoesStore = useStore(selectUpdateConfiguracoes);
  const setTenantActiveStore = useStore(selectSetTenantActive);
  const user = useStore(selectUser);
  const tenant = useStore(selectTenant);

  const [welcomeMsg, setWelcomeMsg] = useState('');
  const [offlineMsg, setOfflineMsg] = useState('');
  const [confirmMsg, setConfirmMsg] = useState('');
  const [reactivateMsg, setReactivateMsg] = useState('');
  const [largeOrderLimit, setLargeOrderLimit] = useState(10);

  // Opening Hours State
  interface DaySchedule {
    open: string;
    close: string;
    active: boolean;
  }
  const [hours, setHours] = useState<Record<string, DaySchedule>>({
    seg_sex: { open: '08:00', close: '18:00', active: true },
    sab: { open: '08:00', close: '12:00', active: true },
    dom: { open: '08:00', close: '18:00', active: false }
  });

  // Users List State
  interface LocalUser {
    id: string;
    nome: string;
    email: string;
    perfil: string;
  }
  const [usersList, setUsersList] = useState<LocalUser[]>([]);
  const [userModalOpen, setUserModalOpen] = useState(false);
  const [newUserName, setNewUserName] = useState('');
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserPassword, setNewUserPassword] = useState('');
  const [newUserProfile, setNewUserProfile] = useState('recepcionista');
  
  // Kill Switch State
  const [confirmKillOpen, setConfirmKillOpen] = useState(false);
  const [systemActiveState, setSystemActiveState] = useState(tenant.sistemaAtivo);
  const [killSwitchConfirmText, setKillSwitchConfirmText] = useState('');

  // React Query Fetch Configuration
  const { data: config = null, isLoading } = useQuery<ConfigType>({
    queryKey: ['configuracoes'],
    queryFn: () => api.get('/configuracoes').then(r => r.data),
    staleTime: 60000,
  });

  // Sync settings when data arrives
  useEffect(() => {
    if (config) {
      setWelcomeMsg(config.mensagem_boas_vindas || '');
      setOfflineMsg(config.mensagem_fora_horario || '');
      setConfirmMsg(config.mensagem_confirmacao || '');
      setReactivateMsg(config.mensagem_reativacao || '');
      setLargeOrderLimit(config.limite_pedido_grande || 10);
      setSystemActiveState(config.sistema_ativo);
      
      if (config.horario_funcionamento) {
        try {
          setHours(JSON.parse(config.horario_funcionamento));
        } catch {
          // Keep defaults
        }
      }
    }
  }, [config]);

  // Load operators list
  const loadUsers = async () => {
    try {
      setUsersList([
        { id: '1', nome: 'Dono da Empresa', email: 'dono@empresa.com.br', perfil: 'dono' },
        { id: '2', nome: 'Maria Auxiliadora', email: 'maria@empresa.com.br', perfil: 'recepcionista' },
        { id: '3', nome: 'Dr. Lucas Silva', email: 'lucas@empresa.com.br', perfil: 'medico' }
      ]);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    void loadUsers();
    // Sync Zustand legacy (just to be safe)
    void fetchConfiguracoesStore();
  }, [fetchConfiguracoesStore]);

  // Update configuration mutation
  const updateSettingsMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.put('/configuracoes', payload),
    onSuccess: async (_, variables) => {
      try {
        await updateConfiguracoesStore(variables);
      } catch {
        // ignore
      }
      queryClient.invalidateQueries({ queryKey: ['configuracoes'] });
      toast.success('Configurações salvas com sucesso!');
    },
    onError: () => {
      toast.error('Erro ao salvar configurações.');
    }
  });

  const handleSave = () => {
    updateSettingsMutation.mutate({
      limite_pedido_grande: Number(largeOrderLimit),
      mensagem_boas_vindas: welcomeMsg,
      mensagem_fora_horario: offlineMsg,
      mensagem_confirmacao: confirmMsg,
      mensagem_reativacao: reactivateMsg,
      horario_funcionamento: JSON.stringify(hours)
    });
  };

  // Toggle active tenant status mutation
  const activeTenantMutation = useMutation({
    mutationFn: (active: boolean) => api.put('/configuracoes', { sistema_ativo: active }),
    onSuccess: async (_, active) => {
      try {
        await setTenantActiveStore(active);
      } catch {
        // ignore
      }
      queryClient.invalidateQueries({ queryKey: ['configuracoes'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      setSystemActiveState(active);
      setConfirmKillOpen(false);
      toast.success(
        active 
          ? 'Operações reativadas com sucesso! WhatsApp e Dashboard liberados.' 
          : 'Operações suspensas! Todas as integrações foram bloqueadas.'
      );
    },
    onError: (e: unknown) => {
      const errMsg = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Erro ao processar alteração.';
      toast.error(errMsg);
    }
  });

  const handleConfirmKillSwitch = () => {
    const safetyPhrase = systemActiveState ? 'SUSPENDER' : 'ATIVAR';
    if (killSwitchConfirmText !== safetyPhrase) return;

    activeTenantMutation.mutate(!systemActiveState);
  };

  const handleCreateUser = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUserName || !newUserEmail || !newUserPassword) return;

    const newUser = {
      id: Math.random().toString(),
      nome: newUserName,
      email: newUserEmail,
      perfil: newUserProfile
    };
    
    setUsersList([...usersList, newUser]);
    
    // Reset forms
    setNewUserName('');
    setNewUserEmail('');
    setNewUserPassword('');
    setUserModalOpen(false);
    toast.success('Usuário cadastrado com sucesso!');
  };

  const handleDeactivateUser = (id: string) => {
    setUsersList(usersList.filter(u => u.id !== id));
    toast.success('Usuário removido da lista local.');
  };

  const toggleKillSwitch = () => {
    setKillSwitchConfirmText('');
    setConfirmKillOpen(true);
  };

  const handleHoursChange = (dayKey: string, field: string, value: string | boolean) => {
    setHours({
      ...hours,
      [dayKey]: {
        ...hours[dayKey],
        [field]: value
      }
    });
  };

  return (
    <div className="space-y-6 relative">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-text-primary">Configurações Gerais</h2>
          <p className="text-xs text-text-secondary">Ajuste de fluxos, mensagens padrão e administração</p>
        </div>
        
        <button
          onClick={handleSave}
          disabled={updateSettingsMutation.isPending || isLoading}
          className="touch-target bg-accent hover:bg-accent-hover text-white text-xs font-semibold px-4 py-2 rounded-medium flex items-center gap-1.5 shadow-sm transition-all cursor-pointer disabled:opacity-50"
        >
          <Save size={16} />
          {updateSettingsMutation.isPending ? 'Salvando...' : 'Salvar Configurações'}
        </button>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Coluna 1 & 2: Opções de Fluxo e Mensagens */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Horário de Funcionamento */}
          <div className="bg-surface border border-border rounded-large p-5 shadow-xs">
            <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider mb-4 flex items-center gap-2">
              <Clock size={16} className="text-text-secondary" />
              Horário de Atendimento
            </h3>

            {isLoading ? (
              <div className="space-y-2">
                <div className="h-10 w-full shimmer rounded-medium"></div>
                <div className="h-10 w-full shimmer rounded-medium"></div>
              </div>
            ) : (
              <div className="space-y-3">
                {Object.keys(hours).map((dayKey) => {
                  const day = hours[dayKey];
                  const label = dayKey === 'seg_sex' ? 'Segunda a Sexta' : dayKey === 'sab' ? 'Sábado' : 'Domingo';

                  return (
                    <div key={dayKey} className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 bg-background rounded-medium border border-border">
                      <label className="flex items-center gap-2 text-xs font-semibold text-text-primary cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={day.active}
                          onChange={(e) => handleHoursChange(dayKey, 'active', e.target.checked)}
                          className="rounded border-border text-accent focus:ring-accent"
                        />
                        {label}
                      </label>

                      {day.active && (
                        <div className="flex items-center gap-2 text-xs font-mono">
                          <input
                            type="text"
                            value={day.open}
                            onChange={(e) => handleHoursChange(dayKey, 'open', e.target.value)}
                            placeholder="08:00"
                            className="w-16 h-8 px-2 border border-border rounded-medium bg-surface text-center focus:outline-none focus:border-accent"
                          />
                          <span className="text-text-secondary">às</span>
                          <input
                            type="text"
                            value={day.close}
                            onChange={(e) => handleHoursChange(dayKey, 'close', e.target.value)}
                            placeholder="18:00"
                            className="w-16 h-8 px-2 border border-border rounded-medium bg-surface text-center focus:outline-none focus:border-accent"
                          />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Mensagens Padrão */}
          <div className="bg-surface border border-border rounded-large p-5 shadow-xs space-y-4">
            <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider mb-2 flex items-center gap-2">
              <MessageSquare size={16} className="text-text-secondary" />
              Mensagens Automatizadas (WhatsApp)
            </h3>

            {isLoading ? (
              <div className="space-y-4">
                <div className="h-20 w-full shimmer rounded-medium"></div>
                <div className="h-20 w-full shimmer rounded-medium"></div>
              </div>
            ) : (
              <>
                <div>
                  <label className="block text-xs font-bold text-text-secondary uppercase mb-1.5">Boas-vindas & Menu</label>
                  <textarea
                    value={welcomeMsg}
                    onChange={(e) => setWelcomeMsg(e.target.value)}
                    rows={3}
                    className="w-full p-3 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-text-secondary uppercase mb-1.5">Fora de Expediente</label>
                  <textarea
                    value={offlineMsg}
                    onChange={(e) => setOfflineMsg(e.target.value)}
                    rows={3}
                    className="w-full p-3 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-text-secondary uppercase mb-1.5">Confirmação de Agendamento</label>
                  <textarea
                    value={confirmMsg}
                    onChange={(e) => setConfirmMsg(e.target.value)}
                    rows={3}
                    className="w-full p-3 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-text-secondary uppercase mb-1.5">CRM Reativação (Inativos)</label>
                  <textarea
                    value={reactivateMsg}
                    onChange={(e) => setReactivateMsg(e.target.value)}
                    rows={3}
                    className="w-full p-3 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
                  />
                </div>
              </>
            )}
          </div>

        </div>

        {/* Coluna 3: Limites, Usuários e Autenticação */}
        <div className="space-y-6">
          
          {/* Limite de Pedido Grande */}
          <div className="bg-surface border border-border rounded-large p-5 shadow-xs">
            <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider mb-3 flex items-center gap-2">
              <AlertOctagon size={16} className="text-text-secondary" />
              Limites de Alerta
            </h3>

            <div>
              <label className="block text-xs font-bold text-text-secondary mb-1">
                {tenant.tipo === 'clinica' ? 'Procedimentos simultâneos' : 'Limite Pedido Grande (unidades)'}
              </label>
              <input
                type="number"
                value={largeOrderLimit}
                onChange={(e) => setLargeOrderLimit(Number(e.target.value))}
                className="w-full h-10 px-3 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15 font-mono"
              />
              <span className="text-[10px] text-text-secondary mt-1.5 block">
                Acima deste limite, o fluxo do WhatsApp pausará para validação manual do dono.
              </span>
            </div>
          </div>

          {/* Usuários e Perfis */}
          <div className="bg-surface border border-border rounded-large p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                <Users size={16} className="text-text-secondary" />
                Usuários & Perfis
              </h3>
              
              <button
                onClick={() => setUserModalOpen(true)}
                className="text-[10px] font-bold text-accent hover:underline flex items-center gap-0.5 cursor-pointer"
              >
                + Convidar
              </button>
            </div>

            <div className="space-y-2">
              {usersList.map((u) => (
                <div key={u.id} className="p-3 bg-background border border-border rounded-medium flex items-center justify-between text-xs">
                  <div>
                    <span className="font-semibold text-text-primary block">{u.nome}</span>
                    <span className="text-text-secondary text-[10px] block mt-0.5">{u.email}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 text-[9px] bg-accent-light text-accent rounded-full font-bold capitalize">
                      {u.perfil}
                    </span>
                    {u.perfil !== 'dono' && (
                      <button
                        onClick={() => handleDeactivateUser(u.id)}
                        className="p-1 text-text-secondary hover:text-rose-600 rounded-medium cursor-pointer"
                      >
                        <Trash2 size={12} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Kill Switch (Admin Only) */}
          {user?.perfil === 'dono' && (
            <div className="bg-surface border border-rose-200 rounded-large p-5 shadow-xs space-y-4">
              <h3 className="text-xs font-bold text-rose-600 uppercase tracking-wider flex items-center gap-2">
                <ShieldAlert size={16} />
                Kill Switch de Segurança
              </h3>

              <p className="text-[10px] text-text-secondary leading-relaxed">
                Esta ação suspende imediatamente todo o processamento de mensagens no WhatsApp do cliente e bloqueia o acesso à dashboard de todos os funcionários. Use apenas em caso de emergência ou cancelamento do serviço.
              </p>

              <button
                type="button"
                onClick={toggleKillSwitch}
                className={`w-full touch-target font-semibold rounded-medium text-xs transition-all shadow-sm cursor-pointer ${
                  systemActiveState 
                    ? 'bg-rose-600 text-white hover:bg-rose-700' 
                    : 'bg-emerald-600 text-white hover:bg-emerald-700'
                }`}
              >
                {systemActiveState ? 'Suspender Operações' : 'Reativar Operações'}
              </button>
            </div>
          )}

        </div>

      </div>

      {/* Modal Convidar Usuário */}
      {userModalOpen && (
        <div className="fixed inset-0 bg-text-primary/20 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-surface w-full max-w-md rounded-large border border-border p-6 shadow-lg relative">
            <div className="flex justify-between items-center mb-4 border-b border-border pb-3">
              <h3 className="text-sm font-semibold text-text-primary">Adicionar Novo Operador</h3>
              <button onClick={() => setUserModalOpen(false)} className="p-1 rounded-full hover:bg-slate-50 text-text-secondary cursor-pointer">
                <X size={16} />
              </button>
            </div>
            
            <form onSubmit={handleCreateUser} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-text-secondary uppercase mb-1">Nome Completo</label>
                <input
                  type="text"
                  required
                  placeholder="Nome do operador"
                  value={newUserName}
                  onChange={(e) => setNewUserName(e.target.value)}
                  className="w-full h-10 px-3 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-text-secondary uppercase mb-1">E-mail Corporativo</label>
                <input
                  type="email"
                  required
                  placeholder="operador@empresa.com.br"
                  value={newUserEmail}
                  onChange={(e) => setNewUserEmail(e.target.value)}
                  className="w-full h-10 px-3 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-text-secondary uppercase mb-1">Senha Provisória</label>
                <input
                  type="password"
                  required
                  placeholder="Mínimo 6 caracteres"
                  value={newUserPassword}
                  onChange={(e) => setNewUserPassword(e.target.value)}
                  className="w-full h-10 px-3 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-text-secondary uppercase mb-1">Perfil / Permissões</label>
                <select
                  value={newUserProfile}
                  onChange={(e) => setNewUserProfile(e.target.value)}
                  className="w-full h-10 px-3 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
                >
                  <option value="recepcionista">Recepcionista (Sem Financeiro)</option>
                  <option value="medico">Profissional de Saúde (Agenda/Consultas)</option>
                  <option value="funcionario">Funcionário (Operacional/Prontidão)</option>
                </select>
              </div>

              <div className="flex gap-2 justify-end pt-4 border-t border-border mt-6">
                <button
                  type="button"
                  onClick={() => setUserModalOpen(false)}
                  className="touch-target px-4 bg-background border border-border text-text-primary text-xs font-semibold rounded-medium cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="touch-target px-4 bg-accent hover:bg-accent-hover text-white text-xs font-semibold rounded-medium shadow-sm cursor-pointer"
                >
                  Criar Cadastro
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Confirmação Kill Switch */}
      {confirmKillOpen && (
        <div className="fixed inset-0 bg-text-primary/20 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-surface w-full max-w-md rounded-large border border-border p-6 shadow-lg text-center">
            <div className="w-12 h-12 rounded-full bg-rose-50 border border-rose-100 text-rose-600 flex items-center justify-center mx-auto mb-4 animate-pulse">
              <ShieldAlert size={24} />
            </div>
            
            <h3 className="text-sm font-semibold text-text-primary mb-2">Confirmar Ação de Emergência</h3>
            
            <p className="text-xs text-text-secondary mb-4 leading-relaxed">
              Você tem certeza que deseja <strong>{systemActiveState ? 'SUSPENDER' : 'REATIVAR'}</strong> todas as operações de atendimento do WhatsApp e do painel da empresa?
              <br />
              <strong className="text-rose-600 font-semibold">Isso impactará todos os atendimentos correntes dos clientes.</strong>
            </p>

            <div className="mb-6 text-left">
              <label className="block text-[10px] font-bold text-text-secondary uppercase mb-1.5 text-center">
                Digite <strong className="text-rose-600">{systemActiveState ? 'SUSPENDER' : 'ATIVAR'}</strong> para confirmar:
              </label>
              <input
                type="text"
                placeholder={systemActiveState ? 'SUSPENDER' : 'ATIVAR'}
                value={killSwitchConfirmText}
                onChange={(e) => setKillSwitchConfirmText(e.target.value)}
                className="w-full h-10 px-3 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-rose-600 font-mono tracking-wider text-center"
              />
            </div>

            <div className="flex gap-2 justify-center">
              <button
                disabled={activeTenantMutation.isPending}
                onClick={() => setConfirmKillOpen(false)}
                className="touch-target px-4 bg-background border border-border text-text-primary text-xs font-semibold rounded-medium cursor-pointer"
              >
                Voltar
              </button>
              <button
                disabled={killSwitchConfirmText !== (systemActiveState ? 'SUSPENDER' : 'ATIVAR') || activeTenantMutation.isPending}
                onClick={handleConfirmKillSwitch}
                className="touch-target px-4 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-medium shadow-sm cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5 justify-center"
              >
                {activeTenantMutation.isPending && (
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                )}
                Sim, Confirmar
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
