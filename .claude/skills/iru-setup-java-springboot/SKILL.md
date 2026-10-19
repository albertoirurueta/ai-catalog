---
name: iru-setup-java-springboot
description: >-
  End-to-end bootstrap for a new (or older/partially set-up) Spring Boot service repository built on DDD +
  hexagonal architecture as a multi-module build (`boot`, `application`, `domain`, `infrastructure/*`, `api/*`) —
  in Java (always a Maven reactor) or Kotlin (a Maven reactor, or a Gradle Kotlin DSL multi-project build with a
  `gradle/libs.versions.toml` catalog and `build-logic/` convention plugins). Asks the implementation language
  (Java recommended unless the repository already has Kotlin) and, for Kotlin only, the build tool (Gradle KTS
  recommended for a new repository, Maven for an existing Maven one), resolving the Kotlin version from the one the
  chosen Spring Boot version manages rather than from memory. Collects the project's identity (groupId,
  artifactId, base package), the target cloud (AWS or Google Cloud), the concurrency model (reactive/blocking/both),
  and every technology choice (databases + index/migration tooling, caches, security, Kafka via Spring Cloud
  Stream + AVRO, REST/gRPC/GraphQL servers and clients, the API mocking tool backing those clients in tests —
  Microcks or WireMock — logging, metrics, tracing, Spring AI, dynamic configuration), resolving the latest Spring
  Boot version and validating every dependency id against the live Spring Initializr metadata API
  (`https://start.spring.io/metadata/client`) rather than a hardcoded list. Records all of it in a
  `springboot-stack.yml` manifest (including `project.language`, `project.buildTool`, and `project.kotlinVersion`),
  then orchestrates `iru-setup-java-springboot-pom` (the root build — reactor pom with
  Javadoc/Checkstyle/PMD/SpotBugs for Java or Dokka/detekt/ktlint for Kotlin, plus
  Surefire/Failsafe/JaCoCo/JXR/site/build-info/Sonar, or the Gradle KTS settings/catalog/convention plugins/wrapper
  equivalent), `iru-setup-java-springboot-modules` (module tree, ports/adapters skeleton, configuration),
  `iru-setup-java-springboot-apis` (the `apis/` spec tree plus OpenAPI/protobuf/GraphQL-SDL/AVRO code generation
  and AsyncAPI documentation generation), `iru-setup-java-springboot-testcontainers` (docker compose +
  Testcontainers integration-test harness), `iru-setup-java-springboot-platform` (OpenTofu deployment),
  `iru-setup-java-springboot-github-workflows` (test/publish, deploy and undeploy workflows), and
  `iru-update-java-springboot-documentation` (Antora site with Mermaid + Kroki and the full template page set) —
  each reading the language and build tool from the manifest. Also asks whether the project is open source, the
  GitHub repository's visibility (detected via `gh` when possible), whether GitHub Actions workflows are wanted at
  all (`ci` set to `no` skips the github-workflows sub-skill — build, deploy and undeploy workflows and the
  security block alike), which tests CI runs (`unit` = unit tests only, `full` = plus Testcontainers integration
  tests), whether docs are deployed to GitHub Pages, which SonarCloud/self-hosted SonarQube/no Sonar analysis it
  runs — stating the Actions-minutes, SonarCloud and Pages cost differences for private repositories — and
  whether a Hilla frontend is part of the service — when it is, `iru-setup-java-springboot-hilla` scaffolds the
  Vaadin/Hilla React frontend (BOM, starters, Vaadin build plugin, `src/main/frontend/`, Vitest, ESLint/Prettier)
  into the `boot` module right after `iru-setup-java-springboot-apis` — recording all of it (including a
  `visibility` field and a `ci:` block with `enabled`/`tests`/`pages`) in the manifest for the sub-skills to read.
  Announces up front whether it is setting the repository up from scratch or updating an existing one (with an
  inventory of every component it owns), and each sub-skill then warns and asks Update / Keep as is / Replace per
  pre-existing artifact instead of a blanket stop; only a genuinely incompatible repository (e.g. a Gradle build
  for a Java service, a Groovy-DSL Gradle build, or a single-module build with root sources) gets a hard stop
  question. Enforces Java 21 as a minimum. Invoke as `/iru-setup-java-springboot`, optionally with `args`
  (`key`/`value` lines) to pre-resolve `mode` (`new`/`existing`), `language` (`java`/`kotlin`), `build-tool`
  (`maven`/`gradle`; `gradle` only with Kotlin), `open-source` (`yes`/`no`), `sonar`
  (`cloud`/`self-hosted`/`none`, plus `sonar-organization`/`sonar-project-key`/`sonar-host-url` when set),
  `frontend` (`none`/`hilla`), `visibility` (`public`/`private`/`internal`), `ci` (`yes`/`no`), `ci-tests`
  (`unit`/`full`), `pages` (`yes`/`no`), `rolling-deployments` (`yes`/`no`), `deployment-strategy`
  (`rolling`/`blue-green`/`canary`/`linear`), `advance` (`auto`/`manual`/`hybrid`), and `on-existing`
  (`ask`/`keep`/`update`/`replace`, forwarded to every file-writing sub-skill only when supplied), skipping the
  matching interview question. When CI is on it also asks whether to support blue/green rolling deployments
  (opt-in; default is today's single-job deploy): every deployment then becomes a staged rollout — the new version
  is deployed at 0 % traffic, shifted per the chosen strategy/steps, the old one kept for rollback — advanced
  automatically, manually or by a metric gate plus a human via a generated `promote.yml` workflow; the choice is
  recorded as `deploy.rolling` in the manifest. Use when starting a new
  Spring Boot microservice (Java or Kotlin) from nothing and you want the whole hexagonal build, CI/CD,
  infrastructure-as-code, and documentation scaffold in one pass, instead of running the sub-skills separately and
  re-answering the same questions each time.
model: sonnet
---

# Setup Java Spring Boot Service

Bootstrap a Spring Boot service repository in one pass — from scratch, or by updating a repository that already
has an older or partial setup. This skill is the **interviewer and
orchestrator**: it asks every question exactly once, resolves the Spring Boot version and dependency ids against
the live Spring Initializr API, writes the resolved answers to a `springboot-stack.yml` manifest at the repository
root, and then delegates the actual file generation to seven sub-skills (eight when `frontend: hilla`) that each
read that manifest back.

The architecture is not negotiable — it is what this skill exists to impose:

- **Domain-Driven Design + hexagonal (ports & adapters)**, realised as a **multi-module build**: a **Maven
  multi-module reactor** for Java (Java services are Maven-only in this catalog) and for Kotlin + Maven, or a
  **Gradle Kotlin DSL multi-project build** for Kotlin + Gradle. The language (`project.language`: `java` |
  `kotlin`) and build tool (`project.buildTool`: `maven` | `gradle`) are asked once in Step 3 and recorded in the
  manifest; every sub-skill branches on them.
- **One place declares every dependency and plugin version.** On Maven that is the **root `pom.xml`** — module
  poms list artifacts without `<version>`, inheriting from the root's `<dependencyManagement>`/`<pluginManagement>`.
  On Gradle it is **`gradle/libs.versions.toml`** (the Spring Boot BOM imported via `platform()`), consumed by the
  `build-logic/` convention plugins and the module build files — no version literal anywhere else.
- **Java 21 is the enforced minimum** (Maven: `maven.compiler.release`, `java.version`, and a
  `maven-enforcer-plugin` `requireJavaVersion` rule; Gradle: the JDK toolchain `languageVersion` set by the
  `iru.kotlin-library` convention plugin). Never generate a project below 21, even if Spring Initializr's own
  default is lower — as of this writing its default `javaVersion` is `17`, which this skill overrides.

## Module layout this skill imposes

`<a>` below is the project `artifactId`; directory names are the short forms. The **artifactId** and
**Packaging** columns apply to Maven builds (Java, or Kotlin + Maven); the **Gradle project path** column applies
to Kotlin + Gradle builds, where `settings.gradle.kts` sets `rootProject.name = "<a>"` and `include(...)`s one
project per module directory, its `:`-path mirroring the directory tree. Aggregator directories are plain parent
projects on Gradle (no build file of their own needed).

| Directory | artifactId | Packaging | Gradle project path | May depend on |
|---|---|---|---|---|
| `.` | `<a>-parent` | `pom` | root (`<a>`) | — (declares all versions) |
| `domain/` | `<a>-domain` | `jar` | `:domain` | nothing in this project |
| `application/` | `<a>-application` | `jar` | `:application` | `domain` |
| `infrastructure/` | `<a>-infrastructure` | `pom` | `:infrastructure` | — (aggregator) |
| `infrastructure/database/` | `<a>-infrastructure-database` | `pom` | `:infrastructure:database` | — (aggregator) |
| `infrastructure/database/<engine>/` | `<a>-infrastructure-database-<engine>` | `jar` | `:infrastructure:database:<engine>` | `domain` |
| `infrastructure/configuration/` | `<a>-infrastructure-configuration` | `jar` | `:infrastructure:configuration` | `domain` |
| `infrastructure/clients/` | `<a>-infrastructure-clients` | `pom` | `:infrastructure:clients` | — (aggregator) |
| `infrastructure/clients/<name>/` | `<a>-infrastructure-clients-<name>` | `jar` | `:infrastructure:clients:<name>` | `domain` |
| `infrastructure/producers/` | `<a>-infrastructure-producers` | `jar` | `:infrastructure:producers` | `domain` |
| `infrastructure/metrics/` | `<a>-infrastructure-metrics` | `jar` | `:infrastructure:metrics` | `domain` |
| `api/` | `<a>-api` | `pom` | `:api` | — (aggregator) |
| `api/rest-server/` | `<a>-api-rest-server` | `jar` | `:api:rest-server` | `application`, `domain` |
| `api/grpc-server/` | `<a>-api-grpc-server` | `jar` | `:api:grpc-server` | `application`, `domain` |
| `api/graphql-server/` | `<a>-api-graphql-server` | `jar` | `:api:graphql-server` | `application`, `domain` |
| `api/consumers/` | `<a>-api-consumers` | `jar` | `:api:consumers` | `application`, `domain` |
| `boot/` | `<a>-boot` | `jar` | `:boot` | every other module |
| `coverage/` | `<a>-coverage` | `pom` | `:coverage` (`jacoco-report-aggregation`) | every other module (test-scope, aggregation only) |

The dependency direction is enforced by `maven-enforcer-plugin` `banned-dependencies` plus an ArchUnit test on
Maven, and by an ArchUnit test alone on Gradle (module dependencies declared with `project(":...")` exactly per the
table) — ArchUnit reads bytecode, so it works the same for Kotlin. Sources live in `src/main/java`/`src/test/java`
for Java and `src/main/kotlin`/`src/test/kotlin` for Kotlin.

Only the modules the user's technology choices actually call for are created — a project with no gRPC gets no
`api/grpc-server/`, no GraphQL gets no `api/graphql-server/`, and no Kafka gets no `infrastructure/producers/` or
`api/consumers/`. `domain`, `application`, `boot`, and `coverage` are always created.

`apis/` at the repository root is **not** a Maven module or Gradle project — it holds the API contracts
(`apis/rest-server/`, `apis/grpc-server/`, `apis/graphql-server/`, `apis/rest-client/<name>/`,
`apis/grpc-client/<name>/`, `apis/graphql-client/<name>/`, `apis/messaging/` — AVRO schemas *and* the AsyncAPI
specification describing the topics that carry them) that the code-generation and documentation generators read.
See `iru-setup-java-springboot-apis`.

## Step 0 — Parse inputs, detect the setup mode, and check the repository is a safe starting point

This skill can be invoked stand-alone (`/iru-setup-java-springboot`) or driven by another orchestrator, so parse
`args` first, as `key: value` lines, one per line, e.g.:

```
mode: new
language: kotlin
build-tool: gradle
open-source: yes
sonar: cloud
sonar-organization: example-github
sonar-project-key: example_orders-service
sonar-host-url: https://sonarcloud.io
frontend: none
visibility: public
ci: yes
ci-tests: full
pages: yes
rolling-deployments: yes
deployment-strategy: canary
advance: hybrid
on-existing: ask
```

Recognized keys: `mode` (`new`/`existing`), `language` (`java`/`kotlin`), `build-tool` (`maven`/`gradle`),
`open-source` (`yes`/`no`), `sonar` (`cloud`/`self-hosted`/`none`), and
— only when `sonar` is `cloud` or `self-hosted` — `sonar-organization`, `sonar-project-key`, `sonar-host-url`, plus
`frontend` (`none`/`hilla`), `accessibility` (`enforce`/`report`/`off`/`none`, only meaningful with `frontend: hilla`),
`visibility` (`public`/`private`/`internal`), `ci` (`yes`/`no`), `ci-tests`
(`unit`/`full`, only meaningful when `ci: yes`), `pages` (`yes`/`no`, only meaningful when `ci: yes`), and
`rolling-deployments` (`yes`/`no`, only meaningful when `ci: yes`), `deployment-strategy`
(`rolling`/`blue-green`/`canary`/`linear`) and `advance` (`auto`/`manual`/`hybrid`) — both only meaningful with
`rolling-deployments: yes` — and `on-existing` (`ask`/`keep`/`update`/`replace`, default `ask`). Optional extras
`steps` (comma list of percentages) and `bake-minutes` override the Step 3c defaults. Every key found here is
resolved — skip the matching question in Step 3, 3b or 3c. If `args` is absent or doesn't look like this format, treat everything as unset and ask
normally.

Validate the language/build-tool pair before anything else: `build-tool: gradle` together with `language: java` is
**rejected** — say that a Java Spring Boot service is Maven-only in this catalog and ask (`AskUserQuestion`)
whether to switch to **Kotlin + Gradle** or to **Java + Maven**; never proceed with Java on Gradle. `build-tool:
gradle` with no `language` implies `language: kotlin` (say so). `language: java` with no `build-tool` resolves
`build-tool: maven` without asking. `on-existing` is never asked: it exists for scripted runs, and this skill forwards it to its sub-skills
**only** when it arrived here via `args` — otherwise every sub-skill asks per artifact itself.

**Detect the mode.** `mode` from `args` wins; otherwise a root `pom.xml`, `settings.gradle.kts` or
`build.gradle.kts` means `existing`, and so does **any** other artifact this run owns being present (it is an
update for that component even when there's no root build yet).

**Detect the existing build's language and tool** (used to pre-select Step 3's answers, and by the hard-stop check
below): Kotlin is present when there are `src/**/kotlin/` directories or `*.kt` files outside `build/`/`target/`,
a `kotlin-maven-plugin` in any `pom.xml`, or `kotlin("jvm")`/`org.jetbrains.kotlin.jvm` in any `*.gradle.kts`
or `gradle/libs.versions.toml`. The build tool is Maven when a root `pom.xml` exists, Gradle Kotlin DSL when
`settings.gradle.kts`/`build.gradle.kts` exist, and **Gradle Groovy DSL** when only `settings.gradle`/
`build.gradle` exist. Record what you found (e.g. "existing Maven reactor, Kotlin sources present").
Then, before asking anything else, print a short **Setup mode** statement:

- `mode: new` → "Setting up this repository **from scratch** — no prior setup found."
- `mode: existing` → "**Updating an existing repository** — prior setup found:" followed by an inventory table of
  every component this run owns, each marked **absent / present / partial** with the evidence (file paths):

  | Component | Owner | Evidence to look for |
  |---|---|---|
  | Manifest | this skill | `springboot-stack.yml` |
  | Root build + module builds | `iru-setup-java-springboot-pom` | Maven: `pom.xml`, `*/pom.xml`; Gradle: `settings.gradle.kts`, `build.gradle.kts`, `*/build.gradle.kts`, `gradle/libs.versions.toml`, `build-logic/`, `gradlew`/`gradlew.bat`/`gradle/wrapper/` (partial: modules listed but missing on disk, or vice versa) |
  | Module tree / source skeleton | `iru-setup-java-springboot-modules` | `domain/`, `application/`, `boot/`, `infrastructure/*`, `api/*`, `coverage/`, `application*.yml` |
  | API contracts + generators | `iru-setup-java-springboot-apis` | `apis/**` |
  | Hilla frontend (only when `frontend: hilla`) | `iru-setup-java-springboot-hilla` | `boot/src/main/frontend/`, `boot/package.json`, `vitest.config.ts` |
  | Compose stack + IT harness | `iru-setup-java-springboot-testcontainers` | `compose.yaml`/`docker-compose.yml`, the IT base class |
  | OpenTofu platform | `iru-setup-java-springboot-platform` | `infra/**` |
  | Workflows + security block | `iru-setup-java-springboot-github-workflows` | each of `.github/workflows/build.yml`, `deploy.yml`, `promote.yml` (only when rolling deployments are enabled), `undeploy.yml`, `security.yml`, and `.github/dependabot.yml` |
  | Antora docs | `iru-update-java-springboot-documentation` | `docs/antora.yml`, `docs/antora-playbook.yml`, `docs/modules/ROOT/` |
  | Sonar config | `iru-setup-java-springboot-pom` | `sonar.*` properties / `sonar-maven-plugin` in `pom.xml`, or the `org.sonarqube` plugin / `sonar {}` block in the root `build.gradle.kts` |
  | `detekt.yml` (Kotlin only) | `iru-setup-java-springboot-pom` | the file |
  | `.gitignore` | `iru-setup-java-gitignore` | `.gitignore` |
  | `README.md` / `CHANGELOG.md` | `iru-setup-readme` / `iru-setup-changelog` | the files |
  | `checkstyle.xml` (Java only) / `LICENSE` | this skill (Step 9) | the files |

  Then: "For each component that already exists you'll be asked whether to keep it, update it, or replace it."
  Each sub-skill asks that itself, per artifact it owns, when it runs (unless `on-existing` was forwarded) — this
  skill does not ask the same question again on its behalf.

**Hard stop only for a genuinely incompatible repository.** The root build is incompatible when it is not
something this multi-module build can be laid over:

- a **Gradle build when the language is Java** — `language: java` from `args`, or Step 3's answer once known (a
  Java Spring Boot service is Maven-only in this catalog);
