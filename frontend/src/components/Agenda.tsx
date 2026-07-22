import React, { useState } from 'react';
import { useStore } from '../store/useStore';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Atendimento } from '../types';
import api from '../services/api';
import toast from '../services/toast';
import { EmptyState } from './EmptyState';
import { selectTenant } from '../store/selectors';
import { 
  Calendar, 
  Search, 
  Clock, 
  User, 
  ExternalLink, 
  ChevronRight,
  X,
  SearchX
} from 'lucide-react';

interface ClientProfile {
  id: string;
  nome: string;
  whatsapp: string;
  convenio?: string;
  total_atendimentos?: number;
  ticket_medio?: number;
}

export const Agenda: React.FC = () => {
  const queryClient = useQueryClient();
  const tenant = useStore(selectTenant);

  const [dateFilter, setDateFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [searchFilter, setSearchFilter] = useState('');
  
  // Modal State
  const [selectedClientId, setSelectedClientId] = useState<string | null>(null);
  const [clientData, setClientData] = useState<ClientProfile | null>(null);
  const [clientHistory, setClientHistory] = useState<Atendimento[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Parse date ranges
  let startStr = '';
  let endStr = '';
  if (dateFilter) {
    const d = new Date(dateFilter);
    startStr = new Date(d.getFullYear(), d.getMonth(), d.getDate(), 0, 0, 0).toISOString();
    endStr = new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59).toISOString();
  }

  // React Query fetch for appointments list
  const { data: atendimentos = [], isLoading } = useQuery<Atendimento[]>({
    queryKey: ['atendimentos', startStr, endStr, statusFilter],
    queryFn: () => {
      const params: Record<string, string> = {};
      if (startStr) params.data_inicio = startStr;
      if (endStr) params.data_fim = endStr;
      if (statusFilter) params.status = statusFilter;
      return api.get('/atendimentos', { params }).then(r => r.data);
    },
    staleTime: 15000,
  });

  // Action status change mutation
  const patchStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => 
      api.patch(`/atendimentos/${id}/status`, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['atendimentos'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      toast.success('Status do atendimento alterado!');
      if (selectedClientId) {
        void fetchClientHistory(selectedClientId);
      }
    },
    onError: () => {
      toast.error('Erro ao atualizar status.');
    }
  });

  const fetchClientHistory = async (clientId: string) => {
    setHistoryLoading(true);
    try {
      const clientRes = await api.get(`/clientes/${clientId}`);
      const historyRes = await api.get('/atendimentos', { params: { cliente_id: clientId } });
      setClientData(clientRes.data);
      setClientHistory(historyRes.data);
    } catch (e) {
      console.error(e);
      toast.error('Erro ao obter histórico do cliente.');
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleOpenClientModal = (clientId: string, clientName: string, clientWhatsapp: string) => {
    setSelectedClientId(clientId);
    setClientData({ id: clientId, nome: clientName, whatsapp: clientWhatsapp });
    setClientHistory([]);
    void fetchClientHistory(clientId);
  };

  const handleCloseClientModal = () => {
    setSelectedClientId(null);
    setClientData(null);
    setClientHistory([]);
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'aguardando': return 'bg-blue-50 text-blue-600 border-blue-200/50';
      case 'confirmado': return 'bg-emerald-50 text-emerald-600 border-emerald-200/50';
      case 'em_producao': return 'bg-amber-50 text-amber-600 border-amber-200/50';
      case 'pronto': return 'bg-indigo-50 text-indigo-600 border-indigo-200/50';
      case 'realizado': return 'bg-emerald-100 text-emerald-800 border-emerald-200/80';
      case 'entregue': return 'bg-emerald-100 text-emerald-800 border-emerald-200/80';
      case 'falta': return 'bg-rose-50 text-rose-600 border-rose-200/50';
      case 'cancelado': return 'bg-rose-50 text-rose-600 border-rose-200/50';
      case 'abandonado': return 'bg-slate-100 text-slate-600 border-slate-200/50';
      default: return 'bg-slate-50 text-slate-600 border-slate-200/50';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'aguardando': return 'Aguardando';
      case 'confirmado': return 'Confirmado';
      case 'em_producao': return tenant.tipo === 'clinica' ? 'Em atendimento' : 'Em produção';
      case 'pronto': return tenant.tipo === 'clinica' ? 'Pronto para atendimento' : 'Pronto';
      case 'realizado': return 'Realizado';
      case 'entregue': return 'Entregue';
      case 'falta': return 'Falta';
      case 'cancelado': return 'Cancelado';
      case 'abandonado': return 'Abandonado';
      default: return status;
    }
  };

  const formatTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Sao_Paulo' });
    } catch {
      return '';
    }
  };

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString('pt-BR');
    } catch {
      return '';
    }
  };

  const filteredAtendimentos = atendimentos.filter(appt => {
    if (!searchFilter) return true;
    const nameMatch = appt.cliente_nome?.toLowerCase().includes(searchFilter.toLowerCase());
    const phoneMatch = appt.cliente_whatsapp?.includes(searchFilter);
    return nameMatch || phoneMatch;
  });

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-text-primary">
            {tenant.tipo === 'clinica' ? 'Agenda de Consultas' : 'Controle de Pedidos'}
          </h2>
          <p className="text-xs text-text-secondary">Visualização completa de fluxos e agendas</p>
        </div>
        {isLoading && (
          <div className="flex items-center gap-2 text-xs text-text-secondary animate-pulse">
            <div className="w-2 h-2 rounded-full bg-accent animate-ping"></div>
            <span>Carregando...</span>
          </div>
        )}
      </div>

      {/* Filtros */}
      <div className="bg-surface border border-border rounded-large p-4 shadow-xs grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Busca por cliente */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" size={16} />
          <input
            type="text"
            placeholder="Buscar por cliente..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="w-full pl-9 pr-4 h-10 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
          />
        </div>

        {/* Data */}
        <div className="relative">
          <input
            type="date"
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
            className="w-full px-4 h-10 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
          />
        </div>

        {/* Status */}
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="w-full px-4 h-10 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
        >
          <option value="">Todos os Status</option>
          <option value="aguardando">Aguardando</option>
          <option value="confirmado">Confirmado</option>
          {tenant.tipo === 'loja' && <option value="em_producao">Em Produção</option>}
          {tenant.tipo === 'loja' && <option value="pronto">Pronto</option>}
          <option value="realizado">{tenant.tipo === 'clinica' ? 'Realizado' : 'Realizado / Entregue'}</option>
          <option value="falta">Falta</option>
          <option value="cancelado">Cancelado</option>
          <option value="abandonado">Abandonado</option>
        </select>
      </div>

      {/* Lista de Atendimentos */}
      <div className="bg-surface border border-border rounded-large shadow-xs divide-y divide-border overflow-hidden">
        {isLoading ? (
          <div className="p-6 space-y-4">
            <div className="h-14 w-full shimmer rounded-medium"></div>
            <div className="h-14 w-full shimmer rounded-medium"></div>
            <div className="h-14 w-full shimmer rounded-medium"></div>
          </div>
        ) : filteredAtendimentos.length > 0 ? (
          filteredAtendimentos.map((appt) => (
            <div key={appt.id} className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-bg/40 transition-colors duration-150">
              
              {/* Informações principais */}
              <div 
                className="flex items-start gap-3 cursor-pointer group min-w-0"
                onClick={() => handleOpenClientModal(appt.cliente_id, appt.cliente_nome || '', appt.cliente_whatsapp || '')}
              >
                <div className="w-10 h-10 rounded-full bg-slate-100 border border-slate-200/60 flex items-center justify-center text-text-secondary shrink-0 group-hover:border-accent transition-colors">
                  <User size={18} className="group-hover:text-accent transition-colors" />
                </div>
                <div className="min-w-0">
                  <h4 className="text-sm font-semibold text-text-primary group-hover:text-accent transition-colors flex items-center gap-1.5 truncate">
                    {appt.cliente_nome}
                    <ChevronRight size={14} className="text-text-secondary opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                  </h4>
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1 text-xs text-text-secondary">
                    <span className="flex items-center gap-1">
                      <Calendar size={12} className="text-slate-400" />
                      {formatDate(appt.data_agendamento)}
                    </span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <Clock size={12} className="text-slate-400" />
                      {formatTime(appt.data_agendamento)}
                    </span>
                    <span>•</span>
                    <span className="font-semibold text-accent">
                      R$ {appt.total.toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Status / Ações */}
              <div className="flex items-center justify-between sm:justify-end gap-3 pt-3 border-t border-border/50 sm:border-t-0 sm:pt-0">
                <span className={`px-2.5 py-0.5 text-xs border rounded-full font-semibold ${getStatusBadgeClass(appt.status)}`}>
                  {getStatusLabel(appt.status)}
                </span>

                <div className="flex items-center gap-1.5">
                  {/* Status transitions */}
                  {appt.status === 'aguardando' && (
                    <button
                      onClick={() => patchStatusMutation.mutate({ id: appt.id, status: 'confirmado' })}
                      className="touch-target px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-medium cursor-pointer"
                    >
                      Confirmar
                    </button>
                  )}
                  {appt.status === 'confirmado' && tenant.tipo === 'loja' && (
                    <button
                      onClick={() => patchStatusMutation.mutate({ id: appt.id, status: 'em_producao' })}
                      className="touch-target px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-xs font-semibold rounded-medium cursor-pointer"
                    >
                      Produzir
                    </button>
                  )}
                  {appt.status === 'em_producao' && (
                    <button
                      onClick={() => patchStatusMutation.mutate({ id: appt.id, status: 'pronto' })}
                      className="touch-target px-3 py-1.5 bg-accent hover:bg-accent-hover text-white text-xs font-semibold rounded-medium cursor-pointer"
                    >
                      Pronto
                    </button>
                  )}
                  {appt.status === 'pronto' && (
                    <button
                      onClick={() => patchStatusMutation.mutate({ id: appt.id, status: tenant.tipo === 'clinica' ? 'realizado' : 'entregue' })}
                      className="touch-target px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-medium cursor-pointer"
                    >
                      Entregar
                    </button>
                  )}
                  
                  {/* Cancel/No-show */}
                  {!['realizado', 'entregue', 'cancelado', 'falta'].includes(appt.status) && (
                    <button
                      onClick={() => patchStatusMutation.mutate({ id: appt.id, status: 'cancelado' })}
                      className="touch-target px-3 py-1.5 border border-border text-rose-600 hover:bg-rose-50 hover:border-rose-300 text-xs font-semibold rounded-medium cursor-pointer"
                    >
                      Cancelar
                    </button>
                  )}
                </div>
              </div>

            </div>
          ))
        ) : (
          <EmptyState
            icon={SearchX}
            title="Nenhum agendamento encontrado."
            description="Tente ajustar a busca, a data ou o status selecionado."
          />
        )}
      </div>

      {/* Modal de Detalhes do Cliente/Paciente */}
      {selectedClientId && clientData && (
        <div className="fixed inset-0 bg-text-primary/20 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-surface w-full max-w-lg rounded-large border border-border shadow-md flex flex-col max-h-[85vh] overflow-hidden">
            
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-slate-50/50">
              <h3 className="text-sm font-semibold text-text-primary">Perfil do Cliente</h3>
              <button 
                onClick={handleCloseClientModal}
                className="p-1.5 rounded-full hover:bg-slate-100 text-text-secondary transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-6">
              
              {/* Client general info */}
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-full bg-accent/10 text-accent flex items-center justify-center text-lg font-bold shrink-0">
                  {clientData.nome ? clientData.nome.charAt(0) : 'U'}
                </div>
                <div className="space-y-1">
                  <h4 className="text-base font-semibold text-text-primary">{clientData.nome}</h4>
                  <a 
                    href={`https://wa.me/${clientData.whatsapp}`} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-xs text-accent hover:underline flex items-center gap-1"
                  >
                    {clientData.whatsapp}
                    <ExternalLink size={12} />
                  </a>
                  {clientData.convenio && (
                    <span className="inline-block px-2 py-0.5 text-[10px] bg-accent-light text-accent rounded-full font-medium mt-1">
                      Convênio: {clientData.convenio}
                    </span>
                  )}
                </div>
              </div>

              {/* Statistics */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-slate-50 border border-slate-100 rounded-medium">
                  <span className="block text-[9px] uppercase font-bold text-text-secondary">Total Visitas</span>
                  <strong className="text-lg text-text-primary">{clientData.total_atendimentos || 0}</strong>
                </div>
                <div className="p-3 bg-slate-50 border border-slate-100 rounded-medium">
                  <span className="block text-[9px] uppercase font-bold text-text-secondary">Ticket Médio</span>
                  <strong className="text-lg text-text-primary">R$ {(clientData.ticket_medio || 0).toFixed(2)}</strong>
                </div>
              </div>

              {/* Appointment History */}
              <div className="space-y-3">
                <h5 className="text-[10px] font-bold text-text-primary uppercase tracking-wider">Histórico de Atendimentos</h5>
                
                {historyLoading ? (
                  <div className="py-8 text-center text-xs text-text-secondary flex items-center justify-center gap-2">
                    <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin"></div>
                    <span>Buscando histórico...</span>
                  </div>
                ) : clientHistory.length > 0 ? (
                  <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
                    {clientHistory.map((hAppt) => (
                      <div key={hAppt.id} className="p-3 border border-border rounded-medium flex items-center justify-between text-xs bg-surface shadow-2xs hover:border-slate-300 transition-colors duration-150">
                        <div>
                          <strong className="text-text-primary">{formatDate(hAppt.data_agendamento)}</strong>
                          <span className="text-text-secondary block mt-0.5">Total: R$ {hAppt.total.toFixed(2)}</span>
                        </div>
                        <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${getStatusBadgeClass(hAppt.status)}`}>
                          {getStatusLabel(hAppt.status)}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="py-6 text-center text-xs text-text-secondary border border-dashed border-border rounded-medium">
                    Nenhum atendimento anterior encontrado.
                  </div>
                )}
              </div>

            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-border flex justify-end bg-slate-50/50">
              <button 
                onClick={handleCloseClientModal}
                className="touch-target px-4 bg-background border border-border text-text-primary text-xs font-semibold rounded-medium cursor-pointer hover:bg-slate-50 transition-colors"
              >
                Fechar
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
};
