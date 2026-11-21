# Implementation plan — functional definition skills and reviewer agent (issue 41)

## Task summary

Add a functional-definition capability to the catalog so every GitHub issue or Jira ticket is created or updated with a
fixed shape (Context, Requirements, Acceptance criteria incl. a mandatory functional-documentation criterion `AC-DOC`),
grounded in a repository exploration, completeness-gated by asking the user for anything missing, and reviewed for gaps
and wrong definitions by an independent agent in a fresh context. The full specification is issue 41 (requirements
R1–R11, acceptance criteria AC1–AC16 and AC-DOC); this plan implements it as written.

Choices made (no ambiguity needed the user):
- All tasks are untagged: they edit Markdown skills/agents, JSON registries, Python-free config and AsciiDoc, plus the shared
  Node `.mjs` Mermaid scripts (documented as part of the shared byte-identical set); no `iru-<key>-code-one-task` skill
  covers them, so `iru-code-one-task-group` implements them directly.
- The canonical copy of the two shared reference files is written under `iru-functional-definition/reference/` first,
  then copied byte-identically (`cp`) into every skill that needs it (Task 1); the audit enforces identity.
- Shared files are registered by their path relative to a skill directory (as the existing `reference/toolchain.md`
  entry is): `reference/functional-definition-template.md` and `reference/functional-definition-checklist.md`.
- The `iru-update-docs` argument contract (Task 13) is `target: markdown|antora|mcp`, `pages: <comma-separated paths>`,
  `content: <comma-separated kinds>` (kinds: data-model, uml-class, sequence, workflow, architecture, api, configuration,
  equations, figures). `iru-code` (Task 14) forwards it.