- a **Gradle Groovy DSL build** (`settings.gradle`/`build.gradle` without `.kts`) for any language — the Kotlin
  path generates Kotlin DSL only;
- a **Maven build when `build-tool: gradle`** was requested (or a Gradle KTS build when `build-tool: maven` was) —
  switching build tools is a migration, not an update;
- a **single-module build with its own sources at the root** — a `pom.xml` that is a `jar`/`war` project with
  `src/main/java`/`src/main/kotlin` at the root, or a `build.gradle.kts` applying the Spring Boot plugin with
  `src/main/kotlin` at the root (re-parenting it under a multi-module build would move or overwrite real code).

When the language isn't resolved yet (no `args`), an existing Gradle KTS build simply pre-selects Kotlin + Gradle
in Step 3; re-apply this check right after Step 3 if the user then picks Java (or a different build tool). For an
incompatible build, use `AskUserQuestion` to ask **Stop (Recommended)** — "end now, nothing written; this
repository's build can't host a DDD/hexagonal multi-module build without a manual migration" — or **Continue
anyway** — "the sub-skills will still ask per file, but expect them to propose replacing the root build and to
leave the existing root sources orphaned outside every module". This applies even when `mode: existing` came via
`args`. An existing `pom`-packaged reactor (from this skill or similar, Java or Kotlin) is **not** incompatible,
and neither is an existing Gradle Kotlin DSL multi-project build when the language is Kotlin — both are normal
update runs.

- If `springboot-stack.yml` already exists, read it and offer its values as the defaults for every question below,
  so a re-run is a cheap "add one more database/client" pass rather than a full re-interview. Whether the manifest
  itself is then rewritten is asked in Step 6, not here.
