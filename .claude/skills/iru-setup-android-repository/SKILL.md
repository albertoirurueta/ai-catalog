---
name: iru-setup-android-repository
description: End-to-end bootstrap for an Android/Gradle repository of either flavor — collects `flavor`
  (`library`/`app`, asked via `AskUserQuestion` when absent), `branching` (`gitflow`/`main-only`), the project's
  identity (group/artifact id + namespace + description for a library, application id + namespace + app name for
  an app, plus license and developer name/email/organization URL), and the shared pipeline parameters (integration
  branch `develop`, stable branch `main`, Java `17`, min SDK `26`, emulator API level `35`, instrumented tests
  `yes`, `open-source`, `publish` for libraries, `distribution` for apps, `sonar` plus its detail keys) once, then
  orchestrates the flavor's scaffold skill (`iru-setup-android-library` / `iru-setup-android-app`) →
  `iru-setup-antora` → `iru-setup-android-gitignore` → `iru-setup-android-github-workflows` → `iru-setup-changelog`
  → `iru-setup-readme`, in that order, via `iru-isolated-skill-executor`, so nothing is asked twice. Invoke as
  `/iru-setup-android-repository`, optionally with `args` (`key: value` lines) to pre-resolve `flavor`, `branching`,
  `mode` (`new`/`existing`), `open-source`, `publish`, `distribution`, `sonar` (+ `sonar-organization`/
  `sonar-project-key`/`sonar-host-url`), `integration-branch`, `stable-branch`, `java-version`, `min-sdk`,
  `compile-sdk`, `api-level`, `run-instrumented-tests`, and every identity field, skipping the matching question.
  In `mode: existing` it skips the scaffold when `settings.gradle.kts` already exists and tells every downstream
  step to take its own update/gap-fill path instead of assuming a brand-new repository. Use whenever bootstrapping
  (or catching up) an Android library or app repository's full Gradle/docs/gitignore/CI/changelog/README scaffold
  in one pass, whichever flavor it is, instead of running six skills separately and re-answering the same
  questions each time.
model: haiku
---

# Setup Android Repository

Bootstrap a brand-new (or catch up an existing) Android/Gradle repository in one pass, for either of its two
flavors, by orchestrating six existing skills: the flavor's own scaffold skill (`iru-setup-android-library` — a
`lib/` library module plus a Compose `app/` sample module — or `iru-setup-android-app` — a single `app/`
application module), `iru-setup-antora` (Antora documentation site), `iru-setup-android-gitignore` (root and
per-module `.gitignore`), `iru-setup-android-github-workflows` (CI/CD + security workflows), `iru-setup-changelog`
(root `CHANGELOG.md`), and `iru-setup-readme` (root `README.md`). This skill does not duplicate any of their logic
— it collects the shared parameters once and passes each skill only the `args` keys that skill's own Step 0
actually accepts, so the user isn't asked the same question repeatedly and no sub-skill sees a key it doesn't
recognize.

Each of Steps 4–9 invokes its sub-skill via the `iru-isolated-skill-executor` agent (`subagent_type:
"iru-isolated-skill-executor"`, always naming the full `iru-`-prefixed skill inside the prompt, e.g.
`Skill({skill: "iru-setup-android-library", args: "..."})`) rather than calling `Skill(...)` directly — every
sub-skill re-derives whatever it needs from the filesystem this orchestrator has just written to, so only a short
completion summary needs to flow back, keeping all six sub-skills' full transcripts (and the Android scaffold's
very long template listings) out of this orchestrator's own context. Every sub-agent is launched with
`run_in_background: false` — each step depends on the previous one's files being on disk.

## Step 0 — Resolve inputs

