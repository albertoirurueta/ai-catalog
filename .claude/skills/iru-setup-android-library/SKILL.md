---
name: iru-setup-android-library
description: Generate the standard Gradle/Kotlin toolchain for a new Android library at the repository root — the Gradle wrapper (`gradle/wrapper/gradle-wrapper.properties` pinned to the current Gradle version plus its `distributionSha256Sum`, `gradlew`/`gradlew.bat`/`gradle-wrapper.jar`), root `build.gradle.kts`, `settings.gradle.kts`, `gradle.properties`, `gradle/libs.versions.toml`, a `lib/` library module (`build.gradle.kts`, `proguard-rules.pro`, manifests, `robolectric.properties`, `.gitignore`, one placeholder source + unit test + instrumented test), and an `app/` Jetpack Compose sample module (`build.gradle.kts`, manifest, `.gitignore`, `MainActivity.kt`, launcher/theme resources) that depends on `lib` — asks for `group-id`, `artifact-id`, `namespace`, `description`, `min-sdk` (default `26`), `compile-sdk` (default the current stable API level), license, developer name/email/organization URL, whether the project is open source, whether it publishes to Maven Central (`publish`, gating the `mavenPublishing`/vanniktech block), whether to wire up SonarQube/SonarCloud (`sonar`: `cloud`/`self-hosted`/`none`), `built-in-kotlin` (`no`/`yes`, gating `android.builtInKotlin`/`android.newDsl` in `gradle.properties`), `junit` (`4`/`5`, gating the `de.mannodermaus.android-junit` plugin), `coverage-tool` (`jacoco`/`kover`, gating AGP's own unit-test-coverage flags vs. the Kover plugin), and `static-analysis` (`lint`/`lint+detekt+ktlint`, gating Detekt + Spotless(ktlint + licenseHeader)). Invoke as `/iru-setup-android-library`. Ships with explicit example templates embedded in this skill file, genericized (no real repository/organization/person names, `<placeholder>` markers with a resolution table) from a real Android library's actual project files — https://github.com/albertoirurueta/irurueta-android-glutils — including its `lib/` module shape (JUnit 4 + MockK + Robolectric + AndroidX Espresso, AGP JaCoCo, inline `sonar { properties {…} } ` block run as `./gradlew :lib:sonar`, `mavenPublishing { AndroidSingleVariantLibrary(...) }`) and its Compose `app/` sample module, which is part of this scaffold, not a separate skill. Every toolchain version (Gradle, AGP, Kotlin, Dokka, the `sonarqube`/`com.vanniktech.maven.publish`/Detekt/Spotless/Kover/`de.mannodermaus.android-junit` Gradle plugins, JUnit, AndroidX Test, Compose BOM, Material3, MockK, Robolectric, `com.irurueta:irurueta-android-test-utils`) is looked up at run time (Google Maven, Maven Central, the Gradle Plugin Portal, `services.gradle.org`), with this skill's own September 2026 findings as the fallback. If any of this skill's files already exist, asks whether to stop, fill gaps only, or regenerate (`mode: existing` skips straight to gap-fill, this catalog's shared front-door convention); accepts every input pre-resolved via `args` (`key: value` lines) so an orchestrating skill can supply them without re-prompting. Verifies with `./gradlew --offline help` then `./gradlew :lib:assembleDebug` through the `iru-gate-runner` agent, warning up front that the first run downloads Gradle itself, Android SDK components, and every dependency. Use whenever a new Android/Kotlin library repository (with its Compose sample app) needs its Gradle build scaffolded from this house template, instead of hand-writing each Gradle/manifest/properties file.
model: haiku
---

# Setup Android Library

Generate the standard Android/Kotlin library toolchain at the repository root: the Gradle wrapper, root project
files, a `lib/` library module, and an `app/` Jetpack Compose sample module that depends on `lib` — using explicit
example templates embedded in this skill (Steps 5–7) that are genericized (no real repo/org/person names,
`<placeholder>` markers resolved from Steps 2–4) from a real Android library's actual project files:
https://github.com/albertoirurueta/irurueta-android-glutils. The Compose `app/` module is not optional or a
separate skill — it ships as part of this scaffold, exactly as it does in that reference repository. Every Gradle
plugin/dependency version is looked up from the network at run time; the versions recorded in this file are only
the fallback for when that lookup fails.

## Step 0 — Resolve inputs

This skill can be invoked stand-alone (`/iru-setup-android-library`) or as a step inside another skill (e.g. a
future `iru-setup-android-library-repository` or the catalog's `iru-setup-repository` front door), which resolves
these same inputs itself and passes them through `args` as `key: value` lines, one per line, e.g.:

```
group-id: com.example
artifact-id: my-android-library
namespace: com.example.myandroidlibrary
description: A small example Android library.
min-sdk: 26
compile-sdk: 36
license: Apache License 2.0
developer-name: Jane Doe
developer-email: jane@example.com
organization-url: https://github.com/example-org
open-source: yes
publish: yes
sonar: cloud
sonar-organization: example-org-github
sonar-project-key: example-org_my-android-library
sonar-host-url: https://sonarcloud.io
built-in-kotlin: no
junit: 4
coverage-tool: jacoco
static-analysis: lint
version: 1.0.0-SNAPSHOT
mode: new
```

Parse any such lines from `args` now. Every field found here is resolved — skip asking about it in Step 2. Only
fields genuinely missing from `args` still need a question. If `args` is absent or doesn't look like this format,
treat everything as unset and ask normally.

Recognized keys: `group-id`, `artifact-id`, `namespace` (the Android `namespace`/application id base, e.g.
`com.example.myandroidlibrary` — also the base package for the placeholder source under `lib/src/main/java`),
`description`, `min-sdk` (default `26`), `compile-sdk` (default the current stable API level — see Step 4),
`license`, `developer-name`, `developer-email`, `organization-url`, `open-source` (`yes`/`no`), `publish`
(`yes`/`no`), `sonar` (`cloud`/`self-hosted`/`none`) plus, only when `sonar` is `cloud` or `self-hosted`,
`sonar-organization`/`sonar-project-key`/`sonar-host-url`, `built-in-kotlin` (`no`/`yes`, default `no`), `junit`
(`4`/`5`, default `4`), `coverage-tool` (`jacoco`/`kover`, default `jacoco`), `static-analysis`
(`lint`/`lint+detekt+ktlint`, default `lint`), `version` (default `1.0.0-SNAPSHOT`), and `mode` (`new`/`existing`).

`mode: existing` is this catalog's shared signal (set by a front door that already ran `iru-explore` and knows this
is an established repository) that Step 1 should skip its stop-or-regenerate question entirely and go straight to
gap-fill: create only whatever files from Steps 5–7 are genuinely missing, and leave every file that already exists
untouched. `mode: new` or an unset `mode` follows Step 1's normal survey instead.

## Step 1 — Survey the repository

Check, at the repository root, which of this skill's files already exist: `build.gradle.kts`, `settings.gradle.kts`,
`gradle.properties`, `gradle/libs.versions.toml`, `gradle/wrapper/gradle-wrapper.properties`, `gradlew`,
`gradlew.bat`, `gradle/wrapper/gradle-wrapper.jar`, `local.properties`, `lib/build.gradle.kts`,
`lib/proguard-rules.pro`, `lib/.gitignore`, `lib/src/main/AndroidManifest.xml`,
`lib/src/androidTest/AndroidManifest.xml`, the placeholder source/tests under `lib/src/{main,test,androidTest}`,
`detekt.yml` (only relevant once `static-analysis` is resolved in Step 2), `app/build.gradle.kts`, `app/.gitignore`,
`app/src/main/AndroidManifest.xml`, `app/src/main/java/.../MainActivity.kt`, and the `app/src/main/res/` files from
Step 7.

- **None exist**: skip straight to Step 2. There is nothing to preserve.
- **`mode: existing` was resolved in Step 0**: skip the question below — go straight to **gap-fill**: create only
  the files that are missing; leave every file that already exists completely untouched (including
  `lib/build.gradle.kts` and `app/build.gradle.kts` — merge nothing into them). Note in Step 11's report which
  files were left alone because they already existed.
- **Otherwise, and at least one file already exists**: warn the user which files were found, then use
  `AskUserQuestion` with three options:
  - **Stop** — leave every existing file untouched; make no changes at all. Report this and end here.
  - **Fill gaps only** (recommended once real library code exists under `lib/src/main`) — create only the files
    that are missing; don't overwrite anything already present. Same effective behavior as `mode: existing`.
  - **Regenerate everything** — before asking Step 2's questions, read the existing `lib/build.gradle.kts` (if
    present) for its current `namespace`, `libraryVersion`, `compileSdk`/`minSdk`, and whether a `sonar`/
    `mavenPublishing` block is already present, and use those as the *defaults* offered for whichever Step 2
    question Step 0 didn't already resolve via `args` — a value supplied via `args` always wins. Tell the user up
    front that regenerating replaces every one of this skill's files wholesale; any customization added since the
    last run (extra dependencies, extra Gradle tasks, hand-edited manifests/resources) will be lost unless
    re-added afterward (call this out again in Step 11).

## Step 2 — Collect the required inputs

For any field Step 0 already resolved from `args`, use that value directly and don't ask about it again. For
everything else, ask the user directly (plain conversation, pre-filling defaults found in Step 1 if regenerating):

- **group-id** — the Maven Central `groupId` used to publish this library, e.g. `com.example`.
- **artifact-id** — the Maven Central `artifactId` / Gradle project name, e.g. `my-android-library`. Used verbatim
  as `rootProject.name` in `settings.gradle.kts` and as the `coordinates(...)` artifact id in Step 6's
  `mavenPublishing` block.
- **namespace** — the Android `namespace` (and the base package for the placeholder source under
  `lib/src/main/java`), e.g. `com.example.myandroidlibrary`. This need not equal `group-id`; ask for it explicitly.
  The `app/` module's own namespace/`applicationId` is always `<namespace>.app` (Step 7) — not asked separately.
