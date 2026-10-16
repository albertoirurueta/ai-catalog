# `shared/` module templates

The KMP module: Android target via `com.android.kotlin.multiplatform.library` + `com.android.lint`, `iosArm64`/`iosSimulatorArm64` static framework `Shared`, sample code and a test in every source set.

Conditional markers (`// >>> ui: compose` … `// <<< ui: compose`, `# >>> sonar` …) and `__pkg__` work as described in SKILL.md's "Reference files" section; every file below was rendered and built for both `ui` values on 2026-10-15.

### `shared/build.gradle.kts`

```kotlin
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    alias(libs.plugins.kotlin.multiplatform)
    alias(libs.plugins.android.kotlinMultiplatformLibrary)
    // The KMP library plugin registers no lint task on its own — this adds :shared:lint.
    alias(libs.plugins.android.lint)
    // >>> ui: compose
    alias(libs.plugins.compose.multiplatform)
    alias(libs.plugins.kotlin.compose)
    // <<< ui: compose
    alias(libs.plugins.detekt)
    alias(libs.plugins.ktlint)
    alias(libs.plugins.kover)
    alias(libs.plugins.dokka)
}

kotlin {
    android {
        namespace = "<namespace>.shared"
        compileSdk = libs.versions.android.compileSdk.get().toInt()
        minSdk = libs.versions.android.minSdk.get().toInt()

        // JVM host tests for androidMain + commonMain (task: testAndroidHostTest, source set: androidHostTest).
        withHostTest {}

        compilerOptions {
            jvmTarget.set(JvmTarget.JVM_17)
        }
    }

    listOf(
        iosArm64(),
        iosSimulatorArm64(),
    ).forEach { iosTarget ->
        iosTarget.binaries.framework {
            baseName = "Shared"
            isStatic = true
        }
    }

    sourceSets {
        commonMain.dependencies {
            // >>> ui: compose
            implementation(libs.compose.runtime)
            implementation(libs.compose.foundation)
            implementation(libs.compose.ui)
            implementation(libs.compose.material3)
            implementation(libs.compose.uiToolingPreview)
            // <<< ui: compose
        }
        commonTest.dependencies {
            implementation(libs.kotlin.test)
        }
        getByName("androidHostTest").dependencies {
            implementation(libs.kotlin.testJunit)
            implementation(libs.junit)
        }
    }
}

detekt {
    config.setFrom(rootProject.files("detekt.yml"))
    buildUponDefaultConfig = true
    source.setFrom(
        "src/commonMain/kotlin",
        "src/androidMain/kotlin",
        "src/iosMain/kotlin",
        "src/commonTest/kotlin",
        "src/androidHostTest/kotlin",
        "src/iosTest/kotlin",
    )
}

// Same exclusions as the root aggregate, so this module's own report (`koverXmlReport`) agrees with it.
kover {
    reports {
        filters {
            excludes {
                annotatedBy("androidx.compose.runtime.Composable")
                classes("*ComposableSingletons*", "*.BuildConfig")
            }
        }
    }
}

dokka {
    moduleName.set("shared")
    moduleVersion.set(providers.gradleProperty("VERSION_NAME"))
}
```

### `shared/src/androidHostTest/kotlin/__pkg__/AndroidPlatformTest.kt`

```kotlin
package <namespace>

import org.junit.Assert.assertTrue
import org.junit.Test

class AndroidPlatformTest {
    @Test
    fun nameStartsWithAndroid() {
        assertTrue(getPlatform().name.startsWith("Android "))
    }
}
```

### `shared/src/androidMain/kotlin/__pkg__/AndroidPlatform.kt`

```kotlin
package <namespace>

import android.os.Build

/**
 * Android [Platform], named after the device's API level.
 */
class AndroidPlatform : Platform {
    override val name: String = "Android ${Build.VERSION.SDK_INT}"
}

actual fun getPlatform(): Platform = AndroidPlatform()
```

### `shared/src/commonMain/kotlin/__pkg__/App.kt` (ui: compose)

```kotlin
package <namespace>

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview

/**
 * Root composable shared by the Android and iOS apps.
 */
@Composable
fun App() {
    MaterialTheme {
        var state by remember { mutableStateOf(GreetingUiState.initial()) }
        GreetingScreen(state = state, onClick = { state = state.clicked() })
    }
}

/**
 * Stateless greeting screen.
 */
@Composable
fun GreetingScreen(
    state: GreetingUiState,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(modifier = modifier.fillMaxSize()) {
        Column(
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(text = state.message, style = MaterialTheme.typography.headlineSmall)
            Button(onClick = onClick) {
                Text(text = state.buttonLabel)
            }
        }
    }
}

@Preview
@Composable
private fun GreetingScreenPreview() {
    GreetingScreen(state = GreetingUiState(message = "Hello, Preview!"), onClick = {})
}
```

### `shared/src/commonMain/kotlin/__pkg__/Greeting.kt`