This skill can be invoked stand-alone (`/iru-setup-android-repository`) or driven by another orchestrator (the
catalog's `iru-setup-repository` front door), so parse `args` first, as `key: value` lines, one per line, e.g.:

```
flavor: library
branching: gitflow
mode: new
open-source: yes
publish: yes
sonar: cloud
sonar-organization: example-org-github
sonar-project-key: example-org_my-android-library
sonar-host-url: https://sonarcloud.io
integration-branch: develop
stable-branch: main
java-version: 17
min-sdk: 26
api-level: 35
run-instrumented-tests: yes
```

Recognized keys:

- **Flavor and mode**: `flavor` (`library`/`app`), `branching` (`gitflow`/`main-only`), `mode` (`new`/`existing`).
- **Shared pipeline vocabulary**: `open-source` (`yes`/`no`), `publish` (`yes`/`no` — `library` only),
  `distribution` (`none`/`internal`/`store` — `app` only), `sonar` (`cloud`/`self-hosted`/`none`) plus, only when
  set, `sonar-organization`/`sonar-project-key`/`sonar-host-url`, `integration-branch`, `stable-branch`,
  `java-version`, `min-sdk`, `compile-sdk`, `api-level`, `run-instrumented-tests` (`yes`/`no`).
- **Identity fields** named in Step 2: `group-id`, `artifact-id`, `namespace`, `description`, `version`
  (`library`); `application-id`, `namespace`, `app-name`, `version-name`, `version-code` (`app`); and, for both,
  `license`, `developer-name`, `developer-email`, `organization-url`.
- **Scaffold toolchain toggles**, passed through untouched if supplied but never asked by this orchestrator (see
  Step 2): `built-in-kotlin`, `junit`, `coverage-tool`, `static-analysis`, and `ui` (`app` only).

Every key found here is resolved — skip the matching question in Steps 1–3. Only keys genuinely missing from
`args` still need asking. If `args` is absent or doesn't look like this format, treat everything as unset and ask
normally.

## Step 1 — Resolve the flavor, branching model and mode

Survey the repository root first — `settings.gradle.kts`, `lib/build.gradle.kts`, `app/build.gradle.kts` — since
their presence decides both `flavor` and `mode` without a question in the common cases.

Unless `flavor` was already supplied via `args`, resolve it:

- `lib/build.gradle.kts` exists and applies `com.android.library` → `library` (whether or not a sample `app/`
  module also exists); `app/build.gradle.kts` exists and applies `com.android.application` with no
  `lib/build.gradle.kts` → `app`. Confirm the detected value with the user rather than assuming it silently.
- Nothing on disk yet, or genuinely ambiguous → `AskUserQuestion` with two options: **Library** (a redistributable
  `lib/` module published as an AAR, plus a Compose sample `app/` module that depends on it) / **App** (a single
  `app/` application module installed on devices or uploaded to a store, never published to Maven Central).

Map the resolved `flavor` to its scaffold skill for the rest of this run:

| `flavor` | Scaffold skill | Scaffold manifest checked in Step 4 |
|---|---|---|
| `library` | `iru-setup-android-library` | `settings.gradle.kts` (+ `lib/build.gradle.kts`) |
| `app` | `iru-setup-android-app` | `settings.gradle.kts` (+ `app/build.gradle.kts`) |

Unless `branching` was already supplied via `args`, resolve it with `AskUserQuestion` (two options):

- **gitflow** (recommended, this catalog's house pattern) — an integration branch (`develop`, carrying a
  `-SNAPSHOT` version) plus a stable branch (`main`, releases only); `iru-setup-android-github-workflows` generates
  `develop.yml`/`main.yml`/`sync.yml`, and `sync.yml` opens the post-release version-bump PR back into the
  integration branch.
- **main-only** — a single stable branch; `iru-setup-android-github-workflows` generates `main.yml`/`publish.yml`
  and no `sync.yml`. Step 3's integration-branch question is skipped for this model.

If `mode` wasn't supplied via `args`, don't ask about it as an isolated question — check whether
`settings.gradle.kts` already exists at the repository root: if it does, default to `existing` and confirm with
`AskUserQuestion` (`existing` pre-selected; `new` as the other option, noting that "new" re-runs the scaffold's
own stop/gap-fill/regenerate survey and that regenerating replaces `lib/build.gradle.kts`/`app/build.gradle.kts`
wholesale, discarding hand-added dependencies); if it doesn't, default to `new` without asking further — there's
nothing on disk yet to conflict with.

## Step 2 — Collect the project's identity

**`mode: existing` with the scaffold manifest already on disk** (`settings.gradle.kts` at the repository root, the same
check Step 4 uses to skip the scaffold): skip every identity question in this step — nothing downstream consumes
these answers once the scaffold is skipped (`iru-setup-readme` derives identity from the existing build files
itself), so asking them is a wasted question (verified in Task 53.2). Resolve `license` only if `args` supplied it,
and record in the final report that project identity was taken from the existing files rather than asked.

For any field Step 0 already resolved from `args`, use that value directly. For everything else, ask the user
directly (plain conversation — these are free-text project-identity fields, not a bounded choice). Only ask what
applies to the resolved `flavor`, using **exactly** the key names the scaffold skill reads:

- **`library`**: **group-id** (the Maven Central `groupId`, e.g. `com.example`), **artifact-id** (the
  `artifactId` and `rootProject.name`, e.g. `my-android-library`), **namespace** (the Android `namespace` and base
  Kotlin package, e.g. `com.example.myandroidlibrary` — need not equal `group-id`; the sample `app/` module's
  namespace is always `<namespace>.app`, so don't ask for it), **description** (one line, for the published
  `pom`). Leave **version** unset unless `args` supplied it — `iru-setup-android-library` applies its own
  `1.0.0-SNAPSHOT` default, which is what the gitflow `sync.yml` expects on the integration branch.
- **`app`**: **application-id** (reverse-DNS, e.g. `com.example.myapp`), **namespace** (offer `application-id`
  as the default rather than asking open-endedly), **app-name** (the launcher label). Leave **version-name**/
  **version-code** unset unless `args` supplied them — `iru-setup-android-app` defaults them to `1.0.0`/`1`.
- **Both**: **developer name**, **developer email**, **organizationUrl**. For a library they populate the
  published `pom`'s `developers` block; for an app they're only recorded in the scaffold's report — still worth
  collecting once here so `iru-setup-readme` and any later `iru-check-license` run see consistent authorship.

Then resolve the **license** with `AskUserQuestion`, unless `args` supplied one (one consistent choice reused
across both flavors, matching the four options every other setup skill in this catalog offers; the two scaffold
skills merely differ on which they recommend first — Apache for a library, MIT for an app — so present the
recommendation that matches the resolved `flavor`):

- Apache License 2.0 (recommended for `library`) — `Apache License 2.0` / `http://www.apache.org/licenses/LICENSE-2.0.txt`
- MIT License (recommended for `app`) — `The MIT License` / `https://opensource.org/license/mit`
- No license (proprietary / all rights reserved)
- Other — ask for the license's display name and URL directly afterward

The scaffold toolchain toggles — **`built-in-kotlin`**, **`junit`**, **`coverage-tool`**, **`static-analysis`**,
and (`app` only) **`ui`** — are **deliberately left unasked here**: nothing downstream of the scaffold needs them
as inputs (`iru-setup-android-gitignore` detects Detekt/ktlint from `detekt.yml` and the version catalog, and
`iru-setup-android-github-workflows` reads `enableUnitTestCoverage`/the `sonar {}` block straight from the module
build files), so the scaffold skill asks them itself with its own defaults (`no`/`4`/`jacoco`/`lint`/`compose`)
when invoked without them. Pass them through only if `args` supplied them.

## Step 3 — Collect the pipeline parameters

Ask the user directly, presenting each with its default so a plain "yes"/blank reply accepts it (skip any Step 0
already resolved from `args`, and skip the integration branch entirely when `branching: main-only`):

| Parameter | `args` key | Default | Consumed by |
|---|---|---|---|
| Integration branch | `integration-branch` | `develop` | `iru-setup-android-github-workflows` (gitflow only) |
| Stable branch | `stable-branch` | `main` | `iru-setup-android-github-workflows` |
| Java version | `java-version` | `17` | `iru-setup-android-github-workflows` (`actions/setup-java`) |
| Min SDK | `min-sdk` | `26` | `iru-setup-android-library` / `iru-setup-android-app` |
| Emulator API level | `api-level` | `35` | `iru-setup-android-github-workflows` (`reactivecircus/android-emulator-runner`) |
| Instrumented tests in CI | `run-instrumented-tests` | `yes` | `iru-setup-android-github-workflows` |

Notes on these, so the two halves of the pipeline can't disagree:

- **Java version** is a CI-only parameter here: neither scaffold skill accepts a `java-version` key — both write
  `sourceCompatibility`/`jvmTarget` 17 from their templates, which is exactly why the workflows skill's default is
  `17`. If the user overrides it, warn that the scaffold's Gradle files still target 17 and would need a matching
  hand edit (Step 10 repeats this).
- **`compile-sdk`** is *not* asked here: `iru-setup-android-library`/`-app` resolve it themselves from the locally
  installed SDK platforms (coupled with the Compose BOM lookup — see their Step 2), which this orchestrator can't
  do better. Pass it through only if `args` supplied it. The emulator **API level** is independent of `compileSdk`
  (an emulator image must exist for it — `35` is the verified default) and only feeds the workflows.
- **Instrumented tests** default to `yes` because both scaffolds always generate a placeholder test under
  `src/androidTest`; say plainly that `yes` adds an emulator boot (KVM on the runner) to every CI run, and that
  `no` is the faster choice for a repository that won't keep instrumented tests.

Then resolve, with `AskUserQuestion`, per this catalog's shared open-source-driven convention (skip any Step 0
already resolved):

