# tools/

Maintenance scripts for the catalog itself. None of them is part of what a consuming repository installs: they
measure and guard the skills and agents under `.claude/`.

## `catalog-audit.py`

Audits every `.claude/skills/*/SKILL.md` and `.claude/agents/*.md`. Requires Python 3.9+ and PyYAML
(`pip install pyyaml`); everything else is standard library.

Per skill and agent it collects: bytes, lines, frontmatter keys, `model`, `description` length, the position of the
first `/iru-` or `Invoke as` in the description, bytes inside fenced code blocks, total bytes of supporting files,
`Skill({skill: ...})` targets, `subagent_type` dispatch counts, and whether the frontmatter parses with
`yaml.safe_load` (when it does not, `model` and `description` are read leniently so the metrics still exist).
Across the catalog it also computes duplicate supporting files by SHA-256 (groups and redundant bytes), the md5
set of each shared byte-identical file (`ui-contract.md`, `cli-contract.md`, `ui-docs.md`,
`accessibility-detection.md`), `Skill()` targets that do not exist, and **inline cross-model calls**: a `Skill()`
call whose caller `model` differs from the callee's and that is not inside an `Agent({...})` prompt string (the
cache-hit penalty case). The report flags calls whose preceding prose already mentions `iru-gate-runner` or
`iru-isolated-skill-executor`, which usually are delegated and need a manual look.

```bash
python3 tools/catalog-audit.py --json out.json     # full data
python3 tools/catalog-audit.py --markdown          # summary tables on stdout
python3 tools/catalog-audit.py --check             # budgets; exit 1 on any error-level violation
python3 tools/catalog-audit.py --plan FILE         # plan shape (see "Checking an implementation plan")
```

The modes can be combined. `--budgets FILE` and `--root DIR` override the budgets file and the repository root.
Output is deterministic (no timestamps), so two runs on the same tree are byte-identical.

### Running `--check` locally

```bash
python3 tools/catalog-audit.py --check
```

Violations go to stderr, one per line (`ERROR [rule] subject: message`), followed by a count. Only errors change
the exit status; warnings are informational. Typical rules: `description-max`, `invocation-form-position`,
`frontmatter-parse`, `skill-lines-max`, `agent-model-missing`, `shared-file-drift`, `skill-target-missing`, `asset-path-missing`, `template-unreferenced`. Run it
before opening a pull request that touches a skill or agent.

### Template and reference paths

Skills keep their generated-file templates under `templates/<variant>/<generated path>` and their guidance under
`reference/`, inside the skill directory. `--check` verifies both directions:

