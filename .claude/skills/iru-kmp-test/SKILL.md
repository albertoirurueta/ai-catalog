---
name: iru-kmp-test
description: >-
  Run a Kotlin Multiplatform (Android + iOS) project's tests per target — the shared module's Android host (JVM) tests
  (`testAndroidHostTest` under the AGP `com.android.kotlin.multiplatform.library` plugin, `testDebugUnitTest` under
  `androidTarget()` + `com.android.library`, plus `jvmTest` when a `jvm()` target exists), the Android app module's
  `testDebugUnitTest`, the Kotlin/Native iOS simulator tests (`iosSimulatorArm64Test`, or `iosX64Test` on an Intel
  Mac), and the SwiftUI host app's XCTest bundle (`xcodebuild test` on `iosApp/iosApp.xcodeproj`) — discovering the
  modules and exact task names at runtime from `./gradlew <module>:tasks --all` instead of assuming one plugin's
  names, and tolerating the JetBrains wizard's single `composeApp/` layout. Invoke as `/iru-kmp-test` to run every
  target, or `/iru-kmp-test <scope>` where `<scope>` is a test class (`GreeterTest`), class+method
  (`GreeterTest#greets`), wildcard/package pattern, a test file path (its source set picks the targets: `commonTest`
  → every target, `androidHostTest`/`androidUnitTest`/`androidTest` → Android only, `iosTest`/`appleTest`/
  `nativeTest` → iOS only, `iosApp/…` → the XCTest bundle), a module (`:shared`, `androidApp`), a source-set name,
  plus optional `key: value` lines (`target: android|ios|all`, `module:`, `destination:`, `lock: held`). Android/JVM
  tests run on any host; iOS stages run only on macOS with a full Xcode and an iOS Simulator runtime — otherwise they
  are reported "unverified", never "passed" — and every stage that boots or spawns a simulator is serialized
  repository-wide behind the shared atomic-`mkdir` `.integration-test.lock` (owner file, stale after 60 minutes,
  released on every exit path). Parses the JUnit XML under `<module>/build/test-results/<task>/` and the
  `.xcresult` bundle into a compact per-target pass/fail/skip summary, detects the "selector matched nothing" cases
  (Gradle fails the JVM task with "No tests found for given includes", but a Kotlin/Native simulator task exits 0
  and writes no XML), and never dumps raw Gradle/xcodebuild output. Report-only: never fixes a failing test or
  modifies source/test code. Equivalent to `iru-android-test`/`iru-swift-test` for KMP apps. Use whenever the user
  (or `iru-kmp-code-one-task-group` via `iru-gate-runner`) wants to run, re-run, or narrow down KMP tests instead of
  invoking `./gradlew allTests`/`xcodebuild test` by hand.
model: haiku
allowed-tools: Read Write Bash(./gradlew *) Bash(python3 *) Bash(xcodebuild *) Bash(xcrun *) Bash(xcode-select *) Bash(xcodegen *) Bash(uname *) Bash(command -v *) Bash(git rev-parse *) Bash(find *) Bash(grep *) Bash(ls *) Bash(cat *) Bash(date *) Bash(rm -rf *iru-kmp-test-*) Bash(mkdir .integration-test.lock*) Bash(rmdir .integration-test.lock*) Bash(rm -f .integration-test.lock/owner) Bash(/usr/libexec/java_home *)
---

# KMP Test

Run a Kotlin Multiplatform project's tests on each target it actually has, scoped to what the user asked for, and
report a compact per-target pass/fail summary parsed from JUnit XML (Gradle) and `.xcresult` (Xcode). This skill
only runs tests and reports results — it never fixes failures or modifies source/test code.

## Step 0 — Resolve inputs

A single positional `<scope>` plus optional `key: value` lines; explicit keys win over inference:

