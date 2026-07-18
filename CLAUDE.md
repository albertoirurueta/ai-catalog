# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

`ai-catalog` is a collection of Claude Code Skills — reusable, version-controlled playbooks for common
software engineering workflows, each invoked on demand with a slash command (`/iru-plan`, `/iru-pr-review`, etc.).
There is no application code, no `pom.xml`/`package.json` at the root, and nothing to compile or unit-test
in this repository itself — the deliverable is the skills (and the Antora docs describing them).

## Commands

The only buildable artifact is the Antora documentation site under `docs/`:

```bash
cd docs && npm ci                          # install Antora + extensions (only needed once / after changes)
cd docs && npx antora antora-playbook.yml  # build the site into docs/build/site (gitignored, generated)
```

CI (`.github/workflows/docs.yml`) runs the same build and publishes `docs/build/site` to the `gh-pages`
branch on every push to `main`. There is no separate lint/test command for this repository.

## Architecture

### Skills (`.claude/skills/<name>/SKILL.md`)

Every skill and agent in this catalog carries an `iru-` prefix (directory name, frontmatter `name`, and every
cross-reference to it) so its slash command can't collide with a same-named skill installed from another
marketplace once both sit side by side in a consuming repository's `.claude/skills/`. Any new skill or agent
added to this catalog must follow the same convention — see
`docs/modules/ROOT/pages/guides/creating-skills-and-agents.adoc`.

Each skill is a single, self-contained `SKILL.md` file: YAML frontmatter with `name` and `description` (the
description is what Claude Code uses to decide when the skill is relevant — it should state the exact
invocation form, e.g. `/iru-check-license` or `/iru-check-license <path-or-glob>`), followed by step-by-step
instructions written for an agent to follow. A skill is adopted by another repository by copying its
directory into that repository's `.claude/skills/` — skills must not assume they're running inside
`ai-catalog` itself (they detect language/platform/tooling at runtime rather than hardcoding it).

Skills compose into a few recurring pipelines rather than each standing alone:

- **Issue-to-PR cycle**: `iru-issue` → `iru-explore` → `iru-plan` → `iru-code` → `iru-pr-description` → `iru-pr-review`. `iru-plan` groups
  `implementation_plan.md`'s tasks into dependency-aware groups; `iru-code` doesn't implement anything itself — it
  dispatches each group, in order, to `iru-code-one-task-group`, which resolves each task's language and delegates
  to the matching `<key>-code-one-task-group` skill (`iru-java-code-one-task-group`, `iru-dotnet-code-one-task-group`).
  That skill captures one quality baseline for the whole group, runs `<key>-code-one-task`
  (`iru-java-code-one-task`, `iru-dotnet-code-one-task`) once per task — in parallel when the group allows it — and
  validates the group once (tests/coverage/quality/doc/license), instead of once per task.
- **Repository bootstrap**: `iru-setup-java-library-repository` orchestrates `iru-setup-java-library` →
  `iru-setup-antora` → `iru-setup-java-gitignore` → `iru-setup-java-github-workflows` → `iru-setup-changelog` →
  `iru-setup-readme` in a fixed order for a brand-new Java library repo; each also runs standalone.
- **Ticket intake**: `iru-create-github-issue` / `iru-create-jira-ticket` ground a draft in the codebase via
  `iru-explore` before filing.

### Agents (`.claude/agents/<name>.md`)

This repository defines three custom agents for its most-duplicated sub-agent shapes:

- **`iru-gate-runner`** — runs a single verification/quality-gate skill (tests, coverage, code-quality/lint, license
  headers, doc-comment audits, security scans, or a full build), optionally diffs it against a baseline, and
  reports back only a compact summary. Used throughout `iru-code`, `iru-code-one-task-group`, `iru-java-code-one-task-group`,
  and `iru-dotnet-code-one-task-group`, and recommended by `iru-plan` for the scoped test-run step it writes into
  generated plans.
- **`iru-isolated-skill-executor`** — runs one named skill end-to-end in a completely fresh context so an earlier
  exploration/planning transcript can't bias it, while the caller keeps running afterward. Used by `iru-issue` to
  delegate the entire `iru-code` run for a ticket.
- **`iru-change-summarizer`** — fans out over a git commit/tag range and returns only the user-facing changes.
  Used by `iru-setup-changelog` to summarize one release at a time when backfilling a long tag history.

Skills that need ad hoc context isolation beyond these three shapes still use Claude Code's *built-in* agent
types via the `Agent` tool: `iru-explore` uses the `Explore` agent explicitly; one-off cases like bootstrapping
`iru-setup-antora` mid-run (`iru-generate-skill-docs`, `iru-update-docs`) use `general-purpose`, the default.

### Documentation (`docs/`)

An Antora site (`docs/antora.yml`, `docs/antora-playbook.yml`) with two kinds of pages under
`docs/modules/ROOT/pages/`, which matters because they're maintained differently:

- **Generated**: `index.adoc`, every `skills/*.adoc`, and `agents/*.adoc` are regenerated by the
  `iru-generate-skill-docs` skill (`/iru-generate-skill-docs`) directly from the
  `SKILL.md` files and agent usage actually on disk, including the reference table, dependency graph, and
  purpose groups. Re-run it after adding, removing, or materially changing a skill — hand edits to these
  pages are overwritten on the next run.
- **Hand-maintained**: everything under `guides/` (`claude-md.adoc`, `common-workflows.adoc`,
  `creating-skills-and-agents.adoc`, etc.) is regular prose, edited directly like any other doc.

`nav.adoc` lists every page and must gain an entry when a new skill or guide page is added (the
`iru-generate-skill-docs` skill handles this for generated pages automatically).

`docs/build/` is gitignored — never hand-edit generated site output.
