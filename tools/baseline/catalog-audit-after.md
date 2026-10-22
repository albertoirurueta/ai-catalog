# Catalog audit

## Totals

| Metric | Value |
|---|---:|
| Skills | 196 |
| Agents | 3 |
| SKILL.md bytes (total) | 5303911 (5179.6 KB) |
| SKILL.md lines (total) | 70353 |
| Bytes inside fenced code blocks (SKILL.md) | 489768 (478.3 KB) |
| Supporting files | 524 |
| Supporting file bytes | 4851168 (4737.5 KB) |
| Redundant bytes in duplicate supporting files | 365397 (356.8 KB) |
| Skill description characters (total) | 73851 |
| Agent description characters (total) | 1459 |
| Descriptions over 1,024 chars (skills + agents) | 0 |
| Descriptions over 1,536 chars (listing cap) | 0 |
| SKILL.md over 500 lines | 36 |
| SKILL.md over 1,000 lines | 0 |
| Frontmatter parse failures (yaml.safe_load) | 0 |
| `Skill()` call sites | 298 |
| `subagent_type` dispatch sites | 294 |
| Missing `Skill()` targets | 0 |
| Inline cross-model `Skill()` calls | 17 (17 accepted) |

## Top 20 skills by size (SKILL.md bytes)

| Skill | Model | SKILL.md bytes | Lines | Fenced bytes | Supporting bytes |
|---|---|---:|---:|---:|---:|
| iru-setup-typescript-github-workflows | sonnet | 84764 | 970 | 1622 | 87919 |
| iru-setup-swift-github-workflows | sonnet | 80834 | 884 | 467 | 66394 |
| iru-setup-android-library | sonnet | 75617 | 923 | 1729 | 35862 |
| iru-setup-android-app | sonnet | 75060 | 963 | 1994 | 34118 |
| iru-setup-readme | sonnet | 73338 | 751 | 0 | 0 |
| iru-setup-java-springboot-github-workflows | sonnet | 71607 | 845 | 2121 | 62181 |
| iru-setup-repository | sonnet | 70289 | 748 | 2180 | 5761 |
| iru-setup-android-github-workflows | sonnet | 65851 | 782 | 527 | 28970 |
| iru-setup-java-springboot-apis | sonnet | 63814 | 791 | 994 | 31156 |
| iru-setup-java-springboot | sonnet | 62125 | 788 | 2872 | 25307 |
| iru-setup-java-springboot-pom | sonnet | 58984 | 764 | 3078 | 58627 |
| iru-setup-swift-repository | sonnet | 56687 | 665 | 5748 | 0 |
| iru-setup-swift-library | sonnet | 54286 | 671 | 1084 | 5914 |
| iru-explore | opus | 53505 | 609 | 2981 | 5761 |
| iru-setup-react-native-app | sonnet | 51706 | 618 | 1062 | 49065 |
| iru-setup-typescript-repository | sonnet | 50358 | 614 | 2833 | 0 |
| iru-setup-apple-app | sonnet | 49143 | 543 | 2492 | 78589 |
| iru-setup-java-springboot-modules | sonnet | 47947 | 728 | 9408 | 0 |
| iru-setup-python-github-workflows | sonnet | 47252 | 546 | 494 | 40234 |
| iru-setup-python-django | sonnet | 47238 | 576 | 3000 | 78196 |

## Top 20 descriptions by length

