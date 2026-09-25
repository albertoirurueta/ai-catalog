---
name: iru-setup-react-native-app
description: Scaffold a new Expo-managed React Native app at the repository root (or a chosen subdirectory) —
  runs `npx create-expo-app@latest <dir> --template blank-typescript`, then adds a `jest-expo` + `@testing-library/react-native`
  test setup (`jest.config.js` with `collectCoverage`/`coverageReporters: ["text","lcov"]`, a working async-render
  test skeleton), an `eslint-config-expo` flat config generated non-interactively via `npx expo lint` plus Prettier,
  an `eas.json` with `development`/`preview`/`production` build profiles, a Maestro smoke-test skeleton
  (`.maestro/smoke.yaml`), and, when opted in, `sonar-project.properties` excluding `android/**`/`ios/**`/
  `node_modules/**`/`coverage/**`. Asks for the app name/slug/directory, license, developer name/email/organization
  URL, whether the project is open source, whether to wire up a SonarQube/SonarCloud scan (`sonar`:
  `cloud`/`self-hosted`/`none`), how native builds should run (`native-builds`: `eas`/`local` — explains the EAS
  free tier's 15-builds-per-platform-per-month cap versus `eas build --local`/`npx expo prebuild`), and the
  distribution target (`distribution`: `none`/`internal`/`store` — gates `eas.json`'s `submit` block and any store
  credentials called out in the report). Invoke as `/iru-setup-react-native-app`. Ships with explicit templates
  embedded in this skill (Step 5), genericized with `<placeholder>` markers, verified end-to-end while building
  this skill (`npm test -- --coverage`, `npx expo lint`, `npx expo export --platform web` all run clean against
  them). If `package.json` already exists at the target directory, surveys which of this skill's files are already
  present and asks whether to stop, fill gaps only, or regenerate. Accepts pre-resolved inputs via `args`
  (`key: value` lines) — `app-name`, `app-slug`, `app-directory`, `license`, `developer-name`, `developer-email`,
  `organization-url`, `open-source`, `sonar` (+ `sonar-organization`/`sonar-project-key`/`sonar-host-url`),
  `native-builds`, `distribution`, and `mode` (`new`/`existing`) — so an orchestrating skill can supply them
  without re-prompting; invoked stand-alone, it asks `open-source` first and derives the `sonar` question's default
  from that answer. Targets Expo SDK 57 / React Native's New Architecture only (no legacy-architecture toggle
  exists to opt out of) and produces no Cordova/Capacitor artifacts — for a Capacitor-based hybrid app use
  `iru-setup-ionic-app` instead. Use whenever a new Expo/React Native mobile app needs its scaffold, test, lint,
  build-profile, and Maestro/Sonar tooling bootstrapped from this house template, instead of hand-configuring each
  piece.
model: haiku
---

# Setup React Native App

Scaffold a new Expo-managed (New Architecture only, Cordova-free) React Native app using `create-expo-app`'s
`blank-typescript` template, then layer on this catalog's standard test/lint/build/Sonar tooling using explicit
example templates embedded in this skill (Step 5) that were verified together end-to-end while building it —
`npm install`, `npm test -- --coverage`, `npx expo lint`, and `npx expo export --platform web` all run clean
against them. Every template is genericized (no real repo/org/person names); only the `<placeholder>` values are
filled in per project using Steps 2–4.

This skill only produces a **managed** Expo app (JS/TS + Expo config plugins, no committed `ios/`/`android/`
folders). Native projects are generated on demand via `eas build` or `npx expo prebuild` — see the `native-builds`
question in Step 2. It does not scaffold a bare React Native CLI project.

## Step 0 — Resolve inputs

