---
name: iru-setup-typescript-gitignore
description: Create or update the root `.gitignore` file for a TypeScript/npm project — `node_modules/`, build/output
  directories (`dist/`, `build/`, `out/`), test/coverage output, TypeScript incremental-build info, lint caches, env
  files (keeping `.env.example`), OS and editor noise — and, when detected, framework-specific generated paths for
  Angular, React (Vite/Storybook), React Native/Expo, Ionic/Capacitor native projects, Antora docs, TypeDoc/Compodoc
  API docs, and a Spring Boot + Vaadin Hilla frontend embedded in a Maven project. Invoke as
  `/iru-setup-typescript-gitignore`. Only creates `.gitignore` when one doesn't exist yet — if one already exists,
  this skill never overwrites it silently: it proposes an updated version, shows the user a diff, and only writes it
  on explicit approval. Mirrors the `iru-setup-java-gitignore` skill's contract for the npm/TypeScript ecosystem.
  Use whenever a TypeScript, React, Angular, React Native, or Ionic project needs a `.gitignore` bootstrapped from
  scratch, or an existing one checked against this house template without touching it unless the user approves.
model: haiku
---

# Setup TypeScript Gitignore

Create or refresh the root `.gitignore` for a TypeScript/npm project. Never overwrite an existing `.gitignore`
without showing the user exactly what would change and getting explicit approval first — a `.gitignore` can carry
hand-added, project-specific entries that must not be silently dropped.

## Step 1 — Check whether `.gitignore` already exists at the repository root

- **Not found**: continue to Step 2. Because there's nothing to lose, the final write in Step 5 happens without
  needing approval — go straight from composing the content to writing it, then report in Step 6.
- **Found**: read its current content now — it matters later, both to avoid proposing duplicate entries and
  because Step 4 must preserve any hand-written, project-specific lines this skill doesn't know how to regenerate.
  Warn the user up front that a `.gitignore` already exists and this skill will propose changes for them to review
  rather than overwrite it silently. Continue to Step 2.

## Step 2 — The universal base template

Every TypeScript/npm project gets this baseline, regardless of framework or package manager:

```gitignore
# Dependencies
node_modules/

# Build output
dist/
build/
out/

# Test / coverage output
coverage/

# TypeScript incremental build info
*.tsbuildinfo

# Lint cache
.eslintcache

# Environment files (never commit real secrets; the example file documents the shape)
.env*
!.env.example

# npm debug logs
npm-debug.log*

# OS noise
.DS_Store

# IDE noise
.idea/

# VS Code — ignore the directory but keep the shared, non-machine-specific config files
.vscode/*
!.vscode/settings.json
!.vscode/extensions.json
!.vscode/launch.json
!.vscode/tasks.json
```

This section is unconditional — include it verbatim regardless of framework.