| Skill | Model | Description chars | Invocation form at | Parses |
|---|---|---:|---:|---|
| iru-plan | opus | 780 | 0 | yes |
| iru-knowledge-to-jira | sonnet | 721 | 0 | yes |
| iru-springboot-rolling-deployments | sonnet | 705 | 0 | yes |
| iru-setup-repository | sonnet | 694 | 0 | yes |
| iru-setup-swift-repository | sonnet | 684 | 0 | yes |
| iru-release | sonnet | 663 | 0 | yes |
| iru-knowledge-to-issue | sonnet | 660 | 0 | yes |
| iru-setup-macos-repository | sonnet | 647 | 0 | yes |
| iru-setup-windows-repository | sonnet | 646 | 0 | yes |
| iru-setup-quarkus-repository | sonnet | 632 | 0 | yes |
| iru-update-java-springboot-documentation | sonnet | 631 | 0 | yes |
| iru-review-github-issue | sonnet | 628 | 0 | yes |
| iru-setup-typescript-repository | sonnet | 620 | 0 | yes |
| iru-pr-description | sonnet | 614 | 0 | yes |
| iru-setup-java-springboot | sonnet | 607 | 0 | yes |
| iru-setup-python-repository | sonnet | 606 | 0 | yes |
| iru-setup-php-repository | sonnet | 604 | 0 | yes |
| iru-update-docs | sonnet | 597 | 0 | yes |
| iru-split-github-issue | sonnet | 587 | 0 | yes |
| iru-setup-kmp-repository | sonnet | 583 | 0 | yes |

## Models

| Model | Skills | Agents |
|---|---:|---:|
| haiku | 58 | 2 |
| inherit | 0 | 1 |
| opus | 3 | 0 |
| sonnet | 135 | 0 |

## Agents

| Agent | Model | Description chars | Bytes | Skill() calls | Dispatches |
|---|---|---:|---:|---:|---:|
| iru-change-summarizer | haiku | 485 | 3037 | 0 | 1 |
| iru-gate-runner | haiku | 432 | 10475 | 1 | 1 |
| iru-isolated-skill-executor | inherit | 542 | 3397 | 1 | 1 |

## Agent dispatch sites

| subagent_type | Sites |
|---|---:|
| <agent-name> | 4 |
| iru-change-summarizer | 3 |
| iru-gate-runner | 185 |
| iru-isolated-skill-executor | 102 |

## Duplicate supporting files (by SHA-256)

9 duplicate groups, 356.8 KB redundant.

| File name | Copies | Bytes each | Redundant bytes |
|---|---:|---:|---:|
| ui-contract.md | 12 | 22206 | 244266 |
| ui-screenshots.ts | 7 | 10487 | 62922 |
| cli-contract.md | 4 | 12044 | 36132 |
| ui-docs.md | 3 | 7816 | 15632 |
| accessibility-detection.md | 2 | 5761 | 5761 |
| .ui-quality.yml | 2 | 384 | 384 |
| gradle-wrapper.properties | 2 | 264 | 264 |
| robolectric.properties | 2 | 22 | 22 |
| .gitignore | 3 | 7 | 14 |

### Shared byte-identical files

| File | Copies | Distinct md5 | Status |
|---|---:|---:|---|
| accessibility-detection.md | 2 | 1 | identical |
| cli-contract.md | 4 | 1 | identical |
| ui-contract.md | 12 | 1 | identical |
| ui-docs.md | 3 | 1 | identical |

## Inline cross-model `Skill()` calls

17 calls where caller and callee `model` differ and the call is not inside an `Agent({...})` prompt (17 recorded as accepted under `accepted_cross_model_calls` in the budgets file).

