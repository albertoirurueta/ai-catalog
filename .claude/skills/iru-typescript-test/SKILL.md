---
name: iru-typescript-test
description: Run a TypeScript/npm project's unit test suite through whichever runner the project actually has wired — Vitest (`vitest run`), Jest (`jest`), or the Angular CLI's Vitest-backed unit-test builder (`ng test --watch=false`) — optionally scoped to a file, directory, or test-name pattern. Also recognizes NestJS (`@nestjs/core` — ESM/Vitest with `vitest.config.ts` + `vitest.config.e2e.ts`, or CommonJS/Jest with `jest.config.ts` + `test/jest-e2e.json`; unit `*.spec.ts` by default, the `test/*.e2e-spec.ts` suite only on an explicit `e2e` selector, reporting a missing database/Docker/Testcontainers runtime as an environment failure rather than a test failure) and Next.js (`next` — Vitest via `vitest.config.mts` or Jest via `next/jest`; Playwright end-to-end tests, which build and start the app, only on an explicit `e2e` selector, never by default). Invoke as `/iru-typescript-test` to run every unit test, or `/iru-typescript-test <selector>` where `<selector>` is a file path, a directory, or a `-t "<name pattern>"` filter (combinable with a file/directory), optionally prefixed with `e2e` (NestJS/Next.js only) to run the end-to-end suite instead. Report-only — never fixes a failing test or modifies source/test code. Use whenever the user wants to run, re-run, or narrow down TypeScript/JavaScript unit (or, on request, NestJS/Next.js end-to-end) tests instead of invoking the runner by hand.
model: haiku
---

# TypeScript Test

Run the project's unit tests through whichever test runner it actually has configured, scoping the run to
whatever the user asked for, and report a compact pass/fail summary parsed from the runner's own JSON reporter.
This skill only runs tests and reports results — it does not fix failures or modify source/test code unless
asked to as a follow-up.

## Step 1 — Detect the runner, the package manager, and confirm it is actually wired

Never assume a runner from the framework alone — read `package.json` (and `angular.json` when present) first:

- **Vitest**: `vitest` appears in `dependencies`/`devDependencies` and a `vitest.config.ts`/`.js`/`.mts` file (or
  a `test`/`vitest` block in `vite.config.ts`) exists.
- **Jest**: `jest` or `jest-expo` appears in `dependencies`/`devDependencies` and a `jest.config.*` file, or a
  `"jest"` key in `package.json`, exists.
- **Angular (`ng test`, Vitest runner)**: `@angular/build` is a devDependency and `angular.json`'s `test`
  architect target for the project uses builder `@angular/build:unit-test`. This builder's `runner` option
  defaults to `"vitest"` (confirmed via `ng test --help` on Angular CLI 22.1 — choices are `"karma"`/`"vitest"`,
  default `"vitest"`); if the target's `options.runner` is explicitly set to `"karma"`, this skill's Vitest-shaped
  commands below don't apply — report that and stop rather than guessing at Karma's CLI.
- If none of the above is found (no matching devDependency and no config file), **stop and report "no test
  runner wired"** — do not report "0 tests" as if a scoped run legitimately found nothing; those look identical
  in a broken CI job and must not be conflated.

**Framework detection** (shared with `iru-typescript-coverage`/`-code-quality`/`-tsdoc`): `@nestjs/core` in
`dependencies` → **nestjs**; `next` in `dependencies` → **nextjs**. Both still run on Vitest or Jest, detected
exactly as above — the framework only changes which suite counts as "unit" and how the opt-in `e2e` selector
(Step 2) is resolved:

- **NestJS** — two flavors, both with unit tests as `*.spec.ts` next to the source and end-to-end tests as
  `test/*.e2e-spec.ts`, kept apart by two separate configs so the default run never picks up e2e files:
  - **ESM (Nest 12's default scaffold)**: `"type": "module"` in `package.json`, Vitest, `vitest.config.ts`
    (`include: ['**/*.spec.ts']`) for unit and `vitest.config.e2e.ts` (`include: ['**/*.e2e-spec.ts']`) for e2e;
    scripts `test` = `vitest run`, `test:e2e` = `vitest run --config ./vitest.config.e2e.ts`. Relative imports
    ending in `.js` are correct here (nodenext resolution) — never report them as a problem.
  - **CommonJS (pre-v12 projects, or Nest 12 with CommonJS chosen)**: no `"type"` field, Jest 30 + `ts-jest`,
    `jest.config.ts` (or a `"jest"` key in `package.json`, `testRegex: '.*\\.spec\\.ts$'`) for unit and
    `test/jest-e2e.json` (`testRegex: ".e2e-spec.ts$"`) for e2e; `test:e2e` = `jest --config ./test/jest-e2e.json`.
    Some scaffolds run Jest as `node --experimental-vm-modules ./node_modules/jest/bin/jest.js` in their scripts —
    when the project's `test`/`test:e2e` script does, invoke Jest the same way (that prefix replaces `npx jest`
    below) so the run behaves identically.
  - Always read the project's actual `test:e2e` script to find the e2e config path rather than assuming the
    scaffold's default location; if there is no `test:e2e` script and no e2e config file, an `e2e` selector is
    reported as "NestJS e2e suite not wired", not as zero tests.
