---
name: iru-functional-definition
description: "Invoke as `/iru-functional-definition [<ticket-id> | draft:<path>] [<initial functional description>]`. Writes or updates a functional definition (context, testable requirements, acceptance criteria with verification methods, mandatory AC-DOC documentation block) for a GitHub issue or Jira ticket: explores the code, asks only what is missing, reviews the draft with iru-functional-reviewer and files or updates after confirmation."
model: sonnet
---

# Functional definition

Produce a complete, testable functional definition for a ticket — grounded in the real codebase — as a Markdown draft in
the format of `reference/functional-definition-template.md`, reviewed against `reference/functional-definition-checklist.md`
by the read-only `iru-functional-reviewer` agent. Standalone it files a new ticket or updates an existing one after
confirmation; when called by another skill (`mode: embedded` or `tracker:` argument) it only returns the draft path.
It writes no code and never invents requirements: whatever the user or the code does not state is asked.

Agent dispatch: call the agent as `subagent_type: "iru-functional-reviewer"` when installed under `.claude/agents/`, or as
`"iru-core:iru-functional-reviewer"` when installed as a plugin — use whichever name appears in your available agent types.
Every `subagent_type` below is written in the first form.

## Step 1 — Resolve the tracker

- A `tracker: github|jira` argument (passed by a calling skill) is used as is; skip detection.
- Otherwise, if `iru-explore` already ran in this conversation, reuse its `Repository host:` finding. Else read the remote
  (`git remote get-url origin`, falling back to `git remote -v` or the remote the branch tracks): `github.com` or a GitHub
  Enterprise Server domain means **GitHub** (`gh` CLI, else GitHub MCP tools via `ToolSearch` "github issue").
- If the host is not GitHub, or there is no remote, look for a Jira MCP integration (`ToolSearch` "jira issue"): found means
  **Jira** (note whether it can fetch, create, update and comment).
- Neither: tell the user plainly that this skill only supports GitHub and Jira and that none is available here, then stop.
  Write nothing (no draft file, no ticket).

## Step 2 — Parse the arguments and choose the mode

Arguments are, in order, an optional ticket reference and an optional free-text description; `mode: embedded` and
`tracker:` may also appear.

- **`draft:<path>`**: read that Markdown file as the working draft (first line `# <title>`) and continue at Step 3.
- **A ticket id** (auto-detected like `iru-explore`: Jira key pattern such as `PROJ-123` means Jira, a bare number
  optionally prefixed with `#` means GitHub, otherwise ask via `AskUserQuestion`) selects **update mode**. Fetch it:
  `gh issue view <n> --json number,title,body,labels,comments,state,url` (or the Jira MCP fetch with comments). If it
  cannot be fetched, say so and stop. Use the body and the comments as the starting content; later comments may amend it.
- **No ticket**: **create mode**. Treat any remaining text as the initial functional description. If there is none, ask
  once, in plain text, what behaviour should exist and why.

## Step 3 — Explore

Run `Skill({skill: "iru-explore"})` with no argument in create mode and with the ticket id in update mode. Skip it when
exploration already happened in this conversation and is current. Keep its stack, architecture, docs-location and host
findings; they ground every following step.

## Step 4 — Draft

