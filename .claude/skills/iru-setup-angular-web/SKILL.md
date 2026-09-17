---
name: iru-setup-angular-web
description: Scaffold a new Angular web application with `npx -p @angular/cli@latest ng new <name> --standalone
  --style=scss --routing --skip-git --package-manager=npm --defaults --ssr=false` (Angular 22's own defaults
  already give a zoneless, Vitest-backed, standalone-component workspace — the flags above only make every prompt
  non-interactive), then wires up the full toolchain on top of it: confirms `angular.json`'s `test` target uses the
  `@angular/build:unit-test` builder with `runner: vitest`, adds `coverageReporters: ["text","lcov"]` and an
  80%-lines `coverageThresholds` gate, installs a matching-major `@vitest/coverage-v8`; `ng add angular-eslint`
  (auto-pins its major to the installed Angular major) plus `eslint-config-prettier`; normalizes the CLI's own
  scaffold with the `.prettierrc` it already ships (adding a `.prettierignore`); Stylelint 17 for SCSS
  (`stylelint-config-standard-scss`); Playwright via `ng add playwright-ng-schematics` (and fixes the schematic's
  own hardcoded `/MyApp/` title assertion); Compodoc (`@compodoc/compodoc`, a `docs` script into `docs/api`);
  optional Storybook (`@storybook/angular-vite`, asked); and, when `sonar` ≠ `none`, `sonar-project.properties`
  (`sonar.sources=src`, `sonar.tests=src`, `sonar.test.inclusions=**/*.spec.ts`,
  `sonar.javascript.lcov.reportPaths=coverage/<project>/lcov.info`). Invoke as `/iru-setup-angular-web`. Accepts
  pre-resolved inputs via `args` (`key: value` lines) — `name`, `directory`, `license`, `developer-name`,
  `developer-email`, `organization-url`, `open-source`, `sonar` (+ `sonar-organization`/`sonar-project-key`/
  `sonar-host-url`), `storybook`, `mode` (`new`/`existing`) — so an orchestrating skill can supply them without
  re-prompting; invoked stand-alone, it asks `open-source` first and derives the `sonar` question's default from
  that answer. If `angular.json` already exists, surveys every file this skill owns and asks whether to stop, fill
  gaps only, or regenerate everything. Use whenever a new Angular web application needs its scaffold, test/coverage
  config, lint/format/style tooling, e2e tests, API docs, and Sonar wiring bootstrapped from this house template,
  instead of hand-running each `ng add`/`npm install` separately.
model: haiku
---

# Setup Angular Web

Scaffold a new Angular application with the Angular CLI, then layer on this catalog's standard toolchain: coverage
gates on the built-in Vitest test runner, ESLint (angular-eslint), Prettier, Stylelint for SCSS, Playwright e2e,
Compodoc API docs, optional Storybook, and Sonar wiring. Every step below was verified against a real
`ng new`/`ng add` run — quirks the current Angular CLI doesn't advertise up front (a coverage package that must be
installed separately, an e2e scaffold with a hardcoded title assertion, generated files that don't pass the CLI's
own Prettier config out of the box) are called out explicitly where they bite.

## Step 0 — Resolve inputs

