---
name: iru-kmp-code-one-task-group
description: >-
  Implement one bucket of Kotlin Multiplatform (Android + iOS app) tasks from a plan's task group end-to-end — detects
  the project shape once (the `iru-setup-kmp-app` `shared/` + `androidApp/` + `iosApp/` layout or the wizard's single
  `composeApp/` module, the shared module's Android plugin, `ui: compose|native`, XcodeGen, macOS/Xcode availability),
  captures a single pre-change quality baseline for the whole bucket, runs `iru-kmp-code-one-task` once per task (in
  parallel agents when the group is marked parallelizable) to implement each one with its tests and per-target
  compile-check, then validates the entire bucket once, cheapest first, every check delegated to an `iru-gate-runner`
  agent so no raw report lands in this context — license headers via `iru-check-license`, KDoc via `iru-kmp-dokka`,
  scoped JVM/Android tests via `iru-kmp-test` (`target: android`), an 80% line-coverage gate via `iru-kmp-coverage`
  measured from the JVM/Android host runs only (Kotlin/Native iOS code is reported "not measurable" and never fails
  the gate), the full Android/JVM suite, a quality regression check via `iru-kmp-code-quality` (detekt, ktlint,
  Android Lint, SwiftLint) against that one baseline — and, last, the iOS stage (Kotlin/Native simulator tests plus
  the `iosApp` XCTest bundle via `iru-kmp-test` `target: ios`), macOS only, serialized repository-wide behind the
  shared atomic-`mkdir` `.integration-test.lock` (owner file, stale after 60 minutes, bounded ~45-minute wait,
  released on every exit path) and passed to the gate as `lock: held`; an unavailable iOS stage (not macOS, no full
  Xcode, no simulator runtime, lock wait timeout) is reported "unverified", never silently skipped or reported as
  passed. Scopes each gate by the module(s) the bucket touched (`shared`/`composeApp`, `androidApp`, `iosApp`) and by
  source set — a `commonMain` change runs every target's tests, `androidMain` only the Android host tests, `iosMain`
  only the iOS tests, `iosApp` Swift only the XCTest bundle. `iru-kmp-code-one-task` checks off each task's box itself
  with a "group validation pending" note; this skill backfills any that didn't land and replaces each note with the
  final outcome. Invoke as `/iru-kmp-code-one-task-group <bucket text>`, passing every task/sub-task in the bucket
  with its own text, the group's `Parallelizable` verdict, and any relevant "Current code state" context. The Kotlin
  Multiplatform counterpart to `iru-android-code-one-task-group`/`iru-swift-code-one-task-group`; used by
  `iru-code-one-task-group`, which invokes it once per plan group for its `kmp`-tagged tasks.
model: sonnet
allowed-tools: Read Edit Write Bash(./gradlew *) Bash(gradle *) Bash(xcodebuild *) Bash(xcrun *) Bash(xcodegen *) Bash(xcode-select *) Bash(uname *) Bash(git status *) Bash(git diff *) Bash(git log *) Bash(git rev-parse *) Bash(find *) Bash(grep *) Bash(ls *) Bash(cat *) Bash(date *) Bash(mkdir .integration-test.lock*) Bash(rmdir .integration-test.lock*) Bash(rm -f .integration-test.lock/owner) Skill Agent
---

# Implement one task-group bucket (Kotlin Multiplatform)

Carry out every `kmp` task in one plan-group bucket end to end: one quality baseline up front, implement each task
(in parallel where safe), then validate everything the bucket touched in a single consolidated pass instead of once
per task. It is the Kotlin Multiplatform counterpart to `iru-android-code-one-task-group` and
`iru-swift-code-one-task-group`, built on `iru-kmp-test`, `iru-kmp-coverage`, `iru-kmp-code-quality`, and
`iru-kmp-dokka`, each invoked through an `iru-gate-runner` agent so its report never lands in this context; fall back
to the explicit command shown only when a gate skill isn't installed in the consuming repository.

Three things shape the validation order:

1. **One change, several targets.** A `commonMain` change runs on the Android host (JVM) *and* in the iOS simulator;
   a test can pass on one and fail on the other. Scoping is by source set, not just by module (Step 1).
2. **Coverage is JVM-only.** Kover measures the Android host-test and `androidApp` unit-test runs; Kotlin/Native has
   no coverage tool. `commonMain` code is measured through `commonTest` on the JVM target, `iosMain` code is "not
   measurable" and never fails the 80% gate.
3. **The iOS stage boots a simulator and goes last, behind the lock.** `iosSimulatorArm64Test` boots a simulator
   itself and `xcodebuild test` drives one — two overlapping runs collide on simulator state. This skill takes the
   repository-wide `.integration-test.lock` once around the whole iOS stage (Step 3.7) and passes `lock: held` to the
   gate; the cheaper JVM gates run first so a bucket that's red on Android never holds the lock.

It uses a medium model on purpose: the plan carries the hard reasoning; this skill drives execution of it.

## Step 0 — Read this before running anything on a simulator

**Only one simulator-backed run may be in flight against this repository at any moment** — enforced across buckets
by the lock (Step 3.7a), within this bucket by never running iOS tests from Step 2's per-task agents (the per-task
skill only compile-checks), and within the run by issuing the iOS stage as a single gate call. The lock directory
lives at the **repository root** (`git rev-parse --show-toplevel`) — the same `.integration-test.lock` every other
group skill in this catalog uses (`iru-java-springboot-code-one-task-group`, `iru-nestjs-code-one-task-group`,
`iru-react-native-code-one-task-group`, …), so a polyglot repository serializes them all together. Never hold it while
implementing (Step 2) or while running JVM gates.

