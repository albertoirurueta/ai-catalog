---
name: iru-setup-java-library-repository
description: End-to-end bootstrap for a Java/Maven library repository — collects the project's identity (groupId, artifactId, base package, developer name/email/organizationUrl, license), pipeline parameters (integration branch, Java version, publishing server id, sign/extras profile ids, Maven settings file), and whether the project is open source, publishes to Maven Central, and runs SonarCloud/self-hosted SonarQube/no Sonar analysis, once, then orchestrates `iru-setup-java-library` (pom.xml + source folders), `iru-setup-antora` (documentation site), `iru-setup-java-gitignore` (root `.gitignore`), `iru-setup-java-github-workflows` (CI/CD workflows), `iru-setup-changelog` (root CHANGELOG.md), and `iru-setup-readme` (root README.md) in that order so nothing is asked twice. Invoke as `/iru-setup-java-library-repository`, optionally with `args` (`key: value` lines) to pre-resolve `mode` (`new`/`existing`), `open-source` (`yes`/`no`), `publish` (`yes`/`no`), `sonar` (`cloud`/`self-hosted`/`none`, plus `sonar-organization`/`sonar-project-key`/`sonar-host-url` when set) and skip the matching question. Each pipeline parameter has the same default as the skill it feeds (`develop`, `21`, `central`, `build-extras`, `sign`, `mvnsettings.xml`) and can be overridden; `publish`/`sonar` default per whether the project is open source (see Step 2). In `mode: existing` it skips regenerating an already-present `pom.xml` and tells every downstream step to take its own update/gap-fill path instead of assuming a brand-new repository. Use when bootstrapping (or catching up) a Java library repository's full pom/docs/gitignore/CI/changelog/README scaffold in one pass, instead of running the skills separately and re-answering the same questions each time.
model: haiku
---

# Setup Java Library Repository

Bootstrap a brand-new Java/Maven library repository in one pass by orchestrating six existing skills:
`iru-setup-java-library` (writes `pom.xml` and the `src/main/java|resources`/`src/test/java` folders),
`iru-setup-antora` (scaffolds the Antora documentation site), `iru-setup-java-gitignore` (writes or updates the root
`.gitignore`), `iru-setup-java-github-workflows` (writes `develop.yml`/`main.yml`), `iru-setup-changelog` (bootstraps a
root `CHANGELOG.md`), and `iru-setup-readme` (bootstraps a root `README.md`). This skill does not duplicate their
logic — it collects the shared parameters once and passes each skill only what it needs, so the user isn't asked
the same question repeatedly.

Each of Steps 3–8 invokes its sub-skill via the `iru-isolated-skill-executor` agent rather than calling `Skill(...)`
directly. Every sub-skill already re-derives whatever it needs straight from the filesystem this orchestrator has
just written to (as each step below notes), so this orchestrator only ever needs a short completion summary back
— nothing is lost by keeping each sub-skill's own exploration, file reads, and internal reasoning out of this
orchestrator's own context. Without this, all six sub-skills' full transcripts would accumulate in one
conversation over the course of a single bootstrap run.

## Step 0 — Resolve inputs

This skill can be invoked stand-alone (`/iru-setup-java-library-repository`) or driven by another orchestrator, so
parse `args` first, as `key: value` lines, one per line, e.g.:

```
mode: new
open-source: yes
publish: yes
sonar: cloud
sonar-organization: example-github
sonar-project-key: example_my-library
sonar-host-url: https://sonarcloud.io
```

Recognized keys: `mode` (`new` or `existing`), `open-source` (`yes`/`no`), `publish` (`yes`/`no`), `sonar`
(`cloud`/`self-hosted`/`none`), and — only when `sonar` is `cloud` or `self-hosted` — `sonar-organization`,
`sonar-project-key`, `sonar-host-url`. Every key found here is resolved — skip the matching question in Step 2.
Only keys genuinely missing from `args` still need asking. If `args` is absent or doesn't look like this format,
treat everything as unset and ask normally.

