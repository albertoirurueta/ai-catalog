# `App/Tests` and `App/UITests` templates

- **`<AppName>Tests`** (`bundle.unit-test`, hosted by the app, Swift Testing): tests of the app-target glue — the
  SwiftUI views lay out, or the AppKit view controller wires its widgets to the controller/view model, the menu bar
  is complete, Settings writes its preference. The screen logic itself is tested in `Packages/Core` (CoreTests);
  the app target is **not** part of the coverage bar.
- **`<AppName>UITests`** (`bundle.ui-testing`, XCTest/XCUIAutomation — Swift Testing has no UI driver): launches the
  real app, types a name, clicks Greet and reads the greeting. It drives the real desktop session, so it is never
  run in parallel with another UI-test run (the Swift gates serialize every app `xcodebuild test` behind
  `.simulator-test.lock`), and it needs the Accessibility/Automation permission described in SKILL.md.

The accessibility identifiers (`nameField`, `greetButton`, `greetingLabel`, `errorLabel`, `greetsOnSubmitToggle`)
are identical for both `ui` values, so the UI test is shared. Placeholders and markers work as described in
SKILL.md's "Reference files" section; rendered and run on 2026-10-16.

### `App/Sources/LaunchOptions.swift`

```swift
import Foundation

/// Launch arguments the app understands. Shared by both `ui` values.
enum LaunchOptions {
    /// Passed by the UI tests: start from a known state (the app's own preferences back to their defaults).
    static let uiTesting = "--uitesting"

    /// Removes the app's own preferences when `arguments` contains ``uiTesting``.
    ///
    /// Only the keys the app owns are removed, never the whole defaults domain (which also holds AppKit/SwiftUI
    /// window state).
    ///
    /// - Parameters:
    ///   - arguments: The process arguments, `CommandLine.arguments` in the app.
    ///   - defaults: The preferences to reset.
    ///   - keys: The preference keys to remove.
    /// - Returns: Whether the app was launched for UI testing.
    @discardableResult
    static func apply(
        arguments: [String] = CommandLine.arguments,
        defaults: UserDefaults = .standard,
        keys: [String] = SettingsKeys.all
    ) -> Bool {
        guard arguments.contains(uiTesting) else {
            return false
        }
        for key in keys {
            defaults.removeObject(forKey: key)
        }
        return true
    }
}
```

The SwiftUI `App` calls `LaunchOptions.apply()` in its `init()`; the AppKit `AppDelegate` in
`applicationWillFinishLaunching(_:)`, before it registers the defaults. Add every new preference key to
`SettingsKeys.all`.

### `App/Tests/LaunchOptionsTests.swift`

```swift
import Foundation
import Testing

@testable import <AppName>

@Suite("LaunchOptions")
struct LaunchOptionsTests {
    private func makeDefaults() throws -> (UserDefaults, String) {
        let domain = "<bundle-id>.tests.\(UUID().uuidString)"
        let defaults = try #require(UserDefaults(suiteName: domain))
        defaults.set(false, forKey: SettingsKeys.greetsOnSubmit)
        return (defaults, domain)
    }

    @Test("--uitesting removes the app's preferences")
    func resetsForUITesting() throws {
        let (defaults, domain) = try makeDefaults()
        defer { defaults.removePersistentDomain(forName: domain) }
        #expect(LaunchOptions.apply(arguments: ["app", "--uitesting"], defaults: defaults))
        // The suite's own value is gone (a registered default may still answer object(forKey:)).
        #expect(defaults.persistentDomain(forName: domain)?[SettingsKeys.greetsOnSubmit] == nil)
    }

    @Test("a normal launch leaves the preferences alone")
    func normalLaunch() throws {
        let (defaults, domain) = try makeDefaults()
        defer { defaults.removePersistentDomain(forName: domain) }
        #expect(!LaunchOptions.apply(arguments: ["app"], defaults: defaults))
        #expect(defaults.persistentDomain(forName: domain)?[SettingsKeys.greetsOnSubmit] as? Bool == false)
    }
}
```

### `App/Tests/<AppName>Tests.swift` (ui: swiftui)

