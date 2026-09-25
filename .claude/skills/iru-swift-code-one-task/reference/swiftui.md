# SwiftUI

Conventions specific to SwiftUI views and view models in an app target. Everything in `code-style.md`, `docc.md`,
and `testing.md` still applies; this file adds what's specific to view composition and Observation.

## Small, composed views

A screen is a tree of small views, each responsible for one piece of the UI, not one large `body` with deeply
nested `if`/`HStack`/`VStack` chains. Extract a subview once a `body` needs a comment to explain a section — that
comment is naming the view you should have extracted:

```swift
struct OrientationBadge: View {

  let orientationDegrees: Int
  let onRecalculate: () -> Void

  var body: some View {
    HStack {
      Text("\(orientationDegrees)°")
      Button(action: onRecalculate) {
        Image(systemName: "arrow.clockwise")
      }
    }
  }
}
```

A view struct that only reads its own stored properties and has no identity of its own needs no explicit `init`
— the memberwise initializer SwiftUI synthesizes is enough; write one explicitly only to give a parameter a
default value or to validate/transform an input.

## `@Observable` view models, `@State`, `@Bindable`, `@Environment`

- **`@Observable`** (the `Observation` framework macro, not the older `ObservableObject` protocol) on a
  reference type that holds a screen's mutable state — it tracks per-property access automatically, so a view
  only re-renders for the specific properties it actually reads, unlike `ObservableObject`'s `@Published`, which
  invalidates on every change to any published property.
- **`@State`** in the view that owns an `@Observable` model's lifetime — creates and keeps it alive across
  recomposition:

  ```swift
  struct CounterScreen: View {

    @State private var viewModel: CounterViewModel

    init(counter: Counter) {
      _viewModel = State(initialValue: CounterViewModel(counter: counter))
    }

    var body: some View {
      Button("Increment: \(viewModel.displayValue)") {
        Task { await viewModel.increment() }
      }
    }
  }
  ```

- **`@Bindable`** when a child view needs a two-way `Binding` into an `@Observable` model it doesn't own (passed
  in from a parent) — `@Bindable var viewModel: CounterViewModel` inside the child, then `$viewModel.someField`
  for a binding to one of its properties.
- **`@Environment`** to read a value injected higher in the view tree (the app's own `@Observable` services, or a
  SwiftUI environment key) instead of threading a dependency through every intermediate view's initializer —
  reach for it for something genuinely ambient (a theme, a session, a feature flag), not as a shortcut around
  passing an explicit parameter for something only one branch of the tree needs.
- **A view model that touches UI state is `@MainActor`** — see `code-style.md`'s strict-concurrency section;
  `@Observable` doesn't imply main-actor isolation on its own, so an `@Observable` type meant to back a view
  still needs the `@MainActor` attribute explicitly.

## `NavigationStack`

Use `NavigationStack` (not the deprecated `NavigationView`) for a push/pop hierarchy, with a typed path
(`NavigationStack(path: $path) { ... }`, `path: NavigationPath` or `[Route]` for a `Hashable`/`Codable` route
enum) when the app needs programmatic navigation (deep links, restoring state) — a plain, uncontrolled
`NavigationStack { }` with `.navigationDestination(for:)` is enough when the app only ever pushes in response to
direct user taps.

## `#Preview`

Every view meant to be visually reviewed gets at least one `#Preview` alongside it — the macro that replaced
`PreviewProvider`:

```swift
#Preview {
  OrientationBadge(orientationDegrees: 90, onRecalculate: {})
}
```

Add a second, named preview (`#Preview("Dark") { ... }`) whenever the view has non-trivial color/contrast logic
worth checking in dark mode, or needs representative sample data that isn't obvious from the default preview.

## Platform conditionals

Guard platform-specific code with `#if os(...)` at the narrowest scope that needs it — a whole file only when the
entire file is platform-specific, a single property/modifier otherwise:

```swift
var body: some View {
  content
#if os(watchOS)
    .navigationBarTitleDisplayMode(.inline)
#endif
}
```

For behavior that varies across more than a couple of platforms, prefer an extension providing a single
cross-platform API (e.g. a `Color` initializer bridging `UIColor`/`NSColor`) over `#if os(...)` scattered through
every call site — see `app-structure.md` for where such cross-platform shims belong in a multi-target app.

## Testing

See `testing.md`'s Swift Testing section for a `@MainActor`-marked `@Suite`/`@Test` exercising a view model
directly (the common, fast case — assert on the model's published state after calling its methods, without
touching SwiftUI's rendering at all). Reach for XCUITest (also in `testing.md`) only for an actual UI-automation
scenario — tapping through a real running app — not as the default way to test a view's logic.
