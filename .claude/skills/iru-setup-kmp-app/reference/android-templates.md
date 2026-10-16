# `androidApp/` module templates

The Android application (AGP 9 built-in Kotlin — no `org.jetbrains.kotlin.android` plugin).

Conditional markers (`// >>> ui: compose` … `// <<< ui: compose`, `# >>> sonar` …) and `__pkg__` work as described in SKILL.md's "Reference files" section; every file below was rendered and built for both `ui` values on 2026-10-15.

### `androidApp/build.gradle.kts`

```kotlin
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    // AGP 9 compiles Kotlin itself (built-in Kotlin) — no org.jetbrains.kotlin.android plugin.
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.detekt)
    alias(libs.plugins.ktlint)
    alias(libs.plugins.kover)
}

// Read once at configuration time. The release signing config only exists when all four are set, so
// `assembleDebug`/`assembleRelease` never fail on a machine without signing secrets (release is left unsigned).
val signingStoreFile: String? = System.getenv("SIGNING_STORE_FILE")
val signingStorePassword: String? = System.getenv("SIGNING_STORE_PASSWORD")
val signingKeyAlias: String? = System.getenv("SIGNING_KEY_ALIAS")
val signingKeyPassword: String? = System.getenv("SIGNING_KEY_PASSWORD")
val hasReleaseSigning: Boolean =
    !signingStoreFile.isNullOrBlank() &&
        !signingStorePassword.isNullOrBlank() &&
        !signingKeyAlias.isNullOrBlank() &&
        !signingKeyPassword.isNullOrBlank()

android {
    namespace = "<namespace>.android"
    compileSdk = libs.versions.android.compileSdk.get().toInt()

    defaultConfig {
        applicationId = "<application-id>"
        minSdk = libs.versions.android.minSdk.get().toInt()
        targetSdk = libs.versions.android.targetSdk.get().toInt()
        // Single source of truth: root gradle.properties (iru-kmp-bump-version rewrites it).
        versionCode = providers.gradleProperty("VERSION_CODE").get().toInt()
        versionName = providers.gradleProperty("VERSION_NAME").get()
    }

    signingConfigs {
        if (hasReleaseSigning) {
            create("release") {
                storeFile = file(signingStoreFile!!)
                storePassword = signingStorePassword
                keyAlias = signingKeyAlias
                keyPassword = signingKeyPassword
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            if (hasReleaseSigning) {
                signingConfig = signingConfigs.getByName("release")
            }
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        compose = true
    }

    testOptions {
        unitTests {
            // Robolectric needs the merged resources/manifest.
            isIncludeAndroidResources = true
        }
    }

    lint {
        // Reports (lint-results-debug.xml/.sarif/.html) are always written by AGP 9. New-version-available warnings are Dependabot's job, not a build failure.
        disable += setOf("GradleDependency", "NewerVersionAvailable", "AndroidGradlePluginVersion")
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

detekt {
    config.setFrom(rootProject.files("detekt.yml"))
    buildUponDefaultConfig = true
    source.setFrom("src/main/kotlin", "src/test/kotlin")
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

dependencies {
    implementation(projects.shared)
    implementation(libs.androidx.activity.compose)
    // >>> ui: native
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.uiToolingPreview)
    debugImplementation(libs.androidx.compose.uiTooling)
    // <<< ui: native

    testImplementation(libs.junit)
    testImplementation(libs.robolectric)
    testImplementation(libs.androidx.test.core)
}
```

### `androidApp/proguard-rules.pro`

```proguard
# Project-specific ProGuard/R8 rules. Release builds ship with isMinifyEnabled = false until rules are written here.
```

### `androidApp/src/main/AndroidManifest.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:roundIcon="@mipmap/ic_launcher"
        android:supportsRtl="true"
        android:theme="@android:style/Theme.Material.Light.NoActionBar">
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>

</manifest>
```

### `androidApp/src/main/kotlin/__pkg__/android/MainActivity.kt` (ui: compose)

```kotlin
package <namespace>.android

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import <namespace>.App

/**
 * Hosts the shared Compose Multiplatform [App].
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        setContent {
            App()
        }
    }
}
```

### `androidApp/src/main/kotlin/__pkg__/android/MainActivity.kt` (ui: native)

```kotlin
package <namespace>.android

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
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
import <namespace>.GreetingUiState

/**
 * Native Android UI (Jetpack Compose) over the shared [GreetingUiState].
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                var state by remember { mutableStateOf(GreetingUiState.initial()) }
                GreetingScreen(state = state, onClick = { state = state.clicked() })
            }
        }
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

### `androidApp/src/main/res/drawable/ic_launcher_foreground.xml`

```xml
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="@color/ic_launcher_foreground"
        android:pathData="M44,34h20v10h-20z M44,49h20v10h-20z M44,64h20v10h-20z" />
</vector>
```

### `androidApp/src/main/res/mipmap-anydpi-v26/ic_launcher.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background" />
    <foreground android:drawable="@drawable/ic_launcher_foreground" />
    <monochrome android:drawable="@drawable/ic_launcher_foreground" />
</adaptive-icon>
```

### `androidApp/src/main/res/values/colors.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="ic_launcher_background">#FF6750A4</color>
    <color name="ic_launcher_foreground">#FFFFFFFF</color>
</resources>
```

### `androidApp/src/main/res/values/strings.xml`

```xml
<resources>
    <string name="app_name"><app-name></string>
</resources>
```

### `androidApp/src/test/kotlin/__pkg__/android/MainActivityTest.kt`

```kotlin
package <namespace>.android

import org.junit.Assert.assertFalse
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class MainActivityTest {
    @Test
    fun activityStartsAndRendersContent() {
        Robolectric.buildActivity(MainActivity::class.java).use { controller ->
            val activity = controller.setup().get()

            assertFalse(activity.isFinishing)
        }
    }
}
```

### `androidApp/src/test/resources/robolectric.properties`

```properties
sdk=<robolectric-sdk>
```
