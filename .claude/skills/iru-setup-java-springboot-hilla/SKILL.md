---
name: iru-setup-java-springboot-hilla
description: Scaffold a Hilla (Vaadin) React frontend into one module of an existing Spring Boot hexagonal reactor — the Vaadin BOM and `hilla-spring-boot-starter`/`vaadin-spring-boot-starter` dependencies, the `vaadin-maven-plugin` execution wired into that module's pom, `src/main/frontend/` (file-based-routing `views/@index.tsx` + `views/@layout.tsx`, a customized `index.html`), the module-root `vitest.config.ts` extending Vaadin's generated Vite config with `@vitest/coverage-v8` lcov output, a sample `@testing-library/react` test, `eslint.config.js` (flat config, `typescript-eslint` + `eslint-plugin-react-hooks` + `eslint-config-prettier`) plus `.prettierrc.json`/`.prettierignore`, `package.json` `test`/`coverage`/`lint`/`format` scripts, the `.gitignore` additions this frontend needs, and — only when the manifest's `sonar.mode` isn't `none` — the `sonar.sources`/`sonar.tests`/`sonar.javascript.lcov.reportPaths` additions to the root pom. Invoke as `/iru-setup-java-springboot-hilla`, optionally with `args` (a `stack-file` line naming the manifest path, default `springboot-stack.yml` at the repository root). Runs standalone against any reactor built by `iru-setup-java-springboot-modules`, or is invoked by `iru-setup-java-springboot`'s Step 8 (via `iru-isolated-skill-executor`) right after `iru-setup-java-springboot-apis` whenever the manifest's `frontend` is `hilla`. Reads `springboot-stack.yml` for the module layout and `sonar.mode`, and looks up the Vaadin BOM version and every npm devDependency version live (Maven Central and the npm registry) rather than from memory. The root pom's `vaadin.version` property, `dependencyManagement` import, `pluginManagement` entry, and `production` profile are primarily written by `iru-setup-java-springboot-pom` (see that skill) — this skill only fills that gap itself when running standalone against a reactor where it's missing. Use whenever a Spring Boot service needs its Hilla frontend module actually scaffolded, instead of hand-wiring the Vaadin/Hilla Maven and npm toolchains file by file.
model: haiku
---

# Setup Java Spring Boot Hilla Frontend

Scaffold a Hilla React frontend into the module of a Spring Boot hexagonal reactor that runs the web server. Two
things about Hilla in the Vaadin 25.x line are easy to get wrong and were confirmed empirically while writing this
skill (a real Spring Boot 4 + Hilla project was built and run end to end — the same verification this skill's own
Step 8 repeats on every future run):

1. **`com.vaadin:hilla-spring-boot-starter` alone does not build.** Even a frontend with zero server-side Flow
   `@Route` views still ships an auto-generated Flow compatibility shim
   (`src/main/frontend/generated/flow/Flow.tsx`) that imports a Flow client resource
   (`Frontend/generated/jar-resources/Flow.js`) which is only present when `com.vaadin:vaadin-spring-boot-starter`
   is also on the classpath. Without it, `vaadin:build-frontend` fails at the Vite step with
   `Cannot find module 'Frontend/generated/jar-resources/Flow.js'`. **Always add both starters** — the "Flow
   views" question in Step 1 decides only whether example Flow `@Route` Java views are scaffolded, not whether the
   dependency is present.
2. **`routes.tsx` is generated, never hand-written.** Hilla 25's file-based router derives
   `src/main/frontend/generated/routes.tsx` and `generated/file-routes.ts` from whatever `.tsx`/`.jsx` files exist
   under `src/main/frontend/views/`, every time `vaadin:prepare-frontend`/`build-frontend` runs. This skill writes
   `views/@index.tsx` and `views/@layout.tsx` only — never `routes.tsx` itself, and never anything under
   `src/main/frontend/generated/`.

## Step 0 — Resolve inputs

Parse `args` for `key: value` lines:

```
stack-file: springboot-stack.yml
```

