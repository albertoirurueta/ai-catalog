---
name: iru-setup-android-github-workflows
description: Create or update the `develop.yml`/`main.yml`/`sync.yml` (gitflow) or `main.yml`/`publish.yml` (main-only) GitHub Actions workflows plus `.github/dependabot.yml` and `security.yml` for an Android/Gradle repository produced by `iru-setup-android-library` or `iru-setup-android-app` — build, unit test, optional instrumented test on a `reactivecircus/android-emulator-runner` emulator, lint with SARIF upload, unit-test coverage via AGP's own `createDebugUnitTestCoverageReport` task (with a vendored-`jacococli.jar` fallback), an optional SonarQube/SonarCloud scan (`:lib:sonar`/`:app:sonar`), a Dokka + Antora documentation build published to GitHub Pages, and — for the `library` flavor — an optional Maven Central publish, or — for the `app` flavor — a signed release build uploaded to Google Play or Firebase App Distribution. Invoke as `/iru-setup-android-github-workflows`. Accepts pre-resolved inputs via `args` (`key: value` lines): `flavor` (`library`/`app`, required), `branching` (`gitflow`/`main-only`, default `gitflow`), `integration-branch` (default `develop`), `stable-branch` (default `main`), `java-version` (default `17`), `run-instrumented-tests` (`yes`/`no`), `api-level` (default `35`), plus this catalog's shared workflow-args vocabulary — `open-source`, `publish` (library only), `distribution` (`none`/`internal`/`store`, app only), `sonar` (`cloud`/`self-hosted`/`none` + `sonar-organization`/`sonar-project-key`/`sonar-host-url`), `mode` (`new`/`existing`), and the four `security-*` opt-outs plus two security opt-ins — so an orchestrating skill can supply them without re-prompting. Ships with generic example templates (genericized, no real repo/org/person names) derived from a real Android library repository's actual `main.yml`/`publish.yml` (linked in Step 3) — see Step 6 for how they were adapted into the `gitflow` variant's `develop.yml`/`main.yml`/`sync.yml`. Creates all workflows (and the sync/security scripts) from scratch if none exist; if any already exists, asks the user whether to stop or attempt an update using the templates as reference, preserving any step/job this skill doesn't own. Use whenever an Android/Gradle repository needs this CI/CD release and security pipeline bootstrapped or brought in line with this house pattern, instead of hand-writing the YAML.
model: haiku
---

# Setup Android GitHub Workflows

Scaffold (or update) the GitHub Actions workflows plus a Dependabot config for an Android/Gradle repository
produced by `iru-setup-android-library` or `iru-setup-android-app`, for whichever `branching` model the
repository actually uses:

- **`branching: gitflow`** (default) — **`develop.yml`** (push to the integration branch + `workflow_dispatch`),
  **`main.yml`** (triggered by a published GitHub Release instead — the same pipeline, plus the actual
  publish/store step), and **`sync.yml`** + its companion `.github/scripts/sync_versions.py` (opens a pull
  request merging the released branch back into the integration branch and bumping the development
  `-SNAPSHOT` version once a release lands).
- **`branching: main-only`** — **`main.yml`** (push/PR to the stable branch — build and test only, no
  publish/store step) and **`publish.yml`** (triggered by a published GitHub Release — the actual publish/store
  step). No `sync.yml` — there's no second branch to sync back into.
- **`security.yml`** and **`.github/dependabot.yml`** — generated (or updated) regardless of `branching`: a
  `dependency-review` job, a CodeQL job (`java-kotlin`, `build-mode: autobuild`), an OSV-Scanner job, a
  `gitleaks` job (each individually omittable via `args`), plus two opt-in jobs (OWASP dependency-check,
  `MobSF/mobsfscan` — apps only), and grouped weekly Dependabot updates for the `gradle` and `github-actions`
  ecosystems.

Every pipeline stage differs slightly by `flavor`:

- **`flavor: library`** — runs `<lib-module>:dokkaGenerate`, publishes Dokka + Antora docs to GitHub Pages,
  runs `:<lib-module>:sonar` when `sonar` isn't `none`, and — only in `main.yml`, only when `publish: yes` —
  publishes to Maven Central (a plain snapshot publish under `gitflow`'s `develop.yml`, a full
  `assembleRelease` + `publishAndReleaseToMavenCentral` under the release-triggered workflow).
- **`flavor: app`** — no Dokka/Antora-docs job, runs `:<app-module>:sonar` instead of `:<lib-module>:sonar`,
  and — only in the release-triggered workflow, only when `distribution` isn't `none` — decodes a keystore,
  runs `:<app-module>:bundleRelease`, and uploads to Google Play (`distribution: store`) or Firebase App
  Distribution (`distribution: internal`).

This skill is designed for the Gradle project shape `iru-setup-android-library`/`iru-setup-android-app`
produce — Gradle task names (`test`, `lint`, `<lib-module>:dokkaGenerate`, `<lib-module>:sonar`,
`createDebugUnitTestCoverageReport`, `lib:publishToMavenCentral`), the `mavenPublishing`/`sonar {}` Gradle DSL
blocks, and the `libraryVersion`/`versionName`/`versionCode` version scheme (`iru-android-bump-version`) are
all assumed. If neither `lib/build.gradle.kts` nor `app/build.gradle.kts` exists at the repository root, warn
the user this skill's templates assume that layout and most of Step 1's survey won't resolve, then use
`AskUserQuestion` to ask whether to stop here or continue anyway (treating every Gradle-derived placeholder in
Step 3+ as an open gap to ask about directly, called out again in the final report).

## Step 0 — Resolve inputs

This skill can be invoked stand-alone (`/iru-setup-android-github-workflows`) or as a step inside another
skill, which resolves the parameters below itself and passes them through `args` as `key: value` lines, one
per line, e.g.:

```
flavor: library
branching: gitflow
integration-branch: develop
stable-branch: main
java-version: 17
run-instrumented-tests: yes
api-level: 35
open-source: yes
publish: yes
sonar: cloud
sonar-organization: example-org
sonar-project-key: example-org_example-library
sonar-host-url: https://sonarcloud.io
security-dependency-review: yes
security-codeql: yes
security-osv: yes
security-gitleaks: yes
security-owasp-dependency-check: no
security-mobsfscan: no
```

Parse any such lines first; for each key found there, use that value directly and skip the matching
fact-finding step below. If `args` is absent or doesn't look like this format, treat everything as unset and
gather every fact via Step 1's survey / `AskUserQuestion` instead. Bounded choices (`flavor`, `branching`,
`sonar`, `publish`/`distribution`, the `security-*` toggles) go through `AskUserQuestion` with at most four
options per question when not resolved by `args` or Step 1's survey; free-text values (branch names, the
Sonar organization/key/host, `java-version`, `api-level`) are asked as plain conversation.