**Note on `dist/`/`build/`**: a handful of projects intentionally commit their build output (e.g. a GitHub Pages
site served straight from a `docs/`-as-`dist/` branch, or a library that vendors its compiled output into the repo
for consumers without a build step). If the target repository already has tracked files under `dist/`, `build/`, or
`out/` (check with `git ls-files -- dist build out` when `.gitignore` doesn't already exist, before assuming), ask
the user via `AskUserQuestion` whether to keep ignoring that directory or drop it from the template — don't ignore a
directory out from under files that are already tracked.

## Step 3 — Detect project-specific additions

Don't guess; only add a section below when the thing it targets is actually present in the target repository. Use
the same manifest signals `iru-explore` and the sibling TypeScript setup skills rely on: `package.json`,
`angular.json`, `app.json`, `capacitor.config.*`, `pom.xml`, `docs/antora.yml` (or `docs/antora-playbook.yml`), and
`typedoc.json`.

- **Package manager–specific debug logs**: inspect `package.json`'s `packageManager` field and the lockfile present
  at the root.
  - `pnpm-lock.yaml` (or `packageManager: pnpm@...`) → pnpm project: add
    ```gitignore
    pnpm-debug.log*
    .pnpm-store/
    ```
  - `yarn.lock` (or `packageManager: yarn@...`) → Yarn project: add
    ```gitignore
    yarn-error.log*
    ```
  - `package-lock.json` (or no lockfile / npm default) → nothing extra; `npm-debug.log*` in the base template
    already covers it.
  - More than one lockfile can exist in a transitional repo — include every block that matches; don't guess a
    manager that has no lockfile evidence.

- **Angular** (`angular.json` at the root, or `@angular/core` in `package.json` dependencies): add
  ```gitignore
  .angular/
  ```
  (the Angular CLI's build/dev-server cache directory).

- **React / Vite** (`vite.config.ts`/`vite.config.js` at the root, or `vite` in `package.json` devDependencies):
  add
  ```gitignore
  .vite/
  *.local
  ```
  (`.vite/` is Vite's own cache directory when it lands at the project root rather than nested under
  `node_modules/.vite`; `*.local` is the entry `npm create vite@latest` itself scaffolds, for local env overrides
  beyond the `.env*` pattern already in the base template). If a `.storybook/` directory or a `storybook`-scoped
  package (`storybook`, `@storybook/react-vite`, `@storybook/angular-vite`, etc.) is present in
  `package.json` devDependencies, also add:
  ```gitignore
  storybook-static/
  ```

- **React Native / Expo** (`app.json` with an `"expo"` key, `expo` or `react-native` in `package.json`
  dependencies, and no `capacitor.config.*` — see the Ionic/Capacitor case below, which takes precedence when
  both signals are present): add
  ```gitignore
  .expo/
  .expo-shared/
  expo-env.d.ts
  web-build/
  *.jks
  *.p8
  *.p12
  *.mobileprovision
  *.keystore
  android/app/build/
  android/.gradle/
  android/local.properties
  ios/Pods/
  ios/build/
  DerivedData/
  ```
  These paths assume a bare/prebuilt React Native layout (`android/`, `ios/` at the project root, as `expo
  prebuild` or `react-native init` produce them). If the project stays fully managed (no `android/`/`ios/`
  directories committed), the `android/`/`ios/`-prefixed lines are harmless no-ops but still worth including since
  `expo prebuild` can be run later.

- **Ionic / Capacitor** (`capacitor.config.ts`/`capacitor.config.json` at the root, or `@capacitor/core` in
  `package.json` dependencies): add
  ```gitignore
  .capacitor/
  *.jks
  *.p8
  *.p12
  *.mobileprovision
  *.keystore
  android/app/build/
  android/.gradle/
  android/local.properties
  ios/App/Pods/
  ios/App/App.xcworkspace/xcuserdata/
  DerivedData/
  ```
  Capacitor nests the generated iOS project under `ios/App/` (unlike bare React Native's `ios/<AppName>/`), so the
  Pods/xcuserdata paths are prefixed accordingly — verify the actual nested folder name against `ios/` once it
  exists (`npx cap add ios` names the Xcode project after the app), and adjust the line if the project used a
  different name.

- **Playwright** (`playwright.config.ts`/`playwright.config.js` at the root, or `@playwright/test` in
  `package.json` devDependencies): add
  ```gitignore
  playwright-report/
  test-results/
  blob-report/
  .playwright/
  ```

- **Turborepo** (`turbo.json` at the root): add
  ```gitignore
  .turbo/
  ```

- **Istanbul/nyc coverage** (`.nycrc`/`.nycrc.json` at the root, or `nyc` in `package.json` devDependencies —
  most projects in this catalog use Vitest's or Jest's built-in coverage instead, already covered by the base
  `coverage/` entry, so this is rare): add
  ```gitignore
  .nyc_output/
  ```

- **Antora documentation build output** (`docs/antora.yml` or `docs/antora-playbook.yml` exists — see the
  `iru-setup-antora` skill): add
  ```gitignore
  docs/build/
  ```

- **TypeDoc / Compodoc API docs** (`typedoc.json` at the root, or a `docs`/`typedoc`/`compodoc` script in
  `package.json` invoking `typedoc` or `@compodoc/compodoc`; also `@compodoc/compodoc` itself in devDependencies):
  add
  ```gitignore
  docs/api/
  ```
  If both Antora and TypeDoc/Compodoc are present and TypeDoc/Compodoc is configured to output *inside* the Antora
  tree (e.g. `docs/modules/ROOT/assets/api/`, matching how the TypeScript workflows skill merges API docs under
  the Antora build), use that actual `out` path from `typedoc.json`/the `docs` script instead of the generic
  `docs/api/` — don't duplicate an entry already covered by `docs/build/` above.

- **Spring Boot + Vaadin Hilla frontend at a Maven root** (`pom.xml` at the root depends on
  `hilla-spring-boot-starter` / `com.vaadin:hilla`, or a `src/main/frontend/` directory exists): the frontend
  toolchain lives inside a Maven project, so the generated/installed paths sit under `src/main/frontend/` and
  `node_modules/` sits at the Maven root rather than the repository root the base template assumes. Add:
  ```gitignore
  node_modules/
  src/main/frontend/generated/
  src/main/frontend/vite.generated.ts
  pnpmfile.js
  .npmrc
  ```
  This block is **verified against Vaadin's own published `.gitignore` template** (Vaadin docs, "Using source
  control with Vaadin Flow" — the Hilla frontend is generated by the same `vaadin-maven-plugin`/
  `vaadin-gradle-plugin` tooling as Flow): `node_modules/`, `src/main/frontend/generated/`, and
  `vite.generated.ts` are explicitly listed there as plugin-generated and never committed, and so are the
  plugin-written `pnpmfile.js` and `.npmrc`. That same source explicitly calls out `tsconfig.json`, `types.d.ts`,
  and `src/main/frontend/index.html` as auto-generated **only if missing** — they should be tracked, not ignored,
  once the project customizes any of them, so this skill deliberately does **not** add them here. No official
  Vaadin/Hilla source mentions a `.vaadin/` directory in the `.gitignore` template, so this skill does not add one
  — if a future Hilla version introduces one, fold it in here once confirmed rather than guessing.

- Don't invent additional entries beyond what's actually detected — if the project has no Storybook, no native
  mobile shell, no docs tooling, or no Hilla frontend, the composed `.gitignore` should simply not mention them.

## Step 4 — Compose the proposed content

Concatenate Step 2's base template with whichever Step 3 sections actually matched, each under its own comment
header for readability (e.g. `# Angular`, `# Playwright`, `# Vaadin Hilla frontend`). If Step 1 found an existing
`.gitignore`, merge rather than duplicate: keep any of its lines that aren't already covered by the composed
template (hand-added project-specific ignores must survive), and don't repeat a line that's already present
verbatim.

## Step 5 — If `.gitignore` already existed, get approval before writing

Skip this step entirely if Step 1 found no existing file — proceed straight to Step 6's write.

- Show the user the proposed new `.gitignore` content as a diff against the current file (writing the draft to a
  temp path and running `git diff --no-index <current> <draft>` gives a clean unified diff).
- Ask via `AskUserQuestion` whether to: (a) accept and write the proposed content, (b) skip and leave the existing
  `.gitignore` untouched. There is no partial-apply option here — if the user wants only some of the proposed
  lines, let them say so in free text and revise the draft before writing.
- Only proceed to Step 6 on explicit acceptance.

## Step 6 — Write `.gitignore` and report

Write the composed content (Step 4, incorporating any edits from Step 5's review) to `.gitignore` at the repository
root. Then summarize: whether the file was newly created or updated, which conditional sections from Step 3 were
included versus skipped and why (e.g. "no Playwright section — no `playwright.config.ts` or `@playwright/test`
found", "no Hilla section — no `src/main/frontend/` and no Hilla dependency in `pom.xml`"), and — if `.gitignore`
already existed — whether the user accepted or skipped the proposed changes.

**Warn explicitly**:

- Review the generated `.gitignore` before committing — detection is heuristic (manifest/config-file signals), not
  a guarantee that every relevant path was found.
- If the repository already had files tracked under a directory this skill now proposes to ignore (e.g. a
  deliberately committed `dist/`), `git rm -r --cached` that directory manually after reviewing the diff —
  writing `.gitignore` alone does not untrack already-committed files.
- Which values were inferred versus verified: the Vaadin Hilla block (Step 3) was checked against Vaadin's current
  published source-control documentation as part of authoring this skill; every other Step 3 section is inferred
  purely from local manifest/config-file signals in the target repository and should be spot-checked against the
  project's actual generated output once its scaffold exists.