```kotlin
package <namespace>

/**
 * Builds the greeting shown on the app's first screen.
 *
 * Overloads instead of default arguments: Kotlin default values are not visible from Swift.
 *
 * @property platform the platform to greet.
 */
class Greeting(
    private val platform: Platform,
) {
    /** Greets the platform the code is currently running on. */
    constructor() : this(getPlatform())

    /**
     * Returns a greeting naming the platform.
     */
    fun greet(): String = "Hello, ${platform.name}!"
}
```

### `shared/src/commonMain/kotlin/__pkg__/GreetingUiState.kt`

```kotlin
package <namespace>

/**
 * Immutable UI state for the greeting screen, shared by the Android and iOS UIs.
 *
 * @property message the greeting to display.
 * @property clicks how many times the user tapped the button.
 */
data class GreetingUiState(
    val message: String,
    val clicks: Int = 0,
) {
    /** Label for the counter button. */
    val buttonLabel: String
        get() =
            when (clicks) {
                0 -> "Tap me"
                1 -> "Tapped 1 time"
                else -> "Tapped $clicks times"
            }

    /**
     * Returns the state after one more tap.
     */
    fun clicked(): GreetingUiState = copy(clicks = clicks + 1)

    /** Factories for the initial state (overloads, so Swift sees both). */
    companion object {
        /**
         * Creates the initial state greeting the current platform.
         */
        fun initial(): GreetingUiState = initial(Greeting())

        /**
         * Creates the initial state from [greeting].
         */
        fun initial(greeting: Greeting): GreetingUiState = GreetingUiState(message = greeting.greet())
    }
}
```

### `shared/src/commonMain/kotlin/__pkg__/Platform.kt`

```kotlin
package <namespace>

/**
 * The platform the shared code is currently running on.
 */
interface Platform {
    /** Human-readable platform name, e.g. `Android 36` or `iOS 26.4`. */
    val name: String
}

/**
 * Returns the [Platform] implementation for the current target.
 */
expect fun getPlatform(): Platform
```

### `shared/src/commonTest/kotlin/__pkg__/GreetingTest.kt`

```kotlin
package <namespace>

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class GreetingTest {
    private val fakePlatform =
        object : Platform {
            override val name: String = "Test"
        }

    @Test
    fun greetNamesThePlatform() {
        assertEquals("Hello, Test!", Greeting(fakePlatform).greet())
    }

    @Test
    fun defaultGreetingUsesTheCurrentPlatform() {
        assertTrue(Greeting().greet().startsWith("Hello, "))
    }
}
```

### `shared/src/commonTest/kotlin/__pkg__/GreetingUiStateTest.kt`

```kotlin
package <namespace>

import kotlin.test.Test
import kotlin.test.assertEquals

class GreetingUiStateTest {
    private val greeting =
        Greeting(
            object : Platform {
                override val name: String = "Test"
            },
        )

    @Test
    fun initialStateHasNoClicks() {
        val state = GreetingUiState.initial(greeting)

        assertEquals("Hello, Test!", state.message)
        assertEquals(0, state.clicks)
        assertEquals("Tap me", state.buttonLabel)
    }

    @Test
    fun clickedIncrementsTheCounter() {
        val once = GreetingUiState.initial(greeting).clicked()
        val twice = once.clicked()

        assertEquals("Tapped 1 time", once.buttonLabel)
        assertEquals("Tapped 2 times", twice.buttonLabel)
    }

    @Test
    fun defaultInitialStateGreetsTheCurrentPlatform() {
        assertEquals(Greeting().greet(), GreetingUiState.initial().message)
    }
}
```

### `shared/src/iosMain/kotlin/__pkg__/IOSPlatform.kt`

```kotlin
package <namespace>

import platform.UIKit.UIDevice

/**
 * iOS [Platform], named after the running system and version.
 */
class IOSPlatform : Platform {
    override val name: String =
        UIDevice.currentDevice.systemName() + " " + UIDevice.currentDevice.systemVersion
}

actual fun getPlatform(): Platform = IOSPlatform()
```

### `shared/src/iosMain/kotlin/__pkg__/MainViewController.kt` (ui: compose)

```kotlin
package <namespace>

import androidx.compose.ui.window.ComposeUIViewController
import platform.UIKit.UIViewController

/**
 * Entry point the iOS app embeds (see iosApp/iosApp/ContentView.swift).
 */
@Suppress("FunctionName", "ktlint:standard:function-naming")
fun MainViewController(): UIViewController = ComposeUIViewController { App() }
```

### `shared/src/iosTest/kotlin/__pkg__/IOSPlatformTest.kt`

```kotlin
package <namespace>

import kotlin.test.Test
import kotlin.test.assertTrue

class IOSPlatformTest {
    @Test
    fun nameIsNotBlank() {
        assertTrue(getPlatform().name.isNotBlank())
    }
}
```
