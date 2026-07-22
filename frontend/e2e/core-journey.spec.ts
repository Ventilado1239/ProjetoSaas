import { expect, test, type Page } from '@playwright/test';

const user = {
  id: '10000000-0000-0000-0000-000000000001',
  tenant_id: '20000000-0000-0000-0000-000000000002',
  nome: 'Dono E2E',
  email: 'dono@example.com',
  perfil: 'dono',
};

const configuration = {
  id: '30000000-0000-0000-0000-000000000003',
  tenant_id: user.tenant_id,
  tenant_nome: 'Loja E2E',
  tenant_tipo: 'loja',
  tenant_cor_primaria: '#2563eb',
  limite_pedido_grande: 10,
  sistema_ativo: true,
  owner_whatsapp: '5511999999999',
  evolution_instance_name: 'loja-e2e',
};

const dashboard = {
  atendimentos_total: 1,
  atendimentos_confirmados: 0,
  aprovacoes_pendentes: 1,
  receita_total: 120,
  receita_paga: 0,
  receita_pendente: 120,
  atendimentos: [],
};

async function mockApi(page: Page) {
  let clients: unknown[] = [];
  let operators = [{ ...user, ativo: true }];
  await page.route(/:\/\/[^/]+:8000\//, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();
    let status = 200;
    let body: unknown = {};

    if (path === '/auth/login' && method === 'POST') body = { user };
    else if (path === '/auth/me') body = user;
    else if (path === '/configuracoes') body = configuration;
    else if (path === '/dashboard/hoje') body = dashboard;
    else if (path === '/clientes' && method === 'GET') body = clients;
    else if (path === '/clientes' && method === 'POST') {
      const input = request.postDataJSON();
      const created = {
        ...input,
        id: '40000000-0000-0000-0000-000000000004',
        tenant_id: user.tenant_id,
        total_atendimentos: 0,
        ticket_medio: 0,
        status_reativacao: 'ativo',
      };
      clients = [created];
      status = 201;
      body = created;
    } else if (path === '/usuarios' && method === 'GET') body = operators;
    else if (path === '/usuarios' && method === 'POST') {
      const input = request.postDataJSON();
      const created = {
        id: '50000000-0000-0000-0000-000000000005',
        nome: input.nome,
        email: input.email,
        perfil: input.perfil,
        ativo: true,
      };
      operators = [...operators, created];
      status = 201;
      body = created;
    } else if (path.startsWith('/usuarios/') && method === 'DELETE') {
      operators = operators.filter(item => !path.endsWith(item.id));
      status = 204;
      body = '';
    } else if (path === '/atendimentos/aprovacoes') body = [];
    else if (path === '/atendimentos') body = [];
    else if (path === '/servicos') body = [];
    else if (path === '/lista-espera') body = [];
    else if (path === '/dashboard/roi') {
      body = {
        taxa_comparecimento: 100,
        receita_total: 120,
        receita_perdida: 0,
        reativados_count: 0,
        lista_espera_agendados: 0,
        impacto_total: 0,
        mensalidade: 199,
        roi: 0,
      };
    } else if (path === '/auth/logout') body = { status: 'success' };

    await route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(body),
    });
  });
}

test.beforeEach(async ({ page }) => {
  await mockApi(page);
  await page.goto('/');
});

test('login, navigation and customer creation work without horizontal overflow', async ({ page, isMobile }, testInfo) => {
  await page.getByLabel('E-mail corporativo').fill('dono@example.com');
  await page.getByLabel('Senha de acesso').fill('SenhaForte2026');
  await page.getByRole('button', { name: 'Entrar no Painel', exact: true }).click();

  await expect(page.getByRole('heading', { name: 'Visão Geral' })).toBeVisible();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);

  if (isMobile) {
    await page.getByRole('button', { name: 'Clientes' }).click();
  } else {
    await page.getByRole('button', { name: 'Clientes', exact: true }).click();
  }
  await expect(page.getByRole('heading', { name: 'Clientes' })).toBeVisible();
  await page.getByRole('button', { name: 'Cadastrar Novo' }).click();
  await page.getByLabel('Nome Completo').fill('Cliente Browser');
  await page.getByLabel(/WhatsApp/).fill('5511987654321');
  await page.getByRole('button', { name: 'Salvar Cadastro' }).click();
  await expect(page.getByText('Cliente Browser')).toBeVisible();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath('customer-journey.png'), fullPage: true });
});

test('mobile secondary navigation is keyboard and screen-reader reachable', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'Fluxo específico da navegação móvel');
  await page.getByLabel('E-mail corporativo').fill('dono@example.com');
  await page.getByLabel('Senha de acesso').fill('SenhaForte2026');
  await page.getByRole('button', { name: 'Entrar no Painel', exact: true }).click();
  await page.getByRole('button', { name: 'Abrir menu' }).click();
  await expect(page.getByRole('dialog', { name: 'Mais opções' })).toBeVisible();
  await page.getByRole('button', { name: 'Configurações' }).click();
  await expect(page.getByRole('heading', { name: 'Configurações Gerais' })).toBeVisible();
});

test('owner creates and deactivates a persisted operator', async ({ page, isMobile }) => {
  await page.getByLabel('E-mail corporativo').fill('dono@example.com');
  await page.getByLabel('Senha de acesso').fill('SenhaForte2026');
  await page.getByRole('button', { name: 'Entrar no Painel', exact: true }).click();

  if (isMobile) {
    await page.getByRole('button', { name: 'Abrir menu' }).click();
    await page.getByRole('button', { name: 'Configurações' }).click();
  } else {
    await page.getByRole('button', { name: 'Configurações' }).click();
  }
  await page.getByRole('button', { name: '+ Convidar' }).click();
  await page.getByLabel('Nome Completo').fill('Operador Browser');
  await page.getByLabel('E-mail Corporativo').fill('operador.browser@example.com');
  await page.getByLabel('Senha Provisória').fill('OperadorBrowser2026');
  await page.getByLabel('Perfil / Permissões').selectOption('recepcionista');
  await page.getByRole('button', { name: 'Criar Cadastro' }).click();

  await expect(page.getByText('Operador Browser')).toBeVisible();
  await page.getByRole('button', { name: 'Desativar Operador Browser' }).click();
  await expect(page.getByText('Operador Browser')).toHaveCount(0);
});
