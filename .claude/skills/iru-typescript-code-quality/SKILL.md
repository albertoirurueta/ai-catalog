---
name: iru-typescript-code-quality
description: Run this project's TypeScript static-analysis and formatting tools — ESLint (flat config, plus Oxlint when it's set up alongside ESLint), `tsc --noEmit` type-checking, Prettier `--check`, and Stylelint for CSS/SCSS when configured — then report every issue found (file, line, rule id, message), grouped by tool and classified by rule id. Invoke as `/iru-typescript-code-quality` to check the whole project, or `/iru-typescript-code-quality <path-or-glob>` to scope both the run and the report to specific files — unlike Java's Checkstyle/PMD/SpotBugs trio, ESLint/tsc/Prettier/Stylelint all accept a glob directly, so a scoped invocation narrows what actually runs. Detects the project's framework (npm/TypeScript library, React, Angular, React Native, Ionic, Hilla frontend) from `package.json` to pick the right invocation (`ng lint` vs `npx eslint`) and the right rule-id prefixes to classify against, and verifies each tool's own config file actually exists before trusting a "zero issues" result from it. When the prompt supplies a baseline (a prior per-rule-id issue count from an earlier run of this skill, e.g. captured by `iru-typescript-code-one-task-group` before a task group's changes), reports only the new-vs-baseline diff per rule id instead of the full current list. Use whenever the user wants a lint/type-check/format pass called out separately from `iru-typescript-test`/`iru-typescript-coverage`, instead of eyeballing `npm run lint` output.
model: haiku
---

# TypeScript Code Quality

Run ESLint, `tsc --noEmit`, Prettier, and (when configured) Stylelint and Oxlint directly, and report every issue
they find, grouped by tool and by rule id. This skill only runs static analysis/formatting checks and reports
results — it does not fix issues unless asked to as a follow-up.

## Step 1 — Detect the toolchain, verify it is actually wired, then run each tool

**Framework detection** (also used by `iru-typescript-test`/`-coverage`/`-tsdoc`/`-code-one-task*`, kept
consistent across all of them): inspect `package.json` — `@vaadin/hilla`/`hilla-spring-boot-starter` in a
Maven `pom.xml` or a `src/main/frontend/` directory → `hilla-frontend`; `expo` or `react-native` in dependencies
→ `react-native`; `@ionic/angular` or `@ionic/react` + `@capacitor/core` → `ionic`; `@angular/core` → `angular`;
`react` + `vite` → `react`; otherwise → `library`. This decides which rule-id prefixes matter (Step 3) and, for
Angular, how lint is invoked (below).

**Package manager**: from `packageManager` in `package.json`, else the lockfile present —
`package-lock.json` → npm, `pnpm-lock.yaml` → pnpm, `yarn.lock` → yarn. Run every command below through it:
npm → `npx <tool> ...`; pnpm → `pnpm exec <tool> ...`; yarn (classic or Berry) → `yarn <tool> ...` — all three
resolve the project's own locally-installed binary, which matters in a pnpm/Yarn PnP workspace where a bare
`npx`/global install may not see it. Examples below use the npm form; substitute per the detected manager.

**Verify each tool is actually wired before trusting a zero result from it** — the whole point of this step is
that "no issues found" must mean the tool ran against real rules, not that it had nothing to check:

