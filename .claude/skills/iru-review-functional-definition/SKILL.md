---
name: iru-review-functional-definition
description: "Invoke as `/iru-review-functional-definition <ticket-id> | draft:<path>`. Read-only review of a functional definition (a GitHub issue, Jira ticket or local draft) against the functional-definition checklist and the real repository, by the iru-functional-reviewer agent. Prints the Verdict, Findings and Suggestions block unchanged; for existing tickets offers to leave it, post the findings as a comment or hand over to /iru-functional-definition."
model: sonnet
---

# Review functional definition

Review one functional definition and report the reviewer's verdict. Nothing is edited, posted or filed unless the user
explicitly chooses it at the end. This skill reviews; rewriting a definition is `/iru-functional-definition`.

Agent dispatch: call the agent as `subagent_type: "iru-functional-reviewer"` when installed under `.claude/agents/`, or as
`"iru-core:iru-functional-reviewer"` when installed as a plugin — use whichever name appears in your available agent types.
Every `subagent_type` below is written in the first form.

## Step 1 — Resolve the tracker and the input

- `draft:<path>`: a local Markdown file; no tracker is needed (tracker "none"). Read it; if unreadable, say so and stop.
- A ticket id (auto-detected like `iru-explore`: Jira key such as `PROJ-123` means Jira, a bare number optionally with `#`
  means GitHub, otherwise ask via `AskUserQuestion`): the id decides the tracker first, whatever the remote. A Jira key
  means **Jira** even in a GitHub-hosted repository: look for a Jira MCP integration (`ToolSearch` "jira issue"). A GitHub
  number needs a GitHub host: reuse `iru-explore`'s `Repository host:` finding if it ran in this conversation, else read
  the remote (`git remote get-url origin`); `github.com` or a GitHub Enterprise Server domain means **GitHub**. If neither exists, tell the user plainly that only GitHub and Jira tickets can be reviewed here and stop,
  writing nothing.
- No argument: ask once which ticket or draft to review; stop if none is given.

## Step 2 — Fetch the definition and write a draft file

For a ticket, fetch it with its comments: `gh issue view <n> --json number,title,body,labels,comments,state,url` (or the
Jira MCP fetch). If it cannot be fetched, say so and stop. Write `# <title>` followed by the body, appending relevant
later comments under a heading `## Comments (clarifications)`, to `functional-definition-draft.md` in a new temporary
directory (for example under `mktemp -d`). For `draft:<path>` use the given file directly; do not copy or modify it.

## Step 3 — Review

Dispatch `Agent({description: "Review functional definition", subagent_type: "iru-functional-reviewer", prompt: <...>})`
with the draft's absolute path, the absolute path of this skill's own `reference/functional-definition-checklist.md` (its
base directory plus `/reference/`), the tracker (`github`, `jira` or none), and an `iru-explore` summary only if one already
exists in this conversation. Do not run `iru-explore` just for this.

## Step 4 — Print the result

Print the agent's `Verdict` / `Findings` / `Suggestions` block unchanged: no rewording, reordering or filtering. If the agent
returned anything else (an error, an unreadable draft), print it as is and say the review did not complete.

## Step 5 — Next step (existing tickets only)

For a `draft:<path>` input, stop after Step 4. For an existing ticket, ask via `AskUserQuestion`:

- **Leave the ticket untouched** (default).
- **Post the findings as a comment** on the ticket (`gh issue comment <n> --body-file <file>` or the Jira MCP comment tool,
  with the block unchanged). Show the exact text first; post only after this choice.
- **Hand over to `/iru-functional-definition <id>`** to resolve the findings: run `Skill({skill: "iru-functional-definition",
  args: "<id>"})`; it does its own confirmation before changing anything.

The skill stays read-only unless the user picks a posting or hand-over option.

## Verification

Exercised while authoring this skill: the tracker detection rules and ticket-id patterns were checked against
`iru-explore`, `iru-create-github-issue` and `iru-create-jira-ticket`, and the reviewer's input and output contract against
`.claude/agents/iru-functional-reviewer.md`. Exercised live on 2026-11-21 on an open issue of a private scratch
repository: fetch with comments, draft file, agent dispatch, block printed unchanged, and "Leave the ticket untouched" left
the issue byte-identical with no comment. **Unverified**: the Jira MCP fetch and comment calls, and the "post as comment"
path (`gh issue comment <n> --body-file`), which was not chosen.