`stack-file` defaults to `springboot-stack.yml` at the repository root. Read it in full. Stop and tell the user to
run `/iru-setup-java-springboot` (or `/iru-setup-java-springboot-modules`) first if it doesn't exist — this skill
doesn't scaffold a reactor from nothing, only a frontend into one that already exists. Confirm `frontend: hilla` is
actually set; if it's `none`, ask via `AskUserQuestion` whether to proceed anyway (the user may be adding a
frontend after the fact) or stop, and if proceeding, update the manifest's `frontend:` field to `hilla` before
writing anything else, so a later re-run of `iru-setup-java-springboot` sees the choice that was actually made.

## Step 1 — Survey

- **The web module.** This catalog's reactor runs the `@SpringBootApplication` class and packages the executable
  jar in the `boot` module (see `iru-setup-java-springboot`'s module table) — that is also the module
  `spring-boot-maven-plugin`'s `repackage` goal runs in, and Vaadin's `build-frontend` must run in the module that
  produces the boot jar, since the production Vite bundle is written under that module's
  `target/classes/META-INF/VAADIN/`. Unless the manifest's `modules:` list is missing `boot` (report this as a
  blocker — it means `iru-setup-java-springboot-modules` hasn't run yet), **`boot` is the web module** this skill
  writes into. This was checked against `iru-setup-java-springboot-pom`'s own module table (`boot` is "every other
  module, `spring-boot-starter`... the only module with `spring-boot-maven-plugin`") and confirmed against the
  official `vaadin/skeleton-starter-hilla-react` reference project, whose single module plays exactly this role.
- **The root pom.** Check whether `<vaadin.version>`, the `vaadin-bom` `dependencyManagement` import, the
  `vaadin-maven-plugin` `pluginManagement` entry, and a `production` profile already exist (written by
  `iru-setup-java-springboot-pom` — see that skill's Step 1). If they do, use the existing `<vaadin.version>`
  as-is rather than re-resolving it, so the module and root stay on one version. **If they don't** (this skill is
  running standalone, or the root pom predates that skill's Hilla support), write them yourself now, following
  exactly the fragment `iru-setup-java-springboot-pom` documents, and say so in the final report so the user knows
  the root pom was touched by this skill rather than its usual owner.
- **Existing frontend.** Check for `<web-module>/src/main/frontend/`, `<web-module>/vitest.config.ts`,
  `<web-module>/eslint.config.js`, and an existing `com.vaadin:hilla-spring-boot-starter`/
  `vaadin-spring-boot-starter` dependency in `<web-module>/pom.xml`. If any exist, use `AskUserQuestion` (max four
  options: **stop**, **update — fill gaps only**, **update — regenerate the sample view/test**, **regenerate
  everything**) rather than overwriting hand-written frontend code by default. "Fill gaps only" preserves every
  file already present and only adds what's missing.
- **Look up current versions**, and record what you resolved for Step "Report":
  - `com.vaadin:vaadin-bom` — `https://repo1.maven.org/maven2/com/vaadin/vaadin-bom/maven-metadata.xml`. Use the
    `<release>` version (skip any `-alpha`/`-beta`/`-rc` suffix even if it's newer — an RC line is not what a
    service scaffold should default to). At the time this skill was written, `<release>` briefly pointed at a
    `-rc1` build; if that's still true, use the newest version in `<versions>` **without** a pre-release suffix
    instead of trusting `<release>`/`<latest>` blindly. Recorded fallback: **`25.2.8`**.
  - Every npm devDependency below — `https://registry.npmjs.org/<package>/latest`. Two npm-specific traps, both
    hit while verifying this skill, worth checking for on every run:
    - `@eslint/js` is versioned independently of `eslint` itself (e.g. `eslint@10.10.0` next to `@eslint/js@10.0.1`
      at the time of writing) — never assume the two version numbers match.
    - A single `npm view <pkg>@latest` can return a stale cached answer; if an `npm install` then reports an
      `ERESOLVE` peer conflict against the version you resolved, re-resolve from the failing install's own error
      message (it names the actual peer range) rather than retrying the same lookup.
  - Recorded fallbacks (all current at the time this skill was written and mutually compatible — verified by an
    actual `npm install` + `npx eslint`/`npx prettier --check`/`npx vitest run --coverage` run): `eslint@10.10.0`,
    `@eslint/js@10.0.1`, `typescript-eslint@8.70.0`, `eslint-plugin-react-hooks@7.1.1`,
    `eslint-config-prettier@10.1.8`, `prettier@3.9.7`, `vitest@5.0.1`, `@vitest/coverage-v8@5.0.1` (must match
    `vitest`'s own version), `@testing-library/react@16.3.3`, `@testing-library/jest-dom@7.0.1`, `jsdom@30.0.1`.
- **Node.** Confirm `node`/`npm`/`npx` are on `PATH` and report the version found. `vaadin:prepare-frontend` uses a
  globally installed Node when one satisfies its minimum version requirement (confirmed: it logged
  `Using globally installed Node.js version 24.16.0` rather than downloading one) and only downloads its own copy
  into `~/.vaadin` when no usable global Node exists — mention whichever happened in the report, since the
  download adds real time to a first CI run.
- **Flow views** (`AskUserQuestion`, default **No**) — does this service want hand-written server-side Flow
  `@Route` views alongside the Hilla React ones? Default is No (a pure-React Hilla frontend). This only decides
  whether Step 3 also scaffolds an example `@Route` Java class — `vaadin-spring-boot-starter` is added either way,
  per the "always add both starters" finding above.

## Step 2 — Module pom: dependencies and plugin execution

Add to `<web-module>/pom.xml` (`boot/pom.xml` unless Step 1 found otherwise). No `<version>` on any of these — they
resolve through the root pom's `dependencyManagement`/`pluginManagement`, exactly like every other module in this
reactor.

```xml
<dependencies>
  <!-- ... existing boot module dependencies ... -->

  <!-- Hilla (React endpoints/file-router) needs vaadin-spring-boot-starter too: the auto-generated Flow
       compatibility shim under src/main/frontend/generated/flow/ always references a Flow client resource
       that only vaadin-spring-boot-starter provides, even when no @Route Flow view is ever written. -->
  <dependency>
    <groupId>com.vaadin</groupId>
    <artifactId>vaadin-spring-boot-starter</artifactId>
  </dependency>
  <dependency>
    <groupId>com.vaadin</groupId>
    <artifactId>hilla-spring-boot-starter</artifactId>
  </dependency>
  <!-- Dev-mode live reload banner and Vaadin's browser dev tools; harmless and excluded from the runtime
       artifact in a production build. -->
  <dependency>
    <groupId>com.vaadin</groupId>
    <artifactId>vaadin-dev</artifactId>
    <optional>true</optional>
  </dependency>
</dependencies>

<build>
  <plugins>
    <!-- ... existing boot module plugins (spring-boot-maven-plugin, groovy-maven-plugin, ...) ... -->
    <plugin>
      <groupId>com.vaadin</groupId>
      <artifactId>vaadin-maven-plugin</artifactId>
      <!-- version comes from the root pom's pluginManagement (${vaadin.version}) -->
      <executions>
        <execution>
          <goals>
            <goal>prepare-frontend</goal>
            <goal>build-frontend</goal>
          </goals>
        </execution>
      </executions>
    </plugin>
  </plugins>
</build>
```

If Step 1's "Flow views" question was answered Yes, also add whichever Flow UI component starters the user wants
(e.g. `com.vaadin:vaadin` for the full component set) and scaffold one example `@Route` class under
`<web-module>/src/main/java/<base-package>/...`; this is a small, self-contained addition and not templated here
since it's opt-in and Java-only.

## Step 3 — `src/main/frontend/`

All of this lives directly under `<web-module>/src/main/frontend/` — **not** under `src/main/resources` or any
generated-sources directory. Never create or hand-edit anything under `src/main/frontend/generated/`: that whole
directory (and `routes.tsx`/`file-routes.ts` inside it) is written by `vaadin:prepare-frontend` on every run and
would be silently overwritten.

**`src/main/frontend/views/@index.tsx`** — the file-based router's index route:

```tsx
export default function HomeView() {
  return <div>Hello from <project-name></div>;
}
```

**`src/main/frontend/views/@layout.tsx`** — wraps every route; `<Outlet />` is where the router renders the active
view:

```tsx
import { Outlet } from 'react-router';

export default function MainLayout() {
  return (
    <div>
      <header><project-name></header>
      <Outlet />
    </div>
  );
}
```

**`src/main/frontend/index.html`** — Vaadin auto-generates a default the first time `prepare-frontend` runs if
none exists, but it's meant to be committed and customized afterward (the official Vaadin skeleton ships its own
with a real `<title>`), so write it once, up front, rather than letting the generic default land:

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title><project-name></title>
    <style>
      body {
        margin: 0;
        width: 100vw;
        height: 100vh;
      }
      #outlet {
        height: 100%;
      }
    </style>
    <!-- index.ts is included here automatically (either by the dev server or during the build) -->
  </head>
  <body>
    <div id="outlet"></div>
  </body>
</html>
```

Do **not** write `views/routes.tsx` or anything else under `generated/` — see the note at the top of this skill.

## Step 4 — `vitest.config.ts`, the sample test, and `@vitest/coverage-v8`

Write at `<web-module>/vitest.config.ts` (module root, next to `pom.xml` — **not** inside `src/main/frontend/`).
The one thing this file must get right, confirmed empirically: Vaadin's own generated Vite config
(`<web-module>/vite.generated.ts`, which both `vite.config.ts` and this file build on via its exported
`overrideVaadinConfig(customConfig: UserConfigFn)` helper — not `useVaadinConfig`, which doesn't exist) sets Vite's
`root` to `src/main/frontend`. Every glob and path below is written **relative to that root**, not to the module
root, or `vitest run` reports "No test files found" despite the tests being right there.

```ts
import { overrideVaadinConfig } from './vite.generated';

export default overrideVaadinConfig(() => ({
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./test/setup.ts'],
    include: ['**/*.test.{ts,tsx}'],
    exclude: ['generated/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      // Vite's root is src/main/frontend; three levels up lands back at the module root, so the report ends
      // up at <web-module>/coverage/lcov.info — the exact path Sonar's sonar.javascript.lcov.reportPaths
      // and the CI workflow's coverage step both expect. Confirmed by an actual `vitest run --coverage`.
      reportsDirectory: '../../../coverage',
      include: ['**/*.{ts,tsx}'],
      exclude: ['generated/**', '**/*.test.{ts,tsx}'],
    },
  },
}));
```

**`src/main/frontend/test/setup.ts`**:

```ts
import '@testing-library/jest-dom/vitest';
```

**`src/main/frontend/views/@index.test.tsx`** (sample test, colocated with the view it tests — the same
convention Hilla's own generator uses):

```tsx
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import HomeView from './@index';

