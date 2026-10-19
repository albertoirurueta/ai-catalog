---
name: iru-setup-java-springboot-github-workflows
description: >-
  Create the GitHub Actions workflows for a Spring Boot service repository — in Java (Maven) or Kotlin (Maven, or
  Gradle Kotlin DSL), read from the manifest's `project.language`/`project.buildTool` (absent ⇒ `java`/`maven`, the
  unchanged Java path) — a build workflow (`build.yml`) that runs on pushes to the integration and main branches and
  on pull requests, executing unit tests via Surefire and Testcontainers-backed integration tests via Failsafe,
  Checkstyle/PMD/SpotBugs static analysis (detekt + ktlint for Kotlin), aggregated JaCoCo coverage, optionally a
  SonarCloud/SonarQube scan via `mvn sonar:sonar` or `./gradlew sonar` (gated by the manifest's `sonar.mode`), the
  Antora documentation build, Javadoc (Dokka for Kotlin), and the generated API documentation — OpenAPI, protobuf, the
  AsyncAPI HTML produced by `@asyncapi/html-template`, and the GraphQL reference produced by `spectaql` and
  `graphql-voyager` — publishing all of it to GitHub Pages; when the manifest's `frontend` is `hilla`, `build.yml`
  also sets up Node via `actions/setup-node`, runs `vaadin:prepare-frontend` before it, then `npm ci` and `npx vitest
  run --coverage` in the web module, and packages with `-Pproduction -Dvaadin.ci.build=true`; on Gradle every job uses
  `gradle/actions/setup-gradle` (open-source `basic` cache provider) with `./gradlew
  test`/`integrationTest`/`:coverage:testCodeCoverageReport`/`detekt ktlintCheck`/`dokkaGeneratePublicationHtml`; a
  `deploy.yml` that builds and pushes the container image (`spring-boot:build-image`, or `bootBuildImage` tagged with
  the `gradle.properties` version on Gradle), authenticates to AWS or Google Cloud via keyless OIDC, and applies the
  OpenTofu configuration for a chosen environment behind a GitHub Environment approval gate; an `undeploy.yml` that
  scales the service to zero or destroys an environment's infrastructure, guarded by a typed-confirmation input and a
  protected environment; a `security.yml` that runs a `dependency-review` job (`actions/dependency-review-action@v5`),
  a CodeQL job (`github/codeql-action@v4`, `java-kotlin` with autobuild on Maven or a manual `./gradlew` compile on
  Gradle, matrix including `javascript-typescript` when `frontend` is `hilla`), on Gradle a `dependency-submission`
  job (`gradle/actions/dependency-submission`) feeding the dependency graph that dependency review compares, an
  OSV-Scanner job (the `google/osv-scanner-action` reusable workflow), and a `gitleaks` job
  (`gitleaks/gitleaks-action@v3`) — each individually omittable; and a `.github/dependabot.yml` with grouped weekly
  updates for the `maven` (or `gradle`), `docker`, and `github-actions` ecosystems, plus `npm` (pointed at the real
  web module's directory) when the manifest's `frontend` isn't `none`. Reads `sonar.mode` from `springboot-stack.yml`
  as the source of truth for whether the Sonar step and `SONAR_TOKEN` secret are generated at all, rather than asking
  reactively, and reads the manifest's `visibility` and `ci:` block (`ci.tests` = `unit` ⇒ Surefire only with
  `-DskipITs` and no Testcontainers/Docker stack in CI, `full` ⇒ Surefire + Failsafe + Testcontainers; `ci.pages` =
  `no` ⇒ the docs are still built but uploaded as a workflow artifact instead of deployed to GitHub Pages) — `args`
  may override them, and when invoked standalone with no `ci:` block it resolves `visibility` (args, then `gh repo
  view`, then asks) and asks `ci-tests`/`pages` (and `sonar` when the manifest has none) itself, stating the
  Actions-minutes/SonarCloud/Pages cost facts for a private repository. Announces whether it is creating the workflows
  from scratch or updating existing ones, and for every workflow/config file that already exists warns and asks Update
  / Keep as is / Replace (or applies `on-existing` from `args`). Derives the pipeline from `springboot-stack.yml` and
  the actual reactor/`infra/` layout on disk, lists every required repository secret and environment, and never writes
  a credential into a workflow file. Invoke as `/iru-setup-java-springboot-github-workflows`, or with `args`
  (`stack-file:`, `integration-branch:`, `main-branch:` lines, plus
  `security-dependency-review`/`security-codeql`/`security-osv`/`security-gitleaks`, each `yes`/`no`, default `yes`,
  and the shared `visibility` (`public`/`private`/`internal`), `ci-tests` (`unit`/`full`), `pages` (`yes`/`no`),
  `sonar`, `mode` (`new`/`existing`), and `on-existing` (`ask`/`keep`/`update`/`replace`) keys) when called from
  `iru-setup-java-springboot`. When the manifest's `deploy.rolling.enabled` is true (or `rolling: yes` arrives in
  `args`, with `deployment-strategy:` (`rolling`/`blue-green`/`canary`/`linear`), `advance:` (`auto`/`manual`/`hybrid`),
  `steps:` and `bake-minutes:`) `deploy.yml` becomes a staged rollout — build image, deploy the new version at 0 %
  traffic, smoke-test its candidate URL, shift traffic in steps with a metric gate and an automatic rollback — and a
  `promote.yml` (`workflow_dispatch`, no GitHub Environment reviewers needed) lets a human advance, roll back or abort
  the rollout on any GitHub plan, with the rollout state read from the cloud (ECS weighted target groups, Cloud Run
  traffic tags, Argo Rollouts); `undeploy.yml` resets the split first. Rolling disabled or absent keeps today's
  single-job `deploy.yml` unchanged and generates no `promote.yml`; with `ci: no` no workflows, hence no rolling. Use
  whenever a Spring Boot service needs its CI/CD pipeline bootstrapped instead of
  hand-writing the YAML for testing, analysis, documentation publishing, deployment, teardown, and
  dependency/secret/code security scanning.
model: sonnet
---

# Setup Java Spring Boot GitHub Workflows

Generate the workflows for a Spring Boot service (three, plus `promote.yml` when rolling deployments are enabled). This is deliberately a different pipeline from the
library-oriented `iru-setup-java-github-workflows`: a service is not published to Maven Central and is not
GPG-signed — it is built into a container image and deployed. The shared stages (test, analyse, Sonar, Antora,
GitHub Pages) follow the same house pattern as that skill, so the two are recognisably related; the publish/sign/
sync stages are replaced by image build, OpenTofu apply, and teardown.