- `target: android|ios|all` — default `all`. `android` runs the JVM stages only (Android host tests, `jvmTest`,
  the Android app's unit tests); `ios` runs the iOS stages only (Kotlin/Native simulator tests and the iosApp XCTest
  bundle). A fast caller-side check (e.g. a coding skill's per-task compile-and-test loop) passes `target: android`;
  group validation leaves the default.
- `module: <gradle path>` — restrict to one module (`:shared`, `:androidApp`, `:composeApp`).
- `destination: <xcodebuild destination>` — override the simulator chosen in Step 5.
- `lock: held` — the caller (e.g. `iru-kmp-code-one-task-group`) already holds `.integration-test.lock`; don't
  acquire or release it here (Step 4).

`<scope>` shapes:

| Scope | Effect |
|---|---|
| none | every test task of every in-scope target |
| `FooTest`, `FooTest#bar`, `*ServiceTest`, `com.example.pkg.*` | Gradle `--tests` filter (Step 3) on every Gradle test task that runs; for the XCTest stage, see Step 5 |
| path under `src/commonTest/` | the owning module, every target |
| path under `src/androidHostTest/`, `src/androidUnitTest/`, `src/test/` (Android app), `src/jvmTest/` | Android/JVM only |
| path under `src/iosTest/`, `src/appleTest/`, `src/nativeTest/`, `src/ios*Test/` | Kotlin/Native iOS only |
| path under `iosApp/` (e.g. `iosApp/iosAppTests/FooTests.swift`) | the XCTest stage only |
| `:shared`, `shared`, `androidApp` | that module, every target it has |
| `commonTest`, `androidHostTest`, `iosTest`, … | the same mapping as the matching path |

A path's class name (file stem) becomes the `--tests '*.<Stem>'` filter.

## Step 1 — Detect the layout and verify prerequisites

```bash
grep -nE 'include\(' settings.gradle.kts settings.gradle 2>/dev/null
grep -lE 'kotlin\("multiplatform"\)|kotlinMultiplatform|org\.jetbrains\.kotlin\.multiplatform' */build.gradle.kts */build.gradle 2>/dev/null
grep -lE 'com\.android\.application|androidApplication' */build.gradle.kts */build.gradle 2>/dev/null
ls -d iosApp/*.xcodeproj iosApp/*.xcworkspace iosApp/project.yml 2>/dev/null
```

- **KMP modules**: every included module applying the Kotlin Multiplatform plugin (`shared/` in this catalog's
  layout; `composeApp/` in the JetBrains wizard's single-module layout, which is *both* the KMP module and the
  Android application). **Android app modules**: those applying `com.android.application` (`androidApp/`, or
  `composeApp/` again). **iOS host app**: `iosApp/` with an `.xcodeproj`/`.xcworkspace` or an XcodeGen
  `project.yml`.
- No KMP module at all → stop: this isn't a KMP project (point to `iru-android-test`/`iru-java-test`).

Prerequisites — check before invoking Gradle; a missing one fails in a way that looks like a test problem:

- **`JAVA_HOME`** on a JDK the build accepts (17 or 21 for current AGP/Kotlin; the machine default may be newer than
  supported). On macOS `export JAVA_HOME=$(/usr/libexec/java_home -v 21)` when unset or wrong.
- **`ANDROID_HOME`/`ANDROID_SDK_ROOT`, or `local.properties` `sdk.dir`** — otherwise configuration fails with
  `SDK location not found` before any test runs (the iOS tasks too, since every module configures).
- **`./gradlew`** at the repository root — never fall back to a bare `gradle`.
- **iOS stages only** — all of: `uname -s` is `Darwin`; `xcodebuild -version` succeeds and `xcode-select -p` points
  into an `Xcode.app` (Command Line Tools alone can't run simulators); `xcrun simctl list runtimes` lists an iOS
  runtime. Any missing → the iOS stages are **unverified (<what's missing>)** — never "passed", never "0 tests" —
  and the Android stages still run and report normally.

## Step 2 — Discover the test tasks

Never hardcode one plugin's names — list them per module (one invocation per module; configuration is the slow
part, so reuse the output for the whole run):

```bash
./gradlew :<module>:tasks --all > "$TMPDIR/iru-kmp-test-tasks-<module>.txt"
grep -E '^(testAndroidHostTest|testDebugUnitTest|jvmTest|iosSimulatorArm64Test|iosX64Test|allTests)( |$)' "$TMPDIR/iru-kmp-test-tasks-<module>.txt"
```

| Stage | Task (first that exists) |
|---|---|
| Android host tests of a KMP module | `testAndroidHostTest` (AGP KMP library plugin with `withHostTest {}` — the name may follow a custom host-test compilation name, so also accept any `test<Name>HostTest`), else `testDebugUnitTest` (`androidTarget()` + `com.android.library`) |
| JVM target | `jvmTest` (only when a `jvm()` target exists) |
| Android app module | `testDebugUnitTest` |
| Kotlin/Native iOS | `iosSimulatorArm64Test` on Apple silicon (`uname -m` = `arm64`), `iosX64Test` on Intel; device targets (`iosArm64`) have no runnable test task |

Use the explicit per-target tasks, not `allTests`: `allTests` is an aggregate (no `--tests` filter of its own) and
hides which target a failure came from. A KMP module whose Android host tests aren't enabled (no `withHostTest {}`
→ no `testAndroidHostTest`) has its `commonTest` exercised only on the other targets — say so in the report rather
than implying Android coverage of shared tests.

## Step 3 — Run the Gradle stages

**Android/JVM stages** (any host, no lock):

```bash
./gradlew :shared:testAndroidHostTest [--tests '<pattern>'] :androidApp:testDebugUnitTest [--tests '<pattern>'] --continue
```

- **`--tests` binds to the task immediately before it** — verified: `./gradlew :shared:testAndroidHostTest
  :shared:iosSimulatorArm64Test --tests '*.GreeterTest.greets'` filtered only the iOS task and ran the whole Android
  suite. Repeat `--tests '<pattern>'` after **every** test task it should filter.
- Pattern mapping is Gradle's: one class `'*.FooTest'`, one method `'*.FooTest.bar'` (from `FooTest#bar`), a package
  `'com.example.pkg.*'`; several patterns → repeat `--tests` (each adds an inclusion). Kotlin backtick test names
  with spaces work as-is inside the quotes.
- `--continue` so a failing Android stage doesn't stop the next one from running.
- **Unmatched filter on a JVM task fails the build**: `No tests found for given includes: [<pattern>](--tests
  filter)`, exit 1 (verified on `testAndroidHostTest`). Report it as **"no matching tests for `<pattern>` in
  `:<module>:<task>`"** — not a build failure and not "0 passed". When a class-name scope exists in only some
  modules' test trees, add the filter only to the tasks of the modules that contain it (`find */src/*Test* -name
  '<Stem>.kt'`), so the other modules don't fail on it.
- Don't add `clean`; retry once with `--no-configuration-cache` if a configuration-cache error unrelated to the
  tests appears; `--offline` only after a prior online run populated the caches.

**Kotlin/Native iOS stage** — only when Step 1's iOS prerequisites hold, and only behind the lock (Step 4): the
task links a `test.kexe` and runs it on an iOS Simulator via `xcrun simctl spawn --standalone <device-udid>` (booting
a device standalone), so two concurrent runs contend for the same simulator.

```bash
./gradlew :shared:iosSimulatorArm64Test [--tests '<pattern>'] --continue
```

- **An unmatched `--tests` filter on the Kotlin/Native task exits 0** (`BUILD SUCCESSFUL`) and leaves **no**
  `TEST-*.xml` in `shared/build/test-results/iosSimulatorArm64Test/` (verified) — the "matched nothing" signal is
  the missing XML, never the exit code. Report **"no matching tests for `<pattern>` on iosSimulatorArm64"**.
- The first run downloads the Kotlin/Native toolchain into `~/.konan` (hundreds of MB) and links the test binary —
  minutes, not a hang. A run that sits on `iosSimulatorArm64Test` with no output for many minutes while its
  `test.kexe` process uses no CPU is a hang inside the test binary (verified: a test touching
  `UIDevice.currentDevice` hung under `simctl spawn --standalone`); stop it after ~10 minutes, release the lock,
  and report that test task as **timed out** naming the process — not as passed or failed.

## Step 4 — Serialize simulator stages behind the repository lock

Applies to the Kotlin/Native simulator task and the XCTest stage; skip it for Android/JVM-only runs and when the iOS
stages are unverified (nothing to run).

1. **`lock: held`** → the caller holds the lock; go straight to the runs.
2. Otherwise acquire it at the repository root (`git rev-parse --show-toplevel`, else the current directory) — a
   directory, because `mkdir` creates it or fails atomically:

   ```bash
   mkdir .integration-test.lock 2>/dev/null && echo ACQUIRED || echo HELD
   ```

   - **`ACQUIRED`** — write `.integration-test.lock/owner` (via `Write`) with "iru-kmp-test", the scope, and
     `date -u +'%Y-%m-%dT%H:%M:%SZ'`. Check `.integration-test.lock/` is in the root `.gitignore`; if not, say so in
     the report (this skill doesn't edit `.gitignore`).
   - **`HELD`** — say the run is waiting (naming the holder from `cat .integration-test.lock/owner`), re-run the
     `mkdir` roughly every 30 seconds, and never start a simulator run anyway.
   - **Stale**: `find .integration-test.lock -maxdepth 0 -mmin +60` returns the directory → its holder almost
     certainly died; report the owner file, break it (`rm -f .integration-test.lock/owner && rmdir
     .integration-test.lock`), acquire fresh, and say so.
   - **Wait timeout**: still held after ~45 minutes and not stale → the iOS stages are **unverified — blocked by a
     concurrent simulator/integration run**; the Android results still stand.
3. Run the Kotlin/Native task, then the XCTest stage (Step 5), one at a time, in the foreground.
4. **Release** as soon as the last simulator stage ends, on **every** exit path (passed, failed, timed out,
   interrupted): `rm -f .integration-test.lock/owner && rmdir .integration-test.lock`. Never release a lock taken
   under `lock: held`.

## Step 5 — iosApp XCTest stage

Runs when the iOS stages are in scope, an iOS test target exists (`iosApp/iosAppTests/` or a `*Tests` target in
`project.yml`/the scheme), and the scope isn't a Gradle-only class pattern that has no Swift counterpart.

- **Project**: use `iosApp/iosApp.xcodeproj` (or the `.xcworkspace` when CocoaPods made one). Only a
  `project.yml` → run `xcodegen generate --spec iosApp/project.yml` when `xcodegen` is on `PATH`; otherwise report
  the XCTest stage **unverified (project not generated, xcodegen not installed)** — this skill installs nothing.
- **Scheme**: `iosApp` by default; otherwise the sole non-test scheme from `xcodebuild -list -project <project>`.
- **Destination**: `destination:` if given, else the first available iPhone simulator:

  ```bash
  xcrun simctl list devices available -j | python3 -c "
  import json, sys
  for runtime, devices in json.load(sys.stdin)['devices'].items():
      if 'iOS' in runtime:
          for d in devices:
              if d['name'].startswith('iPhone'):
                  print(d['name']); sys.exit(0)
  "
  ```

- **Run** (fresh result bundle outside the repository; the project's pre-build phase runs `./gradlew
  :shared:embedAndSignAppleFrameworkForXcode`, so the Gradle/JDK prerequisites of Step 1 apply here too):

  ```bash
  rm -rf "$TMPDIR/iru-kmp-test-ios.xcresult"
  xcodebuild test -project iosApp/iosApp.xcodeproj -scheme iosApp \
    -destination 'platform=iOS Simulator,name=<device>' \
    [-only-testing:iosAppTests/<Suite>[/<test>]] \
    -resultBundlePath "$TMPDIR/iru-kmp-test-ios.xcresult"
  ```

- **Parse** exactly as `iru-swift-test`'s Step 5 (app path) does: `xcrun xcresulttool get test-results summary
  --path <bundle>` for `passedTests`/`failedTests`/`skippedTests`/`totalTestCount`/`testFailures[]`, and
  `totalTestCount == 0` (`result: "unknown"`) for an unmatched `-only-testing:` — which `xcodebuild` reports as `**
  TEST SUCCEEDED **`, exit 0. A crash exit with a readable bundle is inconclusive, not a failure — read the bundle.

## Step 6 — Parse the JUnit XML

Each Gradle test task writes one `TEST-*.xml` per class to `<module>/build/test-results/<task>/`. Kotlin/Native
results prefix the class name with the task (`iosSimulatorArm64Test.com.example.FooTest`) and suffix each test name
with the target (`greets[iosSimulatorArm64]`) — strip both so the same test reads identically across targets:

```bash
python3 - shared/build/test-results/testAndroidHostTest shared/build/test-results/iosSimulatorArm64Test \
  androidApp/build/test-results/testDebugUnitTest <<'PY'
import glob, os, re, sys
import xml.etree.ElementTree as ET

# argv: one or more "<module>/build/test-results/<task>" directories
for d in sys.argv[1:]:
    files = sorted(glob.glob(os.path.join(d, "TEST-*.xml")))
    task = os.path.basename(d.rstrip("/"))
    if not files:
        print(f"{d}: NO RESULTS (no TEST-*.xml - no matching tests, task skipped, or it never ran)")
        continue
    total = passed = failed = skipped = 0
    failures = []
    for path in files:
        for tc in ET.parse(path).getroot().iter("testcase"):
            total += 1
            # Kotlin/Native prefixes classname with "<task>." and suffixes name with "[<target>]"
            cls = re.sub(r"^" + re.escape(task) + r"\.", "", tc.get("classname", ""))
            name = re.sub(r"\[[A-Za-z0-9]+\]$", "", tc.get("name", ""))
            fail = tc.find("failure")
            if fail is None:
                fail = tc.find("error")
            if fail is not None:
                failed += 1
                lines = (fail.text or "").strip().splitlines()
                failures.append((f"{cls}#{name}", fail.get("message", ""), lines[0] if lines else ""))
            elif tc.find("skipped") is not None:
                skipped += 1
            else:
                passed += 1
    print(f"{d}: total={total} passed={passed} failed={failed} skipped={skipped}")
    for n, msg, first in failures:
        print(f"  FAIL {n}: {msg}\n    {first}")
PY
```

Pass only the directories of tasks that ran in this invocation. A Gradle test task that was `UP-TO-DATE` keeps its
previous XML, which still describes the current inputs — that's fine; but if the build failed before a task ran
(compile error), report the compile error instead of parsing a stale directory.

## Step 7 — Report

Per target, one line: Android host (`:<module>:<task>`), JVM, Android app, iOS simulator (Kotlin/Native), iosApp
XCTest — each **passed** (counts), **failed** (counts plus each failing `Class#test`, the assertion message, the first
stack line, and the XML/`.xcresult` path for the full trace), **no matching tests for `<pattern>`**, **timed out**,
**not applicable** (the project has no such target/test bundle), or **unverified (<reason>)** — non-macOS host, no
Xcode/simulator runtime, project not generated, or blocked by the lock. A test failing on one target only (e.g. iOS
but not Android) is worth calling out explicitly — it usually means an `actual` implementation differs. Mention the
lock only when it was anything other than an immediate acquire. Never paste raw Gradle/xcodebuild output, and never
fix tests or source code — that's a follow-up the user (or `iru-kmp-code-one-task`) drives.

