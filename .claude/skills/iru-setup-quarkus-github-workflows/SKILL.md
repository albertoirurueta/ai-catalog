---
name: iru-setup-quarkus-github-workflows
description: >-
  Create or update the GitHub Actions workflows for a Quarkus service — Java or Kotlin, Maven or Gradle (Kotlin DSL),
  single-module or hexagonal multi-module, as scaffolded by `iru-setup-quarkus-service` (read from its
  `quarkus-stack.yml` when present, otherwise detected from the build). Writes `build.yml` (every push to the
  integration/stable branches, every pull request, `workflow_dispatch` — build and tests per `ci-tests` (`unit` =
  plain + `@QuarkusComponentTest` only, Dev Services off, every `@QuarkusTest` excluded, no containers; `full` = also
  `@QuarkusTest` with Dev Services containers and `@QuarkusIntegrationTest` against the packaged artifact, using the
  runner's Docker), the JaCoCo 80% gate, Checkstyle/PMD/SpotBugs or detekt/ktlint reports, an optional
  SonarCloud/SonarQube scan (`mvn sonar:sonar` / `./gradlew sonar`, skipped on fork pull requests), a docs job (Antora
  + Maven site/Javadoc or Dokka, deployed to GitHub Pages from the stable branch with `pages: yes`, uploaded as a
  workflow artifact with `pages: no`), and an optional native build-and-test job when the service builds native);
  `release.yml` (when a GitHub Release is published, only with `distribution: registry` — builds and pushes the
  container image tagged with the release version and `latest`, via `quarkus-container-image-jib` or
  `src/main/docker/Dockerfile.jvm` + `docker/build-push-action`, to GHCR by default); `sync.yml` +
  `.github/scripts/sync_versions.py` (after a release from the stable branch, opens a PR merging it back into the
  integration branch and bumping the next `-SNAPSHOT` — `mvn versions:set` for Maven, `gradle.properties` for Gradle —
  plus `README.md`/`docs/antora.yml`, consistent with `iru-release` and `iru-java-bump-version`); and the shared
  security block — `security.yml` (dependency-review, plus Gradle dependency submission; CodeQL `java-kotlin` with a
  real compile; OSV-Scanner; gitleaks) and `.github/dependabot.yml` (`maven` or `gradle`, `github-actions`, `docker`
  for a Dockerfile build, `npm` for the docs toolchain) — and ends with a required-secrets table. Invoke as
  `/iru-setup-quarkus-github-workflows`, optionally with `args` (`key: value` lines): `integration-branch` (default
  `develop`), `stable-branch` (default `main`), `java-version`, `open-source`, `visibility`
  (`public`/`private`/`internal`), `ci-tests` (`unit`/`full`), `pages` (`yes`/`no`), `sonar`
  (`cloud`/`self-hosted`/`none`, + `sonar-organization`/`sonar-project-key`/`sonar-host-url`), `distribution`
  (`none`/`registry`), `registry` (default `ghcr.io`), `image-builder` (`jib`/`docker`), `native` (`yes`/`no`),
  `mode` (`new`/`existing`), `on-existing` (`ask`/`keep`/`update`/`replace`), and
  `security-dependency-review`/`security-codeql`/`security-osv`/`security-gitleaks` (each `yes`/`no`, default `yes`).
  Stand-alone, it resolves `visibility` itself and asks `ci-tests`/`pages`/`sonar` with visibility-aware cost notes.
  Announces whether it is creating the pipeline from scratch or updating one, and asks Update / Keep as is / Replace
  (or Stop) per existing workflow file. Used by `iru-setup-quarkus-repository`; also runs standalone.
model: sonnet
---

# Setup Quarkus GitHub Workflows

Scaffold (or update) the CI/CD and security pipeline for a Quarkus service:

| File | Trigger | Does |
|---|---|---|
| `.github/workflows/build.yml` | push to `<integration-branch>`/`<stable-branch>`, pull requests to them, `workflow_dispatch` | build + tests per `ci-tests`, 80% coverage gate, quality reports, optional Sonar, docs (Pages deploy from `<stable-branch>` or artifact), optional native job |
| `.github/workflows/release.yml` | GitHub Release published — **only when `distribution: registry`** | container image `<version>` + `latest` pushed to the registry |
| `.github/workflows/sync.yml` + `.github/scripts/sync_versions.py` | GitHub Release published from `<stable-branch>` | PR merging the release back into `<integration-branch>` with the next `-SNAPSHOT` |
| `.github/workflows/security.yml` | pushes, pull requests, weekly | dependency review (+ Gradle dependency submission), CodeQL, OSV-Scanner, gitleaks |
| `.github/dependabot.yml` | — | weekly grouped updates for the build, the actions, and (when present) the Dockerfile and docs toolchain |

It fits the catalog's release flow: `iru-release` cuts `release_x.y.z` from `<integration-branch>`, bumps the version
with `iru-java-bump-version` (Maven `versions:set`, or Gradle's `gradle.properties` `version=`), and opens a PR into
`<stable-branch>`; merging it runs `build.yml` on `<stable-branch>` (docs to Pages); publishing the GitHub Release
runs `release.yml` (image) and `sync.yml` (next snapshot back on `<integration-branch>`).

Every action reference uses the major that was current when this skill was written (checked against the GitHub
API): `actions/checkout@v7`, `actions/setup-java@v6`, `gradle/actions/*@v6`, `actions/setup-node@v7`,
`actions/setup-python@v7`, `actions/upload-artifact@v7`, `crazy-max/ghaction-github-pages@v5`,
`docker/setup-buildx-action@v4`, `docker/login-action@v4`, `docker/metadata-action@v6`,
`docker/build-push-action@v7`, `github/codeql-action/*@v4`, `actions/dependency-review-action@v5`,
`google/osv-scanner-action/...@v2.7.0`, `gitleaks/gitleaks-action@v3`. Re-check them when updating an old pipeline —
Dependabot's `github-actions` entry keeps them current afterwards.

## Step 1 — Resolve inputs and survey the repository

Parse `args` (`key: value` lines, one per line) first; every key found is resolved and its survey/question below is
skipped:

```
integration-branch: develop
stable-branch: main
java-version: 21
open-source: yes
visibility: public
ci-tests: full
pages: yes
sonar: cloud
sonar-organization: example-github
sonar-project-key: example_orders-service
sonar-host-url: https://sonarcloud.io
distribution: registry
registry: ghcr.io
image-builder: jib
native: no
mode: new
on-existing: ask
```

Ignore any other key (`ci` included — invoking this skill means CI is wanted). `mode` is informational; `on-existing`
pre-answers Step 2's per-file question.

Then read `quarkus-stack.yml` if it exists — it's the authoritative record: `project.buildTool`/`language`/`layout`/
`javaVersion`/`artifactId`, `visibility`, `ci.tests`, `ci.pages`, `sonar.*`, `distribution.*`, `native`. Values from
`args` win over the manifest (an orchestrator passing them reflects what the user just chose); the manifest wins over
detection. Without a manifest, detect:

- **Build tool / layout** — `pom.xml` (reactor if it has `<modules>`; the app module is the one whose pom applies
  `quarkus-maven-plugin`) or `settings.gradle.kts` (multi-project if it `include`s; the app project applies
  `id("io.quarkus")`). Not a Quarkus build at all → warn and ask (`AskUserQuestion`) **Stop** / **Continue anyway**
  (every command becomes an open gap to confirm).
- **Language** — `src/main/kotlin` / `quarkus-kotlin` → Kotlin, else Java.
- **Java version** — `maven.compiler.release` / `java { sourceCompatibility }`; ask (default `21`) if absent.
- **Coverage gate, quality tools, Sonar** — confirm the build has the JaCoCo check, Checkstyle/PMD/SpotBugs or
  detekt/ktlint, Dokka, and (for `sonar` ≠ `none`) `sonar-maven-plugin`/`org.sonarqube` with `sonar.projectKey`. A
  missing piece isn't fixed here — `iru-setup-quarkus-service` owns the build — but every workflow step that would
  call it is dropped, and the report says so.
- **Native** — a `native` Maven profile is always generated by `create`; treat `native` as `yes` only when the
  manifest says so or `args` does.
- **Container image** — `quarkus-container-image-jib` in the build → `image-builder: jib`; otherwise `docker` when
  `src/main/docker/Dockerfile.jvm` exists (in `app/` for hexagonal).
- **Docs** — `docs/antora.yml` + `docs/antora-playbook.yml` (+ `docs/package-lock.json` for `npm ci`). Missing →
  recommend running `iru-setup-antora` first; the docs job would have nothing to build.
- **Branches** — confirm `<integration-branch>`/`<stable-branch>` against `git branch -a` (or ask); `sync.yml` needs
  both.
- **README/Antora wording** for `sync_versions.py` — `grep -n -i "current development version\|latest release"
  README.md`; note any deviation from the default row labels so Step 3's script matches the real wording.

**Cost-aware choices** (only those still unresolved, in this order, `AskUserQuestion`; prices per GitHub's/
SonarSource's current pricing — tell the user to double-check their plan):

1. **`visibility`** — `gh repo view --json visibility -q .visibility` (lowercased) when there's a GitHub remote;
   otherwise ask **Public** / **Private** (Public recommended when open source). Open source + private is
   contradictory — say so. `internal` = `private` below. Public repositories run standard runners free; private
   ones consume the included minutes (2,000/month Free, 3,000 Pro/Team, 50,000 Enterprise Cloud), then ~$0.006/min
   for Linux 2-core — this pipeline is Linux-only; the native job is the expensive one (often 10+ minutes).
2. **`sonar`** — when neither `args` nor the manifest nor the build resolves it: ask open source first if unknown,
   then "Configure SonarCloud / SonarQube and send CI analysis and coverage reports to it?" — **SonarCloud** only for
   a public open-source repository, otherwise **None** recommended, **self-hosted** second.
3. **`ci-tests`** — **Unit only** (`unit`; recommended for private) — "plain + `@QuarkusComponentTest` classes, Dev
   Services off, every `@QuarkusTest` excluded: no containers, fastest, cheapest; container-backed tests stay local
   (or run by the coding skills' group stage)". **Full** (`full`; recommended for public) — "also `@QuarkusTest`
   classes with Dev Services containers and `@QuarkusIntegrationTest` against the packaged jar — complete
   verification; GitHub's Ubuntu runners ship Docker, so no extra setup, but considerably more minutes".
4. **`pages`** — public: `yes` without asking (say so in Step 7). Private: **No (Recommended)** — "docs still built,
   uploaded as a workflow artifact" — vs **Yes** — "needs Pro/Team/Enterprise Cloud; the site is public unless
   Enterprise Cloud private Pages".
5. **`distribution`** — when unresolved: **None** / **Registry** (GHCR by default — free for public repositories,
   storage/transfer quotas for private ones), then `image-builder` if a Jib extension or Dockerfile doesn't decide it.

## Step 2 — Announce scratch vs update, decide per existing file

Check `build.yml`, `release.yml`, `sync.yml` + `.github/scripts/sync_versions.py` (one unit — partial if only one
exists), `security.yml`, `.github/dependabot.yml`. None → "creating the CI/CD pipeline **from scratch**". Any → "
**updating an existing CI/CD setup**", list each as present/absent/partial, read each existing one, and name every
concrete contradiction with this run's choices ("`build.yml` runs `-DskipITs=false` but `ci-tests: unit`", "it deploys
to Pages but `pages: no`", "it has a Sonar step but `sonar: none`", "there's a `release.yml` but `distribution:
none`"). Unless `on-existing` decides, ask per unit (`AskUserQuestion`, ≤ 4 per call):

- **Update (Recommended)** — merge: add/correct what this skill owns (stages, gating, action majors, commands),
  keep every other step/job/entry; diff shown before writing.
- **Keep as is** — untouched; mismatches listed in Step 7.
- **Replace** — regenerate from the template; customizations lost (git history keeps them).
- **Stop** (first question only) — end without changing anything.

With `distribution: none`, an existing `release.yml` that only publishes the image is offered for removal (ask; never
delete silently).

## Step 3 — Templates

Resolve every `<placeholder>` from Step 1. Lines/blocks marked `# Maven:`/`# Gradle:`, `# ci-tests: …`,
`# pages: …`, `# sonar …`, `# native …`, `# jib`/`# docker`, `# hexagonal` are alternatives or gates: keep the one that
applies and **drop the others together with these guidance comments** — a step that can never run is dead YAML.
`<app-dir>` is `app` for a hexagonal build and `.` for a single module; `<app-module>` is `-pl app -am ` (Maven) or
`:app:` (Gradle) for hexagonal, empty for single-module. `<artifact-id>` is the service's artifactId (single module)
or the base artifactId without `-app` (hexagonal) — the image name.

### `build.yml`

```yaml
name: Build

on:
  push:
    branches: [ <integration-branch>, <stable-branch> ]
  pull_request:
    branches: [ <integration-branch>, <stable-branch> ]
  workflow_dispatch:

# A newer push to the same branch/PR makes the running build obsolete.
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
          # Sonar attributes issues using full history.
          fetch-depth: 0

      - name: Set up JDK <java-version>
        uses: actions/setup-java@v6
        with:
          distribution: temurin
          java-version: <java-version>
          cache: maven                     # Maven: keep this line; Gradle: drop it (setup-gradle caches)

      - name: Set up Gradle                # Gradle only
        uses: gradle/actions/setup-gradle@v6
        with:
          cache-provider: basic

      # ci-tests: full — Surefire/test runs plain, component and @QuarkusTest classes (Dev Services start PostgreSQL,
      # Kafka, … containers on the runner's Docker), then the @QuarkusIntegrationTest classes run against the packaged
      # jar; the JaCoCo 80% check runs in verify/check.
      - name: Build, tests and coverage gate
        run: ./mvnw -B -ntp verify -DskipITs=false            # Maven
        # run: ./gradlew check <app-module>quarkusIntTest     # Gradle

      # ci-tests: unit — no containers: Dev Services off and every @QuarkusTest/@QuarkusMainTest class excluded, so
      # only plain and @QuarkusComponentTest classes run. The coverage gate is measured from exactly those.
      - name: Build, unit tests and coverage gate (no containers)
        env:
          QUARKUS_DEVSERVICES_ENABLED: "false"
        run: |
          grep -rlE '^[[:space:]]*@Quarkus(Main)?Test([^A-Za-z0-9_]|$)' --include='*.java' --include='*.kt' . \
            | sed -E 's#^(.*/)?src/test/(java|kotlin)/##; s#\.(java|kt)$#.class#' > "$RUNNER_TEMP/quarkus-tests.excludes" || true
          ./mvnw -B -ntp verify -DskipITs -Dsurefire.excludesFile="$RUNNER_TEMP/quarkus-tests.excludes"        # Maven
          # ./gradlew check -PexcludeTestsFile="$RUNNER_TEMP/quarkus-tests.excludes"                           # Gradle

      # Java: Checkstyle/PMD/SpotBugs findings as XML for the job artifact (they report, the coverage check gates).
      - name: Static analysis reports
        run: ./mvnw -B -ntp checkstyle:checkstyle pmd:pmd spotbugs:spotbugs     # Maven + Java
        # run: ./gradlew checkstyleMain pmdMain spotbugsMain                    # Gradle + Java
        # Kotlin: drop this step — detekt and ktlint already ran (and gate) inside verify/check.

      # sonar: cloud | self-hosted only — drop the whole step for sonar: none. Fork pull requests get no secrets.
      - name: Run SonarCloud analysis
        if: ${{ github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository }}
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
        run: ./mvnw -B -ntp sonar:sonar          # Maven
        # run: ./gradlew sonar                   # Gradle

      - name: Upload test and quality reports
        if: always()
        uses: actions/upload-artifact@v7
        with:
          name: reports
          retention-days: 7
          # Maven paths; Gradle: '**/build/test-results/**', '**/build/reports/**'
          path: |
            **/target/surefire-reports/**
            **/target/failsafe-reports/**
            **/target/site/jacoco/**
            **/target/checkstyle-result.xml
            **/target/pmd.xml
            **/target/spotbugsXml.xml
            **/target/detekt.xml
            **/target/ktlint.xml

  # native: yes only — builds the native executable inside a Mandrel builder container and re-runs the
  # @QuarkusIntegrationTest classes against it. Pushes to <stable-branch> and manual runs only: it takes minutes and
  # several GB of memory, too much for every pull request.
  native:
    name: Native build and integration tests
    needs: build
    if: ${{ github.event_name == 'workflow_dispatch' || (github.event_name == 'push' && github.ref == 'refs/heads/<stable-branch>') }}
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Set up JDK <java-version>
        uses: actions/setup-java@v6
        with:
          distribution: temurin
          java-version: <java-version>
          cache: maven                     # Maven only
      - name: Set up Gradle                # Gradle only
        uses: gradle/actions/setup-gradle@v6
        with:
          cache-provider: basic
      - name: Native build and integration tests
        run: ./mvnw -B -ntp verify -Pnative -Dquarkus.native.container-build=true -DskipTests        # Maven
        # run: ./gradlew <app-module>quarkusIntTest -Dquarkus.native.enabled=true -Dquarkus.native.container-build=true -Dquarkus.package.jar.enabled=false   # Gradle

  docs:
    name: Build documentation
    needs: build
    # Docs are built on every push (so a broken page fails the branch) but only published from <stable-branch>.
    if: ${{ github.event_name == 'push' || github.event_name == 'workflow_dispatch' }}
    runs-on: ubuntu-latest
    permissions:
      contents: write                      # pages: yes — pushes the gh-pages branch; pages: no → drop this block
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Set up JDK <java-version>
        uses: actions/setup-java@v6
        with:
          distribution: temurin
          java-version: <java-version>
          cache: maven                     # Maven only
      - name: Set up Gradle                # Gradle only
        uses: gradle/actions/setup-gradle@v6
        with:
          cache-provider: basic
      - name: Set up Node
        uses: actions/setup-node@v7
        with:
          node-version: 24
          cache: npm
          cache-dependency-path: docs/package-lock.json

      # Java + Maven: the Maven site (Javadoc, test/coverage/Checkstyle/PMD/SpotBugs/JXR reports).
      # Hexagonal: `./mvnw -B -ntp install -DskipTests -Djacoco.skip` first, then `site site:stage`, and copy
      # target/staging instead of target/site below.
      - name: Generate API documentation
        run: ./mvnw -B -ntp site -DskipTests -Djacoco.skip          # Java + Maven
        # run: ./gradlew javadoc                                    # Java + Gradle   → build/docs/javadoc
        # run: ./mvnw -B -ntp compile dokka:dokka                   # Kotlin + Maven  → target/dokka
        # run: ./gradlew dokkaGeneratePublicationHtml               # Kotlin + Gradle → build/dokka/html

      - name: Install Antora
        working-directory: docs
        run: npm ci

      - name: Build Antora docs
        working-directory: docs
        run: npx antora antora-playbook.yml

      - name: Merge documentation
        run: |
          cp -r docs/build/site ./doc
          touch ./doc/.nojekyll
          cp -r target/site ./doc/mvn-site            # Java + Maven (hexagonal: target/staging)
          # mkdir -p doc/api && cp -r build/docs/javadoc doc/api/javadoc   # Java + Gradle
          # mkdir -p doc/api && cp -r target/dokka doc/api/kdoc            # Kotlin + Maven
          # mkdir -p doc/api && cp -r build/dokka/html doc/api/kdoc        # Kotlin + Gradle

      # pages: yes — publish from <stable-branch> only.
      - name: Deploy to GitHub Pages
        if: ${{ github.ref == 'refs/heads/<stable-branch>' }}
        uses: crazy-max/ghaction-github-pages@v5
        with:
          target_branch: gh-pages
          build_dir: ./doc
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      # pages: no — replace the deploy step with this (and drop the job's permissions block and the .nojekyll touch).
      - name: Upload documentation
        uses: actions/upload-artifact@v7
        with:
          name: documentation
          path: ./doc
          retention-days: 14
```

Gating summary for `build.yml`: keep exactly one of the two test steps (`ci-tests`); drop the static-analysis step
for Kotlin; drop the Sonar step for `sonar: none`; drop the `native` job unless `native: yes`; keep exactly one of
"Deploy to GitHub Pages"/"Upload documentation" (`pages`); keep exactly one command per `# Maven/Gradle/Java/Kotlin`
alternative and drop `cache: maven` or the `Set up Gradle` step accordingly. Gradle's `-D` flags reach Quarkus's
build (native/container-image config) but not the test JVM — that's why the unit step passes Dev Services' switch as
the `QUARKUS_DEVSERVICES_ENABLED` environment variable for both build tools.

### `release.yml` (`distribution: registry` only)

```yaml
name: Release

on:
  release:
    types: [ released ]

permissions:
  contents: read
  packages: write                          # GHCR push with GITHUB_TOKEN; other registries: drop it

jobs:
  image:
    name: Build and push the container image
    runs-on: ubuntu-latest
    steps:
      - name: Check out the released commit
        uses: actions/checkout@v7

      - name: Set up JDK <java-version>
        uses: actions/setup-java@v6
        with:
          distribution: temurin
          java-version: <java-version>
          cache: maven                     # Maven only
      - name: Set up Gradle                # Gradle only
        uses: gradle/actions/setup-gradle@v6
        with:
          cache-provider: basic

      - name: Compute image coordinates
        id: image
        run: |
          version="${GITHUB_REF_NAME#v}"
          # Registry paths must be lowercase; GitHub owners may not be.
          echo "owner=${GITHUB_REPOSITORY_OWNER,,}" >> "$GITHUB_OUTPUT"
          echo "version=$version" >> "$GITHUB_OUTPUT"

      # jib — Quarkus builds and pushes the image itself (no Docker daemon needed). The released commit was already
      # tested by build.yml on <stable-branch>, so tests are skipped here.
      - name: Build and push with Jib
        env:
          QUARKUS_CONTAINER_IMAGE_USERNAME: ${{ github.actor }}               # other registry: ${{ secrets.REGISTRY_USERNAME }}
          QUARKUS_CONTAINER_IMAGE_PASSWORD: ${{ secrets.GITHUB_TOKEN }}       # other registry: ${{ secrets.REGISTRY_PASSWORD }}
        run: >
          ./mvnw -B -ntp <app-module>package -DskipTests
          -Dquarkus.container-image.build=true
          -Dquarkus.container-image.push=true
          -Dquarkus.container-image.registry=<registry>
          -Dquarkus.container-image.group=${{ steps.image.outputs.owner }}
          -Dquarkus.container-image.name=<artifact-id>
          -Dquarkus.container-image.tag=${{ steps.image.outputs.version }}
          -Dquarkus.container-image.additional-tags=latest
        # Gradle: replace the first line with `./gradlew <app-module>build -x test -x check` (same -D flags).

      # docker — package the fast-jar, then build src/main/docker/Dockerfile.jvm (use these four steps instead of
      # "Build and push with Jib").
      - name: Package the application
        run: ./mvnw -B -ntp <app-module>package -DskipTests        # Maven
        # run: ./gradlew <app-module>build -x test -x check        # Gradle
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v4
      - name: Log in to the registry
        uses: docker/login-action@v4
        with:
          registry: <registry>
          username: ${{ github.actor }}                 # other registry: ${{ secrets.REGISTRY_USERNAME }}
          password: ${{ secrets.GITHUB_TOKEN }}         # other registry: ${{ secrets.REGISTRY_PASSWORD }}
      - name: Image metadata
        id: meta
        uses: docker/metadata-action@v6
        with:
          images: <registry>/${{ steps.image.outputs.owner }}/<artifact-id>
          tags: |
            type=raw,value=${{ steps.image.outputs.version }}
            type=raw,value=latest
      - name: Build and push with Docker
        uses: docker/build-push-action@v7
        with:
          context: <app-dir>
          file: <app-dir>/src/main/docker/Dockerfile.jvm
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

Notes: `-Dquarkus.container-image.*` (Jib) works for Gradle's `build` too — Quarkus reads them as build-time
configuration. The image name comes from the service, not from `${{ github.repository }}`, so a repository rename
doesn't change it. A snapshot image per `<integration-branch>` push is deliberately not published (a registry full
of `-SNAPSHOT` tags costs storage on private repositories); add one to `build.yml` only if a deployment pipeline
consumes it.

### `sync.yml`

The library pipeline's Sync workflow (`iru-setup-java-github-workflows`), with the version bump made build-tool
aware:

```yaml
name: Sync

# After a release is published from <stable-branch>, open a pull request that merges it back into
# <integration-branch> and bumps the development version to the next -SNAPSHOT.
on:
  release:
    types: [ released ]

permissions:
  contents: write
  pull-requests: write

jobs:
  sync:
    name: Open sync PR from the released branch into <integration-branch>
    runs-on: ubuntu-latest
    if: ${{ github.event.release.target_commitish == '<stable-branch>' }}
    steps:
      - name: Check out code
        uses: actions/checkout@v7
        with:
          fetch-depth: 0

      - name: Compute versions and branch names
        id: versions
        env:
          TAG: ${{ github.event.release.tag_name }}
        run: |
          set -euo pipefail
          RELEASE_VERSION="${TAG#v}"
          IFS='.' read -r MAJOR MINOR PATCH <<< "$RELEASE_VERSION"
          if [ -z "${MAJOR:-}" ] || [ -z "${MINOR:-}" ] || [ -z "${PATCH:-}" ]; then
            echo "::error::Release tag '$RELEASE_VERSION' is not in X.Y.Z form; cannot compute the next snapshot."
            exit 1
          fi
          NEXT_MINOR=$((MINOR + 1))
          {
            echo "release_version=$RELEASE_VERSION"
            echo "next_snapshot=${MAJOR}.${NEXT_MINOR}.0-SNAPSHOT"
            echo "sync_branch=sync_${MAJOR}.${NEXT_MINOR}.0"
          } >> "$GITHUB_OUTPUT"

      - name: Skip if this release was already synced
        id: guard
        run: |
          if git ls-remote --exit-code --heads origin "${{ steps.versions.outputs.sync_branch }}" >/dev/null 2>&1; then
            echo "::notice::${{ steps.versions.outputs.sync_branch }} already exists on origin; skipping."
            echo "exists=true" >> "$GITHUB_OUTPUT"
          else
            echo "exists=false" >> "$GITHUB_OUTPUT"
          fi

      - name: Configure git identity
        if: ${{ steps.guard.outputs.exists == 'false' }}
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

      - name: Create the sync branch and merge the release into it
        if: ${{ steps.guard.outputs.exists == 'false' }}
        run: |
          git fetch origin <integration-branch> <stable-branch>
          git checkout -b "${{ steps.versions.outputs.sync_branch }}" "origin/<integration-branch>"
          git merge --no-ff --no-edit \
            -m "Merge <stable-branch> (${{ steps.versions.outputs.release_version }}) into <integration-branch>" \
            "origin/<stable-branch>"

      # Maven only: versions:set rewrites the root and every module's version (and their parent references).
      - name: Set up JDK <java-version>
        if: ${{ steps.guard.outputs.exists == 'false' }}
        uses: actions/setup-java@v6
        with:
          distribution: temurin
          java-version: <java-version>
          cache: maven
      - name: Bump the Maven project version
        if: ${{ steps.guard.outputs.exists == 'false' }}
        run: ./mvnw -B -ntp -q versions:set -DnewVersion="${{ steps.versions.outputs.next_snapshot }}" -DgenerateBackupPoms=false -DprocessAllModules=true

      - name: Set up Python
        if: ${{ steps.guard.outputs.exists == 'false' }}
        uses: actions/setup-python@v7
        with:
          python-version: '3.x'

      - name: Bump gradle.properties, README and Antora versions
        if: ${{ steps.guard.outputs.exists == 'false' }}
        env:
          RELEASE_VERSION: ${{ steps.versions.outputs.release_version }}
          NEXT_SNAPSHOT: ${{ steps.versions.outputs.next_snapshot }}
        run: python3 .github/scripts/sync_versions.py

      - name: Commit and push the sync branch
        if: ${{ steps.guard.outputs.exists == 'false' }}
        run: |
          git add -u
          git diff --cached --quiet || git commit -m "Sync ${{ steps.versions.outputs.next_snapshot }}"
          git push origin "${{ steps.versions.outputs.sync_branch }}"

      - name: Open pull request into <integration-branch>
        if: ${{ steps.guard.outputs.exists == 'false' }}
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh label create sync --color 0e8a16 \
            --description "Sync pull request from a release back into <integration-branch>" 2>/dev/null || true
          gh pr create \
            --base <integration-branch> \
            --head "${{ steps.versions.outputs.sync_branch }}" \
            --title "Sync ${{ steps.versions.outputs.next_snapshot }}" \
            --body "Merges \`<stable-branch>\` back into \`<integration-branch>\` after releasing \`${{ steps.versions.outputs.release_version }}\`, and bumps the development version to \`${{ steps.versions.outputs.next_snapshot }}\`." \
            --label sync
```

Gradle: drop the two Maven-only steps (JDK + `versions:set`) — the script rewrites `gradle.properties`. The bump is
always minor (`1.3.0` → `1.4.0-SNAPSHOT`), matching `iru-release`'s default "next upcoming version"; flag it in
Step 7 if the team releases patches from `<integration-branch>` too.

### `.github/scripts/sync_versions.py`

```python
#!/usr/bin/env python3
"""Rewrites version references after a release, for the Sync workflow.

Reads RELEASE_VERSION and NEXT_SNAPSHOT from the environment. Maven poms are bumped by `mvn versions:set` in the
workflow itself; this script handles gradle.properties (Gradle builds keep `version=` there), the README's version
table, and the Antora component version. Every file is optional, so the script fits either build tool.
CHANGELOG.md is left alone: its release section arrives through the merge that precedes this script.
"""
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def update_gradle_properties(next_snapshot):
    path = REPO_ROOT / "gradle.properties"
    if not path.exists():
        return
    text = path.read_text()
    updated, count = re.subn(r"(?m)^version=.*$", f"version={next_snapshot}", text, count=1)
    if count != 1:
        sys.exit("gradle.properties: no 'version=' line to bump")
    path.write_text(updated)


def update_readme(release_version, next_snapshot):
    path = REPO_ROOT / "README.md"
    if not path.exists():
        return
    text = path.read_text()
    # Adjust these row labels if this repository's README words them differently (Step 1's survey).
    text = re.sub(r"(\| Current development version \| `)[^`]*(` \|)", rf"\g<1>{next_snapshot}\g<2>", text)
    text = re.sub(r"(\| Latest release[^|]*\| `)[^`]*(` \|)", rf"\g<1>{release_version}\g<2>", text)
    path.write_text(text)


def update_antora_component_version(release_version):
    path = REPO_ROOT / "docs" / "antora.yml"
    if not path.exists():
        return
    text = path.read_text()
    updated, count = re.subn(r"(?m)^version:.*$", f"version: {release_version}", text, count=1)
    if count == 1:
        path.write_text(updated)


def main():
    release_version = os.environ["RELEASE_VERSION"]
    next_snapshot = os.environ["NEXT_SNAPSHOT"]
    update_gradle_properties(next_snapshot)
    update_readme(release_version, next_snapshot)
    update_antora_component_version(release_version)


if __name__ == "__main__":
    main()
```

### `security.yml`

The shared security block every workflows skill in this catalog embeds. Drop a job's whole entry when its
`security-*` flag is `no`; if all four are `no`, don't write the file at all (say so in Step 7).

```yaml
name: Security

on:
  push:
    branches: [ <integration-branch>, <stable-branch> ]
  pull_request:
    branches: [ <integration-branch>, <stable-branch> ]
  schedule:
    - cron: '0 6 * * 1'   # weekly: catch CVEs disclosed after the code was merged
  workflow_dispatch:

permissions:
  contents: read

jobs:
  # Gradle only, and only with security-dependency-review: yes — GitHub's dependency graph can't read Gradle build
  # scripts, so dependency review has nothing to compare without a submitted snapshot.
  dependency-submission:
    name: Submit Gradle dependency graph
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

  dependency-review:
    name: Dependency review
    needs: dependency-submission                     # Gradle only — drop on Maven
    if: ${{ !cancelled() && github.event_name == 'pull_request' }}   # Maven: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Dependency review
        uses: actions/dependency-review-action@v5
        with:                                        # Gradle only — a submitted snapshot may still be processing
          retry-on-snapshot-warnings: true
          retry-on-snapshot-warnings-timeout: 600

  codeql:
    name: CodeQL analysis
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Set up JDK <java-version>
        uses: actions/setup-java@v6
        with:
          distribution: temurin
          java-version: <java-version>
          cache: maven                     # Maven only
      - name: Set up Gradle                # Gradle only
        uses: gradle/actions/setup-gradle@v6
        with:
          cache-provider: basic
      - name: Initialize CodeQL
        uses: github/codeql-action/init@v4
        with:
          languages: java-kotlin
          build-mode: manual               # Kotlin needs a real compilation; Java gets the same for consistency
      - name: Compile
        run: ./mvnw -B -ntp compile -DskipTests -Djacoco.skip      # Maven
        # run: ./gradlew classes                                   # Gradle
      - name: Perform CodeQL analysis
        uses: github/codeql-action/analyze@v4

  osv-scanner:
    name: OSV-Scanner
    permissions:
      contents: read
      security-events: write
      actions: read
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
          fetch-depth: 0                   # scan the history, not just the tree
      - name: Run gitleaks
        uses: gitleaks/gitleaks-action@v3
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### `.github/dependabot.yml` (always written — no opt-out)

```yaml
version: 2
updates:
  - package-ecosystem: maven               # Gradle: gradle (reads build.gradle.kts, settings, libs.versions.toml, gradle.properties)
    directory: /
    schedule:
      interval: weekly
    groups:
      build-dependencies:
        patterns: [ "*" ]

  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    groups:
      github-actions-dependencies:
        patterns: [ "*" ]

  # image-builder: docker only — keeps the Dockerfile's base image current (Jib's base image is a Quarkus default
  # that moves with the platform).
  - package-ecosystem: docker
    directory: /<app-dir>/src/main/docker
    schedule:
      interval: weekly

  # Only when docs/package-lock.json exists — the Antora toolchain.
  - package-ecosystem: npm
    directory: /docs
    schedule:
      interval: weekly
    groups:
      docs-dependencies:
        patterns: [ "*" ]
```

For `directory: /<app-dir>/…` write `/src/main/docker` (single module) or `/app/src/main/docker` (hexagonal). When
updating an existing `dependabot.yml`, keep entries for ecosystems this skill doesn't manage.

## Step 4 — Fill and gate

Substitute every placeholder from Step 1, apply every gate described above (keeping one alternative per
`# Maven/Gradle/Java/Kotlin` choice), and strip the guidance comments. Never invent a value: an unresolved fact
(e.g. no Antora playbook, no Sonar project key) is either asked or reported as an open gap in Step 7.

Notes that change what is generated:

- **Hexagonal Maven**: tests, coverage, and Sonar run from the root as written (`verify` walks the reactor; the
  `coverage` module aggregates). Image/native steps target the app module (`-pl app -am`), and the docs job uses
  `install` + `site site:stage` (multi-module site needs the modules installed and staged).
- **Hexagonal Gradle**: `quarkusIntTest`/native/image tasks are `:app:…`; Dokka aggregates at the root
  (`dokkaGeneratePublicationHtml` → `build/dokka/html`).
- **No Docker in `ci-tests: unit`** — no service containers, no `docker` login; everything that would need Docker is
  excluded by the grep, which anchors on the annotation at the start of a line (a Javadoc mention of `@QuarkusTest`
  must not exclude a plain test).

## Step 5 — Validate

- Run `actionlint` on every generated workflow — `actionlint` if installed, else
  `docker run --rm -v "$PWD":/repo -w /repo rhysd/actionlint:latest -color` — and fix every finding (shellcheck
  findings in `run:` blocks included). `.github/dependabot.yml` is not a workflow: parse it with
  `python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" .github/dependabot.yml`.
- Run the build commands the workflows contain locally first, through the `iru-gate-runner` agent (compact
  results): the chosen test step (for `unit`, with the same grep/excludes and `QUARKUS_DEVSERVICES_ENABLED=false`),
  the static-analysis step, and the docs commands. A workflow whose commands were never run is a guess. Docker
  unavailable locally → the `full` step is **unverified**, not failed.
- Never trigger `release.yml` or `sync.yml` for real as a test. Recommend a throwaway pre-release/tag on a fork, or
  review of the first real release run.

## Step 6 — Write the files

Write (or, per Step 2, update/replace — and skip kept units) the workflows, `sync_versions.py` (only together with
`sync.yml`), `security.yml`, and `.github/dependabot.yml`. With `distribution: none`, write no `release.yml`.

## Step 7 — Report: secrets, settings, choices, warnings

Required secrets (Settings → Secrets and variables → Actions) — list only the rows that apply:

| Secret | Purpose | Needed when |
|---|---|---|
| `SONAR_TOKEN` | SonarCloud/SonarQube token for `sonar:sonar` / `./gradlew sonar` | `sonar` is `cloud` or `self-hosted` (cloud on a private repository also needs a paid SonarCloud plan) |
| `REGISTRY_USERNAME` / `REGISTRY_PASSWORD` | Registry credentials for the image push | `distribution: registry` with a registry other than GHCR (GHCR uses the automatic `GITHUB_TOKEN` + `packages: write`) |

`GITHUB_TOKEN` needs no setup and covers Pages, GHCR, Sync and every `security.yml` job (gitleaks needs
`GITLEAKS_LICENSE` only for organization accounts on its paid tier — mention it). Repository settings to check:

- **Settings → Actions → General → Workflow permissions** must allow GitHub Actions to create pull requests, or
  `sync.yml` fails on `gh pr create` despite its `permissions:` block.
- **Pages** (`pages: yes`): source = `gh-pages` branch. Private repositories need Pro/Team/Enterprise Cloud, and the
  site is public unless Enterprise Cloud private Pages.
- **Code scanning** must be enabled for CodeQL to upload; **Dependency graph** for dependency review (on by default
  for public repositories).
- **GHCR**: the first push creates the package as *private*; make it public (package settings) if it should be
  pullable anonymously, and link it to the repository.

Then summarize: scratch vs update and, per unit, **created / updated / replaced / kept as is** (with mismatches) or
stopped; the build tool/language/layout and Java version used; `visibility` (and its source) with the
minutes note for private repositories; `ci-tests` (and, for `unit`, that container-backed tests only run locally or
in the coding skills' group stage); `pages`; `sonar` (+ keys) or why omitted; `distribution`/registry/image builder
(or why `release.yml` wasn't written); `native` (and its cost); which security jobs were included; and every open
gap (no Antora setup, a build without the JaCoCo check or Sonar plugin, README wording `sync_versions.py` won't match,
patch releases the minor-bump default doesn't handle).

Warn explicitly: **review every workflow before pushing it.** Branch names, the Java version, image coordinates and
the registry were inferred from this repository and may need correcting; `release.yml` publishes an image and
`sync.yml` pushes branches and opens pull requests, so verify both against the first real release. Nothing in these
files contains a credential, and it must stay that way.
