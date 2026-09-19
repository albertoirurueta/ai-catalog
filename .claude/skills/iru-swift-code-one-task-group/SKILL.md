---
name: iru-swift-code-one-task-group
description: Implement one bucket of Swift tasks from a plan's task group end-to-end — captures a single pre-change quality baseline for the whole bucket, runs `iru-swift-code-one-task` once per task (in parallel agents when the group is marked parallelizable) to implement each one and its tests, then validates the entire bucket once: license headers, DocC completeness via `iru-swift-docc`, a scoped test run via `iru-swift-test`, an 80% unit-test line-coverage check via `iru-swift-coverage` (branch coverage is unavailable for Swift and is never part of the bar), a full-suite run (`swift test` for a Swift Package, `xcodebuild test -scheme <scheme> -destination <destination>` for an Xcode app target), and a code-quality regression check via `iru-swift-code-quality` against that one baseline. Because an app-target test/coverage/full-suite run boots and drives an iOS/tvOS/watchOS Simulator, and only one such run can safely use a given simulator destination at a time, every `xcodebuild test` invocation this skill makes is serialized behind a repository-wide `mkdir`-based lock (`.simulator-test.lock`) so two parallel task groups' simulator runs never overlap; a Swift Package's `swift test` needs no simulator and never takes this lock. `iru-swift-code-one-task` itself checks off each task/sub-task's box in `implementation_plan.md` the moment that task finishes (with a "group validation pending" note), so an interrupted run doesn't re-attempt already-finished tasks; this skill backfills any checkbox that didn't land and replaces each task's pending note with the final coverage/quality outcome once group validation passes, notifying the user as each phase completes rather than waiting until the whole bucket is done. If group validation surfaces a regression traceable to a specific task, that task's implementation is revised and the affected checks re-run, instead of re-validating the whole bucket per task. Invoke as `/iru-swift-code-one-task-group <bucket text>`, passing every task/sub-task in the bucket, each with its own text, plus the group's `Parallelizable` verdict and any relevant "Current code state" context. Equivalent to `iru-java-code-one-task-group`/`iru-typescript-code-one-task-group`/`iru-android-code-one-task-group` for Swift Package Manager / Apple app projects; used by `iru-code-one-task-group`, which invokes this once per plan group for its `swift`-tagged tasks.
model: sonnet
allowed-tools: Read Edit Write Bash(swift *) Bash(xcodebuild *) Bash(xcrun *) Bash(xcodegen *) Bash(tuist *) Bash(mkdir *) Bash(rmdir *) Bash(git status *) Bash(git diff *) Bash(git log *) Bash(find *) Bash(grep *) Bash(ls *) Skill Agent
---

# Implement one task-group bucket (Swift)

Carry out every Swift task in one plan-group bucket end to end: capture one quality baseline for the whole bucket
up front, implement each task (in parallel where safe), then validate everything the bucket touched in a single
consolidated pass instead of once per task. It is the Swift Package Manager / Apple-app counterpart to
`iru-java-code-one-task-group`/`iru-typescript-code-one-task-group`/`iru-android-code-one-task-group` — same
shape, but built on `iru-swift-code-quality`, `iru-swift-test`, `iru-swift-coverage`, and `iru-swift-docc`, and
aware that an app target's test/coverage/full-suite run needs a Simulator that only one run may drive at a time.
It uses a medium model on purpose: the plan already carries the hard reasoning; this skill drives execution of it.

## Step 1 — Detect the project shape and touched target(s), then capture one pre-change quality baseline