This skill can be invoked stand-alone (`/iru-setup-react-native-app`) or as a step inside another skill (e.g. a
future `iru-setup-react-native-app-repository` or the catalog's `iru-setup-repository` front door), which resolves
these same inputs itself and passes them through `args` as `key: value` lines, one per line, e.g.:

```
app-name: My App
app-slug: my-app
app-directory: mobile
license: MIT License
developer-name: Jane Doe
developer-email: jane@example.com
organization-url: https://github.com/example-org
open-source: yes
sonar: cloud
sonar-organization: example-org-github
sonar-project-key: example-org_my-app
sonar-host-url: https://sonarcloud.io
native-builds: eas
distribution: store
mode: new
```

Parse any such lines from `args` now. Every field found here is resolved — skip asking about it in Step 2. Only
fields genuinely missing from `args` still need a question. If `args` is absent or doesn't look like this format,
treat everything as unset and ask normally.

Recognized keys: `app-name`, `app-slug` (kebab-case; defaults to a slugified `app-name` if omitted),
`app-directory` (the subdirectory to scaffold into — see Step 1 if unset), `license`, `developer-name`,
`developer-email`, `organization-url`, `open-source` (`yes`/`no`), `sonar` (`cloud`/`self-hosted`/`none`) plus,
only when `sonar` is `cloud` or `self-hosted`, `sonar-organization`/`sonar-project-key`/`sonar-host-url`,
`native-builds` (`eas`/`local`), `distribution` (`none`/`internal`/`store`), and `mode` (`new`/`existing`).

`mode: existing` is this catalog's shared signal (set by a front door that already ran `iru-explore` and knows this
is an established repository) that Step 1 should skip its stop-or-regenerate question entirely and go straight to
gap-fill: create only whatever files from Step 5 are genuinely missing at the resolved `app-directory`, and leave
every file that already exists untouched. `mode: new` or an unset `mode` follows Step 1's normal survey instead.

## Step 1 — Survey the repository

First resolve **where** to scaffold, unless `app-directory` was already supplied via `args`:

- If the repository root has no files other than dotfiles/directories (`.git`, `.github`, `.gitignore` alone —
  nothing else), it's safe to scaffold directly into the root: offer `.` as the default `app-directory`.
- Otherwise — the common case, since most repositories already carry at least a `README.md` or `LICENSE` —
  `create-expo-app` refuses outright to scaffold into a non-empty directory (confirmed: it exits with `"The
  directory <dir> has files that might be overwritten"` and makes **no changes** the moment it finds even one
  pre-existing file, so this is safe to attempt but never silently succeeds). Default `app-directory` to the
  resolved `app-slug` (see Step 2) and confirm it with the user rather than assuming silently.

Then check, at that `app-directory`, whether `package.json` already exists:

- **Doesn't exist**: skip straight to Step 2. There is nothing to preserve.
- **Exists and its `dependencies` include `expo`**: this skill owns this scaffold. Warn the user it will be
  regenerated, then:
  - **`mode: existing` was resolved in Step 0**: skip the question below — go straight to **gap-fill**: create
    only the files from Step 5 that are missing at `app-directory` (never touch `App.tsx`, `app.json`, `assets/`,
    or any file already there); note in Step 8's report which files were left alone because they already existed.
  - **Otherwise**: use `AskUserQuestion` with two options:
    - **Stop** — leave `app-directory` untouched entirely. Report this and end here.
    - **Update** — re-run only this skill's *tooling* files (Step 5's `jest.config.js`, the `tsconfig.json`
      `types` merge, `__tests__/App.test.tsx` if missing, `eslint.config.js`, `.prettierrc`/`.prettierignore`,
      `eas.json`, `.maestro/smoke.yaml`, `sonar-project.properties`) — never re-run `create-expo-app` itself and
      never touch `App.tsx`/`app.json`/`assets/`/any other application source. Tell the user up front that any
      hand customization already made to the tooling files listed above will be lost unless re-added afterward
      (call this out again in Step 8).
- **Exists but has no `expo` dependency** (a bare React Native CLI project, or an unrelated Node project already
  living at that path): this skill only supports Expo-managed apps — warn the user explicitly and ask whether to
  scaffold into a different subdirectory instead, or stop. Don't attempt to convert or merge into a non-Expo
  project.

## Step 2 — Collect the required inputs

For any field Step 0 already resolved from `args`, use that value directly and don't ask about it again. For
everything else, ask the user directly (plain conversation, pre-filling defaults found in Step 1 if updating an
existing scaffold):

