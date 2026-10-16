# UI-test templates — `ui-tests: flaui`

`tests/__AppName__.UITests`: MSTest 4 + **FlaUI** (`FlaUI.UIA3`, a third-party UI Automation wrapper — Microsoft has
no current desktop UI-test recommendation: WinAppDriver has had no release since 2020 and is effectively
unmaintained; the Appium Windows Driver is the other option). Every test class is `[TestCategory("UI")]` so ordinary
runs exclude it (`--filter "TestCategory!=UI"`) and the UI gate selects it (`--filter "TestCategory=UI"`); the
assembly is `[DoNotParallelize]` because UI automation drives the real desktop session, and every run must hold the
repository-wide `.integration-test.lock`. `[OSCondition(OperatingSystems.Windows)]` makes MSTest report every test as
skipped (ignored) off Windows — never passed; MSTest's analyzer (MSTEST0061) prefers it to a runtime
`OperatingSystem.IsWindows()` check plus `Assert.Inconclusive`.

The app under test is located through, in order: `APP_AUMID` (a deployed MSIX package's AppUserModelID,
`<PackageFamilyName>!App` — required for `ui: winui`, whose packaged exe cannot start without package identity),
`APP_EXE` (an explicit exe path), or the newest `src/__AppName__/bin/{Release,Debug}/**/__AppName__.exe`
(`ui: wpf|winforms` only). Automation ids are shared by every `ui`: `nameTextBox`, `greetButton`, `messageLabel`
(WPF/WinUI set `AutomationProperties.AutomationId`; WinForms exposes the control's `Name`).

Compiled on macOS (`EnableWindowsTargeting`) on 2026-10-16; executing the tests is unverified locally (needs an
interactive Windows desktop).

### `tests/__AppName__.UITests/__AppName__.UITests.csproj` (flaui)

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net10.0-windows</TargetFramework>
    <RootNamespace>__RootNamespace__.UITests</RootNamespace>
    <IsPackable>false</IsPackable>
    <!-- FlaUI needs the Microsoft.WindowsDesktop.App runtime, which exists only on Windows: elsewhere the project
         still compiles but is not a test project, so a solution-wide dotnet test does not abort on it. -->
    <IsTestProject Condition="!$([MSBuild]::IsOSPlatform('Windows'))">false</IsTestProject>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="MSTest" />
    <PackageReference Include="FlaUI.UIA3" />
  </ItemGroup>

  <ItemGroup>
    <Using Include="Microsoft.VisualStudio.TestTools.UnitTesting" />
  </ItemGroup>
</Project>
```

### `tests/__AppName__.UITests/MSTestSettings.cs` (flaui)

```csharp
// UI automation drives the one interactive desktop session: never run these tests in parallel.
[assembly: DoNotParallelize]
```

### `tests/__AppName__.UITests/AppLauncher.cs` (flaui)

```csharp
using FlaUI.Core;

namespace __RootNamespace__.UITests;

/// <summary>
/// Starts the app under test: <c>APP_AUMID</c> (deployed MSIX), then <c>APP_EXE</c>, then the newest built exe.
/// </summary>
internal static class AppLauncher
{
    private const string AppName = "__AppName__";

    public static Application Launch()
    {
        var aumid = Environment.GetEnvironmentVariable("APP_AUMID");
        if (!string.IsNullOrWhiteSpace(aumid))
        {
            return Application.LaunchStoreApp(aumid);
        }

        var exe = Environment.GetEnvironmentVariable("APP_EXE");
        if (!string.IsNullOrWhiteSpace(exe))
        {
            return Application.Launch(exe);
        }

        // >>> ui: winui
        throw new InvalidOperationException(
            "Set APP_AUMID to the deployed package's AppUserModelID (<PackageFamilyName>!App) — a packaged WinUI " +
            "exe cannot start without package identity — or APP_EXE to an unpackaged build.");
        // <<< ui: winui
        // >>> ui: wpf|winforms
        return Application.Launch(FindBuiltExe());
        // <<< ui: wpf|winforms
    }
    // >>> ui: wpf|winforms

    private static string FindBuiltExe()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null && !File.Exists(Path.Combine(directory.FullName, $"{AppName}.slnx")))
        {
            directory = directory.Parent;
        }

        if (directory is null)
        {
            throw new InvalidOperationException($"Could not find {AppName}.slnx above {AppContext.BaseDirectory}.");
        }

        var bin = new DirectoryInfo(Path.Combine(directory.FullName, "src", AppName, "bin"));
        var newest = bin.Exists
            ? bin.EnumerateFiles($"{AppName}.exe", SearchOption.AllDirectories)
                .OrderByDescending(file => file.LastWriteTimeUtc)
                .FirstOrDefault()
            : null;
        return newest?.FullName
            ?? throw new FileNotFoundException(
                $"Build the app first (dotnet build src/{AppName} -c Release) or set APP_EXE.", $"{AppName}.exe");
    }
    // <<< ui: wpf|winforms
}
```

### `tests/__AppName__.UITests/MainWindowTests.cs` (flaui)

```csharp
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Tools;
using FlaUI.UIA3;

namespace __RootNamespace__.UITests;

[TestClass]
[TestCategory("UI")]
[OSCondition(OperatingSystems.Windows)]
public sealed class MainWindowTests
{
    private static readonly TimeSpan Timeout = TimeSpan.FromSeconds(30);

    [TestMethod]
    public void Greet_ShowsTheGreetingForTheTypedName()
    {
        using var app = AppLauncher.Launch();
        using var automation = new UIA3Automation();
        try
        {
            var window = app.GetMainWindow(automation, Timeout)
                ?? throw new AssertFailedException("The main window did not appear.");
            var nameTextBox = Find(window, "nameTextBox").AsTextBox();
            var greetButton = Find(window, "greetButton").AsButton();
            var messageLabel = Find(window, "messageLabel");

            nameTextBox.Enter("Ada");
            Retry.WhileFalse(() => greetButton.IsEnabled, Timeout, throwOnTimeout: true);
            greetButton.Invoke();

            var shown = Retry.WhileFalse(() => messageLabel.Name == "Hello, Ada!", Timeout);
            Assert.IsTrue(shown.Result, $"Expected the greeting, found '{messageLabel.Name}'.");
        }
        finally
        {
            app.Close();
        }
    }

    private static AutomationElement Find(Window window, string automationId) =>
        Retry.WhileNull(() => window.FindFirstDescendant(condition => condition.ByAutomationId(automationId)), Timeout)
            .Result
        ?? throw new AssertFailedException($"No element with automation id '{automationId}'.");
}
```
