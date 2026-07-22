import React, { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import toast from '../services/toast';
import { EmptyState } from './EmptyState';
import { useStore } from '../store/useStore';
import { selectTenant } from '../store/selectors';
import type { Aprovacao } from '../types';
import { Check, X, AlertOctagon, Clock, User, Phone, BadgeCheck } from 'lucide-react';

export const Aprovacoes: React.FC = () => {
  const queryClient = useQueryClient();
  const tenant = useStore(selectTenant);
  const isClinic = tenant.tipo === 'clinica';

  const [timeState, setTimeState] = useState(new Date());

  // React Query fetch for approvals list
  const { data: aprovacoes = [], isLoading } = useQuery<Aprovacao[]>({
    queryKey: ['aprovacoes'],
    queryFn: () => api.get('/atendimentos/aprovacoes').then(r => r.data),
    staleTime: 10000,
  });

  // Action mutation
  const approvalMutation = useMutation({
    mutationFn: ({ id, aprovado }: { id: string; aprovado: boolean }) => 
      api.post(`/atendimentos/aprovacoes/${id}/processar`, { aprovado }),
    onSuccess: (_, variables) => {
      queryClient.setQueryData<Aprovacao[]>(['aprovacoes'], (current = []) =>
        current.filter((aprovacao) => aprovacao.id !== variables.id)
      );
      queryClient.invalidateQueries({ queryKey: ['aprovacoes'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      toast.success(
        variables.aprovado
          ? isClinic ? 'Solicitação aprovada com sucesso!' : 'Pedido aprovado com sucesso!'
          : isClinic ? 'Solicitação recusada.' : 'Pedido recusado.'
      );
    },
    onError: () => {
      toast.error('Erro ao processar. Tente novamente.');
    }
  });

  const handleAction = (id: string, aprovado: boolean) => {
    approvalMutation.mutate({ id, aprovado });
  };

  useEffect(() => {
    // Live timer update every 30 seconds
    const interval = setInterval(() => {
      setTimeState(new Date());
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const calculateMinutesWaiting = (createdAtString: string) => {
    try {
      const created = new Date(createdAtString);
      const diffMs = timeState.getTime() - created.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      return diffMins > 0 ? diffMins : 0;
    } catch {
      return 0;
    }
  };

  const getDetailsObject = (detailsString?: string) => {
    if (!detailsString) return {};
    try {
      return JSON.parse(detailsString);
    } catch {
      return { raw: detailsString };
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-text-primary">Aprovações Operacionais</h2>
          <p className="text-xs text-text-secondary">
            {isClinic
              ? 'Solicitações que excedem limites automáticos ou precisam de liberação administrativa'
              : 'Pedidos que excedem limites automáticos ou necessitam de liberação do administrador'}
          </p>
        </div>
        {isLoading && (
          <div className="flex items-center gap-2 text-xs text-text-secondary animate-pulse">
            <div className="w-2.5 h-2.5 rounded-full bg-accent animate-ping"></div>
            <span>Buscando...</span>
          </div>
        )}
      </div>

      {/* Approvals list */}
      {aprovacoes.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {aprovacoes.map((aprv) => {
            const minutes = calculateMinutesWaiting(aprv.criado_em);
            const isUrgent = minutes >= 120; // 2 hours waiting time
            const details = getDetailsObject(aprv.detalhes);
            const total = aprv.atendimento_total || details.total || 0;
            const productName = details.produto_nome || (isClinic ? 'Procedimento/Consulta' : 'Produto/Serviço');
            const qty = details.quantidade || 1;
            const pendingLabel = isClinic ? 'Solicitação Pendente' : 'Pedido Grande Pendente';
            const itemLabel = isClinic ? 'Procedimento:' : 'Produto:';
            const quantityLabel = isClinic ? 'Sessões/itens:' : 'Quantidade:';
            const quantitySuffix = isClinic ? 'un.' : 'unidades';

            return (
              <div 
                key={aprv.id} 
                className="bg-surface border-y border-r border-warning/15 rounded-r-large p-6 shadow-xs flex flex-col justify-between border-l-[3.5px] border-l-warning"
                style={{ backgroundColor: 'hsla(var(--app-color-warning) / 0.04)' }}
              >
                <div>
                  {/* Card Header with warning type and timer */}
                  <div className="flex items-center justify-between mb-4 border-b border-border/50 pb-3 gap-2">
                    <span className="flex items-center gap-1.5 text-xs font-semibold text-warning">
                      <AlertOctagon size={16} />
                      {pendingLabel}
                    </span>
                    <div className="flex items-center gap-2">
                      {isUrgent && (
                        <span className="px-2 py-0.5 text-[9px] font-bold bg-danger text-white rounded-full badge-urgent uppercase">
                          URGENTE
                        </span>
                      )}
                      <span className="text-xs text-text-secondary flex items-center gap-1 font-mono">
                        <Clock size={14} className="text-text-secondary" />
                        Aguardando há {minutes} min
                      </span>
                    </div>
                  </div>

                  {/* Customer details */}
                  <div className="space-y-3 mb-6">
                    <div className="flex items-start gap-2.5">
                      <User size={16} className="text-text-secondary mt-0.5" />
                      <div>
                        <p className="text-sm font-semibold text-text-primary">
                          {aprv.cliente_nome || details.cliente_nome}
                        </p>
                        <p className="text-xs text-text-secondary flex items-center gap-1">
                          <Phone size={10} />
                          {aprv.cliente_whatsapp}
                        </p>
                      </div>
                    </div>

                    {/* Order details */}
                    <div className="p-3 bg-surface border border-border rounded-medium space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-text-secondary">{itemLabel}</span>
                        <strong className="text-text-primary">{productName}</strong>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-text-secondary">{quantityLabel}</span>
                        <strong className="text-text-primary">{qty} {quantitySuffix}</strong>
                      </div>
                      <div className="flex justify-between text-xs border-t border-border pt-1.5 mt-1.5">
                        <span className="text-text-secondary font-medium">Valor Estimado:</span>
                        <strong className="text-accent text-sm">R$ {total.toFixed(2)}</strong>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Approve / Reject actions with 52px min-height on mobile */}
                <div className="flex flex-col sm:grid sm:grid-cols-2 gap-3 mt-4">
                  <button
                    disabled={approvalMutation.isPending}
                    onClick={() => handleAction(aprv.id, false)}
                    className="h-[52px] sm:h-11 sm:min-h-0 flex items-center justify-center gap-1.5 border border-danger/20 hover:border-danger text-danger bg-rose-50 font-semibold rounded-medium transition-all cursor-pointer text-xs disabled:opacity-50"
                  >
                    {approvalMutation.isPending && approvalMutation.variables?.id === aprv.id && !approvalMutation.variables?.aprovado ? (
                      <div className="w-4 h-4 border-2 border-danger border-t-transparent rounded-full animate-spin"></div>
                    ) : (
                      <X size={18} />
                    )}
                    Recusar
                  </button>
                  <button
                    disabled={approvalMutation.isPending}
                    onClick={() => handleAction(aprv.id, true)}
                    className="h-[52px] sm:h-11 sm:min-h-0 flex items-center justify-center gap-1.5 bg-success hover:bg-success/90 text-white font-semibold rounded-medium transition-all shadow-sm cursor-pointer text-xs disabled:opacity-50"
                  >
                    {approvalMutation.isPending && approvalMutation.variables?.id === aprv.id && approvalMutation.variables?.aprovado ? (
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    ) : (
                      <Check size={18} />
                    )}
                    Aprovar
                  </button>
                </div>

              </div>
            );
          })}
        </div>
      ) : (
        <div className="bg-surface border border-border rounded-large shadow-xs max-w-lg mx-auto">
          <EmptyState
            icon={BadgeCheck}
            title="Tudo em dia!"
            description={isClinic
              ? 'Nenhuma solicitação pendente de aprovação neste momento.'
              : 'Nenhuma aprovação de pedido grande pendente neste momento.'}
          />
        </div>
      )}

    </div>
  );
};