| Workflow | Trigger | Does |
|---|---|---|
| `build.yml` | push to integration/main branch, and every pull request | build, unit tests, integration tests (only when `ci.tests: full`), static analysis, coverage, Sonar (when `sonar.mode` isn't `none`), docs; publishes Pages from the main branch only when `ci.pages: yes`, otherwise uploads the built docs as a workflow artifact |
| `deploy.yml` | `workflow_dispatch` (environment input) and optionally on release published | build + push image, OIDC auth, `tofu apply`, smoke check — or, with rolling deployments, a staged rollout (Step 2b) |
| `promote.yml` | `workflow_dispatch` (environment + target inputs); **only with rolling deployments** (not for `strategy: rolling`) | advance a rollout one step, or roll back / abort it (Step 2c) |
| `undeploy.yml` | `workflow_dispatch` only, with typed confirmation | scale to zero, or `tofu destroy` an environment |
| `security.yml` | push to main branch, every pull request, weekly schedule | dependency review, CodeQL, OSV-Scanner, gitleaks — each individually omittable |
| `.github/dependabot.yml` | n/a (config, not a workflow) | grouped weekly updates for `maven`, `docker`, `github-actions`, and `npm` when a frontend is present |

**No credential is ever written into a workflow file.** Cloud access is keyless via OIDC; everything else is a
repository or environment secret referenced by name.

## Step 0 — Survey and resolve inputs

Parse `args` for `key: value` lines:

```
stack-file: springboot-stack.yml
integration-branch: develop
main-branch: main
security-dependency-review: yes
security-codeql: yes
security-osv: yes
security-gitleaks: yes
visibility: private
ci-tests: unit
pages: no
sonar: none
mode: existing
on-existing: ask
```

- **`stack-file`**/**`integration-branch`**/**`main-branch`** — as before.
- **`visibility`** (`public`/`private`/`internal`), **`ci-tests`** (`unit`/`full`), **`pages`** (`yes`/`no`),
  **`sonar`** (`cloud`/`self-hosted`/`none`) — overrides for the manifest's `visibility`, `ci.tests`, `ci.pages`,
  and `sonar.mode` (see "Resolving the CI choices" below). Normally absent: `iru-setup-java-springboot` records
  them in the manifest, which is enough.
- **`rolling`** (`yes`/`no`), **`deployment-strategy`** (`rolling`/`blue-green`/`canary`/`linear`), **`advance`**
  (`auto`/`manual`/`hybrid`), **`steps`** (comma list of percentages), **`bake-minutes`** — rolling deployments (see
  "Rolling deployments" below). Normally absent: the manifest's `deploy.rolling` block is the source of truth when
  `stack-file` is given; the `args` lines apply when there is no such block or when the caller passes them
  explicitly. Absent or `rolling: no` ⇒ rolling is off and Steps 2b/2c, the `promote.yml` rows and every "rolling"
  paragraph below are skipped.
- **`mode`** (`new`/`existing`) — informational; this skill still decides scratch-vs-update per file from what's on
  disk, and `mode: existing` does **not** mean "update silently" — existing files are still asked about below.
- **`on-existing`** (`ask`/`keep`/`update`/`replace`, default `ask`) — how to treat each workflow/config file that
  already exists (see "Existing workflow files" below).
- **`security-dependency-review`**/**`security-codeql`**/**`security-osv`**/**`security-gitleaks`** — each
  `yes`/`no`, default `yes` when not supplied. Individually gate the matching job in `security.yml` (Step 3b);
  `.github/dependabot.yml` itself is always generated regardless of these four flags, since dependency updates and
  vulnerability scanning are two different concerns. Any not supplied via `args` is asked with `AskUserQuestion`
  (default yes) rather than silently assumed, unless this skill is running unattended as part of
  `iru-setup-java-springboot`'s Step 8, in which case the default stands without asking.

Read `springboot-stack.yml` for the cloud, the Java version, `project.language` and `project.buildTool` (see
"Language and build tool" below), `visibility`, the `ci:` block (`ci.tests`,
`ci.pages`), `sonar.mode`
(`cloud`/`self-hosted`/`none` — absent means `cloud`, for backward compatibility with a manifest written before
this field existed) and its `sonar.organization`/`sonar.projectKey`/`sonar.hostUrl`, `frontend`
(`none`/`hilla`), and which technologies are in play. **`sonar.mode` is the source of truth for whether `build.yml`
gets a Sonar step at all** — this skill no longer asks reactively whether to add or omit it. **`frontend: hilla`
is the source of truth for whether `build.yml` gets a Node/Vitest step, `security.yml`'s CodeQL matrix gets a
`javascript-typescript` language, and `.github/dependabot.yml` gets an `npm` ecosystem entry** — see Step 1 and
Step 3b. Then survey what's actually on disk — the workflows must match reality, not the manifest's intent:

- The reactor's modules, and the `boot` module's directory (that's what produces the image).
- Whether `coverage/` exists and where `report-aggregate` writes (`coverage/target/site/jacoco-aggregate/jacoco.xml`)
  — this is the path Sonar reads, when `sonar.mode` isn't `none`.
- When `sonar.mode` isn't `none`: whether `sonar-maven-plugin` and the `sonar.*` properties actually exist in the
  root pom (written by `iru-setup-java-springboot-pom` per the same `sonar.mode` field). If they don't — a
  manifest/pom drift, e.g. the pom was generated by an older `iru-setup-java-springboot-pom` that predates the
  `sonar:` block — say so in Step 6's report and offer to
  re-run `iru-setup-java-springboot-pom` rather than silently generating a `mvn sonar:sonar` step that's certain
  to fail. When `sonar.mode: none`, skip this check entirely: no Sonar step is generated, so there's nothing on
  the pom side to verify.
- Whether `docs/antora.yml` and `docs/antora-playbook.yml` exist, and which extensions `docs/package.json` lists
  (the install step must match — including `asciidoctor-kroki` if the docs use Kroki).
- Where the API documentation generators write (`*/target/generated-docs/...`), from the module poms.
- Whether `apis/graphql-server/` holds an SDL and an `apis/graphql-server/docs/package.json`, and whether that
  toolchain includes `graphql-voyager` as well as `spectaql` — the docs job's GraphQL step must match what's
  actually pinned there, and its `package-lock.json` must be committed for `npm ci`.
- Whether `apis/messaging/` holds an AsyncAPI specification and an `apis/messaging/docs/package.json`
  (set up by `iru-setup-java-springboot-apis`). If so, the docs job must also produce the AsyncAPI HTML; note
  whether `apis/messaging/docs/package-lock.json` is committed, since that decides `npm ci` versus `npm install`,
  and which module's pom carries the `frontend-maven-plugin` executions.
- When `frontend: hilla`: which module actually carries `src/main/frontend/` and the `vaadin-maven-plugin`
  execution (written by `iru-setup-java-springboot-hilla` — normally `boot`), and whether that module's
  `package-lock.json` is committed (it should be — `vaadin:prepare-frontend` generates it alongside `package.json`
  at the module root, next to `pom.xml`, not inside `src/main/frontend/`; confirm the real path rather than
  assuming `src/main/frontend/package-lock.json`, which is not where it lives). If the module or its
  `vitest.config.ts` doesn't exist yet, still generate the Node/Vitest step in `build.yml` but mark it as
  requiring `/iru-setup-java-springboot-hilla` first, and say so in the report.
- Whether `infra/envs/<env>/` directories exist and which environments they define. If `infra/` doesn't exist,
  still generate `deploy.yml`/`undeploy.yml` but mark the OpenTofu steps as requiring
  `/iru-setup-java-springboot-platform` first, and say so in the report.
- **Rolling deployments.** Resolve `deploy.rolling` (`enabled`, `strategy`, `advance`, `steps`, `bakeMinutes`) as
  described above and validate it like the orchestrator does (`steps` ascending, ending in 100, `blue-green` is
  `[100]`; `rolling` with `manual`/`hybrid` is contradictory — ask which to change). Rolling is **forced off** when
  `ci.enabled: false` (no workflows exist to drive it — say so). When on, survey `infra/envs/*` for the OpenTofu
  outputs `rollout_candidate_url`, `rollout_gate`, `rollout_alarm_names`, `rollout_target_groups`, `rollout_name`
  (grep the `outputs.tf` files): which runtime they imply (`cloudwatch` ⇒ ECS, `cloud-monitoring` ⇒ Cloud Run,
  `prometheus` ⇒ Kubernetes) decides the rollout-functions block and the auth/kubeconfig steps in Step 2b. If they
  are missing, still generate the workflows but mark the rollout steps as requiring
  `/iru-setup-java-springboot-platform` (with `rolling: yes`) first and say so in the report. For `strategy:
  rolling` only Step 2's single-job template (plus the settle step) is generated.
- The branch model: run `git branch -a`, don't assume gitflow. Confirm the integration and main branch names.
- Whether GitHub Environments already exist (`gh api repos/{owner}/{repo}/environments`) — `deploy.yml` and
  `undeploy.yml` depend on them for approval gates.
- Whether `compose.yaml` exists and how heavy the container stack is: integration tests on a standard GitHub
  runner (4 vCPU / 16 GB) can't host Elasticsearch + Couchbase + Kafka + several databases simultaneously. If the
  stack looks too large, say so now and offer either a larger runner or splitting integration tests into a matrix
  by module. Skip this check when `ci.tests: unit` — no container stack runs in CI then.

### Language and build tool

`project.language` (`java`/`kotlin`, absent ⇒ `java`) and `project.buildTool` (`maven`/`gradle`, absent ⇒ `maven`;
`gradle` only ever appears with `kotlin`) pick one of three variants. Confirm them against the disk the same way as
everything else: `pom.xml` at the root ⇒ Maven, `settings.gradle.kts` + `gradlew` ⇒ Gradle, `src/main/kotlin` in the
modules ⇒ Kotlin. If the manifest and the disk disagree, the disk wins for this run — say so in the report.

| Variant | Templates | What changes |
|---|---|---|
| `java` + `maven` | Steps 1–3b exactly as written | nothing — the Java path is the base template |
| `kotlin` + `maven` | Steps 1–3b as written, plus "Kotlin + Maven" in Step 1 | static analysis is detekt + ktlint instead of Checkstyle/PMD/SpotBugs, code docs are Dokka instead of Javadoc; every `mvn` build/test/Sonar/image command is unchanged |
| `kotlin` + `gradle` | the Gradle templates in Steps 1, 2 and 3b | every job uses `gradle/actions/setup-gradle` and `./gradlew`; `security.yml` gains `dependency-submission`; Dependabot uses the `gradle` ecosystem |

For Gradle, also survey: that `gradlew`, `gradle/wrapper/gradle-wrapper.properties` and
`gradle/wrapper/gradle-wrapper.jar` are committed (CI uses the wrapper only — never a runner-installed `gradle`);
that the `integrationTest` task and the `:coverage` project's `testCodeCoverageReport` task exist
(`./gradlew tasks --all`, both written by `iru-setup-java-springboot-pom`'s `build-logic/` convention plugins); where
the aggregated JaCoCo XML lands (`coverage/build/reports/jacoco/testCodeCoverageReport/testCodeCoverageReport.xml`
by default); whether the root project aggregates Dokka (`dokka(project(":…"))` dependencies ⇒ one site at
`build/dokka/html`) or only each module runs it (⇒ one `build/dokka/html` per module); that `gradle.properties`
carries a `version=` line (the deploy workflow's image tag reads it); and which tasks generate the API documentation
(`./gradlew -q :<project>:tasks --group documentation` for each project applying a codegen plugin — the root-level
`./gradlew tasks --group documentation` doesn't list subproject tasks like `generateRestServerV1Docs` — the OpenAPI
html2 and protoc-gen-doc equivalents
`iru-setup-java-springboot-apis` registers), and that they write under `<module>/build/generated-docs/`.

### Resolving the CI choices

The manifest is the source of truth, `args` overrides it, and only what is still unresolved is asked. Being
invoked at all means CI is wanted, so `ci` itself is never asked here (a manifest with `ci.enabled: false` is
contradictory with running this skill — say so, and ask whether to proceed and flip it to `true`, or stop).

1. **`visibility`** — `args`, else the manifest's `visibility`, else `gh repo view --json visibility -q
   .visibility` (lowercased; tell the user the detected value), else ask with `AskUserQuestion` — **Public** /
   **Private** — recommending Public when the manifest's `openSource: true`, otherwise Private. `internal`
   behaves like `private` for every decision below. If `openSource: true` but visibility is `private`/`internal`,
   warn that this is contradictory (a private repo forfeits the free-for-public-repos pricing) and ask which is
   right.
2. **`sonar`** — `args`, else the manifest's `sonar.mode`. Only when neither has it (a manifest written before the
   `sonar:` block existed), ask "Configure SonarCloud / SonarQube and send CI analysis and coverage reports to
   it?", recommending `cloud` only when the repository is public **and** open source, otherwise `none` (with
   `self-hosted` as the alternative) — SonarCloud is free for public/open-source projects; a private project needs
   a paid plan. If `sonar.mode: cloud` and visibility is `private`/`internal`, point that out in the report.
3. **`ci-tests`** — `args`, else the manifest's `ci.tests`, else ask "Which tests should CI run?":
   - **Unit tests only** (`unit`) — Surefire `*Test` only; Failsafe `*IT` integration tests and the
     Testcontainers/docker compose stack stay local. Cheaper: fewer minutes, faster feedback. Recommended for
     private/internal repositories.
   - **Unit + integration** (`full`) — Surefire plus Failsafe integration tests against the Testcontainers stack
     (databases, Kafka + Schema Registry, the API mock, …). Complete verification, but uses considerably more
     minutes. Recommended for public repositories.
   For a private/internal repository, state the cost facts per GitHub's current pricing (tell the user to
   double-check their plan): standard GitHub-hosted runners are free for public repositories; private/internal
   ones consume the account's included minutes — 2,000/month on GitHub Free, 3,000 on Pro and Team, 50,000 on
   Enterprise Cloud — then are billed per minute (Linux 2-core $0.006/min). Every workflow here runs on
   `ubuntu-latest`, so the macOS/Windows multipliers don't apply.
4. **`pages`** — `args`, else the manifest's `ci.pages`, else: public ⇒ `yes` without asking (say so in the
   report); private/internal ⇒ ask with **No (Recommended)** — "CI still builds the Antora site, Maven site, and
   API docs and uploads them as a workflow artifact; nothing is published" — versus **Yes** — "GitHub Pages for a
   private/internal repository requires GitHub Pro, Team, or Enterprise Cloud (not GitHub Free), and the site
   will be **publicly accessible on the internet** unless the organization is on Enterprise Cloud and publishes it
   with private access control".

When any of these was resolved by asking (or by `gh`) rather than read from the manifest, offer to record it in
`springboot-stack.yml` (`visibility:`, `ci: { enabled: true, tests: …, pages: … }`, `sonar.mode`) so the next
run and `iru-update-java-springboot-documentation` see the same choice; an `args` override is applied for this run
only and not written back unless the user agrees.

### Existing workflow files

Say up front whether this run is **creating the workflows from scratch** (none of `build.yml`, `deploy.yml`,
`promote.yml`, `undeploy.yml`, `security.yml`, `.github/dependabot.yml` exist) or **updating existing ones** (list
which exist), and **whether rolling deployments are on or off** (strategy, advance, steps, bake minutes when on) with
the state of the two files it changes — `deploy.yml`: *absent*, *single-job* (today's template), or *staged*
(contains `deploy-green`); `promote.yml`: *absent*, *present*, or *partial* (exists but does not match the current
`steps`/`advance`/runtime). The usual Update / Keep as is / Replace / Stop prompt applies to `promote.yml` like any
other file, with these rolling-specific warnings: switching `deploy.yml` between single-job and staged is a
**behavioural change** (replace/update it only with an explicit yes — a rollout in flight must not be orphaned, so
check the cloud split via `/iru-springboot-rolling-deployments`'s in-progress check first); a `promote.yml` found
while rolling is off is *stale* (offer to remove it — never delete without confirmation); `promote.yml` carries
the `target` options generated from `steps`, so a changed `steps` list makes an existing one *partial*.
For each one that exists, warn and — unless `on-existing` is `keep`/`update`/`replace`, in which case apply it to
every file without asking (still print the warning) — ask with `AskUserQuestion` (up to 4 files per call, one
question each), stating concretely where the existing file contradicts this run's choices (e.g. "your current
`build.yml` runs `mvn verify` with Failsafe/Testcontainers but you chose `ci-tests: unit`", "it deploys to
`gh-pages` but `pages: no`", "it still runs `sonar:sonar` after `sonar: none`"):

- **Update (Recommended)** — merge: add what's missing and correct the stages this skill owns (action versions,
  gated steps, test scope, Pages vs artifact, Sonar) using the templates below; keep every step/job this skill
  doesn't own (a Slack notification, an extra matrix leg). You review a diff; your customizations survive, but a
  customized part of a stage this skill owns may be rewritten.
- **Keep as is** — leave the file untouched. Nothing you customized changes, but it may stay out of date or
  disagree with this run's choices — Step 6's report lists each mismatch.
- **Replace** — regenerate from the template. Matches this house pattern exactly, but every customization in the
  file is lost (recoverable only from git history).
- **Stop** — end this skill now without changing any file.

**Accessibility opt-out.** Read the repository's `.ui-quality.yml` `accessibility` level (UI contract §8). When it is
`none` (opted out entirely), emit no accessibility report artifact, upload or step: do not collect `a11y-report.txt`
or other accessibility reports into the `ui-screenshots` artifacts, and drop any accessibility-only job or step;
the UI test run and the screenshot upload are unaffected. With `enforce`, `report` or `off` the workflows are
generated exactly as below (`off` runs no automated checks, so no accessibility report exists to upload either).

## Step 1 — `build.yml`

Structure it as two jobs so a pull request gets fast feedback and Pages publishing only happens on the main branch.
The template below is the `ci.tests: full` / `ci.pages: yes` shape; the `unit` and `pages: no` variants follow it.

```yaml
name: Build

on:
  push:
    branches: [ <integration-branch>, <main-branch> ]
  pull_request:
    branches: [ <integration-branch>, <main-branch> ]

# A new push to the same branch/PR makes the previous run obsolete.
concurrency:
  group: build-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  build:
    name: Build, test and analyse
    runs-on: ubuntu-latest
    steps:
      - name: Check out code
        uses: actions/checkout@v7
        with:
          # Sonar needs full history to attribute issues to blame data.
          fetch-depth: 0

      - name: Set up JDK <java-version>
        uses: actions/setup-java@v6
        with:
          distribution: temurin
          java-version: <java-version>
          cache: maven

      # Only when the manifest's frontend: hilla. Must come before the Maven build step below: the Vaadin
      # plugin's `prepare-frontend`/`build-frontend` goals (bound in <web-module>/pom.xml by
      # iru-setup-java-springboot-hilla) need Node on PATH, and without a pre-installed Node the plugin falls
      # back to downloading its own into ~/.vaadin, which adds real time to every uncached run.
      - name: Set up Node
        uses: actions/setup-node@v7
        with:
          node-version: 24
          cache: npm
          # The real path npm writes its lock file to: vaadin:prepare-frontend generates package.json/
          # package-lock.json at the web module's root, next to its pom.xml — never inside
          # src/main/frontend/. Confirmed by an actual generated project; don't use
          # src/main/frontend/package-lock.json here.
          cache-dependency-path: <web-module>/package-lock.json

      - name: Build, unit tests and integration tests
        # `verify` runs Surefire, then Failsafe against the Testcontainers stack, then the JaCoCo
        # aggregate report. Docker is available on ubuntu-latest runners, so no extra setup is needed.
        # -Pproduction -Dvaadin.ci.build=true only apply when frontend: hilla: the production profile builds
        # the real Vite bundle instead of leaving the frontend in dev-bundle mode, and vaadin.ci.build=true
        # (confirmed against the plugin's own parameter metadata) makes it run `npm ci` instead of
        # `npm install` so the committed package-lock.json is never silently rewritten by CI.
        run: mvn -B -ntp clean verify -Pproduction -Dvaadin.ci.build=true

      # Only when the manifest's frontend: hilla. Must run after the Maven step above, not before: both
      # vite.config.ts and vitest.config.ts import <web-module>/vite.generated.ts, which itself imports
      # helper scripts under <web-module>/target/plugins/ — files that exist only once a Maven build has
      # reached vaadin:prepare-frontend. Running this step first fails on a module-not-found error that has
      # nothing to do with the frontend tests themselves. Confirmed by an actual local run.
      - name: Frontend unit tests and coverage
        working-directory: <web-module>
        run: |
          npm ci
          npx vitest run --coverage

      # Only when frontend: hilla, ci.tests: full, and the web module has a playwright.config.ts (written by
      # iru-setup-java-springboot-hilla). Runs the Playwright component tests against the standalone Vite gallery
      # in the same job (no extra runner); captures land in .ui-screenshots/ per the catalog's UI contract.
      - name: Frontend UI tests
        working-directory: <web-module>
        env:
          CI: "true"
          UI_SCREENSHOTS_DIR: ${{ github.workspace }}/.ui-screenshots
        run: |
          npx playwright install --with-deps chromium
          npx playwright test

      - name: Upload UI screenshots
        if: always()
        uses: actions/upload-artifact@v7
        with:
          name: ui-screenshots
          path: .ui-screenshots/
          retention-days: 7
          if-no-files-found: ignore

      - name: Static analysis and site report
        run: mvn -B -ntp site -DskipTests -Djacoco.skip

      - name: Run SonarCloud analysis
        # Only present at all when the manifest's sonar.mode isn't `none` — see Step 0. Skipped on pull
        # requests from forks, where SONAR_TOKEN is not available.
        if: ${{ github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: mvn -B -ntp sonar:sonar -Dsonar.token=${{ secrets.SONAR_TOKEN }}

      - name: Upload test reports
        # `always()` so a failing build still yields the reports that explain why.
        if: always()
        uses: actions/upload-artifact@v7
        with:
          name: test-reports
          path: |
            **/target/surefire-reports/**
            **/target/failsafe-reports/**
            coverage/target/site/jacoco-aggregate/**
            <web-module>/coverage/**
          retention-days: 7

  docs:
    name: Build and publish documentation
    needs: build
    if: github.ref == 'refs/heads/<main-branch>' && github.event_name == 'push'
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Check out code
        uses: actions/checkout@v7

      - name: Set up JDK <java-version>
        uses: actions/setup-java@v6
        with:
          distribution: temurin
          java-version: <java-version>
          cache: maven

      - name: Install Node
        # v7 — confirmed the current major via the live GitHub API at the time of writing, and kept in step
        # with the `build` job's own Set up Node step (frontend: hilla) so both jobs use one version.
        uses: actions/setup-node@v7
        with:
          node-version: 24
          cache: npm
          # Every npm toolchain in the repository: the Antora site, the AsyncAPI
          # generators, and the GraphQL ones. Omit any path the repository doesn't have.
          cache-dependency-path: |
            docs/package-lock.json
            apis/messaging/docs/package-lock.json
            apis/graphql-server/docs/package-lock.json

      - name: Generate API documentation and the Maven site
        # generate-resources runs the OpenAPI html2 and protoc-gen-doc executions;
        # `site` produces the Javadoc/Surefire/JaCoCo/Checkstyle/PMD/SpotBugs/JXR reports.
        # The npm-driven generators (AsyncAPI, GraphQL) are skipped here and run as their
        # own steps below, so this job doesn't generate them twice; the `build` job above
        # still exercises the frontend-maven-plugin wiring, because `mvn clean verify`
        # passes through generate-resources like any other build.
        run: |
          mvn -B -ntp clean generate-resources -Dasyncapi.docs.skip=true -Dgraphql.docs.skip=true
          mvn -B -ntp site -DskipTests -Djacoco.skip

      - name: Generate AsyncAPI documentation
        # The official AsyncAPI HTML generator, run against the committed toolchain in
        # apis/messaging/docs — see iru-setup-java-springboot-apis.
        if: hashFiles('apis/messaging/docs/package.json') != ''
        working-directory: apis/messaging/docs
        env:
          # Committed file with analyticsEnabled=false, so the CLI reports nothing anywhere.
          ASYNCAPI_METRICS_CONFIG_PATH: .asyncapi-analytics
        run: |
          npm ci --no-audit --no-fund
          out="$GITHUB_WORKSPACE/target/generated-docs/messaging"
          for spec in ../*-async-api-v*.yaml; do
            v="$(basename "$spec" .yaml | sed -e 's/.*-async-api-//')"     # v1, v2, ...
            npx asyncapi validate "$spec"
            npx asyncapi generate fromTemplate "$spec" @asyncapi/html-template \
              -o "$out/$v" --force-write -p singleFile=true
          done

      - name: Generate GraphQL documentation
        # SpectaQL renders the static reference from the SDL; the small build-voyager.mjs
        # script renders the interactive schema graph beside it. Both read the SDL directly,
        # so neither needs a running service or an introspection endpoint in CI.
        if: hashFiles('apis/graphql-server/docs/package.json') != ''
        working-directory: apis/graphql-server/docs
        run: |
          npm ci --no-audit --no-fund
          out="$GITHUB_WORKSPACE/target/generated-docs/graphql-server"
          for sdl in ../*-v*.graphqls; do
            v="$(basename "$sdl" .graphqls | sed -e 's/.*-\(v[0-9]*\)$/\1/')"      # v1, v2, ...
            npx spectaql "spectaql-$v.yml" --target-dir "$out/$v"
            # Drop this line if the Voyager schema graph wasn't wanted.
            node build-voyager.mjs "$sdl" "$out/$v/voyager" "GraphQL schema $v"
          done

      - name: Install Antora
        working-directory: docs
        run: npm ci

      - name: Build Antora docs
        working-directory: docs
        run: npx antora antora-playbook.yml

      - name: Merge documentation
        run: |
          touch ./docs/build/site/.nojekyll
          cp -r ./docs/build/site ./doc
          cp -r ./target/site ./doc/mvn-site
          # Generated API documentation, published alongside so the Antora pages can link to
          # it. Every generator in the repository writes under some `target/generated-docs`
          # — the OpenAPI html2 and protoc-gen-doc executions into their module's, the
          # AsyncAPI step above into the root one — so copying the *contents* of each such
          # directory merges rest-server/, grpc-server/ and messaging/ under ./doc/api
          # without needing to know which module produced which. The result is
          # doc/api/rest-server/v1/, doc/api/grpc-server/v1/, doc/api/messaging/v1/.
          mkdir -p ./doc/api
          while IFS= read -r root; do
            cp -r "$root"/. ./doc/api/
          done < <(find . -type d -path '*/target/generated-docs')

      - name: Deploy to GitHub Pages
        if: success()
        uses: crazy-max/ghaction-github-pages@v5
        with:
          target_branch: gh-pages
          build_dir: ./doc
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Adjust to the survey: `npm ci` only works if `docs/package-lock.json` is committed — if it isn't, fall back to the
explicit `npm i` list `iru-setup-antora` uses, **including `asciidoctor-kroki`** if the playbook requires it, or a
Kroki-diagram page will fail the build. The `mvn site` invocation at the reactor root aggregates every module's
reports; verify the aggregate actually lands in `./target/site` for this reactor (a multi-module `site` sometimes
needs `site:stage`) and use whichever path is real.

**`ci.tests: unit`** — CI runs Surefire only, with no Testcontainers/Docker stack:

- Rename the Maven step to `Build and unit tests` and run `mvn -B -ntp clean verify -DskipITs` (keeping
  `-Pproduction -Dvaadin.ci.build=true` when `frontend: hilla`). `-DskipITs` is Failsafe's own skip property, so
  `*IT` classes — the only ones that start the Testcontainers/compose stack written by
  `iru-setup-java-springboot-testcontainers` — never run, while Surefire `*Test` classes and the `coverage/`
  module's `report-aggregate` still do; the JaCoCo aggregate (and therefore Sonar's coverage) then reflects unit
  tests only. Replace the step's comment accordingly (no Failsafe, no Docker needed).