**Never both**: when this skill holds the lock it passes `lock: held` to `iru-kmp-test`/`iru-kmp-coverage`; when it
doesn't, it must not pass `lock: held`, and the gate takes the lock itself.

## Step 1 — Detect the shape and scope once, then capture one pre-change quality baseline

Detect once and reuse for every gate call below (the same facts `iru-kmp-code-one-task` and the gate skills detect):

- **Modules**: the KMP module(s) (`org.jetbrains.kotlin.multiplatform` applied — `shared`, or `composeApp` in the
  wizard layout), the Android app module (`androidApp`; absent in the wizard layout, where `composeApp` is the app),
  and `iosApp/` (XcodeGen `project.yml` or a committed `.xcodeproj`).
- **Host capability for iOS**: `uname -s` is `Darwin`, `xcode-select -p` points into `Xcode.app` (not only the
  Command Line Tools), and `xcrun simctl list runtimes` shows an iOS runtime. If any fails, the iOS stage will be
  reported **unverified** with that reason — decide it now so every note says so consistently.
- **Bucket scope**, from each task's text (paths win; otherwise the same inference `iru-kmp-code-one-task` Step 1
  uses), as a set of (module, source set) pairs, then the **targets to validate**:

  | Bucket touched | Android/JVM gates | iOS stage |
  |---|---|---|
  | `commonMain`/`commonTest` of a KMP module | that module's Android host tests | that module's Kotlin/Native simulator tests (+ XCTest if Swift calls changed API) |
  | `androidMain`/Android host-test set | that module's Android host tests | — |
  | `iosMain`/`iosTest` | — (coverage: not measurable) | that module's Kotlin/Native simulator tests |
  | `androidApp` | `:androidApp` unit tests | — |
  | `iosApp` Swift or `project.yml` | — | the `iosApp` XCTest bundle |
  | a public declaration of the framework-exported module | (per source set above) | **also** the `iosApp` XCTest bundle, since Swift callers compile against it |

Record this once as the bucket's **validation scope** and reuse it, rather than re-deriving per gate.

Then collect the files every task is expected to touch and capture a single pre-change baseline via
`iru-gate-runner`:

```
Agent({
  description: "Capture pre-change quality baseline for task group",
  subagent_type: "iru-gate-runner",
  prompt: "Invoke Skill({skill: \"iru-kmp-code-quality\", args: \"<file1,file2,...>\\nmodule: <module, when the bucket
    touches only one>\"}). Report back only the per-tool, per-rule-id issue counts and the issues for these files
    (detekt, ktlint, Android Lint, SwiftLint), and which tools were wired vs not wired.",
  run_in_background: false
})
```

Record it as the bucket's baseline — empty if every file is new. Step 3.6 diffs against it. Skip if
`iru-kmp-code-quality` isn't installed, and say so in Step 5.

## Step 2 — Implement each task via `iru-kmp-code-one-task`

- **Bucket marked `Parallelizable: yes`**: issue all the `Agent` calls together, in the same response:
  ```
  Agent({
    description: "Implement <task N> via iru-kmp-code-one-task",
    subagent_type: "iru-isolated-skill-executor",
    prompt: "Invoke Skill({skill: \"iru-kmp-code-one-task\", args: \"<the task's full text, including its exact
      implementation_plan.md checkbox line(s) for itself and its sub-tasks, its sub-tasks' own text, and any relevant
      Current code state context>\"}). Report back: the layout/module/source sets detected, the files touched
      (including Swift and project.yml), the tests added/updated per source set, the compile-check result per target,
      public API changes visible to Swift, any deviation from the skill's reference/, and whether the task stopped on a
      blocker. Compile-check only — do not run tests, coverage, linters, link the iOS framework, or boot a simulator:
      sibling agents run concurrently and the group's iOS stage is serialized behind a repository-wide lock.",
    run_in_background: false
  })
  ```
- **Bucket marked `Parallelizable: no`**: invoke them one at a time in the plan's order, waiting for each.

**One ordering constraint KMP imposes regardless of the verdict**: tasks where one adds an `expect`/interface in
`commonMain` and another implements its `actual`s or consumes it (in Kotlin or Swift), or two tasks editing the same
`expect`/`actual` set, the same Gradle build file, `iosApp/project.yml`, or the same Koin module, run sequentially
(declaration first). Check before fanning out; if the group was marked parallelizable, run just those sequentially and
note the deviation in Step 5.

As each agent reports back, re-read `implementation_plan.md` and confirm its box is checked; if not (a
concurrent-write race), flip it yourself with the same "group validation pending" note. Notify the user that this
task's implementation and tests landed. A task that stopped on a blocker — or whose compile-check failed for a reason
outside its scope that a re-run didn't clear — is recorded and excluded from Step 3's validation, without blocking the
rest of the bucket.

## Step 3 — Validate the whole bucket once

Derive the file scope first: the union of the files each agent reported, cross-checked against `git status`,
`git diff --name-only`, and `git diff --name-only --cached`. Drop generated output (`build/`, the generated
`iosApp.xcodeproj`). Then run, in this order — **3.1–3.6 gate the bucket; 3.7 runs only once they pass**. Skip any
Android/JVM item whose row in Step 1's table is empty for this bucket (e.g. an `iosMain`-only bucket has no Android
tests to run — say so rather than reporting a pass).

1. **License headers**, via `iru-gate-runner`: `Agent({description: "Add license headers for task group",
   subagent_type: "iru-gate-runner", prompt: "Invoke Skill({skill: \"iru-check-license\", args: \"<file1,file2,...>\"})
   scoped to every Kotlin, Swift, and build-script file this bucket's tasks added or modified. Report back only which
   files were missing a header vs. fixed vs. already compliant, and — if no header convention existed anywhere in the
   repo — whether the user chose to skip or generate one."})`. Respect a skip choice for the rest of the run. Skip if
   `iru-check-license` isn't installed.

