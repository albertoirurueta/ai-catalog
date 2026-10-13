# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

`ai-catalog` is a collection of Claude Code Skills — reusable, version-controlled playbooks for common
software engineering workflows, each invoked on demand with a slash command (`/iru-plan`, `/iru-pr-review`, etc.).
There is no application code, no `pom.xml`/`package.json` at the root, and nothing to compile or unit-test
in this repository itself — the deliverable is the skills (and the Antora docs describing them).

## Commands

The only buildable artifact is the Antora documentation site under `docs/`:

```bash
cd docs && npm ci                          # install Antora + extensions (only needed once / after changes)
cd docs && npx antora antora-playbook.yml  # build the site into docs/build/site (gitignored, generated)
```

CI (`.github/workflows/docs.yml`) runs the same build and publishes `docs/build/site` to the `gh-pages`
branch on every push to `main`. There is no separate lint/test command for this repository.

## Architecture

### Skills (`.claude/skills/<name>/SKILL.md`)

Every skill and agent in this catalog carries an `iru-` prefix (directory name, frontmatter `name`, and every
cross-reference to it) so its slash command can't collide with a same-named skill installed from another
marketplace once both sit side by side in a consuming repository's `.claude/skills/`. Any new skill or agent
added to this catalog must follow the same convention — see
`docs/modules/ROOT/pages/guides/creating-skills-and-agents.adoc`.

Each skill is a single, self-contained `SKILL.md` file: YAML frontmatter with `name` and `description` (the
description is what Claude Code uses to decide when the skill is relevant — it should state the exact
invocation form, e.g. `/iru-check-license` or `/iru-check-license <path-or-glob>`), followed by step-by-step
instructions written for an agent to follow. A skill is adopted by another repository by copying its
directory into that repository's `.claude/skills/` — skills must not assume they're running inside
`ai-catalog` itself (they detect language/platform/tooling at runtime rather than hardcoding it).

Skills compose into a few recurring pipelines rather than each standing alone:

- **Issue-to-PR cycle**: `iru-issue` → `iru-explore` → `iru-plan` → `iru-code` → `iru-pr-description` → `iru-pr-review`. `iru-plan` groups
  `implementation_plan.md`'s tasks into dependency-aware groups; `iru-code` doesn't implement anything itself — it
  dispatches each group, in order, to `iru-code-one-task-group`, which resolves each task's language and delegates
  to the matching `iru-<key>-code-one-task-group` skill. Installed keys: `java`, `java-springboot`,
  `kotlin-springboot`, `quarkus` (Java or Kotlin, detected inside), `dotnet`, `typescript`, `nestjs`, `nextjs`,
  `php` (Laravel / WordPress plugin or theme / PrestaShop module, detected inside), `android`, `swift`, `database`
  — each key `<key>` has an `iru-<key>-code-one-task-group` + `iru-<key>-code-one-task` pair (keys are discovered
  from the installed directories, never hardcoded). The group skill captures one quality baseline for the whole
  group, runs `iru-<key>-code-one-task` once per task — in parallel when the group allows it (`database` is always
  sequential) — and validates the group once (license → doc comments → tests → 80% coverage → quality diff vs
  baseline), instead of once per task. Coding skills detect build tool (Maven / Gradle KTS / Gradle Groovy,
  npm/pnpm/yarn, Composer) and architecture (hexagonal multi-module vs layered/feature) at runtime. Every
  container-backed or server-starting stage (Spring Testcontainers, Quarkus Dev Services, NestJS e2e, Next.js
  Playwright, WordPress `wp-env`) is serialized repository-wide behind one shared atomic-`mkdir` lock directory,
  `.integration-test.lock` (owner file, stale after 60 min, released on every exit path, gitignored); Docker
  unavailable makes that stage "unverified", never silently skipped, and the coverage gate counts only tests
  that need no containers.
