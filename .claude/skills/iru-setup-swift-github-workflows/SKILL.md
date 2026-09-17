---
name: iru-setup-swift-github-workflows
description: Create or update the `build.yml`, `release.yml`, `sync.yml` (gitflow), `security.yml`, and `.github/dependabot.yml` GitHub Actions workflows for a Swift repository produced by `iru-setup-swift-library` (a SwiftPM package) or `iru-setup-apple-app` (an XcodeGen/Tuist-generated Xcode app) — SwiftLint + `swift format lint --strict`, `swift build`/`swift test --enable-code-coverage --parallel` plus an `xcrun llvm-cov`-to-SonarQube-generic-XML coverage conversion and an `ubuntu-latest` matrix leg for the library flavor, `xcodegen generate`/`tuist generate` plus one `xcodebuild test -enableCodeCoverage YES -resultBundlePath` per selected platform destination (piped through `xcbeautify`, `.xcresult` uploaded as a build artifact, coverage converted via SonarSource's `xccov-to-sonarqube-generic.sh`) for the app flavor, an optional `SonarSource/sonarqube-scan-action` scan, a DocC + Antora documentation build published to GitHub Pages from the stable branch, a release workflow (library: verifies the release tag is valid semver and `swift package dump-package` succeeds, plus an optional `googleapis/release-please-action` job; app: `xcodebuild archive` + `-exportArchive`, signed via `fastlane match` or an App Store Connect API key, uploaded to TestFlight, notarized+stapled for macOS), and a `dependabot.yml`/CodeQL(`swift`, macOS-only)/dependency-review/OSV-Scanner/gitleaks security block. Invoke as `/iru-setup-swift-github-workflows`. Accepts pre-resolved inputs via `args` (`key: value` lines): `flavor` (`library`/`app`, required), `platforms` (comma-separated, matching `iru-setup-swift-library`'s/`iru-setup-apple-app`'s own `platforms` vocabulary), `runner` (`macos-26`/`xcode-27` — a GitHub-hosted GA image label vs. the newer-Xcode preview image label, which some self-hosted/ARC macOS runner pools also adopt by convention; default `macos-26`, both looked up at run time against `actions/runner-images`), `xcode-version` (passed to `maxim-lobanov/setup-xcode`), `integration-branch`, `stable-branch`, `branching` (`gitflow`/`main-only`, default `gitflow`, as the Android sibling), `generator` (`xcodegen`/`tuist`, app only, matching whichever manifest `iru-setup-apple-app` wrote), `signing` (`fastlane-match`/`api-key`/`none`, app only), `release-please` (`yes`/`no`, library only, default `no`), plus this catalog's shared workflow-args vocabulary — `open-source`, `publish` (library only), `distribution` (app only), `sonar` (+ coordinates), `mode`, and the four `security-*` opt-outs — so an orchestrating skill can supply them without re-prompting. Ships with explicit example templates embedded in this skill file (there is no single real reference repository to genericize from, unlike the Java/TypeScript/Android siblings — these templates are assembled from `iru-setup-swift-library`'s/`iru-setup-apple-app`'s/`iru-swift-coverage`'s/`iru-swift-bump-version`'s own verified commands plus this skill's own verification pass, Step 3). Creates all workflows from scratch if none exist; if any already exists, asks the user whether to stop or attempt an update using the templates as reference. Equivalent to `iru-setup-java-github-workflows`/`iru-setup-typescript-github-workflows`/`iru-setup-android-github-workflows` for the Swift/Apple-platform stack. Use whenever a Swift package or Apple app repository needs this CI/CD release and security pipeline bootstrapped or brought in line with this house pattern, instead of hand-writing the YAML.
model: haiku
---

# Setup Swift GitHub Workflows

Scaffold (or update) the GitHub Actions workflows plus a Dependabot config for a Swift repository produced by
`iru-setup-swift-library` (a bare SwiftPM package, `flavor: library`) or `iru-setup-apple-app` (an
XcodeGen/Tuist-generated native app, `flavor: app`):

- **`build.yml`** — runs on every push to the integration/stable branches and every pull request: lint
  (SwiftLint + `swift format lint --strict`), build, test with coverage, an optional SonarQube/SonarCloud scan,
  a DocC + Antora documentation build published to GitHub Pages (only when the push lands on the stable
  branch). The flavor changes what "build/test" means underneath (Step 4/5).
- **`release.yml`** — triggered when a GitHub Release is published. For a library this verifies the release is
  sound (semver tag, a manifest that still parses) rather than publishing anywhere — a SwiftPM package's actual
  release artifact is the git tag itself, nothing this workflow uploads (Step 6). For an app it archives, signs,
  exports, uploads to TestFlight, and (for macOS) notarizes (Step 7).
- **`sync.yml`** (`branching: gitflow` only) — once a release is published from the stable branch, opens a pull
  request merging it back into the integration branch and bumps the development version, reusing
  `iru-swift-bump-version`'s exact rewrite targets (`version.txt`/`CHANGELOG.md`/README for a library,
  `MARKETING_VERSION`/`CURRENT_PROJECT_VERSION` for an app) so a manual `/iru-swift-bump-version` run and this
  CI-driven script never drift apart (Step 8).
- **`security.yml`** and **`.github/dependabot.yml`** — generated (or updated) regardless of `branching`: a
  `dependency-review` job, a CodeQL job (`swift`, which only runs on a macOS runner — Linux CodeQL has no Swift
  extractor), an OSV-Scanner job, a `gitleaks` job (each individually omittable via `args`), and grouped weekly
  Dependabot updates for the `swift` and `github-actions` ecosystems (Step 9).

This skill is designed for the project shapes `iru-setup-swift-library`/`iru-setup-apple-app` produce — a root
`Package.swift` with a `<Name>` library target (library flavor), or a `project.yml`/`Project.swift` generator
manifest plus a `Packages/Core` local SwiftPM package and per-platform `Targets/<Platform>/` directories (app
flavor). If neither shape is found at the repository root, warn the user this skill's templates assume one of
them and most of Step 1's survey won't resolve, then use `AskUserQuestion` to ask whether to stop here or
continue anyway (treating every derived placeholder in Step 4+ as an open gap to ask about directly, called out
again in the final report).

**No single real reference repository exists for this skill to genericize from**, unlike its Java/TypeScript/
Android siblings (Step 3 explains why and what these templates are actually derived from instead). **CocoaPods
is never generated** — every template here assumes SwiftPM (for dependencies and, for an app, the local
`Packages/Core` package) exclusively, matching `iru-setup-swift-library`'s and `iru-setup-apple-app`'s own
scaffolds. **macOS runner minutes cost roughly 10x Linux minutes** on GitHub-hosted runners — every job in
`build.yml`/`release.yml` that needs Xcode runs on the chosen `<runner>` (macOS) for exactly that reason; the
library flavor's `ubuntu-latest` matrix leg (Step 4) is the one job in this whole pipeline that deliberately
avoids that cost where it safely can.

## Step 0 — Resolve inputs

This skill can be invoked stand-alone (`/iru-setup-swift-github-workflows`) or as a step inside another skill,
which resolves the parameters below itself and passes them through `args` as `key: value` lines, one per line,
e.g.:

```
flavor: library
platforms: ios, macos
runner: macos-26
xcode-version: 26.6
integration-branch: develop
stable-branch: main
branching: gitflow
release-please: no
open-source: yes
publish: yes
sonar: cloud
sonar-organization: example-org-github
sonar-project-key: example-org_example-library
sonar-host-url: https://sonarcloud.io
security-dependency-review: yes
security-codeql: yes
security-osv: yes
security-gitleaks: yes
```

Parse any such lines first; for each key found there, use that value directly and skip the matching
fact-finding step below. If `args` is absent or doesn't look like this format, treat everything as unset and
gather every fact via Step 1's survey / `AskUserQuestion` instead. Bounded choices (`flavor`, `runner`,
`branching`, `generator`, `signing`, `sonar`, `publish`/`distribution`, `release-please`, the `security-*`
toggles) go through `AskUserQuestion` with at most four options per question when not resolved by `args` or
Step 1's survey; free-text values (branch names, the Sonar organization/key/host, `xcode-version`) are asked as
plain conversation.

| `args` key | Meaning | Default / resolution |
|---|---|---|
| `flavor` | `library` or `app` | Required — detect from Step 1 if not given (a root `Package.swift` with no generator manifest → `library`; `project.yml`/`Project.swift` → `app`), ask if ambiguous |
| `platforms` | Comma-separated platform list | Library: read from `Package.swift`'s `platforms:` array (Step 1); app: read from `project.yml`/`Project.swift`'s per-platform targets (Step 1) |
| `runner` | `macos-26` (GitHub-hosted GA image) or `xcode-27` (the newer-Xcode preview image label — see the note below) | `macos-26` |
| `xcode-version` | Passed to `maxim-lobanov/setup-xcode`'s `xcode-version` input | Looked up in Step 2 against the chosen `<runner>` image's own documented default |
| `integration-branch` | Branch `build.yml` also runs on (gitflow only) | `develop` |
| `stable-branch` | Branch releases are published from, and Pages deploys from | `main` |
| `branching` | `gitflow` or `main-only` | `gitflow` |
| `generator` | `xcodegen` or `tuist` (app only) | Detect from Step 1 (`project.yml` vs. `Project.swift`); ask only if genuinely ambiguous |
| `signing` | `fastlane-match`/`api-key`/`none` (app only) | Detect from `fastlane/Fastfile`'s existing lanes (Step 1) if `iru-setup-apple-app` already ran; otherwise ask, default `none` recommended unless `distribution` isn't `none` |
| `release-please` | `yes`/`no` (library only) — an optional automated changelog/version-bump PR job in `release.yml` | `no` — this catalog already has a hand-driven release path (`iru-release`/`iru-swift-bump-version`); release-please is an alternative, automated path some teams prefer instead, not a required addition |
| `open-source` | `yes`/`no` | `gh repo view --json isPrivate` if unresolved otherwise |
| `publish` (library only) | `yes`/`no` — informational only for this skill (gates nothing here; a SwiftPM library "publishes" by existing at a tagged git URL, per `iru-setup-swift-library`) | Accepted so an orchestrator can pass its full shared-args set without error; noted in the final report if supplied |
| `distribution` (app only) | `none`/`internal`/`store` — gates `release.yml`'s TestFlight/App Store steps | `store` only when `open-source: yes`; otherwise ask, `none` recommended |
| `sonar` | `cloud`/`self-hosted`/`none` | `cloud` when `open-source: yes`; otherwise ask, `none` recommended, with the paid-plan caveat stated |
| `sonar-organization` / `sonar-project-key` / `sonar-host-url` | Sonar coordinates | Only asked when `sonar` isn't `none`; read from an existing `sonar-project.properties` first (Step 1) |
| `mode` | `new`/`existing` | Whether this is a first-time setup or a re-run against an existing pipeline; if `existing`, go straight to Step 1's stop-or-update path |
| `security-dependency-review` / `security-codeql` / `security-osv` / `security-gitleaks` | `yes`/`no`, each gates one `security.yml` job | `yes` |
| `license` / `developer-name` / `developer-email` / `organization-url` | This catalog's shared scaffold-args vocabulary | **Not used by this skill's generated files** — accepted only so an orchestrator can pass its full shared-args set without this skill erroring on unrecognized keys; note this in the final report if any were supplied |

