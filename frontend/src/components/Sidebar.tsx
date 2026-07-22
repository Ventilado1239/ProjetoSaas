import React from 'react';
import { useStore } from '../store/useStore';
import { useQuery } from '@tanstack/react-query';
import api from '../services/api';
import type { DashboardData, TabType } from '../types';
import { 
  selectActiveTab, 
  selectSetActiveTab, 
  selectLogout, 
  selectUser, 
  selectTenant 
} from '../store/selectors';

import { 
  LayoutDashboard, 
  CheckSquare, 
  Calendar, 
  Users, 
  Settings, 
  TrendingUp, 
  ListOrdered, 
  Activity,
  LogOut 
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const activeTab = useStore(selectActiveTab);
  const setActiveTab = useStore(selectSetActiveTab);
  const logout = useStore(selectLogout);
  const user = useStore(selectUser);
  const tenant = useStore(selectTenant);

  // Sync real-time approvals badge using React Query (shared cache)
  const { data: dashboard } = useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: () => api.get('/dashboard/hoje').then(r => r.data),
    refetchInterval: 30000,
    staleTime: 20000,
  });

  const approvalsCount = dashboard?.aprovacoes_pendentes ?? dashboard?.aprovacoes_pendentes ?? 0;

  const navigationItemsGroup1 = [
    { id: 'dashboard' as TabType, label: 'Visão do Dia', icon: LayoutDashboard },
    { 
      id: 'aprovacoes' as TabType, 
      label: 'Aprovações', 
      icon: CheckSquare, 
      badge: approvalsCount 
    },
    { id: 'agenda' as TabType, label: tenant.tipo === 'clinica' ? 'Agenda' : 'Pedidos', icon: Calendar },
    { id: 'clientes' as TabType, label: tenant.tipo === 'clinica' ? 'Pacientes' : 'Clientes', icon: Users },
  ];

  const navigationItemsGroup2 = [
    { id: 'servicos' as TabType, label: tenant.tipo === 'clinica' ? 'Serviços' : 'Produtos', icon: Activity },
    { id: 'lista_espera' as TabType, label: 'Lista de Espera', icon: ListOrdered },
    { id: 'relatorios' as TabType, label: 'Desempenho & ROI', icon: TrendingUp },
    { id: 'configuracoes' as TabType, label: 'Configurações', icon: Settings },
  ];

  return (
    <aside className="w-60 min-w-[240px] max-w-[240px] bg-surface border-r border-border min-h-screen flex flex-col justify-between select-none">
      <div className="flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-border flex items-center gap-3">
          {tenant.logo_url ? (
            <img src={tenant.logo_url} alt="Logo" className="w-8 h-8 rounded-medium object-contain" />
          ) : (
            <div className="w-8 h-8 rounded-medium bg-accent-light text-accent flex items-center justify-center font-bold">
              {tenant.nome.charAt(0)}
            </div>
          )}
          <div className="min-w-0">
            <h1 className="text-sm font-semibold text-text-primary truncate">
              {tenant.nome}
            </h1>
            <span className="text-[10px] uppercase font-bold tracking-wider text-text-secondary">
              {tenant.tipo === 'clinica' ? 'Clínica' : 'Loja'}
            </span>
          </div>
        </div>

        {/* Links Group 1 */}
        <nav className="p-4 space-y-1">
          {navigationItemsGroup1.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                aria-current={isActive ? 'page' : undefined}
                className={`w-full flex items-center justify-between h-10 px-3 rounded-medium transition-all cursor-pointer sidebar-item ${
                  isActive 
                    ? 'bg-accent-light text-accent font-semibold' 
                    : 'text-text-secondary hover:bg-bg hover:text-text-primary'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon size={18} />
                  <span className="text-xs">{item.label}</span>
                </div>
                {item.badge !== undefined && item.badge > 0 && (
                  <span className="px-2 py-0.5 text-[10px] font-bold bg-danger text-white rounded-full">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Visual Separator */}
        <div className="px-6 py-2">
          <hr className="border-border/60" />
        </div>

        {/* Links Group 2 */}
        <nav className="p-4 space-y-1">
          {navigationItemsGroup2.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                aria-current={isActive ? 'page' : undefined}
                className={`w-full flex items-center justify-between h-10 px-3 rounded-medium transition-all cursor-pointer sidebar-item ${
                  isActive 
                    ? 'bg-accent-light text-accent font-semibold' 
                    : 'text-text-secondary hover:bg-bg hover:text-text-primary'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon size={18} />
                  <span className="text-xs">{item.label}</span>
                </div>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer / Profile details */}
      <div className="p-4 border-t border-border flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex flex-col min-w-0">
            <span className="text-xs font-semibold text-text-primary truncate">
              {user?.nome}
            </span>
            <span className="text-[10px] text-text-secondary capitalize truncate">
              {user?.perfil === 'dono' ? 'Administrador' : user?.perfil}
            </span>
          </div>
          
          <button 
            onClick={logout}
            title="Sair do sistema"
            aria-label="Sair do sistema"
            className="p-2 text-text-secondary hover:text-danger hover:bg-rose-50 rounded-medium transition-all cursor-pointer"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  );
};
