export interface TenantConfig {
  id: string;
  nome: string;
  tipo: 'clinica' | 'loja';
  corPrimaria: string;
  sistemaAtivo: boolean;
  logo_url?: string;
}

export const getTenantConfig = (): TenantConfig => {
  return {
    id: import.meta.env.VITE_TENANT_ID || 'd290f1ee-6c54-4b01-90e6-d701748f0851', // Default tenant ID
    nome: import.meta.env.VITE_TENANT_NOME || 'Clínica Sorriso',
    tipo: (import.meta.env.VITE_TENANT_TIPO as 'clinica' | 'loja') || 'clinica',
    corPrimaria: import.meta.env.VITE_TENANT_COR_PRIMARIA || '#2563eb',
    sistemaAtivo: import.meta.env.VITE_TENANT_SISTEMA_ATIVO !== 'false',
    logo_url: import.meta.env.VITE_TENANT_LOGO_URL || '',
  };
};


export const applyTenantTheme = (tipo: 'clinica' | 'loja') => {
  const root = document.documentElement;
  root.setAttribute('data-theme', tipo);
};


