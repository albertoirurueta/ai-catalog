---
name: iru-setup-java-springboot-pom
description: >-
  Generate the multi-module build for a DDD/hexagonal Spring Boot service, in the language and build tool the
  `springboot-stack.yml` manifest records (`project.language` `java`|`kotlin`, `project.buildTool` `maven`|`gradle`,
  `project.kotlinVersion`; absent means Java on Maven, generated exactly as before). Java and Kotlin on Maven get a
  Maven reactor — the root `pom.xml` (the single place every dependency and plugin version is declared) plus one
  `pom.xml` per module (`domain`, `application`, `infrastructure/database/<engine>`, `infrastructure/configuration`,
  `infrastructure/clients/<name>`, `infrastructure/producers`, `infrastructure/metrics`, `api/rest-server`,
  `api/grpc-server`, `api/graphql-server`, `api/consumers`, `boot`, `coverage`). Enforces Java 21 as a minimum via
  `maven.compiler.release`, `java.version`, and a `maven-enforcer-plugin` `requireJavaVersion` rule, and enforces
  the hexagonal dependency direction per module with `banned-dependencies`. Wires the full report/quality plugin
  set — for Java Javadoc, Checkstyle, PMD, SpotBugs; for Kotlin the `kotlin-maven-plugin` (spring/jpa/all-open
  compiler plugins, `-Xjsr305=strict`, mixed Java/Kotlin source roots with `default-compile` rebound after
  `kotlinc`), detekt, ktlint and Dokka instead; for both Surefire, Failsafe, JaCoCo (per module plus a
  `report-aggregate` in `coverage`), JXR, Maven Site, `groovy-maven-plugin` for `build-info.properties`, and, unless
  the manifest's `sonar.mode` is `none`, `sonar-maven-plugin` (Kotlin adds the detekt/ktlint report paths and
  `src/main/kotlin` sources) — with generated sources excluded from every analysis. Kotlin on Gradle gets the
  equivalent Gradle Kotlin DSL multi-project build instead — `settings.gradle.kts`, `gradle.properties`,
  `gradle/libs.versions.toml` (every version, the Spring Boot BOM through `platform()`), a `build-logic/` included
  build with the `iru.kotlin-library`, `iru.spring-boot-app`, `iru.quality` (detekt + ktlint + Dokka),
  `iru.integration-test` (`integrationTest` over `*IT*`) and `iru.coverage` convention plugins, one
  `build.gradle.kts` per module with `project(":...")` dependencies matching the module table, a root
  `build.gradle.kts` with Dokka aggregation and Sonar, a `coverage` project using `jacoco-report-aggregation`, and
  the Gradle wrapper. Writes the root `detekt.yml` and `.editorconfig` for Kotlin (as `checkstyle.xml` and
  `spotbugs-exclude.xml` for Java). When the manifest's `frontend` is `hilla`, also owns the root-level
  Vaadin/Hilla version pins (Maven: a `vaadin.version` property, a `vaadin-bom` import, a `vaadin-maven-plugin`
  `pluginManagement` entry, a `production` profile and the `vaadin.skip` escape hatch; Gradle: the catalog's
  `vaadin` version, BOM and plugin entries) — `iru-setup-java-springboot-hilla` then wires the actual module.
  Reads its inputs from `springboot-stack.yml` (including `sonar.mode`/`sonar.organization`/`sonar.projectKey`/
  `sonar.hostUrl` — `cloud` points at SonarCloud, `self-hosted` at the given host URL, `none` omits Sonar
  entirely — and `frontend`) and from the Initializr reference build (a pom, or the starter's
  `build.gradle.kts` for Gradle), so starter artifact names and BOM imports come from the API rather than from
  memory; every other version is resolved live from Maven Central or the Gradle plugin portal. Announces whether
  it is generating the build from scratch or updating an existing one, and for every build/analysis-config file it
  owns that already exists warns and asks Update (merge, keeping custom dependencies/plugins/profiles) / Keep as
  is / Replace / Stop — or applies `on-existing` from `args`. Invoke as `/iru-setup-java-springboot-pom` (it reads
  `springboot-stack.yml` from the repository root), or with `args` (`stack-file:` / `initializr-pom:` / `mode:`
  (`new`/`existing`) / `on-existing:` (`ask`/`keep`/`update`/`replace`) lines) when called from
  `iru-setup-java-springboot`. Use whenever a Spring Boot service's multi-module Maven reactor or Gradle KTS build
  needs generating or regenerating from the recorded stack, instead of hand-writing a dozen interdependent build
  files.
model: sonnet
---

# Setup Java Spring Boot Poms

Generate the whole multi-module build for a hexagonal Spring Boot service. Which build depends on two manifest
fields, read in Step 0:

| `project.language` | `project.buildTool` | What this skill writes | Steps |
|---|---|---|---|
| `java` (or absent) | `maven` (or absent) | Maven reactor, Java toolchain (Lombok, MapStruct, Checkstyle/PMD/SpotBugs, Javadoc) | 0–8 as written |
| `kotlin` | `maven` | The same Maven reactor and module poms, with the Kotlin deltas of Step 1K (kotlin-maven-plugin, detekt, ktlint, Dokka) | 0–5, 1K, 6–8 |
| `kotlin` | `gradle` | A Gradle Kotlin DSL multi-project build (Step 5G) instead of any pom | 0, 2, 5G, 6–8 |

The Java path is the default and is unchanged: a manifest without these fields regenerates exactly the reactor
it always did. Two rules govern every path:

1. **Every version lives in one place.** On Maven that is the root `pom.xml`: module poms declare
   `<groupId>`/`<artifactId>` only, with no `<version>`, resolving through the root's `<dependencyManagement>` and
   `<pluginManagement>`. On Gradle it is `gradle/libs.versions.toml`: module build files and convention plugins
   reference catalog aliases only, and the Spring Boot BOM (plus any other BOM) is applied through `platform()`.
   A version anywhere else is a bug, not a shortcut.
2. **Starter and driver artifact names come from the Initializr reference build, never from memory.** They change
   across Boot major versions — in Boot 4.x `spring-boot-starter-web` became `spring-boot-starter-webmvc`, the
   Testcontainers modules became `testcontainers-<engine>`, Jackson moved to `tools.jackson.*`, and each starter
   gained a `spring-boot-starter-<x>-test` companion. Copy what the reference build actually says; the Maven
   coordinates are the same on Gradle.

## Step 0 — Resolve inputs

Parse `args` for `key: value` lines:

```
stack-file: springboot-stack.yml
initializr-pom: /path/to/scratchpad/initializr-pom.xml
mode: existing
on-existing: ask
```

- **`stack-file`** — defaults to `springboot-stack.yml` at the repository root. Read it in full; it carries the
  project identity, the concurrency model, every technology choice, the top-level `sonar:` block
  (`mode: cloud | self-hosted | none`, plus `organization`/`projectKey`/`hostUrl`), and `frontend`
  (`none`/`hilla`). If it doesn't exist, stop and tell the user to run `/iru-setup-java-springboot` first — this
  skill deliberately doesn't re-interview. `sonar.mode` decides the four `sonar.*` properties and the
  `sonar-maven-plugin` entry below: `cloud` keeps today's `https://sonarcloud.io` default, `self-hosted`
  substitutes the manifest's `sonar.hostUrl`, and `none` drops all of it. A manifest written before this field
  existed (no `sonar:` key at all) is treated as `cloud` for backward compatibility, so an older
  `springboot-stack.yml` regenerates the same pom it always did. `frontend: hilla` adds the Vaadin/Hilla version
  management described in Step 1's "Frontend (Hilla) version management" note below; `frontend: none` (or the key
  absent, for the same backward-compatibility reason) omits all of it.
- **`project.language` / `project.buildTool` / `project.kotlinVersion`** — from the manifest's `project:` block.
  Absent `language` means `java`, absent `buildTool` means `maven` (manifests written before these fields existed).
  `buildTool: gradle` with `language: java` is invalid — Java services are Maven-only in this catalog — so stop and
  tell the user to fix the manifest via `/iru-setup-java-springboot` rather than guessing. For Kotlin, use
  `kotlinVersion` exactly as recorded: `iru-setup-java-springboot` resolves it to the Kotlin version the chosen
  Spring Boot release manages (`kotlin.version` in `spring-boot-dependencies`, e.g. `2.3.21` for Boot `4.1.1`) —
  never substitute "the latest Kotlin" (a newer Kotlin than Boot manages is untested by Boot). Only if the field is
  missing, read it from `https://repo1.maven.org/maven2/org/springframework/boot/spring-boot-dependencies/<boot-version>/spring-boot-dependencies-<boot-version>.pom`
  and say so in Step 8.
- **`initializr-pom`** — the reference build. For Java and Kotlin + Maven it is a pom; for Kotlin + Gradle the
  orchestrator passes the starter's `build.gradle.kts` (extracted from `/starter.zip`) under the same key — read
  its `dependencies { }` block the same way (coordinates are identical; Gradle only drops the `<scope>` in favour
  of `implementation`/`runtimeOnly`/`testImplementation`). If it wasn't supplied, fetch it now yourself from the
  ids in the manifest's `initializr.dependencies` — for Kotlin add `-d language=kotlin` so the reference carries
  `kotlin-reflect`, `kotlin-test-junit5` and Initializr's current Kotlin compiler arguments:

  ```bash
  curl -sG https://start.spring.io/pom.xml \
    --data-urlencode 'bootVersion=<project.springBootVersion>' \
    -d type=maven-build -d javaVersion=<project.javaVersion> \
    -d groupId=<project.groupId> -d artifactId=<project.artifactId> \
    -d packageName=<project.basePackage> \
    -d 'dependencies=<comma-separated ids>' -o <scratchpad>/initializr-pom.xml
  ```

  Confirm the response is XML, not a plain-text error, before using it. For Kotlin + Gradle fetch the starter
  instead (the `/build.gradle.kts` endpoint does not exist) and unzip it into the scratchpad — it also carries a
  Gradle wrapper Step 5G may reuse:

  ```bash
  curl -sG https://start.spring.io/starter.zip -d type=gradle-project-kotlin -d language=kotlin \
    --data-urlencode 'bootVersion=<project.springBootVersion>' -d javaVersion=<project.javaVersion> \
    -d groupId=<project.groupId> -d artifactId=<project.artifactId> -d packageName=<project.basePackage> \
    -d 'dependencies=<comma-separated ids>' -o <scratchpad>/starter.zip
  unzip -q -o <scratchpad>/starter.zip -d <scratchpad>/initializr-starter
  ```
- **`mode`** (`new`/`existing`) — informational; scratch-vs-update is still decided per file from what's on disk,
  and `mode: existing` does not mean "update silently".
- **`on-existing`** (`ask`/`keep`/`update`/`replace`, default `ask`) — applied to every pre-existing file below
  without asking (the warning is still printed).

From the reference pom, extract into a working table you'll consult for every module below:

- every starter/driver `groupId:artifactId` and its scope (compile / runtime / test / optional);
- every `<dependencyManagement>` BOM import plus its version property (e.g. `spring-cloud.version`,
  `spring-ai.version`) — these go into the root pom verbatim;
- any build plugin Initializr added and whether the Boot parent already manages its version;
- the `annotationProcessorPaths` entries (Java only — Kotlin uses no annotation processors here: no Lombok, no
  MapStruct, no kapt; drop `lombok` and `spring-boot-configuration-processor` from a Kotlin reference, and mapping
  is hand-written extension functions generated by `iru-setup-java-springboot-modules`).

Then classify every extracted dependency to the module that should own it, using the table in Step 2. A dependency
you can't confidently place goes in the `boot` module (which depends on everything and where a misplacement is
harmless) and gets reported as unplaced in Step 8 — never drop it silently.

Say whether this run is **generating the build from scratch** or **updating an existing one**, listing which of
the files this skill owns already exist. Those are, per path:

- **Java + Maven**: the root pom, the module poms named in `modules:`, `checkstyle.xml`, `spotbugs-exclude.xml`.
- **Kotlin + Maven**: the root pom, the module poms, `detekt.yml`, `.editorconfig`.
- **Kotlin + Gradle**: `settings.gradle.kts`, `gradle.properties`, `gradle/libs.versions.toml`, the root
  `build.gradle.kts`, `build-logic/` (its `settings.gradle.kts`, `build.gradle.kts` and the five convention
  plugins), each module's `build.gradle.kts` (asked as one grouped question, like the module poms), the Gradle
  wrapper (`gradlew`, `gradlew.bat`, `gradle/wrapper/*`), `detekt.yml`, `.editorconfig`. A `pom.xml` at the root of
  a repository whose manifest says `buildTool: gradle` (or a Gradle build where the manifest says `maven`) is a
  build-tool switch, not an update — say so and offer Stop (recommended) or Replace (writes the new build; the
  old one is left on disk for the user to delete once satisfied, never deleted by this skill).

For each one that exists, warn and — unless `on-existing` says otherwise —
ask with `AskUserQuestion` (up to 4 files per call, one question each; the module poms may be asked as one
grouped question, "all existing module poms", with a per-module override if the user wants one). Say concretely
where an existing file disagrees with the manifest (e.g. "your root pom has `sonar-maven-plugin` but
`sonar.mode: none`", "it lists `api/grpc-server` but the manifest has no gRPC server"):

- **Update (Recommended)** — merge: add what's missing and correct what this skill owns (versions, managed
  BOMs, plugin configuration, the `sonar.*`/Vaadin wiring per the manifest, `<modules>`) using the templates
  below; keep every dependency, plugin, profile, and property the existing pom has that the template doesn't, and
  list those in Step 8 so the user can confirm each one survived. A customized part this skill owns may be
  rewritten.
