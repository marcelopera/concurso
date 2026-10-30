import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  use: { baseURL: 'http://127.0.0.1:8877', browserName: 'chromium' },
  webServer: {
    command: `${process.env.PYTHON || 'python'} scripts/servidor_e2e.py`,
    url: 'http://127.0.0.1:8877/api/health',
    reuseExistingServer: false,
    timeout: 30000,
  },
});
