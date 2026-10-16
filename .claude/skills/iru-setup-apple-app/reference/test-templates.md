# `Targets/<Platform>/Tests` and `Targets/<Platform>/UITests` templates

- **`<AppName>Tests-<Platform>`** (`bundle.unit-test`, hosted by the app — `TEST_HOST` pinned in `project.yml`,
  Swift Testing): tests of the app-target glue — the SwiftUI screen lays out, the UIKit view controller wires its
  widgets to the controller/view model, the scene manifest names `SceneDelegate`, `--uitesting` is honoured. The
  screen logic itself is tested in `Packages/Core` (`CoreTests`); the app target is **not** part of the coverage bar.
- **`<AppName>UITests-<Platform>`** (`bundle.ui-testing`, XCTest/XCUIAutomation — Swift Testing has no UI driver):
  launches the real app with `--uitesting`, types a name, taps Greet and reads the greeting (watchOS: only checks
  the screen appears, since typing goes through the system input sheet). Every app `xcodebuild test` is serialized
  behind `.simulator-test.lock` by the Swift gates.

One copy per platform folder; the files use `#if os(...)` so the same text compiles on every platform. Rendered and
run on 2026-10-16 (see SKILL.md Known quirks for the per-platform results).


### `Targets/<Platform>/Tests/LaunchOptionsTests.swift` (every platform)

```swift
import Testing

@testable import <AppName>

#if os(iOS) || os(visionOS)
    import UIKit
#endif

@MainActor
@Suite("LaunchOptions")
struct LaunchOptionsTests {
    @Test("a normal launch changes nothing")
    func normalLaunch() {
        #expect(!LaunchOptions.apply(arguments: ["app"]))
    }

    @Test("--uitesting is recognized")
    func uiTestingLaunch() {
        #if os(iOS) || os(visionOS)
            defer { UIView.setAnimationsEnabled(true) }
        #endif
        #expect(LaunchOptions.apply(arguments: ["app", LaunchOptions.uiTesting]))
        #if os(iOS) || os(visionOS)
            #expect(!UIView.areAnimationsEnabled)
        #endif
    }
}
```

### `Targets/<Platform>/Tests/<AppName>Tests.swift` (ui: swiftui or a non-iOS platform)

```swift
import SwiftUI
import Testing

@testable import <AppName>

#if os(iOS) || os(visionOS)
    import UIKit
#elseif os(macOS)
    import AppKit
#endif

/// Smoke tests of the SwiftUI layer. The screen logic is tested in Packages/Core (CoreTests).
@MainActor
@Suite("SwiftUI views")
struct <AppName>Tests {
    @Test("the greeting screen lays out")
    func contentViewLaysOut() {
        #if os(iOS) || os(visionOS)
            let host = UIHostingController(rootView: ContentView())
            let size = host.sizeThatFits(in: CGSize(width: 390, height: 844))
            #expect(size.width > 0)
            #expect(size.height > 0)
        #elseif os(macOS)
            let host = NSHostingView(rootView: ContentView())
            host.layoutSubtreeIfNeeded()
            #expect(host.fittingSize.width > 0)
        #else
            _ = ContentView()
        #endif
    }
}
```

### `Targets/iOS/Tests/GreetingViewControllerTests.swift` (ui: uikit, architecture: mvc)

```swift
import Core
import Testing
import UIKit

@testable import <AppName>

@MainActor
@Suite("GreetingViewController (MVC)")
struct GreetingViewControllerTests {
    private func makeLoadedController() -> GreetingViewController {
        let controller = GreetingViewController()
        controller.loadViewIfNeeded()
        return controller
    }

    private func type(_ text: String, into controller: GreetingViewController) {
        controller.nameField.text = text
        controller.nameField.sendActions(for: .editingChanged)
    }

    @Test("starts with Greet disabled and no greeting")
    func initialState() {
        let controller = makeLoadedController()
        #expect(controller.title == "<app-name>")
        #expect(!controller.greetButton.isEnabled)
        #expect(controller.greetingLabel.text?.isEmpty != false)
        #expect(controller.errorLabel.isHidden)
    }

    @Test("tapping Greet shows the greeting for the typed name")
    func greetButton() {
        let controller = makeLoadedController()
        type("Ada", into: controller)
        #expect(controller.greetButton.isEnabled)
        controller.greetButton.sendActions(for: .primaryActionTriggered)
        #expect(controller.greetingLabel.text == "Hello, Ada!")
    }

    @Test("Return greets only when Greet is enabled", arguments: [("Ada", "Hello, Ada!"), ("  ", "")])
    func returnKey(name: String, expected: String) {
        let controller = makeLoadedController()
        type(name, into: controller)
        #expect(controller.textFieldShouldReturn(controller.nameField))
        #expect((controller.greetingLabel.text ?? "") == expected)
    }

    @Test("a blank name shows the validation error")
    func blankName() {
        let controller = makeLoadedController()
        type("  ", into: controller)
        controller.greet()
        #expect(!controller.errorLabel.isHidden)
        #expect(controller.errorLabel.text == "Enter a name first.")
        #expect(controller.greetingLabel.text?.isEmpty != false)
    }
}
```

### `Targets/iOS/Tests/GreetingViewControllerTests.swift` (ui: uikit, architecture: mvvm)

