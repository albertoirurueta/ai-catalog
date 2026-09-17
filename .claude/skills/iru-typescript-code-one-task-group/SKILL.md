---
name: iru-typescript-code-one-task-group
description: Implement one bucket of TypeScript tasks from a plan's task group end-to-end — captures a single pre-change quality baseline for the whole bucket, runs `iru-typescript-code-one-task` once per task (in parallel agents when the group is marked parallelizable) to implement each one and its tests, then validates the entire bucket once: license headers, TSDoc, scoped tests, an 80% coverage check, a full-suite run, and a code-quality regression check against that one baseline. `iru-typescript-code-one-task` itself checks off each task/sub-task's box in `implementation_plan.md` the moment that task finishes (with a "group validation pending" note), so an interrupted run doesn't re-attempt already-finished tasks; this skill backfills any checkbox that didn't land — a rare concurrent-write race when several tasks finish at nearly the same moment — and replaces each task's pending note with the final coverage/quality outcome once group validation passes, notifying the user as each phase completes rather than waiting until the whole bucket is done. If group validation surfaces a regression traceable to a specific task, that task's implementation is revised and the affected checks re-run, instead of re-validating the whole bucket per task. Invoke as `/iru-typescript-code-one-task-group <bucket text>`, passing every task/sub-task in the bucket, each with its own text, plus the group's `Parallelizable` verdict and any relevant "Current code state" context. Equivalent to `iru-java-code-one-task-group` for npm/TypeScript projects; used by `iru-code-one-task-group`, which invokes this once per plan group for its TypeScript-tagged tasks.
model: sonnet
allowed-tools: Read Edit Write Bash(npm *) Bash(npx *) Bash(pnpm *) Bash(yarn *) Bash(git status *) Bash(git diff *) Bash(git log *) Bash(find *) Bash(grep *) Bash(ls *) Skill Agent
---

# Implement one task-group bucket (TypeScript)

Carry out every TypeScript task in one plan-group bucket end to end: capture one quality baseline for the whole
bucket up front, implement each task (in parallel where safe), then validate everything the bucket touched in a
single consolidated pass instead of once per task — this is what cuts the token cost and wall-clock time this
catalog's per-task validation used to spend redundantly. It is the npm/TypeScript counterpart to
`iru-java-code-one-task-group` — same shape, but built on `iru-typescript-code-quality`, `iru-typescript-test`,
`iru-typescript-coverage`, and `iru-typescript-tsdoc`. It uses a medium model on purpose: the plan already carries
the hard reasoning; this skill drives execution of it.

## Step 1 — Detect the toolchain once, then capture one pre-change quality baseline for the whole bucket