Read only `reference/functional-definition-template.md` (relative to this skill's base directory) and write the draft to
a new temporary directory (for example under `mktemp -d`) as `functional-definition-draft.md`; the first line is the title.

- **Create mode**: fill Context from the prompt and the real files found in Step 3, then Requirements (`R1…`), Acceptance
  criteria (`AC1 (R1)…` each with a verification method and concrete values, at least one negative case per behavioural
  requirement), Out of scope, Dependencies, Task details (due date, importance, estimated difficulty with rationale) and
  References. Add Technical details only when the task is highly technical.
- **Update mode**: start from the existing body, keep every unchanged section and id verbatim, change or add only what the
  new description, comments or gaps require, and append new ids instead of renumbering. Never silently drop content.
- Mark anything unknown as a question for Step 5; never write placeholders (`TBD`, `TODO`, `?`).

## Step 5 — Completeness gate

List what is missing or unclear against the checklist (F1–F9) and resolve it with the user in small batches of at most
three questions:

- Open answers (purpose, behaviour, values, errors, due date): plain conversational text, then wait.
- Choices (importance, difficulty, which candidate to keep): `AskUserQuestion`.
- Propose candidates derived from the code and the prompt ("the list endpoint has no pagination; should R2 require it?")
  and let the user accept, change or reject each. Never add a requirement or criterion the user has not confirmed.

Repeat until Context, Requirements, criteria with verification, negative cases, Out of scope and Dependencies are
complete. Update the draft after every batch.

## Step 6 — AC-DOC

Every definition carries exactly one `AC-DOC` item. Detect documentation targets: an Antora site (`antora.yml`, find the
module and existing pages), a Markdown docs folder or README sections, and a documentation MCP (`ToolSearch` "confluence",
"notion", "wiki"). Offer them via `AskUserQuestion` together with "No functional documentation", and suggest content
kinds that fit the change (sequence or flow diagram, configuration properties, UI screenshots, API reference, user
procedure) limited to formats the target supports (Mermaid and AsciiDoc tables for Antora; Markdown and fenced Mermaid
for a docs folder; whatever the MCP accepts). Record an accepted block as `AC-DOC. Functional documentation: <target>;
pages <names, new or existing>; content: <kinds>; formats: <formats>.` A declined block must state a specific reason
(`AC-DOC. Functional documentation: not required — <reason>`); ask for one if the user gives none.

## Step 7 — Review loop

Run at most **3 rounds**:

1. Dispatch `Agent({description: "Review functional definition", subagent_type: "iru-functional-reviewer", prompt: <...>})`
   with the draft's absolute path, the absolute path of this skill's own `reference/functional-definition-checklist.md`
   (its base directory plus `/reference/`), the tracker, and the `iru-explore` summary.
2. If `Verdict: ready`, stop the loop.
3. For each finding, first try to resolve it from the codebase or the fetched ticket (read the cited file, correct a wrong
   name, mark a not-yet-existing artefact `(new)`). If it cannot be resolved that way, ask the finding's `Question:` to the
   user (batched, as in Step 5) and fold the answer into the draft. Findings for `doubt` and `pending` classes are always
   asked, never guessed.
4. Update the draft and start the next round.

After round 3, or when the user declines to answer a finding, show the remaining findings verbatim to the user before
anything is filed; they decide whether to proceed. Reviewer suggestions (for example a size signal) are shown, not applied.

## Step 8 — Output

- **Embedded** (`mode: embedded` or a `tracker:` argument from a calling skill): return the final draft path, the tracker
  and a three-line summary (requirements count, criteria count, AC-DOC target or reason, unresolved findings). File
  nothing.
- **Standalone, create mode**: show the draft path and a summary, then file via the tracker after `AskUserQuestion`
  confirmation (create / edit the draft first / do not file), exactly as `iru-create-github-issue` Step 8 or
  `iru-create-jira-ticket` does, using the draft's first line as title and the rest as body. The draft is the deliverable
  if the user declines.
- **Standalone, update mode**: show a before/after of every changed section (unchanged sections are named, not repeated).
  Apply only after `AskUserQuestion` confirmation (apply / edit first / leave untouched):
  - GitHub: `gh issue edit <n> --body-file <draft-without-title-line>`; the title only if it changed and was confirmed.
  - Jira: the Jira MCP update tool, converting the Markdown body to the format the connection expects (wiki markup or ADF:
    headings, lists, code blocks, links); if no update tool exists, add the new definition as a comment and say so.
  - If the edit fails, post the new body as a comment, report the failure and keep the draft path.
- Report the issue number and URL (or the draft path) and that it is ready for `/iru-issue`, `/iru-plan` or `/iru-code`.

## Verification

Exercised while authoring this skill: the host and Jira-MCP checks, the argument and ticket-id detection rules and the
draft format were checked by reading the sibling skills and the template and checklist copies, and the reviewer agent's
output contract was read in `.claude/agents/iru-functional-reviewer.md`. `gh issue view` with `--json
number,title,body,labels,comments,state,url` is the same call `iru-explore` family skills rely on.

Exercised live on 2026-11-21 against a private scratch repository (a small Flask API with Markdown docs): create mode
(gate questions with code-derived candidates, `AC-DOC` accepted and declined with a reason, a vague prompt that led only
to questions), the review loop with the real `iru-functional-reviewer` agent (stops at 3 rounds, remaining findings shown
before filing), `gh issue create --body-file`, and update mode: before/after, unchanged sections and ids preserved,
"leave untouched" left the issue byte-identical, then `gh issue edit <n> --title … --body-file …` applied after
confirmation. A Bitbucket remote with no Jira MCP stops at Step 1 and writes nothing. **Unverified** (no Jira connection):
every Jira MCP call (fetch, update, comment) and the Markdown to Jira formatting conversion.