- **Repository bootstrap**: `iru-setup-repository` is the front door — it detects a non-empty repository (via
  `iru-explore`, reading its `Project type:` line to pre-select), otherwise asks the project type over up to four
  `AskUserQuestion` rounds of three options each (JVM services & libraries, Web & Node, PHP, Mobile & Apple), every
  round ending in a "Something in the next group" escape hatch (the last in "None of these"); an option bundling
  several types (Web app → React/Next.js/Angular, WordPress → plugin/block theme, Android, Apple, cross-platform
  mobile) gets one bounded follow-up, while stack-shape questions (Spring Boot/Quarkus `language`/`build-tool`/
  `layout`/`frontend`, NestJS `orm`, Next.js `output`) are left to the orchestrator, asks the shared inputs once, and delegates to the
  matching stack orchestrator via `iru-isolated-skill-executor`; on an existing repository it forces `mode: existing`
  so every sub-skill takes its update path instead of assuming a brand-new repo. The front door and every
  orchestrator first announce the **setup mode** — "from scratch" or "updating an existing repository" plus an
  inventory of each owned component (build manifest, sources, Antora docs, `.gitignore`, each workflow file,
  Dependabot, Sonar config, `CHANGELOG.md`, `README.md`, `LICENSE`) marked absent/present/partial — and every
  component skill that finds a prior artifact it owns warns and asks **Update** (merge, keep customizations) /
  **Keep as is** (report mismatches with this run's choices) / **Replace** (regenerate, customizations lost), with
  a **Stop** option where it makes sense; `mode: existing` alone never means "update silently" — only an explicit
  `on-existing` does. Final reports repeat the mode and the per-component action (created / updated / replaced /
  kept as is / skipped (ci: no)). The six `*-repository`
  stack orchestrators — `iru-setup-java-library-repository`, `iru-setup-quarkus-repository`,
  `iru-setup-typescript-repository`, `iru-setup-php-repository`, `iru-setup-android-repository`,
  `iru-setup-swift-repository` — each also run standalone, and each chains the
  same six-step shape in order: scaffold (the language/flavor-specific library or app skill) → `iru-setup-antora` →
  `iru-setup-<stack>-gitignore` → `iru-setup-<stack>-github-workflows` → `iru-setup-changelog` → `iru-setup-readme`
  (Quarkus reuses `iru-setup-java-gitignore`). Flavors: `iru-setup-typescript-repository`'s `flavor` picks `library`,
  `react`, `angular`, `react-native`, `ionic`, `nestjs` (`iru-setup-nestjs-app`), or `nextjs` (`iru-setup-nextjs-web`);
  `iru-setup-php-repository`'s picks `laravel`, `wordpress-plugin`, `wordpress-theme` (block theme), or
  `prestashop-module` (`iru-setup-php-laravel` / `-wordpress` / `-prestashop`); `iru-setup-quarkus-repository`
  (via `iru-setup-quarkus-service`, `quarkus-stack.yml` manifest) takes `language: java|kotlin`,
  `build-tool: maven|gradle` (Gradle = Kotlin DSL), and `layout: single|hexagonal`.
  `iru-setup-java-springboot` is the seventh orchestrator but follows its own manifest-driven chain instead: it
  interviews the user once, writes a `springboot-stack.yml` manifest, delegates the reactor's generation to its
  `iru-setup-java-springboot-*` sub-skills (pom, modules, apis, optional hilla, testcontainers, platform,
  github-workflows) plus `iru-update-java-springboot-documentation` for the Antora site, and only then fills the
  remaining repository-level files (`iru-setup-java-gitignore`, `iru-setup-readme`, `iru-setup-changelog`) directly.
  Its `language: java|kotlin` and `build-tool: maven|gradle` args (manifest `project.language`/`buildTool`; Gradle
  only with Kotlin) switch the same module tree to Kotlin — detekt/ktlint + Dokka instead of Checkstyle/PMD/SpotBugs
  + Javadoc, and for Gradle a Kotlin DSL build with `gradle/libs.versions.toml` and `build-logic/` convention
  plugins; the Java path stays Maven-only and unchanged.
- **Shared bootstrap inputs**: the front door and the orchestrators share one `args` vocabulary —
  `open-source: yes|no`, `visibility: public|private|internal`, `ci: yes|no`, `ci-tests: unit|full`, `pages: yes|no`,
  `publish: yes|no` (libraries), `distribution: none|internal|store` (apps), `sonar: cloud|self-hosted|none`
  (+ `sonar-organization`/`sonar-project-key`/`sonar-host-url`), `mode: new|existing`, and
  `on-existing: ask|keep|update|replace` — so a value collected once by a front door or orchestrator never needs
  re-asking downstream; each downstream scaffold/workflows skill parses only the subset of those keys its own Step 0
  lists and ignores the rest. `visibility` comes from `args`, else `gh repo view --json visibility`, else is asked
  (Public recommended when open source); `internal` counts as `private` for every cost decision, and open source +
  private is flagged as contradictory. Because GitHub Actions minutes (free on public repos; included-minutes budget
  on private, macOS ~10×), SonarCloud (free only for public/open-source projects), and GitHub Pages (private repos
  need Pro/Team/Enterprise Cloud, and the site is public unless Enterprise Cloud private Pages) cost differently, the
  entry point asks, in order: `ci` (Yes recommended; `ci: no` skips the whole workflows step including the shared
  security block), `sonar` ("send CI reports to SonarCloud/SonarQube?" — `cloud` recommended only for a public,
  open-source repo, otherwise `none`; with `ci: no`, `none` is recommended since nothing would send reports),
  `ci-tests` (only with `ci: yes`; `unit` recommended for private repos, `full` for public), and `pages` (only with
  `ci: yes`; defaulted to `yes` for public repos, asked with `no` recommended for private — `pages: no` keeps the
  docs build but uploads it as a workflow artifact). A standalone workflows skill resolves `visibility` and asks
  `ci-tests`/`pages`/`sonar` itself (never `ci`). `on-existing` defaults to `ask` and is only for scripted runs —
  orchestrators forward it only when their own `args` received it. Defaults: `publish`/`distribution` default to
  `yes`/`store` only when the project is open source.
- **Ticket intake**: `iru-create-github-issue` / `iru-create-jira-ticket` ground a draft in the codebase via
  `iru-explore` before filing.
- **Release**: `iru-release` converts a SNAPSHOT/pre-release version into a final release and is not Maven-only —
  it discovers the installed `iru-<key>-bump-version` skills (`find .claude/skills -maxdepth 1 -type d -name
  "iru-*-bump-version"`, currently `java` (Java or Kotlin, Maven or Gradle), `typescript`, `android`, `swift`,
  `php` (Laravel `config/app.php`, WordPress plugin/theme headers, PrestaShop module class; `x.y.z-dev`
  convention)) and delegates the actual version-file edit to whichever key matches the detected project, keeping
  its own branch/PR/label/changelog steps ecosystem-agnostic.
- **Android reference repository**: every `iru-*android*` skill's embedded templates are genericized from a single
  real repository, https://github.com/albertoirurueta/irurueta-android-glutils (`lib/` + Compose `app/`,
  `gradle/libs.versions.toml`, JUnit 4 + MockK + Robolectric + AndroidX test + Espresso, AGP JaCoCo, inline
  `sonar {}`, Dokka to gh-pages) — keep new Android skills consistent with it, with the decided departures (Antora
  site + Dokka under `api/`, `develop`/`main` branching with `-SNAPSHOT` on `develop` and a `sync.yml`) documented
  in each skill rather than silently reintroduced.