- **app-name** — the display name, e.g. `My App` (written to `app.json`'s `expo.name`).
- **app-slug** — kebab-case, e.g. `my-app` (written to `app.json`'s `expo.slug` and `package.json`'s `name`;
  offer a slugified `app-name` as the default rather than asking open-endedly).
- **Developer name**, **developer email**, **organizationUrl**.

Then, unless Step 0 already resolved a `license` value from `args`, ask about the **license** with
`AskUserQuestion` (mirrors this catalog's other setup skills):

- MIT License (recommended for app source not meant for redistribution as a library)
- Apache License 2.0
- No license (proprietary / all rights reserved)
- Other — ask for the license's display name directly afterward

If a license is chosen (anything but "No license"), remind the user in Step 8 to also add a matching `LICENSE`
file at the repository root — `create-expo-app`'s own template ships its **own** `LICENSE` file (Expo's MIT
license for the template code itself, not the project), which Step 6 replaces/removes per the chosen license
here. The `iru-check-license` skill can verify/backfill source headers against it once a real one is in place.

Then resolve `open-source`, `sonar`, `native-builds`, and `distribution` — skip any of the four Step 0 already
resolved from `args`. When invoked stand-alone with none of them pre-resolved, ask `open-source` *first*
(`AskUserQuestion`: yes/no) and derive the recommended default for `sonar` from that answer, per this catalog's
shared convention:

- **open-source** — is this repository open source? Yes / No.
- **sonar** — whether to wire up a SonarQube/SonarCloud scan (`sonar-project.properties`, typically consumed by a
  CI workflow such as `iru-setup-typescript-github-workflows`, so it's worth setting up here even if that workflow
  comes later). Recommend **SonarCloud** (`cloud`) when open-source is Yes; when not open source, state that
  SonarCloud is free only for open-source projects (a paid plan is required otherwise) and recommend **None**
  (`none`), offering **self-hosted SonarQube** as the second option:
  - `cloud` — ask for the `sonar.organization` key, offering `<owner>-github` (the owner parsed in Step 3) as the
    suggested default. Default `sonar.projectKey` to `<owner>_<repo>` (also from Step 3) and `sonar.host.url` to
    `https://sonarcloud.io`, confirming both with the user rather than assuming silently.
  - `self-hosted` — ask for `sonar.host.url` directly (no sensible default), plus `sonar.organization` only if
    that server has organizations enabled, and `sonar.projectKey`.
  - `none` — skip `sonar-project.properties` entirely (Step 5/6).
- **native-builds** — how should this app's native builds run? Present as a bounded choice:
  - **`eas`** (recommended default) — build in Expo's own cloud via `eas build --platform <ios|android|all>
    --profile <profile>`. State explicitly: EAS's free plan currently includes **15 builds per platform per
    month**; once that's exceeded mid-month, either upgrade to a paid EAS plan or fall back to local builds for
    the rest of the period. No local native toolchain is required to trigger a cloud build.
  - **`local`** — skip Expo's build cloud (and its monthly cap) entirely, at the cost of needing a full native
    toolchain wherever builds run: either `eas build --local` (still driven by `eas-cli` and this skill's
    `eas.json` profiles, but compiles on the invoking machine/CI runner — Xcode + a valid Apple developer identity
    for iOS, the Android SDK/NDK + a JDK for Android), or `npx expo prebuild` to materialize the native `ios/`/
    `android/` projects once and build them directly with `xcodebuild`/`./gradlew` from there (note: `expo
    prebuild` output is meant to be regenerated, not hand-edited, whenever `app.json`/config plugins change — hand
    edits to a prebuilt `ios/`/`android/` folder are lost on the next `prebuild` run).
  - This answer doesn't change anything this skill writes to disk beyond `eas.json`'s `cli` block (Step 5) — it's
    recorded here so `iru-setup-typescript-github-workflows` can wire the matching CI job
    later without asking again.
- **distribution** — `none`/`internal`/`store`:
  - `none` — builds (however `native-builds` produces them) are for local install/manual QA only. `eas.json`'s
    `submit` block is omitted (Step 5/6); no store credentials are ever asked for or referenced by this skill.
  - `internal` — builds are shared ad hoc (an EAS internal-distribution install link, or added manually to
    TestFlight/Play internal testing) without any submission automation from this skill. `eas.json`'s `submit`
    block is still omitted — that path doesn't call `eas submit`.
  - `store` — full App Store Connect / Google Play production submission is wired up: `eas.json` gains a
    `submit.production` block (Step 5/6), and Step 8's report flags the credentials
    (`EXPO_TOKEN`/`APP_STORE_CONNECT_API_KEY_ID`+`_ISSUER_ID`+`_KEY_BASE64`/`GOOGLE_PLAY_SERVICE_ACCOUNT_JSON`)
    that `iru-setup-typescript-github-workflows`'s release workflow will need — this skill itself never collects
    or stores those credentials, only names them.

## Step 3 — Infer repository information

Don't ask for these — derive them from the current repository, the same way `iru-setup-java-library` and
`iru-setup-typescript-library` do:

- **Owner/repo and host**: parse `git remote get-url origin` (handles both `git@host:owner/repo.git` and
  `https://host/owner/repo.git` forms). Used only for Step 2's `sonar.organization`/`sonar.projectKey` defaults.
  If there's no `origin` remote yet, ask the user directly instead of leaving these blank.
- **Initial-screen text**: read `App.tsx` right after Step 6's scaffold runs, to fill `<initial-screen-text>` in
  the Maestro skeleton (Step 5) with whatever the scaffold's placeholder screen actually renders (`"Open up
  App.tsx to start working on your app!"` in the `blank-typescript` template as of Expo SDK 57 — confirm against
  the actual file rather than assuming this exact string, since the template can change).