describe('HomeView', () => {
  it('renders the greeting', () => {
    render(<HomeView />);
    expect(screen.getByText('Hello from <project-name>')).toBeInTheDocument();
  });
});
```

A `.tsx` test file living directly under `views/` trips Vite's React plugin Fast Refresh boundary check (it logs
`... should contain a default export of a component` because a test module has no default export) — this is
purely a console warning; the test still runs and passes, confirmed by an actual run. Don't try to "fix" it by
moving the test elsewhere unless the user objects to the noise; it's the same layout Vaadin's own project
generator produces.

## Step 5 — `package.json` scripts, ESLint, and Prettier

**`package.json`** — merge these into whatever `vaadin:prepare-frontend` already wrote (it owns the
`dependencies`/`vaadin`/`overrides` blocks; never hand-edit those), adding only `scripts` and the devDependencies
below:

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "coverage": "vitest run --coverage",
    "lint": "eslint src/main/frontend",
    "format": "prettier --check src/main/frontend/**/*.{ts,tsx}"
  },
  "devDependencies": {
    "vitest": "<resolved>",
    "@vitest/coverage-v8": "<resolved, matches vitest>",
    "@testing-library/react": "<resolved>",
    "@testing-library/jest-dom": "<resolved>",
    "jsdom": "<resolved>",
    "eslint": "<resolved>",
    "@eslint/js": "<resolved>",
    "typescript-eslint": "<resolved>",
    "eslint-plugin-react-hooks": "<resolved>",
    "eslint-config-prettier": "<resolved>",
    "prettier": "<resolved>"
  }
}
```