## Known quirks / verification notes

Verified in `$TMPDIR/iru-verify/kmp/iru-kmp-test/` (October 2026, macOS on Apple silicon, Xcode 27.0, JDK 21, Gradle
9.8.1, Kotlin 2.4.21, AGP 9.4.1 with `com.android.kotlin.multiplatform.library` + `withHostTest {}`, a
`com.android.application` `androidApp`, `iosArm64` + `iosSimulatorArm64` targets):

- `./gradlew :shared:tasks --all` listed `testAndroidHostTest`, `iosSimulatorArm64Test`, `allTests` (no
  `iosArm64Test`, no `testDebugUnitTest` on the KMP module); `:androidApp` listed `testDebugUnitTest`.
- `commonTest` tests ran under both `testAndroidHostTest` and `iosSimulatorArm64Test`; XML landed in
  `shared/build/test-results/testAndroidHostTest/TEST-com.example.shared.GreeterTest.xml` and
  `shared/build/test-results/iosSimulatorArm64Test/TEST-iosSimulatorArm64Test.com.example.shared.GreeterTest.xml`
  (`classname="iosSimulatorArm64Test.com.example.shared.GreeterTest"`, `name="greets[iosSimulatorArm64]"`), the
  app's in `androidApp/build/test-results/testDebugUnitTest/`.
