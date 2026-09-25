---
name: iru-typescript-test
description: Run a TypeScript/npm project's unit test suite through whichever runner the project actually has wired — Vitest (`vitest run`), Jest (`jest`), or the Angular CLI's Vitest-backed unit-test builder (`ng test --watch=false`) — optionally scoped to a file, directory, or test-name pattern. Invoke as `/iru-typescript-test` to run everything, or `/iru-typescript-test <selector>` where `<selector>` is a file path, a directory, or a `-t "<name pattern>"` filter (combinable with a file/directory). Report-only: never fixes a failing test or modifies source/test code. Use whenever the user wants to run, re-run, or narrow down TypeScript/JavaScript unit tests instead of invoking the runner by hand.
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

## Step 3 — Run with a JSON reporter and parse it

Always keep the runner's normal console reporter for a human glancing at the log, and add a JSON reporter written
to a scratch file so this skill parses structured results instead of screen-scraping. Flag names and output shape
differ per runner — do not mix them up:

| Runner | Command | JSON flag(s) |
|---|---|---|
| Vitest | `npx vitest run [scope] --reporter=default --reporter=json --outputFile=<path>.json` | `--reporter=json` (repeatable, camelCase `--outputFile`) |
| Jest | `npx jest [scope] --json --outputFile=<path>.json` | `--json` is a boolean flag, not a reporter name; `--outputFile` still writes the file while the normal console summary still prints |
| `ng test` | `npx ng test --watch=false [scope] --reporters=default --reporters=json --output-file=<path>.json` | `--reporters` (plural, repeatable) and kebab-case `--output-file`; verified both `default,json` and `json,default` orderings keep the console summary *and* write the file (the `--help` text warns `--output-file` "applies only to the first reporter", but in practice the JSON reporter still received the file regardless of its position in the two orderings tried) |

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
- On failures, list each failing test's name (`fullName`) and the first line of its assertion message
  (`failureMessages[0]`'s first line) — nothing more per failure, and no noise about the passing tests.
- Do not attempt to fix failing tests or modify source/test code unless the user asks for that as a next step.
