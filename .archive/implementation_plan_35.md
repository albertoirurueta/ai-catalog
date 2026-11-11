# Implementation plan — Antora 3.2.2 pinned toolchain, `npm ci`, Pagefind, nav override and `iru-update-antora`

## Task summary

Source: GitHub issue #35
Base branch: main

Bring the catalog's Antora tooling to the setup the docs site now uses (albertoirurueta/docs#255 / #393 / #394):
Antora 3.2.2 and every extension pinned exactly, one `npm ci` from a committed lockfile in CI, Pagefind instead of the
Lunr extension, a generic nav-tree override that keeps pages small, and a new skill, `iru-update-antora`, that upgrades
an existing repository's Antora setup. This repository's own `docs/` site moves to the same setup.

Decisions made on the user's behalf (the ticket's own recommendations; challenge in review):

- **Search provider for new sites: Pagefind everywhere**, through shared `ui-overrides/`; Lunr is dropped.
- **Collector extension**: added only when the repository's `antora.yml` uses `ext.collector`.
- **Nav override for new sites: always written**, with defaults that make it a no-op on a small nav.
- **One source of truth for versions = `reference/toolchain.md`**, kept byte-identical in the four skills that read it
  (`iru-setup-antora`, `iru-build-docs`, `iru-update-docs`, `iru-update-antora`), following the catalog's existing shared-file
  convention (a skill must stay copyable on its own) and enforced by adding the file name to `shared_identical_files`
  in `tools/catalog-budgets.json`. Workflow templates need **no versions** (they run `npm ci` from the lockfile), so they
  embed the CI snippet and the Node version from `toolchain.md` instead of carrying a copy of it.
- **Shared override and script files** (`ui-overrides/**`, `scripts/**`) live in `iru-setup-antora` and are copied
  byte-identically into `iru-update-antora` (and the check scripts into `iru-build-docs`); their file names are added to
  `shared_identical_files` too.
- **Override sources**: the reference implementation is in `albertoirurueta/docs` (`ui-overrides/{css,helpers,partials}`,
  `scripts/nav-fix/nav-item-state.test.mjs`, `scripts/site-metrics/measure.mjs`), readable with `gh api`. The nav pieces are
  generalized as the ticket describes; the Pagefind pieces are copied as they are.
- **No language tags**: the work is Markdown, YAML and AsciiDoc authoring plus shipped Handlebars and Node assets for the
  generated repositories, so every task is implemented directly by `iru-code-one-task-group`, not by a `*-code-one-task`
  skill. Node scripts ship with their own tests, run with `node --test`.
- **Verify before asserting**: the `\( \)` math claim, the `docs-toolchain` failure and Pagefind output are checked in a
  scratch directory (Task 3) before any guidance is rewritten.

Open clarifications: none

## Acceptance criteria coverage

| # | Criterion | Covered by tasks |
|---|---|---|
| 1 | "One reference file holds the pinned Antora toolchain, and every skill and template takes its versions and CI snippet from it." | Task 1, Task 3, Task 6, Task 7, Task 8, Task 9, Task 10, Task 11, Task 12, Task 13, Task 14, Task 15 |
| 2 | "`/iru-setup-antora` on a fresh repository writes exact versions and a committed lockfile, wires Pagefind (or the chosen provider) and builds and indexes the site without warnings." | Task 3, Task 5, Task 20 |
| 3 | "No workflow template installs Antora package by package, uses `mkdir docs` or uses `docs-toolchain`. Each runs `npm ci` in `docs/` and builds the Pagefind index." | Task 9, Task 10, Task 11, Task 12, Task 13, Task 14, Task 20 |
| 4 | "`/iru-update-antora` exists and is registered and documented. Run on a repository pinned to 3.1.15 with Lunr, it upgrades it to the pinned set, updates its workflows and lockfile, and shows a build diff limited to the generator tag and sitemap dates." | Task 8, Task 15, Task 19, Task 20 |
| 5 | "This repository's `docs/` uses the pinned set and Pagefind, and `docs/node_modules/` is no longer tracked." | Task 16, Task 20 |
| 6 | "The math syntax guidance in `iru-setup-antora` and `iru-update-docs` matches what renders." | Task 3, Task 5, Task 7 |
| 7 | "The generic nav-tree override (no hard-coded group, text-only groups never pruned) ships with `iru-setup-antora`, with its unit tests and a built-HTML dead-end check. `iru-build-docs` and `iru-update-antora` measure nav size and recommend or upgrade the override, and the nav authoring rules (link or group with children, no `#fragment`) are in `iru-setup-antora` and `iru-update-docs`." | Task 2, Task 4, Task 5, Task 6, Task 7, Task 8, Task 16 |

