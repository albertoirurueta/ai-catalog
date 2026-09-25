# React Native (Expo)

Conventions specific to a React Native (Expo, `iru-setup-react-native-app`) project. Everything in
`code-style.md`, `tsdoc.md`, `testing.md`, and `react.md` (function components, hooks rules, state colocation)
still applies; this file adds what's specific to Expo Router, native platform differences, and RNTL.

## Expo Router: file-based routing

- A screen is a file under `app/`; the file's path *is* its route — `app/orders/[id].tsx` is the dynamic
  `/orders/:id` screen, `app/orders/index.tsx` is `/orders`, `app/(tabs)/home.tsx` is a route inside the
  `(tabs)` group (parenthesized segments don't appear in the URL).
- **A route file's default export is the screen component** — this is the one place in this catalog's TypeScript
  conventions where a default export is required, because Expo Router resolves the route by file location and
  expects the default export; still give the component a proper `PascalCase` name (`export default function
  OrderDetailScreen() { ... }`) rather than an anonymous function, and still name/export any non-screen
  helper/type from the file as a named export.
- Shared UI, hooks, and non-route logic live outside `app/` (in `src/features/<name>/`, mirroring `react.md`'s
  layout) and are imported into the route file — a route file itself should stay thin (composition + navigation
  glue), with the real logic in a tested, non-route module.
- Navigate with the router's own APIs (`useRouter()`, `<Link href="...">`, `router.push(...)`) rather than
  reaching into `react-navigation` primitives directly — Expo Router wraps them.
- Typed routes: use the project's generated route types (`expo-router`'s `Href` type) instead of a bare `string`
  for a route path, when the project has typed routes enabled.

## Platform-specific files and code

- **`Component.ios.tsx` / `Component.android.tsx` / `Component.tsx`** (fallback) — the platform-suffixed file is
  picked automatically by the bundler; use this over an in-file `Platform.OS === "ios"` branch whenever the
  divergence is substantial (different layout, different native behavior), and reserve the in-file
  `Platform.select({ ios: ..., android: ... })`/`Platform.OS` check for a small, localized difference (a style
  value, a spacing constant).
- Don't guess a platform behavior — check the actual Expo/React Native API docs for the component in question;
  some props and native modules are one-platform-only and silently no-op (or warn) on the other.

## No direct native modules without a config plugin

- **This is an Expo managed/New-Architecture project — no ad hoc native module written or linked directly.** A
  task needing native functionality outside Expo's own SDK modules and an already-installed library's JS API is
  a blocker to report (Step 5 of `SKILL.md`), not something to implement by dropping native (Swift/Kotlin) code
  into `ios/`/`android/` — those directories are `expo prebuild` output in a managed workflow and aren't meant to
  be hand-edited.
- Adding a *new* third-party native library is a "new runtime dependency" decision (`code-style.md`) with an
  extra wrinkle here: check whether it ships (or needs) a **config plugin** (`app.json`/`app.config.ts`
  `plugins` array) before treating it as usable — a native module with no config plugin and no plain-JS API
  can't be wired up without ejecting, which is out of scope for a single task.
- Prefer an existing Expo SDK module (`expo-camera`, `expo-notifications`, `expo-file-system`, …) over a
  third-party equivalent when one covers the need — it already has a maintained config plugin and New
  Architecture support.

## Testing: RNTL

- **`@testing-library/react-native`** (RNTL), following `testing.md`'s Testing Library query-priority guidance —
  `getByRole`/`getByText`/`getByLabelText`/`getByTestId` (RNTL leans on `testID` more than web RTL leans on
  `data-testid`, since native accessibility roles are less consistently exposed than DOM roles; still prefer an
  accessible query when the component actually sets `accessibilityRole`/`accessibilityLabel`).
- **`fireEvent`** for basic interaction (`fireEvent.press(button)`) is still idiomatic in RNTL (unlike web RTL,
  where `userEvent` is preferred) — RNTL's own `userEvent` companion exists and is preferred where the project
  already uses it, but `fireEvent.press`/`fireEvent.changeText` remain acceptable for a project that hasn't
  adopted it.
- Run under `jest-expo`'s preset (this catalog's scaffold default) — don't add a second Jest config or preset for
  a single task.
- Mock a native module the test doesn't need to exercise (camera, notifications) at the module boundary
  (`jest.mock("expo-camera", () => ({ ... }))`), matching `testing.md`'s "mock what you don't own" rule; don't
  mock the component under test.
- For a screen under `app/`, test the underlying component logic directly where practical (import the named
  pieces it composes) rather than trying to render the full Expo Router tree, which needs router context most
  unit tests shouldn't have to set up.

## Styling and platform UI

- `StyleSheet.create({...})` for styles (typed, and slightly faster than inline style objects on the old
  architecture; still idiomatic under New Architecture). Avoid inline style objects created fresh on every render
  for anything beyond a one-off override.
- Respect safe areas (`react-native-safe-area-context`'s `useSafeAreaInsets`/`SafeAreaView`) for any screen-level
  layout — don't hardcode a top/bottom padding value that assumes no notch/home indicator.