- With one failing and one `@Ignore`d common test, `:shared:allTests --continue` ran both targets and the Step 6
  parser reported `total=5 passed=3 failed=1 skipped=1` for each, with `java.lang.AssertionError: expected:<3> but
  was:<1>` (Android) and `kotlin.AssertionError: Expected <3>, actual <1>.` (iOS).
- Unmatched `--tests '*.NoSuchTest'`: `testAndroidHostTest` failed the build with `No tests found for given
  includes`; `iosSimulatorArm64Test` exited 0 and emptied its results directory (only `binary/` left).
- `--tests` placed once after two tasks filtered only the second; repeating it after each task filtered both.
- A Kotlin/Native test calling `UIDevice.currentDevice.systemName()` hung indefinitely under the task's
  `simctl spawn --standalone` run (0% CPU for 4+ minutes); the same tests without UIKit finished in seconds.
- **Unverified locally**: the iosApp XCTest stage (no XcodeGen installed, so no `iosApp.xcodeproj` could be
  generated here — the `xcodebuild test`/`xcresulttool` commands and their zero-match behaviour are
  `iru-swift-test`'s, verified there on Xcode 27), the `androidTarget()` + `com.android.library` variant's
  `testDebugUnitTest` naming (taken from AGP's documented variant tasks), the `iosX64Test` Intel path, and the
  stale-lock/wait branches of Step 4 (the protocol is the catalog's shared one, as in `iru-python-test`).
