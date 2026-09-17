---
name: iru-setup-swift-repository
description: End-to-end bootstrap for a Swift repository of either flavor — collects `flavor` (`library`, a SwiftPM
  package, or `app`, an XcodeGen/Tuist-generated native iOS/iPadOS/macOS/watchOS app; asked via `AskUserQuestion`
  when absent and not detectable from disk), `branching` (`gitflow`/`main-only`), the project's identity
  (`package-name` for a library; `app-name` + `bundle-id-prefix` for an app; plus license and developer
  name/email/organization URL), the flavor-specific inputs (`platforms`, `min-deployment-targets`/
  `min-deployment-target`, `generator` and `signing` for an app), and the shared pipeline parameters
  (`integration-branch` `develop`, `stable-branch` `main`, `runner` `macos-26`, `open-source`, `publish` for
  libraries, `distribution` for apps, `sonar` plus its detail keys) once, then orchestrates the flavor's scaffold
  skill (`iru-setup-swift-library` / `iru-setup-apple-app`) → `iru-setup-antora` → `iru-setup-swift-gitignore` →
  `iru-setup-swift-github-workflows` → `iru-setup-changelog` → `iru-setup-readme`, in that order, via
  `iru-isolated-skill-executor`, so nothing is asked twice and no sub-skill receives a key its own Step 0 doesn't
  accept. Invoke as `/iru-setup-swift-repository`, optionally with `args` (`key: value` lines) to pre-resolve
  `flavor`, `branching`, `mode` (`new`/`existing`), `platforms`, `generator`, `signing`, `open-source`, `publish`,
  `distribution`, `sonar` (+ `sonar-organization`/`sonar-project-key`/`sonar-host-url`), `integration-branch`,
  `stable-branch`, `runner`, `xcode-version`, `release-please`, `formatter`, `min-deployment-targets`/
  `min-deployment-target`, `package-resolved`, and every identity field, skipping the matching question. In
  `mode: existing` it skips the scaffold when `Package.swift` or a generator manifest (`project.yml`/
  `Project.swift`) already exists and tells every downstream step to take its own update/gap-fill path instead
  of assuming a brand-new repository. Use whenever bootstrapping (or catching up) a Swift package or Apple app
  repository's full scaffold/docs/gitignore/CI/changelog/README pipeline in one pass, whichever flavor it is,
  instead of running six skills separately and re-answering the same questions each time.
model: haiku
---

# Setup Swift Repository

Bootstrap a brand-new (or catch up an existing) Swift repository in one pass, for whichever of two flavors it is,
by orchestrating six existing skills: the flavor's own scaffold skill (`iru-setup-swift-library` for a SwiftPM
package, or `iru-setup-apple-app` for a native iOS/iPadOS/macOS/watchOS app driven by an XcodeGen `project.yml`
or a Tuist `Project.swift`), `iru-setup-antora` (Antora documentation site), `iru-setup-swift-gitignore` (root
`.gitignore`), `iru-setup-swift-github-workflows` (CI/CD + security workflows), `iru-setup-changelog` (root
`CHANGELOG.md`), and `iru-setup-readme` (root `README.md`). This skill does not duplicate any of their logic — it
collects the shared parameters once and passes each skill only the `args` keys that skill's own Step 0 actually
accepts, so the user isn't asked the same question repeatedly and no sub-skill sees a key it doesn't recognize.

Each of Steps 5–10 invokes its sub-skill via the `iru-isolated-skill-executor` agent (`subagent_type:
"iru-isolated-skill-executor"`, always naming the full `iru-`-prefixed skill inside the prompt, e.g.
`Skill({skill: "iru-setup-swift-library", args: "..."})`) rather than calling `Skill(...)` directly — every
sub-skill re-derives whatever it needs from the filesystem this orchestrator has just written to, so only a short
completion summary needs to flow back, keeping all six sub-skills' full transcripts (and the two scaffold skills'
very long template listings) out of this orchestrator's own context. Every sub-agent is launched with
`run_in_background: false` — each step depends on the previous one's files being on disk.

## Step 0 — Resolve inputs

