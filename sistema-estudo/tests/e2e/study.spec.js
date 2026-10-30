import { test, expect } from '@playwright/test';

test('perfil e catálogo de demonstração funcionam em uma instalação isolada', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Roadmap · APOFP SP' })).toBeVisible();
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
  await page.getByRole('button', { name: 'Continuar' }).click();
  await expect(page.getByRole('heading', { name: bootstrap.steps[1].title })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: bootstrap.steps[1].title })).toBeVisible();
});
