import React from 'react';
import { useStore } from '../store/useStore';
import { useQuery } from '@tanstack/react-query';
import api from '../services/api';
import toast from '../services/toast';
import type { ROIStats } from '../types';
import { selectTenant } from '../store/selectors';
import { 
  Download as DownloadIcon,
  Sparkles as SparklesIcon,
  DollarSign as DollarIcon,
  Users as UsersIcon,
  CalendarCheck as CalendarIcon,
  Percent as PercentIcon
} from 'lucide-react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';

export const Relatorios: React.FC = () => {
  const tenant = useStore(selectTenant);

  // React Query Fetch ROI Statistics
  const { data: roiStats = null, isLoading } = useQuery<ROIStats>({
    queryKey: ['roiStats'],
    queryFn: () => api.get('/dashboard/roi').then(r => r.data),
    staleTime: 30000,
  });

  const handleDownloadDia = async () => {
    try {
      const response = await api.get('/relatorios/pdf/dia', { responseType: 'blob' });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `fechamento_${new Date().toISOString().split('T')[0]}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      toast.success('Fechamento diário exportado com sucesso!');
    } catch (e) {
      console.error('Erro ao baixar PDF diário', e);
      toast.error('Erro ao exportar PDF diário.');
    }
  };

  const handleDownloadMensal = async () => {
    try {
      const response = await api.get('/relatorios/pdf/mensal', { responseType: 'blob' });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `roi_mensal_${new Date().getMonth() + 1}_${new Date().getFullYear()}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      toast.success('Relatório executivo exportado com sucesso!');
    } catch (e) {
      console.error('Erro ao baixar PDF de ROI', e);
      toast.error('Erro ao exportar PDF mensal.');
    }
  };

  // Chart data
  const dataFinanceira = roiStats ? [
    { name: 'Receita Realizada', valor: roiStats.receita_total, fill: '#16a34a' },
    { name: 'Receita Perdida (Faltas)', valor: roiStats.receita_perdida, fill: '#dc2626' },
  ] : [];

  const comparecimentoData = roiStats ? [
    { name: 'Comparecimento', value: roiStats.taxa_comparecimento },
    { name: 'Faltas', value: 100 - roiStats.taxa_comparecimento }
  ] : [];

  const COLORS = ['#16a34a', '#dc2626'];

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-text-primary">Desempenho & ROI</h2>
          <p className="text-xs text-text-secondary">Indicadores financeiros e de reativação de clientes</p>
        </div>
        {isLoading && (
          <div className="flex items-center gap-2 text-xs text-text-secondary animate-pulse">
            <div className="w-2.5 h-2.5 rounded-full bg-accent animate-ping"></div>
            <span>Carregando...</span>
          </div>
        )}
      </div>

      {/* ROI Highlight Card */}
      {roiStats && (
        <div className="bg-success-light border border-success/30 rounded-large p-6 sm:p-8 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-6 relative overflow-hidden">
          <div className="absolute right-0 top-0 translate-x-4 -translate-y-4 text-success/5 pointer-events-none">
            <SparklesIcon size={140} />
          </div>
          
          <div className="space-y-3 relative z-10">
            <span className="inline-flex items-center gap-1 bg-success/15 text-success text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full">
              <SparklesIcon size={10} /> Impacto Financeiro Gerado
            </span>
            <h3 className="text-xl sm:text-2xl font-bold text-text-primary leading-tight">
              Este mês o sistema gerou <strong className="text-success">R$ {roiStats.impacto_total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</strong> de impacto para sua {tenant.tipo === 'clinica' ? 'clínica' : 'loja'}.
            </h3>
            <p className="text-xs text-text-secondary max-w-xl">
              Cálculo baseado no retorno de {roiStats.reativados_count} pacientes inativos pelo CRM 
              e {roiStats.lista_espera_agendados} agendamentos recuperados pela lista de espera.
            </p>
          </div>

          <div className="bg-surface border border-success/20 rounded-medium p-4 text-center shrink-0 min-w-[140px] shadow-2xs relative z-10">
            <span className="block text-[10px] font-bold text-text-secondary uppercase">Retorno (ROI)</span>
            <strong className="block text-3xl font-extrabold text-success mt-1">{roiStats.roi.toFixed(1)}x</strong>
            <span className="text-[9px] text-text-secondary block mt-0.5">do valor mensal investido</span>
          </div>
        </div>
      )}

      {/* Métricas e Download de PDFs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* KPI Cards */}
        <div className="bg-surface border border-border rounded-large p-4 shadow-xs space-y-4 col-span-1 md:col-span-2">
          <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider">Indicadores Chave</h4>
          
          {isLoading ? (
            <div className="grid grid-cols-2 gap-4">
              <div className="h-16 shimmer rounded-medium"></div>
              <div className="h-16 shimmer rounded-medium"></div>
              <div className="h-16 shimmer rounded-medium"></div>
              <div className="h-16 shimmer rounded-medium"></div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-bg rounded-medium flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-accent-light text-accent flex items-center justify-center">
                  <UsersIcon size={18} />
                </div>
                <div>
                  <span className="block text-[9px] uppercase font-bold text-text-secondary">Reativados</span>
                  <strong className="text-sm text-text-primary">{roiStats?.reativados_count || 0} clientes</strong>
                </div>
              </div>

              <div className="p-3 bg-bg rounded-medium flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-success-light text-success flex items-center justify-center">
                  <CalendarIcon size={18} />
                </div>
                <div>
                  <span className="block text-[9px] uppercase font-bold text-text-secondary">Lista de Espera</span>
                  <strong className="text-sm text-text-primary">{roiStats?.lista_espera_agendados || 0} vagas</strong>
                </div>
              </div>

              <div className="p-3 bg-bg rounded-medium flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-warning-light text-warning flex items-center justify-center">
                  <PercentIcon size={18} />
                </div>
                <div>
                  <span className="block text-[9px] uppercase font-bold text-text-secondary">Comparecimento</span>
                  <strong className="text-sm text-text-primary">{roiStats?.taxa_comparecimento ? roiStats.taxa_comparecimento.toFixed(1) : '0.0'}%</strong>
                </div>
              </div>

              <div className="p-3 bg-bg rounded-medium flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-danger-light text-danger flex items-center justify-center">
                  <DollarIcon size={18} />
                </div>
                <div>
                  <span className="block text-[9px] uppercase font-bold text-text-secondary">Mensalidade Plano</span>
                  <strong className="text-sm text-text-primary">R$ {roiStats?.mensalidade ? roiStats.mensalidade.toFixed(2) : '0.00'}</strong>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Downloads */}
        <div className="bg-surface border border-border rounded-large p-4 shadow-xs flex flex-col justify-between">
          <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider mb-3">Exportar Relatórios</h4>
          
          <div className="space-y-3">
            <button
              onClick={handleDownloadDia}
              disabled={isLoading}
              className="w-full touch-target border border-border hover:border-accent hover:bg-accent-light/30 text-text-primary text-xs font-semibold rounded-medium flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-50"
            >
              <DownloadIcon size={16} className="text-text-secondary" />
              Fechamento Diário (Hoje)
            </button>

            <button
              onClick={handleDownloadMensal}
              disabled={isLoading}
              className="w-full touch-target bg-accent hover:bg-accent-hover text-white text-xs font-semibold rounded-medium flex items-center justify-center gap-2 transition-all shadow-sm cursor-pointer disabled:opacity-50"
            >
              <DownloadIcon size={16} />
              Relatório Executivo (Mês)
            </button>
          </div>

          <p className="text-[10px] text-text-secondary mt-4 leading-relaxed text-center">
            Arquivos gerados em PDF estruturados sob a identidade visual de sua empresa.
          </p>
        </div>
      </div>

      {/* Gráficos de Análise */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Gráfico Financeiro */}
        <div className="bg-surface border border-border rounded-large p-6 shadow-xs h-[300px] flex flex-col">
          <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider mb-4">Faturamento vs Faltas</h4>
          <div className="flex-1 w-full">
            {isLoading ? (
              <div className="h-full w-full shimmer rounded-medium"></div>
            ) : roiStats ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dataFinanceira}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip formatter={(value) => `R$ ${Number(value).toFixed(2)}`} />
                  <Bar dataKey="valor" radius={[4, 4, 0, 0]}>
                    {dataFinanceira.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full w-full flex items-center justify-center text-xs text-text-secondary">Sem dados para exibir</div>
            )}
          </div>
        </div>

        {/* Gráfico Comparecimento */}
        <div className="bg-surface border border-border rounded-large p-6 shadow-xs h-[300px] flex flex-col">
          <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider mb-4">Proporção de Comparecimento</h4>
          <div className="flex-1 w-full flex items-center justify-center">
            {isLoading ? (
              <div className="h-full w-full shimmer rounded-medium"></div>
            ) : roiStats ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={comparecimentoData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent !== undefined ? percent * 100 : 0).toFixed(0)}%`}
                    outerRadius={70}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {comparecimentoData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} />
                  <Legend verticalAlign="bottom" height={36} iconSize={10} iconType="circle" wrapperStyle={{ fontSize: 10 }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full w-full flex items-center justify-center text-xs text-text-secondary">Sem dados para exibir</div>
            )}
          </div>
        </div>

      </div>

    </div>
  );
};
