# Sample runs: before

Baseline sample runs of the **original** tree (`git archive main`, exported to `$TMPDIR/iru-verify/before/`) for the
before/after comparison of issue #11. Claude Code 2.1.260, 2026-10-20, macOS. Raw JSON and produced files live under
`$TMPDIR/iru-verify/results/before/` (outside this repository).

**Status: run (S0 to S3).** Run with `claude -p --output-format json --permission-mode acceptEdits`, from a clean
environment (`env -i` with only `HOME`, `PATH`, `TMPDIR`, so no nested-session variables such as `CLAUDECODE` or
`CLAUDE_CODE_SIMPLE` leak in), 1500 s alarm, stdin from `/dev/null`. Default model of the account (Opus 5; the skills
that declare `model: haiku` ran their work on Haiku 4.5, see "Model" below).

| Sample | Prompt / skill | Fixture | Input tokens | Cache read | Cache creation | Output tokens | Cost (USD) | Duration (ms) | Turns | Status |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| S0 listing cost | `Reply with the single word OK` | none (exported tree) | 2 | 10,130 | 32,655 | 4 | 0.3327 | 5,063 | 1 | run |
| S1 | `/iru-setup-typescript-github-workflows` with `flavor: library`, `ci-tests: unit`, `pages: no`, `sonar: none`, `visibility: private`, `on-existing: replace` | `ts-lib` | 121 | 1,078,046 | 80,736 | 5,977 | 0.2993 | 69,044 | 15 | run, no permission denials |
| S2 | `/iru-setup-android-gitignore` | `android-lib` | 16 | 274,248 | 29,682 | 3,786 | 0.5287 | 58,147 | 9 | run, 4 Bash `git check-ignore`/`ls` calls denied by `acceptEdits` (verification step only; `.gitignore` was written) |
| S3 | `/iru-explore` | `ts-lib` | 10 | 215,819 | 43,935 | 3,835 | 0.6432 | 59,620 | 13 | run, 2 Bash `git remote` calls denied by `acceptEdits`; no `AskUserQuestion` tool in `-p` mode so no ticket was asked for |

Prompt-side tokens of a run = `input_tokens + cache_read_input_tokens + cache_creation_input_tokens`. For S0 that is
**42,787** tokens, i.e. the fixed system prompt + tool schemas + the skill listing of the 196-skill tree plus whatever
the account's own user-level skills/plugins add (about 10 k of it was already a cache read from the account's other
sessions). It is the number the "after" S0 must be compared with; the absolute value includes the account overhead, the
delta does not.

Cost is not comparable across samples (different models, caching), only before vs. after of the same sample.

## Produced files (kept for the byte comparison)

`$TMPDIR/iru-verify/results/before/`:

- `S0.json`, `S1.json`, `S2.json`, `S3.json` (full `claude -p` JSON), `*.err` (stderr, only the stdin warning).
- `produced/S1/.github/` (`workflows/build.yml`, `workflows/security.yml`, `dependabot.yml`) and `produced/S1/.gitignore`
  (286 bytes) from the TypeScript library run.
- `produced/S2/.gitignore` (740 bytes) from the Android library run.
- `produced/S3-final-message.md`: the final message of `/iru-explore`; its **Tech stack** block was:
  languages TypeScript; frameworks none; Project type `typescript-library`; User interface none; Accessibility not
  applicable (`.ui-quality.yml` missing); Antora docs none; repository host none (local git, no remote).
- `produced/S1-final-message.md`, `produced/S2-final-message.md`.
- `ts-lib-run/`, `ts-lib-run-explore/`, `android-lib-run/`: the working copies (fixture + the unmodified `.claude/` of
  `main`).

## Approach

Each of S1 to S3 ran in a fresh copy of the fixture into which `$TMPDIR/iru-verify/before/.claude` had been copied, so
the unmodified skills of `main` were the ones loaded for that cwd and the skill acts on the fixture itself. S0 ran from
`$TMPDIR/iru-verify/before` itself. Nothing was run inside this repository. The three runs executed concurrently.

## Caveats

- LLM output is not deterministic: compare produced files with a tolerance for wording, but the generated YAML/gitignore
  structure should match. Re-run twice before concluding a difference is caused by an optimization.
- `--permission-mode acceptEdits` denies some Bash commands (S2, S3), which changes the number of turns slightly; the
  "after" runs must use exactly the same flags so the comparison stays fair.
- Model: S1 reported only Haiku 4.5 usage (the workflows skill declares `model: haiku`), S2 only the 1M-context Opus 5
  variant, S3 plain Opus 5, S0 mostly Opus 5 plus a small Haiku call. The token fields in the JSON are those of the main
  model; use `modelUsage` in the saved JSON for the per-model split.

## Re-running

```bash
V="${TMPDIR:-/tmp}/iru-verify"
# run.sh: cd <cwd>; perl -e 'alarm 1500; exec @ARGV' env -i HOME PATH TMPDIR USER SHELL LANG \
#   claude -p --output-format json --permission-mode acceptEdits "$@" > <out> 2> <out>.err < /dev/null
"$V/run.sh" "$V/before" "$V/results/before/S0.json" "Reply with the single word OK"
# S1/S2/S3: cp -R the fixture to a fresh dir, cp -R "$V/before/.claude" into it, then run the same prompts as in the table.
```

Fields to copy from each JSON: `usage.input_tokens`, `usage.cache_read_input_tokens`,
`usage.cache_creation_input_tokens`, `usage.output_tokens`, `total_cost_usd`, `duration_ms`.
