const { createRequire } = require('node:module');
const { spawn, execFileSync } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const runtimeRequire = createRequire('C:/Users/marce/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/package.json');
const { chromium } = runtimeRequire('playwright');
const python = 'C:/Users/marce/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';

(async () => {
  const root = path.resolve(__dirname, '..');
  const temp = fs.mkdtempSync(path.join(__dirname, 'profiles-ui-'));
  const evidence = path.join(__dirname, 'evidencias-perfis');
  fs.mkdirSync(evidence, { recursive: true });
  const env = { ...process.env, ESTUDO_DB: path.join(temp, 'study.sqlite') };
  execFileSync(python, ['-c', 'import server,roadmap; server.init_db(); roadmap.install(server.STUDY_DB)'], { cwd: root, env });
  const child = spawn(python, ['-u', 'server.py', '--port', '8877'], { cwd: root, env, windowsHide: true, stdio: 'ignore' });
  let browser;
  try {
    const url = 'http://127.0.0.1:8877';
    let ready = false;
    for (let i = 0; i < 60; i++) {
      try { if ((await fetch(url + '/api/health')).ok) { ready = true; break; } } catch {}
      await new Promise(resolve => setTimeout(resolve, 250));
    }
    assert.ok(ready, 'Temporary server must start');
    browser = await chromium.launch({ headless: true, executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe' });
    const context = await browser.newContext({ viewport: { width: 1280, height: 1000 } });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(url);
    const selector = page.getByRole('combobox', { name: 'Perfil de estudo', exact: true });
    await selector.waitFor();
    assert.equal(await selector.inputValue(), 'principal');
    await page.getByRole('button', { name: '+ Criar perfil', exact: true }).click();
    await page.getByLabel('Nome do perfil', { exact: true }).fill('Meu estudo');
    await page.getByRole('button', { name: 'Criar perfil', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('[aria-label="Perfil de estudo"] select')?.value !== 'principal');
    await page.waitForFunction(() => !document.querySelector('main').hasAttribute('inert'));
    const profile = await selector.inputValue();
    assert.equal(await selector.locator('option:checked').innerText(), 'Meu estudo');
    async function toggleFirst() {
      await Promise.all([
        page.waitForResponse(r => r.url().endsWith('/api/bootstrap') && r.ok()),
        page.locator('.plan-activity input').first().click(),
      ]);
      await page.waitForFunction(() => document.querySelector('.plan-activity input')?.checked);
    }
    async function switchTo(id) {
      await Promise.all([
        page.waitForResponse(r => r.url().endsWith('/api/bootstrap') && r.ok()),
        selector.selectOption(id),
      ]);
      await page.waitForFunction(value => document.querySelector('main')?.getAttribute('inert') === null && document.querySelector('[aria-label="Perfil de estudo"] select')?.value === value, id);
    }
    await toggleFirst();
    await page.reload();
    await selector.waitFor();
    assert.equal(await selector.inputValue(), profile);
    assert.ok(await page.locator('.plan-activity input').first().isChecked());
    await switchTo('principal');
    assert.equal(await page.locator('.plan-activity input').first().isChecked(), false);
    await toggleFirst();
    await switchTo(profile);
    await page.locator('.daily-unit').first().getByRole('button', { name: 'Estudar', exact: true }).click();
    await page.getByLabel('Despejo livre', { exact: true }).waitFor();
    assert.ok(await selector.isDisabled());
    const saved = page.waitForResponse(r => r.url().endsWith('/state') && r.request().method() === 'PUT' && r.ok());
    await page.getByLabel('Despejo livre', { exact: true }).fill('Anotação do meu perfil');
    const save = await saved;
    assert.equal(save.request().headers()['x-study-profile'], profile);
    await page.getByRole('button', { name: 'Salvar e sair da sessão', exact: true }).click();
    await page.getByRole('heading', { name: 'Roadmap · APOFP SP', exact: true }).waitFor();
    const reset = page.getByRole('button', { name: 'Resetar progresso do roadmap', exact: true });
    await reset.click();
    assert.match(await page.getByRole('dialog').innerText(), /Meu estudo/);
    await page.getByRole('button', { name: 'Cancelar', exact: true }).click();
    assert.ok(await page.locator('.plan-activity input').first().isChecked());
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(evidence, 'perfis-desktop.png'), fullPage: false });
    await reset.click();
    await page.getByRole('button', { name: 'Confirmar reset', exact: true }).click();
    await page.getByText('O roadmap de Meu estudo foi resetado.', { exact: false }).waitFor();
    assert.equal(await page.locator('.plan-activity input').first().isChecked(), false);
    assert.equal(await page.locator('.resume-card').count(), 0);
    await switchTo('principal');
    assert.ok(await page.locator('.plan-activity input').first().isChecked());
    await switchTo(profile);
    // Another tab changing the profile cannot redirect writes from this tab.
    const other = await context.newPage();
    await other.goto(url);
    await other.getByRole('combobox', { name: 'Perfil de estudo', exact: true }).selectOption('principal');
    await other.waitForFunction(() => !document.querySelector('main').hasAttribute('inert'));
    const [activitySave] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/api/roadmap/activities/') && r.ok()),
      toggleFirst(),
    ]);
    assert.equal(activitySave.request().headers()['x-study-profile'], profile);
    await other.close();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.evaluate(() => window.scrollTo(0, 0));
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: path.join(evidence, 'perfis-mobile.png'), fullPage: false });
    await reset.click();
    assert.ok(await page.evaluate(() => document.querySelector('dialog').getBoundingClientRect().right <= innerWidth));
    await page.screenshot({ path: path.join(evidence, 'reset-mobile.png'), fullPage: false });
    await page.keyboard.press('Escape');
    await page.getByRole('button', { name: 'Usar tema escuro', exact: true }).click();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(evidence, 'perfis-dark.png'), fullPage: false });
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ ok: true, checks: ['create profile', 'independent progress', 'reload persistence', 'session autosave', 'cancel reset', 'scoped reset', 'two-tab isolation', 'mobile layout and dialog', 'dark theme', 'no browser errors'], evidence }));
  } finally {
    if (browser) await browser.close();
    child.kill();
    if (child.exitCode === null) await new Promise(resolve => child.once('exit', resolve));
    if (path.dirname(temp) !== __dirname || !path.basename(temp).startsWith('profiles-ui-')) throw new Error('Unexpected temporary folder');
    fs.rmSync(temp, { recursive: true, force: true });
  }
})().catch(e => { console.error(e); process.exitCode = 1; });