- **Keep as is** — leave the file untouched. Customizations survive, but it may stay out of date or disagree with
  the manifest — Step 8 lists each mismatch. Recommend this one instead of Update for `checkstyle.xml` and
  `spotbugs-exclude.xml`, which are the project's own rulesets.
- **Replace** — regenerate from the template; every customization in the file is lost (recoverable only from git
  history).
- **Stop** — end this skill now without writing anything (offered only on the root pom question). An existing
  root pom that isn't `pom`-packaged (a single-module project) can't simply be updated into a reactor — say so,
  and recommend Stop there instead of Update.

If the root pom ends up kept as is (or the run stops), say so prominently in Step 8: `iru-setup-java-springboot`
needs a usable reactor root to continue.

On Gradle the same four answers apply file by file; **Stop** is offered on the `settings.gradle.kts` question
(the Gradle equivalent of the root pom), and **Update** means: add missing `include(...)` lines, catalog entries,
convention-plugin blocks and module dependencies, correct versions and the Sonar/Dokka wiring per the manifest,
and keep every hand-added plugin, dependency, task and catalog entry (listed in Step 8). For `detekt.yml` and
`.editorconfig` recommend **Keep as is**, like `checkstyle.xml` — they are the project's own rulesets.

## Step 1 — Root `pom.xml`

Java + Maven writes this template as is; Kotlin + Maven starts from it and then applies Step 1K; Kotlin + Gradle
writes no pom at all — read Step 2 for placement, then go to Step 5G.

Substitute `<placeholders>` from the manifest. Include only the `<module>` entries for modules the manifest's
`modules:` list actually names.

```xml
<project xmlns="http://maven.apache.org/POM/4.0.0"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>

  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version><spring-boot-version></version>
    <relativePath/>
  </parent>

  <groupId><group-id></groupId>
  <artifactId><artifact-id>-parent</artifactId>
  <version><version></version>
  <packaging>pom</packaging>

  <name>${project.groupId}:${project.artifactId}</name>
  <description><description></description>
  <url>https://<host>/<owner>/<repo></url>
  <inceptionYear><inception-year></inceptionYear>

  <developers>
    <developer>
      <name><developer-name></name>
      <email><developer-email></email>
      <organizationUrl><organization-url></organizationUrl>
    </developer>
  </developers>
  <scm>
    <connection>scm:git@<host>:<owner>/<repo>.git</connection>
    <developerConnection>scm:git@<host>:<owner>/<repo>.git</developerConnection>
    <url>git@<host>:<owner>/<repo>.git</url>
  </scm>

  <modules>
    <module>domain</module>
    <module>application</module>
    <module>infrastructure</module>
    <module>api</module>
    <module>boot</module>
    <module>coverage</module>
  </modules>

  <properties>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    <!-- Java 21 is this catalog's enforced minimum; all three must agree. -->
    <java.version><java-version></java.version>
    <maven.compiler.release><java-version></maven.compiler.release>
    <maven.compiler.source><java-version></maven.compiler.source>
    <maven.compiler.target><java-version></maven.compiler.target>

    <!-- BOM versions copied verbatim from the Initializr reference pom; omit any not present there. -->
    <spring-cloud.version><from-reference-pom></spring-cloud.version>
    <spring-ai.version><from-reference-pom></spring-ai.version>

    <!-- Dependencies with no Initializr id and no Boot-managed version. Omit any the stack doesn't use. -->
    <mapstruct.version><latest></mapstruct.version>
    <lombok-mapstruct-binding.version><latest></lombok-mapstruct-binding.version>
    <caffeine.version><latest></caffeine.version>
    <flamingock.version><latest></flamingock.version>
    <liquibase-mongodb.version><latest></liquibase-mongodb.version>
    <liquibase-couchbase.version><latest></liquibase-couchbase.version>
    <liquibase-neo4j.version><latest></liquibase-neo4j.version>
    <spring-cloud-aws.version><latest></spring-cloud-aws.version>
    <archunit.version><latest></archunit.version>

    <!-- Plugin versions. Pinned explicitly for reproducible builds even where the Boot parent also manages
         them — that override is deliberate and shared with the rest of this catalog's Java skills. -->
    <maven-enforcer-plugin.version>3.5.0</maven-enforcer-plugin.version>
    <maven-surefire-plugin.version>3.5.4</maven-surefire-plugin.version>
    <maven-failsafe-plugin.version>3.5.4</maven-failsafe-plugin.version>
    <maven-javadoc-plugin.version>3.11.3</maven-javadoc-plugin.version>
    <maven-checkstyle-plugin.version>3.6.0</maven-checkstyle-plugin.version>
    <maven-pmd-plugin.version>3.27.0</maven-pmd-plugin.version>
    <spotbugs-maven-plugin.version>4.9.6.0</spotbugs-maven-plugin.version>
    <jacoco-maven-plugin.version>0.8.13</jacoco-maven-plugin.version>
    <maven-jxr-plugin.version>3.6.0</maven-jxr-plugin.version>
    <maven-site-plugin.version>3.21.0</maven-site-plugin.version>
    <groovy-maven-plugin.version>2.1.1</groovy-maven-plugin.version>
    <sonar-maven-plugin.version><latest></sonar-maven-plugin.version>
    <openapi-generator-maven-plugin.version><latest></openapi-generator-maven-plugin.version>
    <protobuf-maven-plugin.version><from-reference-pom-or-latest></protobuf-maven-plugin.version>
    <avro-maven-plugin.version><latest></avro-maven-plugin.version>
    <!-- GraphQL SDL -> Java. The same version is ALSO used for the io.github.kobylynskyi:graphql-java-codegen
         runtime dependency that generated GraphQL *client* code extends; keep the two in lockstep. -->
    <graphql-codegen-maven-plugin.version><latest></graphql-codegen-maven-plugin.version>
    <!-- Runs the AsyncAPI documentation generators (npm-based) from the Maven build; see
         iru-setup-java-springboot-apis. Needed when messaging and/or a GraphQL server is enabled. -->
    <frontend-maven-plugin.version><latest></frontend-maven-plugin.version>
    <!-- Escape hatches for the two npm-driven documentation steps, so an offline build can opt out.
         CI must leave both false or the published documentation silently goes stale. -->
    <asyncapi.docs.skip>false</asyncapi.docs.skip>
    <graphql.docs.skip>false</graphql.docs.skip>

    <!-- Only when the manifest's frontend: hilla. vaadin.version pins both the vaadin-bom import below and the
         vaadin-maven-plugin pluginManagement entry, so the module (wired by iru-setup-java-springboot-hilla) and
         the root always agree on one version. vaadin.skip is the plugin's own documented escape hatch
         (verified: the plugin's own metadata declares `<skip>` bound to `${vaadin.skip}`, default false) so an
         analysis-only or offline build can pass -Dvaadin.skip=true and get a real compile without Node/npm. -->
    <vaadin.version><latest-release-from-maven-metadata></vaadin.version>
    <vaadin.skip>false</vaadin.skip>

    <!-- Analysis and coverage settings. The whole sonar.* block below is omitted, property for property,
         when the manifest's `sonar.mode: none` — a service with no Sonar wiring has no use for any of them,
         not just the identity properties. sonar.organization is normally omitted for `self-hosted` too, unless
         that server has organizations enabled — see the note after this template. -->
    <sonar.organization><sonar-organization></sonar.organization>
    <sonar.projectKey><owner>_<repo></sonar.projectKey>
    <sonar.host.url><sonar-host-url></sonar.host.url> <!-- https://sonarcloud.io for mode: cloud; manifest's sonar.hostUrl for mode: self-hosted -->
    <sonar.coverage.jacoco.xmlReportPaths>${maven.multiModuleProjectDirectory}/coverage/target/site/jacoco-aggregate/jacoco.xml</sonar.coverage.jacoco.xmlReportPaths>
    <!-- Generated sources are never the developer's code; keep them out of coverage and duplication metrics. -->
    <sonar.exclusions>**/generated-sources/**,**/generated/**</sonar.exclusions>
  </properties>

  <dependencyManagement>
    <dependencies>
      <!-- This project's own modules, so module poms never repeat ${project.version}. -->
      <dependency>
        <groupId>${project.groupId}</groupId>
        <artifactId><artifact-id>-domain</artifactId>
        <version>${project.version}</version>
      </dependency>
      <!-- ... one entry per module in the manifest's `modules:` list, same shape ... -->

      <!-- BOM imports copied from the Initializr reference pom (Spring Cloud, Spring AI, ...). -->
      <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-dependencies</artifactId>
        <version>${spring-cloud.version}</version>
        <type>pom</type>
        <scope>import</scope>
      </dependency>

      <!-- Only when the manifest's frontend: hilla. Not from the Initializr reference pom — Initializr's own
           "vaadin" dependency id resolves to a Flow-oriented starter combination, not this catalog's Hilla
           wiring, so this BOM import is added independently, version from Maven Central's vaadin-bom
           maven-metadata.xml (see the <vaadin.version> note above). -->
      <dependency>
        <groupId>com.vaadin</groupId>
        <artifactId>vaadin-bom</artifactId>
        <version>${vaadin.version}</version>
        <type>pom</type>
        <scope>import</scope>
      </dependency>

      <!-- Non-Initializr dependencies. Include only what the stack uses. -->
      <dependency>
        <groupId>org.mapstruct</groupId>
        <artifactId>mapstruct</artifactId>
        <version>${mapstruct.version}</version>
      </dependency>
      <dependency>
        <groupId>com.github.ben-manes.caffeine</groupId>
        <artifactId>caffeine</artifactId>
        <version>${caffeine.version}</version>
      </dependency>
      <dependency>
        <groupId>com.tngtech.archunit</groupId>
        <artifactId>archunit-junit5</artifactId>
        <version>${archunit.version}</version>
        <scope>test</scope>
      </dependency>
      <!-- ... the Flamingock BOM, the Liquibase extensions, and the AWS BOM as the stack requires ... -->
    </dependencies>
  </dependencyManagement>

  <dependencies>
    <!-- Project-wide: every module gets these. Nothing Spring-specific belongs here — `domain` inherits it too. -->
    <dependency>
      <groupId>org.projectlombok</groupId>
      <artifactId>lombok</artifactId>
      <optional>true</optional>
    </dependency>
    <dependency>
      <groupId>org.mapstruct</groupId>
      <artifactId>mapstruct</artifactId>
    </dependency>
    <!-- Test dependencies every module needs; artifact names taken from the reference pom. -->
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-test</artifactId>
      <scope>test</scope>
    </dependency>
    <dependency>
      <groupId>org.mockito</groupId>
      <artifactId>mockito-junit-jupiter</artifactId>
      <scope>test</scope>
    </dependency>
  </dependencies>

  <build>
    <pluginManagement>
      <plugins>
        <plugin>
          <groupId>org.openapitools</groupId>
          <artifactId>openapi-generator-maven-plugin</artifactId>
          <version>${openapi-generator-maven-plugin.version}</version>
        </plugin>
        <plugin>
          <groupId><protobuf-plugin-group-from-reference-pom></groupId>
          <artifactId>protobuf-maven-plugin</artifactId>
          <version>${protobuf-maven-plugin.version}</version>
        </plugin>
        <plugin>
          <groupId>org.apache.avro</groupId>
          <artifactId>avro-maven-plugin</artifactId>
          <version>${avro-maven-plugin.version}</version>
        </plugin>
        <plugin>
          <groupId>io.github.kobylynskyi</groupId>
          <artifactId>graphql-codegen-maven-plugin</artifactId>
          <version>${graphql-codegen-maven-plugin.version}</version>
        </plugin>
        <plugin>
          <groupId>com.github.eirslett</groupId>
          <artifactId>frontend-maven-plugin</artifactId>
          <version>${frontend-maven-plugin.version}</version>
        </plugin>
        <plugin>
          <groupId>org.springframework.boot</groupId>
          <artifactId>spring-boot-maven-plugin</artifactId>
        </plugin>
        <!-- Only when the manifest's frontend: hilla. The execution itself (which goals run, in which module)
             is wired by iru-setup-java-springboot-hilla into the boot module's pom — this pluginManagement
             entry only pins the version every such execution inherits. -->
        <plugin>
          <groupId>com.vaadin</groupId>
          <artifactId>vaadin-maven-plugin</artifactId>
          <version>${vaadin.version}</version>
        </plugin>
      </plugins>
    </pluginManagement>

    <plugins>
      <!-- Java 21 minimum, enforced at build time and not just declared in a property -->
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-enforcer-plugin</artifactId>
        <version>${maven-enforcer-plugin.version}</version>
        <executions>
          <execution>
            <id>enforce-java</id>
            <goals>
              <goal>enforce</goal>
            </goals>
            <configuration>
              <rules>
                <requireJavaVersion>
                  <version>[<java-version>,)</version>
                  <message>This project requires Java <java-version> or newer.</message>
                </requireJavaVersion>
                <requireMavenVersion>
                  <version>[3.9.0,)</version>
                </requireMavenVersion>
              </rules>
            </configuration>
          </execution>
        </executions>
      </plugin>

      <!-- Lombok and MapStruct annotation processors. lombok-mapstruct-binding is required for the two to
           coexist: without it MapStruct runs before Lombok has generated getters and produces empty mappers.
           Order matters — lombok, then the binding, then mapstruct-processor. -->
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-compiler-plugin</artifactId>
        <configuration>
          <release>${maven.compiler.release}</release>
          <parameters>true</parameters>
          <annotationProcessorPaths>
            <path>
              <groupId>org.projectlombok</groupId>
              <artifactId>lombok</artifactId>
              <version>${lombok.version}</version>
            </path>
            <path>
              <groupId>org.projectlombok</groupId>
              <artifactId>lombok-mapstruct-binding</artifactId>
              <version>${lombok-mapstruct-binding.version}</version>
            </path>
            <path>
              <groupId>org.mapstruct</groupId>
              <artifactId>mapstruct-processor</artifactId>
              <version>${mapstruct.version}</version>
            </path>
            <path>
              <groupId>org.springframework.boot</groupId>
              <artifactId>spring-boot-configuration-processor</artifactId>
              <version>${spring-boot.version}</version>
            </path>
          </annotationProcessorPaths>
          <compilerArgs>
            <arg>-Amapstruct.defaultComponentModel=spring</arg>
            <arg>-Amapstruct.unmappedTargetPolicy=ERROR</arg>
          </compilerArgs>
        </configuration>
      </plugin>

      <!-- Unit tests: *Test. Integration tests are Failsafe's, below, and never run here. -->
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-surefire-plugin</artifactId>
        <version>${maven-surefire-plugin.version}</version>
        <configuration>
          <includes>
            <include>**/*Test.java</include>
          </includes>
          <excludes>
            <exclude>**/*IT.java</exclude>
          </excludes>
        </configuration>
      </plugin>

      <!-- Integration tests: *IT, bound to verify. These are the Testcontainers-backed ones. -->
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-failsafe-plugin</artifactId>
        <version>${maven-failsafe-plugin.version}</version>
        <configuration>
          <includes>
            <include>**/*IT.java</include>
          </includes>
        </configuration>
        <executions>
          <execution>
            <id>integration-tests</id>
            <goals>
              <goal>integration-test</goal>
              <goal>verify</goal>
            </goals>
          </execution>
        </executions>
      </plugin>

      <!-- Coverage. Generated sources are excluded so codegen output can't inflate or deflate the number. -->
      <plugin>
        <groupId>org.jacoco</groupId>
        <artifactId>jacoco-maven-plugin</artifactId>
        <version>${jacoco-maven-plugin.version}</version>
        <configuration>
          <excludes>
            <exclude><base-package-path>/**/generated/**</exclude>
            <exclude>**/*MapperImpl.class</exclude>
            <exclude>**/*Application.class</exclude>
          </excludes>
        </configuration>
        <executions>
          <execution>
            <id>jacoco-initialize</id>
            <goals>
              <goal>prepare-agent</goal>
            </goals>
          </execution>
          <execution>
            <id>jacoco-initialize-it</id>
            <goals>
              <goal>prepare-agent-integration</goal>
            </goals>
          </execution>
          <execution>
            <id>jacoco-report</id>
            <phase>verify</phase>
            <goals>
              <goal>report</goal>
              <goal>report-integration</goal>
            </goals>
          </execution>
        </executions>
      </plugin>

      <!-- Static analysis. All three analyse hand-written sources only. -->
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-checkstyle-plugin</artifactId>
        <version>${maven-checkstyle-plugin.version}</version>
        <configuration>
          <configLocation>${checkstyle.config.location}</configLocation>
          <sourceDirectories>
            <sourceDirectory>${project.build.sourceDirectory}</sourceDirectory>
          </sourceDirectories>
          <includeTestSourceDirectory>true</includeTestSourceDirectory>
        </configuration>
      </plugin>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-pmd-plugin</artifactId>
        <version>${maven-pmd-plugin.version}</version>
        <configuration>
          <targetJdk>${maven.compiler.release}</targetJdk>
          <excludeRoots>
            <excludeRoot>${project.build.directory}/generated-sources</excludeRoot>
          </excludeRoots>
        </configuration>
      </plugin>
      <plugin>
        <groupId>com.github.spotbugs</groupId>
        <artifactId>spotbugs-maven-plugin</artifactId>
        <version>${spotbugs-maven-plugin.version}</version>
        <configuration>
          <excludeFilterFile>${maven.multiModuleProjectDirectory}/spotbugs-exclude.xml</excludeFilterFile>
        </configuration>
      </plugin>

      <!-- Maven site, the report aggregator -->
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-site-plugin</artifactId>
        <version>${maven-site-plugin.version}</version>
      </plugin>

      <!-- SonarCloud/SonarQube; omit this whole plugin entry when manifest `sonar.mode: none` -->
      <plugin>
        <groupId>org.sonarsource.scanner.maven</groupId>
        <artifactId>sonar-maven-plugin</artifactId>
        <version>${sonar-maven-plugin.version}</version>
      </plugin>
    </plugins>
  </build>

  <reporting>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-javadoc-plugin</artifactId>
        <version>${maven-javadoc-plugin.version}</version>
        <configuration>
          <show>private</show>
          <nohelp>true</nohelp>
          <detectJavaApiLink>true</detectJavaApiLink>
          <doclint>none</doclint>
        </configuration>
      </plugin>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-surefire-report-plugin</artifactId>
        <version>${maven-surefire-plugin.version}</version>
        <reportSets>
          <reportSet>
            <reports>
              <report>report</report>
              <report>failsafe-report-only</report>
            </reports>
          </reportSet>
        </reportSets>
      </plugin>
      <plugin>
        <groupId>org.jacoco</groupId>
        <artifactId>jacoco-maven-plugin</artifactId>
        <version>${jacoco-maven-plugin.version}</version>
      </plugin>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-checkstyle-plugin</artifactId>
        <version>${maven-checkstyle-plugin.version}</version>
        <configuration>
          <configLocation>${checkstyle.config.location}</configLocation>
        </configuration>
        <reportSets>
          <reportSet>
            <reports>
              <report>checkstyle</report>
            </reports>
          </reportSet>
        </reportSets>
      </plugin>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-pmd-plugin</artifactId>
        <version>${maven-pmd-plugin.version}</version>
      </plugin>
      <plugin>
        <groupId>com.github.spotbugs</groupId>
        <artifactId>spotbugs-maven-plugin</artifactId>
        <version>${spotbugs-maven-plugin.version}</version>
      </plugin>
      <!-- Cross-referenced source, so every report above can link straight to the offending line -->
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-jxr-plugin</artifactId>
        <version>${maven-jxr-plugin.version}</version>
      </plugin>
    </plugins>
  </reporting>

  <!-- Only when the manifest's frontend: hilla. `mvn package -Pproduction` builds the real Vite production
       bundle instead of leaving the frontend in dev-bundle mode; without it a packaged jar still works (Vaadin
       serves the dev bundle) but is not what should ship. See the profile note below the template. -->
  <profiles>
    <profile>
      <id>production</id>
      <properties>
        <vaadin.productionMode>true</vaadin.productionMode>
      </properties>
    </profile>
  </profiles>
</project>
```