| Caller | Caller model | Callee | Callee model | Line | Near agent mention | Decision |
|---|---|---|---|---:|---|---|
| iru-android-generate-all-tests | sonnet | iru-android-test | haiku | 183 | yes | accepted: Already delegated: the Skill() call is the prompt of the iru-gate-runner dispatch described in the surrounding prose, so the callee does not run in the caller's context (audit false positive). |
| iru-create-github-issue | sonnet | iru-explore | opus | 31 | no | accepted: Intentional direct call: iru-explore is opus by the model-tier policy and its report (Project type, Tech stack, docs location) must land in the caller's own context; routing it through an agent would return only a summary and change what the caller can use. |
| iru-create-jira-ticket | sonnet | iru-explore | opus | 35 | no | accepted: Intentional direct call: iru-explore is opus by the model-tier policy and its report (Project type, Tech stack, docs location) must land in the caller's own context; routing it through an agent would return only a summary and change what the caller can use. |
| iru-database-code-one-task | sonnet | iru-explore | opus | 19 | no | accepted: Intentional direct call: iru-explore is opus by the model-tier policy and its report (Project type, Tech stack, docs location) must land in the caller's own context; routing it through an agent would return only a summary and change what the caller can use. |
| iru-database-code-one-task | sonnet | iru-explore | opus | 20 | no | accepted: Intentional direct call: iru-explore is opus by the model-tier policy and its report (Project type, Tech stack, docs location) must land in the caller's own context; routing it through an agent would return only a summary and change what the caller can use. |
| iru-dotnet-generate-all-tests | sonnet | iru-dotnet-test | haiku | 169 | yes | accepted: Already delegated: the Skill() call is the prompt of the iru-gate-runner dispatch described in the surrounding prose, so the callee does not run in the caller's context (audit false positive). |
| iru-draft-github-issue | sonnet | iru-explore | opus | 29 | no | accepted: Intentional direct call: iru-explore is opus by the model-tier policy and its report (Project type, Tech stack, docs location) must land in the caller's own context; routing it through an agent would return only a summary and change what the caller can use. |
| iru-issue | sonnet | iru-explore | opus | 193 | no | accepted: Intentional direct call: iru-explore is opus by the model-tier policy and its report (Project type, Tech stack, docs location) must land in the caller's own context; routing it through an agent would return only a summary and change what the caller can use. |
| iru-issue | sonnet | iru-plan | opus | 194 | no | accepted: Intentional direct call: iru-plan is opus by policy and interactive (AskUserQuestion, plan review with the user); it must run in the orchestrator's conversation, not in an isolated agent. |
| iru-issue | sonnet | iru-pr-review | opus | 372 | no | accepted: Intentional direct call: iru-pr-review is opus by policy and asks the user to confirm before posting comments; it must run in the orchestrator's conversation, not in an isolated agent. |
| iru-kmp-generate-all-tests | sonnet | iru-kmp-test | haiku | 160 | yes | accepted: Already delegated: the Skill() call is the prompt of the iru-gate-runner dispatch described in the surrounding prose, so the callee does not run in the caller's context (audit false positive). |
| iru-knowledge-compact | sonnet | iru-knowledge-complete | haiku | 140 | no | accepted: Intentional direct call: iru-knowledge-complete is a single-purpose haiku file operation (delete a pending file, check off one item) whose stop-on-inconsistency message the caller must read; an agent per task would add a context for a few file edits. |
| iru-knowledge-to-issue | sonnet | iru-explore | opus | 90 | no | accepted: Intentional direct call: iru-explore is opus by the model-tier policy and its report (Project type, Tech stack, docs location) must land in the caller's own context; routing it through an agent would return only a summary and change what the caller can use. |
| iru-knowledge-to-jira | sonnet | iru-explore | opus | 93 | no | accepted: Intentional direct call: iru-explore is opus by the model-tier policy and its report (Project type, Tech stack, docs location) must land in the caller's own context; routing it through an agent would return only a summary and change what the caller can use. |
| iru-setup-readme | sonnet | iru-explore | opus | 95 | no | accepted: Intentional direct call: iru-explore is opus by the model-tier policy and its report (Project type, Tech stack, docs location) must land in the caller's own context; routing it through an agent would return only a summary and change what the caller can use. |
| iru-setup-repository | sonnet | iru-explore | opus | 86 | no | accepted: Intentional direct call: iru-explore is opus by the model-tier policy and its report (Project type, Tech stack, docs location) must land in the caller's own context; routing it through an agent would return only a summary and change what the caller can use. |
| iru-swift-generate-all-tests | sonnet | iru-swift-test | haiku | 245 | yes | accepted: Already delegated: the Skill() call is the prompt of the iru-gate-runner dispatch described in the surrounding prose, so the callee does not run in the caller's context (audit false positive). |

`Near agent mention = yes` means the 250 characters before the call name `iru-gate-runner` or `iru-isolated-skill-executor` in prose: likely already delegated, review by hand.

## Missing `Skill()` targets

0 missing.

Calls to skills outside this catalog (listed as `external_skills` in the budgets file, not counted as missing): `code-review` (1).

## Frontmatter parse failures (`yaml.safe_load`)

0 files.