- Verify prerequisites and report any that are missing before asking anything (a missing one is not a hard stop —
  the generated files are still correct, they just can't be verified in Step 10):
  `java -version` (must be 21+), `mvn -v` (Maven builds), `docker info` (needed by Testcontainers), `curl --version`,
  `git rev-parse --show-toplevel`. For a Gradle build also check `gradle --version` — optional: the build
  sub-skill generates the Gradle wrapper with a local `gradle` if present, else through Docker
  (`gradle:<tag>` image), else asks the user; afterwards every command runs through `./gradlew`. Since the build
  tool may only be known after Step 3, check the Maven/Gradle prerequisites again then if they weren't yet.

## Step 1 — Resolve Spring Boot versions and the dependency catalogue from the live API

**Never rely on remembered Spring Boot version numbers, starter artifact ids, or Initializr dependency ids.**
Boot renames artifacts across major versions (in Boot 4.x, `spring-boot-starter-web` became
`spring-boot-starter-webmvc`, the Testcontainers modules became `testcontainers-<engine>`, and every starter
gained a matching `spring-boot-starter-<x>-test` module), and Initializr's dependency catalogue changes with it.
Fetch the truth instead:

```bash
curl -s https://start.spring.io/metadata/client -H 'Accept: application/json' -o /tmp/initializr.json
```

From that JSON, extract and keep for the rest of this run:

- `bootVersion.default` — the current GA release; this is what you offer the user.
- `bootVersion.values[]` — the full list. Entries ending in `.BUILD-SNAPSHOT` or containing `-M`/`-RC` are
  pre-release; never offer one as the default, and if the user picks one, warn that it isn't production-ready.
- `javaVersion.values[]` — the language levels this Initializr accepts. Filter to `>= 21`.
- `dependencies.values[].values[]` — every valid dependency, each with `id`, `name`, `description`, and a
  compatibility range. **This is the authoritative id list.** Step 4's mapping table gives the ids observed at the
  time of writing; for every id you intend to send, confirm it appears in this list, and if it doesn't, find the
  replacement by matching on the human-readable `name` instead of guessing a new id. Report any id you couldn't
  resolve rather than silently dropping the capability.

If the API is unreachable (offline, proxy, firewall), stop and tell the user — do not fall back to hardcoded
version numbers and artifact names. This skill's correctness depends on that call.

Then use `AskUserQuestion` to confirm:

- **Spring Boot version** — offer `bootVersion.default` as the recommended choice, the previous GA line as the
  conservative alternative, and "other (specify)".
- **Java version** — offer `21` as the default and the highest available LTS (e.g. `25`) as the alternative. If
  the user asks for anything below 21, refuse that value, explain that this catalog enforces 21 as a minimum, and
  re-ask. Note that Java 25+ may not yet be supported by every third-party plugin in the reactor, so `21` stays
  the safe recommendation.

## Step 2 — Collect the project identity

Ask in plain conversation (these are free-text fields, not bounded choices):

- **groupId** — e.g. `com.example`.
- **artifactId** — e.g. `orders-service`. Used as the `<a>` prefix for every module artifactId.
- **version** — default `0.0.1-SNAPSHOT`.
- **Base package** — e.g. `com.example.orders` (the same for Java and Kotlin). Need not equal `groupId`. Every module's package is derived
  from it (`<base>.domain`, `<base>.application`, `<base>.infrastructure.database.mongodb`, `<base>.api.rest`, …),
  and `boot`'s `@SpringBootApplication` class lives directly in `<base>`.
- **Service description** — one line; feeds the poms, the README, and the documentation overview page.
- **Developer name / email / organizationUrl** — for the root pom's `<developers>` block.

Derive, don't ask:

- **Owner/repo/host** from `git remote get-url origin` (handles both `git@host:owner/repo.git` and
  `https://host/owner/repo.git`). Feeds `<url>`/`<scm>` in the root pom and the Sonar project key. If there's no
  `origin` remote yet, ask for the intended repository URL.
- **Inception year** from `git log --reverse --format=%ad --date=format:%Y | head -1`, falling back to the current
  year.

## Step 3 — Ask the decisions that shape everything else

Use `AskUserQuestion` for each, skipping any already resolved in Step 0's `args`.

**Language** (`project.language`) — header `Language`:

- **Java** — recommended unless the repository already has Kotlin (Step 0's detection). Always a Maven reactor;
  Checkstyle/PMD/SpotBugs + Javadoc; Lombok + MapStruct.
- **Kotlin** — recommended when Step 0 found Kotlin sources or a Kotlin build plugin. Null-safety, data classes,
  coroutines (`suspend` handlers work on MVC and WebFlux). Built with the `spring` (all-open) and `jpa` (no-arg)
  compiler plugins and `-Xjsr305=strict`; detekt + ktlint instead of Checkstyle/PMD/SpotBugs; Dokka instead of
  Javadoc; JaCoCo, Surefire/Failsafe-style unit vs `*IT` integration split, ArchUnit and Testcontainers unchanged.

**Build tool** (`project.buildTool`) — asked **only when the language is Kotlin**; Java always resolves to `maven`
without asking. Header `Build tool`:

- **Gradle (Kotlin DSL)** — recommended for a new Kotlin repository (and for an existing Gradle KTS build):
  `settings.gradle.kts`, a `gradle/libs.versions.toml` version catalog, `build-logic/` precompiled convention
  plugins (`iru.kotlin-library`, `iru.spring-boot-app`, `iru.quality`, `iru.integration-test`, `iru.coverage`),
  and the Gradle wrapper.
- **Maven** — recommended when the repository already has a Maven build (Kotlin reactor or Java reactor being
  converted): the same reactor and pom-per-module layout as the Java path, with `kotlin-maven-plugin`.

If Step 0 found an existing build, re-apply its hard-stop check now that both answers are known.

**Kotlin version** (`project.kotlinVersion`, only when the language is Kotlin) — resolve, don't ask and don't
remember. The safest source is the `kotlin.version` the chosen Spring Boot version itself manages (its
`spring-boot-dependencies` BOM), which is exactly what Initializr writes into a Kotlin build — so probe Initializr
with a minimal Kotlin build for the Boot version confirmed in Step 1:

```bash
curl -sG https://start.spring.io/pom.xml \
  --data-urlencode 'bootVersion=<boot-version>' \
  -d type=maven-build -d language=kotlin -d javaVersion=<java-version> -d dependencies=web \
  | sed -n 's:.*<kotlin.version>\(.*\)</kotlin.version>.*:\1:p'
```

(Equivalently: `<kotlin.version>` in
`https://repo1.maven.org/maven2/org/springframework/boot/spring-boot-dependencies/<boot-version>/spring-boot-dependencies-<boot-version>.pom`.)
Use that value. Do **not** take the newest Kotlin from Maven Central's `maven-metadata.xml` (`<release>`/`<latest>`
there can be a Beta/RC) or the newest GitHub release: a newer Kotlin line than the one Boot manages may work, but
Boot hasn't been tested against it. If the user explicitly wants a newer stable Kotlin, tell them the Boot-managed
version, warn that the override is untested by Spring Boot, and record their choice. Step 7 cross-checks this value
against the reference build.

**Deployment platform** — this drives `iru-setup-java-springboot-platform`'s whole OpenTofu layout, the dynamic
configuration mechanism in Step 4, and the deploy workflows:

- **Amazon Web Services** — OpenTofu targets ECS Fargate or EKS, with AWS managed data services.
- **Google Cloud** — OpenTofu targets Cloud Run or GKE Autopilot, with Google managed data services.

**Concurrency model** — this decides the starter for every single technology chosen in Step 4, so it must be
settled first:

- **Non-reactive / blocking (Spring MVC on Tomcat)** — recommended default unless there's a concrete reason
  otherwise. Simpler to write, debug, and profile; virtual threads (`spring.threads.virtual.enabled=true` on Java
  21+) already remove most of the thread-per-request scaling argument. Uses the blocking `spring-data-*` starters.
- **Reactive (Spring WebFlux on Netty, Project Reactor)** — choose when the service is predominantly I/O-bound
  fan-out with very high concurrency and every downstream dependency has a reactive driver. Uses the
  `spring-data-*-reactive` starters. With Kotlin, reactive code is usually written as `suspend` functions and
  `Flow` over Reactor — Initializr adds `kotlinx-coroutines-reactor`, `reactor-kotlin-extensions` and
  `kotlinx-coroutines-test` automatically for `webflux` when `language=kotlin`.
- **Both** — a blocking web tier plus reactive clients (or vice versa). Pulls in Tomcat *and* Netty and both
  driver families. Warn the user this is the hardest to reason about: two runtime models coexist, blocking calls
  on a Netty event-loop thread will stall the whole server, and both dependency sets must be kept in sync. Only
  worth it for a genuine migration or a genuinely mixed workload.

Record the answer as `stack.concurrency: blocking | reactive | both`. For every technology below, "the matching
starter" means: blocking → the plain starter; reactive → the `-reactive`/`r2dbc` starter; both → both.

## Step 3b — Open source, visibility, CI, Sonar, and frontend

Resolve these choices **in this order**, skipping any already answered by Step 0's `args` (or offered as a default
from an existing manifest). Use `AskUserQuestion` for each (header ≤ 12 chars, recommended option first). The cost
facts below are per GitHub's current pricing — say so and tell the user to double-check their plan.

- **Open source** (`openSource`) — is this repository open source? Yes / No, asked directly with no default. This
  answer drives the recommended defaults for the visibility and Sonar questions, per this catalog's shared
  convention (see `iru-setup-java-library-repository`).
- **Visibility** (`visibility`) — if the repository has a GitHub remote, detect it with
  `gh repo view --json visibility -q .visibility` (lowercase the `PUBLIC`/`PRIVATE`/`INTERNAL` result) and tell the
  user the detected value; otherwise (no remote yet, `gh` unavailable, not GitHub) ask **Public** / **Private**,
  recommending Public when open source is Yes, otherwise Private. If open source is Yes but visibility is
  `private`/`internal`, warn that this is contradictory (an open-source project's repository is normally public,
  and a private repo forfeits the free-for-public-repos pricing below) and ask which one is right. `internal`
  behaves like `private` for every cost decision below.
