# .NET development reference

Extra code agreements for implementing a task in a .NET repository, loaded by `iru-dotnet-code-one-task` **only when
the project shape calls for them**. The general .NET rules (conventions from `CLAUDE.md`, XML doc comments,
`ArgumentException`/`ArgumentNullException`, the repository's own test framework, no new NuGet packages) live in
`SKILL.md` itself and apply to every task; these files add what a specific shape needs.

## Read this much, and no more

Detect the shape first (`iru-dotnet-code-one-task` Step 0), then read:

| Read | When |
|---|---|
| `cli.md` | **CLI-shaped project only** — an `<OutputType>Exe</OutputType>` project referencing `System.CommandLine` (or `Spectre.Console.Cli`, or with `PackAsTool`/`PublishAot`), e.g. the `iru-setup-dotnet-cli` layout. System.CommandLine 2.0 patterns, where code goes (Core vs the thin CLI project), output/errors/colour/prompts/signals with Spectre.Console, Native AOT and trimming rules, testing commands in-process, regenerating the CLI reference. |
| `cli-contract.md` | **CLI-shaped project only**, whenever the task adds or changes a command, flag, output, error or exit path. The language-agnostic behaviour every command keeps: streams, exit codes, TTY/colour/prompts, JSON output and the error envelope, safety, configuration, self-description. |

A library, service or plain console app that isn't CLI-shaped reads **neither** file. A CLI task that only changes
logic inside one existing Core type, with no new command, flag, output or error, needs `cli.md`'s "Where code goes"
and "Native AOT and trimming" sections at most.

## The rules that override everything else

1. **Match the surrounding code.** Every rule here is the default for *new* code. If the project consistently does
   something else (e.g. Spectre.Console.Cli instead of System.CommandLine, no Core project), follow it and note the
   divergence in the report rather than restructuring untouched code.
2. **A task implements what the task says.** These references never license adding a NuGet package (a JSON, TUI or
   mocking library), a project, or a "while I'm here" refactor the plan didn't ask for.
3. **Never renumber exit codes or reshape the error envelope** — scripts and agents depend on both. A new failure
   maps onto an existing exit code; finer detail goes in the envelope's `code`/`details`.
4. **This skill doesn't validate.** Beyond compile-checking the projects it touched, it never runs tests, coverage,
   analyzer reports, DocFX, Native AOT publish, or `gen-docs` checks — `iru-dotnet-code-one-task-group` does that once
   per task group.

## Sources

- irurueta docs: ai/cli-for-agents/frameworks-swift-and-dotnet.adoc (System.CommandLine 2.x, Spectre.Console,
  Spectre.Console.Cli, .NET global tools), streams-and-exit-codes.adoc, tty-colour-and-interactivity.adoc,
  machine-readable-output.adoc, agent-ergonomics.adoc, safety-and-idempotency.adoc, configuration-and-auth.adoc,
  self-describing-help.adoc, security.adoc, testing-clis.adoc, documenting-clis.adoc, tuis-vs-clis.adoc and
  agent-readiness-checklist.adoc — https://www.irurueta.com/ai/cli-for-agents/index.html
- irurueta docs: programming-languages/csharp/coding-conventions-and-documentation.adoc, testing.adoc and
  build-and-tooling.adoc (https://github.com/albertoirurueta/docs)
- System.CommandLine: <https://learn.microsoft.com/en-us/dotnet/standard/commandline/> (2.0 GA API — the
  `2.0.0-beta*` articles and samples describe a different API)
- Native AOT and trimming: <https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/>,
  <https://learn.microsoft.com/en-us/dotnet/core/deploying/trimming/prepare-libraries-for-trimming>,
  <https://learn.microsoft.com/en-us/dotnet/core/deploying/trimming/fixing-warnings>
- System.Text.Json source generation:
  <https://learn.microsoft.com/en-us/dotnet/standard/serialization/system-text-json/source-generation>
- `PosixSignalRegistration`: <https://learn.microsoft.com/en-us/dotnet/api/system.runtime.interopservices.posixsignalregistration>
- RID-specific and Native AOT .NET tools, `dnx`: <https://learn.microsoft.com/en-us/dotnet/core/tools/rid-specific-tools>
- Spectre.Console: <https://spectreconsole.net/>; Terminal.Gui v2: <https://tui-cs.github.io/Terminal.Gui/>
- Command Line Interface Guidelines (clig.dev); NO_COLOR (no-color.org)
- Verified against a scaffold rendered by `iru-setup-dotnet-cli` on 2026-10-16 (.NET SDK 10.0.402,
  System.CommandLine 2.0.13, Spectre.Console 0.57.2, Terminal.Gui 2.5.0, MSTest 4.5.1) — see that skill's
  "Verification notes".