- **ESLint**: an `eslint.config.{js,mjs,cjs,ts}` (flat config, ESLint ≥ 9) at the project root, OR — Angular
  only — an `angular.json` `architect.<project>.lint` target (the `@angular-eslint/builder` or
  `@angular/build:lint` builder). A legacy `.eslintrc*` means an ESLint 8-era project; the commands below still
  work (flat-config-only flags like `--no-error-on-unmatched-pattern` do too — they aren't flat-config-specific)
  but confirm the project hasn't already migrated before assuming a config shape.
- **tsc**: `tsconfig.json` must exist. If it is a **solution-style** file (a bare `"files": []` plus
  `"references": [...]`, common in Vite/Angular scaffolds that split `tsconfig.app.json`/`tsconfig.spec.json`/
  `tsconfig.node.json`), running `tsc --noEmit -p tsconfig.json` directly is a trap: it reports **zero errors
  unconditionally** because there is nothing in `files` for it to check and project references aren't followed
  in plain `--noEmit` mode — verified locally: a solution `tsconfig.json` with a type error in the referenced
  project's source exits `0` with no output under plain `-p`, but the same run under `tsc -b --noEmit` (or
  `tsc --noEmit -p tsconfig.app.json` against the concrete project file directly) reports it. Detect this shape
  (`"files": []` with no `"include"`, plus `"references"`) and use `tsc -b --noEmit -p tsconfig.json` in that
  case, or enumerate and run `--noEmit` against each referenced project file when `-b` isn't desired (e.g. to
  scope to just one project).
- **Prettier**: a `.prettierrc*`/`prettier.config.*` file, or a `"prettier"` key in `package.json`. Without one,
  Prettier still runs (it has built-in defaults) but "no issues" would just mean nothing violates the defaults,
  not that the project's own style is enforced — report this distinction if no config is found rather than
  treating the run as equivalent to a configured one.
- **Stylelint**: only relevant, and only run, when the project has `.css`/`.scss` files *and* a
  `stylelint.config.*`/`.stylelintrc*` file or a `"stylelint"` key in `package.json` exists. No config → skip it
  and say so explicitly; don't report a clean Stylelint pass for a project that never wired it.
- **Oxlint**: only run when `oxlint` is a `package.json` dependency, or an `oxlintrc.json` exists (some Vite/React
  scaffolds ship it as a fast pre-check alongside, not instead of, ESLint — see `iru-setup-react-web`). Skip
  silently otherwise; Oxlint is a bonus signal, not a substitute for a missing ESLint config.

If a tool's config is missing, **skip running it and say so in the report** ("ESLint: not configured, skipped")
instead of silently omitting it or reporting a misleading "0 issues".

**Run each configured tool, scoped to `[scope]` when given** (a file, directory, or glob):

1. **ESLint** —
   `npx eslint --format json --no-error-on-unmatched-pattern -o eslint-report.json [scope or default dirs]`.
   Verified locally against ESLint 10 (flat config): stdout carries the JSON array directly (also confirmed via
   `-o <file>`, which writes the identical JSON to disk instead — prefer `-o` so nothing else on stdout/stderr
   gets mixed in), one entry per linted file:
   `[{"filePath":"...","messages":[{"ruleId":"@typescript-eslint/no-unused-vars","severity":2,"message":"...",
   "line":2,"column":7,...}],"errorCount":4,"warningCount":0,...}]` — a file with `"messages":[]` was linted
   clean, it is still listed. `severity` is `1` (warn) or `2` (error). Exit code is `1` when any error-severity
   message exists (`0` if only warnings or none); a glob matching no files exits `2` with an "Oops!" message
   instead of JSON unless `--no-error-on-unmatched-pattern` is passed (verified: with the flag, a no-match run
   prints `[]` and exits `0` — always pass it so an empty scope reads as "nothing to check", not a crash).
   `--max-warnings <n>` fails the run once warning-severity messages exceed `<n>` (errors always fail regardless
   of this flag) — pass `--max-warnings 0` only if the caller wants warnings treated as failures too; otherwise
   omit it and just report warning counts separately from error counts.
   - **Angular**: prefer `npx ng lint --format json` (or `ng lint` if the Angular CLI is installed globally) over
     a direct `eslint` invocation when the `lint` architect target exists — it resolves the per-project ESLint
     config(s) and any Angular-specific include/exclude Angular's own schematic set up, which a bare `eslint .`
     may not match exactly in a multi-project workspace. `ng lint`'s `--format json` output is the same ESLint
     JSON array shape above (`ng lint` wraps `@angular-eslint/builder`, which wraps ESLint) — **unverified
     locally** (`ng`/Angular CLI isn't installed on this machine; only confirm this against a real Angular
     scaffold, e.g. right after `iru-setup-angular-web` runs).
   - **Oxlint**, when configured: `npx oxlint --format json [scope]`. Verified locally: output is a single JSON
     **object** (not an array like ESLint) — `{"diagnostics":[{"message":"...","code":"eslint(no-unused-vars)",
     "severity":"warning","filename":"src/index.ts","labels":[{"span":{"line":2,"column":7,...}}]}],
     "number_of_files":1,...}` — `code` is `eslint(<rule-name>)` or `typescript-eslint(<rule-name>)`, no
     `@typescript-eslint/` prefix. Exit code is `0` even with warning-severity diagnostics by default; pass
     `--deny-warnings` to make warnings fail the run too (verified: exit `1` then). Report Oxlint's findings as a
     separate line item from ESLint's — they're two different linters even when scoped to the same files, and a
     project running both typically uses Oxlint as a fast subset check, not a replacement.