- **description** — one line, used in `lib/build.gradle.kts`'s `pom { description.set(...) }`.
- **version** — the `libraryVersion` written into `lib/build.gradle.kts`. Default `1.0.0-SNAPSHOT` if the user
  doesn't give one (this is why `settings.gradle.kts`'s `dependencyResolutionManagement` in Step 5 includes the
  Sonatype snapshots repository — it resolves `-SNAPSHOT` dependencies of this exact form).
- **min-sdk** — default `26` if the user doesn't give one. Written to `defaultConfig.minSdk` in both modules.
- **compile-sdk** — the API level both modules compile against. There's no public "current" endpoint for this the
  way there is for Gradle/npm; resolve it by checking the highest `android-<N>` directory under
  `$ANDROID_HOME/platforms` (or `$ANDROID_SDK_ROOT/platforms`) if the SDK is installed locally, otherwise from the
  latest stable Android release notes. Offer that resolved value as the default; the fallback recorded while
  building this skill (September 2026) is `36`. **This choice is coupled to Step 4's `androidx.compose:compose-bom`
  lookup** — confirmed while verifying this skill: the Compose BOM's own release cadence outruns `compileSdk`
  support, and a too-new BOM's `androidx.compose.foundation`/`androidx.compose.material` artifacts fail
  `:app:checkDebugAarMetadata` with "requires libraries and applications that depend on it to compile against
  version `<N>` or later of the Android APIs" when `compile-sdk` is older. Either resolve `compile-sdk` to a
  platform actually installed (or installable) locally and then pick the newest `compose-bom` release that AAR
  metadata check still accepts for it, or bump `compile-sdk` to whatever the chosen `compose-bom` actually needs —
  don't resolve the two independently.
- **Developer name**, **developer email**, **organizationUrl** — populate `lib/build.gradle.kts`'s
  `pom { developers { developer {...} } }` block (Step 6).

