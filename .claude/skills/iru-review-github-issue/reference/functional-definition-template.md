# Functional definition template

Single source of truth for the draft format used by `iru-functional-definition` and read by every skill that consumes a
functional definition (`iru-review-functional-definition`, `iru-create-github-issue`, `iru-create-jira-ticket`,
`iru-draft-github-issue`, `iru-review-github-issue`, `iru-plan`, `iru-update-docs`). The format is tracker-neutral: the
same Markdown body is filed as a GitHub issue or a Jira ticket.

A draft file is Markdown whose **first line is `# <title>`** (imperative, one line); the remainder is the ticket body.
Omit an optional section entirely rather than leaving it empty or filled with a placeholder (`TBD`, `TODO`, `?`, "etc."
are review findings). Write the body in the user's language; section names may be translated.

## Format

```markdown
# <imperative one-line title>

## Context
<Why this is needed: the problem or opportunity, who is affected, what exists today (name real files/modules found by
exploration), and why now.>

## Requirements
- R1. <Observable behaviour, testable, no vague wording.>
- R2. ...

## Acceptance criteria
- AC1 (R1). <Verifiable condition> — Verification: <method> — <concrete values>
- AC2 (R2). ...
- AC-DOC. <Functional documentation block, see below. Mandatory.>

## Technical details
<Optional. Only when the task is highly technical: files, classes, methods, config keys. Every artefact named must
exist, or be marked "(new)".>

## Out of scope
- <What this ticket deliberately does not cover.>

## Dependencies and related tickets
- Related: <id> <title> (<why>)
- Blocked by: none

## Task details
- Due date: <absolute date>            <!-- omit the line when none -->
- Importance: trivial | minor | important | blocking | not specified
- Estimated difficulty: <very easy | easy | medium | hard | very hard | extreme | impossible> - <one-line rationale>

## References
- <URL or document> (<what it is for>)
```

Required sections: Context, Requirements, Acceptance criteria (including `AC-DOC`). Optional: Technical details, Out of
scope, Dependencies and related tickets, Task details, References. Stating Out of scope and Dependencies (even "none") is
recommended; when the work clearly has adjacent features or prerequisites, the reviewer suggests them.

Rules:

- Every requirement `Rn` has at least one criterion `ACm (Rn)`; every criterion names the requirement it verifies.
- Requirements state behaviour, not implementation; implementation choices go in Technical details.
- Every criterion states its **verification method** (vocabulary below) with concrete values, so someone who did not
  write the ticket can run it and answer yes or no.
- Include negative cases (invalid input, missing permission, empty state, failure of a dependency) wherever the
  requirement accepts input or depends on something that can fail.
- **`FRn` equivalence**: the headings and ids of the existing `iru-draft-github-issue` template (`Functional
  requirements`, `FR1…`, `Dependencies and related issues`) are accepted as equivalent to `Requirements`, `R1…` and
  `Dependencies and related tickets`. Readers must treat `FRn` and `Rn` identically; do not rewrite an existing draft
  only to rename them. Within one draft use one prefix consistently.

## Verification-method vocabulary

Each acceptance criterion carries `Verification: <method>` using exactly one of these words, followed by concrete values.

