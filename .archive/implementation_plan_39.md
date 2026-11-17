# Implementation plan — Sync workflows: name sync branches after the released version

## Task summary

Every `iru-setup-<stack>-github-workflows` skill generates a `sync.yml` workflow. When a GitHub Release is published from
the stable branch, the workflow merges it back into the integration branch, bumps the development version and opens a
`sync` pull request. Today the branch is named after the **next development version** (`sync_1.1.0` for release
`1.0.0`), and the "already synced" guard skips the job when that branch exists on `origin`. A later patch release
(`1.0.1`) computes the same name, finds the leftover branch and silently skips, so the hotfix never reaches `develop`.

Fix: name the branch after the **released version** (`sync_${RELEASE_VERSION}`, e.g. `sync_1.0.1`), so the guard really
means "this release was already synced".

Decisions taken with the user while planning:

- **Merge conflicts** (new: surfaced in planning). Once patch releases get past the guard, merging the stable branch
  almost always conflicts on the version line (`main` changed `1.0.0 → 1.0.1`, `develop` changed
  `1.0.0 → 1.1.0-SNAPSHOT` against the same merge base). Today that fails the job. Chosen: on a merge conflict, abort
  the merge, point the sync branch at the release commit (`origin/<stable-branch>`) with **no version bump**, push it,
  and open the PR into the integration branch with a body that tells the reviewer to resolve the conflicts keeping the
  integration branch's development version. It works the same for every stack, with no per-stack path lists.
- **Version downgrade**: document only. With the conflict fallback a patch sync never runs the version script, so it
  cannot write a lower development version over the integration branch. No change to the `sync_versions.py`
  scripts.

Source: GitHub issue #39
Base branch: main

Open clarifications: none

## Acceptance criteria coverage

| # | Criterion | Covered by tasks |
|---|---|---|
| 1 | "All 11 sync templates name the branch `sync_<release-version>`; the "already synced" guard checks that name." | Task 1 – Task 11 |
| 2 | "Releasing `1.0.0` then `1.0.1` (with `sync_1.0.0` still on `origin`) opens a second sync PR from `sync_1.0.1`." | Task 1 – Task 11, Task 14 |
| 3 | "Re-running the workflow for the same release still skips (idempotency kept)." | Task 1 – Task 11, Task 14 |
| 4 | "SKILL.md examples, smoke-check descriptions and `iru-release` wording match the new naming." | Task 1 – Task 11, Task 12 |
| 5 | "The next-version downgrade case above is handled or explicitly documented." | Task 1 – Task 11 (per-skill note), Task 12, Task 13 |
| 6 | "`python3 tools/catalog-audit.py --check`, `python3 tools/generate-marketplace.py --check` and `python3 -m unittest discover -s tools/tests` pass; skill docs regenerated with `/iru-generate-skill-docs` if the skill pages change." | Task 15, Task 16 |
| 7 | derived: a patch-release sync whose merge conflicts still opens a PR (from the release commit, no bump) instead of failing the job | Task 1 – Task 11, Task 14 |

## Current code state

- There is no application code. The deliverables are skill templates (GitHub Actions YAML with Bash) and `SKILL.md`
  prose. No `*-code-one-task` key applies, so every task is untagged and implemented directly.
- All 11 `sync.yml` templates follow the same shape: check out → **Compute versions and branch names** (strip `v`, split
  `X.Y.Z`, compute the next version, derive `sync_branch`) → **Skip if this release was already synced**
  (`git ls-remote --exit-code --heads origin <sync_branch>`, output `exists`) → configure git → create the sync branch
  from `origin/<integration-branch>` → `git merge --no-ff --no-edit … origin/<stable-branch>` → set up the toolchain →
  run the version script(s) → commit → push → ensure the `sync` label → `gh pr create --title "Sync <next>" --label sync`.
  Every later step is gated on `steps.guard.outputs.exists == 'false'`.
- Some templates merge steps together: Python and PHP use "Create the sync branch and merge the release into it" and
  "Commit and push the sync branch". TypeScript has two bump steps (npm and Python). Swift has two "Commit the version
  bump" steps (one per flavor). Each must be adapted to its own structure, following the Shared contract below.
