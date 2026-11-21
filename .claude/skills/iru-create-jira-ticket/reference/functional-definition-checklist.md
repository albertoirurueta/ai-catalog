# Functional definition checklist

Single source of truth for `iru-review-functional-definition`, `iru-functional-definition` and the
`iru-functional-reviewer` agent. Every item has an id, the check, how to verify it, and one failing and one passing
example. Each violated item becomes one finding of one of the classes listed at the end (see "Finding classes").
The draft format is defined in `functional-definition-template.md`; `FRn` ids are equivalent to `Rn`.

Applicability: **Common** items apply to every functional definition; **Codebase** items need the repository (read it
with Read/Grep/Glob, never guess); **Hunts** are open-ended searches done by the reviewer after the items.

## Common

### F1 — Context is grounded
- **Check**: Context says why the work matters and refers to real things that exist (files, modules, behaviour today).
- **Verify**: read Context; grep the repository for each named file, module or behaviour; confirm it exists.
- **Fails**: "Context: add CSV export."
- **Passes**: "Context: finance re-keys the report by hand because `src/reports/ReportPage.tsx` cannot export; about two hours a month."

### F2 — Requirements are testable
- **Check**: each requirement is observable and bounded; no vague adjectives ("fast", "robust", "user-friendly") without a measure.
- **Verify**: scan every requirement for unbounded adjectives and for implementation verbs outside Technical details.
- **Fails**: "R1. The export should be fast."
- **Passes**: "R1. Exporting 10 000 rows completes in under 5 seconds on the reference environment."

### F3 — Requirement and criterion traceability
- **Check**: every `Rn` has at least one `ACm (Rn)` and every `ACm` names an existing `Rn`.
- **Verify**: build the matrix; report orphans on either side and criteria whose cited id does not exist.
- **Fails**: R2 "Support `;` separators" with no criterion citing R2.
- **Passes**: "AC3 (R2). A file exported with separator `;` uses `;` between every pair of fields."

### F4 — Verification method with concrete values
- **Check**: every criterion declares a method from the vocabulary (`automated-test`, `form-input`, `ui-browser`,
  `ui-simulator`, `api`, `cli`, `data`, `performance`, `manual`) and gives concrete values (inputs, expected outputs, status codes, thresholds).
- **Verify**: each criterion has `Verification: <method>` and at least one literal value someone could type or compare; `manual` has a stated reason.
- **Fails**: "AC1 (R1). Export works. Verification: manual."
- **Passes**: "AC1 (R1). Verification: api — `curl -i -X POST /exports -d '{"format":"csv"}'` returns 202 and `{"status":"queued"}`."

### F5 — Negative cases covered
- **Check**: wherever input is accepted or a dependency can fail, at least one criterion covers the invalid, denied, empty or failing case.
- **Verify**: for each requirement that takes input or calls something, look for a rejecting or degraded-path criterion.
- **Fails**: only "a valid email is accepted".
- **Passes**: "AC4 (R2). `user@` and an empty value show 'Enter a valid email' and block submit."

### F6 — AC-DOC present and well-formed
- **Check**: exactly one `AC-DOC` item exists, either accepted (target, pages, content kinds, formats) or declined with a specific reason (`AC-DOC. Functional documentation: not required — <reason>`).
- **Verify**: grep for `AC-DOC`; an accepted block names target, pages, content kinds written as the template's slugs (`data-model`, `uml-class`, `sequence`, `workflow`, `architecture`, `api`, `configuration`, `equations`, `figures`; any other word is a `doubt`) and formats the target supports; a declined block has a non-generic reason.
- **Fails**: no `AC-DOC`, or "AC-DOC. not required".
- **Passes**: "AC-DOC. Functional documentation: Antora ROOT; pages `export.adoc` (new); content: sequence, configuration; formats: Mermaid."

