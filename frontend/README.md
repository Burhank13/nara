# MAF frontend

React 19 + Vite + Tailwind v4 + TanStack Query. One responsive app serving all three roles.

Setup, and how to run this alongside the API, is in the [repository README](../README.md).
Conventions for working in here are in [CONTRIBUTING.md](../CONTRIBUTING.md#frontend).

```bash
npm run dev      # dev server on :5173, proxies /api to localhost:8000
npm run build    # tsc -b, then vite build
npm run lint     # oxlint
npm run e2e      # Playwright, desktop + 390px phone; needs the API and dev server up
```