- **Guidance sources for the newer stacks**: the Kotlin, Spring Boot (Java/Kotlin), Quarkus, PHP/Laravel, NestJS,
  and Next.js coding references (each `iru-<key>-code-one-task/reference/` routing table) and their setup skills
  are grounded in the author's docs repository, https://github.com/albertoirurueta/docs (cited in each
  `reference/README.md` Sources as "irurueta docs: <page path>"); WordPress and PrestaShop aren't covered there,
  so those references/scaffolds follow the official docs (developer.wordpress.org handbooks + WordPress Coding
  Standards, devdocs.prestashop-project.org). Keep new guidance for these stacks consistent with those sources.
- **Template verification**: every scaffold/workflows/gate skill's embedded templates are meant to be exercised
  against the real tooling in a throwaway directory *outside* this repository (`$TMPDIR/iru-verify/<stack>/<skill>/`)
  before being trusted — nothing inside this repository is ever deleted for that purpose, and whatever can't be
  verified locally is reported rather than assumed to work. Every `-github-workflows` skill also embeds the same
  security block (Dependabot, dependency-review, CodeQL, OSV-Scanner, gitleaks) and ends with a required-secrets table;
  a stack may add opt-in scanners beyond those shared four (e.g. MobSF for Android) as long as the shared block stays.