Then, unless Step 0 already resolved a `license` value from `args`, ask about the **license** with
`AskUserQuestion` (small bounded choice, same four options this catalog's other setup skills use):

- Apache License 2.0 (recommended) — `Apache License 2.0` / `http://www.apache.org/licenses/LICENSE-2.0.txt`
- MIT License — `The MIT License` / `https://opensource.org/license/mit`
- No license (proprietary / all rights reserved) — omit the `pom { licenses {...} }` block entirely, and omit the
  license-header comment from every generated Kotlin file (Steps 6–7) and from Spotless's `licenseHeader(...)`
  rule (Step 6, only relevant when `static-analysis: lint+detekt+ktlint`)
- Other — ask for the license's display name and URL directly afterward

If a license is chosen (anything but "No license"), remind the user in Step 11 to also add a matching `LICENSE`
file at the repository root if one doesn't exist yet — the `iru-check-license` skill can verify/backfill file
headers against it once it's there.

Then resolve `open-source`, `publish`, and `sonar` — skip any of the three Step 0 already resolved from `args`.
When invoked stand-alone with none of them pre-resolved, ask `open-source` *first* (`AskUserQuestion`: yes/no) and
derive the recommended defaults for the other two from that answer, per this catalog's shared convention:

- **open-source** — is this repository open source? Yes / No.
- **publish** (Maven Central, via the `com.vanniktech.maven.publish` plugin) — default **Yes** when open-source is
  Yes; when not open source, ask with **No** recommended, explaining that Maven Central is meant for publishing
  redistributable artifacts other projects depend on, which usually isn't appropriate for closed-source code. `No`
  omits the whole `mavenPublishing {...}` block (and the `publish` alias/plugin) from Step 6's template entirely.
- **sonar** — whether to wire up a SonarQube/SonarCloud scan (this house pattern applies the `org.sonarqube`
  plugin per-module and runs it as `./gradlew :lib:sonar`, typically from a CI workflow such as
  `iru-setup-android-github-workflows`, so it's worth setting up here even if that workflow comes later). Recommend
  **SonarCloud** (`cloud`) when open-source is Yes; when not open source, state that SonarCloud is free only for
  open-source projects (a paid plan is required otherwise) and recommend **None** (`none`), offering **self-hosted
  SonarQube** as the second option:
  - `cloud` — ask for the `sonar.organization` key, offering `<owner>-github` (the owner parsed in Step 3) as the
    suggested default. Default `sonar.projectKey` to `<owner>_<repo>` and `sonar.host.url` to
    `https://sonarcloud.io`, confirming both with the user rather than assuming silently.
  - `self-hosted` — ask for `sonar.host.url` directly (no sensible default — this is what replaces the fixed
    `https://sonarcloud.io` host in Step 6's `sonar { properties {...} } ` block), plus `sonar.organization` only if
    that server has organizations enabled, and `sonar.projectKey`.
  - `none` — omit the whole `sonar { properties {...} } ` block (and the `sonarqube` alias/plugin) from Step 6's
    template entirely, in both `lib/build.gradle.kts` and `app/build.gradle.kts`.

Finally, resolve the four toolchain toggles (skip any Step 0 already resolved):

- **built-in-kotlin** (`no`/`yes`, default `no`) — whether to opt into AGP's newer built-in Kotlin compilation path
  (`android.builtInKotlin=true`/`android.newDsl=true` in `gradle.properties`, Step 5) instead of the
  `org.jetbrains.kotlin.android` plugin's own compilation. Default **No** (matching the reference repository, and
  the only combination this skill actually verified — see Step 10's "Known quirks"): explain to the user this is
  an AGP feature still stabilizing, and that `yes` is unverified by this skill.
- **junit** (`4`/`5`, default `4`) — which JUnit major the `lib` module's unit tests (`src/test`) run on.
  Instrumented tests (`src/androidTest`) always run on JUnit 4 via `androidx.test.runner.AndroidJUnitRunner`
  regardless of this answer — there is no mainstream JUnit 5 instrumented-test runner for Android. `5` applies the
  `de.mannodermaus.android-junit` plugin (Step 6) to bridge JUnit 5 into the Android unit-test task; this path is
  **unverified locally** (Step 10's verification run used `junit: 4`) — say so explicitly if the user picks `5`.
- **coverage-tool** (`jacoco`/`kover`, default `jacoco`) — `jacoco` uses AGP's own built-in unit/instrumented-test
  coverage (`buildTypes { debug { enableUnitTestCoverage = true } }`, the reference repository's approach, verified
  by this skill). `kover` applies the Kover Gradle plugin instead, which replaces those two flags with its own
  `koverXmlReportDebug` task — **unverified locally**.
- **static-analysis** (`lint`/`lint+detekt+ktlint`, default `lint`) — Android Lint is always wired (it ships with
  AGP; no opt-in needed). `lint+detekt+ktlint` additionally applies Detekt (with a `detekt.yml` at the repository
  root) and Spotless configured for ktlint + a license-header check — **unverified locally**.

## Step 3 — Infer repository information

Don't ask for these — derive them from the current repository, the same way `iru-setup-java-library` and
`iru-setup-typescript-library` do:

- **Owner/repo and host**: parse `git remote get-url origin` (handles both `git@host:owner/repo.git` and
  `https://host/owner/repo.git` forms). Use the parsed host/owner/repo for the `pom { url.set(...) }`/`scm {...}`
  fields in Step 6's `mavenPublishing` block (only relevant when `publish: yes`) and for the `sonar.organization`/
  `sonar.projectKey` defaults in Step 2. If there's no `origin` remote yet, ask the user for the intended
  repository URL instead of leaving it blank.
- **Description fallback**: if Step 2's `description` question was skipped because `args` supplied nothing and the
  user gave none, and the `gh` CLI is available and authenticated, try `gh repo view --json description -q
  .description` before falling back to an empty string (never invent one).
- **Inception year**: `git log --reverse --format=%ad --date=format:%Y | head -1` for the first commit's year; fall
  back to the current year if the repository has no commits yet. Feeds `pom { inceptionYear.set(...) }`.
- **Stable branch**: default `main` unless the caller (an orchestrator, or the user) names a different stable
  branch this catalog's other Android skills use (`iru-setup-android-github-workflows`'s `stable-branch`, default
  `main`) — used only to build the `LICENSE` URL in Step 6's `pom { licenses {...} }` block.

## Step 4 — Look up toolchain versions

Look up every version below at run time; only fall back to the table's recorded value if the lookup fails (offline,
registry unreachable, rate-limited). Note in Step 11's report whenever a fallback was used instead of a live
lookup, and whenever a resolved version differs meaningfully from what this table recorded.

| Component | Lookup | September 2026 fallback |
|---|---|---|
| Gradle | `curl https://services.gradle.org/versions/current` → `.version` (and `.checksum` for the wrapper's `distributionSha256Sum`, Step 5) | `9.7.1` / sha256 `acd53f1edaf02f1a8ff99879f8a34b302661a057d9b063ae9e35b552f804d20a` |
| AGP (`com.android.application`/`com.android.library`) | `https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/maven-metadata.xml` → highest version with no `-alpha`/`-beta`/`-rc` suffix | `9.4.0` |
| Kotlin (`org.jetbrains.kotlin.android`, `kotlin-reflect`) | `https://dl.google.com/dl/android/maven2/org/jetbrains/kotlin/kotlin-reflect/maven-metadata.xml` `<release>`, or the Gradle Plugin Portal's `org/jetbrains/kotlin/android/...` metadata, filtered to a stable (no `-Beta`/`-RC`) version | `2.4.20` |
| Dokka (`org.jetbrains.dokka`) | `https://plugins.gradle.org/m2/org/jetbrains/dokka/org.jetbrains.dokka.gradle.plugin/maven-metadata.xml`, highest stable — **but see the Dokka/AGP quirk below before trusting the highest stable version** | `2.1.0` (not the newer `2.2.0` — see Step 11's "Known quirks") |
| `org.sonarqube` plugin (only `sonar` ≠ `none`) | `https://plugins.gradle.org/m2/org/sonarqube/org.sonarqube.gradle.plugin/maven-metadata.xml` `<release>` | `7.5.0.8588` |
| `com.vanniktech.maven.publish` (only `publish: yes`) | `https://plugins.gradle.org/m2/com/vanniktech/maven/publish/com.vanniktech.maven.publish.gradle.plugin/maven-metadata.xml`, highest stable (this plugin's own `<release>`/`<latest>` tags were observed stale in September 2026 — sort the `<versions>` list numerically yourself rather than trusting them) | `0.37.0` |
| `junit:junit` (JUnit 4) | `https://repo1.maven.org/maven2/junit/junit/maven-metadata.xml` `<release>` | `4.13.2` |
| `androidx.test.ext:junit` / `:junit-ktx` | `https://dl.google.com/dl/android/maven2/androidx/test/ext/junit/maven-metadata.xml` (and `.../junit-ktx/...`) `<release>` | `1.3.0` |
| `androidx.test.espresso:espresso-core` | `https://dl.google.com/dl/android/maven2/androidx/test/espresso/espresso-core/maven-metadata.xml` `<release>` | `3.7.0` |
| `androidx.test:core-ktx` | `https://dl.google.com/dl/android/maven2/androidx/test/core-ktx/maven-metadata.xml` `<release>` | `1.7.0` |
| `androidx.compose:compose-bom` | `https://dl.google.com/dl/android/maven2/androidx/compose/compose-bom/maven-metadata.xml` `<release>` — **but see the `compile-sdk` compatibility quirk below before taking the newest one blindly** | `2026.02.01` (the newest release at verification time, `2026.09.00`, requires `compileSdk` ≥ 37 — see Step 11) |
| `androidx.activity:activity-compose` (needed to make the `app/` sample a real Compose app — see Step 7) | `https://dl.google.com/dl/android/maven2/androidx/activity/activity-compose/maven-metadata.xml`, highest stable | `1.13.0` |
| `com.google.android.material:material` | `https://dl.google.com/dl/android/maven2/com/google/android/material/material/maven-metadata.xml` `<release>` | `1.14.0` |
| `io.mockk:mockk-android` | Maven Central search `g:io.mockk AND a:mockk-android` | `1.14.9` (the reference repository's own `libs.versions.toml`; Maven Central's search index returned a stale `1.14.3` while verifying this skill — prefer the reference's observed value if the two disagree) |
| `org.robolectric:robolectric` | `https://repo1.maven.org/maven2/org/robolectric/robolectric/maven-metadata.xml` `<release>` | `4.17` — but see Step 6's Robolectric/`compileSdk` quirk before trusting this blindly |
| `com.irurueta:irurueta-android-test-utils` | `https://repo1.maven.org/maven2/com/irurueta/irurueta-android-test-utils/maven-metadata.xml` `<release>` | `1.3.2` |
| `de.mannodermaus.android-junit` (only `junit: 5`) | `https://plugins.gradle.org/m2/de/mannodermaus/android-junit/de.mannodermaus.android-junit.gradle.plugin/maven-metadata.xml` `<release>` — note the plugin id dropped its trailing `5` when the `mannodermaus/android-junit5` project was renamed `android-junit-framework` | `2.0.1` |
| `org.jetbrains.kotlinx.kover` (only `coverage-tool: kover`) | `https://plugins.gradle.org/m2/org/jetbrains/kotlinx/kover/org.jetbrains.kotlinx.kover.gradle.plugin/maven-metadata.xml` `<release>` | `0.9.9` |
| `io.gitlab.arturbosch.detekt` (only `static-analysis: lint+detekt+ktlint`) | `https://plugins.gradle.org/m2/io/gitlab/arturbosch/detekt/io.gitlab.arturbosch.detekt.gradle.plugin/maven-metadata.xml` `<release>` | `1.23.8` |
| `com.diffplug.spotless` (only `static-analysis: lint+detekt+ktlint`) | `https://plugins.gradle.org/m2/com/diffplug/spotless/com.diffplug.spotless.gradle.plugin/maven-metadata.xml` `<release>` | `8.10.2` |
| `com.pinterest.ktlint` CLI (only `static-analysis: lint+detekt+ktlint`, the version Spotless's `ktlint(...)` call pins) | `https://repo1.maven.org/maven2/com/pinterest/ktlint/ktlint-cli/maven-metadata.xml` `<release>` | `1.8.0` |
| `org.junit.jupiter:junit-jupiter` / `org.junit.platform:junit-platform-launcher` (only `junit: 5`) | `https://repo1.maven.org/maven2/org/junit/jupiter/junit-jupiter/maven-metadata.xml` / `.../org/junit/platform/junit-platform-launcher/maven-metadata.xml` `<release>` | `6.1.3` for both |

## Step 5 — Reference templates: Gradle wrapper and root project files

These are genericized example templates — verified together end-to-end while building this skill (`./gradlew
--offline help` and `./gradlew :lib:assembleDebug` both run clean against them with `junit: 4`, `coverage-tool:
jacoco`, `static-analysis: lint`, `built-in-kotlin: no`) — kept verbatim below except for the placeholders. Only
substitute `<placeholder>` values using Steps 2–4; every other line is copied as shown.

### `gradle/wrapper/gradle-wrapper.properties`

```properties
distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\://services.gradle.org/distributions/gradle-<gradle-version>-bin.zip
distributionSha256Sum=<gradle-distribution-sha256>
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
```

`<gradle-version>` and `<gradle-distribution-sha256>` come from Step 4's Gradle lookup (`.version` and `.checksum`
of `https://services.gradle.org/versions/current`) — the checksum can also be fetched directly from
`https://services.gradle.org/distributions/gradle-<gradle-version>-bin.zip.sha256` if you resolved the version some
other way. `distributionSha256Sum` is not optional here even though the reference repository's own
`gradle-wrapper.properties` predates it (it was added later, in a Gradle version that supports wrapper-integrity
verification) — it makes the wrapper refuse a tampered/corrupted download.

### Root `build.gradle.kts`

```kotlin
// Top-level build file where you can add configuration options common to all sub-projects/modules.
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.android) apply false
    alias(libs.plugins.kotlin.compose) apply false
}

project.delete {
    delete(rootProject.layout.buildDirectory)
}
```

No placeholders — copied verbatim. `com.android.library` is deliberately *not* declared `apply false` here: once
`com.android.application` resolves AGP onto the root build's plugin classpath (even `apply false`), the version-less
`android-library` alias in `gradle/libs.versions.toml` (below) resolves against that same classpath when `lib/`
applies it — confirmed this is exactly how the reference repository does it, and it built clean while verifying
this skill.

### `settings.gradle.kts`

```kotlin
pluginManagement {
    repositories {
        google {
            content {
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
                includeGroupByRegex("androidx.*")
            }
        }
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        maven(url = "https://oss.sonatype.org/content/repositories/snapshots")
    }
}

rootProject.name = "<artifact-id>"
include(":app")
include(":lib")
```

Only `<artifact-id>` (Step 2) is substituted. The Sonatype snapshots repository is kept even when `version` doesn't
end in `-SNAPSHOT` — it's what a future `-SNAPSHOT` bump (e.g. via `iru-android-bump-version`) will need without
another edit here. `FAIL_ON_PROJECT_REPOS` is required, not optional: it's what makes `settings.gradle.kts` the
single source of truth for repositories, catching a module that tries to declare its own `repositories {}` block.

### `gradle.properties`

```properties
# Project-wide Gradle settings.
# IDE (e.g. Android Studio) users:
# Gradle settings configured through the IDE *will override*
# any settings specified in this file.
# For more details on how to configure your build environment visit
# http://www.gradle.org/docs/current/userguide/build_environment.html
# Specifies the JVM arguments used for the daemon process.
# The setting is particularly useful for tweaking memory settings.
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
# When configured, Gradle will run in incubating parallel mode.
# This option should only be used with decoupled projects. More details, visit
# http://www.gradle.org/docs/current/userguide/multi_project_builds.html#sec:decoupled_projects
# org.gradle.parallel=true
# AndroidX package structure to make it clearer which packages are bundled with the
# Android operating system, and which are packaged with your app"s APK
# https://developer.android.com/topic/libraries/support-library/androidx-rn
android.useAndroidX=true
# Kotlin code style for this project: "official" or "obsolete":
kotlin.code.style=official
# Enables namespacing of each library's R class so that its R class includes only the
# resources declared in the library itself and none from the library's dependencies,
# thereby reducing the size of the R class for that library
android.nonTransitiveRClass=true
org.jetbrains.dokka.experimental.gradle.pluginMode=V2Enabled
org.jetbrains.dokka.experimental.gradle.pluginMode.noWarn=true
org.gradle.configuration-cache=true
android.defaults.buildfeatures.resvalues=true
android.sdk.defaultTargetSdkToCompileSdkIfUnset=false
android.enableAppCompileTimeRClass=false
android.usesSdkInManifest.disallowed=false
android.uniquePackageNames=false
android.dependency.useConstraints=true
android.r8.strictFullModeForKeepRules=false
android.r8.optimizedResourceShrinking=false
android.builtInKotlin=<built-in-kotlin-flag>
android.newDsl=<built-in-kotlin-flag>
```

`<built-in-kotlin-flag>` is `false` unless the user chose `built-in-kotlin: yes` in Step 2, in which case both lines
become `true`. Every other line is copied verbatim from the reference repository — this is a real, working
`gradle.properties`, not a minimal one; `org.gradle.configuration-cache=true` in particular is why Step 10's
`--no-configuration-cache` caveat exists for the Maven Central publish tasks (see the workflows skill).

### `gradle/libs.versions.toml`

```toml
[versions]
agp = "<agp-version>"
kotlin = "<kotlin-version>"
junit = "<junit4-version>"
junitVersion = "<androidx-junit-version>"
espressoCore = "<androidx-espresso-version>"
composeBom = "<compose-bom-version>"
material = "<material-version>"
dokka = "<dokka-version>"
sonarqube = "<sonarqube-plugin-version>"
mockk = "<mockk-version>"
testCoreKtx = "<androidx-test-core-ktx-version>"
publish = "<vanniktech-publish-version>"
robolectric = "<robolectric-version>"
kotlinReflect = "<kotlin-version>"
iruruetaTestUtils = "<irurueta-test-utils-version>"
activityCompose = "<activity-compose-version>"

[libraries]
junit = { group = "junit", name = "junit", version.ref = "junit" }
androidx-junit = { group = "androidx.test.ext", name = "junit", version.ref = "junitVersion" }
androidx-espresso-core = { group = "androidx.test.espresso", name = "espresso-core", version.ref = "espressoCore" }
androidx-compose-bom = { group = "androidx.compose", name = "compose-bom", version.ref = "composeBom" }
androidx-material3 = { group = "androidx.compose.material3", name = "material3" }
androidx-test-core-ktx = { group = "androidx.test", name = "core-ktx", version.ref = "testCoreKtx" }
androidx-test-ext-junit-ktx = { group = "androidx.test.ext", name = "junit-ktx", version.ref = "junitVersion" }
material = { group = "com.google.android.material", name = "material", version.ref = "material" }
mockk-android = { group = "io.mockk", name = "mockk-android", version.ref = "mockk" }
robolectric = { group = "org.robolectric", name = "robolectric", version.ref = "robolectric" }
kotlin-reflect = { group = "org.jetbrains.kotlin", name = "kotlin-reflect", version.ref = "kotlinReflect" }
irurueta-test-utils = { group = "com.irurueta", name = "irurueta-android-test-utils", version.ref = "iruruetaTestUtils" }
androidx-activity-compose = { group = "androidx.activity", name = "activity-compose", version.ref = "activityCompose" }
androidx-ui-tooling-preview = { group = "androidx.compose.ui", name = "ui-tooling-preview" }
androidx-ui-tooling = { group = "androidx.compose.ui", name = "ui-tooling" }

[plugins]
android-application = { id = "com.android.application", version.ref = "agp" }
android-library = { id = "com.android.library" }
kotlin-android = { id = "org.jetbrains.kotlin.android", version.ref = "kotlin" }
kotlin-compose = { id = "org.jetbrains.kotlin.plugin.compose", version.ref = "kotlin" }
dokka = { id = "org.jetbrains.dokka", version.ref = "dokka" }
sonarqube = { id = "org.sonarqube", version.ref = "sonarqube" }
publish = { id = "com.vanniktech.maven.publish", version.ref = "publish" }
```

Every `[versions]`/`[libraries]`/`[plugins]` alias up to `androidx-activity-compose` is copied verbatim from the
reference repository (minus its two project-specific dependencies, `geometry`/`khronos`, which are that library's
own OpenGL/geometry dependencies and have no place in a generic template) — do not rename, reorder, or drop any of
them. `androidx-activity-compose`, `androidx-ui-tooling-preview`, and `androidx-ui-tooling` are the three additions
beyond the reference's own file: the reference's `app/` module declares the Compose BOM/Material3 dependencies but
its actual `MainActivity` never calls `setContent {}` (it's a legacy View-based activity), so it never needed
`activity-compose`, and it never uses `@Preview`, so it never needed `ui-tooling-preview`/`ui-tooling` either. All
three are required to make this skill's own `app/` module (Step 7) a genuinely working Compose sample with a
functioning `@Preview` — confirmed while verifying this skill: omitting `ui-tooling-preview` fails
`:app:compileDebugKotlin` with `Unresolved reference 'tooling'` on the `import
androidx.compose.ui.tooling.preview.Preview` line in `MainActivity.kt` (Step 7).

Then apply the gating rules, each an addition or removal from the exact block above — never touch the rest of the
file for any of them:

- **`sonar: none`**: remove the `sonarqube = "..."` line from `[versions]` and the `sonarqube = {...}` line from
  `[plugins]`.
- **`publish: no`**: remove the `publish = "..."` line from `[versions]` and the `publish = {...}` line from
  `[plugins]`.
- **`junit: 5`**: add to `[versions]`: `junitJupiter = "<junit-jupiter-version>"`,
  `junitPlatformLauncher = "<junit-platform-launcher-version>"`,
  `mannodermausAndroidJunit = "<mannodermaus-plugin-version>"`. Add to `[libraries]`:
  `junit-jupiter = { group = "org.junit.jupiter", name = "junit-jupiter", version.ref = "junitJupiter" }`,
  `junit-platform-launcher = { group = "org.junit.platform", name = "junit-platform-launcher", version.ref = "junitPlatformLauncher" }`.
  Add to `[plugins]`:
  `mannodermaus-android-junit = { id = "de.mannodermaus.android-junit", version.ref = "mannodermausAndroidJunit" }`.
  Keep the base `junit` (JUnit 4) alias regardless — instrumented tests still need it.
- **`coverage-tool: kover`**: add to `[versions]`: `kover = "<kover-version>"`. Add to `[plugins]`:
  `kover = { id = "org.jetbrains.kotlinx.kover", version.ref = "kover" }`.
- **`static-analysis: lint+detekt+ktlint`**: add to `[versions]`: `detekt = "<detekt-version>"`,
  `spotless = "<spotless-version>"`, `ktlint = "<ktlint-version>"`. Add to `[plugins]`:
  `detekt = { id = "io.gitlab.arturbosch.detekt", version.ref = "detekt" }`,
  `spotless = { id = "com.diffplug.spotless", version.ref = "spotless" }`.

## Step 6 — Reference templates: the `lib/` module

### `lib/.gitignore`

```
/build
```

No placeholders. Same shape as the reference repository's `lib/.gitignore` (one line, no trailing newline needed).

### `lib/proguard-rules.pro`

```
# Add project specific ProGuard rules here.
# You can control the set of applied configuration files using the
# proguardFiles setting in old_build.gradle_old.
#
# For more details, see
#   http://developer.android.com/guide/developing/tools/proguard.html

# If your project uses WebView with JS, uncomment the following
# and specify the fully qualified class name to the JavaScript interface
# class:
#-keepclassmembers class fqcn.of.javascript.interface.for.webview {
#   public *;
#}

# Uncomment this to preserve the line number information for
# debugging stack traces.
#-keepattributes SourceFile,LineNumberTable

# If you keep the line number information, uncomment this to
# hide the original source file name.
#-renamesourcefileattribute SourceFile
```

No placeholders — copied verbatim (this is AGP's own default template comment, present unmodified in the reference
repository).

### `lib/src/main/AndroidManifest.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest>

</manifest>
```

No placeholders. A library manifest needs nothing beyond this until real components (services, providers, custom
permissions) are added.

### `lib/src/androidTest/AndroidManifest.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="<namespace>.test">

    <application
        android:allowBackup="true"
        android:label="<artifact-id> test">

    </application>
</manifest>
```

`<namespace>.test` and `<artifact-id>` from Steps 2. The reference repository's own instrumented-test manifest also
points `android:icon`/`android:roundIcon` at a dedicated test launcher icon (`ic_launcher_test`); this template
omits that (no icon needed for a headless instrumentation APK) to avoid shipping more binary launcher assets than
this library scaffold needs — add them later if the library's own instrumented tests want a distinct icon.

### `lib/src/test/resources/<namespace-path>/robolectric.properties`

```properties
sdk=<robolectric-sdk>
```

`<namespace-path>` is `<namespace>` with `.` replaced by `/` (e.g. `com/example/myandroidlibrary`) — Robolectric
resolves this file as a classpath resource next to the package under test, exactly like the reference repository's
own `lib/src/test/resources/com/irurueta/android/glutils/robolectric.properties`. `<robolectric-sdk>` should be the
highest API level Robolectric's resolved version (Step 4) actually ships a shadow jar for — **this is not always
the same as `compile-sdk`**: Robolectric typically lags AGP/`compile-sdk` support by a release or two, and picking
an SDK level Robolectric doesn't support fails every Robolectric-backed test with a "does not support API level"
error at collection time, before any test body runs. Check Robolectric's own release notes/`org.robolectric:android-all`
artifact listing for the resolved Robolectric version before trusting `compile-sdk`'s value here; the fallback
recorded while verifying this skill is `35` (one below the reference repository's `compileSdk = 36`, matching what
Robolectric actually supported at verification time — see Step 10).

### Placeholder source, unit test, and instrumented test

Every source file below carries this license-header comment (omit it entirely, on all three files, if "No license"
was chosen in Step 2):

```kotlin
/*
 * Copyright (C) <copyright-year> <developer-name>
 *
 * Licensed under the <license-name> (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *         <license-url>
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
```

`lib/src/main/java/<namespace-path>/Example.kt`:

```kotlin
package <namespace>

/**
 * Placeholder type for the `<artifact-id>` library.
 *
 * Replace this with the library's real first public type — it exists so the generated
 * build/test/lint/coverage/docs pipeline has something concrete to succeed against
 * immediately after scaffolding.
 */
class Example {
    /**
     * Adds two integers together.
     *
     * @param a the first addend.
     * @param b the second addend.
     * @return the sum of [a] and [b].
     */
    fun add(a: Int, b: Int): Int = a + b
}
```

`lib/src/test/java/<namespace-path>/ExampleUnitTest.kt` — **JUnit 4** (`junit: 4`, the default and the only variant
verified by this skill, Step 10):

```kotlin
package <namespace>

import org.junit.Assert.assertEquals
import org.junit.Test

class ExampleUnitTest {
    @Test
    fun `add returns the sum of two integers`() {
        assertEquals(4, Example().add(2, 2))
    }
}
```

**JUnit 5** (`junit: 5`, unverified locally) — same body, swap the two imports for
`org.junit.jupiter.api.Assertions.assertEquals` and `org.junit.jupiter.api.Test`.

`lib/src/androidTest/java/<namespace-path>/ExampleInstrumentedTest.kt`:

```kotlin
package <namespace>

import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.ext.junit.runners.AndroidJUnit4

import org.junit.Test
import org.junit.runner.RunWith

import org.junit.Assert.assertEquals

/**
 * Instrumented test, which will execute on an Android device.
 *
 * See [testing documentation](http://d.android.com/tools/testing).
 */
@RunWith(AndroidJUnit4::class)
class ExampleInstrumentedTest {
    @Test
    fun useAppContext() {
        // Context of the app under test.
        val appContext = InstrumentationRegistry.getInstrumentation().targetContext
        assertEquals("<namespace>.test", appContext.packageName)
    }
}
```

Kept close to the reference repository's own `ExampleInstrumentedTest.kt` (same imports, same doc comment) — only
the asserted package name is templated, to match `lib/src/androidTest/AndroidManifest.xml`'s `<namespace>.test`
above. This file always uses `@RunWith(AndroidJUnit4::class)`/JUnit 4 regardless of the `junit` answer — see Step
2's note on why instrumented tests are unaffected by that toggle.

### `lib/build.gradle.kts`

```kotlin
import com.vanniktech.maven.publish.AndroidSingleVariantLibrary
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.dokka)
    // Omit the next line entirely when sonar: none
    alias(libs.plugins.sonarqube)
    // Omit the next line entirely when publish: no
    alias(libs.plugins.publish)
    // Only when junit: 5
    alias(libs.plugins.mannodermaus.android.junit)
    // Only when coverage-tool: kover
    alias(libs.plugins.kover)
    // Only when static-analysis: lint+detekt+ktlint (both lines)
    alias(libs.plugins.detekt)
    alias(libs.plugins.spotless)
}

val libraryVersion = "<version>"

android {
    namespace = "<namespace>"
    compileSdk = <compile-sdk>

    defaultConfig {
        minSdk = <min-sdk>
        testOptions.targetSdk = <compile-sdk>

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        val buildNumber = System.getenv("BUILD_NUMBER") ?: ""
        val apkPrefixLabels = listOf("<artifact-id>", libraryVersion, buildNumber)
        base.archivesName = apkPrefixLabels.filter { it != "" }.joinToString("-")
    }

    buildTypes {
        debug {
            // Omit these two lines entirely when coverage-tool: kover — Kover replaces AGP's own
            // unit/instrumented-test coverage wiring with its own report tasks (see below)
            enableUnitTestCoverage = true
            enableAndroidTestCoverage = true
        }
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildFeatures {
        buildConfig = true
    }
    testOptions {
        unitTests {
            isIncludeAndroidResources = true
        }
    }
    packaging {
        resources {
            excludes.add("META-INF/LICENSE-notice.md")
            excludes.add("META-INF/LICENSE.md")
        }
    }
}
kotlin {
    compilerOptions {
        jvmTarget = JvmTarget.JVM_17
    }
}

// Omit this whole `sonar { ... }` block entirely when sonar: none
sonar {
    properties {
        property("sonar.scanner.skipJreProvisioning", true)
        property("sonar.projectKey", "<sonar-project-key>")
        property("sonar.projectName", "<artifact-id>")
        property("sonar.organization", "<sonar-organization>")
        property("sonar.host.url", "<sonar-host-url>")

        property("sonar.tests", listOf("src/test/java", "src/androidTest/java"))
        property("sonar.test.inclusions",
            listOf("**/*Test*/**", "src/androidTest/**", "src/test/**"))
        property("sonar.test.exclusions",
            listOf("**/*Test*/**", "src/androidTest/**", "src/test/**"))
        property("sonar.sourceEncoding", "UTF-8")
        property("sonar.sources", "src/main/java")
        property("sonar.exclusions", "**/*Test*/**,*.json,'**/*test*/**,**/.gradle/**,**/R.class")

        val libraries = project.android.sdkDirectory.path + "/platforms/android-<compile-sdk>/android.jar"
        property("sonar.libraries", libraries)
        property("sonar.java.libraries", libraries)
        property("sonar.java.test.libraries", libraries)
        property("sonar.binaries", "build/intermediates/javac/debug/classes,build/tmp/kotlin-classes/debug")
        property("sonar.java.binaries", "build/intermediates/javac/debug/classes,build/tmp/kotlin-classes/debug")

        property("sonar.coverage.jacoco.xmlReportPaths",
            listOf("build/reports/coverage/androidTest/debug/connected/report.xml",
                "build/reports/coverage/test/report.xml"))
        property("sonar.java.coveragePlugin", "jacoco")
        property("sonar.junit.reportsPath",
            listOf("build/test-results/testDebugUnitTest",
                "build/outputs/androidTest-results/connected/debug"))
        property("sonar.android.lint.report", "build/reports/lint-results-debug.xml")
    }
}

dependencies {
    implementation(libs.material)
    testImplementation(libs.junit)
    // Only when junit: 5, in addition to the JUnit 4 line above (androidTest keeps running on JUnit 4)
    testImplementation(libs.junit.jupiter)
    testRuntimeOnly(libs.junit.platform.launcher)
    testImplementation(libs.mockk.android)
    testImplementation(libs.robolectric)
    testImplementation(libs.androidx.test.core.ktx)
    testImplementation(libs.kotlin.reflect)
    testImplementation(libs.irurueta.test.utils)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(libs.androidx.test.core.ktx)
    androidTestImplementation(libs.androidx.test.ext.junit.ktx)
    androidTestImplementation(libs.mockk.android)
}

// Only when coverage-tool: kover — unverified locally, review the applied Kover version's own
// documentation for its current report-task names/DSL before relying on this block as-is
kover {
    reports {
        total {
            xml {
                onCheck = false
            }
        }
    }
}

// Only when static-analysis: lint+detekt+ktlint — unverified locally
detekt {
    config.setFrom(files("$rootDir/detekt.yml"))
    buildUponDefaultConfig = true
}

spotless {
    kotlin {
        target("src/**/*.kt")
        ktlint("<ktlint-version>")
        // Omit this licenseHeader(...) call if "No license" was chosen in Step 2
        licenseHeader(
            """
            |/*
            | * Copyright (C) ${"$"}YEAR <developer-name>
            | *
            | * Licensed under the <license-name> (the "License");
            | * you may not use this file except in compliance with the License.
            | * You may obtain a copy of the License at
            | *
            | *         <license-url>
            | *
            | * Unless required by applicable law or agreed to in writing, software
            | * distributed under the License is distributed on an "AS IS" BASIS,
            | * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
            | * See the License for the specific language governing permissions and
            | * limitations under the License.
            | */
            |
            """.trimMargin()
        )
    }
    kotlinGradle {
        target("*.gradle.kts")
        ktlint("<ktlint-version>")
    }
}

// Omit this whole `mavenPublishing { ... }` block entirely when publish: no
mavenPublishing {
    configure(AndroidSingleVariantLibrary(
        // the published variant
        variant = "release",
        // whether to publish a sources jar
        sourcesJar = true,
        // whether to publish a javadoc jar
        publishJavadocJar = true,
    ))

    publishToMavenCentral()
    signAllPublications()

    coordinates("<group-id>", "<artifact-id>", libraryVersion)

    pom {
        name.set("<artifact-id>")
        description.set("<description>")
        inceptionYear.set("<inception-year>")
        url.set("<repository-url>")
        // Omit this whole `licenses {...}` block if "No license" was chosen in Step 2
        licenses {
            license {
                name.set("<license-name>")
                url.set("<repository-url>/blob/<stable-branch>/LICENSE")
                distribution.set("<repository-url>/blob/<stable-branch>/LICENSE")
            }
        }
        developers {
            developer {
                id.set("<owner>")
                name.set("<developer-name>")
                email.set("<developer-email>")
                url.set("<organization-url>")
            }
        }
        scm {
            url.set("<repository-url>")
            connection.set("scm:git:<host>/<owner>/<repo>.git")
            developerConnection.set("scm:git:ssh://<host>/<owner>/<repo>.git")
        }
    }
}
```

No `lint { sarifReport = true }` block is written here even though a SARIF report is exactly what
`iru-setup-android-github-workflows`'s CodeQL upload step needs (`lib/build/reports/lint-results-debug.sarif`) —
confirmed while verifying this skill: under the AGP version resolved in Step 4, `sarifReport` is a deprecated,
no-op property (`'var sarifReport: Boolean' is deprecated. Lint reports are now always generated.`) and
`lint-results-debug.sarif` is written unconditionally alongside `lint-results-debug.xml`/`.html`/`.txt` regardless
of this setting. If a lookup at generation time finds an older AGP where `sarifReport` still has an effect, add the
block back; don't add it by default against a current AGP.

`ktlint("<ktlint-version>")` pins the ktlint version Spotless's bundled runner uses (Spotless's own plugin version
does not imply a specific ktlint release) — always pass it explicitly rather than relying on Spotless's default.
The `${"$"}YEAR` in the `licenseHeader(...)` call is written that way *deliberately* — Spotless's own license-header
mechanism substitutes the literal token `$YEAR` per file at check/format time, and `${"$"}YEAR` is how Kotlin's
`build.gradle.kts` DSL escapes a literal `$` inside a string without Kotlin itself trying to interpolate a variable
named `YEAR`.

### `detekt.yml` (repository root, only when `static-analysis: lint+detekt+ktlint`)

```yaml
build:
  maxIssues: 0

style:
  MaxLineLength:
    active: true
    maxLineLength: 120

comments:
  UndocumentedPublicClass:
    active: true
  UndocumentedPublicFunction:
    active: true
  UndocumentedPublicProperty:
    active: true
```

`buildUponDefaultConfig = true` in `lib/build.gradle.kts` means this file only overrides/adds rules on top of
Detekt's own default ruleset — it is not a full replacement. Also wire SARIF output (needed by
`iru-setup-android-github-workflows`'s `github/codeql-action/upload-sarif` step) by adding, still inside the
`static-analysis: lint+detekt+ktlint` block of `lib/build.gradle.kts`:

```kotlin
tasks.withType<io.gitlab.arturbosch.detekt.Detekt>().configureEach {
    reports {
        sarif.required.set(true)
    }
}
```

## Step 7 — Reference templates: the `app/` Compose sample module

The `app/` module is part of this library scaffold, not an optional add-on — it exists so the library has a
minimal, genuinely working Jetpack Compose consumer from the moment it's generated, exactly as the reference
repository ships both `lib/` and `app/` together. Its resources (theme, colors, strings, launcher icon) are the
reference repository's own `app/src/main/res` files, genericized; its `MainActivity.kt` is **not** copied from the
reference as-is — the reference's own `MainActivity` is a legacy View-based activity (a `ConstraintLayout` +
`activity_main.xml`) even though it declares `buildFeatures { compose = true }` and the Compose BOM/Material3
dependencies. This skill writes a real Compose `MainActivity` instead (using those same dependencies, plus
`androidx.activity:activity-compose` — see Step 5's toml note), because the task this scaffold serves needs a
working Compose sample, not a dependency that's declared but unused.

### `app/.gitignore`

```
/build
```

### `app/src/main/AndroidManifest.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="<namespace>.app">

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:theme="@style/<theme-name>">
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />

                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>

</manifest>
```

`<theme-name>` is `Theme.<ArtifactPascalCase>`, where `<ArtifactPascalCase>` is `<artifact-id>` with each
`-`/`_`-separated word capitalized and concatenated, non-alphanumeric characters stripped (e.g. `my-android-library`
→ `MyAndroidLibrary`, so `Theme.MyAndroidLibrary`) — the same derivation `android:theme` and
`app/src/main/res/values/themes.xml`'s `<style name=...>` both use.

### `app/src/main/java/<namespace-path>/app/MainActivity.kt`

```kotlin
package <namespace>.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    Greeting()
                }
            }
        }
    }
}

@Composable
fun Greeting() {
    Text(text = "Hello, <artifact-id>!")
}

@Preview(showBackground = true)
@Composable
fun GreetingPreview() {
    MaterialTheme {
        Greeting()
    }
}
```

Prepend the same license-header comment block as Step 6's source files (omit if "No license"). `<namespace-path>`
is `<namespace>` with `.` replaced by `/`.

### `app/build.gradle.kts`

```kotlin
import org.jetbrains.kotlin.gradle.dsl.JvmTarget
import java.text.SimpleDateFormat
import java.util.Date

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.dokka)
    // Omit the next line entirely when sonar: none
    alias(libs.plugins.sonarqube)
}

