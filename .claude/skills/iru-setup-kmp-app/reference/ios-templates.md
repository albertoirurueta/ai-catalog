# `iosApp/` templates

The SwiftUI host app. `iosApp/project.yml` is the XcodeGen manifest; run `xcodegen generate` inside `iosApp/` to create the (gitignored) `iosApp.xcodeproj`. `Info.plist` is a committed file, not XcodeGen-generated.

Conditional markers (`// >>> ui: compose` … `// <<< ui: compose`, `# >>> sonar` …) and `__pkg__` work as described in SKILL.md's "Reference files" section; every file below was rendered and built for both `ui` values on 2026-10-15.

### `iosApp/project.yml`

```yaml
name: iosApp
options:
  deploymentTarget:
    iOS: "<ios-deployment-target>"
  createIntermediateGroups: true
configFiles:
  Debug: Configuration/Config.xcconfig
  Release: Configuration/Config.xcconfig
settings:
  base:
    SWIFT_VERSION: "6.0"
    # Kotlin/Native frameworks are built by Gradle, not Xcode: the pre-build script below needs to run outside
    # Xcode's user-script sandbox.
    ENABLE_USER_SCRIPT_SANDBOXING: NO
targets:
  iosApp:
    type: application
    platform: iOS
    sources:
      - path: iosApp
        excludes:
          - Info.plist
    settings:
      base:
        # PRODUCT_NAME stays the target name (iosApp.app) — the test bundle's TEST_HOST points at it; the launcher
        # label comes from CFBundleDisplayName = $(APP_NAME) in Info.plist.
        PRODUCT_MODULE_NAME: iosApp
        PRODUCT_BUNDLE_IDENTIFIER: "$(BUNDLE_ID)"
        DEVELOPMENT_TEAM: "$(TEAM_ID)"
        INFOPLIST_FILE: iosApp/Info.plist
        TARGETED_DEVICE_FAMILY: "1,2"
        # The Shared.framework that :shared:embedAndSignAppleFrameworkForXcode builds for this configuration/SDK.
        FRAMEWORK_SEARCH_PATHS:
          - "$(inherited)"
          - "$(SRCROOT)/../shared/build/xcode-frameworks/$(CONFIGURATION)/$(SDK_NAME)"
        OTHER_LDFLAGS:
          - "$(inherited)"
          - "-framework"
          - "Shared"
    preBuildScripts:
      - name: Compile Kotlin Framework
        basedOnDependencyAnalysis: false
        script: |
          if [ "YES" = "$OVERRIDE_KOTLIN_BUILD_IDE_SUPPORTED" ]; then
            echo "Skipping Gradle build task invocation due to OVERRIDE_KOTLIN_BUILD_IDE_SUPPORTED environment variable set to \"YES\""
            exit 0
          fi
          cd "$SRCROOT/.."
          ./gradlew :shared:embedAndSignAppleFrameworkForXcode
  iosAppTests:
    type: bundle.unit-test
    platform: iOS
    sources:
      - path: iosAppTests
    dependencies:
      - target: iosApp
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: "$(BUNDLE_ID).tests"
        DEVELOPMENT_TEAM: "$(TEAM_ID)"
        GENERATE_INFOPLIST_FILE: YES
        # Import-only: the static Shared framework is already linked into the host app (BUNDLE_LOADER).
        FRAMEWORK_SEARCH_PATHS:
          - "$(inherited)"
          - "$(SRCROOT)/../shared/build/xcode-frameworks/$(CONFIGURATION)/$(SDK_NAME)"
schemes:
  iosApp:
    build:
      targets:
        iosApp: all
        iosAppTests: [test]
    test:
      config: Debug
      gatherCoverageData: true
      coverageTargets:
        - iosApp
      targets:
        - iosAppTests
    run:
      config: Debug
    archive:
      config: Release
```

### `iosApp/.swiftlint.yml`

```yaml
included:
  - iosApp
  - iosAppTests
excluded:
  - build
  - DerivedData
opt_in_rules:
  - closure_spacing
  - empty_count
  - explicit_init
  - first_where
  - force_unwrapping
  - implicitly_unwrapped_optional
  - overridden_super_call
  - redundant_nil_coalescing
  - sorted_imports
analyzer_rules:
  - unused_import
line_length:
  warning: 120
  error: 160
```

### `iosApp/Configuration/Config.xcconfig`

```text
// App identity and version for the iOS app. iru-kmp-bump-version keeps the two version keys in step with the
// root gradle.properties on every release: MARKETING_VERSION = the release version (never a -SNAPSHOT value —
// App Store Connect rejects it), CURRENT_PROJECT_VERSION = VERSION_CODE.
TEAM_ID=<team-id>
BUNDLE_ID=<bundle-id>
APP_NAME=<app-name>
MARKETING_VERSION=<marketing-version>
CURRENT_PROJECT_VERSION=<version-code>
```