- `asset-path-missing`: every `templates/...` path that `SKILL.md` names must exist in that skill; every
  `reference/...` path must exist in that skill **or in another skill** (sibling skills legitimately point at each
  other's reference files). Paths with placeholders or wildcards (`{...}`, `<...>`, `*`) and paths preceded by
  another directory (`src/templates/...`) are not checked. Paths that name something in the *target* repository
  rather than in the skill are listed per skill under `asset_path_ignore` in the budgets file.
- `template-unreferenced`: every file under a skill's `templates/` must appear in `SKILL.md` by its full relative
  path (normally in the "Templates" index table), so no template can be orphaned.

### Checking an implementation plan

```bash
python3 tools/catalog-audit.py --plan implementation_plan.md
```

`--plan FILE` checks the shape that `iru-plan` writes and `iru-code` relies on, independently of the catalog budgets
(it may be combined with `--check`, `--json` and `--markdown`; alone it skips the catalog audit). Exit status is `0`
when the plan is clean, `1` on any violation and `2` when the file cannot be read. Violations go to stderr as
`ERROR [rule] FILE: message`:

| Rule | Meaning |
|---|---|
| `plan-coverage-missing` | no `## Acceptance criteria coverage` section (any heading level, case-insensitive) |
| `plan-coverage-empty` | the section exists but its table has no rows |
| `plan-coverage-uncovered` | a row whose last cell, `Covered by tasks`, is empty or missing |
| `plan-clarification-open` | a `[NEEDS CLARIFICATION` marker is still present (one violation per line) |

Text inside fenced code blocks and inline code spans is ignored, so a plan can quote the marker syntax. A plan
written before the convention existed fails `plan-coverage-missing` by design.

## `plugins.json` and `generate-marketplace.py`

`plugins.json` is the membership map: which plugin each skill and agent belongs to. `generate-marketplace.py` turns it
into `.claude-plugin/marketplace.json` (marketplace `ai-catalog`), one entry per plugin with `source: "./"` (no file
moves), `skills` listing that plugin's `./.claude/skills/<name>` directories, `agents` on `iru-core`, `dependencies`
(`iru-core` for every other plugin plus the declared cross-stack edges), a `description` and a `category`
(`core`, `knowledge` or `stack`). Requires Python 3.9+ and PyYAML (it imports `catalog-audit.py` so the `Skill()` graph is
computed exactly as the audit computes it).

```bash
python3 tools/generate-marketplace.py             # write .claude-plugin/marketplace.json
python3 tools/generate-marketplace.py --check     # exit 1 when the committed file is stale; runs `claude plugin validate .`
python3 tools/generate-marketplace.py --check --no-validate   # skip the CLI validation
```

`plugins.json` keys:

| Key | Meaning |
|---|---|
| `marketplace` | `name`, `description` and `root_plugin` (the plugin every other plugin depends on, `iru-core`) |
| `plugins[].skills` | exact skill names or `fnmatch` patterns (`iru-java-*`); `exclude` removes matches (`iru-java-springboot-*` from `iru-java`) |
| `plugins[].agents` | agent names (files in `.claude/agents/`), listed on `iru-core` only |
| `plugins[].depends_on` | dependencies beyond `iru-core` (for example `iru-springboot` -> `iru-java`, `iru-kmp` -> `iru-android`, `iru-swift`) |
| `optional_calls` | `{from, to, reason}` entries for `Skill()` calls that cross plugins but must not become dependencies (a dependency would be circular or the call is conditional on the stack); `to` may be `*` |

The script fails (exit 1, one `ERROR` line per problem) when a skill or agent on disk is in no plugin or in more than
one, when a listed name or pattern matches nothing, when a static `Skill({skill: "..."})` call crosses plugins and
neither a `dependencies` edge nor an `optional_calls` entry covers it (dynamic `<name>` calls and external targets are
not part of the graph), and when the dependency graph has a cycle.

`--check` is where the plugin validation lives: after confirming `marketplace.json` is current it runs
`claude plugin validate <root>` when the `claude` CLI is on `PATH` (and prints a note when it is not). It compares against the
*committed* owner so the result does not depend on the contributor's `git config`; when generating, the owner comes from
`--owner`, else `git config user.name`/`user.email`, else `gh api user`, else the owner already in the file. The `version`
is the newest released `## [x.y.z]` heading of `CHANGELOG.md` (omitted while only `[Unreleased]` exists).

Run the script after adding, removing or renaming a skill or agent (a new skill must also be added to a plugin in
`plugins.json`), then also run `claude plugin validate .` and `claude plugin validate . --strict`.

## Tests

```bash
python3 -m unittest discover -s tools/tests
```

Standard-library `unittest` only. Line coverage of both scripts can be measured with the standard-library `trace` module
(no `coverage` package is needed); both are above 98 %.

## `catalog-budgets.json`

The thresholds `--check` enforces:

| Key | Meaning |
|---|---|
| `description_max` | maximum `description` characters for any skill (error) |
| `description_internal_target` | target for internal skills (warning above it) |
| `invocation_form_within` | the `/iru-...` or `Invoke as` form must start within this many characters (error) |
| `skill_lines_max` / `skill_lines_warn` | `SKILL.md` line limits (error / warning) |
| `agent_description_max` | maximum agent `description` characters |
| `require_agent_model` | every agent must pin a `model` |
| `allowed_models` / `agent_allowed_models` | accepted `model` values for skills / for agents (agents may also say `inherit`) |
| `shared_identical_files` | file names whose copies must stay byte-identical across skills |
| `internal_skills` | skills only ever invoked by other catalog skills through `Skill()` |
| `inline_cross_model_level` | `warning` or `error` for inline cross-model `Skill()` calls |
| `asset_path_ignore` | per skill, `templates/...` or `reference/...` paths its `SKILL.md` mentions that live in the target repository, not in the skill (exempt from `asset-path-missing`) |
| `accepted_cross_model_calls` | `{caller, callee, reason}` entries for inline cross-model `Skill()` calls that were reviewed and kept on purpose; the report shows the reason and `--check` stops warning about them |
| `external_skills` | `Skill()` targets that live outside this catalog (for example Claude Code's built-in `code-review`) and are not reported as missing |

`internal_skills` holds every `*-code-one-task`, `*-code-one-task-group`, `*-test`, `*-coverage`,
`*-code-quality`, `*-bump-version`, `*-generate-all-tests` skill, the doc-audit skills (`iru-java-javadoc`,
`iru-kotlin-kdoc`, `iru-kmp-dokka`, `iru-dotnet-docfx`, `iru-typescript-tsdoc`, `iru-php-phpdoc`,
`iru-python-docstrings`, `iru-android-dokka`, `iru-swift-docc`, `iru-rust-rustdoc`, `iru-go-godoc`), and every
`iru-setup-*` skill except `iru-setup-repository`, the `*-repository` orchestrators and the user-invoked
`iru-setup-java-springboot` orchestrator. Add new internal skills to the list when you add them.

## `baseline/`

Snapshots of the catalog **before** the performance and token-usage work (issue #11), used as the "before" column
of the final comparison:

- `catalog-audit-before.json` / `catalog-audit-before.md`: output of
  `python3 tools/catalog-audit.py --json tools/baseline/catalog-audit-before.json --markdown > tools/baseline/catalog-audit-before.md`.
- `plugin-validate-before.txt`: output of `claude plugin validate .claude/skills`.
- `sample-runs-before.md`: token, cost and duration table of the sample `claude -p` runs on the original tree (currently
  all rows "not run": the runs need an authenticated `claude`; the file lists the commands to fill it in).

These files are snapshots. They are regenerated only deliberately (for example to start a new comparison), never
as part of normal work: regenerating them after the optimizations would erase the "before" column.
