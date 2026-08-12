import React, { useState } from 'react';
import { useStore } from '../store/useStore';
import { selectLogin, selectError, selectTenant } from '../store/selectors';
import api from '../services/api';
import { MessageSquare, Lock, Mail, Loader2 } from 'lucide-react';

export const Login: React.FC = () => {
  const login = useStore(selectLogin);
  const error = useStore(selectError).global;
  const tenant = useStore(selectTenant);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [masterMode, setMasterMode] = useState(false);
  const [masterError, setMasterError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    
    setLoading(true);
    setMasterError('');
    if (masterMode) {
      try {
        await api.post('/master/auth/login', { email, password });
        localStorage.setItem('master_auth', 'true');
        window.dispatchEvent(new Event('master-auth-changed'));
      } catch (err: unknown) {
        const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
        setMasterError(detail || 'Erro ao entrar no painel master.');
      }
    } else {
      await login(email, password);
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-background flex flex-col justify-center items-center p-4 page-enter">
      <div className="bg-surface w-full max-w-md border border-border rounded-large shadow-large p-8">
        
        {/* Branding header */}
        <div className="text-center mb-8 flex flex-col items-center">
          <div className="w-12 h-12 rounded-medium bg-accent-light text-accent flex items-center justify-center mb-3">
            <MessageSquare size={24} />
          </div>
          <h2 className="text-xl font-semibold text-text-primary">
            {masterMode ? 'Painel Master' : 'Painel Administrativo'}
          </h2>
          <p className="text-sm text-text-secondary">
            {masterMode ? 'Gestão comercial e operacional do SaaS' : `${tenant.nome} — Automação de WhatsApp`}
          </p>
        </div>

        {(masterMode ? masterError : error) && (
          <div className="mb-6 p-4 bg-rose-50 border border-rose-100 text-danger text-xs font-semibold rounded-medium">
            {masterMode ? masterError : error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="login-email" className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">
              E-mail corporativo
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" size={18} />
              <input
                id="login-email"
                type="email"
                required
                disabled={loading}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="nome@empresa.com.br"
                className="w-full pl-10 pr-4 h-11 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15 transition-all"
              />
            </div>
          </div>

          <div>
            <label htmlFor="login-password" className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">
              Senha de acesso
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" size={18} />
              <input
                id="login-password"
                type="password"
                required
                disabled={loading}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-10 pr-4 h-11 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15 transition-all"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || !email || !password}
            className="w-full h-11 bg-accent hover:bg-accent-hover disabled:opacity-50 text-white font-medium rounded-medium transition-all shadow-sm flex items-center justify-center gap-2 cursor-pointer"
          >
            {loading ? (
              <>
                <Loader2 className="animate-spin" size={18} />
                Entrando...
              </>
            ) : (
              masterMode ? 'Entrar no Master' : 'Entrar no Painel'
            )}
          </button>
        </form>

        <button
          type="button"
          onClick={() => {
            setMasterMode((value) => !value);
            setMasterError('');
          }}
          className="mt-4 w-full h-10 border border-border bg-background hover:bg-slate-50 text-text-primary text-xs font-semibold rounded-medium transition-all cursor-pointer"
        >
          {masterMode ? 'Entrar como clínica' : 'Entrar no Painel Master'}
        </button>

        <div className="mt-8 text-center text-xs text-text-secondary border-t border-border pt-6">
          SaaS Multi-tenant de Gestão Integrada via WhatsApp.
          <br />
          Desenvolvido com foco em velocidade e segurança.
        </div>
      </div>
    </div>
  );
};