2. **tsc** — `npx tsc --noEmit -p tsconfig.json --pretty false` (or the solution-file handling above). Verified
   locally: output is plain lines on stdout, one per diagnostic, `<file>(<line>,<col>): error TS<code>: <message>`
   e.g. `src/broken.ts(2,3): error TS2322: Type 'string' is not assignable to type 'number'.` — `--pretty false`
   is what keeps this to one line per diagnostic instead of the default multi-line colored/source-snippet format,
   which is much harder to parse reliably. Exit code is non-zero (`1` or `2` depending on invocation form — don't
   rely on the exact number, treat any non-zero exit as "errors were found" and any diagnostic line as one issue)
   when errors exist, `0` when clean. `tsc` has no glob/path argument to scope a single run to a subset of
   files under a project — it always type-checks the whole project graph `tsconfig.json` resolves; when `[scope]`
   is given, run the full command unscoped and then filter the reported lines to ones whose `<file>` prefix
   matches `[scope]`, the same "run whole, report scoped" pattern `iru-java-code-quality` uses for Checkstyle/PMD.
3. **Prettier** — `npx prettier --list-different [scope or "."]`. Verified locally: with `--check` (the more
   commonly documented flag), the human-readable progress line (`Checking formatting...`) goes to **stdout** but
   the actual `[warn] <file>` lines and the summary (`Code style issues found in the above file. Run Prettier
   with --write to fix.`) go to **stderr** — easy to lose if only stdout is captured. `--list-different` avoids
   that split: it prints just the relative paths of unformatted files, one per line, on stdout, with nothing else
   — prefer it. Exit code `1` when any file needs reformatting, `0` when all match, `2` when the glob matches no
   files at all (no equivalent of ESLint's `--no-error-on-unmatched-pattern` — verified, so treat exit `2` here
   as "nothing to check" rather than a real failure only after confirming the message says "No files matching").
   Prettier has no rule ids — every finding is filed under a single `formatting` bucket in Step 3.
4. **Stylelint**, only when configured (Step 1) and CSS/SCSS files are in scope —
   `npx stylelint "**/*.{css,scss}" --formatter json -o stylelint-report.json` (scope the glob to `[scope]`
   when given, e.g. `"<scope>/**/*.{css,scss}"`). Verified locally: the JSON formatter writes to **stderr** by
   default even though `--format json` writes it as a genuine JSON array — always pass `-o <file>` rather than
   trying to capture stdout, exactly like ESLint above. Shape:
   `[{"source":"...","errored":true,"warnings":[{"line":2,"column":10,"rule":"color-hex-length",
   "severity":"error","text":"Expected \"#FFFFFF\" to be \"#FFF\" (color-hex-length)"}]}]`. Exit code `2` when any
   warning has `severity: "error"`, `0` when clean.

