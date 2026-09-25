---
name: iru-setup-java-springboot-github-workflows
description: Create the GitHub Actions workflows for a Spring Boot service repository — a build workflow (`build.yml`) that runs on pushes to the integration and main branches and on pull requests, executing unit tests via Surefire and Testcontainers-backed integration tests via Failsafe, Checkstyle/PMD/SpotBugs static analysis, aggregated JaCoCo coverage, optionally a SonarCloud/SonarQube scan via `mvn sonar:sonar` (gated by the manifest's `sonar.mode`), the Antora documentation build, and the generated API documentation — OpenAPI, protobuf, the AsyncAPI HTML produced by `@asyncapi/html-template`, and the GraphQL reference produced by `spectaql` and `graphql-voyager` — publishing all of it to GitHub Pages; when the manifest's `frontend` is `hilla`, `build.yml` also sets up Node via `actions/setup-node`, runs `vaadin:prepare-frontend` before it, then `npm ci` and `npx vitest run --coverage` in the web module, and packages with `-Pproduction -Dvaadin.ci.build=true`; a `deploy.yml` that builds and pushes the container image, authenticates to AWS or Google Cloud via keyless OIDC, and applies the OpenTofu configuration for a chosen environment behind a GitHub Environment approval gate; an `undeploy.yml` that scales the service to zero or destroys an environment's infrastructure, guarded by a typed-confirmation input and a protected environment; a `security.yml` that runs a `dependency-review` job (`actions/dependency-review-action@v5`), a CodeQL job (`github/codeql-action@v4`, matrix including `javascript-typescript` when `frontend` is `hilla`), an OSV-Scanner job (the `google/osv-scanner-action` reusable workflow), and a `gitleaks` job (`gitleaks/gitleaks-action@v3`) — each individually omittable; and a `.github/dependabot.yml` with grouped weekly updates for the `maven`, `docker`, and `github-actions` ecosystems, plus `npm` (pointed at the real web module's directory) when the manifest's `frontend` isn't `none`. Reads `sonar.mode` from `springboot-stack.yml` as the source of truth for whether the Sonar step and `SONAR_TOKEN` secret are generated at all, rather than asking reactively. Derives the pipeline from `springboot-stack.yml` and the actual reactor/`infra/` layout on disk, lists every required repository secret and environment, and never writes a credential into a workflow file. Invoke as `/iru-setup-java-springboot-github-workflows`, or with `args` (`stack-file:`, `integration-branch:`, `main-branch:` lines, plus `security-dependency-review`/`security-codeql`/`security-osv`/`security-gitleaks`, each `yes`/`no`, default `yes`) when called from `iru-setup-java-springboot`. Use whenever a Spring Boot service needs its CI/CD pipeline bootstrapped instead of hand-writing the YAML for testing, analysis, documentation publishing, deployment, teardown, and dependency/secret/code security scanning.
model: sonnet
---

# Setup Java Spring Boot GitHub Workflows

Generate three workflows for a Spring Boot service. This is deliberately a different pipeline from the
library-oriented `iru-setup-java-github-workflows`: a service is not published to Maven Central and is not
GPG-signed — it is built into a container image and deployed. The shared stages (test, analyse, Sonar, Antora,
GitHub Pages) follow the same house pattern as that skill, so the two are recognisably related; the publish/sign/
sync stages are replaced by image build, OpenTofu apply, and teardown.