This skill can be invoked stand-alone (`/iru-setup-swift-repository`) or driven by another orchestrator (the
catalog's `iru-setup-repository` front door), so parse `args` first, as `key: value` lines, one per line, e.g.:

```
flavor: library
branching: gitflow
mode: new
platforms: ios, macos
open-source: yes
publish: yes
sonar: cloud
sonar-organization: example-org-github
sonar-project-key: example-org_my-example-lib
sonar-host-url: https://sonarcloud.io
integration-branch: develop
stable-branch: main
runner: macos-26
```

Recognized keys:

- **Flavor and mode**: `flavor` (`library`/`app`), `branching` (`gitflow`/`main-only`), `mode` (`new`/`existing`).
- **Shared pipeline vocabulary**: `open-source` (`yes`/`no`), `publish` (`yes`/`no` — `library` only),
  `distribution` (`none`/`internal`/`store` — `app` only), `sonar` (`cloud`/`self-hosted`/`none`) plus, only when
  set, `sonar-organization`/`sonar-project-key`/`sonar-host-url`, `integration-branch`, `stable-branch`, `runner`
  (`macos-26`/`xcode-27`), `xcode-version`, `release-please` (`yes`/`no` — `library` only).
- **Flavor-specific inputs** named in Step 3: `platforms`, `min-deployment-targets` (`library`),
  `min-deployment-target` (`app`), `generator` (`xcodegen`/`tuist` — `app` only), `signing`
  (`fastlane-match`/`api-key`/`none` — `app` only).
- **Identity fields** named in Step 2: `package-name` (`library`); `app-name`, `bundle-id-prefix` (`app`); and,
  for both, `license`, `developer-name`, `developer-email`, `organization-url`.
- **Pass-through toggles**, forwarded untouched if supplied but never asked by this orchestrator (see Steps 2, 7
  and 8): `formatter` (`swift-format`/`swiftformat` — `library` only), `package-resolved` (`commit`/`ignore`),
  and the four `security-*` opt-outs (`security-dependency-review`, `security-codeql`, `security-osv`,
  `security-gitleaks`).

Every key found here is resolved — skip the matching question in Steps 1–4. Only keys genuinely missing from
`args` still need asking. If `args` is absent or doesn't look like this format, treat everything as unset and ask
normally.

## Step 1 — Resolve the flavor, branching model and mode

Survey the repository root first — `Package.swift`, `project.yml` (XcodeGen), `Project.swift` (Tuist), and any
`*.xcodeproj`/`*.xcworkspace` — since their presence decides both `flavor` and `mode` without a question in the
common cases.

Unless `flavor` was already supplied via `args`, resolve it:

- `project.yml` or `Project.swift` exists at the root → `app` (an app repository also carries a
  `Packages/Core/Package.swift`, and may carry its own root `Package.swift` — the generator manifest wins, the
  same disambiguation `iru-setup-swift-github-workflows`'s Step 1 and `iru-swift-bump-version`'s Step 2 use).
  A root `Package.swift` with **no** generator manifest → `library`. Confirm the detected value with the user
  rather than assuming it silently.
- Only a hand-maintained `*.xcodeproj`/`*.xcworkspace` exists, with neither `project.yml` nor `Project.swift`:
  this predates any generator — `flavor` is `app`, but tell the user up front that `iru-setup-apple-app` will ask
  whether to adopt XcodeGen/Tuist going forward or stop, and that this orchestrator can't reverse-engineer the
  project for them.
- Nothing on disk yet, or genuinely ambiguous → `AskUserQuestion` with two options: **Library** (a redistributable
  SwiftPM package consumed via a tagged git URL and optionally listed on the Swift Package Index — no app target)
  / **App** (a native SwiftUI iOS/iPadOS/macOS/watchOS application whose Xcode project is generated on demand
  from an XcodeGen or Tuist manifest, distributed via TestFlight/the App Store, never published as a package).

Map the resolved `flavor` to its scaffold skill for the rest of this run:

| `flavor` | Scaffold skill | Scaffold manifest checked in Step 5 |
|---|---|---|
| `library` | `iru-setup-swift-library` | `Package.swift` |
| `app` | `iru-setup-apple-app` | `project.yml` (XcodeGen) or `Project.swift` (Tuist) |

Unless `branching` was already supplied via `args`, resolve it with `AskUserQuestion` (two options):

- **gitflow** (recommended, this catalog's house pattern) — an integration branch (`develop`) plus a stable
  branch (`main`, releases only); `iru-setup-swift-github-workflows` generates `build.yml`/`release.yml`/
  `sync.yml` (+ `.github/scripts/sync_versions.py`), and `sync.yml` opens the post-release version-bump PR back
  into the integration branch.
- **main-only** — a single stable branch; `iru-setup-swift-github-workflows` generates `build.yml`/`release.yml`
  and no `sync.yml`. Step 4's integration-branch question is skipped for this model.

If `mode` wasn't supplied via `args`, don't ask about it as an isolated question — check whether the resolved
flavor's scaffold manifest (`Package.swift` for `library`; `project.yml` or `Project.swift` for `app`) already
exists at the repository root: if it does, default to `existing` and confirm with `AskUserQuestion` (`existing`
pre-selected; `new` as the other option, noting that "new" re-runs the scaffold's own stop/gap-fill/regenerate
survey and that regenerating replaces `Package.swift` or the generator manifest wholesale, discarding hand-added
targets, dependencies and build settings); if it doesn't, default to `new` without asking further — there's
nothing on disk yet to conflict with.

## Step 2 — Collect the project's identity

**`mode: existing` with the scaffold manifest already on disk** (`Package.swift` (or the flavor's generator manifest) at the repository root, the same
check Step 5 uses to skip the scaffold): skip every identity question in this step — nothing downstream consumes
these answers once the scaffold is skipped (`iru-setup-readme` derives identity from the existing build files
itself), so asking them is a wasted question (verified in Task 53.2). Resolve `license` only if `args` supplied it,
and record in the final report that project identity was taken from the existing files rather than asked.

For any field Step 0 already resolved from `args`, use that value directly. For everything else, ask the user
directly (plain conversation — these are free-text project-identity fields, not a bounded choice). Only ask what
applies to the resolved `flavor`, using **exactly** the key names the scaffold skill reads:

- **`library`**: **package-name** — the SwiftPM package identity written to `Package(name: ...)`, e.g.
  `my-example-lib` (commonly the repository name, hyphens allowed). Don't ask for the PascalCase `<Name>` used for
  the product/target/directories — `iru-setup-swift-library` derives it itself (`my-example-lib` →
  `MyExampleLib`) and warns against passing the raw hyphenated name to `swift package init`.
- **`app`**: **app-name** — the display name, e.g. `My App` (`iru-setup-apple-app` derives the app-slug and
  directory names from it); **bundle-id-prefix** — reverse-DNS, e.g. `com.example` (the app's bundle id is
  `<bundle-id-prefix>.<app-slug>`; the watchOS companion's is `<bundle-id>.watchkitapp`, never asked).
- **Both**: **developer name**, **developer email**, **organizationUrl**. For a library they only appear in
  generated doc-comment headers (SwiftPM has no `<developers>`/`author` metadata block); for an app they populate
  each Info.plist's `NSHumanReadableCopyright` — still worth collecting once here so `iru-setup-readme` and any
  later `iru-check-license` run see consistent authorship.

Then resolve the **license** with `AskUserQuestion`, unless `args` supplied one (one consistent choice reused
across both flavors, matching the four options every other setup skill in this catalog offers; the two scaffold
skills merely differ on which they recommend first — Apache for a library, MIT for an app — so present the
recommendation that matches the resolved `flavor`):

- Apache License 2.0 (recommended for `library`) — `Apache License 2.0` / `http://www.apache.org/licenses/LICENSE-2.0.txt`
- MIT License (recommended for `app`) — `The MIT License` / `https://opensource.org/license/mit`
- No license (proprietary / all rights reserved)
- Other — ask for the license's display name and URL directly afterward

The library's **`formatter`** toggle (`swift-format`, the toolchain's bundled formatter, or the third-party
`swiftformat`) is **deliberately left unasked here**: nothing downstream needs it as an input
(`iru-setup-swift-github-workflows` always writes a `swift format lint --strict` step and accepts no `formatter`
key), so `iru-setup-swift-library` asks it itself with its `swift-format` default when invoked without it. Pass it
through only if `args` supplied it — and if it resolves to `swiftformat`, flag in Step 11 that the generated
`build.yml`'s lint step still invokes `swift format` and needs a hand edit.

## Step 3 — Collect the flavor-specific inputs

Only ask what applies to the resolved `flavor`. For any field Step 0 already resolved from `args`, use that value
directly.

- **platforms** (both flavors, `AskUserQuestion` multi-select, at least one required) — but with each scaffold's
  own vocabulary, since the two skills read different lists:
  - `library`: `ios`, `ipados`, `macos`, `watchos`, `tvos`, `visionos`, `linux` (seven values — split across two
    questions, Apple platforms first, then *tvOS / visionOS / Linux / none of these*, since `AskUserQuestion`
    allows at most four options). Relay `iru-setup-swift-library`'s own caveats when presenting them: `ios` and
    `ipados` collapse to a single `.iOS(...)` entry, and `linux` adds no `platforms:` entry at all (SwiftPM has no
    `.linux` case — Linux support is implicit whenever the code avoids Apple-only imports).
  - `app`: `ios`, `ipados`, `macos`, `watchos` only. Relay `iru-setup-apple-app`'s caveat that `ipados` is not a
    separate target — it widens the iOS target's `TARGETED_DEVICE_FAMILY` — and that `watchos` without `ios`
    produces a standalone (companion-less) watch app.
  The same list is passed verbatim to Step 5's scaffold and Step 8's workflows skill, so `Package.swift`'s
  `platforms:` array / the generator manifest's targets and CI's per-platform test destinations always agree.
- **`library` only — min-deployment-targets**: for each selected Apple platform (`ios`/`ipados` counted once,
  `macos`, `watchos`, `tvos`, `visionos`), the minimum OS version, in `iru-setup-swift-library`'s own
  `ios=17.0, macos=14.0` form. There is no universal default — ask directly, offering the current stable major
  minus one per platform as the suggestion if the user has no preference. Never asked for a `linux`-only
  selection.
- **`app` only — min-deployment-target**: a single OS version applied to every selected platform. **Deliberately
  left unasked** unless `args` supplied it: `iru-setup-apple-app` resolves its default itself from the locally
  installed simulator runtimes (Step 4 there — the bare current SDK major is *not* safe, since installed
  simulator runtimes lag it by one), which this orchestrator can't do better. Pass it through only if supplied.
- **`app` only — generator** (`AskUserQuestion`, two options): **XcodeGen** (recommended for a single-target or
  single-platform-family app — a thin, fast, single-file `project.yml`) / **Tuist** (for a modular app that has or
  will grow multiple internal SwiftPM packages beyond the scaffolded `Packages/Core`, whose module graph and
  caching pay off as packages accumulate). Collected here, not left to the scaffold, because
  `iru-setup-swift-github-workflows` also needs it (Step 8) to write the matching `xcodegen generate`/`tuist
  generate` step — even though that skill could detect it from the manifest afterward, passing it keeps both
  halves in agreement by construction.
- **`app` only — signing**: resolved in Step 4 right after `distribution`, since its recommended default depends
  on that answer.

## Step 4 — Collect the shared pipeline parameters

Ask the user directly, presenting each with its default so a plain "yes"/blank reply accepts it (skip any Step 0
already resolved from `args`, and skip the integration branch entirely when `branching: main-only`):

| Parameter | `args` key | Default | Consumed by |
|---|---|---|---|
| Integration branch | `integration-branch` | `develop` | `iru-setup-swift-github-workflows` (gitflow only) |
| Stable branch | `stable-branch` | `main` | `iru-setup-swift-github-workflows` |
| macOS runner label | `runner` | `macos-26` | `iru-setup-swift-github-workflows` (`runs-on:`) |

Notes on these, so the two halves of the pipeline can't disagree:

- **`runner`** is a CI-only parameter: `macos-26` is GitHub's stable, generally-available image (SwiftLint
  preinstalled); `xcode-27` is the newer-Xcode public-preview image label, only worth choosing when the project
  needs an Xcode 27 feature the GA image's newest Xcode lacks, with the caveat that a preview image can change
  with less notice and always needs the `brew install swiftlint` path. `iru-setup-swift-github-workflows` looks
  up the currently available labels at run time — this orchestrator just forwards the choice.
- **`xcode-version`** is *not* asked here: `iru-setup-swift-github-workflows` resolves its default from the
  chosen runner image's own `(default)`-marked Xcode row at run time. Pass it through only if `args` supplied it.
- **`release-please`** (`library` only) is *not* asked here: it defaults to `no` inside
  `iru-setup-swift-github-workflows` because this catalog already has a hand-driven release path
  (`iru-release`/`iru-swift-bump-version`). Pass it through only if `args` supplied it.

Then resolve, with `AskUserQuestion`, per this catalog's shared open-source-driven convention (skip any Step 0
already resolved):

- **open-source** — is this repository open source? Yes / No. Drives the recommended defaults below.
- **publish** — **`library` only**: does this package get distributed for other projects to depend on (a tagged
  git URL, optionally listed on the Swift Package Index via `.spi.yml`)? Default **Yes** when open-source is Yes;
  otherwise ask with **No** recommended (the Swift Package Index is a public catalog for redistributable
  open-source packages). Say plainly that `no` only omits `.spi.yml` — SwiftPM has no registry publish step to
  gate, so the workflows skill treats `publish` as informational. Never collected or passed for `app`.
- **distribution** — **`app` only**: `none`/`internal`/`store`. Default **`store`** (TestFlight + App Store
  submission lanes) when open-source is Yes; otherwise ask with **`internal`** (TestFlight internal testing only)
  recommended, `none` (local install/manual QA only) as the alternative. Never collected or passed for `library`.
- **signing** — **`app` only**, asked with the `distribution` answer in view (`AskUserQuestion`, three options):
  **`fastlane-match`** (team-shared certificates/profiles in an encrypted private git repo — recommended when more
  than one person/machine produces signed builds; needs `MATCH_GIT_URL`/`MATCH_PASSWORD`), **`api-key`** (Xcode
  automatic signing authenticated by an App Store Connect API key — recommended for a single maintainer or a
  CI-only setup; needs `APP_STORE_CONNECT_API_KEY_ID`/`_ISSUER_ID`/`_KEY_BASE64`), **`none`** (no automated
  signing; only a `test` lane). When `distribution: none`, offer `none` as the default and confirm rather than
  assuming — a signed local archive is still a valid, if unusual, wish. Warn that `signing: none` with a
  non-`none` `distribution` means nothing will produce a distributable build automatically.
- **sonar** — `cloud`/`self-hosted`/`none`. Recommend **`cloud`** when open-source is Yes; when not open source,
  state that SonarCloud is free only for open-source projects (a paid plan is required otherwise) and recommend
  **`none`**, offering **self-hosted SonarQube** as the second option. When `cloud`/`self-hosted` is chosen, also
  collect `sonar-organization`/`sonar-project-key`/`sonar-host-url` the same way both scaffold skills' own Step 2
  does (SonarCloud: suggest `<owner>-github` / `<owner>_<repo>` / `https://sonarcloud.io`, inferred from
  `git remote get-url origin`; self-hosted: ask for `sonar.host.url` directly, plus `sonar.organization` only if
  that server has organizations enabled, and `sonar.projectKey`).

These values (`open-source`, `publish`/`distribution`, `signing`, `sonar` + detail keys) are passed through
unchanged to Step 5 (the scaffold skill) and Step 8 (`iru-setup-swift-github-workflows`) so neither sub-skill
re-asks them — and so the workflows never contain a Sonar scan step for a repository with no
`sonar-project.properties`, or a TestFlight upload for a `fastlane/Fastfile` with no `beta` lane.

## Step 5 — Run the flavor's scaffold skill

If `mode: existing` (Step 1) and the flavor's scaffold manifest already exists at the repository root
(`Package.swift` for `library`; `project.yml` or `Project.swift` for `app`), skip invoking the scaffold skill
entirely — there's nothing to regenerate, and `mode: existing` means the user already confirmed they don't want
it replaced. Note in Step 11's report that the scaffold already existed and was left untouched, then continue to
Step 6 (the existing scaffold is presumed valid enough for the rest of the pipeline to build against). Otherwise,
format Steps 2–4's answers as `key: value` lines using **exactly** the keys the resolved flavor's skill accepts
(never an invented key) and invoke via `iru-isolated-skill-executor`:

```
# flavor: library
Agent({
  description: "Run iru-setup-swift-library",
  subagent_type: "iru-isolated-skill-executor",
  prompt: "Invoke Skill({skill: \"iru-setup-swift-library\", args: \"package-name: <package-name>\\n
    platforms: <platforms, comma-separated>\\nmin-deployment-targets: <ios=17.0, macos=14.0 …, omit if linux-only>\\n
    license: <license display name, or 'none'>\\ndeveloper-name: <developer-name>\\n
    developer-email: <developer-email>\\norganization-url: <organization-url>\\nopen-source: <open-source>\\n
    publish: <publish>\\nsonar: <sonar>\\nsonar-organization: <..., if set>\\nsonar-project-key: <..., if set>\\n
    sonar-host-url: <..., if set>\\nformatter: <..., only if supplied>\\nmode: <mode>\"}).
    Report back: whether Package.swift, Sources/<Name>/, Tests/<Name>Tests/, .swiftlint.yml, the formatter config,
    the DocC catalog, .spi.yml and sonar-project.properties were created fresh, gap-filled, or already existed
    (and, if so, whether the user chose to stop), the PascalCase <Name> it derived, which formatter it resolved,
    whether the swift-docc-plugin version came from a live lookup versus the recorded fallback, whether its
    swift build / swift test verification passed, and any value it resolved on its own (repository URL,
    inception year).",
  run_in_background: false
})
```

```
# flavor: app
Agent({
  description: "Run iru-setup-apple-app",
  subagent_type: "iru-isolated-skill-executor",
  prompt: "Invoke Skill({skill: \"iru-setup-apple-app\", args: \"app-name: <app-name>\\n
    bundle-id-prefix: <bundle-id-prefix>\\nplatforms: <platforms, comma-separated>\\ngenerator: <generator>\\n
    min-deployment-target: <..., only if supplied>\\ndistribution: <distribution>\\nsigning: <signing>\\n
    license: <license display name, or 'none'>\\ndeveloper-name: <developer-name>\\n
    developer-email: <developer-email>\\norganization-url: <organization-url>\\nopen-source: <open-source>\\n
    sonar: <sonar>\\nsonar-organization: <..., if set>\\nsonar-project-key: <..., if set>\\n
    sonar-host-url: <..., if set>\\nmode: <mode>\"}).
    Report back: whether the generator manifest (project.yml, or Project.swift + Tuist.swift), Packages/Core,
    the per-platform Targets/, .swiftlint.yml, .swift-format, fastlane/Fastfile and sonar-project.properties were
    created fresh, gap-filled, or already existed (and, if so, whether the user chose to stop or to adopt a
    generator over a hand-maintained .xcodeproj), the bundle id and min-deployment-target it resolved, which
    Fastfile lanes it wrote as a result of distribution/signing, which generator/tool versions came from a live
    lookup versus the recorded fallback, whether its Packages/Core swift build / swift test verification passed,
    and whether xcodegen/tuist was actually available to run generate locally.",
  run_in_background: false
})
```

Omit every `only if supplied` line whose value wasn't resolved (never send an empty key). Neither scaffold skill
accepts `branching`, `integration-branch`, `stable-branch`, `runner`, `xcode-version`, `release-please` or
`package-resolved` — those are Steps 7–8's alone, so never send them here. `publish` and `formatter` are sent
only for `library`; `generator`, `signing`, `distribution` and `min-deployment-target` only for `app`.

Each scaffold skill parses these itself (its own Step 0) and only asks the user about anything genuinely left
out — `AskUserQuestion` surfaces to the user the same way whether invoked directly or from inside this
sub-agent. If it reports that its files already existed and the user chose to stop, stop this skill here too —
there's no coherent package or project to build Antora docs or CI workflows around yet. For `app`, warn the user
before launching it that `xcodegen`/`tuist` are typically installed via `brew`, and that the scaffold verifies
only the shared `Packages/Core` package with `swift build`/`swift test` when the generator isn't available
locally — a real `.xcodeproj` build is then first exercised in CI.

## Step 6 — Run `iru-setup-antora`

Invoke via `iru-isolated-skill-executor`: `Agent({description: "Run iru-setup-antora", subagent_type:
"iru-isolated-skill-executor", prompt: "Invoke Skill({skill: \"iru-setup-antora\"}) with no args — it takes none,
deriving the Antora component name, title, and version itself from the repository (the name: in Package.swift or
in the XcodeGen/Tuist manifest, a README heading if one exists, git tags/GitHub releases). Report back: which
files/pages were created vs. already present, and whether the site build succeeded.", run_in_background: false})`.

Run this *before* Step 8, not after: `iru-setup-antora` is quick to detect as "already done", and
`iru-setup-swift-github-workflows`'s own survey (Step 1 there) checks whether `docs/antora.yml`/
`docs/antora-playbook.yml` exist before generating its DocC + Antora Pages deploy job — running Antora setup
first means that check finds everything in place instead of flagging a gap. In a repository with no tags or
releases yet, `iru-setup-antora` may ask for a starting version; answer `1.0.0` (the version
`iru-swift-bump-version`/`sync.yml` will later manage) rather than inventing another.

## Step 7 — Run `iru-setup-swift-gitignore`

Invoke via `iru-isolated-skill-executor`: `Agent({description: "Run iru-setup-swift-gitignore", subagent_type:
"iru-isolated-skill-executor", prompt: "Invoke Skill({skill: \"iru-setup-swift-gitignore\", args: \"flavor:
<flavor>\\npackage-resolved: <..., only if supplied>\"}) — it detects mode itself from whether a root .gitignore
already exists, and detects the generator manifest, fastlane/, the Antora config and the DocC catalog directly
from disk. Report back only whether .gitignore was created fresh or, if it already existed, whether the user
accepted or skipped the proposed diff, and which package-resolved choice was applied.",
run_in_background: false})`.

`flavor` is passed so the skill's `Package.resolved` question (commit it for an app, ignore it for a library)
carries the right recommendation without re-detecting the project shape; **`package-resolved` itself is
deliberately left for it to ask** unless `args` supplied it — it's a one-time, single question with a
flavor-informed recommendation, and nothing else in this pipeline depends on the answer. `mode` is deliberately
*not* passed: the skill's own `.gitignore`-presence check is the more precise signal for this file (a `mode: new`
repository can still carry a hand-written `.gitignore` that deserves the diff-and-approve path, never a silent
overwrite). Run this after Steps 5–6, not before: detection depends on the scaffold's `project.yml`/
`Project.swift`/`fastlane/` signals and on the Antora config Step 6 just wrote. Run it *before* Step 8, so
`.build/`, `DerivedData/`, `*.xcresult`, the generated `*.xcodeproj`/`*.xcworkspace`, signing material and the
Antora build output are already ignored before CI-generated reports show up locally.