## Step 4 — Look up dependency versions

Every devDependency version this skill installs beyond what `create-expo-app` itself resolves must be looked up at
run time with `npm view <package> version` (or, if that's unavailable — offline, registry unreachable — fall back
to the version recorded in the table below, which is what this skill's author actually observed on the npm
registry in September 2026 while building and verifying this skill). Note in Step 8's report whenever a fallback
was used instead of a live lookup.

| Package | npm view command | September 2026 fallback |
|---|---|---|
| `jest-expo` | `npm view jest-expo version` | `57.0.5` (keep in lockstep with the scaffolded `expo` SDK's major) |
| `jest` | `npm view jest version` | `29.7.0` |
| `@types/jest` | `npm view @types/jest version` | `30.0.0` |
| `@testing-library/react-native` | `npm view @testing-library/react-native version` | `14.0.1` |
| `eslint` | see the caveat below — **do not** just take `npm view eslint version` | `9.39.5` |
| `eslint-config-expo` | `npm view eslint-config-expo version` | `57.0.2` (keep in lockstep with the scaffolded `expo` SDK's major) |
| `prettier` | `npm view prettier version` | `3.9.7` |
| `eas-cli` | `npm view eas-cli version` | `24.6.0` (never installed as a dependency — always invoked via `npx eas-cli@latest`; this fallback is only for `eas.json`'s `cli.version` constraint) |

**`eslint` version caveat (discovered verifying this skill in September 2026):** `npm view eslint version`
resolves the bare `latest` dist-tag, which had already moved to the `10.x` line at verification time — but
`eslint-config-expo`'s own installer (invoked by `npx expo lint`'s auto-configure path, see Step 7) explicitly
requests `eslint@^9.0.0`, not `latest`, and that's the combination actually verified end-to-end while building
this skill. Resolve the `eslint` version to install like this instead of trusting the bare `latest` tag:

1. `npm view eslint-config-expo peerDependencies.eslint` — read off the range it declares (`>=8.10` at
   verification time, which is wide enough to permit `10.x` too, but is *not* what Expo's own tooling targets).
2. `npm view eslint dist-tags --json` — prefer the `maintenance` dist-tag's version over `latest` when one exists
   and satisfies step 1's range; that's the line `eslint-config-expo`/`expo lint` is actually built and tested
   against, and is what npm resolved (`9.39.5`) even with no explicit version pin in this skill's own
   verification run.
3. If the resolved version differs from the bare `latest` tag, say so explicitly in Step 8's report.

## Step 5 — Reference templates

These are genericized example templates — verified together end-to-end while building this skill (`npm install`,
`npm test -- --coverage`, `npx expo lint`, `npx expo export --platform web` all run clean against them) — kept
verbatim below except for the placeholders. Only substitute `<placeholder>` values using Steps 2–4; every other
line, script, and option is copied as shown.

### `package.json` — scripts to merge in

`create-expo-app`'s own template already writes `name`/`version`/`main`/`dependencies`/`start`/`android`/`ios`/
`web`. Merge these five additional scripts and the `devDependencies` below into that same file — don't replace it
wholesale:

```json
{
  "scripts": {
    "test": "jest",
    "coverage": "jest --coverage",
    "lint": "expo lint",
    "format": "prettier --check .",
    "typecheck": "tsc --noEmit"
  },
  "devDependencies": {
    "@testing-library/react-native": "<testing-library-react-native-version>",
    "@types/jest": "<types-jest-version>",
    "eslint": "<eslint-version>",
    "eslint-config-expo": "<eslint-config-expo-version>",
    "jest": "<jest-version>",
    "jest-expo": "<jest-expo-version>",
    "prettier": "<prettier-version>"
  }
}
```

**Do not add `react-test-renderer` as a dependency.** Confirmed while verifying this skill:
`@testing-library/react-native@14` no longer declares it as a dependency or peer dependency (it renders through
its own internal `test-renderer`), and installing `react-test-renderer@latest` alongside the scaffold's pinned
`react` version fails with `ERESOLVE` (`react-test-renderer@19.3.0` requires `react@^19.3.0`, but
`create-expo-app`'s `blank-typescript` template at SDK 57 pins `react@19.2.3`).

### `jest.config.js`

```js
module.exports = {
  preset: "jest-expo",
  collectCoverage: true,
  coverageReporters: ["text", "lcov"],
  collectCoverageFrom: [
    "**/*.{ts,tsx}",
    "!**/coverage/**",
    "!**/node_modules/**",
    "!**/babel.config.js",
    "!**/jest.config.js",
    "!**/.expo/**",
  ],
};
```

Confirmed: `npm test -- --coverage` (i.e. `jest --coverage`) writes `coverage/lcov.info` (from the `lcov`
reporter, used by `sonar.javascript.lcov.reportPaths` below) plus an HTML report under `coverage/lcov-report/` —
both must be excluded from ESLint's/Prettier's scans and from `.gitignore` (the `iru-setup-typescript-gitignore`
skill covers the latter).

### `tsconfig.json` — merge into the scaffold's

```json
{
  "extends": "expo/tsconfig.base",
  "compilerOptions": {
    "strict": true,
    "types": ["jest"]
  }
}
```

**The `"types": ["jest"]` line is not optional** — this is the single most important quirk found verifying this
skill: `create-expo-app`'s scaffolded `tsconfig.json` only sets `{"extends": "expo/tsconfig.base",
"compilerOptions": {"strict": true}}`, and `expo/tsconfig.base` itself never restricts `types`. Despite
`@types/jest` being installed, `npm run typecheck` (`tsc --noEmit`) still fails on any test file with `error
TS2593: Cannot find name 'test'` / `error TS2304: Cannot find name 'expect'` until `types: ["jest"]` is added
explicitly to `compilerOptions`. Confirmed: adding this one line alone (no other change) makes `tsc --noEmit`
pass clean against the test skeleton below.

### `__tests__/App.test.tsx`

```tsx
import { render, screen } from "@testing-library/react-native";

import App from "../App";

test("renders the root screen", async () => {
  // @testing-library/react-native's `render` is async as of v14 — always await it. Confirmed: omitting the
  // `await` here makes `screen.toJSON()` throw "`render` function has not been called", because `screen` is
  // only populated once the underlying `act()` call inside `render()` resolves.
  await render(<App />);
  expect(screen.toJSON()).not.toBeNull();
});
```

Confirmed this skeleton passes with `66.66%` line coverage on the scaffold's own `App.tsx`/`index.ts` out of the
box (`App.tsx` itself at 100%; `index.ts`'s `registerRootComponent` call is the only uncovered line, which is
expected — it's entry-point wiring, not app logic).

### `eslint.config.js` — generated by `npx expo lint`, not hand-written

Don't write this file directly. Step 7 pre-installs `eslint`/`eslint-config-expo` (Step 4's versions) as
`devDependencies` and then runs `npx expo lint` once, which detects there's no ESLint config yet and generates
this file itself. The generated shape, confirmed while verifying this skill:

```js
// https://docs.expo.dev/guides/using-eslint/
const { defineConfig } = require('eslint/config');
const expoConfig = require("eslint-config-expo/flat");

module.exports = defineConfig([
  expoConfig,
  {
    ignores: ["dist/*", "coverage/*"],
  }
]);
```

After `npx expo lint` generates the file with only `"dist/*"` in `ignores`, add `"coverage/*"` to that array
(Jest's coverage HTML report under `coverage/lcov-report/*.html` would otherwise be linted as JS/HTML and fail).
`eslint-config-expo/flat`'s own rule set was confirmed to carry no stylistic/formatting rules (no `quotes`,
`semi`, `indent`, `comma-dangle`), so no `eslint-config-prettier` layer is needed to avoid ESLint/Prettier
fighting each other, unlike some other ESLint presets.

### `.prettierrc`

```json
{
  "semi": true,
  "singleQuote": false,
  "trailingComma": "all",
  "printWidth": 100
}
```

### `.prettierignore`

```
node_modules/
coverage/
dist/
web-build/
.expo/
android/
ios/
```

**Required, not optional** — without it, `prettier --check .` recurses into `coverage/lcov-report/` (generated
HTML) and the auto-generated `eslint.config.js`/`index.ts` and reports false-positive formatting mismatches
(confirmed: 11 files flagged on a freshly scaffolded project before this file was added, versus 3 — the
scaffold's own un-reformatted `App.tsx`/`eslint.config.js`/`index.ts`, which is expected and left for the user
to `prettier --write` once — after it).

### `eas.json`

```json
{
  "cli": {
    "version": ">= <eas-cli-version>",
    "appVersionSource": "remote"
  },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal"
    },
    "preview": {
      "distribution": "internal"
    },
    "production": {
      "autoIncrement": true
    }
  }
}
```

**Only when `distribution: store`** (Step 2), add a `submit` block after `build`:

```json
  "submit": {
    "production": {}
  }
```

`<eas-cli-version>` is Step 4's resolved `eas-cli` version (fallback `24.6.0`). This file's correctness was
confirmed structurally (valid JSON; matches `eas.json`'s documented schema shape) — the build/submit profiles
themselves are **unverified locally**: running an actual `eas build`/`eas submit` needs an Expo account, project
linking (`eas init`), and (for `store`) real Apple/Google credentials, none of which are available in this
skill's verification environment.

**Who owns the version for this flavor** (`appVersionSource: "remote"` + `autoIncrement: true`) — decided here so
`iru-release`/`iru-typescript-bump-version` don't have to guess:

- **Build numbers** (`ios.buildNumber` / `android.versionCode`) are owned by **EAS**: with `appVersionSource:
  "remote"` they're stored on EAS's servers and `autoIncrement` bumps them on every `production` build. They must
  not be written into `app.json` or bumped by any catalog skill — `eas build:version:set`/`eas build:version:sync`
  are the only sanctioned ways to touch them.
- **The user-facing version** (`1.4.0` on the store listing) is read from **`app.json`'s `expo.version`** —
  `package.json`'s `version` is never consulted by Expo/EAS or the stores. `iru-typescript-bump-version` only
  updates `package.json` (+ lockfile, and README/Antora mentions on request), so on its own a release bump for
  this flavor changes a value the app never ships.
- Therefore, when `iru-release` cuts a release on a `react-native-app` project it must, after delegating the
  `package.json` bump to `iru-typescript-bump-version`, also set `expo.version` in `app.json` (or the equivalent
  `version` field in `app.config.ts`/`app.config.js` when the project uses a dynamic config) to the **same
  release value** — and only the release value: a `-dev.N` pre-release string is not a valid store version, so
  the "next development" bump stays in `package.json` alone and `expo.version` keeps the last released value
  until the next release. `iru-typescript-bump-version`'s convention section (its Step 5) records the same
  rule from the bump skill's side, and its optional file sync offers `app.json` as one of the mirrored files.

### `.maestro/smoke.yaml`

```yaml
appId: <app-id>
---
- launchApp
- assertVisible: "<initial-screen-text>"
```

`<app-id>` — the app's bundle identifier / Android application id (`app.json`'s `expo.ios.bundleIdentifier` /
`expo.android.package`, once the user sets them — `create-expo-app`'s scaffold doesn't set either by default).
Leave the literal `<app-id>` placeholder in place and flag in Step 8's report that it must be filled in before
this flow can run. `<initial-screen-text>` — from Step 3's read of the scaffolded `App.tsx`. **Unverified
locally**: running this flow needs the Maestro CLI plus a booted simulator/emulator or a device, none of which
this skill's verification exercised — only the YAML's structural shape (two documents, `appId` header then a
step list) was validated.

### `sonar-project.properties` (only when `sonar` ≠ `none`)

```
sonar.organization=<sonar-organization>
sonar.projectKey=<sonar-project-key>
sonar.sources=.
sonar.tests=.
sonar.test.inclusions=**/__tests__/**,**/*.test.ts,**/*.test.tsx
sonar.exclusions=android/**,ios/**,node_modules/**,coverage/**,.expo/**,dist/**
sonar.test.exclusions=android/**,ios/**,node_modules/**,coverage/**,.expo/**,dist/**
sonar.javascript.lcov.reportPaths=coverage/lcov.info
```

Omit the `sonar.organization` line entirely for `sonar: self-hosted` servers without organizations enabled (per
Step 2). The source/test split follows the same pattern as this catalog's React/Angular/Ionic scaffolds
(`sonar.sources` and `sonar.tests` name the **same** root, and `sonar.test.inclusions` is what marks the test
files): the blank Expo template keeps `App.tsx` at the repository root and its tests under `__tests__/`, so `.`
is the only root that covers both — but naming `.` as sources and `__tests__` as a *separate* tests root makes
every `__tests__/*` file match both, which the scanner rejects outright ("File ... can't be indexed twice").
With the inclusions pattern, `__tests__/**` (and any colocated `*.test.ts(x)`) is indexed once, as test code, and
everything else under `.` is production code. `sonar.test.exclusions` mirrors `sonar.exclusions` so a
`__tests__/` folder inside `node_modules/`/`android/`/`ios/` is never picked up as this project's tests.
`android/**`/`ios/**` are excluded even though this scaffold doesn't commit those folders by default — they're
excluded defensively for the moment `npx expo prebuild` (Step 2's `native-builds: local` path) or an EAS local
build materializes them.

## Step 6 — Scaffold the Expo project

Skip this entire step if Step 1 resolved **Update**/gap-fill on an already-existing scaffold — go straight to
Step 7 with only the missing tooling files.

Otherwise, from the repository root:

```bash
npx create-expo-app@latest <app-directory> --template blank-typescript --no-install --no-agents-md
```

Confirmed non-interactive end-to-end with exactly these three flags — no `--yes` needed, and no prompt appears:

- `--template blank-typescript` selects the TypeScript blank template (not the default template, which pulls in
  Expo Router and extra example screens this skill doesn't need).
- `--no-install` skips the automatic `npm install` so Step 7 can add this skill's own `devDependencies` in the
  same install pass instead of a second one.
- `--no-agents-md` skips the template's own generated `AGENTS.md`/`CLAUDE.md`/`.claude/settings.json` — this
  catalog already has its own `CLAUDE.md`/skill conventions for the consuming repository, so the template's
  generic Expo-version-reminder files would only add noise (and a stray, unrelated `CLAUDE.md` at the scaffold
  root).
- `<app-directory>` must point at an empty (or nonexistent) path — confirmed `create-expo-app` refuses outright
  and makes **no changes** the instant it finds even one pre-existing file there (see Step 1). Never pass `.`
  unless Step 1 confirmed the repository root is genuinely empty of non-dotfiles.
- Confirmed: when run inside a directory that's already part of a git repository (the normal case for this
  catalog — scaffolding into a subdirectory of an existing repo), `create-expo-app` detects the enclosing `.git`
  and does **not** initialize a nested one. It only runs its own `git init` when there is no enclosing git
  repository at all — if that happens, remove the stray nested `.git` (`rm -rf <app-directory>/.git`) before the
  surrounding repository's own history is affected; check with `git status` right after scaffolding either way.

Then, at `<app-directory>`:

- Replace `LICENSE` with the project's chosen license (Step 2) — or delete it if "No license" was chosen. The
  scaffold's own `LICENSE` is Expo's MIT license for the *template*, not a license for this project's code, and
  leaving it in place would misrepresent the project's actual licensing.
- Set `app.json`'s `expo.name` to `<app-name>` and `expo.slug` to `<app-slug>` (Step 2) — `create-expo-app`
  defaults both to the scaffold directory's own name, which is usually not the same as the app name/slug the user
  gave.
- Merge Step 5's `package.json` scripts/devDependencies fragment into the scaffolded `package.json` (don't
  replace the file — it already has correct `dependencies`/`main` from the scaffold).
- Write `jest.config.js`, merge the `tsconfig.json` fragment, create `__tests__/App.test.tsx`, write
  `.prettierrc`/`.prettierignore`, write `eas.json` (gated per Step 2's `distribution` answer), create
  `.maestro/smoke.yaml`, and write `sonar-project.properties` (only when `sonar` ≠ `none`) — all from Step 5.
  Skip any individual file Step 1's gap-fill path found already present.

## Step 7 — Install dependencies and generate the ESLint config

From `<app-directory>`:

1. `npm install` — installs the scaffold's own `expo`/`react`/`react-native`/`expo-status-bar` dependencies.
2. `npm i -D jest-expo@<version> jest@<version> @types/jest@<version> @testing-library/react-native@<version>`
   (Step 4's versions). Confirmed clean, no peer-dependency conflicts, as long as `react-test-renderer` is never
   added (see Step 5's `package.json` note).
3. `npm i -D eslint@<version> eslint-config-expo@<version>` (Step 4's versions) — **install these two before**
   running `npx expo lint`, not after. Confirmed: running `npx expo lint` on a project with neither package
   installed triggers `expo lint`'s own interactive-looking auto-configure flow, which itself installs
   `eslint@^9.0.0`+`eslint-config-expo` via a nested `npm install` — but that very first invocation then fails
   with `Error: Cannot find module 'eslint'` (the newly-installed package isn't visible to the already-running
   Node process's module resolution). Pre-installing both packages explicitly first, then running `npx expo lint`,
   completes non-interactively in one shot with no prompt and no failure — this is the verified path.
4. `npx expo lint` — generates `eslint.config.js` (see Step 5) since none exists yet, and reports `0` problems
   against the scaffold's own `App.tsx`/`index.ts`. Add `"coverage/*"` to the generated file's `ignores` array
   afterward, per Step 5.
5. `npm i -D prettier@<version>` (Step 4's version).
6. `npx expo install react-dom react-native-web @expo/metro-runtime` — required for `npx expo export --platform
   web` (confirmed: without these three, that command fails outright with `CommandError: It looks like you're
   trying to use web support but don't have the required dependencies installed`, naming exactly these packages).
   `expo install` (not `npm install`) is used deliberately — it resolves each package to the version actually
   compatible with the scaffolded Expo SDK, rather than each package's own independent `latest` tag. This
   `--platform web` export is the fast, native-toolchain-free build-sanity check this catalog's
   `iru-setup-typescript-github-workflows` CI uses for this flavor instead of a full native build.

## Step 8 — Report

Summarize what was generated: the resolved `app-name`/`app-slug`/`app-directory`, the license chosen (or "none"),
and whether Step 6's scaffold ran fresh, was skipped in favor of gap-fill/update (per Step 1), or the user chose
to stop.

State explicitly what was included versus omitted, and why:

- **`open-source`**: yes/no, as resolved in Step 2.
- **`sonar`**: `cloud`/`self-hosted`/`none` — if `cloud`/`self-hosted`, `sonar-project.properties` was written
  with the resolved `sonar.organization`/`sonar.projectKey`; if `none`, note that this is expected when the
  project isn't open source (SonarCloud is free only for open-source projects) unless the user explicitly chose
  it.
- **`native-builds`**: `eas`/`local` — restate the EAS free-tier cap (15 builds/platform/month) if `eas` was
  chosen, or the native-toolchain requirement if `local` was chosen.
- **`distribution`**: `none`/`internal`/`store` — if `store`, list the exact secrets
  (`EXPO_TOKEN`/`APP_STORE_CONNECT_API_KEY_ID`+`_ISSUER_ID`+`_KEY_BASE64`/`GOOGLE_PLAY_SERVICE_ACCOUNT_JSON`) that
  will still need to exist before a CI-driven `eas submit` succeeds; if `none`/`internal`, note that `eas.json`'s
  `submit` block was deliberately omitted.
- Which devDependency versions came from a live `npm view` lookup versus this skill's recorded fallback, and
  whether the `eslint` version caveat (Step 4) resulted in a version older than the registry's bare `latest` tag —
  if so, say so plainly and name `eslint-config-expo` as the package whose own installer pins that older line.

Then report which of Step 5's files were created fresh, left untouched (gap-fill/`mode: existing`), or replaced
(update). If Step 1's existing tooling files were replaced, explicitly list what could have been lost — any script
or config option beyond what Step 5's templates show — and tell the user to check `git diff` for anything they
need to re-add.

Finish with an explicit **Warn explicitly** block:

- **The user must review every generated file before building, committing, or submitting to a store.** Confirm
  the license choice matches an actual repository-root `LICENSE` file (or that none is intended — suggest the
  `iru-check-license` skill otherwise), that `app.json`'s `ios.bundleIdentifier`/`android.package` are set to real
  values before any build/EAS/Maestro step that needs them (this skill leaves both unset, matching the scaffold's
  own default), and that `npm test -- --coverage && npx expo lint && npm run typecheck` succeed before relying on
  this scaffold.
- If `sonar: cloud` or `sonar: self-hosted` was chosen, a `SONAR_TOKEN` repository secret and an actual
  SonarCloud/SonarQube project matching `sonar.projectKey` still need to exist before a CI-driven Sonar scan will
  succeed — this skill only writes `sonar-project.properties`, it does not run a scan itself.
- If `distribution: store` was chosen, the App Store Connect / Google Play accounts and credentials named above
  still need to exist and be registered as repository secrets before a CI-driven `eas submit` will succeed — this
  skill never collects or stores those credentials itself.
- **Unverified locally, and never a blocker**: `eas build`/`eas submit` (need an Expo account and project
  linking), the Maestro flow (needs the Maestro CLI plus a booted simulator/emulator or device), and any
  `native-builds: local` native compile (`eas build --local`/`npx expo prebuild` + `xcodebuild`/`./gradlew`, which
  need the full Xcode/Android SDK toolchains) — this skill only confirms the generated config's shape, not that
  these commands succeed end-to-end. Everything else (`npm install`, `npm test -- --coverage`, `npx expo lint`,
  `npx expo export --platform web`) was run for real while building this skill.
- No `.gitignore` was written by this skill — `node_modules/`, `.expo/`, `dist/`, `coverage/`, and (once
  generated) `ios/`/`android/` should be ignored before the first commit; the `iru-setup-typescript-gitignore`
  skill covers this.
