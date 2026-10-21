# Sample runs: after

Sample runs of **this working tree** (branch `feature/11-optimize-skills-performance-token-usage`, Claude Code 2.1.260,
2026-10-21, macOS) for the before/after comparison of issue #11. The "before" numbers and the way the samples are run
are in `sample-runs-before.md`. Raw JSON and produced files live under `$TMPDIR/iru-verify/results/after/` (outside this
repository).

Same method as the before runs: `claude -p --output-format json --permission-mode acceptEdits` through the
clean-environment wrapper (`env -i` with only `HOME`, `PATH`, `TMPDIR`, `USER`, `SHELL`, `LANG`; 1500 s alarm; stdin from
`/dev/null`), the same prompts, no extra flags (`--allowedTools=Skill` was **not** needed: a slash command is loaded by
the harness, not through the `Skill` tool). S0 ran from the repository root; S1 to S3 ran in fresh copies of the fixtures
with this repository's `.claude/` copied in, concurrently, like the before runs.

Prompt-side tokens = `input_tokens + cache_read_input_tokens + cache_creation_input_tokens`.

## Headline: S0, the listing cost

| | Input | Cache read | Cache creation | Output | Prompt side | Cost (USD) | Duration (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Before | 2 | 10,130 | 32,655 | 4 | 42,787 | 0.3327 | 5,063 |
| After | 2 | 10,130 | 20,146 | 4 | **30,278** | 0.2076 | 1,839 |

The fixed prompt (system prompt, tool schemas, the 196-skill listing and the account's own user-level skills) is **12,509
tokens (29.2 %) smaller**; the cache-read part (about 10 k) is the account's shared prefix and does not move, so the whole
reduction sits in the cache-creation part. The absolute value still contains the account overhead; the delta does not.

## Official S0 to S3 (the exact before commands)

| Sample | Input | Cache read | Cache creation | Output | Prompt side (before) | Prompt side (after) | Cost before | Cost after | Duration before | Duration after | Turns before / after | Model before / after |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| S0 | 2 | 10,130 | 20,146 | 4 | 42,787 | 30,278 | 0.3327 | 0.2076 | 5.1 s | 1.8 s | 1 / 1 | Opus 5 + Haiku / same |
| S1 | 10 | 267,217 | 69,529 | 6,158 | 1,158,903 | 336,756 | 0.2993 | 0.3932 | 69.0 s | 73.6 s | 15 / 5 | Haiku 4.5 / **Sonnet 5** |
| S2 | 73 | 286,583 | 28,791 | 2,721 | 303,946 | 315,447 | 0.5287 | 0.0999 | 58.1 s | 31.8 s | 9 / 9 | **Opus 5 (1M)** / **Haiku 4.5** |
| S3 | 10 | 212,655 | 44,835 | 5,250 | 259,764 | 257,500 | 0.6432 | 0.6860 | 59.6 s | 83.5 s | 13 / 9 | Opus 5 / Opus 5 |

Where the after number is **not** lower:

- S1 cost (0.2993 to 0.3932) and S3 cost (0.6432 to 0.6860) are higher, S3 duration is higher (59.6 s to 83.5 s) and S3
  produced more output (3,835 to 5,250 tokens: the message gained a `Build & layout` line). S2 prompt side is 3.8 % higher.
  Cost and duration of one LLM run vary from run to run; the sample is one run per side (S1 and S2 have more, below).
- The models are **not** the same before and after, by design of Group 2: S1's skill went from `haiku` to `sonnet`; S2's
  skill (`iru-setup-android-gitignore`) had frontmatter that did not parse, so Claude Code ignored its `model: haiku` and
  ran it on the account's default Opus 5 (1M); it now parses and really runs on Haiku. So S1 and S2 are not like-for-like on
  cost, and the cost columns must not be read as the effect of the template/description changes alone.
- Cache-read totals do not drop on a multi-turn skill run; only S0 (the listing) is a clean prompt-size measurement.

## Equivalence of the generated files (Task 22.2)

The official S1 and S2 runs did **not** write files (see below), so byte comparison used controlled runs. Every run was
a separate `claude -p` of the same prompt.

### S1 (`/iru-setup-typescript-github-workflows`, `flavor: library` ...)

| Run | Tree / model | Wrote files? | `build.yml` branches | `sync.yml` + script | Antora/docs steps |
|---|---|---|---|---|---|
| before (recorded) | main / Haiku | yes (`.github` + `.gitignore`) | `[ main ]` | no | no |
| before re-run 1, 2 | main / Haiku | yes | `[ main, main ]`, `[ develop, main ]` | no, no | no, no |
| before, Sonnet override, 3 runs | main / Sonnet | 2 of 3 (one asked) | `[ main ]` | yes | yes (6 and 4 matches) |
| after official, 3 runs (S1, S1-b, S1-c) | this tree / Sonnet | no (all asked a question) | n/a | n/a | n/a |
| after, Sonnet, 2 more runs (d2, d3) | this tree / Sonnet | yes | `[ develop, main ]` both | yes | yes |
| after, Haiku override, 2 runs | this tree / Haiku | yes | `[ develop, main ]`, `[ main, main ]` | yes, yes | yes, no |
| after, plugin mode (see below) | this tree via plugins / Sonnet | yes (5th attempt) | `[ develop, main ]` | yes | yes |

Findings:

1. **The templates are byte-equivalent** (Task 21.2: all 14 skills `cmp` OK and re-inlining reproduces the original
   `SKILL.md`). A same-model comparison, before tree on Sonnet (`ts-lib-before-sonnet`) against this tree on Sonnet
   (`ts-lib-run-d2`), differs only where the model made a different choice: the integration branch (`main` vs `develop`,
   rippling into `sync.yml` names and comments), comment wording in `sync_versions.py`, and one early-return guard.
   `security.yml` and `dependabot.yml` match byte for byte apart from that `branches:` line.
2. **Haiku, before tree vs after tree is a real, systematic difference, in favour of the after tree**: all three recorded
   before-Haiku runs wrote a 790-byte `build.yml` with no docs steps and no `sync.yml`/`sync_versions.py` (the skill says a
   library gets them), working from the 2,949-line inlined body; the two after-Haiku runs, reading the 971-line body plus
   the template files, produced the documented set including `sync.yml`. The old output was the degraded one, so the
   original bytes are not a gold standard for fidelity. Differences between the two trees' Haiku outputs, for the record
   (before recorded vs after-Haiku run 1): `branches: [ develop, main ]` vs `[ main ]`; the Antora build and docs artifact
   block (25 lines) present vs absent; `sync.yml` + `.github/scripts/sync_versions.py` present vs absent; no `.gitignore`
   written (the before run wrote a 286-byte `.gitignore` the skill does not specify).
3. **Sonnet sometimes stops to ask instead of writing** (survey says the repo has no scripts, only `main` branch). That is
   model nondeterminism, not an edit: the before tree forced onto Sonnet asked in 1 of 3 runs, this tree in 3 of 5 (in plugin mode 2
   of 5 asked and 2 were blocked on a read permission, below). The skill body that decides this is unchanged (the 2,000-odd lines removed from it were
   templates). Consequence for the table: the official S1 sample is "stopped to ask" on Sonnet; its token numbers describe
   a short survey-only run, not the cost of producing the files.
4. Task 22.2 asks for byte identity of `.github/` against the before output. It is **not** achieved for S1
   and cannot be, because the before output depends on model choices the skill leaves open (and the before Haiku output
   itself varies run to run: three recorded runs gave three different `build.yml` branch lines/sizes). The equivalence that
   can be guaranteed and was verified is the template bytes.

### S2 (`/iru-setup-android-gitignore`)

- Official run on this tree (now genuinely Haiku): 3 of 3 runs (S2, S2-b, S2-c) asked which modules to give a `.gitignore`
  and wrote nothing (the body, unchanged, says to ask when there is no `settings.gradle.kts` and neither `lib/` nor
  `app/`). The before run (Opus, because the broken frontmatter dropped `model: haiku`) wrote the root file first and then
  reported the blocker.
- Controlled run with the skill's `model:` line removed (so the default model, as before): `.gitignore` is **byte
  identical** to the before output (740 bytes, `diff` empty).

### S3 (`/iru-explore`)

Same model (Opus 5), body unchanged (only the description changed). `Project type:` `typescript-library` in both;
`Repository host:` "no remote configured (local git repository, branch `main`, one commit)" in both. `Build & layout:` is
present after and was absent from the before message (model variation: the skill text has it in both trees); the other
`Tech stack` lines (languages, frameworks, user interface, accessibility, Antora docs) match.

## Extra runs (controlled comparisons, same prompts)

| Run | Input | Cache read | Cache creation | Output | Prompt side | Cost (USD) | Duration (ms) | Turns | Model | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| S1-b | 14 | 420,965 | 53,539 | 4,549 | 474,518 | 0.3439 | 56,283 | 7 | Sonnet 5 | asked |
| S1-c | 10 | 292,384 | 59,978 | 5,691 | 352,372 | 0.3553 | 67,008 | 10 | Sonnet 5 | asked |
| S1-d2 | 42 | 1,761,714 | 89,565 | 21,313 | 1,851,321 | 0.9238 | 221,249 | 32 | Sonnet 5 | wrote files |
| S1-d3 | 52 | 2,285,388 | 93,925 | 24,297 | 2,379,365 | 1.0759 | 267,706 | 38 | Sonnet 5 | wrote files |
| S1-haiku (this tree, Haiku) | 209 | 1,538,778 | 59,705 | 12,448 | 1,598,692 | 0.3357 | 132,722 | 26 | Haiku 4.5 | wrote files |
| S1-haiku2 (this tree, Haiku) | 203 | 1,465,120 | 60,509 | 14,037 | 1,525,832 | 0.3379 | 157,863 | 26 | Haiku 4.5 | wrote files |
| S1-before-rerun1 (main, Haiku) | 51 | 389,324 | 67,893 | 4,675 | 457,268 | 0.1981 | 46,045 | 12 | Haiku 4.5 | wrote files |
| S1-before-rerun2 (main, Haiku) | 113 | 1,029,924 | 72,762 | 9,239 | 1,102,799 | 0.2948 | 100,229 | 14 | Haiku 4.5 | wrote files |
| S1-before-sonnet (main, Sonnet) | 38 | 2,066,041 | 108,030 | 22,514 | 2,174,109 | 1.0705 | 254,835 | 19 | Sonnet 5 | wrote files |
| S1-before-sonnet2 (main, Sonnet) | 8 | 316,002 | 85,521 | 5,532 | 401,531 | 0.4606 | 64,305 | 4 | Sonnet 5 | asked |
| S1-before-sonnet3 (main, Sonnet) | 52 | 2,923,416 | 113,583 | 26,836 | 3,037,051 | 1.3075 | 271,871 | 26 | Sonnet 5 | wrote files |
| S2-b | 67 | 228,504 | 20,766 | 2,122 | 249,337 | 0.0751 | 26,615 | 9 | Haiku 4.5 | asked |
| S2-c | 33 | 103,960 | 20,151 | 1,707 | 124,144 | 0.0593 | 19,967 | 7 | Haiku 4.5 | asked |
| S2-default (no `model:` line) | 16 | 269,301 | 29,637 | 5,733 | 298,954 | 0.5744 | 76,007 | 10 | Opus 5 (1M) | wrote `.gitignore`, identical |

Like for like on Haiku the after tree is **more expensive in prompt tokens** (about 1.5 to 1.6 M against 0.46 to 1.10 M
for the before tree), because it now does the full documented job (reads the template and notes files, 26 turns,
12 to 14 k output tokens) where the before run shortcut it. On the same model that means the template move does not make
a faithful S1 run cheaper in total; it makes the **listing** cheaper (S0) and the **body read on every invocation**
smaller (`iru-setup-typescript-github-workflows` 2,949 to 971 lines), and it makes the generated files follow the
templates.

## Plugin mode (Task 22.3)

`claude plugin marketplace add <this repository>`, then `claude plugin install iru-core@ai-catalog --scope local` and
`iru-typescript@ai-catalog --scope local` from a fresh `ts-lib` copy that has **no** `.claude/skills`; S1 prompt
unchanged.

- Resolution: **works.** The slash command resolved to `/iru-typescript:iru-setup-typescript-github-workflows` (the
  transcript shows `Base directory for this skill: <repository>/.claude/skills/iru-setup-typescript-github-workflows`,
  because the marketplace is a directory source; for a GitHub source it would be the plugin cache). `--allowedTools=Skill`
  was **not** required.
- Headless read permission: the skill's `templates/` and `reference/` files sit outside the working directory, and
  `claude -p --permission-mode acceptEdits` refuses to read them (two runs ended with "cannot read the template files",
  even `Bash cat` was refused). Passing the skills directory with `--add-dir <path>` fixed it. In an interactive session
  the same read raises a permission prompt. Anyone running plugin-installed skills headless needs `--add-dir` for the
  plugin directory (or an `allowedTools` Read rule for it).
- Runs: S1-plugin (asked), S1-plugin2 and 3 (blocked on the read permission), S1-plugin4 (asked), S1-plugin5 with `--add-dir`
  (wrote the files): 1,683,444 prompt-side tokens, 18,209 output, 0.8226 USD, 204 s, 34 turns, Sonnet 5.
- Output of S1-plugin5 against the Sonnet run of this tree in directory mode (`d2`): `build.yml`, `security.yml`,
  `sync.yml`, `dependabot.yml` identical byte for byte; `sync_versions.py` differs by a two-line `if not path.exists():
  return` guard. Against `d3` it differs only in two trailing comments and one comment line in the script.
- Each installed plugin cached a copy of the whole working directory (231 MB for the two plugins, including untracked
  directories such as `.ruff_cache`, `.archive` and `tools`), not the 11 MB the spike estimated: a directory-source
  marketplace copies the working tree, a git source copies only tracked files.
- Cleanup: both plugins uninstalled, marketplace removed, `claude plugin list` reports "No plugins installed",
  `claude plugin marketplace list` shows only `claude-plugins-official`, and the `~/.claude/plugins/cache/ai-catalog`
  directory was deleted.

## S4: new behaviour of Group 4 (no before run)

Prompts: `/iru-plan add an isEven(n) helper exported from src/index.ts, with unit tests; acceptance: exported from the
package entry point, 100 % line coverage, documented in README` (S4a) and the same with the last criterion replaced by
`documented somewhere` (S4b); then `/iru-code` on the S4b fixture (S4c). Each on a fresh `ts-lib` copy with this
repository's `.claude/`.

| Run | Input | Cache read | Cache creation | Output | Prompt side | Cost (USD) | Duration (ms) | Turns | Model |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| S4a `/iru-plan` | 10 | 167,076 | 41,114 | 12,018 | 208,200 | 0.7952 | 151,679 | 8 | Opus 5 |
| S4b run 1 (before wording fix) | 12 | 206,190 | 39,308 | 10,876 | 245,510 | 0.7681 | 136,616 | 8 | Opus 5 |
| S4b run 2 (after marker-wording fix) | 8 | 129,266 | 39,340 | 13,171 | 168,614 | 0.7873 | 165,642 | 6 | Opus 5 |
| S4b run 3 (after vague-criterion fix) | 10 | 171,707 | 37,755 | 11,521 | 209,472 | 0.7515 | 141,358 | 9 | Opus 5 |
| S4c `/iru-code` | 12 | 280,074 | 44,051 | 2,149 | 324,137 | 0.2537 | 34,630 | 6 | Sonnet 5 |

- S4a: `## Acceptance criteria coverage` present, all three quoted criteria mapped (plus three derived), `Open
  clarifications: none`; `catalog-audit.py --plan` exit 0.
- S4b run 1: a marker was written, but for a different question (non-integer input) and wrapped in backticks, so
  `--plan` reported 0 violations (inline code is ignored by design). `iru-plan` now says to write the marker as plain text.
  Run 2 resolved "documented somewhere" itself (README plus TSDoc) with no marker. `iru-plan` now also lists an
  unverifiable acceptance criterion as ambiguity. Run 3: `[NEEDS CLARIFICATION: What does "documented somewhere" require
  to be considered met? ...]` written on the task and in `Open clarifications`; `--plan --check` exit 1 with two
  `plan-clarification-open` errors (lines 42 and 131).
- S4c: `/iru-code` read the plan, named the marker, listed the three options and stopped; `src/`, `package.json`,
  `tsconfig.json` and the plan are byte-unchanged (md5 before/after), no implementation. Its first message said it would
  go on with the recommended option "unless you prefer", but the run ended without doing so.

## Audit totals after

From `catalog-audit-after.md` / `.json` (before in `catalog-audit-before.md`):

| Metric | Before | After |
|---|---:|---:|
| Skill description characters | 494,826 | 73,851 |
| Descriptions over 1,536 chars (cut off in the listing) | 167 | 0 |
| Descriptions over 1,024 chars | 189 | 0 |
| Frontmatter parse failures | 39 | 0 |
| `SKILL.md` lines over 500 / over 1,000 | 39 / 11 | 36 / 0 |
| `SKILL.md` bytes | 6,217,277 | 5,303,911 |
| Supporting files / bytes | 302 / 4,290,070 | 524 / 4,851,168 |
| Redundant duplicate bytes | 364,713 | 365,397 (+684, slightly higher) |

The listing estimate is the S0 prompt-side measurement above (42,787 to 30,278). `claude plugin validate
.claude/skills` after: "Validation passed" (`plugin-validate-after.txt`; before it rejected 7 skills).