## Step 8 — Run `iru-setup-swift-github-workflows`

Format Steps 1–4's answers as `key: value` lines and invoke via `iru-isolated-skill-executor`:

```
Agent({
  description: "Run iru-setup-swift-github-workflows",
  subagent_type: "iru-isolated-skill-executor",
  prompt: "Invoke Skill({skill: \"iru-setup-swift-github-workflows\", args: \"flavor: <flavor>\\n
    platforms: <platforms, comma-separated>\\nbranching: <branching>\\n
    integration-branch: <integration-branch, gitflow only>\\nstable-branch: <stable-branch>\\nrunner: <runner>\\n
    xcode-version: <..., only if supplied>\\ngenerator: <generator, app only>\\nsigning: <signing, app only>\\n
    release-please: <..., library only, only if supplied>\\nopen-source: <open-source>\\n
    publish: <publish, library only>\\ndistribution: <distribution, app only>\\nsonar: <sonar>\\n
    sonar-organization: <..., if set>\\nsonar-project-key: <..., if set>\\nsonar-host-url: <..., if set>\\n
    mode: <mode>\"}). Report back: whether build.yml, release.yml, sync.yml + .github/scripts/sync_versions.py
    (gitflow only), security.yml, .github/dependabot.yml and lcov_to_sonar_generic.py (library + sonar only) were
    created fresh, updated, or already existed (and, if so, whether the user chose to stop), the runner label and
    xcode-version it resolved, any open gap it flagged (missing docs/antora.yml, a Packages/Core without the
    swift-docc-plugin dependency, README/version wording not matching sync_versions.py, a <team-id> still to
    supply), and the full required-secrets/environments table it produced for this flavor/branching/options.",
  run_in_background: false
})
```

