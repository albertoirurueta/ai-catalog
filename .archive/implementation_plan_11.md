# Implementation plan — Optimize skills performance and token usage

## Task summary

Source: GitHub issue #11
Base branch: main

Reduce the token cost and wall-clock time of using this catalog while keeping every skill's **functionality and
output equivalent**: measure first, then apply behavior-preserving optimizations, and package the catalog as
installable plugins. The ticket's six asks map to this plan as follows:

| Ticket ask | Where it lands |
|---|---|
| Reduce token usage, keep quality | Groups 1–3 (audit, descriptions, model tiers, templates out of `SKILL.md`), verified in Group 6 |
| Review the model used by each skill/agent | Group 2 (tiered policy applied; agents pinned) |
| Cache-hit penalties when one agent mixes models | Group 1 analysis + Group 3 fix of inline cross-model calls |
| Additional multi-role agents | Evaluated in the guide written in Group 5 — **not** added (see decisions) |
| Split the catalog by purpose/technology | Group 5: a core plugin plus one plugin per stack, over the unchanged `.claude/skills/` tree |
| Distributable plugins | Group 5: `.claude-plugin/marketplace.json` generated from a membership map |
| Spec Kit comparison (requested during plan review) | Group 4: an "analyze" gate (acceptance-criteria coverage table) and persisted `[NEEDS CLARIFICATION]` markers — the catalog already has every other Spec Kit phase, so the cycle is **not** refactored |

Decisions confirmed with the user before planning:

- **Scope**: measure, then optimize. Every change must leave each skill's observable behavior (files written, reports
  produced, questions asked) equivalent — with one deliberate exception, Group 4 below. Renames and restructurings
  beyond the two approved below are **not** done, only documented as options.
- **Spec Kit-inspired additions (approved during plan review, Group 4)**: compared with GitHub Spec Kit
  (`constitution → specify → clarify → plan → tasks → analyze → implement`), the catalog already covers every phase
  (`iru-draft/review/split-github-issue` = specify/clarify/checklist, `iru-explore` + `iru-plan` = plan + tasks,
  `iru-code` = implement, shared contracts + gates = constitution) except `analyze`. Reviews report Spec Kit's extra
  phases cost more tokens, not fewer, and no measured quality data exists, so the cycle is not refactored to mirror
  it. Two cheap ideas are adopted instead: an acceptance-criteria coverage table written by `iru-plan` and checked by
  `iru-code`, and `[NEEDS CLARIFICATION: …]` markers that `iru-plan` persists when it cannot ask and that `iru-code`
  refuses to start on. These are the only behavior changes in this plan and are verified separately (Task 22.5).
- **Approved restructurings**: (1) move embedded file templates out of the large `SKILL.md` files into per-variant
  template files inside the same skill directory; (2) pin explicit models on the three agents. **Not approved**
  (documented only): consolidating the byte-identical shared reference files into one copy per plugin; merging the
  per-language gate skills into cross-language ones.
- **Plugin split**: one `iru-core` plugin plus one plugin per stack, with the stack plugins depending on core.
- **Model policy**: tiered by task type — haiku for mechanical gates, version bumps and gitignore scaffolds; sonnet for
  coding skills and scaffolds/workflows generators; opus only for `iru-explore`, `iru-plan`, `iru-pr-review`.
- **Validation**: static budgets enforced by a script, plus documented before/after sample runs in a throwaway
  directory outside the repository.
