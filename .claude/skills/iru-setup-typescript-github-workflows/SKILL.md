---
name: iru-setup-typescript-github-workflows
description: Create or update the `build.yml`, `release.yml`, `sync.yml` (library/web flavors only), and `security.yml` GitHub Actions workflows plus `.github/dependabot.yml` for an npm/TypeScript repository of one of five flavors — `library` (a published npm package), `react` (a Vite/React web app), `angular` (an Angular CLI web app), `react-native` (an Expo app), or `ionic` (an Ionic + Capacitor hybrid app). `build.yml` runs on every push to the integration/stable branches, every pull request, and `workflow_dispatch`: checkout, Node setup with dependency caching, install, lint, format check, typecheck, unit tests with coverage, an optional SonarQube/SonarCloud scan (skipped on fork pull requests), Playwright e2e for web flavors, a docs build (TypeDoc/Compodoc/Storybook, gated by `docs-tool`) merged with an Antora build, and a GitHub Pages deploy from the stable branch only. `release.yml` is flavor-specific: for `library` it publishes to npm on `release: published` via OIDC trusted publishing plus an optional Changesets version-PR job; for `react`/`angular` it builds and deploys `dist/` to Pages; for `react-native` it runs EAS or local Gradle/Xcode builds per `native-builds`; for `ionic` it builds Android/iOS store or internal artifacts per `distribution`. `sync.yml` + `.github/scripts/sync_versions.py` (library/react/angular only) merge the stable branch back into the integration branch and bump `package.json`'s version to the next `x.y.(z+1)-dev.0` prerelease plus README/Antora version mentions. `security.yml` runs the shared Dependabot(`npm`)/dependency-review/CodeQL(`javascript-typescript`, `build-mode: none`)/OSV-Scanner/gitleaks block. Invoke as `/iru-setup-typescript-github-workflows`. Ships with generic example templates (genericized, no real repo/org names) embedded in this skill file. Creates all workflows (and the sync/security scripts) from scratch if none exist; if any already exists, asks the user whether to stop or attempt an update using the templates as reference. Accepts pre-resolved inputs via `args` (`key: value` lines): `flavor` (`library`/`react`/`angular`/`react-native`/`ionic`, required), `integration-branch` (default `develop`), `stable-branch` (default `main`), `node-version` (default `24`), `package-manager` (`npm`/`pnpm`/`yarn`), `open-source` (`yes`/`no`), `publish` (`yes`/`no` — library only, gates the npm publish job), `distribution` (`none`/`internal`/`store` — react-native/ionic only, gates native store/signing steps), `sonar` (`cloud`/`self-hosted`/`none`, + `sonar-organization`/`sonar-project-key`/`sonar-host-url`), `native-builds` (`eas`/`local` — react-native only), `framework` (`angular`/`react` — ionic only), `docs-tool` (`typedoc`/`compodoc`/`storybook`/`none`), and `security-dependency-review`/`security-codeql`/`security-osv`/`security-gitleaks` (each `yes`/`no`, default `yes`), so an orchestrating skill can supply them without re-prompting. Use whenever an npm/TypeScript repository of any of these five flavors needs this CI/CD release and security pipeline bootstrapped or brought in line with this house pattern, instead of hand-writing the YAML.
model: haiku
---

# Setup TypeScript GitHub Workflows

Scaffold (or update) up to four GitHub Actions workflows plus a Dependabot config for an npm/TypeScript
repository, for whichever `flavor` the repository actually is:

- **`build.yml`** — runs on every push to the integration branch, every push to the stable branch, every pull
  request, and `workflow_dispatch`. Install, lint, format check, typecheck, unit tests with coverage, an
  optional SonarQube/SonarCloud scan (gated by `sonar`, skipped on pull requests from a fork), Playwright e2e
  for the web flavors (`react`, `angular`, `ionic`), a docs build gated by `docs-tool` merged with an Antora
  build, and a GitHub Pages deploy of the merged docs site — the Pages deploy only runs on a push to the
  stable branch.
- **`release.yml`** — flavor-specific; see Step 3. Always triggered by `release: [published]` (plus
  `workflow_dispatch` for a manual re-run) so a continuous-deployment push to the stable branch never
  accidentally re-publishes or re-signs a release artifact.
- **`sync.yml`** — **library/react/angular flavors only** (the three that keep a version in `package.json`
  meaningfully bumped between releases; `react-native`/`ionic` app versions are usually driven by store
  submission tooling instead — see Step 1). Triggered when a GitHub Release is published from the stable
  branch. Opens a pull request into the integration branch that merges the released branch back in and bumps
  the development prerelease version in `package.json` (and its lockfile), `README.md`, and the Antora docs,
  via the companion script `.github/scripts/sync_versions.py`.
- **`security.yml`** — runs on every pull request and push to the integration/stable branches: a
  `dependency-review` job (`actions/dependency-review-action@v5`), a CodeQL job
  (`github/codeql-action@v4`, language `javascript-typescript`, `build-mode: none` — no compile step is
  needed for JS/TS analysis), an OSV-Scanner job (the `google/osv-scanner-action` reusable workflow), and a
  `gitleaks` job (`gitleaks/gitleaks-action@v3`) — each individually omittable via `args` (defaulting to on;
  see Step 1).
- **`.github/dependabot.yml`** — grouped weekly dependency updates for the `npm` ecosystem and for
  `github-actions` itself. Always generated (or updated) regardless of the four `security-*` `args` keys
  above — it's baseline repository hygiene, not an optional CI job.

This skill is designed for npm/TypeScript projects produced by the matching scaffold skill
(`iru-setup-typescript-library`, `iru-setup-react-web`, `iru-setup-angular-web`,
`iru-setup-react-native-app`, `iru-setup-ionic-app`) — the templates in Step 3 assume the fixed npm script
names those skills wire up (`build`, `test`, `coverage`, `lint`, `format`, `typecheck`, `docs`). If
`package.json` is missing at the repository root, don't stop automatically: warn the user that this skill's
templates assume an npm/TypeScript project and most of Step 1's survey won't resolve, then use
`AskUserQuestion` to ask whether to stop here or continue anyway. If they choose to continue, proceed through
the remaining steps but treat every `package.json`-derived placeholder in Step 3/4 (script names, Node
version, package manager) as an open gap to ask the user about directly, and call this out prominently again
in Step 8's report.

## Step 1 — Survey the target repository

This skill can be invoked stand-alone (`/iru-setup-typescript-github-workflows`) or as a step inside another
skill, which resolves the parameters below itself and passes them through `args` as `key: value` lines, one
per line, e.g.:

```
flavor: library
integration-branch: develop
stable-branch: main
node-version: 24
package-manager: npm
open-source: yes
publish: yes
sonar: cloud
sonar-organization: example-github
sonar-project-key: example_my-library
sonar-host-url: https://sonarcloud.io
docs-tool: typedoc
security-dependency-review: yes
security-codeql: yes
security-osv: yes
security-gitleaks: yes
```

Parse any such lines from `args` first. For each key found there, use that value directly — skip the
corresponding fact-finding bullet below entirely for it. If `args` is absent or doesn't look like this
format, treat everything as unset and gather every fact below as usual.

