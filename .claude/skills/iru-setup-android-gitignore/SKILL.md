---
name: iru-setup-android-gitignore
description: Create or update the root `.gitignore` (Gradle/Android Studio noise, `local.properties`, keystores,
  `google-services.json`, Antora docs build output) plus a per-module `.gitignore` (`/build`) for each Gradle
  module in an Android library/app project — `lib`, `app`, or whatever `settings.gradle.kts` actually includes.
  Invoke as `/iru-setup-android-gitignore`, optionally with `args`: `mode: new|existing` (default: detected from
  whether a root `.gitignore` already exists) and `modules: <comma/space-separated list>` (default: every
  `include(":…")` entry in `settings.gradle.kts`, falling back to `lib`/`app` when neither exists). Only creates a
  `.gitignore` when one doesn't exist yet — if a root or per-module `.gitignore` already exists, this skill never
  overwrites it silently: it merges in whatever's missing (`mode: existing`), shows the user a diff, and only
  writes on explicit approval. Templates are genericized from
  https://github.com/albertoirurueta/irurueta-android-glutils's own `.gitignore`, `lib/.gitignore` and
  `app/.gitignore`. Deliberately does **not** ignore the vendored `jacoco-<ver>/` JaCoCo CLI directory that
  `iru-setup-android-library`/`iru-setup-android-app` commit into the repository — it must stay tracked so CI can
  convert coverage without a network dependency. Mirrors `iru-setup-java-gitignore`'s diff-and-approve contract for
  the Android/Gradle ecosystem. Use whenever an Android library or app project needs a `.gitignore` bootstrapped
  from scratch, or an existing one checked/gap-filled against this house template without touching it unless the
  user approves.
model: haiku
---

# Setup Android Gitignore

Create or refresh the root `.gitignore` and each module's own `.gitignore` for an Android (Gradle/Kotlin) project,
using [irurueta-android-glutils](https://github.com/albertoirurueta/irurueta-android-glutils)'s own `.gitignore`,
`lib/.gitignore` and `app/.gitignore` as the concrete reference templates (genericized — the reference repository
has no project-specific names inside these three files to strip in the first place, they're already generic
Android/Gradle boilerplate). Never overwrite an existing `.gitignore` without showing the user exactly what would
change and getting explicit approval first — a `.gitignore` can carry hand-added, project-specific entries that
must not be silently dropped.

## Step 0 — Resolve inputs

Parse `args` as `key: value` lines, skipping any question already answered:

- `mode: new|existing` — if omitted, detect it: a root `.gitignore` already present at the repository root means
  `existing` (gap-fill only, never a silent overwrite); its absence means `new`.
- `modules: <list>` — comma- or space-separated module directory names to give their own `.gitignore` (e.g. `lib`,
  `app`). If omitted:
  1. If `settings.gradle.kts` (or `settings.gradle`) exists at the repository root, derive the list from every
     `include(":<name>")` (or Groovy `include ':<name>'`) line, stripping the leading `:` and any nested-module
     prefix (`include(":lib")` → `lib`; a nested module like `include(":lib:sub")` → `lib/sub`, and its
     `.gitignore` goes inside that nested directory).
     ```bash
     grep -oE 'include\(?["'"'"']:[^"'"'"']+' settings.gradle.kts settings.gradle 2>/dev/null \
       | sed -E "s/.*:([^\"']+).*/\1/" | tr ':' '/' | sort -u
     ```
  2. If no `settings.gradle*` exists yet (this skill run standalone, ahead of `iru-setup-android-library`/
     `iru-setup-android-app`), default to whichever of `lib`/`app` actually exist as directories at the repository
     root; if neither exists, ask the user via `AskUserQuestion` for the module directory name(s) rather than
     guessing.

## Step 1 — Survey existing `.gitignore` files

- **Root**: read `.gitignore` at the repository root if present (matters for Step 5's merge and to warn the user up
  front that changes will be proposed rather than silently applied).
- **Per module**: for each module resolved in Step 0, read `<module>/.gitignore` if present. Each module's
  `.gitignore` is tracked and merged independently from the root one and from every other module's.
- If **nothing** exists anywhere (no root `.gitignore`, no module `.gitignore`), the final writes in Step 6 happen
  without needing approval — go straight from composing content to writing it, then report in Step 7. If
  **anything** already exists (root and/or any module), warn the user up front that this skill will propose
  changes for them to review rather than overwrite anything silently, and continue.

## Step 2 — The root `.gitignore` base template

Every Android project gets this baseline, adapted verbatim from the reference repository's own root `.gitignore`,
plus two additions this catalog always wants for a project that also carries Antora documentation
(`iru-setup-antora`) — the reference repository itself has no `docs/` yet, so these two lines are this skill's own
addition, not lifted from the reference:

```gitignore
# Gradle files
.gradle/
build/

# Local configuration file (sdk path, etc)
local.properties

# Log/OS Files
*.log

# Android Studio generated files and folders
captures/
.externalNativeBuild/
.cxx/
*.apk
output.json

# IntelliJ
*.iml
.idea/
misc.xml
deploymentTargetDropDown.xml
render.experimental.xml

# Keystore files
*.jks
*.keystore

# Google Services (e.g. APIs or Firebase)
google-services.json

# Android Profiling
*.hprof

# Antora documentation build output (see iru-setup-antora)
docs/build/
docs/node_modules/
```

This section is unconditional — include it verbatim. Notes on specific lines:

- `build/` here is **unanchored** (no leading `/`), exactly as the reference repository has it — it matches any
  directory literally named `build` at any depth, which is what makes every module's own generated output (and
  `docs/build/`, redundantly with the explicit line above) fall out of tracking even before Step 3's per-module
  files are added. Keep it unanchored; don't "fix" it to `/build/` — that would stop matching `lib/build/`,
  `app/build/`, etc. from the root file alone (Step 3's per-module `.gitignore` still covers those directly, but
  the two mechanisms are deliberately redundant, matching the reference).