- Drop `**/target/failsafe-reports/**` from the artifact-upload paths.
- Add a one-line comment at the top of the job stating that integration tests run locally only
  (`mvn verify`), so nobody assumes CI exercised them.
- Verify against the survey that the reactor really separates the two (Failsafe bound with `*IT` includes, as
  `iru-setup-java-springboot-pom` configures it). If some test that needs Docker is a Surefire `*Test`, it would
  still run — and fail — in CI; flag that class by name in the report rather than silently passing.

**`ci.tests: full`** — the template as written: `verify` runs Surefire, then Failsafe against the Testcontainers
stack, then the aggregate report.

**`ci.pages: no`** — keep the `docs` job (it still validates that the Antora site, the Maven site, and every API
doc generator build) but:

- Replace the `Deploy to GitHub Pages` step with an artifact upload of the merged tree:

  ```yaml
      - name: Upload documentation
        # ci.pages: no — nothing is published; download the artifact from the run to browse the docs.
        if: success()
        uses: actions/upload-artifact@v7
        with:
          name: documentation
          path: ./doc
          retention-days: 14
  ```

- Drop the job's `permissions: contents: write` (only the `gh-pages` push needed it) — the workflow-level
  `contents: read` is enough — and the `.nojekyll` touch, which only matters to Pages.
- Rename the job to `Build documentation`. Keep its `if:` (main-branch pushes only) so pull requests don't pay
  for a docs build twice; widening it to every run is the user's call.
- Say in the report that no github.io site will exist, so `iru-update-java-springboot-documentation`'s
  `api-docs-url` attribute (which points the Antora API pages at `https://<owner>.github.io/<repo>/api`) would be
  a dead link — flag it for the user.

If the manifest's `sonar.mode` is `none`, drop the entire `Run SonarCloud analysis` step from `build.yml` rather
than leaving it in with a permanently-false condition — dead YAML that can never run is worse than no YAML.

The `Frontend UI tests` and `Upload UI screenshots` steps (both templates) exist only when `frontend: hilla`,
`ci.tests: full`, and `<web-module>/playwright.config.ts` exists — drop both otherwise (with `ci.tests: unit` the UI
tests stay a local/group-validation stage, so no Chromium download is paid on every run).

If the manifest's `frontend` isn't `hilla`, drop the `Set up Node` and `Frontend unit tests and coverage` steps,
the `-Pproduction -Dvaadin.ci.build=true` flags on the Maven build step, and the `<web-module>/coverage/**`
artifact-upload path entirely — same reasoning as the Sonar step above, and there's no web module for any of it
to point at.

If the repository has no `apis/messaging/`, drop the AsyncAPI step, the `-Dasyncapi.docs.skip=true` flag, and the
second `cache-dependency-path` entry entirely rather than leaving dead YAML behind. If it does:

- The step is guarded by `hashFiles(...) != ''` as well, so the workflow survives someone deleting the messaging
  contracts without a workflow edit.
- The same `apis/messaging/docs/package-lock.json` caveat applies: without a committed lock file `npm ci` fails
  outright — commit it, or fall back to `npm install`, and say which in the report.
- The loop over `../*-async-api-v*.yaml` picks up `v2` automatically when it's added, so a new contract version
  needs no workflow change. Keep the filename convention and the loop in step with each other.
- The published layout ends up as `doc/api/messaging/v1/index.html` and
  `doc/api/graphql-server/v1/index.html` (with the Voyager graph at
  `doc/api/graphql-server/v1/voyager/index.html`), next to `doc/api/rest-server/v1/` and
  `doc/api/grpc-server/v1/`. Those are the URLs the Antora API pages link to, so changing them means updating
  `/iru-update-java-springboot-documentation`'s output too.
- Voyager's page loads `voyager.standalone.js` and `voyager.css` by **relative** path, so those two files must be
  copied alongside `index.html`. The merge step's directory copy preserves that automatically; a merge step
  rewritten to copy only `index.html` files would silently produce a blank graph.

### Kotlin + Maven (`language: kotlin`, `buildTool: maven`)

Same two jobs, same `mvn` build/test/Sonar commands and the same `ci.tests`/`ci.pages`/`sonar.mode`/`frontend`
variants — `iru-setup-java-springboot-pom` keeps Surefire `*Test`, Failsafe `*IT`, JaCoCo and the `coverage/`
`report-aggregate` identical for Kotlin. Only the quality and code-documentation tools differ, because the pom wires
detekt/ktlint/Dokka instead of Checkstyle/PMD/SpotBugs/Javadoc:

- In the `build` job, replace the `Static analysis and site report` step with:

  ```yaml
      - name: Static analysis (detekt + ktlint)
        # detekt-maven-plugin and ktlint-maven-plugin replace Checkstyle/PMD/SpotBugs for Kotlin. Both read
        # sources only, so no compile is needed; their XML reports are what the Sonar Kotlin sensor imports
        # (sonar.kotlin.detekt.reportPaths / sonar.kotlin.ktlint.reportPaths in the root pom), so this step must
        # stay before the Sonar step.
        run: mvn -B -ntp detekt:check ktlint:check
  ```

  Use the goals the pom actually binds: if it already binds `detekt:check`/`ktlint:check` to `verify`, the
  `mvn clean verify` step runs them and this step is redundant — drop it and say so. The `detekt`/`ktlint` prefixes
  resolve because the plugins are declared in the root pom; if the survey finds them only in a profile, call them by
  coordinates (`com.github.ozsie:detekt-maven-plugin:check`, `com.github.gantsign.maven:ktlint-maven-plugin:check`).
- Add `**/target/detekt*.xml` and `**/target/ktlint*.xml` (whatever report paths the pom configures) to the
  `Upload test reports` artifact paths, so a failing lint run leaves its findings attached.
- In the `docs` job, keep `mvn -B -ntp site -DskipTests -Djacoco.skip` (Surefire/JaCoCo/JXR reports — the pom no
  longer configures Javadoc/Checkstyle/PMD/SpotBugs reports, so the site simply doesn't have those sections) and add
  the Dokka build as its own step before `Install Antora`:

  ```yaml
      - name: Generate KDoc (Dokka)
        # dokka-maven-plugin runs per module and writes <module>/target/dokka/ — Dokka's Maven plugin has no
        # multi-module aggregation, so each module gets its own site.
        run: mvn -B -ntp dokka:dokka
  ```

  and, in `Merge documentation`, copy each module's Dokka site under `./doc/api/kdoc/<module-path>/` (that's the
  location `iru-update-java-springboot-documentation` links its code reference to):

  ```bash
          while IFS= read -r dir; do
            module="$(dirname "$(dirname "$dir")")"; module="${module#./}"
            mkdir -p "./doc/api/kdoc/$module" && cp -r "$dir"/. "./doc/api/kdoc/$module/"
          done < <(find . -type d -path '*/target/dokka' -not -path './node_modules/*')
  ```

  Skip a module whose `target/dokka` has no `index.html` (an aggregator `pom` module with no sources).
- CodeQL keeps `autobuild` (Step 3b): it builds a Maven reactor with Kotlin sources correctly.

### Gradle (`language: kotlin`, `buildTool: gradle`)

A Gradle build has no `mvn site`, Surefire/Failsafe or `report-aggregate`; the equivalents come from the
`build-logic/` convention plugins `iru-setup-java-springboot-pom` writes (`iru.integration-test` registers
`integrationTest` over `**/*IT*` while `test` excludes it; `iru.coverage` + the `coverage` project's
`jacoco-report-aggregation` produce `testCodeCoverageReport`; `iru.quality` applies detekt, ktlint and Dokka). The
template below is the `ci.tests: full` / `ci.pages: yes` / `sonar.mode` ≠ `none` shape with every optional step
present; apply the same variant rules as the Maven template (drop what the manifest/survey rules out):

