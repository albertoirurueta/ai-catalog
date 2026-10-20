# Implementation plan — Skills to write, review and split detailed GitHub issues

## Task summary

Source: GitHub issue #23
Base branch: main

Add three new skills to the catalog so a GitHub issue can be written the way a *specify*-style spec is written:
fully detailed, reviewed for gaps before it exists, and split into dependency-aware sub-issues when it is too large.

| Skill | Invocation | Job |
|-------|------------|-----|
| `iru-draft-github-issue` | `/iru-draft-github-issue [functional\|documentation] [<short description>]` | Interview the user, build a complete draft (functional or documentation shape), run the review skill on it in a loop until no gaps remain, show the draft, create the issue after confirmation, and offer to split it when it is large. |
| `iru-review-github-issue` | `/iru-review-github-issue <issue-number>` or `/iru-review-github-issue draft:<path>` | Review an issue (an existing one by number, or an in-progress draft file) against a quality checklist and return classified findings (gap / pending / inconsistency / doubt) with the question to ask for each. |
| `iru-split-github-issue` | `/iru-split-github-issue <issue-number>` or `/iru-split-github-issue draft:<path>` | Assess whether an issue is too large, split it into sub-issues grouped by workflow dependency (parallel/independent vs. sequential), create a root issue, the sub-issues (GitHub sub-issues API) and a milestone that tracks them. |

The ticket's rules, which these skills encode:

- Every functional issue has **Context**. Development tasks also have **functional requirements** and **acceptance
  criteria**, plus optional **technical details** (classes/lines to change) when the task is highly technical.
- Documentation issues state the **page structure** to follow. Technical docs: architecture, data model, use cases,
  configuration properties, metrics, algorithms. Non-technical docs: learning guide with pages/sections per concept.
  All documentation issues require **bibliography / official-documentation links**, and **Mermaid or SVG diagrams**
  when they aid understanding.
- Missing, doubtful or inconsistent points are put to the user as questions, never silently guessed.
- Flow: draft → automatic review (resolve what can be resolved from the codebase/context, ask the user for the rest)
  → user-visible draft → create. A very long task becomes a root issue plus sub-issues ordered by dependencies, noting
  which can run in parallel; an oversized issue also gets a **GitHub milestone** tracking all sub-issues.

Decisions made on the user's behalf (challenge them in review if wrong):

- **New skills, existing ones untouched.** The ticket asks for *new* skills. `iru-create-github-issue` (and
  `iru-knowledge-to-issue`, which delegates to it) keep working unchanged; the docs position the new skills as the
  detailed, spec-style path and the existing one as the quick path. No Jira counterpart (ticket is GitHub-only).
- **`iru-draft-github-issue` is self-contained.** Skills are copied individually into other repositories, so it does
  not read other skills' files at runtime. It reimplements the (small) context-gathering and attachment conventions of
  `iru-create-github-issue` (`gh issue create`, labels from `gh label list`, small text files inline, larger files as
  assets of the `issue-attachments` release) and invokes `iru-review-github-issue` / `iru-split-github-issue` by name
  via `Skill`.
- **Review is report-only by default.** For an existing issue, `iru-review-github-issue` prints findings and asks
  (`AskUserQuestion`) whether to leave them, post them as a comment, or edit the issue body — nothing is changed or
  posted without that confirmation. Inside the draft skill it runs against a local draft file and the draft skill
  applies the resolutions.
- **Size threshold for splitting is judged, not computed**, using concrete signals: more than ~7 acceptance criteria
  or functional requirements, more than one independently deliverable capability, more than one module/area touched,
  or an estimate of "hard" or above. The split skill proposes the split and asks before creating anything. A
  milestone is created for every split (a split always has ≥ 2 sub-issues to track).
- **Dependencies are recorded in three redundant places** so every consumer sees them: GitHub *sub-issues* link the
  children to the root; each sub-issue body has a `Dependencies` section (`Blocked by: #N, #M` / `Blocked by: none`)
  and a `Parallel group: <n>` line; the root body carries an ordered table of groups
  (`Group | Issues | Parallelizable`). Same group number = independent, can proceed in parallel.
