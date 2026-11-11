# Implementation plan — downloadable skills and agents packages on the Antora site (button + generated zips)

## Task summary

Source: GitHub issue #34
Base branch: main

Give readers of the published documentation a one-click way to download the catalog's skills and agents as zip files, and
show that download as a prominent button (same look as the cheat-sheet download buttons in `albertoirurueta/docs`) on the
home page and on every page that explains how to install or adopt the catalog. The zips are generated at docs-build time,
not committed, and the link must work on this repository's GitHub Pages site and on www.irurueta.com (whose
`albertoirurueta/docs` playbook builds this repository's `main` as a content source).

Decisions made on the user's behalf (the issue's own recommendations; challenge in review):

- **Delivery: Antora `@antora/collector-extension`.** An `ext.collector` entry in `docs/antora.yml` runs a script that builds
  the zips into a scan directory mapped to `modules/ROOT/attachments/` (and a generated partial listing them). The docs
  repository already loads the extension (1.0.3, the version pinned in `reference/toolchain.md`), so www.irurueta.com builds the zips
  too; this repository gains the same pinned extension. Rejected: GitHub Release assets (no releases or tags exist yet) and
  committed binaries (bloat git history on every skill change).
- **Scope: one zip of the full catalog (required) plus one zip per plugin in `tools/plugins.json`** (the issue's "nice to
  have", cheap because membership already exists). Layout inside every zip is a consuming repository's `.claude/` directory
  (`skills/iru-*/…`, `agents/iru-*.md`), so unzipping into a project's `.claude/` installs it.
- **Script in `tools/`, Python standard library only** (`tools/build-packages.py`), so it needs no `pip install` in either CI
  (the docs repository's build has no `pyyaml`) and stays out of the byte-identical `docs/scripts/` mirror. It resolves
  plugin membership with the same rules as `tools/generate-marketplace.py` (glob `skills` patterns minus `exclude`, plus
  `agents`); a test pins that equivalence.
- **One partial as the single source of the button**: `docs/modules/ROOT/partials/download-catalog.adoc` holds the block button
  and the "unzip into `.claude/`" step; pages `include::partial$download-catalog.adoc[]` it. `iru-generate-skill-docs`
  emits that include line in `index.adoc`, so regeneration keeps it.
- **Buttons are static SVG files** committed under `docs/modules/ROOT/images/` (a wide pill and a compact variant), copied in
  style from the docs repository's `download-cheat-sheet-pdf.svg` and `download-pdf-compact.svg` (readable with `gh api`),
  relabelled and with `<title>` for accessibility. No generator script is added here.
- **No language tag except `python`** for the zip script: the rest is YAML, AsciiDoc, SVG and Markdown, implemented directly
  (untagged). `python` has no installed `*-code-one-task` skill, so those tasks are implemented directly too.
- **Freshness**: the zips are rebuilt by the collector in every docs build, so they track the skills and agents on `main`
  automatically; no extra trigger is added (Task 3.5 explains the nightly delay on www.irurueta.com).
- **Risk to verify first (Task 4)**: how the collector resolves `dir`/`scan` when `start_path: docs`, and that it works for a
  remote clone of `main` as in the docs repository's playbook. Task 4 proves it with a local build of both playbooks.

Open clarifications: none

## Acceptance criteria coverage

| # | Criterion | Covered by tasks |
|---|---|---|
| 1 | "A build step produces the full-catalog zip (and, if adopted, one zip per plugin) from the skills and agents on disk; unzipping into a project's `.claude/` gives working `skills/` and `agents/` directories." | Task 1, Task 2, Task 4 |
| 2 | "An SVG download button in the same style as the cheat-sheet button (`download-cheat-sheet-pdf.svg`) exists in `docs/modules/ROOT/images/`, with alt text." | Task 5 |
| 3 | "The home page shows the button prominently near the top, linking to the zip." | Task 6, Task 9 |
| 4 | "Every page with installation/adoption instructions (at least `index.adoc` "A plugin", `guides/packaging-and-distribution.adoc`, `guides/plugins.adoc`) shows the button." | Task 6, Task 7 |
| 5 | "`iru-generate-skill-docs` emits the button on the generated pages, so regeneration keeps it." | Task 9 |
| 6 | "The download link works on the GitHub Pages site and on www.irurueta.com (checked against a local build of each, or the docs repository build)." | Task 4, Task 11 |
| 7 | "`cd docs && npx antora antora-playbook.yml`, `npm run test:nav`, `npm run test:nav:site`, `python3 tools/catalog-audit.py --check`, `python3 tools/generate-marketplace.py --check` and `python3 -m unittest discover -s tools/tests` all pass, and the site stays under the size limits." | Task 3, Task 10, Task 11 |
| 8 | "Docs explain where the download is and how to install from the zip (`guides/packaging-and-distribution.adoc`)." | Task 7, Task 8 |

## Current code state

- `docs/antora.yml` is only `name`, `version`, `title`, `nav`; no `ext.collector`. `docs/package.json` pins `antora` 3.2.2,
  `@sntke/antora-mermaid-extension`, `@djencks/asciidoctor-mathjax` and `pagefind`; no collector. `docs/antora-playbook.yml`
  lists mermaid and mathjax extensions (the collector is not required in the local playbook until `antora.yml` uses it).
- `docs/modules/ROOT/` holds only `nav.adoc` and `pages/`; there is no `images/`, `attachments/` or `partials/` directory.
- `docs/modules/ROOT/pages/index.adoc`: intro paragraph at lines 1-12, "A plugin" at line 69, "Further guides" at line 82.
  Regenerated by `iru-generate-skill-docs`, whose Step 7 preserves existing intro material and lists what the page contains.
- `guides/packaging-and-distribution.adoc`: "Option 1 — copy the files directly" (line 11), "This catalog ships both ways"
  (line 46). `guides/plugins.adoc`: "This catalog's own marketplace" (line 72). `README.md`: adoption section at lines 25-48.
- `tools/plugins.json`: 19 plugins, each with `name`, `skills` (globs such as `iru-java-*`), optional `exclude`, optional
  `agents`; resolution lives in `tools/generate-marketplace.py` (`matches`, `resolve_skills`, `resolve_agents`).
  Tests in `tools/tests/` (unittest). `tools/README.md` documents the scripts.
- `.github/workflows/docs.yml` builds with `npm ci`, `npx antora antora-playbook.yml`, Pagefind, a site-size gate
  (960,000 KiB) and deploys to `gh-pages`; it installs Node only (no Python step).
- Measured: zip of `.claude/skills` + `.claude/agents` is about 4.2 MB (11 MB raw); `.gitignore` already ignores
  `/docs/build/` and `/docs/node_modules/`.
- `albertoirurueta/docs` loads `@antora/collector-extension` 1.0.3 and includes this repository from `main` with
  `start_path: docs`; its cheat-sheet pages use `image::download-cheat-sheet-pdf.svg["…",width=320,xref=attachment$<file>.pdf]`.

## Implementation steps

### Group 1 — Package builder (Parallelizable: yes)

- [x] Task 1. Add `tools/build-packages.py` and its tests _(python)_
  - [x] Task 1.1. Create `tools/build-packages.py` (standard library only; `argparse`, `fnmatch`, `json`, `zipfile`, `pathlib`).
    CLI: `python3 tools/build-packages.py --out <dir> [--root <repo>] [--partial <file>]`. Behavior:
    - Read `tools/plugins.json`; list skill directories under `.claude/skills/` and agent files under `.claude/agents/`.
    - Write `<out>/ai-catalog-skills-agents.zip` containing every `skills/<name>/**` and `agents/*.md` (zip paths relative
      to `.claude/`, e.g. `skills/iru-plan/SKILL.md`, `agents/iru-gate-runner.md`).
    - For each plugin write `<out>/<plugin-name>.zip` with its resolved skills and agents (same layout; glob `skills` minus
      `exclude`, plus `agents`); a plugin with no agents has only `skills/`.
    - Deterministic output: sorted entries, fixed timestamp (`ZipInfo` with 1980-01-01), stable permissions, so two runs are
      byte-identical.
    - With `--partial`, also write an AsciiDoc fragment (a table: plugin, skill count, agent count, size, compact download
      button `image:download-zip-compact.svg["Download <plugin> (zip)",width=110,xref=attachment$<plugin>.zip]`) for the
      plugins page; exit non-zero with a clear message when a pattern matches nothing or a listed agent is missing.
    - Never write inside `.claude/` or the repository outside `--out`/`--partial`.
  - [x] Task 1.2. Add `tools/tests/test_build_packages.py` (unittest, temporary directory fixtures): layout of the full zip,
    per-plugin membership with `exclude`, agents routed to `iru-core`, determinism (two runs equal), error on an empty
    pattern, partial content, and an equivalence test asserting the membership equals `generate-marketplace.py`'s
    `resolve_skills`/`resolve_agents` on the real `tools/plugins.json` (skip with a message when `pyyaml` is missing).
  - [x] Task 1.3. Run the new tests through the `iru-gate-runner` agent (`Agent({description: "Run tools tests", subagent_type:
    "iru-gate-runner", prompt: "Run `python3 -m unittest discover -s tools/tests` and report a compact summary"})`) and run
    `python3 tools/catalog-audit.py --check`.
  - [x] Task 1.4. Document the script in `tools/README.md` (purpose, usage, that the docs build calls it through the collector).

### Group 2 — Collector wiring (Parallelizable: no — Task 3 depends on the script of Group 1 and Task 4 verifies Task 3)

- [x] Task 2. Add the collector extension to this repository's docs toolchain
  - [x] Task 2.1. In `docs/`, run `npm i -E @antora/collector-extension@1.0.3` so `package.json` and `package-lock.json` pin
    it exactly (`.claude/skills/iru-setup-antora/reference/toolchain.md` already lists it for `ext.collector` use).
    - Note: `docs/package.json` and `package-lock.json` pin `@antora/collector-extension` 1.0.3 exactly (npm also re-sorted the dependency keys alphabetically).
  - [x] Task 2.2. Add `'@antora/collector-extension'` to `antora.extensions` in `docs/antora-playbook.yml`, before the mermaid
    extension, mirroring the docs repository's playbook.
    - Note: `docs/antora-playbook.yml` loads the collector before the mermaid extension.
- [x] Task 3. Declare the build in `docs/antora.yml`
  - [x] Task 3.1. Add `ext.collector` entries: one that runs `python3 tools/build-packages.py --out <build dir>
    --partial <build dir>/plugin-downloads.adoc` from the repository root and scans the zips into
    `modules/ROOT/attachments/`; one scan of the generated fragment into `modules/ROOT/partials/`. Use paths relative to the
    worktree root as the collector requires for `start_path: docs`.
    - Note: `docs/antora.yml` `ext.collector`: run `python3 tools/build-packages.py --out docs/build/packages --partial docs/build/packages/plugin-downloads.adoc`, scan `*.zip` into `modules/ROOT/attachments`, scan the fragment into `modules/ROOT/partials`.
  - [x] Task 3.2. Add the generated build directory to `.gitignore` (and ignore `docs/modules/ROOT/attachments/*.zip` and
    `docs/modules/ROOT/partials/plugin-downloads.adoc` if the collector writes them into the working tree for the local
    playbook).
    - Note: `.gitignore` adds the two generated working-tree paths; `docs/build/` was already ignored, so the build dir needs no new entry. Verified the local build leaves `docs/modules/ROOT` untouched (collector injects files in memory).
  - [x] Task 3.3. Update `.github/workflows/docs.yml`: no Python install is needed (standard library, `python3` on
    `ubuntu-latest`), but add a `python3 --version` step before the Antora build and print the attachments size next to the
    existing site-size check, so a size regression is visible.
    - Note: `docs.yml` gains a `python3 --version` step before the Antora build and a "Show attachments size" step after the site-size gate.
  - [x] Task 3.4. Update `.github/workflows/catalog-check.yml` (runs on pull requests): add a step that runs
    `python3 tools/build-packages.py --out "$RUNNER_TEMP/packages"` and fails when it errors or produces no full-catalog zip, so a
    skill or `plugins.json` change that breaks packaging is caught in the PR instead of failing the docs build on `main`
    (and, through the collector, the docs repository's build).
    - Note: `catalog-check.yml` gains a final "Check the download packages build" step (fails on script error or missing/empty full zip).
  - [x] Task 3.5. Freshness note, no workflow change needed: `docs.yml` already rebuilds and publishes on every push to `main`, so the
    GitHub Pages zips follow every skill or agent change; `albertoirurueta/docs` rebuilds www.irurueta.com nightly
    (`publish.yml`, cron 03:00 UTC) and on `workflow_dispatch`, so its zips are at most about a day behind. Record this in
    `guides/packaging-and-distribution.adoc` (Task 10.1) so readers know the zips reflect the last published build.
    - Note: No workflow change. Freshness statement (Pages zips follow every push to `main`; www.irurueta.com zips at most about a day behind via the nightly 03:00 UTC `publish.yml`) is to be written into `guides/packaging-and-distribution.adoc` by Task 10.1 (that guide edit is intentionally deferred to that task).
- [x] Task 4. Prove the collector works in both builds (spike with real output)
  - [x] Task 4.1. Build the local playbook (`cd docs && npx antora antora-playbook.yml`) and confirm the zips appear under
    the built site's `_attachments/` (check `docs/build/site/ai-catalog/_attachments/`).
    - Note: Local build produced all 19 zips (full + 18 plugins) under `docs/build/site/ai-catalog/1.0.0/_attachments/` (note the `1.0.0` version segment: `docs/antora.yml` has `version: 1.0.0`; in the docs repo versioned/unversioned depends on its component descriptor, so links must use `xref=attachment$` rather than hard-coded paths).
  - [x] Task 4.2. Build a scratch copy of the `albertoirurueta/docs` playbook (read it with `gh api`; place the scratch files
    - Note: Scratch playbook (copy of the `albertoirurueta/docs` one via `gh api`, ai-catalog source only, in the scratchpad) built OK for (a) `url: <repo path>`, `branches: HEAD`, `start_path: docs`: 19 zips; collector uses the checked-out working tree as the worktree (uncommitted files included) and the log shows `run.command ... start path: docs`. (b) A bare clone (`branches: main`), simulating a remote: no worktree exists, so the collector creates one in its cache and checks out the branch; 19 zips again. In both cases the `run.command` cwd (default `run.dir`) is the ROOT of the worktree, not the start path `docs`, so `tools/build-packages.py` and `docs/build/packages` paths relative to the repository root are correct; the script also resolves the repo root from its own location. `file://` URLs are rejected by Antora itself. No NEEDS CLARIFICATION needed; the collector works for clones. Real remote (`https://github.com/albertoirurueta/ai-catalog.git`, `main`) not run because the branch is not pushed; it needs `python3` on the docs repository runner (ubuntu-latest has it).
    in the scratchpad, not in the repository) pointing the `ai-catalog` source at this local checkout's feature branch
    (`url: <repo path>`, `branches: HEAD`, `start_path: docs`) and confirm the same zips are produced; record the exact
    working-directory/`run.dir` behavior in the plan's progress notes. If the collector cannot run for a remote clone,
    stop and record the alternative (GitHub Release asset or committed zips) as a `[NEEDS CLARIFICATION: …]` marker on
    Task 3 instead of continuing.
  - [x] Task 4.3. Unzip the generated full zip into a temporary `.claude/` and confirm every `SKILL.md` and agent file is
    present and the skill count equals the number of `.claude/skills/iru-*` directories.

### Group 3 — Buttons, partials and page placement (Parallelizable: yes — Tasks 5, 6, 7 and 8 edit disjoint files)

- [x] Task 5. Add the SVG download buttons
  - [x] Task 5.1. Read `modules/ROOT/images/download-cheat-sheet-pdf.svg` and `download-pdf-compact.svg` from
    `albertoirurueta/docs` with `gh api` and create `docs/modules/ROOT/images/download-catalog-zip.svg` (wide gradient pill,
    download icon, label "Download skills & agents (zip)") with `<title>` and `<desc>` elements.
  - [x] Task 5.2. Create `docs/modules/ROOT/images/download-zip-compact.svg` (icon plus "ZIP", legible at ~110 px) for the
    plugin table cells; keep both files self-contained (no external fonts or links) and valid XML (`xmllint --noout`).
- [x] Task 6. Add the shared partial and place it on the home page
  - [x] Task 6.1. Create `docs/modules/ROOT/partials/download-catalog.adoc`: the block button
    `image::download-catalog-zip.svg["Download the catalog skills and agents (zip)",width=320,xref=attachment$ai-catalog-skills-agents.zip]`
    followed by a short "unzip into your repository's `.claude/` directory" step and a pointer to
    `xref:guides/plugins.adoc[]` for per-plugin zips and the marketplace.
  - [x] Task 6.2. Edit `docs/modules/ROOT/pages/index.adoc`: `include::partial$download-catalog.adoc[]` right after the intro
    paragraph (before "== Why this exists") and again at the end of "A plugin"/adoption text (line ~80) via a
    one-line sentence plus the include.
- [x] Task 7. Place the partial on the other install/adoption pages
  - [x] Task 7.1. `guides/packaging-and-distribution.adoc`: include it at the top of "Option 1 — copy the files directly"
    and in "This catalog ships both ways", with a sentence that the zip is the copy path without cloning.
  - [x] Task 7.2. `guides/plugins.adoc`: include it under "This catalog's own marketplace" and add a "Downloading a plugin as a
    zip" section containing `include::partial$plugin-downloads.adoc[]` (the generated table of per-plugin zips).
  - [x] Task 7.3. Search the other pages for installation steps (`grep -rn -iE 'install|copy .*\.claude' docs/modules/ROOT/pages/guides`)
    and add the include where a page really gives adoption steps; list any pages left out and why in the progress notes.
- [x] Task 8. Update `README.md`: add a link to the published download page (the docs home page) in the adoption section, and
  state the unzip step. Keep within the README conventions (no new badges).
  - Note: Task 7.3 left other guides without the include (provider-comparison, performance-and-token-budget, creating-skills-and-agents, extending-the-catalog, catalog-architecture, common-workflows): they only mention install/installed in passing and give no adoption steps. Antora build clean, SVGs pass xmllint, license-header generation skipped (docs/SVG only).

### Group 4 — Generator skill, catalog docs and conventions (Parallelizable: no — depends on the partial and page layout of Group 3)

- [x] Task 9. Make `iru-generate-skill-docs` emit and preserve the download button
  - [x] Task 9.1. Edit `.claude/skills/iru-generate-skill-docs/SKILL.md` Step 7: after the introductory material, the page must
    contain `include::partial$download-catalog.adoc[]` when `docs/modules/ROOT/partials/download-catalog.adoc` exists
    (create the partial from the packaging convention when the repository has `tools/build-packages.py`; otherwise skip
    silently). Keep behavior otherwise equivalent and stay under the skill's line budget.
  - [x] Task 9.2. Mention the include in Step 7's page-content list and in the Step 11 report; update the skill's own page
    `docs/modules/ROOT/pages/skills/iru-generate-skill-docs.adoc` accordingly (generated page, so edit through the skill's
    process or a faithful manual edit that regeneration would reproduce).
  - [x] Task 9.3. Run `python3 tools/catalog-audit.py --check` (description size, line counts, asset paths) through
    `iru-gate-runner`.
- [x] Task 10. Explain the feature in the hand-maintained docs and conventions
  - [x] Task 10.1. `guides/packaging-and-distribution.adoc`: new section "Option 1b — download the zip from the documentation"
    describing the zips, their layout, how to install them, how they are built (collector) and that they reflect the
    catalog on the published branch (satisfies the "Docs explain where the download is and how to install" criterion).
  - [x] Task 10.2. `CLAUDE.md`: add a short paragraph under "Commands" (the collector builds the zips with
    `tools/build-packages.py`; `python3 tools/build-packages.py --out <dir>` to run it by hand) and keep the existing
    text otherwise unchanged. Add a `CHANGELOG.md` entry under the unreleased section.
  - [x] Task 10.3. Confirm `tools/generate-marketplace.py --check` still passes (no manifest change expected).

### Group 5 — Verification and documentation refresh (Parallelizable: no — validates everything above)

- [x] Task 11. Verify the whole change
  - [x] Task 11.1. Build the local site (`cd docs && npm ci && npx antora antora-playbook.yml && npx pagefind --site build/site`), Built OK (no warnings), pagefind OK, test:nav 0 fail, test:nav:site OK (217 pages), site 27,268 KiB.
    then run `npm run test:nav && npm run test:nav:site`; check `du -sk build/site` stays well under 900,000 KiB.
  - [x] Task 11.2. Open the built `index.html`, `guides/plugins.html` and `guides/packaging-and-distribution.html` Button, alt text and _attachments zip links verified on index, plugins, packaging pages; no Antora warnings.
    (`docs/build/site/ai-catalog/…`) and confirm the button renders, links to an existing `_attachments/*.zip`, and has
    alt text; check no nav dead-end or broken `xref` warnings in the Antora log.
  - [x] Task 11.3. Re-run the scratch docs-repository playbook from Task 4.2 and confirm the same page and zip resolve in the Scratch docs playbook (refreshed snapshot, collector) resolves pages and 19 zips; only the expected missing-ROOT start page warning.
    combined site (the www.irurueta.com configuration).
  - [x] Task 11.4. Run `python3 tools/catalog-audit.py --check`, `python3 tools/generate-marketplace.py --check`, catalog-audit 0 errors, marketplace up to date, plugin validate passed, 103 unit tests OK.
    `claude plugin validate .` (when the CLI is installed) and `python3 -m unittest discover -s tools/tests` through
    `iru-gate-runner`.
- [x] Task 12. Run `/iru-update-docs` to confirm the Antora pages match the change (the regenerated catalog pages are covered by
  Task 9; this checks the hand-maintained guides and the nav), and record in the progress notes any page where regeneration
  with `/iru-generate-skill-docs` would drop the include.