Before anything else, detect once — and reuse for every step below rather than re-deriving it per gate call — the
same framework/runner/package-manager facts `iru-typescript-test`, `-coverage`, `-code-quality`, `-tsdoc`, and
`-code-one-task` each detect on their own: read `package.json` (and the root `pom.xml`/`src/main/frontend/` for a
Hilla-hosted frontend) to classify the project as `hilla-frontend` / `react-native` / `ionic` / `angular` /
`react` / `library`; read `package.json`/`angular.json` to identify the test runner (Vitest, Jest, or the Angular
CLI's `@angular/build:unit-test` builder); read `packageManager` in `package.json`, else the lockfile present
(`package-lock.json` → npm, `pnpm-lock.yaml` → pnpm, `yarn.lock` → yarn) to identify the package manager. This is
what tells Step 3.5 which full-suite command to run (`npm test` / `pnpm test` / `yarn test`) and lets every gate
prompt below name the exact invocation the matching skill (or its documented fallback) expects, instead of making
each gate re-detect the same facts independently.

Then collect the set of file(s)/module(s) every task in this bucket is expected to touch (from each task's own
description). Capture a single pre-change quality baseline covering all of them by delegating to the
`iru-gate-runner` agent rather than running `iru-typescript-code-quality` directly: `Agent({description: "Capture
pre-change quality baseline for task group", subagent_type: "iru-gate-runner", prompt: "Invoke Skill({skill:
\"iru-typescript-code-quality\", args: \"<file1,file2,...>\"}), then report back only the list of issues found for
these files."})`. `iru-gate-runner` runs in its own separate context and reports back just the issue list, keeping
unneeded report content out of the main context window. Record the returned issues as this bucket's pre-change
baseline — an empty baseline if every file is new. This is what Step 3.6's quality check compares against, so it
flags only issues this bucket's tasks introduce, not pre-existing ones. Skip this baseline capture if the
`iru-typescript-code-quality` skill is unavailable in this repository.

## Step 2 — Implement each task via `iru-typescript-code-one-task`

For every task in the bucket, invoke `iru-typescript-code-one-task` — it implements exactly what the task
specifies and writes/updates its tests, nothing more (license headers, TSDoc, and all validation now live here
instead).

- **Bucket marked `Parallelizable: yes`**: invoke `iru-typescript-code-one-task` for every task in the bucket
  concurrently — issue all of the `Agent` calls below together, in the same response, so they run in parallel
  rather than one after another:
  ```
  Agent({
    description: "Implement <task N> via typescript-code-one-task",
    subagent_type: "iru-isolated-skill-executor",
    prompt: "Invoke Skill({skill: \"iru-typescript-code-one-task\", args: \"<the task's full text, including its exact
      implementation_plan.md checkbox line(s) for itself and its sub-tasks, its sub-tasks' own text, and any
      relevant Current code state context>\"}). Report back: the files touched, the tests added/updated, and
      whether the task stopped on a blocker instead of finishing.",
    run_in_background: false
  })
  ```
- **Bucket marked `Parallelizable: no`**: invoke them one at a time, in the plan's order, waiting for each to
  finish before starting the next — the plan marked this bucket non-parallel because its tasks have a real
  ordering dependency (e.g. one task's code depends on another's, or two tasks would touch the same file).

`iru-typescript-code-one-task` already checks off that task's own checkbox (and its sub-tasks') in
`implementation_plan.md` itself, with a "group validation pending" note, before it reports back — e.g. `- [x]
Task 2. **Implement `useOrderTotal`** — implemented, tests added; group validation pending.` As each task's agent
reports back (whether run in parallel or sequentially), re-read `implementation_plan.md` and confirm that box is
actually checked; if it isn't (a rare concurrent-write race when two tasks in a parallel bucket finished at
nearly the same moment and one edit clobbered the other), flip it yourself now, using the same note. Notify the
user that this specific task's implementation and tests landed. This is what makes progress visible per task as
it happens, even though full validation is deferred to Step 3.