## Current code state

- **This repo's site**: `docs/package.json` pins `antora` 3.1.15 in `devDependencies`, extensions in `^` ranges, still depends on
  `@antora/lunr-extension`; `docs/antora-playbook.yml` requires Lunr and has no `ui-overrides`; `docs/node_modules/` is tracked
  (6,310 files) although `.gitignore` lists it; `.github/workflows/docs.yml` already runs `npm ci` (Node 24) but has no Pagefind
  step. `docs/ui-bundle.zip` is the shared UI bundle (also at `.claude/skills/iru-setup-antora/ui-bundle.zip`).
- **`iru-setup-antora/SKILL.md`** (376 lines): Step 3 installs `npm i -D -E antora` plus three extensions without `-E`; Step 5's
  playbook template requires Lunr (line ~201); Steps 7 and 9b teach `\( \)` / `\[ \]`; Step 11 calls tracked `node_modules` a
  "legacy quirk"; Step 12 builds without indexing; Step 13 reports. Its only supporting files are `reference/ui-docs.md` and
  `ui-bundle.zip`.
- **`iru-build-docs/SKILL.md`** (haiku, 56 lines): `npm ci` then `npx antora`; no Pagefind step, no version warning, no size
  or nav checks.
- **`iru-update-docs/SKILL.md`**: Step 2 (line ~54) lists "`lunr` search"; line ~97 teaches `\( \)` MathJax.
- **Workflow templates**:
  - Old per-package install: `iru-setup-java-github-workflows/templates/common/.github/workflows/develop.yml` (`mkdir docs`),
    `iru-setup-android-github-workflows/templates/gitflow/.github/workflows/develop.yml` and its `SKILL.md` notes
    (`docs-toolchain`), `iru-setup-swift-github-workflows/templates/{app,library}/.github/workflows/build.yml`,
    `iru-setup-cli-github-workflows/reference/{dotnet,go,rust,swift}-workflows.md`,
    `iru-setup-{kmp,macos,windows}-github-workflows/reference/workflow-templates.md`.
  - Already `npm ci` in `docs/`: python, php, quarkus, typescript (`generic`) and java-springboot (`maven`, `kotlin-gradle`)
    `build.yml`. `iru-setup-typescript-github-workflows` also names the old pattern in `SKILL.md` and
    `reference/notes-build-generic.md`.
- **Catalog tooling**: `tools/plugins.json` lists skills of `iru-core` explicitly (`iru-build-docs`, `iru-update-docs`,
  `iru-setup-antora`, …); `.claude-plugin/marketplace.json` is generated from it; `tools/catalog-budgets.json`
  `shared_identical_files` (default `ui-contract.md`, `cli-contract.md`, `ui-docs.md`, `accessibility-detection.md`) drives the
  drift check in `tools/catalog-audit.py`. No documentation MCP is connected.
- **Precedent**: `.archive/implementation_plan_28.md` (a shared reference copied byte-identically into many skills) and
  `implementation_plan_11.md` (cross-cutting change to many skills) set the grouping granularity.

## Implementation steps

### Group 1 — Source of truth and generic overrides (Parallelizable: yes)

- [x] Task 1. Create the toolchain reference `.claude/skills/iru-setup-antora/reference/toolchain.md` — `reference/toolchain.md` (no code, no tests; catalog audit 0 errors).
  - [x] Task 1.1. Add the exact tested set: `antora` 3.2.2, `@antora/collector-extension` 1.0.3 (only when `ext.collector` is used),
    `@sntke/antora-mermaid-extension` 0.0.13, `@djencks/asciidoctor-mathjax` 0.0.9, `pagefind` 1.6.0; Node minimum 20 (`"engines": {"node": ">=20"}`),
    CI Node 24; the one-line `npm i -E …` install command; the `package.json` scripts (`build`, `search:index`, `test:nav`, `test:nav:site`).
  - [x] Task 1.2. Add the CI snippet (`npm ci`, `npx antora -v`, build, `npx pagefind --site build/site`, all with `working-directory: docs`),
    the rule on where Pagefind runs relative to merged API docs (after the merge only if API pages should be searchable), and the optional
    size guard (`du -sk build/site`, warn above 900,000 KiB, fail above 960,000 KiB).
  - [x] Task 1.3. Add the nav thresholds (more than ~300 nav entries, nav over ~30% of a typical page, or `du -sk` over 500,000 KiB) and the
    Antora 3.2 upgrade notes (Node 20+, exit code 2 at the failure level, `ext` keys no longer camelCased, no trailing slash on `site.url`, quoted
    YAML attribute values). Reserve a "Verified behaviors" section that Task 3 fills.
