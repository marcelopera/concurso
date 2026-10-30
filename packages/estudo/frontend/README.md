# Frontend de estudo

React/Vite em [src/features/](src/features/), com [componentes compartilhados](src/components/) e [cliente HTTP](src/lib/api.js). O [backend](../backend/) é executado separadamente. Consulte o [README principal](../../../README.md).

Na raiz do repositório:

```sh
pnpm --dir packages/estudo/frontend install --frozen-lockfile
pnpm --dir packages/estudo/frontend dev
```

O Vite encaminha `/api` ao servidor local na porta 8765. `build` gera a interface em `data/frontend/`; `preview` a apresenta depois do build. `lint`, `test` e `test:e2e` executam ESLint, regressões da fila de gravação e Playwright. Os E2E exigem os pacotes Python instalados e criam uma aplicação com dados temporários.