2. **KDoc**, via `iru-gate-runner`: `Agent({description: "Update KDoc for task group", subagent_type:
   "iru-gate-runner", prompt: "Invoke Skill({skill: \"iru-kmp-dokka\", args: \"<ClassName1,ClassName2,... or Kotlin
   file paths — no test files, no Swift>\"}) scoped to every Kotlin declaration this bucket's tasks added or modified
   (expect declarations carry the KDoc; actuals only where behavior differs). Report back only which declarations
   were documented/completed and in which files and source sets, whether a module.md include had to be created or
   extended, and whether the Dokka build passed (with any unresolved-link warnings per source set)."})`. Fix and
   re-invoke until the build passes. Skip if `iru-kmp-dokka` isn't installed.

3. **Scoped Android/JVM tests**, via `iru-gate-runner`, once per KMP/app module in scope:
   `Agent({description: "Run Android/JVM tests for task group", subagent_type: "iru-gate-runner", prompt: "Invoke
   Skill({skill: \"iru-kmp-test\", args: \"<test class names, a wildcard, or the test source paths affected by this
   bucket in <module>>\\ntarget: android\\nmodule: <module>\"}). If that skill isn't installed, run
   `./gradlew <module>:testAndroidHostTest --tests '<pattern>'` (or `testDebugUnitTest` under androidTarget() and for
   :androidApp — repeat `--tests` after every task it should filter). If everything passes, report back only that. If
   anything fails, report back only the failing test names, the failure reason, and the first stack-trace line for
   each, and say whether any filter matched no tests."})`. Trace each failure to its task, fix, and re-invoke until
   green. A filter that matched nothing is a scoping mistake to fix, not a pass.

4. **Coverage — the 80% gate**, via `iru-gate-runner`:
   ```
   Agent({
     description: "Check coverage for task group",
     subagent_type: "iru-gate-runner",
     prompt: "Invoke Skill({skill: \"iru-kmp-coverage\", args: \"<ClassName1,ClassName2,... or source paths of every
       production class this bucket changed or added>\\nbar: 80\"}). Coverage comes from the JVM runs only (Android
       host tests including commonTest, and the Android app's unit tests); do not run the iOS app or any simulator.
       Report back, per target class, its module and source set, line and branch coverage percentage, uncovered line
       numbers for classes under 80%, and list iosMain/appleMain/nativeMain classes separately as not measurable.",
     run_in_background: false
   })
   ```
   **Gate: every changed/added class in a measurable source set (`commonMain`, `androidMain`, `androidApp`) at ≥ 80%
   line coverage.** `iosMain` classes are reported "not measurable (Kotlin/Native)" and never fail the gate — but if
   one holds real logic, say so in Step 5: that logic belongs in `commonMain` behind the `actual`. For anything under
   the bar, add tests via the task that owns the class (in `commonTest` for common code), re-run 3.3, re-check here.
   Composables count like any other `commonMain` code; a gap only reachable through a UI test that can't run on the
   JVM target in this project is an accepted exception to record with the reasoning, not something to paper over.

5. **Full Android/JVM suite**, via `iru-gate-runner`: `Agent({description: "Run full Android/JVM test suite",
   subagent_type: "iru-gate-runner", prompt: "Invoke Skill({skill: \"iru-kmp-test\", args: \"target: android\"}) with no
   scope (every module's Android host / JVM / app unit tests), or, if it isn't installed, run the modules' host-test
   tasks (e.g. `./gradlew :shared:testAndroidHostTest :androidApp:testDebugUnitTest`). If everything passes, report
   back only that; otherwise only the failing test names, reasons, and first stack-trace lines."})`. Fix regressions
   and re-invoke until green.

