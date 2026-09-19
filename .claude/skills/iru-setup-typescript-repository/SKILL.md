---
name: iru-setup-typescript-repository
description: End-to-end bootstrap for an npm/TypeScript repository of any of five flavors — collects `flavor`
  (`library`/`react`/`angular`/`react-native`/`ionic`, asked via `AskUserQuestion` in two short rounds when
  absent), the project's identity (name/slug/scope/app-id, description, license, developer name/email/organization
  URL), and the shared pipeline parameters (`open-source`, `publish` for libraries, `distribution` for apps, `sonar`
  plus its detail keys, `integration-branch`, `stable-branch`, `node-version`, `package-manager`) once, then
  orchestrates the flavor's scaffold skill (`iru-setup-typescript-library` / `iru-setup-react-web` /
  `iru-setup-angular-web` / `iru-setup-react-native-app` / `iru-setup-ionic-app`) → `iru-setup-antora` →
  `iru-setup-typescript-gitignore` → `iru-setup-typescript-github-workflows` → `iru-setup-changelog` →
  `iru-setup-readme`, in that order, via `iru-isolated-skill-executor`, so nothing is asked twice. Invoke as
  `/iru-setup-typescript-repository`, optionally with `args` (`key`/`value` lines) to pre-resolve `flavor`, `mode`
  (`new`/`existing`), `open-source`, `publish`, `distribution`, `sonar` (+ `sonar-organization`/`sonar-project-key`/
  `sonar-host-url`), `native-builds` (react-native), `framework` (ionic's own Angular/React choice),
  `integration-branch` (default `develop`), `stable-branch` (default `main`), `node-version` (default `24`),
  `package-manager` (default `npm`), and every identity field, skipping the matching question. In `mode=existing`
  it skips regenerating an already-present `package.json` and tells the CI-workflow step to take its own
  update/gap-fill path. Use whenever bootstrapping (or catching up) a new npm/TypeScript repository's full
  scaffold/docs/gitignore/CI/changelog/README pipeline in one pass, whatever its flavor, instead of running five to
  six skills separately and re-answering the same questions each time.
model: haiku
---

# Setup TypeScript Repository

Bootstrap a brand-new (or catch up an existing) npm/TypeScript repository in one pass, for whichever of five
flavors it is, by orchestrating six existing skills: the flavor's own scaffold skill (`iru-setup-typescript-library`,
`iru-setup-react-web`, `iru-setup-angular-web`, `iru-setup-react-native-app`, or `iru-setup-ionic-app`),
`iru-setup-antora` (Antora documentation site), `iru-setup-typescript-gitignore` (root `.gitignore`),
`iru-setup-typescript-github-workflows` (CI/CD workflows), `iru-setup-changelog` (root `CHANGELOG.md`), and
`iru-setup-readme` (root `README.md`). This skill does not duplicate any of their logic — it collects the shared
parameters once and passes each skill only the `args` keys it actually accepts, so the user isn't asked the same
question repeatedly.

Each of Steps 5–10 invokes its sub-skill via the `iru-isolated-skill-executor` agent (`subagent_type:
"iru-isolated-skill-executor"`, always naming the full `iru-`-prefixed skill inside the prompt, e.g.
`Skill({skill: "iru-setup-typescript-library", args: "..."})`) rather than calling `Skill(...)` directly — every
sub-skill re-derives whatever it needs from the filesystem this orchestrator has just written to, so only a short
completion summary needs to flow back, keeping all six sub-skills' full transcripts out of this orchestrator's own
context.

## Step 0 — Resolve inputs

This skill can be invoked stand-alone (`/iru-setup-typescript-repository`) or driven by another orchestrator, so
parse `args` first, as `key: value` lines, one per line, e.g.:

```
flavor: library
mode: new
open-source: yes
publish: yes
sonar: cloud
sonar-organization: example-github
sonar-project-key: example_my-library
sonar-host-url: https://sonarcloud.io
integration-branch: develop
stable-branch: main
node-version: 24
package-manager: npm
```