Notes on filling this in:

- `${lombok.version}` and `${spring-boot.version}` are provided by `spring-boot-starter-parent` — don't redeclare
  them. `${maven.multiModuleProjectDirectory}` resolves to the reactor root from any module, which is what makes a
  single shared `checkstyle.xml` and `spotbugs-exclude.xml` work.
- Read `sonar.mode` from the manifest (defaulting to `cloud` when the field is absent, for backward compatibility
  with a manifest written before the `sonar:` block existed):
  - `sonar.mode: none` — drop the whole `sonar.*` properties block (all five properties, not just the identity
    ones) and the `sonar-maven-plugin` entry rather than leaving empty placeholders.
  - `sonar.mode: cloud` — keep today's behaviour: `<sonar.host.url>https://sonarcloud.io</sonar.host.url>`, and
    `<sonar.organization>`/`<sonar.projectKey>` from the manifest's `sonar.organization`/`sonar.projectKey`
    (falling back to `<owner>-github`/`<owner>_<repo>` if the manifest left them unset).
  - `sonar.mode: self-hosted` — write the manifest's `sonar.hostUrl` into `<sonar.host.url>` instead of
    `https://sonarcloud.io`, and `sonar.projectKey` into `<sonar.projectKey>` as usual. **Judgment call**: a
    self-hosted SonarQube instance typically has organizations disabled (that concept is SonarCloud/SonarQube
    Server-multi-tenant specific), so omit the `<sonar.organization>` property unless the manifest actually set
    `sonar.organization` (i.e. the user confirmed that server has organizations enabled in
    `iru-setup-java-springboot`'s Step 3b) — don't emit an empty or guessed value.
  - The manifest's `ci:` block doesn't change any of this: with `ci.enabled: false` and a `sonar.mode` other than
    `none` (the user kept Sonar despite having no CI), still write the properties and plugin exactly as above —
    they're what a manual `mvn sonar:sonar -Dsonar.token=…` run needs — and add an XML comment above the
    `sonar.*` block saying no CI workflow sends reports. `ci.tests: unit` only affects coverage content (the
    aggregate then holds unit-test data in CI), not the report paths.
- Look up the current version for every `<latest>` marker (Maven Central's search API) rather than guessing —
  and record what you resolved, so Step 8 can report it.
- Also write `spotbugs-exclude.xml` at the repository root, excluding the generated-source packages (the
  OpenAPI/protobuf/AVRO output) — SpotBugs analyses bytecode, so `excludeRoots` doesn't help it the way it helps
  PMD, and generated DTOs will otherwise produce a large permanent finding list.
- Read `frontend` from the manifest (absent or `none` means no Hilla wiring, same backward-compatibility rule as
  `sonar.mode`): only when it's `hilla` do the `<vaadin.version>`/`<vaadin.skip>` properties, the `vaadin-bom`
  `dependencyManagement` import, the `vaadin-maven-plugin` `pluginManagement` entry, and the `production` profile
  belong in the pom — omit all four, property for property, when it's `none`. Resolve `<vaadin.version>` from
  `https://repo1.maven.org/maven2/com/vaadin/vaadin-bom/maven-metadata.xml`'s `<versions>` list: use the newest
  entry with no pre-release suffix (`-alpha`/`-beta`/`-rc`), since that metadata's own `<release>`/`<latest>`
  tags can point at a release candidate. This skill owns writing these four root-pom pieces; if it's run again
  after `iru-setup-java-springboot-hilla` already filled them in as a standalone-run fallback (see that skill's
  Step 1), treat the existing values as correct and don't regenerate them from scratch unless they're actually
  wrong. The `production` profile's `vaadin.productionMode=true` and the plugin's own `vaadin.skip` property were
  both confirmed against the plugin's own Maven metadata (`<skip implementation="boolean"
  default-value="false">${vaadin.skip}</skip>`) rather than assumed from documentation.

## Step 1K — Kotlin on Maven: deltas to the root pom

Only when `project.language: kotlin` and `project.buildTool: maven`. Start from Step 1's template and apply the
changes below; everything not mentioned (parent, identity, `<modules>`, BOM imports, codegen `pluginManagement`,
enforcer, Surefire/Failsafe, JaCoCo executions, site, Sonar host/identity, the Hilla pieces) stays exactly as in
Step 1. Every snippet here was built in a throwaway 3-module reactor (`domain`, `application`, `boot` with mixed
Java + Kotlin sources, `coverage`) on Boot 4.1.1 / Kotlin 2.3.21 / JDK 21: `mvn verify` ran unit tests, a
`*IT` through Failsafe, detekt, ktlint and the aggregate report (Kotlin and Java classes, unit + IT data);
`mvn detekt:check ktlint:check` and `mvn compile dokka:dokka` ran standalone; detekt and ktlint each failed the
build on a planted violation.

**Remove** (they have no Kotlin meaning, or are replaced below): the root `<dependencies>` entries for `lombok`,
`mapstruct` and `mockito-junit-jupiter`; the `mapstruct.version` and `lombok-mapstruct-binding.version`
properties and the MapStruct `dependencyManagement` entry; the whole `annotationProcessorPaths`/`compilerArgs`
configuration of `maven-compiler-plugin` (replaced below); the Checkstyle, PMD and SpotBugs plugins in both
`<build>` and `<reporting>`, `maven-javadoc-plugin` in `<reporting>`, and their four version properties; the
`**/*MapperImpl.class` JaCoCo exclude.

**Properties** — add, next to the other plugin/library versions:

```xml
    <!-- From the manifest's project.kotlinVersion — the version Spring Boot manages; overriding the parent's
         kotlin.version keeps kotlin-stdlib/-reflect/-test and the kotlin-maven-plugin on one version. -->
    <kotlin.version><kotlin-version></kotlin.version>
    <kotlin.compiler.jvmTarget>${java.version}</kotlin.compiler.jvmTarget>
    <mockk.version><latest></mockk.version>
    <!-- springmockk 5.x is the line built for Spring Boot 4 / Spring Framework 7 (4.x targets Boot 3). -->
    <springmockk.version><latest-5.x></springmockk.version>
    <detekt-maven-plugin.version><latest></detekt-maven-plugin.version>
    <ktlint-maven-plugin.version><latest></ktlint-maven-plugin.version>
    <dokka-maven-plugin.version><latest></dokka-maven-plugin.version>
```

Resolve each `<latest>` from Maven Central's `maven-metadata.xml` (newest version without an
`-alpha`/`-beta`/`-RC`/`-M` suffix): `io/mockk/mockk-jvm`, `com/ninja-squad/springmockk`,
`com/github/ozsie/detekt-maven-plugin`, `com/github/gantsign/maven/ktlint-maven-plugin`,
`org/jetbrains/dokka/dokka-maven-plugin`. As of this writing: 1.14.11, 5.0.1, 1.23.8, 3.7.1, 2.2.0. (detekt
1.23.x embeds its own Kotlin 2.0 compiler to parse sources; it analyses Kotlin 2.3 code fine and ran on JDK 21
and 26. detekt 2.x is still alpha and has no Maven plugin release — don't use it.)

Unless `sonar.mode: none`, add to the `sonar.*` block (all relative paths resolve per module):

```xml
    <!-- Explicit because `mvn sonar:sonar` runs standalone in CI, before kotlin-maven-plugin has registered
         src/main/kotlin as a source root. Paths must exist in every jar module (Step 4 creates them); pom-packaged
         modules ignore missing ones. A module that also has Java sources overrides these two in its own pom. -->
    <sonar.sources>src/main/kotlin</sonar.sources>
    <sonar.tests>src/test/kotlin</sonar.tests>
    <sonar.kotlin.detekt.reportPaths>target/detekt.xml</sonar.kotlin.detekt.reportPaths>
    <sonar.kotlin.ktlint.reportPaths>target/ktlint.xml</sonar.kotlin.ktlint.reportPaths>
```

`sonar.coverage.jacoco.xmlReportPaths` and `sonar.exclusions` stay as in Step 1.

**`dependencyManagement`** — add (scope `test`, like ArchUnit):

```xml
      <dependency>
        <groupId>io.mockk</groupId>
        <artifactId>mockk-jvm</artifactId>   <!-- not io.mockk:mockk: that one is a Gradle-metadata-only umbrella -->
        <version>${mockk.version}</version>
        <scope>test</scope>
      </dependency>
      <dependency>
        <groupId>com.ninja-squad</groupId>
        <artifactId>springmockk</artifactId>
        <version>${springmockk.version}</version>
        <scope>test</scope>
      </dependency>
```

**Root `<dependencies>`** — replace the Java project-wide set with (versions all come from the Boot BOM or the
entries above; nothing Spring-specific, since `domain` inherits it too):

```xml
    <dependency>
      <groupId>org.jetbrains.kotlin</groupId>
      <artifactId>kotlin-stdlib</artifactId>
    </dependency>
    <!-- Spring uses Kotlin reflection for constructor binding, default values and nullability. -->
    <dependency>
      <groupId>org.jetbrains.kotlin</groupId>
      <artifactId>kotlin-reflect</artifactId>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-test</artifactId>
      <scope>test</scope>
    </dependency>
    <dependency>
      <groupId>org.jetbrains.kotlin</groupId>
      <artifactId>kotlin-test-junit5</artifactId>
      <scope>test</scope>
    </dependency>
    <dependency>
      <groupId>io.mockk</groupId>
      <artifactId>mockk-jvm</artifactId>
      <scope>test</scope>
    </dependency>
    <!-- Only when stack.concurrency is reactive or both: suspend ports in domain, runTest in every test. -->
    <dependency>
      <groupId>org.jetbrains.kotlinx</groupId>
      <artifactId>kotlinx-coroutines-core</artifactId>
    </dependency>
    <dependency>
      <groupId>org.jetbrains.kotlinx</groupId>
      <artifactId>kotlinx-coroutines-test</artifactId>
      <scope>test</scope>
    </dependency>
```

`jackson-module-kotlin` is **not** project-wide — `domain` must stay free of Jackson; Step 2's Kotlin note places
it. Initializr's Kotlin pom lists `lombok` and `spring-boot-configuration-processor` when the Java defaults asked
for them; drop both (no kapt in this build).

**Compilation** — insert, in `<build><plugins>` right after the enforcer, replacing Step 1's
`maven-compiler-plugin` entry. `spring-boot-starter-parent` already manages the `kotlin-maven-plugin` version
and pre-configures `jvmTarget`/`javaParameters` and the two executions — but none of the compiler plugins:

```xml
      <!-- kotlinc first, over both source roots, so Java code may reference Kotlin and vice versa. -->
      <plugin>
        <groupId>org.jetbrains.kotlin</groupId>
        <artifactId>kotlin-maven-plugin</artifactId>
        <configuration>
          <jvmTarget>${kotlin.compiler.jvmTarget}</jvmTarget>
          <javaParameters>true</javaParameters>
          <args>
            <!-- Spring's nullability annotations become real Kotlin nullability. -->
            <arg>-Xjsr305=strict</arg>
            <!-- Copied from Initializr's Kotlin pom: the Kotlin 2.2+ default-target rule for annotations on
                 constructor properties (parameter, then property/field), which validation and Jackson rely on. -->
            <arg>-Xannotation-default-target=param-property</arg>
          </args>
          <compilerPlugins>
            <plugin>spring</plugin>   <!-- all-open for @Component/@Transactional/@Configuration/... -->
            <plugin>jpa</plugin>      <!-- no-arg constructors for @Entity/@MappedSuperclass/@Embeddable -->
            <plugin>all-open</plugin> <!-- open entities so Hibernate's lazy proxies work -->
          </compilerPlugins>
          <pluginOptions>
            <option>all-open:annotation=jakarta.persistence.Entity</option>
            <option>all-open:annotation=jakarta.persistence.MappedSuperclass</option>
            <option>all-open:annotation=jakarta.persistence.Embeddable</option>
          </pluginOptions>
        </configuration>
        <dependencies>
          <dependency>
            <groupId>org.jetbrains.kotlin</groupId>
            <artifactId>kotlin-maven-allopen</artifactId>
            <version>${kotlin.version}</version>
          </dependency>
          <dependency>
            <groupId>org.jetbrains.kotlin</groupId>
            <artifactId>kotlin-maven-noarg</artifactId>
            <version>${kotlin.version}</version>
          </dependency>
        </dependencies>
        <executions>
          <execution>
            <id>compile</id>
            <phase>compile</phase>
            <goals>
              <goal>compile</goal>
            </goals>
            <configuration>
              <sourceDirs>
                <sourceDir>${project.basedir}/src/main/kotlin</sourceDir>
                <sourceDir>${project.basedir}/src/main/java</sourceDir>
              </sourceDirs>
            </configuration>
          </execution>
          <execution>
            <id>test-compile</id>
            <phase>test-compile</phase>
            <goals>
              <goal>test-compile</goal>
            </goals>
            <configuration>
              <sourceDirs>
                <sourceDir>${project.basedir}/src/test/kotlin</sourceDir>
                <sourceDir>${project.basedir}/src/test/java</sourceDir>
              </sourceDirs>
            </configuration>
          </execution>
        </executions>
      </plugin>

      <!-- javac after kotlinc: the lifecycle-bound default executions would otherwise run first and fail on any
           Java class that references a Kotlin one. Declaring kotlin-maven-plugin first is not enough on its own. -->
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-compiler-plugin</artifactId>
        <configuration>
          <release>${maven.compiler.release}</release>
          <parameters>true</parameters>
        </configuration>
        <executions>
          <execution>
            <id>default-compile</id>
            <phase>none</phase>
          </execution>
          <execution>
            <id>default-testCompile</id>
            <phase>none</phase>
          </execution>
          <execution>
            <id>java-compile</id>
            <phase>compile</phase>
            <goals>
              <goal>compile</goal>
            </goals>
          </execution>
          <execution>
            <id>java-test-compile</id>
            <phase>test-compile</phase>
            <goals>
              <goal>testCompile</goal>
            </goals>
          </execution>
        </executions>
      </plugin>
```

Don't set `<sourceDirectory>src/main/kotlin</sourceDirectory>` the way a pure-Kotlin Initializr pom does: it
silently drops `src/main/java` from `javac`, and the mixed-source modules this catalog allows (generated Java
DTOs, a Java adapter) then fail at runtime. Surefire's `**/*Test.java` / Failsafe's `**/*IT.java` patterns stay
as they are — both plugins match them against compiled classes, so Kotlin `*Test`/`*IT` classes run (verified).
JaCoCo's `<excludes>` gains `<exclude>**/generated/**</exclude>` (generated Kotlin/Java packages wherever the
generators put them) and `<exclude>**/*ApplicationKt.class</exclude>` (the file class holding `main`).

**Generated code is never analysed.** Everything the OpenAPI/protobuf/AVRO/GraphQL generators write lands under
`target/generated-sources/**` in packages containing a `generated` segment; the templates below keep it out of
every tool: detekt's `<input>` and ktlint's source roots list only `src/*/kotlin` (plus detekt's
`**/generated/**` exclude), Dokka's `sourceDirectories` lists only `src/main/kotlin`, JaCoCo excludes
`**/generated/**`, and Sonar's `sonar.exclusions` (Step 1) already covers `**/generated-sources/**,**/generated/**`.

**Quality and documentation** — insert in `<build><plugins>` where Step 1 had Checkstyle/PMD/SpotBugs. All three
must be in `<build><plugins>` (not only `pluginManagement`, and not in a profile): the generated CI calls
`mvn detekt:check ktlint:check dokka:dokka` by prefix, and the Dokka Maven plugin additionally refuses to run
(`Not found dokka plugin`) when it is only declared in `pluginManagement` (verified).

```xml
      <!-- detekt: fails the build on any finding (maxIssues: 0 in detekt.yml), like Checkstyle/PMD/SpotBugs do
           for Java. Bound to verify; the XML report is what Sonar imports. -->
      <plugin>
        <groupId>com.github.ozsie</groupId>
        <artifactId>detekt-maven-plugin</artifactId>
        <version>${detekt-maven-plugin.version}</version>
        <configuration>
          <config>${maven.multiModuleProjectDirectory}/detekt.yml</config>
          <buildUponDefaultConfig>true</buildUponDefaultConfig>
          <input>${project.basedir}/src/main/kotlin,${project.basedir}/src/test/kotlin</input>
          <excludes>**/generated/**,**/generated-sources/**</excludes>
          <report>
            <report>xml:${project.build.directory}/detekt.xml</report>
            <report>html:${project.build.directory}/detekt.html</report>
          </report>
        </configuration>
        <executions>
          <execution>
            <id>detekt</id>
            <phase>verify</phase>
            <goals>
              <goal>check</goal>
            </goals>
          </execution>
        </executions>
      </plugin>

      <!-- ktlint: formatting/style, failOnViolation defaults to true. Rules come from .editorconfig (Step 5).
           Source roots are explicit so a standalone `mvn ktlint:check` (no compile first) still sees Kotlin;
           generated sources live under target/ and are never listed. `mvn ktlint:format` fixes most findings. -->
      <plugin>
        <groupId>com.github.gantsign.maven</groupId>
        <artifactId>ktlint-maven-plugin</artifactId>
        <version>${ktlint-maven-plugin.version}</version>
        <configuration>
          <sourceRoots>
            <sourceRoot>${project.basedir}/src/main/kotlin</sourceRoot>
          </sourceRoots>
          <testSourceRoots>
            <testSourceRoot>${project.basedir}/src/test/kotlin</testSourceRoot>
          </testSourceRoots>
          <includeScripts>false</includeScripts>
          <reporters>
            <reporter>
              <name>plain</name>
            </reporter>
            <reporter>
              <name>checkstyle</name>
              <output>${project.build.directory}/ktlint.xml</output>
            </reporter>
          </reporters>
        </configuration>
        <executions>
          <execution>
            <id>ktlint</id>
            <phase>verify</phase>
            <goals>
              <goal>check</goal>
            </goals>
          </execution>
        </executions>
      </plugin>

      <!-- Dokka replaces Javadoc: `mvn compile dokka:dokka` writes <module>/target/dokka (no execution bound, so
           ordinary builds don't pay for it). -->
      <plugin>
        <groupId>org.jetbrains.dokka</groupId>
        <artifactId>dokka-maven-plugin</artifactId>
        <version>${dokka-maven-plugin.version}</version>
        <configuration>
          <jdkVersion>${java.version}</jdkVersion>
          <sourceDirectories>
            <dir>${project.basedir}/src/main/kotlin</dir>
          </sourceDirectories>
          <documentedVisibilities>
            <visibility>PUBLIC</visibility>
            <visibility>PROTECTED</visibility>
            <visibility>INTERNAL</visibility>
          </documentedVisibilities>
        </configuration>
      </plugin>
```

**`<reporting>`** — the site keeps Surefire/Failsafe, JaCoCo and JXR exactly as in Step 1, drops Javadoc,
Checkstyle, PMD and SpotBugs, and adds the ktlint report (the plugin is also a Maven reporting plugin); detekt and
Dokka have no site report, so the site links nothing for them and the CI publishes `target/dokka` directly:

```xml
      <plugin>
        <groupId>com.github.gantsign.maven</groupId>
        <artifactId>ktlint-maven-plugin</artifactId>
        <version>${ktlint-maven-plugin.version}</version>
      </plugin>
```

## Step 2 — Where each dependency belongs

Use this to place every artifact extracted in Step 0. The point is that a dependency lands in exactly one module,
so the hexagonal boundaries are enforced by the classpath and not merely by convention.

| Module | Owns these dependencies |
|---|---|
| `domain` | Nothing Spring, nothing infrastructural. Plain Java plus `jakarta.validation-api` if the domain uses constraint annotations, plus the shared Lombok/MapStruct/test dependencies inherited from the root. This module defines the **ports** (interfaces) — repositories, event publishers, clients, metrics — and knows no implementation. |
| `application` | `<a>-domain`. Optionally `spring-context`/`spring-tx` if use cases need `@Service`/`@Transactional`; prefer keeping even this out and wiring in `boot` when practical. |
| `infrastructure/database/<engine>` | `<a>-domain` plus that engine's Spring Data starter and driver, plus its migration tooling (Flamingock, Liquibase + the relevant extension, or Flyway) and its Testcontainers module (`test` scope). One engine per module — never two. |
| `infrastructure/configuration` | `<a>-domain`, `spring-boot-starter` (for `@ConfigurationProperties`), `spring-boot-configuration-processor`, and the dynamic-configuration starter the manifest names (Spring Cloud Kubernetes Config, AWS Secrets Manager, or Spring Cloud Config Client + Bus). |
| `infrastructure/clients/<name>` | `<a>-domain` plus the HTTP client starter (`spring-restclient`/`spring-webclient`) for a REST client, the gRPC client starter for a gRPC one, or `spring-boot-starter-graphql` (for `HttpGraphQlClient`/`HttpSyncGraphQlClient`) **and** `io.github.kobylynskyi:graphql-java-codegen` at compile scope for a GraphQL one — that last artifact supplies the base classes the generated request/projection classes extend, and without it the module generates and then fails to compile. A downstream service reached over more than one protocol keeps one module with one generator execution per protocol. Also the OpenAPI, protobuf or GraphQL generator plugin execution for that client's own contract, and — at `test` scope — the Testcontainers module for whichever API mock `stack.apiMock` names (`io.github.microcks:microcks-testcontainers` or the WireMock Testcontainers module), so this module's own `*IT` can start just the mock instead of the whole compose stack. |
| `infrastructure/producers` | `<a>-domain`, `spring-cloud-stream`, `spring-cloud-stream-binder-kafka`, the AVRO serializer (`io.confluent:kafka-avro-serializer`) and `org.apache.avro:avro`, plus the AVRO generator plugin execution. |
| `infrastructure/metrics` | `<a>-domain`, `spring-boot-starter-actuator`, `micrometer-registry-prometheus` (and `micrometer-registry-otlp` if selected). |
| `api/rest-server` | `<a>-application`, `<a>-domain`, `spring-boot-starter-webmvc`/`-webflux` (whatever the reference pom names), `spring-boot-starter-validation`, plus the OpenAPI generator execution for `apis/rest-server/`. Add the Spring Security starters here if the service authorizes incoming HTTP. |
| `api/grpc-server` | `<a>-application`, `<a>-domain`, the gRPC server starter, plus the protobuf generator execution for `apis/grpc-server/`. |
| `api/graphql-server` | `<a>-application`, `<a>-domain`, `spring-boot-starter-graphql`, **and** the web transport starter the reference pom names for `stack.concurrency` (`spring-boot-starter-webmvc`/`-web` or `-webflux`) — the GraphQL starter carries no HTTP transport of its own — plus `spring-boot-starter-validation`, `spring-boot-starter-graphql-test` at `test` scope, the `graphql-codegen-maven-plugin` execution for `apis/graphql-server/`, the `maven-resources-plugin` execution that copies the SDL to `target/classes/graphql/` for runtime schema loading, and the `frontend-maven-plugin` executions that generate the SpectaQL reference (and optional Voyager schema graph) into `target/generated-docs/graphql-server/`. |
| `api/consumers` | `<a>-application`, `<a>-domain`, `spring-cloud-stream`, the Kafka binder, the AVRO serializer, plus the AVRO generator execution. |
| `boot` | Every other module, `spring-boot-starter`, the Spring AI starters if any, and anything Step 0 couldn't place. This is the only module with `spring-boot-maven-plugin` and the only one that produces an executable artifact. |
| `coverage` | Every other module at `test` scope, for JaCoCo `report-aggregate` only. No sources of its own. |

`spring-boot-docker-compose` (runtime, optional) belongs in `boot` — it starts the local compose stack
automatically during development.

**Kotlin (Maven and Gradle)** — the same table, with these additions (scopes map to Gradle configurations as
compile → `implementation`, runtime → `runtimeOnly`, test → `testImplementation`, optional → `compileOnly`):

- `tools.jackson.module:jackson-module-kotlin` (Boot 4 / Jackson 3; `com.fasterxml.jackson.module` on Boot 3) in
  `boot` and in every module that (de)serializes JSON itself — `api/rest-server`, `api/graphql-server`, each REST
  or GraphQL `infrastructure/clients/<name>`, `infrastructure/producers`, `api/consumers`. Never in `domain`.
- `org.jetbrains.kotlinx:kotlinx-coroutines-reactor` (Boot-managed) in every module that bridges Reactor types —
  WebFlux `api/*` modules, reactive Spring Data adapters, WebClient clients — when `stack.concurrency` is
  `reactive` or `both`. (`kotlinx-coroutines-core`/`-test` are project-wide in that case, so `domain` has them.)
- `org.springframework.cloud:spring-cloud-context` (Spring Cloud BOM) in `infrastructure/configuration` whenever
  `stack.dynamicConfig` isn't `none` — `@RefreshScope` lives there.
- `com.ninja-squad:springmockk` (test) in every module with Spring slice or `@SpringBootTest` tests — at least
  `boot` and the `api/*` modules; `com.tngtech.archunit:archunit-junit5` (test) in `boot`, which holds the ArchUnit
  test — on Gradle that test is the **only** boundary check.
- `org.springframework.boot:spring-boot-testcontainers`, `org.testcontainers:testcontainers-junit-jupiter` and the
  engine's `org.testcontainers:testcontainers-<engine>` (Testcontainers 2.x ids, from the reference build) at
  test scope in every module that holds `*IT` tests — each `infrastructure/database/<engine>`, the `api/*`
  modules, `boot`.
- No `lombok`, `mapstruct`, `spring-boot-configuration-processor` anywhere.

## Step 3 — Module pom template

Every module pom follows this shape. Note the complete absence of `<version>` on dependencies.

```xml
<project xmlns="http://maven.apache.org/POM/4.0.0"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>

  <parent>
    <groupId><group-id></groupId>
    <artifactId><parent-artifact-id></artifactId>
    <version><version></version>
    <relativePath><relative-path-to-parent-pom></relativePath>
  </parent>

  <artifactId><artifact-id>-<module-suffix></artifactId>
  <packaging>jar</packaging>
  <name>${project.groupId}:${project.artifactId}</name>
  <description><what this module is responsible for></description>

  <dependencies>
    <!-- Only what this module needs, per Step 2's table. No <version> anywhere. -->
  </dependencies>
</project>
```

- `<relativePath>` is `../pom.xml` for a top-level module, `../../pom.xml` for an `infrastructure/*` or `api/*`
  module, `../../../pom.xml` for an `infrastructure/database/<engine>` or `infrastructure/clients/<name>` module.
- The intermediate aggregators (`infrastructure/pom.xml`, `infrastructure/database/pom.xml`,
  `infrastructure/clients/pom.xml`, `api/pom.xml`) use `<packaging>pom</packaging>`, carry `<modules>` and no
  `<dependencies>`, and are pure grouping.
- **Kotlin + Maven**: module poms are identical — the Kotlin compiler, detekt, ktlint, Dokka, JaCoCo and the
  enforcer all come from the root. The one per-module addition: a jar module that also has Java sources
  (`src/main/java` exists — e.g. a hand-written Java adapter) overrides the root's Sonar source lists, unless
  `sonar.mode: none`:

  ```xml
  <properties>
    <sonar.sources>src/main/kotlin,src/main/java</sonar.sources>
    <sonar.tests>src/test/kotlin</sonar.tests> <!-- add ,src/test/java only if that directory exists -->
  </properties>
  ```

  Generated Java (OpenAPI/protobuf/AVRO output under `target/generated-sources`) needs no override — it is
  compiled through the generator plugins' own source roots and excluded from analysis anyway.

### Enforcing the dependency direction

Add a `banned-dependencies` enforcer execution to each module so a violation of the hexagon fails the build
instead of being caught in review. In `domain/pom.xml`:

```xml
<build>
  <plugins>
    <plugin>
      <groupId>org.apache.maven.plugins</groupId>
      <artifactId>maven-enforcer-plugin</artifactId>
      <executions>
        <execution>
          <id>enforce-domain-purity</id>
          <goals>
            <goal>enforce</goal>
          </goals>
          <configuration>
            <rules>
              <bannedDependencies>
                <searchTransitive>false</searchTransitive>
                <excludes>
                  <exclude>org.springframework:*</exclude>
                  <exclude>org.springframework.boot:*</exclude>
                  <exclude>org.springframework.data:*</exclude>
                  <exclude>${project.groupId}:<artifact-id>-application</exclude>
                  <exclude>${project.groupId}:<artifact-id>-infrastructure-*</exclude>
                  <exclude>${project.groupId}:<artifact-id>-api-*</exclude>
                </excludes>
                <!-- The root pom gives every module spring-boot-starter-test (test scope), which matches
                     org.springframework.boot:* above; without this include the rule fails on every build. -->
                <includes>
                  <include>org.springframework.boot:spring-boot-starter-test:*:*:test</include>
                </includes>
                <message>The domain module must not depend on Spring or on any outer module. Define a port
                  (interface) here and implement it in the adapter module instead.</message>
              </bannedDependencies>
            </rules>
          </configuration>
        </execution>
      </executions>
    </plugin>
  </plugins>
</build>
```

Apply the same idea to the others, banning what each must not see:

- `application` — must not see any `infrastructure-*` or `api-*` module.
- `infrastructure/*` — must not see `application`, `api-*`, or a sibling `infrastructure-*` module.
- `api/*` — must not see any `infrastructure-*` module.
- `boot` — nothing banned; it is the composition root.

Note in Step 8 that banning `org.springframework:*` in `domain` is a deliberately strict DDD stance and the one
rule a team may reasonably want to relax (e.g. to use `spring-context` annotations in domain services); relaxing
it is a one-line change, whereas noticing the leak later is not.

### `coverage/pom.xml`

```xml
  <artifactId><artifact-id>-coverage</artifactId>
  <packaging>pom</packaging>
  <name>${project.groupId}:${project.artifactId}</name>
  <description>JaCoCo coverage aggregation across every module. No sources of its own.</description>

  <dependencies>
    <!-- one test-scope entry per module whose coverage should be aggregated -->
    <dependency>
      <groupId>${project.groupId}</groupId>
      <artifactId><artifact-id>-domain</artifactId>
    </dependency>
    <!-- ... -->
  </dependencies>

  <build>
    <plugins>
      <plugin>
        <groupId>org.jacoco</groupId>
        <artifactId>jacoco-maven-plugin</artifactId>
        <executions>
          <execution>
            <id>aggregate-report</id>
            <phase>verify</phase>
            <goals>
              <goal>report-aggregate</goal>
            </goals>
            <configuration>
              <dataFileIncludes>
                <dataFileInclude>**/jacoco*.exec</dataFileInclude>
              </dataFileIncludes>
              <outputDirectory>${project.build.directory}/site/jacoco-aggregate</outputDirectory>
            </configuration>
          </execution>
        </executions>
      </plugin>
    </plugins>
  </build>
```

`coverage` must be the **last** `<module>` in the root pom so every other module's `jacoco.exec` already exists
when `report-aggregate` runs. `dataFileIncludes` picks up both the unit (`jacoco.exec`) and integration
(`jacoco-it.exec`) execution data, so the aggregate — which is what Sonar reads — reflects both.

### `boot/pom.xml`

Additionally carries the executable-artifact and build-info plugins:

```xml
  <build>
    <plugins>
      <plugin>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-maven-plugin</artifactId>
        <configuration>
          <mainClass><base-package>.<ServiceName>Application</mainClass>
          <image>
            <name><image-registry>/<artifact-id>:${project.version}</name>
          </image>
        </configuration>
        <executions>
          <execution>
            <goals>
              <goal>repackage</goal>
            </goals>
          </execution>
        </executions>
      </plugin>

      <!-- Writes build-info.properties into this module's resources, the same house pattern as
           iru-setup-java-library, so the running service can report exactly what was deployed. -->
      <plugin>
        <groupId>org.codehaus.gmaven</groupId>
        <artifactId>groovy-maven-plugin</artifactId>
        <version>${groovy-maven-plugin.version}</version>
        <executions>
          <execution>
            <phase>validate</phase>
            <goals>
              <goal>execute</goal>
            </goals>
            <configuration>
              <source>
                <![CDATA[
                import java.util.Date
                import java.util.Properties
                import java.text.SimpleDateFormat
                import java.io.File
                import java.io.FileWriter

                println("Saving build info...")
                def dateFormatter = new SimpleDateFormat("yy-MM-dd HH:mm:ss")
                def buildTimestamp = dateFormatter.format(new Date())

                String groupId = "${project.groupId}"
                String artifactId = "${project.artifactId}"
                String version = "${project.version}"

                //GITHUB ACTIONS
                def buildNumber = System.getenv("GITHUB_RUN_NUMBER")
                def commit = System.getenv("GITHUB_SHA")
                def branch = System.getenv("GITHUB_REF_NAME")

                //JENKINS
                if (buildNumber == null) {
                  buildNumber = System.getenv("BUILD_NUMBER")
                }
                if (commit == null) {
                  commit = System.getenv("GIT_COMMIT")
                }
                if (branch == null) {
                  branch = System.getenv("GIT_BRANCH")
                }

                //GITLAB
                if (buildNumber == null) {
                  buildNumber = System.getenv("CI_JOB_ID")
                }
                if (commit == null) {
                  commit = System.getenv("CI_COMMIT_SHA")
                }
                if (branch == null) {
                  branch = System.getenv("CI_COMMIT_REF_NAME")
                }

                def props = new Properties()
                props.setProperty("BUILD_TIMESTAMP", buildTimestamp)
                props.setProperty("GROUP_ID", groupId)
                props.setProperty("ARTIFACT_ID", artifactId)
                props.setProperty("VERSION", version)
                if (buildNumber != null) {
                  props.setProperty("BUILD_NUMBER", buildNumber)
                }
                if (commit != null) {
                  props.setProperty("COMMIT", commit)
                }
                if (branch != null) {
                  props.setProperty("BRANCH", branch)
                }

                File dir = new File("${project.basedir}/src/main/resources/<base-package-path>")
                dir.mkdirs()
                File file = new File(dir, "build-info.properties")
                FileWriter writer = new FileWriter(file)
                props.store(writer, null)
                writer.close()
                println("Build info saved at " + file)
                ]]>
              </source>
            </configuration>
          </execution>
        </executions>
      </plugin>
    </plugins>
  </build>
```

`<base-package-path>` is the base package with dots replaced by slashes. The GitHub Actions branch is listed
first because that's what this catalog's generated workflows actually run under; the Jenkins/GitLab fallbacks are
kept from the `iru-setup-java-library` template so the same file works in a mirrored pipeline.

## Step 4 — Write the poms

Write the root pom, every aggregator pom, and every module pom named in the manifest's `modules:` list. Create the
directories as needed. Don't create source files here — that's `iru-setup-java-springboot-modules`; a pom for a
module with no sources yet is valid and builds cleanly.

**Kotlin + Maven**, unless `sonar.mode: none`: also create `src/main/kotlin/` and `src/test/kotlin/` in every
`jar` module, each with an empty `.gitkeep` so the directory survives a fresh clone — the explicit `sonar.sources`
/`sonar.tests` from Step 1K make `mvn sonar:sonar` fail with "The directory … does not exist" for a jar module
missing either one (the scanner only tolerates missing paths in `pom` modules). That is the only non-build file
this step writes; sources still belong to `iru-setup-java-springboot-modules`.

## Step 5 — Write the shared analysis configuration

Java writes `checkstyle.xml` and `spotbugs-exclude.xml`; Kotlin (Maven or Gradle) writes `detekt.yml` and
`.editorconfig` instead (last bullet).

- **`checkstyle.xml`** at the repository root, if absent (an existing one follows Step 0's answer — Keep by
  default). Start from Sun or Google checks with the rules a Spring
  Boot service realistically can't satisfy relaxed (line length raised to 120, `JavadocPackage`/`HideUtilityClassConstructor`
  dropped, `FinalParameters` dropped). A ruleset the build immediately fails on gets disabled by the first
  developer who hits it, which is worse than a lenient one that stays enabled.
- **`spotbugs-exclude.xml`** at the repository root, if absent (an existing one follows Step 0's answer — Keep by
  default; on Update, add the generated-source matches below if missing), excluding the generated-source packages:

  ```xml
  <FindBugsFilter>
    <Match>
      <Source name="~.*[\\/]generated-sources[\\/].*"/>
    </Match>
    <Match>
      <Class name="~.*\.generated\..*"/>
    </Match>
    <!-- MapStruct-generated implementations -->
    <Match>
      <Class name="~.*MapperImpl"/>
    </Match>
  </FindBugsFilter>
  ```

- **Kotlin (Maven and Gradle)**: write these two instead of `checkstyle.xml`/`spotbugs-exclude.xml` — both if
  absent, an existing one following Step 0's answer (Keep by default; on Update add only missing keys).

  `detekt.yml` at the repository root, layered over detekt's defaults (`buildUponDefaultConfig`), relaxing only
  what a Spring service can't reasonably satisfy — the same philosophy as the lenient `checkstyle.xml`:

  ```yaml
  # detekt configuration, layered over detekt's default ruleset (buildUponDefaultConfig: true): only deviations
  # from the defaults belong here. maxIssues: 0 makes any finding fail the build, like Checkstyle/PMD/SpotBugs do
  # for the Java services.
  build:
    maxIssues: 0

  config:
    validation: true
    warningsAsErrors: false

  complexity:
    LongParameterList:
      # Spring constructors injecting several collaborators, data classes mapping wide DTOs.
      constructorThreshold: 10
      ignoreDefaultParameters: true
      ignoreAnnotated: ['ConfigurationProperties']
    TooManyFunctions:
      excludes: ['**/test/**', '**/generated/**']

  naming:
    FunctionNaming:
      # Backtick test names (`returns 404 when missing`) are the Kotlin testing convention.
      excludes: ['**/test/**']

  performance:
    SpreadOperator:
      # `runApplication<App>(*args)` in the Spring Boot main function is the one idiomatic spread.
      excludes: ['**/*Application.kt']

  style:
    MaxLineLength:
      maxLineLength: 140
    MagicNumber:
      excludes: ['**/test/**']
      ignorePropertyDeclaration: true
      ignoreAnnotation: true
    ReturnCount:
      max: 3
    UnusedPrivateMember:
      # Reflection-driven members look unused to static analysis.
      ignoreAnnotated: ['Bean', 'EventListener', 'Scheduled', 'KafkaListener']
  ```

  (Verified: with this file the `SpreadOperator` finding on the Boot `main` is gone, and a planted magic number
  still fails the build.)

  `.editorconfig` at the repository root — ktlint reads its rules from here (both the Maven plugin and the Gradle
  plugin), and IntelliJ formats to the same rules:

  ```ini
  root = true

  [*]
  charset = utf-8
  end_of_line = lf
  insert_final_newline = true
  trim_trailing_whitespace = true

  [*.{kt,kts}]
  indent_style = space
  indent_size = 4
  max_line_length = 140
  ktlint_code_style = ktlint_official
  # Backtick test names and Spring's @Bean factory functions.
  ktlint_function_naming_ignore_when_annotated_with = Test, ParameterizedTest, Bean
  ```

  An existing `.editorconfig` with other sections: on Update add only the `[*.{kt,kts}]` section if it is missing.

## Step 5G — Kotlin on Gradle: the Gradle Kotlin DSL build

Only when `project.language: kotlin` and `project.buildTool: gradle`. This replaces Steps 1, 1K, 3 and 4 — no pom
is written — and is this skill's "every module pom" responsibility in Gradle form. The module directories, the
placement of dependencies (Step 2, including its Kotlin note) and the analysis configuration (Step 5) are the same
as on Maven. Every template below was built in a throwaway `domain`/`application`/`boot` (mixed Java + Kotlin) +
`coverage` project on Gradle 9.7.1 / Boot 4.1.1 / Kotlin 2.3.21 / JDK 21 (Docker `gradle:8-jdk21`, running the
wrapper): `build -x test -x integrationTest`, `test` (the `*IT` excluded), `integrationTest` (only the `*IT`),
`:coverage:testCodeCoverageReport` (unit + integration data, Kotlin and Java classes), `detekt ktlintCheck`
(each failing on a planted violation, and ktlint also checking the `*.gradle.kts` files themselves),
`dokkaGeneratePublicationHtml` (aggregated into `build/dokka/html`), `:boot:bootJar` with `build-info.properties`
inside, and the task list containing `sonar` and `:boot:bootBuildImage`. The `sonar` task itself could not be run
without a Sonar server — its properties are unverified against a live analysis.

Write these files (every one is covered by Step 0's existing-file question):

```
settings.gradle.kts
gradle.properties
gradle/libs.versions.toml
build.gradle.kts                      # root: Dokka aggregation + Sonar
build-logic/settings.gradle.kts
build-logic/build.gradle.kts
build-logic/src/main/kotlin/iru.kotlin-library.gradle.kts
build-logic/src/main/kotlin/iru.spring-boot-app.gradle.kts
build-logic/src/main/kotlin/iru.quality.gradle.kts
build-logic/src/main/kotlin/iru.integration-test.gradle.kts
build-logic/src/main/kotlin/iru.coverage.gradle.kts
<module>/build.gradle.kts             # one per leaf module in `modules:`, coverage included
gradlew, gradlew.bat, gradle/wrapper/gradle-wrapper.jar, gradle/wrapper/gradle-wrapper.properties
```

Aggregator directories (`infrastructure/`, `infrastructure/database/`, `infrastructure/clients/`, `api/`) get **no**
build file — Gradle creates those parent projects implicitly from the `:`-paths. Everything written here must be
ktlint-clean (`ktlint_official` style from `.editorconfig`): ktlint checks every module's `build.gradle.kts` too, and a
single formatting slip fails `ktlintCheck` (verified — a missing blank line before a declaration did).

### Versions

Every `<latest>` below is resolved live, never from memory, newest version without a pre-release suffix, and
recorded for Step 8:

- Gradle plugins — the plugin portal marker metadata,
  `https://plugins.gradle.org/m2/<id with . as />/<id>.gradle.plugin/maven-metadata.xml` (e.g.
  `org/jlleitschuh/gradle/ktlint/org.jlleitschuh.gradle.ktlint.gradle.plugin`), for `org.jlleitschuh.gradle.ktlint`,
  `io.gitlab.arturbosch.detekt`, `org.jetbrains.dokka` and `org.sonarqube` (the codegen and Vaadin plugins are
  resolved by the apis/hilla skills that add them).
- Libraries — Maven Central `maven-metadata.xml` as in Step 1 (`io/mockk/mockk`, `com/ninja-squad/springmockk`
  (5.x for Boot 4), `com/tngtech/archunit/archunit-junit5`, `com/pinterest/ktlint/ktlint-cli` for the ktlint
  engine version, `org/jacoco/jacoco-maven-plugin` for the JaCoCo tool version).
- `kotlin` = the manifest's `project.kotlinVersion` (Step 0) — the Kotlin Gradle plugin version must equal the
  Kotlin version Boot manages. `spring-boot` = `project.springBootVersion`. `java` = `project.javaVersion`.
- BOM versions (`spring-cloud`, `spring-ai`, …) — copied from the reference build, exactly as on Maven.

As of this writing: Gradle 9.8.1, ktlint-gradle 14.2.0 (ktlint 1.8.0), detekt 1.23.8, Dokka 2.2.0, sonarqube
7.5.0.8588, JaCoCo 0.8.13+, MockK 1.14.11, springmockk 5.0.1. detekt's 2.x line (`dev.detekt`) is alpha-only —
stay on 1.23.x. Don't add `io.spring.dependency-management`: the BOM is applied with `platform()`, which also keeps
it out of detekt's own classpath (the dependency-management plugin is known to force detekt's embedded Kotlin to
the project's version and break it).

### `settings.gradle.kts`

```kotlin
pluginManagement {
    includeBuild("build-logic")
    repositories {
        gradlePluginPortal()
        mavenCentral()
    }
}

dependencyResolutionManagement {
    repositoriesMode = RepositoriesMode.PREFER_SETTINGS
    repositories {
        mavenCentral()
    }
}

rootProject.name = "<artifact-id>"

// One include per leaf module in the manifest's `modules:` list, `:`-path mirroring the directory, in this order.
include(":domain")
include(":application")
include(":infrastructure:database:<engine>")
include(":infrastructure:configuration")
include(":infrastructure:clients:<name>")
include(":infrastructure:producers")
include(":infrastructure:metrics")
include(":api:rest-server")
include(":api:grpc-server")
include(":api:graphql-server")
include(":api:consumers")
include(":boot")
include(":coverage")
```

Project names are the directory names (`boot`, `rest-server`, …), not the Maven `<a>-<suffix>` artifactIds; the
published jar names follow the project name.

### `gradle.properties`

```properties
group=<group-id>
# Read by the deploy workflow and by every project (Gradle maps it onto project.version).
version=<version>
org.gradle.caching=true
org.gradle.parallel=true
kotlin.code.style=official
```

### `gradle/libs.versions.toml`

```toml
[versions]
java = "<java-version>"
kotlin = "<kotlin-version>"
spring-boot = "<spring-boot-version>"
detekt = "<latest>"
ktlint-gradle = "<latest>"
ktlint = "<latest>"
dokka = "<latest>"
jacoco = "<latest>"
sonarqube = "<latest>"              # omit when sonar.mode: none
mockk = "<latest>"
springmockk = "<latest-5.x>"
archunit = "<latest>"
# BOM versions copied from the reference build; omit any not present there.
spring-cloud = "<from-reference-build>"
spring-ai = "<from-reference-build>"
# Only what the stack uses (see Step 1's property list for the Maven equivalents).
caffeine = "<latest>"
flamingock = "<latest>"

[libraries]
# BOMs — applied with platform() by iru.kotlin-library; they manage every Spring, Jackson, Kotlin, JUnit,
# coroutines and Testcontainers version.
spring-boot-dependencies = { module = "org.springframework.boot:spring-boot-dependencies", version.ref = "spring-boot" }
spring-cloud-dependencies = { module = "org.springframework.cloud:spring-cloud-dependencies", version.ref = "spring-cloud" }
spring-ai-bom = { module = "org.springframework.ai:spring-ai-bom", version.ref = "spring-ai" }

# BOM-managed: no version here on purpose. One alias per starter/driver in the reference build, named after its
# artifactId (spring-boot-starter-webmvc -> spring-boot-starter-webmvc), plus these:
kotlin-reflect = { module = "org.jetbrains.kotlin:kotlin-reflect" }
kotlin-test-junit5 = { module = "org.jetbrains.kotlin:kotlin-test-junit5" }
kotlinx-coroutines-core = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-core" }
kotlinx-coroutines-reactor = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-reactor" }
kotlinx-coroutines-test = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-test" }
jackson-module-kotlin = { module = "tools.jackson.module:jackson-module-kotlin" }
spring-boot-starter = { module = "org.springframework.boot:spring-boot-starter" }
spring-boot-starter-test = { module = "org.springframework.boot:spring-boot-starter-test" }
spring-boot-testcontainers = { module = "org.springframework.boot:spring-boot-testcontainers" }
spring-cloud-context = { module = "org.springframework.cloud:spring-cloud-context" }
testcontainers-junit-jupiter = { module = "org.testcontainers:testcontainers-junit-jupiter" }
junit-platform-launcher = { module = "org.junit.platform:junit-platform-launcher" }

# Not BOM-managed.
mockk = { module = "io.mockk:mockk", version.ref = "mockk" }
springmockk = { module = "com.ninja-squad:springmockk", version.ref = "springmockk" }
archunit-junit5 = { module = "com.tngtech.archunit:archunit-junit5", version.ref = "archunit" }

# Plugin artifacts the build-logic convention plugins compile against (versions shared with the aliases above).
kotlin-gradle-plugin = { module = "org.jetbrains.kotlin:kotlin-gradle-plugin", version.ref = "kotlin" }
kotlin-allopen = { module = "org.jetbrains.kotlin:kotlin-allopen", version.ref = "kotlin" }
kotlin-noarg = { module = "org.jetbrains.kotlin:kotlin-noarg", version.ref = "kotlin" }
spring-boot-gradle-plugin = { module = "org.springframework.boot:spring-boot-gradle-plugin", version.ref = "spring-boot" }
detekt-gradle-plugin = { module = "io.gitlab.arturbosch.detekt:detekt-gradle-plugin", version.ref = "detekt" }
ktlint-gradle-plugin = { module = "org.jlleitschuh.gradle:ktlint-gradle", version.ref = "ktlint-gradle" }
dokka-gradle-plugin = { module = "org.jetbrains.dokka:dokka-gradle-plugin", version.ref = "dokka" }

[plugins]
sonarqube = { id = "org.sonarqube", version.ref = "sonarqube" }
```

Omit every entry the stack doesn't use, exactly as the Maven root pom omits unused properties. The codegen and
frontend pieces are **not** written here: `iru-setup-java-springboot-apis` appends its own versions, libraries and
plugins to this same file (`org.openapi.generator`, `com.google.protobuf` with
`protobuf-protoc`/`grpc-protoc-gen-java`/`grpc-protoc-gen-kotlin`, `com.bakdata.gradle.avro`, …) and declares those
plugins in the root `plugins { }` block with `apply false`; `iru-setup-java-springboot-hilla` does the same for
`com.vaadin` and the Vaadin BOM. On a re-run (Update), keep every entry and root `apply false` line they added.
Any alias you add must not be a dotted prefix of another (`protoc` next to `protoc-gen-…` turns `libs.protoc` into a
group, not a library, and breaks `libs.protoc.get()`).

### `build-logic/` (included build with precompiled script convention plugins)

`build-logic/settings.gradle.kts` — shares the root catalog, so the convention plugins and the modules read one
set of versions:

```kotlin
dependencyResolutionManagement {
    repositories {
        gradlePluginPortal()
        mavenCentral()
    }
    versionCatalogs {
        create("libs") {
            from(files("../gradle/libs.versions.toml"))
        }
    }
}

rootProject.name = "build-logic"
```

`build-logic/build.gradle.kts`:

```kotlin
plugins {
    `kotlin-dsl`
}

dependencies {
    implementation(libs.kotlin.gradle.plugin)
    implementation(libs.kotlin.allopen)
    implementation(libs.kotlin.noarg)
    implementation(libs.spring.boot.gradle.plugin)
    implementation(libs.detekt.gradle.plugin)
    implementation(libs.ktlint.gradle.plugin)
    implementation(libs.dokka.gradle.plugin)
}
```

Precompiled script plugins can't use the type-safe `libs` accessor, so each one looks the catalog up by name.

`build-logic/src/main/kotlin/iru.kotlin-library.gradle.kts` — applied by every module (directly or via
`iru.spring-boot-app`); it applies the other three conventions, so a module build file names one plugin:

```kotlin
// Every Kotlin module: Kotlin/JVM + the Spring (all-open) and JPA (no-arg) compiler plugins, the JDK toolchain,
// the Spring Boot BOM, the shared test stack, and the quality / integration-test / coverage conventions.
plugins {
    id("org.jetbrains.kotlin.jvm")
    id("org.jetbrains.kotlin.plugin.spring")
    id("org.jetbrains.kotlin.plugin.jpa")
    id("iru.quality")
    id("iru.integration-test")
    id("iru.coverage")
}

val libs = versionCatalogs.named("libs")

fun lib(alias: String) = libs.findLibrary(alias).get()

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(libs.findVersion("java").get().requiredVersion)
    }
}

kotlin {
    compilerOptions {
        freeCompilerArgs.addAll("-Xjsr305=strict", "-Xannotation-default-target=param-property")
        javaParameters = true
    }
}

// kotlin-jpa only adds no-arg constructors; Hibernate's lazy proxies also need the entities open.
allOpen {
    annotation("jakarta.persistence.Entity")
    annotation("jakarta.persistence.MappedSuperclass")
    annotation("jakarta.persistence.Embeddable")
}

dependencies {
    implementation(platform(lib("spring-boot-dependencies")))
    // One line per other BOM in the catalog (spring-cloud-dependencies, spring-ai-bom, ...); omit when absent.
    implementation(platform(lib("spring-cloud-dependencies")))
    implementation(lib("kotlin-reflect"))
    // Only when stack.concurrency is reactive or both:
    implementation(lib("kotlinx-coroutines-core"))
    testImplementation(lib("kotlinx-coroutines-test"))

    testImplementation(lib("spring-boot-starter-test"))
    testImplementation(lib("kotlin-test-junit5"))
    testImplementation(lib("mockk"))
    testRuntimeOnly(lib("junit-platform-launcher"))
}

tasks.withType<Test>().configureEach {
    useJUnitPlatform()
}
```

The toolchain makes `./gradlew` compile and test with JDK `<java-version>` whatever JDK runs Gradle; CI's
`setup-java` should install that same version so no toolchain download is needed. `implementation(platform(...))`
also feeds `testImplementation` and the runtime classpaths; it adds version constraints only, so `domain` gets no
Spring class from it. `io.mockk:mockk` is right on Gradle (it resolves the JVM variant through Gradle metadata;
Maven needs `mockk-jvm`).

`build-logic/src/main/kotlin/iru.spring-boot-app.gradle.kts` — applied to `boot` only:

```kotlin
// Applied to `boot` only: the executable jar (bootJar), bootRun and bootBuildImage.
plugins {
    id("iru.kotlin-library")
    id("org.springframework.boot")
}

val libs = versionCatalogs.named("libs")

dependencies {
    // developmentOnly (spring-boot-docker-compose) doesn't extend implementation, so it needs the BOM too.
    "developmentOnly"(platform(libs.findLibrary("spring-boot-dependencies").get()))
    implementation(libs.findLibrary("jackson-module-kotlin").get())
}
```

`build-logic/src/main/kotlin/iru.quality.gradle.kts`:

```kotlin
// detekt + ktlint (both fail the build on any finding, like Checkstyle/PMD/SpotBugs on the Java services)
// and Dokka (KDoc HTML).
import io.gitlab.arturbosch.detekt.Detekt
import org.jlleitschuh.gradle.ktlint.reporter.ReporterType

plugins {
    id("io.gitlab.arturbosch.detekt")
    id("org.jlleitschuh.gradle.ktlint")
    id("org.jetbrains.dokka")
}

val libs = versionCatalogs.named("libs")

detekt {
    buildUponDefaultConfig = true
    config.setFrom(rootProject.file("detekt.yml"))
    source.setFrom("src/main/kotlin", "src/test/kotlin")
}

tasks.withType<Detekt>().configureEach {
    jvmTarget = libs.findVersion("java").get().requiredVersion
    exclude("**/generated/**")
    reports {
        xml.required = true // build/reports/detekt/detekt.xml, imported by Sonar
        html.required = true
        sarif.required = false
        txt.required = false
        md.required = false
    }
}

ktlint {
    version = libs.findVersion("ktlint").get().requiredVersion
    reporters {
        reporter(ReporterType.PLAIN)
        reporter(ReporterType.CHECKSTYLE) // build/reports/ktlint/<task>/<task>.xml, imported by Sonar
    }
    filter {
        exclude { it.file.path.contains("/generated/") || it.file.path.contains("/build/") }
    }
}

dokka {
    dokkaSourceSets.configureEach {
        documentedVisibilities(
            org.jetbrains.dokka.gradle.engine.parameters.VisibilityModifier.Public,
            org.jetbrains.dokka.gradle.engine.parameters.VisibilityModifier.Protected,
            org.jetbrains.dokka.gradle.engine.parameters.VisibilityModifier.Internal,
        )
        // Generated sources (registered on the source sets by the codegen plugins) are not documented.
        suppressedFiles.from(layout.buildDirectory.dir("generated"))
        perPackageOption {
            matchingRegex = ".*\\.generated(\\..*)?"
            suppress = true
        }
    }
}
```

`./gradlew ktlintFormat` fixes most ktlint findings; detekt findings are fixed by hand (or suppressed with a
reason, never by raising `maxIssues`).

`build-logic/src/main/kotlin/iru.integration-test.gradle.kts`:

```kotlin
// *Test classes run in `test`; *IT classes (Testcontainers-backed, slower) run in `integrationTest`, which `check`
// depends on. Both share the test source set, mirroring Surefire/Failsafe on the Maven side.
plugins {
    java
}

tasks.named<Test>("test") {
    exclude("**/*IT*")
}

val integrationTest =
    tasks.register<Test>("integrationTest") {
        description = "Runs the *IT integration tests."
        group = LifecycleBasePlugin.VERIFICATION_GROUP
        testClassesDirs = sourceSets["test"].output.classesDirs
        classpath = sourceSets["test"].runtimeClasspath
        include("**/*IT*")
        // Most modules have unit tests but no *IT; Gradle 9 would otherwise fail on "no tests discovered".
        failOnNoDiscoveredTests = false
        shouldRunAfter(tasks.named("test"))
    }

tasks.named("check") {
    dependsOn(integrationTest)
}
```

Applying it to every module (through `iru.kotlin-library`) means any module that later gains an `*IT` —
`infrastructure/database/<engine>`, `api/*`, `boot` — already has the task; `./gradlew test` never starts a
container, which is what the unit-only coverage gate and `ci.tests: unit` rely on.

`build-logic/src/main/kotlin/iru.coverage.gradle.kts`:

```kotlin
// JaCoCo for every Test task (test.exec and integrationTest.exec under build/jacoco/), plus a per-module XML report.
plugins {
    jacoco
}

val libs = versionCatalogs.named("libs")

jacoco {
    toolVersion = libs.findVersion("jacoco").get().requiredVersion
}

tasks.named<JacocoReport>("jacocoTestReport") {
    dependsOn(tasks.named("test"))
    // Generated code (OpenAPI/protobuf/AVRO/GraphQL output) never counts towards coverage.
    classDirectories.setFrom(
        classDirectories.files.map { dir -> fileTree(dir) { exclude("**/generated/**", "**/*ApplicationKt.class") } },
    )
    reports {
        xml.required = true
        html.required = true
    }
}
```

Like the Maven template, no build-failing coverage threshold is configured here — the 80% gate is enforced by
the coding skills (`iru-java-coverage` reads these reports).

### Root `build.gradle.kts`

```kotlin
// Root project: no sources. Puts build-logic (and with it the Kotlin, Spring Boot, detekt, ktlint and Dokka
// Gradle plugins) on the root classpath once, aggregates Dokka into build/dokka/html, and configures Sonar.
plugins {
    id("iru.quality") apply false
    alias(libs.plugins.sonarqube)
}

apply(plugin = "org.jetbrains.dokka")

dependencies {
    // One entry per Kotlin module (every leaf module except coverage), so dokkaGeneratePublicationHtml
    // aggregates them into build/dokka/html.
    "dokka"(project(":domain"))
    "dokka"(project(":application"))
    "dokka"(project(":boot"))
}

sonar {
    properties {
        property("sonar.organization", "<sonar-organization>")
        property("sonar.projectKey", "<sonar-project-key>")
        property("sonar.host.url", "<sonar-host-url>")
        property(
            "sonar.coverage.jacoco.xmlReportPaths",
            "$rootDir/coverage/build/reports/jacoco/testCodeCoverageReport/testCodeCoverageReport.xml",
        )
        // Relative paths: each module resolves them against its own directory.
        property("sonar.kotlin.detekt.reportPaths", "build/reports/detekt/detekt.xml")
        property(
            "sonar.kotlin.ktlint.reportPaths",
            "build/reports/ktlint/ktlintMainSourceSetCheck/ktlintMainSourceSetCheck.xml," +
                "build/reports/ktlint/ktlintTestSourceSetCheck/ktlintTestSourceSetCheck.xml",
        )
        property("sonar.exclusions", "**/generated/**,**/build/generated/**")
    }
}
```

`id("iru.quality") apply false` is deliberate: it loads the convention plugins' dependencies into the root
classloader once, so every subproject shares one copy of the Kotlin/Dokka/detekt plugins and the root can apply
Dokka without a version (applying `org.jetbrains.dokka` with a version here as well would clash). The Gradle Sonar
plugin finds Kotlin source sets, test sets and binaries by itself — no `sonar.sources` needed. Sonar wiring
follows Step 1's `sonar.mode` rules exactly: `none` — drop the `alias(libs.plugins.sonarqube)` line, the whole
`sonar { }` block and the `sonarqube` catalog entries; `cloud` — `https://sonarcloud.io` and the manifest's
organization/project key; `self-hosted` — the manifest's `sonar.hostUrl`, and `sonar.organization` only when the
manifest set it; `ci.enabled: false` with Sonar kept — add a comment above `sonar { }` saying no CI workflow sends
reports (`./gradlew sonar -Dsonar.token=…` runs it manually).

### Module `build.gradle.kts` files

Every leaf module names one convention plugin and its own dependencies — `project(":...")` for modules of this
project exactly per the module table's "May depend on" column, catalog aliases for everything else, never a
version:

```kotlin
// domain/build.gradle.kts — nothing Spring, nothing of this project.
plugins {
    id("iru.kotlin-library")
}
```

```kotlin
// application/build.gradle.kts
plugins {
    id("iru.kotlin-library")
}

dependencies {
    implementation(project(":domain"))
}
```

```kotlin
// infrastructure/database/<engine>/build.gradle.kts — same shape for every infrastructure/* and api/* module:
// project() lines per the table, then that module's Step 2 dependencies by alias.
plugins {
    id("iru.kotlin-library")
}

dependencies {
    implementation(project(":domain"))
    implementation(libs.spring.boot.starter.data.mongodb) // whatever the reference build names
    testImplementation(libs.spring.boot.testcontainers)
    testImplementation(libs.testcontainers.junit.jupiter)
    testImplementation(libs.testcontainers.mongodb)
}
```

`boot/build.gradle.kts` additionally carries the executable artifact, the image name and the same
`build-info.properties` the Maven build writes with `groovy-maven-plugin` — generated under `build/` instead of
`src/main/resources`, so the working tree stays clean:

```kotlin
import org.springframework.boot.gradle.tasks.bundling.BootBuildImage
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Properties

plugins {
    id("iru.spring-boot-app")
}

dependencies {
    // Every other leaf module of this project except coverage.
    implementation(project(":domain"))
    implementation(project(":application"))
    implementation(libs.spring.boot.starter)
    testImplementation(libs.springmockk)
    testImplementation(libs.archunit.junit5)
}

springBoot {
    // A top-level `fun main` in <ServiceName>Application.kt compiles to <ServiceName>ApplicationKt.
    mainClass = "<base-package>.<ServiceName>ApplicationKt"
}

tasks.named<BootBuildImage>("bootBuildImage") {
    imageName = "<image-registry>/<artifact-id>:${project.version}"
}

val buildInfoDir = layout.buildDirectory.dir("generated/build-info")
val generateBuildInfo =
    tasks.register("generateBuildInfo") {
        val outputFile = buildInfoDir.map { it.file("<base-package-path>/build-info.properties") }

        fun env(name: String) = providers.environmentVariable(name)
        val values =
            mapOf(
                "GROUP_ID" to provider { project.group.toString() },
                "ARTIFACT_ID" to provider { "${rootProject.name}-${project.name}" },
                "VERSION" to provider { project.version.toString() },
                // GitHub Actions first, then Jenkins, then GitLab — as in the Maven template.
                "BUILD_NUMBER" to env("GITHUB_RUN_NUMBER").orElse(env("BUILD_NUMBER")).orElse(env("CI_JOB_ID")),
                "COMMIT" to env("GITHUB_SHA").orElse(env("GIT_COMMIT")).orElse(env("CI_COMMIT_SHA")),
                "BRANCH" to env("GITHUB_REF_NAME").orElse(env("GIT_BRANCH")).orElse(env("CI_COMMIT_REF_NAME")),
            )
        outputs.file(outputFile)
        outputs.upToDateWhen { false }
        doLast {
            val props = Properties()
            props.setProperty("BUILD_TIMESTAMP", SimpleDateFormat("yy-MM-dd HH:mm:ss").format(Date()))
            values.forEach { (key, value) -> value.orNull?.let { props.setProperty(key, it) } }
            val file = outputFile.get().asFile
            file.parentFile.mkdirs()
            file.writer().use { props.store(it, null) }
        }
    }

sourceSets.main {
    resources.srcDir(files(buildInfoDir).builtBy(generateBuildInfo))
}
```

`coverage/build.gradle.kts` — no sources; one `jacocoAggregation` line per other leaf module:

```kotlin
// No sources: aggregates every module's JaCoCo data into
// build/reports/jacoco/testCodeCoverageReport/testCodeCoverageReport.xml (what Sonar reads).
plugins {
    base
    `jacoco-report-aggregation`
}

jacoco {
    toolVersion = libs.versions.jacoco.get()
}

dependencies {
    jacocoAggregation(project(":domain"))
    jacocoAggregation(project(":application"))
    jacocoAggregation(project(":boot"))
}

reporting {
    reports {
        register<JacocoCoverageReport>("testCodeCoverageReport") {
            testSuiteName = "test"
        }
    }
}

tasks.named<JacocoReport>("testCodeCoverageReport") {
    // The aggregation plugin only collects the `test` suite's data; add each module's integrationTest.exec when it
    // exists (after `./gradlew integrationTest`), without forcing the integration tests to run — the same
    // "whatever ran" semantics as the Maven report-aggregate over jacoco*.exec.
    val aggregated = configurations.jacocoAggregation.get().dependencies.withType<ProjectDependency>()
    val itData =
        aggregated.map { dep ->
            rootProject.layout.projectDirectory.file(
                dep.path.removePrefix(":").replace(':', '/') + "/build/jacoco/integrationTest.exec",
            )
        }
    executionData.from(files(itData).filter { it.exists() })
    mustRunAfter(aggregated.map { "${it.path}:integrationTest" })
    // Same exclusions as each module's own report: generated code and the Boot main file class.
    classDirectories.setFrom(
        classDirectories.files.map { dir -> fileTree(dir) { exclude("**/generated/**", "**/*ApplicationKt.class") } },
    )
    reports {
        xml.required = true
        html.required = true
    }
}
```

`base` (not `java`) keeps `coverage` from being a Kotlin/Java project, so `testCodeCoverageReport` must be
registered explicitly as above. Generated code stays out of every tool on Gradle too: detekt reads only
`src/*/kotlin` and excludes `**/generated/**`, ktlint skips anything under `/generated/` or `/build/`, Dokka
suppresses `build/generated` and any `*.generated.*` package, both JaCoCo reports drop `**/generated/**` classes,
and the root `sonar.exclusions` covers `**/generated/**,**/build/generated/**` (verified: a class in a
`generated` package was absent from the aggregate coverage report and from the Dokka output).

### Gradle wrapper

Write `gradlew`, `gradlew.bat` and `gradle/wrapper/*` for the latest stable Gradle (`https://services.gradle.org/versions/current`,
9.8.1 as of this writing), first source that works:

1. The Initializr starter extracted in Step 0 already contains a wrapper — copy its four files when its
   `distributionUrl` version is the current stable one (or the newest the user accepts).
2. A local `gradle` on `PATH`: `gradle wrapper --gradle-version <version> --distribution-type bin`.
3. Docker: `docker run --rm -v "$PWD":/w -w /w gradle:<any 8.x/9.x jdk tag> gradle wrapper --gradle-version <version> --distribution-type bin`
   (verified with `gradle:8-jdk21` producing a 9.8.1 wrapper).

For 2 and 3, run the command in an **empty scratch directory** holding only an empty `settings.gradle.kts`, then
copy `gradlew`, `gradlew.bat` and `gradle/wrapper/*` into the repository. Run in the repository itself, the
`wrapper` task first configures the whole build — including compiling `build-logic/` — with whatever Gradle runs it,
and an 8.x Gradle fails there (`Unresolved reference: failOnNoDiscoveredTests`, a Gradle 9 API).
4. Otherwise ask the user to run one of the above — never hand-write `gradle-wrapper.jar`.

Then `chmod +x gradlew`. All later commands use `./gradlew`.

## Step 6 — Verify the reactor resolves

Delegate to the `iru-gate-runner` agent (a multi-module Maven log is exactly the kind of output that shouldn't land
in this context) and ask for a compact result:

```bash
mvn -q -N validate            # root pom alone parses and the enforcer rules pass
mvn -q validate               # every module pom parses and the reactor order resolves
mvn dependency:tree -q        # every dependency resolves; no version comes from outside the root pom
```

Scan the `dependency:tree` output for two specific problems and fix them before finishing:

- a **version declared in a module pom** — move it to the root's `<dependencyManagement>`;
- an **unmanaged transitive version conflict** Maven resolved by nearest-wins — pin it in the root's
  `<dependencyManagement>` so the choice is explicit.

If the enforcer's `requireJavaVersion` rule fails because the local JDK is older than the target, that's the rule
working: report it and tell the user which JDK the build needs, rather than lowering the target.

**Kotlin + Maven** — the same three commands, then one more run that actually exercises the Kotlin toolchain on
the (still source-less, or freshly scaffolded) reactor:

```bash
mvn -q verify -DskipITs                      # kotlinc + javac ordering, Surefire, JaCoCo, detekt, ktlint
mvn -q detekt:check ktlint:check             # the prefixes CI calls resolve outside the lifecycle
mvn -q compile dokka:dokka                   # Dokka runs (fails with "Not found dokka plugin" if misdeclared)
```

**Kotlin + Gradle** — via the wrapper, again through `iru-gate-runner`:

```bash
./gradlew help                                       # settings, catalog and build-logic compile; projects resolve
./gradlew build -x test -x integrationTest           # every module compiles; detekt, ktlint (incl. *.gradle.kts) pass
./gradlew :boot:dependencies --configuration runtimeClasspath   # every dependency resolves through the BOM/catalog
./gradlew tasks --all                                 # test, integrationTest, :coverage:testCodeCoverageReport,
                                                      # detekt, ktlintCheck, dokkaGeneratePublicationHtml,
                                                      # :boot:bootBuildImage and (unless sonar: none) sonar exist
```

Scan for the Gradle equivalents of the two Maven problems: a version literal in a module `build.gradle.kts` or a
convention plugin (move it to the catalog), and a `FAILED` resolution or a conflict resolved to an unexpected
version (pin it in the catalog). A toolchain error ("Cannot find a Java installation matching languageVersion")
means the local machine lacks JDK `<java-version>` — report it, don't lower the toolchain.

## Step 7 — Sanity-check the hexagon

Confirm by reading the written poms, not by assuming:

- `domain` depends on no other module of this project and on nothing from `org.springframework*`.
- No `infrastructure/*` module depends on `application`, on `api/*`, or on a sibling infrastructure module.
- No `api/*` module depends on an `infrastructure/*` module.
- `boot` depends on every other module.
- No module pom other than the root declares a `<version>` for a dependency.

On Gradle the same four dependency checks apply to the `project(":...")` lines in each `build.gradle.kts`, plus:
no version literal outside `gradle/libs.versions.toml`, and every leaf module in `modules:` has an `include(...)`
in `settings.gradle.kts`, a `"dokka"(project(...))` line in the root build (except `coverage`), and a
`jacocoAggregation(project(...))` line in `coverage/build.gradle.kts`. There is no enforcer on Gradle — say in
Step 8 that the boundaries are guarded by the declared dependencies plus the ArchUnit test
`iru-setup-java-springboot-modules` writes in `boot`, and nothing else.

Report any violation you had to introduce deliberately (e.g. a starter that drags Spring into `domain`) rather
than quietly relaxing the enforcer rule to make the build pass.

## Step 8 — Report

Summarize: whether the reactor was generated from scratch or updated, and per file the action taken (**created /
updated / replaced / kept as is**), with every mismatch left in a kept file; the reactor's module list in build order; every version pinned in the root pom (separating those copied
from the Initializr reference pom from those looked up on Maven Central); which module each significant dependency
landed in; any dependency that couldn't be placed and therefore went to `boot`; whether `checkstyle.xml` and
`spotbugs-exclude.xml` were created or already present; the result of Step 6's three commands; and any hexagon
violation from Step 7. If an existing root pom was regenerated, list what was carried over from it so the user can
confirm nothing was lost. State how `sonar.mode` was wired: `none` (no `sonar.*` properties, no
`sonar-maven-plugin`), `cloud` (SonarCloud, with the resolved `sonar.organization`/`sonar.projectKey`), or
`self-hosted` (the resolved `sonar.host.url`, and whether `sonar.organization` was included or omitted). If the
manifest's `ci.enabled` is `false` while `sonar.mode` isn't `none`, say that the Sonar properties/plugin are
build-side configuration only — no CI step sends reports, so analysis runs only when someone runs `mvn
sonar:sonar` manually with a token. State how
`frontend` was wired: `none` (no Vaadin properties/BOM/plugin/profile at all) or `hilla` (the resolved
`vaadin.version`, and that the `vaadin-bom` import, `vaadin-maven-plugin` `pluginManagement` entry, `production`
profile, and `vaadin.skip` property were all written — noting that `iru-setup-java-springboot-hilla` is what
actually wires a module against these pins).