- **CI** (`ci.enabled`) — "Generate GitHub Actions workflows (CI/CD) for this repository?"
  - Public: recommend **Yes** — standard GitHub-hosted runners are free for public repositories.
  - Private/internal: still offer **Yes** first, but state that every run consumes the account's included
    minutes — 2,000/month on GitHub Free, 3,000 on Pro and Team, 50,000 on Enterprise Cloud — then is billed per
    minute (Linux 2-core $0.006/min; this stack's workflows all run on Linux runners, so the macOS ~10× and
    Windows ~1.7× multipliers don't apply). Offer **No** — "no workflows: build, test, deploy and release locally;
    re-run `/iru-setup-java-springboot-github-workflows` later to add them".
  - `ci: no` ⇒ Step 8 skips `iru-setup-java-springboot-github-workflows` entirely — **no `build.yml`, and no
    `deploy.yml`/`undeploy.yml` either, so deploying and tearing down the OpenTofu environments becomes a manual
    `tofu apply`/`tofu destroy`**; no `security.yml` and no `.github/dependabot.yml` (the shared security block —
    Dependabot, dependency-review, CodeQL, OSV-Scanner, gitleaks — is skipped with it). `ci-tests` and `pages` are
    not asked.
- **Sonar** (`sonar.mode`) — "Configure SonarCloud / SonarQube and send CI analysis and coverage reports to it?"
  Recommend **SonarCloud** (`cloud`) only when the repository is public **and** open source; otherwise state that
  SonarCloud is free only for public/open-source projects (a private project needs a paid plan) and recommend
  **None** (`none`), offering **self-hosted SonarQube** (`self-hosted`, free Community Build, but you run the
  server) as the second option. When `ci: no`, say plainly that nothing would send reports automatically —
  analysis would only run when someone runs `mvn sonar:sonar` (Gradle: `./gradlew sonar`) manually with a token —
  and recommend `none`; if the user still picks `cloud`/`self-hosted`, the root build still gets its Sonar
  properties/plugin, and Step 11 reports
  that no CI step sends reports. When `cloud` or `self-hosted` is chosen, also collect:
  - `sonar.organization` — for `cloud`, suggest `<owner>-github` (the owner parsed in Step 2) as the default,
    since that's the key SonarCloud assigns by default when an organization is created by importing from GitHub;
    for `self-hosted`, ask only if that server has organizations enabled.
  - `sonar.projectKey` — suggest `<owner>_<repo>` (also from Step 2) as the default for both modes.
  - `sonar.hostUrl` — `https://sonarcloud.io` for `cloud` (confirm rather than silently assume); ask directly for
    `self-hosted`, with no sensible default.
  - When `sonar.mode: none`, leave `organization`/`projectKey`/`hostUrl` unset — `iru-setup-java-springboot-pom`
    and `iru-setup-java-springboot-github-workflows` both read `sonar.mode` and omit every Sonar plugin, property,
    and CI step accordingly.
- **CI tests** (`ci.tests`, only when `ci: yes`) — "Which tests should CI run?"
  - **Unit tests only** (`unit`) — "Unit tests only — Surefire `*Test` on Maven, the `test` task on Gradle
    (cheaper: fewer minutes, faster feedback). `*IT` integration tests (Failsafe / the Gradle `integrationTest`
    task) against the Testcontainers/docker compose stack stay local." Recommend for private/internal
    repositories.
  - **Unit + integration** (`full`) — "Unit tests plus `*IT` integration tests against the Testcontainers stack
    (databases, Kafka + Schema Registry, the API mock, …) — complete verification, considerably more minutes."
    Recommend for public repositories.
- **Pages** (`ci.pages`, only when `ci: yes`) — the build workflow publishes the Antora site, the Maven site (Maven
  builds only) and generated API docs (Javadoc or Dokka) to GitHub Pages.
  - Public: `yes` without asking (state it in Step 11's report).
  - Private/internal: ask — **No (Recommended)** — "CI still builds the docs and uploads them as a workflow
    artifact; nothing is published" — versus **Yes** — "requires GitHub Pro, Team, or Enterprise Cloud (not GitHub
    Free); the site will be **public on the internet** unless you're on Enterprise Cloud with private Pages access
    control".
- **Frontend** (`frontend`) — does this service ship a Hilla frontend alongside the Spring Boot backend? **None**
  (recommended default) or **Hilla**. Recording `frontend: hilla` here drives three downstream sub-skills: Step 8
  runs `iru-setup-java-springboot-hilla` (right after `iru-setup-java-springboot-apis`) to actually scaffold the
  Vaadin/Hilla React frontend into the `boot` module — the Vaadin BOM and `hilla-spring-boot-starter`/
  `vaadin-spring-boot-starter` dependencies, the `vaadin-maven-plugin` execution (the `com.vaadin` Gradle plugin on
  Gradle), `src/main/frontend/`, Vitest,
  and ESLint/Prettier — `iru-setup-java-springboot-pom` adds the root pom's `vaadin.version`
  property/`dependencyManagement` import/`pluginManagement` entry/`production` profile, and
  `iru-setup-java-springboot-github-workflows` adds the `npm`/Node ecosystem to `.github/dependabot.yml` plus the
  `actions/setup-node` and `vitest` steps in `build.yml`. Never silently treat `hilla` as `none` — record what the
  user actually asked for and say so in Step 11's report.
- **Accessibility** (`accessibility`, only when `frontend: hilla`) — "Support accessibility and assistive technologies in the
  frontend?" **Enforce (Recommended)** — violations fail the UI tests; **Report only** — listed, never
  failing; **Off** — no automated checks (accessible coding defaults still apply); **None — opt out entirely** ("no accessibility rules, checks or docs"; written as `accessibility: none`). In `mode: existing`, pre-select from `iru-explore`'s `Accessibility:` line per `iru-setup-repository`'s `reference/accessibility-detection.md` (`present` → Enforce, `partial` → Report only with a mixed-compliance warning, `absent` → None) and never silently flip an existing `.ui-quality.yml` value. The Hilla frontend follows the
  catalog's UI contract (composed components with explicit inputs/events, virtualized lists, Playwright UI tests
  across states, left-to-right/right-to-left and light/dark, screenshots reused by the Antora UI pages, axe-core
  checks); `iru-setup-java-springboot-hilla` writes the choice to `.ui-quality.yml`. With `frontend: none` it is
  neither asked nor recorded.

## Step 3c — Rolling deployments (blue/green)

Asked **only when `ci.enabled: true`** (Step 3b) and not already resolved by `rolling-deployments` in `args` or an
existing manifest's `deploy.rolling`. With `ci: no`, skip the whole step, record nothing, and say plainly that
rolling deployments need the generated workflows (`deploy.yml` drives the rollout and `promote.yml` advances it) —
`/iru-springboot-rolling-deployments enable` can add them later once workflows exist.

Ask (`AskUserQuestion`, header `Rolling`): **"Support blue/green rolling deployments?"**

- **No (Recommended for a `dev`-only or small service)** — today's behaviour: one `deploy.yml` job applies the
  OpenTofu environment and health-checks it. No `promote.yml`, no second environment, no extra cost.
- **Yes** — every deployment becomes a staged rollout: the new version ("green") is deployed at **0 % traffic**,
  smoke-tested on a candidate URL, shifted in steps, and the old version ("blue") is kept for rollback. Adds a
  generated `promote.yml` workflow and rollout infrastructure; blue/green temporarily doubles capacity (cost).

If **Yes**, ask the follow-ups in as few calls as possible (`AskUserQuestion`, max 4 questions per call):

1. **Strategy** (`strategy`, header `Strategy`) — **Canary (Recommended)** (gradual shift through `steps`, e.g.
   10 → 50 → 100 %; "blue/green plus gradual"), **Blue/green** (one cutover from 0 to 100 %, `steps: [100]`),
   **Linear** (equal-sized steps at a fixed interval), **Rolling** (in-place replacement by the runtime's native
   rolling update — no second environment, no traffic split, `advance` limited to `auto`, weaker rollback).
2. **Advancement** (`advance`, header `Advance`) — **Hybrid (Recommended)** (a metric gate must pass, then a human
   confirms through `promote.yml` on `prod`; on `dev` it auto-advances; a failing gate rolls back automatically),
   **Auto** (metric gate only, no human), **Manual** (the run ends after green is deployed; a human runs
   `promote.yml` for every step). Skip this question for strategy `rolling` (resolves to `auto`; say so).
3. **Steps and soak** — unless `steps`/`bake-minutes` came in `args`: confirm the defaults `steps: [10, 50, 100]`
   and `bakeMinutes: 10` for canary/linear (`steps: [100]` for blue/green, no `steps` for rolling), offering
   **Use defaults (Recommended)** or **Customize** (then ask the percentages — ascending, ending at 100 — and the
   soak minutes). `bakeMinutes` is ignored for `advance: manual`.

Validate and flag contradictions rather than generating something that can't work:

- `steps` must be strictly ascending integers in 1–100 ending in 100; `blue-green` is exactly `[100]`.
- `rolling` with `advance: manual` or `hybrid` is contradictory (nothing to promote between) — ask which to change.
- The compute runtime (ECS vs EKS, Cloud Run vs GKE) is chosen later by `iru-setup-java-springboot-platform`, so
  runtime-specific limits are enforced there: the platform skill flags `canary`/`linear`/`blue-green` on ECS Fargate
  without an ALB (an internet-facing or internal ALB is required for weighted target groups) and stops rather than
  generating it. Mention this prerequisite here when `stack.cloud` is `aws`. `rolling` is valid on every runtime.
- When `stack.cloud` is `gcp`, Cloud Run shifts traffic between revisions natively; GKE Autopilot uses Argo
  Rollouts (installed or verified by the platform skill).

Record the answers as the `deploy.rolling` block in Step 6 (see the manifest template). `rolling-deployments: no`
(or an unanswered/skipped step) records `enabled: false`, or omits the block.

## Step 4 — Choose the technologies

Work through the groups below **in order**. For each group, present the options as a formatted list including the
"when this is the right choice" guidance verbatim — that guidance is the point of this step, not decoration —
then ask in plain conversation which ones the user wants (multi-select where noted). Use `AskUserQuestion` only
for the genuinely bounded single-choice sub-questions (migration tooling, SQL engine, dynamic configuration),
since it caps out at four options.

For every accepted choice, add the corresponding Initializr dependency id(s) to a running list, and validate each
id against Step 1's catalogue before it goes in.

The technology choices are the same for every language and build tool. Where this step says a version goes "in
the root pom", read "in the version-declaring file": the root `pom.xml` on Maven, `gradle/libs.versions.toml` on
Gradle.

### 4a — Databases (multi-select, may be none)

- **MongoDB** — good when data fits in single independent documents, the structure changes freely over time, and
  many indexes are needed to search that data. Not for workloads that need real transactional guarantees.
  - ids: `data-mongodb` (blocking) / `data-mongodb-reactive` (reactive).
  - Index and schema-change management is **mandatory**; ask with `AskUserQuestion`:
    - **Flamingock** (recommended) — purpose-built for MongoDB change units, integrates cleanly with Spring Data,
      and is the actively-developed successor to Mongock (which is sunsetting, end-of-life 2026-12-31). Add
      `io.flamingock:flamingock-bom` (import scope in dependency management), `io.flamingock:flamingock-community`,
      `io.flamingock:flamingock-springboot-integration`, and the `io.flamingock:flamingock-processor` annotation
      processor (version in the root pom).
    - **Liquibase for MongoDB** — only worth it when Liquibase is already used for another database in the same
      service and one migration tool for everything is worth more than Flamingock's better MongoDB ergonomics. Add
      `org.liquibase.ext:liquibase-mongodb`.
  - Testcontainers image: `mongo:<pinned-tag>`.
- **Couchbase** — good when data fits in single independent documents, the structure changes freely, and no
  indexes beyond lookup-by-id are needed. Not for workloads needing transactional guarantees. In that specific
  shape it usually outperforms MongoDB.
  - ids: `data-couchbase` / `data-couchbase-reactive`.
  - Index management is mandatory: **Liquibase for Couchbase** (`org.liquibase.ext:liquibase-couchbase`).
  - Testcontainers image: `couchbase/server:<pinned-tag>`.
- **Relational / SQL** — good when data must be structured in a very specific way, aggregation queries run over
  it, or transactional guarantees are mandatory. Generally slower than MongoDB or Couchbase for
  document-shaped access.
  - Engine (`AskUserQuestion`, exactly one): **PostgreSQL** (recommended) or **MariaDB**. If PostgreSQL is
    chosen, note that the `pgvector` extension gives it vector storage, so it can also back Spring AI embeddings
    (see 4h) — and pin the Testcontainers image to `pgvector/pgvector:<pg-tag>` rather than plain `postgres` so
    that stays available.
  - ids: blocking → `data-jpa` + (`postgresql` | `mariadb`); reactive → `data-r2dbc` + (`postgresql` |
    `mariadb`) — Initializr adds the R2DBC driver alongside the JDBC one automatically.
  - Data-model versioning and index creation is mandatory; ask with `AskUserQuestion`:
    - **Liquibase** (recommended default) — id `liquibase`.
    - **Flyway** — id `flyway`.
  - Testcontainers image: `pgvector/pgvector:<tag>` (or `postgres:<tag>` if vectors are definitely not needed) /
    `mariadb:<tag>`.
- **Elasticsearch** — good for full-text search, faceted search (e-commerce), and log aggregation. Almost always
  used *alongside* another database in a CQRS arrangement, not as the system of record — say so explicitly, and
  if it's the only database selected, ask the user to confirm that's intentional.
  - ids: `data-elasticsearch`.
  - Testcontainers image: `docker.elastic.co/elasticsearch/elasticsearch:<tag>`.
- **Neo4j** — good when the relationships between entities matter as much as or more than the entities: fraud
  detection, recommendation engines, social graphs, knowledge graphs, dependency graphs. Typically used alongside
  another database in a CQRS arrangement.
  - ids: `data-neo4j`.
  - Migration management is mandatory: **Liquibase for Neo4j** (`org.liquibase.ext:liquibase-neo4j`).
  - Testcontainers image: `neo4j:<tag>`.
- **Qdrant** — the preferred choice over PostgreSQL + `pgvector` when a large volume of vectors is stored: a
  dedicated vector engine outperforms sharing one PostgreSQL instance between application data and embeddings.
  - ids: `spring-ai-vectordb-qdrant` (Qdrant reaches the service through Spring AI's vector store abstraction).
  - Testcontainers image: `qdrant/qdrant:<tag>`.

### 4b — Caches (multi-select, may be none)

- **Caffeine** — best for a local, per-node cache. Each replica keeps its own copy, so it's ideal for small or
  static, infrequently-changing data. Fastest option, no network hop.
  - ids: `cache` (Spring's cache abstraction). Caffeine itself is not an Initializr dependency — add
    `com.github.ben-manes.caffeine:caffeine` explicitly, with its version in the root pom.
- **Redis** — best for a cache shared across all replicas: large cached datasets, or data that changes often
  enough that every node must see the change at once. Slightly slower than a local cache because of the network
  hop.
  - ids: `data-redis` / `data-redis-reactive`, plus `cache` if `@Cacheable` is wanted on top.
  - Testcontainers image: `redis:<tag>`.

If both are selected, note that the conventional arrangement is a two-level cache (Caffeine in front of Redis)
and that it needs deliberate invalidation design — flag it for the architecture documentation page.

### 4c — Spring Security (yes/no)

Needed when OAuth login flows must be implemented, or endpoints must be properly authorized rather than open.

- ids: `security`, plus `oauth2-resource-server` when the service validates incoming JWTs (the usual case for a
  microservice behind a gateway) and/or `oauth2-client` when it initiates login flows itself. Ask which of the
  two applies; both is valid.

### 4d — Spring Cloud Stream / Kafka (yes/no)

Needed for Kafka messaging — publishing or consuming public or private events. This is the standard tool for
eventual consistency in non-transactional architectures (microservices) and for saga orchestration over public
events.

- ids: `cloud-stream`, `kafka`. Add `kafka-streams` only if the user says they need stateful stream processing.
- AVRO is the message format. `avro-maven-plugin` generates Java classes from the schemas in `apis/messaging/` —
  configured by `iru-setup-java-springboot-apis`.
- The same directory also holds an **AsyncAPI specification** describing the topics, their direction, and which
  message each carries — the messaging equivalent of the OpenAPI spec. It is documentation only (no Java is
  generated from it), rendered to HTML on every build by `@asyncapi/html-template` and published to GitHub Pages
  alongside the REST and gRPC pages.
- Creates the `infrastructure/producers/` module (outbound) and/or the `api/consumers/` module (inbound) — ask
  which directions this service needs; at least one must be true.
- Testcontainers needs both a **Kafka broker** image and a **Confluent Schema Registry** image, since AVRO
  serialization resolves schemas through the registry at runtime.

### 4e — REST server (yes/no)

Needed to serve requests over a REST API.

- ids: `web` (blocking) / `webflux` (reactive) / both. Always add `validation`.
- Contract-first: OpenAPI specs live in `apis/rest-server/`, and `openapi-generator-maven-plugin` generates the
  controller interfaces and DTOs into `api/rest-server/`, plus HTML documentation.

### 4f — gRPC server (yes/no)

Needed to serve requests over gRPC.

- ids: `spring-grpc-server` (Spring Boot 4 ships first-party gRPC support; in older lines this was the separate
  `spring-grpc`/`net.devh` starter — trust Step 1's catalogue). Reactive and blocking service implementations
  use the same starter; the difference is in the generated stub flavour.
- Contract-first: protobuf definitions live in `apis/grpc-server/`, and `protobuf-maven-plugin` generates the
  service base classes and messages into `api/grpc-server/`, plus HTML documentation via `protoc-gen-doc`.

### 4g — GraphQL server (yes/no)

Needed to serve requests over a GraphQL API — one endpoint whose clients choose the fields they want, instead of
one endpoint per resource shape.

- ids: `graphql`, **plus a transport starter**: `web` (blocking) or `webflux` (reactive), matching
  `stack.concurrency`. This pairing is not optional and is the easiest thing to get wrong here:
  `spring-boot-starter-graphql` brings the GraphQL engine and `spring-graphql`, but **no HTTP transport at all** —
  Initializr's `graphql` id alone resolves to `spring-boot-starter-graphql` and `spring-boot-starter-graphql-test`
  and nothing else. Without `web` or `webflux` the application starts and serves no `/graphql` endpoint, which
  looks like a routing bug rather than a missing dependency. If REST (4e) is also enabled, the transport starter is
  already there and isn't added twice.
- Also add `validation`, as for REST — the generated input types carry Bean Validation annotations.
- Creates the `api/graphql-server/` module.
- Contract-first: SDL schema files live in `apis/graphql-server/`, and `graphql-codegen-maven-plugin` generates the
  resolver interfaces and model types into `api/graphql-server/`. As with REST, the generator owns the interfaces
  and the hand-written `@Controller` implements them.
- **The SDL is needed twice**: once at build time by the generator, and once at *runtime* by Spring for GraphQL,
  which loads the schema from `classpath:graphql/**/` (`.graphqls`/`.gqls`) to wire and validate the resolvers. The
  contract lives outside the module, so the build copies it onto the classpath —
  `iru-setup-java-springboot-apis` sets that up. A service whose generated code compiles but whose SDL never
  reached the classpath fails at startup complaining the schema is empty.

### 4h — Clients (multi-select, may be none)

- **REST clients** — needed to call other services' REST APIs. Ask for the **name of each** client (one per
  downstream service, e.g. `payments`, `inventory`); each becomes an
  `infrastructure/clients/<name>/` module and an `apis/rest-client/<name>/` spec directory, with
  `openapi-generator-maven-plugin` generating the client and DTOs.
  - ids: `spring-restclient` (blocking) / `spring-webclient` (reactive).
- **gRPC clients** — needed to call other services' gRPC APIs. Ask for the **name of each**; each becomes an
  `infrastructure/clients/<name>/` module and an `apis/grpc-client/<name>/` spec directory, with
  `protobuf-maven-plugin` generating the stubs.
  - ids: `spring-grpc-client`.
- **GraphQL clients** — needed to call other services' GraphQL APIs. Ask for the **name of each**; each becomes an
  `infrastructure/clients/<name>/` module and an `apis/graphql-client/<name>/` SDL directory, with
  `graphql-codegen-maven-plugin` generating the request/response and projection classes.
  - ids: `graphql` (the same starter as 4g — it carries `HttpGraphQlClient`/`HttpSyncGraphQlClient`, so a service
    that only *consumes* GraphQL still needs it), plus the transport starter for `stack.concurrency` if 4e or 4g
    hasn't already added one.
  - Unlike the REST and gRPC client generators, this one needs a **runtime dependency** alongside the generated
    code — `io.github.kobylynskyi:graphql-java-codegen`, matching the plugin version, which supplies the
    `GraphQLRequest`/`GraphQLResponseProjection` base classes the generated classes extend. Without it the module
    generates fine and then fails to compile.

A single downstream service reached over more than one protocol keeps **one** `infrastructure/clients/<name>/`
module with a generator execution per protocol — the module is named after the service, not the transport.

**If — and only if — at least one client of any kind was named**, ask which API mocking tool the docker compose
stack should run, using `AskUserQuestion`. Integration tests must never call a real downstream service: that
couples this repository's CI to someone else's uptime and makes error-path coverage impossible. Both tools are
driven by the contracts in `apis/rest-client/<name>/`, `apis/grpc-client/<name>/` and
`apis/graphql-client/<name>/`, so neither introduces a second description of the downstream API. Preselect the
default by what was chosen above:

- **Microcks** — the default whenever **any gRPC or GraphQL client** exists, with or without REST clients. It mocks
  REST, gRPC and GraphQL from the same contracts in one container, consuming the OpenAPI spec, the `.proto` and the
  SDL directly, and can later verify the real downstream service against those same contracts.
- **WireMock** — the default when the service has **REST clients only**. Lighter, faster to start, with a
  finer-grained stub DSL for delays and faults. Mention when offering it that a `wiremock-grpc-extension` exists,
  so it isn't a dead end if gRPC arrives later — it just adds a descriptor-set build step at that point. For
  GraphQL it is a weaker fit: every operation is a `POST /graphql`, so stubs have to match on the request body
  rather than on the path, and the SDL isn't consumed at all — the mock and the contract stop being connected,
  which is the property this whole arrangement exists to preserve.

Record the answer as `stack.apiMock`. `iru-setup-java-springboot-testcontainers` adds the container and points
every client's base URL at it; if no client was named, set `stack.apiMock: none` and no mock is added.

### 4i — Observability (ask each; recommend all three)

- **Logging** — needed to get log traces into a centralized server; by default they only go to the local console.
  Add the logging starter and configure structured (JSON) output for deployed profiles while keeping
  human-readable console output for the `local`/`dev` profile. The user can always turn logging off via
  configuration. Recommend it.
- **Metrics** — needed to report technical and functional metrics and get real insight into service behaviour.
  - ids: `actuator`, `prometheus` (Micrometer's Prometheus registry is the backend), optionally `otlp-metrics` if
    metrics should also go out over OTLP.
  - Creates the `infrastructure/metrics/` module: a domain-defined metrics port, implemented here over
    Micrometer, including the tags each metric carries and the mapping from domain entities to tag values.
  - Local execution gets **Prometheus and Grafana** containers in the docker compose stack so metrics are
    actually visible while developing.
- **Tracing** — needed to see how each received request flowed and what response was produced.
  - ids: `distributed-tracing`, `opentelemetry`. (In Boot 4 these resolve to
    `spring-boot-starter-opentelemetry`.)

### 4j — Spring AI (yes/no)

Used to integrate with LLMs — building "agentic" services or MCP servers/clients.

If yes:

1. Warn first that this **requires a paid subscription with an LLM provider, billed separately from any cloud
   spend** — token cost is the user's, not this scaffold's.
2. Offer the providers actually present in Step 1's catalogue. As observed at the time of writing these include:
   Anthropic Claude (`spring-ai-anthropic`), OpenAI (`spring-ai-openai`), Google GenAI
   (`spring-ai-google-genai`), Amazon Bedrock (`spring-ai-bedrock-converse`), Mistral AI (`spring-ai-mistral`),
   DeepSeek (`spring-ai-deepseek`), and Ollama (`spring-ai-ollama`, local models — no subscription needed).
   Present the live list, not this one. If the deployment platform from Step 3 is AWS, mention Bedrock, and if
   it's Google Cloud mention Google GenAI, as the options that authenticate via the platform's own IAM instead of
   a separate API key.
3. If embeddings will be stored, ask for the vector store and keep it consistent with 4a:
   `spring-ai-vectordb-qdrant` (preferred at volume), `spring-ai-vectordb-pgvector` (fine when PostgreSQL is
   already in play and vector volume is modest), or none.
4. Also offer `spring-ai-mcp-server` / `spring-ai-mcp-client` if the service is meant to expose or consume MCP.
5. **Never write an API token into the repository in clear text.** State this explicitly to the user, and record
   it as a required manual step in Step 11's report:
   - The generated configuration references the token only as `${<PROVIDER>_API_KEY}` — an environment variable
     resolved at runtime, with **no default value and no example key committed anywhere**.
   - For local development: export it in the shell, or put it in a `.env` file that is **git-ignored** (this
     skill adds `.env` to `.gitignore`). Never in `application.yml`.
   - For CI: a GitHub Actions secret, exposed to the job as an environment variable.
   - For deployed environments: the platform's secret manager — AWS Secrets Manager or Google Secret Manager —
     injected into the container by the OpenTofu configuration, never baked into the image.
   - Tell the user that if a token has ever been committed, rotating it at the provider is the only real fix, and
     `/iru-check-security` can scan the repository for accidentally committed secrets.

### 4k — Dynamic configuration (`AskUserQuestion`, exactly one)

Needed to change service behaviour while it is running, with no restart and no redeployment. Default the
recommendation from Step 3's platform choice:

- **Kubernetes ConfigMaps and Secrets** — recommended when deploying to GKE, or to Cloud Run/EKS backed by
  Kubernetes. Add `org.springframework.cloud:spring-cloud-starter-kubernetes-client-config` (it has no
  Initializr id in the current catalogue, so declare it explicitly with its version in the root pom, and verify
  the Spring Cloud release train in use actually ships a build compatible with the chosen Boot version — report
  it as an open gap if it doesn't).
- **AWS Secrets Manager / Parameter Store** — recommended when deploying to AWS. Add
  `io.awspring.cloud:spring-cloud-aws-starter-secrets-manager` (and
  `spring-cloud-aws-starter-parameter-store` for non-secret dynamic properties), with the
  `io.awspring.cloud:spring-cloud-aws-dependencies` BOM imported in the root pom.
- **Spring Cloud Config Server** — the platform-independent option: add `cloud-config-client`, and `cloud-bus`
  as well if a config change must be broadcast to every replica at once rather than polled.
- **None** — configuration changes require a redeploy. Acceptable for a service with no operationally-tunable
  behaviour, but note in Step 11's report that this removes the fastest mitigation lever during an incident.

Whichever is chosen, every dynamically reloadable property must be bound in the
`infrastructure/configuration/` module on `@ConfigurationProperties` beans annotated `@RefreshScope`, so a
refresh is picked up without a restart — and every one of them belongs in the documentation's configuration table
with its "dynamically changeable" column set accordingly.

### 4l — Anything else from Initializr

Show the user that the remaining groups in Step 1's catalogue are available (Developer Tools, Template Engines,
Spring Cloud Discovery/Routing/Circuit Breaker, Ops, Testing, …) and offer to add any by id or name. Warn that
anything outside the groups above is typically **less relevant to this architecture**, and that some entries
(template engines, `data-rest`, `cloud-gateway`) actively conflict with the contract-first, hexagonal shape this
scaffold imposes — flag such a conflict rather than silently accepting it.

Always include, regardless of the user's answers: `lombok` (boilerplate generation — **Java only**),
`configuration-processor` (configuration metadata), `validation`, `testcontainers`, and `docker-compose`.
For Java, MapStruct has no Initializr id — it's added explicitly in the root pom together with the
`lombok-mapstruct-binding` needed to make the two annotation processors coexist. For **Kotlin**, send neither
`lombok` nor MapStruct: data classes and properties replace Lombok, mappers are plain extension functions (MapStruct
would need kapt, which is in maintenance mode), and Initializr itself adds `kotlin-reflect`, the Kotlin Jackson
module, and `kotlin-test-junit5` when `language=kotlin`. Note that `configuration-processor` only processes Java
sources; Kotlin `@ConfigurationProperties` classes still bind correctly, they just get no generated IDE metadata.

**Generator plugin names in this step and in Step 8 are the Maven ones.** On a Gradle build the same generators run as
Gradle plugins — `org.openapi.generator`, `com.google.protobuf` (+ `grpc-kotlin`), an AVRO plugin
(`com.github.davidmc24.gradle.plugin.avro` or an equivalent maintained one), `com.vaadin` for Hilla — chosen and
wired by `iru-setup-java-springboot-apis`/`-hilla` from the manifest; the choices in Step 4 don't change.

## Step 5 — Confirm the whole plan before writing anything

Present a single compact summary: project identity, Boot and Java versions, platform, concurrency model, whether
the project is open source, the repository visibility, the CI choices (`ci`, and when `yes` the `ci-tests` scope
and whether docs go to GitHub Pages), whether rolling deployments are enabled (and if so strategy, advance mode,
steps and bake minutes), the Sonar mode (and organization/project key/host URL when not `none`), the
frontend choice, every selected technology with the dependency ids it resolved to, the migration tool per database, the
client names and the mocking tool chosen for them,
the language, build tool and (Kotlin) Kotlin version, the exact list of modules (Maven modules or Gradle project
paths) that will be created, and the docker compose services the integration-test stack
will run. Ask for explicit confirmation, or for corrections, and loop back to the relevant part of Step 4 if the
user changes something. **No file is written before this confirmation.**

## Step 6 — Write `springboot-stack.yml`

Write the confirmed answers to `springboot-stack.yml` at the repository root. When reading an existing manifest
that predates the `language`/`buildTool` fields, treat them as `java`/`maven` (its build was generated that way). Every sub-skill reads this file
instead of re-asking, and `iru-update-java-springboot-documentation` reads it later to know what the service is
built from. It is meant to be committed.

If `springboot-stack.yml` already existed (Step 0), warn and — unless `on-existing` arrived via `args`, in which
case apply it — ask with `AskUserQuestion`:

- **Update (Recommended)** — "Rewrite it with this run's confirmed answers (whose defaults came from the existing
  file), keeping any key this skill doesn't know about. Sub-skills then generate against the updated stack."
- **Keep as is** — "Leave the file untouched. Sub-skills read the *old* manifest, so any answer you changed in
  this run (e.g. the CI choices) is ignored by them — Step 11 lists each difference." (Today's re-run behaviour
  when the stack hasn't changed.)
- **Replace** — "Write a fresh manifest from this run's answers only; unknown keys and comments in the old file
  are lost (recoverable from git history)."

```yaml
# Generated by /iru-setup-java-springboot. Records the technology choices this service was scaffolded with.
# Sub-skills read this file; keep it in sync by re-running /iru-setup-java-springboot when the stack changes.
project:
  groupId: com.example
  artifactId: orders-service
  version: 0.0.1-SNAPSHOT
  basePackage: com.example.orders
  description: Handles the order lifecycle.
  javaVersion: "21"
  springBootVersion: "4.1.0"
  language: java                 # java | kotlin — from Step 3; absent ⇒ java (manifests written before this field existed)
  buildTool: maven               # maven | gradle — gradle ONLY when language: kotlin (Gradle Kotlin DSL); absent ⇒ maven
  # kotlinVersion: "2.3.21"      # only when language: kotlin — the kotlin.version the chosen Boot version manages (Step 3)
  repository:
    host: github.com
    owner: example
    name: orders-service
  inceptionYear: "2026"
  developer:
    name: Jane Doe
    email: jane@example.com
    organizationUrl: https://github.com/jane
openSource: true                 # from Step 3b
sonar:                           # from Step 3b — mode is the source of truth downstream
  mode: cloud                    # cloud | self-hosted | none
  organization: example-github   # unset when mode: none
  projectKey: example_orders-service   # unset when mode: none
  hostUrl: https://sonarcloud.io # unset when mode: none; the self-hosted server URL when mode: self-hosted
frontend: none                   # none | hilla — hilla scaffolds a Hilla React frontend via iru-setup-java-springboot-hilla, see Step 3b
accessibility: enforce           # enforce | report | off | none — only with frontend: hilla; written to .ui-quality.yml by iru-setup-java-springboot-hilla
visibility: public               # public | private | internal — from Step 3b (detected via gh when possible)
ci:                              # from Step 3b — read by iru-setup-java-springboot-github-workflows (args may override)
  enabled: true                  # false ⇒ no workflows at all: no build/deploy/undeploy/security.yml, no dependabot.yml
  tests: full                    # unit (Surefire only, -DskipITs / Gradle `test` only, no Testcontainers in CI) | full (plus Failsafe / Gradle `integrationTest` + Testcontainers); omitted when enabled: false
  pages: true                    # false ⇒ docs built in CI and uploaded as a workflow artifact, not deployed to GitHub Pages; omitted when enabled: false
deploy:                          # from Step 3c — optional; absent ⇒ rolling deployments disabled (single-job deploy.yml, no promote.yml)
  rolling:
    enabled: true                # false/absent ⇒ single-job deploy.yml, no promote.yml; always omitted/false when ci.enabled: false
    strategy: canary             # rolling | blue-green | canary | linear
    advance: hybrid              # auto | manual | hybrid — rolling strategy only supports auto
    steps: [10, 50, 100]         # canary/linear shift percentages; blue-green = [100]; omitted for rolling
    bakeMinutes: 10              # soak between steps for auto/hybrid gates
stack:
  concurrency: blocking          # blocking | reactive | both
  cloud: aws                     # aws | gcp
  databases:
    - engine: mongodb            # mongodb | couchbase | postgresql | mariadb | elasticsearch | neo4j | qdrant
      migrations: flamingock     # flamingock | liquibase-mongodb | liquibase-couchbase | liquibase-neo4j | liquibase | flyway | none
      image: mongo:8.0
  caches: [caffeine, redis]      # caffeine | redis
  redisImage: redis:8.2
  security:
    enabled: true
    modes: [oauth2-resource-server]
  messaging:
    enabled: true
    directions: [produce, consume]
    kafkaImage: apache/kafka:4.1.0
    schemaRegistryImage: confluentinc/cp-schema-registry:8.0.0
  restServer: true
  grpcServer: false
  graphqlServer: false
  restClients: [payments]
  grpcClients: []
  graphqlClients: []
  apiMock: wiremock              # microcks | wiremock | none — required whenever any client is listed
  apiMockImage: wiremock/wiremock:3.13.1
  logging: true
  metrics: true
  tracing: true
  ai:
    enabled: false
    providers: []
    vectorStore: none
    mcp: []
  dynamicConfig: aws-secrets-manager   # kubernetes | aws-secrets-manager | spring-cloud-config | none
  extras: []
initializr:
  dependencies: [webmvc-or-web-id, data-mongodb, cloud-stream, kafka, actuator, prometheus, ...]
modules:                         # directories; on Gradle each is the project path with / → : (e.g. :infrastructure:database:mongodb)
  - domain
  - application
  - infrastructure/database/mongodb
  - infrastructure/configuration
  - infrastructure/clients/payments
  - infrastructure/producers
  - infrastructure/metrics
  - api/rest-server
  - api/consumers
  - boot
  - coverage
```

Pin every container image to a concrete tag — never `latest` — so integration tests are reproducible. Look up the
current stable tag for each image rather than inventing one, and record it in this manifest so the compose file,
the Testcontainers harness, and the OpenTofu engine versions all agree.

## Step 7 — Fetch the reference build from Spring Initializr

With the confirmed answers, fetch the single-module build Initializr would have produced — a `pom.xml` for a Maven
build (Java or Kotlin), a `build.gradle.kts` for Kotlin + Gradle. This is the **source of truth for artifact
names, BOM imports, plugin ids and version properties** — not a template to keep. Save it to the scratchpad (not
the repository).

**Maven** (`buildTool: maven`, either language):

```bash
curl -sG https://start.spring.io/pom.xml \
  --data-urlencode 'bootVersion=<boot-version>' \
  -d type=maven-build \
  -d language=<java|kotlin> \
  -d javaVersion=<java-version> \
  -d groupId=<group-id> \
  -d artifactId=<artifact-id> \
  -d name=<artifact-id> \
  -d packageName=<base-package> \
  -d 'dependencies=<comma-separated ids from Step 4>' \
  -o <scratchpad>/initializr-pom.xml
```

**Gradle Kotlin DSL** (`buildTool: gradle`, Kotlin only). Initializr has no standalone `build.gradle.kts` endpoint
(`/build.gradle.kts` is a 404, and `/build.gradle` with `type=gradle-build` returns the *Groovy* DSL), so fetch the
whole starter project and extract its `build.gradle.kts` — into a new, empty scratchpad directory, since it is a
downloaded archive:

```bash
mkdir -p <scratchpad>/initializr-starter && cd <scratchpad>/initializr-starter
curl -sG https://start.spring.io/starter.zip \
  --data-urlencode 'bootVersion=<boot-version>' \
  -d type=gradle-project-kotlin \
  -d language=kotlin \
  -d javaVersion=<java-version> \
  -d groupId=<group-id> \
  -d artifactId=<artifact-id> \
  -d name=<artifact-id> \
  -d packageName=<base-package> \
  -d 'dependencies=<comma-separated ids from Step 4>' \
  -o starter.zip && unzip -q starter.zip
# reference build: <scratchpad>/initializr-starter/build.gradle.kts
```

Read from the reference build:

- the exact `<groupId>/<artifactId>` (Gradle: `group:name` coordinates) of every starter and driver, including
  test-scope ones — Boot 4 adds a `spring-boot-starter-<x>-test` per starter and `testcontainers-<engine>` modules;
- every BOM import and its version property (Maven: `<dependencyManagement>` + e.g. `spring-cloud.version`,
  `spring-ai.version`; Gradle: the `dependencyManagement { imports { mavenBom(...) } }` block and the `extra[...]`
  properties) — these belong in the root pom / `gradle/libs.versions.toml` verbatim;
- any build plugin Initializr added (e.g. `io.github.ascopes:protobuf-maven-plugin` for the gRPC starters, or its
  Gradle plugin id), and whether the Boot parent / plugin already manages its version;
- Java: the `annotationProcessorPaths` configuration for Lombok and the configuration processor;
- Kotlin: the Kotlin version (Maven `<kotlin.version>`; Gradle `kotlin("jvm") version "..."`) — it must equal
  `project.kotlinVersion` from Step 3 unless the user deliberately overrode it; if it differs without an override,
  update the manifest to the reference value and say so — plus the compiler setup Initializr generated
  (`-Xjsr305=strict` and any further `freeCompilerArgs`, the `spring`/`jpa` compiler plugins, and the
  `allOpen` annotations for `jakarta.persistence.Entity`/`MappedSuperclass`/`Embeddable`), which the build
  sub-skill carries over.

The Gradle starter also contains a Gradle wrapper (`gradlew`, `gradle/wrapper/`) pinned to the Gradle version
Initializr currently ships; leave it in the scratchpad — the build sub-skill owns wrapper generation and may use that
version as its reference.

Verify the response is actually the requested build file (XML for the pom, a zip for the starter) — Initializr
answers an invalid dependency id or an incompatible version combination with an HTTP 400 and a short error body
(JSON, e.g. a `message` of `Unknown dependency 'x' check project metadata`). If it errors, read the message, fix
the offending id (usually one that didn't validate against Step 1's catalogue, or one incompatible with the chosen
Boot version), and retry. If a dependency turns out to be incompatible with the chosen Boot version, tell the user
and let them choose between dropping it and changing the Boot version — don't decide silently.

## Step 8 — Delegate the file generation

Run the sub-skills **in this order** (seven always, plus `iru-setup-java-springboot-hilla` as an eighth whenever
the manifest's `frontend: hilla`), each via the `iru-isolated-skill-executor` agent so its own file reads,
template expansion, and build output stay out of this orchestrator's context. Every sub-skill reads
`springboot-stack.yml` itself — including `project.language`, `project.buildTool` and `project.kotlinVersion`, so
nothing about the language or build tool is forwarded in `args` — and each prompt only needs to point it at that
file and at the saved Initializr reference build (passed under the existing `initializr-pom` key whichever file it
is: `initializr-pom.xml` for Maven, `initializr-starter/build.gradle.kts` for Gradle), and to name what should come
back. Add `mode: <new|existing>` to every sub-skill's `args`, and
`on-existing: <value>` **only when it arrived in this skill's own `args`** — otherwise leave it out so each
sub-skill announces scratch-vs-update and asks Update / Keep as is / Replace per artifact it owns. Since a
sub-skill run through `iru-isolated-skill-executor` still asks its `AskUserQuestion`s, tell the executor to let
those questions through to the user rather than answering them itself.

Order matters: root build before modules (a module needs its parent pom / `settings.gradle.kts` entry to exist), modules before APIs (generated sources
need a module to land in), APIs before Hilla (the `boot` module the frontend lands in must already exist, and the
API-generated code Hilla endpoints may call must already be there), Hilla before Testcontainers (the compose stack
and CI docs job both need to know a frontend toolchain now exists on disk), everything before the workflows and
documentation (both survey what's actually on disk).

```
Agent({
  description: "Run springboot pom setup",
  subagent_type: "iru-isolated-skill-executor",
  prompt: "Invoke Skill({skill: \"iru-setup-java-springboot-pom\", args: \"stack-file: springboot-stack.yml\\n
    initializr-pom: <scratchpad-path-to-reference-build>\\nmode: <mode>[\\non-existing: <value>]\"}).
    Report back: whether it created or updated each file and what the user chose per pre-existing file, the
    modules (Maven) or project paths (Gradle) declared, the dependency and plugin versions pinned in the root pom
    or version catalog, the Gradle wrapper version (Gradle), and any dependency it could not place.",
  run_in_background: false
})
```

Repeat that shape for, in order:

1. **`iru-setup-java-springboot-pom`** — the root build and every module build. Maven (Java or Kotlin): root
   reactor pom (all versions, all plugins) and every module pom — Checkstyle/PMD/SpotBugs + Javadoc for Java,
   `kotlin-maven-plugin` + detekt/ktlint + Dokka (and the root `detekt.yml`) for Kotlin. Gradle (Kotlin only):
   `settings.gradle.kts`, `gradle/libs.versions.toml`, the `build-logic/` convention plugins, a minimal root
   `build.gradle.kts`, one `build.gradle.kts` per module, the root `detekt.yml`, and the Gradle wrapper. Report
   back: module list / project paths, pinned versions, anything unplaced.
2. **`iru-setup-java-springboot-modules`** — directory tree, package layout, ports in `domain`, adapter skeletons
   in each `infrastructure`/`api` module, the `@SpringBootApplication` class, `application.yml` per profile, the
   `@RefreshScope` configuration beans, and the ArchUnit test that enforces the dependency direction — as Java
   sources under `src/*/java`, or Kotlin sources under `src/*/kotlin` (MockK-based sample tests) when the manifest
   says Kotlin. Report back: modules created, ports and adapters scaffolded, profiles written.
3. **`iru-setup-java-springboot-apis`** — the `apis/` tree with a starter spec per API, and the
   `openapi-generator-maven-plugin` / `protobuf-maven-plugin` / `avro-maven-plugin` executions wired into the
   right module poms — or, on Gradle, the equivalent Gradle generator plugins wired into the module build files —
   HTML documentation generation included. Report back: spec files created, generator
   executions added and to which module.
3b. **`iru-setup-java-springboot-hilla`** — only when the manifest's `frontend: hilla`. Scaffolds the Hilla React
   frontend into the `boot` module: the Vaadin BOM/starters, the `vaadin-maven-plugin` execution (the `com.vaadin`
   Gradle plugin on Gradle),
   `src/main/frontend/` (file-based-routing views, a customized `index.html`), `vitest.config.ts` with
   `@vitest/coverage-v8` lcov output and a sample test, ESLint flat config + Prettier, and — when `sonar.mode`
   isn't `none` — the frontend's `sonar.sources`/`sonar.tests`/`sonar.javascript.lcov.reportPaths` additions to
   the root build. Report back: the resolved Vaadin version, files written versus already present, whether the
   `vaadin:prepare-frontend` (Gradle: `vaadinPrepareFrontend`) and `vitest run --coverage` gates passed, and the resolved
   `boot/coverage/lcov.info` path.
4. **`iru-setup-java-springboot-testcontainers`** — `docker-compose.yml` (or `compose.yaml`) with one service per
   chosen technology plus Prometheus/Grafana, the Microcks or WireMock mock backing every REST/gRPC client from
   the contracts in `apis/rest-client/`/`apis/grpc-client/`, the `ComposeContainer`-based integration-test base
   class, and the Failsafe wiring (the `integrationTest` task on Gradle). Report back: compose services and their
   pinned images, base test class location, the base URL each client resolves to against the mock, whether
   `mvn verify` / `./gradlew integrationTest` ran and its result.
5. **`iru-setup-java-springboot-platform`** — the OpenTofu configuration for the chosen cloud. When the manifest's
   `deploy.rolling.enabled` is `true` it also generates the rollout infrastructure (second target group / revision
   tags / Argo Rollouts, candidate URL, metric gate), so add these `args` lines in addition to `mode`/`on-existing`:
   `rolling: yes`, `deployment-strategy: <strategy>`, `advance: <advance>`, `steps: <comma list>`,
   `bake-minutes: <n>` (the manifest stays the source of truth through `stack-file`; the lines make a stale
   manifest impossible to misread). Pass `rolling: no` — or nothing — when disabled. Report back:
   resources it will manage, what it deliberately left to the user, every secret/variable that must be
   provided out-of-band, and — when rolling — the `rollout_*` outputs it exposes and its prerequisites.
6. **`iru-setup-java-springboot-github-workflows`** — the test/analyse/publish workflow, the deploy workflow, and
   the undeploy workflow, plus `security.yml` and `.github/dependabot.yml`, and — when rolling deployments are
   enabled — a staged `deploy.yml` and the `promote.yml` workflow that advances or rolls back a rollout. It reads
   `visibility`, `ci.tests`, and
   `ci.pages` (and the language/build tool, which switch it between Maven and `./gradlew` commands and between
   Checkstyle/PMD/SpotBugs + Javadoc and detekt/ktlint + Dokka) from the manifest, so they needn't be forwarded
   (only `mode`, and `on-existing` when applicable) — except the rolling settings, which are forwarded exactly as
   for the platform skill (`rolling:`, `deployment-strategy:`, `advance:`, `steps:`, `bake-minutes:`).
   Report back: workflow files (including `promote.yml`) created/updated/replaced/kept, required repository secrets
   and environments, and any gap. **Skipped entirely when the manifest's `ci.enabled: false`** — record it as "skipped (ci: no)" and
   note in Step 11 that the deploy/undeploy workflows were skipped with it (deployment and teardown are manual
   `tofu apply`/`tofu destroy` runs) along with the shared security block.
7. **`iru-update-java-springboot-documentation`** — the Antora site (Mermaid **and** Kroki) with the full
   template page set, its build/run/test commands and code samples matching the manifest's build tool and language. Report back: pages created versus already present, and whether the site built.

If any sub-skill reports that it stopped, or that the user chose **Keep as is** for a file it owns, don't treat
that as a failure of this skill — carry on with the remaining sub-skills and record it in Step 11's report. The
one exception is `iru-setup-java-springboot-pom`: if no usable root build exists after it ran — no `pom`-packaged
root reactor (Maven), or no `settings.gradle.kts` including the module projects (Gradle); e.g. it stopped on a
brand-new repository, or the existing root build was kept but isn't a multi-module build — there is nothing for
anything else to attach to, so stop the run there and report why.

## Step 9 — Supporting repository files

After the sub-skills, fill in the repository-level files they don't own:

Forward `on-existing` to each of these skills only when it arrived in this skill's own `args`; otherwise each one
announces scratch-vs-update and asks Update / Keep as is / Replace for its own file itself.

- **`.gitignore`** — invoke `iru-setup-java-gitignore` if available. Regardless, make sure `target/` (Maven) or
  `build/` + `.gradle/` (Gradle, with `!gradle/wrapper/gradle-wrapper.jar` kept tracked), `.kotlin/` (Kotlin),
  `.integration-test.lock/`, `docs/build/`, `.env`, `*.tfstate`, `*.tfstate.*`, `.terraform/`, `*.tfvars` (except
  `*.tfvars.example`), and IDE directories are ignored. The tfstate and tfvars entries matter: both routinely contain credentials.
- **`README.md`** — invoke `iru-setup-readme` if available, passing `args` lines `sonar: <manifest sonar.mode>`,
  `ci: <yes|no from ci.enabled>`, and — when `ci: yes` — `pages: <yes|no from ci.pages>` (plus `on-existing` when
  applicable), so the README's Sonar badges/dashboard links, CI badges, and documentation-site link match the
  choices recorded in `springboot-stack.yml` (no CI badge when `ci: no`, no github.io link when Pages is off).
- **`CHANGELOG.md`** — invoke `iru-setup-changelog` if available (forwarding `on-existing` when applicable).
- **`checkstyle.xml`** (Java only) — the root pom's `maven-checkstyle-plugin` points at it; if one already exists, keep it
  (it's a project's own ruleset — mention it in the report, and only offer to replace it if it's clearly broken);
  if no ruleset exists, write a starting one (Sun or Google checks with the line-length and Javadoc rules relaxed to what a Spring Boot service
  can realistically satisfy) rather than leaving the build referencing a missing file.
- **`detekt.yml`** (Kotlin only) — written by `iru-setup-java-springboot-pom`, not here; detekt is configured
  against it on both Maven and Gradle. Just check it exists at the repository root. If it's missing (the pom
  sub-skill stopped, or the user kept an older root build that never had one), don't write one here — report it as
  a gap in Step 11 and point at re-running `/iru-setup-java-springboot-pom`, since the detekt gate fails or falls
  back to defaults without it. Don't write a `checkstyle.xml` for a Kotlin build.
- **`LICENSE`** — ask whether the service needs one. Services often don't, unlike libraries. If one is added,
  `/iru-check-license` can backfill the file headers.

## Step 10 — Verify the build

Run, from the repository root, the three commands for the manifest's build tool, and fix what breaks before
reporting success.

Maven (Java, or Kotlin + Maven — identical commands):

```bash
mvn -q clean verify -DskipTests   # compiles every module and runs all code generation
mvn -q test                       # unit tests (Surefire)
mvn -q verify                     # integration tests (Failsafe + Testcontainers) — needs Docker running
```

Gradle Kotlin DSL (Kotlin + Gradle), always through the wrapper the build sub-skill generated:

```bash
./gradlew clean build -x test -x integrationTest   # compiles every project and runs all code generation
./gradlew test                                     # unit tests (*Test, excluding **/*IT*)
./gradlew integrationTest                          # integration tests (*IT + Testcontainers) — needs Docker running
```

Run all three regardless of `ci.tests`: `unit` only changes what CI runs, and the integration tests are exactly
what still has to be verified locally then.

Delegate each of these to the `iru-gate-runner` agent rather than running them inline (naming the build tool and
the exact command in its prompt), so a multi-module Maven or Gradle log doesn't flood this orchestrator's context — ask it back for a compact pass/fail plus the first real error.

Expect the generated skeleton to build and its example tests to pass. If `mvn verify` / `./gradlew
integrationTest` fails only because Docker
isn't available, say so plainly and don't call it a code problem. If code generation fails (a malformed starter
spec, an OpenAPI/protobuf generator misconfiguration), fix it — a scaffold that doesn't compile isn't done.

If `frontend: hilla`, note that the plain `mvn clean verify -DskipTests` above already exercises
`vaadin:prepare-frontend` (bound in the `boot` module's pom by `iru-setup-java-springboot-hilla`; on Gradle the
`com.vaadin` plugin's `vaadinPrepareFrontend` runs as part of `build`) — a `-Pproduction` (Gradle:
`-Pvaadin.productionMode=true`) build is **not** needed for this local sanity check, only for a real release artifact, since
`vaadin:build-frontend` decides for itself whether a production bundle is actually needed. Don't add
`-Pproduction` here just because the reactor has a Hilla frontend.

## Step 11 — Report and warn

Summarize:

- The setup mode (from scratch / updating an existing repository) and, per component from Step 0's inventory, the
  action actually taken: **created / updated / replaced / kept as is / skipped (ci: no)** — plus, for every
  component kept as is, each mismatch with this run's choices the sub-skill reported.
- The resolved identity, Boot version, Java version, platform, and concurrency model.
- The language and build tool (and how they were decided: `args`, detected from the existing repository, or
  asked); for Kotlin, the `kotlinVersion` recorded and its source (the Boot-managed version confirmed against the
  reference build, or a user override flagged as untested by Spring Boot); for Gradle, the wrapper version the build
  sub-skill generated and how (local `gradle`, Docker, or the user); whether `detekt.yml` (Kotlin) or
  `checkstyle.xml` (Java) is present.
- The repository visibility (and whether it was detected via `gh` or asked), and the CI choices: `ci` (when `no`,
  that the build/deploy/undeploy workflows and the shared security block — Dependabot, dependency-review, CodeQL,
  OSV-Scanner, gitleaks — were skipped, that deployment is a manual `tofu apply`, and that
  `/iru-setup-java-springboot-github-workflows` adds them later), `ci.tests` (when `unit`, that integration tests
  run only locally), and `ci.pages` (when `no`, that the docs are uploaded as a workflow artifact and no github.io
  site exists; when public, that `yes` was applied without asking). For a private/internal repository, repeat the
  included-minutes budget, and if `sonar.mode` is `cloud`, that SonarCloud needs a paid plan for it. If
  `ci: no` with a Sonar mode other than `none`, say no CI step sends reports.
- Rolling deployments: enabled or not (with `ci: no`, "not offered — needs the workflows"); when enabled the
  strategy, advance mode, `steps`/`bakeMinutes`, that `promote.yml` was generated (and its action), the `rollout_*`
  OpenTofu outputs and prerequisites the platform sub-skill reported, the cost note (blue/green temporarily doubles
  capacity), and that `/iru-springboot-rolling-deployments enable|disable` switches it later.
- Whether the project is open source, the Sonar mode wired (`cloud`/`self-hosted`/`none`, plus organization/project
  key/host URL when not `none`), and the frontend choice (`none`/`hilla` — when `hilla`, what
  `iru-setup-java-springboot-hilla` reported back: the resolved Vaadin version, whether the frontend gates passed,
  the resolved lcov path, the `accessibility` level and the `.ui-quality.yml` action).
- Every technology selected, with the starter it resolved to and the migration tool per database.
- The full module tree created (with Gradle project paths on Gradle), and the `apis/` spec directories.
- Which sub-skills completed, which stopped and why.
- The build result from Step 10 for each of the three commands (Maven or Gradle, as run).
- **Every secret and variable that must be provided out-of-band**, consolidated into one table from what the
  workflow (when `ci: yes`) and platform sub-skills reported — GitHub Actions secrets, the cloud OIDC role/workload-identity
  binding, the Sonar token (only when `sonar.mode` is not `none`), the security-block secrets
  (`GITLEAKS_LICENSE` if a Pro key is used), and any LLM API key. State again that none of them belong in the
  repository, and that the OpenTofu state backend must be remote and encrypted since state files contain resource
  attributes that are effectively secrets.
- Any open gap: a missing `detekt.yml` on a Kotlin build, a dependency Step 1's catalogue couldn't resolve, a Spring Cloud component with no build for the
  chosen Boot version, an image tag that couldn't be pinned, a manual platform step the OpenTofu config can't do.

Finish with an explicit warning: **review every generated file before committing, building against real
infrastructure, or running a deploy.** In particular — the OpenTofu configuration will create billable cloud
resources, so run `tofu plan` and read it in full before any `apply`; the undeploy workflow (when `ci: yes`)
destroys infrastructure, so confirm its guards match the intended blast radius; and the generated architecture, use-case,
and API documentation pages are templates describing an empty service — they must be filled in as real code
lands, which is what `/iru-update-java-springboot-documentation` is for.
