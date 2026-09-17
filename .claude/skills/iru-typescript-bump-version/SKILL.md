---
name: iru-typescript-bump-version
description: Set an npm/TypeScript project's version to an exact value, updating `package.json` and syncing the lockfile for whichever package manager the project uses (npm, pnpm, or yarn). Invoke as `/iru-typescript-bump-version <new-version>` where `<new-version>` is the literal target version (e.g. `1.4.0` or `1.4.1-dev.0`) — this skill does not compute bumps itself, it only applies the value it's given (`iru-release` computes the release/next-dev values per the pre-release convention documented in this file and passes each one through in turn). Also accepts `args`: `package: <name-or-path>` to pick one package in an npm/pnpm/yarn workspace (asks if omitted and more than one `package.json` with a `version` field exists), and `sync-files: yes|no` (default: ask) to also update README/Antora version mentions the same way `iru-release`'s Java path does. Reports the old and new version and every file touched. Use whenever the user, or another skill such as `iru-release`, needs an npm-ecosystem project's version set to a specific value instead of hand-editing `package.json`.
model: haiku
---

# TypeScript Bump Version

Set an npm/TypeScript project's version to an exact value across every file that needs to agree with it:
`package.json`, the lockfile, and (optionally) any README/Antora version mentions. This skill never computes a
version itself — it applies exactly the version string it's given, validated for shape. The "which version to
compute next" logic (release vs. pre-release bump) belongs to the caller (typically `iru-release`) and is defined
in Step 5 below so that caller has one place to read it from.

## Step 0 — Resolve inputs

Parse the invocation:
- The positional argument is `<new-version>` — the exact target version string (e.g. `1.4.0`, `2.0.0-dev.3`).
  If it's missing, ask the user for it before doing anything else; don't guess or compute one here.
- `args` (`key: value` lines), if present:
  - `package: <name-or-path>` — which workspace package to bump, when the repository has more than one.
  - `sync-files: yes|no` — whether to also update README/Antora version mentions (Step 6). If omitted, ask once
    with `AskUserQuestion` after Step 2 confirms whether such mentions actually exist; skip asking if none do.

## Step 1 — Validate the version string

`npm version <new-version> --no-git-tag-version` validates semver itself and fails loudly (`npm error Invalid
version: <value>`) on a malformed string, so a separate regex/`npx semver` pre-check isn't necessary — just read
that command's exit status and stderr in Step 4 and stop there if it rejects the value. Do still reject at this
step, before touching anything, an argument that is obviously not attempting a version at all (empty string, or
contains whitespace) with a short message asking for a valid semver string — this avoids running a mutating
command on garbage input purely to get the error message.

## Step 2 — Detect the package manager and the package(s) to bump

Package-manager detection rule (same rule used across this plan's npm-ecosystem skills): check
`package.json`'s `packageManager` field first, then the lockfile actually present —
`package-lock.json` → npm, `pnpm-lock.yaml` → pnpm, `yarn.lock` → yarn. If more than one lockfile exists, prefer
`packageManager` and warn about the stale extra lockfile(s) in the final report; if none exists, default to npm
(the most common case for a not-yet-installed project) and note that assumption in the report.

Also determine yarn's generation if the lockfile/`packageManager` says yarn: `yarn --version` (or the
`packageManager` field's pinned version) starting with `1.` is Yarn Classic, `2.`+ is Yarn Berry — they differ in
Step 4.

Find every `package.json` that declares a top-level `"version"` field (`find . -name package.json -not -path
"*/node_modules/*"`, excluding files under `src/main/frontend/` — see the Hilla note below). If more than one is
found:
- If `args` gave `package:`, use that one.
- Otherwise, if this looks like an npm/pnpm/yarn **workspace** (root `package.json` has a `workspaces` field, or
  a `pnpm-workspace.yaml` exists), ask the user via `AskUserQuestion` which package to bump, or whether to bump
  every workspace member to the same version (offer both as options — some monorepos version every package in
  lockstep, others per-package).
- If it's not a workspace but multiple `package.json` files still exist (e.g. a **Hilla** frontend: a
  `src/main/frontend/package.json` sitting under a Maven-managed root — see design decision context in this
  plan), warn explicitly that the frontend `package.json` under a Hilla project is generated/managed by the
  Vaadin Maven plugin and its version should not be hand-bumped independently of the backend `pom.xml`; ask
  before touching it, and default to skipping it unless the user confirms.