```yaml
name: Build

on:
  push:
    branches: [ <integration-branch>, <main-branch> ]
  pull_request:
    branches: [ <integration-branch>, <main-branch> ]

concurrency:
  group: build-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  build:
    name: Build, test and analyse
    runs-on: ubuntu-latest
    steps:
      - name: Check out code
        uses: actions/checkout@v7
        with:
          # Sonar needs full history to attribute issues to blame data.
          fetch-depth: 0

      - name: Set up JDK <java-version>
        uses: actions/setup-java@v6
        with:
          distribution: temurin
          java-version: <java-version>

      - name: Set up Gradle
        # Caches the Gradle User Home (dependencies, wrapper distribution) and validates the committed wrapper
        # jar's checksum. cache-provider: basic is the MIT-licensed actions/cache-backed provider; the v6 default
        # ("enhanced") is a proprietary component governed by the Gradle Technologies Terms of Use (free for public
        # repositories, a free preview for private ones). Switching to it is the repository owner's call, not
        # something to accept silently on their behalf.
        uses: gradle/actions/setup-gradle@v6
        with:
          cache-provider: basic

      # Only when the manifest's frontend: hilla — same reasoning and ordering as the Maven template: the Vaadin
      # Gradle plugin's vaadinPrepareFrontend/vaadinBuildFrontend tasks need Node on PATH.
      - name: Set up Node
        uses: actions/setup-node@v7
        with:
          node-version: 24
          cache: npm
          cache-dependency-path: <web-module>/package-lock.json

      - name: Build and unit tests
        # `test` excludes **/*IT* (iru.integration-test convention), so nothing here needs Docker.
        # -Pvaadin.productionMode=true -Pvaadin.ci.build=true only when frontend: hilla — the Gradle plugin reads
        # both as Gradle properties (vaadin.ci.build makes it run `npm ci`, never rewriting the lock file).
        # Pass the same two flags to every later ./gradlew call in this job too, or Gradle sees different
        # inputs and re-runs the frontend tasks in development mode. vaadinPrepareFrontend is named explicitly
        # because a plain `build` doesn't depend on it — the frontend unit-test step below needs its output.
        # Without frontend: hilla the command is just `./gradlew build -x integrationTest`.
        run: ./gradlew :boot:vaadinPrepareFrontend build -x integrationTest -Pvaadin.productionMode=true -Pvaadin.ci.build=true

      - name: Integration tests
        # ci.tests: full only. *IT classes start the Testcontainers/compose stack; Docker is available on
        # ubuntu-latest runners.
        run: ./gradlew integrationTest

      - name: Aggregated coverage report
        # jacoco-report-aggregation in the coverage project: one XML over every module's test (and, with
        # ci.tests: full, integrationTest) execution data — the file Sonar reads.
        run: ./gradlew :coverage:testCodeCoverageReport

      # Only when the manifest's frontend: hilla, and after the Gradle build for the same vite.generated.ts reason
      # as the Maven template (its helpers live under <web-module>/build/ once vaadinPrepareFrontend has run).
      - name: Frontend unit tests and coverage
        working-directory: <web-module>
        run: |
          npm ci
          npx vitest run --coverage

      # Only when frontend: hilla, ci.tests: full, and the web module has a playwright.config.ts (written by
      # iru-setup-java-springboot-hilla). Runs the Playwright component tests against the standalone Vite gallery
      # in the same job (no extra runner); captures land in .ui-screenshots/ per the catalog's UI contract.
      - name: Frontend UI tests
        working-directory: <web-module>
        env:
          CI: "true"
          UI_SCREENSHOTS_DIR: ${{ github.workspace }}/.ui-screenshots
        run: |
          npx playwright install --with-deps chromium
          npx playwright test

      - name: Upload UI screenshots
        if: always()
        uses: actions/upload-artifact@v7
        with:
          name: ui-screenshots
          path: .ui-screenshots/
          retention-days: 7
          if-no-files-found: ignore

      - name: Static analysis (detekt + ktlint)
        # Already part of `check` (hence of `build` above); run explicitly with --continue so one tool's failure
        # still yields the other's report, and so the reports exist before the Sonar step reads them.
        run: ./gradlew detekt ktlintCheck --continue

      - name: Run SonarCloud analysis
        # Only present when sonar.mode isn't `none`. The org.sonarqube plugin's `sonar` task reads SONAR_TOKEN
        # from the environment. Skipped on pull requests from forks, where SONAR_TOKEN is not available.
        if: ${{ github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
        run: ./gradlew sonar

      - name: Upload test reports
        if: always()
        uses: actions/upload-artifact@v7
        with:
          name: test-reports
          path: |
            **/build/test-results/**
            **/build/reports/tests/**
            **/build/reports/detekt/**
            **/build/reports/ktlint/**
            coverage/build/reports/jacoco/testCodeCoverageReport/**
            <web-module>/coverage/**
          retention-days: 7

  docs:
    name: Build and publish documentation
    needs: build
    if: github.ref == 'refs/heads/<main-branch>' && github.event_name == 'push'
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Check out code
        uses: actions/checkout@v7

      - name: Set up JDK <java-version>
        uses: actions/setup-java@v6
        with:
          distribution: temurin
          java-version: <java-version>

      - name: Set up Gradle
        uses: gradle/actions/setup-gradle@v6
        with:
          cache-provider: basic

      - name: Install Node
        uses: actions/setup-node@v7
        with:
          node-version: 24
          cache: npm
          cache-dependency-path: |
            docs/package-lock.json
            apis/messaging/docs/package-lock.json
            apis/graphql-server/docs/package-lock.json

      - name: Generate KDoc and API documentation
        # dokkaGeneratePublicationHtml is Dokka 2's HTML task; <api-doc-tasks> are the non-npm API documentation
        # tasks the survey found (OpenAPI html2, protoc-gen-doc) — they write <module>/build/generated-docs/.
        run: ./gradlew dokkaGeneratePublicationHtml <api-doc-tasks>

      - name: Generate AsyncAPI documentation
        if: hashFiles('apis/messaging/docs/package.json') != ''
        working-directory: apis/messaging/docs
        env:
          ASYNCAPI_METRICS_CONFIG_PATH: .asyncapi-analytics
        run: |
          npm ci --no-audit --no-fund
          out="$GITHUB_WORKSPACE/build/generated-docs/messaging"
          for spec in ../*-async-api-v*.yaml; do
            v="$(basename "$spec" .yaml | sed -e 's/.*-async-api-//')"
            npx asyncapi validate "$spec"
            npx asyncapi generate fromTemplate "$spec" @asyncapi/html-template \
              -o "$out/$v" --force-write -p singleFile=true
          done

      - name: Generate GraphQL documentation
        if: hashFiles('apis/graphql-server/docs/package.json') != ''
        working-directory: apis/graphql-server/docs
        run: |
          npm ci --no-audit --no-fund
          out="$GITHUB_WORKSPACE/build/generated-docs/graphql-server"
          for sdl in ../*-v*.graphqls; do
            v="$(basename "$sdl" .graphqls | sed -e 's/.*-\(v[0-9]*\)$/\1/')"
            npx spectaql "spectaql-$v.yml" --target-dir "$out/$v"
            node build-voyager.mjs "$sdl" "$out/$v/voyager" "GraphQL schema $v"
          done

      - name: Install Antora
        working-directory: docs
        run: npm ci

      - name: Build Antora docs
        working-directory: docs
        run: npx antora antora-playbook.yml

      - name: Merge documentation
        run: |
          touch ./docs/build/site/.nojekyll
          cp -r ./docs/build/site ./doc
          mkdir -p ./doc/api/kdoc
          # Dokka: the root-aggregated site when the root project aggregates, otherwise one site per module
          # under doc/api/kdoc/<module-path>/.
          if [ -f ./build/dokka/html/index.html ]; then
            cp -r ./build/dokka/html/. ./doc/api/kdoc/
          else
            while IFS= read -r dir; do
              module="$(dirname "$(dirname "$(dirname "$dir")")")"; module="${module#./}"
              mkdir -p "./doc/api/kdoc/$module" && cp -r "$dir"/. "./doc/api/kdoc/$module/"
            done < <(find . -type d -path '*/build/dokka/html' -not -path './node_modules/*' -not -path './build-logic/*')
          fi
          # Generated API documentation — same merge as the Maven template, from build/ instead of target/.
          while IFS= read -r root; do
            cp -r "$root"/. ./doc/api/
          done < <(find . -type d -path '*/build/generated-docs' -not -path './node_modules/*')

      - name: Deploy to GitHub Pages
        if: success()
        uses: crazy-max/ghaction-github-pages@v5
        with:
          target_branch: gh-pages
          build_dir: ./doc
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Gradle-specific variant rules, on top of the Maven template's:

- **`ci.tests: unit`** — drop the `Integration tests` step (the `Build and unit tests` step already excludes
  `integrationTest`), so the aggregate covers unit tests only; add the same one-line "integration tests run locally
  only (`./gradlew integrationTest`)" comment at the top of the job. Verify against the survey that no Docker-needing
  test class escapes the `**/*IT*` pattern into `test`, and flag it by name if one does.
- **`ci.pages: no`**, **`sonar.mode: none`**, **`frontend` ≠ `hilla`**, no `apis/messaging/` or
  `apis/graphql-server/docs/` — exactly as for Maven (drop the `-Pvaadin.*` flags along with the Node steps, and
  the `SONAR_TOKEN` env along with the Sonar step).
- **Sonar wiring** — the `sonar` task only exists when `iru-setup-java-springboot-pom` applied `org.sonarqube` in the
  root `build.gradle.kts` (it does so when `sonar.mode` isn't `none`); check for it the way Step 0 checks the pom,
  including that `sonar.coverage.jacoco.xmlReportPaths` points at the aggregated XML and
  `sonar.kotlin.detekt.reportPaths`/`sonar.kotlin.ktlint.reportPaths` at the reports the quality step writes.
- **No `mvn site`** — Gradle has no site equivalent; the test and coverage HTML reports travel in the `build` job's
  `test-reports` artifact instead of being published. Say so in the report, so nobody looks for `mvn-site/` on the
  published site.
- **Never `gradle`, always `./gradlew`** — the wrapper pins the Gradle version the build was verified with, and
  `setup-gradle` validates its checksum.

## Step 2 — `deploy.yml`

```yaml
name: Deploy

on:
  workflow_dispatch:
    inputs:
      environment:
        description: Target environment
        required: true
        type: choice
        options: [ dev, prod ]        # from the infra/envs/* directories found in Step 0
      image_tag:
        description: Image tag to deploy (defaults to the commit SHA)
        required: false
        type: string

concurrency:
  # Never let two deploys to the same environment interleave.
  group: deploy-${{ inputs.environment }}
  cancel-in-progress: false

permissions:
  contents: read
  id-token: write        # required for OIDC; this is the whole reason no access key is needed
  packages: write

jobs:
  deploy:
    name: Deploy to ${{ inputs.environment }}
    runs-on: ubuntu-latest
    # The GitHub Environment is where the approval gate and the environment-scoped secrets live.
    environment: ${{ inputs.environment }}
    steps:
      - name: Check out code
        uses: actions/checkout@v7

      - name: Set up JDK <java-version>
        uses: actions/setup-java@v6
        with:
          distribution: temurin
          java-version: <java-version>
          cache: maven

      - name: Resolve image tag
        id: meta
        run: echo "tag=${{ inputs.image_tag || github.sha }}" >> "$GITHUB_OUTPUT"

      # --- Cloud authentication: keyless, via OIDC. No stored access key. ---
      # AWS variant:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}
      # Google Cloud variant (use instead of the above):
      # - uses: google-github-actions/auth@v3
      #   with:
      #     workload_identity_provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
      #     service_account: ${{ secrets.GCP_DEPLOY_SERVICE_ACCOUNT }}

      - name: Build and push the container image
        # spring-boot:build-image uses Cloud Native Buildpacks — no Dockerfile to maintain, and the
        # resulting image is layered so unchanged dependencies aren't re-pushed.
        run: |
          mvn -B -ntp -pl boot -am spring-boot:build-image -DskipTests \
            -Dspring-boot.build-image.imageName=${{ vars.IMAGE_REPOSITORY }}:${{ steps.meta.outputs.tag }} \
            -Dspring-boot.build-image.publish=true \
            -Ddocker.publishRegistry.username=${{ secrets.REGISTRY_USERNAME }} \
            -Ddocker.publishRegistry.password=${{ secrets.REGISTRY_PASSWORD }}

      - name: Set up OpenTofu
        uses: opentofu/setup-opentofu@v2

      - name: Tofu init
        working-directory: infra/envs/${{ inputs.environment }}
        run: tofu init

      - name: Tofu plan
        working-directory: infra/envs/${{ inputs.environment }}
        run: tofu plan -input=false -var="image_tag=${{ steps.meta.outputs.tag }}" -out=tfplan

      - name: Tofu apply
        working-directory: infra/envs/${{ inputs.environment }}
        run: tofu apply -input=false -auto-approve tfplan

      - name: Smoke check
        # Fail the deploy if the service never becomes healthy, rather than reporting success
        # because `apply` returned 0.
        run: |
          url="$(cd infra/envs/${{ inputs.environment }} && tofu output -raw service_health_url)"
          for _ in $(seq 1 30); do
            if curl -fsS "$url" >/dev/null; then echo "Healthy"; exit 0; fi
            sleep 10
          done
          echo "::error::Service did not become healthy within 5 minutes"
          exit 1
```

Points to resolve from the survey rather than copy blindly:

- **Registry authentication.** For ECR, prefer `aws-actions/amazon-ecr-login` (which yields a short-lived token
  from the OIDC session) over `REGISTRY_USERNAME`/`REGISTRY_PASSWORD` secrets; for Artifact Registry, prefer
  `gcloud auth configure-docker`. Use the OIDC-derived credential where the registry supports it and drop the
  username/password secrets entirely — fewer stored secrets is strictly better. Only keep them for a third-party
  registry.
- **`apply` runs the plan file** that was just produced, so what's applied is exactly what was planned. Don't
  replace this with a bare `tofu apply -auto-approve`.
- **The approval gate lives in the GitHub Environment**, not in the YAML. Tell the user to configure required
  reviewers on the `prod` environment — without that, `workflow_dispatch` on `prod` is one click from anyone with
  write access.
- If deploying on release publication is wanted, add `release: types: [published]` to the triggers with the
  environment pinned to `prod`, and note that this removes the manual gate unless the Environment requires
  reviewers.
- Buildpacks need a container daemon; `ubuntu-latest` has one. If the org requires a daemonless build, note Jib as
  the alternative and that it needs different plugin configuration in `boot/pom.xml`.

### Gradle variant (`buildTool: gradle`)

Same workflow, triggers, concurrency, permissions, OIDC and OpenTofu steps; replace the JDK, tag and image steps
with:

```yaml
      - name: Set up JDK <java-version>
        uses: actions/setup-java@v6
        with:
          distribution: temurin
          java-version: <java-version>

      - name: Set up Gradle
        uses: gradle/actions/setup-gradle@v6
        with:
          cache-provider: basic

      - name: Resolve image tag
        id: meta
        # The project version lives in gradle.properties (`version=`), the Gradle counterpart of the pom's
        # <version>. The default tag is <version>-<short sha>: traceable to the release and still unique per
        # commit, so an immutable-tag registry policy never rejects a redeploy of a SNAPSHOT.
        env:
          # Passed through env, not interpolated into the script, so a crafted input can't inject shell.
          IMAGE_TAG_INPUT: ${{ inputs.image_tag }}
        run: |
          version="$(sed -n 's/^version[[:space:]]*=[[:space:]]*//p' gradle.properties | tr -d '[:space:]')"
          if [ -z "$version" ]; then
            echo "::error::No version= line in gradle.properties"; exit 1
          fi
          echo "version=$version" >> "$GITHUB_OUTPUT"
          echo "tag=${IMAGE_TAG_INPUT:-${version}-${GITHUB_SHA::7}}" >> "$GITHUB_OUTPUT"

      - name: Log in to the container registry
        # bootBuildImage has no command-line options for registry credentials; when none are configured in
        # boot/build.gradle.kts it falls back to ~/.docker/config.json, which this step writes. For ECR or
        # Artifact Registry use the OIDC-derived login instead (aws-actions/amazon-ecr-login, or
        # `gcloud auth configure-docker`) and drop the two REGISTRY_* secrets.
        uses: docker/login-action@v4
        with:
          registry: ${{ vars.IMAGE_REGISTRY }}
          username: ${{ secrets.REGISTRY_USERNAME }}
          password: ${{ secrets.REGISTRY_PASSWORD }}

      - name: Build and push the container image
        # bootBuildImage is the Gradle counterpart of spring-boot:build-image — Cloud Native Buildpacks, layered
        # image, no Dockerfile. --imageName/--publishImage are the plugin's own command-line options.
        run: |
          ./gradlew :boot:bootBuildImage -x test -x integrationTest \
            --imageName=${{ vars.IMAGE_REPOSITORY }}:${{ steps.meta.outputs.tag }} \
            --publishImage
```

- `:boot:` is the Gradle path of the `boot` project from `settings.gradle.kts` — use the real one from the survey.
- `bootBuildImage` depends on `bootJar` (written to `boot/build/libs/`, not `boot/target/`); nothing else in the
  workflow reads the jar, so no path changes elsewhere.
- With `frontend: hilla`, add `-Pvaadin.productionMode=true -Pvaadin.ci.build=true` and the `Set up Node` step from
  Step 1's Gradle template, or the image ships a development-mode frontend.
- `IMAGE_REGISTRY` (the registry host, e.g. `ghcr.io` or `<account>.dkr.ecr.<region>.amazonaws.com`) is one more
  environment variable than the Maven variant needs — list it in Step 4's table only for the Gradle variant.

## Step 2b — Rolling `deploy.yml` (only when rolling deployments are enabled)

Generated **instead of** the single-job `deploy.yml` of Step 2 when rolling is enabled (`deploy.rolling.enabled: true`
in the manifest, or `rolling: yes` in `args`) **and** `strategy` is `blue-green`, `canary` or `linear`. With rolling
disabled or absent, Step 2's template is used byte-for-byte as written — nothing in this Step applies.

Design (decided by the platform skill, repeated here because the workflows implement it): **the workflow drives the
traffic shifting and the rollout state lives in the cloud** — never in GitHub (no artifacts, variables or run
history are read back). Every run first asks the platform "is a rollout in progress, what is the current split?", so
`deploy.yml`, `promote.yml` and `undeploy.yml` are stateless and safe to re-run. A new version ("green", the
*candidate*) always deploys at **0 % production traffic**, is smoke-tested on its candidate URL, and is then shifted
in steps while the previous version ("blue", the *stable* one) keeps running for rollback.

`strategy: rolling` has no second environment and no traffic split. For it, generate Step 2's single-job template
plus **one extra step after `Tofu apply`** that waits for the runtime's native rolling update to settle and fail the
deploy if it does not — ECS: `aws ecs wait services-stable --cluster "${{ vars.ECS_CLUSTER }}" --services "${{ vars.ECS_SERVICE }}"`
(the deployment circuit breaker the platform skill enables rolls back on failure); Cloud Run: nothing extra (the
revision only takes traffic once healthy); Kubernetes: `kubectl rollout status deployment/<name> --timeout=10m`. It
generates **no `promote.yml`** (there is nothing to promote between) and `advance` is `auto`. Rollback is weaker: re-run
`deploy.yml` with the previous `image_tag`. Say so in the report.

### Contract with the platform skill

The templates below rely on exactly this from `iru-setup-java-springboot-platform` (its "Rolling deployments"
section); if the generated `infra/` disagrees, fix the mismatch in the generated workflows and report it:

| Runtime | The workflow assumes |
|---|---|
| ECS Fargate | `tofu output -json rollout_target_groups` = `{"blue":{"name":…,"arn":…},"green":{…}}`; `rollout_alarm_names` = JSON list; slot services named `<ECS_SERVICE>-blue` / `<ECS_SERVICE>-green` in cluster `ECS_CLUSTER`; per-slot variables `image_tag_blue` / `image_tag_green`; the production listener is the only listener whose default action forwards to **both** target groups (the test listener forwards to green only) and has `ignore_changes` on its weights; the deploy role may also call `elasticloadbalancing:AddTags`, `RemoveTags`, `DescribeTags` on that listener (the workflow stores *which slot is the candidate* in a listener tag `rollout-candidate` — a 50/50 split cannot say which side is stable) |
| Cloud Run | a service `CLOUD_RUN_SERVICE` whose `traffic` is pinned and `ignore_changes`-d, so a new revision gets 0 %; the deploy identity may update traffic and tags on that service; `image_tag` variable |
| EKS / GKE Autopilot | `rollout_name` = an Argo `Rollout` in namespace `K8S_NAMESPACE` whose **first steps are `setWeight: 0` then `pause: {}`** (the new version is deployed at 0 %, and the first `promote` moves it to step 1) for `canary`, or `autoPromotionEnabled: false` for `blueGreen`; `image_tag` variable; for `auto`/`hybrid` an `AnalysisTemplate` referenced from the steps |

### The rollout functions (runtime-specific, embedded in `deploy.yml` and `promote.yml` and `undeploy.yml`)

Both workflows (and `undeploy.yml`) need the same logic, so each writes the same shell library to
`$RUNNER_TEMP/rollout.sh` in a step called `Load rollout functions` and `source`s it. Use the block for the detected
runtime and embed it **verbatim and identically** in every file. Shared contract of every block: `rollout_init`
(read the state from the cloud), `rollout_active` (a rollout is in progress), `rollout_current` (candidate percent),
`rollout_set <pct>`, `rollout_gate_ok`, `rollout_finalise`, `rollout_rollback` (restore 100 % stable, retire the
candidate), `rollout_abort` (restore 100 % stable, leave the candidate running for debugging). The runtime-independent
helpers `next_step` and `gate_wait` are identical everywhere and come first. The workflow passes `STEPS` (the
manifest's steps, space-separated, e.g. `10 50 100`), `BAKE_MINUTES`, `ADVANCE` and `TF_DIR` as `env`.

```bash
set -euo pipefail

