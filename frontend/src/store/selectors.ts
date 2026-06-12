import type { AppState } from './useStore';

// Data Selectors
export const selectUser = (state: AppState) => state.user;
export const selectIsAuthenticated = (state: AppState) => state.isAuthenticated;
export const selectActiveTab = (state: AppState) => state.activeTab;
export const selectTenant = (state: AppState) => state.tenant;
export const selectDashboard = (state: AppState) => state.dashboard;
export const selectClientes = (state: AppState) => state.clientes;
export const selectAtendimentos = (state: AppState) => state.atendimentos;
export const selectAprovacoes = (state: AppState) => state.aprovacoes;
export const selectServicos = (state: AppState) => state.servicos;
export const selectListaEspera = (state: AppState) => state.listaEspera;
export const selectConfiguracoes = (state: AppState) => state.configuracoes;
export const selectRoiStats = (state: AppState) => state.roiStats;

// Loading & Error Selectors
export const selectLoading = (state: AppState) => state.loading;
export const selectError = (state: AppState) => state.error;

// Auth Action Selectors
export const selectSetUser = (state: AppState) => state.setUser;
export const selectSetActiveTab = (state: AppState) => state.setActiveTab;
export const selectSetError = (state: AppState) => state.setError;
export const selectLogin = (state: AppState) => state.login;
export const selectLogout = (state: AppState) => state.logout;
export const selectCheckAuth = (state: AppState) => state.checkAuth;

// Data Fetching Action Selectors
export const selectFetchDashboard = (state: AppState) => state.fetchDashboard;
export const selectFetchClientes = (state: AppState) => state.fetchClientes;
export const selectFetchAtendimentos = (state: AppState) => state.fetchAtendimentos;
export const selectFetchAprovacoes = (state: AppState) => state.fetchAprovacoes;
export const selectFetchServicos = (state: AppState) => state.fetchServicos;
export const selectFetchListaEspera = (state: AppState) => state.fetchListaEspera;
export const selectFetchConfiguracoes = (state: AppState) => state.fetchConfiguracoes;
export const selectFetchROI = (state: AppState) => state.fetchROI;
export const selectProcessarAprovacao = (state: AppState) => state.processarAprovacao;

// Mutation Action Selectors
export const selectUpdateAtendimentoStatus = (state: AppState) => state.updateAtendimentoStatus;
export const selectAprovarPedido = (state: AppState) => state.aprovarPedido;
export const selectRecusarPedido = (state: AppState) => state.recusarPedido;
export const selectCreateAtendimento = (state: AppState) => state.createAtendimento;
export const selectCreateCliente = (state: AppState) => state.createCliente;
export const selectDeleteClienteLGPD = (state: AppState) => state.deleteClienteLGPD;
export const selectCreateServico = (state: AppState) => state.createServico;
export const selectUpdateServico = (state: AppState) => state.updateServico;
export const selectAddListaEspera = (state: AppState) => state.addListaEspera;
export const selectOferecerListaEspera = (state: AppState) => state.oferecerListaEspera;
export const selectDeleteListaEspera = (state: AppState) => state.deleteListaEspera;
export const selectUpdateConfiguracoes = (state: AppState) => state.updateConfiguracoes;
export const selectSetTenantActive = (state: AppState) => state.setTenantActive;