| `args` key | Meaning | Default / resolution |
|---|---|---|
| `flavor` | `library` or `app` | Required — detect from Step 1 if not given, ask if ambiguous |
| `branching` | `gitflow` or `main-only` | `gitflow` |
| `integration-branch` | Branch `develop.yml` pushes on (gitflow only) | `develop` |
| `stable-branch` | Branch releases are published from | `main` |
| `java-version` | JDK version for `actions/setup-java` | `17` (matches the reference repository, and `iru-setup-android-library`/`-app`'s `sourceCompatibility`) |
| `run-instrumented-tests` | Whether to run `connectedAndroidTest` on an emulator | Ask — instrumented tests need KVM/emulator time and are slower; default recommendation `no` for a first setup, `yes` once the module actually has instrumented tests under `src/androidTest` |
| `api-level` | Emulator API level for `reactivecircus/android-emulator-runner` | `35` (matches the reference repository; independent of `compileSdk` — see Step 12) |
| `open-source` | `yes`/`no` | `gh repo view --json isPrivate` if unresolved otherwise |
| `publish` (library only) | `yes`/`no` — gates the Maven Central publish steps | `yes` only when `open-source: yes`; otherwise ask, `no` recommended |
| `distribution` (app only) | `none`/`internal`/`store` — gates the release upload step | `store` only when `open-source: yes`; otherwise ask, `none` recommended |
| `sonar` | `cloud`/`self-hosted`/`none` | `cloud` when `open-source: yes`. When not open source, state that SonarCloud is free only for open-source projects (a paid plan is required otherwise) and recommend `none`, offering self-hosted SonarQube (`self-hosted`) as the second option — the same wording `iru-setup-android-library`/`-app` use in their Step 2 |
| `sonar-organization` / `sonar-project-key` / `sonar-host-url` | Sonar coordinates | Only asked when `sonar` isn't `none`; read from `lib/build.gradle.kts`'s or `app/build.gradle.kts`'s existing `sonar {}` block first (Step 1) |
| `mode` | `new`/`existing` | Whether this is a first-time setup or a re-run against an existing pipeline; if `existing`, go straight to Step 1's stop-or-update path |
| `security-dependency-review` / `security-codeql` / `security-osv` / `security-gitleaks` | `yes`/`no`, each gates one `security.yml` job | `yes` |
| `security-owasp-dependency-check` | `yes`/`no` — opt-in OWASP Dependency-Check job | `no` |
| `security-mobsfscan` | `yes`/`no` — opt-in `MobSF/mobsfscan` job, **app flavor only** | `no` |
| `license` / `developer-name` / `developer-email` / `organization-url` | This catalog's shared scaffold-args vocabulary | **Not used by this skill's generated files** — accepted only so an orchestrator can pass its full shared-args set without this skill erroring on unrecognized keys; note this in the final report if any were supplied |

`.github/dependabot.yml` has no opt-out key — it's always generated/updated, same as the Java/TypeScript
siblings.

## Step 1 — Survey the target repository

Gather every fact Step 0 didn't already resolve via `args`, and decide whether this is a fresh setup or an
update:

- **Module layout**: check for `lib/build.gradle.kts` and `app/build.gradle.kts`. Both present → this is the
  `iru-setup-android-library` scaffold shape (a `lib/` library plus an `app/` Compose sample/demo module —
  Step 3's test-result and coverage globs must cover **both** modules regardless of `flavor`, since the sample
  app has its own tests). Only `app/build.gradle.kts` present → the `iru-setup-android-app` scaffold shape
  (`flavor: app`, no `lib/` module at all — every `lib/**` glob and the Dokka/Sonar-on-`lib` steps are omitted
  entirely, not just gated). Only `lib/build.gradle.kts` present → a library repository with no sample app
  module; omit every `app/**` glob and the app-release job. Record which of `<lib-module>`/`<app-module>`
  (Gradle project paths — almost always `lib`/`app`, but read the actual `include(...)` lines in
  `settings.gradle.kts` to be sure) actually exist.
- **`flavor`** (skip if supplied via `args`): `app/build.gradle.kts` present with `com.android.application`
  and no `lib/build.gradle.kts` → `app`; `lib/build.gradle.kts` present with `com.android.library` → `library`
  (regardless of whether a sample `app/` module also exists). Ask if genuinely ambiguous.
- **Existing `sonar {}` block**: grep `lib/build.gradle.kts`/`app/build.gradle.kts` for `sonar {` — if present,
  read its `sonar.organization`/`sonar.projectKey`/`sonar.host.url` properties directly rather than asking
  the user again; treat this as `sonar: cloud` (host is `https://sonarcloud.io` or unset) or `sonar:
  self-hosted` (any other host). If absent, fall back to Step 0's `sonar` resolution.
- **Existing `mavenPublishing {}` block** (library only): grep `lib/build.gradle.kts` for
  `mavenPublishing {` — presence implies `publish: yes` already at scaffold time; record the `coordinates(...)`
  group/artifact id for the placeholder table (Step 8). Absence doesn't necessarily mean `publish: no` — the
  user may still want CI to publish once the block is added; don't silently downgrade `publish` from what
  `args`/Step 0 resolved, just note the mismatch.
- **Existing signing config** (app only): grep `app/build.gradle.kts` for `signingConfigs` /
  `hasReleaseSigning` — `iru-setup-android-app`'s template reads `SIGNING_STORE_FILE`,
  `SIGNING_STORE_PASSWORD`, `SIGNING_KEY_ALIAS`, `SIGNING_KEY_PASSWORD` from the environment (not from CI
  secrets directly) — the release workflow must therefore *export* those exact env var names from the
  `ANDROID_KEYSTORE_*`/`ANDROID_KEY_*` secrets (Step 4's `main.yml`/`publish.yml` templates do this). If the
  build script instead reads different env var names, note the mismatch and adjust the template.
- **Existing store/distribution plugin** (app only, `distribution: store`): grep `app/build.gradle.kts` for
  `com.github.triplet.play` (Gradle Play Publisher plugin). If present, prefer `./gradlew
  :<app-module>:publishBundle` in the release workflow over the workflow-level `r0adkll/upload-google-play`
  action (Step 4 notes both forms); if absent, use the workflow-level action, which needs no Gradle-side
  wiring at all.
- **Vendored `jacococli.jar`**: `find . -path '*/jacoco-*/lib/jacococli.jar' -maxdepth 4` (or similar). Present
  → this repository still carries the reference repository's older vendored-JaCoCo-CLI layout; the coverage
  conversion step's fallback template (Step 3) applies and should be the one actually emitted. Absent (the
  common case for a fresh `iru-setup-android-library`/`-app` scaffold, per that skill's own verified finding
  that AGP's `createDebugUnitTestCoverageReport` already emits XML directly) → emit only the AGP-path step,
  skip the fallback template entirely rather than generating a step referencing a jar that doesn't exist.
- **`enableUnitTestCoverage = true` per module**: grep `lib/build.gradle.kts`'s and `app/build.gradle.kts`'s
  `buildTypes { debug { ... } }` block for this flag before deciding which module(s) the coverage-conversion
  step (Step 4) targets — confirmed by actually running the task that `flavor: library`'s sample `app/`
  module (`iru-setup-android-library`'s own Step 7 template) does **not** set it, so
  `:<app-module>:createDebugUnitTestCoverageReport` fails outright there (`Cannot locate tasks that match
  '...'`, not a silent no-op) — never emit a coverage task against a module that doesn't enable it.
- **`docs/antora.yml` / `docs/antora-playbook.yml`** (library flavor, or app flavor if it happens to have
  docs): if either is missing, the Antora build step has nothing to build against — recommend running
  `iru-setup-antora` first, or confirm the user will do so before merging this workflow.
- **Branch names** (skip if supplied via `args`): confirm the integration/stable branch names actually match
  this repository's branching model (`git branch -a`) rather than assuming gitflow defaults; for
  `branching: main-only`, only `stable-branch` matters.
- **README/Antora version-snippet wording** (needed for `sync_versions.py`, gitflow only): grep for the same
  marker text `iru-android-bump-version`'s Step 8 looks for — `grep -n "implementation \['\"]" README.md` and
  `grep -rl "implementation.*[0-9]\+\.[0-9]\+\.[0-9]\+" docs/modules/ROOT/pages/*.adoc`. Note the exact line
  shape found (Groovy `implementation 'group:artifact:version'` vs. Kotlin-DSL
  `implementation("group:artifact:version")`) so Step 5's `sync_versions.py` regex matches it.
- **Existing workflows**: check whether `.github/workflows/develop.yml`, `.github/workflows/main.yml`,
  `.github/workflows/sync.yml`, `.github/scripts/sync_versions.py`, `.github/workflows/publish.yml`,
  `.github/workflows/security.yml`, and `.github/dependabot.yml` already exist (only the subset relevant to
  the resolved `branching`, plus the two always-present files).

### Stop or update

- **None of the relevant files exist** (or `mode: new`): skip straight to Step 2 — create everything from
  scratch.
- **Any relevant file already exists** (or `mode: existing`): use `AskUserQuestion` to ask whether to (a) stop
  here and leave everything untouched, or (b) continue and attempt to update the existing file(s) using this
  skill's templates as reference.
  - **Stop**: report which file(s) already exist and end here — make no changes.
  - **Continue**: proceed to Step 11, but treat each existing file as the base to edit, not something to
    overwrite wholesale:
    - For `develop.yml`/`main.yml` (gitflow) or `main.yml` (main-only): preserve any step/job this skill
      doesn't own (build/test/lint/coverage/SARIF-upload/optional-Sonar/optional-Dokka-Antora-Pages/optional-
      publish-or-release) — e.g. a Slack notification step, an extra matrix entry, or an additional module's
      build step stays untouched. Only add missing stages or correct outdated ones (wrong action version,
      wrong task name, a stage that should now be gated on/off per `sonar`/`publish`/`distribution`/
      `run-instrumented-tests`), and don't reorder foreign steps.
    - For `sync.yml`/`sync_versions.py` (gitflow) or `publish.yml` (main-only): preserve any file the script
      updates beyond `lib/build.gradle.kts`/`app/build.gradle.kts`/`README.md`/the Antora docs that a prior
      customization added, and preserve any extra workflow step the same way.
    - For `security.yml`: preserve any job this skill doesn't own; only add/remove/update the
      dependency-review/CodeQL/OSV-Scanner/gitleaks/OWASP-dependency-check/mobsfscan jobs per the resolved
      `security-*` args.
    - For `.github/dependabot.yml`: preserve any `updates:` entry for an ecosystem this skill doesn't manage
      (e.g. `npm` for `docs/`); only add/update the `gradle` and `github-actions` entries.

## Step 2 — Look up action versions at run time

**Versions are looked up at run time, not hardcoded from this file.** Use the GitHub Releases/tags API
(`gh api repos/<owner>/<action>/releases/latest`, or `.../tags` — see the "Floating major tag" column below,
since not every action publishes one) for every `uses:` action major, and the npm registry
(`npm view antora version`, etc.) for the Antora toolchain packages `build.yml`'s Antora step installs. If a
lookup is unreachable, fall back to the versions confirmed current as of **September 2026**, listed here
(all confirmed to resolve as an actual `git ls-remote --tags` ref during this skill's own
verification pass — see Step 12 for the two that don't have a floating major tag):

| Action | Fallback version | Floating major tag? | Notes |
|---|---|---|---|
| `actions/checkout` | `v7` | yes | |
| `actions/setup-java` | `v6` | yes | |
| `gradle/actions/setup-gradle` | `v6` | yes | subpath action inside the `gradle/actions` monorepo |
| `reactivecircus/android-emulator-runner` | `v2` | yes | only when `run-instrumented-tests: yes` |
| `EnricoMi/publish-unit-test-result-action` | `v2` | yes | |
| `github/codeql-action` (`init`/`analyze`/`upload-sarif`) | `v4` | yes | resolve via `.../tags`, not `.../releases/latest` — that endpoint returns the unrelated `codeql-bundle-*` tag |
| `actions/upload-pages-artifact` | `v5` | yes | |
| `actions/deploy-pages` | `v5` | yes | |
| `actions/setup-node` | `v7` | yes | used only for the Antora build step |
| `actions/setup-python` | `v7` | yes | used only by `sync.yml`, `branching: gitflow` only |
| `actions/dependency-review-action` | **`v5.0.0`** | **no** | this action has never published a floating `v5` tag — only exact-version tags (`v5.0.0`, `v4.9.0`, …); pin the exact version and re-check at generation time whether a floating major now exists |
| `google/osv-scanner-action` (reusable workflow) | **`v2.6.0`** | **no** | same situation — pin the workflow ref to the exact tag, e.g. `google/osv-scanner-action/.github/workflows/osv-scanner-reusable.yml@v2.6.0` |
| `gitleaks/gitleaks-action` | `v3` | yes | |
| `r0adkll/upload-google-play` | `v1` | yes | `flavor: app`, `distribution: store`, workflow-level upload only |
| `wzieba/Firebase-Distribution-Github-Action` | `v1` | yes | `flavor: app`, `distribution: internal` |

`GITHUB_TOKEN`'s automatic scopes are sufficient for every job above except where a secret is explicitly named
in Step 4/6's templates.

## Step 3 — Reference workflows this skill's templates are derived from

The `main-only` branching variant's `main.yml`/`publish.yml` templates (Step 6) are genericized directly from a
real Android library repository's actual workflows:
<https://github.com/albertoirurueta/irurueta-android-glutils/blob/main/.github/workflows/main.yml> and
<https://github.com/albertoirurueta/irurueta-android-glutils/blob/main/.github/workflows/publish.yml>. That
repository has no `develop.yml` — it pushes/PRs directly against `main` — which is exactly the `main-only`
branching model. The `gitflow` variant's `develop.yml`/`main.yml`/`sync.yml` (Step 4/5) are this skill's own
adaptation of the same pipeline onto two branches, following the same integration/stable-branch split and
`sync.yml` shape this catalog's `iru-setup-java-github-workflows`/`iru-setup-typescript-github-workflows`
already establish for their own ecosystems (see Step 6 for exactly what changed and why).

Every `<placeholder>` below is resolved from Step 1's survey / Step 0's `args` before writing the real files —
the full resolution table is in Step 8. Drop whichever blocks this repository's `flavor`/`sonar`/`publish`/
`distribution`/`run-instrumented-tests` values gate off, per the inline comments in the templates, including
the comment itself — it's authoring guidance, not part of the generated file.

## Step 4 — `develop.yml` / `main.yml` templates (`branching: gitflow`)

`develop.yml` and `main.yml` share the same build/test/lint/coverage/docs pipeline; only the trigger differs
(a push to the integration branch vs. a published GitHub Release), and `main.yml` appends the actual
publish/store step. Both are shown as one annotated template — write `main.yml` by copying every step under
`develop.yml`'s `build` job verbatim, changing only the `on:` block, and appending the release-only steps
marked below.

### `develop.yml`

```yaml
name: Develop

on:
  push:
    branches: [ <integration-branch> ]
  workflow_dispatch:

permissions:
  checks: write
  pull-requests: write
  contents: write
  security-events: write   # required by github/codeql-action/upload-sarif (the Lint SARIF upload steps below)

jobs:
  build:
    name: Build and execute tests
    runs-on: ubuntu-latest
    steps:
      - name: Check out code
        uses: actions/checkout@v7
        with:
          fetch-depth: 0

      # Only when run-instrumented-tests: yes — the emulator needs hardware acceleration, which GitHub-hosted
      # Linux runners don't expose by default.
      - name: Enable KVM
        run: |
          echo 'KERNEL=="kvm", GROUP="kvm", MODE="0666", OPTIONS+="static_node=kvm"' | sudo tee /etc/udev/rules.d/99-kvm4all.rules
          sudo udevadm control --reload-rules
          sudo udevadm trigger --name-match=kvm

      - name: Set up JDK <java-version>
        uses: actions/setup-java@v6
        with:
          distribution: temurin
          java-version: '<java-version>'

      - name: Set up Gradle
        uses: gradle/actions/setup-gradle@v6
        with:
          dependency-graph: generate-and-submit

      # run-instrumented-tests: yes — runs the build/test/lint/docs command INSIDE the emulator so
      # connectedAndroidTest has a device to target. flavor: library includes `<lib-module>:dokkaGenerate` in
      # the same script (matching the reference repository exactly); flavor: app omits it (no docs module).
      - name: Run tests
        uses: reactivecircus/android-emulator-runner@v2
        with:
          api-level: <api-level>
          target: google_apis
          arch: x86_64
          script: ./gradlew clean test connectedAndroidTest lint <lib-module>:dokkaGenerate

      # run-instrumented-tests: no — plain Gradle invocation, no emulator/KVM step above either.
      - name: Run tests
        run: ./gradlew clean test lint <lib-module>:dokkaGenerate

      - name: Publish test results
        uses: EnricoMi/publish-unit-test-result-action@v2
        if: (!cancelled())
        with:
          files: |
            <app-module>/build/test-results/**/*.xml
            <app-module>/build/outputs/androidTest-results/**/*.xml
            <lib-module>/build/test-results/**/*.xml
            <lib-module>/build/outputs/androidTest-results/**/*.xml

      # Preferred path — confirmed working against the AGP version iru-setup-android-library/-app resolved:
      # createDebugUnitTestCoverageReport emits build/reports/coverage/test/debug/report.xml directly, no
      # .exec-to-XML conversion needed. Use this form unless Step 1's survey found a vendored
      # jacoco-*/lib/jacococli.jar (the fallback immediately below). IMPORTANT — only target the module(s)
      # that actually set `enableUnitTestCoverage = true` in their buildTypes.debug block (Step 1's survey):
      # `iru-setup-android-library`'s OWN sample `app/` module does NOT set it (confirmed by running this
      # task against it — `Cannot locate tasks that match ':<app-module>:createDebugUnitTestCoverageReport'`,
      # a hard failure, not a no-op), so for `flavor: library` this targets `<lib-module>` ONLY, even when a
      # sample `app/` module also exists. For `flavor: app`, `iru-setup-android-app`'s own template DOES set
      # it, so this targets `<app-module>` instead.
      - name: Convert unit tests coverage results
        run: ./gradlew <lib-module>:createDebugUnitTestCoverageReport
      # flavor: app instead: run: ./gradlew <app-module>:createDebugUnitTestCoverageReport

      # Fallback — only when Step 1's survey found a vendored jacoco-<ver>/lib/jacococli.jar (an older layout
      # some repositories still carry over from before AGP emitted the XML report directly), or the user
      # explicitly asked for it instead. Converts the raw .exec file AGP still writes alongside the XML by
      # hand — this mirrors the reference repository's own older CI step, with paths corrected to where AGP
      # actually writes the .exec file under the version this catalog's Android skills resolved (NOT
      # `<lib-module>/build/jacoco/testReleaseUnitTest.exec`, which is where the reference repository's
      # older CI looked, and is stale).
      - name: Convert unit tests coverage results (vendored jacococli.jar fallback)
        run: |
          mkdir -p <lib-module>/build/reports/coverage/test/debug || true
          java -jar jacoco-<jacoco-cli-version>/lib/jacococli.jar report \
            <lib-module>/build/outputs/unit_test_code_coverage/debugUnitTest/testDebugUnitTest.exec \
            --classfiles <lib-module>/build/tmp/kotlin-classes/debug \
            --sourcefiles <lib-module>/src/main/java \
            --xml <lib-module>/build/reports/coverage/test/debug/report.xml || true

      - name: Upload lint SARIF results
        if: (!cancelled())
        uses: github/codeql-action/upload-sarif@v4
        with:
          sarif_file: <lib-module>/build/reports/lint-results-debug.sarif

      # Only when app/** exists alongside lib/** (the iru-setup-android-library sample module), or flavor: app
      - name: Upload app lint SARIF results
        if: (!cancelled())
        uses: github/codeql-action/upload-sarif@v4
        with:
          sarif_file: <app-module>/build/reports/lint-results-debug.sarif

      # Omit this whole step if sonar: none (Step 0). flavor: library runs `:<lib-module>:sonar`; flavor: app
      # runs `:<app-module>:sonar` instead (there is no lib module to scan).
      - name: Run SonarCloud analysis
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
        run: ./gradlew :<lib-module>:sonar

      # Omit this whole block if flavor: app — no docs module to publish.
      - name: Set up Node
        uses: actions/setup-node@v7
        with:
          node-version: 24

      - name: Install Antora
        run: |
          mkdir -p docs-toolchain && cd docs-toolchain
          npm i -D -E antora
          npm i @antora/lunr-extension
          npm i @sntke/antora-mermaid-extension
          npm i @djencks/asciidoctor-mathjax

      - name: Build Antora docs
        run: cd docs && npx antora antora-playbook.yml

      - name: Merge Dokka API docs into the Antora site
        run: |
          touch ./docs/build/site/.nojekyll
          mkdir -p ./docs/build/site/api
          cp -r ./<lib-module>/build/dokka/html/. ./docs/build/site/api/

      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v5
        with:
          path: ./docs/build/site
      # End of the flavor: app omission block

      # Omit this whole step if publish: no (Step 0). flavor: library only — a plain snapshot publish, no
      # release build/signing (the version in libraryVersion is already a -SNAPSHOT string on this branch).
      - name: Publish snapshot to Maven Central
        run: ./gradlew <lib-module>:publishToMavenCentral --no-configuration-cache
        env:
          ORG_GRADLE_PROJECT_mavenCentralUsername: ${{ secrets.MAVEN_CENTRAL_USERNAME }}
          ORG_GRADLE_PROJECT_mavenCentralPassword: ${{ secrets.MAVEN_CENTRAL_PASSWORD }}
          ORG_GRADLE_PROJECT_signingInMemoryKey: ${{ secrets.SIGNING_MEMORY_KEY }}
          ORG_GRADLE_PROJECT_signingInMemoryKeyId: ${{ secrets.SIGNING_MEMORY_KEY_ID }}
          ORG_GRADLE_PROJECT_signingInMemoryKeyPassword: ${{ secrets.SIGNING_IN_MEMORY_KEY_PASSWORD }}

  # Omit this whole job if flavor: app (no docs to deploy).
  deploy-docs:
    name: Deploy docs to GitHub Pages
    needs: build
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v5
```

Notes specific to this template:

- Only **one** of the two `Run tests` steps applies per repository (`run-instrumented-tests: yes`/`no`) — keep
  the matching one and drop the other, plus the `Enable KVM` step when `no`.
- Only **one** of the two `Convert unit tests coverage results` steps applies (Step 1's vendored-jar survey) —
  keep the AGP-path step unless a vendored `jacococli.jar` was actually found.
- `<lib-module>:dokkaGenerate` and the app's own lint SARIF upload are both present in the same `Run tests`
  script regardless of `flavor` when both `lib/` and `app/` modules exist (the `iru-setup-android-library`
  sample-app shape) — only drop the `app/**`-scoped steps entirely when no `app/` module exists at all, and
  only drop `<lib-module>:dokkaGenerate`/the Sonar-on-lib/Antora block when no `lib/` module exists at all
  (`flavor: app` with no sample library).
- The `Publish snapshot to Maven Central` step's five `ORG_GRADLE_PROJECT_*` env vars and `--no-configuration-
  cache` flag are carried over verbatim from the reference repository's `publish.yml` (Step 3) — Vanniktech's
  Maven Publish plugin reads Maven Central credentials/signing material from exactly these Gradle project
  properties, and its publish tasks are confirmed incompatible with Gradle's configuration cache.

### `main.yml`

Identical to every step under `develop.yml`'s `build` job above, verbatim — including the same
`run-instrumented-tests`/vendored-jar/`sonar`/`flavor` gating — except the trigger, and the release-only
addition appended at the end of the job:

```yaml
name: Release

on:
  release:
    types: [released]
  workflow_dispatch:

permissions:
  checks: write
  pull-requests: write
  contents: write
  security-events: write   # required by github/codeql-action/upload-sarif (the Lint SARIF upload steps below)

jobs:
  build:
    name: Build and execute tests
    runs-on: ubuntu-latest
    steps:
      # ... identical to every step under develop.yml's `build` job above, verbatim ...

      # flavor: library, publish: yes — a full release build + publish, appended after every step above
      # (replaces develop.yml's plain snapshot-publish step with the real release path).
      - name: Release build
        run: ./gradlew :<lib-module>:assembleRelease

      - name: Publish to Maven Central
        run: ./gradlew <lib-module>:publishAndReleaseToMavenCentral --no-configuration-cache
        env:
          ORG_GRADLE_PROJECT_mavenCentralUsername: ${{ secrets.MAVEN_CENTRAL_USERNAME }}
          ORG_GRADLE_PROJECT_mavenCentralPassword: ${{ secrets.MAVEN_CENTRAL_PASSWORD }}
          ORG_GRADLE_PROJECT_signingInMemoryKey: ${{ secrets.SIGNING_MEMORY_KEY }}
          ORG_GRADLE_PROJECT_signingInMemoryKeyId: ${{ secrets.SIGNING_MEMORY_KEY_ID }}
          ORG_GRADLE_PROJECT_signingInMemoryKeyPassword: ${{ secrets.SIGNING_IN_MEMORY_KEY_PASSWORD }}

      # flavor: app, distribution != none — signs and bundles the release build, then uploads per
      # `distribution`. iru-setup-android-app's app/build.gradle.kts reads these four EXACT env var names
      # (SIGNING_STORE_FILE / SIGNING_STORE_PASSWORD / SIGNING_KEY_ALIAS / SIGNING_KEY_PASSWORD) via
      # System.getenv() — map the ANDROID_KEYSTORE_*/ANDROID_KEY_* secrets onto them here.
      - name: Decode Android keystore
        run: echo "${{ secrets.ANDROID_KEYSTORE_BASE64 }}" | base64 -d > <app-module>/release.jks

      - name: Build signed release bundle
        run: ./gradlew :<app-module>:bundleRelease
        env:
          SIGNING_STORE_FILE: release.jks
          SIGNING_STORE_PASSWORD: ${{ secrets.ANDROID_KEYSTORE_PASSWORD }}
          SIGNING_KEY_ALIAS: ${{ secrets.ANDROID_KEY_ALIAS }}
          SIGNING_KEY_PASSWORD: ${{ secrets.ANDROID_KEY_PASSWORD }}

      # distribution: store, and no com.github.triplet.play plugin found in Step 1's survey — the
      # workflow-level upload action. If that plugin WAS found instead, replace this step with
      # `run: ./gradlew :<app-module>:publishBundle` (with the same PLAY_SERVICE_ACCOUNT_JSON-derived
      # credentials the plugin's own `play { serviceAccountCredentials.set(...) }` block expects) and drop
      # this action entirely.
      - name: Upload to Google Play
        uses: r0adkll/upload-google-play@v1
        with:
          serviceAccountJsonPlainText: ${{ secrets.PLAY_SERVICE_ACCOUNT_JSON }}
          packageName: <application-id>
          releaseFiles: <app-module>/build/outputs/bundle/release/<app-module>-release.aab
          track: production

      # distribution: internal
      - name: Distribute via Firebase App Distribution
        uses: wzieba/Firebase-Distribution-Github-Action@v1
        with:
          appId: ${{ secrets.FIREBASE_APP_ID }}
          serviceCredentialsFileContent: ${{ secrets.FIREBASE_SERVICE_CREDENTIALS }}
          groups: internal-testers
          file: <app-module>/build/outputs/bundle/release/<app-module>-release.aab

  # Same deploy-docs job as develop.yml (flavor: library only) — omitted here for brevity, copy verbatim.
```

Notes specific to this template:

- `<app-module>/release.jks` is written at build time from a base64 secret and is never committed — confirm
  `*.jks` is gitignored (`iru-setup-android-gitignore` already covers this and explicitly anticipates this
  exact path).
- `workflow_dispatch` is added alongside `release: [released]` (the reference repository's `publish.yml` has
  neither `workflow_dispatch` nor a push trigger — this skill adds `workflow_dispatch` for a manual re-run
  without cutting a new release, consistent with the Java/TypeScript siblings' `main.yml`/`release.yml`).

## Step 5 — `sync.yml` + `sync_versions.py` templates (`branching: gitflow` only)

Runs once a GitHub Release is published, provided it was published from the stable branch. Opens a pull
request that merges the released branch back into the integration branch and bumps the development
`-SNAPSHOT` version via the companion `sync_versions.py` script — a direct Gradle port of
`iru-setup-java-github-workflows`'s `sync.yml`/`sync_versions.py` (same branch-merge/PR-creation shell logic,
different version-bump target files), using the exact same rewrite rules `iru-android-bump-version` uses so
the two stay consistent.

### `sync.yml`

```yaml
name: Sync

# After a release is published from <stable-branch>, open a pull request that merges it back into
# <integration-branch> and bumps the development -SNAPSHOT version, so <integration-branch> never has to wait
# for a manual sync branch.
on:
  release:
    types: [released]

permissions:
  contents: write
  pull-requests: write

jobs:
  sync:
    name: Open sync PR from the released branch into <integration-branch>
    runs-on: ubuntu-latest
    if: github.event.release.target_commitish == '<stable-branch>'
    steps:
      - name: Check out code
        uses: actions/checkout@v7
        with:
          fetch-depth: 0

      - name: Compute versions and branch names
        id: versions
        run: |
          set -euo pipefail
          RELEASE_VERSION="${{ github.event.release.tag_name }}"
          RELEASE_VERSION="${RELEASE_VERSION#v}"

          IFS='.' read -r MAJOR MINOR PATCH <<< "$RELEASE_VERSION"
          if [ -z "${MAJOR:-}" ] || [ -z "${MINOR:-}" ] || [ -z "${PATCH:-}" ]; then
            echo "::error::Release tag '$RELEASE_VERSION' is not in X.Y.Z form; cannot compute the next snapshot."
            exit 1
          fi

          NEXT_PATCH=$((PATCH + 1))
          NEXT_SNAPSHOT="${MAJOR}.${MINOR}.${NEXT_PATCH}-SNAPSHOT"
          SYNC_BRANCH="sync_${MAJOR}.${MINOR}.${NEXT_PATCH}"

          echo "release_version=$RELEASE_VERSION" >> "$GITHUB_OUTPUT"
          echo "next_snapshot=$NEXT_SNAPSHOT" >> "$GITHUB_OUTPUT"
          echo "sync_branch=$SYNC_BRANCH" >> "$GITHUB_OUTPUT"

      - name: Skip if this release was already synced
        id: guard
        run: |
          set -euo pipefail
          if git ls-remote --exit-code --heads origin "${{ steps.versions.outputs.sync_branch }}" >/dev/null 2>&1; then
            echo "::notice::${{ steps.versions.outputs.sync_branch }} already exists on origin; skipping."
            echo "exists=true" >> "$GITHUB_OUTPUT"
          else
            echo "exists=false" >> "$GITHUB_OUTPUT"
          fi

      - name: Configure git identity
        if: steps.guard.outputs.exists == 'false'
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

      - name: Create sync branch from <integration-branch>
        if: steps.guard.outputs.exists == 'false'
        run: |
          git fetch origin <integration-branch> <stable-branch>
          git checkout -b "${{ steps.versions.outputs.sync_branch }}" "origin/<integration-branch>"

      - name: Merge the released branch into the sync branch
        if: steps.guard.outputs.exists == 'false'
        run: |
          git merge --no-ff --no-edit \
            -m "Merge <stable-branch> (${{ steps.versions.outputs.release_version }}) into <integration-branch>" \
            "origin/<stable-branch>"

      - name: Set up Python
        if: steps.guard.outputs.exists == 'false'
        uses: actions/setup-python@v7
        with:
          python-version: '3.x'

      - name: Bump the development snapshot version
        if: steps.guard.outputs.exists == 'false'
        env:
          RELEASE_VERSION: ${{ steps.versions.outputs.release_version }}
          NEXT_SNAPSHOT: ${{ steps.versions.outputs.next_snapshot }}
        run: python3 .github/scripts/sync_versions.py

      - name: Commit the version bump
        if: steps.guard.outputs.exists == 'false'
        run: |
          # --ignore-errors keeps a missing README/docs tree (or module) from aborting the step with
          # "fatal: pathspec ... did not match any files"; whatever does exist is staged.
          git add --ignore-errors -- <lib-module>/build.gradle.kts <app-module>/build.gradle.kts README.md docs/antora.yml docs/modules/ROOT/pages || true
          git diff --cached --quiet || git commit -m "Sync ${{ steps.versions.outputs.next_snapshot }}"

      - name: Push sync branch
        if: steps.guard.outputs.exists == 'false'
        run: git push origin "${{ steps.versions.outputs.sync_branch }}"

      - name: Ensure the sync label exists
        if: steps.guard.outputs.exists == 'false'
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh label create sync --description "Sync pull request from a release branch back into <integration-branch>" --color 0e8a16 \
            || gh label list --search sync >/dev/null

      - name: Open pull request into <integration-branch>
        if: steps.guard.outputs.exists == 'false'
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh pr create \
            --base <integration-branch> \
            --head "${{ steps.versions.outputs.sync_branch }}" \
            --title "Sync ${{ steps.versions.outputs.next_snapshot }}" \
            --body "Merges \`<stable-branch>\` back into \`<integration-branch>\` after releasing \`${{ steps.versions.outputs.release_version }}\`, and bumps the development version to \`${{ steps.versions.outputs.next_snapshot }}\` in \`<lib-module>/build.gradle.kts\`/\`<app-module>/build.gradle.kts\`, \`README.md\`, and the Antora docs." \
            --label sync
```

Notes specific to this template:

- This uses `gh pr create` directly (matching the Java sibling's `sync.yml`), not
  `peter-evans/create-pull-request` — the Java/TypeScript siblings both open the sync PR via a hand-rolled
  git+`gh` sequence rather than that action, and this skill follows the same convention for consistency.
- The version bump is a **patch** bump (`x.y.z` → `x.y.(z+1)-SNAPSHOT`), matching this catalog's existing
  Maven `-SNAPSHOT` convention and `iru-android-bump-version`'s own Step 5 documented cadence — not a minor
  bump like the Java sibling's `sync.yml` (Maven's own convention there is a minor bump). If this repository
  does minor/major-level releases too, flag it as an open gap in the final report.
- `CHANGELOG.md` is deliberately not touched here, for the same reason as the Java/TypeScript siblings: its
  release section is written before the tag is published and arrives on `<integration-branch>` via the merge
  step above.
- The `permissions:` block is necessary but not sufficient — the repository's Settings → Actions → General →
  "Workflow permissions" must also allow GitHub Actions to create pull requests, or `gh pr create` fails with a
  permissions error even with the right scopes declared here. Flag this in the final report.
- `git add` only stages `<lib-module>/build.gradle.kts` when a `lib/` module exists, and only
  `<app-module>/build.gradle.kts` when an `app/` module exists (per Step 1's module-layout survey) — drop
  whichever path doesn't apply. The `--ignore-errors` flag (plus the trailing `|| true`) is what lets the same
  step survive a repository with no `README.md` or no `docs/` tree yet: without it `git add` aborts with
  `fatal: pathspec 'README.md' did not match any files` and the whole sync run fails before committing anything.
  Keep the flag even after dropping module paths — the README/docs paths are still optional.

### `sync_versions.py`

Companion script at `.github/scripts/sync_versions.py`. Reads `RELEASE_VERSION`/`NEXT_SNAPSHOT` from the
environment and rewrites every version reference the merge step doesn't already carry forward, using the exact
same rewrite targets and regex shapes as `iru-android-bump-version` (Steps 3/4/8 of that skill), so a manual
`/iru-android-bump-version` run and this CI-driven script never drift apart:

```python
#!/usr/bin/env python3
"""Rewrites version references after a release, for the Sync workflow.

Reads RELEASE_VERSION and NEXT_SNAPSHOT from the environment and updates
<lib-module>/build.gradle.kts's `val libraryVersion`, <app-module>/build.gradle.kts's
`versionName` (and, only when the release itself is not a -SNAPSHOT, its `versionCode`
— see iru-android-bump-version's Step 4 for the same rule), README.md, docs/antora.yml,
and any Antora page that carries the same "Latest release" / "Latest snapshot"
dependency snippets as README.md.

CHANGELOG.md is intentionally left untouched: its release section and fresh
"[Unreleased]" heading are written before the tag is published, and arrive on
<integration-branch> via the merge that precedes this script, not by bumping a
version string.
"""
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def update_lib_module(next_snapshot):
    path = REPO_ROOT / "<lib-module>" / "build.gradle.kts"
    if not path.exists():
        return
    text = path.read_text()
    updated, count = re.subn(
        r'(val libraryVersion = )"[^"]*"',
        lambda m: f'{m.group(1)}"{next_snapshot}"',
        text,
        count=1,
    )
    if count == 0:
        sys.exit(f"{path}: libraryVersion pattern not found")
    path.write_text(updated)


def update_app_module(next_snapshot):
    path = REPO_ROOT / "<app-module>" / "build.gradle.kts"
    if not path.exists():
        return
    text = path.read_text()
    updated, count = re.subn(
        r'(versionName = )"[^"]*"',
        lambda m: f'{m.group(1)}"{next_snapshot}"',
        text,
        count=1,
    )
    if count == 0:
        sys.exit(f"{path}: versionName pattern not found")
    path.write_text(updated)
    # versionCode is bumped by a *release* (a non -SNAPSHOT version), never by this script, which only ever
    # writes a -SNAPSHOT value — matching iru-android-bump-version's Step 4 rule exactly. Nothing to do here.


def replace_dependency_snippets(text, release_version, next_snapshot):
    """Rewrites the trailing version segment of an `implementation 'group:artifact:version'` (or Kotlin-DSL
    `implementation("group:artifact:version")`) line, following a "Latest release"/"Latest snapshot" marker."""
    lines = text.splitlines(keepends=True)
    pending = None
    for i, line in enumerate(lines):
        lower = line.strip().lower()
        if lower.startswith("latest release"):
            pending = release_version
        elif lower.startswith("latest snapshot"):
            pending = next_snapshot
        elif pending and re.search(r"implementation\s*\(?['\"][^:'\"]+:[^:'\"]+:", line):
            lines[i] = re.sub(
                r"(implementation\s*\(?['\"][^:'\"]+:[^:'\"]+:)[^'\"]+(['\"])",
                lambda m: f"{m.group(1)}{pending}{m.group(2)}",
                line,
            )
            pending = None
    return "".join(lines)


def update_readme(release_version, next_snapshot):
    path = REPO_ROOT / "README.md"
    if not path.exists():
        return
    text = path.read_text()
    # Adjust these two row-label regexes to match this repository's actual README table wording (resolved in
    # Step 1) if it differs from setup-readme's default "Current development version" / "Latest release" labels.
    text = re.sub(
        r"(\| Current development version \| `)[^`]*(` \|)",
        rf"\g<1>{next_snapshot}\g<2>",
        text,
    )
    text = re.sub(
        r"(\| Latest release[^|]*\| `)[^`]*(` \|)",
        rf"\g<1>{release_version}\g<2>",
        text,
    )
    text = replace_dependency_snippets(text, release_version, next_snapshot)
    path.write_text(text)


def update_antora_component_version(release_version):
    path = REPO_ROOT / "docs" / "antora.yml"
    if not path.exists():
        return
    text = path.read_text()
    updated, count = re.subn(r"(?m)^version:.*$", f"version: {release_version}", text, count=1)
    if count == 1:
        path.write_text(updated)


def update_antora_pages(release_version, next_snapshot):
    pages_dir = REPO_ROOT / "docs" / "modules" / "ROOT" / "pages"
    if not pages_dir.exists():
        return
    for path in sorted(pages_dir.glob("*.adoc")):
        text = path.read_text()
        if "implementation" not in text:
            continue
        updated = replace_dependency_snippets(text, release_version, next_snapshot)
        if updated != text:
            path.write_text(updated)


def main():
    release_version = os.environ["RELEASE_VERSION"]
    next_snapshot = os.environ["NEXT_SNAPSHOT"]

    update_lib_module(next_snapshot)
    update_app_module(next_snapshot)
    update_readme(release_version, next_snapshot)
    update_antora_component_version(release_version)
    update_antora_pages(release_version, next_snapshot)


if __name__ == "__main__":
    main()
```

Notes specific to this template:

- `update_lib_module`/`update_app_module` both no-op cleanly when the matching module doesn't exist, so this
  script is safe to write for either an `iru-setup-android-library`-only, `iru-setup-android-app`-only, or
  combined repository.
- The README regex is the exact `\s*\(?` form `iru-android-bump-version`'s Step 8 verified against both the
  Groovy (`implementation 'group:artifact:version'`) and Kotlin-DSL (`implementation("group:artifact:version")`)
  forms — reuse it verbatim rather than reinventing a stricter pattern.
- `update_antora_component_version` deliberately writes the **release** version, not the next snapshot, to
  `docs/antora.yml` — the Antora component version tracks the latest actual release, matching the Java
  sibling's convention.

## Step 6 — What changed from the reference `main.yml`/`publish.yml`

Recorded explicitly since Step 3 says the `gitflow` templates are this skill's own adaptation, not a literal
copy:

- **Two branches instead of one.** The reference repository triggers its whole pipeline on push/PR to `main`
  and release events, with no second branch. `gitflow`'s `develop.yml` reruns the identical pipeline on every
  push to the integration branch instead, and `main.yml` keeps the release trigger but now sits alongside
  `develop.yml` rather than being the only workflow.
- **`crazy-max/ghaction-github-pages`, pushing to a `gh-pages` branch, replaced by
  `actions/upload-pages-artifact`/`actions/deploy-pages`.** The plan's explicit departure from the reference
  repository — GitHub's own Pages-from-Actions deploy path, matching the Java/TypeScript siblings, instead of
  a branch-push action. Needs the repository's Settings → Pages → "Build and deployment" → Source set to
  **GitHub Actions**, not "Deploy from a branch" (flag in the final report).
- **The vendored-`jacococli.jar` conversion step is now the fallback, not the default.** The reference
  workflow always ran it (against a stale `.exec` path); `iru-setup-android-library`/`-app`'s own verification
  confirmed AGP's `createDebugUnitTestCoverageReport` task emits the XML report directly under the AGP version
  those skills resolve — Step 4's template uses that path by default (see Step 1's survey for when the
  fallback is still the right choice).
- **`lint { sarifReport = true }` is not needed** — confirmed a no-op deprecated property; `lib/build/reports/
  lint-results-debug.sarif` (and the app equivalent) is written unconditionally regardless, matching
  `iru-setup-android-library`/`-app`'s own finding.
- **A `sync.yml` was added.** The reference (`main-only`) repository has no equivalent — there's no second
  branch to sync back into — but `gitflow`'s two-branch model needs one, following this catalog's Java/
  TypeScript pattern.
- **Action versions were bumped** from the reference's `actions/checkout@v4`/`actions/setup-java@v2`/
  `crazy-max/ghaction-github-pages@v2` (its era's current majors) to the versions Step 2 resolves — the
  reference repository's own pins are stale relative to September 2026.
- **`workflow_dispatch` was added to `develop.yml`/`main.yml`'s triggers** — the reference has neither, this
  skill adds it (per this catalog's own convention) for a manual re-run.
- **`Send to Sonarqube` → `Run SonarCloud analysis`, gated by `sonar` instead of always-on** — the reference
  always ran `:lib:sonar` unconditionally; this skill only emits the step when `sonar` isn't `none` (Step 0).
- **`security-events: write` was added to the top-level `permissions:` block** of every workflow that runs
  `github/codeql-action/upload-sarif` (`develop.yml`, `main.yml`, and Step 7's main-only `main.yml`). The
  reference grants only `checks`/`pull-requests`/`contents`, under which the Lint SARIF upload fails with
  "Resource not accessible by integration" — `security.yml` already grants it per job (Step 8).

## Step 7 — `main.yml` / `publish.yml` templates (`branching: main-only`)

For `main-only`, the reference repository's own `main.yml`/`publish.yml` (Step 3) becomes this branching
variant's templates almost unchanged — only the same departures Step 6 lists (Pages-from-Actions instead of
`gh-pages`-branch push, the AGP-first coverage path, the gated Sonar step, bumped action versions,
`run-instrumented-tests`/`flavor` gating) apply. `main.yml` triggers on push/PR to the stable branch (build and
test only — no publish/store step); `publish.yml` triggers on a published release and does the actual
publish/store step, using the exact same release-only block as gitflow's `main.yml` (Step 4).

### `main.yml`

```yaml
name: CI

on:
  push:
    branches: [ <stable-branch> ]
  pull_request:
    branches: [ <stable-branch> ]
  workflow_dispatch:

permissions:
  checks: write
  pull-requests: write
  contents: write
  security-events: write   # required by github/codeql-action/upload-sarif (the Lint SARIF upload steps below)

jobs:
  build:
    name: Build and execute tests
    runs-on: ubuntu-latest
    steps:
      # ... identical to develop.yml's `build` job steps in Step 4, up to and including the
      # `deploy-docs`-feeding `Upload Pages artifact` step — NO publish/release step here, that only happens
      # in publish.yml below ...

  # Same deploy-docs job as Step 4's develop.yml (flavor: library only).
```

### `publish.yml`

```yaml
name: Publish

on:
  release:
    types: [released]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  publish:
    name: Release build and publish
    runs-on: ubuntu-latest
    steps:
      - name: Check out code
        uses: actions/checkout@v7
        with:
          fetch-depth: 0

      - name: Set up JDK <java-version>
        uses: actions/setup-java@v6
        with:
          distribution: temurin
          java-version: '<java-version>'

      - name: Set up Gradle
        uses: gradle/actions/setup-gradle@v6

      # flavor: library, publish: yes
      - name: Release build
        run: ./gradlew :<lib-module>:assembleRelease

      - name: Publish to Maven Central
        run: ./gradlew <lib-module>:publishAndReleaseToMavenCentral --no-configuration-cache
        env:
          ORG_GRADLE_PROJECT_mavenCentralUsername: ${{ secrets.MAVEN_CENTRAL_USERNAME }}
          ORG_GRADLE_PROJECT_mavenCentralPassword: ${{ secrets.MAVEN_CENTRAL_PASSWORD }}
          ORG_GRADLE_PROJECT_signingInMemoryKey: ${{ secrets.SIGNING_MEMORY_KEY }}
          ORG_GRADLE_PROJECT_signingInMemoryKeyId: ${{ secrets.SIGNING_MEMORY_KEY_ID }}
          ORG_GRADLE_PROJECT_signingInMemoryKeyPassword: ${{ secrets.SIGNING_IN_MEMORY_KEY_PASSWORD }}

      # flavor: app, distribution != none — identical to gitflow's main.yml release block in Step 4
      # (Decode Android keystore / Build signed release bundle / Upload to Google Play or Firebase).
```

Notes specific to this variant:

- This is the reference repository's actual permission/trigger shape (`permissions: checks: write,
  pull-requests: write, contents: write` on `main.yml`; `permissions: contents: read` on `publish.yml`),
  preserved except for one addition — `security-events: write` on `main.yml`, without which the
  `github/codeql-action/upload-sarif` Lint steps fail with "Resource not accessible by integration" — plus the
  action versions, Pages mechanism, coverage-conversion default, and Sonar gating changes (Step 6).
- No `sync.yml`/`sync_versions.py` for this branching model — there's only one long-lived branch, so nothing
  needs syncing back. State this plainly in the final report so it doesn't read as an oversight.

## Step 8 — `security.yml` and `.github/dependabot.yml` templates

Generated (or updated) regardless of `branching` — runs on every pull request and push to the integration/
stable branches (or just the stable branch for `main-only`), plus a weekly schedule so CodeQL/OSV-Scanner
findings don't go stale between pushes. Each job is individually omittable via the matching `security-*` arg
(Step 0); drop that whole job's YAML — not just its `if:` — when the resolved value is `no`:

```yaml
name: Security

on:
  push:
    branches: [ <integration-branch>, <stable-branch> ] # gitflow; main-only: just [ <stable-branch> ]
  pull_request:
  schedule:
    - cron: '0 6 * * 1' # weekly, Monday 06:00 UTC

permissions:
  contents: read

jobs:
  # Omit this whole job if security-dependency-review: no (Step 0)
  dependency-review:
    name: Dependency review
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    permissions:
      contents: read
      pull-requests: write
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Dependency review
        uses: actions/dependency-review-action@v5.0.0

  # Omit this whole job if security-codeql: no (Step 0)
  codeql:
    name: CodeQL analysis
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Set up JDK <java-version>
        uses: actions/setup-java@v6
        with:
          distribution: temurin
          java-version: '<java-version>'
      - name: Initialize CodeQL
        uses: github/codeql-action/init@v4
        with:
          languages: java-kotlin
          build-mode: autobuild
      - name: Perform CodeQL analysis
        uses: github/codeql-action/analyze@v4

  # Omit this whole job if security-osv: no (Step 0)
  osv-scanner:
    name: OSV-Scanner
    permissions:
      contents: read
      security-events: write
    uses: google/osv-scanner-action/.github/workflows/osv-scanner-reusable.yml@v2.6.0
    with:
      scan-args: |-
        --recursive
        ./

  # Omit this whole job if security-gitleaks: no (Step 0)
  gitleaks:
    name: gitleaks
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: Check out code
        uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - name: Run gitleaks
        uses: gitleaks/gitleaks-action@v3
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  # Opt-in — only when security-owasp-dependency-check: yes (default no). Unverified locally: the exact
  # action id/version below was not exercised during this skill's own verification pass; confirm it
  # still resolves before relying on it.
  owasp-dependency-check:
    name: OWASP Dependency-Check
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Run OWASP Dependency-Check
        uses: dependency-check/Dependency-Check_Action@main
        with:
          project: <artifact-id>
          path: .
          format: SARIF
        env:
          NVD_API_KEY: ${{ secrets.NVD_API_KEY }}
      - name: Upload Dependency-Check SARIF results
        uses: github/codeql-action/upload-sarif@v4
        with:
          sarif_file: reports/dependency-check-report.sarif

  # Opt-in, app flavor only — only when security-mobsfscan: yes (default no). Unverified locally.
  mobsfscan:
    name: MobSF mobsfscan
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Set up Python
        uses: actions/setup-python@v7
        with:
          python-version: '3.x'
      - name: Install mobsfscan
        run: pip install mobsfscan
      - name: Run mobsfscan
        run: mobsfscan --sarif --output mobsfscan-results.sarif <app-module>/ || true
      - name: Upload mobsfscan SARIF results
        uses: github/codeql-action/upload-sarif@v4
        with:
          sarif_file: mobsfscan-results.sarif
```

Notes specific to this template:

- `build-mode: autobuild` (per the plan's spec) rather than a hand-rolled `./gradlew compile` step like the
  Java sibling's `codeql` job uses — CodeQL's autobuild support for Gradle/Kotlin projects should invoke
  `./gradlew` itself; this is **unverified locally** (Step 12) — if autobuild ever fails against a particular
  module layout, fall back to an explicit `run: ./gradlew :<lib-module>:compileDebugKotlin
  :<app-module>:compileDebugKotlin` build step with `build-mode: manual` instead, the same pattern the Java
  sibling uses.
- `actions/dependency-review-action@v5.0.0` and the OSV-Scanner reusable-workflow ref are pinned to an exact
  tag, not a floating major — see Step 2's table for why.
- None of the four always-on jobs need a secret beyond the automatically provided `GITHUB_TOKEN`. The two
  opt-ins need `NVD_API_KEY` (OWASP Dependency-Check only, and only to raise NVD's public rate limit — the
  scan itself works without it, just slower) — see Step 13's secrets table.
- If `github.com` public-repository default CodeQL setup is simpler for this repository than a workflow-based
  CodeQL job, note that as an alternative in the final report instead of writing the `codeql` job, same as the
  Java/TypeScript siblings.

### `.github/dependabot.yml` template

Always generated (or updated) regardless of the `security-*` args — grouped weekly updates for the `gradle`
ecosystem (the repository's own dependencies/plugins) and for the workflows this skill itself just wrote
(`github-actions`):

```yaml
version: 2
updates:
  - package-ecosystem: gradle
    directory: /
    schedule:
      interval: weekly
    groups:
      gradle-dependencies:
        patterns:
          - "*"

  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    groups:
      github-actions-dependencies:
        patterns:
          - "*"
```

If `.github/dependabot.yml` already exists with entries for other ecosystems (e.g. `npm` for `docs/`),
preserve them — only add or update the `gradle` and `github-actions` entries above (see Step 1's stop-or-update
path).

## Step 9 — Placeholder resolution table

| Placeholder | Resolved from |
|---|---|
| `<integration-branch>` / `<stable-branch>` | Step 1 branch survey / `args` |
| `<java-version>` | Step 0 (`args`, default `17`) |
| `<api-level>` | Step 0 (`args`, default `35`) |
| `<lib-module>` / `<app-module>` | Step 1's `settings.gradle.kts` `include(...)` survey — almost always `lib`/`app` |
| `<application-id>` | `app/build.gradle.kts`'s `defaultConfig.applicationId`, `distribution: store` only |
| `<jacoco-cli-version>` | The vendored `jacoco-<ver>/lib/jacococli.jar` directory name found in Step 1's survey — only needed when that fallback template is emitted |
| `<sonar-organization>` / `<sonar-project-key>` / `<sonar-host-url>` | Step 0/1 Sonar survey / `args`; only needed when `sonar` isn't `none` |
| `<artifact-id>` | `lib/build.gradle.kts`'s `mavenPublishing { coordinates(...) }` (library) or the app's project name (OWASP Dependency-Check `project:` field) |
| `<owner>` / `<repo>` | The current repository's `git remote` (for report text only — no template above embeds a real repo/org name) |

Apply the `flavor`/`sonar`/`publish`/`distribution`/`run-instrumented-tests`/`branching`/vendored-jar gating
resolved in Steps 0–1: drop every block the templates above mark with an "Omit this … if …" comment (and that
comment itself) when the matching value doesn't apply.

## Step 10 — Conditional-blocks table

| Block | Appears when |
|---|---|
| `Enable KVM` + emulator-based `Run tests` step | `run-instrumented-tests: yes` |
| Plain (non-emulator) `Run tests` step | `run-instrumented-tests: no` |
| `<lib-module>:dokkaGenerate` in the test script, Sonar-on-lib, Antora/Dokka merge, Pages upload, `deploy-docs` job | a `lib/` module exists (library flavor, or a library+sample-app combined repo) |
| `<app-module>/**` test-result/SARIF globs, `:<app-module>:sonar` | an `app/` module exists |
| AGP-path coverage-conversion step targeting `<lib-module>` (`flavor: library`) or `<app-module>` (`flavor: app`) | default — no vendored `jacococli.jar` found (Step 1); targets only the module with `enableUnitTestCoverage = true` (Step 1 survey) — never both |
| Vendored-`jacococli.jar` fallback conversion step | a `jacoco-*/lib/jacococli.jar` was found, or the user asked for it |
| `Run SonarCloud analysis` step (`:<lib-module>:sonar` or `:<app-module>:sonar`) | `sonar` is `cloud` or `self-hosted` |
| `Publish snapshot to Maven Central` (develop.yml) / `Release build` + `Publish to Maven Central` (main.yml/publish.yml) | `flavor: library`, `publish: yes` |
| `Decode Android keystore` + `Build signed release bundle` + store/Firebase upload | `flavor: app`, `distribution` isn't `none` |
| `Upload to Google Play` (`r0adkll/upload-google-play`) vs. `./gradlew :<app-module>:publishBundle` | `distribution: store` — action if no `com.github.triplet.play` plugin found (Step 1), Gradle task if found |
| `Distribute via Firebase App Distribution` | `distribution: internal` |
| `sync.yml` + `sync_versions.py` | `branching: gitflow` only |
| `owasp-dependency-check` job | `security-owasp-dependency-check: yes` |
| `mobsfscan` job | `security-mobsfscan: yes`, app flavor only |

## Step 11 — File matrix

| `branching` × `flavor` | Files written |
|---|---|
| `gitflow` / `library` | `.github/workflows/develop.yml`, `main.yml`, `sync.yml`, `.github/scripts/sync_versions.py`, `security.yml`, `.github/dependabot.yml` |
| `gitflow` / `app` | Same six files (the release job inside `main.yml` differs internally per Step 4) |
| `main-only` / `library` | `.github/workflows/main.yml`, `publish.yml`, `security.yml`, `.github/dependabot.yml` |
| `main-only` / `app` | Same four files (the release job inside `publish.yml` differs internally per Step 7) |

## Step 12 — Write the files

Write (or, per Step 1's stop-or-update decision, carefully update) every file from Step 11's matrix with the
filled-in templates from Steps 4–8. `sync.yml` and `sync_versions.py` are written together — never write one
without the other, and never write either for `main-only`. `security.yml` and `.github/dependabot.yml` are
always written (or updated), independent of `flavor`/`branching`/`publish`/`distribution`/`sonar` — only their
own `security-*` args gate individual jobs within `security.yml`, and `.github/dependabot.yml` has no gate at
all.

## Step 13 — Known quirks / verification notes

Recorded from this skill's own verification pass, run entirely in `$TMPDIR/iru-verify/android/workflows/`
(created fresh, outside this repository) — never a blocker, folded into the templates above where a template
change was warranted:

- **`actions/dependency-review-action` and the `google/osv-scanner-action` reusable workflow have no floating
  major tag.** Every other action in Step 2's table resolves a `git ls-remote --tags`-confirmed floating major
  (`v7`, `v6`, `v2`, `v5`, `v3`, `v1`, …) — these two only publish exact-version tags (`v5.0.0`, `v2.6.0`, …
  confirmed via `git ls-remote --tags` returning zero matches for a bare `v5`/`v2` ref, while the exact tag
  resolves). Step 2's/Step 8's templates pin the exact resolved version for both; re-run the same
  `git ls-remote --tags https://github.com/<owner>/<repo> <tag>` check at generation time in case either has
  since published a floating major.
- **The GitHub REST `/tags` endpoint can miss a floating major tag that genuinely exists.**
  `reactivecircus/android-emulator-runner` and `EnricoMi/publish-unit-test-result-action` both looked
  tag-less for `v2` via `gh api repos/<owner>/<repo>/tags` (only full `v2.NN.0`-style tags came back), but
  `git ls-remote --tags https://github.com/<owner>/<repo> v2` confirmed the floating `v2` ref does exist for
  both. Prefer `git ls-remote --tags` over the REST `/tags` listing when confirming whether a floating major
  tag exists — the REST endpoint's pagination/ordering isn't reliable for this.
- **`develop.yml`/`main.yml`'s `Install Antora` step uses `mkdir -p docs-toolchain && cd docs-toolchain`
  (matching the TypeScript sibling), not the Java sibling's bare `mkdir docs && cd docs`.** The bare form
  would fail outright (`mkdir: cannot create directory 'docs': File exists`, and GitHub Actions `run:` steps
  default to `bash -eo pipefail` on Linux runners) against any repository that already has `docs/antora.yml`
  committed — which every repository this skill targets does, since the Antora build step immediately after
  depends on it. Confirmed by inspecting the Java sibling's own template rather than by running it (this
  skill's verification pass used a throwaway repo that already had `docs/`, and `mkdir -p` succeeded as
  expected).
- **YAML-validated every rendered file** (all four `branching`×`flavor` combinations, `run-instrumented-tests:
  yes` for the library variant, `no` for the app variant, `sonar: cloud`, `publish: yes`/`distribution:
  store`) with `python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))"` — every file parsed cleanly.
  As with the TypeScript sibling's own note: PyYAML round-trips the top-level `on:` key as the boolean `True`
  under YAML 1.1's bare-word resolution, not the string `"on"` GitHub's own parser expects — this is a false
  flag in the validator, not a defect in the generated workflow; don't quote `on:` in the template to "fix" it.
- **`sync_versions.py` was exercised against copies of `iru-setup-android-library`'s own scaffold** —
  `1.0.0-SNAPSHOT` → release `1.0.0` → next `1.0.1-SNAPSHOT`-shaped inputs (the patch bump `sync.yml`'s
  `versions` step actually computes — `${MAJOR}.${MINOR}.${NEXT_PATCH}-SNAPSHOT`) correctly rewrote
  `lib/build.gradle.kts`'s `val libraryVersion`, `app/build.gradle.kts`'s `versionName`, and a sample
  README/`antora.yml` copy's version rows/`version:` field, `py_compile`-clean. `versionCode` was correctly
  left untouched (the script never writes anything but a `-SNAPSHOT` value into `NEXT_SNAPSHOT`, and
  `update_app_module` has no `versionCode` logic at all, by design — see the template's own comment).
- **`replace_dependency_snippets`'s marker match only fires on a *bare* `Latest release`/`Latest snapshot`
  line, not on one embedded inside a Markdown table row.** Confirmed by first testing against a README with
  the dependency snippet placed directly under the status-table's own `| Latest release | ... |` row (no
  separate bare marker) — the snippet was silently left at its old version, no error. Re-tested against the
  shape `iru-setup-readme` actually generates (the status table's `Latest release` **row** handled by the
  separate row-label regex, plus a distinct `## Installation` section with its own bare `Latest release` line
  immediately before the snippet) and both mechanisms fired correctly. This is inherited unchanged from the
  Java/TypeScript siblings' own `sync_versions.py` — not a regression introduced here — but confirm a
  repository's actual README puts a bare marker line ahead of its dependency snippet (not just inside the
  status table) before trusting this script's Installation-section rewrite.
- **Gradle steps run against the generated `iru-setup-android-library` scaffold at `$TMPDIR/iru-verify/android/library`**: `export
  JAVA_HOME=$(/usr/libexec/java_home -v 21)` (JDK 21 preferred over the machine's newer default, per this
  catalog's own Android-skill convention); `./gradlew test lint lib:dokkaGenerate` (first invocation, no
  `--offline`) succeeded and confirmed every path this skill's templates reference:
  `lib/build/test-results/testDebugUnitTest/*.xml`, `lib/build/reports/lint-results-debug.sarif`,
  `lib/build/dokka/html/index.html`. `./gradlew :lib:createDebugUnitTestCoverageReport` then confirmed
  `lib/build/reports/coverage/test/debug/report.xml` and the raw
  `lib/build/outputs/unit_test_code_coverage/debugUnitTest/testDebugUnitTest.exec` both exist at exactly the
  paths Step 4's AGP-path template uses — matching `iru-setup-android-library`'s own Step 11 finding exactly
  (this skill's authoring didn't need to rediscover it independently). `./gradlew :app:testDebugUnitTest
  :app:lint` against the same scaffold's sample `app/` module confirmed
  `app/build/reports/lint-results-debug.sarif` is written the same way (`Wrote SARIF report to
  .../app/build/reports/lint-results-debug.sarif`); `:app:testDebugUnitTest` itself printed `NO-SOURCE` and
  wrote no `test-results/` at all, because `iru-setup-android-library`'s own sample `app/` module (Step 7 of
  that skill) has no `src/test` directory — confirmed harmless (the test-result glob in Step 4's
  `Publish test results` step simply matches nothing for that module, `EnricoMi/publish-unit-test-result-
  action` tolerates an empty glob), but means the app-module test-results path itself was **not**
  independently re-confirmed here beyond `iru-setup-android-app`'s own Step 7 verification (a real, standalone
  app repository, unlike this sample module).