- Nothing existing is renamed, merged or moved (per the issue's out-of-scope list).

Source: GitHub issue #41
Base branch: main
Open clarifications: none

## Acceptance criteria coverage

| # | Criterion | Covered by tasks |
|---|---|---|
| 1 | "AC1 (R1, R10). `python3 tools/catalog-audit.py --check` exits 0; both reference files byte-identical in every listed skill, changing one copy makes the check fail" | Task 1, Task 15, Task 18 |
| 2 | "AC2 (R10). `generate-marketplace.py --check`, `claude plugin validate .`, `claude plugin validate .claude/skills`, unittest all succeed; marketplace lists both skills and the agent under `iru-core`" | Task 15, Task 18 |
| 3 | "AC3 (R9, R11). Antora build, Pagefind, `test:nav`, `test:nav:site` succeed and `validate:mermaid` passes for every diagram incl. the new sequence diagram" | Task 11, Task 16, Task 17, Task 18 |
| 4 | "AC4 (R2). `/iru-functional-definition \"Add CSV export of the orders list\"` writes a draft with Context, Requirements and Acceptance criteria with verification methods and a negative case" | Task 3, Task 18.2 |
| 5 | "AC5 (R2). `AC-DOC` offered via `AskUserQuestion` with detected targets; accepting records target/pages/kinds, declining records `not required — <reason>`" | Task 3, Task 18.2 |
| 6 | "AC6 (R2). A prompt with no expected behaviour leads to questions; no invented criteria or placeholders" | Task 3, Task 18.2 |
| 7 | "AC7 (R2). Update mode shows before/after, preserves unchanged sections, `gh issue edit` only after confirmation" | Task 3, Task 18.2 |
| 8 | "AC8 (R4). Agent returns an `incorrect` finding for a nonexistent artefact and `missing-functionality` for a missing validation-error requirement; caller receives only the block" | Task 2, Task 18.3 |
| 9 | "AC9 (R2, R4). Review loop stops after at most 3 rounds; remaining findings shown before filing" | Task 3, Task 7, Task 18.3 |
| 10 | "AC10 (R3). `/iru-review-functional-definition <n>` prints the block unchanged and posts or edits nothing unless chosen" | Task 4, Task 18.3 |
| 11 | "AC11 (R5). `/iru-create-github-issue` without criteria asks for them and for `AC-DOC`; confirmation is not shown until the definition is complete" | Task 5, Task 18.4 |
| 12 | "AC12 (R5). `/iru-create-jira-ticket` without a Jira MCP stops as today; with one, same sections (else marked unverified)" | Task 6, Task 18.4 |
| 13 | "AC13 (R5, R6). `/iru-draft-github-issue functional` uses canonical headings and `AC-DOC`; review of a draft without `AC-DOC` returns a `gap`, output format unchanged" | Task 7, Task 8, Task 18.4 |
| 14 | "AC14 (R7). `/iru-plan` maps `AC-DOC` and `curl`/`api` criteria to tasks" | Task 12, Task 18.5 |
| 15 | "AC15 (R8, R9). In a Markdown-docs repository `iru-code` updates `docs/*.md` with a Mermaid fence, a relative SVG and `$$…$$`; Markdown-extended `validate-mermaid` passes; Antora repositories unchanged" | Task 11, Task 13, Task 14, Task 18.5 |
| 16 | "AC16 (R2). On a non-GitHub remote with no Jira MCP both new skills stop with a clear message and write nothing" | Task 3, Task 4, Task 18.6 |
| 17 | "AC-DOC. Antora pages for the new skills/agent and guides, with workflow, architecture and data-model content; pages build and diagrams validate" | Task 16, Task 17 |

## Current code state

- **Intake skills** (`.claude/skills/`): `iru-create-github-issue` and `iru-create-jira-ticket` have Steps 1–9
  (explore → purpose → context → due date/importance → draft → confirm → create → report); their Step 7 drafts
  *Summary / Context / Acceptance criteria (omitted if none) / Task details / References* and Step 3 asks only for purpose.
  `iru-draft-github-issue` (+ `reference/issue-templates.md`, functional template with `FRn`/`ACn (FRm)`) loops up to 5 rounds
  through `iru-review-github-issue` (+ `reference/issue-quality-checklist.md`; output block `Verdict/Kind/Findings/Suggestions`,
  classes gap|pending|inconsistency|doubt). `iru-split-github-issue` reads `draft:<path>`. `iru-knowledge-to-issue` /
  `iru-knowledge-to-jira` delegate to the create skills.
- **Pipeline**: `iru-plan` Step 6 writes the `## Acceptance criteria coverage` table and ends with an untagged documentation
  task running `/iru-update-docs`; `iru-code` Step 8 invokes `Skill({skill: "iru-update-docs"})` with no arguments;
  `iru-update-docs` Steps 2–5 write Antora pages and, with approval, a documentation MCP; no Markdown-docs path exists.
- **Agents** (`.claude/agents/`): `iru-gate-runner` (haiku, tools `Skill, Bash, Read`), `iru-isolated-skill-executor`,
  `iru-change-summarizer`; each file begins with a dispatch note for `subagent_type` / `iru-core:` naming.
- **Shared Mermaid tooling**: `scripts/mermaid/{blocks,validate-mermaid}.mjs` (+ `blocks.test.mjs`) and
  `reference/mermaid.md` are byte-identical in `iru-setup-antora`, `iru-build-docs`, `iru-update-antora` (and
  `iru-update-docs` for `reference/mermaid.md`); `docs/scripts/` mirrors `iru-setup-antora/scripts`. `blocks.mjs` recognises
  only AsciiDoc `[mermaid]` blocks.
- **Registry/audit**: `tools/plugins.json` (`iru-core` lists skills and the three agents), `tools/catalog-budgets.json`
  (`shared_identical_files`, `mirrored_directories`, `inline_cross_model` allow-list with `caller`/`callee`/`reason`,
  agent model whitelist incl. `opus`), `tools/catalog-audit.py` (descriptions ≤1,024, invocation form in first 200,
  agent model required, shared-file identity). `.claude-plugin/marketplace.json` is generated.
- **Docs**: Antora under `docs/`; generated pages `docs/modules/ROOT/pages/{index,skills/*,agents/*}.adoc` and `nav.adoc`
  from `/iru-generate-skill-docs`; hand-maintained guides under `guides/` (`creating-tickets.adoc` has a
  "Detailed, spec-style issues" section). No `.ui-quality.yml`, no UI.
- No documentation MCP is connected; `.archive/implementation_plan_34.md` is the structural precedent.

## Implementation steps

### Group 1 — Shared reference files and reviewer agent (Parallelizable: yes — disjoint files)

- [x] Task 1. Write the shared functional-definition reference files and distribute byte-identical copies
  - [x] Task 1.1. Create `.claude/skills/iru-functional-definition/reference/functional-definition-template.md`: tracker-neutral draft
    format (first line `# <title>`), sections Context / Requirements (`R1…`) / Acceptance criteria (`AC1 (R1)…`) /
    optional Technical details, Out of scope, Dependencies and related tickets, Task details, References; the verification-method
    vocabulary table (`automated-test`, `form-input`, `ui-browser`, `ui-simulator`, `api`, `cli`, `data`, `performance`,
    `manual`) with a concrete example each (Playwright scenario vs. design reference, `curl` command + expected status/body,
    field values that succeed/fail); the mandatory `AC-DOC` block (accepted: target, pages, content kinds from data model /
    UML / sequence / workflow / architecture / API definition / configuration properties / equations / figures, formats
    Mermaid + SVG + MathJax; declined: `AC-DOC. Functional documentation: not required — <reason>`); rule that `FRn` headings of the
    existing draft template are accepted as equivalent; a worked example.
  - [x] Task 1.2. Create `.claude/skills/iru-functional-definition/reference/functional-definition-checklist.md` in the style of
    `iru-review-github-issue/reference/issue-quality-checklist.md`: items with id, check, how to verify, failing/passing example
    (context grounded; requirements testable; R↔AC traceability; verification method with concrete values; negative cases;
    `AC-DOC` present; no placeholders; no contradictions; named artefacts exist or marked new; verification method feasible in
    this repository) plus the finding classes `gap`, `pending`, `inconsistency`, `doubt`, `missing-functionality`, `incorrect`.
  - [x] Task 1.3. Copy both files with `cp` into `reference/` of `iru-review-functional-definition`, `iru-create-github-issue`,
    `iru-create-jira-ticket`, `iru-draft-github-issue`, `iru-review-github-issue`, `iru-plan`, `iru-update-docs` (create the
    `iru-review-functional-definition/` directory; its `SKILL.md` comes in Task 4). Verify with `diff`/`cmp`.
- [x] Task 2. Create the agent `.claude/agents/iru-functional-reviewer.md`
  - [x] Task 2.1. Frontmatter: `name: iru-functional-reviewer`, quoted `description` (≤1,024 chars), `model: opus`, `tools: Read, Grep, Glob, Bash, WebFetch`;
    first body line is the dispatch note (`subagent_type: "iru-functional-reviewer"` or `"iru-core:iru-functional-reviewer"`) like the other agents.
  - [x] Task 2.2. Body: inputs (draft path, checklist path, tracker, optional `iru-explore` summary); work (run every checklist item;
    verify every named artefact with grep/Read; fetch cited URLs; hunt `missing-functionality` — callers, error/empty states, validation,
    permissions, persistence/migrations, config, i18n, accessibility, backwards compatibility, tests that change; hunt `incorrect` —
    contradictions with code/docs/another requirement, verification methods infeasible in this repository); strictly read-only; output only the
    `Verdict / Findings / Suggestions` block with `[class] <section/id> — <what, with file:line evidence> — Question: <exact question>`.

### Group 2 — New skills (Parallelizable: yes — two new directories, both depend only on Group 1)

- [x] Task 3. Create `.claude/skills/iru-functional-definition/SKILL.md` (`model: sonnet`)
  - [x] Task 3.1. Frontmatter: quoted description with invocation `/iru-functional-definition [<ticket-id> | draft:<path>] [<initial functional description>]`
    in the first 200 characters, ≤1,024 total.
  - [x] Task 3.2. Steps: (1) resolve tracker — GitHub host check as in `iru-create-github-issue`, Jira MCP check as in `iru-create-jira-ticket`, stop with a
    clear message for anything else and write nothing; (2) parse arguments → create mode / update mode (ticket id auto-detected like `iru-explore`,
    fetch with `gh issue view … --json number,title,body,labels,comments,state,url` or Jira MCP) / `draft:<path>`; (3) `Skill({skill:"iru-explore"})`
    (no argument in create mode, ticket id in update mode, skipped if already done this conversation); (4) draft from `reference/functional-definition-template.md`,
    preserving unchanged content in update mode; (5) completeness gate — ask in small batches (plain text for open answers, `AskUserQuestion` for choices),
    propose candidate requirements/criteria derived from code and prompt, never invent; (6) `AC-DOC` offer with detected targets (Antora `antora.yml`,
    Markdown docs folder / README sections, documentation MCP via `ToolSearch` "confluence"/"notion"/"wiki") and suggested content kinds;
    (7) review loop dispatching `Agent({subagent_type:"iru-functional-reviewer", …})` with draft path and the absolute path of its own checklist copy, resolving
    findings from the codebase first, else asking the finding's `Question:`, maximum 3 rounds, remaining findings shown to the user; (8) output the
    final draft path and a summary; `mode: embedded` / `tracker:` args return the path without filing; standalone update mode shows before/after and applies
    only after `AskUserQuestion` confirmation (`gh issue edit <n> --body-file …`, Jira MCP update, fallback comment; Jira formatting conversion).
  - [x] Task 3.3. Add a `## Verification` section stating which calls were exercised and which are unverified (Jira MCP, `gh issue edit`).
- [x] Task 4. Create `.claude/skills/iru-review-functional-definition/SKILL.md` (`model: sonnet`)
  - [x] Task 4.1. Frontmatter with invocation `/iru-review-functional-definition <ticket-id> | draft:<path>` in the first 200 characters.
  - [x] Task 4.2. Steps: resolve tracker (same stop rules); fetch ticket with comments or read the draft; write a draft file; dispatch `iru-functional-reviewer`
    with the checklist path; print the block unchanged; for existing tickets only, `AskUserQuestion` — leave untouched / post findings as comment / hand over to
    `/iru-functional-definition <id>`; read-only unless confirmed; `## Verification` section.

### Group 3 — Ticket-intake skills (Parallelizable: yes — each task edits a different skill directory)

- [x] Task 5. Update `.claude/skills/iru-create-github-issue/SKILL.md`: after Step 3 call `Skill({skill:"iru-functional-definition", args:"mode: embedded\ntracker: github\n<prompt>"})`;
  rewrite Step 7 so the body is Context / Requirements / Acceptance criteria incl. `AC-DOC` plus the existing Task details and References; delete the "omit acceptance criteria rather than
  invent" rule (missing criteria are asked for); Step 8 cannot show "Create the issue now" until the gate passes unless the user accepts listed known gaps, which are then written into the body;
  keep Step 1 host check and attachment handling unchanged.
- [x] Task 6. Update `.claude/skills/iru-create-jira-ticket/SKILL.md` the same way (`tracker: jira`), keeping the Jira-MCP check, epic, attachment upload and `iru-jira-custom-context` folding.
- [x] Task 7. Update `.claude/skills/iru-draft-github-issue/SKILL.md` and `reference/issue-templates.md`: functional template uses the canonical headings and `AC-DOC`; the functional interview
  delegates to `iru-functional-definition`; Step 7 dispatches `iru-functional-reviewer` in addition to `iru-review-github-issue`, merging and de-duplicating findings; the documentation kind and the 5-round cap
  for the documentation kind are unchanged (functional definition uses 3).
- [x] Task 8. Update `.claude/skills/iru-review-github-issue/SKILL.md`: for `Kind: functional` also read `reference/functional-definition-checklist.md` (verification method, negative cases, `AC-DOC` decision);
  the output block format and four finding classes stay exactly as they are (new checks map to `gap`/`doubt`).
- [x] Task 9. Update `.claude/skills/iru-split-github-issue/SKILL.md`: sub-issue drafts keep the canonical sections; `AC-DOC` goes on the sub-issue whose change it documents, or on the root when it spans all.
- [x] Task 10. Verify `iru-knowledge-to-issue` and `iru-knowledge-to-jira` pass the meeting context as the initial prompt and that gate questions still reach the user; edit their Step 8 text only if it
  currently suppresses the create skills' questions.

### Group 4 — Mermaid scripts and planning (Parallelizable: yes — disjoint files)

- [x] Task 11. Extend the Mermaid validator to Markdown fences (`scripts/mermaid/blocks.mjs`, `validate-mermaid.mjs`, `blocks.test.mjs`)
  - [x] Task 11.1. Edit `.claude/skills/iru-setup-antora/scripts/mermaid/blocks.mjs` so it also extracts ```` ```mermaid ```` fences from `.md` files (same static checks, size limit and label-escape rules); update
    `validate-mermaid.mjs` to scan `.md` files under the given roots and add unit tests to `blocks.test.mjs`.
  - [x] Task 11.2. Copy the three files byte-identically to `iru-build-docs/scripts/mermaid/`, `iru-update-antora/scripts/mermaid/` and `docs/scripts/mermaid/`; update `reference/mermaid.md` (Markdown fence rules)
    and copy it to every skill that has it (`iru-setup-antora`, `iru-build-docs`, `iru-update-antora`, `iru-update-docs`).
  - [x] Task 11.3. Run `cd docs && npm run test:nav` and `python3 tools/catalog-audit.py --check` to prove copies are identical.
- [x] Task 12. Update `.claude/skills/iru-plan/SKILL.md` Step 6: the `## Acceptance criteria coverage` rows also name each criterion's verification method and the task that implements or runs it
  (Playwright/simulator UI tests, `curl` checks as integration tests or documented commands, form-validation tests); `AC-DOC` maps to the final documentation task, whose text carries the docs target, pages and
  content kinds (row reads "not required" when declined, the task still runs `/iru-update-docs`); a ticket without `AC-DOC` is planned as today.

### Group 5 — Documentation update pipeline (Parallelizable: no — Task 14 forwards the argument contract that Task 13 defines)

- [x] Task 13. Update `.claude/skills/iru-update-docs/SKILL.md`: add arguments `target:`, `pages:`, `content:`; Step 2 also detects an in-repository Markdown docs folder / README sections when no Antora site exists
  or `target: markdown`; add a Markdown path (GitHub-flavoured: ```` ```mermaid ```` fences validated with the extended `validate-mermaid`, equations as `$…$`/`$$…$$`, SVG figures beside the pages with relative links);
  produce each requested content kind (data model, UML, sequence, workflow, architecture, API definition, configuration properties, equations, figures) on any target; the documentation-MCP approval-before-send rule and
  Antora behaviour stay unchanged.
- [x] Task 14. Update `.claude/skills/iru-code/SKILL.md` Step 8: read the `AC-DOC` details from the plan's documentation task and invoke `Skill({skill:"iru-update-docs", args:"target: …\npages: …\ncontent: …"})`; with no
  `AC-DOC` or when declined, invoke it as today.

### Group 6 — Catalog wiring and guides (Parallelizable: yes — disjoint files)

- [x] Task 15. Register everything
  - Note: plugins.json, catalog-budgets.json (entry is under `accepted_cross_model_calls`), CLAUDE.md updated; audit 0 errors, marketplace current, both plugin validations pass, 107 tools tests OK. Fixed a syntax error (unescaped backticks) in the four validate-mermaid.mjs copies.
  - [x] Task 15.1. `tools/plugins.json`: add `iru-functional-definition` and `iru-review-functional-definition` to `iru-core` skills and `iru-functional-reviewer` to its agents; run `python3 tools/generate-marketplace.py` (never edit
    `.claude-plugin/marketplace.json` by hand).
  - [x] Task 15.2. `tools/catalog-budgets.json`: add the two reference files to `shared_identical_files`; add `inline_cross_model` entries (`caller: iru-functional-definition`, `callee: iru-explore`, standard reason).
  - [x] Task 15.3. `CLAUDE.md`: model tiers list `opus` for `iru-functional-reviewer` too; agents list; ticket-intake convention mentions the functional definition; update `tools/README.md` if it enumerates agents/skills.
  - [x] Task 15.4. Run `python3 tools/catalog-audit.py --check`, `python3 tools/generate-marketplace.py --check`, `claude plugin validate .` and `claude plugin validate .claude/skills`; fix reported issues.
- [x] Task 16. Hand-edit the guides under `docs/modules/ROOT/pages/guides/`: `creating-tickets.adoc` (new "Functional definition" section: template, verification-method table, `AC-DOC`, `[mermaid]` sequence diagram of definition → review → file),
  `catalog-architecture.adoc` (ticket-intake pipeline, four agents), `common-workflows.adoc` ("define, file, implement" workflow), `performance-and-token-budget.adoc` (model tier table, 3-round cap), `plugins.adoc` (`iru-core` contents);
  keep every Mermaid label valid per `reference/mermaid.md`.

### Group 7 — Generated docs and verification (Parallelizable: no — Task 17 needs all skills final; Task 18 needs everything)

- [x] Task 17. Run `/iru-generate-skill-docs` to regenerate `skills/iru-functional-definition.adoc`, `skills/iru-review-functional-definition.adoc`, `agents/iru-functional-reviewer.adoc`, `index.adoc` and `nav.adoc`; then build:
  `cd docs && npm ci && npx antora antora-playbook.yml && npx pagefind --site build/site && npm run test:nav && npm run test:nav:site` and `npm i --no-save mermaid@11 jsdom@31 puppeteer@25 && npm run validate:mermaid`.
  - Done: 3 pages added (2 skills, 1 agent), index.adoc table/groups/dependency diagram/agent list/counts (199 skills, 4 agents) and nav.adoc updated, create-github-issue/create-jira-ticket/draft-github-issue pages gained the new edges; Antora build clean, Pagefind indexed, test:nav 0 failures, test:nav:site OK (220 pages), validate:mermaid 249 diagrams passed.
- [x] Task 18. Final verification (delegate command runs to `iru-gate-runner` where output is large)
  - [x] Task 18.1. `python3 tools/catalog-audit.py --check`, `python3 tools/generate-marketplace.py --check`, `claude plugin validate .`, `claude plugin validate .claude/skills`, `python3 -m unittest discover -s tools/tests`; prove drift detection by changing one reference copy, seeing the audit fail, and reverting.
  - Done: catalog-audit 0 errors (36 pre-existing line-count warnings), marketplace up to date (18 plugins), `claude plugin validate .` and `.claude/skills` passed, 107 unit tests OK; drift proven (appending to the review-github-issue checklist copy gave `shared-file-drift ... 8 copies but 2 distinct contents`, reverted, audit back to 0 errors).
  - [x] Task 18.2. In a scratch repository (small web API + Markdown `docs/`, outside this repo), run `/iru-functional-definition` for AC4–AC7 (accept and decline `AC-DOC`, vague prompt, update of a scratch issue with and without confirmation); save the transcript for the PR.
  - Done live (2026-11-21, private scratch repo albertoirurueta/ai-catalog-fd-scratch, Flask API + Markdown docs): AC4 create mode drafted Context/Requirements/criteria with verification methods and negative cases, reviewed and filed as scratch #1; AC5 AC-DOC offered via AskUserQuestion with the detected docs/orders.md target, accepted (scratch #1) and declined with a specific reason (version-endpoint draft); AC6 the vague prompt "improve orders" produced only questions with code-derived candidates, no invented criteria or placeholders; AC7 update mode on #1 showed a before/after, kept unchanged sections and ids, "leave untouched" left the issue byte-identical, then `gh issue edit` applied only after confirmation.
  - [x] Task 18.3. Run the reviewer on drafts that trigger `incorrect` and `missing-functionality` (AC8), confirm the 3-round cap (AC9) and `/iru-review-functional-definition` read-only behaviour (AC10).
  - Done live with the real `iru-functional-reviewer` agent: AC8 it returned `incorrect` (Flask trailing newline, unsorted Werkzeug Allow header) and `missing-functionality` (formula injection, missing seed-reset fixture) findings with file:line evidence, and only the block; AC9 the #1 update loop stopped after round 3 and the remaining doubt was shown verbatim before filing; AC10 `/iru-review-functional-definition 1` printed the block unchanged and "leave untouched" left the issue byte-identical with 0 comments.
  - [x] Task 18.4. Run `/iru-create-github-issue` and `/iru-draft-github-issue functional` scenarios (AC11, AC13); run `/iru-create-jira-ticket` with no Jira MCP (AC12); record Jira-with-MCP as unverified in the skill's `## Verification` if no MCP is available.
  - Done live: AC11 `/iru-create-github-issue "add an order summary endpoint"` asked for the missing criteria and AC-DOC through the embedded definition, offered "Create" only after `Verdict: ready`, filed scratch #2 with the canonical sections; AC12 `/iru-create-jira-ticket` found no Jira MCP (ToolSearch) and stopped at Step 1, Jira-with-MCP recorded unverified; AC13 `/iru-draft-github-issue functional` used the canonical headings and AC-DOC, merged both reviewers (stopped at "do not create"), and `/iru-review-github-issue draft:` on a copy without AC-DOC returned a `gap` in the unchanged four-class block. Skill text fixed from these runs: draft-github-issue merge keeps the agent's classes and skips a duplicate agent round; create-github-issue states the template's section order.
  - [x] Task 18.5. Run `/iru-plan` on a scratch issue with `AC-DOC` and a `curl` criterion (AC14) and `iru-code`'s documentation step in the Markdown-docs repository and in an Antora repository (AC15).
  - Done: AC14 `iru-plan` on scratch #1 produced the Verification method column, `curl` criteria mapped to tasks that run and record them (plus mirroring tests) and the AC-DOC row mapped to the final documentation task carrying `/iru-update-docs target: markdown pages: docs/orders.md content: api, sequence`; AC15 `iru-update-docs target: markdown pages: docs/orders.md content: api, sequence, equations, figures` on the scratch summary endpoint wrote a ```mermaid fence, a `$$…$$` equation and a relative SVG, and the Markdown-extended validate-mermaid passed static, parse and render (1 diagram). The Antora half is exercised by this repository's own `iru-code` Step 8 docs run.
  - [x] Task 18.6. Run both new skills in a directory with a non-GitHub remote and no Jira MCP (AC16) and confirm they stop and write nothing.
  - Done: scratch repo with a bitbucket.org remote and no Jira MCP (ToolSearch 'jira issue' found none): both skills' Step 1 stop with a clear message and write nothing; the repo tree was unchanged.