`format` is scoped to `.ts`/`.tsx` under `src/main/frontend` deliberately — running Prettier over the whole
frontend directory also flags the framework-generated `index.html`, which is real but not useful noise.

**`<web-module>/eslint.config.js`** (flat config — this catalog's TypeScript skills all use flat config, not
`.eslintrc`):

```js
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import reactHooks from 'eslint-plugin-react-hooks';
import eslintConfigPrettier from 'eslint-config-prettier';

export default tseslint.config(
  { ignores: ['src/main/frontend/generated/**', 'node_modules/**', 'coverage/**'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['src/main/frontend/**/*.{ts,tsx}'],
    plugins: { 'react-hooks': reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
    },
  },
  eslintConfigPrettier,
);
```

**`<web-module>/.prettierrc.json`**:

```json
{
  "singleQuote": true,
  "printWidth": 120,
  "trailingComma": "all"
}
```

**`<web-module>/.prettierignore`** — required: Prettier 3.x does not read `.gitignore` on its own, and running it
unignored produces the same generated-file noise the `format` script's own glob already avoids for `lint`:

```
src/main/frontend/generated/
node_modules/
coverage/
target/
```

## Step 6 — `.gitignore` additions

Confirmed against the official `vaadin/skeleton-starter-hilla-react` repository's own `.gitignore` — the frontend
adds exactly three entries beyond what this reactor's `.gitignore` already has for `target/`:

```
<web-module>/node_modules/
<web-module>/src/main/frontend/generated/
<web-module>/vite.generated.ts
```

`vite.generated.ts` is regenerated ("This file will be overwritten on every run", per its own header comment) on
every `prepare-frontend` run, unlike `vite.config.ts` (which is written once and meant to be edited). Do **not**
ignore `package.json`, `package-lock.json`, `vite.config.ts`, `tsconfig.json`, or `types.d.ts` — all five are
generated once by the plugin, meant to be committed, and safe to hand-edit afterward (`tsconfig.json`/`types.d.ts`
say exactly this in their own generated header comments). `<web-module>/index.html` is likewise committed, not
ignored — Step 3 writes it deliberately so it isn't left at the generic default.

`.gitignore` is hand-maintained in this catalog's conventions (see `CLAUDE.md`), so show the diff and confirm
before writing.

## Step 7 — Sonar additions (only when `sonar.mode` isn't `none`)

Read `sonar.mode` from the manifest. When it's `none`, skip this step entirely — no `sonar.*` property should
reference a frontend that isn't analysed. Otherwise add to the root pom's existing `sonar.*` properties block
(written by `iru-setup-java-springboot-pom`) — **merge**, don't replace, `sonar.exclusions` in particular, since
`iru-setup-java-springboot-pom` already writes `**/generated-sources/**,**/generated/**` there and this addition
must not clobber it:

```xml
<sonar.sources>src/main/java,<web-module>/src/main/frontend</sonar.sources>
<sonar.tests>src/test/java,<web-module>/src/main/frontend</sonar.tests>
<sonar.test.inclusions>**/*.test.ts,**/*.test.tsx</sonar.test.inclusions>
<sonar.javascript.lcov.reportPaths>${maven.multiModuleProjectDirectory}/<web-module>/coverage/lcov.info</sonar.javascript.lcov.reportPaths>
<!-- Merge into the existing sonar.exclusions value — do not replace it. -->
<sonar.exclusions>**/generated-sources/**,**/generated/**,**/frontend/generated/**</sonar.exclusions>
```

`<web-module>/coverage/lcov.info` is the exact path Step 4's `vitest.config.ts` produces — confirmed by an actual
`vitest run --coverage` run, not assumed.

## Step 8 — Verify

Delegate both checks to the `iru-gate-runner` agent so a Maven/npm log doesn't flood this context:

```
Agent({
  description: "Verify Hilla frontend build",
  subagent_type: "iru-gate-runner",
  prompt: "Run `mvn -q -pl <web-module> -am vaadin:prepare-frontend` from the repository root. Report only
    pass/fail and, on failure, the first real error.",
  run_in_background: false
})
```

then, in `<web-module>`:

```
Agent({
  description: "Verify Hilla frontend tests",
  subagent_type: "iru-gate-runner",
  prompt: "In <repository-root>/<web-module>, run `npm ci` then `npx vitest run --coverage`. Report only
    pass/fail, the test count, the coverage summary line, and whether <web-module>/coverage/lcov.info was
    produced.",
  run_in_background: false
})
```

**Ordering matters and is easy to get backwards**: `vitest.config.ts` (and `vite.config.ts`) import
`./vite.generated.ts`, which itself imports compiled helper scripts from `<web-module>/target/plugins/...` —
files that only exist after at least one Maven build has reached `vaadin:prepare-frontend`. Running `npx vitest`
before any Maven build (e.g. against a freshly cloned repository with only `target/` gitignored away) fails with a
module-not-found error that has nothing to do with the tests themselves. Always run the `mvn ... prepare-frontend`
gate before the `vitest` gate, in that order, both here and in the generated CI workflow (see
`iru-setup-java-springboot-github-workflows`).

If a production bundle build is wanted as part of verification, also run (via the same `iru-gate-runner` pattern)
`mvn -q -pl <web-module> -am package -Pproduction -DskipTests` — expect `npm install` to run for real the first
time views exist under `src/main/frontend/views/` (confirmed: with an empty `views/` directory the plugin decides
"a production mode bundle build is not needed" and skips npm entirely, which is correct but would give a false
sense that the toolchain works before any real frontend code exists to prove it).

## Step 9 — Report

Summarize:

- The web module written into (`boot`, unless Step 1 found a reason to use another), and why.
- The resolved `vaadin.version`, and whether the root pom's Vaadin wiring already existed (owned by
  `iru-setup-java-springboot-pom`) or had to be filled in by this skill.
- Every npm package version resolved, separating live lookups from the recorded fallbacks actually used.
- Whether Flow views were requested, and what that added.
- Files written versus already present (per Step 1's stop-or-update answer).
- Whether `sonar.mode` triggered the Sonar additions, and to which properties.
- The result of Step 8's two (or three) gate runs, including the resolved `<web-module>/coverage/lcov.info` path.
- Whether Node was found globally or the plugin downloaded its own into `~/.vaadin` (first-run CI time cost).

Warn explicitly:

- **Review every generated frontend file before committing** — `package.json`'s `dependencies`/`vaadin`/
  `overrides` blocks in particular are plugin-owned and will be silently rewritten on the next
  `vaadin:prepare-frontend`; don't hand-edit them expecting the edit to stick.
- If `sonar.mode` isn't `none`, the SonarCloud/SonarQube project must already exist for the new `sonar.sources`/
  `sonar.tests` to have somewhere to report into — this skill doesn't create it.
- `vaadin:build-frontend` needs Node; state plainly whether this run used a global install or triggered Vaadin's
  own download into `~/.vaadin`, since the latter adds real time to a machine's first build.
- A full `-Pproduction` build (real npm install + Vite production bundle) can take noticeably longer than a plain
  `mvn verify` — mention this if it wasn't run as part of Step 8, so the user isn't surprised the first time CI
  does run it.

## Resolution table

| Placeholder | Resolved from |
|---|---|
| `<web-module>` | The manifest's `modules:` entry for `boot` (Step 1) |
| `<project-name>` | `springboot-stack.yml`'s `project.artifactId` (or `project.description`, whichever reads better as UI copy) |
| `<base-package>` | `springboot-stack.yml`'s `project.basePackage` (only used if Flow views were requested) |
| `<resolved>` (npm versions) | Live npm registry lookups in Step 1, falling back to the pinned versions listed there |
| `${vaadin.version}` | The root pom's `<vaadin.version>` property (Step 1: read if present, written if not — see `iru-setup-java-springboot-pom`) |
