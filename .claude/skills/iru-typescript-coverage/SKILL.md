---
name: iru-typescript-coverage
description: Run the project's TypeScript/JavaScript test runner (Vitest, Jest, or Angular's `ng test`) with
  coverage enabled, then read the exact coverage percentages from the generated `coverage/coverage-summary.json`
  (falling back to `coverage/lcov.info`'s `LF`/`LH`/`BRF`/`BRH` records via `awk` when the summary is missing or a
  specific file's row isn't in it) — reporting line/branch percentage totals, per-file percentages scoped to the
  given selector, and the uncovered line ranges (collapsed from consecutive `DA:<line>,0` records) for files under
  the bar. Invoke as `/iru-typescript-coverage [scope]`, where `[scope]` is a file path, a directory, or a name
  pattern — the same selector syntax as the `iru-typescript-test` skill's — or with no argument to run the whole
  suite and report whole-project coverage. Detects the test runner (Vitest, Jest, or Angular's `@angular/build:
  unit-test` builder) and package manager the same way `iru-typescript-test` does, and reports "coverage not
  wired" (naming the missing package/config) instead of a false 0%/100% when the coverage provider isn't
  installed. Use whenever the user wants to check, or verify a bar (e.g. "at least 80% line coverage") for, a
  TypeScript/JavaScript file, directory, or the whole project, instead of eyeballing a runner's console output.
model: haiku
---

# TypeScript Coverage

Run the project's test runner with coverage enabled and report the exact, measured coverage percentage for the
scope the user cares about. This skill only measures and reports coverage — it does not add tests or modify
source/test code unless asked to as a follow-up.

## Step 1 — Determine the test scope, runner, and package manager

If the user (or the calling skill) gave a `[scope]`, it uses the exact same selector syntax as the
`iru-typescript-test` skill's: a file path (`src/utils/parse.ts`), a directory (`src/features/auth/`), or a name
pattern (`*Service`, `auth`). If no scope was given, run the whole suite and report whole-project coverage.

Detect the runner and package manager the same way `iru-typescript-test` does (the shared rule from this catalog's
TypeScript conventions):

- **Test runner** — read `package.json` devDependencies (and, for Angular, the project's `angular.json`):
  - `vitest` present → **Vitest**.
  - `jest` or `jest-expo` present → **Jest**.
  - `angular.json` has a project whose `architect.test.builder` is `@angular/build:unit-test` → **Angular CLI**
    (`ng test`), which itself runs on Vitest under the hood but is driven through `ng`/`ng test`'s own flags, not
    a bare `vitest` invocation. (An older Angular project pinned to the legacy `@angular-devkit/build-angular:
    karma` builder uses Karma + Istanbul instead — its coverage output layout was not exercised locally; see
    "Unverified" below.)
- **Package manager** — `packageManager` field in `package.json`, else lockfile: `package-lock.json` → npm,
  `pnpm-lock.yaml` → pnpm, `yarn.lock` → yarn. Prefix commands with the matching runner (`npm run`/`npx`, `pnpm`,
  `yarn`) — the commands below are written with `npx`/direct binary names; substitute accordingly.

Important, same caveat as `iru-java-coverage`: coverage is only recorded for code actually exercised by the tests
that run in this invocation. If the scope's source file is covered by tests spread across multiple test files, a
selector narrow enough to exclude some of them will undercount it — when in doubt, prefer a broader selector (the
containing directory, or the full suite) over a narrow one.

## Step 2 — Determine the target file(s) to report on

- If the user (or the calling skill) explicitly named target file(s), use those.
- Otherwise, infer them from the selector: a test file `src/math.test.ts` / `src/__tests__/math.test.ts` targets
  `src/math.ts`; a directory selector targets every source file under it; a name pattern can't be inferred by
  name — report on every file the coverage report actually lists for that run (Step 4 surfaces all of them), or
  ask the user which file(s) they care about if the run touches many unrelated ones.
- **A file that has zero tests still needs to appear in the report** to be reported as 0% rather than silently
  omitted. By default all three runners only instrument files that were actually imported by a test during the
  run — an untested file is simply absent from `coverage-summary.json`/`lcov.info`, not shown at 0%. Force it in
  with the runner's include flag (below), scoped to the selector's directory/pattern (verified locally: an
  untested sibling file is absent without the include flag and present at 0% with it, for both Vitest and Jest).

## Step 3 — Run the coverage build

First confirm the coverage provider is actually installed — do not trust a "0%"/"100%" or an empty report without
checking this first:

- **Vitest** needs `@vitest/coverage-v8` (or `@vitest/coverage-istanbul`) in `package.json`. If it's missing, the
  run exits non-zero with `MISSING DEPENDENCY  Cannot find dependency '@vitest/coverage-v8'` (verified locally) —
  report "coverage not wired: @vitest/coverage-v8 is not installed", not a coverage number.
- **Jest** has coverage built in — no extra package needed. If a scope's source file isn't matched by any
  `collectCoverageFrom`/`coverageProvider` config, it's silently excluded rather than an error, so check `Step 2`'s
  include flag was actually passed instead of trusting an all-green report.
- **Angular CLI (`ng test --coverage`)** with the default Vitest runner also needs `@vitest/coverage-v8` (or
  `@vitest/coverage-istanbul`) installed — verified locally: without it, `ng test --coverage` fails with the same
  "Code coverage requires either '@vitest/coverage-v8' or '@vitest/coverage-istanbul' to be installed" message.
  **Version-pin it to match the Vitest version `@angular/build` bundles internally** — installing the coverage
  package's `latest` (e.g. `5.x`) against an older bundled Vitest (e.g. `4.1.11`) produces a real, verified
  failure: `Running mixed versions is not supported` followed by `AssertionError: coverageFilesDirectory is
  required`, which aborts the whole run. Check the installed version with
  `npm ls vitest` (it prints the version `@angular/build` bundles, deduped) or read
  `node_modules/@angular/build/package.json`'s own `vitest` dependency, then install the exact matching
  `@vitest/coverage-v8@<that version>`. If installing at all fails, report "coverage not wired" the same way.

Run the coverage command for the detected runner, scoped to the selector from Step 1 when one is scriptable, and
passing the include flag from Step 2 for the scope's directory/pattern so untested files aren't dropped:

```bash
# Vitest
npx vitest run [selector] --coverage --coverage.reporter=lcov --coverage.reporter=json-summary \
  --coverage.include='<scope-glob>'   # e.g. src/features/auth/**/*.ts — omit to cover the whole project

# Jest
npx jest [selector] --coverage --coverageReporters=lcov --coverageReporters=json-summary \
  --collectCoverageFrom='<scope-glob>'

# Angular CLI (verified locally: matching @vitest/coverage-v8 version required, see above)
npx ng test --coverage --coverage-reporters=lcov --coverage-reporters=json-summary --watch=false \
  --coverage-include='<scope-glob>'
```

Notes verified locally:

- Neither `--coverage.reporter=lcov`/`json-summary` (Vitest) nor `--coverageReporters=lcov`/`json-summary` (Jest)
  print a text coverage table to the console — only the pass/fail test summary prints. Do not wait for a console
  table; go straight to Step 4's files. (Add a `text` reporter alongside if a human will read the terminal output
  directly, but it changes nothing this skill reads.)
- `--coverage.include`/`--collectCoverageFrom`/`--coverage-include` accept glob patterns and are additive to
  whatever base `include`/`collectCoverageFrom` the project's own config already sets — pass the scope's own glob,
  don't replace the project's config.
- `ng test`'s full verified flag surface (`npx ng test --help` inside a real Angular workspace, Angular CLI
  22.1.8, `@angular/build:unit-test` builder): `--coverage` (boolean, off by default), `--coverage-exclude`,
  `--coverage-include`, `--coverage-reporters` (choices: `cobertura`, `html`, `json`, `json-summary`, `lcov`,
  `lcovonly`, `text`, `text-summary`), `--runner` (`karma`|`vitest`, default `vitest`), plus the shared `--filter`/
  `--include`/`--exclude`/`--watch` flags `iru-typescript-test` uses for scoping.
- If the build/run fails (compile error or test failure), report that failure — don't attempt to read a coverage
  report that wasn't (re)generated for this invocation. Delete a stale `coverage/` directory before re-running
  when in doubt, since these commands don't always start from a clean slate the way `mvn clean` does.

## Step 4 — Read the exact coverage from the report

**Report path**, verified locally:
- Vitest / Jest (project root `coverage/` output): `coverage/coverage-summary.json`, `coverage/lcov.info`.
- Angular CLI: **`coverage/<project-name>/coverage-summary.json`**, `coverage/<project-name>/lcov.info` — nested
  one level under the Angular project name from `angular.json`, not directly under `coverage/`.

**Totals and per-file percentages** — read `coverage-summary.json`. Its shape (identical for Vitest, Jest, and
Angular CLI, verified locally) is a single JSON object: a `"total"` key with the whole run's aggregate, plus one
key per covered file keyed by that file's **absolute** filesystem path (not relative to the project root) — match
by suffix, not exact string equality:

```bash
node -e '
const s = require("./coverage/coverage-summary.json");
const suffix = process.argv[1];   // e.g. "src/math.ts" — the scope from Step 1/2
console.log("total:", "lines", s.total.lines.pct + "%,", "branches", s.total.branches.pct + "%");
for (const [file, m] of Object.entries(s)) {
  if (file === "total" || !file.endsWith(suffix)) continue;
  console.log(file, "->", "lines", m.lines.pct + "%,", "branches", m.branches.pct + "%,", "functions", m.functions.pct + "%");
}
' "src/math.ts"
```

Each per-file entry also carries `statements` and `functions` alongside `lines`/`branches` — report lines and
branches (and functions when relevant), the same fields `iru-java-coverage` reports for JaCoCo.

If `coverage-summary.json` is missing (an older reporter set, or a config that only wrote `lcov.info`), or a
target file's suffix isn't found in it, fall back to `lcov.info` for that file/the totals:

```bash
# Whole-run totals from lcov.info (sum LF/LH/BRF/BRH across every SF: block)
awk -F: '/^LF:/{lf+=$2} /^LH:/{lh+=$2} /^BRF:/{brf+=$2} /^BRH:/{brh+=$2}
  END{printf "lines: %d/%d (%.2f%%)\nbranches: %d/%d (%.2f%%)\n", lh,lf,(lf>0?100*lh/lf:0), brh,brf,(brf>0?100*brh/brf:0)}' \
  coverage/lcov.info

# One file's block (SF: path is relative to the project root, unlike coverage-summary.json's keys)
awk -v f='src/math.ts' '$0=="SF:"f{p=1} p{print} p&&/^end_of_record$/{p=0}' coverage/lcov.info
```

(Both `awk` one-liners verified locally against real Vitest/Jest/Angular CLI `lcov.info` output.)

**Uncovered line ranges** — always come from `lcov.info`'s `DA:<line>,<hit-count>` records (`coverage-summary.json`
has no line-level detail), scoped to one file's `SF:`…`end_of_record` block, then collapsed from individual line
numbers into ranges:

```bash
awk -v f='src/math.ts' '$0=="SF:"f{p=1} p&&/^DA:/{split($0,a,"[,:]"); if(a[3]==0) print a[2]} p&&/^end_of_record$/{p=0}' \
  coverage/lcov.info | sort -n | awk '
  { if (NR==1) { start=$1; prev=$1; next }
    if ($1==prev+1) { prev=$1; next }
    print (start==prev ? start : start"-"prev); start=$1; prev=$1 }
  END { if (NR>0) print (start==prev ? start : start"-"prev) }'
```

Verified locally against a file with both isolated uncovered lines (`11`, `17` → prints `11` and `17` each on
their own line) and a run of consecutive ones (`5,6,7` and `12,13` → prints `5-7` and `12-13`).

Branch coverage per line (`BRDA:<line>,<block>,<branch>,<hit-or-minus>`) is available in the same block if the
user wants branch-level detail beyond the aggregate percentage, but report it only if asked — the default report
is percentages plus uncovered line ranges, not the raw `BRDA` records.

If a target file doesn't appear in either report at all even with the include flag from Step 2, it means the glob
didn't match it (typo, wrong extension, outside `src/`) — report that explicitly rather than a false 0%.

## Step 5 — Report results

State, per target file, the line coverage percentage (and branch coverage when relevant to the discussion),
computed from the actual `coverage-summary.json`/`lcov.info` numbers — never estimate or guess, and never paste
the runner's raw console output, the full JSON file, or the full `lcov.info` file into the report. If the user's
bar is "at least N%": say clearly whether each file/the total meets it.

For files under the bar, give the uncovered line ranges from Step 4 (e.g. `src/math.ts: lines 66.66% — uncovered:
11, 17`) so the user (or a follow-up skill, e.g. `iru-typescript-generate-all-tests`) knows exactly where to add
tests, without needing to open the HTML report.

If coverage wasn't wired (Step 3's "coverage not wired" case), report that clearly instead of a percentage,
naming the missing package/config and the exact command that failed.

Do not add tests, modify source/test code, or re-run anything to try to raise coverage — that's a follow-up the
user (or another skill, e.g. `iru-code`, `iru-typescript-generate-all-tests`) drives explicitly.

## Unverified locally

- **Karma + Istanbul** (legacy `@angular-devkit/build-angular:karma` test builder, still valid on older Angular
  projects): its `karma.conf.js` `coverageIstanbulReporter`/`coverageReporter` config controls the output
  directory and reporter list itself rather than `ng test --coverage-reporters` flags, and the default output
  layout (`coverage/<project-name>/lcov.info` vs. flat `coverage/`) was not exercised — treat the path above as
  Vitest-runner-only until checked against a real Karma project.
- **pnpm and yarn** — only npm was exercised locally for every command above; the coverage commands themselves are
  package-manager-agnostic (they invoke the runner's own binary via `npx`/`pnpm exec`/`yarn`), but this wasn't
  re-run under pnpm/yarn to confirm no wrapper-specific quirk changes the report path.
- **React, React Native, Ionic, and Hilla-frontend scaffolds' own coverage config** — this skill's mechanics
  (Vitest/Jest + `coverage-summary.json`/`lcov.info`) were verified against a bare Vitest project, a bare Jest
  project, and a freshly-scaffolded Angular CLI app only; a framework-specific `vitest.config.ts`/`jest.config.js`
  (e.g. React Native's `jest-expo` preset, or a Hilla Vitest browser-mode config) may set its own `coverage.exclude`
  defaults (test setup files, generated Hilla endpoint clients) that change what shows up unscoped — scope
  explicitly with Step 1's selector when in doubt rather than trusting an unscoped project-wide run.