If `mode` wasn't supplied via `args`, don't ask about it as an isolated question — check whether `pom.xml` already
exists at the repository root: if it does, default to `existing` and confirm with `AskUserQuestion` (`existing`
pre-selected; `new` as the other option, noting that "new" regenerates `pom.xml` from scratch via Step 3 and may
discard project-specific customizations); if it doesn't, default to `new` without asking further — there's nothing
on disk yet to conflict with.

## Step 1 — Collect the project's identity

Ask the user directly (plain conversation — these are free-text project-identity fields, not a bounded choice):

- **groupId** — e.g. `com.example`.
- **artifactId** — e.g. `my-library`.
- **Base package** — the library's base Java package (e.g. `com.example.mylibrary`); need not equal `groupId`.
- **Developer name**, **developer email**, **organizationUrl**.

Then resolve the **license** with `AskUserQuestion` (mirrors `iru-setup-java-library`'s own choice, resolved once
here so it isn't asked again):

- Apache License 2.0 (recommended) — `The Apache License, Version 2.0` /
  `http://www.apache.org/licenses/LICENSE-2.0.txt`
- MIT License — `The MIT License` / `https://opensource.org/license/mit`
- No license (proprietary / all rights reserved)
- Other — ask for the license's display name and URL directly afterward

Leave `version` unset here — `iru-setup-java-library` applies its own `1.0.0-SNAPSHOT` default and isn't worth asking
about twice at this level.

## Step 2 — Collect the pipeline parameters

Ask the user directly, presenting each with its default so a plain "yes"/blank reply accepts it:

| Parameter | Default           |
|---|-------------------|
| Integration branch | `develop`         |
| Java version | `21`              |
| Publishing server id | `central`         |
| Extras profile id | `build-extras`    |
| Sign profile id | `sign`            |
| Maven settings file | `mvnsettings.xml` |

These map directly onto `iru-setup-java-github-workflows`'s own six placeholders — same names, same defaults — so
there's nothing to translate before Step 4. The Java version additionally feeds `iru-setup-java-library` in Step 3
(as its `java-version` arg, whose default is the same `21`), so `pom.xml`'s `maven.compiler.source`/`target` and
the JDK the workflows set up always agree.

Then resolve three more choices with `AskUserQuestion`, skipping any already resolved by Step 0's `args`:

| Parameter | Default |
|---|---|
| Open source (`open-source`) | asked directly, no default |
| Publish to Maven Central (`publish`) | `yes` when open source; otherwise asked, `no` recommended |
| Sonar (`sonar`) | `cloud` when open source; otherwise asked, `none` recommended |

- **open-source** — is this repository open source? Yes / No. This answer drives the recommended defaults for the
  next two questions, per this catalog's shared convention.
- **publish** (Maven Central) — default **Yes** when open-source is Yes; when not open source, ask with **No**
  recommended, explaining that Maven Central is meant for publishing redistributable artifacts other projects
  depend on, which usually isn't appropriate for closed-source code.
- **sonar** — recommend **SonarCloud** (`cloud`) when open-source is Yes; when not open source, state that
  SonarCloud is free only for open-source projects (a paid plan is required otherwise) and recommend **None**
  (`none`), offering **self-hosted SonarQube** as the second option. When `cloud` or `self-hosted` is chosen, also
  collect `sonar-organization`/`sonar-project-key`/`sonar-host-url` the same way `iru-setup-java-library`'s own
  Step 2 does (SonarCloud: suggest `<owner>-github` / `<owner>_<repo>` / `https://sonarcloud.io`; self-hosted: ask
  for `sonar.host.url` directly, plus `sonar.organization` only if that server has organizations enabled, and
  `sonar.projectKey`).

These four values (`open-source`, `publish`, `sonar` and its detail keys) are passed through unchanged to Step 3
(`iru-setup-java-library`) and Step 6 (`iru-setup-java-github-workflows`) so neither sub-skill re-asks them.

## Step 3 — Run `iru-setup-java-library`

If `mode: existing` (from Step 0) and `pom.xml` already exists at the repository root, skip invoking
`iru-setup-java-library` entirely — there's nothing to regenerate, and `mode: existing` means the user already
confirmed they don't want it replaced. Note in Step 9's report that `pom.xml` already existed and was left
untouched, then continue to Step 4 (the existing `pom.xml` is presumed valid enough for the rest of the pipeline to
build against). Otherwise (a genuinely new `pom.xml`, or `mode: new` explicitly regenerating one), format Step 1's
answers — plus the Java version and the `open-source`/`publish`/`sonar` (+ detail keys) answers from Step 2, so
`pom.xml`'s compiler level and the CI pipeline Step 6 generates can't end up targeting different Java versions or
disagreeing about publishing/Sonar — as `key: value` lines and invoke via `iru-isolated-skill-executor`:

```
Agent({
  description: "Run setup-java-library",
  subagent_type: "iru-isolated-skill-executor",
  prompt: "Invoke Skill({skill: \"iru-setup-java-library\", args: \"groupId: <group-id>\\nartifactId: <artifact-id>\\n
    package: <base-package>\\ndeveloper-name: <developer-name>\\ndeveloper-email: <developer-email>\\n
    organization-url: <organization-url>\\nlicense: <license-name, or 'none'>\\n
    java-version: <java-version>\\nopen-source: <open-source>\\npublish: <publish>\\nsonar: <sonar>\\n
    sonar-organization: <sonar-organization, if set>\\nsonar-project-key: <sonar-project-key, if set>\\n
    sonar-host-url: <sonar-host-url, if set>\"}). Report back: whether pom.xml
    and the source folders were created fresh or already existed (and, if so, whether the user chose to stop),
    and any value it resolved on its own (e.g. version, repository info) worth noting in the final summary.",
  run_in_background: false
})
```

`iru-setup-java-library` parses these itself (its own Step 0) and only asks the user about anything genuinely left
out (e.g. `version`, or repository info it infers from git directly) — `AskUserQuestion` surfaces to the user the
same way whether invoked directly or from inside this sub-agent. If it reports that `pom.xml` already existed and
the user chose to stop, stop this skill here too — there's no coherent project identity to build Antora docs or
CI workflows around yet.

## Step 4 — Run `iru-setup-antora`

Invoke via `iru-isolated-skill-executor`: `Agent({description: "Run setup-antora", subagent_type:
"iru-isolated-skill-executor", prompt: "Invoke Skill({skill: \"iru-setup-antora\"}) with no args — it derives the Antora
component name, title, and version straight from the repository's pom.xml, so nothing needs to be passed through.
Report back: which files/pages were created vs. already present, and whether the site build succeeded.",
run_in_background: false})`.

Run this *before* Step 6, not after, even though the user described these two in the other order: `iru-setup-antora`
is quick to detect as "already done" and `iru-setup-java-github-workflows`'s own survey (Step 1 there) checks whether
`docs/antora.yml`/`docs/antora-playbook.yml` already exist — running Antora setup first means that check finds
everything in place instead of flagging a gap it would otherwise ask about.

## Step 5 — Run `iru-setup-java-gitignore`

Invoke via `iru-isolated-skill-executor`: `Agent({description: "Run setup-java-gitignore", subagent_type:
"iru-isolated-skill-executor", prompt: "Invoke Skill({skill: \"iru-setup-java-gitignore\"}) with no args — it takes none,
deriving everything it needs by exploring the repository directly. Report back only whether .gitignore was
created fresh or updated, and what categories of entries it added.", run_in_background: false})`. Run this after
Steps 3–4, not before: `iru-setup-java-gitignore` detects the build tool and any generated build-info file from the
`pom.xml` Step 3 just wrote, and detects the Antora docs build output from the `docs/antora-playbook.yml` Step 4
just scaffolded — running it earlier would miss both and produce a thinner `.gitignore` than the repository's
actual shape supports. Run it *before* Step 6 (`iru-setup-java-github-workflows`), so `target/`, `.idea/`, and the
Antora build output are already ignored before CI config and any generated reports show up locally. In `mode: new`,
`.gitignore` typically won't already exist, so `iru-setup-java-gitignore`'s own approval step is skipped and it
writes directly. In `mode: existing`, it may already exist — that's expected, not an error, and
`iru-setup-java-gitignore` takes its own gap-fill/update path (it explores the repository directly, it isn't told
`mode` explicitly) rather than this orchestrator assuming a blank slate.

## Step 6 — Run `iru-setup-java-github-workflows`

Format Step 2's answers, plus the `groupId`/`artifactId` already collected in Step 1, as `key: value` lines and
invoke via `iru-isolated-skill-executor`:

```
Agent({
  description: "Run setup-java-github-workflows",
  subagent_type: "iru-isolated-skill-executor",
  prompt: "Invoke Skill({skill: \"iru-setup-java-github-workflows\", args: \"integration-branch: <integration-branch>\\n
    java-version: <java-version>\\npublishing-server-id: <publishing-server-id>\\n
    extras-profile-id: <extras-profile-id>\\nsign-profile-id: <sign-profile-id>\\n
    settings-file: <settings-file>\\ngroup-id: <group-id>\\nartifact-id: <artifact-id>\\n
    open-source: <open-source>\\npublish: <publish>\\nsonar: <sonar>\\n
    sonar-organization: <sonar-organization, if set>\\nsonar-project-key: <sonar-project-key, if set>\\n
    sonar-host-url: <sonar-host-url, if set>\"}). Report back: whether
    develop.yml/main.yml/sync.yml/security.yml/.github/dependabot.yml were created fresh or already existed (and,
    if so, whether the user chose to stop), the required GitHub secrets it listed, and any open gap it flagged
    (missing Central plugin, missing signing profile, missing Antora setup, README/Antora wording mismatch, etc.).",
  run_in_background: false
})
```

Passing `open-source`/`publish`/`sonar` (+ detail keys) through here keeps this workflow generation in agreement
with what Step 3 wrote into `pom.xml` — e.g. it never generates a `Deploy to maven central` step for a `pom.xml`
that has no `central-publishing-maven-plugin`, or a `Run SonarCloud analysis` step for one with no
`sonar-maven-plugin`.

Passing `group-id`/`artifact-id` through here lets `iru-setup-java-github-workflows` skip re-reading them from
`pom.xml` in its own Step 1, since this orchestrator already collected both in its own Step 1.
`iru-setup-java-github-workflows` parses these itself (its own Step 1) and only surveys/asks about facts these
parameters don't cover (static-analysis plugins, SonarQube config, branch-model confirmation, etc.). If it reports
that `develop.yml`/`main.yml` already existed and the user chose to stop, note that in Step 9's report rather than
treating it as a failure of this skill — `pom.xml`, the Antora docs, and the `.gitignore` from Steps 3–5 are still
valid on their own.

## Step 7 — Run `iru-setup-changelog`

Invoke via `iru-isolated-skill-executor`: `Agent({description: "Run setup-changelog", subagent_type:
"iru-isolated-skill-executor", prompt: "Invoke Skill({skill: \"iru-setup-changelog\"}) with no args — it takes none,
working entirely from the repository's own git tag/GitHub Release history. Report back only whether
CHANGELOG.md was created (and the version range reconstructed) or already existed.", run_in_background: false})`.
Run this before `iru-setup-readme` (Step 8): it's independent of `pom.xml`, the Antora docs, the `.gitignore`, and the
workflows, so its position relative to them doesn't matter functionally. In `mode: new` (no tags yet) it's the
fastest to resolve — it either bootstraps a minimal `## [Unreleased]`-only file or stops per the user's choice, per
its own Step 2. In `mode: existing`, real tag/release history may already exist, so it can backfill more than a
placeholder. If `CHANGELOG.md` already exists, it stops immediately and reports that regardless of `mode` — treat
that the same way as the stop cases in Steps 3 and 6: not a failure of this skill, just something to note in
Step 9's report. Running it before `iru-setup-readme` means the README's own Documentation section (which links to
`CHANGELOG.md` if present) sees it already in place.

## Step 8 — Run `iru-setup-readme`

Invoke via `iru-isolated-skill-executor`: `Agent({description: "Run setup-readme", subagent_type:
"iru-isolated-skill-executor", prompt: "Invoke Skill({skill: \"iru-setup-readme\", args: \"sonar: <sonar>\"}) — `sonar` is the only key it accepts (with `none` it suppresses Sonar badges/links even if Sonar config exists on disk), deriving
everything it needs by exploring the repository directly (pom.xml, the Antora docs, .gitignore, the workflows and
Sonar config, and CHANGELOG.md). Report back only which sections were included vs. omitted and why.",
run_in_background: false})`. Run this last, after every other skill: `iru-setup-readme`'s badges, documentation links,
and project-status table are only as complete as what already exists on disk when it runs, so giving it the
finished state of Steps 3–7 to explore produces a fuller README than running it earlier would. In `mode: new`,
most of the CI/Sonar/changelog-derived sections will still be sparse or absent at this point (no commits/tags/CI
runs yet) — that's expected; `iru-setup-readme` omits what it can't confirm rather than inventing it, and the
README can be regenerated later once the repository has real history. In `mode: existing`, real history typically
already exists, so more sections should populate. `README.md` may or may not already exist depending on `mode`;
`iru-setup-readme`'s own approval step (its Step 9) handles that on its own — nothing further to confirm here.

## Step 9 — Report

Summarize the outcome of all six delegated skills together: the resolved project identity and license, the
pipeline parameters used, the resolved `mode` (`new`/`existing`), and which of `pom.xml`/source folders, the Antora
docs site, the `.gitignore`, the workflow files (`develop.yml`/`main.yml`/`sync.yml`/`security.yml`/
`.github/dependabot.yml`), `CHANGELOG.md`, and `README.md` were created, updated, or left untouched (per any stop
choice in Steps 3, 6, or 7, or a `mode: existing` skip in Step 3), and the required GitHub secrets
`iru-setup-java-github-workflows` listed.

State explicitly which of Maven Central publishing and Sonar analysis were wired, or deliberately omitted and why:

- **`open-source`**: yes/no, as resolved in Step 2.
- **`publish`**: whether `central-publishing-maven-plugin`/the `sign` profile were included in `pom.xml` and the
  `Deploy to maven central` step in the workflows — `yes` unless the user opted out (or the project isn't open
  source and declined it), in which case say so plainly rather than leaving it implicit.
- **`sonar`**: `cloud`/`self-hosted`/`none`, and whether the `sonar.*` properties/`sonar-maven-plugin` and the
  `Run SonarCloud analysis` workflow step were included — if `none`, note that this is expected default behavior
  for a non-open-source project (SonarCloud requires a paid plan otherwise) unless the user explicitly asked for
  self-hosted SonarQube instead.

Note which README sections `iru-setup-readme` omitted for lack of material (expected in `mode: new`, or for a
repository still short on history). Repeat its closing warning here too: **review every generated file before
building, committing, or relying on CI** — `mvn validate` should succeed, the license should match an actual
`LICENSE` file if one was chosen, the workflow's inferred branch/profile/publishing values should be double checked
before the first real push or release, and the README's "How It Works" example should be verified once real source
code exists.