- [x] Task 2. Ship the generic UI overrides in `.claude/skills/iru-setup-antora/ui-overrides/` — `ui-overrides/{partials,helpers,css}` + README; verified in a scratch Antora 3.2.2 build (Antora camelCases `site.keys`, so the partial reads `navOpenGroups`/`navExpandDepth`); unit tests belong to Task 4.
  - [x] Task 2.1. Copy the Pagefind overrides from `albertoirurueta/docs` with `gh api`: `partials/article.hbs`, `partials/footer-scripts.hbs`,
    `partials/head-styles.hbs`, `partials/header-content.hbs`, `css/pagefind-site.css`. Keep `data-pagefind-body` limited to the latest version of the component.
  - [x] Task 2.2. Generalize `partials/nav-tree.hbs` and `helpers/nav-item-state.js` from the docs site, including the #394 rule (a text-only group heading always
    emits its children with a toggle, collapsed unless on the current path): no hard-coded group title (read `site.keys.nav_open_groups`, a comma-separated list, default none),
    keep the depth-0 untitled-wrapper rule, make the always-expanded depth `site.keys.nav_expand_depth` (default 1). Confirm the helper can read `@root.site.keys`, and
    record the outcome in the helper's header comment.
  - [x] Task 2.3. Write `ui-overrides/README.md`: what each file does, the `ui.supplemental_files` entries to register, and the playbook `site.keys` knobs.

### Group 2 — Verification spike and shipped checks (Parallelizable: yes)

- [x] Task 3. Verify the unverified claims in a scratch directory (not committed) and record the findings — findings in `reference/toolchain.md` Verified behaviors: bare `\( \)` does not render, `stem:[]`/`[stem]` do; Pagefind indexes article bodies only; `docs-toolchain` fails (npx ignores the sibling, `require:` fatal).
  - [x] Task 3.1. Build a throwaway Antora 3.2.2 site from the pinned set with the Task 2 overrides and `ui-bundle.zip`. Check that bare `\( \)` / `\[ \]` pages do not render, and that `:stem: latexmath` + `stem:[…]` / `[stem]` does (with the playbook as the new template generates it). Run Pagefind over `build/site` and confirm only article bodies are indexed.
  - [x] Task 3.2. Reproduce the `docs-toolchain` pattern (install in a sibling directory, `npx antora` in `docs/`) and record whether `npx` fetches a different `antora` and whether `require:` of the extensions fails.
  - [x] Task 3.3. Write the results into `toolchain.md`'s "Verified behaviors" section (and the math guidance wording the later tasks quote); if `\( \)` does render with the generated playbook, record that instead and keep the guidance.
- [x] Task 4. Ship the nav checks in `.claude/skills/iru-setup-antora/scripts/` — `scripts/nav-fix/{nav-item-state.test,check-nav-dead-ends,check-nav-dead-ends.test}.mjs`, `scripts/site-metrics/{measure,measure.test}.mjs`; 33 tests pass (`node --test`), 100% line / 93% branch coverage of the scripts; dead-end check passes on the scratch build.
  - [x] Task 4.1. `scripts/nav-fix/nav-item-state.test.mjs`: copy from the docs site and extend for the generalized helper — text-only groups with children on and off the current path, nested groups, the `nav_open_groups` and `nav_expand_depth` knobs, plus a Handlebars render of `nav-tree.hbs`. Runs with `node --test`.
  - [x] Task 4.2. `scripts/nav-fix/check-nav-dead-ends.mjs`: on built HTML (every page, or `--sample` with at least one page per nav section) fail on a `li.nav-item` whose `.nav-text` has no child `ul.nav-list`, and on a nav link whose target is missing from `build/site`.
  - [x] Task 4.3. `scripts/site-metrics/measure.mjs`: copy from the docs site; report HTML size, sample page sizes and nav size per page, and exit with the recommend/enable verdict from the `toolchain.md` thresholds.
  - [x] Task 4.4. Run the unit tests (`node --test`) by delegating to the `iru-gate-runner` agent, and confirm the dead-end check passes on the Task 3 scratch build.

