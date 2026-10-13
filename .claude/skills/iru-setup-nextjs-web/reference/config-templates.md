# Configuration templates (Steps 4–8)

Same `File:` / `when:` convention as `app-router-samples.md`. Extra tags used here:

| Tag | Applies when |
|---|---|
| `app` / `pages` | `router: app` / `router: pages` |
| `server` / `static` | `output: server` / `output: static` |
| `cc` | `cache-components: yes` |
| `internal` | `output: server` **and** `distribution: internal` (container image) |
| `e2e` | `e2e: playwright` |
| `typedoc` | `docs-tool: typedoc` |
| `sonar` | `sonar: cloud` or `self-hosted` |

## `next.config.ts` (Step 4)

Replace the scaffold's `next.config.ts`, **keeping** whatever `create-next-app` itself put there for the chosen
styling (16.4's Tailwind setup writes a `turbopack.rules` block for `@tailwindcss/turbopack` — merge it into the
object below rather than dropping it; with `--no-tailwind` there is nothing to keep). `--cache-components` writes
`cacheComponents: true` plus `partialPrefetching: true`; keep both exactly as written when `cache-components: yes`.

File: `next.config.ts` — when: `server`, `!internal`

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
};

export default nextConfig;
```

File: `next.config.ts` — when: `internal`

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server in .next/standalone for the Docker image (Step 8).
  output: "standalone",
  poweredByHeader: false,
};

export default nextConfig;
```

File: `next.config.ts` — when: `static`

```ts
import type { NextConfig } from "next";

// Set by the GitHub Pages deploy job (actions/configure-pages `base_path`): "/<repository>" for a project site,
// empty for <owner>.github.io or a custom domain. Unset locally and in tests, so the app serves from "/".
const basePath = process.env.PAGES_BASE_PATH ?? "";

const nextConfig: NextConfig = {
  output: "export",
  basePath,
  // The default image optimizer needs a server; an export must ship images as-is.
  images: { unoptimized: true },
  // Writes books/index.html instead of books.html, which every static host resolves for /books/.
  trailingSlash: true,
  // <Link>, router navigation and /_next assets get basePath automatically; next/image `src` strings and raw
  // public/ URLs do not — prefix those with process.env.NEXT_PUBLIC_BASE_PATH.
  env: { NEXT_PUBLIC_BASE_PATH: basePath },
};

export default nextConfig;
```

`assetPrefix` is deliberately not set: `basePath` already prefixes `/_next/` assets, and `assetPrefix` is only for
serving those assets from a different origin (a CDN).

## Unit tests — Vitest (Step 5)

File: `vitest.config.mts`

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  // Vite 8 resolves the tsconfig "paths" alias (@/*) natively.
  resolve: { tsconfigPaths: true },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    setupFiles: ["./vitest.setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov", "json-summary"],
      reportsDirectory: "coverage",
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.test.{ts,tsx}",
        "src/**/*.d.ts",
        // Framework wiring: next/font and <html>/<body> can't render under jsdom; `next build` and the
        // Playwright suite exercise it.
        "src/app/layout.tsx",
        "src/pages/_app.tsx",
        "src/pages/_document.tsx",
      ],
      thresholds: { lines: 80, branches: 80, functions: 80, statements: 80 },
    },
  },
});
```

File: `vitest.setup.ts`

```ts
import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// The real package throws outside a React Server environment; Server Component modules import it.
vi.mock("server-only", () => ({}));

// Client hooks need a mounted App Router; tests override this with their own vi.mock when they assert calls.
vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));

afterEach(() => {
  cleanup();
});
```

`notFound()`/`redirect()` stay real (spread from `importOriginal`), so tests assert their `digest`
(`NEXT_HTTP_ERROR_FALLBACK;404`, `NEXT_REDIRECT;...`) as `iru-nextjs-code-one-task/reference/testing.md` describes.

## Lint and format (Step 6)

File: `eslint.config.mjs`

```js
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import prettier from "eslint-config-prettier/flat";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Last, so formatting rules that would fight Prettier are switched off.
  prettier,
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Generated reports and docs:
    "coverage/**",
    "playwright-report/**",
    "test-results/**",
    "docs/**",
  ]),
]);

