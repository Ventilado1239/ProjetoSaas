/* eslint-disable react-hooks/set-state-in-effect */
import React, { useEffect, useMemo, useState } from 'react';
import api from '../services/api';
import toast from '../services/toast';
import {
  Building2,
  CreditCard,
  DollarSign,
  KeyRound,
  LogOut,
  Plus,
  Power,
  RefreshCw,
  Search,
  ShieldCheck,
} from 'lucide-react';

interface MasterSummary {
  clientes_total: number;
  clientes_ativos: number;
  inadimplentes: number;
  leads_total: number;
  mrr: number;
}

interface MasterTenant {
  id: string;
  nome: string;
  tipo: 'clinica' | 'loja';
  plano: string;
  sistema_ativo: boolean;
  pagamento_status: string;
  crm_stage: string;
  mensalidade: number;
  proximo_vencimento?: string;
  responsavel_nome?: string;
  responsavel_email?: string;
  whatsapp_numero: string;
  owner_whatsapp?: string;
  evolution_instance_name?: string;
  asaas_customer_id?: string;
  asaas_subscription_id?: string;
  pacientes: number;
  usuarios: number;
  atendimentos: number;
}

interface MasterLead {
  id: string;
  nome_clinica: string;
  responsavel_nome?: string;
  responsavel_email?: string;
  whatsapp?: string;
  etapa: string;
  valor_potencial: number;
  proxima_acao?: string;
  observacoes?: string;
}

const moneyFormatter = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
const leadStages = ['lead', 'demo', 'proposta', 'negociacao', 'ganho', 'perdido'];