### Agents (`.claude/agents/<name>.md`)

This repository defines three custom agents for its most-duplicated sub-agent shapes:

- **`iru-gate-runner`** — runs a single verification/quality-gate skill (tests, coverage, code-quality/lint, license
  headers, doc-comment audits, security scans, or a full build), optionally diffs it against a baseline, and
  reports back only a compact summary. Gate skills it runs: `iru-<lang>-test`/`-coverage`/`-code-quality` for
  `java` (Maven or Gradle, Java or Kotlin sources; coverage from JaCoCo, `quarkus-jacoco`, or Kover), `dotnet`,
  `typescript` (incl. NestJS/Next.js, `e2e` selector), `php` (Pest/PHPUnit, Clover, PHPStan/Psalm/PHPCS),
  `android`, `swift`; `iru-kotlin-code-quality` (detekt/ktlint); doc audits `iru-java-javadoc`, `iru-kotlin-kdoc`,
  `iru-dotnet-docfx`, `iru-typescript-tsdoc`, `iru-php-phpdoc`, `iru-android-dokka`, `iru-swift-docc`; plus
  `iru-check-license`/`iru-check-security`. Used throughout `iru-code`, `iru-code-one-task-group`, and every
  `iru-<key>-code-one-task-group` that validates (all but `database`), and recommended by `iru-plan` for the scoped
  test-run step it writes into generated plans.
- **`iru-isolated-skill-executor`** — runs one named skill end-to-end in a completely fresh context so an earlier
  exploration/planning transcript can't bias it, while the caller keeps running afterward. Used by `iru-issue` to
  delegate the entire `iru-code` run for a ticket.
- **`iru-change-summarizer`** — fans out over a git commit/tag range and returns only the user-facing changes.
  Used by `iru-setup-changelog` to summarize one release at a time when backfilling a long tag history.

Skills that need ad hoc context isolation beyond these three shapes still use Claude Code's *built-in* agent
types via the `Agent` tool: `iru-explore` uses the `Explore` agent explicitly; one-off cases like bootstrapping
`iru-setup-antora` mid-run (`iru-generate-skill-docs`, `iru-update-docs`) use `general-purpose`, the default.

### Documentation (`docs/`)

An Antora site (`docs/antora.yml`, `docs/antora-playbook.yml`) with two kinds of pages under
`docs/modules/ROOT/pages/`, which matters because they're maintained differently:

- **Generated**: `index.adoc`, every `skills/*.adoc`, and `agents/*.adoc` are regenerated by the
  `iru-generate-skill-docs` skill (`/iru-generate-skill-docs`) directly from the
  `SKILL.md` files and agent usage actually on disk, including the reference table, dependency graph, and
  purpose groups. Re-run it after adding, removing, or materially changing a skill — hand edits to these
  pages are overwritten on the next run.
- **Hand-maintained**: everything under `guides/` (`claude-md.adoc`, `common-workflows.adoc`,
  `creating-skills-and-agents.adoc`, etc.) is regular prose, edited directly like any other doc.

`nav.adoc` lists every page and must gain an entry when a new skill or guide page is added (the
`iru-generate-skill-docs` skill handles this for generated pages automatically).

`docs/build/` is gitignored — never hand-edit generated site output.