Before implementing anything, detect the project shape once, the same way `iru-swift-code-one-task`'s own Step 1
does: `Package.swift` alone (no `project.yml`/`Project.swift`/`*.xcodeproj`/`*.xcworkspace` nearby) → **package**;
any of those found → **app**. For an app, also resolve, once, the same way `iru-swift-test`'s Step 3 does: the
**scheme** (`xcodebuild -list`, preferring one that doesn't contain "Tests"/"UITests" in its name) and the
**destination** (`platform=macOS` for a macOS-only target, or the first available simulator — `xcrun simctl list
devices available -j`, run with a generous timeout since it can be slow — for an iOS/tvOS/watchOS target). Record
project kind + scheme + destination once and reuse them for every gate below via `kind:`/`scheme:`/`destination:`
lines, instead of re-deriving them per gate call. Also check now whether a full Xcode install is active
(`xcode-select -p` points at `.../Xcode.app/Contents/Developer`, not just the Command Line Tools) — an app-kind
bucket on a Command-Line-Tools-only machine will need Step 3's test/coverage/full-suite stages reported as
unverified rather than a false pass.

Then determine which target(s) this bucket's tasks touch, using the same heuristic `iru-swift-code-one-task`'s own
Step 1 uses per task: a path under `Sources/<Target>/` or `Packages/Core/Sources/<Target>/` wins; a path under a
per-platform app target directory names that target; otherwise infer from what each task describes. Record this
target set once and reuse it for Step 3's DocC/coverage/quality scoping.

Collect the set of file(s)/type(s) every task in this bucket is expected to touch (from each task's own
description). Capture a single pre-change quality baseline covering all of them by delegating to the
`iru-gate-runner` agent rather than running `iru-swift-code-quality` directly: `Agent({description: "Capture
pre-change quality baseline for task group", subagent_type: "iru-gate-runner", prompt: "Invoke Skill({skill:
\"iru-swift-code-quality\", args: \"<file1,file2,...>\"}), then report back only the list of issues found for these
files, broken down by tool (SwiftLint/formatter/Periphery) and whether each tool was wired."})`. Record the
returned issues as this bucket's pre-change baseline — an empty baseline if every file is new. This is what Step
3.8's quality check compares against. Skip this baseline capture if `iru-swift-code-quality` is unavailable.

## Step 2 — Implement each task via `iru-swift-code-one-task`

For every task in the bucket, invoke `iru-swift-code-one-task` — it detects the task's own project shape and
target, implements exactly what the task specifies, writes/updates its tests, and compile-checks the target (via
`swift build --build-tests` or `xcodebuild build-for-testing`, which builds but never boots a simulator to run
anything — so it never needs Step 3's simulator lock); license headers, DocC, and all further validation live here.

- **Bucket marked `Parallelizable: yes`**: invoke `iru-swift-code-one-task` for every task in the bucket
  concurrently — issue all of the `Agent` calls below together, in the same response:
  ```
  Agent({
    description: "Implement <task N> via swift-code-one-task",
    subagent_type: "iru-isolated-skill-executor",
    prompt: "Invoke Skill({skill: \"iru-swift-code-one-task\", args: \"<the task's full text, including its exact
      implementation_plan.md checkbox line(s) for itself and its sub-tasks, its sub-tasks' own text, and any
      relevant Current code state context>\"}). Report back: the project shape/target detected, the files touched,
      the tests added/updated, the compile-check result, and whether the task stopped on a blocker instead of
      finishing.",
    run_in_background: false
  })
  ```
- **Bucket marked `Parallelizable: no`**: invoke them one at a time, in the plan's order, waiting for each to
  finish before starting the next.

`iru-swift-code-one-task` already checks off that task's own checkbox (and its sub-tasks') in
`implementation_plan.md` itself, with a "group validation pending" note, before it reports back. As each task's
agent reports back, re-read `implementation_plan.md` and confirm that box is actually checked; if it isn't (a rare
concurrent-write race), flip it yourself now with the same note. Notify the user that this specific task's
implementation and tests landed.

If a task's agent reports it stopped on a blocker, record it and skip validating that specific task's code in
Step 3 — surface it in Step 5's report without blocking the rest of the bucket's already-finished tasks.

## Step 3 — Validate the whole bucket once

Once every task that didn't block has been implemented, run the following once for the entire bucket:

1. **License headers**, for every file the bucket added or modified, via `iru-gate-runner`: `Agent({description:
   "Add license headers for task group", subagent_type: "iru-gate-runner", prompt: "Invoke Skill({skill:
   \"iru-check-license\", args: \"<file1,file2,...>\"}) scoped to every file this bucket's tasks added or modified.
   Report back only which files were missing a header vs. fixed vs. already compliant, and — if no header
   convention existed anywhere in the repo — whether the user chose to skip or generate one."})`. Respect a skip
   choice for the rest of the run. Skip if `iru-check-license` isn't installed.
2. **DocC**, for every type/file the bucket added or modified, via `iru-gate-runner`: `Agent({description: "Update
   DocC for task group", subagent_type: "iru-gate-runner", prompt: "Invoke Skill({skill: \"iru-swift-docc\", args:
   \"<Type1,Type2,...>\"}) scoped to every type this bucket's tasks added or modified. Report back only which
   members were documented/completed and in which files, whether any target's DocC catalog landing page had to be
   created or extended, and whether the symbol-graph audit and doc-build verification passed."})`. If it reports
   the build failed, fix and re-invoke until it reports success. Skip if `iru-swift-docc` isn't installed.