| Workflow | Trigger | Does |
|---|---|---|
| `build.yml` | push to integration/main branch, and every pull request | build, unit tests, integration tests, static analysis, coverage, Sonar (when `sonar.mode` isn't `none`), docs; publishes Pages from the main branch only |
| `deploy.yml` | `workflow_dispatch` (environment input) and optionally on release published | build + push image, OIDC auth, `tofu apply`, smoke check |
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
```

- **`stack-file`**/**`integration-branch`**/**`main-branch`** — as before.
- **`security-dependency-review`**/**`security-codeql`**/**`security-osv`**/**`security-gitleaks`** — each
  `yes`/`no`, default `yes` when not supplied. Individually gate the matching job in `security.yml` (Step 3b);
  `.github/dependabot.yml` itself is always generated regardless of these four flags, since dependency updates and
  vulnerability scanning are two different concerns. Any not supplied via `args` is asked with `AskUserQuestion`
  (default yes) rather than silently assumed, unless this skill is running unattended as part of
  `iru-setup-java-springboot`'s Step 8, in which case the default stands without asking.

Read `springboot-stack.yml` for the cloud, the Java version, `sonar.mode`
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
- The branch model: run `git branch -a`, don't assume gitflow. Confirm the integration and main branch names.
- Whether GitHub Environments already exist (`gh api repos/{owner}/{repo}/environments`) — `deploy.yml` and
  `undeploy.yml` depend on them for approval gates.
- Whether `compose.yaml` exists and how heavy the container stack is: integration tests on a standard GitHub
  runner (4 vCPU / 16 GB) can't host Elasticsearch + Couchbase + Kafka + several databases simultaneously. If the
  stack looks too large, say so now and offer either a larger runner or splitting integration tests into a matrix
  by module.

If any workflow file already exists, use `AskUserQuestion` to ask whether to stop or to update it, preserving any
step this skill doesn't own (a Slack notification, an extra matrix leg) and only correcting the stages it does.

## Step 1 — `build.yml`

Structure it as two jobs so a pull request gets fast feedback and Pages publishing only happens on the main branch.

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
        uses: actions/checkout@v5
        with:
          # Sonar needs full history to attribute issues to blame data.
          fetch-depth: 0

      - name: Set up JDK <java-version>
        uses: actions/setup-java@v5
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
        uses: actions/upload-artifact@v4
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
        uses: actions/checkout@v5

      - name: Set up JDK <java-version>
        uses: actions/setup-java@v5
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

If the manifest's `sonar.mode` is `none`, drop the entire `Run SonarCloud analysis` step from `build.yml` rather
than leaving it in with a permanently-false condition — dead YAML that can never run is worse than no YAML.

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
        uses: actions/checkout@v5

      - name: Set up JDK <java-version>
        uses: actions/setup-java@v5
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
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}
      # Google Cloud variant (use instead of the above):
      # - uses: google-github-actions/auth@v2
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
        uses: opentofu/setup-opentofu@v1

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
          for i in $(seq 1 30); do
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
        uses: actions/checkout@v5

      - name: Configure cloud credentials
        # Same OIDC step as deploy.yml
        run: echo "replace with the AWS or Google Cloud OIDC auth action"

      - name: Set up OpenTofu
        uses: opentofu/setup-opentofu@v1

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

Additional guards to put in, and to explain in the report:

- **`stop` is the default**, and it's reversible: re-running `deploy.yml` brings the service back with its data
  intact. `destroy` is not reversible.
- **Data-bearing resources should have deletion protection enabled in the OpenTofu configuration**, so `destroy`
  fails on them rather than silently deleting a production database. That means `destroy` on `prod` will error
  until someone deliberately removes the protection — which is correct behaviour, not a bug. Say this explicitly.
- Recommend restricting `prod` in the Environment settings to required reviewers **and** a deployment branch rule,
  so this workflow can't be dispatched from an arbitrary branch.
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
        uses: actions/checkout@v5
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
        uses: actions/checkout@v5
      - name: Set up JDK <java-version>
        uses: actions/setup-java@v5
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
    uses: google/osv-scanner-action/.github/workflows/osv-scanner-reusable.yml@v2
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
        uses: actions/checkout@v5
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

## Step 4 — Required secrets, variables, and environments

Report these as a table; this skill cannot create them.

| Name | Kind | Purpose |
|---|---|---|
| `SONAR_TOKEN` | repository secret | SonarCloud/SonarQube scan — **only listed when `sonar.mode` isn't `none`**; omit this row entirely for `sonar.mode: none` |
| `AWS_DEPLOY_ROLE_ARN` | environment secret | OIDC role assumed per environment (AWS) |
| `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_DEPLOY_SERVICE_ACCOUNT` | environment secrets | OIDC identity (Google Cloud) |
| `AWS_REGION` / `GCP_PROJECT_ID`, `GCP_REGION` | environment variables | not secret, but environment-specific |
| `IMAGE_REPOSITORY` | environment variable | the registry path the image is pushed to |
| `<PROVIDER>_API_KEY` | environment secret | LLM provider key, if `stack.ai.enabled` — never in the repository |
| third-party provider tokens (`MONGODB_ATLAS_*`, `CONFLUENT_CLOUD_*`, …) | environment secrets | needed by the OpenTofu providers for managed services outside the cloud account |

`frontend: hilla` needs no new secret or variable of its own — `npm ci`/`npx vitest`/`vaadin:build-frontend` all
run unauthenticated against the public npm registry and Maven Central, so this table is unchanged by it.

`GITHUB_TOKEN` needs no setup and is all four `security.yml` jobs (Step 3b) require — none of `dependency-review`,
CodeQL, OSV-Scanner, or gitleaks need a secret of their own in the free/public-repository tier of each action.
Also required, and easy to miss:

- **A GitHub Environment per deployment environment**, with required reviewers on `prod`.
- **GitHub Pages** configured to serve from the `gh-pages` branch (Settings → Pages), or the docs job publishes
  into a branch nobody reads.
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
- Confirm the Maven commands actually work locally first (`mvn -B -ntp clean verify`, `mvn -B -ntp site
  -DskipTests -Djacoco.skip`, `mvn -B -ntp generate-resources`) — delegate to `iru-gate-runner` for a compact
  result. A workflow whose commands were never run locally is a guess.
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
  workflow**: `mvn -B -ntp clean verify -Pproduction -Dvaadin.ci.build=true` first, then `npm ci` and
  `npx vitest run --coverage` in the web module. Running the npm/vitest commands before the Maven build fails on
  a module-not-found error from `vite.generated.ts` (it imports compiled helpers under `<web-module>/target/`)
  that has nothing to do with the frontend tests — confirmed while writing `iru-setup-java-springboot-hilla`, and
  the single most likely way this ordering gets silently swapped in a future edit.
- Do **not** trigger `deploy.yml` or `undeploy.yml` as a test. Recommend instead: a dry run of `build.yml` by
  pushing to a throwaway branch with the trigger temporarily widened, and a first `deploy.yml` run against `dev`
  only, watched to completion.
- Check `security.yml` and `.github/dependabot.yml` parse the same way as the other workflows, and confirm every
  `security-*` flag from Step 0 produced exactly the jobs it should — a flag left `no` must mean the job's whole
  entry is absent from the file, not present-but-disabled.

## Step 6 — Report

Summarize: which workflow files were created or updated; the branch names and Java version resolved; whether the
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

Warn explicitly:

- **Review all workflows before pushing.** `deploy.yml` and `undeploy.yml` change and destroy real
  infrastructure; a wrong environment name or a missing approval gate has immediate consequences.
- **Configure required reviewers on `prod` before the workflows land on the main branch**, not after — until then,
  anyone with write access can dispatch a production deploy or teardown.
- **Verify the OIDC trust policy is scoped to the repository *and* the environment.**
- Integration tests need Docker on the runner; if the compose stack is too heavy for `ubuntu-latest`, the first
  `build.yml` run will fail on resource exhaustion rather than on a code defect — deal with it now if Step 0
  flagged it.
- Nothing in these files contains a credential, and it must stay that way: every new value goes in as a secret or
  variable reference.
