import React, { useState } from 'react';
import { useStore } from '../store/useStore';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Cliente, Servico, ListaEspera as ListaEsperaType } from '../types';
import api from '../services/api';
import toast from '../services/toast';
import { 
  selectAddListaEspera, 
  selectOferecerListaEspera, 
  selectDeleteListaEspera 
} from '../store/selectors';
import { Plus, Send, Trash2, User, Clock, X } from 'lucide-react';

export const ListaEspera: React.FC = () => {
  const queryClient = useQueryClient();
  const addListaEsperaStore = useStore(selectAddListaEspera);
  const oferecerListaEsperaStore = useStore(selectOferecerListaEspera);
  const deleteListaEsperaStore = useStore(selectDeleteListaEspera);

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedClientId, setSelectedClientId] = useState('');
  const [selectedServiceId, setSelectedServiceId] = useState('');
  const [preferredDate, setPreferredDate] = useState('');

  // React Query Fetch Waiting List
  const { data: listaEspera = [], isLoading } = useQuery<ListaEsperaType[]>({
    queryKey: ['listaEspera'],
    queryFn: () => api.get('/lista-espera').then(r => r.data),
    staleTime: 15000,
  });

  // React Query Fetch Clients (for dropdown)
  const { data: clientes = [] } = useQuery<Cliente[]>({
    queryKey: ['clientes', '', ''], // empty queries to get all
    queryFn: () => api.get('/clientes').then(r => r.data),
    staleTime: 60000,
  });

  // React Query Fetch Services (for dropdown)
  const { data: servicos = [] } = useQuery<Servico[]>({
    queryKey: ['servicos'],
    queryFn: () => api.get('/servicos').then(r => r.data),
    staleTime: 60000,
  });

  // Offerhorário Mutation
  const offerMutation = useMutation({
    mutationFn: (id: string) => api.post(`/lista-espera/${id}/oferecer`),
    onSuccess: async (_, id) => {
      // Sync legacy state
      try {
        await oferecerListaEsperaStore(id);
      } catch {
        // ignore
      }
      queryClient.invalidateQueries({ queryKey: ['listaEspera'] });
      toast.success('Disparo de vaga enviado via WhatsApp!');
    },
    onError: () => {
      toast.error('Erro ao enviar oferta de horário.');
    }
  });

  // Delete waiting list mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/lista-espera/${id}`),
    onSuccess: async (_, id) => {
      // Sync legacy state
      try {
        await deleteListaEsperaStore(id);
      } catch {
        // ignore
      }
      queryClient.invalidateQueries({ queryKey: ['listaEspera'] });
      toast.success('Registro removido com sucesso.');
    },
    onError: () => {
      toast.error('Erro ao excluir da lista de espera.');
    }
  });

  // Add waiting list entry mutation
  const addMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.post('/lista-espera', payload),
    onSuccess: async (_, variables) => {
      // Sync legacy state
      try {
        await addListaEsperaStore(variables);
      } catch {
        // ignore
      }
      queryClient.invalidateQueries({ queryKey: ['listaEspera'] });
      toast.success('Cliente adicionado à fila de espera!');
      
      // Clear forms
      setSelectedClientId('');
      setSelectedServiceId('');
      setPreferredDate('');
      setModalOpen(false);
    },
    onError: () => {
      toast.error('Erro ao cadastrar na lista de espera.');
    }
  });

  const handleOffer = (id: string) => {
    offerMutation.mutate(id);
  };

  const handleDelete = (id: string) => {
    deleteMutation.mutate(id);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClientId) return;

    addMutation.mutate({
      cliente_id: selectedClientId,
      servico_id: selectedServiceId || undefined,
      data_preferida: preferredDate ? new Date(preferredDate).toISOString() : undefined
    });
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Qualquer data';
    try {
      const d = new Date(dateString);
      return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return dateString;
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-text-primary">Fila de Lista de Espera</h2>
          <p className="text-xs text-text-secondary">Clientes aguardando vagas ou desistências de horários</p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="touch-target bg-accent hover:bg-accent-hover text-white text-xs font-semibold px-4 py-2 rounded-medium flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
        >
          <Plus size={16} />
          Adicionar à Fila
        </button>
      </div>

      {/* Lista */}
      <div className="bg-surface border border-border rounded-large shadow-xs divide-y divide-border">
        {isLoading ? (
          <div className="p-6 space-y-4">
            <div className="h-14 w-full shimmer rounded-medium"></div>
            <div className="h-14 w-full shimmer rounded-medium"></div>
          </div>
        ) : listaEspera.length > 0 ? (
          listaEspera.map((entry) => (
            <div key={entry.id} className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-bg/40 transition-colors">
              
              {/* Informações */}
              <div className="flex items-start gap-3 min-w-0">
                <div className="w-10 h-10 rounded-full bg-background border border-border flex items-center justify-center text-text-secondary shrink-0">
                  <User size={18} />
                </div>
                <div className="min-w-0">
                  <h4 className="text-sm font-semibold text-text-primary truncate">
                    {entry.cliente_nome}
                  </h4>
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1 text-xs text-text-secondary">
                    <span className="font-semibold text-accent truncate">
                      {entry.servico_nome || 'Qualquer Serviço'}
                    </span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <Clock size={12} />
                      Preferência: {formatDate(entry.data_preferida)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Ações */}
              <div className="flex items-center justify-between sm:justify-end gap-3 pt-3 border-t border-border/50 sm:border-t-0 sm:pt-0">
                <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full border ${
                  entry.status === 'notificado'
                    ? 'bg-blue-50 text-blue-600 border-blue-200/50'
                    : entry.status === 'agendado'
                    ? 'bg-emerald-50 text-emerald-600 border-emerald-200/50'
                    : entry.status === 'expirado'
                    ? 'bg-rose-50 text-rose-600 border-rose-200/50'
                    : 'bg-amber-50 text-amber-600 border-amber-200/50'
                }`}>
                  {entry.status === 'notificado'
                    ? 'Vaga Oferecida'
                    : entry.status === 'agendado'
                    ? 'Confirmado'
                    : entry.status === 'expirado'
                    ? 'Expirado'
                    : 'Aguardando Vaga'}
                </span>

                <div className="flex items-center gap-2">
                  <button
                    disabled={offerMutation.isPending || deleteMutation.isPending || entry.status === 'notificado' || entry.status === 'agendado'}
                    onClick={() => handleOffer(entry.id)}
                    title="Disparar oferta de horário via WhatsApp"
                    className="touch-target px-3 bg-success hover:bg-success/90 text-white text-xs font-semibold rounded-medium flex items-center gap-1.5 shadow-sm transition-all cursor-pointer disabled:opacity-50"
                  >
                    {offerMutation.isPending && offerMutation.variables === entry.id ? (
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    ) : (
                      <Send size={12} />
                    )}
                    Oferecer Vaga
                  </button>

                  <button
                    disabled={deleteMutation.isPending || offerMutation.isPending}
                    onClick={() => handleDelete(entry.id)}
                    title="Remover da lista de espera"
                    className="p-2 border border-border hover:border-danger text-text-secondary hover:text-danger rounded-medium transition-all cursor-pointer disabled:opacity-50"
                  >
                    {deleteMutation.isPending && deleteMutation.variables === entry.id ? (
                      <div className="w-3.5 h-3.5 border-2 border-danger border-t-transparent rounded-full animate-spin"></div>
                    ) : (
                      <Trash2 size={14} />
                    )}
                  </button>
                </div>
              </div>

            </div>
          ))
        ) : (
          <div className="p-12 text-center text-text-secondary text-sm flex flex-col items-center">
            <span className="text-3xl mb-2">📋</span>
            <p className="font-semibold text-text-primary mb-0.5">Fila de espera vazia.</p>
            <p className="text-xs text-text-secondary">Nenhum cliente na fila de espera para este serviço.</p>
          </div>
        )}
      </div>

      {/* Modal Adicionar à Lista */}
      {modalOpen && (
        <div className="fixed inset-0 bg-text-primary/20 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-surface w-full max-w-md rounded-large border border-border p-6 shadow-large relative">
            
            <div className="flex justify-between items-center mb-4 border-b border-border pb-3">
              <h3 className="text-sm font-semibold text-text-primary">Adicionar à Lista de Espera</h3>
              <button onClick={() => setModalOpen(false)} className="p-1 rounded-full hover:bg-slate-50 text-text-secondary cursor-pointer">
                <X size={16} />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-text-secondary uppercase mb-1">Selecionar Cliente</label>
                <select
                  required
                  value={selectedClientId}
                  onChange={(e) => setSelectedClientId(e.target.value)}
                  className="w-full h-10 px-3 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
                >
                  <option value="">Escolha um cliente...</option>
                  {clientes.map(c => (
                    <option key={c.id} value={c.id}>{c.nome} ({c.whatsapp})</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-text-secondary uppercase mb-1">Procedimento/Serviço (Opcional)</label>
                <select
                  value={selectedServiceId}
                  onChange={(e) => setSelectedServiceId(e.target.value)}
                  className="w-full h-10 px-3 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
                >
                  <option value="">Qualquer serviço/produto</option>
                  {servicos.map(s => (
                    <option key={s.id} value={s.id}>{s.nome}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-text-secondary uppercase mb-1">Data/Horário de Preferência (Opcional)</label>
                <input
                  type="datetime-local"
                  value={preferredDate}
                  onChange={(e) => setPreferredDate(e.target.value)}
                  className="w-full h-10 px-3 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
                />
              </div>

              <div className="flex gap-2 justify-end pt-4 border-t border-border/50">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="touch-target px-4 bg-background border border-border text-text-primary text-xs font-semibold rounded-medium cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={addMutation.isPending}
                  className="touch-target px-4 bg-accent hover:bg-accent-hover text-white text-xs font-semibold rounded-medium shadow-sm cursor-pointer disabled:opacity-50"
                >
                  {addMutation.isPending ? 'Adicionando...' : 'Adicionar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
