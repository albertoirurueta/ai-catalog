# Tests

Every task's implementation comes with the tests that prove it. This skill **writes** them and does not **run**
them beyond `iru-swift-code-one-task`'s own Step 5 compile-check — the calling `iru-swift-code-one-task-group`
runs the suite, coverage, and quality checks once for the whole task group. Write tests that will pass and that
will hold the coverage gate up; don't invoke `swift test`/`xcodebuild test` here.

## Follow the target you're in

Before writing a test, read an existing test in the same target. Match its structure, its naming convention, and
which framework it already uses. Introducing a second testing framework in a target that already has one — Swift
Testing next to an entirely XCTest suite, or vice versa — is a cost paid by every later reader, and it isn't what
the task asked for.

Defaults for a target that doesn't yet have a convention: **Swift Testing** for unit tests (the modern default
this catalog's scaffolds ship), **XCTest** only for what Swift Testing doesn't cover — XCUITest (UI automation)
and `measure` performance tests, both still XCTest-only as of Swift 6.4/Xcode 27.

## Swift Testing

All of the following were built and run against a real Swift 6.4 toolchain (`swift build --build-tests` /
`swift test`) as part of authoring this reference, and passed exactly as shown.

- **`@Suite("Display name")` on a `struct`** groups related tests; a nested `struct`/`@Suite` groups a scenario
  further. A suite needs no base class or `@Test`-marked `init`/`deinit` — plain Swift initialization runs before
  each test, giving every test a fresh instance (Swift Testing's replacement for XCTest's `setUp()`).
- **`@Test("Display name")` on a function** (top-level or inside a `@Suite`) marks a test; the display name is
  optional but preferred for a name that reads better in a report than the function name alone.
- **`#expect(condition)`** records a failure and *continues* the test if the condition is false — use it for most
  assertions, including several in the same test, so one failure doesn't hide the next.
- **`#require(expression)`** either returns the successfully-unwrapped value (from an `Optional` or a throwing
  expression) or stops the test immediately — use it for a precondition the rest of the test can't meaningfully
  continue without (unwrapping a value the test is about to use), the Swift Testing equivalent of
  `XCTUnwrap`/`assertThrows`'s "stop here" behavior:

  ```swift
  @Test
  func requireExample() throws {
    let counter = Counter()
    let value = try #require(Optional(counter))
    ...
  }
  ```

- **Parameterized tests** — `@Test(arguments: [1, 3, 5])` (or `arguments:` with a `zip`/two collections for
  paired parameters) runs the function once per argument, reporting which input failed independently:

  ```swift
  @Test("currentValue reflects prior increments", arguments: [1, 3, 5])
  func currentValueReflectsIncrements(times: Int) async {
    let counter = Counter()
    for _ in 0..<times {
      await counter.increment()
    }
    #expect(await counter.currentValue() == times)
  }
  ```

  Prefer this over a hand-written loop inside one test or several near-identical test functions.
- **`withKnownIssue("reason") { ... }`** wraps a block whose failure is a tracked, already-known issue rather than
  a fresh regression — the test still reports (as a known issue, not a failure) if the block fails, and flips to
  an actual failure the moment the block starts passing again (a signal the known issue was fixed and the wrapper
  should come off). Verified: a `#expect` failure inside `withKnownIssue` reports "recorded a known issue" and the
  surrounding test still passes. Use it only for a genuinely tracked, external issue — never to silence a test
  this task's own code should make pass.
- **Tags** — declare a custom tag as a `static var` in an extension of `Tag` (`extension Tag { @Tag static var
  fast: Self }`), then attach it to a suite or test with `.tags(.fast)`; useful for a test the task itself marks
  as belonging to a category the project's tooling filters on (e.g. excluding slow tests from a pre-commit run).
  Don't invent a tag vocabulary the project doesn't already have without the task asking for it.
- **Traits** — `.disabled("reason")` skips a test with a stated reason (verified: it reports "skipped" with that
  reason, not silently); `.timeLimit(.minutes(1))` fails a test that runs too long; `.bug("https://...")`
  annotates a test with a tracked issue link. Reach for these over a commented-out `@Test` or a magic sleep-based
  timeout.
- **Testing an `actor`** — call its `async` methods with `await` from the test function itself (a `@Test`
  function can be `async` freely); no special harness is needed, since the actor's own isolation is exactly what
  production callers see too.