export default eslintConfig;
```

File: `.prettierrc.json`

```json
{
  "printWidth": 100
}
```

File: `.prettierignore`

```
.next
out
build
coverage
playwright-report
test-results
docs
next-env.d.ts
package-lock.json
pnpm-lock.yaml
# Rewritten by `next dev` (create-next-app's agent rules block) — formatting it only creates churn.
AGENTS.md
CLAUDE.md
```

## Playwright (Step 7)

The `webServer` always runs the **production** build (never `next dev`), and under `CI` never reuses a server
already listening on the port. Port 3100 keeps it clear of a developer's `next dev` on 3000.

File: `playwright.config.ts` — when: `e2e`, `server`

```ts
import { defineConfig, devices } from "@playwright/test";

const port = Number(process.env.E2E_PORT ?? 3100);
const baseURL = `http://localhost:${port}`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: { baseURL, trace: "on-first-retry" },
  // Chromium only: `npx playwright install --with-deps chromium` is what CI provisions.
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `npm run build && npm run start -- --port ${port}`,
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 240_000,
  },
});
```

File: `playwright.config.ts` — when: `e2e`, `static`

```ts
import { defineConfig, devices } from "@playwright/test";

const port = Number(process.env.E2E_PORT ?? 3100);
const baseURL = `http://localhost:${port}`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: { baseURL, trace: "on-first-retry" },
  // Chromium only: `npx playwright install --with-deps chromium` is what CI provisions.
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    // The static export served as files, exactly as Pages serves it (PAGES_BASE_PATH unset => root).
    command: `npm run build && npm run start -- --listen ${port}`,
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 240_000,
  },
});
```

Replace `npm run` with `pnpm run`/`yarn` per `package-manager`.

## TypeDoc (Step 8, `docs-tool: typedoc`)

File: `typedoc.json` — when: `typedoc`

```json
{
  "$schema": "https://typedoc.org/schema.json",
  "entryPoints": ["src"],
  "entryPointStrategy": "expand",
  "exclude": ["**/*.test.ts", "**/*.test.tsx"],
  "out": "docs/api",
  "name": "<App title> API",
  "validation": { "notExported": false }
}
```

`validation.notExported: false` is required on Next.js: the global `PageProps`/`LayoutProps`/`RouteContext` helpers
live in `.next/types/routes.d.ts` and TypeDoc otherwise warns that they are referenced but not documented.

## Sonar (Step 8, `sonar` ≠ `none`)

File: `sonar-project.properties` — when: `sonar`

```properties
sonar.organization=<sonar-organization>
sonar.projectKey=<sonar-project-key>
sonar.host.url=<sonar-host-url>
sonar.sources=src
sonar.tests=src
sonar.test.inclusions=**/*.test.ts,**/*.test.tsx
sonar.exclusions=**/node_modules/**,**/.next/**,**/out/**
sonar.coverage.exclusions=src/app/layout.tsx,src/pages/_app.tsx,src/pages/_document.tsx
sonar.javascript.lcov.reportPaths=coverage/lcov.info
```

Omit `sonar.organization` for a self-hosted server without organizations. `sonar.coverage.exclusions` mirrors the
Vitest `coverage.exclude` wiring files so Sonar and the local gate agree.

## Container image (Step 8, `internal`)

File: `Dockerfile` — when: `internal`

```dockerfile
# syntax=docker/dockerfile:1
ARG NODE_VERSION=24

FROM node:${NODE_VERSION}-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:${NODE_VERSION}-slim AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:${NODE_VERSION}-slim AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
# The standalone server plus the assets it does not copy itself, owned by the image's non-root `node` user so
# the server can write its .next/cache (ISR, image cache).
COPY --from=builder --chown=node:node /app/public ./public
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:' + process.env.PORT + '/api/health').then((r) => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"]
CMD ["node", "server.js"]
```

`<package-manager>` other than npm: copy `pnpm-lock.yaml`/`yarn.lock` instead and run `corepack enable &&
pnpm install --frozen-lockfile` (or `yarn install --immutable`) in `deps`, `pnpm run build`/`yarn build` in
`builder` (unverified here — only npm was exercised). `NODE_VERSION` defaults to the resolved `node-version`.

File: `.dockerignore` — when: `internal`

```
.git
.github
node_modules
.next
out
coverage
playwright-report
test-results
docs
e2e
.env*
!.env.example
Dockerfile
.dockerignore
*.md
```
