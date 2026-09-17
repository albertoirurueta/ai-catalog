---
name: iru-setup-apple-app
description: Scaffold a new native Apple app (iOS/iPadOS/macOS/watchOS, SwiftUI, Swift 6) at the repository root —
  a generator manifest (XcodeGen's `project.yml`, or Tuist's `Project.swift` + `Tuist.swift`) declaring one
  application target per selected platform with a SwiftUI `App` entry point, `MARKETING_VERSION`/
  `CURRENT_PROJECT_VERSION`, `SWIFT_STRICT_CONCURRENCY = complete`, and Info.plist keys, a shared `Packages/Core`
  local SwiftPM package for testable business logic, a Swift Testing unit-test target and an XCUITest UI-test
  target per platform, watchOS companion-app wiring when both `ios` and `watchos` are selected, `.swiftlint.yml`,
  `.swift-format`, a `fastlane/Fastfile` with lanes gated by `signing`/`distribution`, and `sonar-project.properties`
  (omitted when `sonar: none`). The generated `.xcodeproj`/`.xcworkspace` is never committed — it's regenerated on
  demand by `xcodegen generate`/`tuist generate` and gitignored by the companion `iru-setup-swift-gitignore` skill.
  Invoke as `/iru-setup-apple-app`. Accepts pre-resolved inputs via `args` (`key: value` lines) — `app-name`,
  `bundle-id-prefix`, `platforms` (multi-select: `ios`, `ipados`, `macos`, `watchos` — `ipados` alone or alongside
  `ios` widens the iOS target's `TARGETED_DEVICE_FAMILY` rather than adding a second target), `generator`
  (`xcodegen`/`tuist` — asked when unset, with XcodeGen recommended for a single-target app and Tuist for a
  modular, multi-package app), `min-deployment-target`, `distribution` (`none`/`internal`/`store`), `signing`
  (`fastlane-match`/`api-key`/`none`), `license`, `developer-name`, `developer-email`, `organization-url`,
  `open-source`, `sonar` (+ `sonar-organization`/`sonar-project-key`/`sonar-host-url`), and `mode` (`new`/
  `existing`) — so an orchestrating skill can supply them without re-prompting; invoked stand-alone, it asks
  `open-source` first and derives the `sonar` question's default from that answer. If `project.yml` or
  `Project.swift` already exists at the repository root, asks the user whether to stop or regenerate (`mode:
  existing` skips straight to gap-fill: create only what's missing, never overwrite hand-written app/test source).
  Every generator/tool version is looked up at run time (GitHub releases API, and the Homebrew formula/cask JSON
  API — reachable over plain HTTPS without `brew` itself installed), falling back to the versions recorded in this
  file when a lookup fails. Equivalent to `iru-setup-android-app`/`iru-setup-react-native-app` for the native Apple
  stack; use `iru-setup-swift-library` instead for a pure SwiftPM library with no app target. Use whenever a new
  native iOS/iPadOS/macOS/watchOS application needs its project generator manifest, shared package, test targets,
  lint/format config, and Fastlane/Sonar tooling bootstrapped from this house template, instead of hand-configuring
  each Xcode build setting.
model: haiku
---

# Setup Apple App

Generate a complete, buildable native Apple application scaffold — a project-generator manifest (XcodeGen's
`project.yml`, or Tuist's `Project.swift` + `Tuist.swift`) declaring one application target per selected platform,
a shared `Packages/Core` local SwiftPM package that holds all testable business logic, per-platform Swift Testing
unit-test and XCUITest UI-test targets, lint/format config, a gated `fastlane/Fastfile`, and `sonar-project.properties`
— from explicit example templates embedded in this skill (Step 5).

This skill never writes application binaries to source control: `.xcodeproj`/`.xcworkspace` are always generator
output, regenerated on demand (`xcodegen generate` or `tuist generate`) and gitignored — the companion
`iru-setup-swift-gitignore` skill covers this, run it right after this one if it hasn't run yet. This skill also
never runs `xcodegen`/`tuist` itself when neither binary is installed (Step 7 says exactly what that means for
verification) — it only ever writes the manifest text; the person running this skill installs the generator
(`brew install xcodegen` / `brew install tuist`, or `mint run …`) before their first `generate`.

## Step 0 — Resolve inputs

This skill can be invoked stand-alone (`/iru-setup-apple-app`) or as a step inside another skill (e.g. a future
`iru-setup-apple-repository` or the catalog's `iru-setup-repository` front door), which resolves these same inputs
itself and passes them through `args` as `key: value` lines, one per line, e.g.:

```
app-name: My App
bundle-id-prefix: com.example
platforms: ios,ipados,watchos
generator: xcodegen
min-deployment-target: 26.0
distribution: store
signing: fastlane-match
license: MIT License
developer-name: Jane Doe
developer-email: jane@example.com
organization-url: https://github.com/example-org
open-source: yes
sonar: cloud
sonar-organization: example-org-github
sonar-project-key: example-org_my-app
sonar-host-url: https://sonarcloud.io
mode: new
```

Parse any such lines from `args` now. Every field found here is resolved — skip asking about it in Step 2. Only
fields genuinely missing from `args` still need a question. If `args` is absent or doesn't look like this format,
treat everything as unset and ask normally.

Recognized keys: `app-name`, `bundle-id-prefix` (reverse-DNS, e.g. `com.example` — the app's own bundle id is this
plus a slugified `app-name`, e.g. `com.example.myapp`), `platforms` (comma-separated subset of `ios`, `ipados`,
`macos`, `watchos` — see Step 2 for how `ipados` combines with `ios`), `generator` (`xcodegen`/`tuist`),
`min-deployment-target` (a single OS version number applied to every selected platform, e.g. `26.0` — default
looked up in Step 4), `distribution` (`none`/`internal`/`store`), `signing` (`fastlane-match`/`api-key`/`none`),
`license`, `developer-name`, `developer-email`, `organization-url`, `open-source` (`yes`/`no`), `sonar`
(`cloud`/`self-hosted`/`none`) plus, only when `sonar` is `cloud` or `self-hosted`, `sonar-organization`/
`sonar-project-key`/`sonar-host-url`, and `mode` (`new`/`existing`).

`mode: existing` is this catalog's shared signal (set by a front door that already ran `iru-explore` and knows this
is an established repository) that Step 1 should skip its stop-or-regenerate question entirely and go straight to
gap-fill: create only whatever files from Step 5 are genuinely missing, and leave every file that already exists
untouched. `mode: new` or an unset `mode` follows Step 1's normal survey instead.

## Step 1 — Survey the repository

Check for `project.yml` and `Project.swift` at the repository root.

- **Neither exists**: skip straight to Step 2. There is nothing to preserve.
- **One of them exists**: this skill (or a hand-written equivalent) already owns this scaffold. Warn the user it
  will be regenerated, then:
  - **`mode: existing` was resolved in Step 0**: skip the question below — go straight to **gap-fill**: create only
    the files from Step 5 that are genuinely missing (never touch an existing SwiftUI view, an existing test file,
    or hand-added target sources beyond the one placeholder app entry point/test this skill creates originally);
    note in Step 8's report which files were left alone because they already existed.
  - **Otherwise**: use `AskUserQuestion` with two options:
    - **Stop** — leave everything untouched. Report this and end here.
    - **Update** — regenerate the manifest (`project.yml` or `Project.swift`+`Tuist.swift`), `Packages/Core/Package.swift`,
      `.swiftlint.yml`, `.swift-format`, `fastlane/Fastfile`, and `sonar-project.properties` from this skill's
      templates, but never touch any file under `Targets/*/Sources`, `Targets/*/Tests`, `Targets/*/UITests`, or
      `Packages/Core/Sources`/`Packages/Core/Tests` beyond the placeholder files this skill created originally
      (detect by exact content match against Step 5's templates before overwriting any Swift file). Tell the user
      up front that regenerating the manifest replaces the whole file — any target, scheme, or build-setting
      customization beyond what Step 5 shows will be lost unless re-added afterward (call this out again in Step 8).
- **Only a hand-maintained `.xcodeproj`/`.xcworkspace` exists, with neither `project.yml` nor `Project.swift`**:
  this isn't this skill's scaffold — it's a project that predates any generator. Warn the user explicitly and ask
  whether to adopt XcodeGen/Tuist going forward (this skill can then write a manifest describing the *existing*
  targets as a starting point, best-effort) or stop. Don't attempt to reverse-engineer the `.xcodeproj` file
  automatically — confirm the target list with the user first.

## Step 2 — Collect the required inputs

For any field Step 0 already resolved from `args`, use that value directly and don't ask about it again. For
everything else, ask the user directly (plain conversation, pre-filling defaults found in Step 1 if updating an
existing scaffold):

- **app-name** — the display name, e.g. `My App` (written to each target's `CFBundleDisplayName` and used to
  derive the app-slug for the bundle id and directory names, e.g. `myapp`).
- **bundle-id-prefix** — reverse-DNS, e.g. `com.example`. The iOS/iPadOS/macOS target's bundle id is
  `<bundle-id-prefix>.<app-slug>`; the watchOS companion target (only when both `ios`/`ipados` and `watchos` are
  selected) is `<bundle-id-prefix>.<app-slug>.watchkitapp` — a distinct, nested id is required by Apple's watch-app
  submission rules even for the modern single-target (extension-free) watch app model this skill generates.
- **platforms** — bounded multi-select (`AskUserQuestion`, at least one required): `ios`, `ipados`, `macos`,
  `watchos`.
  - **`ipados` is not a separate Xcode target.** Selecting it alongside `ios` widens the one iOS application
    target's `TARGETED_DEVICE_FAMILY` to `"1,2"` (iPhone + iPad) instead of `"1"` (iPhone only). Selecting `ipados`
    **without** `ios` still produces exactly one iOS-platform target, just with `TARGETED_DEVICE_FAMILY` set to
    `"2"` alone (iPad only) — the destination platform is still `iOS` (there is no separate "iPadOS" SDK/platform
    value in Xcode). Say this explicitly back to the user so the choice isn't misread as adding a fourth target.
  - `macos` and `watchos` each produce their own, fully separate application target (different platform,
    different `deploymentTarget`, different Info.plist).
  - `watchos` **without** `ios`/`ipados` also selected produces a standalone watch app (no `WKCompanionAppBundleIdentifier`,
    no embed wiring) — state this is unusual (nearly every shipped watch app has an iOS companion) but supported.
- **generator** — `xcodegen` or `tuist`, asked with a stated recommendation when unset: **XcodeGen** for a
  single-target (or single-platform-family) app — it's a thin, fast, single-file-manifest wrapper with the
  smallest learning curve; **Tuist** for a modular app that already has (or will grow) multiple internal SwiftPM
  packages beyond the one shared `Packages/Core` this skill scaffolds, since Tuist's own module graph, caching, and
  `tuist generate --no-open` workflow pay off once there's more than one internal package to wire together. This
  skill's own templates (Step 5) produce an equivalent single `Packages/Core` package either way — the
  recommendation is about which tool scales better as *more* packages get added later, not a difference in what
  gets generated today.
- **min-deployment-target** — a single OS version number (e.g. `26.0`) applied to every selected platform's
  `deploymentTarget`/`deploymentTargets`. Default: looked up in Step 4 (the current major SDK version minus one,
  which is what's actually installed as a simulator runtime — see Step 4's note on why the bare current SDK major
  is *not* a safe default). Offer that looked-up value as the default rather than asking open-endedly; macOS and
  watchOS share the same numeric major as iOS under Apple's unified year-based versioning (confirmed locally:
  Xcode 27 ships iOS/macOS/watchOS/tvOS/visionOS SDKs all at major `27`), so one value covers every platform.
- **Developer name**, **developer email**, **organizationUrl** — recorded in Step 8's report and in each Info.plist's
  `NSHumanReadableCopyright`.

Then, unless Step 0 already resolved a `license` value from `args`, ask about the **license** with
`AskUserQuestion` (mirrors this catalog's other setup skills):

- MIT License (recommended for app source not meant for redistribution as a library)
- Apache License 2.0
- No license (proprietary / all rights reserved)
- Other — ask for the license's display name and URL directly afterward

If a license is chosen (anything but "No license"), remind the user in Step 8 to also add a matching `LICENSE`
file at the repository root if one doesn't exist yet — `iru-check-license` can verify/backfill source headers
against it once it's there.

Then resolve `open-source`, `sonar`, `distribution`, and `signing` — skip any of the four Step 0 already resolved
from `args`. When invoked stand-alone with none of them pre-resolved, ask `open-source` *first* (`AskUserQuestion`:
yes/no) and derive the recommended default for `sonar` from that answer, per this catalog's shared convention:

- **open-source** — is this repository open source? Yes / No.
- **sonar** — whether to wire up a SonarQube/SonarCloud scan (`sonar-project.properties`, typically consumed by a
  CI workflow such as `iru-setup-swift-github-workflows`, so it's worth setting up here even if that workflow comes
  later). Recommend **SonarCloud** (`cloud`) when open-source is Yes; when not open source, state that SonarCloud
  is free only for open-source projects (a paid plan is required otherwise) and recommend **None** (`none`),
  offering **self-hosted SonarQube** as the second option:
  - `cloud` — ask for the `sonar.organization` key, offering `<owner>-github` (the owner parsed in Step 3) as the
    suggested default. Default `sonar.projectKey` to `<owner>_<repo>` and `sonar.host.url` to
    `https://sonarcloud.io`, confirming both with the user rather than assuming silently.
  - `self-hosted` — ask for `sonar.host.url` directly (no sensible default), plus `sonar.organization` only if that
    server has organizations enabled, and `sonar.projectKey`.
  - `none` — skip `sonar-project.properties` entirely (Step 5/6).
- **distribution** — `none`/`internal`/`store`:
  - `none` — builds are for local install/manual QA only via Xcode or a direct `xcodebuild archive`. No TestFlight/
    App Store lanes are written to the Fastfile; `signing` still matters for whether even a locally-run archive can
    be code-signed (see below).
  - `internal` — TestFlight internal testing is the target. The Fastfile gets a `beta` lane
    (`build_app` + `upload_to_testflight`); no public App Store submission lane.
  - `store` — full App Store Connect production submission is intended. The Fastfile gets both the `beta` lane and
    a `release` lane (`upload_to_app_store`/`deliver`); Step 8 flags the App Store Connect credentials this will
    need either way.
- **signing** — `fastlane-match`/`api-key`/`none`, asked with the distribution answer in view (skip the question
  and default to `none` outright when `distribution: none` was chosen and the user doesn't want a signed local
  archive either — confirm this rather than assuming):
  - **`fastlane-match`** — team-shared distribution certificates and provisioning profiles, stored encrypted in a
    private git repo and synced via `fastlane match`. Recommended when more than one person/machine needs to
    produce signed builds (the common case for a team). Needs a `MATCH_GIT_URL` (the certs repo) and
    `MATCH_PASSWORD` (the repo's encryption passphrase) as CI secrets — this skill never creates that certs repo or
    generates certificates itself.
  - **`api-key`** — no shared cert repo; Xcode's automatic signing (`-allowProvisioningUpdates`) manages
    certificates/profiles on demand, authenticated by an **App Store Connect API key** (a `.p8` key file, its Key
    ID, and the Issuer ID) instead of an Apple ID + two-factor prompt. Recommended for a single-maintainer project
    or a CI-only signing setup where nobody wants to manage a certs repo. Needs
    `APP_STORE_CONNECT_API_KEY_ID`/`APP_STORE_CONNECT_API_KEY_ISSUER_ID`/`APP_STORE_CONNECT_API_KEY_BASE64` as CI
    secrets.
  - **`none`** — no automated signing at all. The Fastfile only gets a `test` lane; any archive/export is done by
    hand in Xcode with whatever signing identity is locally available. Choosing this while `distribution` isn't
    `none` is valid but unusual — warn the user in Step 8 that nothing in this scaffold will produce a distributable
    build automatically.

## Step 3 — Infer repository information

Don't ask for these — derive them from the current repository, the same way `iru-setup-java-library` and
`iru-setup-android-app` do:

- **Owner/repo and host**: parse `git remote get-url origin` (handles both `git@host:owner/repo.git` and
  `https://host/owner/repo.git` forms). Used for Step 2's `sonar.organization`/`sonar.projectKey` defaults. If
  there's no `origin` remote yet, ask the user directly instead of leaving these blank.

## Step 4 — Look up toolchain versions

Every version below must be looked up at run time; fall back to the value in this table (what this skill's author
actually observed in September 2026, against Xcode 27.0 / Swift 6.4) only when the lookup fails, and say so
explicitly in Step 8's report.

| Component | Lookup | September 2026 fallback |
|---|---|---|
| Xcode / Swift (informational, never installed by this skill) | `xcodebuild -version`, `swift --version` | Xcode `27.0` (build `27A266a`), Swift `6.4` |
| Current SDK major (ceiling, **not** the safe default — see the note below) | `xcodebuild -showsdks` (read the `iOS`/`macOS`/`watchOS` SDK line's version) | `27.0` across iOS/macOS/watchOS/tvOS/visionOS — confirmed all share the same major under Apple's unified year-based versioning |
| `min-deployment-target` default (the actual safe default) | `xcrun simctl list runtimes available` — use the highest *installed simulator runtime* major, not the SDK major | `26.0` — **confirmed locally**: Xcode 27's SDK is `27.0`, but the only installed simulator runtimes are `iOS/watchOS/tvOS 26.4`; targeting the bare SDK major as a deployment target would make the scaffold un-runnable on every locally available simulator |
| XcodeGen | `gh api repos/yonaskolb/XcodeGen/releases/latest --jq .tag_name`, or `https://formulae.brew.sh/api/formula/xcodegen.json` (`.versions.stable`) — both work without `brew`/`gh` installed as long as the underlying HTTPS endpoint is reachable | `2.46.0` — **live-confirmed during this skill's verification**, both lookups agreed |
| Tuist | **Do not** trust `gh api repos/tuist/tuist/releases/latest` alone (see the note below) — prefer `https://formulae.brew.sh/api/cask/tuist.json` (`.version`) | `4.208.0` — **live-confirmed during this skill's verification** via the Homebrew cask JSON API |
| SwiftLint | `https://formulae.brew.sh/api/formula/swiftlint.json` (`.versions.stable`), or `gh api repos/realm/SwiftLint/releases/latest --jq .tag_name` | `0.65.1` |
| `swift format` (toolchain-bundled formatter — never installed separately) | n/a — ships with the Swift toolchain itself | tracks the Swift version above (`6.4`) |
| SwiftFormat (nicklockwood's third-party tool — only relevant if a project prefers it over the bundled `swift format`) | `https://formulae.brew.sh/api/formula/swiftformat.json` (`.versions.stable`) | `0.63.0` |
| xcbeautify | `https://formulae.brew.sh/api/formula/xcbeautify.json` (`.versions.stable`) | `3.2.1` |
| Periphery (unused-code scan, opt-in via `.periphery.yml` — not written by this skill) | `https://formulae.brew.sh/api/formula/periphery.json` (`.versions.stable`) | `3.8.0` |
| Fastlane (gem) | `gem list -r fastlane --remote` (no install — this just queries the RubyGems index), or `https://rubygems.org/api/v1/versions/fastlane/latest.json` | `2.240.1` |

**Tuist's GitHub releases are not a simple "latest tag" — confirmed while verifying this skill.** `tuist/tuist` is a
monorepo whose `releases` endpoint mixes the CLI's own tags (`4.209.0-canary.*` prereleases sorted first),
unrelated component tags (`server@1.341.0`, `xcresult-processor-image@0.149.0`, even a stray `helm@0.125.0` as the
API's reported `"latest"` release), and no clean non-prerelease CLI tag near the top of that list at all. The
Homebrew cask JSON API (`formulae.brew.sh/api/cask/tuist.json`) is the reliable source instead — it reports the
real current stable release (`4.208.0`, matching the version Tuist's own installer/Homebrew formula ships) and
needs no GitHub API pagination or prerelease filtering. **This same Homebrew JSON API works for every tool in the
table above even though `brew` itself is not installed** — it's a plain HTTPS JSON endpoint
(`formulae.brew.sh/api/formula/<name>.json` or `.../api/cask/<name>.json`, reading `.versions.stable` or
`.version`), not a `brew` CLI call; prefer it over scraping GitHub releases whenever a project's release-tagging
convention (like Tuist's) makes the GitHub API noisy.

## Step 5 — Reference templates

These templates are genericized (no real repository/org/person names; only `<placeholder>` markers) and were
verified as far as this skill's own local environment allows — see Step 7 and "Known quirks / verification notes"
for exactly what ran versus what's syntax-only. Substitute using Steps 2–4; keep everything else exactly as shown
unless a platform/opt-in note below says otherwise.

### `<placeholder>` resolution table

| Placeholder | Source |
|---|---|
| `<app-name>` | Step 2 |
| `<app-slug>` | Slugified `<app-name>` (lowercase, alphanumeric only), derived in Step 2 |
| `<bundle-id-prefix>` | Step 2 |
| `<bundle-id>` | `<bundle-id-prefix>.<app-slug>` |
| `<watch-bundle-id>` | `<bundle-id-prefix>.<app-slug>.watchkitapp` — only when `watchos` + (`ios`/`ipados`) are both selected |
| `<min-deployment-target>` | Step 2/4 |
| `<marketing-version>` | `1.0.0` (a fresh scaffold's starting version; `iru-swift-bump-version` rewrites this later) |
| `<current-project-version>` | `1` |
| `<owner>` / `<repo>` | Step 3 |
| `<sonar-organization>` / `<sonar-project-key>` / `<sonar-host-url>` | Step 2 |
| `<developer-name>` / `<developer-email>` / `<organization-url>` | Step 2 |
| `<xcodegen-version>` / `<tuist-version>` / … | Step 4 |

### Directory layout this skill produces

```
project.yml                        # XcodeGen manifest (generator: xcodegen)
Project.swift                      # Tuist manifest        (generator: tuist)
Tuist.swift                        # Tuist config           (generator: tuist)
Packages/
  Core/
    Package.swift
    Sources/Core/…                 # shared, testable business logic — no UIKit/SwiftUI/WatchKit imports
    Tests/CoreTests/…              # Swift Testing
Targets/
  iOS/                             # written whenever `ios` or `ipados` is selected (one target either way)
    Sources/<AppName>App.swift     # SwiftUI @main App entry
    Sources/ContentView.swift
    Tests/<AppName>Tests.swift     # Swift Testing, unit-test target
    UITests/<AppName>UITests.swift # XCUITest, UI-test target
  macOS/                           # written when `macos` is selected — same three-file shape
    Sources/… Tests/… UITests/…
  watchOS/                         # written when `watchos` is selected — same three-file shape
    Sources/… Tests/… UITests/…
.swiftlint.yml
.swift-format
fastlane/
  Fastfile
sonar-project.properties           # only when `sonar` != none
```

`.xcodeproj`/`.xcworkspace` are never written here — see this skill's intro. `.gitignore` entries for them
(`*.xcodeproj/`, `*.xcworkspace/`, `.build/`, `DerivedData/`, `*.xcresult`, etc.) are the `iru-setup-swift-gitignore`
skill's job, not this one's.

### `project.yml` (XcodeGen)

```yaml
name: <app-name>
options:
  bundleIdPrefix: <bundle-id-prefix>
  deploymentTarget:
    iOS: "<min-deployment-target>"
    macOS: "<min-deployment-target>"
    watchOS: "<min-deployment-target>"
  xcodeVersion: "<xcode-version>"
configs:
  Debug: debug
  Release: release
settings:
  base:
    SWIFT_VERSION: "6.0"
    SWIFT_STRICT_CONCURRENCY: complete
    MARKETING_VERSION: "<marketing-version>"
    CURRENT_PROJECT_VERSION: "<current-project-version>"
packages:
  Core:
    path: Packages/Core
targets:
  # One block per selected platform — repeat this whole shape for macOS/watchOS with that platform's own
  # deploymentTarget/bundle id/Info.plist keys (see the per-platform notes below). Shown here for iOS/iPadOS.
  <AppName>-iOS:
    type: application
    platform: iOS
    deploymentTarget: "<min-deployment-target>"
    sources:
      - path: Targets/iOS/Sources
    dependencies:
      - package: Core
      # Only when `watchos` is also selected — embeds the watch app into the iOS app's build product:
      - target: <AppName>-watchOS
        embed: true
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: <bundle-id>
        # "1" = iPhone only, "2" = iPad only, "1,2" = both — resolved per Step 2's ios/ipados selection.
        TARGETED_DEVICE_FAMILY: "<device-family>"
    info:
      path: Targets/iOS/Info.plist
      properties:
        CFBundleDisplayName: <app-name>
        NSHumanReadableCopyright: "Copyright © <developer-name>"
        ITSAppUsesNonExemptEncryption: false
        UILaunchScreen: {}
  <AppName>Tests-iOS:
    type: bundle.unit-test
    platform: iOS
    deploymentTarget: "<min-deployment-target>"
    sources:
      - path: Targets/iOS/Tests
    dependencies:
      - target: <AppName>-iOS
  <AppName>UITests-iOS:
    type: bundle.ui-testing
    platform: iOS
    deploymentTarget: "<min-deployment-target>"
    sources:
      - path: Targets/iOS/UITests
    dependencies:
      - target: <AppName>-iOS
schemes:
  <AppName>-iOS:
    build:
      targets:
        <AppName>-iOS: all
    test:
      targets:
        - <AppName>Tests-iOS
        - <AppName>UITests-iOS
    run:
      config: Debug
    archive:
      config: Release
```

**Confirmed structurally valid** (`python3 -c "import yaml; yaml.safe_load(open('project.yml'))"` parses clean)
against exactly this shape, with `<AppName>` → `MyApp`, one iOS target, no watchOS/macOS targets, `<device-family>`
→ `"1,2"` — see "Known quirks" for what wasn't runnable (XcodeGen itself isn't installable here).

Repeat the `targets`/`schemes` block per additional selected platform:

- **macOS** — `platform: macOS`, target names `<AppName>-macOS`/`<AppName>Tests-macOS`/`<AppName>UITests-macOS`,
  `type: application` stays the same (AppKit/SwiftUI `App` life cycle), no `TARGETED_DEVICE_FAMILY` key (macOS
  doesn't use it), Info.plist adds `LSMinimumSystemVersion: "<min-deployment-target>"`.
  - Only when `distribution` isn't `none`: `settings.base` also needs `ENABLE_HARDENED_RUNTIME: true` (required for
    `notarytool` to accept the archive later — see the Fastfile's `notarize_release` lane).
- **watchOS** — `platform: watchOS`, target names `<AppName>-watchOS`/`<AppName>Tests-watchOS`/`<AppName>UITests-watchOS`,
  Info.plist adds `WKCompanionAppBundleIdentifier: <bundle-id>` (only when `ios`/`ipados` is also selected — points
  back at the iOS app), `PRODUCT_BUNDLE_IDENTIFIER: <watch-bundle-id>`. This is the modern, single-target watch-app
  shape (no separate WatchKit Extension target) — current for every watchOS version this skill's fallback Xcode
  (27.0) supports.
- **`ipados`-without-`ios`**: same iOS-platform target as above, just `<device-family>` → `"2"` and no iPad-specific
  renaming — it's still literally the `<AppName>-iOS` target, per Step 2's note.

### `Project.swift` + `Tuist.swift` (Tuist)

`Tuist.swift` (project-wide Tuist config, one file regardless of platform count):

```swift
import ProjectDescription

let tuist = Tuist(
    project: .tuist(
        compatibleXcodeVersions: .upToNextMajor("<xcode-version>")
    )
)
```

`Project.swift` (one `Target.target(...)` triple — app/unit-tests/UI-tests — per selected platform, collected into
one `targets:` array; shown here for a single iOS/iPadOS platform):

```swift
import ProjectDescription

let baseSettings: SettingsDictionary = [
    "SWIFT_VERSION": "6.0",
    "SWIFT_STRICT_CONCURRENCY": "complete",
    "MARKETING_VERSION": "<marketing-version>",
    "CURRENT_PROJECT_VERSION": "<current-project-version>",
]

let iosTarget = Target.target(
    name: "<AppName>-iOS",
    destinations: .iOS,
    product: .app,
    bundleId: "<bundle-id>",
    deploymentTargets: .iOS("<min-deployment-target>"),
    infoPlist: .extendingDefault(with: [
        "CFBundleDisplayName": "<app-name>",
        "NSHumanReadableCopyright": "Copyright © <developer-name>",
        "ITSAppUsesNonExemptEncryption": false,
        "UILaunchScreen": [:],
    ]),
    sources: ["Targets/iOS/Sources/**"],
    dependencies: [
        .package(product: "Core"),
        // Only when `watchos` is also selected:
        .target(name: "<AppName>-watchOS"),
    ],
    settings: .settings(base: baseSettings)
)

let iosTestTarget = Target.target(
    name: "<AppName>Tests-iOS",
    destinations: .iOS,
    product: .unitTests,
    bundleId: "<bundle-id>.tests",
    deploymentTargets: .iOS("<min-deployment-target>"),
    sources: ["Targets/iOS/Tests/**"],
    dependencies: [.target(name: "<AppName>-iOS")]
)

let iosUITestTarget = Target.target(
    name: "<AppName>UITests-iOS",
    destinations: .iOS,
    product: .uiTests,
    bundleId: "<bundle-id>.uitests",
    deploymentTargets: .iOS("<min-deployment-target>"),
    sources: ["Targets/iOS/UITests/**"],
    dependencies: [.target(name: "<AppName>-iOS")]
)

let project = Project(
    name: "<app-name>",
    packages: [.local(path: "Packages/Core")],
    targets: [iosTarget, iosTestTarget, iosUITestTarget]
    // Append macOS/watchOS's own three targets here, one Target.target(...) triple per platform, the same
    // way project.yml repeats its `targets:` block per platform above.
)
```

**Syntax-checked only, not typechecked** (`swiftc -parse Project.swift`/`Tuist.swift` both exit `0` against exactly
these two files, with placeholders substituted) — `-parse` validates Swift grammar without resolving imports, so it
never needed `ProjectDescription` (Tuist's manifest-only module) to actually exist locally. It does **not** confirm
these calls match Tuist's real `ProjectDescription` API surface — that needs `tuist generate` itself, which this
skill's environment can't run (see "Known quirks"). For `ipados`-without-`ios`, set `destinations: .iPad` instead of
`.iOS` (Tuist, unlike XcodeGen, *does* expose a distinct `.iPad`/`.iPhone` destination pairing — use `[.iPhone,
.iPad]` for both, `.iPad` alone for iPad-only, matching the same `TARGETED_DEVICE_FAMILY` semantics either generator
produces underneath).

### `Packages/Core/Package.swift`

```swift
// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "Core",
    platforms: [
        .iOS(.v<min-deployment-target-major>),
        .macOS(.v<min-deployment-target-major>),
        .watchOS(.v<min-deployment-target-major>)
        // Include only the platform entries whose corresponding app platform was selected in Step 2 — a
        // `.watchOS` entry with no watchOS app target is harmless but needless.
    ],
    products: [
        .library(name: "Core", targets: ["Core"])
    ],
    targets: [
        .target(name: "Core", swiftSettings: [.swiftLanguageMode(.v6)]),
        .testTarget(name: "CoreTests", dependencies: ["Core"], swiftSettings: [.swiftLanguageMode(.v6)])
    ]
)
```

**Fully verified — confirmed working, not just syntax-checked**: `swift build` and `swift test` both pass clean
against exactly this `Package.swift` shape (with a trivial `Core`/`CoreTests` pair — see Step 7). `PackageDescription`'s
`.v<N>` platform enum only accepts specific known minor/major combinations (e.g. `.v18`, `.v26`) — resolve
`<min-deployment-target-major>` to the nearest value `PackageDescription` actually declares for the toolchain in
use rather than an arbitrary string; `swift build` fails at manifest-parse time with a clear "referencing
inaccessible" error if the requested version doesn't exist as an enum case, which is an easy, safe failure mode to
catch before writing the rest of the scaffold.

### `Packages/Core/Sources/Core/<Placeholder>.swift`

```swift
public struct Greeter: Sendable {
    public init() {}

    public func greeting(for name: String) -> String {
        "Hello, \(name)!"
    }
}
```

A minimal, genuinely testable placeholder — replace with real business logic. Every type here should be `Sendable`
(Swift 6's strict-concurrency default demands it the moment the type crosses an `async`/actor boundary, and
`SWIFT_STRICT_CONCURRENCY = complete` in the app targets makes that a build error, not a warning, everywhere this
package is used).

### `Packages/Core/Tests/CoreTests/<Placeholder>Tests.swift`

```swift
import Testing
@testable import Core

@Suite("Greeter")
struct GreeterTests {
    @Test("greeting includes the given name")
    func greetingIncludesName() {
        let greeter = Greeter()
        #expect(greeter.greeting(for: "World") == "Hello, World!")
    }
}
```

Swift Testing (`@Suite`/`@Test`/`#expect`), not XCTest — matches this catalog's Swift Testing default for unit
tests (`iru-swift-code-one-task`'s own convention). **Confirmed passing**: `swift test` reports `1 test in 1 suite
passed` against exactly this pair (see Step 7).

### `Targets/<Platform>/Sources/<AppName>App.swift` (SwiftUI `App` entry point)

```swift
import Core
import SwiftUI

@main
struct <AppName>App: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
```

### `Targets/<Platform>/Sources/ContentView.swift`

```swift
import Core
import SwiftUI

struct ContentView: View {
    private let greeter = Greeter()

    var body: some View {
        Text(greeter.greeting(for: "<app-name>"))
            .padding()
    }
}

#Preview {
    ContentView()
}
```

Both files are identical across platforms except the module name substitution — write one copy per selected
platform's `Targets/<Platform>/Sources/`.

### `Targets/<Platform>/Tests/<AppName>Tests.swift` (Swift Testing, unit-test target)

```swift
import Testing
@testable import <AppName>

@Suite("ContentView")
struct <AppName>Tests {
    @Test("app module links against Core")
    func linksAgainstCore() {
        let greeter = Greeter()
        #expect(greeter.greeting(for: "Test") == "Hello, Test!")
    }
}
```

A deliberately thin placeholder — its only job is to prove the app target's unit-test target actually compiles and
links against both the app module and `Core`. Real app-target tests belong here once there's app-specific logic
(view models, formatters, etc.) that doesn't belong in the platform-agnostic `Core` package.

### `Targets/<Platform>/UITests/<AppName>UITests.swift` (XCUITest, UI-test target)

```swift
import XCTest

final class <AppName>UITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testAppLaunches() throws {
        let app = XCUIApplication()
        app.launch()
        XCTAssertTrue(app.staticTexts["<app-name>"].waitForExistence(timeout: 5))
    }
}
```

XCUITest, not Swift Testing — Swift Testing does not yet ship a UI-automation driver equivalent to
`XCUIApplication`, so this skill follows the same split `iru-setup-android-app`'s instrumented-test template does
(Espresso/`XCUIApplication`-style black-box automation stays on the older framework; fast unit tests move to the
newer one). **Unverified locally**: running this needs a booted simulator/device driving a real app UI, which this
skill's verification (Step 7) never built (no `.xcodeproj` was ever generated — see "Known quirks").

### `.swiftlint.yml`

```yaml
excluded:
  - .build
  - Packages/Core/.build
  - "**/*.generated.swift"
opt_in_rules:
  - force_unwrapping
  - implicitly_unwrapped_optional
  - closure_spacing
  - explicit_init
  - empty_count
  - fatal_error_message
  - first_where
  - overridden_super_call
  - prohibited_super_call
  - redundant_nil_coalescing
  - sorted_imports
  - unused_import
reporter: json
```

### `.swift-format`

```json
{
  "version": 1,
  "lineLength": 120,
  "indentation": { "spaces": 4 },
  "tabWidth": 4,
  "respectsExistingLineBreaks": true,
  "lineBreakBeforeControlFlowKeywords": false,
  "lineBreakBeforeEachArgument": false
}
```

**Not optional — confirmed while verifying this skill.** `swift format lint --strict` with **no** `.swift-format`
present falls back to the tool's own default style, which is **2-space indentation** — every 4-space-indented file
in this skill's own templates above then fails with `error: [Indentation] unindent by 2 spaces` on nearly every
line. Writing exactly this config (4-space indent) before running `swift format lint` is what makes it pass clean
against Step 5's own templates (see Step 7). `swift format lint` auto-discovers `.swift-format` from the current
directory (or nearest ancestor) with no `--configuration` flag needed — confirmed both with and without the flag
give identical results once the file exists.

### `fastlane/Fastfile`

Base shape (always written, whatever `signing`/`distribution` resolved to):

```ruby
default_platform(:ios)

platform :ios do
  desc "Run unit tests"
  lane :test do
    run_tests(
      scheme: "<AppName>-iOS",
      destination: "platform=iOS Simulator,name=<first-available-simulator-name>"
    )
  end
end
```

**Only when `signing: fastlane-match`**, add before the `test` lane:

```ruby
  desc "Sync distribution signing certificates and profiles"
  private_lane :sync_signing do
    match(type: "appstore", readonly: is_ci)
  end
```

**Only when `signing: api-key`**, add instead:

```ruby
  desc "Authenticate to App Store Connect with an API key"
  private_lane :connect_api_key do
    app_store_connect_api_key(
      key_id: ENV["APP_STORE_CONNECT_API_KEY_ID"],
      issuer_id: ENV["APP_STORE_CONNECT_API_KEY_ISSUER_ID"],
      key_content: ENV["APP_STORE_CONNECT_API_KEY_BASE64"],
      is_key_content_base64: true
    )
  end
```

**Only when `signing` isn't `none` AND `distribution` isn't `none`**, add a `build` lane and, per `distribution`,
`beta`/`release` lanes:

```ruby
  desc "Build a signed, distributable archive"
  lane :build do
    sync_signing if <signing == fastlane-match>
    connect_api_key if <signing == api-key>
    build_app(
      scheme: "<AppName>-iOS",
      export_method: "app-store",
      xcargs: <"-allowProvisioningUpdates" only when signing == api-key, omitted otherwise>
    )
  end

  # Only when distribution is internal or store:
  desc "Upload the latest build to TestFlight"
  lane :beta do
    build
    upload_to_testflight(skip_waiting_for_build_processing: true)
  end

  # Only when distribution is store:
  desc "Submit the latest build to App Store review"
  lane :release do
    build
    upload_to_app_store(skip_screenshots: true, skip_metadata: true, force: true)
  end
end
```

**Only when `macos` was selected AND `distribution` isn't `none` AND `signing` isn't `none`**, add:

```ruby
platform :mac do
  desc "Build, notarize, and staple the macOS release archive"
  lane :notarize_release do
    connect_api_key if <signing == api-key>
    build_app(scheme: "<AppName>-macOS", export_method: "developer-id")
    notarize(package: lane_context[SharedValues::PKG_OUTPUT_PATH] || lane_context[SharedValues::IPA_OUTPUT_PATH])
    # notarize (the fastlane plugin action) already staples on success; if it isn't installed, fall back to:
    #   sh("xcrun notarytool submit '#{lane_context[SharedValues::IPA_OUTPUT_PATH]}' --wait ...")
    #   sh("xcrun stapler staple '#{lane_context[SharedValues::IPA_OUTPUT_PATH]}'")
  end
end
```

`<first-available-simulator-name>` — resolved the same way Step 7's own verification resolves it: the first entry
under the current iOS runtime section of `xcrun simctl list devices available` (confirmed `iPhone 17 Pro` in this
skill's own environment; this is inherently machine-specific, so leave it as a literal name resolved at scaffold
time, not a placeholder the user is expected to fill in later). **Fastlane lanes and signing are never executed by
this skill or its verification** — every lane above is written but never run; Step 7/8 say so explicitly. `notarize`
here refers to Fastlane's community `fastlane-plugin-notarize` (needs `fastlane add_plugin notarize`) — the raw
`xcrun notarytool submit --wait` + `xcrun stapler staple` fallback in the comment needs no plugin and is what
`iru-setup-swift-github-workflows`'s `release.yml` (Task 36) uses directly in CI instead of a Fastlane plugin.

### `sonar-project.properties` (only when `sonar` != `none`)

```
sonar.organization=<sonar-organization>
sonar.projectKey=<sonar-project-key>
sonar.host.url=<sonar-host-url>
sonar.sourceEncoding=UTF-8
sonar.sources=Packages/Core/Sources,Targets/iOS/Sources,Targets/macOS/Sources,Targets/watchOS/Sources
sonar.tests=Packages/Core/Tests,Targets/iOS/Tests,Targets/iOS/UITests,Targets/macOS/Tests,Targets/macOS/UITests,Targets/watchOS/Tests,Targets/watchOS/UITests
sonar.swift.file.suffixes=.swift
sonar.coverageReportPaths=sonarqube-generic-coverage.xml
sonar.swiftlint.reportPaths=swiftlint.json
```

List only the `sonar.sources`/`sonar.tests` path segments for platforms actually selected in Step 2 — omit any
`Targets/<Platform>/…` entry whose platform wasn't chosen (the two example lines above show every platform for
completeness; a real generated file only lists what exists on disk). `sonar.coverageReportPaths` names the same
SonarQube-generic-format XML `iru-setup-swift-github-workflows`'s `build.yml` produces from `xccov`/`llvm-cov`
output (via `slather` or SonarSource's `xccov-to-sonarqube-generic.sh`) — this skill never generates that XML
itself, only names where CI will put it. Omit `sonar.organization` entirely for `sonar: self-hosted` servers
without organizations enabled (per Step 2).

## Step 6 — Scaffold the project

Skip any individual file this step would write if Step 1 resolved gap-fill (`mode: existing` or the "Update"
choice) and that exact file already exists — never overwrite it.

1. Write the manifest — `project.yml` (XcodeGen) or `Project.swift` + `Tuist.swift` (Tuist), per Step 2's
   `generator` choice — with Step 2/3/4's values substituted, one `targets`/`Target.target(...)` triple per
   selected platform, and the watchOS-embed/`TARGETED_DEVICE_FAMILY` conditionals applied.
2. Create `Packages/Core/Sources/Core/` and `Packages/Core/Tests/CoreTests/`, and write `Package.swift` plus the
   placeholder `Greeter.swift`/`GreeterTests.swift` pair from Step 5.
3. For each selected platform, create `Targets/<Platform>/{Sources,Tests,UITests}/` and write that platform's
   `<AppName>App.swift`, `ContentView.swift`, `<AppName>Tests.swift`, and `<AppName>UITests.swift` from Step 5.
4. Write `.swiftlint.yml` and `.swift-format` at the repository root.
5. Write `fastlane/Fastfile` with exactly the lanes Step 2's `signing`/`distribution` answers gate in (see Step
   5's Fastfile section) — never write a lane this skill can't back with the chosen signing/distribution method.
6. Write `sonar-project.properties` only when `sonar` != `none`, scoped to the platforms actually selected.
7. Remind the user now (also repeated in Step 8) that the `.xcodeproj`/`.xcworkspace` this manifest describes does
   not exist yet — it's created by running `xcodegen generate` or `tuist generate` from the repository root, which
   this skill does not do automatically (see the intro).

## Step 7 — Verify

`brew` is not installed in this skill's own environment, so **neither XcodeGen nor Tuist could be installed or run
here** — the manifest-generation step itself (`xcodegen generate`/`tuist generate`, and everything downstream of an
actual `.xcodeproj`, including a real end-to-end app build/run) is **unverified locally**. What follows is what
*was* run for real, run through the `iru-gate-runner` agent where output could be long:

1. **`project.yml` structural validity**: `python3 -c "import yaml; yaml.safe_load(open('project.yml'))"` against
   exactly Step 5's XcodeGen template (one iOS target, `TARGETED_DEVICE_FAMILY: "1,2"`) — parses clean.
2. **`Project.swift`/`Tuist.swift` syntax**: `swiftc -parse Project.swift` and `swiftc -parse Tuist.swift` against
   exactly Step 5's Tuist templates — both exit `0`. This is grammar-only (no typecheck, no `ProjectDescription`
   resolution); it does not prove the Tuist API calls are correct, only that the Swift is well-formed.
3. **`Packages/Core` actually builds and tests**: scaffolded the package exactly as Step 5 shows (`Package.swift`,
   `Sources/Core/Greeter.swift`, `Tests/CoreTests/GreeterTests.swift`) in `$TMPDIR/iru-verify/swift/app/Packages/Core`
   and ran `swift build` (succeeds) and `swift test` (`1 test in 1 suite passed`).
4. **The `xcodebuild`/simulator/`.xcresult` path Step 5's Fastfile and the whole app workflow depend on** — proven
   against the same `Core` package (a SwiftPM package opens directly in `xcodebuild` without any `.xcodeproj`,
   exactly as Task 34.2 specifies):
   - `xcodebuild test -scheme Core -destination 'platform=macOS' -enableCodeCoverage YES -resultBundlePath TestResults.xcresult` — succeeds (`** TEST SUCCEEDED **`).
   - `xcrun simctl list devices available` (no `timeout` binary is installed on this machine — GNU coreutils isn't
     present and `brew` can't supply it either; ran it plain, which returned promptly) — first iOS entry:
     `iPhone 17 Pro`.
   - `xcodebuild test -scheme Core -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -enableCodeCoverage YES -resultBundlePath TestResults-ios.xcresult` — succeeds.
   - `xcrun xccov view --report --json TestResults.xcresult | head -c 600` and the same against the iOS run — both
     produce the real, documented shape: a top-level `{"coveredLines","executableLines","lineCoverage","targets":[…]}`
     object, `targets` listing each build product with its own `coveredLines`/`files`.
   - `xcrun xcresulttool get test-results summary --path TestResults.xcresult` — the modern (Xcode 16+) subcommand;
     produces a `devicesAndConfigurations`/`passedTests`/`failedTests`/`result` JSON summary. The legacy `get object`
     form still exists but prints a deprecation notice recommending `get test-report` instead.
5. **`.swift-format`/`.swiftlint.yml`**: `swift format lint --strict --recursive Sources Tests` against the scaffolded
   `Packages/Core`, once with Step 5's `.swift-format` present (passes clean) and once without it (fails on nearly
   every line — see Step 5's note). SwiftLint itself is **unverified locally** — no `swiftlint` binary is installed
   and `brew install swiftlint` can't run.
6. `gem list -r fastlane --remote` — confirms the RubyGems index is reachable and returns a real current version
   without installing the gem. **Fastlane lanes, `match`, `notarize`, and any signing/upload step are never
   executed** — this skill only wrote the Fastfile text (see Step 5/8).

Verification directory: `$TMPDIR/iru-verify/swift/app` (the `Packages/Core` package lives at
`$TMPDIR/iru-verify/swift/app/Packages/Core`; nothing was ever written inside the `ai-catalog` repository itself).

Report pass/fail and any error output verbatim for a failure; don't dump a successful run's full log.

## Step 8 — Report

Summarize what was generated: the resolved `app-name`/`bundle-id-prefix`/`<bundle-id>`, `platforms` selected (and
how `ipados` combined with `ios`, if relevant), `min-deployment-target`, `generator`, the license chosen (or
"none"), and whether Step 6's scaffold ran fresh, was skipped in favor of gap-fill/update (per Step 1), or the user
chose to stop.

State explicitly what was included versus omitted, and why:

- **`generator`**: `xcodegen`/`tuist` — restate the recommendation logic from Step 2 and which manifest file(s)
  were written.
- **`open-source`**/**`sonar`**: as Step 2 resolved them; if `sonar` != `none`, restate the `sonar.organization`/
  `sonar.projectKey`/`sonar.host.url` written into `sonar-project.properties`, and which platforms' paths it lists.
- **`distribution`**/**`signing`**: as resolved — restate exactly which Fastfile lanes exist as a result (`test`
  only; `test`+`build`+`beta`; or `test`+`build`+`beta`+`release`, plus `notarize_release` if `macos` + a real
  signing method were both chosen) and which CI secrets (`MATCH_GIT_URL`/`MATCH_PASSWORD` for `fastlane-match`;
  `APP_STORE_CONNECT_API_KEY_ID`/`_ISSUER_ID`/`_KEY_BASE64` for `api-key`) each depends on — this skill never
  collects or stores any of them.
- Which Step 4 versions came from a live lookup versus this skill's recorded fallback.

Then report which of Step 5's files were created fresh, left untouched (gap-fill/`mode: existing`), or replaced
(update). If existing files were replaced, explicitly list what could have been lost — any target, scheme, or
build-setting customization beyond what Step 5's templates show — and tell the user to check `git diff` for
anything they need to re-add.

### Known quirks / verification notes

- **Verified in `$TMPDIR/iru-verify/swift/app`** (outside this repository, nothing committed): `swift build` and
  `swift test` both pass against the scaffolded `Packages/Core` (`Package.swift` + one `Greeter`/`GreeterTests`
  pair, Swift tools version `6.0`, `swiftLanguageMode(.v6)`). `xcodebuild test -scheme Core -destination
  'platform=macOS' -enableCodeCoverage YES -resultBundlePath TestResults.xcresult` and the same against
  `-destination 'platform=iOS Simulator,name=iPhone 17 Pro'` both succeed, opening the bare SwiftPM package
  directly (no `.xcodeproj` needed for `xcodebuild` to find a `Core` scheme — SwiftPM auto-generates one scheme per
  product/target). Versions actually present: Xcode `27.0` (build `27A266a`), Swift `6.4`, SDKs at major `27` across
  every platform, simulator runtimes installed at `26.4` (see below).
- **`brew` is not installed, so `xcodegen generate`/`tuist generate` were never run, and neither was a real app
  build.** Everything this skill claims about the *generated* `.xcodeproj` (scheme names beyond `Core` itself,
  watchOS embed wiring actually linking, `TARGETED_DEVICE_FAMILY` actually producing a universal binary,
  `fastlane build_app` succeeding) is derived from XcodeGen's/Tuist's documented behavior, not confirmed by running
  either tool. The three things that *were* verified for real — the manifest's own syntax/YAML validity, the shared
  `Packages/Core` package's build+test, and the `xcodebuild`/simulator/`.xcresult` mechanics a generated app project
  would also rely on — are the closest approximation available without `brew`.
- **Coverage attribution on a bare SwiftPM package opened directly in `xcodebuild` is misleading — a genuine, worth-
  knowing quirk, not a Core.swift bug.** `xcrun xccov view --report --json TestResults.xcresult` against the
  `xcodebuild test -scheme Core` run above reports the `Core` library target itself at `0/0` covered lines (`"name":
  "Core", "coveredLines":0, "executableLines":0, "files":[]`) even though `Greeter.swift`'s one function definitely
  ran — only the `CoreTests` target's own file shows nonzero coverage. The **reliable** path, confirmed separately:
  `swift test --enable-code-coverage` (not `xcodebuild`) followed by `xcrun llvm-cov report
  <bin-path>/CoreTests.xctest/Contents/MacOS/CoreTests -instr-profile <bin-path>/codecov/default.profdata` (bin
  path from `swift build --show-bin-path`) correctly attributes `Sources/Core/Greeter.swift` at `100.00%` line
  coverage. This is expected to resolve once `Packages/Core` is consumed as a real target *dependency* inside a
  generated `.xcodeproj` (a different build graph than "a bare package opened directly by `xcodebuild`") — but
  since that graph was never built here (no XcodeGen/Tuist), treat the `xccov`-against-a-raw-package result as an
  artifact of this verification's own limitation, not a statement about how coverage will look in the real
  generated app. `iru-swift-coverage` documents the correct per-project-kind path.
- **`swift format lint --strict` needs a `.swift-format` file to match this skill's 4-space-indented templates —
  without one, its default is 2-space indentation and every template above fails.** Confirmed: zero issues once
  Step 5's `.swift-format` is present (auto-discovered from the current directory, no `--configuration` flag
  needed); `[Indentation] unindent by 2/4 spaces` on nearly every line without it.
- **The CoreSimulator service needed one `xcodebuild -runFirstLaunch` before the iOS Simulator destination would
  work at all** — the very first `xcodebuild test -destination 'platform=iOS Simulator,…'` attempt in this
  environment failed with `Loaded CoreSimulatorService is no longer valid for this process` /
  `IDESimulatorFoundation` plug-in load errors; `xcodebuild -runFirstLaunch` (no `sudo` needed) resolved it and
  every simulator run since has succeeded. If a fresh machine hits the same error, try that once before assuming
  the environment is broken.
- **Installed simulator runtimes lag the SDK major by one** — Xcode 27's SDKs report major `27` everywhere
  (`xcodebuild -showsdks`), but `xcrun simctl list devices available` only has `iOS/tvOS/watchOS 26.4` runtimes
  installed. This is why Step 4 resolves `min-deployment-target`'s default from the simulator-runtime lookup, not
  the bare SDK major — targeting `27.0` as a deployment target would make the scaffold's own UI tests un-runnable
  on every simulator this machine actually has.
- **No `timeout` binary** on this machine (GNU coreutils isn't installed and `brew` can't supply it) — `xcrun
  simctl list devices available` was run plain instead of wrapped in `timeout 120 …`; it returned promptly both
  times, but a genuinely hung `simctl` call has no safety-net wrapper available in an environment like this one.
- **`gh api repos/tuist/tuist/releases/latest`'s `"latest"` release was `helm@0.125.0`, not a Tuist CLI version at
  all** — Tuist's monorepo release-tagging makes the GitHub releases API unreliable for "current CLI version";
  `formulae.brew.sh/api/cask/tuist.json` (a plain HTTPS JSON call, no `brew` install required) was the reliable
  source instead. See Step 4's version-lookup table.
- Fastlane lanes (`test`, `build`, `beta`, `release`, `sync_signing`, `connect_api_key`, `notarize_release`) were
  **never executed** — only written. `match`, TestFlight/App Store uploads, and notarization all need real Apple
  Developer Program credentials this environment doesn't have and never will during a skill-authoring pass like
  this one.

Finish with an explicit **Warn explicitly** block:

- **The user must review every generated file before running a generator, building, committing, or distributing.**
  In particular: confirm the license choice matches an actual repository-root `LICENSE` file (or that none is
  intended — suggest `iru-check-license` otherwise), replace the placeholder `Greeter`/`ContentView` with real
  app logic, and run `iru-setup-swift-gitignore` right after this skill so `.xcodeproj`/`.xcworkspace`/
  `DerivedData`/`.xcresult`/`xcuserdata` never get committed.
- **`xcodegen generate`/`tuist generate` were never run — install the chosen generator
  (`brew install xcodegen`/`brew install tuist`, or `mint run …`) and run it before opening this project in Xcode.**
  This is the single largest unverified step in this skill (see "Known quirks").
- If `sonar: cloud` or `sonar: self-hosted` was chosen, a `SONAR_TOKEN` repository secret and an actual SonarCloud/
  SonarQube project matching `sonar.projectKey` still need to exist before a CI-driven scan will succeed — this
  skill only writes `sonar-project.properties`, it never runs a scan itself.
- If `signing` isn't `none`, the underlying Apple Developer Program membership, certificates/profiles (or the
  App Store Connect API key), and — for `fastlane-match` — the private certs repo itself, all need to exist before
  any Fastfile `build`/`beta`/`release`/`notarize_release` lane can succeed; this skill never collects, stores, or
  generates any of them.
- **Unverified locally, and never a blocker**: `xcodegen generate`/`tuist generate` and everything downstream of a
  real `.xcodeproj` (the actual per-platform app build, the XCUITest UI-test target actually launching an app, the
  watchOS embed wiring actually linking a companion app, SwiftLint itself), and every Fastlane lane. Everything
  else in "Known quirks" above — the manifest's structural validity, `Packages/Core`'s build+test, the
  `xcodebuild`/simulator/`.xcresult`/`xccov`/`xcresulttool` mechanics, and `swift format lint` — was run for real
  while building and verifying this skill.