# --- runtime independent -----------------------------------------------------------------------------------------
# Smallest manifest step strictly greater than $1 (empty when $1 is already the last step).
next_step() {
  for s in $STEPS; do
    if [ "$s" -gt "$1" ]; then echo "$s"; return; fi
  done
}

# Hold the gate for BAKE_MINUTES: fail on the first breach, succeed only if it is still healthy at the end.
gate_wait() {
  local end=$(( $(date +%s) + BAKE_MINUTES * 60 ))
  while [ "$(date +%s)" -lt "$end" ]; do
    rollout_gate_ok || { echo "::error::Metric gate breached"; return 1; }
    sleep 30
  done
  rollout_gate_ok
}

tfout() { tofu -chdir="$TF_DIR" output -json "$1"; }
```

**AWS — ECS Fargate** (needs `ECS_CLUSTER`, `ECS_SERVICE` environment variables):

```bash
# --- ECS Fargate: weighted target groups on the production ALB listener ------------------------------------------
slot_arn() { if [ "$1" = blue ]; then echo "$BLUE_ARN"; else echo "$GREEN_ARN"; fi; }
other_slot() { if [ "$1" = blue ]; then echo green; else echo blue; fi; }

weight_of() {
  aws elbv2 describe-listeners --listener-arns "$LISTENER" --output json |
    jq -r --arg tg "$1" '[.Listeners[0].DefaultActions[0].ForwardConfig.TargetGroups[] | select(.TargetGroupArn == $tg) | .Weight][0] // 0'
}

rollout_init() {
  TGS="$(tfout rollout_target_groups)"
  ALARMS="$(tfout rollout_alarm_names)"
  BLUE_ARN="$(jq -r .blue.arn <<<"$TGS")"
  GREEN_ARN="$(jq -r .green.arn <<<"$TGS")"
  local lb
  lb="$(aws elbv2 describe-target-groups --target-group-arns "$BLUE_ARN" --query 'TargetGroups[0].LoadBalancerArns[0]' --output text)"
  # The production listener is the one forwarding to BOTH target groups (the test listener forwards to green only).
  LISTENER="$(aws elbv2 describe-listeners --load-balancer-arn "$lb" --output json |
    jq -r --arg b "$BLUE_ARN" --arg g "$GREEN_ARN" '
      [.Listeners[]
       | select(([.DefaultActions[0].ForwardConfig.TargetGroups[]?.TargetGroupArn] | index($b)) != null
            and ([.DefaultActions[0].ForwardConfig.TargetGroups[]?.TargetGroupArn] | index($g)) != null)
       | .ListenerArn][0] // empty')"
  [ -n "$LISTENER" ] || { echo "::error::Production listener not found"; return 1; }
  CAND_SLOT="$(aws elbv2 describe-tags --resource-arns "$LISTENER" \
    --query "TagDescriptions[0].Tags[?Key=='rollout-candidate'].Value | [0]" --output text)"
  if [ "$CAND_SLOT" = None ]; then CAND_SLOT=""; fi
  if [ -n "$CAND_SLOT" ]; then
    STABLE_SLOT="$(other_slot "$CAND_SLOT")"
  elif [ "$(weight_of "$BLUE_ARN")" -ge 50 ]; then
    STABLE_SLOT=blue
  else
    STABLE_SLOT=green
  fi
  IDLE_SLOT="$(other_slot "$STABLE_SLOT")"
}

rollout_active() { [ -n "$CAND_SLOT" ]; }
rollout_current() { if rollout_active; then weight_of "$(slot_arn "$CAND_SLOT")"; else echo 0; fi; }

# Called by deploy.yml before it touches anything, so a second deploy cannot start while this one is unfinished.
rollout_mark_candidate() {
  CAND_SLOT="$IDLE_SLOT"
  aws elbv2 add-tags --resource-arns "$LISTENER" --tags "Key=rollout-candidate,Value=$CAND_SLOT"
}

# Image tag a slot's ECS service is running now (the stable slot keeps its tag across the candidate's apply).
slot_image_tag() {
  local td
  td="$(aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE-$1" --query 'services[0].taskDefinition' --output text)"
  aws ecs describe-task-definition --task-definition "$td" --query 'taskDefinition.containerDefinitions[0].image' --output text | sed 's/.*://'
}

rollout_set() {
  local p="$1"
  aws elbv2 modify-listener --listener-arn "$LISTENER" --default-actions "$(jq -nc \
    --arg c "$(slot_arn "$CAND_SLOT")" --arg s "$(slot_arn "$STABLE_SLOT")" --argjson p "$p" \
    '[{Type: "forward", ForwardConfig: {TargetGroups: [{TargetGroupArn: $s, Weight: (100 - $p)}, {TargetGroupArn: $c, Weight: $p}]}}]')" >/dev/null
}

# Healthy = none of the alarms exported as rollout_alarm_names is in ALARM. INSUFFICIENT_DATA is reported but not a
# breach (a candidate at a few percent may have no datapoints yet); the alarms should use treat_missing_data = notBreaching.
rollout_gate_ok() {
  local names state
  names="$(jq -r '.[]' <<<"$ALARMS")"
  # shellcheck disable=SC2086
  state="$(aws cloudwatch describe-alarms --alarm-names $names --output json)"
  if jq -e '[.MetricAlarms[] | select(.StateValue == "INSUFFICIENT_DATA")] | length > 0' <<<"$state" >/dev/null; then
    echo "::warning::Some rollout alarms report INSUFFICIENT_DATA"
  fi
  ! jq -e '[.MetricAlarms[] | select(.StateValue == "ALARM")] | length > 0' <<<"$state" >/dev/null
}

scale_slot_down() { # scale slot $1 to zero and clear the marker
  aws ecs update-service --cluster "$ECS_CLUSTER" --service "$ECS_SERVICE-$1" --desired-count 0 >/dev/null
  aws elbv2 remove-tags --resource-arns "$LISTENER" --tag-keys rollout-candidate
}

rollout_finalise() { # candidate is now 100 %: retire the old stable slot
  rollout_set 100
  scale_slot_down "$STABLE_SLOT"
}

rollout_rollback() {
  rollout_set 0
  scale_slot_down "$CAND_SLOT"
}

rollout_abort() {
  rollout_set 0
  aws elbv2 remove-tags --resource-arns "$LISTENER" --tag-keys rollout-candidate
}
```

(`scale_slot_down` scales *the slot it is given* to zero and clears the `rollout-candidate` marker: the old stable slot at
finalise, the candidate at rollback.)

**Google Cloud — Cloud Run** (needs `CLOUD_RUN_SERVICE`; `GCP_REGION`, `GCP_PROJECT_ID`; optional `ERROR_RATE_MAX`,
default `0.02`). State is two revision **tags**: `stable` on the revision serving production and `candidate` on the new one.

```bash
# --- Cloud Run: revision tags + traffic percentages ----------------------------------------------------------------
run_describe() { gcloud run services describe "$CLOUD_RUN_SERVICE" --region "$GCP_REGION" --format=json; }

rollout_init() {
  local j
  j="$(run_describe)"
  CAND_REV="$(jq -r '[.status.traffic[]? | select(.tag == "candidate")][0].revisionName // empty' <<<"$j")"
  STABLE_REV="$(jq -r '[.status.traffic[]? | select(.tag == "stable")][0].revisionName // empty' <<<"$j")"
  if [ -z "$STABLE_REV" ]; then # first rollout after a plain deploy: the revision with 100 % is the stable one
    STABLE_REV="$(jq -r '[.status.traffic[]? | select(.percent == 100)][0].revisionName // empty' <<<"$j")"
  fi
}

rollout_active() { [ -n "$CAND_REV" ]; }
rollout_current() { run_describe | jq -r '[.status.traffic[]? | select(.tag == "candidate")][0].percent // 0'; }
rollout_candidate_url() { run_describe | jq -r '[.status.traffic[]? | select(.tag == "candidate")][0].url // empty'; }

# deploy.yml, after `tofu apply` created the new revision at 0 %: tag stable + candidate.
rollout_mark_candidate() {
  CAND_REV="$(gcloud run services describe "$CLOUD_RUN_SERVICE" --region "$GCP_REGION" --format='value(status.latestCreatedRevisionName)')"
  gcloud run services update-traffic "$CLOUD_RUN_SERVICE" --region "$GCP_REGION" \
    --update-tags "stable=$STABLE_REV,candidate=$CAND_REV" >/dev/null
}

rollout_set() {
  local p="$1"
  if [ "$p" -ge 100 ]; then
    gcloud run services update-traffic "$CLOUD_RUN_SERVICE" --region "$GCP_REGION" --to-tags "candidate=100" >/dev/null
  else
    gcloud run services update-traffic "$CLOUD_RUN_SERVICE" --region "$GCP_REGION" --to-tags "candidate=$p,stable=$((100 - p))" >/dev/null
  fi
}

# Healthy = candidate 5xx ratio over the last 5 minutes <= ERROR_RATE_MAX (PromQL on Cloud Monitoring); no traffic = healthy.
rollout_gate_ok() {
  local q ratio
  q="sum(rate(run_googleapis_com:request_count{monitored_resource=\"cloud_run_revision\",service_name=\"$CLOUD_RUN_SERVICE\",revision_name=\"$CAND_REV\",response_code_class=\"5xx\"}[5m])) / sum(rate(run_googleapis_com:request_count{monitored_resource=\"cloud_run_revision\",service_name=\"$CLOUD_RUN_SERVICE\",revision_name=\"$CAND_REV\"}[5m]))"
  ratio="$(curl -fsS -H "Authorization: Bearer $(gcloud auth print-access-token)" \
    --data-urlencode "query=$q" \
    "https://monitoring.googleapis.com/v1/projects/$GCP_PROJECT_ID/location/global/prometheus/api/v1/query" |
    jq -r '.data.result[0].value[1] // "0"')"
  awk -v r="$ratio" -v m="${ERROR_RATE_MAX:-0.02}" 'BEGIN { exit !(r == "NaN" || r + 0 <= m + 0) }'
}

rollout_finalise() {
  gcloud run services update-traffic "$CLOUD_RUN_SERVICE" --region "$GCP_REGION" --to-revisions "$CAND_REV=100" >/dev/null
  gcloud run services update-traffic "$CLOUD_RUN_SERVICE" --region "$GCP_REGION" --remove-tags candidate,stable >/dev/null
  gcloud run services update-traffic "$CLOUD_RUN_SERVICE" --region "$GCP_REGION" --update-tags "stable=$CAND_REV" >/dev/null
}

rollout_rollback() {
  gcloud run services update-traffic "$CLOUD_RUN_SERVICE" --region "$GCP_REGION" --to-revisions "$STABLE_REV=100" >/dev/null
  gcloud run services update-traffic "$CLOUD_RUN_SERVICE" --region "$GCP_REGION" --remove-tags candidate >/dev/null
}

rollout_abort() { rollout_rollback; }
```

**EKS / GKE Autopilot — Argo Rollouts** (needs `K8S_NAMESPACE`; the `kubectl-argo-rollouts` plugin is installed by a
workflow step, see the templates). Percentages are derived from the `Rollout`'s `currentStepIndex`; the analysis
(`AnalysisTemplate`) runs inside the cluster, so the gate is "the Rollout is not Degraded/aborted".

```bash
# --- Kubernetes: Argo Rollouts --------------------------------------------------------------------------------------
rollout_init() {
  ROLLOUT="$(tfout rollout_name | jq -r .)"
  RJ="$(kubectl get rollout "$ROLLOUT" -n "$K8S_NAMESPACE" -o json)"
}

