---
name: iru-draft-github-issue
description: "Invoke as `/iru-draft-github-issue [functional|documentation] [<short description>]`. Interviews the user and writes a complete spec-style GitHub issue, auto-reviewed with `iru-review-github-issue`, optionally split via `iru-split-github-issue`, created after confirmation. GitHub-only. Use for detailed specs; `iru-create-github-issue` is the quick path."
model: sonnet
---

# Draft GitHub Issue

Write a fully specified GitHub issue the way a *specify*-style spec is written: grounded in the codebase, complete,
reviewed for gaps before it exists, and split into dependency-ordered sub-issues when it is too large. Nothing is
created on GitHub until the user confirms in Step 9 (the split skill, if accepted in Step 8, asks its own
confirmation before creating anything). Body templates are in `reference/issue-templates.md` (relative to this
skill's directory); read it before Step 4.

Never guess. A missing, doubtful or inconsistent point is put to the user as a question.

Use this skill for detailed, spec-style issues; `iru-create-github-issue` remains the quick path for a simple issue. It is
not for issues that already exist — use `iru-review-github-issue` or `iru-split-github-issue` for those.

## Step 1 — Confirm this repository is hosted on GitHub

- If `iru-explore` already ran in this conversation, reuse its `Repository host: ...` finding.
- Otherwise run `git remote get-url origin` (fall back to `git remote -v`) and check it matches `github.com` or a
  GitHub Enterprise Server domain.
- If the host is something else or there is no remote, say this skill only drafts GitHub issues and stop.

## Step 2 — Explore the codebase

Run `Skill({skill: "iru-explore"})` with no argument (general orientation, no ticket yet). Skip it when general
exploration already happened in this conversation and looks current. Use the findings to cite real files, modules
and conventions in the draft.

## Step 3 — Decide the kind

Parse the arguments: an optional first word `functional` or `documentation`, the rest being a short description.

- Kind given: use it.
- Kind not given: infer only when unambiguous (writing pages, guides, diagrams or a bibliography means
  `documentation`; changing behaviour means `functional`) and otherwise ask via `AskUserQuestion`: **Functional**
  (feature, enhancement or bug fix) / **Documentation** (pages, guides, diagrams).

A short description is a starting point: ask only for what it leaves unclear.

## Step 4 — Interview

Open-ended questions (purpose, requirements, page contents) are asked as plain conversational text; fixed choices
(technical vs. non-technical, importance, label) use `AskUserQuestion`. Ask in small batches, wait for each answer,
and do not move on while a required item is unanswered.

**Functional**

Delegate the whole functional interview to the shared skill:

```
Skill({skill: "iru-functional-definition", args: "mode: embedded\ntracker: github\n<the short description and what the user said so far>"})
```

It asks for context, testable requirements, acceptance criteria with a verification method and negative cases, Out of
scope, dependencies, technical details when the task is highly technical, and the mandatory `AC-DOC` documentation
decision, and returns a draft path in the canonical format (`reference/functional-definition-template.md`) with any
unresolved findings. Do not repeat those questions here. Use its draft as the starting point for Step 6. If
`iru-functional-definition` is not installed, interview for the same items yourself using the functional template.

**Documentation**

1. Context and audience: why, who reads it, what they should be able to do afterwards.
2. Type via `AskUserQuestion`: **Technical** / **Non-technical (learning guide)**.
3. Page structure. Technical: which of architecture, data model, use cases, configuration properties, metrics,
   algorithms apply, with each page's content. Non-technical: ordered pages from basics to advanced and the sections
   (one per concept) under each, with learning outcomes.
4. Diagrams: for each flow, architecture, data model or state machine, the diagram kind (Mermaid, or SVG when Mermaid
   cannot express it) and what it shows.
5. Bibliography and official documentation: books, specifications, library and class references for every documented
   technology. Fetch each URL with `WebFetch` to confirm it resolves and matches the subject.
6. Acceptance criteria (pages exist, build has no warnings, links resolve, diagrams render), out of scope.

If the user has no answer to a required point, record it as a question to resolve in Step 7, not as a placeholder.

## Step 5 — Optional context, due date, importance, label

Ask (plain text, all optional): linked URLs, local files or documents to attach, related issues.

- **URLs**: fetch with `WebFetch` and fold material points into the draft.
- **Related issues**: confirm with `gh issue view <n> --json number,title,url,state`.
- **Files**: `Read` each for context, then attach it. GitHub's API has no direct issue-attachment endpoint, so:
  small text files (under about 200 lines) are embedded in References inside a `<details><summary>name</summary>`
  block with a fenced code block of the full content; images, PDFs, large or binary files are uploaded as assets of
  a release named `issue-attachments` (`gh release view issue-attachments --json tagName` to check; if missing, ask
  via `AskUserQuestion` before creating it with `gh release create issue-attachments --title "Issue attachments"
  --notes "Storage for files attached to issues."`; upload with `gh release upload issue-attachments <path>`;
  link images as `![name](url)` and others as `[name](url)`). If the user declines or `gh` is unavailable (try
  GitHub MCP tools via `ToolSearch` "github release"), describe the file in the body and say it was not attached.
  This upload is the only GitHub write allowed before Step 9, and only after the explicit approval above.
- **Due date**: plain-text question; normalize to an absolute date; omit if none.
- **Importance**: `AskUserQuestion` with trivial / minor / important / blocking; "not specified" if declined.
- **Estimated difficulty**: your own judgement from the exploration (very easy, easy, medium, hard, very hard,
  extreme, impossible) with a one-line rationale.
- **Label**: run `gh label list --json name,description`; choose `bug`, `enhancement` or `documentation` only if it
  exists in that list (documentation kind maps to `documentation`; a defect to `bug`; otherwise `enhancement`). If
  none fits or it is ambiguous, ask via `AskUserQuestion` from the actual list. Never invent a label.

## Step 6 — Write the draft file

For the documentation kind fill the matching template from `reference/issue-templates.md`; for the functional kind start from the draft returned by `iru-functional-definition` (same canonical headings), fill in what Step 5 added (References, label-related notes) and keep its `AC-DOC`. Write it to a temp file in the scratchpad directory
if the system prompt lists one, otherwise to a fresh `mktemp -d` directory, as `issue-draft.md`: first line `# <title>`
(concise, imperative), then the body. Keep the path; every later step uses it.

## Step 7 — Review loop (maximum 5 rounds for documentation, 3 for functional)

Agent dispatch: call the agent as `subagent_type: "iru-functional-reviewer"` when installed under `.claude/agents/`, or as
`"iru-core:iru-functional-reviewer"` when installed as a plugin — use whichever name appears in your available agent types.

Repeat:

1. Invoke `Skill({skill: "iru-review-github-issue", args: "draft:<path>"})` (add `kind: <kind>` after the path on a
   new line only if the kind is known). Receive its block exactly as emitted:
   ```
   Verdict: ready | needs-work
   Kind: functional | documentation
   Findings:
   - [gap|pending|inconsistency|doubt] <section> — <what is wrong> — Question: <exact question for the user>
   Suggestions: <optional improvements that are not blockers>
   ```
   Do not reformat, summarise or reorder it; read the `Verdict` and each finding from it as-is.
   For the functional kind, in the same round also dispatch `Agent({description: "Review functional definition",
   subagent_type: "iru-functional-reviewer", prompt: <absolute draft path, absolute path of
   reference/functional-definition-checklist.md in this skill's directory, tracker github, iru-explore summary>})`,
   except in round 1 when the embedded `iru-functional-definition` of Step 4 already returned `Verdict: ready` for this
   same draft (its own loop ran the agent; repeat it only after the draft changes).
   Merge both result blocks: the verdict is `ready` only when both are `ready`; findings are de-duplicated (same
   section and same point count once, keeping the more specific `Question:`). Each finding keeps its own class: the
   review skill's four (`gap`, `pending`, `inconsistency`, `doubt`) plus the agent's `missing-functionality` and
   `incorrect`, which are resolved the same way (codebase first, else the user).
2. `Verdict: ready`: leave the loop.
3. Otherwise resolve each finding in this order:
   - first from the codebase and conversation (read the file, grep, re-read an earlier answer, fetch the URL);
     apply the fix to the draft only when the evidence is unambiguous;
   - otherwise ask the user the finding's own `Question:` (plain text for open answers, `AskUserQuestion` for
     choices) and apply their answer verbatim. Group several questions into one message.
   Never fill a gap with an invented answer.