```swift
import AppKit
import SwiftUI
import Testing

@testable import <AppName>

/// Smoke tests of the SwiftUI layer: the views lay out in an AppKit hosting view. Screen logic is tested in
/// Packages/Core (CoreTests).
@MainActor
@Suite("SwiftUI views")
struct <AppName>Tests {
    @Test("the main window content lays out at its minimum size")
    func contentViewLaysOut() {
        let host = NSHostingView(rootView: ContentView())
        host.layoutSubtreeIfNeeded()
        #expect(host.fittingSize.width >= 360)
        #expect(host.fittingSize.height >= 200)
    }

    @Test("the settings window content has a fixed size")
    func settingsViewLaysOut() {
        let host = NSHostingView(rootView: SettingsView())
        host.layoutSubtreeIfNeeded()
        #expect(host.fittingSize == NSSize(width: 420, height: 180))
    }

    @Test("the settings key is stable")
    func settingsKey() {
        #expect(SettingsKeys.greetsOnSubmit == "greetsOnSubmit")
    }
}
```

### `App/Tests/TestDefaults.swift` (ui: appkit)

```swift
import Foundation

@testable import <AppName>

/// An isolated, empty user-defaults suite for one test, so tests never read or write the app's real preferences.
func makeTestDefaults(greetsOnSubmit: Bool = true) -> UserDefaults {
    let suiteName = "<bundle-id>.tests.\(UUID().uuidString)"
    let defaults = UserDefaults(suiteName: suiteName) ?? .standard
    defaults.removePersistentDomain(forName: suiteName)
    defaults.set(greetsOnSubmit, forKey: SettingsKeys.greetsOnSubmit)
    return defaults
}
```

### `App/Tests/MainViewControllerTests.swift` (ui: appkit, architecture: mvc)

```swift
import AppKit
import Core
import Testing

@testable import <AppName>

@MainActor
@Suite("MainViewController (MVC)")
struct MainViewControllerTests {
    private func makeLoadedController(greetsOnSubmit: Bool = true) -> MainViewController {
        let controller = MainViewController(defaults: makeTestDefaults(greetsOnSubmit: greetsOnSubmit))
        controller.loadViewIfNeeded()
        return controller
    }

    private func type(_ text: String, into controller: MainViewController) {
        controller.nameField.stringValue = text
        controller.controlTextDidChange(
            Notification(name: NSControl.textDidChangeNotification, object: controller.nameField))
    }

    @Test("starts with Greet disabled and no greeting")
    func initialState() {
        let controller = makeLoadedController()
        #expect(!controller.greetButton.isEnabled)
        #expect(controller.greetingLabel.stringValue.isEmpty)
        #expect(controller.errorLabel.isHidden)
    }

    @Test("clicking Greet shows the greeting for the typed name")
    func greetButton() {
        let controller = makeLoadedController()
        type("Ada", into: controller)
        #expect(controller.greetButton.isEnabled)
        controller.greetButton.performClick(nil)
        #expect(controller.greetingLabel.stringValue == "Hello, Ada!")
    }

    @Test("Return greets only when the setting is on", arguments: [true, false])
    func returnKey(greetsOnSubmit: Bool) {
        let controller = makeLoadedController(greetsOnSubmit: greetsOnSubmit)
        type("Ada", into: controller)
        controller.nameField.sendAction(controller.nameField.action, to: controller.nameField.target)
        #expect(controller.greetingLabel.stringValue == (greetsOnSubmit ? "Hello, Ada!" : ""))
    }

    @Test("a blank name shows the validation error")
    func blankName() {
        let controller = makeLoadedController()
        type("  ", into: controller)
        controller.greet(nil)
        #expect(!controller.errorLabel.isHidden)
        #expect(controller.errorLabel.stringValue == "Enter a name first.")
        #expect(controller.greetingLabel.stringValue.isEmpty)
    }

    @Test("the Greet menu item follows the button; other items stay enabled")
    func menuValidation() {
        let controller = makeLoadedController()
        let greet = NSMenuItem(title: "Greet", action: #selector(MainViewController.greet(_:)), keyEquivalent: "")
        let other = NSMenuItem(title: "Other", action: #selector(NSText.copy(_:)), keyEquivalent: "")
        #expect(!controller.validateMenuItem(greet))
        type("Ada", into: controller)
        #expect(controller.validateMenuItem(greet))
        #expect(controller.validateMenuItem(other))
    }
}
```