export const MasterPanel: React.FC = () => {
  const [summary, setSummary] = useState<MasterSummary | null>(null);
  const [tenants, setTenants] = useState<MasterTenant[]>([]);
  const [leads, setLeads] = useState<MasterLead[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [leadOpen, setLeadOpen] = useState(false);
  const [resetTenant, setResetTenant] = useState<MasterTenant | null>(null);
  const [billingTenant, setBillingTenant] = useState<MasterTenant | null>(null);
  const [newPassword, setNewPassword] = useState('');
  const [billingForm, setBillingForm] = useState({ cpf_cnpj: '', next_due_date: '', billing_type: 'PIX' });

  const [tenantForm, setTenantForm] = useState({
    nome: '',
    whatsapp_numero: '',
    owner_whatsapp: '',
    admin_nome: 'Administrador',
    admin_email: '',
    admin_password: '',
    plano: 'starter',
    mensalidade: '397',
    evolution_instance_name: '',
    cor_primaria: '#2563eb',
  });

  const [leadForm, setLeadForm] = useState({
    nome_clinica: '',
    responsavel_nome: '',
    responsavel_email: '',
    whatsapp: '',
    etapa: 'lead',
    valor_potencial: '397',
    proxima_acao: '',
    observacoes: '',
  });

  const loadMasterData = async () => {
    setLoading(true);
    try {
      const [summaryRes, tenantsRes, leadsRes] = await Promise.all([
        api.get('/master/summary'),
        api.get('/master/tenants'),
        api.get('/master/leads'),
      ]);
      setSummary(summaryRes.data);
      setTenants(tenantsRes.data);
      setLeads(leadsRes.data);
    } catch {
      toast.error('Erro ao carregar painel master.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadMasterData();
  }, []);

  const filteredTenants = useMemo(() => {
    const q = search.toLowerCase();
    return tenants.filter((tenant) =>
      [tenant.nome, tenant.responsavel_nome, tenant.responsavel_email, tenant.whatsapp_numero]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(q))
    );
  }, [search, tenants]);

  const overdueTenants = useMemo(
    () => tenants.filter((tenant) => ['atrasado', 'inadimplente'].includes(tenant.pagamento_status)),
    [tenants]
  );

  const logout = async () => {
    await api.post('/master/auth/logout');
    localStorage.removeItem('master_auth');
    localStorage.removeItem('master_user');
    window.dispatchEvent(new Event('master-auth-changed'));
  };

  const createTenant = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      const payload = {
        ...tenantForm,
        tipo: 'clinica',
        mensalidade: Number(tenantForm.mensalidade || 0),
        responsavel_nome: tenantForm.admin_nome,
        responsavel_email: tenantForm.admin_email,
        evolution_instance_name: tenantForm.evolution_instance_name || undefined,
        owner_whatsapp: tenantForm.owner_whatsapp || undefined,
      };
      const res = await api.post('/master/tenants', payload);
      toast.success(`Clínica criada. Login: ${res.data.admin_email}`);
      setCreateOpen(false);
      setTenantForm({
        nome: '',
        whatsapp_numero: '',
        owner_whatsapp: '',
        admin_nome: 'Administrador',
        admin_email: '',
        admin_password: '',
        plano: 'starter',
        mensalidade: '397',
        evolution_instance_name: '',
        cor_primaria: '#2563eb',
      });
      await loadMasterData();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      toast.error(detail || 'Erro ao criar clínica.');
    }
  };

  const updateTenant = async (tenant: MasterTenant, patch: Record<string, unknown>) => {
    try {
      await api.put(`/master/tenants/${tenant.id}`, patch);
      toast.success('Cliente atualizado.');
      await loadMasterData();
    } catch {
      toast.error('Erro ao atualizar cliente.');
    }
  };

  const resetPassword = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!resetTenant) return;
    try {
      const res = await api.post(`/master/tenants/${resetTenant.id}/reset-password`, { new_password: newPassword });
      toast.success(`Senha alterada: ${res.data.email}`);
      setResetTenant(null);
      setNewPassword('');
    } catch {
      toast.error('Erro ao redefinir senha.');
    }
  };

  const createSubscription = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!billingTenant) return;
    try {
      await api.post(`/master/tenants/${billingTenant.id}/billing/subscription`, {
        ...billingForm,
        cycle: 'MONTHLY',
      });
      toast.success('Assinatura recorrente criada no Asaas.');
      setBillingTenant(null);
      setBillingForm({ cpf_cnpj: '', next_due_date: '', billing_type: 'PIX' });
      await loadMasterData();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      toast.error(detail || 'Erro ao criar assinatura no Asaas.');
    }
  };

  const createLead = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      await api.post('/master/leads', { ...leadForm, valor_potencial: Number(leadForm.valor_potencial || 0) });
      toast.success('Lead criado.');
      setLeadOpen(false);
      setLeadForm({
        nome_clinica: '',
        responsavel_nome: '',
        responsavel_email: '',
        whatsapp: '',
        etapa: 'lead',
        valor_potencial: '397',
        proxima_acao: '',
        observacoes: '',
      });
      await loadMasterData();
    } catch {
      toast.error('Erro ao criar lead.');
    }
  };

  const updateLead = async (lead: MasterLead, patch: Record<string, unknown>) => {
    try {
      await api.put(`/master/leads/${lead.id}`, patch);
      toast.success('Lead atualizado.');
      await loadMasterData();
    } catch {
      toast.error('Erro ao atualizar lead.');
    }
  };

  const summaryCards = [
    { label: 'Clientes', value: summary?.clientes_total ?? 0, icon: Building2 },
    { label: 'Ativos', value: summary?.clientes_ativos ?? 0, icon: ShieldCheck },
    { label: 'Inadimplentes', value: summary?.inadimplentes ?? 0, icon: CreditCard },
    { label: 'MRR', value: moneyFormatter.format(summary?.mrr ?? 0), icon: DollarSign },
  ];

  return (
    <div className="min-h-screen bg-background text-text-primary">
      <header className="border-b border-border bg-surface">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold">Painel Master</h1>
            <p className="text-xs text-text-secondary">Operação, CRM e financeiro do SaaS</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={loadMasterData} className="touch-target px-3 border border-border rounded-medium text-xs font-semibold bg-surface hover:bg-background flex items-center gap-1.5">
              <RefreshCw size={14} /> Atualizar
            </button>
            <button onClick={logout} className="touch-target px-3 bg-text-primary text-white rounded-medium text-xs font-semibold flex items-center gap-1.5">
              <LogOut size={14} /> Sair
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {summaryCards.map((card) => {
            const Icon = card.icon;
            return (
              <div key={card.label} className="bg-surface border border-border rounded-large p-4 shadow-xs">
                <div className="flex items-center justify-between text-text-secondary mb-3">
                  <span className="text-[10px] font-bold uppercase">{card.label}</span>
                  <Icon size={16} />
                </div>
                <div className="text-2xl font-bold">{card.value}</div>
              </div>
            );
          })}
        </section>

        <section className="bg-surface border border-border rounded-large shadow-xs overflow-hidden">
          <div className="p-4 border-b border-border flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div>
              <h2 className="font-bold">Clientes SaaS</h2>
              <p className="text-xs text-text-secondary">Clínicas contratantes, acessos e financeiro</p>
            </div>
            <div className="flex flex-col sm:flex-row gap-2">
              <div className="relative">
                <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
                <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar cliente..." className="h-10 pl-9 pr-3 border border-border rounded-medium text-xs bg-surface" />
              </div>
              <button onClick={() => setCreateOpen(true)} className="touch-target px-3 bg-accent text-white rounded-medium text-xs font-semibold flex items-center justify-center gap-1.5">
                <Plus size={14} /> Nova clínica
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-background text-xs text-text-secondary">
                <tr>
                  <th className="text-left p-3">Clínica</th>
                  <th className="text-left p-3">Financeiro</th>
                  <th className="text-left p-3">Uso</th>
                  <th className="text-left p-3">Integração</th>
                  <th className="text-right p-3">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredTenants.map((tenant) => (
                  <tr key={tenant.id}>
                    <td className="p-3">
                      <div className="font-semibold">{tenant.nome}</div>
                      <div className="text-xs text-text-secondary">{tenant.responsavel_nome || 'Sem responsável'} · {tenant.responsavel_email || 'sem e-mail'}</div>
                      <div className="text-[10px] text-text-secondary font-mono mt-1">{tenant.id}</div>
                    </td>
                    <td className="p-3">
                      <select value={tenant.pagamento_status} onChange={(e) => updateTenant(tenant, { pagamento_status: e.target.value })} className="h-8 border border-border rounded-medium text-xs bg-surface">
                        <option value="em_dia">Em dia</option>
                        <option value="atrasado">Atrasado</option>
                        <option value="inadimplente">Inadimplente</option>
                        <option value="cancelado">Cancelado</option>
                      </select>
                      <select value={tenant.crm_stage} onChange={(e) => updateTenant(tenant, { crm_stage: e.target.value })} className="h-8 mt-1 border border-border rounded-medium text-xs bg-surface">
                        <option value="onboarding">Onboarding</option>
                        <option value="ativo">Ativo</option>
                        <option value="risco">Em risco</option>
                        <option value="cancelado">Cancelado</option>
                      </select>
                      <div className="text-xs text-text-secondary mt-1">{moneyFormatter.format(tenant.mensalidade || 0)} · {tenant.plano}</div>
                    </td>
                    <td className="p-3 text-xs">
                      <div>{tenant.pacientes} pacientes</div>
                      <div>{tenant.usuarios} usuários</div>
                      <div>{tenant.atendimentos} atendimentos</div>
                    </td>
                    <td className="p-3 text-xs">
                      <div className="font-mono">{tenant.evolution_instance_name || 'sem instância'}</div>
                      <div className="text-text-secondary">{tenant.owner_whatsapp || tenant.whatsapp_numero}</div>
                      <div className={tenant.asaas_subscription_id ? 'text-emerald-700 mt-1' : 'text-amber-700 mt-1'}>
                        {tenant.asaas_subscription_id ? 'Asaas recorrente ativo' : 'Asaas não configurado'}
                      </div>
                    </td>
                    <td className="p-3">
                      <div className="flex justify-end gap-2">
                        {!tenant.asaas_subscription_id && (
                          <button onClick={() => setBillingTenant(tenant)} className="h-9 px-2 rounded-medium text-xs font-semibold bg-background border border-border flex items-center gap-1">
                            <CreditCard size={13} /> Cobrança
                          </button>
                        )}
                        <button onClick={() => updateTenant(tenant, { sistema_ativo: !tenant.sistema_ativo })} className={`h-9 px-2 rounded-medium text-xs font-semibold flex items-center gap-1 ${tenant.sistema_ativo ? 'bg-rose-50 text-rose-600' : 'bg-emerald-50 text-emerald-700'}`}>
                          <Power size={13} /> {tenant.sistema_ativo ? 'Suspender' : 'Ativar'}
                        </button>
                        <button onClick={() => setResetTenant(tenant)} className="h-9 px-2 rounded-medium text-xs font-semibold bg-background border border-border flex items-center gap-1">
                          <KeyRound size={13} /> Senha
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!loading && filteredTenants.length === 0 && (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-text-secondary">Nenhum cliente encontrado.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        {overdueTenants.length > 0 && (
          <section className="bg-rose-50 border border-rose-100 rounded-large p-4">
            <div className="flex items-center justify-between gap-3 mb-3">
              <div>
                <h2 className="font-bold text-rose-900">Atenção financeira</h2>
                <p className="text-xs text-rose-700">Clientes com pagamento atrasado ou inadimplente</p>
              </div>
              <span className="text-sm font-bold text-rose-700">{overdueTenants.length}</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {overdueTenants.map((tenant) => (
                <div key={tenant.id} className="bg-surface border border-rose-100 rounded-medium p-3">
                  <div className="font-semibold text-sm">{tenant.nome}</div>
                  <div className="text-xs text-text-secondary">{tenant.responsavel_email || 'sem e-mail'} · {tenant.owner_whatsapp || tenant.whatsapp_numero}</div>
                  <div className="mt-2 text-xs font-bold text-rose-700">{tenant.pagamento_status} · {moneyFormatter.format(tenant.mensalidade || 0)}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        <section className="bg-surface border border-border rounded-large shadow-xs">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <div>
              <h2 className="font-bold">CRM Comercial</h2>
              <p className="text-xs text-text-secondary">Leads, propostas, demos e próximos passos</p>
            </div>
            <button onClick={() => setLeadOpen(true)} className="touch-target px-3 bg-accent text-white rounded-medium text-xs font-semibold flex items-center gap-1.5">
              <Plus size={14} /> Novo lead
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 p-4">
            {leads.map((lead) => (
              <div key={lead.id} className="border border-border rounded-medium p-3 bg-background">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-semibold text-sm">{lead.nome_clinica}</h3>
                    <p className="text-xs text-text-secondary">{lead.responsavel_nome || 'Sem responsável'}</p>
                  </div>
                  <span className="text-[10px] font-bold uppercase bg-accent-light text-accent px-2 py-1 rounded-full">{lead.etapa}</span>
                </div>
                <div className="text-xs text-text-secondary mt-3 space-y-1">
                  <div>{lead.whatsapp || 'Sem WhatsApp'} · {lead.responsavel_email || 'sem e-mail'}</div>
                  <div>Potencial: {moneyFormatter.format(lead.valor_potencial || 0)}</div>
                  <div>Próxima ação: {lead.proxima_acao || 'não definida'}</div>
                </div>
                <select value={lead.etapa} onChange={(e) => updateLead(lead, { etapa: e.target.value })} className="mt-3 h-9 w-full border border-border rounded-medium text-xs bg-surface">
                  {leadStages.map((stage) => (
                    <option key={stage} value={stage}>{stage}</option>
                  ))}
                </select>
              </div>
            ))}
            {!loading && leads.length === 0 && <div className="text-sm text-text-secondary">Nenhum lead cadastrado.</div>}
          </div>
        </section>
      </main>

      {createOpen && (
        <Modal title="Criar Nova Clínica" onClose={() => setCreateOpen(false)}>
          <form onSubmit={createTenant} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input label="Nome da clínica" value={tenantForm.nome} onChange={(v) => setTenantForm({ ...tenantForm, nome: v })} required />
            <Input label="WhatsApp comercial" value={tenantForm.whatsapp_numero} onChange={(v) => setTenantForm({ ...tenantForm, whatsapp_numero: v })} required />
            <Input label="WhatsApp responsável" value={tenantForm.owner_whatsapp} onChange={(v) => setTenantForm({ ...tenantForm, owner_whatsapp: v })} />
            <Input label="Instância Evolution" value={tenantForm.evolution_instance_name} onChange={(v) => setTenantForm({ ...tenantForm, evolution_instance_name: v })} />
            <Input label="Nome do dono" value={tenantForm.admin_nome} onChange={(v) => setTenantForm({ ...tenantForm, admin_nome: v })} required />
            <Input label="E-mail de acesso" value={tenantForm.admin_email} onChange={(v) => setTenantForm({ ...tenantForm, admin_email: v })} required />
            <Input label="Senha inicial" value={tenantForm.admin_password} onChange={(v) => setTenantForm({ ...tenantForm, admin_password: v })} required type="password" />
            <Input label="Mensalidade" value={tenantForm.mensalidade} onChange={(v) => setTenantForm({ ...tenantForm, mensalidade: v })} />
            <div className="sm:col-span-2 flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setCreateOpen(false)} className="h-10 px-4 border border-border rounded-medium text-xs font-semibold">Cancelar</button>
              <button type="submit" className="h-10 px-4 bg-accent text-white rounded-medium text-xs font-semibold">Criar clínica</button>
            </div>
          </form>
        </Modal>
      )}

      {leadOpen && (
        <Modal title="Novo Lead" onClose={() => setLeadOpen(false)}>
          <form onSubmit={createLead} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input label="Nome da clínica" value={leadForm.nome_clinica} onChange={(v) => setLeadForm({ ...leadForm, nome_clinica: v })} required />
            <Input label="Responsável" value={leadForm.responsavel_nome} onChange={(v) => setLeadForm({ ...leadForm, responsavel_nome: v })} />
            <Input label="E-mail" value={leadForm.responsavel_email} onChange={(v) => setLeadForm({ ...leadForm, responsavel_email: v })} />
            <Input label="WhatsApp" value={leadForm.whatsapp} onChange={(v) => setLeadForm({ ...leadForm, whatsapp: v })} />
            <Input label="Valor potencial" value={leadForm.valor_potencial} onChange={(v) => setLeadForm({ ...leadForm, valor_potencial: v })} />
            <Input label="Próxima ação" value={leadForm.proxima_acao} onChange={(v) => setLeadForm({ ...leadForm, proxima_acao: v })} />
            <div className="sm:col-span-2 flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setLeadOpen(false)} className="h-10 px-4 border border-border rounded-medium text-xs font-semibold">Cancelar</button>
              <button type="submit" className="h-10 px-4 bg-accent text-white rounded-medium text-xs font-semibold">Criar lead</button>
            </div>
          </form>
        </Modal>
      )}

      {resetTenant && (
        <Modal title={`Resetar senha - ${resetTenant.nome}`} onClose={() => setResetTenant(null)}>
          <form onSubmit={resetPassword} className="space-y-3">
            <Input label="Nova senha do dono" value={newPassword} onChange={setNewPassword} type="password" required />
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setResetTenant(null)} className="h-10 px-4 border border-border rounded-medium text-xs font-semibold">Cancelar</button>
              <button type="submit" className="h-10 px-4 bg-accent text-white rounded-medium text-xs font-semibold">Alterar senha</button>
            </div>
          </form>
        </Modal>
      )}

      {billingTenant && (
        <Modal title={`Ativar cobrança - ${billingTenant.nome}`} onClose={() => setBillingTenant(null)}>
          <form onSubmit={createSubscription} className="space-y-3">
            <p className="text-xs text-text-secondary">
              Cria uma assinatura mensal de {moneyFormatter.format(billingTenant.mensalidade || 0)}. O CPF/CNPJ é enviado ao Asaas e não fica armazenado no SaaS.
            </p>
            <Input label="CPF ou CNPJ" value={billingForm.cpf_cnpj} onChange={(v) => setBillingForm({ ...billingForm, cpf_cnpj: v })} required />
            <Input label="Primeiro vencimento" value={billingForm.next_due_date} onChange={(v) => setBillingForm({ ...billingForm, next_due_date: v })} required type="date" />
            <label className="block">
              <span className="text-xs font-bold text-text-secondary uppercase">Forma de cobrança</span>
              <select value={billingForm.billing_type} onChange={(e) => setBillingForm({ ...billingForm, billing_type: e.target.value })} className="mt-1 w-full h-10 px-3 border border-border rounded-medium bg-surface text-xs">
                <option value="PIX">PIX</option>
                <option value="BOLETO">Boleto</option>
                <option value="CREDIT_CARD">Cartão de crédito</option>
                <option value="UNDEFINED">Cliente escolhe</option>
              </select>
            </label>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setBillingTenant(null)} className="h-10 px-4 border border-border rounded-medium text-xs font-semibold">Cancelar</button>
              <button type="submit" className="h-10 px-4 bg-accent text-white rounded-medium text-xs font-semibold">Criar assinatura</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
};

const Modal: React.FC<{ title: string; children: React.ReactNode; onClose: () => void }> = ({ title, children, onClose }) => (
  <div className="fixed inset-0 bg-text-primary/20 backdrop-blur-xs z-50 flex items-center justify-center p-4">
    <div className="bg-surface border border-border rounded-large shadow-large w-full max-w-2xl p-5">
      <div className="flex items-center justify-between border-b border-border pb-3 mb-4">
        <h2 className="font-bold">{title}</h2>
        <button onClick={onClose} className="text-text-secondary text-sm font-semibold">Fechar</button>
      </div>
      {children}
    </div>
  </div>
);

const Input: React.FC<{ label: string; value: string; onChange: (value: string) => void; required?: boolean; type?: string }> = ({ label, value, onChange, required, type = 'text' }) => (
  <label className="block">
    <span className="text-xs font-bold text-text-secondary uppercase">{label}</span>
    <input
      type={type}
      required={required}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="mt-1 w-full h-10 px-3 border border-border rounded-medium bg-surface text-text-primary text-xs focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15"
    />
  </label>
);