- **Sub-issue creation order.** Sub-issues are created in dependency order so `Blocked by:` can reference real issue
  numbers; the root issue is created first (with a placeholder table), then updated with the final table.
- **Language of generated issues** follows the user's language in the interview; the skills themselves are English.
- **No language tag on any task.** All tasks are Markdown/AsciiDoc authoring, for which no `*-code-one-task` key
  applies; `iru-code-one-task-group` implements them directly.
- **Verification** exercises only read-only `gh` calls (labels, milestones list, `issues/<n>/sub_issues` GET, `gh issue
  view`) against this repository. The create/update paths (`gh issue create`, sub-issue POST, milestone POST) are
  documented from the official GitHub REST docs and reported as *unverified* unless the user provides a scratch
  repository — never exercised against `albertoirurueta/ai-catalog` itself.

## Current code state

- Catalog layout: one self-contained `.claude/skills/iru-<name>/SKILL.md` per skill (YAML frontmatter `name`,
  `description` stating the exact invocation form, optional `model`), optional `reference/` files. New skills must
  carry the `iru-` prefix in directory, frontmatter `name` and every cross-reference
  (`docs/modules/ROOT/pages/guides/creating-skills-and-agents.adoc`).
- Closest precedent: [`.claude/skills/iru-create-github-issue/SKILL.md`](.claude/skills/iru-create-github-issue/SKILL.md)
  (190 lines, `model: sonnet`): host check → `iru-explore` → purpose → context (URLs via `WebFetch`, files, related
  issues) → due date/importance → label from `gh label list` → draft (Summary, Context, Acceptance criteria, Task
  details, References) → confirm → `gh issue create --body-file`. It has no documentation-issue shape, no review loop,
  no split/milestone support. Its attachment procedure (inline small text, `issue-attachments` release for large/binary
  files) is the convention to mirror.
- `.claude/skills/iru-knowledge-to-issue/SKILL.md` delegates drafting to `iru-create-github-issue`; unaffected.
- `.claude/skills/iru-issue/SKILL.md` and `iru-plan` consume issues by number; sub-issues produced by the split skill
  must be self-sufficient enough for `/iru-issue <n>` (context + requirements + criteria in each).
- Repository labels: `bug`, `documentation`, `duplicate`, `enhancement`, `good first issue`, `help wanted`,
  `invalid`, `question`, `wontfix`. No milestones exist yet. `gh` 2.96.0 is installed.
- Docs (Antora, `docs/modules/ROOT/`):
  - generated by `iru-generate-skill-docs`, do not hand-edit: `pages/index.adoc`, `pages/skills/*.adoc`,
    `pages/agents/*.adoc`, `nav.adoc` entries for generated pages;
  - hand-maintained: `pages/guides/creating-tickets.adoc` (what each ticket skill asks and produces),
    `pages/guides/common-workflows.adoc` (the "Filing a ticket" section and its Mermaid flow).
- [`CLAUDE.md`](CLAUDE.md) has a "Ticket intake" bullet listing `iru-create-github-issue` / `iru-create-jira-ticket`; it
  must mention the new skills.
