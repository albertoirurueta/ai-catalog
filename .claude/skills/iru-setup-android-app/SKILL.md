---
name: iru-setup-android-app
description: Scaffold a new single-module Android application (Gradle Kotlin DSL, `com.android.application`) at
  the repository root — Gradle wrapper, root `build.gradle.kts`, `settings.gradle.kts`, `gradle.properties`,
  `gradle/libs.versions.toml`, and an `app/` module with `applicationId`/`namespace`, `versionCode`/`versionName`,
  `BUILD_NUMBER`/`BUILD_TIMESTAMP`/`GIT_COMMIT`/`GIT_BRANCH` `buildConfigField`s, a `signingConfigs { release {…} }`
  block that reads `SIGNING_STORE_FILE`/`SIGNING_STORE_PASSWORD`/`SIGNING_KEY_ALIAS`/`SIGNING_KEY_PASSWORD` from the
  environment and leaves the release build type unsigned (never failing configuration) when any is absent, a
  Compose-by-default UI (`ui: compose`, or `ui: views` for an AppCompat + ViewBinding variant), Robolectric + MockK
  + JUnit 4 unit-test tooling, an instrumented-test skeleton, and an inline `sonar { properties {…} } }` block
  (omitted when `sonar: none`). No Maven Central publishing block is ever generated — this skill is for
  distributable *applications*, not libraries (use `iru-setup-android-library` for the latter). Invoke as
  `/iru-setup-android-app`. Accepts pre-resolved inputs via `args` (`key: value` lines) — `application-id`,
  `namespace`, `app-name`, `min-sdk` (default `26`), `compile-sdk`/`target-sdk` (default the current stable API
  level), `version-name` (default `1.0.0`), `version-code` (default `1`), `license`, `developer-name`,
  `developer-email`, `organization-url`, `open-source`, `sonar` (+ `sonar-organization`/`sonar-project-key`/
  `sonar-host-url`), `ui` (`compose`/`views`), `distribution` (`none`/`internal`/`store`), `built-in-kotlin`
  (`no`/`yes`), `junit` (`4`/`5`), `coverage-tool` (`jacoco`/`kover`), `static-analysis`
  (`lint`/`lint+detekt+ktlint`), and `mode` (`new`/`existing`) — so an orchestrating skill can supply them without
  re-prompting; invoked stand-alone, it asks `open-source` first and derives the `sonar` question's default from
  that answer. `distribution: internal` wires the Firebase App Distribution Gradle plugin
  (`com.google.firebase.appdistribution`, `google-services.json` gitignored); `distribution: store` asks via
  `AskUserQuestion` whether to add the Gradle Play Publisher plugin (`com.github.triplet.play`) to the build or
  leave the upload to the workflow-level `r0adkll/upload-google-play@v1` action that `iru-setup-android-github-workflows`
  generates (default: leave it to the workflow). If `settings.gradle.kts`/`app/build.gradle.kts` already exist, asks
  the user whether to stop or regenerate (`mode: existing` skips straight to gap-fill: create only what's missing,
  never overwrite hand-edited application source). Every Gradle/Kotlin/plugin version is looked up at run time
  (Google Maven, Maven Central, the Gradle plugin portal, the Gradle releases API), falling back to the versions
  recorded in this file when a lookup fails. Templates are genericized from a real Android repository's actual
  toolchain and CI-verified `app/` module (see Step 5's header for the link) — no real repository/org/person names
  remain, only `<placeholder>` markers. Use whenever a new standalone Android application repository (or the
  application half of a mixed library+app repository) needs its Gradle project, signing, distribution, and test
  tooling bootstrapped from this house template, instead of hand-configuring each Gradle file.
model: haiku
---

# Setup Android App

Generate a complete, buildable Gradle Kotlin-DSL Android application project — wrapper, root build files, and a
single `app/` `com.android.application` module — from explicit example templates embedded in this skill (Step 5)
that are genericized from **https://github.com/albertoirurueta/irurueta-android-glutils**, a real Android
repository whose Gradle toolchain (root `build.gradle.kts`, `settings.gradle.kts`, `gradle.properties`,
`gradle/libs.versions.toml`, `gradle/wrapper/gradle-wrapper.properties`) and `app/` module this skill's templates
are drawn from line for line, with only project-identity fields turned into `<placeholder>` markers. This skill is
self-contained: it does not read or reference `iru-setup-android-library`'s files at run time, even though a
companion `iru-setup-android-library` skill draws its own toolchain templates from the same reference repository —
if a repository ends up with both a `lib/` and an `app/` module, run each skill once and reconcile the two
generated `settings.gradle.kts`/root `build.gradle.kts` files by hand (Step 8 calls this out).

Exceptions to "genericized": `com.irurueta:irurueta-android-test-utils` (Gradle catalog alias `irurueta-test-utils`)
is kept as a real third-party Robolectric/MockK test-helper dependency, exactly as the reference repository uses
it — it is not a placeholder.

This skill produces only the `app/` module. It never writes a `mavenPublishing {}` block, a `sign`/publish CI
profile, or anything that assumes the output is redistributed as a library artifact — release builds are meant to
be installed on a device or uploaded to a store, not published to Maven Central.

## Step 0 — Resolve inputs

This skill can be invoked stand-alone (`/iru-setup-android-app`) or as a step inside another skill (e.g. a future
`iru-setup-android-app-repository` or the catalog's `iru-setup-repository` front door), which resolves these same
inputs itself and passes them through `args` as `key: value` lines, one per line, e.g.:

```
application-id: com.example.myapp
namespace: com.example.myapp
app-name: My App
min-sdk: 26
compile-sdk: 36
target-sdk: 36
version-name: 1.0.0
version-code: 1
license: Apache License 2.0
developer-name: Jane Doe
developer-email: jane@example.com
organization-url: https://github.com/example-org
open-source: yes
sonar: cloud
sonar-organization: example-org-github
sonar-project-key: example-org_my-app
sonar-host-url: https://sonarcloud.io
ui: compose
distribution: store
built-in-kotlin: no
junit: 4
coverage-tool: jacoco
static-analysis: lint
mode: new
```

Parse any such lines from `args` now. Every field found here is resolved — skip asking about it in Step 2. Only
fields genuinely missing from `args` still need a question. If `args` is absent or doesn't look like this format,
treat everything as unset and ask normally.

Recognized keys: `application-id`, `namespace` (defaults to `application-id` if omitted), `app-name`, `min-sdk`
(default `26`), `compile-sdk`/`target-sdk` (default: the current stable Android API level, looked up in Step 4),
`version-name` (default `1.0.0`), `version-code` (default `1`), `license`, `developer-name`, `developer-email`,
`organization-url`, `open-source` (`yes`/`no`), `sonar` (`cloud`/`self-hosted`/`none`) plus, only when `sonar` is
`cloud` or `self-hosted`, `sonar-organization`/`sonar-project-key`/`sonar-host-url`, `ui` (`compose`/`views`),
`distribution` (`none`/`internal`/`store`), `built-in-kotlin` (`no`/`yes`), `junit` (`4`/`5`), `coverage-tool`
(`jacoco`/`kover`), `static-analysis` (`lint`/`lint+detekt+ktlint`), and `mode` (`new`/`existing`).

`mode: existing` is this catalog's shared signal (set by a front door that already ran `iru-explore` and knows this
is an established repository) that Step 1 should skip its stop-or-regenerate question entirely and go straight to
gap-fill: create only whatever files from Step 5 are genuinely missing, and leave every file that already exists
untouched. `mode: new` or an unset `mode` follows Step 1's normal survey instead.

## Step 1 — Survey the repository

Check for `settings.gradle.kts` and `app/build.gradle.kts` at the repository root.

- **Neither exists**: skip straight to Step 2. There is nothing to preserve.
- **`app/build.gradle.kts` exists and applies `com.android.application`**: this skill (or a hand-written
  equivalent) already owns this module. Warn the user it will be regenerated, then:
  - **`mode: existing` was resolved in Step 0**: skip the question below — go straight to **gap-fill**: create
    only the files from Step 5 that are genuinely missing (never touch `MainActivity.kt`/existing composables/
    `AndroidManifest.xml`'s `<application>` children beyond the one `<activity>` this skill adds/existing
    resources); note in Step 8's report which files were left alone because they already existed.
  - **Otherwise**: use `AskUserQuestion` with two options:
    - **Stop** — leave everything untouched. Report this and end here.
    - **Update** — regenerate the toolchain files (`build.gradle.kts` root, `settings.gradle.kts`,
      `gradle.properties`, `gradle/libs.versions.toml`, `app/build.gradle.kts`) from this skill's templates, but
      never touch `app/src/main/java/**` application source beyond the placeholder files this skill created
      originally (detect by exact content match against Step 5's templates before overwriting any Kotlin file).
      Tell the user up front that regenerating `app/build.gradle.kts` replaces the whole file — any dependency,
      flavor, or build-type customization beyond what Step 5 shows will be lost unless re-added afterward (call
      this out again in Step 8).
- **`settings.gradle.kts` exists but has no `app` module applying `com.android.application`, or `app/build.gradle.kts`
  exists and applies `com.android.library`**: this is not this skill's scaffold (a library-only or differently
  laid out project). Warn the user explicitly and ask whether to add an `app` module alongside the existing one, or
  stop. Don't attempt to convert an existing module.

## Step 2 — Collect the required inputs

For any field Step 0 already resolved from `args`, use that value directly and don't ask about it again. For
everything else, ask the user directly (plain conversation, pre-filling defaults found in Step 1 if updating an
existing scaffold):

- **application-id** — reverse-DNS application id, e.g. `com.example.myapp` (written to `defaultConfig.applicationId`
  and used to derive the Kotlin package path under `app/src/main/java/`).
- **namespace** — the module's Kotlin/resource namespace (`android.namespace`); defaults to `application-id` if the
  user gives none — offer that as the default rather than asking open-endedly. (`namespace` and `applicationId` are
  independent in modern AGP — a namespace change alone never changes what's installed on a device — but keeping
  them equal is the common case and this skill's default.)
- **app-name** — the display name shown under the launcher icon (`strings.xml`'s `app_name`).
- **min-sdk** — default `26` (Android 8.0). `26` is also the API level adaptive launcher icons were introduced at,
  which is why Step 5's icon template needs no legacy raster fallback (see that step's note).
- **compile-sdk**/**target-sdk** — default to the current stable Android API level, looked up in Step 4; offer that
  looked-up value as the default rather than asking open-endedly. `target-sdk` defaults to the same value as
  `compile-sdk` unless the user wants to target an older platform behavior deliberately.
- **version-name** — default `1.0.0` (Android apps don't use Maven's `-SNAPSHOT` convention; `iru-android-bump-version`
  is the skill that later rewrites this).
- **version-code** — default `1` (a plain monotonically increasing integer, not derived from `version-name`).
- **Developer name**, **developer email**, **organizationUrl** — recorded in Step 8's report only; unlike
  `iru-setup-android-library`, no `pom`/`mavenPublishing` block exists here to put them in.

Then, unless Step 0 already resolved a `license` value from `args`, ask about the **license** with
`AskUserQuestion` (mirrors this catalog's other setup skills):

- MIT License (recommended for app source not meant for redistribution as a library)
- Apache License 2.0
- No license (proprietary / all rights reserved)
- Other — ask for the license's display name and URL directly afterward

If a license is chosen (anything but "No license"), remind the user in Step 8 to also add a matching `LICENSE`
file at the repository root if one doesn't exist yet — `iru-check-license` can verify/backfill source headers
against it once it's there.

Then, unless Step 0 already resolved them, ask about **ui**, **built-in-kotlin**, **junit**, **coverage-tool**, and
**static-analysis** as bounded choices (`AskUserQuestion`, max four options each):

- **ui** — `compose` (recommended default; Jetpack Compose Material 3, matches this catalog's other app-flavor
  skills like `iru-setup-react-native-app`) or `views` (classic `AppCompatActivity` + XML layout + ViewBinding, no
  Compose runtime at all — pick this only when the user explicitly wants the older View system, e.g. to match an
  existing design-system investment). Gates which of Step 5's `MainActivity`/layout templates get written, and
  whether `kotlin-compose`/`androidx-compose-bom`/`androidx-material3` are in the version catalog at all.
- **built-in-kotlin** — `no` (default, matches the reference project's `android.builtInKotlin=false`) or `yes` (opts
  into AGP's built-in Kotlin compilation support instead of the separate `org.jetbrains.kotlin.android` plugin —
  still experimental as of AGP 9.x; only recommend `yes` if the user explicitly wants to try it).
- **junit** — `4` (default; Robolectric + MockK + JUnit 4, exactly as the reference project) or `5` (adds the
  `de.mannodermaus.android-junit5` plugin so `app/src/test` can also use JUnit 5 Jupiter alongside the JUnit-4-only
  Robolectric runner — see Step 5's opt-ins).
- **coverage-tool** — `jacoco` (default; AGP's built-in `create<Variant>UnitTestCoverageReport` task, no extra
  plugin) or `kover` (adds `org.jetbrains.kotlinx.kover` for a Kotlin-native coverage report/verification DSL
  instead).
- **static-analysis** — `lint` (default; Android Lint only, already built into AGP) or `lint+detekt+ktlint` (adds
  Detekt for Kotlin static analysis and Spotless-driven ktlint formatting — see Step 5's opt-ins).

Then resolve `open-source`, `sonar`, and `distribution` — skip any of the three Step 0 already resolved from
`args`. When invoked stand-alone with none of them pre-resolved, ask `open-source` *first* (`AskUserQuestion`:
yes/no) and derive the recommended default for `sonar` from that answer, per this catalog's shared convention:

- **open-source** — is this repository open source? Yes / No.
- **sonar** — whether to wire up a SonarQube/SonarCloud scan (this house pattern runs it via the `org.sonarqube`
  Gradle plugin, invoked as `./gradlew :app:sonar` — typically from the CI workflow `iru-setup-android-github-workflows`
  generates, so it's worth setting up here even if that workflow comes later). Recommend **SonarCloud** (`cloud`)
  when open-source is Yes; when not open source, state that SonarCloud is free only for open-source projects (a
  paid plan is required otherwise) and recommend **None** (`none`), offering **self-hosted SonarQube** as the
  second option:
  - `cloud` — ask for the `sonar.organization` key, offering `<owner>-github` (the owner parsed in Step 3) as the
    suggested default. Default `sonar.projectKey` to `<owner>_<repo>` and `sonar.host.url` to
    `https://sonarcloud.io`, confirming both with the user rather than assuming silently.
  - `self-hosted` — ask for `sonar.host.url` directly (no sensible default), plus `sonar.organization` only if that
    server has organizations enabled, and `sonar.projectKey`.
  - `none` — skip the entire `sonar { properties {…} } }` block and the `org.sonarqube` plugin (Step 5/6).
- **distribution** — `none`/`internal`/`store`:
  - `none` — release builds are for local install/manual QA only. No distribution plugin is added; `signingConfigs`
    is still written (Step 5) so a signed release build remains possible whenever the signing secrets exist, but
    nothing uploads it anywhere.
  - `internal` — adds the **Firebase App Distribution** Gradle plugin (`com.google.firebase.appdistribution`,
    version looked up in Step 4) to `app/build.gradle.kts`, so `./gradlew :app:appDistributionUploadRelease` can
    push a build straight to Firebase's tester groups. This needs a Firebase project: `google-services.json` (the
    Firebase config file, unique per Firebase project) is referenced but **never written by this skill** — it must
    be downloaded from the Firebase console and placed at `app/google-services.json`, and Step 5 gitignores it (it
    contains project-specific API keys/identifiers that shouldn't be committed). Step 8 flags the `FIREBASE_APP_ID`
    and a Firebase service-account credential (JSON key, typically stored as a CI secret and referenced via
    `--service-credentials-file` or the `FIREBASE_TOKEN`/`GOOGLE_APPLICATION_CREDENTIALS` env var) that a CI-driven
    upload will need.
  - `store` — full Google Play production submission is intended. Ask via `AskUserQuestion` **how** the upload
    should happen (bounded choice, two options):
    - **Workflow-level action** (recommended default) — leave `app/build.gradle.kts` alone; the actual
      `r0adkll/upload-google-play@v1` GitHub Actions step is generated later by
      `iru-setup-android-github-workflows` when it renders the release workflow for `distribution: store`. This
      skill only records the choice (Step 8) so that skill doesn't have to ask again.
    - **Gradle Play Publisher plugin** — adds `com.github.triplet.play` (`com.github.triplet.play` id, version
      looked up in Step 4) to `app/build.gradle.kts` with a minimal `play { serviceAccountCredentials.set(file(<path>)) }`
      block (Step 5), so `./gradlew :app:publishBundle` can upload directly from any machine/CI runner that has the
      service-account JSON, without depending on the `upload-google-play` Action at all. Either choice needs the
      same underlying Google Play service-account JSON key — this skill never collects or stores it, only names it
      in Step 8's report.

## Step 3 — Infer repository information

Don't ask for these — derive them from the current repository, the same way `iru-setup-java-library` and
`iru-setup-react-native-app` do:

- **Owner/repo and host**: parse `git remote get-url origin` (handles both `git@host:owner/repo.git` and
  `https://host/owner/repo.git` forms). Used for Step 2's `sonar.organization`/`sonar.projectKey` defaults and
  `settings.gradle.kts`'s `rootProject.name`. If there's no `origin` remote yet, ask the user directly instead of
  leaving these blank.

## Step 4 — Look up toolchain versions

Every version below must be looked up at run time; fall back to the value in this table (what this skill's author
actually observed in September 2026) only when the lookup fails, and say so explicitly in Step 8's report.

| Component | Lookup | September 2026 fallback |
|---|---|---|
| Gradle | `https://services.gradle.org/versions/current` (`"version"`/`"checksum"` fields — `"checksum"` in that same JSON response is already the binary distribution's SHA-256, no second fetch needed; `"checksumUrl"` also works) | `9.7.1`, sha256 `acd53f1edaf02f1a8ff99879f8a34b302661a057d9b063ae9e35b552f804d20a` — **live-confirmed during this skill's verification**, and used as-is against AGP `9.0.1` below with no compatibility issue |
| Android Gradle Plugin (AGP) | `https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/maven-metadata.xml` (read the highest non-`-alpha`/`-beta`/`-rc` `<version>` entry — this AGP artifact's own metadata, not AAPT2's, and **not** its `<latest>`/`<release>` tags, which pointed at an alpha during this verification) | `9.0.1` — the reference project's own verified-working version; a live lookup during this verification found `9.4.0` already stable, but the fallback here is deliberately the older, *known-compatible-with-Kotlin-2.3.10* version actually built and tested for this skill (see the compatibility note below the table) |
| Kotlin | `https://repo1.maven.org/maven2/org/jetbrains/kotlin/kotlin-gradle-plugin/maven-metadata.xml` — **prefer this over `search.maven.org`'s `solrsearch` API**, confirmed stale below | `2.3.10` — likewise the version actually verified against AGP `9.0.1`/Compose BOM `2026.02.01` together, not the bare current release |
| Dokka | `https://repo1.maven.org/maven2/org/jetbrains/dokka/dokka-gradle-plugin/maven-metadata.xml` — same staleness caveat as Kotlin above | `2.1.0` |
| SonarQube Gradle plugin | `https://plugins.gradle.org/m2/org/sonarqube/org.sonarqube.gradle.plugin/maven-metadata.xml` | `7.2.3.7755` |
| JUnit 4 | `https://search.maven.org/solrsearch/select?q=g:junit+AND+a:junit&rows=1&wt=json` | `4.13.2` |
| AndroidX Test `junit`/`junit-ktx` | `https://dl.google.com/dl/android/maven2/androidx/test/ext/junit/group-index.xml` | `1.3.0` |
| AndroidX Espresso `espresso-core` | `https://dl.google.com/dl/android/maven2/androidx/test/espresso/espresso-core/group-index.xml` | `3.7.0` |
| AndroidX Compose BOM (only `ui: compose`) | `https://dl.google.com/dl/android/maven2/androidx/compose/compose-bom/group-index.xml` | `2026.02.01` |
| AndroidX `activity-compose` (only `ui: compose`; **not** covered by the Compose BOM, needs its own version) | `https://dl.google.com/dl/android/maven2/androidx/activity/group-index.xml` | `1.13.0` |
| `com.google.android.material:material` | `https://dl.google.com/dl/android/maven2/com/google/android/material/material/group-index.xml` | `1.13.0` |
| AndroidX Test `core-ktx` | `https://dl.google.com/dl/android/maven2/androidx/test/core/group-index.xml` | `1.7.0` |
| MockK (`mockk-android`) | `https://search.maven.org/solrsearch/select?q=g:io.mockk+AND+a:mockk-android&rows=1&wt=json` | `1.14.9` |
| Robolectric | `https://search.maven.org/solrsearch/select?q=g:org.robolectric+AND+a:robolectric&rows=1&wt=json` | `4.16.1` |
| `kotlin-reflect` | same as the Kotlin row above (kept in lockstep) | `2.3.10` |
| `com.irurueta:irurueta-android-test-utils` | `https://search.maven.org/solrsearch/select?q=g:com.irurueta+AND+a:irurueta-android-test-utils&rows=1&wt=json` | `1.3.2` |
| Current stable Android API level (`compile-sdk`/`target-sdk` default) | `sdkmanager --list` on the local SDK, or https://apilevels.com | `36` (Android 16) |
| Detekt (opt-in) | `https://plugins.gradle.org/m2/io/gitlab/arturbosch/detekt/io.gitlab.arturbosch.detekt.gradle.plugin/maven-metadata.xml` | `1.23.8` — **unverified locally**, confirm at run time |
| Spotless (opt-in) | `https://plugins.gradle.org/m2/com/diffplug/spotless/com.diffplug.spotless.gradle.plugin/maven-metadata.xml` | `7.2.1` — **unverified locally**, confirm at run time |
| Kover (opt-in, `coverage-tool: kover`) | `https://plugins.gradle.org/m2/org/jetbrains/kotlinx/kover/org.jetbrains.kotlinx.kover.gradle.plugin/maven-metadata.xml` | `0.9.2` — **unverified locally**, confirm at run time |
| `de.mannodermaus.android-junit5` (opt-in, `junit: 5`) | `https://plugins.gradle.org/m2/de/mannodermaus/android-junit5/de.mannodermaus.android-junit5.gradle.plugin/maven-metadata.xml` | `2.0.0` — **unverified locally**, confirm at run time |
| Firebase App Distribution plugin (opt-in, `distribution: internal`) | `https://plugins.gradle.org/m2/com/google/firebase/appdistribution/com.google.firebase.appdistribution.gradle.plugin/maven-metadata.xml` | `5.1.1` — **unverified locally**, confirm at run time |
| Gradle Play Publisher plugin (opt-in, `distribution: store` + plugin choice) | `https://plugins.gradle.org/m2/com/github/triplet/play/com.github.triplet.play.gradle.plugin/maven-metadata.xml` | `3.11.1` — **unverified locally**, confirm at run time |

**Compatibility over bare "latest", confirmed the hard way while verifying this skill:** looking up every artifact's
own individual latest version and combining them all is *not* the same as a combination someone has actually built.
This skill's fallbacks (AGP/Kotlin/Dokka/Compose BOM/etc.) are the reference project's own real, CI-verified
combination, not each package's independently-latest release — prefer that same discipline when a live lookup
succeeds too: resolve AGP/Kotlin/the Compose BOM together and sanity-check `./gradlew :app:assembleDebug` once with
the new versions before trusting them, rather than bumping each in isolation. `search.maven.org`'s `solrsearch`
API returned a stale `latestVersion` for both `kotlin-gradle-plugin` (`2.2.0`) and `dokka-gradle-plugin` (`2.0.0`)
during this verification, each already superseded by a newer stable release visible in Maven Central's own
`maven-metadata.xml` for the same artifact — treat `solrsearch` results as a hint, not ground truth, and prefer a
direct `maven-metadata.xml`/group-index fetch when precision matters (as it does for Kotlin/AGP compatibility).

## Step 5 — Reference templates

These templates are genericized from **https://github.com/albertoirurueta/irurueta-android-glutils**'s actual
toolchain files and `app/` module — kept as close to verbatim as possible, with only project-identity fields turned
into `<placeholder>` markers. Substitute using Steps 2–4; keep everything else exactly as shown unless a step below
says an opt-in changes it.

### `<placeholder>` resolution table

| Placeholder | Source |
|---|---|
| `<project-name>` | `settings.gradle.kts`'s `rootProject.name` — the repository name from Step 3 |
| `<application-id>` | Step 2 |
| `<namespace>` | Step 2 |
| `<app-name>` | Step 2 |
| `<min-sdk>` / `<compile-sdk>` / `<target-sdk>` | Step 2/4 |
| `<version-name>` / `<version-code>` | Step 2 |
| `<gradle-version>` / `<gradle-distribution-sha256>` | Step 4 |
| `<agp-version>` / `<kotlin-version>` / `<dokka-version>` / `<sonarqube-plugin-version>` / … | Step 4 |
| `<sonar-organization>` / `<sonar-project-key>` / `<sonar-host-url>` | Step 2 |
| `<owner>` / `<repo>` | Step 3 |

### Gradle wrapper — `gradle/wrapper/gradle-wrapper.properties`

```properties
distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\://services.gradle.org/distributions/gradle-<gradle-version>-bin.zip
distributionSha256Sum=<gradle-distribution-sha256>
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
```

The reference project's own `gradle-wrapper.properties` predates `distributionSha256Sum` being set (it has none) —
this skill adds it anyway, since Gradle has supported wrapper checksum verification for years and it's a cheap
supply-chain hardening with no downside. `gradlew`/`gradlew.bat`/`gradle/wrapper/gradle-wrapper.jar` themselves are
binaries/scripts unfit for a Markdown template — obtain them one of two ways (Step 6 says which to try first):

1. If a local Gradle install exists (`gradle -v` succeeds), run `gradle wrapper --gradle-version <gradle-version>`
   at the project root, then overwrite the generated `gradle-wrapper.properties` with the block above (it adds the
   `distributionSha256Sum` line `gradle wrapper` alone doesn't add without `--gradle-distribution-sha256-sum`).
2. Otherwise, fetch the three files directly from the Gradle GitHub repository's matching tag:
   `https://raw.githubusercontent.com/gradle/gradle/v<gradle-version>/gradlew`,
   `.../gradlew.bat`, and `.../gradle/wrapper/gradle-wrapper.jar` (binary — fetch with `curl -fsSL -o`, not a text
   read), then `chmod +x gradlew`.

### Root `build.gradle.kts`

```kotlin
// Top-level build file where you can add configuration options common to all sub-projects/modules.
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.android) apply false
    // Omit the next line entirely when `ui: views` was chosen in Step 2.
    alias(libs.plugins.kotlin.compose) apply false
}

project.delete {
    delete(rootProject.layout.buildDirectory)
}
```

The trailing `project.delete { … }` block is copied verbatim from the reference project — it runs at Gradle
*configuration* time (not as a `clean` task), deleting the root project's own (normally-empty) build directory on
every invocation. Harmless and intentional in the source repository; keep it for fidelity, but call it out in Step
8 since it surprises anyone expecting `build.gradle.kts` to only declare plugins.

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

rootProject.name = "<project-name>"
include(":app")
```

`FAIL_ON_PROJECT_REPOS` matches the reference project: it forbids any module-level `build.gradle.kts` from
declaring its own `repositories {}` block, forcing every dependency to resolve through this single
`dependencyResolutionManagement` block instead — Step 5's `app/build.gradle.kts` template relies on this and never
declares repositories itself.

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
android.newDsl=false
```

`<built-in-kotlin-flag>` is `false` unless Step 2's `built-in-kotlin` answer was `yes`. `android.newDsl` stays
`false` regardless — it gates an unrelated, still-experimental AGP DSL rewrite the reference project also opts out
of. Copied verbatim from the reference project's `gradle.properties` otherwise (no real repository/org names appear
in this file, so nothing else needed genericizing).

### `gradle/libs.versions.toml`

```toml
[versions]
agp = "<agp-version>"
kotlin = "<kotlin-version>"
junit = "<junit-version>"
junitVersion = "<androidx-junit-version>"
espressoCore = "<espresso-version>"
material = "<material-version>"
dokka = "<dokka-version>"
sonarqube = "<sonarqube-plugin-version>"
mockk = "<mockk-version>"
testCoreKtx = "<test-core-ktx-version>"
robolectric = "<robolectric-version>"
kotlinReflect = "<kotlin-version>"
iruruetaTestUtils = "<irurueta-test-utils-version>"
# Only when `ui: compose` (Step 2):
composeBom = "<compose-bom-version>"
activityCompose = "<activity-compose-version>"
```

```toml
[libraries]
junit = { group = "junit", name = "junit", version.ref = "junit" }
androidx-junit = { group = "androidx.test.ext", name = "junit", version.ref = "junitVersion" }
androidx-espresso-core = { group = "androidx.test.espresso", name = "espresso-core", version.ref = "espressoCore" }
androidx-test-core-ktx = { group = "androidx.test", name = "core-ktx", version.ref = "testCoreKtx" }
androidx-test-ext-junit-ktx = { group = "androidx.test.ext", name = "junit-ktx", version.ref = "junitVersion" }
material = { group = "com.google.android.material", name = "material", version.ref = "material" }
mockk-android = { group = "io.mockk", name = "mockk-android", version.ref = "mockk" }
robolectric = { group = "org.robolectric", name = "robolectric", version.ref = "robolectric" }
kotlin-reflect = { group = "org.jetbrains.kotlin", name = "kotlin-reflect", version.ref = "kotlinReflect" }
irurueta-test-utils = { group = "com.irurueta", name = "irurueta-android-test-utils", version.ref = "iruruetaTestUtils" }
# Only when `ui: compose`:
androidx-compose-bom = { group = "androidx.compose", name = "compose-bom", version.ref = "composeBom" }
androidx-material3 = { group = "androidx.compose.material3", name = "material3" }
androidx-activity-compose = { group = "androidx.activity", name = "activity-compose", version.ref = "activityCompose" }
androidx-ui-tooling-preview = { group = "androidx.compose.ui", name = "ui-tooling-preview" }
```

**Both of the last two are required, not optional — confirmed while verifying this skill:** the Compose BOM
(`platform(libs.androidx.compose.bom)`) only pins versions; it doesn't pull either artifact in transitively via
`androidx.compose.material3:material3`. Omitting `androidx.activity:activity-compose` fails
`MainActivity.kt`'s `setContent { }` call with `Unresolved reference 'setContent'`; omitting
`androidx.compose.ui:ui-tooling-preview` fails the `@Preview` composable with `Unresolved reference 'tooling'` /
`Unresolved reference 'Preview'`. `androidx.activity:activity-compose` isn't part of the `androidx.compose` BOM
group at all, so it needs its own version (Step 4) even though `ui-tooling-preview` is covered by the BOM's
version pin once the artifact itself is declared.

```toml
[plugins]
android-application = { id = "com.android.application", version.ref = "agp" }
kotlin-android = { id = "org.jetbrains.kotlin.android", version.ref = "kotlin" }
dokka = { id = "org.jetbrains.dokka", version.ref = "dokka" }
sonarqube = { id = "org.sonarqube", version.ref = "sonarqube" }
# Only when `ui: compose`:
kotlin-compose = { id = "org.jetbrains.kotlin.plugin.compose", version.ref = "kotlin" }
```

Aliases match the reference project's naming exactly (`android-application`, `kotlin-android`, `kotlin-compose`,
`dokka`, `sonarqube`, plus the library dependency names) so a repository that later also runs
`iru-setup-android-library` gets a version catalog with compatible alias spelling if the two files are merged by
hand. No `android-library` or `publish` alias/plugin is written here — this skill never scaffolds a library module
or a publishing block. Step 5's opt-ins (Detekt/Spotless/Kover/JUnit 5) each add their own `[versions]`/`[plugins]`
entries — see the "Opt-ins" subsection below.

### `app/build.gradle.kts`

```kotlin
import org.jetbrains.kotlin.gradle.dsl.JvmTarget
import java.text.SimpleDateFormat
import java.util.Date

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    // Omit when `ui: views`:
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.dokka)
    // Omit the whole line when `sonar: none`:
    alias(libs.plugins.sonarqube)
}

// Read once, at configuration time — used both for signingConfigs below and Step 8's report.
val signingStoreFile: String? = System.getenv("SIGNING_STORE_FILE")
val signingStorePassword: String? = System.getenv("SIGNING_STORE_PASSWORD")
val signingKeyAlias: String? = System.getenv("SIGNING_KEY_ALIAS")
val signingKeyPassword: String? = System.getenv("SIGNING_KEY_PASSWORD")
val hasReleaseSigning: Boolean =
    !signingStoreFile.isNullOrBlank() &&
        !signingStorePassword.isNullOrBlank() &&
        !signingKeyAlias.isNullOrBlank() &&
        !signingKeyPassword.isNullOrBlank()

android {
    namespace = "<namespace>"
    compileSdk = <compile-sdk>

    defaultConfig {
        applicationId = "<application-id>"
        minSdk = <min-sdk>
        targetSdk = <target-sdk>
        versionCode = <version-code>
        versionName = "<version-name>"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        val buildNumber = System.getenv("BUILD_NUMBER") ?: ""
        buildConfigField("String", "BUILD_NUMBER", "\"$buildNumber\"")
        val dateFormatter = SimpleDateFormat("yyyy-MM-dd HH:mm:ss")
        buildConfigField("String", "BUILD_TIMESTAMP", "\"" + dateFormatter.format(Date()) + "\"")
        val gitCommit = System.getenv("GIT_COMMIT")
        buildConfigField("String", "GIT_COMMIT", "\"$gitCommit\"")
        val gitBranch = System.getenv("GIT_BRANCH")
        buildConfigField("String", "GIT_BRANCH", "\"$gitBranch\"")

        val apkPrefixLabels = listOf("<project-name>", versionName, buildNumber)
        base.archivesName = apkPrefixLabels.filter { it != "" }.joinToString("-")
    }

    // Never references signingConfigs["release"] when it wasn't created below — an app can always be configured
    // and `assembleDebug`'d even with zero signing secrets present (e.g. a fresh clone, or a contributor's laptop).
    signingConfigs {
        if (hasReleaseSigning) {
            create("release") {
                storeFile = file(signingStoreFile!!)
                storePassword = signingStorePassword
                keyAlias = signingKeyAlias
                keyPassword = signingKeyPassword
            }
        }
    }

    buildTypes {
        debug {
            enableUnitTestCoverage = true
        }
        release {
            isMinifyEnabled = false
            if (hasReleaseSigning) {
                signingConfig = signingConfigs.getByName("release")
            }
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
        // Only when `ui: compose`:
        compose = true
        // Only when `ui: views`:
        viewBinding = true
    }
}
kotlin {
    compilerOptions {
        jvmTarget = JvmTarget.JVM_17
    }
}

// Omit this entire block when `sonar: none`.
sonar {
    properties {
        property("sonar.scanner.skipJreProvisioning", true)
        property("sonar.projectKey", "<sonar-project-key>")
        property("sonar.projectName", "<project-name>")
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

        val androidJar = project.android.sdkDirectory.path + "/platforms/android-<compile-sdk>/android.jar"
        property("sonar.libraries", androidJar)
        property("sonar.java.libraries", androidJar)
        property("sonar.java.test.libraries", androidJar)
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
    // Only when `ui: compose`:
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.material3)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.ui.tooling.preview)

    testImplementation(libs.junit)
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
    // Only when `ui: compose`:
    androidTestImplementation(platform(libs.androidx.compose.bom))
}
```

**`signingConfigs` safety, spelled out:** `hasReleaseSigning` is computed once, from four env vars, before `android
{}` runs. `signingConfigs { if (hasReleaseSigning) { create("release") { … } } }` means the `"release"`
`SigningConfig` object simply doesn't exist unless all four are present — and `buildTypes { release { if
(hasReleaseSigning) { signingConfig = signingConfigs.getByName("release") } } }` only looks it up in that same
case, so `getByName` never throws `UnknownDomainObjectException`. The net effect: `./gradlew :app:assembleDebug`
never needs signing secrets at all (debug builds use Android's auto-generated debug keystore, untouched by this
config); `./gradlew :app:assembleRelease`/`:app:bundleRelease` succeed with **no** env vars set too, producing an
**unsigned** release APK/AAB (Gradle only warns, it doesn't fail) — confirmed in Step 7's verification. Set all
four (`SIGNING_STORE_FILE` as an absolute or project-relative path to a `.jks`/`.keystore` file,
`SIGNING_STORE_PASSWORD`, `SIGNING_KEY_ALIAS`, `SIGNING_KEY_PASSWORD`) to get a signed release build — this
skill never generates or stores a keystore itself (Step 8 repeats this).

**`bundleRelease`/`assembleRelease` guidance:**

- `./gradlew :app:assembleRelease` — release APK, at `app/build/outputs/apk/release/`. Fine for direct install/
  Firebase App Distribution; **not** what Google Play accepts for new app submissions.
- `./gradlew :app:bundleRelease` — release Android App Bundle (`.aab`), at `app/build/outputs/bundle/release/`.
  This is what Google Play Console (and both the `r0adkll/upload-google-play@v1` Action and the Gradle Play
  Publisher plugin's `publishBundle` task) expect.

**`distribution: internal` addition** — insert into the `plugins {}` block:

```kotlin
    alias(libs.plugins.firebase.appdistribution)
```

and add to `[versions]`/`[plugins]` in `gradle/libs.versions.toml`:

```toml
firebaseAppdistribution = "<firebase-appdistribution-plugin-version>"
# [plugins]
firebase-appdistribution = { id = "com.google.firebase.appdistribution", version.ref = "firebaseAppdistribution" }
```

No further Gradle DSL block is required for a minimal setup — the plugin reads `app/google-services.json` (never
written by this skill; see Step 2) and defaults `appDistributionUploadRelease` off the `release` build type. Add a
`firebaseAppDistribution { releaseNotesFile = "..." ; groups = "..." }` block later by hand if release notes/tester
groups should be fixed rather than passed via `-P` properties.

**`distribution: store` + Gradle Play Publisher plugin chosen** — insert into `plugins {}`:

```kotlin
    alias(libs.plugins.triplet.play)
```

and add to `gradle/libs.versions.toml`:

```toml
tripletPlay = "<gradle-play-publisher-plugin-version>"
# [plugins]
triplet-play = { id = "com.github.triplet.play", version.ref = "tripletPlay" }
```

then, after the `dependencies {}` block:

```kotlin
play {
    serviceAccountCredentials.set(file("<path-to-service-account-json>"))
    defaultToAppBundles.set(true)
}
```

`<path-to-service-account-json>` is never a path this skill resolves or downloads — leave it as a placeholder
comment pointing at wherever CI decodes the `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` secret to (Step 8 flags this). If
the user instead chose the workflow-level action, skip this whole addition — `app/build.gradle.kts` stays exactly
as the base template above.

### `app/proguard-rules.pro`

```proguard
# Add project specific ProGuard rules here.
# You can control the set of applied configuration files using the
# proguardFiles setting in build.gradle.kts.
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

### `app/src/main/AndroidManifest.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:theme="@style/Theme.App">
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

**No `package="<application-id>"` attribute on `<manifest>`, deliberately** — confirmed while verifying this skill:
current AGP no longer reads the application id/namespace from the manifest's `package` attribute at all; leaving
one in (as the reference project's manifest still does, predating this AGP behavior) produces a build-time warning
("Setting the namespace via the package attribute in the source AndroidManifest.xml is no longer supported, and the
value is ignored") for every build. `android.namespace`/`defaultConfig.applicationId` in `app/build.gradle.kts`
above are the only things that matter now — drop the attribute entirely rather than carry a dead, warning-generating
line forward from the reference.

`android:theme="@style/Theme.App"` is a placeholder style name kept short and generic (the reference project's own
manifest points at a theme name derived from its own repository name) — Step 5's theme templates below define
exactly `Theme.App` so the two always match; rename both together if the user wants a different style name.

### `app/src/main/res/**` — theme, colors, strings, launcher icon

`values/colors.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="primary">#FF6200EE</color>
    <color name="primary_variant">#FF3700B3</color>
    <color name="secondary">#FF03DAC5</color>
    <color name="secondary_variant">#FF018786</color>
    <color name="on_primary">#FFFFFFFF</color>
    <color name="on_secondary">#FF000000</color>
</resources>
```

`values/strings.xml`:

```xml
<resources>
    <string name="app_name"><app-name></string>
</resources>
```

**`ui: views`** — `values/themes.xml`:

```xml
<resources>
    <style name="Theme.App" parent="Theme.MaterialComponents.DayNight.DarkActionBar">
        <item name="colorPrimary">@color/primary</item>
        <item name="colorPrimaryVariant">@color/primary_variant</item>
        <item name="colorOnPrimary">@color/on_primary</item>
        <item name="colorSecondary">@color/secondary</item>
        <item name="colorSecondaryVariant">@color/secondary_variant</item>
        <item name="colorOnSecondary">@color/on_secondary</item>
        <item name="android:statusBarColor">?attr/colorPrimaryVariant</item>
    </style>
</resources>
```

(and the same block, with darker color values swapped in, under `values-night/themes.xml` — mirrors the reference
project's day/night pair exactly.)

**`ui: compose`** — no XML theme is required; the manifest's `android:theme="@style/Theme.App"` still needs *some*
style to resolve at inflation time before Compose takes over, so write a minimal one:

```xml
<resources>
    <style name="Theme.App" parent="Theme.Material3.DayNight.NoActionBar" />
</resources>
```

(no `values-night` variant needed — `DayNight` already switches automatically) and a Kotlin Compose theme wrapper,
`app/src/main/java/<package-path>/ui/theme/Theme.kt`:

```kotlin
package <namespace>.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = Color(0xFF6200EE),
    secondary = Color(0xFF03DAC5),
)
private val DarkColors = darkColorScheme(
    primary = Color(0xFFBB86FC),
    secondary = Color(0xFF03DAC5),
)

@Composable
fun AppTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    val colorScheme = if (darkTheme) DarkColors else LightColors
    MaterialTheme(colorScheme = colorScheme, content = content)
}
```

**Launcher icon (both `ui` variants)** — `mipmap-anydpi-v26/ic_launcher.xml` and `ic_launcher_round.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background" />
    <foreground android:drawable="@drawable/ic_launcher_foreground" />
</adaptive-icon>
```

`drawable/ic_launcher_background.xml` (flat brand-color fill):

```xml
<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="@color/primary"
        android:pathData="M0,0h108v108h-108z" />
</vector>
```

`drawable/ic_launcher_foreground.xml` (a simple centered monogram placeholder — replace with real brand art):

```xml
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="@color/on_primary"
        android:pathData="M44,34h20v10h-20z M44,49h20v10h-20z M44,64h20v10h-20z" />
</vector>
```

**No raster (`.webp`/`.png`) launcher icons are generated, and none are needed.** `min-sdk` defaults to `26` — the
exact API level `<adaptive-icon>` was introduced at — so every device this app installs on resolves the vector
adaptive icon directly; legacy `mipmap-hdpi/mdpi/xhdpi/xxhdpi/xxxhdpi` raster fallbacks (present in the reference
project only because *it* targets pre-26 launchers in some configurations) are dead weight here. If a user later
lowers `min-sdk` below 26, generate real raster fallbacks with Android Studio's Image Asset Studio at that point —
this skill deliberately doesn't attempt to rasterize vector art itself.

### `app/src/main/java/<package-path>/MainActivity.kt`

**`ui: compose`** (default):

```kotlin
package <namespace>

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import <namespace>.ui.theme.AppTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            AppTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    Greeting("<app-name>")
                }
            }
        }
    }
}

@Composable
fun Greeting(name: String, modifier: Modifier = Modifier) {
    Text(text = "Hello, $name!", modifier = modifier)
}

@Preview(showBackground = true)
@Composable
fun GreetingPreview() {
    AppTheme {
        Greeting("<app-name>")
    }
}
```

**`ui: views`** (ViewBinding-based alternative — write this instead when Step 2 chose `views`):

`res/layout/activity_main.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<androidx.constraintlayout.widget.ConstraintLayout xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    xmlns:tools="http://schemas.android.com/tools"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    tools:context=".MainActivity">

    <TextView
        android:id="@+id/greetingText"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="@string/app_name"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintLeft_toLeftOf="parent"
        app:layout_constraintRight_toRightOf="parent"
        app:layout_constraintTop_toTopOf="parent" />

</androidx.constraintlayout.widget.ConstraintLayout>
```

`MainActivity.kt`:

```kotlin
package <namespace>

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import <namespace>.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
    }
}
```

`viewBinding = true` (already in the `buildFeatures {}` block above) generates `ActivityMainBinding` from
`activity_main.xml`'s filename — no manual binding class to write. This variant needs
`androidx.appcompat:appcompat` and `androidx.constraintlayout:constraintlayout`, both pulled in transitively by
`com.google.android.material:material`'s own dependency graph, confirmed working with just the `material` alias
already in `dependencies {}` above (no extra explicit dependency line needed) — if that ever stops being true
upstream, add `androidx.appcompat:appcompat` and `androidx.constraintlayout:constraintlayout` explicitly.

### `app/src/test/resources/<package-path>/robolectric.properties`

```properties
sdk=<compile-sdk-minus-one-or-matching-supported-value>
```

The reference project pins this one minor step behind its own `compileSdk` (`compileSdk = 36` → `sdk=35`) because
Robolectric's shipped Android SDK jars lag the very latest platform release by a few months after each Android
release — **always check the installed `robolectric` version's supported SDKs before trusting `<compile-sdk>`
directly here** (Robolectric errors clearly, naming which SDKs it has, if an unsupported one is requested); Step 7
records which value actually worked.

### `app/src/test/java/<package-path>/MainActivityTest.kt` — placeholder unit test

```kotlin
package <namespace>

import org.junit.Test
import org.junit.Assert.assertEquals
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class MainActivityTest {
    @Test
    fun `placeholder arithmetic check`() {
        assertEquals(4, 2 + 2)
    }
}
```

A genuine first test exercises `MainActivity`'s `onCreate` via `Robolectric.buildActivity(MainActivity::class.java)`
— this skill ships only the arithmetic placeholder above (mirroring the reference project's own
`ExampleUnitTest.kt`) so `iru-android-generate-all-tests` has an obvious first target to replace.

### `app/src/androidTest/java/<package-path>/MainActivityInstrumentedTest.kt` — instrumented test skeleton

```kotlin
package <namespace>

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class MainActivityInstrumentedTest {
    @Test
    fun useAppContext() {
        val appContext = InstrumentationRegistry.getInstrumentation().targetContext
        assertEquals("<application-id>", appContext.packageName)
    }
}
```

Runs only via `./gradlew :app:connectedAndroidTest` against a running emulator/device — Step 7 doesn't run this
(no emulator available in this skill's own verification environment).

### `app/.gitignore`

```gitignore
/build
```

### `local.properties` guidance

Never write `local.properties` (it's machine-specific and always gitignored at the root — see
`iru-setup-android-gitignore`). Tell the user in Step 8 instead: on first checkout, either let Android Studio
generate it automatically, or create it by hand with one line, `sdk.dir=<path-to-android-sdk>` (e.g.
`sdk.dir=/Users/<you>/Library/Android/sdk` on macOS, `sdk.dir=/home/<you>/Android/Sdk` on Linux) — the SDK
components this scaffold needs (the `<compile-sdk>` platform, matching build-tools) are downloaded automatically by
AGP on first build as long as `android.builder.sdkDownload` isn't disabled and the SDK licenses are already
accepted (`sdkmanager --licenses`).

### Opt-ins

**Detekt + Spotless (`static-analysis: lint+detekt+ktlint`)** — add to `[versions]`/`[plugins]`:

```toml
detekt = "<detekt-version>"
spotless = "<spotless-version>"
# [plugins]
detekt = { id = "io.gitlab.arturbosch.detekt", version.ref = "detekt" }
spotless = { id = "com.diffplug.spotless", version.ref = "spotless" }
```

apply both in `app/build.gradle.kts`'s `plugins {}` and configure:

```kotlin
detekt {
    config.setFrom(files("$rootDir/detekt.yml"))
    buildUponDefaultConfig = true
}

spotless {
    kotlin {
        target("src/**/*.kt")
        ktlint()
        licenseHeaderFile(rootProject.file("spotless/license-header.kt"))
    }
    kotlinGradle {
        target("*.gradle.kts")
        ktlint()
    }
}
```

Write a minimal `detekt.yml` at the repository root (`build:\n  maxIssues: 0\ncomplexity:\n  active: true`, or
generate a fuller baseline with `./gradlew detektGenerateConfig`); Detekt's SARIF output
(`app/build/reports/detekt/detekt.sarif`) is what `iru-android-code-quality`/`iru-setup-android-github-workflows`'s
CodeQL-adjacent SARIF upload step consumes. Add `spotless/license-header.kt` only if a license was chosen in Step 2
(the file's content is that license's standard header comment).

**Kover (`coverage-tool: kover`, instead of the default AGP JaCoCo path)** — add to `[versions]`/`[plugins]`:

```toml
kover = "<kover-version>"
# [plugins]
kover = { id = "org.jetbrains.kotlinx.kover", version.ref = "kover" }
```

apply in `app/build.gradle.kts`'s `plugins {}`; no further DSL is required for a minimal setup — Kover's default
`koverXmlReportDebug`/`koverHtmlReportDebug` tasks work against the `debug` build type out of the box. When Kover is
chosen, drop `enableUnitTestCoverage = true` from the `debug {}` block above (Kover manages its own coverage
instrumentation and the two mechanisms shouldn't run simultaneously) and use `iru-android-coverage`'s Kover-XML
parsing path instead of the JaCoCo one.

**JUnit 5 (`junit: 5`, additive — Robolectric's runner itself stays JUnit 4)** — add to `[versions]`/`[plugins]`:

```toml
androidJunit5 = "<android-junit5-plugin-version>"
# [plugins]
android-junit5 = { id = "de.mannodermaus.android-junit5", version.ref = "androidJunit5" }
```

apply in `app/build.gradle.kts`'s `plugins {}`, and add the plugin's own BOM-pinned JUnit 5 test dependencies per
its README (`testImplementation(libs.junit.jupiter)`, `testRuntimeOnly(libs.junit.jupiter.engine)` — exact
coordinates come from that plugin's own version catalog recommendation at the version resolved in Step 4, since it
pins compatible JUnit 5 Jupiter/Platform versions together). Robolectric's `@RunWith(RobolectricTestRunner::class)`
tests keep using JUnit 4 exactly as before; JUnit 5 is for new tests that don't need Robolectric, written with
`@Test`/`org.junit.jupiter.api.Test` instead.

## Step 6 — Scaffold the project

Skip any individual file this step would write if Step 1 resolved gap-fill (`mode: existing` or the "Update"
choice) and that exact file already exists — never overwrite it.

1. Obtain the Gradle wrapper (Step 5's two-path recipe): try `gradle wrapper --gradle-version <gradle-version>`
   first, falling back to fetching `gradlew`/`gradlew.bat`/`gradle/wrapper/gradle-wrapper.jar` from the Gradle
   GitHub tag. Then hand-write `gradle-wrapper.properties` with Step 5's exact content (adding
   `distributionSha256Sum`, which neither path adds by default without an extra flag). `chmod +x gradlew`.
2. Write the root `build.gradle.kts`, `settings.gradle.kts`, `gradle.properties`, and `gradle/libs.versions.toml`
   from Step 5, with Step 2/3/4's values substituted and the `ui`/`sonar`/`distribution`/opt-in conditionals
   applied.
3. Create `app/src/main/java/<package-path>/` (from `<namespace>`, dots turned into path separators) and write
   `app/build.gradle.kts`, `app/proguard-rules.pro`, `app/src/main/AndroidManifest.xml`, the `res/` theme/color/
   string/icon files, `MainActivity.kt` (+ `ui/theme/Theme.kt` for `ui: compose`, or `res/layout/activity_main.xml`
   for `ui: views`), `app/src/test/resources/<package-path>/robolectric.properties`,
   `app/src/test/java/<package-path>/MainActivityTest.kt`,
   `app/src/androidTest/java/<package-path>/MainActivityInstrumentedTest.kt`, and `app/.gitignore` — all from
   Step 5.
4. Apply whichever opt-in blocks Step 2 selected (Detekt/Spotless, Kover, JUnit 5, Firebase App Distribution,
   Gradle Play Publisher) to the files just written, per Step 5's "Opt-ins"/distribution subsections.
5. If `distribution: internal` was chosen, remind the user now (also repeated in Step 8) that
   `app/google-services.json` must be downloaded from the Firebase console and placed manually — this skill never
   fetches or writes it.

## Step 7 — Verify

Run through the `iru-gate-runner` agent (never inline in this skill's own context — its reports can be long):

1. `./gradlew --offline help` — confirms the wrapper, root/settings files, and version catalog all parse and
   resolve without touching the network (anything already cached from Step 6's own dependency resolution). If this
   fails offline only because a dependency genuinely isn't cached yet, retry without `--offline`.
2. `./gradlew :app:assembleDebug` — the real scaffold-sanity build. **Warn the user up front that the first run
   downloads the `<compile-sdk>` platform, matching build-tools, and every Gradle/AGP/Kotlin/AndroidX artifact
   above if they aren't already cached — this can take several minutes and needs `ANDROID_HOME`/`local.properties`
   pointing at a real SDK install with licenses accepted.**

Report pass/fail and any error output verbatim for a failure; don't dump a successful build's full log.

## Step 8 — Report

Summarize what was generated: the resolved `application-id`/`namespace`/`app-name`, `min-sdk`/`compile-sdk`/
`target-sdk`, `version-name`/`version-code`, the license chosen (or "none"), and whether Step 6's scaffold ran
fresh, was skipped in favor of gap-fill/update (per Step 1), or the user chose to stop.

State explicitly what was included versus omitted, and why:

- **`ui`**: `compose`/`views` — which `MainActivity`/theme template was written.
- **`open-source`**/**`sonar`**: as Step 2 resolved them; if `sonar` ≠ `none`, restate the `sonar.organization`/
  `sonar.projectKey`/`sonar.host.url` written into `app/build.gradle.kts`'s `sonar { properties {…} } }` block.
- **`distribution`**: `none`/`internal`/`store` —
  - `internal`: restate that `app/google-services.json` must be downloaded from the Firebase console and placed at
    that exact path before any Firebase-related task runs, and that `FIREBASE_APP_ID` plus a service-account
    credential will be needed by CI.
  - `store`: restate which upload path was chosen (workflow-level `r0adkll/upload-google-play@v1`, or the Gradle
    Play Publisher plugin) and the Google Play service-account JSON key it depends on either way — this skill never
    collects or stores it.
  - `none`: no distribution plugin was added; `signingConfigs` is still present and usable whenever the four
    `SIGNING_*` env vars are supplied later.
- **`built-in-kotlin`**/**`junit`**/**`coverage-tool`**/**`static-analysis`**: as resolved, and which opt-in
  Gradle plugins/files that triggered.
- Which Step 4 versions came from a live lookup versus this skill's recorded fallback — call out explicitly any
  row marked "unverified locally" above that was used as-is without confirming it resolves.

Then report which of Step 5's files were created fresh, left untouched (gap-fill/`mode: existing`), or replaced
(update). If existing toolchain files were replaced, explicitly list what could have been lost — any dependency,
flavor, or build-type customization beyond what Step 5's templates show — and tell the user to check `git diff` for
anything they need to re-add.

### Known quirks / verification notes

- Verified in `$TMPDIR/iru-verify/android/app` (outside this repository): `./gradlew :app:assembleDebug
  :app:testDebugUnitTest :app:lint` all pass in one invocation against the scaffold generated with
  `distribution: store` (workflow-level upload — no Gradle Play Publisher plugin applied), `sonar: cloud` (dummy
  org/key/host — the `sonar` task itself was never run, only that `app/build.gradle.kts` configures with the block
  present), `ui: compose`, `junit: 4`, `coverage-tool: jacoco`, `static-analysis: lint`. Versions actually used:
  Gradle `9.7.1` (fresh, from `services.gradle.org/versions/current` — newer than the `9.4.0` recorded as this
  file's fallback; sha256 looked up from the same response), AGP `9.0.1`, Kotlin `2.3.10`, Dokka `2.1.0`, SonarQube
  plugin `7.2.3.7755`, JUnit `4.13.2`, AndroidX `junit` `1.3.0`, Espresso `3.7.0`, Compose BOM `2026.02.01`,
  `material` `1.13.0`, `test-core-ktx` `1.7.0`, MockK `1.14.9`, Robolectric `4.16.1`, `kotlin-reflect` `2.3.10`,
  `irurueta-android-test-utils` `1.3.2` (the reference project's own verified-working combination — deliberately
  used as-is rather than every individual artifact's own bare "latest", since AGP/Kotlin/Compose-compiler version
  skew across a whole toolchain is the actual compatibility risk, not any single artifact being one minor behind).
  **`search.maven.org`'s `solrsearch` API returned stale `latestVersion` values for both `kotlin-gradle-plugin`
  (`2.2.0`) and `dokka-gradle-plugin` (`2.0.0`) during this verification — both were already superseded (Kotlin
  `2.4.20`, confirmed via `repo1.maven.org`'s own `maven-metadata.xml`, is real; Dokka likely similarly stale).**
  Prefer a direct `maven-metadata.xml`/group-index fetch over `solrsearch` for "current version" lookups; treat
  `solrsearch`'s `latestVersion` field as unreliable.
- `./gradlew :app:assembleRelease` **with none of the four `SIGNING_*` env vars set** was also run (separately, with
  `unset SIGNING_STORE_FILE SIGNING_STORE_PASSWORD SIGNING_KEY_ALIAS SIGNING_KEY_PASSWORD` first) and confirmed to
  succeed (`BUILD SUCCESSFUL`), producing `test-app-1.0.0-release-unsigned.apk` at
  `app/build/outputs/apk/release/` — proves the `signingConfigs`/`buildTypes.release` conditional guard above never
  fails configuration when signing secrets are absent, exactly as designed.
- The default JDK on this machine (JDK 26) is **not** used — `JAVA_HOME` was pinned explicitly to JBR 21
  (`export JAVA_HOME=$(/usr/libexec/java_home -v 21)`) for every `./gradlew` invocation; not re-tested against JDK
  17 in this pass (Task 20's library verification exercises that fallback), but the same JBR distribution is
  present locally at `-v 17` too. Record JDK 21 (or 17) as a hard prerequisite, not just a suggestion — this AGP/
  Gradle combination was never tried against JDK 26.
- `app/build/reports/lint-results-debug.xml` (17 issues in this run, **all** `Warning`-severity "newer version
  available"/`GradleDependency`/`NewerVersionAvailable`/`AndroidGradlePluginVersion` — zero real correctness/
  security findings, expected since Step 4's fallback versions are all one or more minor releases behind by
  design) and the matching `.html`/`.txt` siblings are the Lint report paths (`iru-android-code-quality` reads the
  XML). `testDebugUnitTest` results land at `app/build/test-results/testDebugUnitTest/*.xml` (JUnit XML — 1 test,
  0 failures, confirmed — `iru-android-test` parses these) plus an HTML report at
  `app/build/reports/tests/testDebugUnitTest/`. The debug APK lands at
  `app/build/outputs/apk/debug/test-app-1.0.0-debug.apk` (`base.archivesName`'s `<project-name>-<versionName>[-<buildNumber>]`
  pattern, confirmed).
- **Coverage, confirmed working — no vendored JaCoCo CLI needed for the `app` module in this AGP version**:
  `./gradlew :app:createDebugUnitTestCoverageReport` runs (`app:createDebugUnitTestCoverageReport` is exposed for a
  `com.android.application` module exactly the same way it is for a library) and emits a real XML report at
  `app/build/reports/coverage/test/debug/report.xml` (standard JaCoCo-format XML — package/class/method-level
  `<counter type="..." missed="..." covered="...">`). The raw `.exec` file does **not** land at
  `app/build/jacoco/testDebugUnitTest.exec` (that's where the *reference* project's older-AGP/CI script expects it
  for its vendored-jar fallback) — in this verified AGP `9.0.1`, it's at
  `app/build/outputs/unit_test_code_coverage/debugUnitTest/testDebugUnitTest.exec` instead. Since AGP already emits
  the XML directly, this skill never needs `iru-setup-android-library`'s vendored `jacococli.jar` fallback path at
  all for the `app` module — `iru-android-coverage` should read `report.xml` from the path above directly.
- The Firebase App Distribution and Gradle Play Publisher plugin ids/versions were checked only by resolving
  `./gradlew help` with each plugin applied at its Step 4 fallback version (confirms the plugin id + version exist
  and configure without error) — **no distribution task was ever run** (`appDistributionUploadRelease`,
  `publishBundle`), since both need real Firebase/Google Play credentials this environment doesn't have. Mark both
  as "unverified locally" beyond that configuration-time check whenever a live plugin-portal lookup itself can't be
  reached from this machine.
- Detekt/Spotless/Kover/JUnit 5 opt-ins were **not** exercised in this verification pass (the representative inputs
  used `static-analysis: lint` and `coverage-tool: jacoco`/`junit: 4`, i.e. no opt-ins triggered) — their plugin
  ids/fallback versions above are unverified locally; confirm them the first time a user actually opts in.
- **The seven `gradle.properties` flags carried forward from the reference project
  (`android.usesSdkInManifest.disallowed`, `android.sdk.defaultTargetSdkToCompileSdkIfUnset`,
  `android.enableAppCompileTimeRClass`, `android.builtInKotlin`, `android.newDsl`,
  `android.r8.optimizedResourceShrinking`, `android.defaults.buildfeatures.resvalues`) each print an individual
  `WARNING: The option setting '<flag>' is deprecated ... It will be removed in version 10.0 of the Android Gradle
  plugin` on every build with AGP `9.0.1`.** They don't fail the build and are kept for fidelity to the reference
  project (which predates this deprecation), but note this explicitly to the user in Step 8 rather than leaving
  seven silent warnings on every single build — they'll need removing (or explicit new defaults set) before an
  eventual AGP 10 upgrade.
- **Separately, applying `org.jetbrains.kotlin.android` (`libs.plugins.kotlin.android`) itself now prints
  `⚠️ Deprecated 'org.jetbrains.kotlin.android' plugin usage ... no longer required for Kotlin support since AGP
  9.0`, recommending `built-in-kotlin: yes` instead.** This skill still defaults `built-in-kotlin` to `no` (Step
  2), matching the reference project and avoiding AGP's still-young built-in-Kotlin path — but both this and the
  `gradle.properties` deprecations above point the same direction, and a future revision of this skill should
  reconsider defaulting `built-in-kotlin: yes` once that path is less new.
- **`android:theme="@style/Theme.App"` still needed `package="<application-id>"` removed from the manifest's
  `<manifest>` tag** (see Step 5's `AndroidManifest.xml` note) — confirmed this produces a
  "Setting the namespace via the package attribute ... is no longer supported, and the value is ignored" warning on
  every build otherwise; the attribute contributes nothing once `android.namespace` is set in `build.gradle.kts`.
- **`androidx.activity:activity-compose` and `androidx.compose.ui:ui-tooling-preview` must both be declared
  explicitly** (see Step 5's dependency note) — omitting either fails Kotlin compilation
  (`Unresolved reference 'setContent'` / `Unresolved reference 'Preview'`) even with the Compose BOM and
  `androidx.compose.material3:material3` both present; neither pulls the other in transitively. This was the one
  real (not just deprecation-warning) defect found in this skill's first draft, fixed before this verification
  pass's second, successful run.
- `org.gradle.configuration-cache=true` (from `gradle.properties`) is compatible with `:app:assembleDebug`/
  `:app:testDebugUnitTest`/`:app:lint`/`:app:assembleRelease`/`:app:createDebugUnitTestCoverageReport`, all
  confirmed ("Configuration cache entry stored" on every run) — but **not** with `publishAndReleaseToMavenCentral`-
  style tasks in general (irrelevant here, since this skill never generates a publishing task) — if a future opt-in
  ever adds one that warns about configuration cache, pass `--no-configuration-cache` for that specific task the
  same way the reference project's `publish.yml` does for its library module.

Finish with an explicit **Warn explicitly** block:

- **The user must review every generated file before building, committing, or distributing.** In particular:
  confirm the license choice matches an actual repository-root `LICENSE` file (or that none is intended — suggest
  `iru-check-license` otherwise), replace the placeholder launcher icon/monogram vector art with real brand art
  before any real release, and never commit a real keystore — `*.jks`/`*.keystore` must stay gitignored
  (`iru-setup-android-gitignore` covers this) and `SIGNING_STORE_FILE` should point at a keystore kept outside
  version control (a CI secret decoded at build time, or a local, gitignored file).
- `app/google-services.json` (only relevant when `distribution: internal`) must stay gitignored — it carries
  project-specific Firebase identifiers that shouldn't be committed, even though they aren't traditional secrets.
- If `sonar: cloud` or `sonar: self-hosted` was chosen, a `SONAR_TOKEN` repository secret and an actual SonarCloud/
  SonarQube project matching `sonar.projectKey` still need to exist before a CI-driven `./gradlew :app:sonar`
  scan will succeed — this skill only writes the `sonar {}` block, it never runs a scan itself.
- If `distribution` ≠ `none`, the relevant credentials (Firebase `FIREBASE_APP_ID` + service-account JSON for
  `internal`; Google Play service-account JSON for `store`, however it's invoked) must exist as CI secrets — or be
  available locally — before any upload succeeds; this skill never collects or stores them.
- **Unverified locally, and never a blocker**: `connectedAndroidTest` (needs a running emulator/device — none
  available here), `appDistributionUploadRelease`/`publishBundle` (need real Firebase/Google Play credentials), and
  a genuinely signed `assembleRelease`/`bundleRelease` (needs a real keystore) — this skill only confirms the
  unsigned path builds. Everything else in the "Known quirks" section above was run for real while building and
  verifying this skill.