3. **Acquire the simulator lock** — app-kind buckets only; a package needs no simulator and skips 3a/3d entirely.
   `xcodebuild test` (scoped, coverage, and full-suite runs below all use it) drives a Simulator destination that
   only one run may occupy at a time — two overlapping `xcodebuild test` runs against the same destination collide
   on boot state and produce results that are unreliable rather than merely slow, the same reasoning
   `iru-java-springboot-code-one-task-group`'s integration-test lock uses for its shared compose stack, applied
   here to a shared simulator instead:
   ```bash
   mkdir .simulator-test.lock 2>/dev/null && echo ACQUIRED || echo HELD
   ```
   - **`ACQUIRED`**: immediately write `.simulator-test.lock/owner` (via the `Write` tool) with this bucket's
     identifying text (task numbers/titles, target, scheme), and `date -u +'%Y-%m-%dT%H:%M:%SZ'`. Ensure
     `.simulator-test.lock/` is listed in the repository's root `.gitignore`, adding it if missing — the lock is
     transient local state and must never be committed.
   - **`HELD`**: another task group is running simulator tests right now. Tell the user this bucket is waiting
     (naming the holder from `cat .simulator-test.lock/owner` if readable), then poll: re-run the `mkdir` roughly
     every 30 seconds. Do not proceed and do not run `xcodebuild test` anyway.
   - **Stale lock**: `find .simulator-test.lock -maxdepth 0 -mmin +60` returning the directory means its holder has
     been running over an hour — for a simulator run that almost certainly means it died without releasing. Tell
     the user what the owner file says, break it (`rm -f .simulator-test.lock/owner && rmdir .simulator-test.lock`),
     and acquire fresh. Say so in Step 5.
   - **Wait timeout**: still held after roughly 45 minutes of polling and not yet stale — stop waiting, report
     Steps 3.4/3.5/3.6's app-kind stages as **unverified — blocked by a concurrent simulator run**, and continue to
     Step 3.8 (quality needs no simulator; Step 3.7's lock release is a no-op when the lock was never acquired). Name it in Step 5.
4. **Scoped tests**, for every test affected across the bucket, via `iru-gate-runner`: `Agent({description: "Run
   tests for task group", subagent_type: "iru-gate-runner", prompt: "Invoke Skill({skill: \"iru-swift-test\", args:
   \"<selector covering every test affected by this bucket>\\nkind: <package|app>\\nscheme: <scheme>\\ndestination:
   <destination>\"}) (fall back to `swift test --filter '<pattern>'` / `xcodebuild test -only-testing:<...>
   -destination '<destination>'` directly if the swift-test skill is unavailable). If everything passes, report
   back only that all tests passed. If anything fails, report back only the failing test names, the failure
   reason, and the first message/stack-trace line for each."})` (omit `scheme:`/`destination:` for a package). If
   failures are reported, identify which task's code they trace back to, fix that task's implementation and/or
   tests, and re-invoke this same check — repeat until it reports all tests passed.
5. **Coverage**, for every changed/new file/type across the bucket, via `iru-gate-runner`: `Agent({description:
   "Check coverage for task group", subagent_type: "iru-gate-runner", prompt: "Invoke Skill({skill:
   \"iru-swift-coverage\", args: \"<File1.swift,Type2,...>\\nkind: <package|app>\\nscheme: <scheme>\\ndestination:
   <destination>\"}). Report back, per target file/type, its unit-test line coverage percentage and function
   coverage percentage; branch coverage is unavailable for Swift and must be reported as such, never as 0%."})`.
   The bar is **80% line coverage**; branch coverage is never part of it. For anything under 80%, add tests for its
   uncovered lines (via the task that owns it, from the ranges `iru-swift-coverage` reports), re-run Step 3.4 to
   confirm, then re-check coverage here.
6. **Full suite**, to catch regressions elsewhere, via `iru-gate-runner`:
   - **Package**: `Agent({description: "Run full test suite", subagent_type: "iru-gate-runner", prompt: "Run
     `swift test` with no filter. If everything passes, report back only that all tests passed. If anything fails,
     report back only the failing test names, the failure reason, and the first message/stack-trace line for
     each."})`.
   - **App**: `Agent({description: "Run full test suite", subagent_type: "iru-gate-runner", prompt: "Run `rm -rf
     <path>.xcresult && xcodebuild test -scheme '<scheme>' -destination '<destination>' -resultBundlePath
     <path>.xcresult`, then parse it via `xcrun xcresulttool get test-results summary --path <path>.xcresult`. If
     everything passes, report back only that all tests passed. If anything fails, report back only the failing
     test names and the first line of each failure's message."})` — still under the lock acquired in 3.3.
   Fix any regression, then re-invoke until it reports all tests passed.
7. **Release the simulator lock** — app-kind buckets only, as soon as Step 3.6 (or the last fix-and-re-run of
   3.4–3.6) has finished: `rm -f .simulator-test.lock/owner && rmdir .simulator-test.lock`. Release on every exit
   path — tests passed, they failed, a task turned out blocked, or this skill is about to report a hard stop. A
   lock left behind blocks every other app-kind bucket for a full hour until Step 3.3's staleness escape fires.
8. **Code quality**, for the same file/type set as Step 1, via `iru-gate-runner`: `Agent({description: "Check for
   new quality issues in task group", subagent_type: "iru-gate-runner", prompt: "Invoke Skill({skill:
   \"iru-swift-code-quality\", args: \"<file1,file2,...>\\nbaseline: <baseline from Step 1>\"}). Report back only the
   issues that are newly appearing (not present in the baseline), broken down by tool (SwiftLint/formatter/
   Periphery)."})`. Any issue reported is a regression introduced by this bucket — trace it to the task that owns
   the affected file, fix it (then re-run 3.4–3.6 to confirm the fix broke nothing), and re-check until none
   remain. Leave a new issue in place only if fixing it would contradict what its task explicitly specifies —
   record that, and why, for Step 5. Skip if `iru-swift-code-quality` isn't installed.

## Step 4 — Finalize progress notes and notify the user

Once Step 3 passes clean for the bucket (or leaves only explicitly-accepted issues), update each task's note in
`implementation_plan.md` — replacing the "group validation pending" placeholder — with the final outcome: line
coverage achieved and code-quality result for that task's own file(s), e.g. `- [x] Task 2. **Implement
`RouteValidator`** — tests in RouteValidatorTests (94% line coverage), no new SwiftLint/format issues.` If any
stage was unverified (Command-Line-Tools-only machine, lock wait timeout), say so in the note rather than implying
it passed. Save the file, then notify the user that group validation completed and summarize the bucket-wide
result. Before writing these notes, confirm the simulator lock is released (Step 3.7) if it was ever taken.

If any task was recorded as blocked in Step 2, leave its checkbox unchecked and its blocker note in place.

## Step 5 — Report the bucket's outcome

Hand control back to the caller (`iru-code-one-task-group`) with a summary covering the whole bucket: per task, the
target it lives in, the files touched, tests added/updated, line coverage achieved, and code-quality outcome —
including whether a new issue was left in place as unavoidable and why, whether license-header/DocC-catalog work
was needed, whether any stage was reported unverified (and why — no full Xcode install, lock wait timeout), how the
simulator lock behaved whenever it was anything other than an immediate uncontended acquire (wait time, a stale
lock broken, confirmation it was released), and which task(s), if any, stopped on a blocker.
`implementation_plan.md`'s checkboxes are already checked and finalized (Steps 2 and 4) and the user-facing
notifications have already gone out — the caller does not need to redo that bookkeeping for this bucket.

**Warn explicitly**: an app-kind bucket needs a full Xcode install (not just Command Line Tools) and, for a
simulator destination, a matching runtime already downloaded — a missing one fails at destination resolution,
before any test runs, and looks unrelated to the code itself; SwiftLint/the third-party SwiftFormat/Periphery may
be entirely absent on a machine with no Homebrew/Mint, in which case `iru-swift-code-quality` reports them as not
wired rather than clean, and this skill's own quality diff in Step 3.8 reflects only whichever tools actually ran.
This skill's own author did not run any of the `swift`/`xcodebuild` commands above against a real scaffold — no
verification sub-task was assigned for writing this skill itself — so every gate command and report path named
above is **unverified locally by this skill's author**; each is exercised instead by the underlying gate skill's
own verification (see `iru-swift-test`/`iru-swift-coverage`/`iru-swift-code-quality`/`iru-swift-docc`'s own "Known
quirks" sections), not by a dry run of this orchestration skill.