If a task's agent reports it stopped on a blocker, record it and skip validating that specific task's code in
Step 3 below (there's nothing finished to validate) — surface the blocker in this skill's own Step 5 report
without blocking the rest of the bucket's already-finished tasks from being validated.

## Step 3 — Validate the whole bucket once

Once every task that didn't block has been implemented (Step 2), first derive the validation scope: the union of
the file(s) each task's agent reported as touched (Step 2), cross-checked against `git status` and `git diff
--name-only` (plus `git diff --name-only --cached` for anything already staged) run fresh right now — a task's own
report can miss a file it changed as a side effect (e.g. a barrel `index.ts` re-export, a generated `angular.json`
edit), and the plain diff catches those too. Use this combined file list as the scope for every gate below. Then
run the following once for the entire bucket — not once per task:

1. **License headers**, for every file in the bucket's scope, by delegating to `iru-gate-runner`: `Agent({description:
   "Add license headers for task group", subagent_type: "iru-gate-runner", prompt: "Invoke Skill({skill:
   \"iru-check-license\", args: \"<file1,file2,...>\"}) scoped to every file this bucket's tasks added or modified.
   Report back only which files were missing a header vs. fixed vs. already compliant, and — if no header
   convention existed anywhere in the repo — whether the user chose to skip or generate one."})`. If the user
   chose to skip header generation, respect that choice for the rest of this run. Skip this item if
   `iru-check-license` is unavailable in this repository.
2. **TSDoc**, for the same file scope, by delegating to `iru-gate-runner`: `Agent({description: "Update TSDoc for
   task group", subagent_type: "iru-gate-runner", prompt: "Invoke Skill({skill: \"iru-typescript-tsdoc\", args:
   \"<file1,file2,...>\"}) scoped to every file this bucket's tasks added or modified. Report back only which
   exported symbols were documented/completed and in which files, and whether the doc-build verification (TypeDoc
   or Compodoc, per the project's flavor) passed."})`. If it reports the doc build failed, fix the reported issues
   and re-invoke until it reports success. Skip this item if `iru-typescript-tsdoc` is unavailable in this
   repository.
3. **Scoped tests**, for every test file affected across the bucket, by delegating to `iru-gate-runner`: `Agent({description:
   "Run tests for task group", subagent_type: "iru-gate-runner", prompt: "Invoke Skill({skill: \"iru-typescript-test\",
   args: \"<file/directory/name-pattern selector covering every test affected by this bucket>\"}) (fall back to
   `npx vitest run <selector>` / `npx jest <selector>` / `npx ng test --watch=false --include=<glob>`, per the
   detected runner, directly if the typescript-test skill is unavailable). If everything passes, report back only
   that all tests passed. If anything fails, report back only the failing test names, the failure reason, and the
   assertion message for each."})`. If failures are reported, identify which task's code they trace back to (by
   file), fix that task's implementation and/or tests, and re-invoke this same check — repeat until it reports all
   tests passed. Don't move on with a red test.
4. **Coverage**, for every changed/new file across the bucket, by delegating to `iru-gate-runner`: `Agent({description:
   "Check coverage for task group", subagent_type: "iru-gate-runner", prompt: "Invoke Skill({skill:
   \"iru-typescript-coverage\", args: \"<selector covering the bucket's affected tests, plus every target file this
   bucket changed or added>\"}) (fall back to the detected runner's own coverage invocation — `npx vitest run
   --coverage --coverage.reporter=json-summary`, `npx jest --coverage --coverageReporters=json-summary`, or `npx ng
   test --coverage --watch=false --coverage-reporters=json-summary` — and reading
   `coverage/coverage-summary.json` if unavailable). Report back, per target file, its line coverage percentage and
   branch coverage percentage."})`. For any file under 80%, add tests for its uncovered lines/branches (via the
   task that owns that file), re-run Step 3.3 to confirm, then re-check here.
5. **Full suite**, to catch regressions this bucket's changes may have caused elsewhere, by delegating to
   `iru-gate-runner`: `Agent({description: "Run full test suite", subagent_type: "iru-gate-runner", prompt: "Run
   `npm test`" (substitute `pnpm test` / `yarn test` per the package manager detected in Step 1). If everything
   passes, report back only that all tests passed. If anything fails, report back only the failing test names, the
   failure reason, and the assertion message for each."})`. Fix any regression, then re-invoke until it reports
   all tests passed.
6. **Code quality**, for the same file scope as Step 1, by delegating to `iru-gate-runner`: `Agent({description: "Check
   for new quality issues in task group", subagent_type: "iru-gate-runner", prompt: "Invoke Skill({skill:
   \"iru-typescript-code-quality\", args: \"<file1,file2,...>\"}). Compare the reported issues against this pre-change
   baseline: <baseline from Step 1>. Report back only the issues that are newly appearing (not present in the
   baseline)."})`. Any issue reported is a regression introduced by this bucket — trace it to the task that owns
   the affected file, fix it (then re-run Steps 3.3–3.5 to confirm the fix didn't break anything), and re-check
   until none remain. Leave a new issue in place only if fixing it is genuinely unavoidable (e.g. it would
   contradict what its task explicitly specifies) — record that, and why, for Step 4. Skip this item if
   `iru-typescript-code-quality` is unavailable in this repository.

## Step 4 — Finalize progress notes and notify the user

Once Step 3 passes clean for the bucket (or leaves only explicitly-accepted unavoidable issues), update each
task's note in `implementation_plan.md` — replacing the "group validation pending" placeholder from Step 2 — with
the final outcome: coverage achieved and code-quality result for that task's own file(s), e.g. `- [x] Task 2.
**Implement `useOrderTotal`** — tests in useOrderTotal.test.ts (94% line coverage), no new ESLint/tsc/Prettier
issues.` Save the file, then notify the user that group validation completed and summarize the bucket-wide result
(tests, coverage, quality, doc/license outcome).

If any task was recorded as blocked in Step 2, leave its checkbox unchecked and its blocker note in place — do
not run Step 3's validation against a task that never finished implementing.

## Step 5 — Report the bucket's outcome

Hand control back to the caller (`iru-code-one-task-group`) with a summary covering the whole bucket: per task, the
files touched, tests added/updated, coverage achieved, and code-quality outcome — including whether a new issue
was left in place as unavoidable and why, whether license-header generation was skipped by the user, and which
task(s), if any, stopped on a blocker (with enough detail for the caller to surface it further up).
`implementation_plan.md`'s checkboxes are already checked (by `iru-typescript-code-one-task` itself, backfilled
here in Step 2 if needed) and finalized with their validation outcome (Step 4), and the user-facing progress
notifications have already gone out (Steps 2 and 4) — the caller does not need to redo that bookkeeping for this
bucket.
