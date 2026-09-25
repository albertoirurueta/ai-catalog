# Swift development reference

General Swift 6 code agreements for implementing a task in a Swift Package or an Apple app project this catalog
scaffolds (`iru-setup-swift-library`, `iru-setup-apple-app`). These files exist so `iru-swift-code-one-task` can
load **only** what the task in front of it actually needs, instead of carrying every rule in context on every
task.

## Read this much, and no more

Detect the project shape and target first (`iru-swift-code-one-task` Step 1 — package vs. app, and which target),
then read:

| Read | When |
|---|---|
| `code-style.md` | **Always.** Swift 6 strict concurrency, value types, access control, error handling, naming, member ordering. |
| `docc.md` | The task adds or changes a type, or any `public`/`package`/`internal` member. |
| `testing.md` | The task writes or updates tests — which is nearly every task, since writing the tests is part of implementing it. |
| `swiftui.md` | The task adds or changes a SwiftUI `View` or view model. |
| `package-api.md` | The task changes a `public` declaration in a library package's target — semver-stable API, availability, `Package.swift` hygiene. |
| `app-structure.md` | The task adds a new app target, touches the generator manifest, or wires shared logic between `Packages/Core` and a platform target. |

A task that only changes logic inside one existing function, with no signature change and no UI involved, needs
`code-style.md` plus `testing.md`, and nothing else. Don't read the rest speculatively. Read at most one of
`package-api.md`/`app-structure.md` for a given task — a change belongs to the library's published surface or to
the app's own target wiring, rarely both.

## The three rules that override everything else

1. **Match the surrounding code.** Every rule here is the default for *new* code. If the file or target you're
   editing consistently does something else, follow it and note the divergence in the report rather than
   converting the file to this document's preference as a side effect of an unrelated task. Reordering or
   restyling untouched code turns a two-line change into an unreviewable diff.
2. **A task implements what the task says.** These references tell you *how* to write what was asked for. They
   never license adding an abstraction, a protocol, or a "while I'm here" refactor the plan didn't ask for.
3. **This skill doesn't validate.** Beyond a compile-check of the target it touched, it never runs the full test
   suite, coverage, SwiftLint/`swift format`, license headers, or a DocC audit — the calling
   `iru-swift-code-one-task-group` does all of that once for the whole task group. Write code that will pass
   those gates; don't run them here.

## Sources

Compiled from the following, cross-checked against each other and against a real Swift 6.4 toolchain (Xcode 27),
with this catalog's own stated preferences taking precedence where they are stricter (notably on avoiding
`@unchecked Sendable`, and on the public-to-private declaration order, which the Swift API Design Guidelines
leave unspecified).

- Swift API Design Guidelines: <https://www.swift.org/documentation/api-design-guidelines/>
- The Swift Programming Language — Concurrency: <https://docs.swift.org/swift-book/documentation/the-swift-programming-language/concurrency/>
- The Swift Programming Language — Error Handling: <https://docs.swift.org/swift-book/documentation/the-swift-programming-language/errorhandling/>
- Swift 6 migration guide (strict concurrency, `Sendable`, data-race safety): <https://www.swift.org/migration/documentation/migrationguide/>
- Swift evolution, typed throws (SE-0413): <https://github.com/swiftlang/swift-evolution/blob/main/proposals/0413-typed-throws.md>
- Swift Testing documentation: <https://developer.apple.com/documentation/testing>
- Swift Testing on swift.org: <https://swift.org/documentation/testing/>
- XCTest documentation: <https://developer.apple.com/documentation/xctest>
- DocC documentation: <https://www.swift.org/documentation/docc/>, authoring reference: <https://www.swift.org/documentation/docc/writing-symbol-documentation-in-your-source-files>
- SwiftUI documentation: <https://developer.apple.com/documentation/swiftui>, `@Observable`: <https://developer.apple.com/documentation/observation>
- Swift Package Manager documentation: <https://www.swift.org/documentation/package-manager/>, `PackageDescription` reference: <https://developer.apple.com/documentation/packagedescription>
- `apple/swift-format` (the toolchain's bundled formatter/linter): <https://github.com/swiftlang/swift-format>