4. Rewrite the draft file and go to 1.

After the last round (5, or 3 for functional) with `needs-work` still reported, stop looping and show the user the remaining findings; they decide
to fix, accept them as known gaps in the draft, or abort. Do not create the issue while findings the user has not
seen remain.

Keep the last block's `Suggestions:` for Step 8.

## Step 8 — Size check and split offer

Judge whether the issue is large using the same signals as the review (more than about 7 requirements or criteria,
more than one independently deliverable capability, more than one module or area, estimated difficulty hard or
above), and use the review's `Suggestions:` hint. If any fires, ask via `AskUserQuestion`:

- **Split it** (recommended): run `Skill({skill: "iru-split-github-issue", args: "draft:<path>\nlabel: <label>"})`
  (omit the `label:` line when Step 5 chose none), so the root and sub-issues carry the label chosen here. The split skill
  proposes the sub-issues, asks its own confirmation and then creates the root issue, sub-issues and milestone
  together from the draft. If it completes, skip Steps 9-10 (everything is created) and go to Step 11 with the root
  number it reports. If the user declines inside it, return here and offer Step 9 for the single issue.
- **Keep it as one issue**: continue to Step 9.

If no signal fires, continue without asking.

## Step 9 — Show the draft and confirm

Show the full title and body of the final draft, the label, and any remaining accepted findings. Filing an issue is
visible to everyone with repository access, so nothing is created before the user answers via `AskUserQuestion`:

- **Create the issue now**
- **Edit the draft first**: take their edits, update the file, and re-run the review loop (Step 7) before asking again
- **Do not create it**: stop; the draft file is the deliverable (give its path)

## Step 10 — Create the issue

Only after "Create the issue now":

```bash
gh issue create --title "<title>" --body-file <path-to-body-without-the-title-line> --label "<label>"
```

`--body-file` takes the body only, so write the draft minus its first line to a second file. Omit `--label` when
Step 5 chose none. Add `--milestone` only if the user asked for one. If `gh` is missing or unauthenticated, search
for GitHub MCP tools (`ToolSearch` "github issue") and create the issue with the same title, body and label.
Capture the number and URL from the output (or `gh issue view --json number,url`).

## Step 11 — Report

Give the issue number and URL (for a split, the root and the sub-issues with their dependency groups), note that the
issue is ready to be picked up with `/iru-issue <number>` (or `/iru-plan <number>` for a plan only), and mention any
`issue-attachments` release created in Step 5, since it is a repository-visible artifact.

## Verification

`gh label list --json name,description`, `gh issue view <n> --json number,title,url,state` and the read-only
`gh api` calls were exercised against `albertoirurueta/ai-catalog`. `gh issue create`, `gh release create/upload`
and the create paths of the split skill are written from the GitHub CLI and REST documentation and are unverified (no
scratch repository was available).
