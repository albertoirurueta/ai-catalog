# Issue body templates

Templates for `iru-draft-github-issue` (documentation kind here; functional kind: canonical file, see below). A draft file is Markdown whose first line is `# <title>` and whose remainder
is the issue body, so `iru-review-github-issue` and `iru-split-github-issue` can read it with `draft:<path>`.
Omit an optional section entirely rather than leaving it empty or filled with a placeholder (`TBD`, `TODO`, `?`,
"etc." are all review findings). Write the body in the user's language; the section names below may be translated.

## Functional template

The functional template is the canonical one in `reference/functional-definition-template.md` (copied byte-identical
into this skill; do not edit it here). Headings: Context, Requirements (`R1…`), Acceptance criteria (`AC1 (R1)…` each
with `Verification: <method> — <concrete values>`, plus the mandatory `AC-DOC` item), Technical details (optional), Out of
scope, Dependencies and related tickets, Task details, References. The checklist is
`reference/functional-definition-checklist.md`. Existing drafts using `Functional requirements`, `FR1…` and
`Dependencies and related issues` stay valid (`FRn` equals `Rn`); do not rename them only for that.

Shape of a functional draft:

```markdown
# <imperative one-line title>

## Context
## Requirements
- R1. <Observable, testable behaviour.>
## Acceptance criteria
- AC1 (R1). <Condition> — Verification: <automated-test|form-input|ui-browser|ui-simulator|api|cli|data|performance|manual> — <concrete values>
- AC-DOC. Functional documentation: <target; pages; content; formats> | not required — <specific reason>
## Technical details          <!-- optional -->
## Out of scope
## Dependencies and related tickets
## Task details
## References                 <!-- optional -->
```

Rules: every requirement is covered by at least one criterion and every criterion names its requirement; requirements
describe behaviour, implementation choices go in Technical details. See the template file for the verification-method
vocabulary, the `AC-DOC` forms and a worked example.

## Documentation template

```markdown
# <imperative one-line title, e.g. "Document the export module">

## Context and audience
<Why this documentation is needed, who reads it (role, prior knowledge) and what they should be able to do after
reading it.>

## Documentation type
Technical | Non-technical (learning guide)

## Page structure
<Technical: one entry per page that applies, from this list - Architecture, Data model, Use cases, Configuration
properties, Metrics, Algorithms - each with a one-line description of its content.>
<Non-technical: a learning guide - ordered pages from basics to advanced, and under each page the sections, one
per concept to be learned, with the learning outcome of each.>

## Diagrams
<For every flow, architecture, data model or state machine in the page structure: the page, the diagram kind
(Mermaid `flowchart`, `sequenceDiagram`, `erDiagram`, `stateDiagram-v2`, `classDiagram`; or an SVG file when Mermaid
cannot express it) and what it shows. If a page needs none, say why in one phrase.>

## Bibliography and official documentation
- <Title - URL (book, library docs, specification, class or API reference for every technology documented)>

## Acceptance criteria
- AC1. <Verifiable: every listed page exists, the docs build has no warnings, every link resolves, every diagram
  renders.>

## Out of scope
- <What is not documented here.>

## Dependencies and related issues
- Related: #<n> <title> (<why>)
- Blocked by: none

## Task details
- Due date: <absolute date>            <!-- omit the line when none -->
- Importance: trivial | minor | important | blocking | not specified
- Estimated difficulty: <level> - <one-line rationale>

## References
- <Optional: URLs and attached files; omit the section when there are none.>
```

Rules: the page list must match the declared type (technical page names in a learning guide, or the reverse, are a
review finding); at least one bibliography entry per documented technology or concept; each criterion verifiable.

### Worked example (documentation, technical)

```markdown
# Document the export module

## Context and audience
New backend developers cannot tell how exports are scheduled or configured. They must be able to add a new export
format after reading the pages.

## Documentation type
Technical

## Page structure
- Architecture: components (scheduler, queue, writers) and how a request flows through them.
- Data model: export job and export format entities, fields and relations.
- Use cases: export on demand, scheduled export, failed export retry.
- Configuration properties: table of `export.*` keys, type, default, effect.
- Metrics: counters and timers published, name, unit, meaning.
- Algorithms: row batching and back-pressure.

## Diagrams
- Architecture: Mermaid `sequenceDiagram` of request, queue and writer.
- Data model: Mermaid `erDiagram` of ExportJob and ExportFormat.

## Bibliography and official documentation
- Spring Boot reference - https://docs.spring.io/spring-boot/reference/
- RFC 4180 (CSV) - https://www.rfc-editor.org/rfc/rfc4180

## Acceptance criteria
- AC1. The six pages exist and are listed in `nav.adoc`.
- AC2. The Antora build finishes without warnings and both diagrams render.
- AC3. Every configuration key under `export.` in the code appears in the properties table.

## Out of scope
- User-facing guides for the reports page.

## Dependencies and related issues
- Blocked by: none

## Task details
- Importance: minor
- Estimated difficulty: medium - six pages, needs reading the scheduler and writers code
```

For a non-technical guide replace `Page structure` with, for example: "Page 1 What is an export (sections: Why
export, Formats); Page 2 Running your first export (sections: Choosing filters, Downloading, Reading the result)".