- **`flavor`** (skip if supplied via `args`): if not given, detect it with the same rule Tasks 12–17 of this
  catalog's TypeScript group share — inspect `package.json`: `@vaadin/hilla`/`hilla-spring-boot-starter` in a
  parent `pom.xml`, or a `src/main/frontend/` directory → `hilla-frontend` (not one of this skill's five
  flavors — warn the user this skill doesn't cover Hilla frontends and stop); `expo` or `react-native` in
  dependencies → `react-native`; `@ionic/angular` or `@ionic/react` + `@capacitor/core` → `ionic`;
  `@angular/core` → `angular`; `react` + `vite` (or `@vitejs/plugin-react`) → `react`; otherwise → `library`.
  Ask the user to confirm if the detection is ambiguous (e.g. both `react` and `@capacitor/core` present).
- **Package manager** (skip if `package-manager` supplied via `args`): `packageManager` field in
  `package.json`, else lockfile present — `package-lock.json` → `npm`, `pnpm-lock.yaml` → `pnpm`,
  `yarn.lock` → `yarn` (and for `yarn`, check for `.yarnrc.yml` to tell Yarn Berry apart from Yarn Classic —
  Berry uses `yarn install --immutable`, Classic uses `yarn install --frozen-lockfile`). Default `npm` if
  none of these resolve anything.
- **Node version** (skip if `node-version` supplied via `args`): read `engines.node` from `package.json`. If
  absent, ask the user, offering `24` as the default — this catalog's default Node version for new
  repositories (the current Active LTS as of September 2026), and the one the `iru-setup-typescript-*`
  scaffold skills write into a generated `package.json`. Whenever `engines.node` differs from `24`, use what
  `package.json` says (CI must build what the project actually targets) and note the difference in Step 8's
  report.
- **`open-source`** (skip if supplied via `args`): check whether the GitHub repository is public
  (`gh repo view --json isPrivate`) if unresolved otherwise; ask the user only if that's inconclusive
  (e.g. no `gh` remote configured).
- **`publish`** (library flavor only; skip entirely if supplied via `args`): grep `package.json` for
  `"private": true` (implies `publish: no`) or a `publishConfig` block (implies `publish: yes`). If neither
  is conclusive, default to `publish: no` rather than stopping — tell the user npm publishing isn't wired up
  and ask only if they want it added now, or confirm `publish: no` is correct.
- **`distribution`** (react-native/ionic flavors only; skip entirely if supplied via `args`): ask the user
  directly — `none` (CI builds only, nothing is signed or uploaded), `internal` (a signed build artifact, or
  a Firebase App Distribution / TestFlight-internal push if they opt in — ask a follow-up yes/no, default
  "just the artifact, no extra secrets"), or `store` (Google Play / App Store Connect production track,
  needs the signing/API-key secrets in Step 7's table).
- **`native-builds`** (react-native flavor only; skip if supplied via `args`): ask the user `eas` (Expo
  Application Services — simplest, but the free tier is capped at 15 builds/platform/month) or `local`
  (self-hosted Gradle on `ubuntu-latest` + `xcodebuild` on `macos-latest`, no EAS account needed but slower
  runners and the repository must manage its own signing material).
- **`framework`** (ionic flavor only; skip if supplied via `args`): detect from `package.json`
  (`@ionic/angular` vs `@ionic/react`), confirm with the user if ambiguous.
- **`docs-tool`** (skip if supplied via `args`): `typedoc.json` present → `typedoc`; `.compodocrc`/`compodoc`
  script → `compodoc`; `.storybook/` directory → `storybook`; none of these found → ask the user, defaulting
  to `typedoc` for `library`, `compodoc` for `angular`, `none` for `react-native`/`ionic` (mobile apps rarely
  publish a public API doc site) unless the survey found a doc tool already configured.
- **`sonar`** (skip entirely if supplied via `args`): check for `sonar-project.properties` at the repository
  root and its `sonar.organization`/`sonar.projectKey`/`sonar.host.url` keys — this house pattern's
  `SonarSource/sonarqube-scan-action@v8` step reads that file automatically with no extra `with:` args, so
  the config lives there, not inline in the workflow. If present, treat that as `sonar: cloud` (when
  `sonar.host.url` is `https://sonarcloud.io` or unset) or `sonar: self-hosted` (any other host). If absent,
  default to `sonar: none` (omit the scan step entirely) rather than generating a step that can't succeed;
  ask the user only if they want Sonar wired up now instead — recommend `cloud` only when `open-source: yes`
  (SonarCloud is free only for open-source projects), otherwise flag the paid-plan caveat.
- **Antora docs**: check for `docs/antora.yml` and `docs/antora-playbook.yml`. If either is missing, the
  docs step in Step 3 has nothing to build against — tell the user to run the `iru-setup-antora` skill first,
  or confirm they'll do so before merging this workflow.
- **Branch names** (skip the integration branch if `integration-branch` supplied via `args`, likewise
  `stable-branch`): confirm the integration branch (commonly `develop`) and the stable branch (commonly
  `main`) actually match this repository's branching model — run `git branch -a` or ask, don't assume
  gitflow defaults.
- **README/Antora version-snippet wording** (only needed for `sync.yml`'s companion script,
  `sync_versions.py`, and only for the `library`/`react`/`angular` flavors that get a `sync.yml` at all):
  grep for the marker text and its surrounding lines — `grep -B2 -A2 -i "current development version\|latest
  release\|latest snapshot" README.md`, and for Antora pages, `grep -rl "\"version\"\|<version>"
  docs/modules/ROOT/pages/*.adoc`. From that context, find the exact row label used for the development row
  (e.g. `Current development version`) and the exact marker text preceding each version mention. Note any
  deviation from the `iru-setup-readme` skill's default convention now so Step 4 can adjust the template. If
  `README.md` doesn't exist yet, tell the user `sync_versions.py`'s README step will need hand-adjustment once
  the file exists.
- **Existing npm scripts**: confirm `package.json`'s `scripts` block actually has `build`, `test`,
  `coverage`, `lint`, `format`, `typecheck`, and (when `docs-tool` isn't `none`) `docs` — these are the exact
  script names `build.yml` invokes via `npm run <name>`. Note any that are missing or named differently so
  Step 4 can adjust the template rather than generate a step that fails immediately.
- **Playwright** (`react`/`angular`/`ionic` only): check for a `playwright.config.ts` and an `e2e`/`e2e:ci`
  script. If absent, the e2e step in `build.yml` has nothing to run — note this as an open gap; the scaffold
  skills for these flavors are expected to have wired it already.

The four `security-*` keys each default to `yes` when not supplied via `args` and are not otherwise
surveyed — this skill always adds/keeps the corresponding `security.yml` job unless the user (or an
orchestrator's `args`) explicitly opts out. `.github/dependabot.yml` has no matching opt-out key — it's
always generated/updated.

## Step 2 — Decide how to proceed if workflows already exist

Check whether `.github/workflows/build.yml`, `.github/workflows/release.yml`, `.github/workflows/sync.yml`,
`.github/scripts/sync_versions.py`, `.github/workflows/security.yml`, and `.github/dependabot.yml` already
exist (skip the `sync.yml`/script check entirely for the `react-native`/`ionic` flavors, which never get
one). Treat `sync.yml` and its script as one unit for this check — either both exist or neither should.

- **None exist**: skip this step and go straight to Step 4 — create everything from scratch.
- **Any exists**: use `AskUserQuestion` to ask whether to (a) stop here and leave everything untouched, or
  (b) continue and attempt to update the existing file(s) using this skill's templates as reference.
  - **Stop**: report which file(s) already exist and end here — make no changes.
  - **Continue**: proceed to Step 4, but treat each existing file as the base to edit, not as something to
    overwrite wholesale.
    - For `build.yml`: preserve any step that isn't one of the pipeline stages this skill owns
      (install/lint/format/typecheck/test/coverage, optional Sonar, optional e2e, docs build, Pages deploy) —
      e.g. a Slack notification step or an extra matrix entry stays untouched. Only add missing stages or
      correct outdated ones (wrong action version, wrong script name, a stage that should now be gated
      on/off per `sonar`/`docs-tool`, etc.), and don't reorder steps this skill doesn't own.
    - For `release.yml`: preserve any job/step outside this flavor's owned jobs; only correct the
      publish/build/signing jobs per the resolved `publish`/`distribution`/`native-builds` `args`.
    - For `sync.yml`/`sync_versions.py`: preserve any file the script updates beyond
      `package.json`/`README.md`/the Antora docs that a prior customization added, and preserve any extra
      workflow step the same way. Only correct the pipeline stages this skill owns.
    - For `security.yml`: preserve any job this skill doesn't own; only add/remove/update the
      `dependency-review`/CodeQL/OSV-Scanner/gitleaks jobs per the resolved `security-*` `args` (Step 1).
    - For `.github/dependabot.yml`: preserve any `updates:` entry for an ecosystem this skill doesn't manage
      (e.g. `maven` for a sibling backend); only add/update the `npm` and `github-actions` entries.

## Step 3 — Reference templates

These are genericized examples showing the full pipeline. Copy the structure; resolve every `<placeholder>`
using Step 1's survey before writing the real files in Step 4 (the full resolution table is in Step 4), and
drop whichever blocks this repository's `sonar`/`docs-tool`/`publish`/`distribution` values gate off, per the
inline comments in the templates below. **Versions are looked up at run time, not hardcoded from this file**:
query the npm registry (`npm view <package> version`) for every devDependency version this skill's own
supporting files reference, and the GitHub Releases API (`gh api repos/<owner>/<action>/releases/latest`, or
`.../tags` when an action publishes tags without a matching GitHub Release, as `github/codeql-action` and
`SonarSource/sonarqube-scan-action` do) for every `uses:` action major. If either lookup is unreachable, fall
back to the versions confirmed current as of **September 2026**, listed here:

| Action | Fallback version | Notes |
|---|---|---|
| `actions/checkout` | `v7` | |
| `actions/setup-node` | `v7` | |
| `actions/upload-artifact` | `v7` | |
| `actions/download-artifact` | `v8` | note this trails a different major than `upload-artifact` — check both independently, they don't move in lockstep |
| `actions/upload-pages-artifact` | `v5` | |
| `actions/deploy-pages` | `v5` | |
| `actions/configure-pages` | `v6` | |
| `actions/setup-python` | `v7` | used only by `sync.yml` |
| `actions/setup-java` | `v6` | used only by the react-native/ionic Android jobs (Gradle needs a JDK) |
| `android-actions/setup-android` | `v4` | Android SDK/cmdline-tools setup for the Android release jobs |
| `pnpm/action-setup` | `v6` | only when `package-manager: pnpm` — `setup-node`'s built-in `cache: pnpm` needs `pnpm` already on `PATH`, which this action provides; without it the cache step fails with "Dependency lock file is not found" even though `pnpm-lock.yaml` exists |
| `actions/dependency-review-action` | `v5` | |
| `github/codeql-action` (`init`/`analyze`) | `v4` | resolve via `.../tags`, not `.../releases/latest` — that endpoint returns the unrelated `codeql-bundle-*` tag |
| `SonarSource/sonarqube-scan-action` | `v8` | resolve via `.../tags` too, for the same reason |
| `google/osv-scanner-action` (reusable workflow) | `v2` | pin the workflow ref, e.g. `google/osv-scanner-action/.github/workflows/osv-scanner-reusable.yml@v2` |
| `gitleaks/gitleaks-action` | `v3` | |
| `changesets/action` | `v2` | library flavor only |
| `expo/expo-github-action` | `9` (no `v` prefix) | react-native/`native-builds: eas` only |
| `r0adkll/upload-google-play` | `v1` | ionic/`distribution: store` Android upload only |
| `wzieba/Firebase-Distribution-Github-Action` | `v1` | only if the user opted into Firebase App Distribution for `distribution: internal` |

npm's trusted publishing (OIDC, no `NPM_TOKEN` secret, automatic provenance) requires **npm ≥ 11.5.1** —
`actions/setup-node@v7` bundles a current npm already, but if a project pins an older npm via `packageManager`,
flag that as an open gap in Step 8; the `npm publish` step in `release.yml` will otherwise fail with an
auth error instead of using OIDC.

When validating a filled-in workflow with `python3 -c "import yaml; yaml.safe_load(...)"` (or any other
YAML-1.1 tool), expect the top-level `on:` key to round-trip as the boolean `True`, not the string `"on"` —
PyYAML's default resolver still treats bare `on`/`off`/`yes`/`no` as booleans per YAML 1.1, while GitHub's own
workflow parser special-cases `on` as a string. This is a false flag in the *validator*, not a bug in the
generated workflow; don't "fix" it by quoting `on:` in the template (GitHub's parser is stricter about that
than you'd expect for some older Actions runners) — just don't treat that particular diff as an error when
comparing parsed YAML structure.

### `build.yml` template

```yaml
name: Build

on:
  push:
    branches: [ <integration-branch>, <stable-branch> ]
  pull_request:
  workflow_dispatch:

concurrency:
  group: build-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build:
    name: Build, lint and test
    runs-on: ubuntu-latest
    steps:
      - name: Check out code
        uses: actions/checkout@v7
        with:
          fetch-depth: 0

      - name: Set up Node <node-version>
        uses: actions/setup-node@v7
        with:
          node-version: <node-version>
          cache: <package-manager> # 'npm' | 'pnpm' | 'yarn' — requires the matching lockfile to already exist

      # Only when package-manager: pnpm (Step 1) — must run before setup-node's cache step can find pnpm
      - name: Set up pnpm
        uses: pnpm/action-setup@v6

      - name: Install dependencies
        run: <install-command> # npm ci | pnpm install --frozen-lockfile | yarn install --frozen-lockfile (or --immutable for Yarn Berry)

      - name: Lint
        run: <package-manager-run> lint

      - name: Check formatting
        run: <package-manager-run> format

      - name: Typecheck
        run: <package-manager-run> typecheck

      - name: Run tests with coverage
        run: <package-manager-run> coverage

      # Omit this whole step if sonar: none (Step 1). Also skipped on pull requests from a fork, which never
      # get repository secrets, so SONAR_TOKEN would be empty and the scan would fail rather than just skip.
      - name: Run SonarQube/SonarCloud analysis
        if: github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository
        uses: SonarSource/sonarqube-scan-action@v8
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          # Only when sonar: self-hosted — omit for sonar: cloud, which defaults to https://sonarcloud.io
          SONAR_HOST_URL: <sonar-host-url>

      # Omit this whole block if flavor is not one of: react, angular, ionic (react-native has no web build to
      # drive a browser against; library has no UI at all)
      - name: Install Playwright browsers
        run: npx playwright install --with-deps chromium
      - name: Run e2e tests
        run: <package-manager-run> e2e
      - name: Upload Playwright report
        if: failure()
        uses: actions/upload-artifact@v7
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 14

      # Omit this whole step if docs-tool: none (Step 1)
      - name: Build API docs
        run: <package-manager-run> docs # typedoc -> docs/api ; compodoc -> docs/api ; storybook build -> storybook-static

      - name: Install Antora
        run: |
          mkdir -p docs-site && cd docs-site
          npm i -D -E antora
          npm i @antora/lunr-extension
          npm i @sntke/antora-mermaid-extension
          npm i @djencks/asciidoctor-mathjax

      - name: Build Antora docs
        run: cd docs && npx antora antora-playbook.yml

      - name: Merge documentation
        run: |
          touch ./docs/build/site/.nojekyll
          # docs-tool: typedoc or compodoc — merge the generated API reference under the Antora site
          mkdir -p ./docs/build/site/api && cp -r ./docs/api/. ./docs/build/site/api/
          # docs-tool: storybook — merged under a sibling path instead, since Storybook isn't an API reference
          mkdir -p ./docs/build/site/storybook && cp -r ./storybook-static/. ./docs/build/site/storybook/

      - name: Upload Pages artifact
        if: github.ref == format('refs/heads/{0}', '<stable-branch>') && github.event_name == 'push'
        uses: actions/upload-pages-artifact@v5
        with:
          path: ./docs/build/site

  deploy-docs:
    name: Deploy docs to GitHub Pages
    needs: build
    if: github.ref == format('refs/heads/{0}', '<stable-branch>') && github.event_name == 'push'
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Configure Pages
        uses: actions/configure-pages@v6
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v5
```

Notes specific to this template:

- Only ONE of the two `Merge documentation` `mkdir`/`cp` lines applies per repository — keep the one matching
  the resolved `docs-tool` (`typedoc`/`compodoc` → `docs/api`; `storybook` → a `docs/build/site/storybook`
  sibling path, since Storybook is a component gallery, not an API reference, and merging it under `api/`
  would be misleading) and drop the other, plus the whole `Build API docs`/merge block when `docs-tool: none`.
- `actions/upload-pages-artifact`/`actions/deploy-pages` need the repository's Settings → Pages → "Build and
  deployment" → Source set to **GitHub Actions** (not "Deploy from a branch") — `deploy-pages` fails outright
  if that setting still points at a branch. Call this out in Step 7/8.
- The `concurrency` group on `deploy-pages`-style jobs matters: without it, two pushes to the stable branch in
  quick succession can race and leave Pages showing an older deploy that finished last. The `build` job's own
  `concurrency` group (workflow-level, keyed on `ref`) already serializes runs on the same branch, which is
  sufficient here since `deploy-docs` only runs from the stable branch's own `build.yml` run.
- `<package-manager-run>`: `npm run` / `pnpm run` / `yarn run` (or bare `yarn <script>` for Yarn) — resolve
  once in Step 4 and reuse for every `run:` line above.
- `setup-node`'s `cache: <package-manager>` fails outright if the matching lockfile doesn't exist yet
  ("Dependencies lock file is not found") — never generate this workflow before the scaffold skill has run
  `npm install`/`pnpm install`/`yarn install` at least once and committed the lockfile.

### `release.yml` template — `library` flavor

```yaml
name: Release

on:
  release:
    types: [published]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  # Omit this whole job if publish: no (Step 1) — a private package can't be published. With both this job and
  # version-pr omitted, do not write release.yml for the library flavor at all: an `on: release` workflow with no
  # jobs is invalid YAML for Actions, and Step 8 reports the file as "not generated (publish: no)".
  publish:
    name: Publish to npm
    runs-on: ubuntu-latest
    permissions:
      id-token: write # required for npm OIDC trusted publishing — no NPM_TOKEN secret needed
      contents: read
    steps:
      - name: Check out code
        uses: actions/checkout@v7

      - name: Set up Node <node-version>
        uses: actions/setup-node@v7
        with:
          node-version: <node-version>
          cache: <package-manager>
          registry-url: https://registry.npmjs.org

      - name: Install dependencies
        run: <install-command>

      - name: Build
        run: <package-manager-run> build

      - name: Publish
        run: npm publish
        # Provenance and OIDC identity are automatic once registry-url is set above and the trusted publisher
        # is configured on npmjs.com for this package, naming THIS workflow file (release.yml) and job
        # (publish) — see Step 7. No NODE_AUTH_TOKEN/NPM_TOKEN env var is needed or should be set here.

  # Omit this whole job if publish: no (Step 1) — Changesets manages the version-PR workflow, so it only
  # makes sense once npm publishing itself is wired up
  version-pr:
    name: Open/update the Changesets version PR
    if: github.event_name == 'workflow_dispatch' || github.ref == format('refs/heads/{0}', '<stable-branch>')
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - name: Check out code
        uses: actions/checkout@v7
        with:
          fetch-depth: 0

      - name: Set up Node <node-version>
        uses: actions/setup-node@v7
        with:
          node-version: <node-version>
          cache: <package-manager>

      - name: Install dependencies
        run: <install-command>

      - name: Create or update the version PR
        uses: changesets/action@v2
        with:
          version: <package-manager-run> changeset version
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Notes specific to this template:

- This job triggers on a push to the stable branch — not on `release: published` like the `publish` job above
  it — because its purpose is to open the *next* version-bump PR once the current release has landed, not to
  react to the release itself; the top-level `on:` block above only lists `release`/`workflow_dispatch`, so
  add `push: branches: [ <stable-branch> ]` to the workflow's `on:` block when `publish: yes` includes this
  job (both triggers coexist in the same file).
- `changesets/action@v2` needs `.changeset/config.json` to already exist (the `iru-setup-typescript-library`
  scaffold creates it when `publish: yes`) — if it's missing, note this as an open gap rather than generating
  a job that no-ops silently.

### `release.yml` template — `react`/`angular` flavors

```yaml
name: Release

on:
  release:
    types: [published]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  deploy:
    name: Build and deploy to GitHub Pages
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
      contents: read
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Check out code
        uses: actions/checkout@v7

      - name: Set up Node <node-version>
        uses: actions/setup-node@v7
        with:
          node-version: <node-version>
          cache: <package-manager>

      - name: Install dependencies
        run: <install-command>

      - name: Build production bundle
        run: <package-manager-run> build

      - name: Upload build artifact
        uses: actions/upload-artifact@v7
        with:
          name: dist
          path: dist/
          retention-days: 30

      - name: Configure Pages
        uses: actions/configure-pages@v6
      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v5
        with:
          path: dist/
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v5
```

Notes specific to this template:

- **Decision made (no ambiguity worth blocking on):** this job deploys the built app to the *same* GitHub
  Pages site `build.yml`'s `deploy-docs` job publishes the Antora/API docs to, and each workflow's own Pages
  deploy fully replaces whatever the other last published — there is no single-site "merge" between the two
  workflows across separate runs. Recommend the app deploy publish under the site root and treat the docs
  deploy as informational only (or vice-versa, published under a `/docs` subpath by copying the merged Antora
  site into `dist/docs/` before this job's `Upload Pages artifact` step) if the repository genuinely needs
  both live at once; flag this explicitly in Step 8's report as a design choice the user should confirm rather
  than something this skill resolves silently.
- `actions/upload-artifact` here is a convenience for downloading the exact bundle that was deployed (e.g. for
  a manual smoke test) — it isn't consumed by any later job in this workflow.

### `release.yml` template — `react-native` flavor, `native-builds: eas`

```yaml
name: Release

on:
  release:
    types: [published]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  eas-build-and-submit:
    name: EAS build and submit
    runs-on: ubuntu-latest
    steps:
      - name: Check out code
        uses: actions/checkout@v7

      - name: Set up Node <node-version>
        uses: actions/setup-node@v7
        with:
          node-version: <node-version>
          cache: <package-manager>

      - name: Install dependencies
        run: <install-command>

      - name: Set up EAS
        uses: expo/expo-github-action@9
        with:
          token: ${{ secrets.EXPO_TOKEN }}
          eas-version: latest

      - name: EAS build (all platforms)
        run: eas build --platform all --non-interactive --profile production

      # Omit this whole step if distribution: internal (Step 1) — EAS submit always targets the store tracks
      - name: EAS submit (all platforms)
        run: eas submit --platform all --non-interactive --profile production
```

### `release.yml` template — `react-native` flavor, `native-builds: local`

```yaml
name: Release

on:
  release:
    types: [published]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  android:
    name: Android release build
    runs-on: ubuntu-latest
    steps:
      - name: Check out code
        uses: actions/checkout@v7

      - name: Set up Node <node-version>
        uses: actions/setup-node@v7
        with:
          node-version: <node-version>
          cache: <package-manager>

      - name: Install dependencies
        run: <install-command>

      - name: Set up JDK
        uses: actions/setup-java@v6
        with:
          distribution: temurin
          java-version: '21'

      - name: Set up Android SDK
        uses: android-actions/setup-android@v4

      - name: Prebuild native Android project
        run: npx expo prebuild --platform android --non-interactive

      # Omit these two decode/write steps entirely if distribution: none — an unsigned bundleRelease still
      # builds, but has no keystore to sign a distributable artifact with
      - name: Decode Android keystore
        run: echo "${{ secrets.ANDROID_KEYSTORE_BASE64 }}" | base64 -d > android/app/release.keystore
      - name: Write Gradle signing properties
        run: |
          cat >> android/gradle.properties <<EOF
          RELEASE_STORE_FILE=release.keystore
          RELEASE_STORE_PASSWORD=${{ secrets.ANDROID_KEYSTORE_PASSWORD }}
          RELEASE_KEY_ALIAS=${{ secrets.ANDROID_KEY_ALIAS }}
          RELEASE_KEY_PASSWORD=${{ secrets.ANDROID_KEY_PASSWORD }}
          EOF

      - name: Build release bundle
        working-directory: android
        run: ./gradlew bundleRelease

      - name: Upload AAB
        uses: actions/upload-artifact@v7
        with:
          name: app-release.aab
          path: android/app/build/outputs/bundle/release/app-release.aab

  ios:
    name: iOS release build
    runs-on: macos-latest
    steps:
      - name: Check out code
        uses: actions/checkout@v7

      - name: Set up Node <node-version>
        uses: actions/setup-node@v7
        with:
          node-version: <node-version>
          cache: <package-manager>

      - name: Install dependencies
        run: <install-command>

      - name: Prebuild native iOS project
        run: npx expo prebuild --platform ios --non-interactive

      - name: Install CocoaPods
        working-directory: ios
        run: pod install

      # Omit this whole block if distribution: none — building without a distribution profile still compiles,
      # but produces no signed, distributable .ipa
      - name: Import signing certificate and provisioning profile
        env:
          APP_STORE_CONNECT_API_KEY_BASE64: ${{ secrets.APP_STORE_CONNECT_API_KEY_BASE64 }}
        run: |
          echo "$APP_STORE_CONNECT_API_KEY_BASE64" | base64 -d > AuthKey.p8

      - name: Archive
        working-directory: ios
        run: xcodebuild -workspace App.xcworkspace -scheme App -configuration Release archive -archivePath build/App.xcarchive

      - name: Export IPA
        working-directory: ios
        run: |
          xcodebuild -exportArchive -archivePath build/App.xcarchive -exportPath build \
            -authenticationKeyPath ../AuthKey.p8 \
            -authenticationKeyID ${{ secrets.APP_STORE_CONNECT_API_KEY_ID }} \
            -authenticationKeyIssuerID ${{ secrets.APP_STORE_CONNECT_API_KEY_ISSUER_ID }} \
            -exportOptionsPlist ExportOptions.plist

      - name: Upload IPA
        uses: actions/upload-artifact@v7
        with:
          name: app-release.ipa
          path: ios/build/*.ipa
```

Notes specific to both `react-native` variants:

- `ExportOptions.plist` is a project-specific file this skill doesn't generate (it encodes the team id and
  export method) — note in Step 8 that the user must add it under `ios/` before this workflow can export an
  `.ipa`.
- Neither variant submits to a store automatically the way `eas submit` does — they upload a signed artifact
  only. If the user wants an automated Play Console/App Store Connect upload from the `local` path too, that's
  additional scope beyond what Task 9 asked for; note it as a follow-up rather than improvising an untested
  upload step.

### `release.yml` template — `ionic` flavor

```yaml
name: Release

on:
  release:
    types: [published]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  build-web:
    name: Build web bundle and sync Capacitor
    runs-on: ubuntu-latest
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Set up Node <node-version>
        uses: actions/setup-node@v7
        with:
          node-version: <node-version>
          cache: <package-manager>
      - name: Install dependencies
        run: <install-command>
      - name: Build web bundle
        run: <package-manager-run> build
      - name: Sync Capacitor native projects
        run: npx cap sync
      - name: Upload synced native projects
        uses: actions/upload-artifact@v7
        with:
          name: native-projects
          path: |
            android/
            ios/

  android:
    name: Android release build
    needs: build-web
    runs-on: ubuntu-latest
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Download synced native projects
        uses: actions/download-artifact@v8
        with:
          name: native-projects
      - name: Set up JDK
        uses: actions/setup-java@v6
        with:
          distribution: temurin
          java-version: '21'
      - name: Set up Android SDK
        uses: android-actions/setup-android@v4

      # Omit these two steps entirely if distribution: none
      - name: Decode Android keystore
        run: echo "${{ secrets.ANDROID_KEYSTORE_BASE64 }}" | base64 -d > android/app/release.keystore
      - name: Write Gradle signing properties
        run: |
          cat >> android/gradle.properties <<EOF
          RELEASE_STORE_FILE=release.keystore
          RELEASE_STORE_PASSWORD=${{ secrets.ANDROID_KEYSTORE_PASSWORD }}
          RELEASE_KEY_ALIAS=${{ secrets.ANDROID_KEY_ALIAS }}
          RELEASE_KEY_PASSWORD=${{ secrets.ANDROID_KEY_PASSWORD }}
          EOF

      - name: Build release bundle
        working-directory: android
        run: ./gradlew bundleRelease

      # distribution: store only — uploads straight to a Play Console track
      - name: Upload to Google Play
        uses: r0adkll/upload-google-play@v1
        with:
          serviceAccountJsonPlainText: ${{ secrets.GOOGLE_PLAY_SERVICE_ACCOUNT_JSON }}
          packageName: <android-package-name>
          releaseFiles: android/app/build/outputs/bundle/release/app-release.aab
          track: production

      # distribution: internal only, and only if the user opted into Firebase App Distribution (Step 1) —
      # otherwise the plain artifact upload below is enough
      - name: Distribute via Firebase App Distribution
        uses: wzieba/Firebase-Distribution-Github-Action@v1
        with:
          appId: ${{ secrets.FIREBASE_ANDROID_APP_ID }}
          serviceCredentialsFileContent: ${{ secrets.FIREBASE_SERVICE_ACCOUNT_JSON }}
          groups: internal-testers
          file: android/app/build/outputs/bundle/release/app-release.aab

      # distribution: internal without Firebase — the plain fallback, no extra secrets
      - name: Upload AAB
        uses: actions/upload-artifact@v7
        with:
          name: app-release.aab
          path: android/app/build/outputs/bundle/release/app-release.aab

  ios:
    name: iOS release build
    needs: build-web
    runs-on: macos-latest
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Download synced native projects
        uses: actions/download-artifact@v8
        with:
          name: native-projects
      - name: Install CocoaPods
        working-directory: ios/App
        run: pod install

      # Omit this whole block if distribution: none
      - name: Import App Store Connect API key
        env:
          APP_STORE_CONNECT_API_KEY_BASE64: ${{ secrets.APP_STORE_CONNECT_API_KEY_BASE64 }}
        run: echo "$APP_STORE_CONNECT_API_KEY_BASE64" | base64 -d > AuthKey.p8

      - name: Archive
        working-directory: ios/App
        run: xcodebuild -workspace App.xcworkspace -scheme App -configuration Release archive -archivePath build/App.xcarchive

      - name: Export IPA
        working-directory: ios/App
        run: |
          xcodebuild -exportArchive -archivePath build/App.xcarchive -exportPath build \
            -authenticationKeyPath ../../AuthKey.p8 \
            -authenticationKeyID ${{ secrets.APP_STORE_CONNECT_API_KEY_ID }} \
            -authenticationKeyIssuerID ${{ secrets.APP_STORE_CONNECT_API_KEY_ISSUER_ID }} \
            -exportOptionsPlist ExportOptions.plist

      - name: Upload IPA
        uses: actions/upload-artifact@v7
        with:
          name: app-release.ipa
          path: ios/App/build/*.ipa
```

Notes specific to this template:

- Use `xcodebuild -workspace ios/App/App.xcworkspace -scheme App archive` exactly as named in Task 9's spec —
  the `working-directory: ios/App` above plus a relative `-workspace App.xcworkspace` is equivalent and
  keeps every other relative path (`build/...`, `ExportOptions.plist`) short; resolve to whichever form
  matches how the rest of this repository's iOS steps are written, if this is an update (Step 2).
  If the target repository already has a `fastlane/Fastfile`, prefer driving the archive/export/upload
  through `bundle exec fastlane <lane>` instead of raw `xcodebuild` calls — note that as the preferred path in
  Step 8's report rather than silently overriding an existing Fastlane setup with the raw-`xcodebuild` steps
  above.
- `<android-package-name>`: the Android application id from `android/app/build.gradle` (Capacitor's default
  project layout) — resolved in Step 1's survey when `distribution: store`.

### `sync.yml` template (library/react/angular flavors only)

Runs once a GitHub Release is published, provided it was published from the stable branch. Opens a pull
request that merges the released branch back into the integration branch and bumps the development
prerelease version via the companion `sync_versions.py` script (below). Skip this whole workflow — don't
generate it — for the `react-native`/`ionic` flavors: their app version is normally driven by store submission
tooling (EAS `autoIncrement`, or the build number bumped alongside a store listing), not by a `package.json`
prerelease convention; note this omission explicitly in Step 8's report so the user isn't left wondering why
no `sync.yml` was written for those flavors.

```yaml
name: Sync

# After a release is published from <stable-branch>, open a pull request that merges it back into
# <integration-branch> and bumps the development prerelease version, so <integration-branch> never has to
# wait for a manual sync branch.
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
            echo "::error::Release tag '$RELEASE_VERSION' is not in X.Y.Z form; cannot compute the next prerelease."
            exit 1
          fi

          NEXT_PATCH=$((PATCH + 1))
          NEXT_VERSION="${MAJOR}.${MINOR}.${NEXT_PATCH}-dev.0"
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

      - name: Set up Node <node-version>
        if: steps.guard.outputs.exists == 'false'
        uses: actions/setup-node@v7
        with:
          node-version: <node-version>

      - name: Bump package.json and lockfile
        if: steps.guard.outputs.exists == 'false'
        run: <bump-version-command>

      - name: Set up Python
        if: steps.guard.outputs.exists == 'false'
        uses: actions/setup-python@v7
        with:
          python-version: '3.x'

      - name: Bump README/Antora version mentions
        if: steps.guard.outputs.exists == 'false'
        env:
          RELEASE_VERSION: ${{ steps.versions.outputs.release_version }}
          NEXT_VERSION: ${{ steps.versions.outputs.next_version }}
        run: python3 .github/scripts/sync_versions.py

      - name: Commit the version bump
        if: steps.guard.outputs.exists == 'false'
        run: |
          git add package.json <lockfile-name> README.md docs/antora.yml docs/modules/ROOT/pages
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
            --body "Merges \`<stable-branch>\` back into \`<integration-branch>\` after releasing \`${{ steps.versions.outputs.release_version }}\`, and bumps the development version to \`${{ steps.versions.outputs.next_version }}\` in \`package.json\`, \`README.md\`, and the Antora docs." \
            --label sync
```

Notes specific to this template:

- The prerelease convention is a **patch** bump, not a minor bump (deliberately different from this
  catalog's Java `sync.yml`, which bumps the minor and resets the patch): release `1.3.0` → next dev version
  `1.3.1-dev.0`. This matches the convention `iru-typescript-bump-version` documents and that `iru-release`
  relies on for the npm ecosystem — keep them consistent if either is ever revisited.
  If this repository does minor/major-level releases too, flag that as an open gap in Step 8 rather than
  silently guessing which bump the user wants, same as the Java skill does.
  - `<bump-version-command>`: `npm version "${{ steps.versions.outputs.next_version }}" --no-git-tag-version`
    / `pnpm version "${{ steps.versions.outputs.next_version }}" --no-git-tag-version` /
    `yarn version --new-version "${{ steps.versions.outputs.next_version }}" --no-git-tag-version` — resolved
    from `<package-manager>` in Step 4. Using the package manager's own `version` command (rather than a
    hand-rolled regex over `package.json`, unlike the Java template's `pom.xml` edit) also updates the
    lockfile in the same step, so `sync_versions.py` only has to handle README/Antora prose, not the manifest
    itself.
  - `<lockfile-name>`: `package-lock.json` / `pnpm-lock.yaml` / `yarn.lock`, matching `<package-manager>`.
- `CHANGELOG.md` is deliberately not touched by this workflow, for the same reason as the Java template: its
  release section and fresh `[Unreleased]` heading are written before the tag is published, and arrive on
  `<integration-branch>` via the merge step above.
- The `permissions:` block is necessary but not sufficient — flag in Step 8 that the repository's Settings →
  Actions → General → "Workflow permissions" must also allow GitHub Actions to create pull requests, or
  `gh pr create` will fail with a permissions error even though the token has the right scopes declared here.

### `sync_versions.py` template (library/react/angular flavors only)

Companion script for `sync.yml`, at `.github/scripts/sync_versions.py`. Reads `RELEASE_VERSION`/
`NEXT_VERSION` from the environment and rewrites `README.md` and any Antora page carrying the same version
mentions — `package.json`/its lockfile are already bumped by the previous `sync.yml` step (see the note
above), so this script never touches them:

```python
#!/usr/bin/env python3
"""Rewrites README/Antora version references after a release, for the Sync workflow.

Reads RELEASE_VERSION and NEXT_VERSION from the environment and updates README.md,
docs/antora.yml, and any Antora page that carries the same "Latest release" /
"Latest snapshot" dependency snippets as README.md.

package.json (and its lockfile) are bumped by the previous "Bump package.json and
lockfile" workflow step via the package manager's own `version` command, not by this
script.

CHANGELOG.md is intentionally left untouched: its release section and fresh
"[Unreleased]" heading are written before the tag is published, and arrive on
<integration-branch> via the merge that precedes this script, not by bumping a
version string.
"""
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def replace_dependency_snippets(text, release_version, next_version):
    """Replaces the version string following a "Latest release"/"Latest snapshot" marker line."""
    lines = text.splitlines(keepends=True)
    pending = None
    for i, line in enumerate(lines):
        lower = line.strip().lower()
        if lower.startswith("latest release"):
            pending = release_version
        elif lower.startswith("latest snapshot") or lower.startswith("latest dev"):
            pending = next_version
        elif pending and re.search(r'"version":\s*"[^"]*"', line):
            lines[i] = re.sub(r'("version":\s*")[^"]*(")', rf"\g<1>{pending}\g<2>", line)
            pending = None
    return "".join(lines)


def update_readme(release_version, next_version):
    path = REPO_ROOT / "README.md"
    text = path.read_text()
    # Adjust these two row-label regexes to match this repository's actual README table wording
    # (resolved in Step 1) if it differs from setup-readme's default "Current development version" /
    # "Latest release" labels.
    text = re.sub(
        r"(\| Current development version \| `)[^`]*(` \|)",
        rf"\g<1>{next_version}\g<2>",
        text,
    )
    text = re.sub(
        r"(\| Latest release[^|]*\| `)[^`]*(` \|)",
        rf"\g<1>{release_version}\g<2>",
        text,
    )
    text = replace_dependency_snippets(text, release_version, next_version)
    path.write_text(text)


def update_antora_component_version(release_version):
    path = REPO_ROOT / "docs" / "antora.yml"
    if not path.exists():
        return
    text = path.read_text()
    updated, count = re.subn(r"(?m)^version:.*$", f"version: {release_version}", text, count=1)
    if count == 1:
        path.write_text(updated)


def update_antora_pages(release_version, next_version):
    pages_dir = REPO_ROOT / "docs" / "modules" / "ROOT" / "pages"
    if not pages_dir.exists():
        return
    for path in sorted(pages_dir.glob("*.adoc")):
        text = path.read_text()
        if '"version"' not in text and "Latest release" not in text:
            continue
        updated = replace_dependency_snippets(text, release_version, next_version)
        if updated != text:
            path.write_text(updated)


def main():
    release_version = os.environ["RELEASE_VERSION"]
    next_version = os.environ["NEXT_VERSION"]

    update_readme(release_version, next_version)
    update_antora_component_version(release_version)
    update_antora_pages(release_version, next_version)


if __name__ == "__main__":
    main()
```

Notes specific to this template:

- `replace_dependency_snippets`'s regex matches a JSON-style `"version": "..."` snippet (the way an npm
  install snippet is usually shown in prose docs) rather than an XML `<version>` tag like the Java template —
  adjust it if this repository's README/Antora pages show install instructions in a different shape (e.g. a
  fenced `npm install <package>@<version>` line instead of a JSON snippet); resolve the actual wording in
  Step 1 before writing the real file.
- `update_antora_component_version`/`update_antora_pages` both no-op cleanly if `docs/antora.yml` or
  `docs/modules/ROOT/pages` don't exist, so this script is safe to write even before `iru-setup-antora` has
  run.

### `security.yml` template

Runs on every pull request and on every push to the integration/stable branches, plus a weekly schedule so
CodeQL and OSV-Scanner findings don't go stale between pushes. Each job below is individually omittable via
the matching `security-*` `args` key from Step 1 (default `yes`); drop that whole job's YAML — not just its
`if:` — when the resolved value is `no`:

```yaml
name: Security

on:
  push:
    branches: [ <integration-branch>, <stable-branch> ]
  pull_request:
  schedule:
    - cron: '0 6 * * 1' # weekly, Monday 06:00 UTC

permissions:
  contents: read

jobs:
  # Omit this whole job if security-dependency-review: no (Step 1)
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
        uses: actions/dependency-review-action@v5

  # Omit this whole job if security-codeql: no (Step 1)
  codeql:
    name: CodeQL analysis
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Initialize CodeQL
        uses: github/codeql-action/init@v4
        with:
          languages: javascript-typescript
          build-mode: none
      - name: Perform CodeQL analysis
        uses: github/codeql-action/analyze@v4

  # Omit this whole job if security-osv: no (Step 1)
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

  # Omit this whole job if security-gitleaks: no (Step 1)
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

- `build-mode: none` is correct for `javascript-typescript` regardless of flavor — CodeQL's JS/TS extractor
  works directly from source, no compile step needed, unlike the Java template's `codeql` job which must run
  `mvn compile` first.
- None of these four jobs need a repository secret beyond the automatically provided `GITHUB_TOKEN` — don't
  add any of them to Step 7's secrets table.
- If `github.com` public-repository default CodeQL setup is simpler for this repository than a workflow-based
  CodeQL job, note that as an alternative in Step 8's report instead of writing the `codeql` job, same as the
  Java skill.

### `.github/dependabot.yml` template

Always generated (or updated) regardless of the four `security-*` flags above — grouped weekly updates for
the `npm` ecosystem (the repository's own dependencies) and for the workflows this skill itself just wrote
(`github-actions`):

```yaml
version: 2
updates:
  - package-ecosystem: npm
    directory: /
    schedule:
      interval: weekly
    groups:
      npm-dependencies:
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

For the `ionic` flavor, add a second `npm` entry with `directory: /android` only if that directory has its own
`package.json` (Capacitor's default layout doesn't create one — Gradle manages Android dependencies
separately and isn't an ecosystem Dependabot's `npm` updater covers; a `gradle` ecosystem entry is a
reasonable follow-up but out of this skill's generated scope, note it in Step 8 instead of adding it silently).

If `.github/dependabot.yml` already exists with entries for other ecosystems (e.g. `maven` for a sibling
backend), preserve them — only add or update the `npm` and `github-actions` entries above (see Step 2).

## Step 4 — Fill the templates

Resolve every placeholder from Step 1's survey before writing the real files. Don't invent a value — ask the
user or note it as an open gap in Step 8's report instead of silently guessing.

| Placeholder | Resolved from |
|---|---|
| `<integration-branch>` / `<stable-branch>` | Step 1 branch survey / `args` |
| `<node-version>` | Step 1 (`engines.node`, default `24`) / `args` |
| `<package-manager>` | Step 1 (lockfile/`packageManager`) / `args` — one of `npm`/`pnpm`/`yarn` |
| `<install-command>` | derived from `<package-manager>`: `npm ci` / `pnpm install --frozen-lockfile` / `yarn install --frozen-lockfile` (`--immutable` for Yarn Berry) |
| `<package-manager-run>` | derived from `<package-manager>`: `npm run` / `pnpm run` / `yarn run` |
| `<lockfile-name>` | derived from `<package-manager>`: `package-lock.json` / `pnpm-lock.yaml` / `yarn.lock` |
| `<bump-version-command>` | derived from `<package-manager>` — see the `sync.yml` template's notes |
| `<sonar-host-url>` | Step 1 Sonar survey / `args`; only needed when `sonar: self-hosted` |
| `<android-package-name>` | `android/app/build.gradle`'s `applicationId`, only when `flavor: ionic` and `distribution: store` |

Also apply the `sonar`/`docs-tool`/`publish`/`distribution`/`native-builds`/`flavor` gating resolved in Step 1:
drop every block the templates above mark with an "Omit this … if …" comment when the matching value is
`no`/`none`/doesn't apply to this flavor, and drop that same comment itself — it's guidance for filling the
template, not part of the generated workflow file. GitHub Pages publishing in `build.yml` is never gated on
`sonar`/`publish` — it applies regardless.

## Step 5 — Handle missing supporting files

Before writing the workflows, make sure the files they depend on exist:

- **`docs/antora.yml` / `docs/antora-playbook.yml` missing**: recommend running the `iru-setup-antora` skill
  now; the Antora build step in `build.yml` will fail without them.
- **`sonar-project.properties` missing, and `sonar` isn't `none`**: ask the user for `sonar.organization` (if
  using SonarCloud), `sonar.projectKey`, and `sonar.host.url` (default `https://sonarcloud.io` unless they run
  self-hosted SonarQube), then create it at the repository root:

  ```properties
  sonar.organization=<org>
  sonar.projectKey=<project-key>
  sonar.host.url=<sonar-host-url>
  sonar.sources=src
  sonar.tests=test
  sonar.javascript.lcov.reportPaths=coverage/lcov.info
  sonar.exclusions=**/dist/**,**/node_modules/**
  ```

  Skip this entirely when `sonar: none` — there's nothing to add, and the `Run SonarQube/SonarCloud analysis`
  step is omitted from `build.yml` anyway.
- **`.changeset/config.json` missing, `flavor: library`, and `publish: yes`**: recommend the user re-run
  `iru-setup-typescript-library` (or `npx changeset init`) so the `version-pr` job in `release.yml` has
  something to act on. Skip this step entirely if `publish: no` — that job is omitted.
- **`ExportOptions.plist` missing under `ios/`, `flavor` is `react-native` or `ionic`, and `distribution`
  isn't `none`**: flag this prominently — the iOS export step in `release.yml` will fail without it. This
  file is project-specific (team id, export method) and this skill doesn't generate it.
- **`.gitignore` missing entries for `dist/`, `coverage/`, `docs/api/`, `docs/build/`, `storybook-static/`**:
  add whichever are absent, so the build output the workflow generates never gets committed by accident (the
  `iru-setup-typescript-gitignore` skill is the canonical source for this list — defer to it if present rather
  than duplicating logic here).

## Step 6 — Write the workflow files

Write (or, per Step 2, carefully update) `.github/workflows/build.yml`, `.github/workflows/release.yml`, and
`.github/workflows/security.yml` with the filled-in templates from Step 4, plus `.github/dependabot.yml` and
any supporting files created in Step 5. For `library`/`react`/`angular` flavors only, also write
`.github/workflows/sync.yml` together with `.github/scripts/sync_versions.py` — never write one without the
other, and never write either for `react-native`/`ionic` (Step 3). `security.yml` and
`.github/dependabot.yml` are always written (or updated), independent of `sonar`/`publish`/`distribution` —
only their own `security-*` flags (Step 1) gate individual jobs within `security.yml`, and
`.github/dependabot.yml` has no gate at all.

## Step 7 — List required repository secrets and settings

Report the secrets that must exist under the target repository's Settings → Secrets and variables → Actions —
this skill cannot create them itself. List only the rows that apply to what was actually generated (per
`flavor`/`sonar`/`publish`/`distribution`/`native-builds` from Step 1) — an omitted row is one fewer secret
the user needs to go create:

| Secret | Purpose | Only needed when |
|---|---|---|
| `SONAR_TOKEN` | Auth token for the SonarQube/SonarCloud scan | `sonar` is `cloud` or `self-hosted` |
| `EXPO_TOKEN` | Auth token for `expo/expo-github-action`, used by `eas build`/`eas submit` | `flavor: react-native`, `native-builds: eas` |
| `ANDROID_KEYSTORE_BASE64` / `ANDROID_KEYSTORE_PASSWORD` / `ANDROID_KEY_ALIAS` / `ANDROID_KEY_PASSWORD` | Signs the Android release bundle | `flavor: react-native` (`native-builds: local`) or `flavor: ionic`, and `distribution` isn't `none` |
| `APP_STORE_CONNECT_API_KEY_ID` / `APP_STORE_CONNECT_API_KEY_ISSUER_ID` / `APP_STORE_CONNECT_API_KEY_BASE64` | Signs/exports the iOS `.ipa` via `xcodebuild` | `flavor: react-native` (`native-builds: local`) or `flavor: ionic`, and `distribution` isn't `none` |
| `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` | Uploads the signed `.aab` straight to a Play Console track | `flavor: ionic`, `distribution: store` |
| `FIREBASE_ANDROID_APP_ID` / `FIREBASE_SERVICE_ACCOUNT_JSON` | Firebase App Distribution push | `flavor: ionic` (or `react-native`), `distribution: internal`, and the user opted into Firebase App Distribution over a plain artifact upload (Step 1) |

`GITHUB_TOKEN` needs no setup — GitHub Actions provides it automatically, used by `sync.yml`'s `gh` calls and
`security.yml`'s `gitleaks`/CodeQL jobs. `sync.yml` also needs the repository setting under Settings → Actions
→ General → "Workflow permissions" set to allow GitHub Actions to create pull requests — the
`permissions: contents: write / pull-requests: write` block in the workflow itself is not sufficient on its
own. `build.yml`'s Pages deploy needs Settings → Pages → "Build and deployment" → Source set to
**GitHub Actions**. `release.yml`'s `library` flavor `publish` job needs the trusted-publisher relationship
configured on npmjs.com for this package (Package settings → Trusted Publisher → GitHub Actions), naming this
repository, the `release.yml` workflow file, and the `publish` job/environment exactly — publish will
otherwise fail with an authentication error even though `id-token: write` is set correctly here. Call all of
this out explicitly in Step 8's report, since each is easy to miss and fails on the very first real run
without it.

## Step 8 — Report and warn

Summarize what happened: whether `build.yml`/`release.yml`/`sync.yml` (+`sync_versions.py`, when
applicable)/`security.yml` and `.github/dependabot.yml` were created fresh, updated in place, or left
untouched (Step 2's stop path); whether `sonar-project.properties`/`.changeset/config.json` were added versus
already present; and any open gaps noted in Steps 1/4/5 (missing Playwright config, missing
`ExportOptions.plist`, README/Antora wording that didn't match `sync_versions.py`'s default regexes,
non-patch-level releases the bump default doesn't handle, etc.).

State explicitly what was wired versus omitted, and why:

- **`flavor`**: which of the five flavor-specific `release.yml` variants was generated.
- **`sonar`**: `cloud`/`self-hosted`/`none` — if not `none`, the Sonar step and `SONAR_TOKEN` row were
  included; if `none`, both were omitted, and note whether that's because the project isn't open source or a
  direct user choice.
- **`publish`** (library only): yes/no — if `yes`, the `publish` job and (if `.changeset/config.json` exists)
  the `version-pr` job were generated; if `no`, both were omitted and `release.yml` was not written for the
  library flavor (no jobs would remain) — say so explicitly rather than listing it among the created files.
- **`distribution`/`native-builds`** (react-native/ionic only): which signing/store jobs were generated versus
  the plain-artifact fallback, and which secret rows were included versus left out of Step 7's table.
- **`docs-tool`**: which tool's build step was wired into `build.yml`, and whether its output merges under
  `docs/build/site/api/` or a sibling `storybook/` path.
- **Security block**: which of `security-dependency-review`/`security-codeql`/`security-osv`/
  `security-gitleaks` were included in `security.yml` versus omitted per Step 1's `args`/answers, and confirm
  `.github/dependabot.yml` was written regardless (it has no opt-out).
- **`sync.yml`**: generated for `library`/`react`/`angular`; intentionally omitted for `react-native`/`ionic`
  — state this plainly so it doesn't read as an oversight.

Finish with an explicit warning: **the user must review the generated (or updated) workflow files before
relying on them.** Branch names, script names, and the store/signing setup were inferred from this
repository's current state and may need correction — and because this pipeline handles signing keys and
publishes artifacts publicly, a bad assumption here has real consequences. Recommend a dry run (manually
triggering via `workflow_dispatch` where added) before trusting it on a real release. For `sync.yml`
specifically, recommend verifying it against a real (or test) release before relying on it — confirm the
computed next-version and the exact files it touches match expectations, and confirm the "Workflow
permissions" repository setting from Step 7 is enabled. For `release.yml`'s `library` publish job, recommend
confirming the npmjs.com trusted-publisher configuration before the very first release, since there is no
local way to dry-run OIDC trusted publishing.