- The branch-naming line in each file:

  | Task | Skill | File (under `.claude/skills/<skill>/`) | Today |
  |---|---|---|---|
  | 1 | `iru-setup-java-github-workflows` | `templates/common/.github/workflows/sync.yml:40` | `sync_${MAJOR}.${NEXT_MINOR}.0` |
  | 2 | `iru-setup-quarkus-github-workflows` | `templates/common/.github/workflows/sync.yml:40` | `sync_${MAJOR}.${NEXT_MINOR}.0` |
  | 3 | `iru-setup-python-github-workflows` | `templates/common/.github/workflows/sync.yml:40` | `sync_${MAJOR}.${NEXT_MINOR}.0` |
  | 4 | `iru-setup-php-github-workflows` | `templates/common/.github/workflows/sync.yml:40` | `sync_${MAJOR}.${NEXT_MINOR}.0` |
  | 5 | `iru-setup-windows-github-workflows` | `reference/workflow-templates.md:882` | `sync_${MAJOR}.${NEXT_MINOR}.0` |
  | 6 | `iru-setup-cli-github-workflows` | `reference/shared-templates.md:449` | `sync_${MAJOR}.${NEXT_MINOR}.0` |
  | 7 | `iru-setup-android-github-workflows` | `templates/gitflow/.github/workflows/sync.yml:40` | `sync_${MAJOR}.${MINOR}.${NEXT_PATCH}` |
  | 8 | `iru-setup-kmp-github-workflows` | `reference/workflow-templates.md:543` | `sync_${MAJOR}.${MINOR}.${NEXT_PATCH}` |
  | 9 | `iru-setup-swift-github-workflows` | `templates/common/.github/workflows/sync.yml:37` | `sync_${MAJOR}.${MINOR}.${NEXT_PATCH}` |
  | 10 | `iru-setup-typescript-github-workflows` | `templates/common/.github/workflows/sync.yml:40` | `sync_${MAJOR}.${MINOR}.${NEXT_PATCH}` |
  | 11 | `iru-setup-macos-github-workflows` | `reference/workflow-templates.md:757` | `sync_$NEXT_VERSION` |

- Prose that quotes the old naming: `iru-setup-python-github-workflows/SKILL.md:531` (`sync_1.4.0`),
  `iru-setup-windows-github-workflows/SKILL.md:347` (`sync_1.5.0`), `iru-setup-macos-github-workflows/SKILL.md:358`
  (`sync_1.4.1`), and `iru-release/SKILL.md:153` (`sync_x.y.z`, plus the Step 12 note about the minor-bump default).
- None of these files is in `shared_identical_files` (`tools/catalog-budgets.json`), so each is edited on its own.
  `tools/tests` has no sync tests. No generated Antora page quotes `sync_<version>`. The hand-maintained guide
  `docs/modules/ROOT/pages/guides/common-workflows.adoc:385` mentions the Sync workflow's automatic bump (in a Mermaid
  node; leave the diagram unchanged).
- `iru-setup-java-springboot-github-workflows` generates no `sync.yml`, and the three agents are not affected.
- Precedent: `.archive/implementation_plan_15.md` changed workflow templates across skills in parallel groups split by
  file, then regenerated the docs in a final non-parallel group. This plan follows the same shape.

### Shared contract (every template task applies exactly this)

1. **Branch name**: in "Compute versions and branch names", `sync_branch` becomes `sync_${RELEASE_VERSION}`. Keep the
   next-version computation and its output name (`next_snapshot` / `next_version` / `NEXT_DEV`) unchanged, and drop
   variables that are no longer used only if they become unused. Update that step's comment or the job comment if it
   explains the name.
2. **Guard**: unchanged in logic (it already checks `sync_branch`). Its notice stays "`<sync_branch>` already exists on
   origin; skipping.", which now means "this release was already synced".
3. **Merge with conflict fallback**: give the merge step `id: merge` and replace the bare merge with:

   ```bash
   if git merge --no-ff --no-edit \
       -m "Merge <stable-branch> (${RELEASE_VERSION}) into <integration-branch>" \
       "origin/<stable-branch>"; then
     echo "conflict=false" >> "$GITHUB_OUTPUT"
   else
     git merge --abort
     echo "::warning::Merging <stable-branch> (${RELEASE_VERSION}) into <integration-branch> conflicts; opening the sync pull request from the release commit for manual resolution, without bumping the development version."
     git checkout -B "${SYNC_BRANCH}" "origin/<stable-branch>"
     echo "conflict=true" >> "$GITHUB_OUTPUT"
   fi
   ```

   Keep each template's own way of referencing the values (`${{ steps.versions.outputs.* }}` or step `env:`).
   Templates that create the branch and merge in one step get the `id: merge` on that step.
