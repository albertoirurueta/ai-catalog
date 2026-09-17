---
name: iru-android-test
description: Run an Android/Kotlin project's JUnit 4 unit test suite via the Android Gradle Plugin's `testDebugUnitTest` task, optionally scoped to a test class, method, wildcard pattern, or a `lib`/`app` module path, and only run instrumented tests (`connectedAndroidTest`) when the prompt explicitly asks for them and a device/emulator is actually attached. Invoke as `/iru-android-test` to run the whole `lib` module's unit test suite, or `/iru-android-test [selector]` where `[selector]` is a class name (`FooTest`), a class+method (`FooTest#testSomething`), a wildcard pattern (`*ServiceTest`), or a path under a module's `src/test`/`src/androidTest` tree (`lib/src/test/java/.../FooTest.kt`, `app/src/test/...`) — the module (`:lib` by default, `:app` when the path says so) and the `--tests` pattern are both derived from the selector. Report-only: parses `<module>/build/test-results/testDebugUnitTest/*.xml` (JUnit XML) for pass/fail/skip counts and failing-test detail, never dumps raw Gradle/JUnit output, and never fixes a failing test or modifies source/test code. Use whenever the user wants to run, re-run, or narrow down Android unit (or, on request, instrumented) tests instead of invoking `./gradlew` by hand.
model: haiku
---

# Android Test

Run the project's JUnit 4 unit tests through the Android Gradle Plugin (AGP), scoping the run to whatever the
user asked for, and report a compact pass/fail summary parsed from the generated JUnit XML. This skill only runs
tests and reports results — it does not fix failures or modify source/test code unless asked to as a follow-up.

## Step 0 — Resolve inputs

This skill takes a single positional `[selector]` argument (the same shape as `iru-java-test`'s selector), not
`key: value` args, unless the calling skill/prompt explicitly passes `key: value` lines (e.g. `module: app`) — in
that case honor them and skip the matching inference in Step 1/2.

- No argument → run the whole default module (`lib`) unscoped.
- A bare class simple name (`FooTest`), class+method (`FooTest#testSomething`), or wildcard/package pattern
  (`*ServiceTest`, `com.example.pkg.*`) → scope via Step 2's `--tests` mapping.
- A path (absolute or relative) under a module's `src/test`/`src/androidTest` tree → scope via Step 1's module
  table and Step 2's pattern.
- The prompt (not necessarily the selector itself) asking for instrumented/on-device/`connectedAndroidTest`
  tests → also run Step 4, honoring its device-attached gate.

## Step 1 — Resolve the module and verify prerequisites

| Selector shape | Module |
|---|---|
| No selector | `:lib` (default) |
| Path containing `lib/src/test` or `lib/src/androidTest` | `:lib` |
| Path containing `app/src/test` or `app/src/androidTest` | `:app` |
| Bare class name/pattern, no path | search `*/src/test/**/<Name>*.{kt,java}` under the repo root; exactly one module matches → use it; several match → ask which, or default to `lib` and say so explicitly; none match → still default to `lib` and let Gradle's own "No tests found" (Step 3) surface the typo rather than guessing further |

Prerequisites — check these before invoking Gradle, since a missing one produces a confusing failure that looks
like a test problem but isn't:

- **`JAVA_HOME`** set and pointing at a JDK 17+ install — Gradle/AGP on this stack need 17+, and the machine's
  ambient/default `java` may be older or (on a recently-updated machine) newer than what's supported. On macOS,
  `export JAVA_HOME=$(/usr/libexec/java_home -v 17)` (or `-v 21`) if unset or wrong.
- **`ANDROID_HOME`** (or `ANDROID_SDK_ROOT`), or a `local.properties` with `sdk.dir=...` at the repo root —
  without one of these the build fails at configuration time with `SDK location not found`, before any test runs.
- **`./gradlew`** present and executable at the repo root — this skill never generates a wrapper; if missing,
  stop and report it rather than falling back to a bare `gradle` invocation.

## Step 2 — Build the `--tests` pattern

Map the selector to Gradle's built-in `Test` task `--tests` filter (which AGP's `testDebugUnitTest` inherits):