This skill can be invoked stand-alone (`/iru-setup-angular-web`) or as a step inside another skill (e.g. a future
`iru-setup-angular-web-repository` or the catalog's `iru-setup-repository` front door), which resolves these same
inputs itself and passes them through `args` as `key: value` lines, one per line, e.g.:

```
name: my-app
directory: .
license: MIT
developer-name: Jane Doe
developer-email: jane@example.com
organization-url: https://github.com/example-org
open-source: yes
sonar: cloud
sonar-organization: example-org-github
sonar-project-key: example-org_my-app
sonar-host-url: https://sonarcloud.io
storybook: no
mode: new
```

Parse any such lines from `args` now. Every field found here is resolved — skip asking about it in Step 2. Only
fields genuinely missing from `args` still need a question. If `args` is absent or doesn't look like this format,
treat everything as unset and ask normally.

Recognized keys: `name` (the Angular workspace/project name — also the default output directory), `directory`
(where to scaffold; default is `name` itself, but pass `.` to scaffold directly into the current, already-existing
repository root — see Step 3), `license`, `developer-name`, `developer-email`, `organization-url`, `open-source`
(`yes`/`no`), `sonar` (`cloud`/`self-hosted`/`none`) plus, only when `sonar` is `cloud` or `self-hosted`,
`sonar-organization`/`sonar-project-key`/`sonar-host-url`, `storybook` (`yes`/`no`), and `mode` (`new`/`existing`).

`mode: existing` is this catalog's shared signal (set by a front door that already ran `iru-explore` and knows this
is an established repository) that Step 1 should skip its stop-or-regenerate question entirely and go straight to
gap-fill. There is no `publish` or `distribution` key here — an Angular web app isn't published to a package
registry or an app store the way a library or a native app is; it's built and deployed as static assets, which is
`iru-setup-typescript-github-workflows`'s concern, not this skill's.

## Step 1 — Survey the repository

Check, at the target directory (the repository root if `directory: .` was resolved, otherwise the `name`
subdirectory once Step 2 resolves `name` — for this survey, check both the bare repository root and a
subdirectory matching a `name` already given via `args`), whether an Angular workspace already exists: `angular.json`
plus `package.json` with `@angular/core` in its dependencies.

