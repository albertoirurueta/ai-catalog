---
name: iru-setup-repository
description: >-
  End-to-end bootstrap front door for this entire catalog — invoke as `/iru-setup-repository` and use
  it as THE one entry point new users should reach for to bootstrap any repository, instead of hunting for which
  of this catalog's stack-specific orchestrators applies. Covers all twelve project types this catalog can
  scaffold — `java-library`, `java-springboot`, `java-springboot-hilla`, `typescript-library`, `react-web`,
  `angular-web`, `android-library`, `android-app`, `swift-library`, `apple-app` (`ios`/`ipados`/`macos`/`watchos`),
  `react-native-app`, `ionic-app` (`angular`/`react`) — by surveying the working directory (running `iru-explore`
  first when it already holds code) to detect which one applies, asking only the shared, cross-cutting questions
  the detected/chosen type still needs, then delegating the actual scaffold to the matching stack orchestrator
  (`iru-setup-java-library-repository`, `iru-setup-java-springboot`, `iru-setup-typescript-repository`,
  `iru-setup-android-repository`, or `iru-setup-swift-repository`) via `iru-isolated-skill-executor`. Accepts
  `args` (`key: value` lines) to pre-resolve `project-type`, `open-source`, `visibility`
  (`public`/`private`/`internal`, otherwise detected via `gh repo view` or asked), `ci` (`yes`/`no`), `ci-tests`
  (`unit`/`full`), `pages` (`yes`/`no`), `publish`, `distribution`, `sonar`
  (+ `sonar-organization`/`sonar-project-key`/`sonar-host-url`), `mode` (`new`/`existing`), `on-existing`
  (`ask`/`keep`/`update`/`replace`, scripted runs only), `flavor`, `platforms`, `framework`, `native-builds`, `integration-branch`,
  `stable-branch`, `license`, `developer-name`, `developer-email`, and `organization-url` — forwarding each only
  to the delegated orchestrator(s) whose own `args` contract actually accepts it, and never asking a question
  `args` already answered. Asks whether CI workflows are wanted, whether Sonar receives CI reports, whether CI runs
  unit-only or the full test suite, and (private repos) whether docs go to GitHub Pages, stating the Actions-minutes
  / SonarCloud / Pages cost differences between public and private repositories. Announces whether it is setting up
  from scratch or updating an existing repository (with an inventory of the prior setup it found); on an existing
  repository it runs `iru-explore` first and forces `mode: existing`, and every delegated component then warns about
  each pre-existing artifact and asks whether to keep, update, or replace it. Use whenever a
  user wants to bootstrap (or catch up) a repository and either doesn't know or shouldn't have to know which of
  this catalog's five stack-specific setup orchestrators to invoke directly.
model: sonnet
---

# Setup Repository

The catalog's single bootstrap front door. This skill does not scaffold anything itself — it detects or asks which
of the twelve supported project types the repository is (or should become), collects the handful of questions that
are genuinely shared across every stack (open source, repository visibility, CI/CD and its test scope, Sonar,
GitHub Pages, publish/distribution, and a few flavor-specific inputs), and then hands off to exactly one of five existing stack orchestrators, each of which asks its own
project-identity questions (groupId/artifactId, package/app name, etc.) and does the actual scaffolding.

## Step 0 — Resolve inputs

This skill is always the entry point (nothing else in this catalog orchestrates it), but it can still be re-invoked
with `args` (`key: value` lines) by a script or a returning user, so parse `args` first, one `key: value` pair per
line, e.g.:

```
project-type: android-app
mode: new
open-source: yes
visibility: public
ci: yes
ci-tests: full
pages: yes
distribution: store
sonar: cloud
sonar-organization: example-org-github
sonar-project-key: example-org_my-app
sonar-host-url: https://sonarcloud.io
```

