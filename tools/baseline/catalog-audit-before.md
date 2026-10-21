# Catalog audit

## Totals

| Metric | Value |
|---|---:|
| Skills | 196 |
| Agents | 3 |
| SKILL.md bytes (total) | 6217277 (6071.6 KB) |
| SKILL.md lines (total) | 86433 |
| Bytes inside fenced code blocks (SKILL.md) | 997720 (974.3 KB) |
| Supporting files | 302 |
| Supporting file bytes | 4290070 (4189.5 KB) |
| Redundant bytes in duplicate supporting files | 364713 (356.2 KB) |
| Skill description characters (total) | 494826 |
| Agent description characters (total) | 5092 |
| Descriptions over 1,024 chars (skills + agents) | 189 |
| Descriptions over 1,536 chars (listing cap) | 167 |
| SKILL.md over 500 lines | 39 |
| SKILL.md over 1,000 lines | 11 |
| Frontmatter parse failures (yaml.safe_load) | 39 |
| `Skill()` call sites | 298 |
| `subagent_type` dispatch sites | 287 |
| Missing `Skill()` targets | 0 |
| Inline cross-model `Skill()` calls | 21 |

## Top 20 skills by size (SKILL.md bytes)

| Skill | Model | SKILL.md bytes | Lines | Fenced bytes | Supporting bytes |
|---|---|---:|---:|---:|---:|
| iru-setup-typescript-github-workflows | haiku | 173077 | 3011 | 63641 | 0 |
| iru-setup-swift-github-workflows | haiku | 149187 | 2439 | 60388 | 0 |
| iru-setup-java-springboot-github-workflows | sonnet | 133334 | 2378 | 64302 | 0 |
| iru-setup-java-springboot-pom | sonnet | 113273 | 2270 | 61705 | 0 |
| iru-setup-android-library | haiku | 108449 | 1809 | 37591 | 0 |
| iru-setup-android-app | haiku | 105435 | 1805 | 36112 | 0 |
| iru-setup-android-github-workflows | haiku | 94974 | 1511 | 29497 | 0 |
| iru-setup-java-springboot | sonnet | 91575 | 1195 | 7695 | 0 |
| iru-setup-java-springboot-apis | sonnet | 89787 | 1488 | 32150 | 0 |
| iru-setup-python-github-workflows | sonnet | 88681 | 1600 | 40728 | 0 |
| iru-setup-php-github-workflows | sonnet | 78633 | 1640 | 46651 | 0 |
| iru-setup-readme | sonnet | 76694 | 785 | 0 | 0 |
| iru-setup-repository | sonnet | 74012 | 790 | 2180 | 5761 |
| iru-setup-swift-library | haiku | 60266 | 875 | 6998 | 0 |
| iru-setup-swift-repository | haiku | 58944 | 694 | 5748 | 0 |
| iru-setup-java-github-workflows | haiku | 58176 | 978 | 16718 | 0 |
| iru-explore | opus | 56417 | 610 | 2981 | 5761 |
| iru-setup-react-native-app | haiku | 56316 | 663 | 1062 | 49065 |
| iru-setup-typescript-repository | haiku | 53265 | 647 | 2833 | 0 |
| iru-setup-apple-app | haiku | 52414 | 575 | 2492 | 78589 |

## Top 20 descriptions by length

| Skill | Model | Description chars | Invocation form at | Parses |
|---|---|---:|---:|---|
| iru-setup-typescript-github-workflows | haiku | 6558 | 3831 | yes |
| iru-swift-code-one-task | sonnet | 6079 | 5728 | NO |
| iru-setup-java-springboot-github-workflows | sonnet | 5574 | 3965 | yes |
| iru-setup-java-springboot | sonnet | 5527 | 3992 | yes |
| iru-setup-swift-github-workflows | haiku | 5385 | 2346 | NO |
| iru-setup-react-native-app | haiku | 4862 | 2946 | yes |
| iru-setup-android-app | haiku | 4385 | 1530 | NO |
| iru-setup-python-github-workflows | sonnet | 4326 | 3086 | yes |
| iru-setup-repository | sonnet | 4320 | 69 | yes |
| iru-setup-android-library | haiku | 4291 | 1975 | NO |
| iru-setup-cli-github-workflows | sonnet | 4132 | 2792 | yes |
| iru-setup-java-springboot-pom | sonnet | 4108 | 3621 | yes |
| iru-setup-dotnet-cli | sonnet | 4082 | 2642 | yes |
| iru-setup-php-github-workflows | sonnet | 4039 | 2999 | yes |
| iru-setup-windows-app | sonnet | 3946 | 2302 | yes |
| iru-react-native-code-one-task-group | sonnet | 3903 | 3514 | yes |
| iru-setup-rust-cli | sonnet | 3900 | 2621 | yes |
| iru-kmp-code-one-task | sonnet | 3858 | 3569 | yes |
| iru-setup-kmp-app | sonnet | 3810 | 2336 | yes |
| iru-setup-java-springboot-hilla | haiku | 3793 | 2434 | yes |

## Models

