# Plugin-mode resolution spike

Throwaway experiment (issue #11, Task 2) run outside the repository, in `$TMPDIR/iru-verify/plugins/`. Question: when the
catalog is installed as plugins instead of copied into `.claude/skills/`, do the cross-references the skills rely on
still resolve?

- Claude Code version: **2.1.260**
- Date: 2026-10-20 (macOS, Darwin)
- Scope of evidence: manifest validation, install and **all four runtime questions (a) to (d)** were run for real with
  an authenticated `claude -p` (an earlier attempt failed with "OAuth session expired"; the CLI has since been signed
  in again and the runtime checks were re-run from the commands at the end of this file).

## Summary of answers

| # | Question | Outcome |
|---|---|---|
| (a) | `Skill({skill: "iru-java-test"})` by bare name | **Resolves.** The bare name and the namespaced `spike-java:iru-java-test` both loaded the skill; the tool result reports the canonical name `spike-java:iru-java-test`. |
| (b) | `Agent({subagent_type: "iru-gate-runner"})` by bare name | **Does not resolve.** Error: `Agent type 'iru-gate-runner' not found. Available agents: claude, Explore, general-purpose, Plan, spike-core:iru-gate-runner, statusline-setup`. `spike-core:iru-gate-runner` works. **Task 19 must use the namespaced `<plugin>:iru-gate-runner` form in plugin mode.** |
| (c) | `find .claude/skills` finds nothing in plugin mode | **Confirmed at runtime**: `bfs: error: .claude/skills: No such file or directory`; skills come from the plugins. |
| (d) | `${CLAUDE_PLUGIN_ROOT}` substituted in a skill body | **Yes**, and `${CLAUDE_SKILL_DIR}` too (see the value caveat below). |
| - | Do `agents` listed on a root-source marketplace entry load? | **Yes**, they load at runtime. `claude plugin details` shows `Agents (0)` for them, but that is a display limitation of the inventory, not of loading: inside the run the agent type `spike-core:iru-gate-runner` was available and executed. So no physical `agents/` directory is needed. |

## Spike marketplace (what was built and validated)

`$TMPDIR/iru-verify/plugins/spike/` (files copied, not linked):

```
.claude-plugin/marketplace.json      name spike-marketplace, plugins below
.claude/agents/iru-gate-runner.md
.claude/skills/{iru-java-test,iru-java-code-quality,iru-check-license,iru-code-one-task-group,spike-probe}/
```

`spike-probe` is a throwaway skill whose body contains `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_SKILL_DIR}` for question (d).

Plugin entries, using the layout Group 4 plans (`source: "./"`, `strict: false`, `skills` listing subdirectories):

| Plugin | Contents | Notes |
|---|---|---|
| `spike-core` | skills `iru-check-license`, `spike-probe`; `agents: ["./.claude/agents/iru-gate-runner.md"]` | |
| `spike-java` | skills `iru-java-test`, `iru-java-code-quality`, `iru-code-one-task-group` | `dependencies: ["spike-core"]` |
| `spike-alt` (control) | `source: "./alt"` with default `agents/` and `skills/` directories | agent loading control |
| `spike-agent2`, `spike-agent3` (variants) | root source, `agents` pointing to `./.claude/agents/...` / `./alt/agents/...` | agent loading probes |

### Commands run and results

| Command | Result |
|---|---|
| `claude plugin validate . --strict` (spike root) | Passes. Without `description` on the marketplace it passes with one warning (no marketplace description); add `description` to avoid it. |
| `claude plugin marketplace add <spike dir>` | OK (user scope). |
| `claude plugin install spike-core@spike-marketplace --scope local` (and `spike-java`, run from the throwaway Maven project) | OK. `spike-java`'s `dependencies: ["spike-core"]` accepted. |
| `claude plugin details spike-java@spike-marketplace` | Skills (3): `iru-code-one-task-group`, `iru-java-code-quality`, `iru-java-test`; always-on ~1,061 tok. Root-source `skills` lists load exactly the listed subdirectories. |
| `claude plugin details spike-core@spike-marketplace` | Skills (2): `iru-check-license`, `spike-probe`; **Agents (0)**; always-on ~193 tok. |
| `claude plugin details spike-alt@...` (default `agents/` layout) | Skills (1), **Agents (1)**: `iru-gate-runner`. |
| `claude plugin details spike-agent2@...` / `spike-agent3@...` | **Agents (0)** again, with `.claude/agents/...` and `alt/agents/...` paths. |
| cleanup: `claude plugin uninstall <each> --scope local`, `claude plugin marketplace remove spike-marketplace` | Done; `claude plugin list` empty, only the official marketplace remains. An empty `~/.claude/plugins/cache/spike-marketplace/` directory is left behind. |

### Findings that do not need a model

1. **A marketplace entry's `agents` list was not reflected in the plugin inventory when `source` is the marketplace
   root** (`spike-core`, `spike-agent2`, `spike-agent3` all show Agents (0)), while the same agent file in a plugin
   with a default `agents/` directory shows Agents (1). `claude plugin details` does not count entry-level agents. `claude plugin validate` accepts the manifest either way. This matters for Group 5:
   if agents do not load from a root-source entry, `iru-gate-runner` (and the other two agents) would silently be
   missing in plugin mode. **Resolved by the runtime check: the agent does load** (it is available as `spike-core:iru-gate-runner`), so the
   inventory count is only a display limitation and the "no files move" decision stands.
2. **Each installed plugin caches a full copy of the marketplace repository** (`~/.claude/plugins/cache/<marketplace>/<plugin>/unknown/`
   held every `.claude/skills/*` directory of the spike, not only the listed ones, for `spike-core`, `spike-java`,
   `spike-agent2`, `spike-agent3`), confirming the "~11 MB per installed plugin" trade-off in the plan. The plugin
   `version` shows as `unknown` because no version was set.

## Runtime results (authenticated runs)

Project: `$TMPDIR/iru-verify/fixtures/maven-spike` (minimal `pom.xml`, `Calc`, `CalcTest`), `spike-core` and
`spike-java` installed with `--scope local`. Every run: `claude -p --output-format json --permission-mode acceptEdits`
from a clean environment. Saved JSON in `$TMPDIR/iru-verify/plugins/results/`.

| Probe (prompt gist) | Result |
|---|---|
| (a) `Skill("iru-java-test")` | First attempt returned `Execute skill: iru-java-test` with a `permission_denials` entry: this is `-p` mode refusing the Skill call because the skill declares `allowed-tools`, **not** a resolution failure. Re-run with `--allowedTools=Skill`: resolved, `Launching skill: spike-java:iru-java-test`, body heading `# Java Test`. `spike-java:iru-java-test` and `spike-core:iru-check-license` also resolved. |
| (b) `Agent("iru-gate-runner")`, then `Agent("spike-core:iru-gate-runner")` | Bare: `Agent type 'iru-gate-runner' not found. Available agents: claude, Explore, general-purpose, Plan, spike-core:iru-gate-runner, statusline-setup`. Namespaced: ran and answered `OK` (0 tool uses). |
| (b') list available subagent types and skills | Agents: `claude`, `Explore`, `general-purpose`, `Plan`, `spike-core:iru-gate-runner`, `statusline-setup`. Skills: `spike-core:iru-check-license`, `spike-core:spike-probe`, `spike-java:iru-java-test`, `spike-java:iru-java-code-quality`, `spike-java:iru-code-one-task-group`, plus built-ins. So the listing shows plugin skills namespaced, and a bare skill name is still accepted by the `Skill` tool; agents are listed namespaced only and a bare agent name is not accepted. |
| (c) `find .claude/skills -maxdepth 1 -type d` in the project | `bfs: error: .claude/skills: No such file or directory` (the shell here has `bfs` as `find`); the model also noted the skills come from the plugins. |
| (d) `Skill("spike-probe")` printing the two variables | `The plugin root variable is: $TMPDIR/iru-verify/plugins/spike` and `The skill directory variable is: $TMPDIR/iru-verify/plugins/spike/.claude/skills/spike-probe`. Both substituted. |

Caveat on (d): because the spike marketplace was added from a **local directory**, the plugin root resolved to that
source directory rather than to the cache copy under `~/.claude/plugins/cache/`. For a marketplace added from GitHub
the root is the cached checkout; the substitution itself (not the path) is what the design relies on. Both variables
are absolute paths, so a skill can reference its sibling `reference/` files either way.

Consequences for the plan:

- Skill cross-references by bare name (`Skill({skill: "iru-java-test"})`) keep working in plugin mode; no rewrite needed
  for those. (If two installed plugins ever expose the same bare name the tool may pick either, so keep the `iru-`
  prefix.)
- Agent references by bare name (`subagent_type: "iru-gate-runner"`) **break** in plugin mode; Task 19 has to use
  `<plugin>:iru-gate-runner` (the plugin that ships the agent, `spike-core` in the spike) or detect the form at runtime.
- The five `find .claude/skills` discovery sites fail in plugin mode (c), so they need a fallback (e.g. read the
  available-skills listing / try the `Skill` tool) as planned.
- Agents declared on a root-source entry load; the `Agents (0)` in `claude plugin details` must not be used as a
  verification signal for them.
- `-p` mode needs `--allowedTools` for skills that declare `allowed-tools` (Skill call is denied otherwise); this only
  matters for headless sample runs (Task 3 after-runs).

## Decision taken in Task 19

Because a bare `subagent_type: "iru-gate-runner"` does not resolve in plugin mode (question (b)), the "bare name works, no
edits" branch (Task 19.1) is not taken. Task 19.2 applies instead: each of the three agents carries the first body line
"Dispatch as `subagent_type: "<agent-name>"` when installed under `.claude/agents/`, or `"iru-core:<agent-name>"` when
installed as a plugin", and the same rule is stated once in `iru-code`, `iru-code-one-task-group`, `iru-issue` and
`iru-setup-changelog` (the callers that explain dispatch) rather than rewriting the ~235 call sites. The three agents ship
in the `iru-core` plugin, which is why the namespace is always `iru-core:`.

## Re-running the runtime checks

```bash
V="${TMPDIR:-/tmp}/iru-verify"; S="$V/plugins/spike"; M="$V/fixtures/maven-spike"
claude plugin marketplace add "$S"
cd "$M"
claude plugin install spike-core@spike-marketplace --scope local
claude plugin install spike-java@spike-marketplace --scope local
P='claude -p --output-format json --permission-mode acceptEdits'
$P --allowedTools=Skill 'Call the Skill tool once with skill "iru-java-test" (bare name) and report whether it resolved or the exact error. Do not run Maven.'   # (a)
$P 'Call the Agent tool with subagent_type "iru-gate-runner" and prompt "reply OK". If it errors, retry with subagent_type "spike-core:iru-gate-runner". Report both outcomes with exact error text.'   # (b)
$P 'Run: find .claude/skills -maxdepth 1 -type d. Report the output.'                                            # (c)
$P 'Call the Skill tool once with skill "spike-probe" and report the two variable lines exactly as received.'     # (d)
$P 'List every subagent_type and skill name available to you, exactly as written. Do not call them.'              # (b')

claude plugin uninstall spike-java@spike-marketplace --scope local
claude plugin uninstall spike-core@spike-marketplace --scope local
claude plugin marketplace remove spike-marketplace
```

After cleanup `claude plugin marketplace list` shows only `claude-plugins-official` and `claude plugin list` shows no
plugins. `~/.claude/plugins/cache/spike-marketplace/` keeps orphaned (`.orphaned_at`) copies of the spike plugins
(about 420 KB) that Claude Code garbage-collects on its own.