# In progress = paused (or progressing) at a step before the last one, or a blue/green preview waiting for promotion.
rollout_active() {
  RJ="$(kubectl get rollout "$ROLLOUT" -n "$K8S_NAMESPACE" -o json)"
  jq -e '(.status.phase // "") as $p
         | if .spec.strategy.blueGreen != null then $p == "Paused"
           else ((.spec.strategy.canary.steps // []) | length) as $n
                | ($p == "Paused" or $p == "Progressing") and ((.status.currentStepIndex // 0) < $n) end' <<<"$RJ" >/dev/null
}

rollout_current() {
  RJ="$(kubectl get rollout "$ROLLOUT" -n "$K8S_NAMESPACE" -o json)"
  jq -r 'if .spec.strategy.blueGreen != null then (if (.status.phase // "") == "Paused" then 0 else 100 end)
         else ((.spec.strategy.canary.steps // []) as $s | (.status.currentStepIndex // 0) as $i
               | if $i >= ($s | length) then 100 else ([$s[:$i][] | .setWeight | select(. != null)] | last // 0) end) end' <<<"$RJ"
}

# Move to <pct> by promoting step by step (each promote resumes the indefinite pause and stops at the next one).
rollout_set() {
  local p="$1" cur
  if [ "$p" -ge 100 ]; then
    kubectl argo rollouts promote "$ROLLOUT" -n "$K8S_NAMESPACE" --full
    return
  fi
  cur="$(rollout_current)"
  while [ "$cur" -lt "$p" ]; do
    kubectl argo rollouts promote "$ROLLOUT" -n "$K8S_NAMESPACE"
    sleep 5
    cur="$(rollout_current)"
  done
}

rollout_gate_ok() {
  RJ="$(kubectl get rollout "$ROLLOUT" -n "$K8S_NAMESPACE" -o json)"
  jq -e '(.status.phase // "") != "Degraded" and ((.status.abort // false) | not)' <<<"$RJ" >/dev/null
}

rollout_finalise() { kubectl argo rollouts status "$ROLLOUT" -n "$K8S_NAMESPACE" --timeout 15m; }

# `abort` returns traffic to the stable ReplicaSet and scales the new one down; the Rollout reads Degraded until a fixed
# image is deployed (or `kubectl argo rollouts retry`). The next `tofu apply` re-applies the image in the state, so
# fix forward or deploy the previous tag.
rollout_rollback() { kubectl argo rollouts abort "$ROLLOUT" -n "$K8S_NAMESPACE"; }
rollout_abort() { rollout_rollback; }
```

### The staged `deploy.yml`

Maven shown; the Gradle variant swaps only the JDK/Gradle/tag/registry/image steps exactly as in Step 2's Gradle
variant (and publishes the same `tag` job output). The AWS ECS runtime is shown; the other runtimes are the swaps
listed under the template. `<…>` are filled from the survey and manifest; `STEPS`/`BAKE_MINUTES`/`ADVANCE`/
`STRATEGY` are written as literals from `deploy.rolling` — they are not secrets.

```yaml
name: Deploy

on:
  workflow_dispatch:
    inputs:
      environment:
        description: Target environment
        required: true
        type: choice
        options: [ dev, prod ]        # from the infra/envs/* directories found in Step 0
      image_tag:
        description: Image tag to deploy (defaults to the commit SHA)
        required: false
        type: string

concurrency:
  # Shared with promote.yml and undeploy.yml: a deploy, a promotion and a teardown never interleave.
  group: deploy-${{ inputs.environment }}
  cancel-in-progress: false

env:
  TF_DIR: infra/envs/${{ inputs.environment }}
  STRATEGY: <canary>                  # deploy.rolling.strategy
  ADVANCE: <hybrid>                   # deploy.rolling.advance
  STEPS: "<10 50 100>"                # deploy.rolling.steps, space separated (blue-green: "100")
  BAKE_MINUTES: "<10>"                # deploy.rolling.bakeMinutes
  ECS_CLUSTER: ${{ vars.ECS_CLUSTER }}
  ECS_SERVICE: ${{ vars.ECS_SERVICE }}

permissions:
  contents: read
  id-token: write        # required for OIDC; this is the whole reason no access key is needed
  packages: write

jobs:
  build-image:
    name: Build image
    runs-on: ubuntu-latest
    outputs:
      tag: ${{ steps.meta.outputs.tag }}
    environment: ${{ inputs.environment }}
    steps:
      - name: Refuse a production deploy from a non-main branch
        if: inputs.environment == 'prod' && github.ref_name != '<main-branch>'
        run: |
          echo "::error::Production deploys must run from <main-branch>."
          exit 1

      - name: Check out code
        uses: actions/checkout@v7

      - name: Set up JDK <java-version>
        uses: actions/setup-java@v6
        with:
          distribution: temurin
          java-version: <java-version>
          cache: maven

      - name: Resolve image tag
        id: meta
        env:
          IMAGE_TAG_INPUT: ${{ inputs.image_tag }}
        run: echo "tag=${IMAGE_TAG_INPUT:-$GITHUB_SHA}" >> "$GITHUB_OUTPUT"

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}

      - name: Build and push the container image
        # Same image build as Step 2 (registry login rules included).
        run: |
          mvn -B -ntp -pl boot -am spring-boot:build-image -DskipTests \
            -Dspring-boot.build-image.imageName=${{ vars.IMAGE_REPOSITORY }}:${{ steps.meta.outputs.tag }} \
            -Dspring-boot.build-image.publish=true \
            -Ddocker.publishRegistry.username=${{ secrets.REGISTRY_USERNAME }} \
            -Ddocker.publishRegistry.password=${{ secrets.REGISTRY_PASSWORD }}

  deploy-green:
    name: Deploy new version at 0 % traffic
    needs: build-image
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    outputs:
      first_deploy: ${{ steps.apply.outputs.first_deploy }}
      candidate_url: ${{ steps.apply.outputs.candidate_url }}
    steps:
      - name: Check out code
        uses: actions/checkout@v7

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}

      - name: Set up OpenTofu
        uses: opentofu/setup-opentofu@v2

      - name: Load rollout functions
        run: |
          cat > "$RUNNER_TEMP/rollout.sh" <<'ROLLOUT_EOF'
          <the rollout functions block for the runtime, indented to this level>
          ROLLOUT_EOF

      - name: Tofu init
        run: tofu -chdir="$TF_DIR" init

      - name: Plan and apply the new version
        id: apply
        env:
          TAG: ${{ needs.build-image.outputs.tag }}
        run: |
          source "$RUNNER_TEMP/rollout.sh"
          if ! tfout rollout_target_groups >/dev/null 2>&1; then
            # First deploy of this environment: there is no stable version to keep, so apply everything at 100 %.
            echo "first_deploy=true" >> "$GITHUB_OUTPUT"
            tofu -chdir="$TF_DIR" plan -input=false -var="image_tag_blue=$TAG" -var="image_tag_green=$TAG" -out=tfplan
            tofu -chdir="$TF_DIR" apply -input=false -auto-approve tfplan
            exit 0
          fi
          echo "first_deploy=false" >> "$GITHUB_OUTPUT"
          rollout_init
          if rollout_active; then
            echo "::error::A rollout is already in progress. Finish it with promote.yml (next / rollback / abort) first."
            exit 1
          fi
          stable_tag="$(slot_image_tag "$STABLE_SLOT")"
          # Mark the candidate BEFORE changing anything so a concurrent attempt is refused, and so a failed apply is rolled back.
          rollout_mark_candidate
          tofu -chdir="$TF_DIR" plan -input=false \
            -var="image_tag_${STABLE_SLOT}=$stable_tag" -var="image_tag_${IDLE_SLOT}=$TAG" -out=tfplan
          tofu -chdir="$TF_DIR" apply -input=false -auto-approve tfplan
          # The idle slot is scaled to zero between rollouts: bring it to the stable slot's size and wait for it.
          want="$(aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE-$STABLE_SLOT" --query 'services[0].desiredCount' --output text)"
          aws ecs update-service --cluster "$ECS_CLUSTER" --service "$ECS_SERVICE-$IDLE_SLOT" --desired-count "$want" >/dev/null
          aws ecs wait services-stable --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE-$IDLE_SLOT"
          # Guard: the new version must NOT have traffic yet.
          if [ "$(rollout_current)" != "0" ]; then
            echo "::error::Candidate already receives traffic ($(rollout_current) %); aborting."
            exit 1
          fi
          echo "candidate_url=$(tfout rollout_candidate_url | jq -r .)" >> "$GITHUB_OUTPUT"

  smoke-candidate:
    name: Smoke test the candidate
    needs: deploy-green
    if: needs.deploy-green.outputs.first_deploy != 'true'
    runs-on: ubuntu-latest
    steps:
      - name: Smoke check on the candidate URL
        env:
          CANDIDATE_URL: ${{ needs.deploy-green.outputs.candidate_url }}
        run: |
          # The candidate takes no production traffic; this is the only thing exercising it until the first shift.
          for _ in $(seq 1 30); do
            if curl -fsS "$CANDIDATE_URL" >/dev/null; then echo "Candidate healthy"; exit 0; fi
            sleep 10
          done
          echo "::error::Candidate did not become healthy within 5 minutes"
          exit 1

  shift:
    name: Shift traffic
    needs: [ build-image, deploy-green, smoke-candidate ]
    if: needs.deploy-green.outputs.first_deploy != 'true'      # omit this whole job for advance: manual
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}

      - name: Set up OpenTofu
        uses: opentofu/setup-opentofu@v2

      - name: Check out code
        uses: actions/checkout@v7

      - name: Load rollout functions
        run: |
          cat > "$RUNNER_TEMP/rollout.sh" <<'ROLLOUT_EOF'
          <the same rollout functions block>
          ROLLOUT_EOF

      - name: Tofu init
        run: tofu -chdir="$TF_DIR" init

      - name: Shift to the first step and gate it
        run: |
          source "$RUNNER_TEMP/rollout.sh"
          rollout_init
          # advance: auto  -> walk every step, gating each one, then finalise.
          # advance: hybrid-> dev behaves like auto; prod stops after the first gated step and waits for promote.yml.
          walk_all=false
          if [ "$ADVANCE" = auto ] || { [ "$ADVANCE" = hybrid ] && [ "${{ inputs.environment }}" != prod ]; }; then walk_all=true; fi
          pct=0
          while true; do
            nxt="$(next_step "$pct")"
            [ -n "$nxt" ] || break
            rollout_set "$nxt"
            pct="$nxt"
            gate_wait
            if [ "$walk_all" != true ]; then break; fi
          done
          if [ "$pct" -ge 100 ]; then
            rollout_finalise
            echo "### Rollout complete: 100 % on the new version" >> "$GITHUB_STEP_SUMMARY"
          else
            {
              echo "### Rollout paused at ${pct} % — the metric gate passed"
              echo "Run **promote.yml** for \`${{ inputs.environment }}\` with target \`next\` to continue, \`rollback\` to revert."
            } >> "$GITHUB_STEP_SUMMARY"
          fi

  rollback:
    name: Roll back automatically
    needs: [ build-image, deploy-green, smoke-candidate, shift ]
    # A failed deploy, smoke test or gate returns 100 % to the previous version. Omit `shift` from needs for advance: manual.
    if: ${{ always() && (needs.deploy-green.result == 'failure' || needs.smoke-candidate.result == 'failure' || needs.shift.result == 'failure') }}
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}

      - name: Set up OpenTofu
        uses: opentofu/setup-opentofu@v2

      - name: Check out code
        uses: actions/checkout@v7

      - name: Load rollout functions
        run: |
          cat > "$RUNNER_TEMP/rollout.sh" <<'ROLLOUT_EOF'
          <the same rollout functions block>
          ROLLOUT_EOF

      - name: Tofu init
        run: tofu -chdir="$TF_DIR" init

      - name: Restore 100 % on the previous version
        run: |
          source "$RUNNER_TEMP/rollout.sh"
          rollout_init
          if rollout_active; then rollout_rollback; fi
          echo "### Rolled back: 100 % on the previous version" >> "$GITHUB_STEP_SUMMARY"
```

Notes on the template, to apply when generating:

- **`advance: manual`** — omit the `shift` job (and `shift` from `rollback`'s `needs`/`if`) and add a last job
  `announce` (`needs: smoke-candidate`) that writes the candidate URL and "run **promote.yml** with target `next`" to
  `$GITHUB_STEP_SUMMARY`. The run ends with the new version deployed at 0 %.
- **`blue-green`** — `STEPS: "100"`: the shift is a single cutover. With `advance: hybrid` the human confirmation is
  the whole point of the strategy, so on `prod` the cutover must wait for `promote.yml`: add
  `&& inputs.environment != 'prod'` to the `shift` job's `if` and generate the `announce` job (as for `manual`) with
  `if: inputs.environment == 'prod'`; `dev` auto-advances.
- **First deploy** of an environment (no rollout outputs yet) is applied at 100 % and the staged jobs are skipped.
- **Cloud Run** — auth with `google-github-actions/auth@v3` + `google-github-actions/setup-gcloud@v3`; env
  `CLOUD_RUN_SERVICE`, `GCP_REGION`, `GCP_PROJECT_ID`, optional `ERROR_RATE_MAX` from `vars`; the `Plan and apply`
  step passes `-var="image_tag=$TAG"`; after `apply` it calls `rollout_mark_candidate` (the revision exists only
  now), then `echo "candidate_url=$(rollout_candidate_url)"` (fall back to `tfout rollout_candidate_url`) and the same
  0 % guard; there is no slot or ECS scaling code.
- **EKS / GKE** — after cloud auth add `aws eks update-kubeconfig --name "${{ vars.EKS_CLUSTER_NAME }}"` /
  `google-github-actions/get-gke-credentials@v3` (`cluster_name: ${{ vars.GKE_CLUSTER_NAME }}`), install the Argo
  Rollouts kubectl plugin (a **pinned** release from `argoproj/argo-rollouts`, checksum-verified against the
  release's `argo-rollouts-checksums.txt`; resolve the current version live), `-var="image_tag=$TAG"`, and in the
  candidate smoke test use `kubectl run smoke --rm -i --restart=Never --image=curlimages/curl -n "$K8S_NAMESPACE" --
  -fsS "$CANDIDATE_URL"` when the URL is cluster-internal (`*.svc.cluster.local`) because the runner cannot resolve it.
  The Rollout deploys paused at its first step (0 %); `rollout_active` is then true until it is promoted to 100 %.
- Untrusted inputs never reach a shell as `${{ … }}` text: `image_tag` and `target` go through `env`
  (`IMAGE_TAG_INPUT`, `TAG`, `TARGET`); the only `${{ inputs.environment }}` inside scripts is a `choice` input, whose
  value is limited to the generated option list. The Gradle variant keeps its `meta` step as in Step 2.

## Step 2c — `promote.yml` (only when rolling deployments are enabled and `strategy` is not `rolling`)

The human "this step is safe" signal. A separate `workflow_dispatch` workflow — **not** a GitHub Environment
approval: required reviewers on private repositories need GitHub Enterprise, so they cannot be the mechanism on
every plan, and a job waiting for approval would hold a runner open between steps. `promote.yml` is stateless: it
reads the current split from the cloud, validates, moves one step, and ends.

```yaml
name: Promote

on:
  workflow_dispatch:
    inputs:
      environment:
        description: Environment whose rollout to advance
        required: true
        type: choice
        options: [ dev, prod ]        # same list as deploy.yml
      target:
        description: next = the next step; a percentage = that step; rollback = back to 100 % on the previous version; abort = same, keeping the candidate for debugging
        required: true
        type: choice
        default: next
        options: [ next, "10", "50", "100", rollback, abort ]   # percentages = deploy.rolling.steps, in order

concurrency:
  group: deploy-${{ inputs.environment }}     # same group as deploy.yml and undeploy.yml
  cancel-in-progress: false

env:
  TF_DIR: infra/envs/${{ inputs.environment }}
  ADVANCE: <hybrid>
  STEPS: "<10 50 100>"
  BAKE_MINUTES: "<10>"
  ECS_CLUSTER: ${{ vars.ECS_CLUSTER }}
  ECS_SERVICE: ${{ vars.ECS_SERVICE }}

permissions:
  contents: read
  id-token: write

jobs:
  promote:
    name: Promote ${{ inputs.environment }} (${{ inputs.target }})
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - name: Refuse a production promotion from a non-main branch
        if: inputs.environment == 'prod' && github.ref_name != '<main-branch>'
        run: |
          echo "::error::Production promotions must run from <main-branch>."
          exit 1

      - name: Check out code
        uses: actions/checkout@v7

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}

      - name: Set up OpenTofu
        uses: opentofu/setup-opentofu@v2

      - name: Load rollout functions
        run: |
          cat > "$RUNNER_TEMP/rollout.sh" <<'ROLLOUT_EOF'
          <the same rollout functions block>
          ROLLOUT_EOF

      - name: Tofu init
        run: tofu -chdir="$TF_DIR" init

      - name: Advance, hold or revert the rollout
        env:
          TARGET: ${{ inputs.target }}
        run: |
          source "$RUNNER_TEMP/rollout.sh"
          summary() { echo "$1" | tee -a "$GITHUB_STEP_SUMMARY"; }
          rollout_init

          case "$TARGET" in
            rollback|abort)
              if ! rollout_active; then summary "No rollout in progress for ${{ inputs.environment }}; nothing to do."; exit 0; fi
              "rollout_$TARGET"
              summary "### ${TARGET^}: 100 % on the previous version (${{ inputs.environment }})"
              exit 0 ;;
          esac

          if ! rollout_active; then
            echo "::error::No rollout in progress for ${{ inputs.environment }}. Run deploy.yml first."
            exit 1
          fi
          pct="$(rollout_current)"
          nxt="$(next_step "$pct")"
          if [ "$TARGET" = next ]; then target="$nxt"; else target="$TARGET"; fi
          [ -n "$target" ] || { echo "::error::Already at the last step ($pct %)."; exit 1; }
          case " $STEPS " in *" $target "*) ;; *) echo "::error::$target % is not one of the configured steps ($STEPS)."; exit 1 ;; esac
          # Never skip past the configured steps: going forward is only allowed to the very next one.
          if [ "$target" -gt "$pct" ] && [ "$target" != "$nxt" ]; then
            echo "::error::Refusing to jump from $pct % to $target %; the next step is $nxt %."
            exit 1
          fi

          # The previous step must have held its gate before anything moves forward (auto and hybrid).
          if [ "$ADVANCE" != manual ] && [ "$target" -gt "$pct" ]; then
            if ! rollout_gate_ok; then
              rollout_rollback
              summary "### Gate failing at ${pct} % — rolled back to 100 % on the previous version"
              exit 1
            fi
          fi

          rollout_set "$target"
          # Hold the new step for the soak time; a breach rolls back automatically (auto and hybrid).
          if [ "$ADVANCE" != manual ] && ! gate_wait; then
            rollout_rollback
            summary "### Gate breached at ${target} % — rolled back to 100 % on the previous version"
            exit 1
          fi
          if [ "$target" -ge 100 ]; then
            rollout_finalise
            summary "### Rollout complete: 100 % on the new version (${{ inputs.environment }})"
          else
            summary "### Now at ${target} % (${{ inputs.environment }}) — run promote.yml again with target \`next\` when it looks safe"
          fi