4. **Gate the bump**: every toolchain-setup, version-bump, lockfile-refresh and commit step adds
   `&& steps.merge.outputs.conflict == 'false'` to its existing `if:` (keeping any flavor condition). The push, label and
   PR steps stay gated only on the guard. In a combined "commit and push" step (Python, PHP), wrap the commit lines in
   `if [ "${{ steps.merge.outputs.conflict }}" = "false" ]; then … fi` and keep the push unconditional.
5. **PR title and body**: no conflict → unchanged (`Sync <next>`, the existing body). Conflict → title
   `Sync <release_version> (merge conflicts to resolve)` and body:
   "Merges \`<stable-branch>\` (\`<release_version>\`) back into \`<integration-branch>\`. The automatic merge
   conflicted (usually on the version line), so this branch points at the release commit and the development version
   was **not** bumped. Resolve the conflicts keeping \`<integration-branch>\`'s development version and taking the
   release's changes otherwise." Implement it by choosing the title and body in shell from the merge output, using one
   `gh pr create` call.
6. **SKILL.md**: wherever the skill describes `sync.yml` (purpose bullet, Step section, verification or smoke-check
   lines, examples), state that the branch is `sync_<released version>` (e.g. release `1.0.1` → `sync_1.0.1`), describe
   the conflict fallback in one or two sentences, and add one sentence saying a conflicting (patch) sync never bumps, so
   it cannot lower the integration branch's development version. Fix every quoted example that ties the branch to the
   next version.

## Implementation steps

### Group 1 — Per-skill sync templates and their SKILL.md (Parallelizable: yes — each task touches only its own skill's directory; the Shared contract fixes the behavior)

- [x] Task 1. Java: apply the Shared contract to `.claude/skills/iru-setup-java-github-workflows/templates/common/.github/workflows/sync.yml` and the sync sections of `.claude/skills/iru-setup-java-github-workflows/SKILL.md`
  - [x] Task 1.1. Template: branch name, `id: merge` with fallback, gate "Set up Python", "Bump the development snapshot version" and "Commit the version bump", conflict-aware PR title and body
  - [x] Task 1.2. SKILL.md: the `sync.yml` purpose bullet (line ~17) and the Step 3 description gain the naming, fallback and no-downgrade sentences
- [x] Task 2. Quarkus: apply the Shared contract to `.claude/skills/iru-setup-quarkus-github-workflows/templates/common/.github/workflows/sync.yml` and `.claude/skills/iru-setup-quarkus-github-workflows/SKILL.md` (table row line ~15 and the `sync.yml` section)
- [x] Task 3. Python: apply the Shared contract to `.claude/skills/iru-setup-python-github-workflows/templates/common/.github/workflows/sync.yml` (combined "Create the sync branch and merge" step gets `id: merge`; "Set up uv", "Bump the development version", "Refresh uv.lock" and "Bump README and Antora versions" are gated; the combined "Commit and push" step guards only the commit) and `.claude/skills/iru-setup-python-github-workflows/SKILL.md`
  - [x] Task 3.1. SKILL.md line ~531: `1.3.0` / `v1.3.0` → `1.4.0.dev0`, `sync_1.3.0`
- [x] Task 4. PHP: apply the Shared contract to `.claude/skills/iru-setup-php-github-workflows/templates/common/.github/workflows/sync.yml` (same combined-step structure as Python) and `.claude/skills/iru-setup-php-github-workflows/SKILL.md`
- [x] Task 5. Windows: apply the Shared contract to the `sync.yml` block in `.claude/skills/iru-setup-windows-github-workflows/reference/workflow-templates.md` (line ~882) and `.claude/skills/iru-setup-windows-github-workflows/SKILL.md`
  - [x] Task 5.1. SKILL.md line ~347: `v1.4.0` → `1.5.0-dev`, `sync_1.4.0`
- [x] Task 6. CLI: apply the Shared contract to the `sync.yml` block in `.claude/skills/iru-setup-cli-github-workflows/reference/shared-templates.md` (line ~449; the merge is at ~483) and `.claude/skills/iru-setup-cli-github-workflows/SKILL.md` (line ~276 smoke check and the `sync.yml` description)
- [x] Task 7. Android: apply the Shared contract to `.claude/skills/iru-setup-android-github-workflows/templates/gitflow/.github/workflows/sync.yml` and the Step 5 `sync.yml` section of `.claude/skills/iru-setup-android-github-workflows/SKILL.md`
- [x] Task 8. KMP: apply the Shared contract to the `sync.yml` block in `.claude/skills/iru-setup-kmp-github-workflows/reference/workflow-templates.md` (line ~543) and `.claude/skills/iru-setup-kmp-github-workflows/SKILL.md`
- [x] Task 9. Swift: apply the Shared contract to `.claude/skills/iru-setup-swift-github-workflows/templates/common/.github/workflows/sync.yml` (both flavor-specific "Commit the version bump" steps keep their flavor condition and add the conflict gate) and the Step 8 section of `.claude/skills/iru-setup-swift-github-workflows/SKILL.md`
- [x] Task 10. TypeScript: apply the Shared contract to `.claude/skills/iru-setup-typescript-github-workflows/templates/common/.github/workflows/sync.yml` (gate "Set up Node", "Bump package.json and lockfile", "Set up Python", "Bump README/Antora version mentions" and "Commit the version bump"), and update `.claude/skills/iru-setup-typescript-github-workflows/reference/notes-sync.md` / `notes-sync-versions.md` and `.claude/skills/iru-setup-typescript-github-workflows/SKILL.md` wherever they describe the branch name or the merge
- [x] Task 11. macOS: apply the Shared contract to the `sync.yml` block in `.claude/skills/iru-setup-macos-github-workflows/reference/workflow-templates.md` (line ~757) and `.claude/skills/iru-setup-macos-github-workflows/SKILL.md`
  - [x] Task 11.1. SKILL.md line ~358: release `1.4.0` → `1.4.1`, `sync_1.4.0` (the branch now follows the release)

### Group 2 — Release skill and hand-maintained guide (Parallelizable: yes — two different files; both only describe the behavior fixed by the Shared contract)

- [x] Task 12. `.claude/skills/iru-release/SKILL.md` (around line 153 and Step 12's report note)
  - [x] Task 12.1. Say the Sync workflow opens a `sync_<released version>` PR (e.g. `sync_1.0.1`)
  - [x] Task 12.2. Add to the Step 12 note: for a patch release the merge usually conflicts on the version line, so the Sync PR opens from the release commit without a bump, and the reviewer resolves it keeping `develop`'s development version. The "minor-bump default should match" check applies only to releases whose merge is clean.
- [x] Task 13. `docs/modules/ROOT/pages/guides/common-workflows.adoc`: in the release section around line 385 (prose only, the Mermaid diagram stays untouched), add a short paragraph on patch releases: branch `sync_<release>`, conflict fallback, no bump, so no downgrade

### Group 3 — Verification (Parallelizable: no — Task 14 exercises the templates finished in Group 1, and Tasks 15–16 need every file final)

- [x] Task 14. Smoke-test the merge, fallback and guard logic in a scratch git repository (in the session scratchpad, never in this repository)
  - [x] Task 14.1. Build a bare "origin" plus a clone with `main` and `develop`: release `1.0.0` merged to `main`, `develop` bumped to `1.1.0-SNAPSHOT` with a leftover `sync_1.0.0` branch on origin, then a hotfix commit on `main` setting the version to `1.0.1`
  - [x] Task 14.2. Extract the Compute, Guard and Merge scripts from the Java template (placeholders replaced with `main` / `develop`, and `GITHUB_OUTPUT` pointing at a temp file), run them for tag `v1.0.1` and check: `sync_branch=sync_1.0.1`, guard `exists=false`, merge `conflict=true`, branch at `origin/main`'s commit
  - [x] Task 14.3. Re-run for `v1.0.0` → guard `exists=true` (idempotency). Run a clean-merge case (a release branch cut from `develop`) → `conflict=false`
  - [x] Task 14.4. Parse every edited `.yml` template with `python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))"`, and the YAML blocks in the edited `reference/*.md` files the same way after extracting them. Run `actionlint` on the `.yml` templates if it's installed (report it as skipped if not). Grep all 11 templates for `sync_\${MAJOR}`, `NEXT_MINOR}.0"` used in a branch name, or `sync_$NEXT_VERSION`: no matches may remain
- [x] Task 15. Regenerate docs: run `/iru-generate-skill-docs` and keep any changes to the generated pages (expected to be minimal). Then build `cd docs && npm ci && npx antora antora-playbook.yml` and run `npm run test:nav:site`
- [x] Task 16. Catalog checks: delegate to the `iru-gate-runner` agent (or run directly; there's no gate skill for this repository) `python3 tools/catalog-audit.py --check`, `python3 tools/generate-marketplace.py --check` and `python3 -m unittest discover -s tools/tests`. Fix any budget overrun (SKILL.md line counts) by tightening the new prose, never by raising budgets