Omit `integration-branch` when `branching: main-only`, `publish`/`release-please` for `app`, and `generator`/
`signing`/`distribution` for `library` (never send a key the flavor doesn't use). The four `security-*` keys are
deliberately never passed unless `args` supplied them — each defaults to `yes` inside
`iru-setup-swift-github-workflows` itself, and this orchestrator doesn't ask about them; note this once in
Step 11's report rather than re-asking per run. The shared `license`/`developer-*`/`organization-url` keys are
likewise never passed here: the workflows skill accepts them only to tolerate a full shared-args set and would
report them as "supplied but unused".

If it reports that the workflow files already existed and the user chose to stop, note that in Step 11's report
rather than treating it as a failure of this skill — the scaffold, the Antora docs, and the `.gitignore` from
Steps 5–7 are still valid on their own.

## Step 9 — Run `iru-setup-changelog`

Invoke via `iru-isolated-skill-executor`: `Agent({description: "Run iru-setup-changelog", subagent_type:
"iru-isolated-skill-executor", prompt: "Invoke Skill({skill: \"iru-setup-changelog\"}) with no args — it takes
none, working entirely from the repository's own git tag/GitHub Release history. Report back only whether
CHANGELOG.md was created (and the version range reconstructed) or already existed.", run_in_background: false})`.
Position relative to Steps 5–8 doesn't matter functionally — it's independent of all of them. In `mode: new`
(no tags yet) it either bootstraps a minimal `## [Unreleased]`-only file or stops per the user's choice; in
`mode: existing`, real tag/release history may exist to backfill. If `CHANGELOG.md` already exists, it stops
immediately and reports that regardless of `mode` — not a failure of this skill, just something to note in
Step 11's report. Running it before `iru-setup-readme` means the README's Documentation section sees it already
in place, and — for a gitflow library — that `sync.yml`'s `sync_versions.py` has a `CHANGELOG.md` to roll the
`[Unreleased]` heading in after each release.

## Step 10 — Run `iru-setup-readme`

Invoke via `iru-isolated-skill-executor`: `Agent({description: "Run iru-setup-readme", subagent_type:
"iru-isolated-skill-executor", prompt: "Invoke Skill({skill: \"iru-setup-readme\", args: \"sonar: <sonar>\"}) — `sonar` is the only key it accepts (with `none` it suppresses Sonar badges/links even if Sonar config exists on disk),
deriving everything it needs by exploring the repository directly (Package.swift or the XcodeGen/Tuist manifest,
the Antora docs, .gitignore, the workflows and sonar-project.properties, and CHANGELOG.md). Report back only
which sections were included vs. omitted and why, and — for a library — whether the installation snippet it
wrote uses the SwiftPM .package(url: \\\"<repository-url>\\\", from: \\\"<version>\\\") shape.",
run_in_background: false})`. Run this last, after every other skill, so its badges/status-table/
documentation-links sections see the finished state of Steps 5–9 instead of a sparser mid-run snapshot. In
`mode: new`, most CI/Sonar/changelog-derived sections will still be sparse or absent (no commits/tags/CI runs
yet) — expected; `iru-setup-readme` omits what it can't confirm rather than inventing it. `README.md` may or may
not already exist depending on `mode`; `iru-setup-readme`'s own approval step handles that on its own — nothing
further to confirm here.

For a gitflow **library**, the README's dependency snippet is what `sync.yml`'s `sync_versions.py` rewrites after
each release — if `iru-setup-readme` reports a snippet shape other than the `.package(url:from:)` line
`iru-setup-swift-github-workflows` recorded in Step 8 (or no SwiftPM snippet at all), flag the mismatch in
Step 11 so the user reconciles one of the two before the first release.

## Step 11 — Report

Summarize the outcome of all six delegated skills together: the resolved `flavor`, `branching` and `mode`, the
project identity and license, the flavor-specific inputs (`platforms`, `min-deployment-targets`/
`min-deployment-target`, `generator`, `signing`), the pipeline parameters used (the Step 4 table with the values
actually applied), and which of the scaffold's own files (`Package.swift` + `Sources/`/`Tests/`, or the generator
manifest + `Packages/Core` + `Targets/` + `fastlane/Fastfile`, plus `.swiftlint.yml`, the formatter config,
`.spi.yml`, `sonar-project.properties`), the Antora docs site, the `.gitignore`, the workflow files (`build.yml`/
`release.yml`/`sync.yml` + `sync_versions.py`, or `build.yml`/`release.yml`, plus `security.yml` and
`.github/dependabot.yml`), `CHANGELOG.md`, and `README.md` were created, updated, or left untouched (per any stop
choice in Steps 5 or 8, or a `mode: existing` skip in Step 5).