android {
    namespace = "<namespace>.app"
    compileSdk = <compile-sdk>

    defaultConfig {
        applicationId = "<namespace>.app"
        minSdk = <min-sdk>
        targetSdk = <compile-sdk>
        versionCode = 1
        versionName = "<version>"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        val buildNumber = System.getenv("BUILD_NUMBER") ?: ""
        buildConfigField("String", "BUILD_NUMBER", "\"$buildNumber\"")
        val dateFormatter = SimpleDateFormat("yyyy-MM-dd HH:mm:ss")
        buildConfigField("String", "BUILD_TIMESTAMP", "\"" + dateFormatter.format(Date()) + "\"")
        val gitCommit = System.getenv("GIT_COMMIT")
        buildConfigField("String", "GIT_COMMIT", "\"$gitCommit\"")
        val gitBranch = System.getenv("GIT_BRANCH")
        buildConfigField("String", "GIT_BRANCH", "\"$gitBranch\"")

        val apkPrefixLabels = listOf("<artifact-id>", versionName, buildNumber)
        base.archivesName = apkPrefixLabels.filter { it != "" }.joinToString("-")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
}
kotlin {
    compilerOptions {
        jvmTarget = JvmTarget.JVM_17
    }
}

// Omit this whole `sonar { ... }` block entirely when sonar: none — same shape as lib/build.gradle.kts's block
// (Step 6), except `sonar.projectName` is suffixed with the Gradle project name so the two modules are
// distinguishable in the same SonarCloud/SonarQube project
sonar {
    properties {
        property("sonar.scanner.skipJreProvisioning", true)
        property("sonar.projectKey", "<sonar-project-key>")
        property("sonar.projectName", "<artifact-id>-${project.name}")
        property("sonar.organization", "<sonar-organization>")
        property("sonar.host.url", "<sonar-host-url>")

        property("sonar.tests", listOf("src/test/java", "src/androidTest/java"))
        property("sonar.test.inclusions",
            listOf("**/*Test*/**", "src/androidTest/**", "src/test/**"))
        property("sonar.test.exclusions",
            listOf("**/*Test*/**", "src/androidTest/**", "src/test/**"))
        property("sonar.sourceEncoding", "UTF-8")
        property("sonar.sources", "src/main/java")
        property("sonar.exclusions", "**/*Test*/**,*.json,'**/*test*/**,**/.gradle/**,**/R.class")

        val libraries = project.android.sdkDirectory.path + "/platforms/android-<compile-sdk>/android.jar"
        property("sonar.libraries", libraries)
        property("sonar.java.libraries", libraries)
        property("sonar.java.test.libraries", libraries)
        property("sonar.binaries", "build/intermediates/javac/debug/classes,build/tmp/kotlin-classes/debug")
        property("sonar.java.binaries", "build/intermediates/javac/debug/classes,build/tmp/kotlin-classes/debug")

        property("sonar.coverage.jacoco.xmlReportPaths",
            listOf("build/reports/coverage/androidTest/debug/connected/report.xml",
                "build/reports/coverage/test/report.xml"))
        property("sonar.java.coveragePlugin", "jacoco")
        property("sonar.junit.reportsPath",
            listOf("build/test-results/testDebugUnitTest",
                "build/outputs/androidTest-results/connected/debug"))
        property("sonar.android.lint.report", "build/reports/lint-results-debug.xml")
    }
}

dependencies {
    implementation(project(":lib"))
    implementation(libs.material)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.material3)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.ui.tooling.preview)
    debugImplementation(libs.androidx.ui.tooling)
    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
}
```

`versionName` mirrors `<version>` (Step 2's `libraryVersion`, kept as its own literal here rather than a
cross-module reference — Gradle build scripts in different modules don't share Kotlin `val`s) — keep the two in
sync by hand on every version bump, or use `iru-android-bump-version` (Task 30 of this same plan), which updates
both in one pass. `versionCode` starts at `1`; bump it manually (or via that same skill) on every release.
`androidx.activity:activity-compose`, `androidx.compose.ui:ui-tooling-preview`, and its `debugImplementation`-only
counterpart `androidx.compose.ui:ui-tooling` are needed *only* because this skill's `app/` module is a genuine
Compose app, unlike the reference repository's own (see Step 5's toml note) — confirmed while verifying this skill:
without `ui-tooling-preview`, `:app:compileDebugKotlin` fails with `Unresolved reference 'tooling'` on
`MainActivity.kt`'s `import androidx.compose.ui.tooling.preview.Preview` line. This module deliberately carries no
`lint { sarifReport = ... }` block — see Step 6's note on why that property is a deprecated no-op under current AGP.

### `app/src/main/res/values/strings.xml`

```xml
<resources>
    <string name="app_name"><artifact-id></string>