- **open-source** — is this repository open source? Yes / No. Drives the recommended defaults below.
- **publish** — **`library` only**: Maven Central via the `com.vanniktech.maven.publish` plugin. Default **Yes**
  when open-source is Yes; otherwise ask with **No** recommended (Maven Central is meant for redistributable
  artifacts other projects depend on, rarely appropriate for closed-source code). Never collected or passed for
  `app` — neither `iru-setup-android-app` nor the app half of the workflows skill has a publish path.
- **distribution** — **`app` only**: `none`/`internal`/`store`. Default **`store`** when open-source is Yes;
  otherwise ask with **`internal`** (Firebase App Distribution) recommended, `none` as the local-install-only
  alternative. Never collected or passed for `library`. The `store` sub-choice — workflow-level
  `r0adkll/upload-google-play` action versus the Gradle Play Publisher plugin — is deliberately left to
  `iru-setup-android-app` to ask (it isn't an `args` key), and `iru-setup-android-github-workflows` detects the
  outcome from `app/build.gradle.kts` afterward.
- **sonar** — `cloud`/`self-hosted`/`none`. Recommend **`cloud`** when open-source is Yes; when not open source,
  state that SonarCloud is free only for open-source projects (a paid plan is required otherwise) and recommend
  **`none`**, offering **self-hosted SonarQube** as the second option. When `cloud`/`self-hosted` is chosen, also
  collect `sonar-organization`/`sonar-project-key`/`sonar-host-url` the same way both scaffold skills' own Step 2
  does (SonarCloud: suggest `<owner>-github` / `<owner>_<repo>` / `https://sonarcloud.io`, inferred from
  `git remote get-url origin`; self-hosted: ask for `sonar.host.url` directly, plus `sonar.organization` only if
  that server has organizations enabled, and `sonar.projectKey`).

These values (`open-source`, `publish`/`distribution`, `sonar` + detail keys) are passed through unchanged to
Step 4 (the scaffold skill) and Step 7 (`iru-setup-android-github-workflows`) so neither sub-skill re-asks them —
and so the workflows never contain a Maven Central publish job for a `lib/build.gradle.kts` with no
`mavenPublishing {}` block, or a `:lib:sonar`/`:app:sonar` step for a build file with no `sonar {}` block.

## Step 4 — Run the flavor's scaffold skill

If `mode: existing` (Step 1) and `settings.gradle.kts` already exists at the repository root, skip invoking the
scaffold skill entirely — there's nothing to regenerate, and `mode: existing` means the user already confirmed
they don't want it replaced. Note in Step 10's report that the Gradle project already existed and was left
untouched, then continue to Step 5 (the existing scaffold is presumed valid enough for the rest of the pipeline
to build against). Otherwise, format Steps 2–3's answers as `key: value` lines using **exactly** the keys the
resolved flavor's skill accepts (never an invented key) and invoke via `iru-isolated-skill-executor`:

```
# flavor: library
Agent({
  description: "Run iru-setup-android-library",
  subagent_type: "iru-isolated-skill-executor",
  prompt: "Invoke Skill({skill: \"iru-setup-android-library\", args: \"group-id: <group-id>\\n
    artifact-id: <artifact-id>\\nnamespace: <namespace>\\ndescription: <description>\\n
    version: <version, only if supplied>\\nmin-sdk: <min-sdk>\\ncompile-sdk: <compile-sdk, only if supplied>\\n
    license: <license display name, or 'none'>\\ndeveloper-name: <developer-name>\\n
    developer-email: <developer-email>\\norganization-url: <organization-url>\\nopen-source: <open-source>\\n
    publish: <publish>\\nsonar: <sonar>\\nsonar-organization: <..., if set>\\nsonar-project-key: <..., if set>\\n
    sonar-host-url: <..., if set>\\nbuilt-in-kotlin: <..., only if supplied>\\njunit: <..., only if supplied>\\n
    coverage-tool: <..., only if supplied>\\nstatic-analysis: <..., only if supplied>\\nmode: <mode>\"}).
    Report back: whether the Gradle wrapper, root build files, lib/ and app/ modules were created fresh, gap-filled,
    or already existed (and, if so, whether the user chose to stop), which toolchain versions came from a live
    lookup versus the recorded fallback, the compile-sdk it resolved, whether its Gradle verification build
    passed, and any value it resolved on its own (repository URL, inception year).",
  run_in_background: false
})
```

```
# flavor: app
Agent({
  description: "Run iru-setup-android-app",
  subagent_type: "iru-isolated-skill-executor",
  prompt: "Invoke Skill({skill: \"iru-setup-android-app\", args: \"application-id: <application-id>\\n
    namespace: <namespace>\\napp-name: <app-name>\\nmin-sdk: <min-sdk>\\n
    compile-sdk: <compile-sdk, only if supplied>\\ntarget-sdk: <compile-sdk, only if supplied>\\n
    version-name: <..., only if supplied>\\nversion-code: <..., only if supplied>\\n
    license: <license display name, or 'none'>\\ndeveloper-name: <developer-name>\\n
    developer-email: <developer-email>\\norganization-url: <organization-url>\\nopen-source: <open-source>\\n
    sonar: <sonar>\\nsonar-organization: <..., if set>\\nsonar-project-key: <..., if set>\\n
    sonar-host-url: <..., if set>\\ndistribution: <distribution>\\nui: <..., only if supplied>\\n
    built-in-kotlin: <..., only if supplied>\\njunit: <..., only if supplied>\\n
    coverage-tool: <..., only if supplied>\\nstatic-analysis: <..., only if supplied>\\nmode: <mode>\"}).
    Report back: whether the Gradle wrapper, root build files and app/ module were created fresh, gap-filled, or
    already existed (and, if so, whether the user chose to stop), which toolchain versions came from a live lookup
    versus the recorded fallback, the compile-sdk/target-sdk it resolved, whether the release signing config and
    the distribution plugin (Firebase App Distribution / Gradle Play Publisher / none) were written, whether its
    Gradle verification build passed, and any value it resolved on its own.",
  run_in_background: false
})
```

Omit every `only if supplied` line whose value wasn't resolved (never send an empty key). Neither scaffold skill
accepts `branching`, `integration-branch`, `stable-branch`, `java-version`, `api-level` or
`run-instrumented-tests` — those are Step 7's alone, so never send them here. `publish` is sent only for
`library`, `distribution` only for `app`.

Each scaffold skill parses these itself (its own Step 0) and only asks the user about anything genuinely left
out — `AskUserQuestion` surfaces to the user the same way whether invoked directly or from inside this
sub-agent. If it reports that its files already existed and the user chose to stop, stop this skill here too —
there's no coherent Gradle project to build Antora docs or CI workflows around yet. The scaffold's own
verification (`./gradlew --offline help`, then an `assembleDebug`) downloads Gradle, SDK components and every
dependency on first run — warn the user that this step is the slow one before launching it.

## Step 5 — Run `iru-setup-antora`

Invoke via `iru-isolated-skill-executor`: `Agent({description: "Run iru-setup-antora", subagent_type:
"iru-isolated-skill-executor", prompt: "Invoke Skill({skill: \"iru-setup-antora\"}) with no args — it takes none,
deriving the Antora component name, title, and version itself from the repository (the Gradle project name in
settings.gradle.kts, git tags/GitHub releases, or the module's version with any -SNAPSHOT suffix stripped).
Report back: which files/pages were created vs. already present, and whether the site build succeeded.",
run_in_background: false})`.

Run this *before* Step 7, not after: `iru-setup-antora` is quick to detect as "already done", and
`iru-setup-android-github-workflows`'s own survey (Step 1 there) checks whether `docs/antora.yml`/
`docs/antora-playbook.yml` exist before generating its Dokka + Antora Pages deploy job — running Antora setup
first means that check finds everything in place instead of flagging a gap. In a repository with no tags or
releases yet, `iru-setup-antora` may ask for a starting version; answer with the scaffold's version minus any
`-SNAPSHOT` suffix (`1.0.0` for the defaults) rather than inventing another.

## Step 6 — Run `iru-setup-android-gitignore`

Invoke via `iru-isolated-skill-executor`: `Agent({description: "Run iru-setup-android-gitignore", subagent_type:
"iru-isolated-skill-executor", prompt: "Invoke Skill({skill: \"iru-setup-android-gitignore\"}) with no args —
it derives the module list from settings.gradle.kts's include(...) lines and detects mode itself from whether a
root .gitignore already exists. Report back only whether the root and per-module .gitignore files were created
fresh, gap-filled, or left untouched, and — if any already existed — whether the user accepted or skipped the
proposed diff.", run_in_background: false})`.

`iru-setup-android-gitignore` does accept `mode` and `modules` keys, but both are deliberately left for it to
detect: its own `.gitignore`-presence check is the more precise `mode` signal for this file (a `mode: new`
repository can still carry a hand-written `.gitignore` that deserves the diff-and-approve path, never a silent
overwrite), and the module list must come from the `settings.gradle.kts` Step 4 just wrote, not from this
orchestrator's guess. Run this after Steps 4–5, not before: detection depends on the scaffold's
`settings.gradle.kts`/`detekt.yml`/version-catalog signals and on the Antora config Step 5 just wrote. Run it
*before* Step 7, so `build/`, `.gradle/`, `local.properties`, keystores, `google-services.json` and the Antora
build output are already ignored before CI-generated reports show up locally.

## Step 7 — Run `iru-setup-android-github-workflows`

Format Steps 1–3's answers as `key: value` lines and invoke via `iru-isolated-skill-executor`:

```
Agent({
  description: "Run iru-setup-android-github-workflows",
  subagent_type: "iru-isolated-skill-executor",
  prompt: "Invoke Skill({skill: \"iru-setup-android-github-workflows\", args: \"flavor: <flavor>\\n
    branching: <branching>\\nintegration-branch: <integration-branch, gitflow only>\\n
    stable-branch: <stable-branch>\\njava-version: <java-version>\\n
    run-instrumented-tests: <run-instrumented-tests>\\napi-level: <api-level>\\nopen-source: <open-source>\\n
    publish: <publish, library only>\\ndistribution: <distribution, app only>\\nsonar: <sonar>\\n
    sonar-organization: <..., if set>\\nsonar-project-key: <..., if set>\\nsonar-host-url: <..., if set>\\n
    mode: <mode>\"}). Report back: whether develop.yml/main.yml/sync.yml (gitflow) or main.yml/publish.yml
    (main-only), security.yml, .github/dependabot.yml and .github/scripts/sync_versions.py were created fresh,
    updated, or already existed (and, if so, whether the user chose to stop), the coverage-conversion path it
    chose, any open gap it flagged (missing docs/antora.yml, README/Antora wording not matching sync_versions.py,
    a Gradle Play Publisher plugin found), and the full required-secrets/environments table it produced for this
    flavor/branching/options.",
  run_in_background: false
})
```

Omit `integration-branch` when `branching: main-only`, `publish` for `app`, and `distribution` for `library`
(never send a key the flavor doesn't use). The six `security-*` keys are deliberately never passed — the four
always-on jobs default to `yes` and the two opt-ins (`security-owasp-dependency-check`, `security-mobsfscan`) to
`no` inside `iru-setup-android-github-workflows` itself, and this orchestrator doesn't ask about them; note this
once in Step 10's report rather than re-asking per run. The shared `license`/`developer-*`/`organization-url`
keys are likewise never passed here: the workflows skill accepts them only to tolerate a full shared-args set
and would report them as "supplied but unused".

If it reports that the workflow files already existed and the user chose to stop, note that in Step 10's report
rather than treating it as a failure of this skill — the scaffold, the Antora docs, and the `.gitignore` files
from Steps 4–6 are still valid on their own.

## Step 8 — Run `iru-setup-changelog`

Invoke via `iru-isolated-skill-executor`: `Agent({description: "Run iru-setup-changelog", subagent_type:
"iru-isolated-skill-executor", prompt: "Invoke Skill({skill: \"iru-setup-changelog\"}) with no args — it takes
none, working entirely from the repository's own git tag/GitHub Release history. Report back only whether
CHANGELOG.md was created (and the version range reconstructed) or already existed.", run_in_background: false})`.
Position relative to Steps 4–7 doesn't matter functionally — it's independent of all of them. In `mode: new`
(no tags yet) it either bootstraps a minimal `## [Unreleased]`-only file or stops per the user's choice; in
`mode: existing`, real tag/release history may exist to backfill. If `CHANGELOG.md` already exists, it stops
immediately and reports that regardless of `mode` — not a failure of this skill, just something to note in
Step 10's report. Running it before `iru-setup-readme` means the README's Documentation section sees it already
in place.

## Step 9 — Run `iru-setup-readme`

Invoke via `iru-isolated-skill-executor`: `Agent({description: "Run iru-setup-readme", subagent_type:
"iru-isolated-skill-executor", prompt: "Invoke Skill({skill: \"iru-setup-readme\", args: \"sonar: <sonar>\"}) — `sonar` is the only key it accepts (with `none` it suppresses Sonar badges/links even if Sonar config exists on disk),
deriving everything it needs by exploring the repository directly (build.gradle.kts/settings.gradle.kts, the
Antora docs, .gitignore, the workflows and the sonar {} block, and CHANGELOG.md). Report back only which sections
were included vs. omitted and why, and — for a library — whether the Gradle dependency snippet it wrote uses the
implementation(\"group:artifact:version\") shape.", run_in_background: false})`. Run this last, after every
other skill, so its badges/status-table/documentation-links sections see the finished state of Steps 4–8 instead
of a sparser mid-run snapshot. In `mode: new`, most CI/Sonar/changelog-derived sections will still be sparse or
absent (no commits/tags/CI runs yet) — expected; `iru-setup-readme` omits what it can't confirm rather than
inventing it. `README.md` may or may not already exist depending on `mode`; `iru-setup-readme`'s own approval
step handles that on its own — nothing further to confirm here.

For a gitflow **library**, the README's dependency snippet is what `sync.yml`'s `sync_versions.py` rewrites after
each release — if `iru-setup-readme` reports a snippet shape other than the one `iru-setup-android-github-workflows`
recorded in Step 7 (Groovy `implementation 'g:a:v'` vs. Kotlin-DSL `implementation("g:a:v")`), flag the mismatch
in Step 10 so the user reconciles one of the two before the first release.

## Step 10 — Report

Summarize the outcome of all six delegated skills together: the resolved `flavor`, `branching` and `mode`, the
project identity and license, the pipeline parameters used (the Step 3 table with the values actually applied),
and which of the scaffold's own files (`settings.gradle.kts`, root `build.gradle.kts`, `gradle/libs.versions.toml`,
the wrapper, `lib/`/`app/`), the Antora docs site, the root and per-module `.gitignore` files, the workflow files
(`develop.yml`/`main.yml`/`sync.yml` + `sync_versions.py`, or `main.yml`/`publish.yml`, plus `security.yml` and
`.github/dependabot.yml`), `CHANGELOG.md`, and `README.md` were created, updated, or left untouched (per any stop
choice in Steps 4 or 7, or a `mode: existing` skip in Step 4).

State explicitly which of publishing/distribution and Sonar analysis were wired, or deliberately omitted and why:

- **`open-source`**: yes/no, as resolved in Step 3.
- **`publish`** (`library`) / **`distribution`** (`app`): whether the `mavenPublishing {}` block and the Maven
  Central publish job — or the signing config, the Firebase App Distribution / Google Play upload, and the
  store-upload mechanism `iru-setup-android-app` chose — were included; `yes`/non-`none` unless the user opted out
  (or the project isn't open source and declined it), stated plainly rather than left implicit.
- **`sonar`**: `cloud`/`self-hosted`/`none`, and whether the per-module `sonar {}` block and the `:lib:sonar`/
  `:app:sonar` workflow step were included — if `none`, note whether that's the expected non-open-source default
  or a direct user choice.
- **`run-instrumented-tests`**: yes/no — whether the emulator (KVM) job was generated.
- **Toolchain versions**: which came from a live lookup versus the recorded fallback, as reported by the scaffold
  (Gradle/AGP/Kotlin/Compose BOM…) and the workflows skill (action tags).

Reproduce the **consolidated required-secrets/settings table** `iru-setup-android-github-workflows` reported in
Step 7 verbatim (it's already scoped to exactly this flavor/branching/options — don't re-derive or expand it):
`SONAR_TOKEN` for a non-`none` `sonar`; `MAVEN_CENTRAL_USERNAME`/`MAVEN_CENTRAL_PASSWORD` and
`SIGNING_MEMORY_KEY`/`SIGNING_MEMORY_KEY_ID`/`SIGNING_IN_MEMORY_KEY_PASSWORD` for `publish: yes`;
`ANDROID_KEYSTORE_BASE64`/`ANDROID_KEYSTORE_PASSWORD`/`ANDROID_KEY_ALIAS`/`ANDROID_KEY_PASSWORD` for an app whose
`distribution` isn't `none`, plus `PLAY_SERVICE_ACCOUNT_JSON` (`store`) or `FIREBASE_APP_ID`/
`FIREBASE_SERVICE_CREDENTIALS` (`internal`). Then its repository-settings notes: GitHub Pages source set to
**GitHub Actions** for the docs deploy, and — gitflow only — "Workflow permissions" allowing GitHub Actions to
create pull requests for `sync.yml`. Add the two non-secret files the app scaffold never writes but CI/local
builds need: `app/google-services.json` (`distribution: internal`, downloaded from the Firebase console,
gitignored) and `local.properties` pointing at the SDK (local builds only, gitignored).

List every decision made on the user's behalf: the license question's flavor-dependent recommendation (Step 2);
leaving `built-in-kotlin`/`junit`/`coverage-tool`/`static-analysis`/`ui` and the `store` upload mechanism for
their scaffold skill to ask (Steps 2–3); `compile-sdk` resolved by the scaffold from the local SDK rather than
asked (Step 3); `java-version` feeding only the workflows (Step 3); `iru-setup-android-gitignore`'s `mode`/`modules`
left to its own detection (Step 6); and the six `security-*` flags left at their defaults (Step 7).

Finish with an explicit **Warn explicitly** block, repeating each sub-skill's own closing warning:

- **Review every generated/updated file before building, committing, or relying on CI.** Confirm the license
  matches an actual `LICENSE` file at the root if one was chosen (`iru-check-license` can generate one and
  backfill Kotlin headers), and that `./gradlew assembleDebug test lint` succeeds locally — the first run
  downloads Gradle, SDK components and every dependency.
- Branch names, module names and the signing/publish/store setup in the workflows were inferred from the
  resolved parameters and the scaffold's files — a wrong assumption there publishes or signs the wrong thing.
  Do a `workflow_dispatch` dry run before trusting a real release.
- Every secret in the table above, and the matching SonarCloud project / Maven Central Publishing Portal
  registration / Google Play Console service account / Firebase project, must already exist before CI can pass
  — nothing in this pipeline creates or stores any account or credential.
- If `java-version` was overridden from `17`, the scaffold's `sourceCompatibility`/`jvmTarget` still say 17 and
  need a matching hand edit in `lib/build.gradle.kts`/`app/build.gradle.kts`.
- Every toolchain and action version was resolved via a run-time lookup or its recorded September 2026
  fallback — re-check them (Dependabot's `gradle` + `github-actions` entries will start proposing bumps) before
  relying on this scaffold long-term. The emulator instrumented-test run, the Sonar scan, Maven Central
  publishing and the store/Firebase uploads are never exercised locally by any of the six skills — only their
  YAML is validated.
