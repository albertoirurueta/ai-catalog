---
name: iru-setup-readme
description: Create or update the root `README.md` for a repository — a brief description, badges (CI status, SonarCloud/SonarQube, npm, Maven Central, Swift Package Index, etc.), a project status table (language, versions, platforms, license, CI, quality tools), documentation links (Antora site, Maven site report, SonarCloud dashboard, generated API docs such as TypeDoc/Compodoc/Storybook/Dokka/DocC, CHANGELOG), installation instructions (Maven/Gradle/npm/SwiftPM/etc. dependency snippets, or a "run it locally"/store-listing section for apps, matched to the project's actual stack and build tool), and a short "how it works" section with a runnable example. Invoke as `/iru-setup-readme`, or `/iru-setup-readme sonar: none` (an `args` line — the only key it accepts) to suppress Sonar badges and dashboard links even when a `sonar {}` block or `sonar-project.properties` exists, so an orchestrator that resolved `sonar: none` gets a README matching that choice. Explores the repository's actual state (`pom.xml`/`build.gradle`/`package.json`/`Package.swift`/Android Gradle modules/Xcode or Tuist project files/etc., git remote, GitHub Actions workflows, Sonar config, Antora docs, `CHANGELOG.md`, `LICENSE`, source code) to fill in every section — a section whose source material doesn't exist yet (e.g. a brand-new, mostly empty repository) is omitted rather than filled with placeholders or invented content. If `README.md` already exists, warns the user and shows the proposed new content as a diff before writing anything, so they can accept or skip the changes. Use whenever a repository needs a README bootstrapped or refreshed from what's actually there, instead of hand-writing it.
model: sonnet
---

# Setup Readme

Create or refresh a repository's root `README.md` by exploring what actually exists in the repository —
build files, CI workflows, quality-tool config, documentation, license, and source code — and composing only the
sections that real material supports. Never invent version numbers, badge URLs, dashboard links, or example code
that don't correspond to something actually present.

## Step 0 — Resolve inputs

This skill takes a single optional `args` line, `sonar: <cloud|self-hosted|none>`, passed by this catalog's
`iru-setup-*-repository` orchestrators with the value they resolved. Only `none` changes behaviour: Step 3 then
skips every SonarCloud/SonarQube badge and Step 5 the dashboard link, even if Sonar configuration is present on
disk (a `mode: existing` repository may carry a `sonar {}` block the user has just chosen not to wire up —
verified in Task 53.2, where a README otherwise gained eleven SonarCloud badges for a project the run had explicitly
declined). Any other value, or no `args` at all, means "detect from the repository" as Step 3 describes. Record
in Step 11 when badges were suppressed because of this line.

## Step 1 — Check whether `README.md` already exists

Look at the repository root for `README.md`.

- **Not found**: continue to Step 2; the final write in Step 10 happens without needing approval first (there is
  nothing to lose), though the composed content is still worth a quick summary in Step 11.
- **Found**: warn the user up front that a `README.md` already exists and this skill will propose changes for
  them to review rather than overwriting it silently. Read it now — its content matters later: Step 9 shows a
  diff against it, and any hand-written section that doesn't map onto Steps 3–8 (e.g. a "Contributing" or
  "Acknowledgements" section unrelated to this skill's scope) should be preserved in the proposed version rather
  than dropped. Continue to Step 2.

## Step 2 — Gather project identity

- **Repository name and host**: `git remote get-url origin`; if it's GitHub, extract `<owner>/<repo>` — used for
  badge URLs, GitHub Pages links, and compare links throughout. If there's no remote, or it isn't GitHub, skip
  every GitHub-specific link/badge later and note this in Step 11's report rather than guessing a URL scheme.
- **Description/tagline**: prefer, in order, a `<description>` in `pom.xml`, a `"description"` in `package.json`,
  or an existing Antora `docs/modules/ROOT/pages/index.adoc` overview paragraph. If none exist, ask the user for a
  one-sentence description rather than inventing one — this is the first thing a reader sees.
- **License**: look for `LICENSE`/`LICENSE.txt`/`LICENSE.md` at the root. Identify common licenses by their actual
  text (Apache-2.0, MIT, BSD, GPL family) rather than assuming; if the file exists but doesn't match a license you
  can confidently name, still link to it but describe it generically ("see `LICENSE`") rather than guessing a name.
  If no license file exists, omit the License section entirely — don't claim a license the repository doesn't
  declare.
- **Primary language, framework, and build tool**: if an `iru-explore` report with a `- Project type:` line is
  already available earlier in this conversation, reuse that instead of re-detecting from scratch — just confirm
  the manifest(s) it names are still present. Otherwise detect from the manifests actually on disk:
  - `pom.xml` — Java/Maven.
  - `build.gradle`/`build.gradle.kts` with no Android/Kotlin-Multiplatform plugin — Java or Kotlin/Gradle.
  - `package.json` + `pyproject.toml`/`setup.py`/`Cargo.toml` — Python/Rust with incidental Node tooling; see below
    for when `package.json` itself is the library/app.
  - `package.json` with `vite` + `react` dependencies — Vite+React web app.
  - `package.json` with `@angular/cli` + an `angular.json` at the root — Angular CLI web app.
  - `pom.xml`/`build.gradle*` with `hilla-spring-boot-starter` (or `package.json` with `@vaadin/hilla`) and a
    `src/main/frontend/` directory — a Java/Spring Boot + Hilla full-stack app; treat it as both a Java backend
    and a frontend for badges/snippets/status-table purposes.
  - `package.json` with `expo` and/or `react-native`, plus an `app.json`/`app.config.js`/`app.config.ts`,
    `metro.config.js`, and/or `eas.json` — Expo/React Native app.
  - `package.json` with `@ionic/*`/`@capacitor/core` dependencies, plus `capacitor.config.ts`/`.js`/`.json` and/or
    `ionic.config.json` — Ionic/Capacitor app.
  - Gradle modules using the `com.android.library` or `com.android.application` plugin, usually alongside
    `gradle/libs.versions.toml` and a Compose BOM dependency — Android library or application respectively.
  - `Package.swift` (read its `products` to tell library vs. executable), or an Xcode project (`*.xcodeproj`,
    optionally generated from `project.yml` via XcodeGen or `Project.swift` via Tuist) — Swift/Apple-platform
    library or app.
  - `package.json` + `tsconfig.json` with none of the app-framework markers above — a plain TypeScript/npm
    library.
  - A repository can have more than one of these (e.g. a Maven library with an Antora docs site under `docs` that
    has its own `package.json` for the doc toolchain only, or a Hilla app that is both Java and TypeScript) —
    identify the build tool for the library/application itself, not incidental tooling.
- **Current version(s) and package/artifact identity**: read the identity from the source that actually owns it
  for the detected stack, not always `pom.xml`/`package.json`:
  - Maven: the `<version>` in `pom.xml` (immediately under the project's own `artifactId`, not a
    dependency/plugin), plus `groupId`/`artifactId`.
  - Gradle/Android library: `group` and `libraryVersion` (or equivalent) in `lib/build.gradle.kts`, falling back
    to a version property in `gradle.properties` when the build script references one.
  - npm/Vite/Angular/Expo/Ionic/TypeScript: the `"name"`/`"version"` in `package.json`.
  - Swift: the package name from `Package.swift`, with the version taken from git tags (SwiftPM has no in-file
    version field) — `git tag --sort=-v:refname | head -1`.
  - Xcode app: `MARKETING_VERSION` from the project's build settings (`project.pbxproj`, `project.yml`, or
    `Project.swift`, depending on which of Xcode/XcodeGen/Tuist generates the project).
  - Also find the latest released version for any stack: `git tag --sort=-v:refname | head -1` (or `gh release
    list --limit 1` if on GitHub with `gh` available). If the current version has no `-SNAPSHOT`/prerelease
    suffix and matches the latest tag, there's only one version to show, not a "current dev / latest release"
    pair.