</resources>
```

### `app/src/main/res/values/colors.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="purple_200">#FFBB86FC</color>
    <color name="purple_500">#FF6200EE</color>
    <color name="purple_700">#FF3700B3</color>
    <color name="teal_200">#FF03DAC5</color>
    <color name="teal_700">#FF018786</color>
    <color name="black">#FF000000</color>
    <color name="white">#FFFFFFFF</color>
</resources>
```

No placeholders — the reference repository's own generic AGP-scaffolded palette, kept as-is since it names no real
project.

### `app/src/main/res/values/themes.xml`

```xml
<resources>
    <!-- Base application theme. -->
    <style name="<theme-name>" parent="Theme.MaterialComponents.DayNight.DarkActionBar">
        <!-- Primary brand color. -->
        <item name="colorPrimary">@color/purple_500</item>
        <item name="colorPrimaryVariant">@color/purple_700</item>
        <item name="colorOnPrimary">@color/white</item>
        <!-- Secondary brand color. -->
        <item name="colorSecondary">@color/teal_200</item>
        <item name="colorSecondaryVariant">@color/teal_700</item>
        <item name="colorOnSecondary">@color/black</item>
        <!-- Status bar color. -->
        <item name="android:statusBarColor">?attr/colorPrimaryVariant</item>
        <!-- Customize your theme here. -->
    </style>
