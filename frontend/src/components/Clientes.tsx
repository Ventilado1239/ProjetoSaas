import React, { useState } from 'react';
import { useStore } from '../store/useStore';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useDebounce } from '../hooks/useDebounce';
import type { Cliente } from '../types';
import api from '../services/api';
import toast from '../services/toast';
import { EmptyState } from './EmptyState';
import { selectTenant } from '../store/selectors';
import { 
  Search, 
  Plus, 
  Trash2, 
  MessageSquare, 
  Phone,
  ShieldAlert,
  X,
  UsersRound
} from 'lucide-react';

export const Clientes: React.FC = () => {
  const queryClient = useQueryClient();
  const tenant = useStore(selectTenant);

  const [searchInput, setSearchInput] = useState('');
  const debouncedSearch = useDebounce(searchInput, 300);
  const [reactivationFilter, setReactivationFilter] = useState('');
  
  // Create Modal
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newWhatsapp, setNewWhatsapp] = useState('');
  const [newBirthDate, setNewBirthDate] = useState('');
  const [newConvenio, setNewConvenio] = useState('');
  const [formError, setFormError] = useState('');

  // Delete Modal (LGPD)
  const [deleteClient, setDeleteClient] = useState<Cliente | null>(null);

  // React Query Fetch
  const { data: clientes = [], isLoading } = useQuery<Cliente[]>({
    queryKey: ['clientes', debouncedSearch, reactivationFilter],
    queryFn: () => {
      const params: Record<string, string> = {};
      if (debouncedSearch) params.search = debouncedSearch;
      if (reactivationFilter) params.status_reativacao = reactivationFilter;
      return api.get('/clientes', { params }).then(r => r.data);
    },
    staleTime: 20000,
  });

  // Create Client Mutation
  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.post('/clientes', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clientes'] });
      toast.success('Cliente cadastrado com sucesso!');
      
      // Clear form
      setNewName('');
      setNewWhatsapp('');
      setNewBirthDate('');
      setNewConvenio('');
      setFormError('');
      setCreateModalOpen(false);
    },
    onError: (err: unknown) => {
      const errMsg = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Erro ao cadastrar cliente.';
      setFormError(errMsg);
      toast.error(errMsg);
    }
  });

  // Delete Client Mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/clientes/${id}/lgpd`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clientes'] });
      toast.success('Dados do cliente excluídos de forma definitiva.');
      setDeleteClient(null);
    },
    onError: () => {
      toast.error('Erro ao excluir dados do cliente (LGPD).');
    }
  });

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName || !newWhatsapp) return;
    
    // Simple phone number sanitization (digits only)
    const cleanedPhone = newWhatsapp.replace(/\D/g, '');
    if (cleanedPhone.length < 10) {
      setFormError('Telefone inválido. Inclua o DDD.');
      return;
    }

    createMutation.mutate({
      nome: newName,
      whatsapp: cleanedPhone,
      data_nascimento: newBirthDate || undefined,
      convenio: newConvenio || undefined
    });
  };

  const handleDeleteLGPD = () => {
    if (!deleteClient) return;
    deleteMutation.mutate(deleteClient.id);
  };

  const getReactivationBadgeClass = (status: string) => {
    switch (status) {
      case 'ativo': return 'bg-emerald-50 text-emerald-600 border-emerald-200/50';
      case 'inativo_3m': return 'bg-blue-50 text-blue-600 border-blue-200/50';
      case 'inativo_6m': return 'bg-amber-50 text-amber-600 border-amber-200/50';
      case 'inativo_12m': return 'bg-rose-50 text-rose-600 border-rose-200/50';
      case 'reativado': return 'bg-emerald-50 text-emerald-600 border-emerald-200/60';
      default: return 'bg-slate-50 text-slate-600 border-slate-200/50';
    }
  };

  const getReactivationLabel = (status: string) => {
    switch (status) {
      case 'ativo': return 'Ativo';
      case 'inativo_3m': return 'Inativo (3 Meses)';
      case 'inativo_6m': return 'Inativo (6 Meses)';
      case 'inativo_12m': return 'Inativo (1 Ano)';
      case 'reativado': return 'Reativado pelo CRM';
      default: return status;
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return '-';
    try {
      const d = new Date(dateString);
      return d.toLocaleDateString('pt-BR');
    } catch {
      return dateString;
    }
  };
  const moneyFormatter = new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  });

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-text-primary">
            {tenant.tipo === 'clinica' ? 'Pacientes Cadastrados' : 'Clientes Cadastrados'}
          </h2>
          <p className="text-xs text-text-secondary">CRM e monitoramento de inatividade/reativação</p>
        </div>
        <button
          onClick={() => setCreateModalOpen(true)}
          className="touch-target self-start sm:self-auto bg-accent hover:bg-accent-hover text-white text-xs font-semibold px-4 py-2 rounded-medium flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
        >
          <Plus size={16} />
          Cadastrar Novo
        </button>
      </div>

      {/* Filtros */}
      <div className="bg-surface border border-border rounded-large p-4 shadow-xs grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* Busca com debounce */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" size={16} />
          <input
            type="text"
            placeholder="Buscar por nome ou WhatsApp..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="w-full pl-9 pr-4 h-10 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
          />
        </div>

        {/* CRM Status */}
        <select
          value={reactivationFilter}
          onChange={(e) => setReactivationFilter(e.target.value)}
          className="w-full px-4 h-10 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
        >
          <option value="">Todos os Status de Inatividade (CRM)</option>
          <option value="ativo">Ativo</option>
          <option value="inativo_3m">Inativos (3 meses)</option>
          <option value="inativo_6m">Inativos (6 meses)</option>
          <option value="inativo_12m">Inativos (12 meses)</option>
          <option value="reativado">Reativados pelo CRM</option>
        </select>
      </div>

      {/* Grid de Clientes */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <div className="h-44 shimmer rounded-large"></div>
          <div className="h-44 shimmer rounded-large"></div>
          <div className="h-44 shimmer rounded-large"></div>
        </div>
      ) : clientes.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {clientes.map((c) => (
            <div key={c.id} className="bg-surface border border-border rounded-large p-5 shadow-xs flex flex-col justify-between hover:border-accent/40 transition-colors card">
              <div>
                <div className="flex items-start justify-between mb-3 gap-2">
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold text-text-primary truncate">
                      {c.nome}
                    </h3>
                    <a
                      href={`https://wa.me/${c.whatsapp}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-text-secondary hover:text-accent flex items-center gap-1 mt-0.5"
                    >
                      <Phone size={10} className="text-slate-400" />
                      {c.whatsapp}
                    </a>
                  </div>
                  <span className={`px-2 py-0.5 text-[9px] border rounded-full font-bold shrink-0 ${getReactivationBadgeClass(c.status_reativacao)}`}>
                    {getReactivationLabel(c.status_reativacao)}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 border-t border-border pt-3 mt-3 text-xs text-text-secondary">
                  <div>
                    <span className="block text-[9px] uppercase font-bold text-text-secondary">Total Compras</span>
                    <strong className="text-text-primary">{c.total_atendimentos}</strong>
                  </div>
                  <div>
                    <span className="block text-[9px] uppercase font-bold text-text-secondary">Ticket Médio</span>
                    <strong className="text-text-primary">{moneyFormatter.format(Number(c.ticket_medio || 0))}</strong>
                  </div>
                  <div className="col-span-2 border-t border-border/50 pt-2 mt-2">
                    <span className="block text-[9px] uppercase font-bold text-text-secondary">Última Visita</span>
                    <strong className="text-text-primary">{c.ultima_consulta ? formatDate(c.ultima_consulta) : 'Nunca'}</strong>
                  </div>
                </div>
              </div>

              {/* Botões de Ação */}
              <div className="flex justify-between items-center mt-4 border-t border-border/50 pt-3 gap-2">
                <a
                  href={`https://wa.me/${c.whatsapp}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="touch-target px-3 bg-accent-light text-accent text-xs font-semibold rounded-medium flex items-center gap-1 hover:bg-accent/10 transition-colors"
                >
                  <MessageSquare size={14} />
                  Falar no WhatsApp
                </a>
                
                {/* Delete Button compliant with GDPR / LGPD */}
                <button
                  onClick={() => setDeleteClient(c)}
                  title="Apagar dados (Exclusão LGPD)"
                  className="p-2 border border-rose-100 text-rose-600 hover:text-rose-700 hover:bg-rose-50 hover:border-rose-200 rounded-medium transition-all cursor-pointer"
                >
                  <Trash2 size={16} />
                </button>
              </div>

            </div>
          ))}
        </div>
      ) : (
        <div className="bg-surface border border-border rounded-large shadow-xs">
          <EmptyState
            icon={UsersRound}
            title="Nenhum cliente cadastrado."
            description={searchInput ? `Nenhum cliente encontrado para "${searchInput}".` : 'Cadastre seu primeiro cliente para iniciar o monitoramento.'}
          />
        </div>
      )}

      {/* Modal Cadastrar Cliente */}
      {createModalOpen && (
        <div className="fixed inset-0 bg-text-primary/20 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-surface w-full max-w-md rounded-large border border-border p-6 shadow-large relative">
            
            <div className="flex justify-between items-center mb-4 border-b border-border pb-3">
              <h3 className="text-sm font-semibold text-text-primary">Cadastrar Novo Cliente</h3>
              <button onClick={() => setCreateModalOpen(false)} aria-label="Fechar cadastro" className="p-1 rounded-full hover:bg-slate-50 text-text-secondary cursor-pointer">
                <X size={16} />
              </button>
            </div>
            
            {formError && (
              <div className="mb-4 p-3 bg-rose-50 border border-rose-100 text-rose-600 text-xs rounded-medium">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="space-y-4">
              <div>
                <label htmlFor="cliente-nome" className="block text-xs font-bold text-text-secondary uppercase mb-1">Nome Completo</label>
                <input
                  id="cliente-nome"
                  type="text"
                  required
                  placeholder="Nome do cliente"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="w-full h-10 px-3 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
                />
              </div>

              <div>
                <label htmlFor="cliente-whatsapp" className="block text-xs font-bold text-text-secondary uppercase mb-1">WhatsApp (DDD + Número)</label>
                <input
                  id="cliente-whatsapp"
                  type="text"
                  required
                  placeholder="Ex: 11999999999"
                  value={newWhatsapp}
                  onChange={(e) => setNewWhatsapp(e.target.value)}
                  className="w-full h-10 px-3 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="cliente-nascimento" className="block text-xs font-bold text-text-secondary uppercase mb-1">Data Nascimento</label>
                  <input
                    id="cliente-nascimento"
                    type="date"
                    value={newBirthDate}
                    onChange={(e) => setNewBirthDate(e.target.value)}
                    className="w-full h-10 px-3 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
                  />
                </div>
                <div>
                  <label htmlFor="cliente-convenio" className="block text-xs font-bold text-text-secondary uppercase mb-1">Convênio / Detalhe</label>
                  <input
                    id="cliente-convenio"
                    type="text"
                    placeholder="Particular, Bradesco..."
                    value={newConvenio}
                    onChange={(e) => setNewConvenio(e.target.value)}
                    className="w-full h-10 px-3 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
                  />
                </div>
              </div>

              <div className="flex gap-2 justify-end pt-4 border-t border-border/50">
                <button
                  type="button"
                  onClick={() => setCreateModalOpen(false)}
                  className="touch-target px-4 bg-background border border-border text-text-primary text-xs font-semibold rounded-medium cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="touch-target px-4 bg-accent hover:bg-accent-hover text-white text-xs font-semibold rounded-medium shadow-sm cursor-pointer disabled:opacity-50"
                >
                  {createMutation.isPending ? 'Salvando...' : 'Salvar Cadastro'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Deletar LGPD */}
      {deleteClient && (
        <div className="fixed inset-0 bg-text-primary/20 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-surface w-full max-w-md rounded-large border border-border p-6 shadow-large text-center">
            <div className="w-12 h-12 rounded-full bg-rose-50 border border-rose-100 text-rose-600 flex items-center justify-center mx-auto mb-4">
              <ShieldAlert size={24} />
            </div>
            
            <h3 className="text-sm font-semibold text-text-primary mb-2">Exclusão Irreversível de Dados (LGPD)</h3>
            
            <p className="text-xs text-text-secondary mb-6 leading-relaxed">
              Você está prestes a apagar de forma definitiva todos os registros relacionados ao cliente 
              <strong> {deleteClient.nome}</strong>. Esta ação está em conformidade com o direito ao esquecimento da LGPD.
              <br />
              <strong className="text-rose-600 font-semibold">Esta ação não pode ser desfeita.</strong>
            </p>

            <div className="flex gap-2 justify-center">
              <button
                disabled={deleteMutation.isPending}
                onClick={() => setDeleteClient(null)}
                className="touch-target px-4 bg-background border border-border text-text-primary text-xs font-semibold rounded-medium cursor-pointer"
              >
                Cancelar
              </button>
              <button
                disabled={deleteMutation.isPending}
                onClick={handleDeleteLGPD}
                className="touch-target px-4 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-medium shadow-sm cursor-pointer disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Excluindo...' : 'Confirmar Exclusão'}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