- **Next.js** — unit/component tests run on Vitest (`vitest.config.mts`, `.mts` so it's ESM regardless of the
  package `"type"`) or on Jest configured through `next/jest` (`jest.config.ts` importing `next/jest.js`), both
  detected exactly as above. End-to-end tests are **Playwright**: `@playwright/test` in `devDependencies` plus a
  `playwright.config.{ts,js,mjs}`. Its `webServer` block typically runs `next build` + `next start` before any test
  executes, so an e2e run is slow (minutes) and can fail on a build error unrelated to the tests — never run it
  unless the `e2e` selector asks for it. Cypress (`cypress.config.*`) is out of scope for this skill — report it as
  "Cypress e2e present, not run" if the user asks for e2e and only Cypress is wired.

Determine the package manager from `packageManager` in `package.json`, or the lockfile present:
`package-lock.json` → npm, `pnpm-lock.yaml` → pnpm, `yarn.lock` → yarn. Invoke the runner's binary directly
(`npx <bin>` / `pnpm exec <bin>` / `yarn <bin>`) rather than through the project's own `test` npm script — the
script frequently omits `run` (Vitest) or hard-codes its own flags, and forwarding extra flags through `npm test
--` / `pnpm test --` is inconsistent across package managers. Calling the binary directly keeps the exact flags
below predictable regardless of package manager:

| Package manager | Invocation prefix |
|---|---|
| npm | `npx <bin> ...` *(verified locally)* |
| pnpm | `pnpm exec <bin> ...` |
| yarn (classic or berry) | `yarn <bin> ...` |

Only the npm form was exercised on this machine; the pnpm/yarn forms are standard, well-documented invocation
syntax but are marked **unverified locally**.

## Step 2 — Determine scope from the argument

| What the user wants | Vitest | Jest | `ng test` (Vitest runner) |
|---|---|---|---|
| Everything | `vitest run` | `jest` | `ng test --watch=false` |
| One file | `vitest run path/to/file.test.ts` | `jest path/to/file.test.ts` | `ng test --watch=false --include=path/to/file.spec.ts` |
| A directory | `vitest run path/to/dir` | `jest path/to/dir` | `ng test --watch=false --include="path/to/dir/**"` |
| Name pattern | `vitest run -t "<pattern>"` | `jest -t "<pattern>"` (alias of `--testNamePattern`) | `ng test --watch=false --filter="<pattern>"` |
| File/dir + name pattern | `vitest run path/to/file.test.ts -t "<pattern>"` | `jest path/to/file.test.ts -t "<pattern>"` | `ng test --watch=false --include=path/to/file.spec.ts --filter="<pattern>"` |

Notes, all confirmed by running both scenarios locally (Vitest 5.0.1, Jest 30.x, Angular CLI 22.1.8 with its
built-in Vitest 4.0.8 runner) in `$TMPDIR/iru-verify/typescript/test/{vitest-proj,jest-proj,ng-app}`:

- **An unmatched file/directory selector is a hard failure for every runner tested, not a silent zero.**
  - `vitest run <unmatched-path>` prints `No test files found, exiting with code 1` and exits **1**.
  - `jest <unmatched-path>` prints `No tests found, exiting with code 1` (plus a hint about
    `--passWithNoTests`) and exits **1** by default — the plain `jest` CLI does *not* pass silently on zero
    matched files unless the project's own config sets `passWithNoTests: true` or the flag is passed explicitly.
    Treat a non-zero exit here as "selector matched nothing", the same as Vitest, rather than assuming Jest is
    lenient — it only is if the project opted in.
  - `ng test --watch=false --include=<unmatched-glob>` fails before any tests run, with `Error: No tests found
    matching the following patterns: - Included: <glob>` and exits **1** (same underlying Vitest runner).
