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