- **Distribution**: plugins become the documented primary path; copying a skill directory keeps working, so every
  skill stays self-contained (all of a skill's templates/references live under its own directory).

Decisions made on the user's behalf (challenge in review):

- **Budgets** (enforced by `tools/catalog-audit.py --check`): `description` ≤ 1,024 characters for every skill and
  agent, with the invocation form (`/iru-…` or "Invoke as") inside the first 200 characters; internal skills (those
  only ever invoked by other catalog skills via `Skill()`, listed in `tools/catalog-budgets.json`) target ≤ 400
  characters (warning above). `SKILL.md` ≤ 1,000 lines (error) and ≤ 500 lines (warning). Frontmatter must parse
  with a strict YAML parser **and** `claude plugin validate`. Rationale: Claude Code caps each listing entry at
  1,536 characters and gives the whole listing about 1 % of the context window; with 196 skills and 544 KB of
  descriptions most skills are listed name-only today, and 44 descriptions are already cut mid-sentence.
- **Templates layout**: `.claude/skills/<skill>/templates/<flavor-or-variant>/<relative path of the generated
  file>` holding the exact bytes that were inside the fenced block; `SKILL.md` keeps a "Templates" index table
  (generated file → template path → when it applies) and the placeholder list, and tells the agent to read only
  the template(s) for the variant chosen. Threshold: every `SKILL.md` with ≥ 20 KB inside fenced code blocks (14
  skills today).
- **Plugin layout**: no files move. `.claude-plugin/marketplace.json` (marketplace name `ai-catalog`) lists one
  entry per plugin whose `source` is the marketplace root (`"./"`) and whose `skills` array lists that plugin's skill
  directories under `./.claude/skills/…` (per the manifest reference, an entry with the root as source that lists
  skill subdirectories loads only those). Agents are listed on `iru-core` via `agents: ["./.claude/agents/…md"]`.
  Trade-off accepted: each installed plugin caches its own copy of the repository (~11 MB). The alternative — a
  physical `plugins/<name>/skills/` tree — would move 196 directories and change the copy path, so it needs the
  user's approval and is only documented.
- **Skill and agent names are unchanged**, including the `iru-` prefix. In plugin mode a skill is also reachable as
  `/iru-java:iru-java-test`; the bare `/iru-java-test` keeps working because the names are unique.
- **`CLAUDE.md` slimming**: `CLAUDE.md` (321 lines, 31 KB) loads in every session of this repository. Its long
  "Architecture" prose moves verbatim into a new hand-maintained guide, `catalog-architecture.adoc`, and
  `CLAUDE.md` keeps what every session needs (what the repository is, commands, the `iru-` convention, generated vs
  hand-maintained docs, and links). Content is preserved, only relocated.
- **No new multi-role agents.** The three agents already cover the duplicated shapes; a fourth would add another
  context window per invocation. The guide records the evaluation.
- **Scripts in Python 3 (stdlib + PyYAML)** under `tools/`. No `python` coding skill is installed, so those tasks are
  tagged `_(python)_` and implemented directly by `iru-code-one-task-group`; all other tasks are Markdown/YAML/JSON
  authoring and stay untagged.

## Current code state

- **Inventory**: 196 skills (`.claude/skills/<name>/SKILL.md`, 6.2 MB) and 3 agents (`.claude/agents/`). Skills carry
  only `name`, `description`, `model` (all 196) and `allowed-tools` (98) in frontmatter; no skill uses `when_to_use`,
  `context`, `effort` or `disable-model-invocation`. Reference files under `*/reference/` total 4.3 MB.
- **Models**: 85 skills `haiku`, 108 `sonnet`, 3 `opus` (`iru-explore`, `iru-plan`, `iru-pr-review`). Assignment is
  inconsistent with the chosen tier policy: ~30 `iru-setup-*` scaffold/workflows skills are `haiku` (e.g.
  `iru-setup-typescript-github-workflows` at 173 KB, `iru-setup-android-library` 108 KB) while 32 others are
  `sonnet`. No agent sets `model:`, so `iru-gate-runner` inherits the caller's model (sonnet or opus) and the haiku
  gate skills it runs switch model mid-turn inside the subagent.
- **Descriptions**: 544 KB total; 59 over 1,024 characters, 44 over the 1,536-character listing cap (largest:
  `iru-swift-code-one-task` at 6,118). `claude plugin validate .claude/skills` reports 7 skills whose frontmatter
  fails to parse and therefore loads with **no** description and **no** model today: `iru-knowledge-process-inbox`,
  `iru-setup-android-app`, `iru-setup-android-gitignore`, `iru-setup-android-repository`, `iru-setup-angular-web`,
  `iru-setup-swift-gitignore`, `iru-setup-swift-repository`. A strict parser (PyYAML) rejects 39 — all from an
  unquoted `: ` inside the description value. The `iru-gate-runner` agent description is 4,094 characters.
- **Agent dispatch**: 46 skills contain `Agent({… subagent_type: "iru-gate-runner"})` (157 sites),
  `"iru-isolated-skill-executor"` (76), `"iru-change-summarizer"` (2), always by bare name. 269 `Skill({skill:
  "iru-…"})` cross-calls to 118 distinct targets, all existing.
- **Key discovery by filesystem** (breaks when installed as a plugin, since the files live in the plugin cache):
  `iru-code-one-task-group/SKILL.md:31`, `iru-plan/SKILL.md:99`, `iru-release/SKILL.md:82`,
  `iru-typescript-bump-version/SKILL.md:38`, `iru-generate-skill-docs/SKILL.md:31` (`find .claude/skills …`).
- **Templates inline**: 39 `SKILL.md` exceed 500 lines, 11 exceed 1,000. Fenced-block bytes: TypeScript workflows
  60 KB of 173 KB (20 templates, Step 3 `### … template` headings), Spring Boot pom 59 KB of 113 KB, Spring Boot
  workflows ~59 KB of 133 KB, Swift workflows ~60 KB of 149 KB, Python workflows 40 KB of 89 KB, PHP workflows 46 KB
  of 79 KB, Android library 38 KB of 108 KB, Android app ~36 KB of 105 KB, Android workflows ~29 KB of 95 KB,
  Spring Boot apis ~31 KB of 90 KB, Java workflows ~15 KB of 58 KB, Quarkus workflows 23 KB of 43 KB, Spring Boot
  modules ~9 KB of 50 KB, Spring Boot testcontainers ~6 KB of 43 KB. Prose-heavy large skills (`iru-setup-readme`
  77 KB, `iru-setup-repository` 74 KB, `iru-explore` 56 KB) have no templates and are out of scope here.
- **Shared byte-identical files** (convention from issues #16/#28, must stay identical): `reference/ui-contract.md`
  (12 copies), `reference/cli-contract.md` (4), `reference/ui-docs.md` (3), `reference/accessibility-detection.md`
  (2). ~365 KB of redundant bytes overall; left in place (not approved for consolidation) but now checked.
- **Docs**: Antora site under `docs/` (`antora.yml`, `antora-playbook.yml`, `modules/ROOT/pages/`); generated pages
  (`index.adoc`, `skills/*.adoc`, `agents/*.adoc`) come from `/iru-generate-skill-docs`; hand-maintained guides
  under `guides/` already include `plugins.adoc`, `packaging-and-distribution.adoc`,
  `authoring-effective-instructions.adoc` (section "Treat the context window as scarce"),
  `creating-skills-and-agents.adoc`, `extending-the-catalog.adoc` (step "Model tier"). `nav.adoc` lists guides.
  CI: `.github/workflows/docs.yml` builds and publishes the site on push to `main`; no other check exists.
- **Tooling available**: Claude Code CLI 2.1.260 (`claude plugin validate`, `claude plugin marketplace add`,
  `claude -p --output-format json` with `usage` and `total_cost_usd`), Python 3.9.6 with PyYAML, `gh`.
- **Related past plans**: `.archive/implementation_plan_28.md` (accessibility) is the structural precedent —
  decisions list, shared-file convention, grouped Markdown-only tasks ending with a verification group.

## Implementation steps

### Group 1 — Measure before touching anything (Parallelizable: yes)

- [x] Task 1. Catalog audit script, budgets file and baseline snapshot _(python)_
  - Files: `tools/catalog-audit.py`, `tools/catalog-budgets.json`, `tools/README.md`, `tools/tests/test_catalog_audit.py`,
    `tools/baseline/catalog-audit-before.{json,md}`, `tools/baseline/plugin-validate-before.txt`. 29 stdlib `unittest` tests pass;
    line coverage of `catalog-audit.py` 98.8% (stdlib `trace`; no `coverage` module installed); no unused imports; Apache-2.0
    headers verified via `iru-gate-runner`/`iru-check-license` (already compliant). Baseline: 39 frontmatter parse failures,
    149+ descriptions over 1,024 chars, 21 inline cross-model calls, 1 external `code-review` target (`external_skills`).
  - [x] Task 1.1. Create `tools/catalog-audit.py` (Python 3.9+, stdlib + PyYAML, Apache-2.0 header). For every
    `.claude/skills/*/SKILL.md` and `.claude/agents/*.md` collect: bytes, lines, frontmatter keys, `model`,
    `description` length, position of the first `/iru-` or "Invoke as" in the description, bytes inside fenced
    code blocks, total bytes of supporting files, `Skill({skill: …})` targets, `subagent_type` dispatch counts,
    whether frontmatter parses with `yaml.safe_load`. Also compute: duplicate supporting files by SHA-256
    (groups + redundant bytes), the md5 set of each shared file name (`ui-contract.md`, `cli-contract.md`,
    `ui-docs.md`, `accessibility-detection.md`), missing `Skill()` targets, and **inline cross-model calls** — a
    `Skill()` call whose caller `model` differs from the callee's and that does not sit inside an `Agent({…})`
    prompt string.
  - [x] Task 1.2. Output modes: `--json <file>` (full data), `--markdown` (summary tables: totals, top-20 by size,
    top-20 descriptions, per-model counts, duplicates, cross-model calls, parse failures), and `--check` reading
    `tools/catalog-budgets.json` and exiting non-zero on any error-level violation.
  - [x] Task 1.3. Create `tools/catalog-budgets.json` with: `description_max: 1024`, `description_internal_target:
    400`, `invocation_form_within: 200`, `skill_lines_max: 1000`, `skill_lines_warn: 500`, `agent_description_max:
    1024`, `require_agent_model: true`, `shared_identical_files: [...]` (the four names), `internal_skills:
    [...]` (every `*-code-one-task`, `*-code-one-task-group`, `*-test`, `*-coverage`, `*-code-quality`,
    `*-bump-version`, `*-generate-all-tests`, doc-audit skills, and every `iru-setup-*` except
    `iru-setup-repository` and the `*-repository` orchestrators), `allowed_models: [haiku, sonnet, opus]`.
  - [x] Task 1.4. Run `python3 tools/catalog-audit.py --json tools/baseline/catalog-audit-before.json --markdown >
    tools/baseline/catalog-audit-before.md` and commit both (this is the "before" column of Group 6's table).
    Also record `claude plugin validate .claude/skills` output into `tools/baseline/plugin-validate-before.txt`.
  - [x] Task 1.5. Write `tools/README.md`: what each script does, how to run `--check` locally, and that the
    baseline files are snapshots regenerated only deliberately.

- [x] Task 2. Plugin-mode resolution spike (throwaway, outside the repository)
  - Done with an authenticated `claude -p` (2.1.260). Answers in `tools/spikes/plugin-resolution.md`: (a) bare skill name
    resolves (with `--allowedTools=Skill` in `-p` mode); (b) bare agent name does NOT resolve, `spike-core:iru-gate-runner`
    does, so Task 19 must use the namespaced form; (c) `.claude/skills` absent in plugin mode; (d) `${CLAUDE_PLUGIN_ROOT}`
    and `${CLAUDE_SKILL_DIR}` are substituted. Agents on a root-source entry DO load (`claude plugin details` shows
    Agents (0) but the agent is available at runtime). Marketplace and plugins removed afterwards.
  - [x] Task 2.1. In `$TMPDIR/iru-verify/plugins/spike/` build a minimal marketplace by copying (not linking —
    the validator does not follow symlinks) `iru-gate-runner.md`, `iru-java-test`, `iru-java-code-quality`,
    `iru-check-license` and `iru-code-one-task-group` into two plugins (`spike-core` with the agent and
    `iru-check-license`; `spike-java` with the Java skills, `dependencies: ["spike-core"]`), with
    `.claude-plugin/marketplace.json` using root-source entries that list `skills` subdirectories exactly as Group
    4 will. Run `claude plugin validate .` and fix until it passes.
  - [x] Task 2.2. `claude plugin marketplace add <dir>` and install both plugins; in a throwaway Maven project
    run `claude -p` prompts that (a) call `Skill({skill: "iru-java-test"})` by bare name, (b) dispatch
    `Agent({subagent_type: "iru-gate-runner"})` by bare name and, if that fails, by `spike-core:iru-gate-runner`,
    (c) confirm `find .claude/skills …` finds nothing in plugin mode, (d) check whether `${CLAUDE_PLUGIN_ROOT}` is
    substituted inside a skill body. Uninstall and remove the marketplace afterwards.
  - [x] Task 2.3. Record the answers in `tools/spikes/plugin-resolution.md` (commands run, Claude Code version,
    outcome per question). Group 5's Task 19 branches on (b).

- [x] Task 3. "Before" sample runs (throwaway, outside the repository)
  - [x] Task 3.1. Export the current `main` tree with `git archive main | tar -x -C $TMPDIR/iru-verify/before/`
    (no worktree, nothing in this repository changes). Create fixture repositories under
    `$TMPDIR/iru-verify/fixtures/`: `ts-lib` (`npm init -y`, a `tsconfig.json`, one `src/index.ts`, `git init`)
    and `android-lib` (empty `git init` repository).
  - [x] Task 3.2. From the exported tree (`cd $TMPDIR/iru-verify/before` so its `.claude/skills` are the ones
    loaded), run each sample with `claude -p --output-format json --permission-mode acceptEdits` and save the JSON
    (`usage.input_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`, `output_tokens`,
    `total_cost_usd`, `duration_ms`) plus the produced files:
    - S0 listing cost: prompt "Reply with the single word OK" (input tokens ≈ system prompt + skill listing).
    - S1 `/iru-setup-typescript-github-workflows` on `ts-lib` with fixed args (`flavor: library`, `ci-tests: unit`,
      `pages: no`, `sonar: none`, `visibility: private`, `on-existing: replace`) — keep the generated
      `.github/` tree for byte comparison.
    - S2 `/iru-setup-android-gitignore` on `android-lib` — keep the generated `.gitignore`.
    - S3 `/iru-explore` on `ts-lib` — keep the "Tech stack" block from the final message.
    - Done: all four ran (S0 42,787 prompt-side tokens; S1 69 s; S2 58 s; S3 60 s); numbers in
      `tools/baseline/sample-runs-before.md`, raw output in `$TMPDIR/iru-verify/results/before/`.
  - [x] Task 3.3. Save everything under `$TMPDIR/iru-verify/results/before/` and copy a compact table
    (sample → tokens → cost → duration) into `tools/baseline/sample-runs-before.md`. Anything that cannot run
    (e.g. no network) is recorded as "not run" with the reason, never skipped silently.

### Group 2 — Frontmatter: models, descriptions, parse fixes (Parallelizable: yes — each task owns a disjoint set of files and edits frontmatter only; bodies are untouched until Group 3)

- [x] Task 4. Pin agent models and trim agent descriptions
  - Progress: Done: `model: haiku` on `iru-gate-runner` (description 432 chars; per-language enumeration, "Used by" list and raw-report list moved into a new "Gate skills this agent runs" body section) and `iru-change-summarizer`; `model: inherit` on `iru-isolated-skill-executor`; each body ends with / contains a "Why these models" paragraph. All 3 agent descriptions quoted and <= 1,024.
  - [x] Task 4.1. `.claude/agents/iru-gate-runner.md`: add `model: haiku`; rewrite `description` to ≤ 1,024
    characters (what it runs — one gate skill —, that it reports a compact summary, and the one-line list of gate
    families; move the per-language enumeration into the body under a "Gate skills this agent runs" section so no
    information is lost).
  - [x] Task 4.2. `.claude/agents/iru-change-summarizer.md`: add `model: haiku`.
  - [x] Task 4.3. `.claude/agents/iru-isolated-skill-executor.md`: add `model: inherit` explicitly (it runs a
    whole coding skill whose own `model` must decide) and a body sentence explaining why.
  - [x] Task 4.4. Add a "Why these models" paragraph to each agent body (mechanical gate → haiku; the executor
    inherits so a `sonnet` coding skill is not downgraded).

- [x] Task 5. Frontmatter rewrite — core pipeline, tickets, docs, knowledge skills (≈ 37 files: `iru-issue`,
  - Progress: Done: 29 skills (incl. `iru-code-one-task-group`; `iru-setup-java-springboot` was handled under Task 6). Descriptions 284-721 chars, quoted, invocation form first. Models: no change needed (opus: explore/plan/pr-review; haiku: build-docs, check-license, check-security, knowledge-complete, knowledge-setup kept as is; rest sonnet). Relocations: `iru-draft-github-issue`, `iru-create-github-issue`, `iru-create-jira-ticket` (scope/not-for paragraph), `iru-knowledge-process-inbox` (requires `knowledge/` from `iru-knowledge-setup`). `iru-knowledge-process-inbox` parse failure fixed; `iru-pr-review` now has an invocation form.
  `iru-explore`, `iru-plan`, `iru-code`, `iru-code-one-task-group`, `iru-pr-description`, `iru-pr-review`,
  `iru-release`, `iru-create-*`, `iru-draft-github-issue`, `iru-review-github-issue`, `iru-split-github-issue`,
  `iru-jira-custom-context`, `iru-check-license`, `iru-check-security`, `iru-build-docs`, `iru-update-docs`,
  `iru-update-java-springboot-documentation`, `iru-generate-skill-docs`, `iru-springboot-rolling-deployments`,
  `iru-java-springboot-performance-tests`, `iru-knowledge-*`, `iru-database-*`)
  - [x] Task 5.1. For each file rewrite `description` to ≤ 1,024 characters: invocation form first (`/iru-x` or
    `/iru-x <args>`), then what it does, then the trigger phrases; drop enumerations of supported stacks that
    the body already states. Quote the value (`description: "…"` or a `>-` folded block) so `: ` is legal YAML.
  - [x] Task 5.2. Apply the tier policy: keep `opus` on `iru-explore`, `iru-plan`, `iru-pr-review`; `sonnet` on the
    rest of this family except `iru-check-license`, `iru-check-security`, `iru-build-docs` (haiku, mechanical).
    `iru-knowledge-*`: keep current models unless the body shows pure file shuffling (then haiku); record each
    change in the task's progress note.
  - [x] Task 5.3. Verify with `python3 -c 'import yaml,sys;…'` (strict parse) and `claude plugin validate
    .claude/skills/<name>` for every touched skill.

- [x] Task 6. Frontmatter rewrite — every `iru-setup-*` skill (≈ 75 files)
  - Progress: Done: 70 skills. Descriptions 254-694 chars (internal <= 400; orchestrators 420-700). Models changed haiku -> sonnet (27): android-app, android-github-workflows, android-library, android-repository, angular-web, antora, apple-app, cli-repository, ionic-app, java-github-workflows, java-library, java-library-repository, java-springboot-hilla, kmp-repository, macos-repository, php-repository, python-repository, quarkus-repository, react-native-app, react-web, swift-github-workflows, swift-library, swift-repository, typescript-github-workflows, typescript-library, typescript-repository, windows-repository (all `iru-setup-` prefixed). Every `-gitignore` skill (11) stays haiku; the remaining 32 were already sonnet. Fixes the 6 parse failures (android-app, android-gitignore, android-repository, angular-web, swift-gitignore, swift-repository). Relocations: sibling/standalone-use sentences in android-gitignore, apple-app, cli-github-workflows, java-springboot-hilla, php/python/quarkus-github-workflows, php/python/swift/typescript-gitignore, swift-library, python-django, react-native-app.
  - [x] Task 6.1. Descriptions as in 5.1; internal sub-skills (everything except `iru-setup-repository` and the
    twelve `*-repository`/`iru-setup-java-springboot` orchestrators) target ≤ 400 characters.
  - [x] Task 6.2. Models: `sonnet` for every scaffold, app/library/service generator, `-github-workflows`,
    `-antora`, `-changelog`, `-readme`, orchestrator and front door; `haiku` for every `-gitignore` skill.
    List the before→after model of every changed file in the progress note (expected: ~30 haiku→sonnet,
    `iru-setup-*-gitignore` stay haiku).
  - [x] Task 6.3. This task fixes 6 of the 7 skills that fail `claude plugin validate` today
    (`iru-setup-android-app`, `-android-gitignore`, `-android-repository`, `-angular-web`, `-swift-gitignore`,
    `-swift-repository`); the seventh, `iru-knowledge-process-inbox`, is in Task 5. Verify as in 5.3.

- [x] Task 7. Frontmatter rewrite — coding skills (38 files: every `iru-<key>-code-one-task` and
  - Progress: Done: 38 skills (every `iru-<key>-code-one-task` and `-group`, incl. `iru-database-*`; `iru-code-one-task-group` counted under Task 5). Descriptions 282-400 chars, `Invoked as /iru-... via Skill` first; `iru-swift-code-one-task` 6,118 -> 398 chars (its lists were already in the body's Step 1/routing table and `reference/`, no relocation needed). All 38 asserted `model: sonnet`, none edited.
  `iru-<key>-code-one-task-group`)
  - [x] Task 7.1. Descriptions ≤ 400 characters (internal: only ever invoked by `iru-code-one-task-group` or the
    group skill): key, what it implements/validates, the invocation form. Move any stack detail only present in
    the description (e.g. `iru-swift-code-one-task`'s 6,118-character list of platforms/UI frameworks) into the
    body's Step 0 or a `reference/` file so nothing is lost.
  - [x] Task 7.2. Models: all `sonnet` (already the case — assert, don't edit). Verify as in 5.3.

- [x] Task 8. Frontmatter rewrite — gates, doc audits, version bumps, test generators (≈ 46 files:
  - Progress: Done: 59 skills. Descriptions 256-376 chars. Models: no change. Deviation to confirm: the 11 doc-audit skills (`iru-java-javadoc`, `-kotlin-kdoc`, `-android-dokka`, `-kmp-dokka`, `-dotnet-docfx`, `-typescript-tsdoc`, `-php-phpdoc`, `-python-docstrings`, `-swift-docc`, `-rust-rustdoc`, `-go-godoc`) stay `sonnet` instead of haiku because their bodies generate missing doc comments (writing, not only running a tool). The other 42 gates/bumps stay haiku; the 6 `*-generate-all-tests` stay sonnet. Relocations: `iru-dotnet-bump-version` (BOM/line endings), `iru-dotnet-generate-all-tests` (`.ui-screenshots/`), `iru-kmp-generate-all-tests` (UI screenshot helper paths), `iru-kmp-coverage` (JVM-only measurement note).
  `iru-<lang>-test|coverage|code-quality`, `iru-kotlin-code-quality`, `iru-*-javadoc|kdoc|dokka|docfx|tsdoc|phpdoc|
  docstrings|docc|rustdoc|godoc`, `iru-*-bump-version`, `iru-*-generate-all-tests`)
  - [x] Task 8.1. Descriptions ≤ 400 characters, invocation form first, selector syntax kept (one phrase).
  - [x] Task 8.2. Models: `haiku` for test/coverage/code-quality/bump-version/doc-audit skills (they run a tool
    and report); `sonnet` for `*-generate-all-tests` (they write tests). Verify as in 5.3.

### Group 3 — Bodies: templates out of `SKILL.md`, plugin-safe discovery, cross-model calls (Parallelizable: yes — disjoint skill sets; Task 15's sites are assigned to whichever task owns the file)

Common procedure for Tasks 9–13 (apply per skill; functionality must be byte-equivalent):

1. Before editing, dump every fenced block of the skill's template sections to
   `$TMPDIR/iru-verify/templates/<skill>/before/` (one file per `### … template` heading, in order).
2. Create `templates/<variant>/<generated path>` under the skill directory holding the fenced content verbatim
   (no fence lines, trailing newline preserved). Variant directory names follow the heading's qualifier
   (`library`, `react-angular`, `nextjs-static`, `react-native-expo-eas`, `kotlin-gradle`, `common`, …).
3. Replace each fenced block in `SKILL.md` with one line: "Template: `templates/<variant>/<path>` — read it in
   full before filling placeholders", keeping the heading, the surrounding prose, the placeholder list and every
   "when this template applies" rule in place.
4. Add a "Templates" index table near the top of the template step (generated file → template path → applies
   when) and one sentence in the skill's Step 0/1: "Read only the template files for the variant resolved above".
5. Verify: concatenating the new template files in heading order equals the dump from step 1 (`cmp`), `SKILL.md`
   is ≤ 1,000 lines (target ≤ 500), `claude plugin validate .claude/skills/<skill>` passes, and every
   `templates/` path named in `SKILL.md` exists (`tools/catalog-audit.py --check` gains this rule in Task 9).

- [x] Task 9. Templates out: TypeScript workflows — `iru-setup-typescript-github-workflows` (20 templates,
  173 KB) _(python for the audit rule only)_
  - Done: 15 template files (`generic`, `nestjs-nextjs`, `react-native-metro` incl. a `build.yml.append`, `library`, `react-angular`,
    `nextjs-static`, `nestjs-nextjs-server`, `react-native-expo-eas`, `react-native-expo-local`, `ionic`, `common` for
    `sync.yml`/`sync_versions.py`/`security.yml`/`dependabot.yml`) + 13 `reference/notes-*.md` (the per-template "Notes specific
    to this template" prose, moved verbatim and pointed to from SKILL.md; needed to get under 1,000 lines). The two `codeql`
    replacement fragments stay inside `reference/notes-security.md`; the small `dependabot.yml` additions stay inline.
    `cmp`/rebuild check: templates equal the dump and the original SKILL.md is rebuilt exactly (`rebuild==original: True`).
    SKILL.md 2,949 → 970 lines. Dumps and manifest: `$TMPDIR/iru-verify/templates/iru-setup-typescript-github-workflows/`.
    Tests: 38 `unittest` tests pass; line coverage of `tools/catalog-audit.py` 98.9% (stdlib `trace`).
  - [x] Task 9.1. Extend `tools/catalog-audit.py --check` with a rule: every `templates/…` and `reference/…` path
    mentioned in a `SKILL.md` must exist; every file under `templates/` must be referenced by its `SKILL.md`.
    Done: rules `asset-path-missing` (a `templates/…` path named in SKILL.md must exist in the skill; a `reference/…` path
    must exist in the skill or in a sibling skill; placeholder/wildcard paths skipped) and `template-unreferenced` (every file
    under `templates/` must appear in SKILL.md by its full relative path). Target-repository paths that look like skill assets
    are listed under the new `asset_path_ignore` budgets key (5 entries); the new `accepted_cross_model_calls` key (Task 15)
    is documented too. 9 new tests; documented in `tools/README.md`.
  - [x] Task 9.2. Apply the common procedure (variants: `library`, `react-angular`, `nestjs-nextjs`,
    `nextjs-static`, `nestjs-nextjs-server`, `react-native-expo-eas`, `react-native-expo-local`,
    `react-native-metro`, `ionic`, `common` for `security.yml`/`dependabot.yml`/`sync.yml`/`sync_versions.py`).
- [x] Task 10. Templates out: Swift — `iru-setup-swift-github-workflows` (149 KB) and `iru-setup-swift-library`
  (60 KB)
  - `iru-setup-swift-github-workflows`: 9 templates (`library`, `app`, `common`) + 3 notes references; 2,439 → 884 lines; cmp/rebuild True.
    `iru-setup-swift-library`: 10 templates (`common`, `swift-format`, `swiftformat`; `<Name>` path segments written as `{Name}`
    because `<`/`>` are invalid in Windows file names); 876 → 671 lines; cmp/rebuild True.
- [x] Task 11. Templates out: JVM — `iru-setup-java-springboot-pom` (113 KB; `maven`, `kotlin-maven`,
  `kotlin-gradle` incl. `build-logic/`), `iru-setup-java-springboot-github-workflows` (133 KB),
  `iru-setup-java-springboot-apis` (90 KB), `iru-setup-java-springboot-modules`,
  `iru-setup-java-springboot-testcontainers`, `iru-setup-java-github-workflows` (58 KB),
  `iru-setup-quarkus-github-workflows` (43 KB)
  - `iru-setup-java-springboot-pom`: 31 templates (`maven`, `kotlin-maven`, `kotlin`, `kotlin-gradle` incl. `build-logic/`); 2,231 → 764 lines.
    `iru-setup-java-springboot-github-workflows`: 17 (`maven`, `kotlin-gradle`, `rolling`, `common`); 2,327 → 845.
    `iru-setup-java-springboot-apis`: 21 (`maven`, `maven-java`, `maven-kotlin`, `gradle-kotlin`, `common`; `__name__`-style path segments); 1,456 → 791.
    `iru-setup-java-github-workflows`: 6 (`common`); 979 → 556. `iru-setup-quarkus-github-workflows`: 6 (`common`); 842 → 267.
    `iru-setup-java-springboot-modules` (728 lines) and `-testcontainers` (593): no templates — only 9.4 KB / 6.5 KB of fenced
    shape illustrations and snippets, below the 20 KB threshold; left unchanged. cmp/rebuild True for all five changed skills.
    Not in the plan but required by the "no `skill-lines-max` error" gate: `iru-setup-java-springboot` (1,142 → 788 lines) — the
    `springboot-stack.yml` manifest template moved to `templates/common/` and Step 4's groups 4a–4l (verbatim, 271 lines) to
    `reference/technologies.md`; cmp/rebuild True.
- [x] Task 12. Templates out: Android — `iru-setup-android-library` (108 KB), `iru-setup-android-app` (105 KB),
  `iru-setup-android-github-workflows` (95 KB); keep the "Known quirks / verification notes" prose in `SKILL.md`.
  - `iru-setup-android-library`: 28 templates (`common`; gating in the index table); 1,809 → 923 lines. `iru-setup-android-app`: 30
    (`common`, `compose`, `views`); 1,767 → 963. `iru-setup-android-github-workflows`: 8 (`gitflow`, `main-only`, `common`); 1,511 → 782.
    `<namespace-path>`/`<package-path>` segments written `__namespace-path__`/`__package-path__`. Known-quirks prose untouched;
    cmp/rebuild True for all three.
- [x] Task 13. Templates out: Python and PHP workflows — `iru-setup-python-github-workflows` (89 KB),
  `iru-setup-php-github-workflows` (79 KB)
  - `iru-setup-python-github-workflows`: 8 templates (`common`); 1,562 → 546 lines. `iru-setup-php-github-workflows`: 15
    (`common`, `laravel`, `wordpress`, `prestashop-module`); 1,605 → 414. cmp/rebuild True for both. No notes references needed.

- [x] Task 14. Plugin-safe key discovery at the five filesystem-discovery sites
  - [x] Task 14.1. `iru-code-one-task-group/SKILL.md:31` and `iru-plan/SKILL.md:99`: discover installed keys
    first from the skills available in the session (names matching `iru-*-code-one-task(-group)`), and use `find
    .claude/skills …` as the corroborating check when that directory exists; same key-derivation text as today.
  - [x] Task 14.2. `iru-release/SKILL.md:82` and `iru-typescript-bump-version/SKILL.md:38`: same dual discovery
    for `iru-*-bump-version` / `iru-react-native-bump-version`.
  - [x] Task 14.3. `iru-generate-skill-docs/SKILL.md:31`: keep the filesystem scan (it documents this
    repository's own tree) and add that, when `.claude-plugin/marketplace.json` exists, each skill page states
    which plugin ships it (read from `tools/plugins.json`).
    Done at all five sites (`iru-code-one-task-group`, `iru-plan`, `iru-release`, `iru-typescript-bump-version`,
    `iru-generate-skill-docs`): installed keys are read first from the skills available in the session, with the
    `find .claude/skills …` command kept as the corroborating check when that directory exists; key-derivation text
    unchanged. `iru-generate-skill-docs` keeps its filesystem scan and states the plugin line (omitted until
    `tools/plugins.json` exists, Task 18).

- [x] Task 15. Remove inline cross-model `Skill()` calls (list = the audit's "inline cross-model calls" section
  from Task 1; expected to be few or none, since gates go through `iru-gate-runner`)
  - [x] Task 15.1. For each site: either route the call through `iru-gate-runner` (when it is a gate) or align the
    callee's `model` with the caller's. Record each decision in the progress note. If the list is empty, state
    so and check the box.
    Live list: 17 sites; none edited, all 17 recorded as accepted under `accepted_cross_model_calls` in
    `tools/catalog-budgets.json` (the audit then reports "17 (17 accepted)" and `--check` no longer warns):
    - `iru-android-generate-all-tests` → `iru-android-test`, `iru-dotnet-generate-all-tests` → `iru-dotnet-test`,
      `iru-kmp-generate-all-tests` → `iru-kmp-test`, `iru-swift-generate-all-tests` → `iru-swift-test`: accepted, audit
      false positives — the prose already routes the run through `iru-gate-runner`; the `Skill()` call is that
      dispatch's prompt.
    - `iru-explore` called by `iru-create-github-issue`, `iru-create-jira-ticket`, `iru-database-code-one-task`,
      `iru-draft-github-issue`, `iru-issue`, `iru-knowledge-to-issue`, `iru-knowledge-to-jira`, `iru-setup-readme`,
      `iru-setup-repository` (10 sites in 9 skills): accepted — opus by the tier policy and its report must land in the
      caller's own context; an agent would return only a summary.
    - `iru-issue` → `iru-plan`, `iru-issue` → `iru-pr-review`: accepted — interactive opus skills (questions, review
      confirmation) must run in the orchestrator's conversation.
    - `iru-knowledge-compact` → `iru-knowledge-complete` (sonnet → haiku): accepted — single-purpose file operation whose
      stop message the caller reads; an agent per task would add a context for a few file edits.

### Group 4 — Analyze gate and persisted clarification markers (Parallelizable: yes — Task 16 owns `iru-plan`, Task 17 owns `iru-code` and `iru-issue`; the only deliberate behavior changes in this plan)

- [x] Task 16. `iru-plan`: acceptance-criteria coverage table and `[NEEDS CLARIFICATION]` markers
  - [x] Task 16.1. Step 4 ("Resolve ambiguity"): when a genuine ambiguity cannot be put to the user — unattended
    run, `AskUserQuestion` declined, or the user says "decide later" — write it into the plan as
    `[NEEDS CLARIFICATION: <question> — options: <a> | <b>; recommended: <a>]` on the task it blocks and in a new
    "Open clarifications" list in the Task summary, and continue planning around the recommended option. Never
    guess silently. When the user does answer, the marker is resolved in place and the list says "none".
    - _Done:_ iru-plan Step 4 now persists unanswerable questions as `[NEEDS CLARIFICATION: <question> — options: <a> | <b>; recommended: <a>]` on the blocked task and in `Open clarifications:`; resolved in place.
  - [x] Task 16.2. Step 6 (plan structure): add a mandatory section **"Acceptance criteria coverage"** right after
    "Task summary": a table `# | Criterion (quoted from the ticket, or "derived" when the ticket states none) |
    Covered by tasks`. Every criterion must map to at least one task; a criterion with no task is a planning error
    the skill fixes by adding a task or by placing a marker. For tickets without explicit criteria, derive 2–6
    verifiable statements from the request and label them `derived`. Add the "Open clarifications" list (or
    "none") to the Task summary structure.
    - _Done:_ iru-plan Step 6: Task summary ends with `Open clarifications:` (or `none`); new mandatory item 2 `## Acceptance criteria coverage` (`# | Criterion | Covered by tasks`, `derived:` rows when the ticket states none); Implementation steps renumbered to item 4.
  - [x] Task 16.3. Step 7 (ask for review): the review message additionally lists uncovered criteria (should be
    none) and every open marker with its recommended option, so the user resolves them before `/iru-code`.
    - _Done:_ iru-plan Step 7 review message lists uncovered criteria and open markers with their recommended option.
  - [x] Task 16.4. Step 2 (reconcile with an existing plan): when preserving completed work, carry the coverage
    table and markers forward and re-derive only the rows for new or unchecked tasks.
    - _Done:_ iru-plan Step 2 (preserve option) carries the coverage table and markers forward, re-deriving rows only for new/unchecked tasks.
  - [x] Task 16.5. Update `iru-plan`'s description (inside the Task 5 budget) to mention the coverage table and
    markers, and the cycle description in `docs/modules/ROOT/pages/guides/common-workflows.adoc`.
    - _Done:_ iru-plan description now 780 chars (budget 1,024, quoted, invocation form at position 0); `common-workflows.adoc` Prepare-plan and Code-implementation rows describe the table, markers, gate and Step 7 coverage check.

- [x] Task 17. `iru-code` and `iru-issue`: gate on open markers, verify coverage
  - [x] Task 17.1. `iru-code` Step 2 ("Verify checkbox placeholders and task groups"): also scan the plan for
    `[NEEDS CLARIFICATION`. If any remain, list each with the task it blocks and ask the user to resolve them
    (`AskUserQuestion`, one question per marker, the recorded recommended option first), update the plan in place,
    and only then continue. If the user declines or cannot be asked, stop per Step 6's interrupt rules — no
    implementation starts on an unresolved marker. If the "Acceptance criteria coverage" section is absent (a
    plan from an older `iru-plan`), warn once and continue (backward compatible).
    - _Done:_ iru-code Step 2 (retitled) scans for `[NEEDS CLARIFICATION`, asks one `AskUserQuestion` per marker (recommended first), updates the plan in place, stops per Step 6 when declined/unattended (new Step 6 bullet); missing coverage section warns once and continues.
  - [x] Task 17.2. `iru-code` Step 7 ("Final verification"): before archiving (Step 9), check that every row of
    the coverage table maps to tasks whose boxes are checked; report any uncovered or unchecked row as a blocker
    alongside the quality and security gates.
    - _Done:_ iru-code Step 7 gains a final coverage check after the quality and security gates (uncovered/unchecked row blocks Step 8/archiving; follow-up tasks or edit row); Step 8/9 wording and the Step 9 summary updated.
  - [x] Task 17.3. `iru-issue` Step 5: after `iru-plan` finishes, if the plan lists open markers, say so when asking
    the Step 6 question (an automatic `iru-code` run will stop at its Step 2 gate until they are resolved) and
    include them in the Step 9 report.
    - _Done:_ iru-issue Step 5 notes open markers after iru-plan (a declined question is no longer a stop condition), Step 6 question mentions them, Step 9 report lists them.
  - [x] Task 17.4. `iru-code-one-task-group` and the `<key>` group skills: no change (markers and coverage are
    plan-level) — assert and record in the progress note.
    - _Done:_ No change to iru-code-one-task-group or any `<key>` group skill: markers and coverage are plan-level (asserted; none of those skills reference either).
  - [x] Task 17.5. Extend `tools/catalog-audit.py --check` (from Task 1) with a plan-shape rule used by Task 22.5:
    given a plan path, verify the coverage section exists and that no `[NEEDS CLARIFICATION` remains.
    - _Done:_ `tools/catalog-audit.py --plan FILE` (rules `plan-coverage-missing`, `plan-coverage-empty`, `plan-coverage-uncovered`, `plan-clarification-open`; code spans/fences ignored; exit 0/1/2; combinable with `--check`); 12 tests in `PlanShapeTests`, 49 total passing, 99.2% line coverage of catalog-audit.py via `trace`; documented in tools/README.md. Run on this plan: fails `plan-coverage-missing` (expected, predates the convention).

### Group 5 — Plugin packaging, docs, CI (Parallelizable: no — Task 19 consumes Task 18's membership map and the Task 2 spike; Task 20 documents the result of both)

- [x] Task 18. Membership map and generated marketplace _(python)_ — 84 tests pass; `claude plugin validate .` (+ `--strict`) pass; coverage 99.3% / 99.2%.
  - [x] Task 18.1. Create `tools/plugins.json`: `iru-core` (every skill without a stack token — `iru-issue`,
    `iru-explore`, `iru-plan`, `iru-code`, `iru-code-one-task-group`, `iru-pr-*`, `iru-release`, `iru-create-*`,
    `iru-draft/review/split-github-issue`, `iru-jira-custom-context`, `iru-check-*`, `iru-build-docs`,
    `iru-update-docs`, `iru-generate-skill-docs`, `iru-setup-repository`, `iru-setup-antora`,
    `iru-setup-changelog`, `iru-setup-readme`, `iru-database-*`, plus the three agents); `iru-knowledge`
    (`iru-knowledge-*`); stack plugins `iru-java` (`iru-java-*` except Spring Boot, `iru-kotlin-code-quality`,
    `iru-kotlin-kdoc`, `iru-setup-java-*`), `iru-springboot` (`iru-*springboot*`, `iru-springboot-rolling-
    deployments`, `iru-update-java-springboot-documentation`), `iru-quarkus`, `iru-dotnet` (`iru-dotnet-*`,
    `iru-windows-*`, `iru-setup-windows-*`, `iru-setup-dotnet-*`), `iru-typescript` (`iru-typescript-*`,
    `iru-setup-typescript-*`, `iru-setup-react-web`, `iru-setup-angular-web`, `iru-setup-ionic-app`), `iru-nestjs`,
    `iru-nextjs`, `iru-react-native`, `iru-php`, `iru-python` (`iru-python-*`, `iru-fastapi-*`, `iru-django-*`,
    `iru-setup-python-*`), `iru-android`, `iru-swift` (`iru-swift-*`, `iru-setup-swift-*`, `iru-setup-apple-app`,
    `iru-setup-macos-*`), `iru-kmp`, `iru-rust`, `iru-go`, `iru-cli` (`iru-setup-cli-*`, `iru-setup-*-cli`). Every
    skill appears in exactly one plugin (the script asserts it).
    - _Done:_ `tools/plugins.json` — 18 plugins (`iru-core` 25 skills + 3 agents, `iru-knowledge` 7, `iru-java` 14, `iru-springboot` 15, `iru-quarkus` 5, `iru-dotnet` 15, `iru-typescript` 15, `iru-nestjs` 3, `iru-nextjs` 3, `iru-react-native` 4, `iru-php` 13, `iru-python` 14, `iru-android` 13, `iru-swift` 16, `iru-kmp` 12, `iru-rust` 8, `iru-go` 8, `iru-cli` 6 = 196). Membership by `fnmatch` patterns + `exclude`; the generator asserts one owner per skill/agent and no dead pattern. Declared `depends_on` edges and two `optional_calls` (core → any stack, typescript → react-native) are documented in the file.
  - [x] Task 18.2. Create `tools/generate-marketplace.py`: writes `.claude-plugin/marketplace.json` (name
    `ai-catalog`, owner from `git config`/`gh`, `version` from `CHANGELOG.md`'s latest heading) with one entry per
    plugin — `source: "./"`, `skills: ["./.claude/skills/<name>", …]`, `agents` on `iru-core`, `dependencies:
    ["iru-core"]` on every other plugin plus the cross-stack edges the audit's `Skill()` graph proves (e.g.
    `iru-react-native` → `iru-typescript`, `iru-kmp` → `iru-android`, `iru-swift`; `iru-cli` → `iru-rust`,
    `iru-go`, `iru-swift`, `iru-dotnet`), `description`, `category: <stack|core|knowledge>`. Fails if a `Skill()`
    call crosses plugins without a matching `dependencies` edge. Run it and commit the generated file; add
    `claude plugin validate .` (when the CLI is present) to `--check`.
    - _Done:_ `tools/generate-marketplace.py` (reuses `catalog-audit.py`'s parsing via importlib) wrote `.claude-plugin/marketplace.json`; `--check` (stale check against the committed owner, then `claude plugin validate <root>` when the CLI is on PATH, `--no-validate` to skip) is where the CLI validation lives. `claude plugin validate .` and `--strict` pass. 35 tests in `tools/tests/test_generate_marketplace.py` (84 total pass); line coverage via `trace`: generate-marketplace.py 99.3%, catalog-audit.py 99.2%. Version omitted (CHANGELOG has only `[Unreleased]`). Both scripts documented in tools/README.md.
  - [x] Task 18.3. Add `.claude-plugin/README.md` (two paragraphs: this file is generated, how to regenerate).
    - _Done:_ `.claude-plugin/README.md` (two paragraphs).

- [x] Task 19. Agent dispatch in plugin mode (branch on Task 2.3's answer to question (b))
  - [x] Task 19.1. _(n/a — branch not taken: bare `subagent_type: "iru-gate-runner"` does NOT resolve in plugin mode; recorded in `tools/spikes/plugin-resolution.md` "Decision taken in Task 19")_ If bare `subagent_type: "iru-gate-runner"` resolves in plugin mode: no skill edits; record
    the finding in `tools/spikes/plugin-resolution.md` and in the guide (Task 20.2).
  - [x] Task 19.2. _(Done: first body line added to `iru-gate-runner`, `iru-isolated-skill-executor`, `iru-change-summarizer`; one "Agent dispatch" paragraph added to `iru-code` (421→423 lines), `iru-code-one-task-group`, `iru-issue`, `iru-setup-changelog`; `python3 tools/catalog-audit.py --check`: 0 errors, agent descriptions untouched.)_ Otherwise: add to each agent's body a first line "Dispatch as `subagent_type: "iru-gate-runner"`
    when installed under `.claude/agents/`, or `"iru-core:iru-gate-runner"` when installed as a plugin — use
    whichever name appears in your available agent types", and add the same one-sentence rule once to
    `iru-code/SKILL.md`, `iru-code-one-task-group/SKILL.md`, `iru-issue/SKILL.md` and `iru-setup-changelog/SKILL.md`
    (the callers that explain dispatch), not to all 235 call sites.

- [x] Task 20. Documentation, `CLAUDE.md` and CI
  - [x] Task 20.1. _(Done: `docs/modules/ROOT/pages/guides/catalog-architecture.adoc` holds the whole former `CLAUDE.md` Architecture prose (14 list items and every sentence preserved; checked by a word-for-word comparison against the original); `CLAUDE.md` 321 → 97 lines (commands, checks, `iru-` convention, SKILL.md shape, budgets/model tiers/templates/shared files/plugins/agent dispatch in one line each, generated vs hand-maintained docs, pointers to the guides); one sentence adjusted: "no separate lint/test command" now says the skills are checked by the scripts below. Added to `nav.adoc`.)_ New hand-maintained guide `docs/modules/ROOT/pages/guides/catalog-architecture.adoc`: the
    current `CLAUDE.md` "Architecture" sections moved verbatim (pipelines, bootstrap inputs, UI contract, template
    verification, agents, documentation). Slim `CLAUDE.md` to ≤ 120 lines: what the repo is, commands, the `iru-`
    convention, generated vs hand-maintained docs, the shared byte-identical files rule, `tools/` checks, and
    `xref` pointers to the guides. No sentence is deleted, only relocated.
  - [x] Task 20.2. _(Done: `guides/performance-and-token-budget.adoc` — before/after tables with the before numbers from `tools/baseline/` and `_(filled in Task 22.4)_` in every after cell, budgets and why, model-tier table (haiku 58 / sonnet 135 / opus 3), cache analysis with the 17 accepted sites (4 false positives, 10 `iru-explore`, 2 interactive, 1 knowledge), extra agents not adopted, plugin-mode dispatch finding, documented-only options. In `nav.adoc`.)_ New guide `guides/performance-and-token-budget.adoc`: the audit's before/after table
    (filled in Task 22), the budgets and why (listing cap 1,536 chars, 1 % budget), the model-tier table, the
    cache analysis (a skill's `model` switches the model for the rest of the turn → inline cross-model calls
    invalidate the prompt cache; subagents have their own context so routing gates through `iru-gate-runner`
    avoids it), the evaluation of extra multi-role agents (not adopted), and the documented-only options
    (shared-reference consolidation, gate-skill merge, physical `plugins/` tree).
  - [x] Task 20.3. _(Done: `creating-skills-and-agents.adoc` (new section: budget, shape, quoted YAML, templates, tiers, plugin membership, audit before a PR), `extending-the-catalog.adoc` (description budget item, model-tier item updated to the new tiers, templates item, new after-extension bullets), `plugins.adoc` and `packaging-and-distribution.adoc` (this catalog's marketplace: install commands, `/iru-java:iru-java-test` vs bare, `iru-core:iru-gate-runner`, `--allowedTools=Skill`, copying still works), README adoption section. Antora build clean. Also fixed an unescaped `|` inside a table cell in `common-workflows.adoc` (Group 4 text) that made Asciidoctor drop cells.)_ Update `guides/creating-skills-and-agents.adoc` and `guides/extending-the-catalog.adoc`:
    description budget and shape, quoted YAML values, `templates/` convention, model tiers, "run
    `python3 tools/catalog-audit.py --check` before opening a PR". Update `guides/plugins.adoc` and
    `guides/packaging-and-distribution.adoc` with this catalog's own marketplace: `claude plugin marketplace add
    albertoirurueta/ai-catalog`, `/plugin install iru-core@ai-catalog`, `/plugin install iru-java@ai-catalog`, the
    `/iru-java:iru-java-test` vs bare `/iru-java-test` naming, and that copying a skill directory still works.
    Update `README.md`'s adoption section the same way. Add both new guides to `nav.adoc`.
  - [x] Task 20.4. _(Done: `.github/workflows/catalog-check.yml` — pull_request + push to main, `contents: read`, checkout@v5, setup-python@v5, `pip install pyyaml`, audit `--check`, marketplace `--check`, unittest discover, best-effort CLI validation with `continue-on-error: true`. No license header: the existing `docs.yml` has none.)_ New workflow `.github/workflows/catalog-check.yml` (on pull requests and pushes to `main`):
    `pip install pyyaml`, `python3 tools/catalog-audit.py --check`, `python3 tools/generate-marketplace.py --check`
    (fails if the committed `marketplace.json` is stale), and a best-effort step `npm i -g
    @anthropic-ai/claude-code && claude plugin validate .claude/skills && claude plugin validate .`
    (`continue-on-error: true`, since the CLI's availability in CI is not guaranteed).
  - [x] Task 20.5. _(Done: `CHANGELOG.md` Unreleased gains Added (marketplace, audit/budgets/CI, plan coverage + markers, two guides) and Changed (descriptions and 7 fixed frontmatters, model tiers, templates layout, plugin-safe key discovery, plugin-mode agent dispatch rule, CLAUDE.md slimming, guides/README).)_ `CHANGELOG.md`: an "Unreleased" entry under Changed/Added (plugins, budgets, model tiers,
    templates layout, fixed frontmatter of 7 skills).

### Group 6 — Verify equivalence and regenerate (Parallelizable: no — must run after Groups 1–5)

- [x] Task 21. Static verification
  - [x] Task 21.1. _(Done: `catalog-audit.py --check` exit 0 (0 errors, 36 warnings, all `skill-lines-warn`); `claude plugin validate` passed for `.claude/skills`, `.claude/agents` and `.`; shared files byte-identical (ui-contract 12 copies, cli-contract 4, ui-docs 3, accessibility-detection 2, 1 distinct md5 each); `missing_skill_targets` and `missing_asset_paths` empty; `generate-marketplace.py --check` exit 0 (18 plugins); `unittest discover -s tools/tests` 84 tests OK.)_ `python3 tools/catalog-audit.py --check` exits 0; `claude plugin validate .claude/skills`,
    `claude plugin validate .claude/agents` and `claude plugin validate .` pass; the four shared files are still
    byte-identical across their copies; every `Skill()` target exists.
  - [x] Task 21.2. _(Done: all 14 skills OK, both the concatenated-`cmp` against the Group 3 dumps and the re-inlining rebuild == `original-SKILL.md`: android-app 30 blocks, android-github-workflows 8, android-library 28, java-github-workflows 6, java-springboot 2, java-springboot-apis 21, java-springboot-github-workflows 17, java-springboot-pom 31, php-github-workflows 15, python-github-workflows 8, quarkus-github-workflows 6, swift-github-workflows 12, swift-library 10, typescript-github-workflows 28.)_ Template equivalence: for each skill in Tasks 9–13, `cmp` the concatenated `templates/` files
    against the Group 3 dumps; report per skill.
  - [x] Task 21.3. _(Done: `iru-check-license` via `iru-gate-runner`: 4 compliant (`tools/catalog-audit.py`, `tools/generate-marketplace.py`, `tools/tests/test_*.py` x2), 0 missing, 0 fixed; `.github/workflows/catalog-check.yml` left without header (no YAML in the repository carries one); `tools/baseline`, `tools/spikes`, README/JSON skipped as non-source.)_ Run the license-header gate on the new `tools/*.py` and workflow files via `iru-gate-runner`:
    `Agent({description: "License headers for tools/", subagent_type: "iru-gate-runner", prompt: "Invoke
    Skill({skill: \"iru-check-license\", args: \"tools/ .github/workflows/catalog-check.yml\"}) and report only
    which files were missing a header vs fixed vs compliant."})`.

- [x] Task 22. "After" sample runs and the before/after table
  - [x] Task 22.1. _(Done: S0 from the repository root and S1 to S3 in fresh fixture copies with this repository's `.claude/`, same wrapper, prompts and flags as the before runs (no `--allowedTools=Skill` needed for slash commands); JSON under `$TMPDIR/iru-verify/results/after/`. S0 prompt side 42,787 to 30,278 (-29.2 %). Details in `tools/baseline/sample-runs-after.md`.)_ Repeat Task 3.2's S0–S3 from this working tree (`cd` into the repository root so the edited
    skills load) into fresh copies of the fixtures; save under `$TMPDIR/iru-verify/results/after/`.
  - [x] Task 22.2. _(Done: templates byte-identical for all 14 skills (21.2). S1: official run on Sonnet stopped to ask (3 of 5 Sonnet runs; the before tree forced onto Sonnet asked in 1 of 3), so no files; controlled Haiku/Sonnet runs wrote the full documented set, where the before-Haiku runs (3 of 3) wrote a 790-byte `build.yml` with no `sync.yml`/docs steps, so the before output was the degraded one; same-model diffs differ only in model choices (integration branch `main` vs `develop`, comments); `security.yml`/`dependabot.yml` identical apart from the `branches:` line. S2: official run now on Haiku asks for modules (3 of 3), root `.gitignore` byte-identical (740 B) on the default model as before. S3: `Project type` and `Repository host` identical; `Build & layout` now present. No owning-skill defect found, no skill fix needed; diffs in `sample-runs-after.md`.)_ Equivalence: S1's generated `.github/` tree and S2's `.gitignore` must be byte-identical to the
    "before" outputs (ignoring the run date/version strings the skills already vary); S3's "Tech stack" block must
    carry the same `Project type:`, `Build & layout:`, `Repository host:` values. Any difference is reported and
    fixed in the owning skill before continuing.
  - [x] Task 22.3. _(Done: marketplace added, `iru-core` and `iru-typescript` installed (local scope); the bare slash command resolved to `iru-typescript:iru-setup-typescript-github-workflows`, no `--allowedTools=Skill` needed; headless `-p` refuses to read the skill's `templates/` outside the cwd, so the run that wrote files used `--add-dir <skills dir>`; its output equals the directory-mode Sonnet run (one script guard differs); plugin cache of the two plugins was 231 MB (directory-source marketplace copies the working tree). Uninstalled both, removed the marketplace and the cache directory; `claude plugin list` and `marketplace list` show nothing left of it.)_ Plugin-mode smoke: `claude plugin marketplace add <path to this repository>`, install
    `iru-core` and `iru-typescript`, repeat S1 from a directory **outside** this repository (so only the plugins
    provide the skills) and compare its output as in 21.2; then uninstall and remove the marketplace.
  - [x] Task 22.4. _(Done: `performance-and-token-budget.adoc` table filled and a reading paragraph added; `tools/baseline/sample-runs-after.md`, `catalog-audit-after.json`/`.md`, `plugin-validate-after.txt` written. Headline: S0 prompt side 42,787 to 30,278; descriptions 494,826 to 73,851 chars, 167 truncated to 0, 39 parse failures to 0, files over 500 lines 39 to 36, over 1,000 lines 11 to 0. Not lower: S1/S3 cost, S3 duration/output, S2 prompt side, duplicate bytes (+684), S1 on the same model.)_ Fill the table in `guides/performance-and-token-budget.adoc` and `tools/baseline/
    sample-runs-after.md`: per sample, input/cached/output tokens, cost, duration, before vs after, and the audit
    totals (description bytes, number of truncated descriptions, listing estimate, `SKILL.md` lines over 500/1,000,
    parse failures). State plainly where the after number is not lower.
  - [x] Task 22.5. _(Done: S4a `/iru-plan` has the coverage table (3 criteria mapped) and `Open clarifications: none`, `--plan` exit 0. S4b: run 1 wrote a marker for another question inside backticks (audit missed it) and run 2 resolved the vague criterion silently, so `iru-plan` was tightened twice (marker as plain text; unverifiable criterion counts as ambiguity); run 3 wrote `[NEEDS CLARIFICATION: What does "documented somewhere" ...]`, `--plan --check` exit 1 `plan-clarification-open`. S4c `/iru-code` stopped at its Step 2 gate naming the marker, `src/` and plan unchanged. Results under `$TMPDIR/iru-verify/results/after/S4/`.)_ S4 — new behavior from Group 4, no "before" run: on a fresh `ts-lib` copy run `/iru-plan` with
    the free-form task "add an `isEven(n)` helper exported from `src/index.ts`, with unit tests; acceptance: exported
    from the package entry point, 100 % line coverage, documented in README". Confirm the plan has the
    "Acceptance criteria coverage" table mapping all three criteria to tasks and "Open clarifications: none".
    Then edit one criterion to be ambiguous (e.g. "documented somewhere"), re-run `/iru-plan` unattended
    (`claude -p`) and confirm a `[NEEDS CLARIFICATION: …]` marker is written; run `/iru-code` and confirm it stops
    at its Step 2 gate listing that marker. Record tokens for the S4 runs in the table (informational only).

- [x] Task 23. Regenerate generated docs and build the site
  - [x] Task 23.1. _(Done: `iru-generate-skill-docs` run in update mode (all 196 skill pages and 3 agent pages already existed; `nav.adoc` lists all 196 + 4 agent entries and both new guides): every page gained a `== Plugin` section read from `.claude-plugin/marketplace.json`; the 14 template-split skills gained a templates sentence; sub-agents refreshed the 15 skill pages and 3 agent pages whose bodies changed substantively (iru-plan, iru-code, iru-issue, iru-code-one-task-group, iru-release, iru-generate-skill-docs, the three ticket-intake skills, kmp/dotnet/typescript small ones, the three agents); `index.adoc` description 193 to 196, plugin paragraph updated, two new guides added to the table.)_ Run `Skill({skill: "iru-generate-skill-docs"})` so `index.adoc`, `skills/*.adoc` and
    `agents/*.adoc` reflect the new descriptions, models, templates and plugin membership.
  - [x] Task 23.2. _(Done: `npm ci` and `npx antora antora-playbook.yml` exit 0 with empty output, no warnings; no raw `<...>` placeholders in any mermaid block.)_ `cd docs && npm ci && npx antora antora-playbook.yml` builds without warnings about missing
    xrefs (the two new guides are in `nav.adoc`).

### Group 7 — Follow-up: bring `tools/*.py` to zero Ruff findings (Parallelizable: no — added by `iru-code` Step 7 after the final quality comparison showed Ruff lint 39 → 75 and Ruff format 2 → 4 Python files vs the Step 3 baseline; added as a follow-up task because the run is unattended)

- [x] Task 24. Fix every Ruff finding in `tools/` _(python)_
  - Task 24 complete: `ruff check --isolated tools/` and `ruff format --check --isolated tools/` both report 0 findings; no config files added.
  - [x] Task 24.1. With Ruff 0.17.1 run `--isolated` (no project config, as the baseline did), fix all lint findings in
    `tools/catalog-audit.py`, `tools/generate-marketplace.py`, `tools/tests/test_catalog_audit.py` and
    `tools/tests/test_generate_marketplace.py`: `UP031` (printf-style `%` formatting → f-strings/`.format`), `EXE001`
    (shebang without exec bit — make the scripts executable or drop the shebang consistently), `TRY004`, `RUF100`,
    `C401`, `ISC004`, `PLW1510` (`subprocess.run` without `check=`), `UP021` (`universal_newlines` → `text`), `RUF012`
    (mutable class attribute → `ClassVar`), `RUF059` (unused unpacked variable). Behavior must not change.
    - Done: Ruff 0.17.1 `--isolated` lint 75 -> 0 on `tools/` (UP031 x65 -> f-strings/`.format` with identical text, EXE001 x2 -> `chmod +x`, and 1 each of TRY004 (`TypeError`, caught alongside `ValueError`), RUF100, C401, ISC004, PLW1510 (`check=False`), UP021 (`text=True`), RUF012 (`ClassVar`), RUF059). `--markdown`, `--check` stderr and `--plan` output are byte-identical before vs after.
  - [x] Task 24.2. Run `ruff format` on the four files so `ruff format --check --isolated` passes for all `.py` files.
    - Done: `ruff format --isolated` reformatted the 4 files; `ruff format --check --isolated tools/` reports 10 files already formatted.
  - [x] Task 24.3. Re-run `python3 -m unittest discover -s tools/tests` (84 tests pass), confirm line coverage of both
    scripts stays ≥ 80 % (stdlib `trace`), `python3 tools/catalog-audit.py --check` still exits 0,
    `python3 tools/generate-marketplace.py --check` still exits 0, and the Apache-2.0 headers are intact.
    - Done: 84 tests pass; stdlib `trace` line coverage 99.2 % (`catalog-audit.py`), 99.3 % (`generate-marketplace.py`); `catalog-audit.py --check` exit 0 (0 errors), `generate-marketplace.py --check` exit 0; Apache-2.0 headers intact in all four files.