```

- The `target` options are generated from the manifest: `next`, every step as a quoted string, `rollback`, `abort`
  (choice inputs are static, so a changed `steps` list means regenerating this file — that is what
  `/iru-springboot-rolling-deployments` does).
- Use the same cloud auth / kubeconfig / plugin steps as `deploy.yml` for the detected runtime (Cloud Run, EKS/GKE).
  The `env:` block carries the same runtime variables as `deploy.yml`.
- **Do not add `needs`-style approval or Environment reviewers here** — see Step 4's advice on who may dispatch it.

## Step 3 — `undeploy.yml`

This workflow destroys things, so its guards are the feature, not the ceremony.

```yaml
name: Undeploy

on:
  workflow_dispatch:
    inputs:
      environment:
        description: Environment to undeploy
        required: true
        type: choice
        options: [ dev, prod ]
      mode:
        description: stop = scale the service to zero (infrastructure kept); destroy = delete all infrastructure
        required: true
        type: choice
        options: [ stop, destroy ]
        default: stop
      confirmation:
        description: Type the environment name exactly to confirm
        required: true
        type: string

concurrency:
  group: deploy-${{ inputs.environment }}     # same group as deploy.yml: never both at once
  cancel-in-progress: false

permissions:
  contents: read
  id-token: write

jobs:
  undeploy:
    name: ${{ inputs.mode }} ${{ inputs.environment }}
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - name: Verify the typed confirmation
        # Cheap, and it has stopped a wrong-environment destroy more than once.
        run: |
          if [ "${{ inputs.confirmation }}" != "${{ inputs.environment }}" ]; then
            echo "::error::Confirmation '${{ inputs.confirmation }}' does not match environment '${{ inputs.environment }}'."
            exit 1
          fi

      - name: Check out code
        uses: actions/checkout@v7

      - name: Configure cloud credentials
        # Same OIDC step as deploy.yml
        run: echo "replace with the AWS or Google Cloud OIDC auth action"

      - name: Set up OpenTofu
        uses: opentofu/setup-opentofu@v2

      - name: Tofu init
        working-directory: infra/envs/${{ inputs.environment }}
        run: tofu init

      - name: Stop the service (scale to zero)
        if: inputs.mode == 'stop'
        working-directory: infra/envs/${{ inputs.environment }}
        run: |
          tofu apply -input=false -auto-approve -var="desired_count=0" -var="min_instances=0"

      - name: Show the destroy plan
        if: inputs.mode == 'destroy'
        working-directory: infra/envs/${{ inputs.environment }}
        run: tofu plan -destroy -input=false -out=tfdestroy

      - name: Destroy the environment
        if: inputs.mode == 'destroy'
        working-directory: infra/envs/${{ inputs.environment }}
        run: tofu apply -input=false -auto-approve tfdestroy
```

**When rolling deployments are enabled** (and `strategy` is not `rolling`), change the template as follows — with
rolling off it stays exactly as above:

- It already shares `concurrency: deploy-${{ inputs.environment }}` with `deploy.yml`; `promote.yml` uses the same
  group, so a teardown never interleaves with a deploy or a promotion.
- Add the workflow-level `env:` block (`TF_DIR`, and the runtime variables `ECS_CLUSTER`/`ECS_SERVICE`, or
  `CLOUD_RUN_SERVICE`/`GCP_REGION`/`GCP_PROJECT_ID`, or `K8S_NAMESPACE`) and, after `Tofu init`, two steps — `Load
  rollout functions` (the same block as `deploy.yml`) and **`Reset the rollout to the stable version`**:
  ```yaml
      - name: Reset the rollout to the stable version
        # Never tear down (or scale to zero) an environment that is mid-rollout without first returning all traffic to
        # the stable version: otherwise the "stop" leaves a half-shifted split behind for the next deploy to trip over.
        run: |
          source "$RUNNER_TEMP/rollout.sh"
          if tfout rollout_target_groups >/dev/null 2>&1 || tfout rollout_name >/dev/null 2>&1 || tfout rollout_gate >/dev/null 2>&1; then
            rollout_init
            if rollout_active; then rollout_rollback; fi
          fi
  ```
  (the guard makes it a no-op for an environment that was never deployed or has no rollout outputs).
- For `mode: stop`, scale **both** ECS slot services (`$ECS_SERVICE-blue`, `$ECS_SERVICE-green`) to zero as well as
  passing the `desired_count`/`min_instances` variables the platform skill defines; on Cloud Run and Kubernetes the
  existing variables already cover it.

Additional guards to put in, and to explain in the report:

- **`stop` is the default**, and it's reversible: re-running `deploy.yml` brings the service back with its data
  intact. `destroy` is not reversible.
- **Data-bearing resources should have deletion protection enabled in the OpenTofu configuration**, so `destroy`
  fails on them rather than silently deleting a production database. That means `destroy` on `prod` will error
  until someone deliberately removes the protection — which is correct behaviour, not a bug. Say this explicitly.
- Recommend restricting `prod` in the Environment settings to required reviewers **and** a deployment branch rule,
  so this workflow can't be dispatched from an arbitrary branch (required reviewers on a *private* repository need
  GitHub Enterprise; see "Who may promote" in Step 4).
- Consider omitting `prod` from the `destroy` path entirely for a service holding real data, and say so as a
  recommendation.

## Step 3b — `security.yml` and `.github/dependabot.yml`

The shared security block every workflows skill in this catalog embeds (see `iru-setup-java-github-workflows` for
the library-repository equivalent). Four independent jobs, each gated by the matching `security-*` `args` key from
Step 0 (default on) — omit a job's steps entirely when its flag is `no`, rather than disabling it with a
permanently-false `if:`.

```yaml
name: Security

on:
  push:
    branches: [ <main-branch> ]
  pull_request:
    branches: [ <integration-branch>, <main-branch> ]
  schedule:
    # Weekly, so a CVE disclosed after code was merged is still caught — not just at merge time.
    - cron: '0 6 * * 1'
  workflow_dispatch: {}

permissions:
  contents: read

jobs:
  dependency-review:
    name: Dependency review
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Dependency review
        uses: actions/dependency-review-action@v5

  codeql:
    name: CodeQL analysis
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    strategy:
      fail-fast: false
      matrix:
        # java-kotlin covers the whole reactor. javascript-typescript is added here whenever the manifest's
        # frontend: hilla — iru-setup-java-springboot-hilla scaffolds real TS/TSX source under
        # <web-module>/src/main/frontend/ for CodeQL to actually analyse.
        language: [ java-kotlin, javascript-typescript ]  # drop javascript-typescript when frontend: none
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Set up JDK <java-version>
        uses: actions/setup-java@v6
        with:
          distribution: temurin
          java-version: <java-version>
          cache: maven
      - name: Initialize CodeQL
        uses: github/codeql-action/init@v4
        with:
          languages: ${{ matrix.language }}
      - name: Autobuild
        uses: github/codeql-action/autobuild@v4
      - name: Perform CodeQL analysis
        uses: github/codeql-action/analyze@v4

  osv-scanner:
    name: OSV-Scanner
    permissions:
      contents: read
      security-events: write
    uses: google/osv-scanner-action/.github/workflows/osv-scanner-reusable.yml@v2.7.0
    with:
      scan-args: |-
        --recursive
        ./

  gitleaks:
    name: Secret scan (gitleaks)
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: Check out code
        uses: actions/checkout@v7
        with:
          # gitleaks needs full history to scan commits already merged, not just the current tree.
          fetch-depth: 0
      - name: Run gitleaks
        uses: gitleaks/gitleaks-action@v3
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Drop whichever `jobs:` entries the matching `security-*` flag turned off — a job that never runs because its own
condition is always false is dead YAML, same reasoning as the Sonar step above. If all four are off, still write
`security.yml` with a comment explaining it currently declares no jobs would be more confusing than simply not
writing the file — in that case, skip `security.yml` entirely and say so in Step 6's report.

**Kotlin + Maven** — the template as written. The `java-kotlin` CodeQL language covers Kotlin, and `autobuild`
compiles a Maven reactor (Kotlin included, since `kotlin-maven-plugin` compiles in-process). Dependency review
works from the committed poms exactly as for Java.

**Gradle** — three changes, because GitHub's dependency graph can't read Gradle build scripts statically and
CodeQL can't extract Kotlin without a real compilation:

1. **`dependency-submission` job** (generated whenever `security-dependency-review` is on — dependency review has
   nothing to compare without it). It resolves the build's dependency graph with Gradle and submits it to GitHub,
   on pushes (the base snapshot) and on pull requests (the head snapshot the review compares against):

   ```yaml
     dependency-submission:
       name: Submit Gradle dependency graph
       # Needs contents: write, which a pull request from a fork never gets — skipped there.
       if: ${{ github.event_name == 'push' || (github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name == github.repository) }}
       runs-on: ubuntu-latest
       permissions:
         contents: write
       steps:
         - name: Check out code
           uses: actions/checkout@v7
         - name: Set up JDK <java-version>
           uses: actions/setup-java@v6
           with:
             distribution: temurin
             java-version: <java-version>
         - name: Generate and submit dependency graph
           uses: gradle/actions/dependency-submission@v6
           with:
             cache-provider: basic
   ```

   and make `dependency-review` wait for it and tolerate a snapshot still being processed:

   ```yaml
     dependency-review:
       name: Dependency review
       needs: dependency-submission
       # !cancelled(): still runs when the submission job was skipped (fork PR), reviewing whatever graph exists.
       if: ${{ !cancelled() && github.event_name == 'pull_request' }}
       runs-on: ubuntu-latest
       permissions:
         contents: read
         pull-requests: write
       steps:
         - name: Check out code
           uses: actions/checkout@v7
         - name: Dependency review
           uses: actions/dependency-review-action@v5
           with:
             retry-on-snapshot-warnings: true
             retry-on-snapshot-warnings-timeout: 600
   ```

   Also add `push: branches: [ <integration-branch>, <main-branch> ]` (both, not just main) so each base branch a
   pull request targets has a submitted snapshot to compare against.
