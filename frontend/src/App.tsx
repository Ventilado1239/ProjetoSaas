import React, { useEffect, Suspense, lazy } from 'react';
import { useStore } from './store/useStore';
import { 
  selectIsAuthenticated, 
  selectActiveTab, 
  selectTenant, 
  selectUser, 
  selectCheckAuth 
} from './store/selectors';
import { Login } from './components/Login';
import { Sidebar } from './components/Sidebar';
import { BottomNav } from './components/BottomNav';
import { KillSwitchBanner } from './components/KillSwitchBanner';
import { ToastContainer } from './components/Toast';

// Lazy-load screens for code splitting & faster bundle loading
const Dashboard = lazy(() => import('./components/Dashboard').then(m => ({ default: m.Dashboard })));
const Aprovacoes = lazy(() => import('./components/Aprovacoes').then(m => ({ default: m.Aprovacoes })));
const Agenda = lazy(() => import('./components/Agenda').then(m => ({ default: m.Agenda })));
const Clientes = lazy(() => import('./components/Clientes').then(m => ({ default: m.Clientes })));
const Servicos = lazy(() => import('./components/Servicos').then(m => ({ default: m.Servicos })));
const ListaEspera = lazy(() => import('./components/ListaEspera').then(m => ({ default: m.ListaEspera })));
const Relatorios = lazy(() => import('./components/Relatorios').then(m => ({ default: m.Relatorios })));
const Configuracoes = lazy(() => import('./components/Configuracoes').then(m => ({ default: m.Configuracoes })));

const App: React.FC = () => {
  const isAuthenticated = useStore(selectIsAuthenticated);
  const activeTab = useStore(selectActiveTab);
  const tenant = useStore(selectTenant);
  const user = useStore(selectUser);
  const checkAuth = useStore(selectCheckAuth);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // 1. Unauthenticated -> Login Screen
  if (!isAuthenticated) {
    return (
      <>
        <Login />
        <ToastContainer />
      </>
    );
  }

  // 2. Kill Switch Active -> Lock Screen (Allow owner to bypass and re-enable system)
  if (tenant.sistemaAtivo === false && user?.perfil !== 'dono') {
    return (
      <>
        <KillSwitchBanner tenantNome={tenant.nome} />
        <ToastContainer />
      </>
    );
  }

  // Render the currently active tab screen
  const renderActiveScreen = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />;
      case 'aprovacoes':
        return <Aprovacoes />;
      case 'agenda':
        return <Agenda />;
      case 'clientes':
        return <Clientes />;
      case 'servicos':
        return <Servicos />;
      case 'lista_espera':
        return <ListaEspera />;
      case 'relatorios':
        return <Relatorios />;
      case 'configuracoes':
        return <Configuracoes />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="min-h-screen bg-background flex text-text-primary page-enter">
      {/* Desktop Sidebar (hidden on mobile/tablet) */}
      <div className="hidden lg:flex">
        <Sidebar />
      </div>

      {/* Main Content Area */}
      <main className="flex-1 p-4 sm:p-6 lg:p-8 pb-24 lg:pb-8 overflow-x-hidden max-w-7xl mx-auto w-full">
        <Suspense fallback={
          <div className="flex items-center justify-center min-h-[60vh]">
            <div className="w-8 h-8 border-4 border-accent border-t-transparent rounded-full animate-spin"></div>
          </div>
        }>
          {renderActiveScreen()}
        </Suspense>
      </main>

      {/* Mobile Bottom Bar (hidden on desktop) */}
      <div className="lg:hidden">
        <BottomNav />
      </div>

      {/* Toast notifications rendering container */}
      <ToastContainer />
    </div>
  );
};

export default App;