- **Neither exists**: skip straight to Step 2. There is nothing to preserve.
- **`mode: existing` was resolved in Step 0**: skip the question below — go straight to **gap-fill**: run only the
  `ng add`/config steps below whose target file or `package.json` entry is genuinely missing, and leave everything
  already present untouched (including `angular.json`'s existing `test` options — merge in only the missing keys
  from Step 4, don't overwrite ones already set). Note in Step 13's report which steps were skipped because their
  output already existed.
- **Otherwise, and a workspace already exists**: warn the user, then use `AskUserQuestion` with three options:
  - **Stop** — leave everything untouched; make no changes at all. Report this and end here.
  - **Fill gaps only** (recommended) — run only the steps below whose output is missing (e.g. Playwright is set up
    but Compodoc isn't); don't touch anything already configured.
  - **Regenerate everything** — before asking Step 2's questions, read the existing `angular.json`/`package.json`
    and use their current project name, style preprocessor, and any already-resolved license/author info as the
    *defaults* offered for whichever Step 2 question Step 0 didn't already resolve via `args`. Tell the user this
    replaces `angular.json`'s `test` options, `eslint.config.js`, `.stylelintrc.json`, `playwright.config.ts`, and
    `sonar-project.properties` wholesale — any hand-added customization to those files will be lost unless
    re-added afterward (call this out again in Step 13).

## Step 2 — Collect the required inputs

For any field Step 0 already resolved from `args`, use that value directly and don't ask about it again. For
everything else, ask the user directly (plain conversation, pre-filling defaults found in Step 1 if regenerating):

- **name** — the Angular workspace/project name, e.g. `my-app`. Used for the `ng new` command, and as
  `<project>` in the `coverage/<project>/lcov.info` path Step 11's `sonar-project.properties` references.
- **directory** — where to scaffold. If the repository is otherwise empty (no tracked files besides maybe
  `.git`/`README.md`), offer `.` (scaffold directly into the repository root, so the Angular project *is* the
  repository) as the default; otherwise ask explicitly, since scaffolding a full Angular workspace into a
  non-empty repository root would collide with existing files.
- **Developer name**, **developer email**, **organizationUrl** — not written into any Angular-generated file
  directly (there's no `package.json` `author` field convention here the way there is for a library), but recorded
  for `iru-check-license`'s header generation once a license is chosen below.

Then, unless Step 0 already resolved a `license` value from `args`, ask about the **license** with
`AskUserQuestion` (mirrors every other setup skill in this catalog):

- Apache License 2.0 (recommended)
- MIT License
- No license (proprietary / all rights reserved)
- Other — ask for the license's display name and URL directly afterward

If a license is chosen, remind the user in Step 13 to add a matching `LICENSE` file at the repository root if one
doesn't exist yet — `iru-check-license` can verify/backfill source headers against it once it's there.

Then resolve `open-source` and `sonar` — skip either one Step 0 already resolved from `args`:

- **open-source** — is this repository open source? Yes / No.
- **sonar** — recommend **SonarCloud** (`cloud`) when open-source is Yes; when not open source, state that
  SonarCloud is free only for open-source projects (a paid plan is required otherwise) and recommend **None**
  (`none`), offering **self-hosted SonarQube** as the second option. When `cloud` or `self-hosted` is chosen, also
  collect `sonar-organization`/`sonar-project-key`/`sonar-host-url` the same way this catalog's Java/TypeScript
  setup skills do (SonarCloud: suggest `<owner>-github` / `<owner>_<repo>` / `https://sonarcloud.io`, inferring
  `<owner>`/`<repo>` from `git remote get-url origin`; self-hosted: ask for `sonar.host.url` directly, plus
  `sonar.organization` only if that server has organizations enabled, and `sonar.projectKey`).

Then, unless Step 0 already resolved it, ask **storybook** (`AskUserQuestion`, default **No**): whether to also
scaffold Storybook (`@storybook/angular-vite`) for isolated component development/visual review. Most Angular apps
don't need it; recommend Yes only if the user mentions a component library or design-system use case.

## Step 3 — Look up tool versions

Every package this skill installs is looked up at run time (`npm view <package> version`) rather than hardcoded;
the versions below are only the fallback for when the registry is unreachable, as observed in September 2026:

| Package | Run-time lookup | September 2026 fallback |
|---|---|---|
| `@angular/cli` (and the workspace's own Angular packages) | `npm view @angular/cli version` | `22.1.8` |
| `angular-eslint` (installed by `ng add`, not looked up manually) | n/a — `ng add` resolves its own compatible version | `22.5.0` |
| `eslint-config-prettier` | `npm view eslint-config-prettier version` | `10.1.8` |
| `prettier` (already shipped by `ng new`; only relevant if bumping it) | `npm view prettier version` | `3.9.7` |
| `stylelint` | `npm view stylelint version` | `17.15.0` |
| `stylelint-config-standard-scss` | `npm view stylelint-config-standard-scss version` | `17.0.0` |
| `playwright-ng-schematics` (installed by `ng add`, not looked up manually) | n/a — `ng add` resolves its own compatible version | `22.1.2` |
| `@vitest/coverage-v8` | **do not** `npm view` the latest — see Step 4's warning; match the installed `vitest` major instead | `4.1.11` (matching the `vitest ^4.0.8` that `@angular/build` 22.1.8 pins) |
| `@compodoc/compodoc` | `npm view @compodoc/compodoc version` | `2.0.0` |
| `@storybook/angular-vite` (only if `storybook: yes`) | `npm view @storybook/angular-vite version` | `10.6.0` |

## Step 4 — Scaffold the Angular workspace

Run, from the repository root (or its parent, if `directory` resolved to something other than `.`):

```bash
NG_CLI_ANALYTICS=false npx -p @angular/cli@latest ng new <name> \
  --standalone --style=scss --routing --skip-git --package-manager=npm \
  --defaults --ssr=false --directory <directory>
```

Flag notes (each one discovered/confirmed by actually running this command non-interactively):

- **`--defaults`** disables every interactive prompt that has a declared default — this alone was enough to make
  the command run fully unattended in verification, with **no** prompt for SSR, zoneless, or AI-tool config files.
- **`--ssr=false`** is still passed explicitly even though `--defaults` alone didn't prompt for it, since `ssr` has
  no schema-level default of its own (unlike `standalone`/`test-runner`, which do) — passing it explicitly is the
  only way to guarantee no SSR scaffold is generated, rather than relying on undocumented prompt-skipping
  behavior.
- **`NG_CLI_ANALYTICS=false`** (an environment variable, not a CLI flag) suppresses the one-time analytics
  opt-in/out prompt some Angular CLI versions show on first run in an environment with no prior `ng` usage
  recorded.
- **`--standalone`** and Vitest as the **`--test-runner`** are *already the default* in the current Angular CLI
  (22.x) — passing `--standalone` is redundant but harmless and future-proofs the command if a later major changes
  that default back. Likewise, the scaffolded app is **zoneless by default** (no `zone.js` dependency, no
  `provideZoneChangeDetection` call) — there is no need to pass `--zoneless` explicitly today, but note this
  explicitly in Step 13's report since it's easy to assume otherwise from older Angular tutorials.
- **`--directory <directory>`** — pass `.` to scaffold directly into an already-empty repository root (verified:
  this writes `angular.json`/`package.json`/`src/` etc. straight into the current directory instead of creating a
  `<name>/` subdirectory, while the project is still internally named `<name>` in `angular.json`); omit it (or
  pass `<name>` explicitly) to scaffold into a fresh `<name>/` subdirectory instead, per Step 2's resolved
  `directory`.
- **`--skip-git`** is required in this catalog's flow — the enclosing repository already owns Git, so `ng new`
  must never attempt its own `git init`/initial commit.
- No `--collection`, `--ai-config`, or `--minimal` flags are passed: `--ai-config` defaults to generating nothing
  when `--defaults` is used (verified: no `CLAUDE.md`/`.cursorrules`/etc. were created), and `--minimal` would drop
  the test scaffolding this skill's whole coverage setup depends on.

## Step 5 — Configure the `test` target for coverage

The scaffolded `angular.json` already gives the `test` architect target the `@angular/build:unit-test` builder,
but with **no `options` block at all** — it relies entirely on that builder's own schema defaults (`runner:
"vitest"` is one of them, confirmed against the installed `@angular/build` package's schema). Add an explicit
`options` block anyway, both to make the runner choice visible in source control and to add the coverage
reporters/threshold this catalog requires everywhere:

```jsonc
// angular.json — merge this into projects.<project>.architect.test (only the "test" target shown)
"test": {
  "builder": "@angular/build:unit-test",
  "options": {
    "runner": "vitest",
    "coverageReporters": ["text", "lcov"],
    "coverageThresholds": {
      "lines": 80
    }
  }
}
```

Resolution notes:

- `<project>` is the `name` from Step 2 — the key `ng new` used under `projects` in `angular.json`.
- The `coverage` flag itself (whether `ng test` actually *collects* coverage) is a separate, per-invocation CLI
  flag (`ng test --coverage`), not something baked into `angular.json` — that's intentional, so `ng test` stays
  fast for local iteration and `ng test --coverage` (used by CI and by the `iru-typescript-coverage` gate skill) is
  the one that pays the instrumentation cost.
- `coverageThresholds` only gates lines here, matching this catalog's 80%-lines convention; add `statements`/
  `branches`/`functions` keys the same way if a stricter bar is wanted later.
- **This alone is not enough** — Step 6 installs the package the coverage collector actually needs.

## Step 6 — Install the coverage collector (required, not bundled)

Running `ng test --coverage` against a freshly scaffolded project fails outright with:

```
The following packages are required but were not found:
  - Code coverage requires either "@vitest/coverage-v8" or "@vitest/coverage-istanbul" to be installed.
```

`ng new` does **not** install a coverage provider by default. Install `@vitest/coverage-v8` — but **do not** blindly
`npm view @vitest/coverage-v8 version` and install "latest": at verification time, the latest published
`@vitest/coverage-v8` was a major ahead (`5.0.1`) of the `vitest` version `ng new` actually pins
(`vitest: "^4.0.8"` in `package.json`, resolving to `4.1.11`), and installing the mismatched major failed outright.
Instead:

```bash
installed_vitest_major=$(node -p "require('./node_modules/vitest/package.json').version.split('.')[0]")
npm install -D @vitest/coverage-v8@${installed_vitest_major}
```

(equivalently, read `vitest`'s resolved version from `package-lock.json`/`node_modules/vitest/package.json` and
pick the matching major of `@vitest/coverage-v8` from `npm view @vitest/coverage-v8 versions --json`). Verified
after this fix: `ng test --coverage` runs cleanly and writes lcov to **`coverage/<project>/lcov.info`** (confirmed
by inspecting the actual output directory after a real run — this is the path Step 11's `sonar-project.properties`
and this catalog's `iru-typescript-coverage`/CI steps must reference for an Angular project, not the bare
`coverage/lcov.info` a library or React-Vite project uses).

## Step 7 — Add ESLint via `ng add angular-eslint`

```bash
npx ng add angular-eslint --skip-confirmation
```

Verified: this one command auto-detects the workspace's Angular major and installs the matching `angular-eslint`
major (confirmed output: "angular-eslint v22 matches this workspace's Angular v22"), so there is no separate
version-pinning step this skill needs to perform — `ng add` already refuses/adjusts for a mismatched major on its
own. It also fully wires `eslint.config.js` (flat config, `@eslint/js` + `typescript-eslint` recommended +
`angular-eslint` recommended, an inline-template processor, and default directive/component selector rules) *and*
adds a `lint` architect target (`@angular-eslint/builder:lint`) to `angular.json` — nothing further to write for
ESLint itself.

Add one thing on top, to keep ESLint from fighting Prettier over formatting: install `eslint-config-prettier` and
extend it last in `eslint.config.js`'s `.ts` block:

```js
// eslint.config.js — add this require alongside the existing ones
const prettier = require('eslint-config-prettier');

// …and add `prettier` as the LAST entry in the `.ts` block's `extends` array:
//   extends: [
//     eslint.configs.recommended,
//     tseslint.configs.recommended,
//     tseslint.configs.stylistic,
//     angular.configs.tsRecommended,
//     prettier,
//   ],
```

Verified: `npx ng lint` passes cleanly on the untouched scaffold both before and after this addition.

## Step 8 — Confirm Prettier, and normalize the scaffold

`ng new` already ships a `.prettierrc` (`printWidth: 100`, `singleQuote: true`, an `*.html` override using the
`angular` parser) — do not replace it; only add a `.prettierignore` next to it (`ng new` doesn't create one):

```gitignore
# .prettierignore
dist/
coverage/
docs/api/
.angular/
```

**Quirk verified**: `npx prettier --check .` fails on a *freshly scaffolded, untouched* project — 7 of the CLI's
own generated files (`src/app/app.config.ts`, `src/app/app.html`, `src/app/app.spec.ts`, `src/index.html`,
`src/main.ts`, `tsconfig.app.json`, `tsconfig.spec.json`) don't match the `.prettierrc` the same scaffold ships.
Run `npx prettier --write .` once, right after scaffolding (before the first commit), to normalize them — verified
this reformats exactly those files and nothing else, and `prettier --check .` then passes cleanly.

Add npm scripts (merge into `package.json`'s `scripts`, don't replace the ones `ng new`/`ng add` already wrote):

```jsonc
"format": "prettier --check .",
"format:fix": "prettier --write ."
```

## Step 9 — Add Stylelint for SCSS

```bash
npm install -D stylelint@<version> stylelint-config-standard-scss@<version>
```

Write `.stylelintrc.json`:

```json
{
  "extends": "stylelint-config-standard-scss",
  "ignoreFiles": ["dist/**", "coverage/**", "docs/api/**"],
  "rules": {
    "no-empty-source": null
  }
}
```

**Quirk verified**: `ng new`'s own generated `src/app/<root-component>.scss` is a 0-byte file, and
`stylelint-config-standard-scss` enables `no-empty-source` by default, which fails on it immediately
(`1:1 ✖ Empty source no-empty-source`). Disabling `no-empty-source` (as shown above) is the pragmatic fix — a
freshly generated component with no styles yet is expected, not a real lint violation; re-enable it later once the
project has a policy against empty stylesheet files, if desired.

Add an npm script:

```jsonc
"stylelint": "stylelint \"src/**/*.scss\""
```

Verified clean (`exit 0`) against the scaffold with this config.

## Step 10 — Add Playwright via `ng add playwright-ng-schematics`

```bash
npx ng add playwright-ng-schematics --skip-confirmation
```

Verified: this installs `@playwright/test`, writes `playwright.config.ts` and `e2e/example.spec.ts` +
`e2e/tsconfig.json`, adds an `e2e` architect target (`playwright-ng-schematics:playwright`, wired to the `serve`
target so `ng e2e` auto-starts/stops the dev server) to `angular.json`, and an `e2e` script (`ng e2e`) to
`package.json` — all non-interactively, no extra flags needed beyond `--skip-confirmation`.

**Quirk verified**: the schematic's own `e2e/example.spec.ts` asserts a hardcoded, generic title —
`await expect(page).toHaveTitle(/MyApp/)` — regardless of the actual project name, which will always fail against
`<name>`'s real `<title>` (`ng new` writes `<title><name></title>` into `src/index.html`, standalone-cased, e.g.
`DemoApp` for a project named `demo-app`). Fix the generated spec's title regex to match the actual project name
right after running `ng add`:

```ts
// e2e/example.spec.ts — replace the literal /MyApp/ with the real title
await expect(page).toHaveTitle(/<Title-Cased-Project-Name>/);
```

Browser binaries are not installed by `ng add` itself — run `npx playwright install --with-deps chromium` (add
`firefox`/`webkit` too for full cross-browser coverage; each is a large download) before `ng e2e`/`npm run e2e`
will succeed. Verified end-to-end after both the title fix and installing the `chromium` binary: `ng e2e` builds,
serves, and runs the (corrected) smoke test successfully against Chromium.

## Step 11 — Add Compodoc

```bash
npm install -D @compodoc/compodoc@<version>
```

Add a `docs` script to `package.json`:

```jsonc
"docs": "compodoc -p tsconfig.app.json -d docs/api"
```

Verified: `npm run docs` runs cleanly against the scaffold's `tsconfig.app.json`, producing `docs/api/` (an
`index.html`, per-symbol pages, a coverage report, and an `llms.txt`) with no configuration file needed beyond the
script itself — Compodoc infers everything else from the TypeScript project and the root component it finds.

## Step 12 — Optional: Storybook

Only if `storybook: yes` was resolved in Step 2:

```bash
npx storybook@latest init
```

This is Storybook's own installer; it detects the Angular + `@angular/build` (Vite-based) workspace and installs
`@storybook/angular-vite` plus a `.storybook/` config and `storybook`/`build-storybook` npm scripts on its own.
**Unverified locally**: this session did not run `storybook@latest init` end-to-end (it isn't part of Task 5.2's
required verification list, and Storybook's installer both prompts for feature choices and pulls a large
dependency set) — fold in any quirk discovered the next time this step is actually exercised against Angular 22,
in particular whether `--yes`/a non-interactive flag exists on the current Storybook CLI major to fully script the
choices it currently asks about.

## Step 13 — Write `sonar-project.properties`

Only when `sonar` (from Step 2) is `cloud` or `self-hosted` — skip this step entirely for `sonar: none`.

```properties
sonar.organization=<sonar-organization>
sonar.projectKey=<sonar-project-key>
sonar.host.url=<sonar-host-url>
sonar.sources=src
sonar.tests=src
sonar.test.inclusions=**/*.spec.ts
sonar.javascript.lcov.reportPaths=coverage/<project>/lcov.info
sonar.exclusions=**/dist/**,**/docs/api/**
```

Resolution table:

| Placeholder | Source |
|---|---|
| `<sonar-organization>` | Step 2's `sonar` answer (SonarCloud only — omit the whole line for `self-hosted` unless that server has organizations enabled) |
| `<sonar-project-key>` | Step 2's `sonar` answer |
| `<sonar-host-url>` | Step 2's `sonar` answer (`https://sonarcloud.io` for `cloud`) |
| `<project>` | The `name` from Step 2 — verified as the actual `coverage/<project>/lcov.info` path Step 6 produces, not a generic `coverage/lcov.info` |

`sonar.tests=src` (not a separate `test/`/`e2e/` root) matches Angular's convention of co-locating `*.spec.ts`
files next to the source they test; `sonar.test.inclusions` is what tells Sonar which of those `src`-rooted files
are tests rather than production code. `e2e/**` is deliberately not excluded from `sonar.sources`/`sonar.tests`
here since Playwright specs live outside `src/` entirely (`e2e/`) and Sonar's default source/test roots already
don't reach them.

## Step 14 — Report

Summarize: the resolved project `name`/`directory`, the license chosen (or "none"), and which of Steps 4–13 ran
fresh, were skipped because their output already existed (Step 1's gap-fill/regenerate outcome), or were skipped
by design (Storybook when `storybook: no`, `sonar-project.properties` when `sonar: none`).

State explicitly what was included versus omitted, and why:

- **`open-source`**: yes/no, as resolved in Step 2.
- **`sonar`**: `cloud`/`self-hosted`/`none` — if `cloud`/`self-hosted`, `sonar-project.properties` was written
  with the resolved organization/project key/host URL; if `none`, note this is expected when the project isn't
  open source (SonarCloud is free only for open-source projects) unless the user explicitly chose it.
- **`storybook`**: yes/no — if yes, note that Step 12 was not verified end-to-end in this skill's own
  verification pass (see that step) and should be spot-checked the first time it actually runs.

Report the real coverage output path confirmed in Step 6 (`coverage/<name>/lcov.info`) and the zoneless/Vitest/
standalone defaults confirmed in Step 4, since both are easy to get wrong from memory of older Angular versions.

**Warn explicitly**:

- Review every generated/modified file before committing — `angular.json`'s merged `test` options,
  `eslint.config.js`'s added `eslint-config-prettier` extend, `.stylelintrc.json`'s `no-empty-source: null`
  override, and the corrected `e2e/example.spec.ts` title assertion were all applied programmatically and are
  worth a human look.
- Run `npx prettier --write .` once now if it hasn't been run yet (Step 8) — the CLI's own scaffold does not pass
  its own Prettier config out of the box.
- If `sonar: cloud`/`self-hosted` was chosen, a `SONAR_TOKEN` repository secret and an actual SonarCloud/SonarQube
  project matching `sonar.projectKey` still need to exist before a CI-run `sonar` scan will succeed —
  `sonar-project.properties` alone doesn't create either.
- Playwright's browser binaries (`npx playwright install --with-deps <browser>`) are a separate, large download
  not performed by `ng add playwright-ng-schematics` itself — CI must run it explicitly (`iru-setup-typescript-
  github-workflows`'s generated workflow does this; a fresh local clone must too before `ng e2e` will run).
- If a license was chosen and no `LICENSE` file exists yet, suggest the `iru-check-license` skill to generate one
  and backfill source headers.
- Which values were inferred versus verified: every command and file path in this skill (the `ng new` flag set,
  the coverage-collector major-matching requirement, the real `coverage/<project>/lcov.info` path, the Prettier
  and Stylelint scaffold quirks, the Playwright title-assertion bug) was verified against a real `ng new`/`ng add`
  run in September 2026 — only Step 12 (Storybook) was not exercised end-to-end; say so again here if
  `storybook: yes` was chosen.