## Step 3 — Read the current version

Before changing anything, read and report the current value so the diff is visible even if a later step fails
partway through:

```bash
node -p "require('./package.json').version"
```

(Run from the directory containing the target `package.json`, or pass the full path:
`node -p "require('./path/to/package.json').version"`.)

## Step 4 — Apply the new version, per package manager

Run the command from the directory containing the target `package.json` (`cd` there, or use each tool's
workspace-targeting flag if bumping in place from the repository root).

| Package manager | Command | What it updates | Side effects to know about |
|---|---|---|---|
| npm | `npm version <new-version> --no-git-tag-version` | `package.json` **and** `package-lock.json` in one step (confirmed in this repo's local verification: both files' `version` field change together) | Without `--no-git-tag-version`, `npm version` also creates a git commit and an annotated tag — **always pass the flag** here, this skill only sets a value, it never commits/tags. `npm version` validates the string itself (rejects with `npm error Invalid version: <value>`, exit code 1) — no separate validation needed. Works even outside a git repository (verified locally: no git-related warning or failure when run in a plain, non-git directory). |
| pnpm | `pnpm version <new-version> --no-git-tag-version` | `package.json` only | Verified locally (pnpm 12.4.2): the flag **is** supported and behaves like npm's (no git tag/commit). Unlike npm, this does **not** touch `pnpm-lock.yaml` — but that's fine: `pnpm-lock.yaml` does not embed the root package's own `version` field at all (verified: a freshly generated lockfile's `importers: { .: {} }` entry carries no version), so there is nothing to resync. If the project also carries a stray `package-lock.json` (shouldn't happen in a clean pnpm project, but check), that file **would** need `npm pkg set version=<new-version>` + `npm install --package-lock-only` to catch up — warn if you find one. |
| yarn (Classic, 1.x) | `yarn version --new-version <new-version> --no-git-tag-version` | `package.json` only; `yarn.lock` does not embed a root version either | Yarn Classic's plain `yarn version` is interactive (prompts for the new version) — use `--new-version <v>` to pass it non-interactively. **Unverified locally** (this environment has no yarn install; `npx yarn@latest` resolves Classic 1.22.22 but a real project may pin Berry via `packageManager`) — confirm the flag name against `yarn version --help` before relying on it if the project's yarn differs from what's documented here. |
| yarn (Berry, 2.x+) | `yarn version <new-version>` | `package.json` (and Berry's own `.yarn/versions/*.yml` deferred-version file, if the `version` plugin's deferred mode is enabled — check `.yarnrc.yml`) | Berry does **not** create a git tag/commit by default (unlike Classic's interactive flow), so no `--no-git-tag-version`-equivalent flag is normally needed — but verify with `yarn version --help` in the actual project, since this was **not verified locally** (Berry requires `corepack`/`yarn set version berry`, which this run did not fully exercise beyond confirming `corepack` itself is present). |

If the command exits non-zero, stop, show the actual error text, and do not treat any file as updated — don't
partially apply the version by hand as a fallback.

An alternative that works identically across all three package managers when their own `version` subcommand is
unavailable, disabled, or fighting a monorepo's own version-lockstep tooling: `npm pkg set version=<new-version>`
edits `package.json` alone (any package manager can read the result), but it does **not** touch a lockfile that
does embed a version (npm's) — verified locally: after `npm pkg set version=...`, `package-lock.json` still shows
the old value until `npm install --package-lock-only` is run to resync it. Use this pair only as a fallback (e.g.
`pnpm`/`yarn` not actually installed and `npx` resolution isn't acceptable) and always follow an npm-lockfile
project's `npm pkg set` with `npm install --package-lock-only`.

## Step 5 — The ecosystem's pre-release convention (for `iru-release` and other callers)

This is the npm-ecosystem equivalent of the Java catalog's SNAPSHOT convention, and is the contract a later
`iru-release` change is expected to call this skill against (two calls per release, each passing a computed
`new-version` through `args`):

- **Current development version**: `x.y.z-dev.N` (e.g. `1.4.0-dev.0`, `1.4.0-dev.1` after a hotfix to the
  pre-release itself) — `dev` is this catalog's chosen pre-release identifier (parallel to npm's own
  conventional `-alpha`/`-beta`/`-rc`, but denoting "next development snapshot" the way Maven's `-SNAPSHOT`
  does). `N` starts at `0` and only increments if a project chooses to cut multiple pre-release publishes off the
  same target version before releasing it — most projects following this convention will only ever see `.0`.
- **Cutting a release**: strip the pre-release suffix entirely — `x.y.z-dev.N` → `x.y.z`. Call this skill with
  `new-version: x.y.z`.
- **Opening the next development cycle**: bump the patch component and reset to `.dev.0` — `x.y.z` →
  `x.y.(z+1)-dev.0`. Call this skill again, immediately or in a follow-up sync step, with
  `new-version: x.y.(z+1)-dev.0`. (This mirrors the Java catalog's default minor-bump convention only in spirit,
  not in the exact component bumped — npm's own ecosystem convention favors a patch-level pre-release for "next
  unreleased work" since a minor/major bump is a deliberate decision made when the actual next feature set is
  known, not automatically at release time. If a project wants a minor bump instead, that's a caller decision —
  this skill only applies whatever exact string it's given.)

Useful shortcut confirmed by local verification: `npm version prerelease --preid=dev --no-git-tag-version` run
against a plain release version (no existing pre-release suffix) computes exactly the `x.y.(z+1)-dev.0` value
above on its own (verified: `1.2.3` → `1.2.4-dev.0` in one command) — a caller may use this instead of
precomputing the next-dev string by hand, as long as it's running against npm specifically (pnpm/yarn's
`prerelease` bump-type support was not separately verified here).

## Step 6 — Optionally sync other files that mirror the version

Ask (or honor `args: sync-files`) whether to also update other places that name the current version, the same
way `iru-release`'s Java path syncs `README.md`/`docs/antora.yml`/dependency snippets:

- **`README.md`** — installation snippets or a "Current version" mention, if any (`grep -n
  '"version":\|npm install .*@[0-9]\|Current version' README.md`).
- **`docs/antora.yml`** — its `version:` field, if this repository has an Antora site and that field is meant to
  track the package's released version (skip for a pre-release value — Antora's `version:` conventionally names
  a released version, not a `-dev.N` one, matching the Java skills' own convention of only writing release
  versions there).
- Any Antora page under `docs/modules/ROOT/pages/` showing an install/dependency snippet with a literal version
  string (`grep -rl '"version":\|@[0-9]\+\.[0-9]\+\.[0-9]\+' docs/modules/ROOT/pages/*.adoc`).

This is offered, not automatic — these files may be intentionally out of step with `package.json` (e.g. a README
badge pulling live from npm rather than a hardcoded string), so don't rewrite anything the user didn't confirm.
This step exists so a future `iru-release` doesn't have to reimplement it — it can simply pass `sync-files: yes`
once it's ready to delegate this responsibility (Task 50 of this plan).

## Step 7 — Report

Summarize:
- The package (path) bumped, the package manager detected and how (field vs. lockfile), the old version and the
  new version.
- Every file actually changed (`package.json`, lockfile, and any Step 6 files accepted).
- Any package/lockfile skipped and why (Hilla frontend declined, extra stale lockfile, workspace member not
  selected).
- What was verified locally vs. what to double-check in the real project: npm's `--no-git-tag-version` behavior
  and its lockfile sync are confirmed; pnpm's `--no-git-tag-version` flag and its lockfile-free root version are
  confirmed; Yarn Classic's `--new-version` flag and Yarn Berry's no-tag-by-default behavior are **not** verified
  in this environment and should be spot-checked against `yarn version --help` in a real yarn project before
  being trusted blindly.
- **Warn explicitly**: review the diff before committing (this skill doesn't commit anything); a lockfile that
  wasn't regenerated by the package manager's own `version` command (the `npm pkg set` fallback path) needs its
  install/lockfile-only step run or CI's lockfile-freshness check will fail; a Hilla frontend `package.json`
  should generally be left to the Vaadin tooling rather than bumped independently of the backend version.
