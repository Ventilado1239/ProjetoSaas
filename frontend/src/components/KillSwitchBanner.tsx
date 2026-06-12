import React from 'react';
import { ShieldAlert, ExternalLink } from 'lucide-react';

interface KillSwitchBannerProps {
  tenantNome: string;
}

export const KillSwitchBanner: React.FC<KillSwitchBannerProps> = ({ tenantNome }) => {
  return (
    <div className="fixed inset-0 bg-background z-50 flex items-center justify-center p-4">
      <div className="bg-surface max-w-md w-full border border-danger/30 rounded-large p-8 shadow-large text-center flex flex-col items-center">
        <div className="w-16 h-16 rounded-full bg-danger-light flex items-center justify-center text-danger mb-6">
          <ShieldAlert size={36} />
        </div>
        
        <h1 className="text-xl font-bold text-text-primary mb-2">
          Sistema Temporariamente Suspenso
        </h1>
        
        <p className="text-sm text-text-secondary mb-6 leading-relaxed">
          O sistema da empresa <strong className="text-text-primary">{tenantNome}</strong> foi pausado devido a pendências de pagamento.
          Regularize sua assinatura para liberar o WhatsApp e o painel administrativo imediatamente.
        </p>
        
        <a 
          href="https://asaas.com" 
          target="_blank" 
          rel="noopener noreferrer"
          className="w-full touch-target flex items-center justify-center gap-2 bg-danger hover:bg-danger/90 text-white font-medium rounded-medium transition-all shadow-sm"
        >
          Regularizar no Asaas
          <ExternalLink size={16} />
        </a>
        
        <p className="text-xs text-text-secondary mt-6">
          Após realizar o pagamento, a reativação do painel ocorrerá em menos de 1 minuto de forma automática.
        </p>
      </div>
    </div>
  );
};