For Kotlin, also state: the build tool; the `kotlinVersion` used (and that it is the Boot-managed one); the
resolved detekt/ktlint/Dokka/MockK/springmockk versions (and, on Gradle, the Gradle version and which source the
wrapper came from); whether `detekt.yml` and `.editorconfig` were created or already present; that Lombok,
MapStruct and the configuration processor were deliberately left out; and, on Kotlin + Maven, which modules got
the `src/main/kotlin`/`src/test/kotlin` placeholders and which got a mixed-source `sonar.sources` override. On
Gradle report per file (settings, catalog, root build, each convention plugin, each module build file, wrapper)
the action taken, the Step 6 results, and the commands the rest of the chain uses: `./gradlew build -x test -x
integrationTest`, `./gradlew test`, `./gradlew integrationTest`, `./gradlew :coverage:testCodeCoverageReport`,
`./gradlew detekt ktlintCheck`, `./gradlew dokkaGeneratePublicationHtml`, `./gradlew sonar`.

Close by reminding the user that **the root pom (on Gradle, `gradle/libs.versions.toml`) is the only place a
version may be declared** — adding one to a
module pom or build file silently defeats the build's version discipline — and that `mvn dependency:tree` (on
Gradle, `./gradlew :<module>:dependencies`) is the check for that.