- **An unmatched `-t`/`--filter` *name* pattern, against files that *do* match, is not a failure for any runner
  tested.** All three report every test in the matched file(s) as **skipped** and exit **0**
  (`Test Files 1 skipped (1)` / `Tests 2 skipped (2)` for Vitest and `ng test`; `Test Suites: 1 skipped, 0 of 1
  total` / `Tests: 2 skipped, 2 total` for Jest). Report a 0-matched-by-name run as "0 of N tests matched the
  name filter — nothing ran", not as "all passed", since a typoed `-t` value silently runs nothing but still
  exits 0.
- `ng test`'s selector flags differ in name from the other two runners: use `--include=<glob>` (not a bare
  positional path) for file/directory scope, and `--filter=<pattern>` (not `-t`) for the name pattern — `--filter`
  is a regular expression matched against suite + test names, per `ng test --help`.
- `CI=true` in the environment is worth setting defensively alongside the exact invocations above, in case a
  project's own tooling (wrapper scripts, `react-scripts`-style setups) keys off it to force non-watch/run-once
  behavior; it is not required for the `vitest run` / `jest` / `ng test --watch=false` forms themselves, since
  each already runs once and exits by explicit flag/subcommand rather than by CI auto-detection.

### The `e2e` selector (NestJS and Next.js only)

Without a leading `e2e` keyword, every row above runs the **unit** suite only — for NestJS that is the default
`vitest.config.ts`/`jest.config.ts`, which matches `*.spec.ts` and never `*.e2e-spec.ts`; for Next.js it is the
Vitest/Jest suite, never Playwright. `unit` as a leading keyword is accepted and means the same as no keyword.
A leading `e2e` keyword switches to the end-to-end suite, with the rest of the selector scoping it the same way:

| What the user wants | NestJS, Vitest (ESM) | NestJS, Jest (CommonJS) | Next.js, Playwright |
|---|---|---|---|
| Whole e2e suite | `vitest run --config ./vitest.config.e2e.ts` | `jest --config ./test/jest-e2e.json` | `playwright test` |
| One file | `vitest run --config ./vitest.config.e2e.ts test/books.e2e-spec.ts` | `jest --config ./test/jest-e2e.json test/books.e2e-spec.ts` | `playwright test e2e/books.spec.ts` |
| Name pattern | `... -t "<pattern>"` | `... -t "<pattern>"` | `playwright test -g "<pattern>"` |

(Use the config path the project's own `test:e2e` script names, per Step 1, in place of the scaffold defaults
shown.) `e2e` on a project that is neither NestJS nor Next.js is not supported — say so and stop rather than
guessing at a runner.

E2E runs depend on things unit tests don't, and a failure caused by them is an **environment failure**, not a test
failure — report it as such, naming the cause, and never as failing tests:

- **NestJS**: e2e specs boot the whole `AppModule` (`createNestApplication()` + `app.init()`), so they need whatever
  the module connects to at start-up — a database, Redis, a broker. Projects commonly provide it with Testcontainers
  (`testcontainers`/`@testcontainers/*` in `devDependencies`), which needs a running Docker/Podman daemon:
  `Could not find a working container runtime strategy`, `connect ECONNREFUSED` to a DB port, `getaddrinfo
  ENOTFOUND`, a TypeORM/Prisma/Mongoose connection error thrown from `beforeAll`, or a `beforeAll` hook timeout all
  belong here. Check `docker info` first when the project uses Testcontainers; if the daemon isn't reachable, report
  "NestJS e2e not run: Docker unavailable" instead of running and reporting every spec as failed. Container-backed
  runs share databases, so a caller running several of them (e.g. a `*-code-one-task-group` skill) is responsible
  for serializing them — this skill runs exactly one invocation and never in parallel with itself.
- **Next.js / Playwright**: the `webServer` command (`next build && next start`) must succeed and the browsers must
  be installed (`npx playwright install` — this skill never runs it unprompted, since it downloads browser
  binaries). `Executable doesn't exist at ...` (browsers missing), `Error: Timed out waiting ... from config.webServer`,
  `Error: Process from config.webServer was not able to start`, or a `next build` compile error printed before any
  test ran are environment/build failures, not test failures.

## Step 3 — Run with a JSON reporter and parse it

Always keep the runner's normal console reporter for a human glancing at the log, and add a JSON reporter written
to a scratch file so this skill parses structured results instead of screen-scraping. Flag names and output shape
differ per runner — do not mix them up:

| Runner | Command | JSON flag(s) |
|---|---|---|
| Vitest | `npx vitest run [scope] --reporter=default --reporter=json --outputFile=<path>.json` | `--reporter=json` (repeatable, camelCase `--outputFile`) |
| Jest | `npx jest [scope] --json --outputFile=<path>.json` | `--json` is a boolean flag, not a reporter name; `--outputFile` still writes the file while the normal console summary still prints |
| `ng test` | `npx ng test --watch=false [scope] --reporters=default --reporters=json --output-file=<path>.json` | `--reporters` (plural, repeatable) and kebab-case `--output-file`; verified both `default,json` and `json,default` orderings keep the console summary *and* write the file (the `--help` text warns `--output-file` "applies only to the first reporter", but in practice the JSON reporter still received the file regardless of its position in the two orderings tried) |