Recognized keys: `project-type` (any value from the vocabulary in Step 1), `mode` (`new`/`existing`),
`open-source` (`yes`/`no`), `visibility` (`public`/`private`/`internal` — the GitHub repository's visibility;
`internal` is treated like `private` for every cost decision), `ci` (`yes`/`no` — whether GitHub Actions workflows
are generated/updated at all), `ci-tests` (`unit`/`full` — only meaningful with `ci: yes`), `pages` (`yes`/`no` —
whether docs are deployed to GitHub Pages from CI; only meaningful with `ci: yes`), `on-existing`
(`ask`/`keep`/`update`/`replace` — how every component treats prior setup it finds; default `ask`; meant for
scripted runs, so this skill never asks it and forwards it only when it arrived here), `publish` (`yes`/`no` —
library types only), `distribution` (`none`/`internal`/`store` — app types only), `sonar`
(`cloud`/`self-hosted`/`none`) plus, only when set, `sonar-organization`/`sonar-project-key`/`sonar-host-url`,
`flavor` (only meaningful for the typescript orchestrator
— see Step 2's table; usually redundant with `project-type` and can be left unset), `platforms` (Apple app / Swift
library), `framework` (Ionic's `angular`/`react`), `native-builds` (React Native's `eas`/`local`), plus the
pass-through-only keys `integration-branch`, `stable-branch`, `license`, `developer-name`, `developer-email`,
`organization-url` (see Step 3's closing note — this skill never asks for these itself, it only forwards them when
supplied). Every key found here is resolved — skip the matching question below. Any **other** `key: value` line
(e.g. `name`/`scope`/`description`/`node-version`/`package-manager` for `iru-setup-typescript-repository`,
`group-id`/`artifact-id`/`namespace` for `iru-setup-android-repository`) is kept as an opaque pass-through: Step 4
forwards it verbatim only if the delegated orchestrator's own Step 0, read on disk there, recognizes the key, and
Step 5 lists every line that was dropped because no delegated skill accepts it — never silently (without this
pass-through, a fully pre-resolved `mode: new` run still stops to ask for the package name and Node version).
If `args` is absent or doesn't look like this format, treat everything as unset and ask normally.

## Step 1 — Survey the repository

Check whether the working directory already holds a real repository before asking anything: `git ls-files | head`
returning any output, or any of these manifests present at any depth worth a shallow `find`/`ls` check —
`pom.xml`, `build.gradle`/`build.gradle.kts`, `settings.gradle`/`settings.gradle.kts`, `package.json`,
`Package.swift`, `*.xcodeproj`, `project.yml`, `Project.swift`, `*.csproj`/`*.sln`.

- **Non-empty** (a real, at-least-partially-scaffolded repository): run `Skill({skill: "iru-explore"})` with no
  ticket argument — this is a codebase-only exploration, not one grounded in a ticket. Read the `- Project type:`
  line from its `## Tech stack` report block. Set `mode: existing` (unless `args` already supplied `mode`) and
  pre-select the recommended Step 2 option from the value reported, per the mapping table there. If the line reads
  `multiple`, list the reported `<module-path>: <type>` entries to the user and treat this as a repository that
  needs more than one bootstrap pass — ask which module to bootstrap first (or run this skill again per module),
  rather than guessing one.
- **Empty** (no tracked files, no manifest): set `mode: new` (unless `args` already supplied it) without running
  `iru-explore` — there's nothing yet for it to detect.

The `- Project type:` vocabulary, read **verbatim** — this is a shared contract with `iru-explore`'s own Step 7,
which documents the exact same list and derivation table, so never paraphrase or invent a value outside it:

```
java-library, java-springboot, java-springboot-hilla, typescript-library, react-web, angular-web,
android-library, android-app, swift-library, apple-app (ios, ipados, macos, watchos), react-native-app,
ionic-app (angular|react), dotnet, other, unknown
```