### `App/Tests/MainViewControllerTests.swift` (ui: appkit, architecture: mvvm)

```swift
import AppKit
import Core
import Testing

@testable import <AppName>

@MainActor
@Suite("MainViewController (MVVM)")
struct MainViewControllerTests {
    /// Loads the controller into a window, so AppKit runs layout (and with it Observation tracking) on demand.
    private func makeShownController(greetsOnSubmit: Bool = true) -> (MainViewController, NSWindow) {
        let controller = MainViewController(defaults: makeTestDefaults(greetsOnSubmit: greetsOnSubmit))
        let window = NSWindow(contentViewController: controller)
        window.layoutIfNeeded()
        return (controller, window)
    }

    private func type(_ text: String, into controller: MainViewController, window: NSWindow) {
        controller.nameField.stringValue = text
        controller.controlTextDidChange(
            Notification(name: NSControl.textDidChangeNotification, object: controller.nameField))
        window.layoutIfNeeded()
    }

    @Test("starts with Greet disabled and no greeting")
    func initialState() {
        let (controller, _) = makeShownController()
        #expect(!controller.greetButton.isEnabled)
        #expect(controller.greetingLabel.stringValue.isEmpty)
        #expect(controller.errorLabel.isHidden)
    }

    @Test("typing writes the view model; Observation tracking re-renders the view")
    func greetButton() {
        let (controller, window) = makeShownController()
        type("Ada", into: controller, window: window)
        #expect(controller.viewModel.name == "Ada")
        #expect(controller.greetButton.isEnabled)
        controller.greetButton.performClick(nil)
        window.layoutIfNeeded()
        #expect(controller.greetingLabel.stringValue == "Hello, Ada!")
    }

    @Test("Return greets only when the setting is on", arguments: [true, false])
    func returnKey(greetsOnSubmit: Bool) {
        let (controller, window) = makeShownController(greetsOnSubmit: greetsOnSubmit)
        type("Ada", into: controller, window: window)
        controller.nameField.sendAction(controller.nameField.action, to: controller.nameField.target)
        window.layoutIfNeeded()
        #expect(controller.greetingLabel.stringValue == (greetsOnSubmit ? "Hello, Ada!" : ""))
    }

    @Test("a blank name shows the validation error")
    func blankName() {
        let (controller, window) = makeShownController()
        type("  ", into: controller, window: window)
        controller.greet(nil)
        window.layoutIfNeeded()
        #expect(!controller.errorLabel.isHidden)
        #expect(controller.errorLabel.stringValue == "Enter a name first.")
    }

    @Test("the Greet menu item follows the view model; other items stay enabled")
    func menuValidation() {
        let (controller, window) = makeShownController()
        let greet = NSMenuItem(title: "Greet", action: #selector(MainViewController.greet(_:)), keyEquivalent: "")
        let other = NSMenuItem(title: "Other", action: #selector(NSText.copy(_:)), keyEquivalent: "")
        #expect(!controller.validateMenuItem(greet))
        type("Ada", into: controller, window: window)
        #expect(controller.validateMenuItem(greet))
        #expect(controller.validateMenuItem(other))
    }
}
```

### `App/Tests/AppShellTests.swift` (ui: appkit)

