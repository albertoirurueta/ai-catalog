---
name: iru-setup-php-github-workflows
description: >-
  Create or update the GitHub Actions workflows for a PHP repository of one of four flavors — `laravel` (application),
  `wordpress-plugin`, `wordpress-theme` (block theme), or `prestashop-module` — as scaffolded by `iru-setup-php-laravel`,
  `iru-setup-php-wordpress`, and `iru-setup-php-prestashop`, driving everything through their shared composer scripts
  (`test`, `test:coverage`, `test:integration`, `lint`, `lint:report`, `format:check`, PrestaShop's `package`).
  Writes `build.yml` (every push to the integration/stable branches, every pull request, `workflow_dispatch` —
  `shivammathur/setup-php` with PCOV, `composer validate --strict`, cached `composer install`, `composer audit`,
  static analysis and coding style, fast tests with Clover/JUnit coverage across a PHP matrix from the floor to the
  newest supported release, and with `ci-tests: full` an integration job per flavor: Laravel against a MySQL or
  PostgreSQL service container, WordPress inside the dedicated `@wordpress/env` test environment across a WordPress
  matrix (the `Requires at least:` floor and the latest release), PrestaShop inside the Docker shop of
  `tests/Integration/docker-compose.yml` for 8.x and/or 9.x — each integration job also runs the scaffold's Playwright
  browser UI tests against the environment it already starts (`npm run test:e2e`, guarded on a `playwright.config.*`)
  and uploads `.ui-screenshots/` as a 7-day artifact; an optional SonarCloud/SonarQube job
  (`sonarqube-scan-action`, skipped on fork pull requests); and a docs job — Antora plus phpDocumentor API docs only
  when `phpdoc.dist.xml` exists — deployed to GitHub Pages from the stable branch with `pages: yes` or uploaded as an
  artifact with `pages: no`); `release.yml` per `distribution` (WordPress: an installable zip built from `.distignore`
  attached to the GitHub Release, plus with `store` a WordPress.org deploy — `10up/action-wordpress-plugin-deploy`
  for plugins, a Theme Directory SVN commit for themes; PrestaShop: `composer package` zip attached to the release,
  plus with `store` manual PrestaShop Addons upload instructions, since Addons has no upload API; Laravel `internal`:
  the scaffold's `Dockerfile` built and pushed to GHCR — one FrankenPHP image or the FPM `app` + `web` pair);
  `sync.yml` + `.github/scripts/php_version.py` + `.github/scripts/sync_versions.py` (after a release from the stable
  branch, a PR merging it back into the integration branch with the next `x.(y+1).0-dev` version, the same convention
  `iru-php-bump-version` and `iru-release` use); and the shared security block — `security.yml` (dependency-review,
  CodeQL for `actions` and for `javascript-typescript` only when the repository has JS/TS — CodeQL has no PHP
  support — plus a Psalm `--taint-analysis` SARIF upload as the PHP code-scanning substitute, OSV-Scanner over
  `composer.lock`, gitleaks) and `.github/dependabot.yml` (`composer`, `github-actions`, `npm` when a `package.json`
  exists, `docker` for a Laravel image) — ending with a required-secrets table. Invoke as
  `/iru-setup-php-github-workflows`, optionally with `args` (`key: value` lines): `flavor`, `integration-branch`
  (default `develop`), `stable-branch` (default `main`), `php-version` (the floor), `open-source`, `visibility`
  (`public`/`private`/`internal`), `ci-tests` (`unit`/`full`), `pages` (`yes`/`no`), `distribution`
  (`none`/`internal`/`store`; Laravel `none`/`internal`), `sonar` (`cloud`/`self-hosted`/`none`, +
  `sonar-organization`/`sonar-project-key`/`sonar-host-url`), `mode` (`new`/`existing`), `on-existing`
  (`ask`/`keep`/`update`/`replace`), and `security-dependency-review`/`security-codeql`/`security-taint`/
  `security-osv`/`security-gitleaks` (each `yes`/`no`, default `yes`). Stand-alone, it resolves `visibility` itself
  and asks `sonar`/`ci-tests`/`pages`/`distribution` with visibility-aware cost notes. Announces whether it is creating
  the pipeline from scratch or updating one, and asks Update / Keep as is / Replace (or Stop) per existing workflow
  file. Used by `iru-setup-php-repository`; also runs standalone.
model: sonnet
allowed-tools: Read Write Edit AskUserQuestion Bash(gh *) Bash(git *) Bash(curl *) Bash(docker *) Bash(actionlint *) Bash(python3 *) Bash(composer *) Bash(php *) Bash(npm *) Bash(npx *) Bash(mkdir *) Bash(ls *) Bash(cat *) Bash(grep *) Bash(find *) Bash(sed -n *) Bash(chmod *)
---

# Setup PHP GitHub Workflows

Scaffold (or update) the CI/CD and security pipeline for a PHP repository:

| File | Trigger | Does |
|---|---|---|
| `.github/workflows/build.yml` | push to `<integration-branch>`/`<stable-branch>`, pull requests to them, `workflow_dispatch` | validate + audit, static analysis, style, fast tests with coverage on a PHP matrix, integration (`ci-tests: full`), optional Sonar, docs (Pages from `<stable-branch>` or artifact) |
| `.github/workflows/release.yml` | GitHub Release published — **not written with `distribution: none`** | WordPress/PrestaShop: release zip attached to the release (+ WordPress.org deploy / Addons instructions with `store`); Laravel: container image to GHCR |
| `.github/workflows/sync.yml` + `.github/scripts/php_version.py` + `.github/scripts/sync_versions.py` | GitHub Release published from `<stable-branch>` | PR merging the release back into `<integration-branch>` with the next `-dev` version |
| `.github/workflows/security.yml` + `.github/psalm/*` | pushes, pull requests, weekly | dependency review, CodeQL (`actions` + JS/TS when present), Psalm taint analysis (SARIF), OSV-Scanner, gitleaks |
| `.github/dependabot.yml` | — | weekly grouped updates for Composer, the actions, npm (when present), the Laravel `Dockerfile`, the docs toolchain |

It fits the catalog's release flow: `iru-release` cuts `release_x.y.z` from `<integration-branch>`, bumps the version
with `iru-php-bump-version` (`x.y.z-dev` → `x.y.z`, `Stable tag:` included for WordPress), and opens a PR into
`<stable-branch>`; merging it runs `build.yml` there (docs to Pages); publishing the GitHub Release (tag `x.y.z`) runs
`release.yml` and `sync.yml` (next `x.(y+1).0-dev` back on `<integration-branch>`).

Every action reference uses the major (or, where the publisher has no floating major tag, the exact release) current
when this skill was written, checked against the GitHub API: `actions/checkout@v7`, `shivammathur/setup-php@v2`,
`actions/cache@v6`, `actions/setup-node@v7`, `actions/setup-python@v7`, `actions/upload-artifact@v7`,
`actions/download-artifact@v8`, `actions/configure-pages@v6`, `actions/upload-pages-artifact@v5`,
`actions/deploy-pages@v5`, `SonarSource/sonarqube-scan-action@v8`, `10up/action-wordpress-plugin-deploy@2.3.0` (no
major tag exists; its README's `@stable` is a moving branch), `docker/setup-buildx-action@v4`,
`docker/login-action@v4`, `docker/metadata-action@v6`, `docker/build-push-action@v7`, `github/codeql-action/*@v4`,
`actions/dependency-review-action@v5`, `google/osv-scanner-action/...@v2.7.0` (that repository publishes **no** `v2`
ref — `@v2` does not resolve), `gitleaks/gitleaks-action@v3`. When updating an old pipeline re-check them —
`gh api repos/<owner>/<repo>/tags` (not `releases/latest`, which returns `codeql-bundle-*` for CodeQL) or
`git ls-remote --tags https://github.com/<owner>/<repo>`; Dependabot's `github-actions` entry keeps them current
afterwards.

## Step 1 — Resolve inputs and survey the repository

Parse `args` first (`key: value` lines); every key found is resolved and its survey/question below is skipped:

```
flavor: wordpress-plugin
integration-branch: develop
stable-branch: main
php-version: 8.3
open-source: yes
visibility: public
ci-tests: full
pages: yes
distribution: store
sonar: cloud
sonar-organization: example-github
sonar-project-key: example_acme-loans
sonar-host-url: https://sonarcloud.io
mode: new
on-existing: ask
```

Ignore any other key (`ci` included — invoking this skill means CI is wanted). `mode` is informational; `on-existing`
pre-answers Step 2. The `security-*` keys default to `yes`.

Then survey what isn't resolved:

- **Flavor** — the same markers as `iru-php-code-quality` (first match wins): `laravel/framework` in `composer.json`
  `require` + `artisan` → `laravel`; a root `*.php` with a `Plugin Name:` header → `wordpress-plugin`; `style.css`
  with `Theme Name:` → `wordpress-theme`; a root class that `extends Module`/`PaymentModule`/`CarrierModule` →
  `prestashop-module`. Anything else (a plain Composer library) is outside this skill's templates: say so and ask
  (`AskUserQuestion`) **Stop** / **Continue anyway** (every flavor-specific step becomes an open gap).
- **`<slug>`** — WordPress: the main plugin file's basename / the theme's text domain (the WordPress.org slug);
  PrestaShop: `$this->name` (the module's technical name, which is also its directory name in a shop); Laravel: the
  `composer.json` `name` after the `/` (the image name). Confirm when ambiguous.
- **Composer scripts** — read `composer.json` `scripts`. The templates call `test:coverage`, `test:integration`,
  `lint`, `lint:report`, `format:check` (and PrestaShop's `package`, `shop:up`, `shop:install`, `shop:down`,
  `lint:shop`) exactly as the `iru-setup-php-*` scaffolds define them. A missing script is never invented in the
  workflow: drop the step that would call it and list the gap in Step 7 (e.g. no `test:integration` → no integration
  job; no `lint:report` → Sonar gets no PHPStan import).
- **PHP versions** — `<php-floor>` = `php-version` from `args`, else `composer.json` `config.platform.php`
  (major.minor), else the lowest version `require.php` allows. `<php-latest>` and the matrix come from php.net's
  supported branches: `curl -s https://www.php.net/releases/active.php` (JSON; its keys under `"8"` are the branches
  still receiving fixes — `8.2`…`8.5` when this skill was written). `<php-matrix>` = every supported branch from
  `<php-floor>` to `<php-latest>`, quoted (`'8.3', '8.4', '8.5'`). Offline → ask, offering floor..`8.5`.
- **WordPress** — `<wp-floor>` from the main file's / `style.css`'s `Requires at least:` header (major.minor);
  `<wp-content-dir>` = `plugins` or `themes`. Confirm `.wp-env.test.json` and the npm scripts `test:env:start`/
  `test:integration` exist (the scaffold's dedicated test environment); without them the integration job is an open
  gap. Current WordPress: `curl -s https://api.wordpress.org/core/version-check/1.7/` (`offers[0].version`).
- **PrestaShop** — `<ps-versions>`: the majors in `ps_versions_compliancy` whose images can run `<php-floor>` —
  PrestaShop 8.x supports PHP ≤ 8.1, so with a floor above 8.1 only `'9'` is tested (say so); `'8', '9'` otherwise.
  Confirm `tests/Integration/docker-compose.yml` and `bin/package.sh` exist.
- **Laravel** — the integration database from `phpunit.integration.xml`/the scaffold's choice (`mysql` or `pgsql`);
  with `distribution: internal`, the `Dockerfile`: one final stage (FrankenPHP → one image) or two targets `app` +
  `web` (PHP-FPM + Nginx → two images, `<slug>` and `<slug>-web`).
- **JS/TS present** — a `package.json` with sources to analyse (WordPress blocks, Laravel Vite `resources/js`) →
  CodeQL also runs `javascript-typescript`; a WordPress `package.json` that only carries `@wordpress/env` adds nothing
  to analyse but still gets a Dependabot `npm` entry.
- **Docs** — `docs/antora.yml` + `docs/antora-playbook.yml` + `docs/package-lock.json` (`iru-setup-antora`); missing →
  recommend running it first (the docs job would have nothing to build). phpDocumentor only when `phpdoc.dist.xml`/
  `phpdoc.xml` exists — never add one here.
- **Branches** — confirm against `git branch -a` (or ask); `sync.yml` needs both.
- **README/Antora wording** for `sync_versions.py` — `grep -n -i "current development version\|latest release"
  README.md`; note deviations from the default row labels.

**Cost-aware choices** (only those still unresolved, in this order, `AskUserQuestion`; prices per GitHub's/
SonarSource's current pricing — tell the user to double-check their plan):

1. **`visibility`** — `gh repo view --json visibility -q .visibility` (lowercased) when there's a GitHub remote;
   otherwise ask **Public** / **Private** (Public recommended when open source). Open source + private is
   contradictory — say so. `internal` = `private`. Public repositories run standard runners free; private ones
   consume included minutes (2,000/month Free, 3,000 Pro/Team, 50,000 Enterprise Cloud), then ~$0.006/min Linux.
   Everything here is Linux; the PHP matrix multiplies the test job, and the integration jobs (wp-env downloads
   WordPress, a PrestaShop auto-install) are the expensive part.
2. **`sonar`** — "Configure SonarCloud / SonarQube and send CI analysis and coverage reports to it?" — **SonarCloud**
   only for a public open-source repository; otherwise **None** recommended, **self-hosted** second.
3. **`ci-tests`** — **Unit only** (`unit`; recommended for private) — "fast suites only (Pest/PHPUnit on SQLite
   `:memory:`, Brain Monkey, PrestaShop unit tests): no containers". **Full** (`full`; recommended for public) — "also
   the integration job: Laravel against MySQL/PostgreSQL, WordPress in wp-env on the floor and latest WordPress,
   PrestaShop in a real shop — complete verification, considerably more minutes".
4. **`pages`** — public: `yes` without asking. Private: **No (Recommended)** — "docs still built, uploaded as an
   artifact" — vs **Yes** — "needs Pro/Team/Enterprise Cloud; the site is public unless Enterprise Cloud private
   Pages".
5. **`distribution`** — WordPress/PrestaShop: **none** / **internal** (zip attached to the GitHub Release) / **store**
   (WordPress: zip + WordPress.org deploy — needs an approved slug, a directory account, and a GPL-compatible
   license; PrestaShop: zip + Addons upload instructions); default `store` for open-source WordPress, else `none`.
   Laravel: **none** / **internal** (image to GHCR — free for public repositories, storage/transfer quotas for
   private ones); `store` is never valid for Laravel.

**Accessibility opt-out.** Read the repository's `.ui-quality.yml` `accessibility` level (UI contract §8). When it is
`none` (opted out entirely), emit no accessibility report artifact, upload or step: do not collect `a11y-report.txt`
or other accessibility reports into the `ui-screenshots` artifacts, and drop any accessibility-only job or step;
the UI test run and the screenshot upload are unaffected. With `enforce`, `report` or `off` the workflows are
generated exactly as below (`off` runs no automated checks, so no accessibility report exists to upload either).

## Step 2 — Announce scratch vs update, decide per existing file

Check `build.yml`, `release.yml`, `sync.yml` + its two scripts (one unit — partial if not all exist),
`security.yml` + `.github/psalm/` (one unit), `.github/dependabot.yml`. None → "creating the CI/CD pipeline **from
scratch**". Any → "**updating an existing CI/CD setup**", list each as present/absent/partial, read each existing one,
and name every concrete contradiction with this run's choices ("`build.yml` has an integration job but `ci-tests:
unit`", "it deploys to Pages but `pages: no`", "it has a Sonar job but `sonar: none`", "there's a `release.yml` but
`distribution: none`", "`release.yml` deploys to WordPress.org but `distribution: internal`"). Unless `on-existing`
decides, ask per unit (`AskUserQuestion`, ≤ 4 per call):

- **Update (Recommended)** — merge: add/correct what this skill owns (jobs, gating, action versions, commands), keep
  every other step/job/entry; diff shown before writing.
- **Keep as is** — untouched; mismatches listed in Step 7.
- **Replace** — regenerate from the template; customizations lost (git history keeps them).
- **Stop** (first question only) — end without changing anything.

With `distribution: none`, an existing `release.yml` is offered for removal (ask; never delete silently).

## Step 3 — Templates

Resolve every `<placeholder>` from Step 1. Comments marked `# laravel`, `# wordpress`, `# prestashop`,
`# ci-tests: full`, `# pages: yes|no`, `# sonar`, `# store`, `# phpdoc` are gates: keep what applies and **drop the
rest together with these guidance comments** — a step that can never run is dead YAML.

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
  quality:
    name: Validate, audit, analyse and check style
    runs-on: ubuntu-latest
    steps:
      - name: Check out code
        uses: actions/checkout@v7

      - name: Set up PHP <php-floor>
        uses: shivammathur/setup-php@v2
        with:
          php-version: '<php-floor>'
          coverage: none
          tools: composer:v2

      - name: Validate composer.json and composer.lock
        run: composer validate --strict

      - name: Locate the Composer cache
        id: composer-cache
        run: echo "dir=$(composer config cache-files-dir)" >> "$GITHUB_OUTPUT"

      - name: Cache Composer downloads
        uses: actions/cache@v6
        with:
          path: ${{ steps.composer-cache.outputs.dir }}
          key: composer-${{ runner.os }}-<php-floor>-${{ hashFiles('composer.lock') }}
          restore-keys: composer-${{ runner.os }}-<php-floor>-

      - name: Install dependencies
        run: composer install --no-interaction --no-progress --prefer-dist

      # Fails on any known advisory for a locked package (dev packages included — they run in CI too).
      - name: Audit dependencies
        run: composer audit --locked

      - name: Static analysis
        run: composer lint

      - name: Coding style
        run: composer format:check

      # sonar — PHPStan's JSON for Sonar's external-issue import (the gate itself is "Static analysis").
      - name: PHPStan report for Sonar
        run: composer lint:report || true
      - name: Upload the PHPStan report
        uses: actions/upload-artifact@v7
        with:
          name: phpstan-report
          path: build/logs/phpstan.json
          retention-days: 7

  tests:
    name: Tests (PHP ${{ matrix.php }})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        php: [ <php-matrix> ]
    steps:
      - name: Check out code
        uses: actions/checkout@v7

      - name: Set up PHP ${{ matrix.php }} with PCOV
        uses: shivammathur/setup-php@v2
        with:
          php-version: ${{ matrix.php }}
          coverage: pcov
          tools: composer:v2

      - name: Locate the Composer cache
        id: composer-cache
        run: echo "dir=$(composer config cache-files-dir)" >> "$GITHUB_OUTPUT"

      - name: Cache Composer downloads
        uses: actions/cache@v6
        with:
          path: ${{ steps.composer-cache.outputs.dir }}
          key: composer-${{ runner.os }}-${{ matrix.php }}-${{ hashFiles('composer.lock') }}
          restore-keys: composer-${{ runner.os }}-${{ matrix.php }}-

      # The lock is resolved for the floor (config.platform.php), so the same versions install on every PHP here.
      - name: Install dependencies
        run: composer install --no-interaction --no-progress --prefer-dist

      # laravel — the fast suites need an application key (phpunit.xml provides SQLite :memory:).
      - name: Prepare the Laravel environment
        run: |
          cp .env.example .env
          php artisan key:generate --ansi

      # Fast suites only (no Docker, no database server); writes build/logs/clover.xml and junit.xml and enforces
      # the scaffold's 80% line-coverage floor.
      - name: Fast tests with coverage
        run: composer test:coverage

      - name: Upload test and coverage reports
        if: ${{ always() && matrix.php == '<php-floor>' }}
        uses: actions/upload-artifact@v7
        with:
          name: test-reports
          path: build/logs/
          retention-days: 7

  # sonar: cloud | self-hosted only — drop the whole job for sonar: none. Fork pull requests get no secrets.
  sonar:
    name: SonarCloud analysis
    needs: [ quality, tests ]
    if: ${{ github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository }}
    runs-on: ubuntu-latest
    steps:
      - name: Check out code
        uses: actions/checkout@v7
        with:
          # Sonar attributes issues and new code using full history.
          fetch-depth: 0
      - name: Download test and coverage reports
        uses: actions/download-artifact@v8
        with:
          name: test-reports
          path: build/logs
      - name: Download the PHPStan report
        uses: actions/download-artifact@v8
        with:
          name: phpstan-report
          path: build/logs
      # Reads sonar-project.properties (sources, tests, clover.xml, junit.xml, phpstan.json paths).
      - name: Run SonarCloud analysis
        uses: SonarSource/sonarqube-scan-action@v8
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          # SONAR_HOST_URL: <sonar-host-url>    # sonar: self-hosted only

  # docs — built on every push (a broken page fails the branch), published from <stable-branch> only.
  docs:
    name: Build documentation
    needs: [ quality, tests ]
    if: ${{ github.event_name == 'push' || github.event_name == 'workflow_dispatch' }}
    runs-on: ubuntu-latest
    steps:
      - name: Check out code
        uses: actions/checkout@v7

      # phpdoc — only when phpdoc.dist.xml exists: API reference merged under api/.
      - name: Set up PHP with phpDocumentor
        uses: shivammathur/setup-php@v2
        with:
          php-version: '<php-latest>'
          coverage: none
          tools: phpDocumentor
      - name: Build API documentation
        run: phpdoc run --config phpdoc.dist.xml --target build/api --cache-folder "$RUNNER_TEMP/phpdoc-cache"

      - name: Set up Node for the Antora toolchain
        uses: actions/setup-node@v7
        with:
          node-version: 24
          cache: npm
          cache-dependency-path: docs/package-lock.json

      - name: Install Antora
        working-directory: docs
        run: npm ci

      - name: Build Antora docs
        working-directory: docs
        run: npx antora antora-playbook.yml

      - name: Merge documentation
        run: |
          touch docs/build/site/.nojekyll
          mkdir -p docs/build/site/api && cp -r build/api/. docs/build/site/api/    # phpdoc only

      # pages: yes
      - name: Upload Pages artifact
        if: ${{ github.event_name == 'push' && github.ref == 'refs/heads/<stable-branch>' }}
        uses: actions/upload-pages-artifact@v5
        with:
          path: docs/build/site

      # pages: no — instead of "Upload Pages artifact" (and drop the deploy-docs job)
      - name: Upload documentation
        uses: actions/upload-artifact@v7
        with:
          name: documentation
          path: docs/build/site
          retention-days: 14

  # pages: yes only — Settings → Pages → Source must be "GitHub Actions".
  deploy-docs:
    name: Deploy docs to GitHub Pages
    needs: docs
    if: ${{ github.event_name == 'push' && github.ref == 'refs/heads/<stable-branch>' }}
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    concurrency:
      group: pages
      cancel-in-progress: false
    steps:
      - name: Configure Pages
        uses: actions/configure-pages@v6
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v5
```

**`ci-tests: full`** — append exactly one of the three `integration` jobs below under `jobs:`. They never count
towards the coverage gate (that's `tests`, fast suites only — the same rule the coding skills' group stage applies).

`laravel` — the scaffold's `Integration` suite (`phpunit.integration.xml` defaults `DB_CONNECTION`/`DB_DATABASE` to
the `testing` database; CI supplies host, port and credentials):

```yaml
  integration:
    name: Integration tests (MySQL)
    needs: tests
    runs-on: ubuntu-latest
    services:
      database:
        image: mysql:8.4
        env:
          MYSQL_ROOT_PASSWORD: password
          MYSQL_DATABASE: testing
        ports: [ '3306:3306' ]
        options: >-
          --health-cmd="mysqladmin ping -h 127.0.0.1 -ppassword"
          --health-interval=5s --health-timeout=5s --health-retries=20
      # pgsql instead of the mysql service above:
      # database:
      #   image: postgres:18
      #   env: { POSTGRES_PASSWORD: password, POSTGRES_DB: testing }
      #   ports: [ '5432:5432' ]
      #   options: --health-cmd=pg_isready --health-interval=5s --health-timeout=5s --health-retries=20
    env:
      DB_HOST: 127.0.0.1
      DB_PORT: 3306              # pgsql: 5432
      DB_USERNAME: root          # pgsql: postgres
      DB_PASSWORD: password
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Set up PHP <php-floor>
        uses: shivammathur/setup-php@v2
        with:
          php-version: '<php-floor>'
          coverage: none
          extensions: pdo_mysql    # pgsql: pdo_pgsql
          tools: composer:v2
      - name: Install dependencies
        run: composer install --no-interaction --no-progress --prefer-dist
      - name: Prepare the Laravel environment
        run: |
          cp .env.example .env
          php artisan key:generate --ansi
      - name: Integration tests
        run: composer test:integration
      # Browser UI tests (Playwright + axe-core, `.ui-quality.yml` level) — only when the scaffold wrote
      # playwright.config.ts. Its webServer runs `php artisan serve` on the .env above (SQLite), so the database is
      # created and migrated first; assets are built so the pages render as in production.
      - name: Set up Node for the browser UI tests
        if: ${{ hashFiles('playwright.config.*') != '' }}
        uses: actions/setup-node@v7
        with:
          node-version: 24
          cache: npm
      - name: Browser UI tests
        if: ${{ hashFiles('playwright.config.*') != '' }}
        run: |
          npm ci
          npm run build
          npx playwright install --with-deps chromium
          touch database/database.sqlite
          php artisan migrate --force --no-interaction
          npm run test:e2e
      - name: Upload UI screenshots
        if: always()
        uses: actions/upload-artifact@v7
        with:
          name: ui-screenshots-integration
          path: .ui-screenshots/
          retention-days: 7
          if-no-files-found: ignore
```

`wordpress-plugin` / `wordpress-theme` — the scaffold's `WP_UnitTestCase` suite inside its dedicated wp-env test
environment (`.wp-env.test.json`, never the development site's `.wp-env.json`), on the `Requires at least:` floor
with the PHP floor and on the latest WordPress with the newest PHP. wp-env mounts the repository as
`wp-content/<wp-content-dir>/<directory basename>` and the scaffold's `test:integration` script assumes that basename
is `<slug>` — on a runner the checkout directory is the *repository* name, so the job checks out into `<slug>/`:

```yaml
  integration:
    name: Integration tests (WordPress ${{ matrix.wp }}, PHP ${{ matrix.php }})
    needs: tests
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        include:
          - wp: '<wp-floor>'
            core: 'WordPress/WordPress#<wp-floor>'
            php: '<php-floor>'
          - wp: latest
            core: ''
            php: '<php-latest>'
    defaults:
      run:
        working-directory: <slug>
    steps:
      - name: Check out code
        uses: actions/checkout@v7
        with:
          path: <slug>
      - name: Set up PHP <php-floor>
        uses: shivammathur/setup-php@v2
        with:
          php-version: '<php-floor>'
          coverage: none
          tools: composer:v2
      # vendor/ is installed on the runner and mounted into the wp-env containers with the plugin/theme.
      - name: Install Composer dependencies
        run: composer install --no-interaction --no-progress --prefer-dist
      - name: Set up Node
        uses: actions/setup-node@v7
        with:
          node-version: 24
          cache: npm
          cache-dependency-path: <slug>/package-lock.json
      - name: Install wp-env
        run: npm ci
      # WP_ENV_CORE / WP_ENV_PHP_VERSION override .wp-env.test.json's core/phpVersion for this matrix entry
      # (an empty core keeps "latest").
      - name: Start the WordPress test environment
        env:
          CORE: ${{ matrix.core }}
          WP_ENV_PHP_VERSION: ${{ matrix.php }}
        run: |
          if [ -n "$CORE" ]; then export WP_ENV_CORE="$CORE"; fi
          npm run test:env:start
      - name: Integration tests
        run: composer test:integration
      # Browser UI tests (`wp-scripts test-playwright`, `.ui-quality.yml` level) against the test environment the
      # step above started (`.wp-env.test.json`, http://localhost:8889 — the instance the scaffold's
      # playwright.config.ts targets through WP_BASE_URL) — only when the scaffold wrote playwright.config.ts, and
      # only on the latest-WordPress entry. Chromium is installed explicitly, so wp-scripts must not download again.
      - name: Browser UI tests
        if: ${{ matrix.wp == 'latest' && hashFiles('<slug>/playwright.config.*') != '' }}
        env:
          WP_BASE_URL: http://localhost:8889
        run: |
          npx playwright install --with-deps chromium
          PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm run test:e2e
      - name: Upload UI screenshots
        if: ${{ always() && matrix.wp == 'latest' }}
        uses: actions/upload-artifact@v7
        with:
          name: ui-screenshots-integration-wp-${{ matrix.wp }}
          path: <slug>/.ui-screenshots/
          retention-days: 7
          if-no-files-found: ignore
```

`hashFiles()` and `upload-artifact`'s `path` resolve from the workspace root, not from `defaults.run.working-directory`
— hence the `<slug>/` prefix there. The browser tests reuse the environment this job already starts: no extra job,
runner, or WordPress matrix entry.

`prestashop-module` — the scaffold's Docker shop (`tests/Integration/docker-compose.yml`, `PS_VERSION=8|9`): the
`Integration` suite plus PHPStan against the real shop (`lint:shop`, which the stub-based `lint` can't cover), and —
because this job already has a running shop (`PS_DOMAIN` `localhost:${PS_PORT:-8080}`) — the scaffold's Playwright
browser UI tests against it through `PS_BASE_URL` (they skip without a shop):

```yaml
  integration:
    name: Integration tests (PrestaShop ${{ matrix.ps }})
    needs: tests
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        ps: [ <ps-versions> ]
    env:
      PS_VERSION: ${{ matrix.ps }}
      # shop:up waits for the auto-install; Composer would otherwise kill a script after 300 s.
      COMPOSER_PROCESS_TIMEOUT: 0
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Set up PHP <php-floor>
        uses: shivammathur/setup-php@v2
        with:
          php-version: '<php-floor>'
          coverage: none
          tools: composer:v2
      # vendor/ (with PHPUnit and PHPStan) is mounted into the shop together with the module.
      - name: Install dependencies
        run: composer install --no-interaction --no-progress --prefer-dist
      - name: Start the shop
        run: composer shop:up
      - name: Install the module
        run: composer shop:install
      - name: Integration tests
        run: composer test:integration
      - name: Static analysis against the shop
        run: composer lint:shop
      # Browser UI tests (Playwright + axe-core, `.ui-quality.yml` level) against the running shop — only when the
      # scaffold wrote playwright.config.ts.
      - name: Set up Node for the browser UI tests
        if: ${{ hashFiles('playwright.config.*') != '' }}
        uses: actions/setup-node@v7
        with:
          node-version: 24
          cache: npm
      - name: Browser UI tests
        if: ${{ hashFiles('playwright.config.*') != '' }}
        env:
          PS_BASE_URL: http://localhost:8080
        run: |
          npm ci
          npx playwright install --with-deps chromium
          npm run test:e2e
      - name: Upload UI screenshots
        if: always()
        uses: actions/upload-artifact@v7
        with:
          name: ui-screenshots-integration-ps-${{ matrix.ps }}
          path: .ui-screenshots/
          retention-days: 7
          if-no-files-found: ignore
      - name: Stop the shop
        if: ${{ always() }}
        run: composer shop:down
```

Gating summary for `build.yml`: drop "Prepare the Laravel environment" for WordPress/PrestaShop; drop the
`PHPStan report for Sonar`/`Upload the PHPStan report` steps and the `sonar` job for `sonar: none` (and the
`SONAR_HOST_URL` line unless self-hosted); drop the two phpDocumentor steps and the `api/` merge line unless
`phpdoc.dist.xml` exists; keep exactly one of "Upload Pages artifact"/"Upload documentation" and drop `deploy-docs`
with `pages: no`; drop the whole `docs`/`deploy-docs` pair when there is no Antora site and no phpDocumentor (report
it); with `ci-tests: full` append the flavor's `integration` job (Laravel: keep the service/port/user/extension
alternative for the scaffold's database), keeping its browser-UI-test steps (self-guarded on `playwright.config.*`;
drop them only when the project has no `test:e2e` npm script). With `ci-tests: unit` no job runs the browser UI tests
— they stay local (`npm run test:e2e`, behind `.integration-test.lock`); say so in Step 7.

### `release.yml` (not written with `distribution: none`)

`wordpress-plugin` / `wordpress-theme`, `distribution: internal | store`:

```yaml
name: Release

on:
  release:
    types: [ released ]

permissions:
  contents: write                          # gh release upload

jobs:
  package:
    name: Build the installable zip
    runs-on: ubuntu-latest
    env:
      TAG: ${{ github.event.release.tag_name }}
    steps:
      - name: Check out the released tag
        uses: actions/checkout@v7

      # The release must carry its own version everywhere: header, constant, Stable tag (and package.json).
      - name: Check the version matches the tag
        run: |
          VERSION="${TAG#v}"
          python3 .github/scripts/php_version.py --list | grep -E '^[^ ]+:[0-9]+: ' > "$RUNNER_TEMP/versions.txt"
          cat "$RUNNER_TEMP/versions.txt"
          if grep -v -F ": $VERSION " "$RUNNER_TEMP/versions.txt"; then
            echo "::error::Some version locations don't match the release tag $VERSION (iru-php-bump-version $VERSION fixes them)."
            exit 1
          fi

      - name: Set up PHP <php-floor>
        uses: shivammathur/setup-php@v2
        with:
          php-version: '<php-floor>'
          coverage: none
          tools: composer:v2

      # wordpress-plugin — the plugin ships its production vendor/ (.distignore keeps it).
      - name: Install production dependencies
        run: composer install --no-dev --classmap-authoritative --no-interaction --no-progress --prefer-dist

      # Only when package.json has a "build" script (@wordpress/scripts blocks/assets).
      - name: Set up Node
        uses: actions/setup-node@v7
        with:
          node-version: 24
          cache: npm
      - name: Build assets
        run: |
          npm ci
          npm run build

      # The zip unpacks to <slug>/ as WordPress expects, without anything .distignore lists.
      - name: Assemble the zip
        run: |
          mkdir -p "$RUNNER_TEMP/dist/<slug>"
          rsync -a --exclude-from=.distignore ./ "$RUNNER_TEMP/dist/<slug>/"
          (cd "$RUNNER_TEMP/dist" && zip -qr -X "$RUNNER_TEMP/<slug>.zip" <slug>)

      - name: Attach the zip to the GitHub Release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: gh release upload "$TAG" "$RUNNER_TEMP/<slug>.zip" --clobber

      # store only — hands the assembled files to the deploy job.
      - name: Keep the build for the WordPress.org deploy
        uses: actions/upload-artifact@v7
        with:
          name: wordpress-org-build
          path: ${{ runner.temp }}/dist/<slug>
          retention-days: 1

  # store + wordpress-plugin only. The slug must already be approved on WordPress.org.
  deploy-plugin:
    name: Deploy to the WordPress.org Plugin Directory
    needs: package
    runs-on: ubuntu-latest
    environment: wordpress-org             # optional: add required reviewers to this environment
    permissions:
      contents: read
    steps:
      - name: Check out the released tag
        uses: actions/checkout@v7          # .wordpress-org/ (banners, icons, screenshots) comes from the repository
      - name: Download the build
        uses: actions/download-artifact@v8
        with:
          name: wordpress-org-build
          path: ${{ runner.temp }}/wordpress-org-build
      - name: Commit trunk and the tag to the plugin's SVN
        uses: 10up/action-wordpress-plugin-deploy@2.3.0
        env:
          SVN_USERNAME: ${{ secrets.SVN_USERNAME }}
          SVN_PASSWORD: ${{ secrets.SVN_PASSWORD }}
          SLUG: <slug>
          VERSION: ${{ github.event.release.tag_name }}
          BUILD_DIR: ${{ runner.temp }}/wordpress-org-build

  # store + wordpress-theme only. Themes are added through the upload form once; updates are new
  # /<slug>/<version>/ directories committed to themes.svn.wordpress.org, each reviewed before it goes live.
  deploy-theme:
    name: Deploy to the WordPress.org Theme Directory
    needs: package
    runs-on: ubuntu-latest
    environment: wordpress-org
    permissions:
      contents: read
    steps:
      - name: Download the build
        uses: actions/download-artifact@v8
        with:
          name: wordpress-org-build
          path: ${{ runner.temp }}/theme
      - name: Commit the new version to the theme's SVN
        env:
          SVN_USERNAME: ${{ secrets.SVN_USERNAME }}
          SVN_PASSWORD: ${{ secrets.SVN_PASSWORD }}
          TAG: ${{ github.event.release.tag_name }}
        run: |
          VERSION="${TAG#v}"
          command -v svn >/dev/null || { sudo apt-get update -q && sudo apt-get install -y -q subversion; }
          svn checkout --depth immediates "https://themes.svn.wordpress.org/<slug>" "$RUNNER_TEMP/svn"
          if [ -e "$RUNNER_TEMP/svn/$VERSION" ]; then
            echo "::error::Version $VERSION already exists in the Theme Directory; versions are immutable there."
            exit 1
          fi
          cp -R "$RUNNER_TEMP/theme" "$RUNNER_TEMP/svn/$VERSION"
          cd "$RUNNER_TEMP/svn"
          svn add --quiet "$VERSION"
          svn commit -m "Release $VERSION" --username "$SVN_USERNAME" --password "$SVN_PASSWORD" \
            --non-interactive --no-auth-cache
```

`prestashop-module`, `distribution: internal | store` (same `on:`/`permissions:` header):

```yaml
jobs:
  package:
    name: Build the module zip
    runs-on: ubuntu-latest
    env:
      TAG: ${{ github.event.release.tag_name }}
    steps:
      - name: Check out the released tag
        uses: actions/checkout@v7
      - name: Check the version matches the tag
        run: |
          VERSION="${TAG#v}"
          python3 .github/scripts/php_version.py --list | grep -E '^[^ ]+:[0-9]+: ' > "$RUNNER_TEMP/versions.txt"
          cat "$RUNNER_TEMP/versions.txt"
          if grep -v -F ": $VERSION " "$RUNNER_TEMP/versions.txt"; then
            echo "::error::Some version locations don't match the release tag $VERSION (iru-php-bump-version $VERSION fixes them)."
            exit 1
          fi
      - name: Set up PHP <php-floor>
        uses: shivammathur/setup-php@v2
        with:
          php-version: '<php-floor>'
          coverage: none
          tools: composer:v2
      # bin/package.sh: .distignore'd copy, composer install --no-dev, index.php guard in every directory.
      - name: Build build/<slug>-<version>.zip
        run: composer package
      - name: Attach the zip to the GitHub Release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: gh release upload "$TAG" "build/<slug>-${TAG#v}.zip" --clobber
      # store only — the PrestaShop Addons marketplace has no upload API.
      - name: PrestaShop Addons instructions
        run: |
          {
            echo "### Publish ${TAG#v} on PrestaShop Addons"
            echo "1. Download \`<slug>-${TAG#v}.zip\` from this release."
            echo "2. Seller account → Products → <your module> → upload a new version; set the PrestaShop compatibility range to match \`ps_versions_compliancy\`."
            echo "3. Fill in the changelog (copy this release's CHANGELOG.md section) and submit for validation."
          } >> "$GITHUB_STEP_SUMMARY"
```

`laravel`, `distribution: internal` — the scaffold's `Dockerfile` to GHCR:

```yaml
name: Release

on:
  release:
    types: [ released ]

permissions:
  contents: read
  packages: write                          # GHCR push with GITHUB_TOKEN

jobs:
  image:
    name: Build and push the container image
    runs-on: ubuntu-latest
    steps:
      - name: Check out the released tag
        uses: actions/checkout@v7
      - name: Compute image coordinates
        id: image
        env:
          TAG: ${{ github.event.release.tag_name }}
        run: |
          echo "owner=${GITHUB_REPOSITORY_OWNER,,}" >> "$GITHUB_OUTPUT"   # registry paths must be lowercase
          echo "version=${TAG#v}" >> "$GITHUB_OUTPUT"
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v4
      - name: Log in to GHCR
        uses: docker/login-action@v4
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Image metadata
        id: meta
        uses: docker/metadata-action@v6
        with:
          images: ghcr.io/${{ steps.image.outputs.owner }}/<slug>
          tags: |
            type=raw,value=${{ steps.image.outputs.version }}
            type=raw,value=latest
      # frankenphp: the only build. fpm: the "app" target (PHP-FPM); the web image follows.
      - name: Build and push the application image
        uses: docker/build-push-action@v7
        with:
          context: .
          target: app                      # fpm only — drop for frankenphp
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      # fpm only — the Nginx "web" target serving public/ and proxying PHP to the app container.
      - name: Web image metadata
        id: meta-web
        uses: docker/metadata-action@v6
        with:
          images: ghcr.io/${{ steps.image.outputs.owner }}/<slug>-web
          tags: |
            type=raw,value=${{ steps.image.outputs.version }}
            type=raw,value=latest
      - name: Build and push the web image
        uses: docker/build-push-action@v7
        with:
          context: .
          target: web
          push: true
          tags: ${{ steps.meta-web.outputs.tags }}
          labels: ${{ steps.meta-web.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

Notes: the image carries no `.env` — `APP_KEY`, `APP_VERSION`, database credentials are runtime environment
variables (`config('app.version')` reads `APP_VERSION`; `docker/metadata-action` already labels the image with the
version). No image per `<integration-branch>` push — add one only if a deployment pipeline consumes it. WordPress
`Stable tag:` is checked by "Check the version matches the tag": WordPress.org serves whatever tag `Stable tag:` names,
so a release whose readme still names the previous version must fail here, not after the SVN commit. PrestaShop:
never upload a `-dev` zip to a real shop or to Addons — `ps_module.version` is `VARCHAR(8)`, so `1.5.0-dev` is
stored as `1.5.0-de` and the module manager keeps offering an upgrade (only release zips come out of this workflow).

### `sync.yml`

```yaml
name: Sync

# After a release is published from <stable-branch>, open a pull request that merges it back into
# <integration-branch> and bumps the development version to the next x.(y+1).0-dev.
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
            echo "::error::Release tag '$RELEASE_VERSION' is not in X.Y.Z form; cannot compute the next -dev version."
            exit 1
          fi
          NEXT_MINOR=$((MINOR + 1))
          {
            echo "release_version=$RELEASE_VERSION"
            echo "next_version=${MAJOR}.${NEXT_MINOR}.0-dev"
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

      - name: Set up Python
        if: ${{ steps.guard.outputs.exists == 'false' }}
        uses: actions/setup-python@v7
        with:
          python-version: '3.x'

      # Same helper iru-php-bump-version uses: rewrites the flavor's version locations, refuses if they disagree,
      # never touches readme.txt's Stable tag for a -dev value.
      - name: Bump the development version
        if: ${{ steps.guard.outputs.exists == 'false' }}
        run: python3 .github/scripts/php_version.py "${{ steps.versions.outputs.next_version }}"

      # wordpress — only when package.json carries a "version".
      - name: Bump package.json and its lockfile
        if: ${{ steps.guard.outputs.exists == 'false' }}
        run: npm version "${{ steps.versions.outputs.next_version }}" --no-git-tag-version --allow-same-version

      - name: Bump README and Antora versions
        if: ${{ steps.guard.outputs.exists == 'false' }}
        env:
          RELEASE_VERSION: ${{ steps.versions.outputs.release_version }}
          NEXT_VERSION: ${{ steps.versions.outputs.next_version }}
        run: python3 .github/scripts/sync_versions.py

      - name: Commit and push the sync branch
        if: ${{ steps.guard.outputs.exists == 'false' }}
        run: |
          git add -u
          git diff --cached --quiet || git commit -m "Sync ${{ steps.versions.outputs.next_version }}"
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
            --title "Sync ${{ steps.versions.outputs.next_version }}" \
            --body "Merges \`<stable-branch>\` back into \`<integration-branch>\` after releasing \`${{ steps.versions.outputs.release_version }}\`, and bumps the development version to \`${{ steps.versions.outputs.next_version }}\`." \
            --label sync
```

The bump is always minor (`1.3.0` → `1.4.0-dev`), matching `iru-php-bump-version`'s Step 5 and `iru-release`'s
default "next upcoming version"; flag it in Step 7 if the team releases patches from `<integration-branch>` too.
`CHANGELOG.md` isn't touched — its release section arrives through the merge. PrestaShop: the sync PR's `-dev`
version shows truncated (`1.4.0-de`) in a dev shop's module manager — expected, see the release notes above.

### `.github/scripts/php_version.py`

The exact helper embedded in `iru-php-bump-version`'s Step 2 (keep the two identical — the release workflows'
version check and `sync.yml` both rely on its `--list` output format `<file>:<line>: <value>    [<location>]`):

```python
import difflib, json, pathlib, re, subprocess, sys

args = sys.argv[1:]
dry, force = "--dry-run" in args, "--force" in args
flavor = next((a.split("=", 1)[1] for a in args if a.startswith("--flavor=")), "auto")
args = [a for a in args if not a.startswith("--")]
new = args[0] if args else None          # None => --list
root = pathlib.Path(".")
is_release = new is not None and "-" not in new


def read(p):
    return p.read_text(encoding="utf-8")


def header(p, size=8192):
    return read(p)[:size]                 # WordPress reads only the first 8 KB for file headers


def tracked(p):
    try:
        r = subprocess.run(["git", "ls-files", "--error-unmatch", str(p)], capture_output=True)
        return r.returncode == 0 if r.returncode in (0, 1) else True
    except FileNotFoundError:
        return True                       # no git: treat an existing file as tracked


def composer():
    p = root / "composer.json"
    return json.loads(read(p)) if p.exists() else {}


def detect():
    c = composer()
    if "laravel/framework" in c.get("require", {}) and (root / "artisan").exists():
        return "laravel", None
    for p in sorted(root.glob("*.php")):
        if re.search(r"^[ \t/*#@]*Plugin Name:", header(p), re.M):
            return "wordpress-plugin", p
    css = root / "style.css"
    if css.exists() and re.search(r"^[ \t/*#@]*Theme Name:", header(css), re.M):
        return "wordpress-theme", css
    for p in sorted(root.glob("*.php")):
        t = read(p)
        if re.search(r"\bclass\s+\w+\s+extends\s+(Module|PaymentModule|CarrierModule)\b", t) and "$this->version" in t:
            return "prestashop-module", p
    return "library", None


# Each rule: (file, compiled regex with groups pre/value/post, release_only, note)
def rules(kind, main):
    out = []
    if kind == "laravel":
        out.append((root / "config/app.php",
                    re.compile(r"""(['"]version['"]\s*=>\s*(?:env\(\s*['"]APP_VERSION['"]\s*,\s*)?['"])([^'"]*)(['"])"""),
                    False, "config/app.php 'version'"))
    elif kind in ("wordpress-plugin", "wordpress-theme"):
        out.append((main, re.compile(r"^([ \t/*#@]*Version:[ \t]*)(\S+)()", re.M), False, "header Version:"))
        const_file = main if kind == "wordpress-plugin" else root / "functions.php"
        out.append((const_file,
                    re.compile(r"""(define\(\s*['"][A-Z][A-Z0-9_]*_VERSION['"]\s*,\s*['"])([^'"]+)(['"])"""
                               r"""|(const\s+[A-Z][A-Z0-9_]*_VERSION\s*=\s*['"])([^'"]+)(['"])"""),
                    False, "<PREFIX>_VERSION constant"))
        out.append((root / "readme.txt", re.compile(r"^(Stable tag:[ \t]*)(\S+)()", re.M | re.I), True,
                    "readme.txt Stable tag (release versions only)"))
    elif kind == "prestashop-module":
        out.append((main, re.compile(r"""(\$this->version\s*=\s*['"])([^'"]+)(['"])"""), False, "$this->version"))
        xml = root / "config.xml"
        if xml.exists() and tracked(xml):
            out.append((xml, re.compile(r"(<version>\s*(?:<!\[CDATA\[)?)([^<\]]+)((?:\]\]>)?\s*</version>)"),
                        False, "config.xml <version>"))
    return out


def groups(m):
    g = m.groups()
    if len(g) == 6 and g[0] is None:      # second alternative of the constant regex
        g = g[3:]
    return g[:3]


kind, main = (flavor, None) if flavor != "auto" else detect()
if flavor != "auto" and kind != "library":
    _, main = detect()
print(f"flavor: {kind}" + (f" (main file: {main.as_posix()})" if main else ""))

c = composer()
if "version" in c:
    print(f"WARNING: composer.json has a \"version\" field ({c['version']}); Composer recommends omitting it — "
          "it is not part of this convention and is left untouched", file=sys.stderr)

if kind == "library":
    print("library: no in-tree version — the git tag is the version; nothing to change")
    sys.exit(0)
if kind in ("wordpress-plugin", "wordpress-theme", "prestashop-module") and main is None:
    sys.exit(f"Could not find the main file for flavor {kind}")

found, new_texts = [], {}
for path, rx, release_only, label in rules(kind, main):
    if not path.exists():
        continue
    text = new_texts.get(path, read(path))
    hits = list(rx.finditer(text[:8192] if label == "header Version:" else text))
    if label in ("header Version:", "readme.txt Stable tag (release versions only)"):
        hits = hits[:1]
    elif label == "<PREFIX>_VERSION constant" and len(hits) > 1:
        # Several *_VERSION constants (e.g. ACME_DB_VERSION): the plugin/theme version is the shortest name.
        name = lambda m: re.search(r"[A-Z][A-Z0-9_]*_VERSION", m.group(0)).group(0)
        keep = min(hits, key=lambda m: len(name(m)))
        for m in hits:
            if m is not keep:
                print(f"note: ignoring {name(m)} in {path.as_posix()} (not the {name(keep)} version constant)")
        hits = [keep]
    for m in hits:
        pre, value, post = groups(m)
        found.append((path.as_posix(), text.count("\n", 0, m.start()) + 1, value, label, release_only))
    if new is None or not hits or (release_only and not is_release):
        continue
    def repl(m):
        pre, _, post = groups(m)
        return pre + new + post
    for m in reversed(hits):              # only the selected occurrences, never every regex match
        text = text[:m.start()] + repl(m) + text[m.end():]
    new_texts[path] = text

pkg = root / "package.json"
if pkg.exists() and kind != "laravel":
    v = json.loads(read(pkg)).get("version")
    if v is not None:
        found.append(("package.json", 0, v, "package.json version (written with npm, not by this script)", False))

for path, line, value, label, release_only in found:
    print(f"{path}:{line}: {value}    [{label}]")
required = {"laravel": "config/app.php 'version'", "wordpress-plugin": "header Version:",
            "wordpress-theme": "header Version:", "prestashop-module": "$this->version"}[kind]
if not any(f[3] == required for f in found):
    sys.exit(f"No {required} found — the version location this flavor's convention requires is missing")
values = {f[2] for f in found if not f[4]}
if len(values) > 1:
    print(f"WARNING: version locations disagree: {sorted(values)}", file=sys.stderr)
    if new is not None and not force:
        sys.exit("Refusing to write: confirm with the user, then re-run with --force to align every location")
if new is None:
    sys.exit(0)
for path, text in new_texts.items():
    old = read(path)
    if text == old:
        continue
    if dry:
        sys.stdout.writelines(difflib.unified_diff(old.splitlines(True), text.splitlines(True), str(path), str(path)))
    else:
        path.write_text(text, encoding="utf-8")
        print(f"updated {path.as_posix()}")
if any(f[4] for f in found) and not is_release:
    print("note: readme.txt Stable tag left unchanged (only release versions are written there)")
if kind == "prestashop-module" and is_release and not (root / "upgrade" / f"upgrade-{new}.php").exists():
    print(f"note: no upgrade/upgrade-{new}.php — add one if this release changes the schema, configuration or hooks")
if pkg.exists() and kind != "laravel" and any(f[0] == "package.json" for f in found):
    print(f"next: npm version {new} --no-git-tag-version --allow-same-version  (package.json + lockfile)")
```

### `.github/scripts/sync_versions.py`

```python
#!/usr/bin/env python3
"""Rewrites README/Antora version references after a release, for the Sync workflow.

Reads RELEASE_VERSION and NEXT_VERSION from the environment. The flavor's own version locations (config/app.php,
plugin/theme headers and constants, the PrestaShop module class and config.xml) are bumped by php_version.py in the
step before, and package.json by npm; this script only handles the README's version table and the Antora component
version. CHANGELOG.md is left alone: its release section arrives through the merge that precedes this script.
"""
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def update_readme(release_version, next_version):
    path = REPO_ROOT / "README.md"
    if not path.exists():
        return
    text = path.read_text()
    # Adjust these row labels if this repository's README words them differently (Step 1's survey).
    text = re.sub(r"(\| Current development version \| `)[^`]*(` \|)", rf"\g<1>{next_version}\g<2>", text)
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
    next_version = os.environ["NEXT_VERSION"]
    update_readme(release_version, next_version)
    update_antora_component_version(release_version)


if __name__ == "__main__":
    main()
```

### `security.yml`

The shared security block every workflows skill in this catalog embeds, adapted to PHP: **CodeQL has no PHP
extractor**, so CodeQL covers the workflows themselves (`actions`) and any JS/TS, and Psalm's taint analysis is the
PHP code-scanning substitute — its SARIF lands in the same Security → Code scanning view. Drop a job's whole entry
when its `security-*` flag is `no`; if all are `no`, don't write the file (say so in Step 7).

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
  dependency-review:
    name: Dependency review
    if: ${{ github.event_name == 'pull_request' }}
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
    name: CodeQL analysis (${{ matrix.language }})
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    strategy:
      fail-fast: false
      matrix:
        language: [ actions, javascript-typescript ]   # javascript-typescript only when the repository has JS/TS
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Initialize CodeQL
        uses: github/codeql-action/init@v4
        with:
          languages: ${{ matrix.language }}
          build-mode: none
      - name: Perform CodeQL analysis
        uses: github/codeql-action/analyze@v4
        with:
          category: /language:${{ matrix.language }}

  # PHP code scanning: Psalm's taint analysis (XSS, SQL injection, SSRF, header/shell/file injection …), as SARIF.
  psalm-taint:
    name: Psalm taint analysis
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Set up PHP <php-latest> with Psalm
        uses: shivammathur/setup-php@v2
        with:
          php-version: '<php-latest>'
          coverage: none
          tools: composer:v2, psalm
      # Psalm needs the autoloader to resolve the project's own classes and its dependencies.
      - name: Install dependencies
        run: composer install --no-interaction --no-progress --prefer-dist --ignore-platform-req=php
      # Exit code 2 = taint findings (reported through SARIF); anything else non-zero is a real failure.
      - name: Run the taint analysis
        run: |
          mkdir -p build
          psalm --config=.github/psalm/psalm-taint.xml --taint-analysis --no-cache --no-progress \
            --report=build/psalm-taint.sarif || [ $? -eq 2 ]
      - name: Upload results to code scanning
        if: ${{ always() && hashFiles('build/psalm-taint.sarif') != '' }}
        uses: github/codeql-action/upload-sarif@v4
        with:
          sarif_file: build/psalm-taint.sarif
          category: psalm-taint

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

`security-taint` gates `psalm-taint` (and the `.github/psalm/` files); `security-codeql: no` drops `codeql`, and with
no JS/TS the matrix is just `[ actions ]`. OSV-Scanner reads `composer.lock` (plus `package-lock.json`s) — no setup.

**`.github/psalm/psalm-taint.xml`** — a dedicated config so the project's own Psalm setup (if any) isn't touched;
`resolveFromConfigFile="false"` makes paths relative to the repository root. `<project-files>` per flavor:
Laravel `<directory name="app"/>` (+ `routes`); WordPress plugin `<file name="<slug>.php"/>`, `<directory
name="src"/>` (+ `includes`/`admin`/`public` when present) and `uninstall.php`; theme `functions.php`, `src`,
`patterns`; PrestaShop `<file name="<slug>.php"/>`, `src`, `controllers`, `upgrade`. Drop the `<stubs>` element for
Laravel (PrestaShop points it at `prestashop-taint.phpstub`); `<globals>` is WordPress only.

```xml
<?xml version="1.0"?>
<psalm errorLevel="8" resolveFromConfigFile="false" findUnusedCode="false" findUnusedBaselineEntry="false"
       xmlns="https://getpsalm.org/schema/config">
    <projectFiles>
        <project-files/>
        <ignoreFiles allowMissingFiles="true">
            <directory name="vendor"/>
            <directory name="tests"/>
        </ignoreFiles>
    </projectFiles>
    <stubs>
        <file name=".github/psalm/wordpress-taint.phpstub"/>   <!-- PrestaShop: prestashop-taint.phpstub -->
    </stubs>
    <globals>
        <var name="wpdb" type="\wpdb"/>
    </globals>
</psalm>
```

**`.github/psalm/wordpress-taint.phpstub`** — Psalm doesn't know WordPress's escaping API, so without these
annotations every correctly escaped `echo esc_html( … )` would be reported. Stubs are read by Psalm only:

```php
<?php
// Taint annotations for the WordPress escaping/sanitizing API (read by Psalm only, never loaded by PHP).
/** @psalm-taint-escape html @psalm-taint-escape has_quotes */ function esc_html($text) {}
/** @psalm-taint-escape html @psalm-taint-escape has_quotes */ function esc_attr($text) {}
/** @psalm-taint-escape html @psalm-taint-escape has_quotes */ function esc_textarea($text) {}
/** @psalm-taint-escape html @psalm-taint-escape has_quotes */ function esc_html__($text, $domain = 'default') {}
/** @psalm-taint-escape html @psalm-taint-escape has_quotes */ function esc_attr__($text, $domain = 'default') {}
/** @psalm-taint-escape html @psalm-taint-escape has_quotes @psalm-taint-escape ssrf */ function esc_url($url, $protocols = null, $_context = 'display') {}
/** @psalm-taint-escape ssrf @psalm-taint-escape header */ function esc_url_raw($url, $protocols = null) {}
/** @psalm-taint-escape html @psalm-taint-escape has_quotes */ function wp_kses_post($data) {}
/** @psalm-taint-escape html @psalm-taint-escape has_quotes */ function wp_kses($content, $allowed_html, $allowed_protocols = array()) {}
/** @psalm-taint-escape html @psalm-taint-escape has_quotes @psalm-taint-escape sql */ function sanitize_text_field($str) {}
/** @psalm-taint-escape html @psalm-taint-escape has_quotes @psalm-taint-escape sql */ function sanitize_key($key) {}
/** @psalm-taint-escape html @psalm-taint-escape has_quotes @psalm-taint-escape sql */ function absint($maybeint) {}
/** @psalm-taint-escape html @psalm-taint-escape has_quotes */ function wp_json_encode($value, $flags = 0, $depth = 512) {}
/** @psalm-pure */ function wp_unslash($value) { return $value; }
class wpdb {
    /** @psalm-taint-sink sql $query */
    public function query($query) {}
    /** @psalm-taint-escape sql */
    public function prepare($query, ...$args) {}
}
```

**`.github/psalm/prestashop-taint.phpstub`** — the shop's classes aren't installed in this job, so the stub also
declares the input source and the SQL sinks:

```php
<?php
// Taint annotations for the PrestaShop input/escaping API (read by Psalm only, never loaded by PHP).
class Tools
{
    /** @psalm-taint-source input */
    public static function getValue($key, $default_value = false) {}
    /** @psalm-taint-source input */
    public static function getAllValues() {}
    /** @psalm-taint-escape html @psalm-taint-escape has_quotes */
    public static function safeOutput($string, $html = false) {}
    /** @psalm-taint-escape html @psalm-taint-escape has_quotes */
    public static function htmlentitiesUTF8($string, $type = ENT_QUOTES) {}
}
class Db
{
    /** @return Db */
    public static function getInstance($master = true) {}
    /** @psalm-taint-sink sql $sql */
    public function execute($sql, $use_cache = true) {}
    /** @psalm-taint-sink sql $sql */
    public function executeS($sql, $array = true, $use_cache = true) {}
    /** @psalm-taint-sink sql $sql */
    public function getValue($sql, $use_cache = true) {}
    /** @psalm-taint-sink sql $sql */
    public function getRow($sql, $use_cache = true) {}
}
/** @psalm-taint-escape sql */
function pSQL($string, $htmlOK = false) {}
/** @psalm-taint-escape sql */
function bqSQL($string) {}
class Module {}
```

Limits to state in Step 7: taint analysis sees PHP only — Blade, Smarty and Twig templates (where most output
happens in Laravel/PrestaShop) aren't analysed; for Laravel, Psalm knows superglobals but not `Request::input()` —
adding `psalm/plugin-laravel` to `require-dev` and `<plugins><pluginClass class="Psalm\LaravelPlugin\Plugin"/></plugins>`
to the config makes request input a taint source (a project decision, not made here). Findings are alerts, not a
failed build; triage them in Code scanning.

### `.github/dependabot.yml` (always written — no opt-out)

```yaml
version: 2
updates:
  - package-ecosystem: composer
    directory: /
    schedule:
      interval: weekly
    groups:
      composer-dependencies:
        patterns: [ "*" ]

  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    groups:
      github-actions-dependencies:
        patterns: [ "*" ]

  # Only when a root package.json exists (Laravel Vite, @wordpress/scripts, @wordpress/env).
  - package-ecosystem: npm
    directory: /
    schedule:
      interval: weekly
    groups:
      npm-dependencies:
        patterns: [ "*" ]

  # laravel + distribution: internal only — the Dockerfile's base images.
  - package-ecosystem: docker
    directory: /
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

Composer updates respect `config.platform.php`, so Dependabot never proposes a version the floor can't run. When
updating an existing `dependabot.yml`, keep entries for ecosystems this skill doesn't manage.

## Step 4 — Fill and gate

Substitute every placeholder from Step 1, apply every gate above, and strip the guidance comments. Never invent a
value: an unresolved fact (no `test:integration` script, no Antora playbook, no Sonar project key, no `Dockerfile`
for Laravel `internal` — `iru-setup-php-laravel` writes it) is either asked or reported as an open gap in Step 7.
Also:

- **`sonar-project.properties`** missing with `sonar` ≠ `none` → ask for the organization/project key (and host URL
  for self-hosted) and write the flavor scaffold's own template (`iru-setup-php-laravel`/`-wordpress`/`-prestashop`
  own it); every flavor reads `sonar.php.coverage.reportPaths=build/logs/clover.xml`,
  `sonar.php.tests.reportPath=build/logs/junit.xml`, `sonar.php.phpstan.reportPaths=build/logs/phpstan.json`.
- `.github/scripts/php_version.py` is written whenever `sync.yml` or a WordPress/PrestaShop `release.yml` is (both use
  it); `chmod +x` both scripts.

## Step 5 — Validate

- Run `actionlint` on every generated workflow — `actionlint` if installed, else
  `docker run --rm -v "$PWD":/repo -w /repo rhysd/actionlint:latest -color` — and fix every finding (shellcheck
  findings in `run:` blocks included). Parse `.github/dependabot.yml` with
  `python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" .github/dependabot.yml` and the Psalm config with
  `python3 -c "import xml.dom.minidom,sys; xml.dom.minidom.parse(sys.argv[1])" .github/psalm/psalm-taint.xml`.
- Run the commands the workflows contain locally first, through `iru-gate-runner` agents (compact results):
  `composer validate --strict`, `composer audit --locked`, `composer lint`, `composer format:check`, `composer
  test:coverage`, and `python3 .github/scripts/php_version.py --list` (every location must agree and match the
  `-dev` convention). With `ci-tests: full` and Docker available, also the flavor's integration commands; Docker
  unavailable → the integration job is **unverified**, not failed. The browser UI test steps likewise: run
  `npm run test:e2e` locally behind `.integration-test.lock` when Node, a browser and the flavor's server (Laravel's
  `php artisan serve`, wp-env) are available, else **unverified**. A workflow whose commands were never run is a
  guess.
- Never trigger `release.yml` or `sync.yml` for real as a test. Recommend a throwaway pre-release on a fork, or
  review of the first real release run.

## Step 6 — Write the files

Write (or, per Step 2, update/replace — and skip kept units) the workflows, the two scripts (only together with
`sync.yml`/`release.yml` as above), `security.yml` with `.github/psalm/`, and `.github/dependabot.yml`. With
`distribution: none`, write no `release.yml`.

## Step 7 — Report: secrets, settings, choices, warnings

Required secrets (Settings → Secrets and variables → Actions) — list only the rows that apply:

| Secret | Purpose | Needed when |
|---|---|---|
| `SONAR_TOKEN` | SonarCloud/SonarQube token for the scan | `sonar` is `cloud` or `self-hosted` (cloud on a private repository also needs a paid SonarCloud plan) |
| `SVN_USERNAME` / `SVN_PASSWORD` | WordPress.org account (SVN password from the profile's Account & Security page) committing to the plugin/theme SVN | `distribution: store`, WordPress |

`GITHUB_TOKEN` needs no setup and covers release uploads, GHCR, Pages, Sync and every `security.yml` job (gitleaks needs
`GITLEAKS_LICENSE` only for organization accounts on its paid tier — mention it). Repository settings to check:

- **Settings → Actions → General → Workflow permissions** must allow GitHub Actions to create pull requests, or
  `sync.yml` fails on `gh pr create` despite its `permissions:` block.
- **Pages** (`pages: yes`): Source = **GitHub Actions**. Private repositories need Pro/Team/Enterprise Cloud, and the
  site is public unless Enterprise Cloud private Pages.
- **Code scanning** must be enabled for the CodeQL and Psalm SARIF uploads; **Dependency graph** for dependency review
  (on by default for public repositories).
- **WordPress.org** (`store`): the plugin/theme must already be approved (first submission is manual, via the upload
  form); an optional `wordpress-org` environment with required reviewers gates every deploy.
- **GHCR** (Laravel `internal`): the first push creates the package as *private*; link it to the repository and change
  its visibility if needed.
- **PrestaShop Addons** (`store`): uploads stay manual — the release's job summary lists the steps.

Then summarize: scratch vs update and, per unit, **created / updated / replaced / kept as is** (with mismatches) or
stopped; flavor, `<slug>`, PHP floor and matrix (and where they came from); `visibility` (and its source) with the
minutes note for private repositories; `ci-tests` (and for `full`, which integration job — database, WordPress
matrix, PrestaShop majors and why a major was left out — and whether it runs the browser UI tests and uploads
`.ui-screenshots/`, or why not); `pages`; `sonar` (+ keys) or why omitted; `distribution`
(or why `release.yml` wasn't written); which security jobs were included, that CodeQL can't analyse PHP and Psalm
taint analysis substitutes for it (with its limits above); and every open gap (missing composer scripts, no Antora
setup, README wording `sync_versions.py` won't match, patch releases the minor-bump default doesn't handle, a
repository name that differs from the WordPress slug — handled by the integration job's checkout path, but worth
knowing for local runs).

Warn explicitly: **review every workflow before pushing it.** Branch names, versions, slugs and image coordinates were
inferred from this repository and may need correcting; `release.yml` publishes to GitHub Releases, WordPress.org or
GHCR, and `sync.yml` pushes branches and opens pull requests, so verify both against the first real release. Nothing
in these files contains a credential, and it must stay that way.

## Verification notes

Verified in `$TMPDIR/iru-verify/php-setup/workflows/`:

- **actionlint** (`rhysd/actionlint`, Docker) clean on every workflow rendered from these templates for four variants —
  `laravel` (MySQL integration, `internal` FPM two-image release, Sonar, Pages), `wordpress-plugin` (`store`, wp-env
  integration matrix, Sonar, phpDocumentor, Pages), `wordpress-theme` (`internal` + theme SVN deploy job, `pages: no`),
  `prestashop-module` (`store`, shop integration, no Sonar) — including `sync.yml` and `security.yml`.
- **Action refs** checked against the GitHub API on the day of writing; `google/osv-scanner-action` has no `v2` ref
  (tags `v2.0.0`…`v2.7.0` only), so this skill pins `v2.7.0`.
- **Version helper**: identical to `iru-php-bump-version`'s (diffed); its fixture runs are listed there. The release
  workflows' tag check (`grep -v -F ": $VERSION "` over `--list`) was run against those fixtures: it passes on a
  released plugin and fails when `Stable tag:` still names the previous release.
- **wp-env**: `@wordpress/env` 11.17.0 on the host Docker, a plugin with a `.wp-env.test.json` (`testsEnvironment:
  false`): `WP_ENV_CORE=WordPress/WordPress#6.5 WP_ENV_PHP_VERSION=8.2 wp-env start --config=.wp-env.test.json` gave
  WordPress 6.5 on PHP 8.2.34 and a `WP_UnitTestCase` suite passed via `wp-env run cli --config=… --env-cwd=…
  vendor/bin/phpunit`; without `WP_ENV_CORE` the latest release (7.1.3) on PHP 8.4 passed too.
- **Zip assembly**: `rsync -a --exclude-from=.distignore` + `zip` produced a `<slug>/` archive without the excluded
  anchored and unanchored paths while keeping `vendor/`.
- **Psalm 6.20 taint analysis** (`psalm.phar`, `php:8.4-cli`) with the configs above: exit 2 + valid SARIF 2.1.0 on
  findings; with the WordPress stub, raw `echo $_GET[…]` and a concatenated `$wpdb->query()` were reported while
  `esc_html()`/`esc_attr( sanitize_text_field() )`/`$wpdb->prepare()`/`esc_url_raw()` paths were not; with the
  PrestaShop stub, `Db::execute()` with raw `Tools::getValue()` was reported while `(int)` and `pSQL()` paths were not.
- `composer audit --locked` exists in Composer 2 (`composer:2` image).

Not verified locally: a run on GitHub itself (service containers, PCOV via setup-php, GHCR push, Pages deploy, SARIF
upload), the WordPress.org plugin/theme SVN deploys (need real credentials and an approved slug), the PrestaShop shop
integration job (its composer scripts were verified by `iru-setup-php-prestashop`; this workflow only sequences
them), and SonarCloud ingestion of the reports.