6. **Code quality**, diffed against Step 1's baseline, via `iru-gate-runner`: `Agent({description: "Check for new
   quality issues in task group", subagent_type: "iru-gate-runner", prompt: "Invoke Skill({skill:
   \"iru-kmp-code-quality\", args: \"<file1,file2,...>\\nbaseline: <baseline from Step 1>\"}) — detekt over every KMP
   source set, ktlint, Android Lint, and SwiftLint for iosApp when configured. Report back only newly appearing issues
   (not in the baseline), each with tool, rule id, file, and line, plus any tool not wired."})`. Any new issue is a
   regression this bucket introduced — trace it to its task, fix it, re-run 3.3 and 3.5, and re-check. Leave one in
   place only if fixing it would contradict what its task explicitly specifies, and record why. Skip if
   `iru-kmp-code-quality` isn't installed.

7a. **Acquire the repository-wide lock for the iOS stage** — immediately before 3.7, never earlier. Skip 3.7a–3.7b
   entirely (no lock, no run) when:

   - **Step 1's table has no iOS stage for this bucket** (an `androidMain`/`androidApp`-only bucket) — say so in Step 5.
   - **The host can't run iOS** (Step 1: not macOS, Command Line Tools only, no iOS simulator runtime) — report the
     iOS stage as **unverified (<reason>)** and continue to Step 4. Never "skipped" without a reason, never "passed".

   From the repository root:

   ```bash
   mkdir .integration-test.lock 2>/dev/null && echo ACQUIRED || echo HELD
   ```

   - **`ACQUIRED`** — immediately write `.integration-test.lock/owner` (via the `Write` tool) with this bucket's
     identifying text (task numbers/titles), "KMP iOS stage", the module(s), and `date -u +'%Y-%m-%dT%H:%M:%SZ'`.
     Ensure `.integration-test.lock/` is in the repository's root `.gitignore` (add the line if missing) — transient
     local state, never committed.
   - **`HELD`** — another group is running a simulator/integration stage. Tell the user this bucket is waiting (naming
     the holder from `cat .integration-test.lock/owner` if readable), then re-run the `mkdir` roughly every 30 seconds.
     Don't run iOS tests anyway.
   - **Stale lock** — `find .integration-test.lock -maxdepth 0 -mmin +60` returns the directory: its holder almost
     certainly died. Tell the user what the owner file says, break it
     (`rm -f .integration-test.lock/owner && rmdir .integration-test.lock`), acquire fresh, and say so in Step 5.
   - **Wait timeout** — still held (and not stale) after ~45 minutes: stop waiting, report the iOS stage as
     **unverified — blocked by a concurrent simulator/integration run**, continue to Step 4, and name it in Step 5.

7. **iOS stage** — only now, with 3.1–3.6 clean and the lock held, as one gate call:
   ```
   Agent({
     description: "Run iOS tests for task group",
     subagent_type: "iru-gate-runner",
     prompt: "Invoke Skill({skill: \"iru-kmp-test\", args: \"<scope covering the bucket's iOS side: the commonTest/iosTest
       test classes or paths of the touched KMP module(s), and/or iosApp/ when the XCTest bundle is in scope — or no
       scope to run every iOS test>\\ntarget: ios\\nlock: held\"}). This runs the Kotlin/Native simulator tests
       (iosSimulatorArm64Test, or iosX64Test on an Intel Mac) and, when in scope, the iosApp XCTest bundle via
       xcodebuild test. The caller already holds .integration-test.lock — do not acquire or release it. Run exactly this
       one invocation; wait for it rather than backgrounding it. Report back only: whether all iOS tests passed; for each
       failure the test name (and target), reason, and first message line; separately any environment problem (no
       simulator runtime, simulator boot failure, xcodegen missing, framework build failure in the Xcode pre-build
       phase) as opposed to an assertion failure; and whether a test filter matched no tests (the Kotlin/Native task
       exits 0 with no XML in that case — that is not a pass).",
     run_in_background: false
   })
   ```
   Run this agent on its own — never in the same response as another test-running agent.

   - **Environment failure** — report the stage as **unverified** with the cause, not as a code defect.
   - **A filter that matched nothing** — fix the scope and re-run; never record it as passed.
   - **Assertion failure** — trace it to its task and fix. Typical KMP causes the JVM run can't see: a missing or
     wrong `iosMain` `actual`, `Dispatchers.Main` assumptions, string/number formatting differences, a Swift caller
     broken by a public API change (default arguments dropped, a renamed declaration). Keep the lock across a quick
     fix-and-re-run; for a long debugging session release it (3.7b), fix, and re-acquire before re-running. If the fix
     touched Kotlin production code, re-run 3.3–3.6 afterwards.

7b. **Release the lock** as soon as 3.7's agent has reported back and any fix-and-re-run cycle is over:

   ```bash
   rm -f .integration-test.lock/owner && rmdir .integration-test.lock
   ```

   Release it on **every** exit path — pass, failure, environment failure, a blocked task, a user interrupt, or a hard
   stop. If you took the lock, you own releasing it before this skill returns.

## Step 4 — Finalize progress notes and notify the user

Confirm the lock is released (3.7b) if it was ever taken; release it now if a failure path skipped it.

Replace each task's "group validation pending" note in `implementation_plan.md` with the final outcome, quoting
coverage (JVM-measured) and the iOS result separately:

```
- [x] Task 3. **Add `SecureStore` with Keychain/Keystore actuals** — commonMain interface + actuals; tests in
  SecureStoreContractTest/IosSecureStoreTest (commonMain 92% lines; iosMain not measurable); iOS tests passed;
  no new detekt/ktlint/Lint issues.
```

If the iOS stage was unverified, say so with the reason — `iOS unverified (not macOS)` or `iOS unverified (lock held
by another group)` is actionable; silence reads as a pass. Leave blocked tasks unchecked with their blocker note.
Notify the user that group validation completed, with the bucket-wide result per module and per target.

## Step 5 — Report the bucket's outcome

Hand control back to `iru-code-one-task-group` with a summary covering the whole bucket:

- **The shape detected** (layout, Android plugin, `ui` mode, iOS host capability) and the validation scope (modules,
  source sets, targets).
- **Per task**: module/source sets, files touched, tests added/updated per source set, coverage achieved (and
  "not measurable" iOS classes), and the code-quality outcome.
- **The Android/JVM results** (3.3, 3.5) and **the iOS result** (3.7): passed, failed-and-fixed, **unverified** with
  the reason, or not in scope. Name any failure that showed on one target only, even once fixed.
- **Coverage exceptions accepted**, with reasoning; iOS-only logic that should move to `commonMain`.
- **How the lock behaved** whenever it wasn't an immediate uncontended acquire (wait time, a broken stale lock and its
  owner text, a timeout) and confirmation it was released.
- Whether a new quality issue was left in place as unavoidable, whether license-header generation was skipped,
  whether a sequential-ordering deviation was applied in Step 2, which tools were not wired, and which task(s), if
  any, stopped on a blocker.

`implementation_plan.md`'s checkboxes are already checked and finalized (Steps 2 and 4) and the user-facing
notifications have gone out — the caller doesn't need to redo that bookkeeping for this bucket.

**Warn explicitly**: every Gradle invocation needs `JAVA_HOME` on a JDK the build accepts (17/21) and the Android SDK
(`ANDROID_HOME` or `local.properties`) — a missing one fails at configuration time and looks like a gate failure; the
first build on a clean machine downloads the Kotlin/Native toolchain (hundreds of MB), and the first iOS test link
can take many minutes on a loaded machine — neither is a hang. This orchestration skill was not dry-run end to end by
its author; the gate commands, task names (`:shared:testAndroidHostTest`, `:shared:iosSimulatorArm64Test`,
`:androidApp:testDebugUnitTest`, root `koverXmlReport`), and lock behavior are exercised by the gate skills' own
verification and by `iru-kmp-code-one-task`'s verification build (which confirmed `testAndroidHostTest` and
`iosSimulatorArm64Test` run `commonTest` on both targets and that the latter boots a simulator by itself).