</resources>
```

### `app/src/main/res/values-night/themes.xml`

```xml
<resources>
    <!-- Base application theme. -->
    <style name="<theme-name>" parent="Theme.MaterialComponents.DayNight.DarkActionBar">
        <!-- Primary brand color. -->
        <item name="colorPrimary">@color/purple_200</item>
        <item name="colorPrimaryVariant">@color/purple_700</item>
        <item name="colorOnPrimary">@color/black</item>
        <!-- Secondary brand color. -->
        <item name="colorSecondary">@color/teal_200</item>
        <item name="colorSecondaryVariant">@color/teal_200</item>
        <item name="colorOnSecondary">@color/black</item>
        <!-- Status bar color. -->
        <item name="android:statusBarColor">?attr/colorPrimaryVariant</item>
        <!-- Customize your theme here. -->
    </style>
</resources>
```

### Launcher icon — `app/src/main/res/drawable/ic_launcher_background.xml`, `ic_launcher_foreground.xml`, `app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml`, `ic_launcher_round.xml`

Copy the reference repository's own four launcher-icon files verbatim — they're already generic (AGP's own
default Android-robot launcher asset, no project-specific art):

```xml
<!-- app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml and ic_launcher_round.xml (identical content) -->
<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background" />
    <foreground android:drawable="@drawable/ic_launcher_foreground" />