- `.archive/` plans (#6, #15, #28) are structure precedent only: Markdown-only tasks in parallel groups, then docs.

### Pinned contracts (so group 1 and group 2 can be authored independently)

**`iru-review-github-issue`**
- Args: `<issue-number>` (fetch with `gh issue view <n> --json number,title,body,labels,comments,state,url`) **or**
  `draft:<path>` (a local Markdown file whose first line is `# <title>` and whose remainder is the body); optional
  `kind: functional|documentation` (auto-detected from the `documentation` label / body when absent).
- Output (printed, and returned to a calling skill in this exact shape):
  ```
  Verdict: ready | needs-work
  Kind: functional | documentation
  Findings:
  - [gap|pending|inconsistency|doubt] <section> — <what is wrong> — Question: <exact question for the user>
  Suggestions: <optional improvements that are not blockers>
  ```
- Checklist (single source, in `reference/issue-quality-checklist.md` inside the review skill): context present and
  explains *why*; functional requirements present, each testable (no vague "should be fast/nice"); acceptance criteria
  present, each verifiable and traceable to a requirement; no requirement without a criterion and no criterion without
  a requirement; technical details only when warranted and referencing files/classes that exist (verified with
  Read/grep); no `TBD`/`TODO`/`?`/"etc." placeholders; no contradictions between sections (scope, numbers, names);
  out-of-scope stated; dependencies/related issues referenced; documentation issues additionally: page structure given
  and matching technical vs. non-technical type, bibliography/official links present and reachable, diagrams (Mermaid or
  SVG) present where a flow/architecture/data model is described; size signals (hand-off hint to the split skill).
- With an existing issue number and user confirmation it may post the findings as a comment
  (`gh issue comment <n> --body-file`) or edit the body (`gh issue edit <n> --body-file`).

**`iru-split-github-issue`**
- Args: `<issue-number>` (existing issue; the root keeps this number) **or** `draft:<path>` (not yet created; the root is
  created from it); optional `force: yes` to split without the size assessment.
- Steps: fetch/read → assess size (signals above) → if not large, say so and stop (unless `force`) → propose
  sub-issues (title, scope, requirements and criteria subset, kind) → compute dependencies and group numbers → show the
  plan as a table + Mermaid `flowchart` and confirm with the user → create milestone (`<root title>`, description
  linking the root) → create/update root → create sub-issues in dependency order, attach as sub-issues, assign the
  milestone, add `Blocked by` / `Parallel group` lines → update root table → run `iru-review-github-issue` on each
  sub-issue draft *before* creating it (report-only; unresolved blockers go to the user).
- Each sub-issue body: `Parent: #<root>`, Context (its slice + link to root), Requirements, Acceptance criteria,
  Dependencies, Parallel group. Never creates anything before the explicit confirmation.

**`iru-draft-github-issue`**
- Args: optional `functional` | `documentation` and/or a short description; asks the kind when not given.
- Steps: GitHub host check → `iru-explore` (reuse if already in the conversation) → interview (context/why;
  functional: requirements, acceptance criteria, optional technical details; documentation: audience, technical vs.
  non-technical, page structure, sources/bibliography, diagrams) → optional context (URLs, files, related issues,
  due date, importance) → write draft to the scratchpad/temp file → loop `iru-review-github-issue draft:<path>` (resolve
  findings from the codebase/context first, ask the rest via `AskUserQuestion`/plain questions, max 5 rounds, then show
  what remains) → show final draft → confirm → `gh issue create` (labels `enhancement` / `bug` / `documentation` only
  if they exist) → if size signals fire, offer `iru-split-github-issue draft:<path>` *before* creating, so the root and
  sub-issues are created together → report number/URL and next step (`/iru-issue <n>`).

## Implementation steps

### Group 1 — Review and split skills (Parallelizable: yes — different directories, no shared files; each follows the pinned contracts above)

- [x] Task 1. Create the `iru-review-github-issue` skill
  - [x] Task 1.1. Create `.claude/skills/iru-review-github-issue/reference/issue-quality-checklist.md` with the checklist
    from "Pinned contracts", grouped as: Common (context, requirements, criteria, traceability, placeholders,
    contradictions, out-of-scope, dependencies), Development issues (technical details verified against the code),
    Documentation issues (page structure by technical/non-technical type, bibliography, diagrams), Size signals. Each
    item: id, check, how to verify, example of a failing and a passing sentence.
  - [x] Task 1.2. Create `.claude/skills/iru-review-github-issue/SKILL.md`: frontmatter (`name`, a `description`
    stating both invocation forms `/iru-review-github-issue <issue-number>` and `/iru-review-github-issue draft:<path>`,
    that it is read-only unless the user confirms a comment/edit, GitHub-only, and when to use it; `model: sonnet`);
    Steps: 1 resolve input and fetch (host check, `gh issue view`, or read the draft); 2 detect kind; 3 run the
    checklist, verifying referenced files/classes with Read/grep and fetching cited URLs with `WebFetch` to confirm they
    resolve; 4 emit the output block exactly as pinned; 5 for an existing issue offer (`AskUserQuestion`) leave /
    comment / edit body, executing only on confirmation; 6 report. Include the rule that a caller skill receives the
    block unchanged.
  - [x] Task 1.3. Self-check: the pinned output shape appears verbatim, the checklist file is referenced by relative
    path, no reference to files outside the skill directory.
- [x] Task 2. Create the `iru-split-github-issue` skill
  - [x] Task 2.1. Create `.claude/skills/iru-split-github-issue/reference/split-templates.md` holding the root-issue
    body template (summary, context, ordered group table, Mermaid dependency `flowchart`, milestone link) and the
    sub-issue body template (`Parent`, Context, Requirements, Acceptance criteria, Dependencies, `Parallel group`).
  - [x] Task 2.2. Create `.claude/skills/iru-split-github-issue/SKILL.md`: frontmatter (`name`, `description` with both
    invocation forms and `force: yes`, GitHub-only, creates a milestone, never creates anything before confirmation;
    `model: sonnet`); Steps per "Pinned contracts": input resolution, size assessment with the signals, split proposal,
    dependency/group computation (same group = independent, ordered groups = dependency), confirmation with table and
    Mermaid, then creation via `gh api`:
    - milestone: `gh api repos/{owner}/{repo}/milestones -f title=… -f description=…`
    - sub-issue link: `gh api repos/{owner}/{repo}/issues/<root>/sub_issues -F sub_issue_id=<id of child>` (the REST
      `sub_issue_id` is the child's numeric `id`, not its `number` — resolve it via `gh api repos/{owner}/{repo}/issues/<n> --jq .id`)
    - milestone on issue: `gh issue create --milestone <title>` / `gh issue edit <n> --milestone <title>`
    Fallbacks: if the sub-issues endpoint is unavailable (GHES, permissions) fall back to a task list
    `- [ ] #<n>` in the root body and say so; if `gh` is missing use GitHub MCP tools.
  - [x] Task 2.3. Add an "Existing issue" path: when splitting issue `#N`, keep `#N` as the root, rewrite its body from
    the template preserving the original text under "Original description", and require explicit confirmation before
    `gh issue edit`.
  - [x] Task 2.4. Self-check as in Task 1.3.

### Group 2 — Verification of the `gh` calls (Parallelizable: yes — single task; needs Tasks 1–2 final)

- [x] Task 3. Verify the read-only `gh` calls the two skills rely on
  - [x] Task 3.1. Run against `albertoirurueta/ai-catalog`: `gh label list`, `gh api repos/albertoirurueta/ai-catalog/milestones`,
    `gh api repos/albertoirurueta/ai-catalog/issues/28/sub_issues`, `gh issue view 23 --json …`; record observed
    behaviour/quirks (e.g. empty array vs. 404 for no sub-issues, numeric `id` vs `number`) in the skills' notes.
  - [x] Task 3.2. Dry-run the review checklist mentally on issue #23 itself and on issue #28; confirm the verdict and
    findings are sensible (e.g. #23 lacks acceptance criteria and a structured context → `needs-work`) and fix the
    checklist wording if not.
  - [x] Task 3.3. Report, in the final summary and a short "Verification" note in each skill, that `gh issue create`,
    sub-issue POST, milestone POST and `gh issue edit/comment` paths are unverified (no scratch repository).

### Group 3 — Draft skill (Parallelizable: yes — one task; depends on Group 2's verified quirks)

- [x] Task 4. Create the `iru-draft-github-issue` skill
  - [x] Task 4.1. Create `.claude/skills/iru-draft-github-issue/reference/issue-templates.md` with the two body
    templates: **functional** (Context, Functional requirements, Acceptance criteria, Technical details (optional),
    Out of scope, Dependencies/related issues, Task details — due date, importance, estimated difficulty, References) and
    **documentation** (Context/audience, Documentation type, Page structure — technical list: architecture, data model,
    use cases, configuration properties, metrics, algorithms; non-technical: learning-guide pages and sections per
    concept —, Diagrams (Mermaid/SVG guidance), Bibliography and official documentation, Acceptance criteria, Out of
    scope, Task details). Include a short worked example of each.
  - [x] Task 4.2. Create `.claude/skills/iru-draft-github-issue/SKILL.md` per "Pinned contracts": frontmatter
    (`name`, `description` with the invocation forms, the functional/documentation distinction, the review loop, the
    split offer, GitHub-only, "use for detailed spec-style issues; `iru-create-github-issue` remains the quick path";
    `model: sonnet`); Steps 1 host check; 2 `iru-explore`; 3 kind; 4 interview (open questions as plain text, choices via
    `AskUserQuestion`); 5 optional context incl. attachments convention; 6 write draft file; 7 review loop invoking
    `Skill({skill: "iru-review-github-issue", args: "draft:<path>"})`, resolving findings (codebase first, then ask),
    cap at 5 rounds; 8 size check → offer `iru-split-github-issue draft:<path>`; 9 show draft and confirm; 10 create via
    `gh issue create --body-file` with labels from `gh label list`; 11 report and point to `/iru-issue <n>`.
  - [x] Task 4.3. Self-check: the skill never creates an issue or milestone before the confirmation in step 9; the
    loop passes the review block through unchanged; no runtime reads of other skills' files.
  - [x] Task 4.4. Dry-run the interview mentally with the text of issue #23 as input for both kinds and confirm the
    produced draft passes `iru-review-github-issue`'s checklist.

### Group 4 — Hand-maintained docs and project files (Parallelizable: yes — four distinct files)

- [x] Task 5. Update `docs/modules/ROOT/pages/guides/creating-tickets.adoc`: add a section "Detailed, spec-style issues"
  covering the three new skills — what each asks/produces, functional vs. documentation shapes, the review loop, the
  split + milestone behaviour and dependency notation (`Blocked by`, `Parallel group`), with a Mermaid flow
  (`draft → review → (split) → create`) and links (`xref:skills/iru-draft-github-issue.adoc[]` etc.); keep the
  existing GitHub/Jira content intact and clarify when to use the quick vs. detailed path.
- [x] Task 6. Update `docs/modules/ROOT/pages/guides/common-workflows.adoc` "Filing a ticket" section: mention the
  detailed path and add the new entry point to the Mermaid flow.
- [x] Task 7. Update `CLAUDE.md` "Ticket intake" bullet: add the three skills, their pipeline
  (`iru-draft-github-issue` → `iru-review-github-issue` loop → optional `iru-split-github-issue`), the sub-issue +
  milestone + dependency convention, and that `iru-create-github-issue` stays the quick path.
- [x] Task 8. Update `CHANGELOG.md` (add an entry under the unreleased section, matching the file's existing format;
  create the section only if the file's convention requires it) and check `README.md` for a skill list or count that
  must mention the new skills.

### Group 5 — Regenerate and verify the docs (Parallelizable: yes — single task, depends on Groups 1–4)

- [x] Task 9. Run `/iru-generate-skill-docs` so `index.adoc`, `skills/iru-draft-github-issue.adoc`,
  `skills/iru-review-github-issue.adoc`, `skills/iru-split-github-issue.adoc`, the dependency graph and `nav.adoc` pick
  up the new skills, then build the site and confirm no Antora warnings about the new pages:
  `cd docs && npx antora antora-playbook.yml`
  - [x] Task 9.1. Confirm the three new skill pages exist, are in `nav.adoc`, and that `iru-create-github-issue`'s page
    still builds unchanged.
  - [x] Task 9.2. Run `/iru-check-security` over the changed files (scoped) and `/iru-check-license` is not applicable
    (Markdown/AsciiDoc only; state that in the report).