### Group 3 — Skills that read the toolchain (Parallelizable: yes — each task edits a different skill directory)

- [x] Task 5. Update `.claude/skills/iru-setup-antora/SKILL.md` — `iru-setup-antora/SKILL.md` updated (Steps 2, 3, 5, 7, 9b, 11, 12, 13, supporting-files table); description under 400 chars; catalog audit 0 errors.
  - [x] Task 5.1. Step 3: install the pinned set in one `npm i -E` command (keep the `npm init -y` guard and `"private": true`), add `engines.node` and the `build`, `search:index`, `test:nav`, `test:nav:site` scripts, commit `docs/package-lock.json`, drop Lunr, and add the collector extension only when `ext.collector` is used. Point at `reference/toolchain.md` instead of restating versions.
  - [x] Task 5.2. Step 5 and the playbook template: remove the Lunr extension; add the Pagefind `ui.supplemental_files` entries and the nav override; document `site.keys.nav_open_groups` / `nav_expand_depth`; copy `ui-overrides/` and `scripts/` into `docs/`.
  - [x] Task 5.3. Steps 7 and 9b: replace the math guidance with the Task 3 result. Step 7 nav guidance: add the authoring rules (every entry is an `xref:` or a text-only group with children, never an empty group; no `#fragment` links; renamed groups listed in `nav_open_groups` are renamed there too; prefer a section `index.adoc` over a text-only heading when the group's pages should be reachable from elsewhere) and write them into the generated repository's docs `README`/`CLAUDE.md`.
  - [x] Task 5.4. Step 11: stop calling tracked `node_modules` a quirk; require the ignore entry and offer `git rm -r --cached`. Step 12: build, then `npx pagefind --site build/site`, run the dead-end check, and report that search needs the site served over HTTP (`python3 -m http.server 8090 --directory docs/build/site`). Step 13: list the pinned versions installed and whether the lockfile was written. Update mode: when the site is on an older Antora or uses Lunr, point to `/iru-update-antora`.
  - [x] Task 5.5. Keep the description within budget (≤1,024 chars, invocation form in the first 200) and add an index table of the new `reference/`, `ui-overrides/` and `scripts/` files.
- [x] Task 6. Update `.claude/skills/iru-build-docs/SKILL.md` — `iru-build-docs/SKILL.md` + `reference/toolchain.md`, `scripts/nav-fix/check-nav-dead-ends.mjs`, `scripts/site-metrics/measure.mjs` (byte-identical copies, runtime scripts only); audit 0 errors.
  - [x] Task 6.1. Copy `toolchain.md` and the `scripts/` check files (byte-identical) into the skill directory.
  - [x] Task 6.2. After the build run `npm run search:index` (or `npx pagefind --site build/site`) when `pagefind` is a dependency; delete `build/site` before the run when it measures sizes; run the dead-end check when the override is present; run `measure.mjs` and recommend the override when thresholds are crossed.
  - [x] Task 6.3. Warn and point to `/iru-update-antora` when the installed `antora` is older than the pinned version. Keep the skill read-only on page content and `haiku`-cheap.
- [x] Task 7. Update `.claude/skills/iru-update-docs/SKILL.md` — `iru-update-docs/SKILL.md` + `reference/toolchain.md` copy; audit 0 errors.
  - [x] Task 7.1. Copy `toolchain.md` byte-identically into `iru-update-docs/reference/`; Step 2 recognises Pagefind (a `pagefind` dependency or the `ui-overrides` search partials) as the search provider.
  - [x] Task 7.2. Replace the math guidance with the Task 3 result; add the nav authoring rules for edits to `nav.adoc` and run the dead-end check after `nav.adoc` changes when the override is present.
- [x] Task 8. Create `.claude/skills/iru-update-antora/SKILL.md` (`/iru-update-antora [<version>]`, `model: sonnet`) — new `iru-update-antora/` (SKILL.md, `reference/toolchain.md`, `ui-overrides/`, `scripts/` byte-identical copies); audit 0 errors; not yet in `tools/plugins.json` (Group 5).
  - [x] Task 8.1. Frontmatter with `iru-` name and a description of the exact invocation form in the first 200 characters, quoted values, within budget.
  - [x] Task 8.2. Steps 1–9 from the ticket: find toolchains (`package.json` depending on `antora`, playbook, workflows that run `npx antora`); report and confirm with current/target versions, the relevant Antora changelog entries (fetched at run time) and 3.2 breaking changes; baseline build in a scratch directory with logs; upgrade (`npm i -E`, remove stale packages, `engines.node`, lockfile, offer untracking `node_modules`); Lunr → Pagefind question (recommended yes); workflows (`npm ci`, `npx antora -v`, Pagefind, `setup-node` ≥ minimum); verify (rebuild, diff against baseline ignoring the `generator` tag and sitemap `lastmod`, compare logs, repository docs checks, search over HTTP); UI bundle comparison, stop if a rebuilt bundle is required; docs and report. Never edits pages.
  - [x] Task 8.3. Nav override handling: offer it when the thresholds say so and none exists; offer to replace an older copy (no text-only group rule, or a hard-coded group title), comparing the nav HTML of a sample of pages before and after.
  - [x] Task 8.4. Copy `reference/toolchain.md`, `ui-overrides/` and `scripts/` byte-identically from `iru-setup-antora`; the skill never assumes it runs inside `ai-catalog`.

### Group 4 — Workflow templates (Parallelizable: yes — disjoint files)

Every task replaces the old install step with the `toolchain.md` snippet, adds `npx antora -v` and the Pagefind step (placed per the API-docs rule), checks `actions/setup-node` is Node 20 or later, adds the optional (commented) size-guard block, and keeps every other step.

- [x] Task 9. `iru-setup-java-github-workflows/templates/common/.github/workflows/develop.yml` (remove `mkdir docs`) and the skill's notes.
  - Done: java develop.yml + SKILL.md notes; YAML parses, catalog-audit 0 errors; no tests apply (templates only).
- [x] Task 10. `iru-setup-android-github-workflows/templates/gitflow/.github/workflows/develop.yml` (remove `docs-toolchain`) and the "Install Antora step uses `mkdir -p docs-toolchain`" notes in its `SKILL.md`.
  - Done: android develop.yml + SKILL.md notes; YAML parses, catalog-audit 0 errors; no tests apply (templates only).
- [x] Task 11. `iru-setup-swift-github-workflows/templates/{app,library}/.github/workflows/build.yml` and its notes.
  - Done: swift app/library build.yml + SKILL.md notes; YAML parses, catalog-audit 0 errors; no tests apply (templates only).
- [x] Task 12. `iru-setup-cli-github-workflows/reference/{dotnet,go,rust,swift}-workflows.md`.
  - Done: cli dotnet/go/rust/swift reference; YAML parses, catalog-audit 0 errors; no tests apply (templates only).
- [x] Task 13. `iru-setup-{kmp,macos,windows}-github-workflows/reference/workflow-templates.md`.
  - Done: kmp/macos/windows workflow-templates.md; YAML parses, catalog-audit 0 errors; no tests apply (templates only).
- [x] Task 14. Templates already on `npm ci` — add Pagefind step, Node check and optional size guard: python, php, quarkus, `iru-setup-typescript-github-workflows/templates/generic` (+ `SKILL.md`, `reference/notes-build-generic.md`), `iru-setup-java-springboot-github-workflows/templates/{maven,kotlin-gradle}`.
  - Done: python, php, quarkus, typescript generic (+SKILL/notes), springboot maven/kotlin-gradle; YAML parses, catalog-audit 0 errors; no tests apply (templates only).

### Group 5 — Registration and this repository's own site (Parallelizable: yes — `tools/`, README and `docs/` are disjoint)

- [x] Task 15. Register and enforce
  - [x] Task 15.1. Add `iru-update-antora` to `iru-core` in `tools/plugins.json`, regenerate `.claude-plugin/marketplace.json` with `tools/generate-marketplace.py`, and mention the skill in `README.md` where skills are listed.
  - [x] Task 15.2. Add `toolchain.md`, the override file names (`article.hbs`, `footer-scripts.hbs`, `head-styles.hbs`, `header-content.hbs`, `nav-tree.hbs`, `nav-item-state.js`, `pagefind-site.css`) and the script file names to `shared_identical_files` in `tools/catalog-budgets.json` (document in `tools/README.md`); add a unit test in `tools/tests/test_catalog_audit.py` that drift in `toolchain.md` fails the check.
  - [x] Task 15.3. Run `python3 tools/catalog-audit.py --check`, `python3 tools/generate-marketplace.py --check`, `claude plugin validate .` and `python3 -m unittest discover -s tools/tests` via `iru-gate-runner` and fix findings (description budgets, model tier, shared drift).
- [x] Task 16. Move this repository's `docs/` to the new setup (run `iru-update-antora` on it, or do the same by hand)
  - [x] Task 16.1. `docs/package.json`: exact pinned set in `dependencies`, `engines`, scripts; regenerate `docs/package-lock.json`; drop Lunr.
  - [x] Task 16.2. `docs/antora-playbook.yml`: remove Lunr, register the Pagefind (and nav) `ui.supplemental_files`; copy `ui-overrides/` and `scripts/` into `docs/`.
  - [x] Task 16.3. `git rm -r --cached docs/node_modules` (keep the `.gitignore` entry) so the 6,310 tracked files go away.
  - [x] Task 16.4. `.github/workflows/docs.yml`: `npx antora -v`, Pagefind step, optional size guard; keep `.nojekyll` and deploy as they are.
  - [x] Task 16.5. Run `measure.mjs` on the built site, enable the nav override only if the thresholds say so, and record the decision in `docs/README` / `CLAUDE.md` either way; update `CLAUDE.md` commands (`npm ci`, `npx antora`, Pagefind) and any text naming Lunr.

### Group 6 — Generated docs (Parallelizable: no — Task 18 edits pages after Task 17 regenerates them)

- [x] Task 17. Run `/iru-generate-skill-docs` so `iru-update-antora` gets its page, `nav.adoc`, `index.adoc` and the dependency graph, and the `iru-setup-antora`, `iru-build-docs`, `iru-update-docs` pages and the workflow-skill pages drop Lunr and `docs-toolchain`. Hand-edit the `guides/` pages only where they state the old install pattern or the Antora version (check `plugins.adoc`, `catalog-architecture.adoc`, `creating-skills-and-agents.adoc`).
  - Done: new `skills/iru-update-antora.adoc`, nav, index row/group/graph node, count 196 to 197; setup-antora, build-docs, update-docs pages updated; build passes (Antora, Pagefind, nav dead-end check OK); no tests applicable (docs only).
- [x] Task 18. Run `/iru-update-docs` for the diff so the hand-maintained guides match the new toolchain.

### Group 7 — End-to-end validation (Parallelizable: no — needs every earlier group)

- [x] Task 19. Exercise `iru-update-antora` on a scratch copy of the pre-change `docs/` (3.1.15 + Lunr): confirm it upgrades the set, rewrites the workflow, regenerates the lockfile and that the build diff shows only the `generator` tag and sitemap `lastmod` (plus the intended search UI change when Lunr is replaced).
  - Done on a scratch git repo from `git archive HEAD docs .github/workflows/docs.yml` (3.1.15 + Lunr, node_modules excluded): baseline build exit 0; upgraded to the pinned set (Lunr removed, pagefind 1.6.0, engines, scripts, lockfile regenerated), workflow rewritten (setup-node cache, npm ci, antora -v, Pagefind), build exit 0 with identical log. Diff (generator tag normalised; no sitemap because no `site.url`): only the search UI change (Lunr files removed, Pagefind added, header menu replaced, `data-pagefind-body`), the same 57-line hunk on 214 pages; nav override adds only `is-active` and the marker comment. Dead-end check OK, nav tests 33/33.
  - Defect found and fixed: `measure.mjs` `usesOverride` keyed on `data-depth`, which the stock bundle also emits, so a Lunr-era site with a 57% nav got "enabled" (exit 0) instead of "recommend" (exit 3). `nav-tree.hbs` now writes `<!-- nav-tree override -->` in each list and `measure.mjs` checks that marker (tests updated). Copies synced byte-identically in `iru-setup-antora`, `iru-update-antora`, `iru-build-docs` and `docs/`.
- [x] Task 20. Final checks by delegating to `iru-gate-runner`: `cd docs && npm ci && npx antora antora-playbook.yml && npx pagefind --site build/site`, the dead-end check, `node --test` for the nav scripts, `python3 tools/catalog-audit.py --check`, `python3 tools/generate-marketplace.py --check`, `python3 -m unittest discover -s tools/tests`; grep that no template contains `docs-toolchain`, `mkdir docs` or `lunr`.
  - Run directly (not via gate-runner): `npm ci`, antora build, pagefind, dead-end check (217 pages OK), `npm run test:nav` 33/33, catalog-audit 0 errors (36 warnings, line counts), generate-marketplace up to date, unittest 91 OK, grep for docs-toolchain / mkdir docs / lunr in templates and workflow references: no matches. Added `/docs/node_modules/` to `.gitignore`.