The NestJS e2e configs take the same Vitest/Jest flags (append `--config <e2e-config>`). Verified locally against a
fresh `@nestjs/cli` 12 ESM scaffold (Vitest 4.1) in `$TMPDIR/iru-verify/typescript/nest-next/nest-esm`: the
default `vitest run` with the JSON reporter picked up only `src/app.controller.spec.ts`, and `vitest run --config
./vitest.config.e2e.ts` with the same flags picked up only `test/app.e2e-spec.ts`, both writing the shape below.
A Next.js 16.4 scaffold with a `vitest.config.mts` (`@vitejs/plugin-react`, `jsdom`, `resolve.tsconfigPaths`)
wrote the same shape too, resolving the `@/*` alias without a plugin.

**Playwright** (Next.js `e2e` only) has its own JSON shape: `npx playwright test [scope] --reporter=list,json` with
`PLAYWRIGHT_JSON_OUTPUT_NAME=<path>.json` set in the environment (the `json` reporter otherwise writes to stdout,
interleaved with `list`). Parse `stats.expected` (passed), `stats.unexpected` (failed), `stats.flaky`, and
`stats.skipped` for the headline counts, then walk `suites[]` recursively (suites nest under `suites[].suites[]`)
to each `specs[].tests[]` whose `status` is `"unexpected"`: its name is the enclosing suite titles plus
`specs[].title`, its message the first line of `results[-1].error.message` (strip ANSI color codes). **Unverified
locally** — the Playwright browsers weren't installed on this machine; confirm the field names against the first
real report before relying on them.

All three runners (Jest, Vitest, and `ng test`'s Vitest runner) emit a **structurally compatible** JSON shape,
confirmed by inspecting the actual files produced above:

```jsonc
{
  "numTotalTests": 2,
  "numPassedTests": 1,
  "numFailedTests": 1,
  "success": false,
  "testResults": [
    {
      "name": "test/sample.test.ts",          // absolute/relative file path
      "status": "failed",
      "assertionResults": [
        {
          "fullName": "sample passes",
          "title": "passes",
          "status": "passed",
          "failureMessages": []
        },
        {
          "fullName": "sample fails",
          "title": "fails",
          "status": "failed",
          "failureMessages": ["AssertionError: expected 2 to be 3 // Object.is equality\n    at ..."]
        }
      ]
    }
  ]
}
```

Jest's JSON additionally nests each `failureMessages` entry's structured data under `failureDetails` and carries
extra bookkeeping fields (`invocations`, `numPassingAsserts`, `location`, `retryMessages`, …); ignore anything not
listed below.

Parse:
- `numTotalTests`, `numPassedTests`, `numFailedTests` for the headline counts.
- For each `testResults[].assertionResults[]` entry with `status === "failed"`, take `fullName` (or
  `ancestorTitles.join(" > ") + " > " + title` if `fullName` is absent) as the failing test's name, and the
  **first line** of `failureMessages[0]` as its assertion message — never dump the full stack trace.

Delete the scratch JSON output file after parsing (or write it under a `.gitignore`d/scratch location) so it
doesn't get committed as build noise.

## Step 4 — Report results

- If everything passed (or the run legitimately matched zero because the user's scope intentionally excludes
  something), state the counts briefly — don't paste the JSON or the full console log.
- If the selector matched no files at all (Step 2's non-zero-exit case for every runner), report that plainly as
  "selector `<x>` matched no test files" — not as 0 passed/0 failed, since that reads as a clean run.
- If a `-t`/`--filter` name pattern matched no individual tests within otherwise-matched files (Step 2's
  exit-0-but-all-skipped case), report that plainly too — it is easy to mistake for "all passed".
- State which suite ran (unit, or NestJS/Next.js `e2e`) whenever the project is NestJS or Next.js, so "all passed"
  on the unit suite is never read as e2e coverage. An e2e environment failure (Step 2) is reported as "e2e not
  run/aborted: <cause>" with the first line of the error — never as N failed tests.
- On failures, list each failing test's name (`fullName`) and the first line of its assertion message
  (`failureMessages[0]`'s first line) — nothing more per failure, and no noise about the passing tests.
- Do not attempt to fix failing tests or modify source/test code unless the user asks for that as a next step.