## Step 3 — Gather badge sources

Only include a badge when its underlying resource actually exists — don't fabricate a badge for a CI workflow or
SonarCloud project that isn't configured yet.

- **CI status**: list `.github/workflows/*.yml`. For each workflow that looks like a build/test pipeline (not,
  say, a stale/dependabot-only workflow), add a status badge:
  `https://github.com/<owner>/<repo>/actions/workflows/<file>/badge.svg`, linking to
  `https://github.com/<owner>/<repo>/actions/workflows/<file>`.
- **SonarCloud/SonarQube** (skip entirely when Step 0 resolved `sonar: none`): check `sonar-project.properties` or `sonar.*` properties in `pom.xml`/`build.gradle*`
  (or an equivalent `sonar-project.properties` used by a non-Java stack) for `sonar.projectKey` (and
  `sonar.organization` if using SonarCloud) — this applies to any stack, not just Java/Maven. If found and hosted
  on SonarCloud, add the full metric set the reference Android READMEs use — Quality Gate Status,
  Maintainability Rating, Reliability Rating, Security Rating, Bugs, Code Smells, Coverage, Duplicated Lines (%),
  Lines of Code, Technical Debt, Vulnerabilities — each of the form
  `https://sonarcloud.io/api/project_badges/measure?project=<project-key>&metric=<metric>` (metric keys:
  `alert_status`, `sqale_rating`, `reliability_rating`, `security_rating`, `bugs`, `code_smells`, `coverage`,
  `duplicated_lines_density`, `ncloc`, `sqale_index`, `vulnerabilities`), each linking to
  `https://sonarcloud.io/summary/new_code?id=<project-key>`. If Sonar config exists but points at a self-hosted
  SonarQube instance instead, link the dashboard but skip the SonarCloud-specific badge images (they're a
  SonarCloud-only feature) and note this in Step 11.
