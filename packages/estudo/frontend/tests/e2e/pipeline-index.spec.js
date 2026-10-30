import { readFile } from 'node:fs/promises';
import { test, expect } from '@playwright/test';

test('índice do pipeline apresenta texto sem interpretar HTML ou URLs executáveis', async ({ page }) => {
  const template = await readFile(new URL('../../../../pipeline/src/concurso_pipeline/templates/index.html', import.meta.url), 'utf8');
  const record = {
    tipo: 'Questão', numero: '1', titulo: 'Prova sintética', banca: 'Teste', concurso: 'Teste',
    texto: '<img src=x onerror="window.injected=true">', paginas: [1], status: 'extraido',
    pdf: 'javascript:window.injected=true', imagens: ['data:text/html,<script>window.injected=true</script>'],
    gabaritos: [{ resposta: 'A', situacao: 'valido', natureza: 'definitivo', pdf: 'javascript:window.injected=true' }],
  };
  const data = JSON.stringify([record]).replaceAll('<', '\\u003c');
  const report = JSON.stringify({ ocorrencias_questoes: 1, provas: 1, questoes_unicas: 1, topicos: 0 });
  const html = template.replace('DATA_PLACEHOLDER', data).replace('REPORT_PLACEHOLDER', report);
  await page.route('**/pipeline-index', route => route.fulfill({ contentType: 'text/html', body: html }));
  await page.goto('/pipeline-index');
  await expect(page.locator('article pre').first()).toHaveText(record.texto);
  await expect(page.getByRole('link', { name: 'Abrir PDF original' })).toHaveAttribute('href', '#');
  await expect(page.locator('article a').first()).toHaveAttribute('href', '#');
  await expect(page.locator('article img')).toHaveAttribute('src', '#');
  expect(await page.evaluate(() => window.injected)).toBeUndefined();
});