- `*.jks` / `*.keystore` cover a locally-created release keystore and also the file CI decodes a base64 secret
  into during a release workflow (`app/release.jks`, matching `iru-setup-android-github-workflows`'s `main.yml`
  signing step) — that path is a `*.jks` match already, no separate line needed.
- `google-services.json` (Firebase/Google APIs config, `distribution: internal`/`store` app flavors) is ignored
  unconditionally, matching the reference; if the project intentionally commits a placeholder version for CI to
  overwrite, that's a project-specific call to flag in Step 7's report, not something this template should special
  case.
- **The vendored JaCoCo CLI directory (`jacoco-<ver>/`, e.g. `jacoco-0.8.13/lib/jacococli.jar`) is deliberately
  never added to this template, and no line here may be broadened to match it.** `iru-setup-android-library`/
  `iru-setup-android-app` commit that directory into the repository on purpose (JaCoCo CLI jars used to convert
  the AGP unit-test coverage `.exec` output to XML in CI, without depending on network access at build/CI time —
  see Task 20.2/23's verification notes). Concretely: **do not** add a `*.jar` pattern anywhere in this template
  (the reference `.gitignore` has none, precisely so the vendored jars stay tracked) — before proposing any new
  line in Step 4 that could plausibly be a glob starting with `*.jar`, `**/*.jar`, `jacoco*/`, `lib/`, or `/lib/`,
  check it against `git check-ignore -v jacoco-<ver>/lib/jacococli.jar` in the target repository (or the verified
  pattern below if the directory doesn't exist there yet) and refuse to add it if it would match. No negation
  (`!jacoco-*/`) is needed as long as this rule is followed — negating an ignored path only matters once something
  ignores it, and nothing in this template does.

## Step 3 — Per-module `.gitignore`

For each module resolved in Step 0, its own `.gitignore` is a single line, matching the reference repository's
`lib/.gitignore` and `app/.gitignore` exactly:

```gitignore
/build
```

(Anchored to the module root, unlike the root file's unanchored `build/` — this is the reference's own convention:
a module's `.gitignore` only needs to ignore its own top-level `build/` output directory, not every directory
named `build` nested arbitrarily deep inside its sources.) This line is unconditional for every module in the
list — a Gradle module's build output directory always needs ignoring, and there's no project-specific variant of
this one line to detect.

## Step 4 — Detect additional project-specific root entries

Don't guess; only add a section below when the thing it targets is actually present (or about to be created by a
sibling skill) in the target repository — everything in Step 2 is unconditional, this step is the only place that
varies per project.

- **Antora docs already covered** — Step 2's `docs/build/`/`docs/node_modules/` lines are unconditional (added even
  when `docs/` doesn't exist yet, since `iru-setup-antora` typically runs later in the same bootstrap pipeline);
  don't duplicate them here.
- **Detekt/ktlint/Spotless caches**, if `iru-setup-android-library`/`-app` was run with static analysis opted in
  (`detekt.yml` exists, or a `spotless`/`detekt` plugin alias is present in `gradle/libs.versions.toml`): add
  ```gitignore
  .kotlin/
  ```
  (Kotlin compiler's own incremental-compilation cache directory at the repository root, distinct from each
  module's `build/`). Skip if neither tool is wired.
- **Fastlane**, if a `fastlane/` directory exists (some app projects add it later for store metadata/screenshots
  automation, outside this catalog's own scaffold skills but sometimes added by hand): add
  ```gitignore
  fastlane/report.xml
  fastlane/Preview.html
  fastlane/screenshots/**/*.png
  fastlane/test_output
  ```
  Skip entirely if no `fastlane/` directory exists — don't preemptively add Fastlane's own template when the
  project has no Fastlane setup to speak of.
- Don't invent additional entries beyond what's actually detected — if the project has no Detekt/ktlint/Spotless
  config and no `fastlane/` directory, the composed root `.gitignore` should simply not mention them.

## Step 5 — Compose the proposed content

- **Root**: concatenate Step 2's base template with whichever Step 4 sections actually matched, each under its own
  comment header. If Step 1 found an existing root `.gitignore`, merge rather than duplicate: keep any of its lines
  that aren't already covered by the composed template (hand-added project-specific ignores must survive — e.g. a
  project that added its own `fastlane/` block by hand before this skill learned to detect it), and don't repeat a
  line that's already present verbatim. If `mode: existing` and the existing file was itself missing lines this
  template supplies (e.g. it predates the Antora `docs/build/` addition), the merge naturally adds them — that's
  the intended gap-fill behavior, not an overwrite.
- **Per module**: for each module, Step 3's single `/build` line either becomes the whole file (module had no
  `.gitignore` yet) or is merged into whatever the module's existing `.gitignore` already has (added only if
  missing — most module `.gitignore` files that already exist for an Android module will already have this exact
  line, in which case there is nothing to change and this module is skipped from Step 6's writes/diffs entirely).

## Step 6 — If anything already existed, get approval before writing

Skip entirely for any file (root or a given module) that Step 1 found absent — write that one straight away, no
approval needed, since there's nothing to lose.

For every file that did already exist and whose proposed content differs from what's on disk:

- Show the user the proposed new content as a diff against the current file (writing the draft to a temp path and
  running `git diff --no-index <current> <draft>` gives a clean unified diff) — do this for the root `.gitignore`
  and each affected module `.gitignore` together, in one batch, rather than one approval round-trip per file.
- Ask via `AskUserQuestion` whether to: (a) accept and write every proposed change, (b) skip and leave every
  existing file untouched. There is no partial-apply option here — if the user wants only some of the proposed
  lines, let them say so in free text and revise the draft before writing.
- Only proceed to Step 7's writes for files the user accepted.

## Step 7 — Write and report

Write the composed content (Step 5, incorporating any edits from Step 6's review) to `.gitignore` at the
repository root and to `<module>/.gitignore` for each module in the resolved list. Then summarize:

- Whether the root `.gitignore` was newly created, updated (and which lines were added), or left untouched
  (already matched).
- Same, per module.
- Which conditional Step 4 sections were included versus skipped and why (e.g. "no Detekt/ktlint section — no
  `detekt.yml` and no matching plugin alias in `gradle/libs.versions.toml`", "no Fastlane section — no `fastlane/`
  directory").
- Confirmation that the vendored `jacoco-<ver>/` CLI directory was **not** added to any ignore pattern (or, if it
  was found already tracked in the target repository, confirm it still shows as tracked via
  `git check-ignore jacoco-*/lib/jacococli.jar; echo $?` returning `1`, i.e. not ignored).
- If any file already existed: whether the user accepted or skipped the proposed changes, per file.

**Warn explicitly**:

- Review every generated/updated `.gitignore` before committing — detection is heuristic (manifest/config-file
  signals), not a guarantee every relevant path was found.
- If the repository already had files tracked under a directory this skill now proposes to ignore, `git rm -r
  --cached` that directory manually after reviewing the diff — writing `.gitignore` alone does not untrack
  already-committed files.
- The vendored `jacoco-<ver>/lib/*.jar` files must stay committed for CI's coverage-conversion fallback
  (`iru-setup-android-github-workflows`'s "Convert unit tests coverage results" step) to work without network
  access — never let a future edit to this `.gitignore` start matching them.
- Which values were inferred versus verified: the root/per-module templates (Step 2/3) are lifted verbatim from
  irurueta-android-glutils's own `.gitignore` files, which is a real, currently-maintained Android library
  repository — verified as accurate to that source as of this skill's authoring. The Detekt/ktlint and Fastlane
  additions (Step 4) are this catalog's own convention, not sourced from that reference repository, and worth a
  second look on a project with an unusual layout for either tool.

## Verification notes

Verified in `$TMPDIR/iru-verify/android/gitignore/`: wrote the composed root `.gitignore` and both module
`.gitignore` files (`lib/.gitignore`, `app/.gitignore`) into a throwaway `git init`-ed directory seeded with
`lib/build/x`, `docs/build/site/index.html`, `jacoco-0.8.13/lib/jacococli.jar`, `local.properties`,
`app/release.jks`, `google-services.json`, and `.idea/x`, then ran `git check-ignore -v` on each path:

| Path | Result |
|---|---|
| `lib/build/x` | ignored — `lib/.gitignore:1:/build` |
| `docs/build/site/index.html` | ignored — `.gitignore:docs/build/` |
| `jacoco-0.8.13/lib/jacococli.jar` | **not ignored** (confirmed — no rule matches it) |
| `local.properties` | ignored — `.gitignore:local.properties` |
| `app/release.jks` | ignored — `.gitignore:*.jks` |
| `google-services.json` | ignored — `.gitignore:google-services.json` |
| `.idea/x` | ignored — `.gitignore:.idea/` |

All seven matched the expected outcome. The `modules:` default-detection `grep`/`sed` one-liner in Step 0 was
exercised by hand against the reference repository's own `settings.gradle.kts` (`include(":app")`,
`include(":lib")`) and correctly produced `app`, `lib`.