- **Package registry badges**, only if the project is actually published there — never fabricate a badge for a
  registry the project has never published to:
  - **npm**: `img.shields.io/npm/v/<name>` (version) and `img.shields.io/npm/dm/<name>` (monthly downloads),
    linking to `https://www.npmjs.com/package/<name>`, when `package.json`'s `"name"` is confirmed published
    (e.g. a publish step in a GitHub Actions workflow, or the package is already live on the registry).
  - **Maven Central**: `https://maven-badges.herokuapp.com/maven-central/<group>/<artifact>/badge.svg` (or the
    `img.shields.io/maven-central/v/<group>/<artifact>` equivalent), linking to the Maven Central search page for
    that coordinate, when the `pom.xml` publishing profile actually targets Central (e.g. a
    `central-publishing-maven-plugin`/`nexus-staging-maven-plugin` configuration or a release-publish workflow
    step).
  - **Swift Package Index**: platform and Swift-version shields,
    `https://img.shields.io/endpoint?url=https%3A%2F%2Fswiftpackageindex.com%2Fapi%2Fpackages%2F<owner>%2F<repo>%2Fbadge%3Ftype%3Dplatforms`
    and `…%2Fbadge%3Ftype%3Dswift-versions`, linking to `https://swiftpackageindex.com/<owner>/<repo>`, when the
    package is confirmed listed there (or a `Package.swift` plus an SPI-focused release workflow strongly implies
    it — note the inference in Step 11 if not confirmed live).
- If none of the above exist yet, skip the badges section of the README entirely rather than leaving an empty
  heading.

## Step 4 — Build the project status table

Compose a small table from whatever Steps 2–3 actually resolved; omit rows with no data rather than writing "N/A":

| Row | Source                                                                                                                         |
| --- |--------------------------------------------------------------------------------------------------------------------------------|
| Language | Detected primary language + version (e.g. `Java 21`)                                                                           |
| Build tool | Maven / Gradle / npm / SwiftPM / Xcode / etc.                                                                                  |
| Current development version | The unreleased/SNAPSHOT version from the build file, if different from the latest release                                      |
| Latest release | The latest git tag / release version                                                                                           |
| Platform(s) | For Android/Apple/web projects only: Android / iOS / iPadOS / macOS / watchOS / web, as applicable                             |
| Min / target SDK | Android only: `minSdk` and compile/target SDK from the Gradle module, when they differ from the platform row above             |
| Kotlin / AGP | Android/Kotlin-Gradle only: Kotlin version and Android Gradle Plugin version, when pinned explicitly                           |
| Swift tools / deployment targets | Swift only: the Swift tools version from `Package.swift` and the platform deployment targets it declares          |
| Node engine | npm-based projects only: the `engines.node` range from `package.json`, if one is declared                                     |
| TypeScript | TypeScript projects only: the `typescript` version pinned in `package.json`/`package-lock.json`                               |
| Framework | Where applicable: the pinned framework version (React, Angular, Ionic, Expo, etc.)                                            |
| License | The license identified in Step 2, if any                                                                                       |
| CI | Which CI system and what it runs (e.g. "GitHub Actions for release and `develop` branch builds")                               |
| Quality | Which tools actually run — only list ones with real config found (SonarCloud, JaCoCo, Checkstyle, SpotBugs, PMD, ESLint, Detekt, SwiftLint, etc.) |