| What the user wants | `--tests` value |
|---|---|
| Everything in the module | *(omit `--tests`)* |
| One class | `--tests '*.FooTest'` (or the fully-qualified name if known) |
| One method | `--tests '*.FooTest.testSomething'` |
| Several classes/methods | repeat `--tests` once per pattern — Gradle ANDs multiple `--tests` flags as independent inclusions, unlike Maven Surefire's single comma-separated `-Dtest` value |
| Wildcard/package pattern | `--tests 'com.example.pkg.*'` |

## Step 3 — Run

```bash
./gradlew :<module>:testDebugUnitTest [--tests '<pattern>' ...] [--offline]
```

- Target `:lib:testDebugUnitTest` / `:app:testDebugUnitTest` specifically — not the bare `test` lifecycle task —
  so only the debug variant's unit tests build and run (the reference scaffold only turns on
  `enableUnitTestCoverage`/`enableAndroidTestCoverage` for `debug`, and building the `release` variant's tests too
  is pure overhead for this skill's purpose).
- **An unmatched `--tests` pattern FAILS the whole build**, not a silent zero: Gradle exits non-zero with
  `Execution failed for task ':lib:testDebugUnitTest'. > No tests found for given includes: [<pattern>](...)`.
  Detect this exact message and report it as **"no matching tests for `<pattern>`"** — a distinct outcome from
  both a clean run and a real compile/test failure. Do not report it as a build failure, and do not treat it as
  "0 passed, 0 failed" (that reads as a clean, intentionally-empty run, which this isn't).
- Do not add `clean` by default — an incremental re-run is what "run/re-run tests" normally means; add it only if
  the user asks for a clean run or a prior run's results look stale.
- `--offline`: only retry with this flag if a run fails on dependency resolution *and* a prior successful run
  already populated the Gradle/Robolectric caches (see Known quirks) — on a cold cache `--offline` just fails
  differently (missing artifacts) and hides the real network problem, so don't reach for it first.

## Step 4 — `connectedAndroidTest` (instrumented), only when explicitly asked

Run instrumented tests only when **both** hold:

1. the prompt explicitly asks for instrumented/on-device tests (a `src/androidTest` path in the selector alone is
   not enough — Step 1 still resolves the module for the unit-test run unless instrumented is explicitly asked
   for), and
2. `adb devices` lists at least one line, after the `List of devices attached` header, whose state is `device`
   (not `unauthorized`, `offline`, or an empty list) — no attached/booted device or emulator means skip this step
   and say so explicitly; never silently fall back to reporting only the unit-test results without noting that
   instrumented tests were requested but skipped.

```bash
adb devices
./gradlew :<module>:connectedDebugAndroidTest [--tests '<pattern>']
```

Results land under `<module>/build/outputs/androidTest-results/connected/**/*.xml` — same JUnit XML shape Step 5
parses; parse and report the same way, labeled as instrumented results.

## Step 5 — Parse the JUnit XML results

Gradle/AGP write one `TEST-<classname>.xml` file per test class under
`<module>/build/test-results/testDebugUnitTest/` (unit tests) or
`<module>/build/outputs/androidTest-results/connected/**` (instrumented, Step 4). Parse every matching file with
`python3`'s standard-library `xml.etree.ElementTree` — no external dependency needed:

```python
import glob
import xml.etree.ElementTree as ET

total = passed = failed = skipped = 0
failures = []
for path in sorted(glob.glob("<module>/build/test-results/testDebugUnitTest/TEST-*.xml")):
    root = ET.parse(path).getroot()
    for tc in root.findall("testcase"):
        total += 1
        name, classname = tc.get("name"), tc.get("classname")
        fail, err, skip = tc.find("failure"), tc.find("error"), tc.find("skipped")
        if fail is not None or err is not None:
            failed += 1
            node = fail if fail is not None else err
            text_lines = (node.text or "").strip().splitlines()
            failures.append((f"{classname}#{name}", node.get("message", ""),
                              text_lines[0] if text_lines else ""))
        elif skip is not None:
            skipped += 1
        else:
            passed += 1

print(f"total={total} passed={passed} failed={failed} skipped={skipped}")
for name, message, first_line in failures:
    print(f"FAIL {name}: {message}\n  {first_line}")
```

Each `<testcase name="..." classname="...">` holds at most one of `<failure message="..." type="...">` /
`<error message="..." type="...">` (stack trace as element text) or a self-closing `<skipped/>`; a `<testcase>`
with none of those passed. This snippet was verified against hand-written sample files in
`$TMPDIR/iru-verify/android/gates/junit/` (`TEST-com.example.lib.FooTest.xml` with one passed, one `<failure>`
assertion, and one `<skipped/>`; `TEST-com.example.lib.BarTest.xml` with one `<error>` unchecked exception) — it
correctly counted `total=4 passed=1 failed=2 skipped=1` and extracted each failure's `classname#name`, its
`message` attribute, and the first stack-trace line.

If Step 3's build failed before producing any XML (compile error, or the unmatched-`--tests` case), report that
instead of trying to parse a stale or missing report directory.

## Step 6 — Report

- **All passed**: state the counts (`total`, module, and the pattern if scoped) briefly — no per-test list.
- **No matching tests** (Step 3's unmatched-`--tests` case): report plainly as `no tests matched '<pattern>' in
  :<module>`, never as `0 passed, 0 failed`.
- **Failures/errors**: list each failing test's `classname#name`, its assertion/exception message, and the first
  stack-trace line; point to `<module>/build/test-results/testDebugUnitTest/TEST-<classname>.xml` for the full
  trace instead of pasting it.
- **Instrumented run skipped** (not asked for, or no device attached): say so explicitly rather than silently
  reporting only unit-test results as if that were the whole answer.
- **Warn explicitly**: a first run on a clean machine downloads Robolectric's `android-all` jars (can be hundreds
  of MB) and may take minutes — don't mistake a long first run for a hang; `ANDROID_HOME`/`local.properties` must
  already be correct or the build fails before any test executes; this skill never fixes failing tests or
  modifies source/test code, that is a follow-up the user (or `iru-android-code-one-task`) drives explicitly.

## Known quirks / verification notes

- **Unmatched `--tests` fails the build** (`No tests found for given includes: [...]`, exit 1) — this is Gradle's
  own long-documented `Test`-task contract (not scaffold-specific), but this skill's author did not run a live
  `./gradlew testDebugUnitTest` against the Task 20 scaffold to reproduce the exact current wording — **unverified
  locally by this skill's author; exercised by Task 20.2/23.2**.
- Gradle/AGP need **JDK 17+**; do not trust the machine's ambient/default `java` — set `JAVA_HOME` explicitly.
- `ANDROID_HOME`/`local.properties` missing is the most common "works on my machine" failure; check it before
  suspecting the test code itself.
- Robolectric downloads `android-all-<sdk>-robolectric-r0.jar` (one per configured SDK level) into the Gradle
  cache on first run — needs network, is slow; subsequent runs are cached and fast.
- Configuration cache (`org.gradle.configuration-cache=true` in the reference `gradle.properties`) can be
  incompatible with some third-party Gradle plugins/tasks; if a run fails with a configuration-cache-specific
  error unrelated to the tests themselves, retry once with `--no-configuration-cache` before treating it as a
  real test failure.
- This skill's JUnit-XML parsing (Step 5) was verified against hand-written sample files under
  `$TMPDIR/iru-verify/android/gates/junit/` only, per this catalog's convention that gate-skill authors verify
  their own parsing logic against small fixtures rather than running the heavy Gradle build themselves — the live
  `./gradlew :lib:testDebugUnitTest` invocation and its real report path/shape are **unverified locally by this
  skill's author; exercised by Task 20.2/23.2**. The report-path convention
  (`<module>/build/test-results/testDebugUnitTest/*.xml`) is taken directly from the reference repository's
  (https://github.com/albertoirurueta/irurueta-android-glutils) `sonar.junit.reportsPath` property in
  `lib/build.gradle.kts`.