```swift
import Core
import Testing
import UIKit

@testable import <AppName>

@MainActor
@Suite("GreetingViewController (MVVM)")
struct GreetingViewControllerTests {
    /// Loads the controller and lays its view out once, so UIKit records which view-model properties
    /// `viewWillLayoutSubviews()` read (Observation tracking).
    private func makeLaidOutController() -> GreetingViewController {
        let controller = GreetingViewController()
        controller.loadViewIfNeeded()
        controller.view.layoutIfNeeded()
        return controller
    }

    private func type(_ text: String, into controller: GreetingViewController) {
        controller.nameField.text = text
        controller.nameField.sendActions(for: .editingChanged)
        controller.view.layoutIfNeeded()
    }

    @Test("starts with Greet disabled and no greeting")
    func initialState() {
        let controller = makeLaidOutController()
        #expect(controller.title == "<app-name>")
        #expect(!controller.greetButton.isEnabled)
        #expect(controller.greetingLabel.text?.isEmpty != false)
        #expect(controller.errorLabel.isHidden)
    }

    @Test("typing writes the view model; Observation tracking re-renders the view")
    func greetButton() {
        let controller = makeLaidOutController()
        type("Ada", into: controller)
        #expect(controller.viewModel.name == "Ada")
        #expect(controller.greetButton.isEnabled)
        controller.greetButton.sendActions(for: .primaryActionTriggered)
        controller.view.layoutIfNeeded()
        #expect(controller.greetingLabel.text == "Hello, Ada!")
    }

    @Test("Return greets only when the name can be greeted", arguments: [("Ada", "Hello, Ada!"), ("  ", "")])
    func returnKey(name: String, expected: String) {
        let controller = makeLaidOutController()
        type(name, into: controller)
        #expect(controller.textFieldShouldReturn(controller.nameField))
        controller.view.layoutIfNeeded()
        #expect((controller.greetingLabel.text ?? "") == expected)
    }

    @Test("a blank name shows the validation error")
    func blankName() {
        let controller = makeLaidOutController()
        type("  ", into: controller)
        controller.greet()
        controller.view.layoutIfNeeded()
        #expect(!controller.errorLabel.isHidden)
        #expect(controller.errorLabel.text == "Enter a name first.")
    }
}
```


These MVVM tests never refresh the view by hand — they only call `layoutIfNeeded()`, so they pass **only** when
Observation tracking actually re-runs `viewWillLayoutSubviews()`. Verified: with `min-deployment-target: 18.0` on
an iOS 18.5 simulator they pass with `UIObservationTrackingEnabled` and three of them fail without it.


### `Targets/iOS/Tests/AppShellTests.swift` (ui: uikit)

```swift
import Testing
import UIKit

@testable import <AppName>

@MainActor
@Suite("App shell")
struct AppShellTests {
    @Test("Info.plist declares the scene manifest with SceneDelegate")
    func sceneManifest() throws {
        let manifest = try #require(
            Bundle.main.object(forInfoDictionaryKey: "UIApplicationSceneManifest") as? [String: Any])
        let configurations = try #require(manifest["UISceneConfigurations"] as? [String: Any])
        let roles = try #require(configurations["UIWindowSceneSessionRoleApplication"] as? [[String: Any]])
        let delegateClassName = try #require(roles.first?["UISceneDelegateClassName"] as? String)
        #expect(NSClassFromString(delegateClassName) == SceneDelegate.self)
    }

    @Test("every window starts at the greeting screen inside a navigation controller")
    func rootViewController() {
        let root = SceneDelegate.makeRootViewController()
        #expect(root.topViewController is GreetingViewController)
    }

    @Test("the app delegate finishes launching")
    func appDelegate() {
        #expect(AppDelegate().application(UIApplication.shared, didFinishLaunchingWithOptions: nil))
    }
}
```

### `Targets/<Platform>/UITests/<AppName>UITests.swift` (every platform)

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
        #if os(macOS)
            // Start from a fresh window instead of restoring the last session. Keep --uitesting LAST: the
            // argument domain reads "-key value" pairs, so a leading "--uitesting" would swallow the next flag.
            app.launchArguments += ["-ApplePersistenceIgnoreState", "YES"]
        #endif
        app.launchArguments.append("--uitesting")
        app.launch()
        return app
    }

    #if os(watchOS)
        @MainActor
        func testShowsTheGreetingScreen() throws {
            let app = launchApp()
            let greetButton = app.buttons["greetButton"]
            XCTAssertTrue(greetButton.waitForExistence(timeout: 10))
            XCTAssertFalse(greetButton.isEnabled)
        }
    #else
        @MainActor
        func testGreetsTheTypedName() throws {
            let app = launchApp()
            let nameField = app.textFields["nameField"]
            XCTAssertTrue(nameField.waitForExistence(timeout: 10))
            XCTAssertFalse(app.buttons["greetButton"].isEnabled)

            press(nameField)
            nameField.typeText("Ada")
            press(app.buttons["greetButton"])

            let greeting = app.staticTexts["greetingLabel"]
            XCTAssertTrue(greeting.waitForExistence(timeout: 5))
            #if os(macOS)
                XCTAssertEqual(greeting.value as? String, "Hello, Ada!")
            #else
                XCTAssertEqual(greeting.label, "Hello, Ada!")
            #endif
        }

        /// Taps on iOS and visionOS, clicks on macOS.
        @MainActor
        private func press(_ element: XCUIElement) {
            #if os(macOS)
                element.click()
            #else
                element.tap()
            #endif
        }
    #endif
}
```