</adaptive-icon>
```

For `ic_launcher_background.xml` and `ic_launcher_foreground.xml`, copy the reference repository's two vector
drawables byte-for-byte (they're AGP's stock 108dp adaptive-icon vector art with no text/branding — safe to reuse
as-is). This template deliberately ships **only** the `mipmap-anydpi-v26` adaptive-icon variant and skips the
legacy per-density raster (`mipmap-hdpi`/`-mdpi`/`-xhdpi`/`-xxhdpi`/`-xxxhdpi`) `.webp` fallbacks the reference
repository also carries: `minSdk` defaults to `26` (Step 2), which is exactly the API level `mipmap-anydpi-v26`
targets, so the vector-only adaptive icon covers every device this template supports without needing raster
fallbacks for older APIs. If a future `min-sdk` below `26` is ever chosen, regenerate raster mipmaps (e.g. via
Android Studio's Image Asset tool) before relying on the launcher icon rendering correctly.

## Step 8 — Resolve every placeholder

One consolidated resolution table for every `<placeholder>` used across Steps 5–7 — cross-reference this when
filling any template above:

| Placeholder | Source |
|---|---|
| `<group-id>`, `<artifact-id>`, `<namespace>`, `<description>`, `<version>`, `<min-sdk>`, `<compile-sdk>`, `<developer-name>`, `<developer-email>`, `<organization-url>` | Step 2 |
| `<license-name>` / `<license-url>` | Step 2's license choice; if "No license", remove every block/line that references them instead of leaving empty tags |
| `<built-in-kotlin-flag>` | Step 2's `built-in-kotlin` answer: `false` (default) or `true` |
| `<sonar-organization>`, `<sonar-project-key>`, `<sonar-host-url>` | Step 2's `sonar` answer; omit every `sonar`-gated block entirely if `sonar: none` |
| `<repository-url>`, `<host>`, `<owner>`, `<repo>`, `<inception-year>`, `<stable-branch>` | Step 3 |
| `<gradle-version>`, `<gradle-distribution-sha256>`, `<agp-version>`, `<kotlin-version>`, `<dokka-version>`, `<sonarqube-plugin-version>`, `<vanniktech-publish-version>`, `<junit4-version>`, `<androidx-junit-version>`, `<androidx-espresso-version>`, `<androidx-test-core-ktx-version>`, `<compose-bom-version>`, `<activity-compose-version>`, `<material-version>`, `<mockk-version>`, `<robolectric-version>`, `<irurueta-test-utils-version>`, `<mannodermaus-plugin-version>`, `<kover-version>`, `<detekt-version>`, `<spotless-version>`, `<ktlint-version>`, `<junit-jupiter-version>`, `<junit-platform-launcher-version>` | Step 4 |
| `<namespace-path>` | `<namespace>` with `.` → `/` |
| `<robolectric-sdk>` | Step 6's Robolectric/`compileSdk` note — not always equal to `<compile-sdk>` |
| `<theme-name>` | Step 7's PascalCase derivation from `<artifact-id>` |
| `<copyright-year>` | The current year |

`publish: no` removes the whole `mavenPublishing {...}` block from `lib/build.gradle.kts` and the `publish`
alias/plugin from `gradle/libs.versions.toml`; `publish: yes` (the default when open source) keeps them as shown,
with no placeholders of their own beyond the identity/license/repository ones already listed.

## Step 9 — Write the files

Apply Step 1's decision (regenerate / fill gaps only / gap-fill from `mode: existing`) file by file, across every
file listed in Steps 5–7 — write each one unless "fill gaps only"/`mode: existing` found that specific file already
present, in which case leave it untouched. Create every intermediate directory (`lib/src/main/java/<namespace-path>`,
`lib/src/test/resources/<namespace-path>`, `app/src/main/res/values-night`, etc.) as needed — don't touch any other
file already inside a directory this skill writes into.

Then create `local.properties` at the repository root, **only if it doesn't already exist** (it's per-machine and
this skill never overwrites it even on "regenerate"):

```properties
sdk.dir=<resolved-android-sdk-path>
```

`<resolved-android-sdk-path>` is `$ANDROID_HOME` or `$ANDROID_SDK_ROOT` if either is set in the environment,
otherwise ask the user for their Android SDK path. `local.properties` must never be committed — it isn't one of
this skill's own gitignore entries (`lib/.gitignore`/`app/.gitignore` only cover `/build`); the root `.gitignore`
that ignores it is `iru-setup-android-gitignore`'s responsibility (Task 22 of this same plan) — call this out
explicitly in Step 11 if that root `.gitignore` doesn't exist yet in this repository.

## Step 10 — Obtain the Gradle wrapper binaries

`gradle/wrapper/gradle-wrapper.properties` (Step 5) only tells an *existing* wrapper which Gradle version to
download — the wrapper script and jar themselves (`gradlew`, `gradlew.bat`, `gradle/wrapper/gradle-wrapper.jar`)
still need to exist. Obtain them one of these ways, in order of preference:

1. If a `gradle` CLI is already installed locally (any version — `gradle --version`), run `gradle wrapper
   --gradle-version <gradle-version> --distribution-type bin` at the repository root. This regenerates all three
   wrapper files (script + jar) already pinned to Step 5's resolved version — simplest, and what this skill used
   while verifying itself.
2. Otherwise, fetch the fixed wrapper scripts directly from the Gradle GitHub repository's matching release tag:
   `https://raw.githubusercontent.com/gradle/gradle/v<gradle-version>/gradlew` and `.../gradlew.bat`, and
   `gradle-wrapper.jar` from `https://raw.githubusercontent.com/gradle/gradle/v<gradle-version>/gradle/wrapper/gradle-wrapper.jar`.
   Mark `gradlew` executable afterward (`chmod +x gradlew`) — a `curl`-fetched file loses the executable bit.

Either way, confirm `gradle/wrapper/gradle-wrapper.properties` still matches Step 5's template afterward — `gradle
wrapper` regenerates that file too, and will overwrite `distributionSha256Sum` if the local `gradle` CLI's own
version differs from `<gradle-version>`.

## Step 11 — Verify

Run through the `iru-gate-runner` agent (per this catalog's convention: gates run through it rather than inline
Bash, so the caller gets a compact pass/fail summary instead of raw Gradle output):

1. `./gradlew --offline help` — a cheap first check that the Gradle files parse and the project configures at all.
   **Note explicitly to the user**: despite `--offline`, this first invocation still downloads the Gradle
   distribution itself (the version pinned in `gradle-wrapper.properties`) if it isn't already cached in
   `~/.gradle/wrapper/dists` — `--offline` only affects dependency resolution, not the wrapper's own bootstrap. This
   download can take several minutes on a fresh machine; be patient rather than treating a long-running first
   invocation as a failure.
2. `./gradlew :lib:assembleDebug` — compiles the library module (and transitively the `app/` module's dependency on
   it isn't exercised by this task alone; a full check should also try `:app:assembleDebug` and `:lib:testDebugUnitTest`,
   which `iru-android-test`/`iru-android-coverage` cover separately). **Note explicitly to the user**: this first
   real build also downloads every Android SDK component (`platforms;android-<compile-sdk>`, build-tools) and every
   Gradle dependency declared in Steps 5–6 that AGP/Gradle don't already have cached — also potentially several
   minutes, and requires `ANDROID_HOME`/`ANDROID_SDK_ROOT` (or `local.properties`'s `sdk.dir`, from Step 9) to point
   at a real Android SDK installation with SDK licenses already accepted.

If either step fails, report the actual Gradle error to the user rather than guessing at a fix — a missing SDK
component, an unaccepted SDK license, or a network-blocked plugin/dependency download are all common first-run
causes and are not, by themselves, defects in this skill's templates.

### Known quirks / verification notes (from building and verifying this skill, September 2026)

- **`./gradlew --offline help` genuinely fails on a cold machine**, not just slowly: with nothing cached yet,
  resolving the `com.android.application`/`com.android.library` plugins themselves needs the network, and
  `--offline` refuses that outright (`Plugin [...] was not found in any of the following sources ... Plugin
  Repositories`). Run the *first* invocation of any Gradle command without `--offline` (plain `./gradlew help`
  succeeded and populated the caches); only subsequent invocations can safely add `--offline`. Step 11 above already
  reflects this.
- **Dokka `2.2.0` cannot generate docs for this exact module shape.** `:lib:dokkaGenerate` (with `dokka = "2.2.0"`,
  `org.jetbrains.kotlin.android` applied, `built-in-kotlin: no`) fails every time with `org.jetbrains.dokka.DokkaException:
  Pre-generation validity check failed: Source sets 'androidJvm' and 'release' have the common source roots: .../
  lib/src/main/java/.../Example.kt, .../lib/src/main/java. Every Kotlin source file should belong to only one source
  set (module)` (tracked upstream as a known Dokka Gradle plugin V2 + Android limitation, similar to
  `Kotlin/dokka#3701`/`#3239`). **Dokka `2.1.0` (the version this skill actually pins as its fallback, Step 4) does
  not have this problem** — `:lib:dokkaGenerate` succeeds cleanly and writes `lib/build/dokka/html/index.html`. Do
  not silently take Dokka's "highest stable" release at generation time without first confirming `:lib:dokkaGenerate`
  still succeeds against an Android library module using the `org.jetbrains.kotlin.android` plugin — this exact
  combination is what broke.
- **Android Lint's `sarifReport` property is a deprecated no-op under the AGP version this skill resolved.** The
  reference repository's era of AGP needed `lint { sarifReport = true }` to emit a SARIF file; under AGP `9.4.0` it
  logs `'var sarifReport: Boolean' is deprecated. Lint reports are now always generated.` and
  `lib/build/reports/lint-results-debug.sarif` is written unconditionally either way, alongside
  `lint-results-debug.xml`/`.html`/`.txt` in the same directory — confirmed by removing the block entirely and
  re-running `:lib:lint`; the SARIF file still appeared. Both templates (Steps 6–7) omit this block for that reason.
  Confirmed the exact path CodeQL's `upload-sarif` step (`iru-setup-android-github-workflows`) should point at:
  **`lib/build/reports/lint-results-debug.sarif`**, alongside `lib/build/reports/lint-results-debug.xml`.
- **AGP's `createDebugUnitTestCoverageReport` DOES emit an XML report directly** — confirmed at
  **`lib/build/reports/coverage/test/debug/report.xml`** (plus `index.html`/`jacoco-sessions.html`/per-class HTML
  next to it), with `enableUnitTestCoverage = true` (Step 6) the only prerequisite. This means the reference
  repository's own CI-era workaround — running the vendored `jacoco-<ver>/lib/jacococli.jar` CLI by hand to convert
  a raw `.exec` file into XML — is **not needed** against the AGP version this skill resolved, and this skill
  deliberately does not vendor that jar or that conversion step. The raw JaCoCo exec file this task produces along
  the way (in case a future conversion is ever needed) is at
  **`lib/build/outputs/unit_test_code_coverage/debugUnitTest/testDebugUnitTest.exec`** — not
  `lib/build/jacoco/testReleaseUnitTest.exec`, which is where the reference repository's own (older) CI workflow
  looked for it. `iru-setup-android-github-workflows` (Task 23 of this same plan) should prefer the AGP task's own
  `report.xml` and only fall back to a vendored-jar conversion if a future AGP/Gradle combination stops emitting it.
