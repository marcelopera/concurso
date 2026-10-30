import { test, expect } from '@playwright/test';

test('perfil e catálogo de demonstração funcionam em uma instalação isolada', async ({ page }) => {
  await page.goto('/');
  const data = await (await page.request.get('/api/bootstrap')).json();
  await expect(page.getByRole('heading', { name: 'Roadmap · ' + data.roadmap.title })).toBeVisible();
  await page.getByRole('button', { name: '+ Criar perfil' }).click();
  await page.getByLabel('Nome do perfil').fill('Teste');
  await page.getByRole('button', { name: 'Criar perfil', exact: true }).click();
  await expect(page.getByRole('combobox', { name: 'Perfil de estudo' })).not.toHaveValue('principal');
  await page.getByRole('button', { name: 'Questões livres' }).click();
  await expect(page.getByRole('heading', { name: 'Questões livres' })).toBeVisible();
  await expect(page.getByText(/Questão de demonstração 1:/).first()).toBeVisible();
});

test('sessão usa as etapas fornecidas pelo servidor e mantém o estado', async ({ page, request }) => {
  const bootstrap = await (await request.get('/api/bootstrap')).json();
  const created = await request.post('/api/lessons/apofp26_a01_01/sessions', { data: {} });
  expect(created.ok()).toBeTruthy();
  await page.goto('/');
  await expect(page.getByRole('heading', { name: bootstrap.steps[0].title })).toBeVisible();
  await page.getByPlaceholder('O que você lembra da aula anterior…').fill('Anotação persistida no teste');
  await expect(page.getByText('Salvo automaticamente')).toBeVisible();
  await page.getByRole('button', { name: 'Continuar' }).click();
  await expect(page.getByRole('heading', { name: bootstrap.steps[1].title })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: bootstrap.steps[1].title })).toBeVisible();
  await page.getByRole('button', { name: 'Voltar', exact: true }).click();
  await expect(page.getByPlaceholder('O que você lembra da aula anterior…')).toHaveValue('Anotação persistida no teste');
});

test('quadro carrega sob demanda usando somente recursos locais', async ({ page, request }) => {
  const profile = await (await request.post('/api/profiles', { data: { name: 'Quadro offline' } })).json();
  const headers = { 'X-Study-Profile': profile.id };
  const session = await (await request.post('/api/lessons/apofp26_a01_01/sessions', { headers, data: {} })).json();
  const advanced = await request.post(`/api/sessions/${session.session_id}/step`, { headers, data: { step: 3 } });
  expect(advanced.ok()).toBeTruthy();
  await page.addInitScript((id) => localStorage.setItem('study-profile', id), profile.id);
  const external = [];
  page.on('request', (req) => { if (/^https?:/.test(req.url()) && new URL(req.url()).origin !== 'http://127.0.0.1:8877') external.push(req.url()); });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Whiteboard', exact: true })).toBeVisible();
  await expect(page.locator('.excalidraw canvas').first()).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  expect(external).toEqual([]);
});

test('desenho permanece ao retomar e ao iniciar outra sessão da aula', async ({ page, request }) => {
  const profile = await (await request.post('/api/profiles', { data: { name: 'Persistência do quadro' } })).json();
  const headers = { 'X-Study-Profile': profile.id };
  const session = await (await request.post('/api/lessons/apofp26_a01_01/sessions', { headers, data: {} })).json();
  await request.post(`/api/sessions/${session.session_id}/step`, { headers, data: { step: 3 } });
  await page.addInitScript((id) => localStorage.setItem('study-profile', id), profile.id);
  await page.goto('/');
  const canvas = page.locator('.excalidraw canvas').first();
  await expect(canvas).toBeVisible();
  await page.keyboard.press('r');
  const box = await canvas.boundingBox();
  await page.mouse.move(box.x + 200, box.y + 180);
  await page.mouse.down();
  await page.mouse.move(box.x + 350, box.y + 280, { steps: 10 });
  await page.mouse.up();
  await page.getByRole('button', { name: 'Salvar e sair da sessão' }).click();
  let resumed = await (await request.post('/api/lessons/apofp26_a01_01/sessions', { headers, data: {} })).json();
  expect(resumed.payload.boardScene.elements.filter((element) => !element.isDeleted)).toHaveLength(1);
  await page.reload();
  await expect(canvas).toBeVisible();
  await page.getByRole('button', { name: 'Salvar e sair da sessão' }).click();
  await request.post(`/api/sessions/${session.session_id}/complete`, { headers, data: {} });
  const next = await (await request.post('/api/lessons/apofp26_a01_01/sessions', { headers, data: {} })).json();
  expect(next.payload.boardScene.elements.filter((element) => !element.isDeleted)).toHaveLength(1);
  await request.post(`/api/sessions/${next.session_id}/step`, { headers, data: { step: 3 } });
  await page.reload();
  await expect(canvas).toBeVisible();
  await page.getByRole('button', { name: 'Salvar e sair da sessão' }).click();
  resumed = await (await request.post('/api/lessons/apofp26_a01_01/sessions', { headers, data: {} })).json();
  expect(resumed.payload.boardScene.elements.filter((element) => !element.isDeleted)).toHaveLength(1);
});

test('plano externo pode omitir fontes, marcos e regras específicas de prova', async ({ page, request }) => {
  const profile = await (await request.post('/api/profiles', { data: { name: 'Plano externo' } })).json();
  await page.addInitScript((id) => localStorage.setItem('study-profile', id), profile.id);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/api/bootstrap', async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    body.roadmap.title = 'Meu plano externo';
    for (const key of ['sources', 'sources_checked', 'milestones', 'scoring', 'board']) delete body.roadmap[key];
    await route.fulfill({ response, json: body });
  });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Roadmap · Meu plano externo' })).toBeVisible();
  await page.getByText('Estratégia de prova, marcos e fontes oficiais', { exact: true }).click();
  expect(errors).toEqual([]);
});
