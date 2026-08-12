import React from 'react';
import { useStore } from '../store/useStore';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import toast from '../services/toast';
import { EmptyState } from './EmptyState';
import type { DashboardData } from '../types';
import { 
  selectSetActiveTab, 
  selectTenant
} from '../store/selectors';
import { 
  CalendarDays, 
  CheckCircle2, 
  AlertTriangle, 
  DollarSign, 
  User,
  Clock,
  ArrowRight,
  CalendarX
} from 'lucide-react';

export const Dashboard: React.FC = () => {
  const queryClient = useQueryClient();
  const setActiveTab = useStore(selectSetActiveTab);
  const tenant = useStore(selectTenant);

  // React Query Fetch with 30s auto-refresh
  const { data: dashboard, isLoading } = useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: () => api.get('/dashboard/hoje').then((r) => r.data),
    refetchInterval: 30000,
    staleTime: 20000,
    retry: 2,
  });

  // Action status patch mutation
  const patchStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => 
      api.patch(`/atendimentos/${id}/status`, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['atendimentos'] });
      toast.success('Status do atendimento atualizado!');
    },
    onError: () => {
      toast.error('Erro ao atualizar status. Tente novamente.');
    }
  });

  const formatTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Sao_Paulo' });
    } catch {
      return '';
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'aguardando': return 'bg-blue-50 text-blue-600 border-blue-200/50';
      case 'confirmado': return 'bg-emerald-50 text-emerald-600 border-emerald-200/50';
      case 'em_producao': return 'bg-amber-50 text-amber-600 border-amber-200/50';
      case 'pronto': return 'bg-indigo-50 text-indigo-600 border-indigo-200/50';
      case 'realizado':
      case 'entregue': return 'bg-emerald-50 text-emerald-600 border-emerald-200/60';
      case 'falta':
      case 'cancelado': return 'bg-rose-50 text-rose-600 border-rose-200/50';
      default: return 'bg-slate-50 text-slate-600 border-slate-200/50';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'aguardando': return 'Aguardando';
      case 'confirmado': return 'Confirmado';
      case 'em_producao': return tenant.tipo === 'clinica' ? 'Em atendimento' : 'Em Produção';
      case 'pronto': return tenant.tipo === 'clinica' ? 'Pronto para atendimento' : 'Pronto';
      case 'realizado': return 'Realizado';
      case 'entregue': return 'Entregue';
      case 'falta': return 'Falta';
      case 'cancelado': return 'Cancelado';
      case 'abandonado': return 'Abandonado';
      default: return status;
    }
  };

  // Variance formatting helper
  const renderVariance = (val?: number) => {
    if (val === undefined) return null;
    const isPositive = val >= 0;
    return (
      <span className={`text-[10px] font-bold ${isPositive ? 'text-success' : 'text-danger'}`}>
        {isPositive ? `+${val.toFixed(1)}%` : `${val.toFixed(1)}%`} em relação a ontem
      </span>
    );
  };

  const apptsTotal = dashboard?.atendimentos_hoje ?? dashboard?.atendimentos_total ?? 0;
  const apptsConfirmados = dashboard?.confirmados ?? dashboard?.atendimentos_confirmados ?? 0;
  const pendingApprovals = dashboard?.aprovacoes_pendentes ?? 0;
  const revenueDia = dashboard?.receita_dia ?? dashboard?.receita_total ?? 0;
  const varAtendimentos = dashboard?.variacao_atendimentos ?? 0;
  const varReceita = dashboard?.variacao_receita ?? 0;
  const moneyFormatter = new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  });

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-text-primary">Visão Geral</h2>
          <p className="text-xs text-text-secondary">Acompanhamento operacional em tempo real</p>
        </div>
        {isLoading && (
          <div className="flex items-center gap-2 text-xs text-text-secondary animate-pulse">
            <div className="w-2 h-2 rounded-full bg-accent animate-ping"></div>
            <span>Atualizando...</span>
          </div>
        )}
      </div>

      {/* Alerta de Aprovações Pendentes */}
      {pendingApprovals > 0 && (
        <div className="p-4 bg-amber-50/80 border border-amber-200/60 backdrop-blur-md rounded-large flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm animate-fade-in">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-amber-500/10 flex items-center justify-center text-amber-600 shrink-0">
              <AlertTriangle size={20} className="badge-urgent" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-amber-800">
                Aprovações Pendentes
              </h3>
              <p className="text-xs text-amber-700/80">
                {tenant.tipo === 'clinica'
                  ? `Há ${pendingApprovals} solicitação(ões) aguardando liberação administrativa.`
                  : `Há ${pendingApprovals} pedido(s) aguardando liberação do administrador.`}
              </p>
            </div>
          </div>
          <button 
            onClick={() => setActiveTab('aprovacoes')}
            className="touch-target bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold px-4 py-2 rounded-medium flex items-center gap-1.5 self-start sm:self-auto shadow-sm hover:shadow transition-all duration-200 cursor-pointer"
          >
            Analisar Solicitações
            <ArrowRight size={14} />
          </button>
        </div>
      )}

      {/* Cards de Métricas */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Atendimentos hoje */}
        <div 
          className="border border-border rounded-large p-5 shadow-xs hover:border-accent/20 transition-all duration-300 group card"
          style={{ background: 'linear-gradient(135deg, hsl(var(--app-color-surface)) 0%, hsl(var(--app-color-accent-light)) 100%)' }}
        >
          <div className="flex items-center justify-between text-text-secondary mb-3">
            <span className="text-[10px] font-bold uppercase tracking-wider">
              {tenant.tipo === 'clinica' ? 'Consultas' : 'Pedidos'}
            </span>
            <div className="p-2 bg-slate-100 rounded-medium text-slate-500 group-hover:bg-accent/10 group-hover:text-accent transition-colors duration-300">
              <CalendarDays size={16} />
            </div>
          </div>
          {isLoading ? (
            <div className="h-8 w-20 shimmer rounded-medium my-1"></div>
          ) : (
            <p className="text-[32px] font-bold tracking-tight text-text-primary leading-none mb-1" style={{ letterSpacing: '-0.02em' }}>
              {apptsTotal}
            </p>
          )}
          <div className="text-[12px] text-text-secondary">
            {renderVariance(varAtendimentos)}
          </div>
        </div>

        {/* Confirmados */}
        <div 
          className="border border-border rounded-large p-5 shadow-xs hover:border-emerald-500/20 transition-all duration-300 group card"
          style={{ background: 'linear-gradient(135deg, hsl(var(--app-color-surface)) 0%, hsl(var(--app-color-accent-light)) 100%)' }}
        >
          <div className="flex items-center justify-between text-text-secondary mb-3">
            <span className="text-[10px] font-bold uppercase tracking-wider">Confirmados</span>
            <div className="p-2 bg-emerald-50 rounded-medium text-emerald-500 group-hover:bg-emerald-100 transition-colors duration-300">
              <CheckCircle2 size={16} />
            </div>
          </div>
          {isLoading ? (
            <div className="h-8 w-20 shimmer rounded-medium my-1"></div>
          ) : (
            <p className="text-[32px] font-bold tracking-tight text-text-primary leading-none mb-1" style={{ letterSpacing: '-0.02em' }}>
              {apptsConfirmados}
            </p>
          )}
          <span className="text-[12px] text-text-secondary">
            {tenant.tipo === 'clinica' ? 'Presença confirmada' : 'Presença ou produção confirmada'}
          </span>
        </div>

        {/* Pendências */}
        <div 
          className="border border-border rounded-large p-5 shadow-xs hover:border-amber-500/20 transition-all duration-300 group card"
          style={{ background: 'linear-gradient(135deg, hsl(var(--app-color-surface)) 0%, hsl(var(--app-color-accent-light)) 100%)' }}
        >
          <div className="flex items-center justify-between text-text-secondary mb-3">
            <span className="text-[10px] font-bold uppercase tracking-wider">Pendentes</span>
            <div className="p-2 bg-amber-50 rounded-medium text-amber-500 group-hover:bg-amber-100 transition-colors duration-300">
              <AlertTriangle size={16} />
            </div>
          </div>
          {isLoading ? (
            <div className="h-8 w-20 shimmer rounded-medium my-1"></div>
          ) : (
            <p className="text-[32px] font-bold tracking-tight text-text-primary leading-none mb-1" style={{ letterSpacing: '-0.02em' }}>
              {pendingApprovals}
            </p>
          )}
          <span className="text-[12px] text-text-secondary">Aguardando decisão manual</span>
        </div>

        {/* Receita do Dia */}
        <div 
          className="border border-border rounded-large p-5 shadow-xs hover:border-accent/20 transition-all duration-300 group card"
          style={{ background: 'linear-gradient(135deg, hsl(var(--app-color-surface)) 0%, hsl(var(--app-color-accent-light)) 100%)' }}
        >
          <div className="flex items-center justify-between text-text-secondary mb-3">
            <span className="text-[10px] font-bold uppercase tracking-wider">Receita</span>
            <div className="p-2 bg-blue-50 rounded-medium text-accent group-hover:bg-accent/10 transition-colors duration-300">
              <DollarSign size={16} />
            </div>
          </div>
          {isLoading ? (
            <div className="h-8 w-32 shimmer rounded-medium my-1"></div>
          ) : (
            <p className="text-[32px] font-bold tracking-tight text-text-primary leading-none mb-1" style={{ letterSpacing: '-0.02em' }}>
              {moneyFormatter.format(revenueDia)}
            </p>
          )}
          <div className="text-[12px] text-text-secondary leading-none">
            {renderVariance(varReceita)}
          </div>
        </div>
      </div>

      {/* Lista de Atendimentos */}
      <div className="bg-surface border border-border rounded-large shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-border bg-gradient-to-r from-surface to-background/10">
          <h3 className="text-sm font-semibold text-text-primary">Agenda do Dia</h3>
        </div>
        
        {isLoading ? (
          <div className="p-6 space-y-4">
            <div className="h-12 w-full shimmer rounded-medium"></div>
            <div className="h-12 w-full shimmer rounded-medium"></div>
            <div className="h-12 w-full shimmer rounded-medium"></div>
          </div>
        ) : dashboard?.atendimentos && dashboard.atendimentos.length > 0 ? (
          <div className="divide-y divide-border">
            {dashboard.atendimentos.map((appt) => (
              <div key={appt.id} className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-bg/40 transition-colors duration-150">
                
                {/* Informações principais */}
                <div className="flex items-start gap-3 min-w-0">
                  <div className="w-10 h-10 rounded-full bg-slate-100 border border-slate-200/60 flex items-center justify-center text-text-secondary shrink-0">
                    <User size={18} />
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-sm font-semibold text-text-primary truncate">
                      {appt.cliente_nome}
                    </h4>
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1">
                      <span className="text-xs text-text-secondary flex items-center gap-1">
                        <Clock size={12} className="text-slate-400" />
                        {formatTime(appt.data_agendamento)}
                      </span>
                      <span className="text-xs text-text-secondary">•</span>
                      <span className="text-xs text-text-secondary truncate max-w-[120px] sm:max-w-xs">
                        {appt.itens && appt.itens.length > 0
                          ? appt.itens.map(i => `${i.quantidade}x ${tenant.tipo === 'clinica' ? 'Procedimento' : 'Item'}`).join(', ')
                          : tenant.tipo === 'clinica' ? 'Serviço/Consulta' : 'Item/Pedido'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Status e Ações */}
                <div className="flex items-center justify-between sm:justify-end gap-3 border-t border-border/50 pt-3 sm:border-t-0 sm:pt-0">
                  <span className={`px-2 py-0.5 text-[11px] font-semibold border rounded-full ${getStatusBadgeClass(appt.status)}`}>
                    {getStatusLabel(appt.status)}
                  </span>
                  
                  {/* Ações rápidas baseadas no status */}
                  <div className="flex items-center gap-2">
                    {appt.status === 'aguardando' && (
                      <button
                        onClick={() => patchStatusMutation.mutate({ id: appt.id, status: 'confirmado' })}
                        className="touch-target px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-medium transition-all shadow-xs cursor-pointer"
                      >
                        Confirmar
                      </button>
                    )}
                    
                    {appt.status === 'confirmado' && tenant.tipo === 'loja' && (
                      <button
                        onClick={() => patchStatusMutation.mutate({ id: appt.id, status: 'em_producao' })}
                        className="touch-target px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-xs font-semibold rounded-medium transition-all shadow-xs cursor-pointer"
                      >
                        Produzir
                      </button>
                    )}

                    {appt.status === 'em_producao' && (
                      <button
                        onClick={() => patchStatusMutation.mutate({ id: appt.id, status: 'pronto' })}
                        className="touch-target px-3 py-1.5 bg-accent hover:bg-accent-hover text-white text-xs font-semibold rounded-medium transition-all shadow-xs cursor-pointer"
                      >
                        Pronto
                      </button>
                    )}

                    {appt.status === 'pronto' && (
                      <button
                        onClick={() => patchStatusMutation.mutate({ id: appt.id, status: tenant.tipo === 'clinica' ? 'realizado' : 'entregue' })}
                        className="touch-target px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-medium transition-all shadow-xs cursor-pointer"
                      >
                        Finalizar
                      </button>
                    )}

                    {/* Quick status change buttons */}
                    {['aguardando', 'confirmado'].includes(appt.status) && (
                      <button
                        onClick={() => patchStatusMutation.mutate({ id: appt.id, status: 'falta' })}
                        className="touch-target px-3 py-1.5 border border-border text-rose-600 hover:bg-rose-50 hover:border-rose-300 text-xs font-medium rounded-medium transition-all cursor-pointer"
                      >
                        Falta
                      </button>
                    )}
                  </div>
                </div>

              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={CalendarX}
            title="Nenhum atendimento hoje."
            description="A agenda está livre para novos encaixes e acompanhamentos."
            className="bg-slate-50/20"
          />
        )}
      </div>

    </div>
  );
};
