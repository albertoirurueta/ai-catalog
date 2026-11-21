# Split templates

Body templates used by `iru-split-github-issue`. Placeholders are in `<angle brackets>`. Write the issue text in the
language of the original issue.

## Root issue body

````markdown
## Summary
<one or two sentences: the overall goal of the split work>

## Context
<why the work matters; carried over from the original issue>

## Milestone
[<milestone title>](<milestone url>)

## Work breakdown
Issues in the same group are independent and can proceed in parallel. A group starts when every issue of the
previous groups is done.

| Group | Issues | Parallelizable |
|-------|--------|----------------|
| 1 | #<n>, #<m> | yes |
| 2 | #<k> | no |

```mermaid
flowchart LR
    subgraph G1[Group 1]
        A["#<n> <short title>"]
        B["#<m> <short title>"]
    end
    subgraph G2[Group 2]
        C["#<k> <short title>"]
    end
    A --> C
    B --> C
```

## Original description
<only when splitting an existing issue: the original body, verbatim>
````

Notes:

- While sub-issues do not exist yet, use placeholders (`#TBD-1`) in the table and the diagram; replace them with real
  numbers once all sub-issues are created.
- If the sub-issues endpoint is unavailable, add under the table a task list `- [ ] #<n> <title>` per sub-issue.
- A one-group split has a single row; the diagram then has no arrows.

## Sub-issue body

````markdown
Parent: #<root>

## Context
<the slice of the parent this issue covers, and why; link to the parent for the overall goal>

## Requirements
- <requirement subset for this slice, testable>

## Acceptance criteria
- <verifiable criterion, traceable to a requirement above>

## Dependencies
Blocked by: #<n>, #<m>
<or: Blocked by: none>

## Parallel group
Parallel group: <n>
````

Notes:

- The canonical functional sections are kept (`Context`, `Requirements`, `Acceptance criteria` with verification
  methods; `Out of scope` and `Dependencies and related tickets` whenever the original has them, narrowed to the slice); when the original issue used `FRn`/`Functional
  requirements` headings, keep them consistently within the sub-issue.
- `AC-DOC` goes on the sub-issue whose change it documents, as a verbatim or narrowed copy of the original item; when
  the documentation spans all slices it stays on the root issue instead. Each sub-issue either carries its own `AC-DOC`
  or states `AC-DOC. Functional documentation: not required — documented by #<n>` (never omitted).
- Include `Technical details` only if the original issue had content for this slice; `Out of scope` follows the rule above.
- Every sub-issue must be self-sufficient for `/iru-issue <n>`: Context, Requirements and Acceptance criteria are
  mandatory, even if short.
- `Blocked by` lists the issues of earlier groups this issue really needs, not every earlier issue.