| Model | Skills | Agents |
|---|---:|---:|
| (none) | 0 | 3 |
| haiku | 85 | 0 |
| opus | 3 | 0 |
| sonnet | 108 | 0 |

## Agents

| Agent | Model | Description chars | Bytes | Skill() calls | Dispatches |
|---|---|---:|---:|---:|---:|
| iru-change-summarizer | (none) | 485 | 2505 | 0 | 0 |
| iru-gate-runner | (none) | 4065 | 9690 | 1 | 0 |
| iru-isolated-skill-executor | (none) | 542 | 2808 | 1 | 0 |

## Agent dispatch sites

| subagent_type | Sites |
|---|---:|
| iru-change-summarizer | 2 |
| iru-gate-runner | 184 |
| iru-isolated-skill-executor | 101 |

## Duplicate supporting files (by SHA-256)

5 duplicate groups, 356.2 KB redundant.

| File name | Copies | Bytes each | Redundant bytes |
|---|---:|---:|---:|
| ui-contract.md | 12 | 22206 | 244266 |
| ui-screenshots.ts | 7 | 10487 | 62922 |
| cli-contract.md | 4 | 12044 | 36132 |
| ui-docs.md | 3 | 7816 | 15632 |
| accessibility-detection.md | 2 | 5761 | 5761 |

### Shared byte-identical files

| File | Copies | Distinct md5 | Status |
|---|---:|---:|---|
| accessibility-detection.md | 2 | 1 | identical |
| cli-contract.md | 4 | 1 | identical |
| ui-contract.md | 12 | 1 | identical |
| ui-docs.md | 3 | 1 | identical |

## Inline cross-model `Skill()` calls

21 calls where caller and callee `model` differ and the call is not inside an `Agent({...})` prompt.

| Caller | Caller model | Callee | Callee model | Line | Near agent mention |
|---|---|---|---|---:|---|
| iru-android-generate-all-tests | sonnet | iru-android-test | haiku | 183 | yes |
| iru-create-github-issue | sonnet | iru-explore | opus | 28 | no |
| iru-create-jira-ticket | sonnet | iru-explore | opus | 32 | no |
| iru-database-code-one-task | sonnet | iru-explore | opus | 19 | no |
| iru-database-code-one-task | sonnet | iru-explore | opus | 20 | no |
| iru-dotnet-generate-all-tests | sonnet | iru-dotnet-test | haiku | 168 | yes |
| iru-draft-github-issue | sonnet | iru-explore | opus | 26 | no |
| iru-issue | sonnet | iru-explore | opus | 191 | no |
| iru-issue | sonnet | iru-plan | opus | 192 | no |
| iru-issue | sonnet | iru-pr-review | opus | 360 | no |
| iru-kmp-generate-all-tests | sonnet | iru-kmp-test | haiku | 181 | yes |
| iru-knowledge-compact | sonnet | iru-knowledge-complete | haiku | 152 | no |
| iru-knowledge-to-issue | sonnet | iru-explore | opus | 108 | no |
| iru-knowledge-to-jira | sonnet | iru-explore | opus | 112 | no |
| iru-setup-cli-repository | haiku | iru-setup-rust-cli | sonnet | 52 | yes |
| iru-setup-kmp-repository | haiku | iru-setup-kmp-app | sonnet | 45 | yes |
| iru-setup-macos-repository | haiku | iru-setup-macos-app | sonnet | 50 | yes |
| iru-setup-readme | sonnet | iru-explore | opus | 129 | no |
| iru-setup-repository | sonnet | iru-explore | opus | 128 | no |
| iru-setup-windows-repository | haiku | iru-setup-windows-app | sonnet | 48 | yes |
| iru-swift-generate-all-tests | sonnet | iru-swift-test | haiku | 245 | yes |

`Near agent mention = yes` means the 250 characters before the call name `iru-gate-runner` or `iru-isolated-skill-executor` in prose: likely already delegated, review by hand.

## Missing `Skill()` targets

0 missing.

Calls to skills outside this catalog (listed as `external_skills` in the budgets file, not counted as missing): `code-review` (1).

## Frontmatter parse failures (`yaml.safe_load`)

39 files.