- **Testing a `@MainActor` type** — mark the test function (or the whole `@Suite`) `@MainActor` so it runs on the
  main actor and can call the type's isolated members without an extra `await` hop across actors:

  ```swift
  @Suite("CounterViewModel")
  @MainActor
  struct CounterViewModelTests {

    @Test("increment updates displayValue")
    func incrementUpdatesDisplayValue() async {
      let viewModel = CounterViewModel(counter: Counter())
      await viewModel.increment()
      #expect(viewModel.displayValue == 1)
    }
  }
  ```

- **`#expect(throws:)`** asserts a specific error (by value, when the error type is `Equatable`, or by type
  otherwise) is thrown by the expression in the trailing closure — verified against the typed-throws example in
  `code-style.md`:

  ```swift
  @Test("validate rejects a negative value")
  func validateRejectsNegativeValue() {
    #expect(throws: ValidationError.negativeValue(-1.0)) {
      try MeasurementValidator.validate(meters: -1.0)
    }
  }
  ```

## XCTest — where it's still the right tool

- **XCUITest** (`XCTestCase` subclass, `XCUIApplication`, `.launch()`, `app.buttons["..."].tap()`) for UI
  automation against a running app — Swift Testing has no UI-automation equivalent as of Swift 6.4/Xcode 27.
- **`measure { ... }`** for a performance test asserting on wall-clock/CPU baselines — also XCTest-only; Swift
  Testing has no direct equivalent yet.
- An XCTest class still uses `func testX()` naming (no `@Test` attribute) and `XCTAssertEqual`/`XCTAssertTrue`/
  `XCTAssertThrowsError`/`XCTUnwrap` — don't mix `#expect`/`#require` into an `XCTestCase` subclass; a file is one
  framework or the other.
- **`@testable import <ModuleName>`** at the top of a test file reaches `internal` declarations from the test
  target without widening production access control to `public` — the standard way both Swift Testing and XCTest
  files see a package's/app's own non-public API. It cannot reach `private`/`fileprivate` declarations; don't
  widen those just to test them (see the next section).

## What to cover

- **The behavior the task added or changed**, through the type's `public`/`package`/`internal` API — the happy
  path plus the meaningful variations.
- **Every `- Throws:` in the DocC comment.** Each documented error case gets a test asserting it's thrown for the
  documented condition — this is the single most useful habit here, and where most real defects surface.
- **Boundaries**: empty/single-element collections, zero, negative, the first and last valid value, `nil` where
  an optional makes it a meaningful input.
- **Actor isolation and `Sendable` boundaries** the task's type introduces — a test that calls an actor's method
  concurrently from two tasks and asserts the invariant still holds is worth writing when the task's whole point
  is that serialization; a test that just calls one method once doesn't exercise it.
- **Not the trivia.** A synthesized `Equatable`/`Hashable` conformance, a constant, or a one-line delegate to an
  already-tested function needs no dedicated test. Coverage is a gate, not a goal.

## Writing the test

- **One behavior per test function**, named so the assertion is clear from the name alone.
- **Arrange, act, assert**, in that order and visibly separated.
- **Assert the specific thing** — `#expect(a == b)` over a hand-rolled boolean condition, so the failure message
  shows the actual values.
- **No `Thread.sleep`/`Task.sleep` as a synchronization mechanism.** Await the actual async call, or use
  `.timeLimit(...)` if a genuine timeout assertion is the point — a sleep-based wait is either flaky or slow,
  usually both.
- **Don't test `private`/`fileprivate` members directly** by widening their access level. Exercise them through
  the type's `internal`-or-wider behavior (reachable via `@testable import`); if that's genuinely impossible, the
  design is telling you the logic wants to be its own type — a finding to report, not a refactor to perform
  mid-task.
- Test types get the same member ordering/`// MARK:` grouping as any other Swift type (`code-style.md`). Test
  functions don't need DocC comments unless the *why* of the scenario is non-obvious.

## What this skill does not do

Beyond `iru-swift-code-one-task`'s own Step 5 compile-check, no running the suite, no coverage report, no
SwiftLint/`swift format` run, no license headers, no DocC audit — all of those belong to
`iru-swift-code-one-task-group`, once per task group. If a test can't be made to pass without something outside
the task's scope, say so in the report; don't delete the assertion to make the file green.