2. **CodeQL builds manually.** Replace the matrix and the `Autobuild` step with a per-language build mode
   (`build-mode: none` is not an option for Kotlin — CodeQL then skips every Kotlin file with a warning):

   ```yaml
       strategy:
         fail-fast: false
         matrix:
           include:
             - language: java-kotlin
               build-mode: manual
             # frontend: hilla only
             - language: javascript-typescript
               build-mode: none
       steps:
         - name: Check out code
           uses: actions/checkout@v7
         - name: Set up JDK <java-version>
           if: matrix.build-mode == 'manual'
           uses: actions/setup-java@v6
           with:
             distribution: temurin
             java-version: <java-version>
         - name: Set up Gradle
           if: matrix.build-mode == 'manual'
           uses: gradle/actions/setup-gradle@v6
           with:
             cache-provider: basic
         - name: Initialize CodeQL
           uses: github/codeql-action/init@v4
           with:
             languages: ${{ matrix.language }}
             build-mode: ${{ matrix.build-mode }}
         - name: Compile for CodeQL
           if: matrix.build-mode == 'manual'
           # CodeQL only sees what is actually compiled while it traces the build: `clean` + --no-build-cache stop
           # Gradle restoring classes from a cache, --no-daemon keeps the compiler inside the traced process tree,
           # and the in-process Kotlin strategy keeps kotlinc out of the separate Kotlin daemon. No tests, no
           # detekt/ktlint — compilation (main + test sources, including codegen) is all CodeQL needs.
           run: >-
             ./gradlew --no-daemon --no-build-cache clean assemble testClasses
             -Pkotlin.compiler.execution.strategy=in-process
         - name: Perform CodeQL analysis
           uses: github/codeql-action/analyze@v4
           with:
             category: /language:${{ matrix.language }}
   ```

   CodeQL supports a bounded Kotlin range (1.8.0 up to 2.4.x at the time of writing — see
   https://codeql.github.com/docs/codeql-overview/supported-languages-and-frameworks/); if `project.kotlinVersion` is
   newer than the range the live page lists, say so in the report — extraction fails until CodeQL catches up.
3. **Dependabot uses the `gradle` ecosystem** — see below.

`.github/dependabot.yml` is **always** generated, independent of the four flags above — dependency-update PRs and
vulnerability scanning are separate concerns, and this catalog's convention keeps Dependabot on unconditionally:

```yaml
version: 2
updates:
  - package-ecosystem: maven
    directory: "/"
    schedule:
      interval: weekly
    groups:
      maven-dependencies:
        patterns: [ "*" ]

  - package-ecosystem: docker
    # This reactor builds its image with Cloud Native Buildpacks (spring-boot:build-image), so there is
    # normally no Dockerfile — but Dependabot's docker ecosystem also tracks image tags referenced from
    # compose.yaml at the repository root (written by iru-setup-java-springboot-testcontainers), which is
    # what this entry actually keeps current: Postgres/MongoDB/Kafka/etc. and the API-mock image.
    directory: "/"
    schedule:
      interval: weekly
    groups:
      docker-dependencies:
        patterns: [ "*" ]

  # Only when the manifest's `frontend` field isn't `none` (e.g. `hilla`) — directory is the real web module
  # iru-setup-java-springboot-hilla scaffolded the frontend into (survey Step 0; normally "/boot"), since
  # that's where package.json/package-lock.json actually live, never "/" or "/<web-module>/src/main/frontend".
  - package-ecosystem: npm
    directory: "/boot"
    schedule:
      interval: weekly
    groups:
      npm-dependencies:
        patterns: [ "*" ]

  - package-ecosystem: github-actions
    directory: "/"
    schedule:
      interval: weekly
    groups:
      github-actions-dependencies:
        patterns: [ "*" ]
```

Omit the `npm` entry entirely when the manifest's `frontend: none` — an ecosystem entry for a toolchain that
doesn't exist yet gives Dependabot nothing to scan and just adds noise to its config. When `frontend: hilla`, set
`directory` to the actual web module (survey Step 0; `iru-setup-java-springboot-hilla` currently always chooses
`boot`, so `/boot` unless the survey finds otherwise) — `package.json`/`package-lock.json` live at that module's
root next to its `pom.xml`, never inside `src/main/frontend/`. If the repository's Antora
docs (`docs/package.json`) or the AsyncAPI/GraphQL documentation toolchains (`apis/messaging/docs/package.json`,
`apis/graphql-server/docs/package.json`) already have their own `package-lock.json` files, list each as a
separate `npm` entry pointed at its own `directory` regardless of `frontend`, since those are genuinely present on
disk — the `frontend` gate is specifically about a Hilla application frontend, not the documentation toolchains
`iru-setup-java-springboot-apis`/`iru-setup-antora` already manage.

For **`buildTool: gradle`**, replace the `maven` entry with a `gradle` one. Dependabot's Gradle support reads
`gradle/libs.versions.toml` and the build scripts, and also bumps the wrapper (`gradle-wrapper.properties`); the
`build-logic/` included build declares plugin dependencies of its own, so list it as a second directory:

```yaml
  - package-ecosystem: gradle
    directories: [ "/", "/build-logic" ]
    schedule:
      interval: weekly
    groups:
      gradle-dependencies:
        patterns: [ "*" ]
```

Drop `"/build-logic"` if the survey finds no `build-logic/build.gradle.kts`. Kotlin + Maven keeps the `maven` entry.

## Step 4 — Required secrets, variables, and environments

Report these as a table; this skill cannot create them.

| Name | Kind | Purpose |
|---|---|---|
| `SONAR_TOKEN` | repository secret | SonarCloud/SonarQube scan — **only listed when `sonar.mode` isn't `none`**; omit this row entirely for `sonar.mode: none` (for `cloud` on a private/internal repository, note that the SonarCloud project needs a paid plan) |
| `AWS_DEPLOY_ROLE_ARN` | environment secret | OIDC role assumed per environment (AWS) |
| `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_DEPLOY_SERVICE_ACCOUNT` | environment secrets | OIDC identity (Google Cloud) |
| `AWS_REGION` / `GCP_PROJECT_ID`, `GCP_REGION` | environment variables | not secret, but environment-specific |
| `IMAGE_REPOSITORY` | environment variable | the registry path the image is pushed to |
| `IMAGE_REGISTRY` | environment variable | the registry host `docker/login-action` logs in to — **Gradle variant only**, and only while the `REGISTRY_*` secrets below are used |
| `REGISTRY_USERNAME`, `REGISTRY_PASSWORD` | environment secrets | registry push credentials — **only for a third-party registry**; omit both when the image goes to ECR or Artifact Registry through the OIDC-derived login (Step 2) |
| `ECS_CLUSTER`, `ECS_SERVICE` | environment variables | **rolling, ECS only** — the cluster and the base service name (slot services are `<ECS_SERVICE>-blue` / `-green`); must match the platform skill's resources |
| `CLOUD_RUN_SERVICE` | environment variable | **rolling, Cloud Run only** — the service whose revisions are tagged `stable`/`candidate`; reuses `GCP_PROJECT_ID`/`GCP_REGION`; optional `ERROR_RATE_MAX` (default `0.02`) tunes the 5xx gate |
| `EKS_CLUSTER_NAME` or `GKE_CLUSTER_NAME`, `K8S_NAMESPACE` | environment variables | **rolling, Kubernetes only** — kubeconfig and the namespace of the Argo `Rollout` (its name comes from the `rollout_name` output) |
| `<PROVIDER>_API_KEY` | environment secret | LLM provider key, if `stack.ai.enabled` — never in the repository |
| third-party provider tokens (`MONGODB_ATLAS_*`, `CONFLUENT_CLOUD_*`, …) | environment secrets | needed by the OpenTofu providers for managed services outside the cloud account |

`frontend: hilla` needs no new secret or variable of its own — `npm ci`/`npx vitest`/`vaadin:build-frontend` all
run unauthenticated against the public npm registry and Maven Central, so this table is unchanged by it.

`GITHUB_TOKEN` needs no setup and is all four `security.yml` jobs (Step 3b) require — none of `dependency-review`,
CodeQL, OSV-Scanner, or gitleaks need a secret of their own in the free/public-repository tier of each action.
The Gradle variant adds no secret either: `gradle/actions/setup-gradle` and `dependency-submission` use
`GITHUB_TOKEN` (the latter with the job-level `contents: write` shown in Step 3b), and with `cache-provider: basic`
there is no Develocity/Gradle account or access key involved. Kotlin itself (detekt, ktlint, Dokka) needs nothing.
Also required, and easy to miss:

- **A GitHub Environment per deployment environment**, with required reviewers on `prod` where the plan allows it
  (public repositories, or GitHub Pro/Team/Enterprise on private ones — for private repositories on the lower plans
  required reviewers are an Enterprise feature) and a **deployment branch rule on `prod`** limiting it to the main
  branch. The rolling templates also refuse a `prod` run from any other branch themselves, but the branch rule is
  the control that holds.
- **Who may promote (rolling deployments only).** `promote.yml` is a `workflow_dispatch` workflow, so anyone with
  **repository write access** can dispatch it — including `target: 100`, `rollback` and `abort` on `prod`. This is
  deliberately **not** gated by Environment required reviewers (unavailable on private repositories below Enterprise,
  and a job waiting for approval would hold a runner open between steps). Treat that as a **security finding to
  state in the report**: the "this step is safe" signal is as trustworthy as your write-access list. Mitigate by
  restricting `prod` with a deployment branch rule, a ruleset/CODEOWNERS on `.github/workflows/`, keeping write
  access small, and — on a private Enterprise repository — adding required reviewers to the `prod` Environment (the
  `promote` job already declares `environment:`, so it then pauses for approval with no template change). The metric
  gate still runs in `promote.yml`, so a human cannot promote past a failing gate.
- **GitHub Pages** configured to serve from the `gh-pages` branch (Settings → Pages), or the docs job publishes
  into a branch nobody reads — only when `ci.pages: yes`. For a private/internal repository that needs GitHub
  Pro, Team, or Enterprise Cloud, and the site is public unless Enterprise Cloud private Pages access control is
  used. Omit this bullet entirely when `ci.pages: no`.
- For a **private/internal repository**, every run of these workflows consumes the account's included Actions
  minutes (see Step 0) — mention it so the user can watch their usage.
- The **OIDC trust policy** on the cloud side must name this repository *and* the environment. If it's scoped only
  to the repository, any branch can deploy to production — flag this as a real finding if the platform skill's
  output shows a wildcard subject.
- **CodeQL** requires "Code scanning" to be enabled for the repository (Settings → Code security) — the workflow
  uploads results there. **Dependency review** requires Dependency graph to be enabled (on by default for public
  repositories). Both are one-time repository settings this skill cannot flip itself; say so in Step 6's report.

## Step 5 — Validate

- Check every workflow's YAML parses: `gh workflow list` after pushing, or locally with `python3 -c "import
  yaml,sys; yaml.safe_load(open(sys.argv[1]))" .github/workflows/<f>.yml` for each file.
- Confirm every action reference is a current major version, and every secret/variable name used appears in Step
  4's table — a typo'd secret name silently evaluates to empty, which usually surfaces as a confusing
  authentication failure much later.
- Lint every workflow with `actionlint` when it's available (`actionlint`, or `docker run --rm -v "$PWD":/repo -w
  /repo rhysd/actionlint:latest`) — it catches expression, `needs`/`if`, permission and shellcheck errors that a
  plain YAML parse doesn't. Report it as not run, rather than as passing, when neither is available.
- Confirm the Maven commands actually work locally first (`mvn -B -ntp clean verify` — or `mvn -B -ntp clean
  verify -DskipITs` for `ci.tests: unit`, confirming no Docker-dependent test runs in it —, `mvn -B -ntp site
  -DskipTests -Djacoco.skip`, `mvn -B -ntp generate-resources`) — delegate to `iru-gate-runner` for a compact
  result. A workflow whose commands were never run locally is a guess. Kotlin + Maven adds `mvn -B -ntp
  detekt:check ktlint:check` and `mvn -B -ntp dokka:dokka`. Gradle: `./gradlew build -x integrationTest`
  (plus `./gradlew integrationTest` for `ci.tests: full`), `./gradlew :coverage:testCodeCoverageReport` (confirm the
  XML lands where Sonar is configured to read it), `./gradlew detekt ktlintCheck --continue`,
  `./gradlew dokkaGeneratePublicationHtml <api-doc-tasks>`, and `./gradlew --no-daemon --no-build-cache clean
  assemble testClasses` (the CodeQL compile).
- If the GraphQL step was added, run its commands locally too (`npm ci` in `apis/graphql-server/docs`, then
  `spectaql` and `build-voyager.mjs`) and **open both pages in a browser**. SpectaQL's output is server-rendered so
  a wrong SDL path fails loudly, but Voyager renders client-side: a bad introspection payload or a missing
  `voyager.standalone.js` gives a blank page with only a console error, and the workflow reports success.
- If the AsyncAPI step was added, run its commands locally too (`npm ci` in `apis/messaging/docs`, then
  `asyncapi validate` and `asyncapi generate fromTemplate`) and confirm an `index.html` is produced with the AVRO
  field names in it. `asyncapi validate` exits 1 on a malformed document, a `$ref` to a missing `.avsc`, or an
  `.avsc` that isn't valid AVRO — so it is a real gate, not decoration — while an out-of-date `asyncapi:` version
  is only reported as information and exits 0, so a new specification release won't break the pipeline. Note that
  `npm ci` here has failed before on an unpublished transitive dependency of the CLI, so a green run on your
  machine with a warm cache isn't proof CI will install cleanly.
- If the Node/Vitest step was added (`frontend: hilla`), run its commands locally too, **in the same order as the
  workflow**: `mvn -B -ntp clean verify -Pproduction -Dvaadin.ci.build=true` (Gradle: `./gradlew build -x
  integrationTest -Pvaadin.productionMode=true -Pvaadin.ci.build=true`) first, then `npm ci` and
  `npx vitest run --coverage` in the web module. Running the npm/vitest commands before the Maven build fails on
  a module-not-found error from `vite.generated.ts` (it imports compiled helpers under `<web-module>/target/`)
  that has nothing to do with the frontend tests — confirmed while writing `iru-setup-java-springboot-hilla`, and
  the single most likely way this ordering gets silently swapped in a future edit.
- Rolling deployments: lint `deploy.yml` and `promote.yml` with `actionlint` the same way, run `bash -n` on the
  embedded rollout-functions block for the runtime (it is a shell library — `shellcheck` it too when available), and
  read `promote.yml`'s `target` options against the manifest's `steps`. Never trigger `deploy.yml`, `promote.yml` or
  `undeploy.yml` as a test: the first real exercise should be a deploy to `dev` followed by `promote` steps and one
  deliberate `rollback`, watched to completion. Anything that needs a live cloud (the PromQL query endpoint, ALB
  listener discovery, `kubectl argo rollouts` semantics, the tag-based candidate marker) is **unverified** until that
  `dev` rehearsal — report it as such.
- Do **not** trigger `deploy.yml` or `undeploy.yml` as a test. Recommend instead: a dry run of `build.yml` by
  pushing to a throwaway branch with the trigger temporarily widened, and a first `deploy.yml` run against `dev`
  only, watched to completion.
- Check `security.yml` and `.github/dependabot.yml` parse the same way as the other workflows, and confirm every
  `security-*` flag from Step 0 produced exactly the jobs it should — a flag left `no` must mean the job's whole
  entry is absent from the file, not present-but-disabled.

## Step 6 — Report

Summarize: whether this run created the workflows from scratch or updated existing ones, and per file the action
actually taken (**created / updated / replaced / kept as is**) — for every file kept as is, each mismatch with
this run's choices (e.g. still runs integration tests after `ci-tests: unit`, still deploys to Pages after
`pages: no`, still runs a Sonar step after `sonar: none`); the resolved `visibility` and how (args, manifest,
`gh`, or asked), `ci.tests` and `ci.pages` (and whether they were written back to the manifest), plus the
Actions-minutes note for a private/internal repository; the branch names and Java version resolved; the
language/build-tool variant used (`java`+`maven`, `kotlin`+`maven`, or `kotlin`+`gradle`), how it was resolved
(manifest, or the disk overriding it), and — for Gradle — the `setup-gradle` cache provider (`basic`, and that
switching to the default enhanced provider means accepting the Gradle Technologies Terms of Use), the image tag
scheme (`<version>-<short sha>` from `gradle.properties`), whether `dependency-submission` was added, whether Dokka
publishes one aggregated site or one per module under `doc/api/kdoc/`, that no Maven site is published, and whether
`project.kotlinVersion` falls inside CodeQL's supported Kotlin range; whether the
Sonar step was included (and, if so, `sonar.mode` and the resolved organization/project key/host URL) or omitted
because `sonar.mode: none`, and whether the pom's own Sonar wiring matched what Step 0 expected; whether the docs
job's Antora install matches `docs/package.json` (including Kroki); whether the AsyncAPI and GraphQL documentation
steps were included and what they publish under `doc/api/messaging/` and `doc/api/graphql-server/` (and whether
the Voyager graph was part of it); which environments `deploy.yml`/`undeploy.yml` offer and where they came
from; the container-image build approach chosen; which of the four `security.yml` jobs were included versus
omitted (and by which flag), whether the CodeQL matrix includes `javascript-typescript` (and why, per the
manifest's `frontend` field), and whether `.github/dependabot.yml` includes the `npm` ecosystem and at which
`directory` (and why, per the manifest's `frontend` field); when `frontend: hilla`, whether the `Set up Node` and
`Frontend unit tests and coverage` steps were added, the resolved web module and `package-lock.json` path (and
whether it matched or differed from the plan's `src/main/frontend/package-lock.json` assumption — it does differ:
the real path is `<web-module>/package-lock.json`), the `actions/setup-node` major version used (`v7`, confirmed
current against the live GitHub API — no discrepancy found at the time of writing) and whether it matches the
docs job's own `actions/setup-node` version; the full secrets/variables/environments table from Step 4; and any
gap — missing `infra/`, missing Sonar config, missing GitHub Environments, a container stack too large for a
standard runner, Code scanning or Dependency graph not yet enabled for `security.yml`'s jobs to report into, or a
missing `<web-module>/src/main/frontend/` (`frontend: hilla` but `iru-setup-java-springboot-hilla` hasn't run
yet).

Also report the rolling-deployment outcome: **on or off** (and why — `ci: no` forces off), the strategy, advance
mode, `steps`/`bakeMinutes`, the runtime the rollout functions were generated for, the `deploy.yml` shape
(single-job / staged) and the action taken, `promote.yml`'s action (**created / updated / replaced / kept as is /
not generated** — `strategy: rolling` or rolling off — **/ removed**), the new environment variables from Step 4, any
`rollout_*` output the platform skill has not produced yet, the "who may promote" security finding, and which parts
could not be verified without a live cloud.

Warn explicitly:

- **Review all workflows before pushing.** `deploy.yml` and `undeploy.yml` change and destroy real
  infrastructure; a wrong environment name or a missing approval gate has immediate consequences.
- **Configure required reviewers on `prod` before the workflows land on the main branch**, not after — until then,
  anyone with write access can dispatch a production deploy or teardown. With rolling deployments that includes
  `promote.yml`; on plans without Environment reviewers the deployment branch rule and the write-access list are the
  only controls (Step 4, "Who may promote").
- **Verify the OIDC trust policy is scoped to the repository *and* the environment.**
- With `ci.tests: full`, integration tests need Docker on the runner; if the compose stack is too heavy for
  `ubuntu-latest`, the first `build.yml` run will fail on resource exhaustion rather than on a code defect — deal
  with it now if Step 0 flagged it. With `ci.tests: unit`, integration tests run only when someone runs
  `mvn verify` locally — say so plainly.
- Nothing in these files contains a credential, and it must stay that way: every new value goes in as a secret or
  variable reference.