Omit every row in this extended set (platforms through framework) that doesn't apply to the detected stack — a
plain Java/Maven library still shows only the original rows.

## Step 5 — Gather documentation links

Include a link only when the thing it points to actually exists in the repository (or is confirmed published):

- **Antora documentation site**: if `docs/antora.yml` and `docs/antora-playbook.yml` exist, link to the published
  site. If a GitHub Pages workflow step publishes it (grep workflows for `gh-pages`/`ghaction-github-pages`), the
  URL is normally `https://<owner>.github.io/<repo>`; if you can't confirm it's actually published, still include
  the link but note in Step 11 that it's inferred from convention, not confirmed live.
- **Maven/Gradle site report**: if the CI workflow merges a Maven `site` (or Gradle equivalent) report into the
  published docs (e.g. a `mvn-site` subpath alongside the Antora output, matching this repository's own
  `develop`/`main` workflow pattern), link to it at that subpath.
- **Generated API docs published to GitHub Pages**: grep `.github/workflows/*.yml` for the publish step of each
  tool below, and link only the ones actually wired into a workflow — never assume one just because the stack
  matches:
  - **TypeDoc** (TypeScript libraries): a `typedoc` invocation feeding a Pages publish step, normally landing at
    `https://<owner>.github.io/<repo>/api`.
  - **Compodoc** (Angular): a `compodoc`/`@compodoc/compodoc` invocation, normally landing at
    `https://<owner>.github.io/<repo>/api`.
  - **Storybook** (React/Angular component libraries): a `build-storybook` (or `storybook build`) step publishing
    the static build, normally landing at `https://<owner>.github.io/<repo>/storybook` or
    `https://<owner>.github.io/<repo>/api/storybook`, depending on where the workflow places it.
  - **Dokka** (Android/Kotlin): a `dokkaHtml`/`dokkaGenerate` Gradle task feeding a Pages publish step, normally
    landing at `https://<owner>.github.io/<repo>/api`.
  - **DocC** (Swift): a `docc`/`xcodebuild docbuild` step (often via `docc-render`/`Swift-DocC-Plugin`) feeding a
    Pages publish step, normally landing at `https://<owner>.github.io/<repo>/api`.
  - Use the subpath the workflow actually publishes to rather than assuming `/api` when the workflow config makes
    a different path clear (e.g. `/storybook` vs. `/api/storybook`).
- **SonarCloud/SonarQube dashboard**: reuse the link built in Step 3.
- **Changelog**: if `CHANGELOG.md` exists at the root, link to it directly (`CHANGELOG.md`).
- Omit any of the above whose source doesn't exist — don't add a "Documentation" section at all if none of these
  resolve.

## Step 6 — Compose installation instructions

Match the snippet to the build tool detected in Step 2 — don't show a Maven snippet for a Gradle project or vice
versa:

- **Maven**: a `<dependency>` block with the real `groupId`/`artifactId`, using the latest release version; if the
  current build-file version is a distinct `-SNAPSHOT`, show both under "Latest release" / "Latest snapshot"
  (mirroring how a snapshot repository would need to be added — only mention that if the project's own POM/
  settings actually reference one).
- **Gradle (Kotlin DSL)**: `implementation("<group>:<artifact>:<version>")`. If the project publishes a
  `gradle/libs.versions.toml` version catalog, show that form too — the catalog entry under `[libraries]`
  (`<alias> = { module = "<group>:<artifact>", version.ref = "<versionAlias>" }`) plus the consuming
  `implementation(libs.<alias>)` line — instead of (or alongside) the plain coordinate form.
- **npm**: `npm install <name>`, using the real `package.json` name and its latest published version. Add the
  pnpm (`pnpm add <name>`) and/or yarn (`yarn add <name>`) equivalents only when the repository's own lockfile
  (`pnpm-lock.yaml` / `yarn.lock`) shows that's the package manager actually in use, rather than listing all
  three by default.