State explicitly which of publishing/distribution and Sonar analysis were wired, or deliberately omitted and why:

- **`open-source`**: yes/no, as resolved in Step 4.
- **`publish`** (`library`): whether `.spi.yml` was written — and restate that SwiftPM has no registry publish
  job, so `release.yml` only validates the semver tag and `swift package dump-package` either way.
- **`distribution`**/**`signing`** (`app`): which Fastfile lanes exist as a result (`test` only; `test`+`build`+
  `beta`; or `test`+`build`+`beta`+`release`, plus `notarize_release` for `macos` with a real signing method) and
  which `release.yml` archive/export/TestFlight/notarization steps were generated; `store`/non-`none` unless the
  user opted out (or the project isn't open source and declined it), stated plainly rather than left implicit.
- **`sonar`**: `cloud`/`self-hosted`/`none`, and whether `sonar-project.properties`, the coverage-conversion
  step (`lcov_to_sonar_generic.py` for a library, `xccov-to-sonarqube-generic.sh` for an app) and the
  `SonarSource/sonarqube-scan-action` step were included — if `none`, note whether that's the expected
  non-open-source default or a direct user choice.
- **`runner`**: `macos-26` or `xcode-27`, restating the GA-vs-preview tradeoff, and the `xcode-version` the
  workflows skill resolved from it.
- **Toolchain versions**: which came from a live lookup versus the recorded September 2026 fallback, as reported
  by the scaffold (`swift-docc-plugin`, XcodeGen/Tuist) and the workflows skill (action tags, runner image).

Reproduce the **consolidated required-secrets/settings table** `iru-setup-swift-github-workflows` reported in
Step 8 verbatim (it's already scoped to exactly this flavor/branching/options — don't re-derive or expand it):
`SONAR_TOKEN` for a non-`none` `sonar`; `MATCH_GIT_URL`/`MATCH_PASSWORD` for `signing: fastlane-match`;
`APP_STORE_CONNECT_API_KEY_ID`/`APP_STORE_CONNECT_API_KEY_ISSUER_ID`/`APP_STORE_CONNECT_API_KEY_BASE64` for
`signing: api-key` (and also, regardless of `signing`, for notarization when `macos` is selected); `GITHUB_TOKEN`
is automatic. Then its repository-settings notes: GitHub Pages source set to **GitHub Actions** for the docs
deploy, and — gitflow only — "Workflow permissions" allowing GitHub Actions to create pull requests for
`sync.yml`. For an app, add the Apple Developer Team ID placeholder the workflows skill leaves for the user to
supply, and the `fastlane match` certs repository / App Store Connect API key that must exist before the first
signed build.

List every decision made on the user's behalf: the license question's flavor-dependent recommendation (Step 2);
leaving `formatter` for `iru-setup-swift-library` to ask (Step 2); `min-deployment-target` resolved by
`iru-setup-apple-app` from the local simulator runtimes rather than asked (Step 3); `xcode-version` resolved by the
workflows skill from the runner image and `release-please` left at its `no` default (Step 4); `signing: none`
offered as the default when `distribution: none` (Step 4); `iru-setup-swift-gitignore`'s `mode` left to its own
detection and `package-resolved` left for it to ask (Step 7); and the four `security-*` flags left at their `yes`
default (Step 8).

Finish with an explicit **Warn explicitly** block, repeating each sub-skill's own closing warning:

- **Review every generated/updated file before building, committing, or relying on CI.** Confirm the license
  matches an actual `LICENSE` file at the root if one was chosen (`iru-check-license` can generate one and
  backfill Swift headers), and that `swift build && swift test` (library) or `xcodegen generate`/`tuist generate`
  followed by `xcodebuild test` (app) succeeds locally — the generator itself is typically a `brew install` the
  scaffold never performs.
- Branch names, the Apple Developer Team ID, and the signing/distribution setup in the workflows were inferred
  from the resolved parameters and the scaffold's files — because this pipeline handles signing keys and can
  upload to TestFlight/the App Store, a wrong assumption there signs or ships the wrong thing. Do a
  `workflow_dispatch` dry run before trusting a real release.
- Every secret in the table above, and the matching SonarCloud project / Apple Developer Program membership /
  `fastlane match` certs repository / App Store Connect API key, must already exist before CI can pass — nothing
  in this pipeline creates or stores any account or credential.
- If `formatter: swiftformat` was supplied, the generated `build.yml` still runs `swift format lint --strict` and
  needs a matching hand edit (and a `brew install swiftformat` step) before its lint job passes.
- Every toolchain and action version was resolved via a run-time lookup or its recorded September 2026
  fallback — re-check them (Dependabot's `swift` + `github-actions` entries will start proposing bumps) before
  relying on this scaffold long-term. The real `xcodegen`/`tuist` run, SwiftLint, the Sonar scan, Fastlane's
  `match`/`pilot`, TestFlight/App Store uploads and notarization are never exercised locally by any of the six
  skills — only their YAML and the shared SwiftPM package build are validated.