- **`:<app-module>:createDebugUnitTestCoverageReport` is a hard failure, not a no-op, against
  `iru-setup-android-library`'s own sample `app/` module** — confirmed by actually running it:
  `FAILURE: Build failed with an exception. * What went wrong: Selection failed. Cannot locate tasks that
  match ':app:createDebugUnitTestCoverageReport' as task 'createDebugUnitTestCoverageReport' not found in
  project ':app'.` That module's `buildTypes { debug { ... } }` block never sets `enableUnitTestCoverage =
  true` (only `lib/build.gradle.kts` does — see `iru-setup-android-library`'s Step 6 template) — an earlier
  draft of this skill's `Convert unit tests coverage results` step ran the task against **both**
  `<lib-module>` and `<app-module>` unconditionally, which would have broken every `flavor: library`
  `develop.yml`/`main.yml` run generated against that exact scaffold shape. Fixed before this file was
  finalized: Step 4's template now targets `<lib-module>` only for `flavor: library` (`<app-module>` only for
  `flavor: app`, per `iru-setup-android-app`'s own template, which DOES set the flag) — see Step 1's survey
  and Step 10's conditional-blocks table.
- **The vendored-`jacococli.jar` fallback conversion command was run for real**, against a downloaded
  `org.jacoco.cli-0.8.13-nodeps.jar` (from `repo1.maven.org`, since neither scaffold vendors one — no
  `~/.gradle/caches` copy was found locally either) and the `.exec`/class-file paths confirmed above: `java
  -jar org.jacoco.cli-0.8.13-nodeps.jar report lib/build/outputs/unit_test_code_coverage/debugUnitTest/
  testDebugUnitTest.exec --classfiles lib/build/tmp/kotlin-classes/debug --sourcefiles lib/src/main/java --xml
  <out>/report.xml` produced a valid JaCoCo-format XML report — confirming the fallback template's command
  line is correct, not just plausible.
- **The Antora copy step was verified at the shell-command level only** (`mkdir -p`/`cp -r` against the
  scaffold's real `lib/build/dokka/html/` output into a throwaway `docs/build/site/api/` directory, confirming
  the copy succeeds and lands `index.html` where expected) — a full `cd docs && npx antora
  antora-playbook.yml` run was **not** repeated here (the scaffold's own `docs/` setup and Antora build are
  `iru-setup-antora`'s/the scaffold skills' responsibility to verify, not this skill's).
- **Unverified locally, never a blocker**: the emulator-based `Run tests` step (`reactivecircus/android-
  emulator-runner`, needs real KVM-backed hardware acceleration this environment doesn't reliably provide for
  a full `connectedAndroidTest` run), the `Run SonarCloud analysis` step (needs a real `SONAR_TOKEN` and
  SonarCloud project), Maven Central publishing (needs real signing/publishing credentials), the Google
  Play/Firebase App Distribution uploads (need real store/Firebase credentials), CodeQL actually analyzing this
  project (`build-mode: autobuild` against a real Gradle/Android module was not run through the CodeQL CLI
  locally), and both opt-in jobs (OWASP Dependency-Check, `mobsfscan`) beyond confirming their action/CLI
  names are plausible.

## Step 14 — Report

Summarize what happened: whether each file in Step 11's matrix was created fresh, updated in place, or left
untouched (Step 1's stop path); any open gaps noted along the way (missing `docs/antora.yml`, a
`com.github.triplet.play` plugin found and used instead of the workflow-level upload action, README/Antora
wording that didn't match `sync_versions.py`'s default regexes, a vendored `jacococli.jar` found and used
instead of the AGP-path default, any shared-`args` key supplied but unused by this skill).

State explicitly what was wired versus omitted, and why:

- **`flavor`**: `library` or `app` — which pipeline shape (Dokka/Antora/Sonar-on-lib vs. Sonar-on-app/
  signing-and-store) was generated.
- **`branching`**: `gitflow` (`develop.yml`/`main.yml`/`sync.yml`) or `main-only` (`main.yml`/`publish.yml`,
  no `sync.yml` — state this omission plainly).
- **`run-instrumented-tests`**: yes/no — which `Run tests` step variant was used, and whether the `Enable KVM`
  step was included.
- **`sonar`**: `cloud`/`self-hosted`/`none` — if not `none`, the Sonar step and `SONAR_TOKEN` row were
  included; if `none`, both were omitted, and note whether that's because the project isn't open source or a
  direct user choice.
- **`publish`** (library only) / **`distribution`** (app only): yes/no or `none`/`internal`/`store` — which
  publish/store jobs and secret rows were generated versus omitted.
- **Security block**: which of the four always-on `security-*` jobs and the two opt-ins were included versus
  omitted, and confirm `.github/dependabot.yml` was written regardless (it has no opt-out).
- **Coverage-conversion path**: AGP-direct (default) or the vendored-`jacococli.jar` fallback, and why.

Then give the required-secrets/environments table — list only the rows that apply to what was actually
generated (an omitted row is one fewer secret the user needs to create):

| Secret | Purpose | Only needed when |
|---|---|---|
| `SONAR_TOKEN` | Auth token for the SonarQube/SonarCloud scan | `sonar` is `cloud` or `self-hosted` |
| `MAVEN_CENTRAL_USERNAME` / `MAVEN_CENTRAL_PASSWORD` | Maven Central Publishing Portal credentials | `flavor: library`, `publish: yes` |
| `SIGNING_MEMORY_KEY` / `SIGNING_MEMORY_KEY_ID` / `SIGNING_IN_MEMORY_KEY_PASSWORD` | In-memory GPG signing key, its id, and its passphrase, for Vanniktech's Maven Publish plugin | `flavor: library`, `publish: yes` |
| `ANDROID_KEYSTORE_BASE64` | Base64-encoded release keystore, decoded to `<app-module>/release.jks` at build time | `flavor: app`, `distribution` isn't `none` |
| `ANDROID_KEYSTORE_PASSWORD` / `ANDROID_KEY_ALIAS` / `ANDROID_KEY_PASSWORD` | Exported as `SIGNING_STORE_PASSWORD`/`SIGNING_KEY_ALIAS`/`SIGNING_KEY_PASSWORD` — the exact env vars `iru-setup-android-app`'s `app/build.gradle.kts` reads via `System.getenv()` | `flavor: app`, `distribution` isn't `none` |
| `PLAY_SERVICE_ACCOUNT_JSON` | Google Play service-account JSON for `r0adkll/upload-google-play`'s `serviceAccountJsonPlainText` input | `flavor: app`, `distribution: store`, workflow-level upload (no Gradle Play Publisher plugin found) |
| `FIREBASE_APP_ID` / `FIREBASE_SERVICE_CREDENTIALS` | Firebase App Distribution upload | `flavor: app`, `distribution: internal` |
| `NVD_API_KEY` | Raises the NVD lookup rate limit for OWASP Dependency-Check (the scan runs without it, just slower) | `security-owasp-dependency-check: yes` |
| `GITHUB_TOKEN` | `sync.yml`'s `gh` calls, `security.yml`'s CodeQL/gitleaks jobs | Automatic — no setup needed |

`sync.yml` also needs the repository setting under Settings → Actions → General → "Workflow permissions" set
to allow GitHub Actions to create pull requests — the `permissions:` block in the workflow itself is not
sufficient on its own. The Pages deploy jobs need Settings → Pages → "Build and deployment" → Source set to
**GitHub Actions**. Call all of this out explicitly, since each is easy to miss and fails on the very first
real run without it.

**Warn explicitly:**

- **The user must review every generated (or updated) workflow file before relying on it.** Branch names,
  module names, and the store/signing/publish setup were inferred from this repository's current state and
  may need correction — and because this pipeline handles signing keys and publishes/distributes artifacts
  publicly, a bad assumption here has real consequences. Recommend a dry run via `workflow_dispatch` before
  trusting it on a real release.
- Every secret in the table above, the matching SonarCloud project / Maven Central Publishing Portal
  registration / Google Play Console service account / Firebase project, must already exist before CI can
  pass — this skill only writes the workflow YAML, it never creates any of those accounts or credentials
  itself.
- Which toolchain versions (Step 2) came from a live lookup versus this skill's recorded September 2026
  fallback, and specifically that `actions/dependency-review-action`/`google/osv-scanner-action`'s reusable
  workflow are pinned to an exact tag rather than a floating major (Step 13) — re-check both at the next
  regeneration in case a floating major has since been published.
- **Unverified locally, and never a blocker** (Step 13): the emulator-based instrumented-test run, the actual
  SonarCloud scan, Maven Central publishing, the Google Play/Firebase App Distribution uploads, CodeQL
  actually analyzing this project, and both opt-in security jobs beyond a plausibility check of their
  action/CLI names.