| Name | Kind | Error |
|---|---|---|
| iru-android-code-one-task | skill | mapping values are not allowed here in "<unicode string>", line 2, column 501: ... l Kotlin/Android code agreements: Kot |
| iru-android-code-one-task-group | skill | mapping values are not allowed here in "<unicode string>", line 2, column 347: ... validates the entire bucket once: lic |
| iru-android-test | skill | mapping values are not allowed here in "<unicode string>", line 2, column 855: ... d from the selector. Report-only: par |
| iru-create-jira-ticket | skill | mapping values are not allowed here in "<unicode string>", line 2, column 700: ... y attached to the created ticket: onc |
| iru-dotnet-code-one-task | skill | mapping values are not allowed here in "<unicode string>", line 2, column 1967: ... act.md` (the shared CLI contract: st |
| iru-java-code-one-task | skill | mapping values are not allowed here in "<unicode string>", line 2, column 254: ... g's general Java code agreements: `va |
| iru-java-code-one-task-group | skill | mapping values are not allowed here in "<unicode string>", line 2, column 334: ... validates the entire bucket once: lic |
| iru-java-springboot-code-one-task | skill | mapping values are not allowed here in "<unicode string>", line 2, column 717: ... d this catalog's Java code style: rec |
| iru-java-springboot-code-one-task-group | skill | mapping values are not allowed here in "<unicode string>", line 2, column 464: ... s `iru-java-code-one-task-group`: lic |
| iru-java-springboot-performance-tests | skill | mapping values are not allowed here in "<unicode string>", line 2, column 326: ... lan plus three scenario profiles: a l |
| iru-jira-custom-context | skill | mapping values are not allowed here in "<unicode string>", line 2, column 742: ... ication. Invoke as `Skill({skill: "ir |
| iru-knowledge-process-inbox | skill | mapping values are not allowed here in "<unicode string>", line 3, column 107: ... st of the `knowledge/` structure: a ^ |
| iru-review-github-issue | skill | mapping values are not allowed here in "<unicode string>", line 2, column 412: ... ainder the body); optional `kind: fun |
| iru-setup-android-app | skill | mapping values are not allowed here in "<unicode string>", line 8, column 29: Compose-by-default UI (`ui: compose`, or ` |
| iru-setup-android-github-workflows | skill | mapping values are not allowed here in "<unicode string>", line 2, column 820: ... to GitHub Pages (or, with `pages: no` |
| iru-setup-android-gitignore | skill | mapping values are not allowed here in "<unicode string>", line 5, column 67: ... tignore`, optionally with `args`: `mod |
| iru-setup-android-library | skill | mapping values are not allowed here in "<unicode string>", line 2, column 1097: ... up SonarQube/SonarCloud (`sonar`: `c |
| iru-setup-android-repository | skill | mapping values are not allowed here in "<unicode string>", line 17, column 61: ... ecurity block included) when `ci: no` |
| iru-setup-angular-web | skill | mapping values are not allowed here in "<unicode string>", line 5, column 66: ... the full toolchain on top of it: confi |
| iru-setup-ionic-app | skill | mapping values are not allowed here in "<unicode string>", line 2, column 1097: ... s for the framework (`framework`: `a |
| iru-setup-java-github-workflows | skill | mapping values are not allowed here in "<unicode string>", line 2, column 572: ... to GitHub Pages (or, with `pages: no` |
| iru-setup-java-library | skill | mapping values are not allowed here in "<unicode string>", line 2, column 526: ... he `sonar-maven-plugin` (`sonar`: `cl |
| iru-setup-java-library-repository | skill | mapping values are not allowed here in "<unicode string>", line 2, column 861: ... y`, optionally with `args` (`key: val |
| iru-setup-java-springboot-platform | skill | mapping values are not allowed here in "<unicode string>", line 2, column 1847: ... ng.enabled` is true (or `rolling: ye |
| iru-setup-react-web | skill | mapping values are not allowed here in "<unicode string>", line 2, column 1044: ... resolved inputs via `args` (`key: va |
| iru-setup-swift-github-workflows | skill | mapping values are not allowed here in "<unicode string>", line 2, column 1714: ... nch, a release workflow (library: ve |
| iru-setup-swift-gitignore | skill | mapping values are not allowed here in "<unicode string>", line 6, column 71: ... ed` (asked via `AskUserQuestion`: comm |
| iru-setup-swift-library | skill | mapping values are not allowed here in "<unicode string>", line 2, column 213: ... .swift` (`// swift-tools-version: 6.0 |
| iru-setup-swift-repository | skill | mapping values are not allowed here in "<unicode string>", line 14, column 64: ... lows` (skipped entirely when `ci: no` |
| iru-setup-typescript-library | skill | mapping values are not allowed here in "<unicode string>", line 2, column 620: ... narQube/SonarCloud scan (`sonar`: `cl |
| iru-split-github-issue | skill | mapping values are not allowed here in "<unicode string>", line 2, column 380: ... reated from it); optional `force: yes |
| iru-swift-bump-version | skill | mapping values are not allowed here in "<unicode string>", line 2, column 364: ... "x.y.z[-dev]"` and/or a `version: "…" |
| iru-swift-code-one-task | skill | mapping values are not allowed here in "<unicode string>", line 2, column 954: ... general Swift 6 code agreements: stri |
| iru-swift-code-one-task-group | skill | mapping values are not allowed here in "<unicode string>", line 2, column 336: ... validates the entire bucket once: lic |
| iru-swift-coverage | skill | mapping values are not allowed here in "<unicode string>", line 2, column 782: ... ackage/target. Also accepts `key: val |
| iru-swift-generate-all-tests | skill | mapping values are not allowed here in "<unicode string>", line 2, column 1304: ... target/Xcode app target (default: th |
| iru-swift-test | skill | mapping values are not allowed here in "<unicode string>", line 2, column 687: ... method` pair) plus optional `key: val |
| iru-typescript-code-one-task | skill | mapping values are not allowed here in "<unicode string>", line 2, column 593: ... neral TypeScript code agreements: str |
| iru-typescript-code-one-task-group | skill | mapping values are not allowed here in "<unicode string>", line 2, column 346: ... validates the entire bucket once: lic |