If any tool's underlying build/compile step fails outright for a reason unrelated to lint/type rules (e.g. a
missing dependency, a syntax error severe enough that ESLint can't parse the file), report that and stop for that
tool — its report wasn't meaningfully generated, so don't read a stale or empty one.

## Step 2 — Read each generated report, scoped to the request if given

Every tool above (unlike Java's Checkstyle/PMD/SpotBugs) accepts a glob directly, so `[scope]` should already
have narrowed what ran wherever the tool supports it (ESLint, Prettier, Stylelint, Oxlint file arguments). Only
`tsc` always runs the whole project graph regardless of scope (Step 1.2) — for it, filter the parsed diagnostic
lines to ones whose leading `<file>` path matches `[scope]` before reporting, the same way `iru-java-code-quality`
extracts a matching `<file>`/`classname` block from a whole-project Checkstyle/PMD/SpotBugs report instead of
re-running the tool per class.

**With no argument** (project-wide): report every parsed entry from every tool that ran.

**With a `[scope]` argument**: for ESLint/Oxlint, only report entries whose `filePath`/`filename` falls under
`[scope]`; for Prettier/Stylelint, only report files under `[scope]`; for `tsc`, filter as above. An empty result
for a tool after filtering means that tool found nothing in `[scope]`, not that it didn't run — say so rather
than omitting the tool from the report.

## Step 3 — Classify by rule id, diff against a baseline if given, and report

Bucket every issue by rule id, grouped first by which linter/checker reported it (a scan bucketed only by rule id
without stating its source is ambiguous — `no-unused-vars` exists in both ESLint's core rules and Oxlint's):

- **ESLint** — bucket by the exact `ruleId` (`@typescript-eslint/no-unused-vars`, `@typescript-eslint/no-explicit-any`,
  `react-hooks/rules-of-hooks`, `@angular-eslint/no-empty-lifecycle-method`, bare ESLint-core ids like
  `prefer-const`/`eqeqeq` with no prefix). A `null` `ruleId` (parsing errors ESLint itself can't attribute to a
  rule) gets its own `<parse-error>` bucket.
- **Oxlint** — bucket by `code` verbatim (`eslint(no-unused-vars)`, `typescript-eslint(no-explicit-any)`) —
  report these separately from ESLint's buckets even when the rule name overlaps; they're different tools' runs.
- **tsc** — bucket by the `TS<code>` diagnostic code (`TS2322`, `TS2345`, `TS6133`, …), parsed out of each
  `error TS<code>:` line.
- **Prettier** — every finding is one `formatting` bucket (Prettier doesn't have rule ids); count of files listed
  by `--list-different`.
- **Stylelint** — bucket by the `rule` field (`color-hex-length`, `selector-class-pattern`, …).

**Report**: per tool, a total issue count and the config-not-found/skipped note if applicable; within each tool,
one line per rule-id bucket giving its count and, for a scope smaller than the whole project, the file:line list
too. State an overall total across all tools at the top.

**Baseline diff** — when the prompt that invoked this skill supplies a baseline (a prior run's per-rule-id counts
or issue list, e.g. `iru-typescript-code-one-task-group` capturing one before a task group's changes and asking
for the post-change result compared against it, the same contract `iru-java-code-one-task-group` uses for
`iru-java-code-quality`): compute the diff yourself — for each tool/rule-id bucket, report only issues that are
new since the baseline (a rule id whose count increased, or one that appears now but didn't in the baseline; a
specific new file:line entry when the baseline was itemized rather than just counts) — never report the full
current list next to the full baseline for the caller to diff themselves. A rule id whose count decreased or
stayed the same is not a regression and is omitted from this diff entirely, even though it's still reported in
the plain (non-baseline) count above it. State explicitly when a tool couldn't be diffed because it wasn't run in
the baseline (skipped/not configured then) — treat every one of its current issues as new in that case.

Do not attempt to fix any of the issues found, or modify ESLint/tsc/Prettier/Stylelint configuration — that's a
follow-up the user drives explicitly.