- **SwiftPM**: a `.package(url: "<repository-url>", from: "<version>")` entry for `Package.swift`, plus the
  matching `.product(name: "<ProductName>", package: "<PackageName>")` target dependency (read the real product
  name from `Package.swift`'s `products`), and the equivalent steps for Xcode users ("File > Add Package
  Dependencies…", paste the repository URL, select the product).
- **Python**: `pip install <package-name>`, using the real project name from `pyproject.toml`/`setup.py`.
- **Distributed apps** (Android/iOS apps, not libraries): when the manifest declares a store distribution (e.g. a
  Gradle `distribution`/Play publishing config, an App Store Connect/Fastlane/`eas submit` workflow step, or
  existing store metadata in the repository), replace the dependency snippet with store links the user fills in
  — `<App Store URL>`, `<TestFlight URL>`, `<Google Play URL>` — as placeholders, never invented real URLs.
  Otherwise (no store distribution config found, or the app isn't a library at all), show how to run it locally
  instead, matched to the detected stack: `npm start` / `npx expo start` (Expo/React Native), `ionic serve`
  (Ionic), `./gradlew installDebug` (Android), `xcodebuild -scheme <Scheme> -destination …` or "open in Xcode and
  run" (Apple platforms) — pick the one command that actually matches the project's own scripts/Gradle
  tasks/scheme rather than a generic default.
- If the build tool isn't one of the above, or the project isn't actually published/publishable/runnable yet (no
  registry/repository/run config found), omit the Installation section and note the gap in Step 11 rather than
  guessing coordinates.

## Step 7 — Write the "how it works" section with an example

This is the most judgment-heavy part — ground it in what the code actually does, don't invent behavior:

- Identify the main source entry points (the primary public classes/interfaces/functions a consumer would use —
  for a library, usually a small number of top-level types; for an application, its README-worthy commands/
  endpoints) without reading the whole source tree directly: use the `Explore` agent to locate them first, then
  read only those specific files.
- If Antora docs already exist (`docs/modules/ROOT/pages/index.adoc`, `getting-started.adoc`, or similar), prefer
  reusing/adapting their conceptual explanation and example code rather than writing a divergent one from scratch
  — the README and the docs site describing the same library differently is a maintenance trap.
  If a docs example exists, verify it still matches the current API shape before reusing it — the docs page might
  itself be stale.
- Write a short paragraph (a few sentences) on the core concept, plus one minimal, realistic code example that
  would actually compile/run against the current API — check public method/constructor signatures rather than
  guessing them.
- If the repository has no meaningful source yet (a brand-new, scaffolded-but-empty project), omit this section
  entirely rather than writing a placeholder example.

## Step 8 — Compose the remaining structural sections

Include each only when Steps 2–7 gave it real content:

- **Title + tagline**: repository name as an `# H1`, one-sentence description from Step 2 underneath.
- **Badges**: from Step 3, directly under the title.
- **Project Status**: table from Step 4.
- **Documentation**: links from Step 5.
- **Installation**: snippet(s) from Step 6.
- **How It Works** / **Quick Example**: prose + code from Step 7.
- **License**: one line naming the license from Step 2, linking to the `LICENSE` file.

If the existing `README.md` read in Step 1 had additional sections this skill doesn't generate (e.g.
"Contributing", "Acknowledgements", a project-specific comparison table like "Choosing a Detector"), keep them
verbatim in the proposed version, in their original relative position, rather than silently dropping
hand-written content this skill doesn't know how to regenerate.

## Step 9 — If `README.md` already existed, get approval before writing

Skip this step entirely if Step 1 found no existing file — proceed straight to Step 10.

- Show the user the full proposed new `README.md` content (or a diff against the current file — writing the
  draft to a temp path and running `git diff --no-index <current> <draft>` gives a clean unified diff) so they
  can see exactly what would change section by section.
- Ask via `AskUserQuestion` whether to: (a) accept and write the proposed content, (b) skip and leave the
  existing `README.md` untouched. There is no partial-apply option here — if the user wants to keep some sections
  and change others, let them say so in free text and revise the draft before writing.
- Only proceed to Step 10 on explicit acceptance.

## Step 10 — Write `README.md`

Write the composed content (Step 8, incorporating any edits from Step 9's review) to `README.md` at the
repository root.

## Step 11 — Report

Summarize: which sections were included versus omitted and why (e.g. "no Installation section — no build/package
config found", "no CI badges — no GitHub Actions workflows present"), any fact that had to be inferred rather than
confirmed (e.g. an Antora Pages URL assumed from convention), and — if `README.md` already existed — whether the
user accepted or skipped the proposed changes. Remind the user to double-check the "How It Works"/example section
specifically, since it's the part most dependent on this skill's reading of the current API rather than on
mechanically-derived facts like versions or badge URLs.
