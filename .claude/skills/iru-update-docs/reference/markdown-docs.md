# Markdown documentation path and content kinds

Read this file when `target: markdown` is given, when no Antora site exists, or when `content:` lists any kind.

## 1. Argument contract

`/iru-update-docs [<git-ref-or-range>] [target: markdown|antora|mcp] [pages: <path>,<path>] [content: <kind>,<kind>]`

Arguments arrive as `key: value` lines (as `iru-code` Step 8 passes them) or inline. All are optional.

- `target`: where the documentation lives. `markdown` = GitHub-flavoured Markdown in the repository; `antora` = the
  Antora AsciiDoc module; `mcp` = a connected documentation MCP (Step 5 only; Antora and Markdown files are then
  untouched unless they also exist and the diff affects them). Omitted: detect it (Step 2).
- `pages`: comma-separated page paths to create or update (a `.md` or `.adoc` path under the docs folder, or a README
  heading such as `README.md#Architecture`). Omitted: choose the pages the diff affects, as before.
- `content`: comma-separated kinds to produce, among `data-model`, `uml-class`, `sequence`, `workflow`, `architecture`,
  `api`, `configuration`, `equations`, `figures`. Omitted: produce only what the diff warrants.

An unknown kind is reported and skipped, never guessed. Every requested kind is produced on every target; only the
syntax differs (section 3).

## 2. Markdown path

Use it when `target: markdown`, or when Step 2 finds no `antora.yml` and a Markdown docs folder or README exists.

- **Detect**: a `docs/`, `doc/` or `documentation/` folder holding `*.md` files (read its index or README for the page
  map), else the root `README.md` split by its headings. Follow the existing heading style, link style and tone.
- **No Markdown docs and no Antora**: with `pages:` given, create those files; otherwise ask whether to create
  `docs/` pages, to set up Antora (`iru-setup-antora`), or to stop.
- **Diagrams**: a fenced block whose info string is `mermaid`. GitHub draws it; no extension is needed.
- **Equations**: `$...$` inline and `$$...$$` as a display block (GitHub renders both through MathJax). Never `\( \)`.
- **Figures**: SVG files stored beside the pages (a sibling `images/` or `figures/` folder, or the folder the existing
  pages already use), linked with a relative path and alt text: `![Alt text](images/name.svg)`. Write plain, valid SVG
  (viewBox, no scripts, no external references, readable in light and dark themes). Never a remote URL for a figure.
- **Links**: relative links between pages; add every new page to the docs index or README table of contents.
- **Validate**: after editing, check every fence you touched (section 4).

## 3. Content kinds

Ground every item in the real source; never invent classes, fields, endpoints or properties.

| Kind | Produce |
|---|---|
| `data-model` | entities, fields with types, keys and relations; a Mermaid `erDiagram` plus a field table |
| `uml-class` | a Mermaid `classDiagram` of the real types, their members and relationships |
| `sequence` | a Mermaid `sequenceDiagram` of one real interaction, with real participant names |
| `workflow` | a Mermaid `flowchart` or `stateDiagram-v2` of the process, decisions and end states |
| `architecture` | a component or layer diagram (Mermaid `flowchart` with subgraphs, or an SVG figure) plus a short responsibility table |
| `api` | endpoints or public functions: method and path or signature, parameters, request and response shapes, errors, one example |
| `configuration` | a table of every property or option: name, type, default, meaning, allowed values, read from the code or config files |
| `equations` | the formulas stated precisely, with symbols defined |
| `figures` | SVG figures (section 2) referenced from the page text |

On Antora the diagrams are `[mermaid]` blocks and equations `stem:[...]` / `[stem]`, only where Step 2 found the
extension wired in, and figures go under the module's `images/` with `image::` macros; if an extension is missing,
say so and fall back to a table or an SVG figure.

## 4. Running the Mermaid validator

Order of preference, first one that exists:

1. The repository's own `scripts/mermaid/validate-mermaid.mjs` (or `docs/scripts/mermaid/`).
2. The `scripts/mermaid/` copy of an installed `iru-setup-antora`, `iru-update-antora` or `iru-build-docs` (look in
   `.claude/skills/<name>/scripts/mermaid/`, or the plugin's skill directory).

Run it from a scratch install of the dependencies, so a Markdown-only repository gets no `package.json`:

```bash
d=$(mktemp -d) && (cd "$d" && npm init -y >/dev/null && npm i mermaid@11 jsdom@31 puppeteer@25)
NODE_PATH="$d/node_modules" node <path-to>/validate-mermaid.mjs <docs-folder-or-README-dir> --render
```

The validator scans `.md` fences and `.adoc` blocks alike. Fix every failure in a file you touched; list failures in
files you did not touch without fixing them. When puppeteer cannot run, drop `--render` (static and parse checks only)
and say so. When no validator copy exists anywhere, skip the check, tell the user, and recommend `/iru-update-antora`
or `/iru-setup-antora`, which copy `scripts/mermaid/` into the repository. Delete the scratch directory afterwards.