### F7 — No placeholders
- **Check**: no `TBD`, `TODO`, `FIXME`, `???`, lone `?`, "etc.", "and so on", "to be defined", `XXX`, unfilled `<...>` template text.
- **Verify**: grep the draft for those tokens; each hit is a finding.
- **Fails**: "Supported formats: CSV, JSON, etc."
- **Passes**: "Supported formats: CSV and JSON. Any other format is out of scope."

### F8 — No contradictions
- **Check**: scope, numbers, names, defaults and behaviours agree across sections and with comments on the ticket.
- **Verify**: collect every number, identifier and default mentioned more than once and compare; read ticket comments for later corrections.
- **Fails**: R1 says "maximum 100 rows", AC1 expects 1 000 rows.
- **Passes**: both say "maximum 1 000 rows".

### F9 — Out of scope and dependencies (optional sections)
- **Check**: when present, Out of scope and Dependencies are specific and each referenced ticket resolves. When absent, this is not a finding; add a `Suggestions:` line only if the work clearly has adjacent features or prerequisites worth stating.
- **Verify**: for GitHub `gh issue view <n> --json number,title,state`; for Jira use the Jira MCP; confirm title and state match the description.
- **Fails**: "Depends on the auth rework." (no link)
- **Passes**: "Blocked by #41 (auth rework, open). Related: #38."

## Codebase

### F10 — Named artefacts exist or are marked new
- **Check**: every file, class, method, endpoint, config key, table or document named exists in the repository, or is explicitly marked `(new)`.
- **Verify**: Read or grep each name; a missing, unmarked one is `incorrect`, and so is an artefact that exists but behaves differently from the description.
- **Fails**: "Change `ExportService.write()`" when no `ExportService` exists.
- **Passes**: "Extend `src/export/CsvWriter.ts` (`writeRow`, currently ignores quoting); add `src/export/RowBatcher.ts` (new)."

### F11 — Verification method is feasible in this repository
- **Check**: the tool a criterion relies on exists here: Playwright config for `ui-browser`, a simulator project for `ui-simulator`, a running service and port for `api`, an installed CLI for `cli`, a database and migration tool for `data`, a test framework for `automated-test`.
- **Verify**: look for the config, dependency or script in the repository (`package.json`, `pom.xml`, `playwright.config.*`, `.github/workflows`); where absent, the draft must say the tool is introduced by this work.
- **Fails**: "ui-browser — Playwright scenario" in a repository with no Playwright and no mention of adding it.
- **Passes**: "ui-browser — Playwright scenario (configured in `e2e/playwright.config.ts`)."

## Hunts (reviewer, after the items)

### H1 — Missing functionality
Search the codebase and the draft for what the work implies but does not state: callers of changed code, error and empty
states, validation, permissions and roles, persistence and migrations, configuration, internationalisation,
accessibility, backwards compatibility, and existing tests that will have to change. Each omission is a
`missing-functionality` finding with the evidence and the question to ask.

### H2 — Incorrect statements
Search for statements that contradict the code, the documentation or another requirement, and for verification methods
that cannot work in this repository. Each is an `incorrect` finding with `file:line` evidence.

## Finding classes

- **gap**: required information is absent (F1 context, F2/F3 requirements or criteria, F4 method or values, F5 negative cases, F6 `AC-DOC`).
- **pending**: the author deferred something (F7 placeholders, unresolved questions in comments).
- **inconsistency**: two statements, or a statement and a URL or ticket, disagree (F8, F9 unresolvable ticket, unreachable reference).
- **doubt**: the text is present but ambiguous or questionable and a human must decide (vague wording, over-prescriptive details, unjustified `manual`).
- **missing-functionality**: the definition omits behaviour the change necessarily involves (H1).
- **incorrect**: the definition states something false against the code, docs or another requirement, or relies on a verification method infeasible here (F10 missing or mismatching artefact, F11, H2).

Every finding carries the exact question to put to the user, phrased so the answer can be pasted into the ticket.
