import React, { useState } from 'react';
import { useStore } from '../store/useStore';
import { useQuery } from '@tanstack/react-query';
import api from '../services/api';
import type { DashboardData, TabType } from '../types';
import { 
  selectActiveTab, 
  selectSetActiveTab, 
  selectLogout, 
  selectTenant 
} from '../store/selectors';

import { 
  LayoutDashboard, 
  CheckSquare, 
  Calendar, 
  Users, 
  Menu,
  Activity,
  ListOrdered,
  TrendingUp,
  Settings,
  LogOut,
  X
} from 'lucide-react';

export const BottomNav: React.FC = () => {
  const activeTab = useStore(selectActiveTab);
  const setActiveTab = useStore(selectSetActiveTab);
  const logout = useStore(selectLogout);
  const tenant = useStore(selectTenant);
  
  const [menuOpen, setMenuOpen] = useState(false);

  // Sync real-time approvals badge
  const { data: dashboard } = useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: () => api.get('/dashboard/hoje').then(r => r.data),
    refetchInterval: 30000,
    staleTime: 20000,
  });

  const approvalsCount = dashboard?.aprovacoes_pendentes ?? 0;

  const mainTabs = [
    { id: 'dashboard' as TabType, label: 'Início', icon: LayoutDashboard },
    { 
      id: 'aprovacoes' as TabType, 
      label: 'Aprovações', 
      icon: CheckSquare, 
      badge: approvalsCount 
    },
    { id: 'agenda' as TabType, label: tenant.tipo === 'clinica' ? 'Agenda' : 'Pedidos', icon: Calendar },
    { id: 'clientes' as TabType, label: tenant.tipo === 'clinica' ? 'Pacientes' : 'Clientes', icon: Users },
  ];

  const secondaryTabs = [
    { id: 'servicos' as TabType, label: tenant.tipo === 'clinica' ? 'Serviços' : 'Produtos', icon: Activity },
    { id: 'lista_espera' as TabType, label: 'Lista de Espera', icon: ListOrdered },
    { id: 'relatorios' as TabType, label: 'Desempenho & ROI', icon: TrendingUp },
    { id: 'configuracoes' as TabType, label: 'Configurações', icon: Settings },
  ];

  const handleTabClick = (tabId: TabType) => {
    setActiveTab(tabId);
    setMenuOpen(false);
  };

  const isSecondaryActive = secondaryTabs.some(tab => tab.id === activeTab);

  return (
    <>
      {/* Mobile Bottom Bar — height 64px + safe area padding */}
      <div 
        className="fixed bottom-0 left-0 right-0 bg-surface border-t border-border flex items-center justify-around z-40 select-none px-2 shadow-md pb-[env(safe-area-inset-bottom)] h-[calc(64px+env(safe-area-inset-bottom))]"
      >
        {mainTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          
          return (
            <button
              key={tab.id}
              onClick={() => handleTabClick(tab.id)}
              aria-label={tab.label}
              aria-current={isActive ? 'page' : undefined}
              className="flex flex-col items-center justify-center flex-1 h-full relative cursor-pointer"
            >
              <div 
                className={`p-1 rounded-medium transition-all duration-150 ${
                  isActive ? 'text-accent scale-105' : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                <Icon size={22} />
              </div>
              <span className={`text-[10px] tracking-tight leading-none mt-0.5 ${isActive ? 'text-accent font-semibold' : 'text-text-secondary'}`}>
                {tab.label}
              </span>
              {tab.badge !== undefined && tab.badge > 0 && (
                <span className="absolute top-1 right-1/4 px-1.5 py-0.5 text-[8px] font-bold bg-danger text-white rounded-full leading-none animate-pulse">
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}

        {/* More Tab */}
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label={menuOpen ? 'Fechar menu' : 'Abrir menu'}
          aria-expanded={menuOpen}
          className="flex flex-col items-center justify-center flex-1 h-full cursor-pointer"
        >
          <div 
            className={`p-1 rounded-medium transition-all duration-150 ${
              isSecondaryActive || menuOpen ? 'text-accent scale-105' : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {menuOpen ? <X size={22} /> : <Menu size={22} />}
          </div>
          <span className={`text-[10px] tracking-tight leading-none mt-0.5 ${isSecondaryActive || menuOpen ? 'text-accent font-semibold' : 'text-text-secondary'}`}>
            Mais
          </span>
        </button>
      </div>

      {/* Menu overlay sheet */}
      {menuOpen && (
        <div className="fixed inset-0 bg-text-primary/20 backdrop-blur-xs z-30 flex flex-col justify-end">
          <div 
            className="absolute inset-0" 
            onClick={() => setMenuOpen(false)}
          />
          <div className="bg-surface w-full rounded-t-large border-t border-border p-6 relative z-10 animate-in slide-in-from-bottom duration-200" role="dialog" aria-modal="true" aria-label="Mais opções">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-sm font-semibold text-text-primary">Outras Opções</h3>
              <button 
                onClick={() => setMenuOpen(false)}
                aria-label="Fechar menu"
                className="p-1 rounded-full hover:bg-background text-text-secondary cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>
            
            <div className="grid grid-cols-2 gap-3 mb-6">
              {secondaryTabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                
                return (
                  <button
                    key={tab.id}
                    onClick={() => handleTabClick(tab.id)}
                    aria-current={isActive ? 'page' : undefined}
                    className={`flex flex-col items-center p-4 border rounded-medium touch-target gap-2 justify-center transition-all cursor-pointer ${
                      isActive 
                        ? 'border-accent bg-accent-light text-accent font-semibold' 
                        : 'border-border bg-surface text-text-secondary hover:border-slate-300'
                    }`}
                  >
                    <Icon size={20} />
                    <span className="text-xs">{tab.label}</span>
                  </button>
                );
              })}
            </div>

            <button
              onClick={() => {
                setMenuOpen(false);
                logout();
              }}
              className="w-full touch-target border border-danger/20 hover:border-danger text-danger bg-rose-50 font-semibold rounded-medium flex items-center justify-center gap-2 cursor-pointer"
            >
              <LogOut size={16} />
              Sair do Sistema
            </button>
          </div>
        </div>
      )}
    </>
  );
};