```swift
import AppKit
import Testing

@testable import <AppName>

@MainActor
@Suite("App shell")
struct AppShellTests {
    @Test("the menu bar has the standard menus in order")
    func menuTitles() {
        let menu = MainMenu.make(appName: "Demo")
        #expect(menu.items.map(\.title) == ["Demo", "File", "Edit", "Greeting", "Window", "Help"])
    }

    @Test("Settings… is ⌘, and Greet is ⇧⌘G")
    func keyEquivalents() throws {
        let menu = MainMenu.make(appName: "Demo")
        let settings = try #require(menu.item(withTitle: "Demo")?.submenu?.item(withTitle: "Settings…"))
        #expect(settings.keyEquivalent == ",")
        #expect(settings.action == #selector(AppDelegate.showSettings(_:)))
        let greet = try #require(menu.item(withTitle: "Greeting")?.submenu?.item(withTitle: "Greet"))
        #expect(greet.keyEquivalent == "g")
        #expect(greet.keyEquivalentModifierMask == [.command, .shift])
    }

    @Test("install registers the Window, Services and Help menus")
    func install() {
        let application = NSApplication.shared
        let previous = application.mainMenu
        defer { application.mainMenu = previous }
        MainMenu.install(in: application, appName: "Demo")
        #expect(application.windowsMenu?.title == "Window")
        #expect(application.servicesMenu?.title == "Services")
        #expect(application.helpMenu?.title == "Help")
    }

    @Test("the main window is titled, resizable and remembers its frame")
    func mainWindow() throws {
        let window = try #require(MainWindowController().window)
        #expect(window.title == "<app-name>")
        #expect(window.styleMask.contains(.resizable))
        #expect(window.frameAutosaveName == "MainWindow")
    }

    @Test("the settings checkbox reads and writes the preference")
    func settings() {
        let defaults = makeTestDefaults(greetsOnSubmit: false)
        let controller = SettingsWindowController(defaults: defaults)
        #expect(controller.greetsOnSubmitCheckbox.state == .off)
        controller.greetsOnSubmitCheckbox.performClick(nil)
        #expect(defaults.bool(forKey: SettingsKeys.greetsOnSubmit))
        defaults.set(false, forKey: SettingsKeys.greetsOnSubmit)
        controller.showWindow(nil)
        #expect(controller.greetsOnSubmitCheckbox.state == .off)
        controller.close()
    }

    @Test("the app quits after its last window closes and restores state securely")
    func appDelegate() {
        let delegate = AppDelegate()
        #expect(delegate.applicationShouldTerminateAfterLastWindowClosed(NSApplication.shared))
        #expect(delegate.applicationSupportsSecureRestorableState(NSApplication.shared))
    }
}
```

### `App/UITests/<AppName>UITests.swift`

```swift
import XCTest

/// End-to-end tests that launch the real app and drive it like a person (XCUIAutomation).
final class <AppName>UITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    @MainActor
    private func launchApp() -> XCUIApplication {
        let app = XCUIApplication()
        // -ApplePersistenceIgnoreState YES: start from a fresh window instead of restoring the last session.
        // --uitesting (LaunchOptions) resets the app's preferences. Keep it LAST: the argument domain reads
        // "-key value" pairs, so "--uitesting" placed first would swallow "-ApplePersistenceIgnoreState" as its
        // value, and a SwiftUI app then restores a session with no window open.
        app.launchArguments += ["-ApplePersistenceIgnoreState", "YES", "--uitesting"]
        app.launch()
        return app
    }

    @MainActor
    func testGreetsTheTypedName() throws {
        let app = launchApp()
        let window = app.windows.firstMatch
        let nameField = window.textFields["nameField"]
        XCTAssertTrue(nameField.waitForExistence(timeout: 10))
        XCTAssertFalse(window.buttons["greetButton"].isEnabled)

        nameField.click()
        nameField.typeText("Ada")
        window.buttons["greetButton"].click()

        let greeting = window.staticTexts["greetingLabel"]
        XCTAssertTrue(greeting.waitForExistence(timeout: 5))
        XCTAssertEqual(greeting.value as? String, "Hello, Ada!")
    }

    @MainActor
    func testGreetMenuCommand() throws {
        let app = launchApp()
        let nameField = app.windows.firstMatch.textFields["nameField"]
        XCTAssertTrue(nameField.waitForExistence(timeout: 10))
        nameField.click()
        nameField.typeText("Grace")

        app.menuBars.menuBarItems["Greeting"].click()
        app.menuBars.menuItems["Greet"].click()

        let greeting = app.windows.firstMatch.staticTexts["greetingLabel"]
        XCTAssertTrue(greeting.waitForExistence(timeout: 5))
        XCTAssertEqual(greeting.value as? String, "Hello, Grace!")
    }
}
```
