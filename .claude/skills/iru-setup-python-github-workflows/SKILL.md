---
name: iru-setup-python-github-workflows
description: >-
  Create or update the GitHub Actions workflows for a Python web repository of either flavor — `fastapi` (a FastAPI
  service) or `django` (a Django project) — as scaffolded by `iru-setup-python-fastapi` / `iru-setup-python-django`,
  driving everything through that scaffold contract's uv commands (`uv sync --locked`, `uv run ruff check .`,
  `uv run ruff format --check .`, `uv run mypy .`, `uv run pytest -m "not integration" --cov …`, `uv run pytest -m
  integration …`, the Sphinx `docs/api` build, `uv build`). Writes `build.yml` (every push to the integration/stable
  branches, every pull request, `workflow_dispatch` — `astral-sh/setup-uv` with its cache, lint/format/type checks,
  Django's `manage.py check` + `makemigrations --check --dry-run` + DRF `spectacular --validate --fail-on-warn`, fast
  tests with Cobertura coverage (80% floor from `[tool.coverage.report]`) and JUnit XML — across a Python matrix only
  for `ci-tests: full` on a public repository; a `migrations` job against a PostgreSQL service container (or a
  SQLite file for `database: sqlite`; no job for FastAPI `database: none`) — Alembic `upgrade head` / `check` /
  single head / `downgrade base` round trip for FastAPI (`APP_DATABASE_URL`), `check --deploy --fail-level WARNING`
  with the production settings (`DJANGO_SECRET_KEY`/`DJANGO_ALLOWED_HOSTS`/`POSTGRES_*` or `DJANGO_SQLITE_PATH`)
  plus `migrate` / `migrate --check` for Django; with `ci-tests: full` **and** `database: postgresql` an integration
  job running the testcontainers-backed `integration` marker; an unpushed container-image build check
  when a `Dockerfile` ships; an optional SonarCloud/SonarQube job (`sonarqube-scan-action`, skipped on fork pull
  requests); and a docs job — Antora plus Sphinx API docs and the OpenAPI document under `api/` — deployed to GitHub
  Pages from the stable branch with `pages: yes` or uploaded as an artifact with `pages: no`); `release.yml` (not
  written with `distribution: none`; on a published GitHub Release: version check against the tag, `uv build`
  sdist + wheel attached to the release, and the root `Dockerfile` pushed to GHCR — a private image for `internal`,
  a public one for `store`); `sync.yml` + `.github/scripts/python_version.py` (the exact helper
  `iru-python-bump-version` embeds) + `.github/scripts/sync_versions.py` (after a release from the stable branch, a PR
  merging it back into the integration branch with the next PEP 440 `X.(Y+1).0.dev0` version and a refreshed
  `uv.lock`); and the shared security block — `security.yml` (dependency-review, CodeQL for `python` and `actions`,
  OSV-Scanner over `uv.lock`, gitleaks, plus this stack's `pip-audit` job over the exported lock) and
  `.github/dependabot.yml` (`uv` — or `pip` without a `uv.lock` — `github-actions`, `docker` when a `Dockerfile`
  exists, `docker-compose` for a `compose.yaml`, `npm` for the Antora toolchain) — ending with a required-secrets
  table. Invoke as `/iru-setup-python-github-workflows`, optionally with `args` (`key: value` lines): `flavor`
  (`fastapi`/`django`, detected when absent), `integration-branch` (default `develop`), `stable-branch` (default
  `main`), `python-version` (the primary CI version, default `.python-version` else `3.13`), `database`
  (`postgresql`/`sqlite`/`none`), `orm` (FastAPI), `api` (`drf`/`ninja`/`none`, Django), `open-source`, `visibility`
  (`public`/`private`/`internal`), `ci-tests` (`unit`/`full`), `pages` (`yes`/`no`), `distribution`
  (`none`/`internal`/`store`), `sonar` (`cloud`/`self-hosted`/`none`, + `sonar-organization`/`sonar-project-key`/
  `sonar-host-url`), `mode` (`new`/`existing`), `on-existing` (`ask`/`keep`/`update`/`replace`), and
  `security-dependency-review`/`security-codeql`/`security-osv`/`security-gitleaks`/`security-pip-audit` (each
  `yes`/`no`, default `yes`). Stand-alone, it resolves `visibility` itself and asks `sonar`/`ci-tests`/`pages`/
  `distribution` with visibility-aware cost notes; it never asks `ci`. Announces whether it is creating the pipeline
  from scratch or updating one, and asks Update / Keep as is / Replace (or Stop) per existing workflow file. Used by
  `iru-setup-python-repository`; also runs standalone.
model: sonnet
allowed-tools: Read Write Edit AskUserQuestion Bash(gh *) Bash(git *) Bash(curl *) Bash(docker *) Bash(actionlint *) Bash(python3 *) Bash(uv *) Bash(uvx *) Bash(npm *) Bash(npx *) Bash(mkdir *) Bash(ls *) Bash(cat *) Bash(grep *) Bash(find *) Bash(sed -n *) Bash(chmod *)
---

# Setup Python GitHub Workflows

Scaffold (or update) the CI/CD and security pipeline for a FastAPI or Django repository:

| File | Trigger | Does |
|---|---|---|
| `.github/workflows/build.yml` | push to `<integration-branch>`/`<stable-branch>`, pull requests to them, `workflow_dispatch` | lint/format/types (+ Django checks), fast tests with coverage, migration checks against PostgreSQL, integration (`ci-tests: full`), image build check, optional Sonar, docs (Pages from `<stable-branch>` or artifact) |
| `.github/workflows/release.yml` | GitHub Release published — **not written with `distribution: none`** | tag/version check, `uv build` sdist + wheel attached to the release, container image to GHCR (private for `internal`, public for `store`) |
| `.github/workflows/sync.yml` + `.github/scripts/python_version.py` + `.github/scripts/sync_versions.py` | GitHub Release published from `<stable-branch>` | PR merging the release back into `<integration-branch>` with the next `X.(Y+1).0.dev0` version and a refreshed `uv.lock` |
| `.github/workflows/security.yml` | pushes, pull requests, weekly | dependency review, CodeQL (`python` + `actions`), OSV-Scanner, gitleaks, pip-audit |
| `.github/dependabot.yml` | — | weekly grouped updates for uv (or pip), the actions, the `Dockerfile`/`compose.yaml` images, the docs toolchain |

It fits the catalog's release flow: `iru-release` cuts `release_x.y.z` from `<integration-branch>`, bumps the version
with `iru-python-bump-version` (`X.Y.Z.dev0` → `X.Y.Z`, `uv.lock` refreshed), and opens a PR into `<stable-branch>`;
merging it runs `build.yml` there (docs to Pages); publishing the GitHub Release (tag `X.Y.Z`, no `v` prefix by this
catalog's convention — a `v` is tolerated) runs `release.yml` and `sync.yml` (next `X.(Y+1).0.dev0` back on
`<integration-branch>`).

There is deliberately **no PyPI publishing**: both flavors are deployable services, not libraries, so the
distribution channel is a container image (`distribution`), and the `publish` key of the shared vocabulary is
ignored. The sdist/wheel attached to the release is a reproducible build artifact (what `uv build` produced from the
tagged commit), not something to `pip install` from an index. A plain Python library is out of this skill's scope
(the docs' route for one is PyPI Trusted Publishing — irurueta docs: programming-languages/python/virtual-environments-and-packaging.adoc).

Every action reference uses the major (or, where the publisher has no floating major tag, the exact release) current
when this skill was written, checked with `git ls-remote --tags`: `actions/checkout@v7`, `astral-sh/setup-uv@v10.3.0`
(setup-uv stopped moving major tags after `v7` — every later release is immutable, so pin the exact one; `@v10` does
not resolve), `actions/setup-node@v7`, `actions/upload-artifact@v7`, `actions/download-artifact@v8`,
`actions/configure-pages@v6`, `actions/upload-pages-artifact@v5`, `actions/deploy-pages@v5`,
`SonarSource/sonarqube-scan-action@v8`, `docker/setup-buildx-action@v4`, `docker/login-action@v4`,
`docker/metadata-action@v6`, `docker/build-push-action@v7`, `github/codeql-action/*@v4`,
`actions/dependency-review-action@v5`, `google/osv-scanner-action/...@v2.7.0` (that repository publishes **no** `v2`
ref), `gitleaks/gitleaks-action@v3`. This is the catalog-wide convention every `iru-setup-*-github-workflows` skill
follows; the author's docs recommend pinning third-party actions to a full commit SHA in a real project instead
(irurueta docs: backend/flask/cloud-platforms-and-monitoring.adoc) — offer that as a hardening option in Step 7, and
never mix the two styles in one file. When updating an old pipeline re-check them — `gh api repos/<owner>/<repo>/tags` (not `releases/latest`,
which returns `codeql-bundle-*` for CodeQL) or `git ls-remote --tags https://github.com/<owner>/<repo>`; Dependabot's
`github-actions` entry keeps them current afterwards.

## Step 1 — Resolve inputs and survey the repository

Parse `args` first (`key: value` lines); every key found is resolved and its survey/question below is skipped:

```
flavor: fastapi
integration-branch: develop
stable-branch: main
python-version: 3.13
database: postgresql
api: drf
open-source: yes
visibility: public
ci-tests: full
pages: yes
distribution: store
sonar: cloud
sonar-organization: example-github
sonar-project-key: example_bookshelf-api
sonar-host-url: https://sonarcloud.io
mode: new
on-existing: ask
```

Ignore any other key (`ci` and `publish` included — invoking this skill means CI is wanted, and these services never
publish to PyPI). `mode` is informational; `on-existing` pre-answers Step 2. The `security-*` keys default to `yes`.

Then survey what isn't resolved:

- **Flavor** — the same markers `iru-explore` uses (first match wins): a root `manage.py` and `django` among
  `pyproject.toml` `[project].dependencies` (or `requirements*.txt`) → `django`; `fastapi` among them → `fastapi`.
  Anything else (a plain package) is outside this skill's templates: say so and ask (`AskUserQuestion`) **Stop** /
  **Continue anyway** (every flavor-specific step becomes an open gap).
- **Runner** — the templates assume uv with a committed `uv.lock` (the scaffold contract). `poetry.lock`/`pdm.lock`/
  `Pipfile.lock`/`requirements*.txt` only → say so and ask **Stop** / **Continue anyway** (every `uv sync --locked`
  becomes an open gap; this skill never migrates a project to uv). Read `[tool.uv] required-version` if present
  (setup-uv honours it). `[build-system]` missing (a uv *virtual* project, `tool.uv.package = false`) → `uv build`
  can't run: the release `dist` job is dropped and reported.
- **`<image-name>`** — `[project].name`, lowercased (the GHCR image name); confirm when the repository name differs.
- **Python versions** — `<python-version>` = `python-version` from `args`, else `.python-version` (major.minor), else
  `3.13`. `<python-floor>` = the lowest minor `requires-python` allows (`>=3.12` → `3.12`). `<python-matrix>` = every
  CPython minor from `<python-floor>` up to the newest one in bugfix support **that every locked dependency ships
  wheels for** — `curl -s https://endoflife.date/api/python.json` lists the cycles (`3.12`…`3.15` when this skill was
  written, 3.15 released days earlier: offer it only after a local `uv sync --locked --python 3.15` succeeds), quoted
  (`'3.12', '3.13', '3.14'`). Offline → ask, offering floor..`3.14`.
- **Contract tooling** — confirm in `pyproject.toml`: `[tool.ruff]`, `[tool.mypy]` (or `[tool.pyright]` — then the
  type step runs `uv run pyright`), `[tool.pytest.ini_options]` with the `integration` marker, `[tool.coverage.xml]
  output = "build/coverage/coverage.xml"`, the `dev` and `docs` dependency groups. A missing tool is never invented in
  the workflow: drop the step that would call it and list the gap in Step 7 (no `integration` marker → no integration
  job; no `docs` group/`docs/api/conf.py` → no Sphinx step).
- **FastAPI** — `alembic.ini` + its `script_location` (the scaffold's is `%(here)s/migrations` — revisions under
  `migrations/versions/`, never `alembic/`; Alembic in use → `migrations` job); the database URL setting: read
  `app/settings.py` (`env_prefix`, the URL field) → `<db-url-env>` (scaffold: `APP_DATABASE_URL` on a URL-only
  `DatabaseSettings`, so the migration job needs no other `APP_*` variable, even with `auth: yes`) and the driver the
  engine expects (`postgresql+asyncpg://`, scaffold default; `sqlite+aiosqlite://` for `database: sqlite`;
  `postgresql+psycopg://` for a sync engine); `scripts/export_openapi.py` (→ the OpenAPI step, writes
  `build/api-docs/openapi.json`).
- **Django** — `config/settings/{base,local,test,production}.py` + `config/env.py` (the scaffold contract; adapt the
  module paths for an existing project's layout); `DJANGO_SETTINGS_MODULE` for tests from `[tool.pytest.ini_options]`
  (`config.settings.test`). `<django-prod-env>` is every variable `production.py` requires, with a CI dummy. For the
  scaffold that is exactly (no `DATABASE_URL` — the scaffold never reads one): `DJANGO_ALLOWED_HOSTS` (and
  `DJANGO_SECRET_KEY`, generated per run by its own step, ≥ 50 characters); `database: postgresql` →
  `POSTGRES_HOST`, `POSTGRES_PASSWORD` (required by `config/env.py`'s `postgresql_database()`) plus `POSTGRES_PORT`,
  `POSTGRES_DB`, `POSTGRES_USER`, set explicitly to the service container's `5432`/`app`/`postgres` because their
  defaults are `5432`/`<package>`/`<package>`; `database: sqlite` → `DJANGO_SQLITE_PATH` (optional — defaults to
  `db.sqlite3` at the root — set to `build/ci.sqlite3` so CI never touches a developer-style file). Every other
  `DJANGO_*` variable (`DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_HTTPS`, HSTS, e-mail, …) has a default that passes
  `check --deploy --fail-level WARNING` — don't set them. For a non-scaffold project, find the required ones with
  `grep -n "os.environ\[\|env(\|env\.\(str\|bool\|list\|db\|int\)(" config/settings/*.py config/env.py` (a
  read with no default) and ask for anything you can't give a harmless dummy. `api` from `args`, else
  `drf_spectacular` in `INSTALLED_APPS` → `drf`, `ninja` → `ninja` (its `NinjaAPI` instance path → `<ninja-api>`;
  scaffold: `config.api.api`), else `none`.
- **`database`** — from `args`, else FastAPI: `asyncpg` in `[project].dependencies` → `postgresql`, `aiosqlite` there
  (not only in the `dev` group, where the PostgreSQL shape keeps it for the fast tests) → `sqlite`, no `alembic.ini`
  and no SQL driver → `none`; Django: `psycopg` in `[project].dependencies` → `postgresql`, else `sqlite` (Django has
  no `none`). PostgreSQL image `postgres:18` (the docs' compose and CI image — irurueta docs:
  web/django/pytest-factories-and-browser-tests.adoc).
- **Integration tier** — present only with `database: postgresql` (`tests/integration/` exists). The `sqlite`/`none`
  shapes keep the `integration` marker declared but have no such tests: `pytest -m integration` collects nothing and
  exits **5**, so those variants never get the `integration` job (see the template-selection table).
- **Container** — a root `Dockerfile` (+ `compose.yaml`/`docker-compose.yml`); without one, `distribution`
  `internal`/`store` has nothing to push: recommend running the scaffold skill first, or ask **Stop** / **Continue
  with `distribution: none`**.
- **Docs** — `docs/antora.yml` + `docs/antora-playbook.yml` + `docs/package-lock.json` (`iru-setup-antora`); missing
  → recommend running it first. Sphinx only when `docs/api/conf.py` exists — never add one here (the scaffold owns it).
- **Sonar** — `sonar-project.properties`; note whether it sets `sonar.python.ruff.reportPaths` (gates the Ruff report
  step).
- **Branches** — confirm against `git branch -a` (or ask); `sync.yml` needs both.
- **README/Antora wording** for `sync_versions.py` — `grep -n -i "current development version\|latest release"
  README.md`; note deviations from the default row labels.

**Cost-aware choices** (only those still unresolved, in this order, `AskUserQuestion`; prices per GitHub's/
SonarSource's current pricing — tell the user to double-check their plan):

1. **`visibility`** — `gh repo view --json visibility -q .visibility` (lowercased) when there's a GitHub remote;
   otherwise ask **Public** / **Private** (Public recommended when open source). Open source + private is
   contradictory — say so. `internal` = `private`. Public repositories run standard runners free; private ones
   consume included minutes (2,000/month Free, 3,000 Pro/Team, 50,000 Enterprise Cloud), then ~$0.006/min Linux.
   Everything here is Linux; the Python matrix multiplies the test job, and the PostgreSQL service / testcontainers
   jobs are the expensive part.
2. **`sonar`** — "Configure SonarCloud / SonarQube and send CI analysis and coverage reports to it?" — **SonarCloud**
   only for a public open-source repository; otherwise **None** recommended, **self-hosted** second.
3. **`ci-tests`** — **Unit only** (`unit`; recommended for private) — "fast suites only (pytest on SQLite in-memory,
   `-m "not integration"`), one Python version: no testcontainers; the migration checks still run".
   **Full** (`full`; recommended for public) — "also the integration job (the `integration` marker against a real
   PostgreSQL started by testcontainers — `database: postgresql` only) and, on a public repository, the fast tests
   across `<python-matrix>` — complete verification, more minutes". With `database: sqlite`/`none` say `full` only
   adds the matrix (public) — there is no integration tier.
4. **`pages`** — public: `yes` without asking. Private: **No (Recommended)** — "docs still built, uploaded as an
   artifact" — vs **Yes** — "needs Pro/Team/Enterprise Cloud; the site is public unless Enterprise Cloud private
   Pages".
5. **`distribution`** — **none** (no `release.yml`; the GitHub Release/tag is the release) / **internal** (sdist +
   wheel on the release, image to GHCR as a **private** package — free for public repositories, storage/transfer
   quotas for private ones) / **store** (same, image made **public** — anyone can `docker pull` it; only sensible
   for an open-source project). Default `store` for open source, else `internal` when a `Dockerfile` exists, else
   `none`.

## Step 2 — Announce scratch vs update, decide per existing file

Check `build.yml`, `release.yml`, `sync.yml` + its two scripts (one unit — partial if not all exist),
`security.yml`, `.github/dependabot.yml`. None → "creating the CI/CD pipeline **from scratch**". Any → "**updating an
existing CI/CD setup**", list each as present/absent/partial, read each existing one, and name every concrete
contradiction with this run's choices ("`build.yml` has an integration job but `ci-tests: unit`", "it deploys to
Pages but `pages: no`", "it has a Sonar job but `sonar: none`", "there's a `release.yml` but `distribution: none`",
"it installs with `pip install -r requirements.txt` but the project has a `uv.lock`", "it runs `python -m build`
where this skill uses `uv build`"). Unless `on-existing` decides, ask per unit (`AskUserQuestion`, ≤ 4 per call):

- **Update (Recommended)** — merge: add/correct what this skill owns (jobs, gating, action versions, commands), keep
  every other step/job/entry; diff shown before writing.
- **Keep as is** — untouched; mismatches listed in Step 7.
- **Replace** — regenerate from the template; customizations lost (git history keeps them).
- **Stop** (first question only) — end without changing anything.

With `distribution: none`, an existing `release.yml` is offered for removal (ask; never delete silently).

## Step 3 — Templates

Resolve every `<placeholder>` from Step 1. Comments marked `# fastapi`, `# django`, `# drf`, `# ninja`,
`# ci-tests: full`, `# pages: yes|no`, `# sonar`, `# ruff-report`, `# sphinx`, `# openapi`, `# image`, `# postgresql`,
`# database: sqlite`, `# matrix` are gates: keep what applies and **drop the rest together with these guidance comments** — a step that
can never run is dead YAML.

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

env:
  # uv: fail instead of silently re-resolving when uv.lock is stale; colour in logs.
  UV_LOCKED: '1'
  FORCE_COLOR: '1'

jobs:
  quality:
    name: Lint, format, types and framework checks
    runs-on: ubuntu-latest
    env:
      DJANGO_SETTINGS_MODULE: config.settings.test     # django
    steps:
      - name: Check out code
        uses: actions/checkout@v7

      - name: Set up uv and Python <python-version>
        uses: astral-sh/setup-uv@v10.3.0
        with:
          python-version: '<python-version>'
          enable-cache: true

      # --locked: the job fails when uv.lock no longer matches pyproject.toml.
      - name: Install the project and the dev group
        run: uv sync --locked

      - name: Lint (Ruff)
        run: uv run ruff check .

      - name: Formatting (Ruff)
        run: uv run ruff format --check .

      - name: Type check (mypy)
        run: uv run mypy .

      # django — system checks and "every model change has a migration" (no database needed).
      - name: Django system checks
        run: uv run python manage.py check
      - name: Missing migrations
        run: uv run python manage.py makemigrations --check --dry-run

      # drf — the schema must generate without warnings (drf-spectacular).
      - name: Validate the OpenAPI schema
        run: |
          mkdir -p build
          uv run python manage.py spectacular --validate --fail-on-warn --file build/openapi.yaml
      # ninja — the schema must build (needs "ninja" in INSTALLED_APPS; the command doesn't create directories).
      - name: Export the OpenAPI schema (Django Ninja)
        run: |
          mkdir -p build
          uv run python manage.py export_openapi_schema --api <ninja-api> --output build/openapi.json

      # sonar + ruff-report — Ruff's JSON for Sonar's external-issue import (the gate itself is "Lint (Ruff)").
      - name: Ruff report for Sonar
        run: |
          mkdir -p build/reports
          uv run ruff check . --exit-zero --output-format json --output-file build/reports/ruff.json
      - name: Upload the Ruff report
        uses: actions/upload-artifact@v7
        with:
          name: ruff-report
          path: build/reports/ruff.json
          retention-days: 7

  tests:
    name: Tests (Python ${{ matrix.python }})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        # matrix — [ <python-matrix> ] only for ci-tests: full on a public repository; otherwise the single
        # primary version.
        python: [ '<python-version>' ]
    steps:
      - name: Check out code
        uses: actions/checkout@v7

      - name: Set up uv and Python ${{ matrix.python }}
        uses: astral-sh/setup-uv@v10.3.0
        with:
          python-version: ${{ matrix.python }}
          enable-cache: true

      - name: Install the project and the dev group
        run: uv sync --locked

      # Container-free tests only (SQLite in-memory, dependency overrides); writes build/coverage/coverage.xml
      # (Cobertura) and build/test-results/pytest.xml, and enforces [tool.coverage.report] fail_under (80).
      - name: Fast tests with coverage
        run: >-
          uv run pytest -m "not integration" --cov --cov-report=xml --cov-report=term-missing
          --junitxml=build/test-results/pytest.xml

      - name: Upload test and coverage reports
        if: ${{ always() && matrix.python == '<python-version>' }}
        uses: actions/upload-artifact@v7
        with:
          name: test-reports
          path: |
            build/coverage/
            build/test-results/
          retention-days: 7

  # fastapi with Alembic (database: postgresql | sqlite), or django. Real PostgreSQL as a service container
  # (postgresql); with database: sqlite drop `services:` and use the SQLite env lines below instead.
  migrations:
    name: Migration checks (PostgreSQL)
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres            # throwaway CI container, never a real credential
          POSTGRES_DB: app
        ports: [ '5432:5432' ]
        options: >-
          --health-cmd="pg_isready -U postgres" --health-interval=5s --health-timeout=5s --health-retries=20
    env:
      # fastapi — the only setting Alembic's env.py reads (DatabaseSettings, env_prefix APP_).
      <db-url-env>: postgresql+asyncpg://postgres:postgres@localhost:5432/app
      # django — production settings with CI dummies for every variable production.py requires (Step 1);
      # config/env.py reads POSTGRES_* (no DATABASE_URL). DB/USER default to <package>, so set them explicitly.
      DJANGO_SETTINGS_MODULE: config.settings.production
      DJANGO_ALLOWED_HOSTS: ci.example.com
      POSTGRES_HOST: localhost
      POSTGRES_PORT: '5432'
      POSTGRES_DB: app
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres            # the service container's throwaway password
    steps:
      - name: Check out code
        uses: actions/checkout@v7

      - name: Set up uv and Python <python-version>
        uses: astral-sh/setup-uv@v10.3.0
        with:
          python-version: '<python-version>'
          enable-cache: true

      - name: Install the project
        run: uv sync --locked

      # database: sqlite — the database file's directory must exist.
      - name: Create the SQLite directory
        run: mkdir -p build

      # fastapi — upgrade from an empty database, no drift between models and revisions, one head, and a full
      # downgrade/upgrade round trip (irurueta docs: backend/pyramid/sqlalchemy-transactions-and-migrations.adoc).
      - name: Apply every revision
        run: uv run alembic upgrade head
      - name: Models match the migrations
        run: uv run alembic check
      - name: Single head
        run: |
          heads="$(uv run alembic heads | grep -c '(head)' || true)"
          if [ "$heads" -gt 1 ]; then
            echo "::error::$heads Alembic heads — merge them (alembic merge heads) before releasing."
            exit 1
          fi
      - name: Downgrade/upgrade round trip
        run: |
          uv run alembic downgrade base
          uv run alembic upgrade head

      # django — no SECRET_KEY default exists outside local/test settings, so CI generates a masked one per run
      # (works on fork pull requests too, unlike a repository secret).
      # 64 random bytes, URL-safe: >= 50 characters, no django-insecure- prefix (security.W009).
      - name: Generate a throw-away DJANGO_SECRET_KEY
        run: |
          key="$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')"
          echo "::add-mask::$key"
          echo "DJANGO_SECRET_KEY=$key" >> "$GITHUB_ENV"
      - name: Deployment checks (production settings)
        run: uv run python manage.py check --deploy --fail-level WARNING
      - name: Apply the migrations
        run: uv run python manage.py migrate --noinput
      - name: No unapplied migrations
        run: uv run python manage.py migrate --check

  # image — only with distribution: internal | store (a Dockerfile exists). Builds the release image without pushing,
  # so a broken Dockerfile fails the pull request rather than the release; the GHA cache is shared with release.yml.
  image:
    name: Container image build check
    runs-on: ubuntu-latest
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v4
      - name: Build the image (not pushed)
        uses: docker/build-push-action@v7
        with:
          context: .
          push: false
          tags: <image-name>:ci
          cache-from: type=gha
          cache-to: type=gha,mode=max

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
          path: build
      # ruff-report only
      - name: Download the Ruff report
        uses: actions/download-artifact@v8
        with:
          name: ruff-report
          path: build/reports
      # Reads sonar-project.properties (sources, tests, coverage.xml, pytest*.xml, ruff.json paths).
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
    env:
      DJANGO_SETTINGS_MODULE: config.settings.test     # django (schema export)
    steps:
      - name: Check out code
        uses: actions/checkout@v7

      # sphinx | openapi
      - name: Set up uv and Python <python-version>
        uses: astral-sh/setup-uv@v10.3.0
        with:
          python-version: '<python-version>'
          enable-cache: true

      # sphinx — docs/api (autodoc + napoleon + sphinx-autodoc-typehints); -W turns every warning into a failure.
      - name: Build the API reference (Sphinx)
        run: uv run --group docs sphinx-build -W --keep-going -b html docs/api build/api-docs

      # openapi, fastapi — the app's OpenAPI document next to the reference.
      - name: Export the OpenAPI document
        run: |
          mkdir -p build/api-docs
          uv run python scripts/export_openapi.py build/api-docs/openapi.json
      # openapi, drf
      - name: Export the OpenAPI schema (drf-spectacular)
        run: |
          mkdir -p build/api-docs
          uv run python manage.py spectacular --validate --fail-on-warn --file build/api-docs/openapi.yaml
      # openapi, ninja — Ninja's own command (needs "ninja" in INSTALLED_APPS and the API mounted in urls.py).
      - name: Export the OpenAPI schema (Django Ninja)
        run: |
          mkdir -p build/api-docs
          uv run python manage.py export_openapi_schema --api <ninja-api> --output build/api-docs/openapi.json

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
          mkdir -p docs/build/site/api && cp -r build/api-docs/. docs/build/site/api/    # sphinx | openapi only

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

**`ci-tests: full` with `database: postgresql`** — append this job under `jobs:` (never for `sqlite`/`none`: those
shapes have no integration tests, and `pytest -m integration` would exit 5, "no tests collected"). It never counts towards the coverage gate (that's `tests`,
container-free tests only — the same rule the coding skills' group stage applies). Testcontainers finds the runner's
Docker engine itself (ubuntu-latest ships it; Ryuk cleans up), so there is no `services:` block and no `DOCKER_HOST`
tweak; the repository-wide `.integration-test.lock` the coding skills use is a local-machine concern and isn't needed
on a fresh runner:

```yaml
  integration:
    name: Integration tests (testcontainers)
    needs: tests
    runs-on: ubuntu-latest
    env:
      DJANGO_SETTINGS_MODULE: config.settings.test     # django — the suite's fixtures swap in the container's DB
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Set up uv and Python <python-version>
        uses: astral-sh/setup-uv@v10.3.0
        with:
          python-version: '<python-version>'
          enable-cache: true
      - name: Install the project and the dev group
        run: uv sync --locked
      - name: Integration tests
        run: uv run pytest -m integration --junitxml=build/test-results/pytest-integration.xml
      - name: Upload the integration report
        if: ${{ always() }}
        uses: actions/upload-artifact@v7
        with:
          name: integration-report
          path: build/test-results/pytest-integration.xml
          retention-days: 7
```

Gating summary for `build.yml` — template selection per scaffold variant (`database` × `api`; the rows are what
`iru-setup-python-fastapi`/`-django` actually generate):

| Variant | `quality` extras | `migrations` job | `integration` job (`ci-tests: full`) | `docs` API steps |
|---|---|---|---|---|
| FastAPI, `postgresql` | — | PostgreSQL service; `APP_DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/app`; the four Alembic steps | yes | Sphinx + `export_openapi.py` → `build/api-docs/openapi.json` |
| FastAPI, `sqlite` | — | no `services:`; `APP_DATABASE_URL: sqlite+aiosqlite:///./build/ci.sqlite3`; "Create the SQLite directory" + the four Alembic steps (the scaffold's `env.py` already sets `render_as_batch` on SQLite) | **no** (exit 5) | same |
| FastAPI, `none` | — | **no job** (no Alembic) | **no** (exit 5) | same |
| Django, `postgresql`, `drf` | `manage.py check`, `makemigrations --check --dry-run`, `spectacular --validate --fail-on-warn` | PostgreSQL service; the `DJANGO_*` + `POSTGRES_*` lines; the four Django steps | yes | Sphinx + `spectacular … --file build/api-docs/openapi.yaml` |
| Django, `postgresql`, `ninja` | `check`, `makemigrations --check`, Ninja `export_openapi_schema --api config.api.api` | same | yes | Sphinx + `export_openapi_schema … --output build/api-docs/openapi.json` |
| Django, `sqlite`, any `api` | as the row for its `api` (`none` → only `check` + `makemigrations --check`) | no `services:`; replace the four `POSTGRES_*` lines with `DJANGO_SQLITE_PATH: build/ci.sqlite3`; "Create the SQLite directory" + the four Django steps | **no** (exit 5) | Sphinx (+ the `api`'s export; none for `api: none`) |

Name the job honestly ("Migration checks (SQLite)" without the service). Then:

- **Flavor** — drop every `# django`/`# drf`/`# ninja` step and the `DJANGO_SETTINGS_MODULE` lines for FastAPI; drop
  the four Alembic steps and the `<db-url-env>` line for Django; "Create the SQLite directory" only for `sqlite`.
- **`api`** (Django) — `drf` keeps "Validate the OpenAPI schema" + "Export the OpenAPI schema (drf-spectacular)";
  `ninja` keeps both "Export the OpenAPI schema (Django Ninja)" steps (`<ninja-api>` = `config.api.api` for the
  scaffold); `none` keeps neither — no schema step at all.
- **Type checker** — `[tool.pyright]` instead of mypy → `uv run pyright`; neither → drop the step (open gap).
- **Matrix** — `ci-tests: full` **and** `visibility: public` → `python: [ <python-matrix> ]`; otherwise the single
  `'<python-version>'` entry. The reports are uploaded from the `<python-version>` entry only.
- **`sonar: none`** — drop the `sonar` job and both Ruff-report steps; `SONAR_HOST_URL` only for self-hosted. With
  `sonar` ≠ `none` the Ruff-report steps (and their download in the `sonar` job) **stay**: both scaffolds'
  `sonar-project.properties` set `sonar.python.ruff.reportPaths=build/reports/ruff.json`, so the `quality` job must
  write that file. Only a non-scaffold properties file without that key drops them — add the key when updating
  Sonar config is in scope, else drop the steps and report it.
- **`image`** — only with `distribution: internal | store` and a root `Dockerfile` (both scaffolds always write one;
  its last stage is the runtime image, so no `target:` is needed).
- **Docs** — Sphinx step only with `docs/api/conf.py`; FastAPI OpenAPI only with `scripts/export_openapi.py`; DRF/Ninja
  export per `api`; no API step at all → drop the uv setup and the `api/` merge line. Keep exactly one of "Upload
  Pages artifact"/"Upload documentation" and drop `deploy-docs` with `pages: no`; drop the whole `docs`/`deploy-docs`
  pair when there is no Antora site and no API docs (report it).
- **`ci-tests: full`** — append `integration` only with `database: postgresql` (an existing project whose
  `tests/integration/` holds tests on another backend counts too); otherwise say in Step 7 that `full` added only
  the matrix. If a non-scaffold project's integration job must stay generic, run it as
  `uv run pytest -m integration … || [ $? -eq 5 ]` and say why — never let exit 5 fail the build silently or
  pretend a tier ran.

### `release.yml` (not written with `distribution: none`)

```yaml
name: Release

on:
  release:
    types: [ released ]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  dist:
    name: Build the sdist and wheel
    runs-on: ubuntu-latest
    permissions:
      contents: write                          # gh release upload
    env:
      TAG: ${{ github.event.release.tag_name || github.ref_name }}
    steps:
      - name: Check out the released tag
        uses: actions/checkout@v7

      # A manual re-run must start from the release tag (Run workflow → "Use workflow from" → Tags).
      - name: Check the version matches the tag
        run: |
          if [ "$GITHUB_EVENT_NAME" = workflow_dispatch ] && [ "$GITHUB_REF_TYPE" != tag ]; then
            echo "::error::Run this workflow from a release tag, not a branch."
            exit 1
          fi
          VERSION="${TAG#v}"
          python3 .github/scripts/python_version.py --list | grep -E '^[^ ]+:[0-9]+: ' \
            | grep -v -F 'FastAPI(version=)' > "$RUNNER_TEMP/versions.txt"
          cat "$RUNNER_TEMP/versions.txt"
          if grep -v -F ": $VERSION " "$RUNNER_TEMP/versions.txt"; then
            echo "::error::Some version locations don't match the release tag $VERSION (iru-python-bump-version $VERSION fixes them)."
            exit 1
          fi

      - name: Set up uv
        uses: astral-sh/setup-uv@v10.3.0
        with:
          python-version: '<python-version>'

      # Fails if uv.lock still records the previous version of this project (uv lock wasn't run after the bump).
      - name: Check the lockfile
        run: uv lock --check

      # sdist + wheel into dist/, built in isolation from the tagged sources.
      - name: Build
        run: uv build --no-sources

      - name: Attach the distributions to the GitHub Release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: gh release upload "${TAG}" dist/* --clobber

  image:
    name: Build and push the container image
    needs: dist
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write                          # GHCR push with GITHUB_TOKEN
    steps:
      - name: Check out the released tag
        uses: actions/checkout@v7
      - name: Compute image coordinates
        id: image
        env:
          TAG: ${{ github.event.release.tag_name || github.ref_name }}
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
          images: ghcr.io/${{ steps.image.outputs.owner }}/<image-name>
          tags: |
            type=raw,value=${{ steps.image.outputs.version }}
            type=raw,value=latest
      - name: Build and push
        uses: docker/build-push-action@v7
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

Notes:

- **`internal` vs `store`** differ only in the GHCR package's visibility, which a workflow can't set (the
  `GITHUB_TOKEN` has no permission to change package settings): the first push creates the package as *private*;
  for `store`, Step 7 tells the user to make it public (package → Package settings → Change visibility) and to link
  it to the repository if `metadata-action`'s `org.opencontainers.image.source` label didn't.
- **No `[build-system]`** (uv virtual project) → drop the `dist` job, move "Check the version matches the tag" into
  `image` as its first step after the checkout, and drop `needs: dist`. VCS-derived dynamic versions (hatch-vcs,
  setuptools-scm) → drop the version check (`python_version.py` prints `version: dynamic …` and no location lines,
  which would fail the `grep`) and give the `dist` checkout `fetch-depth: 0` so the backend sees the tag.
- `uv build --no-sources` builds the way an index consumer would (ignoring `[tool.uv.sources]` overrides), as uv's
  docs recommend before publishing anything. The released commit was already tested by `build.yml` on
  `<stable-branch>`, so no tests run here.
- Configuration stays out of the image: database URLs, `SECRET_KEY`/`DJANGO_SECRET_KEY`, `APP_*` settings are runtime
  environment variables; migrations run as a one-shot job/compose service per release, never at container start
  (irurueta docs: backend/fastapi/deployment.adoc, web/django/deployment.adoc). Deploying the image is the user's own
  pipeline — list it as a follow-up in Step 7. No image is pushed per `<integration-branch>` push (a registry full of
  `.dev0` tags costs storage on private repositories); add one only if a deployment pipeline consumes it.
- `build-push-action` attaches its default minimal provenance attestation to a pushed image; add `provenance: mode=max`
  + `sbom: true` only if the consumer verifies attestations.

### `sync.yml`

```yaml
name: Sync

# After a release is published from <stable-branch>, open a pull request that merges it back into
# <integration-branch> and bumps the development version to the next X.(Y+1).0.dev0.
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
          if ! [[ "$RELEASE_VERSION" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
            echo "::error::Release tag '$RELEASE_VERSION' is not in X.Y.Z form; cannot compute the next .dev0 version."
            exit 1
          fi
          MAJOR="${BASH_REMATCH[1]}"
          NEXT_MINOR=$((BASH_REMATCH[2] + 1))
          {
            echo "release_version=$RELEASE_VERSION"
            echo "next_version=${MAJOR}.${NEXT_MINOR}.0.dev0"
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

      - name: Set up uv
        if: ${{ steps.guard.outputs.exists == 'false' }}
        uses: astral-sh/setup-uv@v10.3.0
        with:
          python-version: '<python-version>'

      # Same helper iru-python-bump-version uses: rewrites pyproject.toml, __version__ literals, a Django settings
      # VERSION and a FastAPI(version=) that tracks the package; refuses if they disagree.
      - name: Bump the development version
        if: ${{ steps.guard.outputs.exists == 'false' }}
        run: python3 .github/scripts/python_version.py "${{ steps.versions.outputs.next_version }}"

      # uv.lock records this project's own version; without this, uv sync --locked fails on the sync branch.
      - name: Refresh uv.lock
        if: ${{ steps.guard.outputs.exists == 'false' }}
        run: uv lock

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

The bump is always minor (`1.3.0` → `1.4.0.dev0`), matching `iru-python-bump-version`'s Step 5 and `iru-release`'s
default "next upcoming version"; flag it in Step 7 if the team releases patches from `<integration-branch>` too. Tags
that aren't plain `X.Y.Z` (`1.4.0rc1`) stop the job with an error instead of guessing. `CHANGELOG.md` isn't touched —
its release section arrives through the merge. `uv lock` keeps every other pin (it only re-resolves what changed — the
project's own version), so the sync PR's lockfile diff is one line. A VCS-derived dynamic version makes the bump step
a no-op (`version: dynamic …`) — then also drop "Refresh uv.lock". The runner's own `python3` (3.12 on
ubuntu-latest) runs both scripts; they need nothing beyond the standard library.

### `.github/scripts/python_version.py`

The exact helper embedded in `iru-python-bump-version`'s Step 1 (keep the two identical — the release workflow's
version check and `sync.yml` both rely on its `--list` output format `<file>:<line>: <value>    [<location>]`, its
`version: dynamic` short-circuit, and its refusal to write when locations disagree). Copy it from that skill's
current `SKILL.md` (the heredoc between `cat > "$TMPDIR/iru-python-bump-version/py_version.py" <<'PY'` and `PY`)
rather than retyping it; the copy below is the version this skill was verified with:

```python
import difflib, pathlib, re, subprocess, sys

args = sys.argv[1:]
dry, force, antora = "--dry-run" in args, "--force" in args, "--antora" in args
validate = "--validate" in args
args = [a for a in args if not a.startswith("--")]
new = args[0] if args else None          # None => --list
root = pathlib.Path(".")

# PEP 440 (the public-version pattern from the spec, verbose form) + canonical rendering.
PEP440 = re.compile(r"""^\s*v?(?:(?P<epoch>[0-9]+)!)?(?P<release>[0-9]+(?:\.[0-9]+)*)
    (?P<pre>[-_.]?(?P<pre_l>alpha|a|beta|b|preview|pre|c|rc)[-_.]?(?P<pre_n>[0-9]+)?)?
    (?P<post>(?:-(?P<post_n1>[0-9]+))|(?:[-_.]?(?P<post_l>post|rev|r)[-_.]?(?P<post_n2>[0-9]+)?))?
    (?P<dev>[-_.]?(?P<dev_l>dev)[-_.]?(?P<dev_n>[0-9]+)?)?
    (?:\+(?P<local>[a-z0-9]+(?:[-_.][a-z0-9]+)*))?\s*$""", re.X | re.I)


def canonical(v):
    m = PEP440.match(v)
    if not m:
        return None
    s = (m["epoch"] + "!" if m["epoch"] and int(m["epoch"]) else "") + ".".join(str(int(x)) for x in m["release"].split("."))
    if m["pre"]:
        lab = {"alpha": "a", "beta": "b", "c": "rc", "pre": "rc", "preview": "rc"}.get(m["pre_l"].lower(), m["pre_l"].lower())
        s += lab + str(int(m["pre_n"] or 0))
    if m["post"]:
        s += ".post" + str(int(m["post_n1"] or m["post_n2"] or 0))
    if m["dev"]:
        s += ".dev" + str(int(m["dev_n"] or 0))
    if m["local"]:
        s += "+" + ".".join(p if not p.isdigit() else str(int(p)) for p in re.split(r"[-_.]", m["local"].lower()))
    return s


if validate:
    c = canonical(new or "")
    if c is None:
        sys.exit(f"invalid: {new!r} is not a PEP 440 version")
    print(f"canonical: {c}")
    if c != new:
        print(f"WARNING: {new} is valid PEP 440 but not canonical — packaging tools will normalize it to {c}")
    if not re.fullmatch(r"\d+\.\d+\.\d+(\.dev\d+)?", c):
        print("WARNING: not in this catalog's X.Y.Z / X.Y.Z.devN convention")
    sys.exit(0)

is_release = new is not None and canonical(new) is not None and re.fullmatch(r"[0-9.]+", canonical(new)) is not None


def read(p):
    return p.read_text(encoding="utf-8")


def ignored(p):
    try:
        return subprocess.run(["git", "check-ignore", "-q", str(p)], capture_output=True).returncode == 0
    except FileNotFoundError:
        return False


def tables(text):
    """Map TOML table name -> (start, end) offsets of its body (regex-based; no tomllib needed on Python < 3.11)."""
    heads = [(m.group(1).strip(), m.start(), m.end()) for m in re.finditer(r"(?m)^[ \t]*\[\[?([^\[\]\n]+)\]\]?[ \t]*(?:#.*)?$", text)]
    out = {}
    for i, (name, _, end) in enumerate(heads):
        out.setdefault(name, (end, heads[i + 1][1] if i + 1 < len(heads) else len(text)))
    return out


def key_in(text, span, key):
    rx = re.compile(r"(?m)^([ \t]*" + re.escape(key) + r"[ \t]*=[ \t]*)([\"'])([^\"'\n]*)(\2)")
    return [m for m in rx.finditer(text, *span)] if span else []


VERSION_ASSIGN = re.compile(r"""(?m)^(__version__[ \t]*(?::[ \t]*str[ \t]*)?=[ \t]*)(["'])([^"'\n]*)(\2)""")
SETTINGS_ASSIGN = re.compile(r"""(?m)^((?:APP_)?VERSION[ \t]*(?::[ \t]*str[ \t]*)?=[ \t]*)(["'])([^"'\n]*)(\2)""")
SETTINGS_ENV = re.compile(r"""(?m)^((?:APP_)?VERSION[ \t]*(?::[ \t]*str[ \t]*)?=[ \t]*(?:os\.environ\.get|os\.getenv|env\.str|env)\([ \t]*["'](?:APP_)?VERSION["'][ \t]*,[ \t]*(?:default[ \t]*=[ \t]*)?)(["'])([^"'\n]*)(\2)""")
FASTAPI_CTOR = re.compile(r"""(FastAPI\((?:[^()]|\([^()]*\))*?\bversion[ \t]*=[ \t]*)(["'])([^"'\n]*)(\2)""", re.S)
SKIP = {".venv", "venv", ".git", "node_modules", "build", "dist", "docs", "tests", "test", "migrations", ".tox", ".nox", "site-packages"}


def walk(globs):
    seen = []
    for g in globs:
        for p in sorted(root.glob(g)):
            if p.is_file() and not (set(p.parts) & SKIP) and p not in seen and not ignored(p):
                seen.append(p)
    return seen


locs = []      # (path, regex, kind, role) role: primary|mirror|conditional|antora
notes = []
pp = root / "pyproject.toml"
text = read(pp) if pp.exists() else ""
tb = tables(text)
name = None
if "project" in tb:
    n = key_in(text, tb["project"], "name")
    name = n[0].group(3) if n else None

dynamic = False
if "project" in tb:
    d = re.search(r"(?ms)^[ \t]*dynamic[ \t]*=[ \t]*\[(.*?)\]", text[tb["project"][0]:tb["project"][1]])
    dynamic = bool(d and re.search(r"[\"']version[\"']", d.group(1)))
backend = ""
if "build-system" in tb:
    b = key_in(text, tb["build-system"], "build-backend")
    backend = b[0].group(3) if b else ""
requires = text[tb["build-system"][0]:tb["build-system"][1]] if "build-system" in tb else ""


def module_file(dotted):
    parts = dotted.split(".")
    for base in (root / "src", root):
        for cand in (base.joinpath(*parts).with_suffix(".py"), base.joinpath(*parts, "__init__.py")):
            if cand.exists():
                return cand
    return None


def stop_vcs(why):
    print(f"version: dynamic — {why}; the version is derived from git tags, nothing to change")
    sys.exit(0)


if dynamic:
    hv = tb.get("tool.hatch.version")
    sd = tb.get("tool.setuptools.dynamic")
    pv = tb.get("tool.pdm.version")
    if hv and key_in(text, hv, "source") and key_in(text, hv, "source")[0].group(3) == "vcs":
        stop_vcs("[tool.hatch.version] source = \"vcs\" (hatch-vcs)")
    if pv and key_in(text, pv, "source") and key_in(text, pv, "source")[0].group(3) == "scm":
        stop_vcs("[tool.pdm.version] source = \"scm\"")
    if re.search(r"setuptools[-_]scm|hatch-vcs|versioningit|dynamic-versioning|uv-dynamic-versioning", requires + text, re.I) \
            or "tool.setuptools_scm" in tb:
        stop_vcs("a VCS versioning plugin (setuptools-scm / hatch-vcs / versioningit / *-dynamic-versioning) is configured")
    target = None
    if hv and key_in(text, hv, "path"):
        target = root / key_in(text, hv, "path")[0].group(3)
    elif pv and key_in(text, pv, "path"):
        target = root / key_in(text, pv, "path")[0].group(3)
    elif sd:
        body = text[sd[0]:sd[1]]
        a = re.search(r"""version[ \t]*=[ \t]*\{[^}]*attr[ \t]*=[ \t]*["']([^"']+)["']""", body)
        f = re.search(r"""version[ \t]*=[ \t]*\{[^}]*file[ \t]*=[ \t]*\[?[ \t]*["']([^"']+)["']""", body)
        if a:
            mod, _, attr = a.group(1).rpartition(".")
            target = module_file(mod)
            if attr != "__version__":
                notes.append(f"attr {a.group(1)}: only __version__ literals are rewritten — check {attr} by hand")
        elif f:
            vf = root / f.group(1)
            locs.append((vf, re.compile(r"\A()()([^\s]+)()"), "VERSION file (setuptools dynamic file)", "primary"))
    elif "flit" in backend and name:
        target = module_file(re.sub(r"[-.]+", "_", name).lower())
    if target is not None:
        if not target.exists():
            sys.exit(f"dynamic version points at {target.as_posix()}, which does not exist")
        locs.append((target, VERSION_ASSIGN, "__version__ (dynamic source)", "primary"))
    if not locs:
        sys.exit("dynamic version with an unrecognized source — explain to the user and stop; nothing was changed")
else:
    if "project" in tb and key_in(text, tb["project"], "version"):
        locs.append((pp, None, "[project].version", "primary"))

if "tool.poetry" in tb and key_in(text, tb["tool.poetry"], "version"):
    locs.append((pp, None, "[tool.poetry].version", "primary"))

cfg = root / "setup.cfg"
if cfg.exists():
    m = re.search(r"(?ms)^\[metadata\][^\[]*?^(version[ \t]*=[ \t]*)()([^\s]+)()", read(cfg))
    if m and not m.group(3).startswith(("attr:", "file:")):
        locs.append((cfg, re.compile(r"(?ms)(^\[metadata\][^\[]*?^version[ \t]*=[ \t]*)()([^\s]+)()"), "setup.cfg [metadata] version", "primary"))
spy = root / "setup.py"
if spy.exists() and re.search(r"""\bversion[ \t]*=[ \t]*["'][^"']+["']""", read(spy)):
    locs.append((spy, re.compile(r"""(\bversion[ \t]*=[ \t]*)(["'])([^"'\n]+)(\2)"""), "setup.py version=", "primary"))

dyn_targets = {l[0] for l in locs if l[2].startswith("__version__")}
for p in walk(["src/*/__init__.py", "src/*/_version.py", "src/*/__about__.py", "src/*/version.py",
               "*/__init__.py", "*/_version.py", "*/__about__.py", "*/version.py"]):
    t = read(p)
    if p not in dyn_targets and VERSION_ASSIGN.search(t):
        locs.append((p, VERSION_ASSIGN, "__version__ literal", "primary"))
    elif p not in dyn_targets and re.search(r"(?m)^__version__\s*=", t):
        notes.append(f"{p.as_posix()}: __version__ is computed (e.g. importlib.metadata.version()) — follows pyproject, untouched")
for p in walk(["*/settings.py", "*/settings/*.py", "*/*/settings.py", "*/*/settings/*.py"]):
    t = read(p)
    if SETTINGS_ENV.search(t):
        locs.append((p, SETTINGS_ENV, "settings VERSION env default", "primary"))
    elif SETTINGS_ASSIGN.search(t):
        locs.append((p, SETTINGS_ASSIGN, "settings VERSION literal", "primary"))
for p in walk(["app/*.py", "src/*/*.py", "src/*/*/*.py", "*/main.py"]):
    if FASTAPI_CTOR.search(read(p)):
        locs.append((p, FASTAPI_CTOR, "FastAPI(version=) literal — written only when it equals the package version", "conditional"))
ay = root / "docs" / "antora.yml"
if antora and ay.exists():
    locs.append((ay, re.compile(r"(?m)^(version:[ \t]*)(['\"]?)([^\s'\"#]+)(\2)"), "docs/antora.yml version (release versions only)", "antora"))

if not locs:
    sys.exit("No version location found (no [project].version, [tool.poetry].version, __version__ literal, setup.cfg/setup.py version)")

found, new_texts = [], {}
for path, rx, label, role in locs:
    t = new_texts.get(path, read(path))
    if rx is None:      # pyproject table keys
        span = tables(t)["project" if label.startswith("[project]") else "tool.poetry"]
        hits = key_in(t, span, "version")[:1]
    else:
        hits = list(rx.finditer(t))[:1]
    for m in hits:
        found.append([path.as_posix(), t.count("\n", 0, m.start(3)) + 1, m.group(3), label, role, path, m])
for f in found:
    print(f"{f[0]}:{f[1]}: {f[2]}    [{f[3]}]")
for n in notes:
    print(f"note: {n}")
primary = [f for f in found if f[4] == "primary"]
if not primary:
    sys.exit("No primary version location found — only mirrors/conditional ones")
values = {f[2] for f in primary}
current = primary[0][2]
print(f"current: {current}")
if len(values) > 1:
    print(f"WARNING: version locations disagree: {sorted(values)}", file=sys.stderr)
    if new is not None and not force:
        sys.exit("Refusing to write: confirm with the user, then re-run with --force to align every location")
if new is None:
    sys.exit(0)

for f in sorted(found, key=lambda f: -f[6].start()):  # rewrite back to front per file
    path, m, role = f[5], f[6], f[4]
    if role == "conditional" and f[2] != current:
        print(f"note: {f[0]}:{f[1]} FastAPI version {f[2]} differs from the package version — left alone (separate API version)")
        continue
    if role == "antora" and (not is_release or f[2] in ("~", "true", "false", "")):
        print(f"note: {f[0]} version left at {f[2]} (Antora's component version names releases only)")
        continue
    t = new_texts.get(path, read(path))
    new_texts[path] = t[:m.start(3)] + new + t[m.end(3):]
for path, t in new_texts.items():
    old = read(path)
    if t == old:
        continue
    if dry:
        sys.stdout.writelines(difflib.unified_diff(old.splitlines(True), t.splitlines(True), str(path), str(path)))
    else:
        path.write_text(t, encoding="utf-8")
        print(f"updated {path.as_posix()}")
lock = root / "uv.lock"
if lock.exists() and name and re.search(r'(?m)^name = "' + re.escape(re.sub(r"[-_.]+", "-", name).lower()) + r'"\nversion = ', read(lock)):
    print("next: uv lock   (refreshes this project's own version entry in uv.lock)")
```

### `.github/scripts/sync_versions.py`

```python
#!/usr/bin/env python3
"""Rewrites README/Antora version references after a release, for the Sync workflow.

Reads RELEASE_VERSION and NEXT_VERSION from the environment. The project's own version locations (pyproject.toml,
__version__ literals, a Django settings VERSION, a FastAPI(version=) tracking the package) are bumped by
python_version.py in the step before, and uv.lock by `uv lock`; this script only handles the README's version table
and the Antora component version. CHANGELOG.md is left alone: its release section arrives through the merge that
precedes this script.
"""
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def update_readme(release_version, next_version):
    path = REPO_ROOT / "README.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    # Adjust these row labels if this repository's README words them differently (Step 1's survey).
    text = re.sub(r"(\| Current development version \| `)[^`]*(` \|)", rf"\g<1>{next_version}\g<2>", text)
    text = re.sub(r"(\| Latest release[^|]*\| `)[^`]*(` \|)", rf"\g<1>{release_version}\g<2>", text)
    path.write_text(text, encoding="utf-8")


def update_antora_component_version(release_version):
    path = REPO_ROOT / "docs" / "antora.yml"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(r"(?m)^version:.*$", f"version: {release_version}", text, count=1)
    if count == 1:
        path.write_text(updated, encoding="utf-8")


def main():
    release_version = os.environ["RELEASE_VERSION"]
    next_version = os.environ["NEXT_VERSION"]
    update_readme(release_version, next_version)
    update_antora_component_version(release_version)


if __name__ == "__main__":
    main()
```

### `security.yml`

The shared security block every workflows skill in this catalog embeds — dependency review, CodeQL, OSV-Scanner,
gitleaks, identical in shape to the other stacks — with CodeQL's `python` extractor (no build needed:
`build-mode: none`) next to `actions`, plus this stack's addition, **pip-audit** over the exported lock (the Python
Packaging Advisory Database / OSV, the auditor the author's docs put in CI — irurueta docs:
backend/flask/security-considerations.adoc, backend/fastapi/property-based-and-load-testing.adoc). Bandit's rules
already run in `build.yml` as Ruff's `S` rules (the scaffold selects them); a separate `bandit` step is only added
when the project configures `[tool.bandit]` itself. Drop a job's whole entry when its `security-*` flag is `no`; if all
are `no`, don't write the file (say so in Step 7).

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
        language: [ actions, python ]
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

  # Python dependency audit: every locked package (dev and docs groups too — they run in CI) against PyPA/OSV
  # advisories. --disable-pip audits the hashed, exported pins as they are, without resolving or installing anything.
  pip-audit:
    name: Python dependency audit (pip-audit)
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: Check out code
        uses: actions/checkout@v7
      - name: Set up uv
        uses: astral-sh/setup-uv@v10.3.0
        with:
          python-version: '<python-version>'
      - name: Export the locked dependencies
        run: |
          mkdir -p build
          uv export --frozen --all-groups --no-emit-project --format requirements-txt \
            --output-file build/requirements-audit.txt
      - name: Audit
        run: uvx pip-audit@2.10.1 --disable-pip --strict --requirement build/requirements-audit.txt

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

`security-codeql: no` drops `codeql`; `security-pip-audit: no` drops `pip-audit`. OSV-Scanner reads `uv.lock` (and
`docs/package-lock.json`) directly — no setup. pip-audit and OSV-Scanner overlap on purpose: pip-audit fails the
workflow on any advisory (a red check on the PR), OSV-Scanner reports into Code scanning. Without a `uv.lock` (pip
projects) the export step becomes `cp requirements.txt build/requirements-audit.txt` and `--disable-pip` needs
hashed requirements — otherwise drop it (pip-audit then resolves in a throwaway venv). `pip-audit@2.10.1` is pinned
(the version verified here); re-check it with `uvx pip-audit --version` when updating the pipeline, since Dependabot
doesn't see versions inside `run:` lines.

### `.github/dependabot.yml` (always written — no opt-out)

```yaml
version: 2
updates:
  # uv when uv.lock exists; pip for requirements*.txt / Poetry projects.
  - package-ecosystem: uv
    directory: /
    schedule:
      interval: weekly
    groups:
      python-dependencies:
        patterns: [ "*" ]

  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    groups:
      github-actions-dependencies:
        patterns: [ "*" ]

  # Only when a root Dockerfile exists — the python:3.x-slim base and the ghcr.io/astral-sh/uv image.
  - package-ecosystem: docker
    directory: /
    schedule:
      interval: weekly

  # Only when compose.yaml / docker-compose.yml exists — the postgres image of the local stack.
  - package-ecosystem: docker-compose
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

Dependabot's `uv` ecosystem updates `pyproject.toml` constraints and `uv.lock` together and respects
`requires-python`. Base-image bumps across a Python minor (`3.13-slim` → `3.14-slim`) arrive as normal PRs — merge them
only together with `python-version`/`.python-version`. When updating an existing `dependabot.yml`, keep entries for
ecosystems this skill doesn't manage.

## Step 4 — Fill and gate

Substitute every placeholder from Step 1, apply every gate above, and strip the guidance comments. Never invent a
value: an unresolved fact (no `integration` marker, no Antora playbook, no Sonar project key, no `Dockerfile` for
`internal`/`store`, a production-settings variable without an obvious dummy) is either asked or reported as an open gap
in Step 7. The Django `migrations` env block in the template **is** `<django-prod-env>` for the scaffold's
PostgreSQL shape; for `database: sqlite` it becomes

```yaml
      DJANGO_SETTINGS_MODULE: config.settings.production
      DJANGO_ALLOWED_HOSTS: ci.example.com
      DJANGO_SQLITE_PATH: build/ci.sqlite3
```

and for a non-scaffold project it is whatever Step 1's survey found — one `NAME: value` line per required variable,
never `DATABASE_URL` unless the settings really read it, and never `DJANGO_SECRET_KEY` (generated by its own step).
Also:

- **`sonar-project.properties`** missing with `sonar` ≠ `none` → ask for the organization/project key (and host URL
  for self-hosted) and write the flavor scaffold's own template (`iru-setup-python-fastapi`/`-django` own it); both
  read `sonar.python.version`, `sonar.python.coverage.reportPaths=build/coverage/coverage.xml`,
  `sonar.python.xunit.reportPath=build/test-results/pytest*.xml` (and optionally
  `sonar.python.ruff.reportPaths=build/reports/ruff.json`).
- `.github/scripts/python_version.py` is written whenever `sync.yml` or `release.yml` is (both use it), together with
  `sync_versions.py` for `sync.yml`; `chmod +x` both scripts.

## Step 5 — Validate

- Run `actionlint` on every generated workflow — `actionlint` if installed, else
  `docker run --rm -v "$PWD":/repo -w /repo rhysd/actionlint:latest -color` — and fix every finding (shellcheck
  findings in `run:` blocks included). Parse `.github/dependabot.yml` with
  `python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" .github/dependabot.yml` (PyYAML reads the
  workflows' `on:` key as `True` — a YAML 1.1 quirk, not an error).
- Run the commands the workflows contain locally first, through `iru-gate-runner` agents (compact results):
  `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .` (`iru-python-code-quality`),
  the fast tests with coverage (`iru-python-test` / `iru-python-coverage`), Django's `manage.py check` +
  `makemigrations --check --dry-run` (+ `spectacular --validate --fail-on-warn` for DRF, `export_openapi_schema` for
  Ninja — `mkdir -p` its output directory first), the Sphinx build
  (`iru-python-docstrings`), `uv build`, the pip-audit export + audit, and `python3 .github/scripts/python_version.py
  --list` (every location must agree and follow the `.dev0` convention). With Docker available, also the `migrations`
  job's commands, with exactly the job's `env:` values, against `docker run --rm -d -e POSTGRES_USER=postgres -e
  POSTGRES_PASSWORD=postgres -e POSTGRES_DB=app -p 5432:5432 postgres:18` (SQLite variants need no container) and,
  with `ci-tests: full` + `database: postgresql`, `iru-python-test integration`; Docker unavailable → those jobs are
  **unverified**, not failed. A workflow whose commands were never run is a guess.
- Never trigger `release.yml` or `sync.yml` for real as a test. Recommend a throwaway pre-release on a fork, or
  review of the first real release run.

## Step 6 — Write the files

Write (or, per Step 2, update/replace — and skip kept units) the workflows, the two scripts (only together with
`sync.yml`/`release.yml` as above), `security.yml`, and `.github/dependabot.yml`. With `distribution: none`, write no
`release.yml`.

## Step 7 — Report: secrets, settings, choices, warnings

Required secrets (Settings → Secrets and variables → Actions) — list only the rows that apply:

| Secret | Purpose | Needed when |
|---|---|---|
| `SONAR_TOKEN` | SonarCloud/SonarQube token for the scan | `sonar` is `cloud` or `self-hosted` (cloud on a private repository also needs a paid SonarCloud plan) |

`GITHUB_TOKEN` needs no setup and covers the release uploads, GHCR, Pages, Sync and every `security.yml` job (gitleaks
needs `GITLEAKS_LICENSE` only for organization accounts on its paid tier — mention it). No database password,
`DJANGO_SECRET_KEY` or `APP_*` secret is needed: CI uses throwaway service containers and a per-run generated key.
Repository settings to check:

- **Settings → Actions → General → Workflow permissions** must allow GitHub Actions to create pull requests, or
  `sync.yml` fails on `gh pr create` despite its `permissions:` block.
- **Pages** (`pages: yes`): Source = **GitHub Actions**. Private repositories need Pro/Team/Enterprise Cloud, and the
  site is public unless Enterprise Cloud private Pages.
- **Code scanning** must be enabled for the CodeQL and OSV-Scanner SARIF uploads; **Dependency graph** for dependency
  review (on by default for public repositories).
- **GHCR** (`internal`/`store`): the first push creates the package as *private*; for `store` change its visibility to
  public, and link it to the repository if needed.

Then summarize: scratch vs update and, per unit, **created / updated / replaced / kept as is** (with mismatches) or
stopped; flavor, `<image-name>`, primary Python and matrix (and where they came from); `visibility` (and its source)
with the minutes note for private repositories; `ci-tests` (and for `full`, whether the matrix applies); the
`migrations` job's shape (Alembic / Django, PostgreSQL / SQLite) or why it was omitted (FastAPI `database: none`);
whether the `integration` job was added (`ci-tests: full` + `database: postgresql`) or why not; `pages`; `sonar` (+ keys) or
why omitted; `distribution` (or why `release.yml` wasn't written); which security jobs were included; and every open
gap (missing contract tooling, no Antora setup, no `Dockerfile`, README wording `sync_versions.py` won't match, patch
releases the minor-bump default doesn't handle, a production-settings variable that needed a guessed dummy, the
SHA-pinning hardening option).

Warn explicitly: **review every workflow before pushing it.** Branch names, versions, image coordinates and the
production-settings dummies were inferred from this repository and may need correcting; `release.yml` publishes to
GitHub Releases and GHCR, and `sync.yml` pushes branches and opens pull requests, so verify both against the first real
release. Nothing in these files contains a credential, and it must stay that way.

## Sources

- irurueta docs: web/django/pytest-factories-and-browser-tests.adoc — the GitHub Actions job (postgres:18 service with
  `pg_isready`, generated masked `DJANGO_SECRET_KEY`, `manage.py check`, `makemigrations --check --dry-run`, pytest
  with coverage XML).
- irurueta docs: web/django/settings-and-configuration.adoc, web/django/deployment.adoc — `check --deploy
  --fail-level WARNING` against the production settings, `migrate --check`, no default `SECRET_KEY`, migrations once
  per release.
- irurueta docs: web/django/django-rest-framework.adoc — `spectacular --validate --fail-on-warn` in CI.
- irurueta docs: backend/pyramid/sqlalchemy-transactions-and-migrations.adoc, backend/flask/database-migrations.adoc —
  `alembic check`, single head, upgrade/downgrade round trip in CI; migrations once per release as a one-shot job;
  backend/fastapi/sql-databases-with-sqlmodel.adoc — Alembic with SQLModel's metadata.
- irurueta docs: backend/fastapi/testing.adoc, backend/fastapi/deployment.adoc — pytest with a coverage threshold,
  warnings as errors, a DB-backed tier against a real PostgreSQL, pinned FastAPI.
- irurueta docs: backend/docker/ci-cd-with-github-actions.adoc, backend/flask/docker-and-kubernetes.adoc — image job
  after tests, Buildx + `type=gha` cache, `docker/metadata-action`, push only outside pull requests;
  backend/fastapi/docker-and-kubernetes.adoc, web/django/docker-and-kubernetes.adoc — the multi-stage uv image the
  release builds;
  backend/flask/cloud-platforms-and-monitoring.adoc — pin third-party actions to a full commit SHA.
- irurueta docs: backend/flask/security-considerations.adoc, backend/fastapi/property-based-and-load-testing.adoc —
  `pip-audit` (and Bandit) on every commit; Dependabot/Renovate; base-image scanning.
- irurueta docs: programming-languages/python/virtual-environments-and-packaging.adoc — uv, committed `uv.lock`,
  `uv sync --locked`; Trusted Publishing as the route for libraries (not used here).
- `iru-setup-php-github-workflows` (pipeline shape, security block, sync scripts), `iru-setup-typescript-github-workflows`
  (NestJS/Next.js image build check and GHCR release), `iru-setup-android-github-workflows` (Antora + API docs under
  `api/`).

## Verification notes

Verified in `$TMPDIR/iru-verify/python/workflows/` (uv 0.12.8, CPython 3.13.15, Docker 29.8):

- **actionlint 1.7.12** (`rhysd/actionlint`, Docker, shellcheck active — a planted unquoted variable was reported) clean
  on every workflow rendered from these templates (a script extracts the YAML blocks above and applies the gates) for
  four variants — `fastapi` (PostgreSQL + Alembic `migrations`, `ci-tests: full` with the 3.12–3.14 matrix and the
  integration job, Sonar cloud with the Ruff report, Sphinx + OpenAPI, Pages, `store` release); `django` + DRF
  (PostgreSQL deploy/migrate checks, `unit`, no Sonar, `pages: no`, `internal` release); `django` + Ninja (SQLite
  `migrations` without a service, `full` on a private repository — no matrix, and since the reconciliation pass no integration job — self-hosted Sonar, no
  `release.yml`); `fastapi` without a database or `[build-system]` (no `migrations` job, image-only release with the
  version check moved into it) — `sync.yml` and `security.yml` included. Every `.github/dependabot.yml` variant
  validated against the SchemaStore Dependabot 2.0 schema (`check-jsonschema`), which lists the `uv` and
  `docker-compose` ecosystems.
- **Build-job command sequence**, run as written on a minimal FastAPI project shaped like the scaffold contract
  (layered `app/`, SQLModel, async engine, Alembic async template, `docs/api` Sphinx, `scripts/export_openapi.py`):
  `uv sync --locked`, `ruff check .`, `ruff format --check .`, `mypy .` (strict + `pydantic.mypy`), the fast pytest
  command (coverage XML at `build/coverage/coverage.xml`, JUnit at `build/test-results/pytest.xml`, the 80%
  `fail_under` enforced by pytest-cov), the integration command (a testcontainers `postgres:18` test passed), the
  Alembic steps against a `postgres:18` container (`upgrade head`, `check` → "No new upgrade operations detected",
  one `(head)`, `downgrade base` + `upgrade head`; an unmigrated model made `alembic check` fail as intended), the
  Sphinx build with `-W` under `UV_LOCKED=1`, the OpenAPI export, `uv lock --check`, `uv build --no-sources`, and the
  Ruff JSON report. The async Alembic template needs `sqlalchemy[asyncio]` (greenlet) in the dependencies — without it
  every Alembic step fails with "the greenlet library is required".
- **Django sequence** on a minimal split-settings project (`config/settings/{base,local,test,production}.py`, DRF +
  drf-spectacular, Django 6.1, psycopg 3): `manage.py check`, `makemigrations --check --dry-run` (and exit 1 after an
  unmigrated field), `spectacular --validate --fail-on-warn`, the fast pytest-django command, the secret-key one-liner,
  then with the production settings against `postgres:18`: `check --deploy --fail-level WARNING`, `migrate
  --noinput`, `migrate --check` (re-run against the real scaffolds, see the reconciliation bullet below). Django
  Ninja's schema command is
  `export_openapi_schema` (not `export_ninja_api_schema`) and, like drf-spectacular's `--file`, needs its output
  directory to exist — hence the `mkdir -p` in every export step.
- **Reconciliation with the scaffolds** (2026-10-14, `$TMPDIR/iru-verify/python/reconcile/`): the templates were
  re-rendered for five variants — FastAPI `postgresql` (`full`, public matrix, Sonar cloud, Pages, `store`), FastAPI
  `sqlite` (`full` → no integration job, SQLite `migrations`), Django DRF `postgresql` (`full`, Sonar cloud), Django
  Ninja `postgresql` (`unit`, self-hosted Sonar, `pages: no`, no `release.yml`), Django `api: none` + `sqlite`
  (`full` → no integration job) — and actionlint 1.7.12 was clean on every `build`/`release`/`sync`/`security.yml`.
  The jobs' commands ran, with exactly the jobs' `env:` values, on projects rendered by `iru-setup-python-django`
  (DRF, Ninja, none-sqlite) and `iru-setup-python-fastapi` (postgresql, sqlite, none): Django `check --deploy
  --fail-level WARNING` ("no issues"), `migrate --noinput`, `migrate --check` green on `postgres:18` with
  `DJANGO_ALLOWED_HOSTS` + `POSTGRES_HOST/PORT/DB/USER/PASSWORD` and a `secrets.token_urlsafe(64)` key, and on SQLite
  with `DJANGO_SQLITE_PATH=build/ci.sqlite3`; Ninja `export_openapi_schema --api config.api.api` and DRF
  `spectacular --validate --fail-on-warn` green; FastAPI's four Alembic steps green on `postgres:18`
  (`postgresql+asyncpg://…`) and on `sqlite+aiosqlite:///./build/ci.sqlite3`; `pytest -m integration` exits 5 on
  FastAPI `sqlite`/`none` and Django `sqlite` — hence no integration job there. Fixed by that pass: the Django job
  used to set a `DATABASE_URL` the scaffold never reads (and would have connected as `<package>` to a database named
  `<package>`), and the integration job used to be added for SQLite/no-database shapes.
- **pip-audit 2.10.1** over `uv export --frozen --all-groups --no-emit-project`: clean on the fixture's 94 hashed pins
  with `--disable-pip --strict`; exit 1 on a known-vulnerable pin. **OSV-Scanner** (v2 image) read `uv.lock` directly
  ("Scanned /src/uv.lock file and found 95 packages").
- **Version helper**: byte-identical to `iru-python-bump-version`'s (extracted from its `SKILL.md`, same SHA-1) and
  runs on macOS's system `python3` 3.9 as well as 3.13. On fixtures it listed `[project].version`, `__version__`, a
  settings `VERSION`, and a `FastAPI(version=)` literal; wrote `0.2.0.dev0` (then `uv lock` → `uv sync --locked`
  passed); short-circuited on hatch-vcs with `version: dynamic …`; refused to write when locations disagreed. The
  release tag check (`--list` | location lines | minus `FastAPI(version=)` | `grep -v -F ": $VERSION "`) passed for
  the matching version and failed for another. `uv lock --check` failed (exit 1) after a version change without
  `uv lock`, which is what release.yml's "Check the lockfile" relies on.
- **Sync**: `sync_versions.py` rewrote the README rows and `docs/antora.yml`'s `version:` on a fixture; the
  next-version computation (`1.3.0` / `v1.3.0` → `1.4.0.dev0`, `sync_1.4.0`; `1.3` and `1.3.0rc1` rejected) was run
  in bash.
- **Action refs** checked with `git ls-remote --tags` on the day of writing: `astral-sh/setup-uv` has no tag after
  `v7` that floats (latest `v10.3.0`), hence the exact pin; its `python-version`/`enable-cache` inputs were read from
  that tag's `action.yml`.

Not verified locally: a run on GitHub itself (service containers, setup-uv caching, GHCR push, Pages deploy, SARIF
uploads, `gh release upload`, the sync PR), the Antora steps (identical to the other workflows skills, verified
there), the container image build check (the `Dockerfile` belongs to the scaffold skills and is verified there),
Dependabot's actual `uv`/`docker-compose` update runs, and SonarCloud ingestion of the Cobertura/JUnit/Ruff reports.