- **The Compose BOM's release cadence outran `compileSdk = 36`.** The newest `compose-bom` release found at
  verification time, `2026.09.00`, pulls in `androidx.compose.foundation:foundation-android:1.12.1` and
  `androidx.compose.material:material-ripple-android:1.12.1`, both of which require `compileSdk` ≥ 37 — with
  `compile-sdk: 36` (this skill's own default, and the only `android-36`/`android-36.1` platforms installed
  locally), `:app:checkDebugAarMetadata` fails outright with 9 "requires... compile against version 37" errors.
  `compose-bom = "2026.02.01"` (the version this skill's fallback now pins, matching the reference repository's own
  choice) builds clean against `compileSdk = 36`. Re-verify this pairing whenever versions are re-resolved — see
  Step 2's `compile-sdk` note for the general rule (resolve `compile-sdk` and `compose-bom` together, not
  independently).
- **The Compose sample needed two dependencies this skill's authoring pass initially missed**:
  `androidx.compose.ui:ui-tooling-preview` (for the `@Preview` annotation import) and its `debugImplementation`-only
  companion `androidx.compose.ui:ui-tooling`. Without the first, `:app:compileDebugKotlin` fails with
  `org.jetbrains.kotlin.gradle.tasks.CompilationErrorException: Unresolved reference 'tooling'` on `MainActivity.kt`'s
  `import androidx.compose.ui.tooling.preview.Preview` line. Both are now in Step 5's `libs.versions.toml` template
  and Step 7's `app/build.gradle.kts` dependencies.
- **Robolectric lags `compileSdk`.** The reference repository pins `compileSdk = 36` but its own
  `robolectric.properties` pins `sdk=35` — confirmed this is deliberate, not an oversight: Robolectric's shadow-jar
  support for a new API level typically ships a release or two after AGP/Google Maven publish that `compile-sdk`.
  This skill's own verification run used `robolectric.properties`'s `sdk=35` against `compileSdk = 36` and
  `:lib:testDebugUnitTest` passed cleanly — always check Robolectric's resolved version actually supports the
  chosen `robolectric-sdk` before relying on the `compile-sdk` default there (Step 6).
- **`com.android.library`'s plugin version is deliberately left off the version catalog entry** (`android-library =
  { id = "com.android.library" }`, no `version.ref`) and still resolves correctly, because the root
  `build.gradle.kts` applies `com.android.application` (`apply false`) first, putting a specific AGP version on the
  build's plugin classpath before `lib/build.gradle.kts` ever requests `com.android.library` — see Step 5's note.
  Don't "fix" this by adding an explicit version — it isn't a mistake in the reference repository.
- **`com.vanniktech.maven.publish`'s Gradle Plugin Portal metadata `<latest>`/`<release>` tags were stale** during
  this skill's own lookups (reporting `0.13.0` when `0.37.0` was the actual newest stable release in the
  `<versions>` list) — sort that plugin's `<versions>` list numerically yourself rather than trusting the metadata
  document's own `<latest>`/`<release>` tags (Step 4).
- **`de.mannodermaus.android-junit5` was renamed.** The upstream GitHub project (`mannodermaus/android-junit5`) was
  renamed `mannodermaus/android-junit-framework`, and its Gradle plugin id dropped the trailing `5`
  (`de.mannodermaus.android-junit`, now on major version `2.x`) — a lookup against the old
  `de.mannodermaus.android-junit5` coordinate returns nothing.
- **`androidx.activity:activity-compose` is not in the reference repository's own `libs.versions.toml`** even
  though its `app/` module declares `buildFeatures { compose = true }` and the Compose BOM/Material3 dependencies —
  because its actual `MainActivity` never calls `setContent {}`. This skill adds the dependency so its own `app/`
  module (Step 7) is a real, working Compose sample rather than one with unused Compose dependencies.
- **`gradle.properties`'s AGP-behavior flags are increasingly deprecated under the resolved AGP version.** Roughly
  a dozen of the reference repository's `android.*` properties (`android.usesSdkInManifest.disallowed`,
  `android.sdk.defaultTargetSdkToCompileSdkIfUnset`, `android.enableAppCompileTimeRClass`, `android.builtInKotlin`,
  `android.newDsl`, `android.r8.optimizedResourceShrinking`, `android.defaults.buildfeatures.resvalues`, and more)
  now log `WARNING: The option setting '...' is deprecated ... It will be removed in version 10.0 of the Android
  Gradle plugin` at every configuration. None of them broke the build — this is purely a deprecation-noise finding,
  not a defect — but expect this list to shrink on every AGP major bump; re-check `gradle.properties` for dead
  properties whenever this skill's `<agp-version>` fallback is bumped across a major version.
- **JDK 26 (this machine's default JVM) was NOT the JDK primarily used for verification** (JDK 21, a JetBrains
  Runtime build, was — per this catalog's own guidance to prefer 21/17 over a brand-new default JDK) — but a
  spot-check (`./gradlew --offline help` and `:lib:compileDebugKotlin`, both under `JAVA_HOME` pointed at the local
  JDK 26) also succeeded against Gradle `9.7.1`/AGP `9.4.0`/Kotlin `2.4.20`. This spot-check is not a substitute for
  the full JDK 21 run above; prefer JDK 21 or 17 as this catalog's other Android skills do, but JDK 26 is not
  confirmed broken either.
- Configuration cache: every run above stored a configuration cache entry successfully (`Configuration cache entry
  stored`) with no invalidation errors or incompatibility warnings — `org.gradle.configuration-cache=true` in
  `gradle.properties` (Step 5) did not need any adjustment for this template.
- Everything above `junit: 4`, `coverage-tool: jacoco`, `static-analysis: lint`, `built-in-kotlin: no`,
  `sonar: cloud`, `publish: yes` was exercised end-to-end (`./gradlew --offline help`, `:lib:testDebugUnitTest`,
  `:lib:lint`, `:lib:dokkaGenerate`, `:lib:createDebugUnitTestCoverageReport`, `:app:assembleDebug`, plus a
  configuration-only check that `:lib:tasks --all` lists both the `sonar`/`sonarqube` and
  `publish*ToMavenCentral*` tasks without ever running them) in `$TMPDIR/iru-verify/android/library` — see that
  run's own findings (also recorded in this plan's `findings-task20.md` for `iru-setup-android-github-workflows` to
  consume) for exact report paths and resolved versions. `junit: 5`, `coverage-tool: kover`,
  `static-analysis: lint+detekt+ktlint`, and `built-in-kotlin: yes` are **unverified locally** — each is called out
  individually above; re-verify before relying on them in a real repository.

## Step 12 — Report

Summarize what was generated: the resolved `group-id`/`artifact-id`/`namespace`/`version`, `min-sdk`/`compile-sdk`,
the license chosen (or "none"), and the repository info inferred in Step 3.

State explicitly what was included versus omitted, and why:

- **`open-source`**: yes/no, as resolved in Step 2.
- **`publish`**: yes/no — if `yes`, the `mavenPublishing {...}` block and the `publish` toml alias were included; if
  `no`, both were omitted.
- **`sonar`**: `cloud`/`self-hosted`/`none` — if `cloud`/`self-hosted`, the `sonar {...}` blocks (in both modules)
  and the `sonarqube` toml alias were included with the resolved `sonar.organization`/`sonar.projectKey`/
  `sonar.host.url`; if `none`, note that this is expected when the project isn't open source unless the user
  explicitly chose it.
- **`built-in-kotlin`**/**`junit`**/**`coverage-tool`**/**`static-analysis`**: the resolved value for each, and
  which of them fall into Step 11's "unverified locally" list.
- Which toolchain versions (Step 4) came from a live lookup versus this skill's recorded fallback, and any version
  drift worth flagging (e.g. the `com.vanniktech.maven.publish` metadata quirk).

Then report which of Steps 5–7's files were created fresh, left untouched (fill-gaps/`mode: existing`), or replaced
(regenerate), whether `local.properties` was created or left alone, and whether Step 10's wrapper-binary fetch and
Step 11's two verification commands succeeded. If Step 1's existing files were replaced, explicitly list what could
have been lost — any dependency, Gradle task, or config option beyond what Steps 5–7's templates show — and tell
the user to check `git diff` for anything they need to re-add.

Finish with an explicit **Warn explicitly** block:

- **The user must review every generated file before building, committing, or publishing.** Confirm the license
  choice matches an actual `LICENSE` file (or that none is intended — suggest the `iru-check-license` skill to
  generate one and backfill source headers otherwise), that the inferred repository URL is correct, and that
  `./gradlew :lib:assembleDebug :app:assembleDebug` succeeds before relying on this scaffold.
- If `sonar: cloud` or `sonar: self-hosted` was chosen, a `SONAR_TOKEN` repository secret and an actual
  SonarCloud/SonarQube project matching `sonar.projectKey` still need to exist before `./gradlew :lib:sonar`
  (typically run from a generated CI workflow) will succeed — this skill only writes the `sonar {...}` block, it
  does not run a scan itself.
- If `publish: yes` was chosen, Maven Central publishing credentials and signing secrets still need to exist before
  `./gradlew :lib:publishToMavenCentral` (typically from that same generated CI) will succeed.
- No root `.gitignore` was written by this skill (only `lib/.gitignore`/`app/.gitignore`, both `/build`) —
  `local.properties`, `.gradle/`, `*.jks`, and other machine-local files should be ignored before the first commit;
  the `iru-setup-android-gitignore` skill covers this.
- Toolchain versions were resolved via run-time lookups (Step 4) and may already be stale by the time this report
  is read — especially Kotlin/AGP, which release frequently; re-check before a first real release.
- `junit: 5`, `coverage-tool: kover`, `static-analysis: lint+detekt+ktlint`, and `built-in-kotlin: yes` are
  unverified by this skill (Step 11) — spot-check whichever of them was chosen before trusting the generated build
  to actually work.
