import React, { useState } from 'react';
import { useStore } from '../store/useStore';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Servico, Preco } from '../types';
import api from '../services/api';
import toast from '../services/toast';
import { EmptyState } from './EmptyState';
import { selectTenant } from '../store/selectors';
import { Plus, Trash2, Edit2, X, PackageOpen } from 'lucide-react';

interface PriceTier {
  qtd_min: number;
  qtd_max: number;
  preco_particular: number;
  preco_convenio?: number;
  convenio?: string;
}

export const Servicos: React.FC = () => {
  const queryClient = useQueryClient();
  const tenant = useStore(selectTenant);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  
  // Form fields
  const [name, setName] = useState('');
  const [category, setCategory] = useState('');
  const [duration, setDuration] = useState<number>(30);
  const [isActive, setIsActive] = useState(true);
  
  // Price Tiers
  const [priceTiers, setPriceTiers] = useState<PriceTier[]>([]);

  // React Query Fetch for services
  const { data: servicos = [], isLoading } = useQuery<Servico[]>({
    queryKey: ['servicos'],
    queryFn: () => api.get('/servicos').then(r => r.data),
    staleTime: 30000,
  });

  // Create/Update Service Mutation
  const serviceMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => {
      if (editingId) {
        return api.put(`/servicos/${editingId}`, payload);
      } else {
        return api.post('/servicos', payload);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['servicos'] });
      toast.success(editingId ? 'Serviço atualizado com sucesso!' : 'Serviço cadastrado com sucesso!');
      setModalOpen(false);
    },
    onError: () => {
      toast.error('Erro ao salvar informações do serviço/produto.');
    }
  });

  const handleOpenCreate = () => {
    setEditingId(null);
    setName('');
    setCategory('');
    setDuration(30);
    setIsActive(true);
    setPriceTiers([{ qtd_min: 1, qtd_max: 9999, preco_particular: 50.00 }]);
    setModalOpen(true);
  };

  const handleOpenEdit = (s: Servico) => {
    setEditingId(s.id);
    setName(s.nome);
    setCategory(s.categoria || '');
    setDuration(s.duracao_minutos || 30);
    setIsActive(s.ativo);
    
    if (s.precos && s.precos.length > 0) {
      setPriceTiers(s.precos.map((p: Preco) => ({
        qtd_min: p.qtd_min,
        qtd_max: p.qtd_max,
        preco_particular: p.preco_particular,
        preco_convenio: p.preco_convenio,
        convenio: p.convenio
      })));
    } else {
      setPriceTiers([{ qtd_min: 1, qtd_max: 9999, preco_particular: 50.00 }]);
    }
    
    setModalOpen(true);
  };

  const handleAddTier = () => {
    const lastTier = priceTiers[priceTiers.length - 1];
    const newMin = lastTier ? Number(lastTier.qtd_max) + 1 : 1;
    
    setPriceTiers([...priceTiers, { 
      qtd_min: newMin, 
      qtd_max: newMin + 9, 
      preco_particular: lastTier ? lastTier.preco_particular : 50.00 
    }]);
  };

  const handleRemoveTier = (index: number) => {
    if (priceTiers.length === 1) return;
    setPriceTiers(priceTiers.filter((_, i) => i !== index));
  };

  const handleTierChange = (index: number, field: string, val: string | number | boolean) => {
    const updated = [...priceTiers];
    ((updated[index] as unknown) as Record<string, string | number | boolean | undefined>)[field] = val;
    setPriceTiers(updated);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name) return;

    const payload = {
      nome: name,
      categoria: category || undefined,
      duracao_minutos: tenant.tipo === 'clinica' ? Number(duration) : undefined,
      ativo: isActive,
      precos: priceTiers.map(t => ({
        qtd_min: Number(t.qtd_min),
        qtd_max: Number(t.qtd_max),
        preco_particular: Number(t.preco_particular),
        preco_convenio: t.preco_convenio ? Number(t.preco_convenio) : undefined,
        convenio: t.convenio || undefined
      }))
    };

    serviceMutation.mutate(payload);
  };

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-text-primary">
            {tenant.tipo === 'clinica' ? 'Serviços & Procedimentos' : 'Produtos & Faixas de Preço'}
          </h2>
          <p className="text-xs text-text-secondary">
            {tenant.tipo === 'clinica' 
              ? 'Gerenciamento de agenda, procedimentos médicos e convênios' 
              : 'Configuração de descontos por volume e tabelas de preços'}
          </p>
        </div>
        <button
          onClick={handleOpenCreate}
          className="touch-target bg-accent hover:bg-accent-hover text-white text-xs font-semibold px-4 py-2 rounded-medium flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
        >
          <Plus size={16} />
          {tenant.tipo === 'clinica' ? 'Adicionar Serviço' : 'Adicionar Produto'}
        </button>
      </div>

      {/* Grid de Serviços */}
      <div className="bg-surface border border-border rounded-large shadow-xs overflow-x-auto">
        {isLoading ? (
          <div className="p-6 space-y-4">
            <div className="h-10 w-full shimmer rounded-medium"></div>
            <div className="h-10 w-full shimmer rounded-medium"></div>
            <div className="h-10 w-full shimmer rounded-medium"></div>
          </div>
        ) : servicos.length > 0 ? (
          <table className="w-full text-left border-collapse min-w-[600px]">
            <thead>
              <tr className="bg-bg text-[11px] uppercase font-bold text-text-secondary border-b border-border" style={{ letterSpacing: '0.05em' }}>
                <th className="px-6 py-4 font-semibold">Nome</th>
                <th className="px-6 py-4 font-semibold">Categoria</th>
                {tenant.tipo === 'clinica' && <th className="px-6 py-4 font-semibold">Duração</th>}
                <th className="px-6 py-4 font-semibold">Faixas de Preço</th>
                <th className="px-6 py-4 font-semibold text-center">Status</th>
                <th className="px-6 py-4 font-semibold text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border text-xs">
              {servicos.map((s) => (
                <tr key={s.id} className="hover:bg-bg/40 transition-colors">
                  <td className="px-6 py-4 font-semibold text-text-primary">{s.nome}</td>
                  <td className="px-6 py-4 text-text-secondary">{s.categoria || '-'}</td>
                  {tenant.tipo === 'clinica' && (
                    <td className="px-6 py-4 text-text-secondary">{s.duracao_minutos} min</td>
                  )}
                  <td className="px-6 py-4">
                    <div className="space-y-1">
                      {s.precos.map((p, idx) => (
                        <div key={idx} className="font-mono text-text-secondary flex items-center gap-2">
                          <span className="bg-slate-100 px-1.5 py-0.5 rounded-small text-[10px] text-text-primary font-bold">
                            {p.qtd_min === p.qtd_max ? `${p.qtd_min}` : `${p.qtd_min}-${p.qtd_max}`}
                          </span>
                          <span className="text-accent font-semibold">R$ {Number(p.preco_particular).toFixed(2)}</span>
                          {p.convenio && (
                            <span className="text-[10px] text-text-secondary bg-accent-light px-1.5 py-0.5 rounded-full font-medium">
                              ({p.convenio})
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-center">
                    <span className={`px-2.5 py-1 text-[11px] rounded-full font-semibold border ${
                      s.ativo 
                        ? 'bg-emerald-50 text-emerald-600 border-emerald-200/50' 
                        : 'bg-slate-50 text-slate-500 border-slate-200/50'
                    }`}>
                      {s.ativo ? 'Ativo' : 'Inativo'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => handleOpenEdit(s)}
                      className="p-1.5 hover:bg-slate-100 text-text-secondary hover:text-accent rounded-medium transition-all inline-flex cursor-pointer"
                    >
                      <Edit2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <EmptyState
            icon={PackageOpen}
            title="Nenhum registro encontrado."
            description="Adicione serviços ou produtos para criar sua grade de valores."
          />
        )}
      </div>

      {/* Modal CRUD */}
      {modalOpen && (
        <div className="fixed inset-0 bg-text-primary/20 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-surface w-full max-w-xl rounded-large border border-border shadow-lg flex flex-col max-h-[90vh]">
            
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-slate-50/50">
              <h3 className="text-sm font-semibold text-text-primary">
                {editingId ? 'Editar Cadastro' : 'Cadastrar Novo'}
              </h3>
              <button 
                onClick={() => setModalOpen(false)}
                className="p-1.5 rounded-full hover:bg-slate-100 text-text-secondary transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Body */}
            <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">
              
              {/* Basic info */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-xs font-bold text-text-secondary uppercase mb-1">
                    Nome do {tenant.tipo === 'clinica' ? 'Serviço' : 'Produto'}
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="Ex: Consulta Odontológica, Camiseta Personalizada..."
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full h-10 px-3 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-text-secondary uppercase mb-1">Categoria</label>
                  <input
                    type="text"
                    placeholder="Ex: Estética, Roupas, Tratamentos..."
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full h-10 px-3 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
                  />
                </div>

                {tenant.tipo === 'clinica' ? (
                  <div>
                    <label className="block text-xs font-bold text-text-secondary uppercase mb-1">Duração (minutos)</label>
                    <input
                      type="number"
                      required
                      min={5}
                      value={duration}
                      onChange={(e) => setDuration(Number(e.target.value))}
                      className="w-full h-10 px-3 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
                    />
                  </div>
                ) : (
                  <div className="flex items-center pt-6">
                    <label className="flex items-center gap-2 text-xs font-semibold text-text-primary cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={isActive}
                        onChange={(e) => setIsActive(e.target.checked)}
                        className="rounded border-border text-accent focus:ring-accent"
                      />
                      Produto Ativo no Catálogo
                    </label>
                  </div>
                )}
              </div>

              {/* Price Tiers */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider">Tabela de Faixas de Preço</h4>
                  <button
                    type="button"
                    onClick={handleAddTier}
                    className="text-[10px] font-bold text-accent hover:underline flex items-center gap-1 cursor-pointer"
                  >
                    + Adicionar Faixa
                  </button>
                </div>

                <div className="space-y-2">
                  {priceTiers.map((tier, idx) => (
                    <div key={idx} className="bg-slate-50 p-3 rounded-medium border border-border flex flex-wrap items-center gap-3">
                      
                      <div className="flex items-center gap-1 text-xs">
                        <span className="text-text-secondary font-bold">Qtd Mín:</span>
                        <input
                          type="number"
                          required
                          min={1}
                          value={tier.qtd_min}
                          onChange={(e) => handleTierChange(idx, 'qtd_min', e.target.value)}
                          className="w-16 h-8 px-2 border border-border rounded-medium bg-surface text-center font-mono focus:outline-none focus:border-accent"
                        />
                      </div>

                      <div className="flex items-center gap-1 text-xs">
                        <span className="text-text-secondary font-bold">Qtd Máx:</span>
                        <input
                          type="number"
                          required
                          min={1}
                          value={tier.qtd_max}
                          onChange={(e) => handleTierChange(idx, 'qtd_max', e.target.value)}
                          className="w-20 h-8 px-2 border border-border rounded-medium bg-surface text-center font-mono focus:outline-none focus:border-accent"
                        />
                      </div>

                      <div className="flex items-center gap-1 text-xs">
                        <span className="text-text-secondary font-bold">Preço Particular (R$):</span>
                        <input
                          type="number"
                          required
                          step="0.01"
                          min={0}
                          value={tier.preco_particular}
                          onChange={(e) => handleTierChange(idx, 'preco_particular', e.target.value)}
                          className="w-24 h-8 px-2 border border-border rounded-medium bg-surface text-right font-mono focus:outline-none focus:border-accent"
                        />
                      </div>

                      {tenant.tipo === 'clinica' && (
                        <>
                          <div className="flex items-center gap-1 text-xs">
                            <span className="text-text-secondary font-bold">Convênio (R$):</span>
                            <input
                              type="number"
                              step="0.01"
                              value={tier.preco_convenio || ''}
                              onChange={(e) => handleTierChange(idx, 'preco_convenio', e.target.value)}
                              className="w-20 h-8 px-2 border border-border rounded-medium bg-surface text-right font-mono focus:outline-none focus:border-accent"
                            />
                          </div>
                          <div className="flex items-center gap-1 text-xs">
                            <input
                              type="text"
                              placeholder="Nome convênio"
                              value={tier.convenio || ''}
                              onChange={(e) => handleTierChange(idx, 'convenio', e.target.value)}
                              className="w-28 h-8 px-2 border border-border rounded-medium bg-surface focus:outline-none focus:border-accent"
                            />
                          </div>
                        </>
                      )}

                      {priceTiers.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveTier(idx)}
                          className="p-1.5 hover:bg-slate-200 text-text-secondary hover:text-danger rounded-medium transition-all self-end ml-auto cursor-pointer"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2 justify-end pt-4 border-t border-border bg-slate-50/50 -mx-6 -mb-6 px-6 pb-6 rounded-b-large">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="touch-target px-4 bg-background border border-border text-text-primary text-xs font-semibold rounded-medium cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={serviceMutation.isPending}
                  className="touch-target px-4 bg-accent hover:bg-accent-hover text-white text-xs font-semibold rounded-medium shadow-sm cursor-pointer disabled:opacity-50"
                >
                  {serviceMutation.isPending ? 'Salvando...' : 'Salvar Modificações'}
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

    </div>
  );
};