| Method | Use when | Concrete example |
|---|---|---|
| `automated-test` | A unit/integration test can prove it | `Verification: automated-test — CsvWriterTest#quotesSeparator: input cell a,"b" yields "a,""b"""` |
| `form-input` | Behaviour of a form or input field | `Verification: form-input — email field: user@example.com is accepted; user@ and an empty value show "Enter a valid email" and block submit` |
| `ui-browser` | Web UI behaviour, layout, flow | `Verification: ui-browser — Playwright scenario: open /reports, apply filter year=2025, click "Export CSV"; the downloaded file has as many rows as the table; layout matches the design reference docs/design/export.png at 375 px and 1280 px` |
| `ui-simulator` | Mobile/desktop native UI | `Verification: ui-simulator — iOS Simulator iPhone 15: tap "Export", the share sheet lists "reports.csv"; repeat in dark mode and right-to-left` |
| `api` | HTTP/RPC contract | `Verification: api — curl -i -X POST http://localhost:8080/exports -H 'Content-Type: application/json' -d '{"format":"csv"}' returns 202 and body {"id":"<uuid>","status":"queued"}; format "xlsx" returns 400 and {"error":"unsupported_format"}` |
| `cli` | Command-line behaviour | `Verification: cli — mytool export --format csv --out /tmp/r.csv exits 0 and writes /tmp/r.csv; --format xlsx exits 2 with "unsupported format: xlsx" on stderr` |
| `data` | Persisted data, migrations, reports | `Verification: data — after migration V12, SELECT count(*) FROM export_job WHERE status IS NULL returns 0; rolling back restores the previous schema` |
| `performance` | Measurable bound | `Verification: performance — exporting 10 000 rows completes in under 5 s (p95 of 20 runs) on the reference environment` |
| `manual` | Only a person can judge; last resort | `Verification: manual — a reviewer follows docs/runbook.md section 3 on staging and confirms the printed invoice shows the new VAT line` |

Prefer the first method that can prove the criterion; `manual` needs a reason why no automated method applies.

## AC-DOC block (mandatory)

Every functional definition ends its acceptance criteria with exactly one `AC-DOC` item recording the documentation
decision. Two forms are accepted.

**Accepted** (documentation is part of the work):

```markdown
- AC-DOC. Functional documentation: Antora module ROOT (`docs/modules/ROOT/pages/`); pages: `export.adoc` (new),
  `configuration.adoc` (update); content: data-model (ER diagram of `export_job`), sequence (request, queue, writer),
  configuration (table of `export.*` keys), equations (row batching size, MathJax); formats: Mermaid for
  diagrams, SVG for figures, MathJax for equations. Verification: automated-test — the documentation build reports no
  warnings and every listed page is in `nav.adoc`.
```

An accepted block names: the **target** (Antora site, Markdown docs folder or README section, or a documentation
system reached through MCP such as Confluence/Notion), the **pages** to create or update, the **content kinds**, written with
exactly these slugs (the `content:` argument of `iru-update-docs`, which skips any other word): `data-model`, `uml-class`,
`sequence`, `workflow`, `architecture`, `api`, `configuration`, `equations`, `figures` (a short note in parentheses after a
slug is fine; screenshots and user procedures are `figures` and `workflow`), and the **formats** (Mermaid, SVG, MathJax) —
only formats the target's pipeline supports.

**Declined** (nothing to document):

```markdown
- AC-DOC. Functional documentation: not required — <reason>
```

The reason must be specific (for example "internal refactor with no change in behaviour, configuration or interfaces").

## Worked example

```markdown
# Export the filtered report as CSV

## Context
Finance re-keys the monthly report by hand because `src/reports/ReportPage.tsx` cannot export; this costs about two
hours a month and causes typos. The data is already filtered client-side by `useReportFilter`.

## Requirements
- R1. The report page offers an "Export CSV" action that downloads the currently filtered rows.
- R2. Fields containing the separator, quotes or line breaks are quoted per RFC 4180.
- R3. When no rows match the filter, the action is disabled and explains why.

## Acceptance criteria
- AC1 (R1). With year=2025 applied, "Export CSV" downloads a file whose data rows equal the visible rows — Verification:
  ui-browser — Playwright scenario on /reports: filter year=2025 (12 rows), click "Export CSV", the file has a header and 12 lines.
- AC2 (R2). A cell containing `a,"b"` is written as `"a,""b"""` — Verification: automated-test — `CsvWriterTest#quotesSpecialCharacters`.
- AC3 (R3). With a filter matching 0 rows the button is disabled and shows "Nothing to export" — Verification: form-input —
  filter year=1900: button disabled; filter year=2025: button enabled.
- AC-DOC. Functional documentation: not required — the page is self-explanatory and no interface or configuration changes.

## Out of scope
- XLSX and JSON export, scheduled exports.

## Dependencies and related tickets
- Blocked by: none

## Task details
- Importance: important
- Estimated difficulty: easy - one new writer and one button
```