Recognized keys: `flavor` (`library`/`react`/`angular`/`react-native`/`ionic`), `mode` (`new`/`existing`),
`open-source` (`yes`/`no`), `publish` (`yes`/`no` — library only), `distribution` (`none`/`internal`/`store` —
react-native/ionic only), `sonar` (`cloud`/`self-hosted`/`none`) plus, only when set, `sonar-organization`/
`sonar-project-key`/`sonar-host-url`, `native-builds` (`eas`/`local` — react-native only), `framework`
(`angular`/`react` — ionic's own UI framework only), `integration-branch`, `stable-branch`, `node-version`,
`package-manager`, and every identity field named in Steps 2–3 below (`name`, `scope`, `app-id`, `description`,
`license`, `developer-name`, `developer-email`, `organization-url`, `directory`, `storybook`). Every key found here
is resolved — skip the matching question in Steps 1–4. Only keys genuinely missing from `args` still need asking.
If `args` is absent or doesn't look like this format, treat everything as unset and ask normally.

## Step 1 — Resolve the flavor and mode

Unless `flavor` was already supplied via `args`, resolve it in **two short rounds** (`AskUserQuestion` allows at
most four options per question, and five flavors don't fit in one):

- **Round 1**: *Library (published npm package)* / *React web app (Vite)* / *Angular web app* / *Mobile app
  (React Native or Ionic)*.
- **Round 2** (only if "Mobile app" was picked): *React Native (Expo-managed, over-the-air/EAS)* / *Ionic
  (Capacitor hybrid app, Angular or React UI)*. Sets `flavor` to `react-native` or `ionic` accordingly.
- **If `ionic` was picked**, ask one further bounded question — Ionic's own UI framework, a separate concern from
  this orchestrator's `flavor` and recorded as the `framework` key: **Angular** or **React**. `iru-setup-ionic-app`
  and (later) `iru-setup-typescript-github-workflows` both need this value.

Map the resolved `flavor` to its scaffold skill for the rest of this run:

| `flavor` | Scaffold skill |
|---|---|
| `library` | `iru-setup-typescript-library` |
| `react` | `iru-setup-react-web` |
| `angular` | `iru-setup-angular-web` |
| `react-native` | `iru-setup-react-native-app` |
| `ionic` | `iru-setup-ionic-app` |

If `mode` wasn't supplied via `args`, don't ask about it as an isolated question — check whether `package.json`
already exists at the repository root: if it does, default to `existing` and confirm with `AskUserQuestion`
(`existing` pre-selected; `new` as the other option, noting that "new" re-runs the scaffold and may discard
project-specific customizations, and that some flavors scaffold into a subdirectory rather than the root — see
Step 3); if it doesn't, default to `new` without asking further — there's nothing on disk yet to conflict with.

## Step 2 — Collect the project's identity

**`mode: existing` with the scaffold manifest already on disk** (`package.json` at the repository root, the same
check Step 5 uses to skip the scaffold): skip every identity question in this step — nothing downstream consumes
these answers once the scaffold is skipped (`iru-setup-readme` derives identity from the existing build files
itself), so asking them is a wasted question (verified against an existing repository). Resolve `license` only if `args` supplied it,
and record in the final report that project identity was taken from the existing files rather than asked.

For any field Step 0 already resolved from `args`, use that value directly. For everything else, ask the user
directly (plain conversation — these are free-text project-identity fields, not a bounded choice):

- **name** — the project name. Mapped to each scaffold skill's own key: `package-name` (library), `app-name`
  (react, react-native, ionic), or `name` (angular).
- **scope** — **library only**: the npm scope without the leading `@` (optional — ask whether the package should be
  scoped at all before asking for the scope itself).
- **app-id** — **ionic only**: the reverse-DNS application id, e.g. `com.example.myapp`.
- **app-slug** — **react-native only**: kebab-case; default to a slugified `name` rather than asking open-endedly,
  confirming with the user only if they want something different.
- **description** — one line. **Only asked for `library`/`react`/`ionic`** — `iru-setup-angular-web` and
  `iru-setup-react-native-app` accept no `description` key at all, so don't collect or pass one for those two
  flavors (a decision made here rather than inventing a key neither skill reads).
- **Developer name**, **developer email**, **organizationUrl**.

Then resolve the **license** with `AskUserQuestion` (one consistent choice reused across every flavor, since the
sub-skills' own recommended default order varies slightly and there's no need to track which):

- MIT License (recommended)
- Apache License 2.0
- No license (proprietary / all rights reserved)
- Other — ask for the license's display name (and SPDX id, if applicable) directly afterward

## Step 3 — Collect flavor-specific inputs

Only ask what applies to the resolved `flavor`; skip this step entirely for `library` (it has nothing here beyond
Step 2). For any field Step 0 already resolved from `args`, use that value directly.

- **`angular`**: **directory** — where to scaffold. If the repository root has no tracked files besides dotfiles,
  offer `.` as the default (the Angular project becomes the repository); otherwise ask explicitly, since
  `iru-setup-angular-web` can collide with existing root files. Then **storybook** (`AskUserQuestion`, default
  **No**) — needed here (not left to the sub-skill) because it also decides `docs-tool` in Step 8.
- **`react`**: **storybook** (`AskUserQuestion`, default **No**) — same reason as angular. **`keep-oxlint` is
  deliberately left unasked here** — it doesn't affect anything downstream of `iru-setup-react-web`, so that skill
  asks it directly when invoked without the key, instead of this orchestrator collecting it redundantly.
- **`react-native`**: **app-directory** — where to scaffold (if the repository root is otherwise empty, offer `.`;
  otherwise default to the resolved `app-slug` and confirm). **native-builds** (`AskUserQuestion`, default
  **`eas`** — cloud builds via Expo, noting the free tier's 15-builds/platform/month cap; **`local`** the
  alternative, needing a full native toolchain). This is collected here, not left to the scaffold skill alone,
  because `iru-setup-typescript-github-workflows` also needs it (Step 8) to pick the right `release.yml` variant.
- **`ionic`**: `framework` was already resolved in Step 1. **`add-android`/`add-ios` are deliberately left unasked
  here** — they don't affect anything outside `iru-setup-ionic-app` itself, so that skill asks them directly.

`distribution` (react-native/ionic) is resolved in Step 4 alongside `open-source`/`sonar`, since its default
depends on `open-source` per this catalog's shared convention.

## Step 4 — Collect the shared pipeline parameters

Ask the user directly, presenting each with its default so a plain "yes"/blank reply accepts it (skip any Step 0
already resolved from `args`):

| Parameter | Default |
|---|---|
| Integration branch | `develop` |
| Stable branch | `main` |
| Node version | `24` |
| Package manager | `npm` |

These map directly onto `iru-setup-typescript-github-workflows`'s own placeholders (Step 8) — nothing to translate.

Then resolve, with `AskUserQuestion`, per this catalog's shared open-source-driven convention:

- **open-source** — is this repository open source? Yes / No. Drives the recommended defaults below.
- **publish** — **library only**: default **Yes** when open-source is Yes; otherwise ask with **No** recommended
  (publishing to the public npm registry is meant for redistributable packages).
- **distribution** — **react-native/ionic only**: `none`/`internal`/`store`. Default **`store`** when open-source
  is Yes; otherwise ask with **`internal`** recommended (a closed-source app rarely targets the public stores).
- **sonar** — `cloud`/`self-hosted`/`none`. Recommend **`cloud`** when open-source is Yes; when not open source,
  state that SonarCloud is free only for open-source projects (a paid plan is required otherwise) and recommend
  **`none`**, offering **self-hosted SonarQube** as the second option. When `cloud`/`self-hosted` is chosen, also
  collect `sonar-organization`/`sonar-project-key`/`sonar-host-url` the same way every sub-skill's own Step 2 does
  (SonarCloud: suggest `<owner>-github` / `<owner>_<repo>` / `https://sonarcloud.io`, inferred from `git remote
  get-url origin`; self-hosted: ask for `sonar.host.url` directly, plus `sonar.organization` only if that server has
  organizations enabled, and `sonar.projectKey`).

These values (`open-source`, `publish`/`distribution`, `sonar` + detail keys) are passed through unchanged to Step 5
(the scaffold skill) and Step 8 (`iru-setup-typescript-github-workflows`) so neither sub-skill re-asks them.

## Step 5 — Run the flavor's scaffold skill

If `mode: existing` (Step 1) and `package.json` already exists at the repository root, skip invoking the scaffold
skill entirely — there's nothing to regenerate, and `mode: existing` means the user already confirmed they don't
want it replaced. Note in Step 11's report that `package.json` already existed and was left untouched, then
continue to Step 6 (the existing scaffold is presumed valid enough for the rest of the pipeline to build against).
Otherwise, format Steps 2–4's answers as `key: value` lines using **exactly** the keys the resolved flavor's skill
accepts (never an invented key) and invoke via `iru-isolated-skill-executor`. One example per flavor:

```
# flavor: library
Agent({
  description: "Run setup-typescript-library",
  subagent_type: "iru-isolated-skill-executor",
  prompt: "Invoke Skill({skill: \"iru-setup-typescript-library\", args: \"package-name: <name>\\nscope: <scope, if set>\\n
    description: <description>\\nlicense: <license>\\ndeveloper-name: <developer-name>\\n
    developer-email: <developer-email>\\norganization-url: <organization-url>\\nopen-source: <open-source>\\n
    publish: <publish>\\nsonar: <sonar>\\nsonar-organization: <..., if set>\\nsonar-project-key: <..., if set>\\n
    sonar-host-url: <..., if set>\\nintegration-branch: <integration-branch>\\nmode: <mode>\"}). Report back: whether package.json and the toolchain files
    were created fresh or already existed (and, if so, whether the user chose to stop), which devDependency
    versions came from a live registry lookup versus a fallback, and any value it resolved on its own.",
  run_in_background: false
})
```

`integration-branch` (Step 4's answer, default `develop`) is forwarded **only** to the `library` flavor: it's the
`baseBranch` `iru-setup-typescript-library` writes into `.changeset/config.json` when `publish: yes`, and without
it that file silently defaults to `main` while Step 8's workflows run on `develop`. The other four scaffold skills
have no such key — never send it to them.

The other four flavors follow the same shape, with only the `args` keys and skill name changed:

- **`react`**: `iru-setup-react-web` — `app-name`, `description`, `license`, `developer-name`, `developer-email`,
  `organization-url`, `open-source`, `sonar` (+ detail keys), `storybook`, `mode`. No `publish`/`distribution` key
  exists for this skill — never send one. `keep-oxlint` is deliberately omitted (Step 3) so the sub-skill asks it.
- **`angular`**: `iru-setup-angular-web` — `name`, `directory`, `license`, `developer-name`, `developer-email`,
  `organization-url`, `open-source`, `sonar` (+ detail keys), `storybook`, `mode`. No `description` key exists for
  this skill — never send one.
- **`react-native`**: `iru-setup-react-native-app` — `app-name`, `app-slug`, `app-directory`, `license`,
  `developer-name`, `developer-email`, `organization-url`, `open-source`, `sonar` (+ detail keys), `native-builds`,
  `distribution`, `mode`. No `description` key exists for this skill — never send one.
- **`ionic`**: `iru-setup-ionic-app` — `framework`, `app-name`, `app-id`, `description`, `license`,
  `developer-name`, `developer-email`, `organization-url`, `open-source`, `distribution`, `sonar` (+ detail keys),
  `mode`. `add-android`/`add-ios` are deliberately omitted (Step 3) so the sub-skill asks them.

Each sub-skill parses these itself (its own Step 0) and only asks the user about anything genuinely left out —
`AskUserQuestion` surfaces to the user the same way whether invoked directly or from inside this sub-agent. If it
reports that its own manifest file already existed and the user chose to stop, stop this skill here too — there's
no coherent project identity to build Antora docs or CI workflows around yet.

## Step 6 — Run `iru-setup-antora`

Invoke via `iru-isolated-skill-executor`: `Agent({description: "Run setup-antora", subagent_type:
"iru-isolated-skill-executor", prompt: "Invoke Skill({skill: \"iru-setup-antora\"}) with no args — it derives the
Antora component name, title, and version straight from the repository's package.json, so nothing needs to be
passed through. Report back: which files/pages were created vs. already present, and whether the site build
succeeded.", run_in_background: false})`.

Run this *before* Step 8, not after, even though the user might expect them in the other order:
`iru-setup-antora` is quick to detect as "already done", and `iru-setup-typescript-github-workflows`'s own survey
(Step 1 there) checks whether `docs/antora.yml`/`docs/antora-playbook.yml` already exist — running Antora setup
first means that check finds everything in place instead of flagging a gap.

## Step 7 — Run `iru-setup-typescript-gitignore`

Invoke via `iru-isolated-skill-executor`: `Agent({description: "Run setup-typescript-gitignore", subagent_type:
"iru-isolated-skill-executor", prompt: "Invoke Skill({skill: \"iru-setup-typescript-gitignore\"}) with no args — it
takes none, deriving everything it needs (package manager, framework, Playwright, docs tooling) by exploring the
repository directly. Report back only whether .gitignore was created fresh or, if it already existed, whether the
user accepted or skipped the proposed diff.", run_in_background: false})`. Run this after Steps 5–6, not before:
detection depends on the scaffold's lockfile/framework signals and the Antora config Step 6 just wrote. Run it
*before* Step 8, so `node_modules/`, `dist/`, `coverage/`, and the Antora build output are already ignored before
CI-generated reports show up locally.

## Step 8 — Run `iru-setup-typescript-github-workflows`

First derive `docs-tool` from the resolved `flavor` and Step 3's `storybook` answer — checked against what each
scaffold skill actually wires up, not assumed:

| `flavor` | `docs-tool` |
|---|---|
| `library` | `typedoc` (`iru-setup-typescript-library` always writes `typedoc.json`) |
| `angular` | `compodoc` (`iru-setup-angular-web` always adds a `docs` script running Compodoc) |
| `react` | `storybook` if Step 3's `storybook` answer was Yes, else `none` |
| `react-native` | `none` — `iru-setup-react-native-app` has no Storybook option at all |
| `ionic` | `none` — `iru-setup-ionic-app` has no Storybook option at all |

Format Steps 1–4's answers as `key: value` lines and invoke via `iru-isolated-skill-executor`:

```
Agent({
  description: "Run setup-typescript-github-workflows",
  subagent_type: "iru-isolated-skill-executor",
  prompt: "Invoke Skill({skill: \"iru-setup-typescript-github-workflows\", args: \"flavor: <flavor>\\n
    integration-branch: <integration-branch>\\nstable-branch: <stable-branch>\\nnode-version: <node-version>\\n
    package-manager: <package-manager>\\nopen-source: <open-source>\\npublish: <publish, library only>\\n
    distribution: <distribution, react-native/ionic only>\\nsonar: <sonar>\\n
    sonar-organization: <..., if set>\\nsonar-project-key: <..., if set>\\nsonar-host-url: <..., if set>\\n
    native-builds: <native-builds, react-native only>\\nframework: <framework, ionic only>\\n
    docs-tool: <docs-tool>\\nmode: <mode>\"}). Report back: whether build.yml/release.yml/sync.yml/security.yml and
    .github/dependabot.yml were created fresh, updated, or already existed (and, if so, whether the user chose to
    stop), and the full required-secrets table it produced for this flavor/options.",
  run_in_background: false
})
```

Omit `publish`/`distribution`/`native-builds`/`framework` entirely when they don't apply to the resolved `flavor`
(never send a key the flavor doesn't use). `mode` is always passed: with `mode: existing`,
`iru-setup-typescript-github-workflows` takes its own update/gap-fill path on any workflow file already present
(its Step 2) without asking the stop-or-update question — this is what makes this orchestrator's `mode:
existing` promise hold for the CI step; with `mode: new` (or unset) it asks as usual. The four `security-*` keys
are deliberately never passed — they each default to `yes` inside `iru-setup-typescript-github-workflows` itself,
and this orchestrator doesn't ask about them separately; note this once in Step 11's report rather than re-asking
per run. If it reports that the workflow files already existed and the user chose to stop (only possible when
`mode` isn't `existing`), note that in Step 11's report rather than treating it as a failure of this skill — the
scaffold, the Antora docs, and the `.gitignore` from Steps 5–7 are still valid on their own.

## Step 9 — Run `iru-setup-changelog`

Invoke via `iru-isolated-skill-executor`: `Agent({description: "Run setup-changelog", subagent_type:
"iru-isolated-skill-executor", prompt: "Invoke Skill({skill: \"iru-setup-changelog\"}) with no args — it takes
none, working entirely from the repository's own git tag/GitHub Release history. Report back only whether
CHANGELOG.md was created (and the version range reconstructed) or already existed.", run_in_background: false})`.
Position relative to Steps 5–8 doesn't matter functionally — it's independent of all of them. If `CHANGELOG.md`
already exists, it stops immediately and reports that regardless of `mode` — not a failure of this skill, just
something to note in Step 11's report. Running it before `iru-setup-readme` means the README's Documentation
section sees it already in place.

## Step 10 — Run `iru-setup-readme`

Invoke via `iru-isolated-skill-executor`: `Agent({description: "Run setup-readme", subagent_type:
"iru-isolated-skill-executor", prompt: "Invoke Skill({skill: \"iru-setup-readme\", args: \"sonar: <sonar>\"}) — `sonar` is the only key it accepts (with `none` it suppresses Sonar badges/links even if Sonar config exists on disk),
deriving everything it needs by exploring the repository directly (package.json, the Antora docs, .gitignore, the
workflows and Sonar config, and CHANGELOG.md). Report back only which sections were included vs. omitted and why.",
run_in_background: false})`. Run this last, after every other skill, so its badges/status-table/documentation-links
sections see the finished state of Steps 5–9 instead of a sparser mid-run snapshot. In `mode: new`, most
CI/Sonar/changelog-derived sections will still be sparse or absent (no commits/tags/CI runs yet) — expected;
`iru-setup-readme` omits what it can't confirm rather than inventing it.

## Step 11 — Report

Summarize the outcome of all six delegated skills together: the resolved `flavor` and `mode`, the project identity
and license, the pipeline parameters used, and which of the scaffold's own files, the Antora docs site, the
`.gitignore`, the workflow files (`build.yml`/`release.yml`/`sync.yml` where applicable/`security.yml`/
`.github/dependabot.yml`), `CHANGELOG.md`, and `README.md` were created, updated, or left untouched (per any stop
choice in Steps 5 or 8, or a `mode: existing` skip in Step 5).

State explicitly which of publishing/distribution and Sonar analysis were wired, or deliberately omitted and why:

- **`open-source`**: yes/no, as resolved in Step 4.
- **`publish`** (library) / **`distribution`** (react-native, ionic): whether the corresponding scaffold config and
  `release.yml` job were included — `yes`/non-`none` unless the user opted out (or the project isn't open source
  and declined it), stated plainly rather than left implicit.
- **`sonar`**: `cloud`/`self-hosted`/`none`, and whether `sonar-project.properties` and the `Run SonarQube/SonarCloud
  analysis` workflow step were included — if `none`, note whether that's the expected non-open-source default or a
  direct user choice.
- **`docs-tool`**: the value derived in Step 8 and why (flavor, plus the `storybook` answer for `react`).

Reproduce the **consolidated required-secrets/settings table** `iru-setup-typescript-github-workflows` reported in
Step 8 verbatim (it's already scoped to exactly this flavor/options — don't re-derive or expand it), plus its
repository-settings notes (GitHub Pages source = GitHub Actions, "Workflow permissions" allowing PR creation for
`sync.yml`, the npmjs.com trusted-publisher relationship for `publish: yes`).

List every decision made on the user's behalf: the license question's fixed MIT-first ordering (Step 2), leaving
`keep-oxlint`/`add-android`/`add-ios` for their sub-skills to ask (Step 3), the mobile flavors' `docs-tool: none`
default (Step 8), and the four `security-*` flags left at their `yes` default (Step 8).

Finish with an explicit **Warn explicitly** block, repeating each sub-skill's own closing warning:

- **Review every generated/updated file before building, committing, or relying on CI.** Confirm the license
  matches an actual `LICENSE` file if one was chosen (`iru-check-license` can generate one and backfill headers),
  and that `npm run build && npm test && npm run typecheck` (or the flavor's equivalent scripts) succeed.
- If `sonar: cloud`/`self-hosted` was chosen, a `SONAR_TOKEN` repository secret and an actual SonarCloud/SonarQube
  project matching `sonar.projectKey` still need to exist before a CI-run Sonar scan will succeed.
- If `publish: yes`/`distribution: store` was chosen, the registry/store credentials named in the secrets table
  still need to exist before a CI-driven publish/submit will succeed — nothing in this pipeline creates or stores
  them.
- Every devDependency/action version the scaffold and workflows skills wrote was resolved via a run-time lookup (or
  its recorded fallback) — re-run `npm outdated` before relying on this scaffold long-term.