### `iosApp/iosApp/ContentView.swift` (ui: compose)

```swift
import Shared
import SwiftUI
import UIKit

/// Embeds the shared Compose Multiplatform UI (`MainViewController()` in shared/src/iosMain).
struct ComposeView: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> UIViewController {
        MainViewControllerKt.MainViewController()
    }

    func updateUIViewController(_ uiViewController: UIViewController, context: Context) {}
}

struct ContentView: View {
    var body: some View {
        ComposeView()
            .ignoresSafeArea()
    }
}
```

### `iosApp/iosApp/ContentView.swift` (ui: native)

```swift
import SwiftUI

/// Native SwiftUI screen over the shared `GreetingUiState`.
struct ContentView: View {
    @StateObject private var model = GreetingModel()

    var body: some View {
        VStack(spacing: 16) {
            Text(model.state.message)
                .font(.title2)
            Button(model.state.buttonLabel) {
                model.tap()
            }
            .buttonStyle(.borderedProminent)
        }
        .padding()
    }
}

#Preview {
    ContentView()
}
```

### `iosApp/iosApp/GreetingModel.swift` (ui: native)

```swift
import Combine
import Shared

/// SwiftUI-facing wrapper around the shared, immutable `GreetingUiState`.
@MainActor
final class GreetingModel: ObservableObject {
    @Published private(set) var state: GreetingUiState

    init(state: GreetingUiState = GreetingUiState.companion.initial()) {
        self.state = state
    }

    func tap() {
        state = state.clicked()
    }
}
```

### `iosApp/iosApp/Info.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleDevelopmentRegion</key>
	<string>$(DEVELOPMENT_LANGUAGE)</string>
	<key>CFBundleDisplayName</key>
	<string>$(APP_NAME)</string>
	<key>CFBundleExecutable</key>
	<string>$(EXECUTABLE_NAME)</string>
	<key>CFBundleIdentifier</key>
	<string>$(PRODUCT_BUNDLE_IDENTIFIER)</string>
	<key>CFBundleInfoDictionaryVersion</key>
	<string>6.0</string>
	<key>CFBundleName</key>
	<string>$(PRODUCT_NAME)</string>
	<key>CFBundlePackageType</key>
	<string>$(PRODUCT_BUNDLE_PACKAGE_TYPE)</string>
	<key>CFBundleShortVersionString</key>
	<string>$(MARKETING_VERSION)</string>
	<key>CFBundleVersion</key>
	<string>$(CURRENT_PROJECT_VERSION)</string>
	<key>LSRequiresIPhoneOS</key>
	<true/>
	<key>CADisableMinimumFrameDurationOnPhone</key>
	<true/>
	<key>ITSAppUsesNonExemptEncryption</key>
	<false/>
	<key>UILaunchScreen</key>
	<dict/>
	<key>UISupportedInterfaceOrientations</key>
	<array>
		<string>UIInterfaceOrientationPortrait</string>
		<string>UIInterfaceOrientationLandscapeLeft</string>
		<string>UIInterfaceOrientationLandscapeRight</string>
	</array>
	<key>UISupportedInterfaceOrientations~ipad</key>
	<array>
		<string>UIInterfaceOrientationPortrait</string>
		<string>UIInterfaceOrientationPortraitUpsideDown</string>
		<string>UIInterfaceOrientationLandscapeLeft</string>
		<string>UIInterfaceOrientationLandscapeRight</string>
	</array>
</dict>
</plist>
```

### `iosApp/iosApp/MainApp.swift`

```swift
import SwiftUI

@main
struct MainApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
```

### `iosApp/iosAppTests/iosAppTests.swift` (ui: compose)

```swift
@testable import iosApp
import Shared
import UIKit
import XCTest

final class IosAppTests: XCTestCase {
    func testSharedGreetingNamesThePlatform() {
        XCTAssertTrue(Greeting().greet().hasPrefix("Hello, "))
    }

    @MainActor
    func testComposeViewControllerIsCreated() {
        let controller = MainViewControllerKt.MainViewController()
        XCTAssertNotNil(controller.view)
    }
}
```

### `iosApp/iosAppTests/iosAppTests.swift` (ui: native)

```swift
@testable import iosApp
import Shared
import XCTest

final class IosAppTests: XCTestCase {
    @MainActor
    func testInitialStateGreetsThePlatform() {
        let model = GreetingModel()
        XCTAssertTrue(model.state.message.hasPrefix("Hello, "))
        XCTAssertEqual(model.state.clicks, 0)
    }

    @MainActor
    func testTapIncrementsTheCounter() {
        let model = GreetingModel()
        model.tap()
        XCTAssertEqual(model.state.clicks, 1)
        XCTAssertEqual(model.state.buttonLabel, "Tapped 1 time")
    }
}
```