(`multiple` is also possible — handled above, not a project type in its own right.) Map a detected value straight
to its Step 2 option (see that step's table for the full project-type → option → delegated-skill mapping):

- The twelve real types (`java-library` through `ionic-app`) each map to exactly one Step 2 option — offer it as
  that option's first choice, labeled "(detected)", instead of running the full four-round interview. An
  `android-library` line carrying a `- sample app: <module>/` sub-line is still `android-library` (the catalog's
  reference `lib/` + sample `app/` layout) — never treat the sample module as a reason to ask "which module".
- `apple-app (…)` and `ionic-app (…)` also pre-fill Step 3's `platforms`/`framework` questions from the
  parenthetical, so the user only needs to confirm rather than re-answer them.
- `dotnet` — this catalog has **no bootstrap orchestrator for .NET**. Report that plainly (project type detected:
  `dotnet`; no `iru-setup-dotnet-repository`-style skill exists in this catalog to delegate to) and stop here for
  this run rather than falling through to Step 2 — there is nothing to offer.
- `other` / `unknown` / no ticket detected at all — fall through to asking the user directly in Step 2, with no
  pre-selection; a stack `iru-explore` couldn't place isn't one this skill can guess a delegated orchestrator for
  either.

### Announce the setup mode

Right after the survey (and before asking anything in Steps 2–3), tell the user which of the two this run is doing:

- **`mode: new`** → "Setting up this repository **from scratch** — no prior setup found."
- **`mode: existing`** → "**Updating an existing repository** — prior setup found:" followed by an inventory table
  of every component the delegated pipeline owns, each marked **absent** / **present** / **partial** with the
  evidence (file paths) — a shallow `ls`/`find` per row is enough, no deep reads:

  | Component | Evidence to check |
  |---|---|
  | Build manifest | `pom.xml`, `build.gradle(.kts)`/`settings.gradle(.kts)`, `package.json`, `Package.swift`, `*.xcodeproj`/`project.yml`/`Project.swift` |
  | Source layout | `src/`, `lib/`/`app/` modules, `Sources/`/`Tests/` |
  | Antora docs | `docs/antora.yml`, `docs/antora-playbook.yml`, `docs/modules/ROOT/` |
  | `.gitignore` | `.gitignore` |
  | CI workflows | each file under `.github/workflows/` (listed individually) |
  | Dependabot | `.github/dependabot.yml` |
  | Sonar config | `sonar-project.properties`, `sonar.*` properties in `pom.xml`, a `sonar {}` block in Gradle |
  | Changelog | `CHANGELOG.md` (or `CHANGELOG.rst`/`CHANGELOG.txt`/`HISTORY.md`) |
  | README | `README.md` |
  | License | `LICENSE`/`LICENSE.txt`/`LICENSE.md`/`COPYING` |

  Then: "For each component that already exists you'll be asked whether to keep it, update it, or replace it." (or,
  when `on-existing` arrived in `args` with `keep`/`update`/`replace`, say that value will be applied to every
  existing component without asking).

`mode` itself stays as detected above, but **any** owned artifact present — not just the build manifest — means
the run is an update for that component, so even a `mode: new` run lists in the announcement any stray component it
did find (e.g. a GitHub-created `README.md`/`LICENSE`) as present. Keep the inventory: Step 5 repeats it with the
action actually taken per component.

## Step 2 — Ask the project type

Skip this step entirely when `project-type` was already resolved — either supplied via `args`, or detected in
Step 1 and confirmed by the user (offered as that option's first entry, labeled "(detected)").

Otherwise resolve it with `AskUserQuestion`, in up to four rounds (the tool caps each question at four options,
so each round offers three concrete project types plus one explicit escape hatch). Rounds 1–3 end with a fourth
option, **"Something in the next group"**, whose label names the theme the next round covers (e.g. "Something in
the next group (mobile/native)") — picking it moves on to the next round without forcing a pick. Round 4 is the
last round, so its fourth option is instead **"None of these"**: choosing it means `project-type: other` — ask the
user to describe the stack in one line, and report per Step 5 that this catalog has no bootstrap orchestrator for
it (the same outcome as a detected `dotnet`/`other` in Step 1) rather than guessing a delegated skill to force it
into. If the user free-types a type from a later round via the tool's built-in *Other* choice, accept it directly
instead of walking them through the remaining rounds.

- **Round 1 — "Java/JVM"**: Java library / Spring Boot service / Spring Boot + Vaadin + Hilla / Something in the
  next group (Android & Swift).
- **Round 2 — "Android & Swift"** (only if Round 1 ended on the escape hatch): Android library / Android app /
  Swift library / Something in the next group (mobile apps).
- **Round 3 — "Mobile apps"** (only if Round 2 ended on the escape hatch): Apple app (iOS/iPadOS/macOS/watchOS) /
  React Native app / Ionic app / Something in the next group (web/Node).
- **Round 4 — "Web/Node"** (only if Round 3 ended on the escape hatch): TypeScript/npm library / React web app /
  Angular web app / None of these.

| Option | `project-type` key | Delegated skill | `flavor`/extra arg |
|---|---|---|---|
| Java library | `java-library` | `iru-setup-java-library-repository` | — |
| Spring Boot service | `java-springboot` | `iru-setup-java-springboot` | `frontend: none` |
| Spring Boot + Vaadin + Hilla | `java-springboot-hilla` | `iru-setup-java-springboot` | `frontend: hilla` |
| Android library | `android-library` | `iru-setup-android-repository` | `flavor: library` |
| Android app | `android-app` | `iru-setup-android-repository` | `flavor: app` |
| Swift library | `swift-library` | `iru-setup-swift-repository` | `flavor: library`, `platforms` |
| Apple app | `apple-app` | `iru-setup-swift-repository` | `flavor: app`, `platforms` |
| React Native app | `react-native-app` | `iru-setup-typescript-repository` | `flavor: react-native`, `native-builds` |
| TypeScript/npm library | `typescript-library` | `iru-setup-typescript-repository` | `flavor: library` |
| React web app | `react-web` | `iru-setup-typescript-repository` | `flavor: react` |
| Angular web app | `angular-web` | `iru-setup-typescript-repository` | `flavor: angular` |
| Ionic app | `ionic-app` | `iru-setup-typescript-repository` | `flavor: ionic`, `framework` |

## Step 3 — Ask the shared inputs once

Ask only what the resolved `project-type` actually needs, skipping anything already resolved by `args` or by
Step 1's detection. Every question here uses `AskUserQuestion` (header ≤ 12 characters, 2–4 options, recommended
option first and labeled "(Recommended)") and follows this catalog's shared open-source- and visibility-driven
convention (see any of the five delegated orchestrators' own Step 0–4 for the identical wording this mirrors). Ask
them in the order below — `visibility` and `ci` change the recommendations of everything after them.

1. **open-source** — is this repository open source? Yes / No, asked directly with no default. Drives the
   recommended defaults for every question below.
2. **visibility** — the GitHub repository's visibility, resolved (not necessarily asked) in this order:
   1. `args` supplied it — use it.
   2. The repository has a GitHub remote (`git remote get-url origin` matches `github.com`) and `gh` is available:
      run `gh repo view --json visibility -q .visibility` (returns `PUBLIC`/`PRIVATE`/`INTERNAL`; lowercase it) and
      tell the user the detected value.
   3. Otherwise (no remote yet, `gh` unavailable/unauthenticated, or not GitHub): ask with `AskUserQuestion` —
      **Public** / **Private** — recommending **Public** when `open-source: yes`, otherwise **Private**.
   4. Consistency check: `open-source: yes` with `visibility: private|internal` is contradictory — warn and ask the
      user which one is right (an open-source project's repository is normally public; a private repository
      forfeits the free-for-public-repositories pricing stated below). `internal` behaves like `private` for every
      cost decision in this step.

   Every cost statement in questions 3–6 below is **per GitHub's current pricing** (verified October 2026 against
   docs.github.com) — say so, and tell the user to double-check their own plan:
   - **Actions minutes**: standard GitHub-hosted runners are free for public repositories. Private/internal
     repositories consume the account's included minutes — 2,000/month on GitHub Free, 3,000 on Pro and Team, 50,000
     on Enterprise Cloud — then are billed per minute. macOS runner minutes cost roughly 10× Linux minutes, Windows
     roughly 1.7× (per-minute rates: Linux 2-core $0.006, Windows 2-core $0.010, macOS $0.062). Dependabot
     version/security update runs on standard hosted runners are free.
   - **SonarCloud (SonarQube Cloud)** is free for public/open-source projects; a private project needs a paid plan.
     Self-hosted SonarQube Community Build is free, but you run the server.
   - **GitHub Pages** is available for public repositories on every plan; for private/internal repositories it
     requires GitHub Pro, Team, or Enterprise Cloud (not GitHub Free), and a Pages site published from a private
     repository is **publicly accessible on the internet** unless the organization is on Enterprise Cloud and
     publishes it with private access control.
3. **ci** — "Generate GitHub Actions workflows (CI/CD) for this repository?"
   - **Public**: recommend **Yes** — standard runners are free for public repositories.
   - **Private/internal**: still offer **Yes** first, but state the included-minutes budget for their plan, and —
     when the resolved type builds on macOS (`swift-library`, `apple-app`, `react-native-app` with
     `native-builds: local` — question 8 hasn't been asked yet, so state it conditionally unless `args` resolved
     it — and `ionic-app` iOS builds) — the ~10× macOS multiplier, estimating plainly that a few
     dozen macOS builds a month can exhaust 2,000 included minutes. Offer **No** as "no workflows — build, test, and
     release locally (re-run the stack's `-github-workflows` skill later to add them)".
   - `ci: no` means the delegated orchestrator skips its workflows step entirely (no `.github/workflows/*`, no
     `security.yml`, no `.github/dependabot.yml`, no sync script) — and with it the shared security block
     (Dependabot, dependency-review, CodeQL, OSV-Scanner, gitleaks); for `java-springboot`/`java-springboot-hilla`
     that also means no deploy/undeploy workflows, so deployment has to be done manually. Questions 5 and 6 are then
     not asked.
4. **sonar** — "Configure SonarCloud / SonarQube and send CI analysis and coverage reports to it?"
   `cloud`/`self-hosted`/`none`. Recommend **`cloud`** only when the repository is **public AND open source**.
   Otherwise state plainly that SonarCloud is free only for public/open-source projects (a private project needs a
   paid plan) and recommend **`none`**, offering **self-hosted SonarQube** as the second option. When `ci: no`, say
   plainly that nothing would send reports automatically — analysis would only run when someone runs the scanner
   manually with a token — and recommend **`none`**; if the user still picks `cloud`/`self-hosted`, the delegated
   skills configure only the build-side Sonar properties/plugin and Step 5 reports that no CI step sends reports.
   When `cloud`/`self-hosted` is chosen, also collect `sonar-organization`/`sonar-project-key` (cloud) or
   `sonar-host-url`/`sonar-project-key` (self-hosted), the same way every delegated orchestrator's own Sonar
   question does.
5. **ci-tests** (only when `ci: yes`) — "Which tests should CI run?" Name the concrete test kinds for the resolved
   type in the option descriptions: Maven Failsafe `*IT` integration tests (`java-library`); Failsafe +
   Testcontainers/Docker integration tests (`java-springboot`/`java-springboot-hilla`); emulator-backed
   instrumented tests (`android-library`/`android-app` — the emulator job runs on Linux with KVM, and emulator time
   is billed minutes on a private repository); Playwright e2e (`react-web`/`angular-web`, and any e2e suite of
   `react-native-app`/`ionic-app`); XCUITest UI tests on every selected destination (`apple-app`, every macOS minute
   ~10×); an integration-test target if one exists (`swift-library`, `typescript-library`).
   - **`unit`** — "Unit tests only (cheaper: fewer minutes, faster feedback). Integration / instrumentation / e2e
     tests stay local." Recommend for private/internal repositories.
   - **`full`** — "Unit + integration / instrumentation / e2e tests (complete verification, uses considerably more
     minutes — emulators, containers, browsers, simulators)." Recommend for public repositories.
6. **pages** (only when `ci: yes` — every delegated pipeline builds an Antora docs site that its workflows can
   publish to GitHub Pages):
   - **Public**: default **`yes`** without asking (Step 5 states it).
   - **Private/internal**: ask — **No (Recommended)** ("CI still builds the docs and uploads them as a workflow
     artifact; nothing is published") vs **Yes** ("requires GitHub Pro/Team/Enterprise Cloud; the site will be
     PUBLIC on the internet unless you're on Enterprise Cloud with private Pages access control").
7. **publish** or **distribution**, depending on whether the resolved type is a library or an app-shaped
   deliverable — never ask both, and skip entirely for `java-springboot`/`java-springboot-hilla` (a service isn't
   published or distributed the way a library or an installable app is, and neither's own orchestrator accepts
   either key) and for `react-web`/`angular-web` (`iru-setup-typescript-repository` accepts neither key for these
   two flavors — a web app is deployed by its own CI job, not published or distributed):
   - **`publish`** — library types (`java-library`, `typescript-library`, `android-library`, `swift-library`):
     does this get published for other projects to depend on (Maven Central / npm / the Swift Package Index,
     per the type)? Default **Yes** when open source; otherwise ask with **No** recommended — these registries are
     for redistributable artifacts, which usually isn't the point of closed-source code.
   - **`distribution`** — app types (`android-app`, `apple-app`, `react-native-app`, `ionic-app`):
     `none`/`internal`/`store`. Default **`store`** only when open source; otherwise ask with **`internal`**
     recommended, `none` as the local-install-only alternative.
8. **Conditional, per resolved type**:
   - **Apple app / Swift library** — Apple platforms (`AskUserQuestion`, multi-select, at least one required):
     `ios` / `ipados` / `macos` / `watchos`. Pre-fill from Step 1's detected `apple-app (…)` parenthetical when
     present. For a **Swift library only**, follow up with a second multi-select question — "Also target tvOS /
     visionOS / Linux?" with options `tvos` / `visionos` / `linux` (none required) — and append every selected
     value to `platforms`. This follow-up is necessary because Step 4 always forwards `platforms` pre-resolved,
     and `iru-setup-swift-repository`'s own Step 0 skips any question whose key was supplied — so a library's
     extra platforms can only reach `Package.swift` if this front door collects them itself. Never ask it for an
     Apple app: `iru-setup-apple-app` accepts only the four values above.
   - **Ionic app** — framework (`AskUserQuestion`, two options): **Angular** or **React**. Pre-fill from Step 1's
     detected `ionic-app (…)` parenthetical when present.
   - **React Native app** — native-builds (`AskUserQuestion`, two options, default **`eas`**): does CI build the
     iOS/Android binaries via cloud builds (`eas`), or does it need a full local native toolchain (`local`)?

`integration-branch`, `stable-branch`, `license`, `developer-name`, `developer-email`, and `organization-url` are
**never actively asked here** — this front door only forwards them when they arrived via its own `args`
(`iru-setup-typescript-repository`, `iru-setup-android-repository`, and `iru-setup-swift-repository` all accept
these as `args` keys and would otherwise ask their own equivalent question; `iru-setup-java-library-repository`
and `iru-setup-java-springboot` accept none of them and always ask their own identity/branch questions directly
regardless of what this skill would pass). Asking them here would either duplicate a question the delegated skill
asks anyway or collect a value the delegated skill has no `args` key to receive — so let each one ask.

## Step 4 — Delegate to the stack orchestrator

**Before writing this step's `Agent(...)` call**, confirm the exact `args` keys and values the target skill
actually accepts by reading its `SKILL.md` frontmatter description and Step 0 on disk — never rely on memory of
the table above once actually invoking:

- `.claude/skills/iru-setup-java-library-repository/SKILL.md`
- `.claude/skills/iru-setup-java-springboot/SKILL.md`
- `.claude/skills/iru-setup-typescript-repository/SKILL.md`
- `.claude/skills/iru-setup-android-repository/SKILL.md`
- `.claude/skills/iru-setup-swift-repository/SKILL.md`
- `.claude/skills/iru-explore/SKILL.md` Step 7, for the `## Tech stack` report shape Step 1 already relied on.
- `.claude/agents/iru-isolated-skill-executor.md`, for how it runs a named skill and reports back.

Then delegate via `iru-isolated-skill-executor`, exactly one of the five, always passing `mode` and every shared
input Step 3 resolved (omitting any key the target skill's own Step 0 doesn't recognize — never send an invented
key). All five orchestrators accept the cost/CI keys `visibility`, `ci`, `ci-tests`, and `pages`, plus
`on-existing`: always send `visibility` and `ci`; send `ci-tests` and `pages` only when `ci: yes` (they're
meaningless otherwise); send `on-existing` **only** when it arrived via this skill's own `args` — never invent a
value, so an interactive run leaves every component free to warn and ask per pre-existing artifact:

```
# project-type: android-app
Agent({
  description: "Run iru-setup-android-repository",
  subagent_type: "iru-isolated-skill-executor",
  prompt: "Invoke Skill({skill: \"iru-setup-android-repository\", args: \"flavor: app\\nmode: <mode>\\n
    open-source: <open-source>\\nvisibility: <visibility>\\nci: <ci>\\nci-tests: <..., if ci: yes>\\n
    pages: <..., if ci: yes>\\non-existing: <..., only if supplied via args>\\ndistribution: <distribution>\\n
    sonar: <sonar>\\nsonar-organization: <..., if set>\\nsonar-project-key: <..., if set>\\n
    sonar-host-url: <..., if set>\\nintegration-branch: <..., if set>\\nstable-branch: <..., if set>\\n
    license: <..., if set>\\ndeveloper-name: <..., if set>\\ndeveloper-email: <..., if set>\\n
    organization-url: <..., if set>\"}).
    Report back: the setup mode it announced, and per component (scaffold/build manifest, Antora docs, .gitignore,
    each workflow file, CHANGELOG.md, README.md) the action actually taken — created / updated / replaced / kept as
    is / skipped (ci: no) — and whether the user chose to stop at any point; every mismatch it reported between a
    kept file and this run's choices; the full required-secrets/settings table it produced; and any open gap it
    flagged.",
  run_in_background: false
})
```

The other four project types follow the same shape — one delegation, one `iru-isolated-skill-executor` call —
with only the skill name and `args` changed. Every list below implicitly includes `visibility`, `ci`, `ci-tests`
and `pages` (when `ci: yes`), and `on-existing` (when supplied via `args`), per the rule above:

- **`java-library`** → `iru-setup-java-library-repository`, `args`: `mode`, `open-source`, the cost/CI keys,
  `publish`, `sonar` (+ detail keys) only — its own Step 0 recognizes nothing else, so `integration-branch`/
  `license`/developer identity are never sent here even if the user supplied them via this skill's own `args`.
- **`java-springboot`** / **`java-springboot-hilla`** → `iru-setup-java-springboot`, `args`: `mode`,
  `open-source`, the cost/CI keys, `sonar` (+ detail keys), and `frontend` (`none` for `java-springboot`, `hilla`
  for `java-springboot-hilla`) — no `publish`/`distribution`/branch/license/developer keys exist on this skill
  either. It records `ci`/`ci-tests`/`pages` in its `springboot-stack.yml` manifest for its sub-skills.
- **`typescript-library`** / **`react-web`** / **`angular-web`** / **`react-native-app`** / **`ionic-app`** →
  `iru-setup-typescript-repository`, `args`: `flavor` (`library`/`react`/`angular`/`react-native`/`ionic`), `mode`,
  `open-source`, the cost/CI keys, `publish` (library only), `distribution` (react-native/ionic only), `sonar`
  (+ detail keys), `native-builds` (react-native only), `framework` (ionic only), plus `integration-branch`/
  `stable-branch`/`license`/`developer-name`/`developer-email`/`organization-url` when this skill's own `args`
  supplied them.
- **`android-library`** → `iru-setup-android-repository`, `args`: `flavor: library`, `mode`, `open-source`, the
  cost/CI keys, `publish`, `sonar` (+ detail keys), plus the same pass-through branch/license/developer keys when
  supplied.
- **`swift-library`** / **`apple-app`** → `iru-setup-swift-repository`, `args`: `flavor` (`library`/`app`),
  `mode`, `platforms` (comma-separated), `open-source`, the cost/CI keys, `publish` (library) / `distribution`
  (app), `sonar` (+ detail keys), plus the same pass-through branch/license/developer keys when supplied. Neither
  `flavor` needs `branching` sent — `iru-setup-swift-repository` asks that itself, as it isn't one of this skill's
  `args` keys.

If the on-disk Step 0 of the target orchestrator turns out **not** to recognize one of the cost/CI keys (e.g. an
older copy of it was installed), don't send that key — instead tell the user the orchestrator will ask that
question itself (or, if it has no such question, that the choice can't be applied by it), and list it in Step 5.

Each delegated orchestrator parses its own `args` (its own Step 0) and asks the user about anything genuinely left
out — its own project identity, its own `mode`-driven survey, `branching`/`generator`/`signing`/toolchain toggles,
and (for `java-library`/`java-springboot`) branch/license/developer identity that this front door never collects.
`AskUserQuestion` surfaces to the user the same way whether invoked directly or from inside the isolated
sub-agent — including each component's own keep/update/replace question for a pre-existing artifact, which this
front door never asks on the components' behalf (so the user is never asked the same question twice). Ask the
executor to report back: the per-component action actually taken (created / updated / replaced / kept as is /
skipped (ci: no)) and any point where the user chose to stop, every mismatch reported between a kept file and this
run's choices, the full required-secrets/settings table the delegated orchestrator produced, and any open gap it
flagged — a short structured summary, not the delegated run's full transcript.

## Step 5 — Report

Summarize for the user:

- The resolved `project-type` (and, for `apple-app`/`ionic-app`, the platforms/framework that came with it), the
  setup mode restated as in Step 1's announcement ("set up from scratch" / "updated an existing repository") with
  whether `mode` came from Step 1's survey or an explicit `args`/user answer, and every shared input from Step 3 as
  actually applied (`open-source`, `visibility` and whether it was supplied/detected via `gh`/asked, `ci`,
  `ci-tests`, `pages` — noting when `pages: yes` was defaulted because the repository is public —
  `publish`/`distribution`, `sonar` + detail keys, `on-existing` if supplied, and any conditional flavor-specific
  input).
- A **per-component table** — the Step 1 inventory's rows, each with what the delegated orchestrator (named
  explicitly) reported doing: **created / updated / replaced / kept as is / skipped (ci: no)** and the file paths
  involved. Reproduce its report rather than re-deriving one, and list under it every mismatch it flagged between a
  kept-as-is file and this run's choices (e.g. a kept `build.yml` that still runs a Sonar step after `sonar: none`,
  still deploys to Pages after `pages: no`, or still runs integration/e2e tests after `ci-tests: unit`).
- **Cost notes**, tied to the resolved `visibility` and stated as per GitHub's current pricing (the user should
  double-check their plan): for a public repository, that standard Actions runners and SonarCloud are free; for a
  private/internal one, the included-minutes budget, the macOS ~10× multiplier when the stack builds on macOS, that
  `ci-tests: full` uses considerably more minutes, that SonarCloud requires a paid plan for a private project when
  `sonar: cloud`, and — when `pages: yes` — that Pages needs Pro/Team/Enterprise Cloud and the site is public unless
  on Enterprise Cloud with private access control (with `pages: no`, the docs are uploaded as a workflow artifact
  instead).
- When `ci: no`: that no workflows were generated, that the shared security block (Dependabot, dependency-review,
  CodeQL, OSV-Scanner, gitleaks) was skipped with them (and, for Spring Boot, the deploy/undeploy workflows), that
  any Sonar configuration is build-side only with no CI step sending reports, and that re-running the stack's
  `-github-workflows` skill (e.g. `/iru-setup-android-github-workflows`) adds them later.
- Any key Step 4 couldn't forward because the target orchestrator's on-disk Step 0 didn't recognize it.
- One **consolidated secrets/environments table**, merged from the delegated orchestrator's own table (repository
  secrets such as `SONAR_TOKEN`, publish/store credentials, signing material, and any CI environment it named) —
  don't re-derive or expand it, just merge duplicates if this run somehow touched more than one delegated skill
  (e.g. the `multiple` case from Step 1).
- An explicit **Warn explicitly** block, always including:
  - **Review every generated/updated file before committing, building, or relying on CI.**
  - Every secret in the table above, and the matching SonarCloud project / registry account (npm, Maven Central,
    the Swift Package Index) / store account (App Store Connect, Google Play Console, Firebase) named there, must
    already exist before CI can pass — nothing in this pipeline creates or stores any account or credential.
  - Which values were **inferred** rather than asked — anything Step 1's `iru-explore` run detected and this skill
    pre-selected or pre-filled, `visibility` when it was detected via `gh repo view`, and every default this skill
    or a delegated orchestrator applied silently (e.g. `distribution: store` only because the project is open
    source, `pages: yes` only because the repository is public) — so the user can correct a wrong guess before
    relying on it.

If Step 1 or Step 2 ended on `dotnet`/`other`/no orchestrator available, report that outcome plainly instead of
the above (project type identified, no bootstrap orchestrator exists in this catalog for it, no delegation was
attempted) rather than fabricating a report for a run that never happened.