**The `runner` choice, explained.** GitHub's own hosted macOS runner fleet (`actions/runner-images`) currently
ships two relevant image families: a stable, generally-available image labeled by macOS major version
(`macos-26`, tracking macOS 26 "Tahoe"), and a newer-Xcode preview image labeled by Xcode major version instead
(`xcode-27`, tracking the Xcode 27 public preview, itself running on a newer macOS major the GA label hasn't
adopted yet) — confirmed live via `gh api repos/actions/runner-images/contents/images/macos` returning exactly
`macos-14-Readme.md`, `macos-15-Readme.md`, `macos-26-Readme.md` (plus each `-arm64` variant), and
`xcode-27-arm64-Readme.md`, during this skill's own verification (September 2026). `runs-on: <runner>` accepts
either label verbatim whether it's satisfied by GitHub's own hosted fleet or by a self-hosted/Actions Runner
Controller (ARC) pool an organization labels the same way by convention (e.g. pinning a self-managed macOS
runner group to a specific Xcode and naming its label after that version) — the workflow YAML is identical
either way, since `runs-on:` only ever matches a label string. Default to **`macos-26`**: it's the stable,
generally-available image (fewer surprise outages than a public-preview image) and — confirmed in this skill's
own verification — ships **SwiftLint 0.65.1 preinstalled**, unlike the `xcode-27` preview image, which has no
`### Linters` section in its own published image manifest at all. Recommend `xcode-27` only when the project
genuinely needs an Xcode 27 feature the `macos-26` image's own newest available Xcode doesn't have yet (per that
image's own `### Xcode` table, `macos-26` currently tops out at `26.6`, not `27.x`) — and warn that a
public-preview image can change or be pulled with less notice than a GA one, and that its SwiftLint step (Step
4) then always needs the `brew install swiftlint` path since nothing is preinstalled there. **Look up the
currently available labels at run time** rather than trusting this skill's own September 2026 snapshot: `gh api
repos/actions/runner-images/contents/images/macos --jq '.[].name'` lists every `<label>-Readme.md`/
`<label>-arm64-Readme.md` file (strip the suffix for the label itself), and `curl -sL
"https://raw.githubusercontent.com/actions/runner-images/main/images/macos/<label>-arm64-Readme.md"` shows that
image's own `### Xcode` table (available versions, which one is `(default)`) and whether it lists SwiftLint
under `### Linters` — resolve `xcode-version`'s default from whichever `(default)`-marked row applies to the
chosen `<runner>`.

## Step 1 — Survey the target repository

Gather every fact Step 0 didn't already resolve via `args`, and decide whether this is a fresh setup or an
update:

- **Project shape / `flavor`** (skip if supplied via `args`): a root `Package.swift` with no `project.yml`/
  `Project.swift`/`*.xcodeproj` at the root → `library`; any of `project.yml` (XcodeGen), `Project.swift`
  (Tuist), or a checked-in `*.xcodeproj` → `app`. Both present (an app repository with its own root
  `Package.swift` in addition to `Packages/Core`'s) → prefer `app`, same disambiguation
  `iru-swift-bump-version`'s Step 2 uses; ask via `AskUserQuestion` only if genuinely ambiguous.
- **`platforms`** (skip if supplied via `args`): library — parse `Package.swift`'s `platforms:` array
  (`.iOS(.v17)` → `ios`, `.macOS(.v14)` → `macos`, etc.; an absent `platforms:` key with no non-Apple-only
  imports implies `linux` is at least implicitly supported, per `iru-setup-swift-library`'s own Step 2 note —
  don't add a `linux` matrix leg unless the package's own source is confirmed Apple-API-free, see Step 4). App —
  parse `project.yml`'s `targets:` platform values or `Project.swift`'s `destinations:`/`Target.target(...)`
  blocks (one entry per selected platform, per `iru-setup-apple-app`'s own template shape).
- **`generator`** (app only, skip if supplied via `args`): `project.yml` present → `xcodegen`; `Project.swift`
  present → `tuist`. If both are present (a mid-migration repository), ask which one CI should drive.
- **`signing`/`distribution`** (app only, skip whichever is supplied via `args`): grep `fastlane/Fastfile` for
  `sync_signing`/`match(` (→ `signing: fastlane-match`) or `connect_api_key`/`app_store_connect_api_key(` (→
  `signing: api-key`); for `distribution`, a `release`/`upload_to_app_store` lane implies `store`, a `beta`/
  `upload_to_testflight` lane with no `release` lane implies `internal`, neither implies `none` — matching
  exactly what `iru-setup-apple-app`'s own Step 5 conditionally writes. If `fastlane/Fastfile` doesn't exist yet,
  fall back to Step 0's normal ask.
- **Existing `sonar-project.properties`**: if present, read its `sonar.organization`/`sonar.projectKey`/
  `sonar.host.url` directly rather than asking the user again (written by `iru-setup-swift-library`/
  `iru-setup-apple-app`, Step 9/Step 5 of those skills respectively) — treat a `https://sonarcloud.io` host (or
  no host line) as `sonar: cloud`, anything else as `sonar: self-hosted`. Absence falls back to Step 0's
  resolution as usual.
- **`version.txt`/`CHANGELOG.md`** (library, informational for `sync.yml`/`release.yml`): note whether each
  exists — `sync.yml`'s companion script (Step 8) only rewrites `version.txt` if it already exists (mirroring
  `iru-swift-bump-version`'s own "don't create one unless something reads it" rule).
- **`docs/antora.yml`/`docs/antora-playbook.yml`**: if either is missing, the Antora build step in `build.yml`
  has nothing to build against — recommend running `iru-setup-antora` first, or confirm the user will do so
  before merging this workflow.
- **Branch names** (skip whichever is supplied via `args`): confirm the integration/stable branch names actually
  match this repository's branching model (`git branch -a`) rather than assuming gitflow defaults; for
  `branching: main-only`, only `stable-branch` matters.
- **Existing workflows**: check whether `.github/workflows/build.yml`, `release.yml`, `sync.yml`,
  `.github/scripts/sync_versions.py`, `security.yml`, and `.github/dependabot.yml` already exist (only the
  subset relevant to the resolved `branching`, plus the three always-present files).

### Stop or update

- **None of the relevant files exist** (or `mode: new`): skip straight to Step 2 — create everything from
  scratch.
- **Any relevant file already exists** (or `mode: existing`): use `AskUserQuestion` to ask whether to (a) stop
  here and leave everything untouched, or (b) continue and attempt to update the existing file(s) using this
  skill's templates as reference.
  - **Stop**: report which file(s) already exist and end here — make no changes.
  - **Continue**: proceed to Step 13, but treat each existing file as the base to edit, not something to
    overwrite wholesale:
    - For `build.yml`/`release.yml`: preserve any step/job this skill doesn't own (a Slack notification, an
      extra matrix entry, a hand-added deployment target) — only add missing stages or correct outdated ones
      (wrong action version, wrong path, a stage that should now be gated on/off per `sonar`/`distribution`/
      `signing`/`release-please`), and don't reorder foreign steps.
    - For `sync.yml`/`sync_versions.py`: preserve any file the script updates beyond what Step 8's template
      touches, and preserve any extra workflow step the same way.
    - For `security.yml`: preserve any job this skill doesn't own; only add/remove/update the
      dependency-review/CodeQL/OSV-Scanner/gitleaks jobs per the resolved `security-*` args.
    - For `.github/dependabot.yml`: preserve any `updates:` entry for an ecosystem this skill doesn't manage;
      only add/update the `swift` and `github-actions` entries.

## Step 2 — Look up action/tool versions at run time

**Versions are looked up at run time, not hardcoded from this file.** Use the GitHub Releases/tags API
(`gh api repos/<owner>/<action>/releases/latest`, or `git ls-remote --tags` for the "floating major tag?"
column — the REST `/tags` listing can miss a real floating tag, the same caveat the Android sibling's own Step
2/13 documents) for every `uses:` action, and the Homebrew formula/cask JSON API
(`https://formulae.brew.sh/api/formula/<name>.json` / `.../api/cask/<name>.json`, reading `.versions.stable`/
`.version` — reachable over plain HTTPS with no `brew` installed, confirmed in `iru-setup-apple-app`'s own
verification) for `swiftlint`/`xcodegen`/`tuist`/`xcbeautify`, since none of those are `uses:` actions. If a
lookup is unreachable, fall back to the versions confirmed current as of **September 2026**, listed here (every
`uses:` action below was confirmed to resolve as a real `gh api`/`git ls-remote --tags` ref during this skill's
own verification):

| Action / tool | Fallback version | Floating major tag? | Notes |
|---|---|---|---|
| `actions/checkout` | `v7` | yes | |
| `maxim-lobanov/setup-xcode` | `v1` | yes | |
| `actions/setup-node` | `v7` | yes | used only for the Antora build step |
| `actions/setup-python` | `v7` | yes | used only by `sync.yml`, `branching: gitflow` only |
| `actions/upload-artifact` | `v7` | yes | uploads each `.xcresult` bundle, app flavor only |
| `actions/upload-pages-artifact` | `v5` | yes | |
| `actions/deploy-pages` | `v5` | yes | |
| `actions/dependency-review-action` | **`v5.0.0`** | **no** | never published a floating `v5` tag — only exact-version tags; pin the exact version and re-check at generation time |
| `github/codeql-action` (`init`/`analyze`) | `v4` | yes | resolve via `git ls-remote --tags`, not `.../releases/latest` — that endpoint returns the unrelated `codeql-bundle-*` tag (confirmed again during this skill's own verification, same finding as the Android sibling's Step 13) |
| `google/osv-scanner-action` (reusable workflow) | **`v2.6.0`** | **no** | only exact-version tags; pin the workflow ref to the exact tag |
| `gitleaks/gitleaks-action` | `v3` | yes | |
| `SonarSource/sonarqube-scan-action` | `v8` | yes | only when `sonar` isn't `none` |
| `googleapis/release-please-action` | `v5` | yes | only when `release-please: yes` (library only) |
| `apple-actions/upload-testflight-build` | `v5` | yes | app flavor, `distribution` isn't `none`, only when `signing != fastlane-match` (the Fastlane `pilot` path is used instead when `fastlane-match` is chosen — Step 7) |
| `swift-actions/setup-swift` | `v2` | yes | library flavor's `ubuntu-latest` matrix leg — an alternative to the official `swift` Docker image (below) |
| `swift` Docker image (`container: swift:<tag>`) | `6.3-noble` | n/a — not a `uses:` action | the **open-source Linux Swift toolchain lags the Apple-toolchain-bundled Swift version** — confirmed during this skill's own verification: this machine's Xcode 27/Swift 6.4 has no Linux `swift:6.4*` tag published yet on Docker Hub, only up to `6.3.3`; re-check `https://hub.docker.com/v2/repositories/library/swift/tags` at generation time rather than assuming the two track each other |
| `swiftlint` (Homebrew formula, not a `uses:` action) | `0.65.1` | n/a | preinstalled on the `macos-26` runner image (Step 0's note); only `brew install`ed when missing |
| `xcodegen` (Homebrew formula) | `2.46.0` | n/a | app flavor, `generator: xcodegen` |
| `tuist` (Homebrew **cask**, not formula — `iru-setup-apple-app`'s own Step 4 finding) | `4.208.0` | n/a | app flavor, `generator: tuist` |
| `xcbeautify` (Homebrew formula) | `3.2.1` | n/a | app flavor, pipes `xcodebuild test` output |

`GITHUB_TOKEN`'s automatic scopes are sufficient for every job above except where a secret is explicitly named
in Step 6/7/9's templates.

## Step 3 — Why this skill's templates have no single reference repository

Unlike `iru-setup-java-github-workflows`/`iru-setup-typescript-github-workflows`/
`iru-setup-android-github-workflows`, each of which genericizes its templates from one real repository's actual
workflow files, no equivalent real Swift/Apple repository was available to derive this skill's templates from.
Instead, every template in Steps 4–9 is assembled from:

- The exact, verified commands `iru-setup-swift-library` (Task 33), `iru-setup-apple-app` (Task 34),
  `iru-swift-coverage`, and `iru-swift-bump-version` already established and verified for this catalog's Swift
  stack — the build-products path, the `.xctest` binary naming, the `llvm-cov`/`xccov` invocations, the DocC
  flags, the version-file rewrite targets — reused here verbatim rather than reinvented.
- This skill's own verification pass (Step 13), run against Task 33's actual scaffold.
- The Java/TypeScript/Android siblings' own conventions for the parts that are ecosystem-agnostic — the
  Dependabot/CodeQL/dependency-review/OSV-Scanner/gitleaks security block shape, the Pages-deploy-from-Actions
  mechanism, the gitflow `sync.yml` merge-back-and-bump pattern — carried over for consistency across this
  catalog rather than invented fresh for Swift.

Every `<placeholder>` below is resolved from Step 1's survey / Step 0's `args` before writing the real files —
the full resolution table is in Step 10. Drop whichever blocks this repository's `flavor`/`sonar`/
`distribution`/`signing`/`release-please`/`branching` values gate off, per the inline comments in the templates,
including the comment itself — it's authoring guidance, not part of the generated file.

## Step 4 — `build.yml` (`flavor: library`)

```yaml
name: Build

on:
  push:
    branches: [ <integration-branch>, <stable-branch> ] # gitflow; main-only: just [ <stable-branch> ]
  pull_request:
  workflow_dispatch:

jobs:
  build-test:
    name: Build, lint, and test
    runs-on: <runner>
    steps:
      - name: Check out code
        uses: actions/checkout@v7
        with:
          fetch-depth: 0

      - name: Select Xcode <xcode-version>
        uses: maxim-lobanov/setup-xcode@v1
        with:
          xcode-version: '<xcode-version>'

      - name: Install SwiftLint
        run: command -v swiftlint >/dev/null || brew install swiftlint

      - name: Run SwiftLint
        run: swiftlint lint --strict --reporter json > swiftlint.json

      - name: Run swift format lint
        run: swift format lint --strict --recursive Sources Tests

      - name: Build
        run: swift build

      - name: Test with coverage
        run: swift test --enable-code-coverage --parallel

      - name: Export lcov coverage
        run: |
          BIN=$(swift build --show-bin-path)
          TESTBIN=$(find "$BIN" -maxdepth 1 -iname '*.xctest' | head -1)/Contents/MacOS/$(basename "$(find "$BIN" -maxdepth 1 -iname '*.xctest' | head -1)" .xctest)
          xcrun llvm-cov export -format=lcov "$TESTBIN" -instr-profile "$BIN/codecov/default.profdata" \
            --ignore-filename-regex='(Tests/|DerivedSources)' > coverage.lcov

      # Omit this whole step if sonar: none (Step 0). A bare SwiftPM package has no .xcodeproj/.xcworkspace for
      # slather to find (confirmed in this skill's own verification — slather's own design requires one), and
      # SonarSource's xccov-to-sonarqube-generic.sh (used below for flavor: app) takes an .xcresult bundle, which
      # `swift test` never produces either — so this step converts the lcov file above directly instead, via a
      # small vendored python script (Step 4's own note explains why this, not slather/xccov-to-sonarqube, is the
      # library-flavor default).
      - name: Convert coverage to SonarQube generic XML
        if: <sonar != none>
        run: python3 .github/scripts/lcov_to_sonar_generic.py coverage.lcov > sonarqube-generic-coverage.xml

      # Omit this whole step if sonar: none (Step 0)
      - name: Run SonarQube analysis
        if: <sonar != none>
        uses: SonarSource/sonarqube-scan-action@v8
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
        with:
          args: >
            -Dsonar.host.url=<sonar-host-url>

      # Only on a push landing on <stable-branch> — building and publishing docs on every PR/integration-branch
      # push is wasted Pages-deploy churn. mkdir -p the parent directory before generate-documentation — confirmed
      # in this skill's own verification: --allow-writing-to-directory alone does not create missing intermediate
      # directories, and generate-documentation fails with an NSCocoaErrorDomain "couldn't be moved" error if the
      # parent doesn't already exist.
      - name: Generate DocC documentation
        if: github.ref == 'refs/heads/<stable-branch>'
        run: |
          mkdir -p docc-output
          swift package --allow-writing-to-directory docc-output generate-documentation \
            --target <Name> --transform-for-static-hosting --hosting-base-path <repo> \
            --output-path docc-output

      - name: Set up Node
        if: github.ref == 'refs/heads/<stable-branch>'
        uses: actions/setup-node@v7
        with:
          node-version: 24

      - name: Install Antora
        if: github.ref == 'refs/heads/<stable-branch>'
        run: |
          mkdir -p docs-toolchain && cd docs-toolchain
          npm i -D -E antora
          npm i @antora/lunr-extension
          npm i @sntke/antora-mermaid-extension
          npm i @djencks/asciidoctor-mathjax

      - name: Build Antora docs
        if: github.ref == 'refs/heads/<stable-branch>'
        run: cd docs && npx antora antora-playbook.yml

      - name: Merge DocC API docs into the Antora site
        if: github.ref == 'refs/heads/<stable-branch>'
        run: |
          touch ./docs/build/site/.nojekyll
          mkdir -p ./docs/build/site/api
          cp -r ./docc-output/. ./docs/build/site/api/

      - name: Upload Pages artifact
        if: github.ref == 'refs/heads/<stable-branch>'
        uses: actions/upload-pages-artifact@v5
        with:
          path: ./docs/build/site

  # Omit this whole job unless the package's own Sources/ are confirmed free of Apple-only imports (Foundation
  # extras, UIKit/SwiftUI, Combine's Apple-platform-only pieces, etc.) — Step 1's survey. Runs on ubuntu-latest
  # deliberately (see this skill's intro on macOS-minutes cost) since it needs no Xcode, no SwiftLint, no DocC —
  # only confirms the package still builds and tests clean under the open-source Swift toolchain.
  build-test-linux:
    name: Build and test on Linux
    runs-on: ubuntu-latest
    container: swift:<linux-swift-tag>
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Build
        run: swift build
      - name: Test
        run: swift test --parallel

  # Omit this whole job if github.ref != refs/heads/<stable-branch> was already the deploy job's own gate above —
  # this job still needs its own `if:`, since a job-level condition (not a step-level one) is what actually skips
  # the whole runner spin-up when the push isn't on the stable branch.
  deploy-docs:
    name: Deploy docs to GitHub Pages
    needs: build-test
    if: github.ref == 'refs/heads/<stable-branch>'
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

- The `Export lcov coverage` step's two-line `find`-based binary lookup is deliberately awkward instead of a
  hardcoded `<Name>Tests.xctest` path, because — confirmed in `iru-swift-coverage`'s own verification and
  re-confirmed here — the `.xctest` bundle is always named after its **test target**, not the package, and a
  package can carry more than one test target; globbing avoids hardcoding a name this skill can't fully predict
  from `Package.swift` alone (a `<Name>Tests` convention holds for `iru-setup-swift-library`'s own scaffold, but
  not necessarily for an existing repository this skill is asked to update).
- `.github/scripts/lcov_to_sonar_generic.py` (referenced above, written in Step 9's file matrix alongside this
  workflow) is a small, self-contained SonarQube Generic Test Coverage XML converter this skill vendors — see
  Step 9 for its full source and Step 13 for why slather/`xccov-to-sonarqube-generic.sh` don't apply to a bare
  SwiftPM package's coverage output.
- `swiftLanguageModes`/`swift-tools-version: 6.0` (per `iru-setup-swift-library`'s own scaffold) needs no
  special CI handling — `swift build`/`swift test` resolve the toolchain requirement from the manifest itself,
  as long as the selected Xcode (`xcode-version`) bundles a Swift toolchain new enough.
- `sonar.host.url` is passed explicitly via `-D` even though `sonar-project.properties` (written by
  `iru-setup-swift-library`) already carries it, matching this catalog's convention of not relying solely on the
  properties file for the one value most likely to differ between a `cloud` and `self-hosted` setup.

## Step 5 — `build.yml` (`flavor: app`)

Same job name/trigger shape as Step 4's `build-test` job, replacing every step from `Install SwiftLint` onward
(the checkout/`setup-xcode` steps are identical):

```yaml
      - name: Install SwiftLint
        run: command -v swiftlint >/dev/null || brew install swiftlint

      - name: Run SwiftLint
        run: swiftlint lint --strict --reporter json > swiftlint.json

      - name: Run swift format lint
        run: swift format lint --strict --recursive Packages/Core/Sources Packages/Core/Tests Targets

      # generator: xcodegen
      - name: Generate Xcode project
        run: |
          command -v xcodegen >/dev/null || brew install xcodegen
          xcodegen generate

      # generator: tuist
      - name: Generate Xcode project
        run: |
          command -v tuist >/dev/null || brew install --cask tuist
          tuist generate --no-open

      - name: Install xcbeautify
        run: command -v xcbeautify >/dev/null || brew install xcbeautify

      # One block per selected platform (Step 1's platforms survey) — shown here for iOS/iPadOS. Resolves the
      # first available simulator the same way iru-swift-test/iru-setup-apple-app's own Fastfile does; macOS
      # needs no destination resolution (`platform=macOS` is fixed).
      - name: Test <AppName>-iOS
        run: |
          set -o pipefail
          DEVICE=$(xcrun simctl list devices available -j | python3 -c "
          import json, sys
          runtimes = json.load(sys.stdin)['devices']
          for name, devices in runtimes.items():
              if 'iOS' in name and devices:
                  print(devices[0]['name']); break
          ")
          xcodebuild test -scheme <AppName>-iOS -destination "platform=iOS Simulator,name=$DEVICE" \
            -enableCodeCoverage YES -resultBundlePath <AppName>-iOS.xcresult | xcbeautify

      # macOS platform variant
      - name: Test <AppName>-macOS
        run: |
          set -o pipefail
          xcodebuild test -scheme <AppName>-macOS -destination 'platform=macOS' \
            -enableCodeCoverage YES -resultBundlePath <AppName>-macOS.xcresult | xcbeautify

      - name: Upload xcresult bundles
        if: always()
        uses: actions/upload-artifact@v7
        with:
          name: xcresults
          path: '*.xcresult'
          retention-days: 14

      # Omit this whole step if sonar: none. SonarSource's own xccov-to-sonarqube-generic.sh (unlike the
      # library flavor's lcov path, Step 4) fits naturally here — it consumes an .xcresult bundle directly
      # (`xcrun xccov view --archive <path>`), which xcodebuild test above already produced. Only the first
      # selected platform's .xcresult is converted (Sonar merges one coverage report per scan; converting every
      # platform's .xcresult and passing a comma-separated sonar.coverageReportPaths list is also valid if
      # per-platform coverage genuinely differs and the user wants both counted).
      - name: Convert coverage to SonarQube generic XML
        if: <sonar != none>
        run: |
          curl -sSfL -o xccov-to-sonarqube-generic.sh \
            https://raw.githubusercontent.com/SonarSource/sonar-scanning-examples/master/swift-coverage/swift-coverage-example/xccov-to-sonarqube-generic.sh
          chmod +x xccov-to-sonarqube-generic.sh
          ./xccov-to-sonarqube-generic.sh <AppName>-iOS.xcresult > sonarqube-generic-coverage.xml

      - name: Run SonarQube analysis
        if: <sonar != none>
        uses: SonarSource/sonarqube-scan-action@v8
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
        with:
          args: >
            -Dsonar.host.url=<sonar-host-url>

      # DocC/Antora/Pages: identical shape to Step 4's library steps, but documents Packages/Core (the app's own
      # testable business-logic package) rather than a top-level library target — only when that package
      # actually declares a swift-docc-plugin dependency (iru-setup-apple-app's own scaffold does not add one by
      # default; note this as an open gap in the final report if the DocC step is included but the dependency
      # is missing from Packages/Core/Package.swift).
      - name: Generate DocC documentation
        if: github.ref == 'refs/heads/<stable-branch>'
        run: |
          mkdir -p docc-output
          swift package --package-path Packages/Core --allow-writing-to-directory docc-output \
            generate-documentation --target Core --transform-for-static-hosting \
            --hosting-base-path <repo> --output-path docc-output
      # ... Set up Node / Install Antora / Build Antora docs / Merge DocC API docs / Upload Pages artifact:
      # identical to Step 4, copy verbatim.
```

`deploy-docs` (needs: `build-test`, gated the same way) is identical to Step 4's — copy it verbatim, including
its own `if: github.ref == 'refs/heads/<stable-branch>'` job-level gate. There is no `ubuntu-latest` matrix leg
for the app flavor — an Xcode app target has no meaningful Linux build.

Notes specific to this template:

- Only the platform-specific `Test <AppName>-<Platform>` steps for the platforms actually selected (Step 1) are
  emitted — drop every other platform's block entirely, don't comment it out.
- `xcodebuild test`'s exit code must survive the `xcbeautify` pipe — `set -o pipefail` at the top of every such
  `run:` block is required (bash's default `on error` behavior doesn't propagate a failing left-hand command
  through a pipe otherwise, which would silently report a failed test run as a green step).
- watchOS is deliberately **not** given its own `Test <AppName>-watchOS` block when `ios`/`ipados` is also
  selected — per `iru-setup-apple-app`'s own single-target embed model, the watchOS companion app is embedded
  into the iOS app's own build product and tested/archived alongside the iOS scheme, not as a separate scheme
  (Step 7 restates this for `release.yml`'s archive step). A standalone watchOS app (no iOS companion selected)
  does get its own `Test <AppName>-watchOS` block, following the same shape as the iOS one but with a
  `watchOS`-runtime destination lookup.
- The `Install SwiftLint`/`Install xcbeautify`/`xcodegen`/`tuist` `brew install` lines are each guarded by
  `command -v ... >/dev/null ||` so this template works unmodified whether the chosen `<runner>` already
  preinstalls the tool (Step 0's `macos-26` note) or not.

## Step 6 — `release.yml` (`flavor: library`)

```yaml
name: Release

on:
  release:
    types: [released]
  # Only when release-please: yes (Step 0) — the release-please job below runs on this trigger instead.
  push:
    branches: [ <stable-branch> ]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  verify-release:
    name: Verify the release tag and manifest
    if: github.event_name == 'release' || github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    container: swift:<linux-swift-tag>
    steps:
      - name: Check out code
        uses: actions/checkout@v7
        with:
          fetch-depth: 0

      - name: Verify the tag is valid semver
        env:
          TAG: ${{ github.event.release.tag_name }}
        run: |
          set -euo pipefail
          VERSION="${TAG#v}"
          python3 -c 'import re,sys; v=sys.argv[1]; sys.exit(0 if re.fullmatch(r"\d+\.\d+\.\d+(-[0-9A-Za-z][0-9A-Za-z.]*)?(\+[0-9A-Za-z][0-9A-Za-z.]*)?", v) else 1)' "$VERSION" \
            || { echo "::error::Release tag '$TAG' is not a valid semver version"; exit 1; }

      - name: Verify Package.swift still parses
        run: swift package dump-package >/dev/null

  # Only when release-please: yes (Step 0) — an alternative, automated changelog/version-bump PR path; this
  # catalog's default release flow is the hand-driven iru-release/iru-swift-bump-version instead (Step 0's note).
  release-please:
    name: Open the next release-please PR
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: googleapis/release-please-action@v5
        with:
          release-type: simple
          target-branch: <stable-branch>
```

**This workflow never publishes anything** — a SwiftPM library's release artifact **is** the git tag a consumer's
`.package(url:, from:/exact:)` resolves against (per `iru-swift-bump-version`'s own Step 5); `verify-release`
only confirms the tag/manifest are sound *after* the tag already exists, so a broken release is caught
immediately (surfaced as a failed check against the just-published Release) rather than only when a consumer's
own build breaks later. Runs on `ubuntu-latest` with the official `swift` container deliberately (this skill's
intro note on macOS-minutes cost) — neither check needs Xcode.

## Step 7 — `release.yml` (`flavor: app`)

```yaml
name: Release

on:
  release:
    types: [released]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  archive-and-upload:
    name: Archive, sign, and upload
    runs-on: <runner>
    steps:
      - name: Check out code
        uses: actions/checkout@v7
        with:
          fetch-depth: 0

      - name: Select Xcode <xcode-version>
        uses: maxim-lobanov/setup-xcode@v1
        with:
          xcode-version: '<xcode-version>'

      - name: Generate Xcode project
        run: |
          command -v xcodegen >/dev/null || brew install xcodegen   # generator: tuist — swap for tuist generate --no-open
          xcodegen generate

      # signing: fastlane-match only
      - name: Fetch distribution signing certificates and profiles
        env:
          MATCH_GIT_URL: ${{ secrets.MATCH_GIT_URL }}
          MATCH_PASSWORD: ${{ secrets.MATCH_PASSWORD }}
        run: fastlane match appstore --readonly --git_url "$MATCH_GIT_URL"

      # signing: api-key only — writes the .p8 key match/App Store Connect API auth both eventually need
      - name: Write the App Store Connect API key
        if: <signing == api-key>
        env:
          API_KEY_BASE64: ${{ secrets.APP_STORE_CONNECT_API_KEY_BASE64 }}
        run: echo "$API_KEY_BASE64" | base64 -d > AuthKey.p8

      - name: Archive <AppName>-iOS
        run: |
          xcodebuild archive -scheme <AppName>-iOS -archivePath build/<AppName>-iOS.xcarchive \
            <signing == api-key: -allowProvisioningUpdates -authenticationKeyPath AuthKey.p8 -authenticationKeyID ${{ secrets.APP_STORE_CONNECT_API_KEY_ID }} -authenticationKeyIssuerID ${{ secrets.APP_STORE_CONNECT_API_KEY_ISSUER_ID }}>

      - name: Write ExportOptions.plist
        run: |
          cat > ExportOptions.plist <<'PLIST'
          <?xml version="1.0" encoding="UTF-8"?>
          <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
          <plist version="1.0">
          <dict>
            <key>method</key>
            <string>app-store</string>
            <key>teamID</key>
            <string><team-id></string>
            <key>signingStyle</key>
            <string>automatic</string>
          </dict>
          </plist>
          PLIST

      - name: Export <AppName>-iOS.ipa
        run: |
          xcodebuild -exportArchive -archivePath build/<AppName>-iOS.xcarchive \
            -exportPath build/export -exportOptionsPlist ExportOptions.plist \
            <signing == api-key: -allowProvisioningUpdates -authenticationKeyPath AuthKey.p8 -authenticationKeyID ${{ secrets.APP_STORE_CONNECT_API_KEY_ID }} -authenticationKeyIssuerID ${{ secrets.APP_STORE_CONNECT_API_KEY_ISSUER_ID }}>

      # distribution: internal or store, signing: fastlane-match — uses the Fastfile's own credentials wiring
      - name: Upload to TestFlight via fastlane pilot
        if: <signing == fastlane-match>
        run: fastlane pilot upload --ipa build/export/<AppName>.ipa --skip_waiting_for_build_processing

      # distribution: internal or store, signing: api-key — no Fastlane session needed, the action takes the API
      # key directly
      - name: Upload to TestFlight
        if: <signing == api-key>
        uses: apple-actions/upload-testflight-build@v5
        with:
          app-path: build/export/<AppName>.ipa
          api-key-id: ${{ secrets.APP_STORE_CONNECT_API_KEY_ID }}
          api-key-issuer-id: ${{ secrets.APP_STORE_CONNECT_API_KEY_ISSUER_ID }}
          api-key-base64: ${{ secrets.APP_STORE_CONNECT_API_KEY_BASE64 }}

      # macos platform selected, distribution != none — notarization is macOS-only; iOS/watchOS builds never go
      # through notarytool/stapler.
      - name: Archive and export <AppName>-macOS
        if: <macos selected>
        run: |
          xcodebuild archive -scheme <AppName>-macOS -archivePath build/<AppName>-macOS.xcarchive \
            <signing == api-key: -allowProvisioningUpdates -authenticationKeyPath AuthKey.p8 -authenticationKeyID ${{ secrets.APP_STORE_CONNECT_API_KEY_ID }} -authenticationKeyIssuerID ${{ secrets.APP_STORE_CONNECT_API_KEY_ISSUER_ID }}>
          xcodebuild -exportArchive -archivePath build/<AppName>-macOS.xcarchive \
            -exportPath build/export-macos -exportOptionsPlist ExportOptions.plist \
            <signing == api-key: -allowProvisioningUpdates -authenticationKeyPath AuthKey.p8 -authenticationKeyID ${{ secrets.APP_STORE_CONNECT_API_KEY_ID }} -authenticationKeyIssuerID ${{ secrets.APP_STORE_CONNECT_API_KEY_ISSUER_ID }}>

      - name: Notarize <AppName>-macOS
        if: <macos selected>
        run: |
          xcrun notarytool submit build/export-macos/<AppName>.app \
            --key AuthKey.p8 --key-id ${{ secrets.APP_STORE_CONNECT_API_KEY_ID }} \
            --issuer ${{ secrets.APP_STORE_CONNECT_API_KEY_ISSUER_ID }} --wait
          xcrun stapler staple build/export-macos/<AppName>.app
```

Notes specific to this template:

- **watchOS rides along with the iOS archive, never gets its own archive step** — per `iru-setup-apple-app`'s
  single-target embed model (`embed: true` on the iOS target's watchOS dependency), the watchOS companion binary
  is already inside `<AppName>-iOS.xcarchive`'s product once `xcodebuild archive -scheme <AppName>-iOS` runs;
  archiving `<AppName>-watchOS` as its own scheme instead would produce a standalone watch app bundle, not the
  companion-embedded shape this catalog's scaffold assumes. Only a *standalone* watchOS app (no iOS companion at
  all, `iru-setup-apple-app`'s own documented-as-unusual case) gets its own archive/export/notarize block,
  mirroring the iOS one.
- `xcrun notarytool submit --key/--key-id/--issuer` (the API-key auth form) is used regardless of `signing`
  because Apple's notarization service has never accepted `fastlane match`-style certificate-only auth for
  submission — it always needs either an Apple ID + app-specific password or an API key; this catalog's
  `iru-setup-apple-app` Fastfile comment already documents the same `xcrun notarytool submit --wait` +
  `xcrun stapler staple` fallback for exactly this reason. When `signing: fastlane-match` (no App Store Connect
  API key secrets configured), the `Notarize` step above needs an additional `APP_STORE_CONNECT_API_KEY_*` secret
  set purely for notarization even though the rest of the pipeline uses `match` — call this out explicitly in the
  final report as an extra secret requirement specific to macOS distribution.
- `<team-id>` in `ExportOptions.plist` has no run-time lookup — ask the user for their Apple Developer Team ID
  directly (Step 0/1 has no signal for it) and note it as a required manual input in the final report.
- Every `<signing == api-key: ...>` inline marker means "append these flags only when `signing: api-key`" —
  when `signing: fastlane-match`, `xcodebuild archive`/`-exportArchive` need no extra flags at all (the
  certificates `fastlane match` already installed into the login keychain are picked up automatically by
  `signingStyle: automatic`).

## Step 8 — `sync.yml` + `sync_versions.py` (`branching: gitflow` only)

Runs once a GitHub Release is published, provided it was published from the stable branch. Opens a pull request
that merges the released branch back into the integration branch and bumps the development version — a direct
port of `iru-setup-java-github-workflows`'s/`iru-setup-android-github-workflows`'s own `sync.yml` shell logic,
with the version-bump step replaced by exactly the rewrite rules `iru-swift-bump-version` already verified:

### `sync.yml`

```yaml
name: Sync

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
            echo "::error::Release tag '$RELEASE_VERSION' is not in X.Y.Z form; cannot compute the next version."
            exit 1
          fi

          NEXT_PATCH=$((PATCH + 1))
          NEXT_VERSION="${MAJOR}.${MINOR}.${NEXT_PATCH}"
          SYNC_BRANCH="sync_${MAJOR}.${MINOR}.${NEXT_PATCH}"

          echo "release_version=$RELEASE_VERSION" >> "$GITHUB_OUTPUT"
          echo "next_version=$NEXT_VERSION" >> "$GITHUB_OUTPUT"
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

      - name: Bump the development version
        if: steps.guard.outputs.exists == 'false'
        env:
          RELEASE_VERSION: ${{ steps.versions.outputs.release_version }}
          NEXT_VERSION: ${{ steps.versions.outputs.next_version }}
        run: python3 .github/scripts/sync_versions.py

      - name: Commit the version bump
        if: steps.guard.outputs.exists == 'false'
        run: |
          git add version.txt CHANGELOG.md README.md project.yml Project.swift docs/antora.yml docs/modules/ROOT/pages 2>/dev/null || true
          git diff --cached --quiet || git commit -m "Sync ${{ steps.versions.outputs.next_version }}"

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
            --title "Sync ${{ steps.versions.outputs.next_version }}" \
            --body "Merges \`<stable-branch>\` back into \`<integration-branch>\` after releasing \`${{ steps.versions.outputs.release_version }}\`, and bumps the development version to \`${{ steps.versions.outputs.next_version }}\`." \
            --label sync
```

Notes specific to this template:

- **A patch bump** (`x.y.z` → `x.y.(z+1)`), matching `iru-swift-bump-version`'s own Step 5 documented convention
  for both the library and app cases (there is no `-SNAPSHOT`/`-dev.N`-style pre-release marker in either Swift
  case to gate a minor-vs-patch choice on, unlike the Java sibling's Maven `-SNAPSHOT` convention). If this
  repository does minor/major-level releases too, flag it as an open gap in the final report.
- `git add` lists every file either the library or the app path might touch and swallows the "no such file"
  error for whichever half doesn't apply (`|| true`) rather than needing a separate `git add` line per flavor —
  simpler than the Java/Android siblings' flavor-specific `git add`, since this skill already knows `flavor` at
  generation time and could narrow it, but keeping it broad costs nothing since `git add` on a nonexistent path
  is harmless once redirected.
- Same "Workflow permissions" repository-setting caveat as every sibling's `sync.yml` — the `permissions:` block
  here is necessary but not sufficient; Settings → Actions → General → "Workflow permissions" must also allow
  GitHub Actions to create pull requests, or `gh pr create` fails despite the token having the right scopes.
- `CHANGELOG.md` is deliberately not given its own rewrite logic beyond what `sync_versions.py` does (see
  below) — matching every sibling's own reasoning, its release section is written before the tag is published
  and arrives on `<integration-branch>` via the merge step above.

### `.github/scripts/sync_versions.py`

Reads `RELEASE_VERSION`/`NEXT_VERSION` from the environment and rewrites exactly the same files
`iru-swift-bump-version` rewrites for each flavor, reusing that skill's own verified regexes so a manual
`/iru-swift-bump-version` run and this CI-driven script never drift apart:

```python
#!/usr/bin/env python3
"""Rewrites version references after a release, for the Sync workflow.

Reads RELEASE_VERSION and NEXT_VERSION from the environment. For a library,
rewrites version.txt (if it exists) and reopens CHANGELOG.md's [Unreleased]
section — the release section itself was already written before the tag was
published. For an app, bumps MARKETING_VERSION/CURRENT_PROJECT_VERSION in
project.yml or Project.swift. Mirrors iru-swift-bump-version's own Step 3/4
rewrite rules exactly.
"""
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def update_version_txt(release_version):
    path = REPO_ROOT / "version.txt"
    if not path.exists():
        return
    path.write_text(release_version + "\n")


def update_readme_package_snippets(release_version):
    path = REPO_ROOT / "README.md"
    if not path.exists():
        return
    text = path.read_text()
    updated, n = re.subn(
        r'((?:from|exact)\s*:\s*)"[^"]*"',
        lambda m: f'{m.group(1)}"{release_version}"',
        text,
    )
    if n:
        path.write_text(updated)


def update_project_yml(next_version):
    path = REPO_ROOT / "project.yml"
    if not path.exists():
        return
    text = path.read_text()
    text, n_mv = re.subn(r'(MARKETING_VERSION:\s*)\S+', lambda m: f'{m.group(1)}{next_version}', text, count=1)
    if n_mv == 0:
        sys.exit("project.yml: MARKETING_VERSION not found")

    def bump(m):
        return f"{m.group(1)}{int(m.group(2)) + 1}"

    text, n_cpv = re.subn(r'(CURRENT_PROJECT_VERSION:\s*)(\d+)', bump, text, count=1)
    if n_cpv == 0:
        sys.exit("project.yml: CURRENT_PROJECT_VERSION not found")
    path.write_text(text)


def update_project_swift(next_version):
    path = REPO_ROOT / "Project.swift"
    if not path.exists():
        return
    text = path.read_text()
    text, n_mv = re.subn(
        r'("MARKETING_VERSION":\s*)"[^"]*"', lambda m: f'{m.group(1)}"{next_version}"', text, count=1
    )
    if n_mv == 0:
        sys.exit("Project.swift: MARKETING_VERSION not found")

    def bump(m):
        return f'{m.group(1)}"{int(m.group(2)) + 1}"'

    text, n_cpv = re.subn(r'("CURRENT_PROJECT_VERSION":\s*)"(\d+)"', bump, text, count=1)
    if n_cpv == 0:
        sys.exit("Project.swift: CURRENT_PROJECT_VERSION not found")
    path.write_text(text)


def update_changelog(today):
    path = REPO_ROOT / "CHANGELOG.md"
    if not path.exists():
        return
    text = path.read_text()
    updated, n = re.subn(
        r'^## \[Unreleased\]\s*\n(?:[ \t]*\n)*',
        '## [Unreleased]\n\n',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if n:
        path.write_text(updated)


def update_antora(release_version):
    path = REPO_ROOT / "docs" / "antora.yml"
    if not path.exists():
        return
    text = path.read_text()
    updated, n = re.subn(r"(?m)^version:.*$", f"version: {release_version}", text, count=1)
    if n:
        path.write_text(updated)


def main():
    release_version = os.environ["RELEASE_VERSION"]
    next_version = os.environ["NEXT_VERSION"]
    import datetime

    today = datetime.date.today().isoformat()

    # Library path — version.txt and the README dependency snippet always reflect the last actual RELEASE (the
    # real, taggable version), never NEXT_VERSION, which has no git tag yet. The merge step that runs before
    # this script already carries both forward correctly from the stable branch, so these two calls are a
    # defensive no-op in the common case, not the primary mechanism — they matter when the merge itself didn't
    # touch the file (e.g. it was already in sync) or a manual conflict resolution got it wrong.
    update_version_txt(release_version)
    update_readme_package_snippets(release_version)
    update_changelog(today)

    # App path — MARKETING_VERSION/CURRENT_PROJECT_VERSION track the *next* development version, the same
    # "-SNAPSHOT"-equivalent bump every sibling's own sync_versions.py performs.
    update_project_yml(next_version)
    update_project_swift(next_version)

    update_antora(release_version)


if __name__ == "__main__":
    main()
```

Notes specific to this template:

- **`update_version_txt`/`update_readme_package_snippets` are called with `release_version`, not
  `next_version`** — a deliberate correctness choice, not an oversight, caught and fixed while verifying this
  skill (see "Known quirks" below). `version.txt` and a library's README `.package(...)` snippet must always
  name a version that actually exists as a git tag; `next_version` never does (it's the *next*, not-yet-released
  value) — writing it there would advertise a dependency version a consumer's `swift build` can't resolve. The
  merge step that runs immediately before this script already carries the correct `release_version` value
  forward from the stable branch (where `iru-swift-bump-version`/`iru-release` set it before the tag was cut),
  so these two calls are a defensive reaffirmation, not the primary mechanism.
- Every `update_*` function no-ops cleanly when its target file doesn't exist — safe to run against either a
  library-only or app-only repository without branching the script itself on `flavor`.
- `update_changelog` here only reopens a fresh `[Unreleased]` heading — unlike `iru-swift-bump-version`'s own
  `CHANGELOG.md` rewrite (which also inserts the dated release-version heading), this script's release section
  was already written and tagged before the Release was published, so only the fresh `[Unreleased]` reopening is
  this script's job; adjust the regex per `iru-swift-bump-version`'s own verified form if a repository's
  `CHANGELOG.md` needs the fuller rewrite instead.
- `update_project_swift`'s regex assumes the same `"MARKETING_VERSION": "..."` dictionary-literal shape
  `iru-swift-bump-version`'s own Step 4 verified — a `Project.swift` with a different `SettingsDictionary`
  construction needs manual review after this script runs (same caveat that skill's own report step states).

## Step 9 — `security.yml`, `.github/dependabot.yml`, and `lcov_to_sonar_generic.py`

Runs on every pull request and on every push to the integration/stable branches (just the stable branch for
`main-only`), plus a weekly schedule so CodeQL/OSV-Scanner findings don't go stale between pushes. Each job is
individually omittable via the matching `security-*` `args` key (Step 0); drop that whole job's YAML — not just
its `if:` — when the resolved value is `no`:

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

  # Omit this whole job if security-codeql: no (Step 0). CodeQL's swift extractor only runs on a macOS runner —
  # there is no Linux Swift CodeQL support, unlike every other language this catalog's CodeQL jobs cover.
  codeql:
    name: CodeQL analysis
    runs-on: <runner>
    permissions:
      contents: read
      security-events: write
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Select Xcode <xcode-version>
        uses: maxim-lobanov/setup-xcode@v1
        with:
          xcode-version: '<xcode-version>'
      - name: Initialize CodeQL
        uses: github/codeql-action/init@v4
        with:
          languages: swift
          build-mode: autobuild
          # If autobuild ever fails against this project's layout, switch to build-mode: manual and add an
          # explicit build step here instead (flavor: library — `swift build`; flavor: app — `xcodegen
          # generate`/`tuist generate` then `xcodebuild build -scheme <Scheme>`), the same fallback the Java/
          # Android siblings document for their own autobuild step.
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
```

Notes specific to this template:

- `codeql`'s `runs-on: <runner>` and its own `maxim-lobanov/setup-xcode` step make this the only `security.yml`
  job that runs on a macOS runner (and therefore the only one subject to the ~10x minutes-cost note) — every
  other language this catalog's `iru-setup-*-github-workflows` siblings cover runs CodeQL on `ubuntu-latest`;
  Swift genuinely cannot.
- `actions/dependency-review-action@v5.0.0` and the OSV-Scanner reusable-workflow ref are pinned to an exact
  tag, not a floating major — see Step 2's table for why.
- None of the four jobs need a secret beyond the automatically provided `GITHUB_TOKEN`.
- If `github.com` public-repository default CodeQL setup is simpler for this repository than a workflow-based
  CodeQL job, note that as an alternative in the final report instead of writing the `codeql` job, same as every
  sibling.

### `.github/dependabot.yml`

```yaml
version: 2
updates:
  - package-ecosystem: swift
    directory: /
    schedule:
      interval: weekly
    groups:
      swift-dependencies:
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

Always generated (or updated) regardless of the `security-*` args — grouped weekly updates for the `swift`
ecosystem (`Package.swift`'s own `dependencies:`, and, for an app, `Packages/Core/Package.swift`'s — Dependabot's
`swift` ecosystem support scans every `Package.swift` it finds under `directory: /` recursively, no separate
entry needed per nested package) and for the workflows this skill itself just wrote (`github-actions`). If
`.github/dependabot.yml` already exists with entries for other ecosystems, preserve them — only add or update
the `swift` and `github-actions` entries above (see Step 1's stop-or-update path).

### `.github/scripts/lcov_to_sonar_generic.py`

Referenced by Step 4's library-flavor coverage-conversion step. A small, from-scratch SonarQube Generic Test
Coverage XML converter — verified end-to-end during this skill's own verification pass (Step 13) against a real
`coverage.lcov` produced by `xcrun llvm-cov export -format=lcov`:

```python
#!/usr/bin/env python3
"""Converts an lcov coverage report (xcrun llvm-cov export -format=lcov) into
SonarQube's Generic Test Coverage XML format (sonar.coverageReportPaths).

Usage: python3 lcov_to_sonar_generic.py coverage.lcov > sonarqube-generic-coverage.xml

File paths are rewritten relative to the current working directory, since
llvm-cov's SF: lines are always absolute and Sonar expects project-relative
paths.
"""
import os
import sys
import xml.sax.saxutils as sx


def main():
    lcov_path = sys.argv[1] if len(sys.argv) > 1 else "coverage.lcov"
    root = os.getcwd()
    files = []
    current = None
    with open(lcov_path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("SF:"):
                current = {"path": line[3:], "lines": []}
            elif line.startswith("DA:") and current is not None:
                lineno, hits = line[3:].split(",", 1)
                current["lines"].append((int(lineno), int(hits) > 0))
            elif line == "end_of_record" and current is not None:
                files.append(current)
                current = None

    out = ['<coverage version="1">']
    for f in files:
        rel = os.path.relpath(f["path"], root)
        out.append(f'  <file path="{sx.escape(rel)}">')
        for lineno, covered in f["lines"]:
            out.append(f'    <lineToCover lineNumber="{lineno}" covered="{"true" if covered else "false"}"/>')
        out.append("  </file>")
    out.append("</coverage>")
    print("\n".join(out))


if __name__ == "__main__":
    main()
```

Written only when `flavor: library` **and** `sonar` isn't `none` — omit this file entirely otherwise (the app
flavor uses SonarSource's own `xccov-to-sonarqube-generic.sh`, fetched at CI time rather than vendored, since it
needs no adaptation for this catalog's use — see Step 5).

## Step 10 — Placeholder resolution table

| Placeholder | Resolved from |
|---|---|
| `<integration-branch>` / `<stable-branch>` | Step 1 branch survey / `args` |
| `<runner>` | Step 0 (`args`, default `macos-26`) |
| `<xcode-version>` | Step 0/2 |
| `<linux-swift-tag>` | Step 2's live Docker Hub lookup, fallback `6.3-noble` |
| `<Name>` | Library: `Package.swift`'s target/product name (Step 1). Not used for the app flavor. |
| `<AppName>` / `<app-name>` | App: `project.yml`'s `name:` / `Project.swift`'s `Project(name:` (Step 1) |
| `<repo>` | Parsed from `git remote get-url origin`, used only as DocC's `--hosting-base-path` |
| `<team-id>` | Asked directly (Step 7) — no run-time signal for it |
| `<sonar-host-url>` / `<sonar-organization>` / `<sonar-project-key>` | Step 0/1 Sonar survey / `args`; only needed when `sonar` isn't `none` |
| `<generator>` | Step 1 (`project.yml` vs. `Project.swift`) |

Apply the `flavor`/`sonar`/`distribution`/`signing`/`release-please`/`branching` gating resolved in Steps 0–1:
drop every block the templates above mark with an "Omit this … if …" comment (and that comment itself) when the
matching value doesn't apply.

## Step 11 — Conditional-blocks table

| Block | Appears when |
|---|---|
| `build-test-linux` job (Step 4) | `flavor: library`, and Step 1 confirms the package's `Sources/` has no Apple-only imports |
| DocC/Antora/Pages steps + `deploy-docs` job | Any push landing on `<stable-branch>` — both flavors |
| `Run SonarQube analysis` step + its coverage-conversion step | `sonar` is `cloud` or `self-hosted` |
| `lcov_to_sonar_generic.py` (vendored file) | `flavor: library`, `sonar` isn't `none` |
| `xccov-to-sonarqube-generic.sh` (fetched at CI time) | `flavor: app`, `sonar` isn't `none` |
| `release-please` job in `release.yml` | `flavor: library`, `release-please: yes` |
| `Fetch distribution signing certificates` step | `flavor: app`, `signing: fastlane-match` |
| `Write the App Store Connect API key` step + every `-authenticationKeyPath` flag | `flavor: app`, `signing: api-key` |
| `Upload to TestFlight` steps | `flavor: app`, `distribution` isn't `none` (`fastlane pilot` for `fastlane-match`, the action for `api-key`) |
| `Archive and export <AppName>-macOS` + `Notarize` steps | `flavor: app`, `macos` selected, `distribution` isn't `none` |
| `codeql` job | `security-codeql: yes` |
| `dependency-review` / `osv-scanner` / `gitleaks` jobs | matching `security-*: yes` |
| `sync.yml` + `sync_versions.py` | `branching: gitflow` only |

## Step 12 — File matrix

| `flavor` × `branching` | Files written |
|---|---|
| `library` / `gitflow` | `.github/workflows/build.yml`, `release.yml`, `sync.yml`, `.github/scripts/sync_versions.py`, `.github/scripts/lcov_to_sonar_generic.py` (only if `sonar` isn't `none`), `security.yml`, `.github/dependabot.yml` |
| `library` / `main-only` | Same, minus `sync.yml`/`sync_versions.py` |
| `app` / `gitflow` | `.github/workflows/build.yml`, `release.yml`, `sync.yml`, `.github/scripts/sync_versions.py`, `security.yml`, `.github/dependabot.yml` (no `lcov_to_sonar_generic.py` — the app flavor uses the fetched-at-CI-time `xccov-to-sonarqube-generic.sh` instead) |
| `app` / `main-only` | Same, minus `sync.yml`/`sync_versions.py` |

## Step 13 — Write the files, then verify

Write (or, per Step 1's stop-or-update decision, carefully update) every file from Step 12's matrix with the
filled-in templates from Steps 4–9. `sync.yml` and `sync_versions.py` are written together — never write one
without the other, and never write either for `main-only`. `security.yml` and `.github/dependabot.yml` are
always written (or updated), independent of `flavor`/`branching`/`sonar`/`distribution` — only their own
`security-*` args gate individual jobs within `security.yml`.

Run through the `iru-gate-runner` agent where output could be long. Verification directory:
`$TMPDIR/iru-verify/swift/workflows/` (created fresh; never inside this repository):

1. Render both the `library` and `app` variants of every YAML file to disk (every combination of `sonar`/
   `distribution`/`signing`/`branching`/`release-please` that changes which blocks appear at least once each).
2. YAML-validate every rendered file: `ruby -ryaml -e 'YAML.load_file(ARGV[0])' <file>` (Ruby ships with macOS,
   confirmed present in this environment) — or `python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))"`
   if PyYAML is available. The top-level `on:` key round-tripping as the boolean `True` under YAML 1.1's
   bare-word resolution is a known false flag in a Python-based validator, not a defect in the generated
   workflow (same note the Java/TypeScript/Android siblings record) — don't quote `on:` in the template to "fix"
   it.
3. Resolve every `uses:` ref with `gh api repos/<owner>/<repo>/git/ref/tags/<ref>` or `git ls-remote --tags
   https://github.com/<owner>/<repo> <ref>`, recording which actions lack a floating major tag (Step 2's table
   already reflects this skill's own such run).
4. Run the library flavor's `build.yml` shell steps for real against Task 33's existing scaffold, copied first
   (never mutate the original) — see "Known quirks / verification notes" below for exact commands and results.

### Known quirks / verification notes (September 2026, against Xcode 27.0 / Swift 6.4, no `brew` installed)

- **Verified for real** in `$TMPDIR/iru-verify/swift/workflows/library-copy` (a fresh `cp -R` of Task 33's own
  `$TMPDIR/iru-verify/swift/library` scaffold, package `ExampleLibrary`, `.build`/`Package.resolved`/
  `coverage.lcov` removed first since the copied `.build` carried stale absolute-path symlinks back to the
  original directory):
  - `swift build` — succeeds, including re-resolving `swift-docc-plugin` from the local package cache.
  - `swift test --enable-code-coverage --parallel` — succeeds, `1 test in 0 suites passed` (the XCTest-framed
    test from `iru-setup-swift-library`'s own template).
  - The `Export lcov coverage` step's `find`-based binary lookup + `xcrun llvm-cov export -format=lcov
    --ignore-filename-regex='(Tests/|DerivedSources)'` — succeeds, produces the exact `SF:`/`FN:`/`DA:`/
    `end_of_record` shape `iru-swift-coverage` already documents.
  - `swift format lint --strict --recursive Sources Tests` — exits `0` against the scaffold's own
    `.swift-format` (written by `iru-setup-swift-library`).
  - `python3 .github/scripts/lcov_to_sonar_generic.py coverage.lcov` — produces valid, well-formed
    `sonarqube-generic-coverage.xml` (confirmed with `xml.dom.minidom.parse`), with **project-relative** `path`
    attributes (`Sources/ExampleLibrary/ExampleLibrary.swift`), not the absolute paths `llvm-cov` itself emits —
    the `os.path.relpath` rewrite in the script is required for this, not cosmetic; a first draft without it
    produced Sonar-unusable absolute paths.
  - The DocC step: `swift package --allow-writing-to-directory docc-output generate-documentation --target
    ExampleLibrary --transform-for-static-hosting --hosting-base-path example-library --output-path
    docc-output` — **fails** with an `NSCocoaErrorDomain` "couldn't be moved" (or, with the parent pre-created
    but not the leaf, an `Operation not permitted`) error unless the **parent** of `--output-path`'s directory
    already exists before the command runs (`mkdir -p docc-output` first) — confirmed by first running without
    any pre-created directory (fails), then with only `docs/build/site` pre-created while targeting
    `docs/build/site/api` (still fails, permission error), then with `docc-output` itself pre-created (succeeds,
    produces `index.html`/`documentation/`/`data/`/etc.). This refines `iru-setup-swift-library`'s own Step 10
    note that `--output-path` alone is enough — in this skill's own CI context (a script computing the path
    fresh, not an interactive shell that may have already `cd`'d through intermediate directories) the `mkdir
    -p` is not optional.
- **All ten rendered `build.yml`/`release.yml`/`sync.yml`/`security.yml`/`dependabot.yml` files (both `flavor`
  variants, `sonar`/`distribution`/`signing`/`branching`/`release-please` combinations exercised at least once
  each) YAML-validated clean** with `ruby -ryaml -e 'YAML.load_file(ARGV[0])'` — Ruby ships with macOS, confirmed
  present in this environment, no PyYAML fallback needed.
- **A real bug was found and fixed in `sync_versions.py` while verifying it end-to-end, not just
  `py_compile`-checked**: an earlier draft called `update_version_txt(next_version)` and
  `update_readme_package_snippets(next_version)` — writing the **next**, not-yet-released version into
  `version.txt` and the library's README `.package(url:, from:/exact:)` snippet. Running the script against a
  sample fixture (`version.txt: 1.0.0`, a README snippet at `1.0.0`, `RELEASE_VERSION=1.1.0`,
  `NEXT_VERSION=1.1.1`) exposed the problem concretely: both files ended up advertising `1.1.1`, a version with
  **no git tag at all** — a consumer copy-pasting that snippet would get an unresolvable `swift build` error, and
  `version.txt`'s own documented purpose (`iru-swift-bump-version`'s Step 3: "a plain one-line file holding the
  **current released** version") was violated outright. Fixed to call both with `release_version` instead;
  re-run against the same fixture correctly produced `1.1.0` in both files (verified: `version.txt` → `1.1.0`,
  README's `from:` → `"1.1.0"`), while `project.yml`/`Project.swift`'s `MARKETING_VERSION` and `Project.swift`'s/
  `project.yml`'s `CURRENT_PROJECT_VERSION` correctly still bump to `next_version`/`+1` (`1.1.1`/`2`) — that half
  *is* a genuine "next development version" concept, unlike the library's tag-bound files. `docs/antora.yml`'s
  `version:` field and `CHANGELOG.md`'s `[Unreleased]` reopening were both already correct in the first draft
  (`release_version` and no-argument respectively) and needed no fix. The version embedded in this SKILL.md
  reflects the fixed, re-verified form.
- **`gem install --user-install slather` genuinely fails in this environment** — not merely "unreachable", a
  real, reproducible failure: this machine's system Ruby is `2.6.10` (macOS's bundled interpreter; no `brew`,
  `rbenv`, `rvm`, or `asdf` present to install a newer one), and `slather`'s own dependency chain (`securerandom
  >= 0.3`) requires Ruby `>= 3.1.0`. Confirmed via `gem env`: only one Ruby is on this machine's `PATH` at all.
  Separately from the install failure, slather's own design fundamentally requires an `.xcodeproj`/
  `.xcworkspace` to locate build settings — it has no path for a bare SwiftPM package with neither, which
  `iru-setup-swift-library`'s scaffold never produces. **Both problems independently rule out slather for the
  library flavor** — this skill's `lcov_to_sonar_generic.py` (verified above) is the actual default for exactly
  the reason Task 36's own brief anticipated, not a fallback of convenience.
- **SonarSource's `xccov-to-sonarqube-generic.sh` was located and read in full** (at
  `SonarSource/sonar-scanning-examples/swift-coverage/swift-coverage-example/xccov-to-sonarqube-generic.sh` —
  not the more guessable `swift-coverage/xccov-to-sonarqube-generic.sh` path) — confirmed by reading its actual
  source that it takes exactly one positional argument, an `.xcresult` directory path, and shells out to `xcrun
  xccov view --archive`; it **cannot** consume an lcov file at all. This confirms the flavor split in Steps 4/5:
  the library flavor's `swift test`-based pipeline never produces an `.xcresult`, so this script only fits the
  app flavor's `xcodebuild test`-based one. Not independently re-run end-to-end against a real `.xcresult` here
  (that needs an actual generated `.xcodeproj`, which `xcodegen`/`tuist` being uninstallable in this environment
  — no `brew` — rules out, the same limitation `iru-setup-apple-app`'s own verification records); its logic was
  confirmed by reading the script's source, not by executing it.
- **GitHub's hosted macOS runner image labels were confirmed live**, not assumed:
  `gh api repos/actions/runner-images/contents/images/macos --jq '.[].name'` returned
  `macos-14-Readme.md`/`macos-14-arm64-Readme.md`, `macos-15-Readme.md`/`macos-15-arm64-Readme.md`,
  `macos-26-Readme.md`/`macos-26-arm64-Readme.md`, and `xcode-27-arm64-Readme.md` (no non-arm64 `xcode-27`
  variant published yet). Reading each `-arm64-Readme.md`'s own content: `macos-26`'s `### Xcode` table lists
  `26.6 (default)` down to `26.0.1`, with a `### Linters` section listing `SwiftLint 0.65.1`; `xcode-27`'s table
  lists only `27.0 (beta) (default)`, with **no** `### Linters` section at all. This directly confirms Step 0's
  runner-choice guidance (default `macos-26` for its preinstalled SwiftLint and GA stability) and Step 4/5's
  `command -v swiftlint >/dev/null ||` guard (required unconditionally, since the `xcode-27` image never has it).
- **`actions/dependency-review-action` and `google/osv-scanner-action`'s reusable workflow still have no
  floating major tag** (re-confirmed via `git ls-remote --tags` returning zero matches for a bare `v5`/`v2`),
  same finding the Android sibling's own Step 13 already recorded for the Java/Kotlin ecosystem — this is an
  action-level fact, not a Swift-specific one, but re-verified here rather than assumed.
- **`github/codeql-action`'s `/releases/latest` endpoint returns the unrelated `codeql-bundle-v2.27.0` tag, not
  a CLI version** — re-confirmed here; `git ls-remote --tags https://github.com/github/codeql-action v4`
  resolves the real floating major used in Step 9's template.
- **The Linux Swift Docker toolchain lags the Apple-toolchain-bundled Swift version** — this machine reports
  Swift `6.4` (`swift --version`, bundled with Xcode 27.0), but Docker Hub's `library/swift` repository's newest
  `6.x` tags top out at `6.3.3`/`6.3-noble` (confirmed via the Docker Hub v2 tags API) — no `6.4` tag exists yet.
  Step 2's table records `6.3-noble` as the fallback specifically because of this gap, not as a guess; re-check
  at generation time rather than assuming the two numbers track each other release-for-release.
- **Never executed, and never a blocker** — recorded here explicitly rather than silently assumed correct:
  `swiftlint` itself (no `brew`, matching every other Swift-stack skill in this catalog's own recorded
  limitation), `xcbeautify`/`xcodegen`/`tuist` and therefore the entire app-flavor `build.yml`/`release.yml`
  pipeline beyond its YAML/placeholder structure, the `SonarSource/sonarqube-scan-action` step itself (needs a
  real `SONAR_TOKEN` and Sonar project), `googleapis/release-please-action`, `fastlane match`/`pilot`,
  `apple-actions/upload-testflight-build`, `xcrun notarytool submit`/`stapler staple` against a real signed
  archive, and the `codeql`/`osv-scanner`/`gitleaks`/`dependency-review` jobs' actual scan behavior (their
  `uses:` refs were confirmed to resolve, per point 3 of Step 13's own list above, but the scans themselves were
  never run against this repository).

## Step 14 — Report

Summarize what happened: whether each file in Step 12's matrix was created fresh, updated in place, or left
untouched (Step 1's stop path); any open gaps noted along the way (missing `docs/antora.yml`, a `Packages/Core`
with no `swift-docc-plugin` dependency for the app flavor's DocC step, README/version wording that didn't match
`sync_versions.py`'s default regexes, a `<team-id>` the user still needs to supply).

State explicitly what was wired versus omitted, and why:

- **`flavor`**: `library` or `app` — which pipeline shape (`ubuntu-latest` matrix leg + lcov-to-generic-XML vs.
  per-platform `xcodebuild test` + `xccov-to-sonarqube-generic.sh` + archive/sign/upload) was generated.
- **`runner`**: `macos-26` or `xcode-27` — restate the GA-vs-preview tradeoff and whether the `brew install
  swiftlint` guard actually fires for this choice.
- **`branching`**: `gitflow` (`sync.yml` included) or `main-only` (state this omission plainly).
- **`sonar`**: `cloud`/`self-hosted`/`none` — which coverage-conversion step/file was generated (or omitted).
- **`distribution`**/**`signing`** (app only): which `release.yml` steps and secrets are actually needed as a
  result.
- **`release-please`** (library only): whether the optional job was included.
- **Security block**: which of the four `security-*` jobs were included versus omitted, and confirm
  `.github/dependabot.yml` was written regardless.

Then give the required-secrets/environments table — list only the rows that apply to what was actually
generated:

| Secret | Purpose | Only needed when |
|---|---|---|
| `SONAR_TOKEN` | Auth token for the SonarQube/SonarCloud scan | `sonar` is `cloud` or `self-hosted` |
| `MATCH_GIT_URL` / `MATCH_PASSWORD` | `fastlane match`'s certs-repo URL and its encryption passphrase | `flavor: app`, `signing: fastlane-match` |
| `APP_STORE_CONNECT_API_KEY_ID` / `_ISSUER_ID` / `_KEY_BASE64` | App Store Connect API key (auth for `-allowProvisioningUpdates`, TestFlight upload, and — regardless of `signing` — notarization on macOS) | `flavor: app`, `signing: api-key`; also needed purely for notarization when `macos` is selected and `signing: fastlane-match` |
| `GITHUB_TOKEN` | `sync.yml`'s `gh` calls, `security.yml`'s CodeQL/gitleaks jobs | Automatic — no setup needed |

`sync.yml` also needs the repository setting under Settings → Actions → General → "Workflow permissions" set to
allow GitHub Actions to create pull requests. The Pages deploy job needs Settings → Pages → "Build and
deployment" → Source set to **GitHub Actions**. Call both out explicitly.

**Warn explicitly:**

- **The user must review every generated (or updated) workflow file before relying on it.** Branch names, the
  Apple Developer Team ID, and the signing/distribution setup were inferred or asked for directly and may need
  correction — and because this pipeline handles signing keys and can publish to TestFlight/App Store, a bad
  assumption here has real consequences. Recommend a dry run via `workflow_dispatch` before trusting it on a
  real release.
- Every secret in the table above, and the matching SonarCloud project / Apple Developer Program membership /
  `fastlane match` certs repository / App Store Connect API key, must already exist before CI can pass — this
  skill only writes the workflow YAML, it never creates any of those accounts or credentials itself.
- Which toolchain versions (Step 2) came from a live lookup versus this skill's recorded September 2026
  fallback, and specifically that `actions/dependency-review-action`/`google/osv-scanner-action`'s reusable
  workflow are pinned to an exact tag rather than a floating major, and that the Linux Swift Docker tag can lag
  the Apple-toolchain Swift version — re-check all three at the next regeneration.
- **`gem install --user-install slather` does not work in this catalog's own verification environment** (Ruby
  too old) and slather's own design doesn't apply to a bare SwiftPM package regardless of Ruby version — the
  library flavor's `lcov_to_sonar_generic.py` conversion is the one this skill actually generates and verified;
  don't substitute slather in without first confirming both problems don't apply to the target repository/CI
  runner.
- **Unverified locally, and never a blocker** (Step 13): SwiftLint/`xcbeautify`/`xcodegen`/`tuist` themselves
  (no `brew` in this skill's own environment), the entire app-flavor pipeline beyond its rendered YAML/
  placeholder structure, the actual SonarQube scan, `release-please`, Fastlane's `match`/`pilot`, TestFlight/App
  Store Connect uploads, notarization, and the security jobs' real scan behavior (only their `uses:` refs were
  confirmed to resolve).
