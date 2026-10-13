# Shared tooling templates (plugin and theme)

Files both flavors get. Placeholders are listed in SKILL.md Step 5; `<code-paths>` differs per flavor:

| Placeholder | `flavor: plugin` | `flavor: theme` |
|---|---|---|
| `<composer-type>` | `wordpress-plugin` | `wordpress-theme` |
| `<phpstan-paths>` | `<slug>.php`, `uninstall.php`, `src`, `tests` | `functions.php`, `src`, `patterns`, `tests` |
| `<wp-env-key>` | `plugins` | `themes` |
| `<wp-content-dir>` | `wp-content/plugins` | `wp-content/themes` |
| `<sonar-sources>` | `src,<slug>.php,uninstall.php` | `src,functions.php,patterns` |

All of it was generated with these exact templates and verified (see SKILL.md "Verification notes").

## `composer.json`

```json
{
    "name": "<vendor>/<slug>",
    "description": "<description>",
    "type": "<composer-type>",
    "license": "<license-spdx>",
    "authors": [
        {
            "name": "<developer-name>",
            "email": "<developer-email>",
            "homepage": "<organization-url>"
        }
    ],
    "require": {
        "php": ">=<php-floor>"
    },
    "require-dev": {
        "brain/monkey": "^2.7",
        "dealerdirect/phpcodesniffer-composer-installer": "^1.2",
        "php-stubs/wordpress-tests-stubs": "^7.1",
        "phpcompatibility/phpcompatibility-wp": "^2.1",
        "phpstan/extension-installer": "^1.4",
        "phpstan/phpstan": "^2.3",
        "phpunit/phpunit": "^9.6",
        "szepeviktor/phpstan-wordpress": "^2.0",
        "wp-coding-standards/wpcs": "^3.4",
        "yoast/phpunit-polyfills": "^4.0"
    },
    "autoload": {
        "psr-4": {
            "<namespace-json>\\": "src/"
        }
    },
    "autoload-dev": {
        "psr-4": {
            "<namespace-json>\\Tests\\": "tests/"
        }
    },
    "config": {
        "platform": {
            "php": "<php-floor>.0"
        },
        "sort-packages": true,
        "optimize-autoloader": true,
        "allow-plugins": {
            "dealerdirect/phpcodesniffer-composer-installer": true,
            "phpstan/extension-installer": true
        }
    },
    "scripts": {
        "test": "phpunit",
        "test:coverage": "phpunit --coverage-clover build/logs/clover.xml --coverage-text",
        "test:integration": "npm run test:integration",
        "lint": "phpstan analyse --memory-limit=1G",
        "lint:report": [
            "@php -r \"is_dir('build/logs') || mkdir('build/logs', 0777, true);\"",
            "@php vendor/bin/phpstan analyse --no-progress --memory-limit=1G --error-format=json > build/logs/phpstan.json"
        ],
        "format": "phpcbf",
        "format:check": "phpcs"
    },
    "scripts-descriptions": {
        "test": "Runs the fast unit suite (Brain Monkey, no WordPress loaded).",
        "test:coverage": "Runs the unit suite with coverage (needs PCOV or Xdebug) and writes build/logs/clover.xml.",
        "test:integration": "Runs the WP_UnitTestCase suite inside @wordpress/env (needs Docker and a started test environment).",
        "lint": "Runs PHPStan (phpstan-wordpress, level 6).",
        "lint:report": "Writes the PHPStan result as JSON to build/logs/phpstan.json (read by Sonar).",
        "format": "Fixes WordPress Coding Standards violations PHPCBF can fix.",
        "format:check": "Checks WordPress Coding Standards, PHPCompatibilityWP, i18n and prefixes."
    }
}
```

- Each `require-dev` constraint becomes `^<major>.<minor>` of the version Step 4 resolved — **except
  `phpunit/phpunit`, which stays `^9.6`** (Step 4's PHPUnit caveat) — and `yoast/phpunit-polyfills` must keep a
  major that supports PHPUnit 9 (4.x does).
- `<namespace-json>` is the namespace with every `\` doubled (`Acme\\Loans`).
- `config.platform.php` pins resolution to the floor so a newer local/CI PHP never locks a dependency the floor
  can't run. No `"version"` field — the plugin header / `style.css` carries the version (catalog convention).
- No `require` beyond `php`: the scaffold ships no runtime Composer dependency. See SKILL.md Step 5's "Composer
  dependencies inside WordPress" before adding one.
- `phpcbf` exits `1` when it fixed something, so `composer format` reports a "failure" after a successful fix —
  re-run `composer format:check` to confirm it's clean.
- **License "No license" (proprietary)**: `"license": "proprietary"`.

## `phpcs.xml.dist`

```xml
<?xml version="1.0"?>
<ruleset name="<name>">
	<description>WordPress Coding Standards for <name>.</description>

	<file>.</file>

	<exclude-pattern>/vendor/*</exclude-pattern>
	<exclude-pattern>/node_modules/*</exclude-pattern>
	<exclude-pattern>/build/*</exclude-pattern>
	<exclude-pattern>/docs/*</exclude-pattern>
	<exclude-pattern>/.claude/*</exclude-pattern>

	<arg name="extensions" value="php"/>
	<arg name="basepath" value="."/>
	<arg name="parallel" value="8"/>
	<arg value="sp"/>

	<!-- Lowest PHP and WordPress versions supported: keep in sync with the Requires PHP / Requires at least headers. -->
	<config name="testVersion" value="<php-floor>-"/>
	<config name="minimum_wp_version" value="<wp-floor>"/>

	<rule ref="WordPress-Extra"/>
	<rule ref="WordPress-Docs"/>
	<rule ref="PHPCompatibilityWP"/>

	<rule ref="WordPress.WP.I18n">
		<properties>
			<property name="text_domain" type="array">
				<element value="<slug>"/>
			</property>
		</properties>
	</rule>

	<rule ref="WordPress.NamingConventions.PrefixAllGlobals">
		<properties>
			<property name="prefixes" type="array">
				<element value="<prefix>"/>
				<element value="<namespace>"/>
			</property>
		</properties>
	</rule>

	<!-- PSR-4: class files are named after their class, not class-*.php. -->
	<rule ref="WordPress.Files.FileName">
		<exclude-pattern>/src/*</exclude-pattern>
		<exclude-pattern>/tests/*</exclude-pattern>
	</rule>

	<!-- Tests are not shipped and document themselves through their names. -->
	<rule ref="Squiz.Commenting">
		<exclude-pattern>/tests/*</exclude-pattern>
	</rule>
	<rule ref="Generic.Commenting.DocComment">
		<exclude-pattern>/tests/*</exclude-pattern>
	</rule>
	<!-- Tests fake request input, fire core hooks and use plain PHP file functions; production code keeps these rules. -->
	<rule ref="WordPress.Security.NonceVerification">
		<exclude-pattern>/tests/*</exclude-pattern>
	</rule>
	<rule ref="WordPress.Security.EscapeOutput">
		<exclude-pattern>/tests/*</exclude-pattern>
	</rule>
	<rule ref="WordPress.NamingConventions.PrefixAllGlobals">
		<exclude-pattern>/tests/*</exclude-pattern>
	</rule>
	<rule ref="WordPress.WP.AlternativeFunctions">
		<exclude-pattern>/tests/*</exclude-pattern>
	</rule>
</ruleset>
```

- WordPress-Extra already contains WordPress-Core; WordPress-Docs adds the inline-documentation sniffs
  `iru-php-phpdoc` relies on. PHPCompatibilityWP 2.x still runs on PHPCompatibility 9.3.x, which predates the newest
  PHP releases: `testVersion` above its known range is accepted (verified with `8.4-`, no warning) but adds no
  checks for syntax it doesn't know yet — PHPStan (which reads the `composer.json` floor) covers that gap.
- WPCS 3.x pins PHP_CodeSniffer 3.x — `composer install` resolves 3.13.x even though PHPCS 4 exists.
- Tests follow the same layout rules (tabs, Yoda, `array()`, `snake_case` methods) — only the documentation,
  security and prefix sniffs are relaxed for `/tests/`, never for shipped code.

## `phpstan.neon.dist`

```neon
# szepeviktor/phpstan-wordpress is registered by phpstan/extension-installer.
parameters:
    level: 6
    paths:
        - <slug>.php
        - uninstall.php
        - src
        - tests
    excludePaths:
        - tests/Integration/bootstrap.php
    scanFiles:
        # WP_UnitTestCase and its factories, for the integration suite.
        - vendor/php-stubs/wordpress-tests-stubs/wordpress-tests-stubs.php
```

`paths` per `<phpstan-paths>` above (theme: `functions.php`, `src`, `patterns`, `tests`). The `.dist` name is
deliberate: PHPStan reads `phpstan.neon` first, so a developer can keep an untracked local override. `blocks/`
(plugin with `blocks: yes`) is deliberately **not** analysed: block `render.php` files read `$attributes`/`$block`
variables WordPress injects, which PHPStan can't see.

## `phpunit.xml.dist` (unit suite — the default for `composer test` and the coverage gate)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<phpunit xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:noNamespaceSchemaLocation="vendor/phpunit/phpunit/phpunit.xsd"
         bootstrap="tests/Unit/bootstrap.php"
         colors="true"
         beStrictAboutOutputDuringTests="true"
         failOnRisky="true"
         failOnWarning="true">
    <testsuites>
        <testsuite name="unit">
            <directory suffix="Test.php">tests/Unit</directory>
        </testsuite>
    </testsuites>
    <coverage processUncoveredFiles="true">
        <include>
            <directory suffix=".php">src</directory>
        </include>
    </coverage>
    <logging>
        <junit outputFile="build/logs/junit.xml"/>
    </logging>
</phpunit>
```

## `phpunit-integration.xml.dist` (integration suite — WordPress loaded, run inside wp-env)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<phpunit xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:noNamespaceSchemaLocation="vendor/phpunit/phpunit/phpunit.xsd"
         bootstrap="tests/Integration/bootstrap.php"
         colors="true"
         failOnRisky="true"
         failOnWarning="true">
    <testsuites>
        <testsuite name="integration">
            <directory suffix="Test.php">tests/Integration</directory>
        </testsuite>
    </testsuites>
    <coverage processUncoveredFiles="true">
        <include>
            <directory suffix=".php">src</directory>
        </include>
    </coverage>
    <logging>
        <junit outputFile="build/logs/junit-integration.xml"/>
    </logging>
</phpunit>
```

**Why two files instead of two suites in one:** a PHPUnit config has exactly one `bootstrap`. The unit suite must
never load WordPress (Brain Monkey/Patchwork can't redefine a function WordPress already declared), and the
integration suite must load it before any test class — so each suite gets its own config. `iru-php-test` /
`iru-php-coverage` select them with `-c phpunit-integration.xml.dist` (or `--testsuite unit` on the default one).
PHPUnit 9 schema (`<coverage processUncoveredFiles>`, `<logging>`) — not the PHPUnit 10+ `<source>` element —
because the WordPress test library still requires PHPUnit 9 (SKILL.md Step 4). PHPUnit creates `build/logs/` itself
(verified on a clean checkout); the result cache stays the default `.phpunit.result.cache` at the root.

## `tests/Unit/bootstrap.php`

```php
<?php
/**
 * Unit-suite bootstrap: Composer autoloader only, WordPress is never loaded.
 *
 * Brain Monkey (loaded through the autoloader) stubs the WordPress functions each test needs.
 *
 * @package <namespace>
 */

require_once dirname( __DIR__, 2 ) . '/vendor/autoload.php';
```

## `tests/Unit/TestCase.php`

```php
<?php
/**
 * Base class of the unit suite.
 *
 * @package <namespace>
 */

namespace <namespace>\Tests\Unit;

use Brain\Monkey;
use Brain\Monkey\Functions;
use Mockery\Adapter\Phpunit\MockeryPHPUnitIntegration;
use Yoast\PHPUnitPolyfills\TestCases\TestCase as PolyfillTestCase;

/**
 * Sets up and tears down Brain Monkey around every test.
 */
abstract class TestCase extends PolyfillTestCase {

	use MockeryPHPUnitIntegration;

	/**
	 * Starts Brain Monkey and stubs the translation and escaping functions.
	 */
	protected function set_up(): void {
		parent::set_up();
		Monkey\setUp();
		Functions\stubTranslationFunctions();
		Functions\stubEscapeFunctions();
	}

	/**
	 * Resets Brain Monkey so expectations never leak between tests.
	 */
	protected function tear_down(): void {
		Monkey\tearDown();
		parent::tear_down();
	}
}
```

The polyfills' `set_up()`/`tear_down()` (snake_case, WPCS-friendly) are the same hooks `WP_UnitTestCase` uses, so
unit and integration tests read alike. PHPUnit 9 means **annotations** (`@covers`, `@dataProvider`), not attributes.

## `.wp-env.json` (development site, http://localhost:8888)

```json
{
	"$schema": "https://schemas.wp.org/trunk/wp-env.json",
	"core": null,
	"phpVersion": "<php-floor>",
	"<wp-env-key>": [ "." ],
	"testsEnvironment": false
}
```

## `.wp-env.test.json` (dedicated integration-test environment, http://localhost:8889)

```json
{
	"$schema": "https://schemas.wp.org/trunk/wp-env.json",
	"core": null,
	"phpVersion": "<php-floor>",
	"<wp-env-key>": [ "." ],
	"port": 8889,
	"testsEnvironment": false,
	"config": {
		"WP_DEBUG": true
	}
}
```

- **Container naming (wp-env 11.x, checked against its README and source):** `wp-env run` accepts `mysql`,
  `wordpress`, `cli`, `composer`, `phpmyadmin`; the old built-in `tests-wordpress`/`tests-cli` pair only exists while
  the **deprecated** `testsEnvironment` option is on — and it still defaults to `true`, which is why both files set
  it to `false`. The documented replacement is a separate config passed with `--config`, which gets its own
  containers and database. Every container carries `WP_TESTS_DIR=/wordpress-phpunit` (the WordPress PHPUnit library
  matching the installed core) plus PHPUnit and Composer.
- **Never run the integration suite against the development config:** wp-env's `wp-tests-config.php` is derived
  from the site's own `wp-config.php` (same database, same `wp_` prefix), and the test installer drops those tables
  — the dedicated `.wp-env.test.json` environment is the one it is allowed to wipe.
- `core: null` = latest WordPress release. To test the floor too, a CI matrix can override it per job
  (`WP_ENV_CORE=WordPress/WordPress#<wp-floor>`) — that's `iru-setup-php-github-workflows`' concern.
- wp-env names the mapped directory after the **repository directory's basename**; the `--env-cwd` path in
  `package.json` assumes it equals `<slug>` (SKILL.md Step 1 warns when it doesn't).

## `package.json` (only for wp-env, plus `@wordpress/scripts` when blocks are built)

```json
{
	"name": "<slug>",
	"version": "<dev-version>",
	"private": true,
	"description": "Local WordPress environments for <name> (@wordpress/env).",
	"license": "<license-spdx>",
	"scripts": {
		"env:start": "wp-env start",
		"env:stop": "wp-env stop",
		"test:env:start": "wp-env start --config=.wp-env.test.json",
		"test:env:stop": "wp-env stop --config=.wp-env.test.json",
		"test:integration": "wp-env run cli --config=.wp-env.test.json --env-cwd=<wp-content-dir>/<slug> vendor/bin/phpunit -c phpunit-integration.xml.dist"
	},
	"devDependencies": {
		"@wordpress/env": "^11.17.0"
	}
}
```

- `"private": true` always — this file only drives tooling; nothing is published to npm. `<dev-version>` is the
  same `x.y.z-dev` as the plugin header / `style.css` (`iru-php-bump-version` keeps it in sync via npm).
- `@wordpress/env` constraint: `^<version>` from Step 4. Integration tests run **inside** the `cli` container with
  the host's `vendor/` (mounted with the plugin/theme), so run `composer install` on the host first; `config.platform`
  keeps that `vendor/` loadable by the container's `<php-floor>` PHP.
- npm 11 prints `install-scripts … fs-ext-extra-prebuilt` after `npm install`: that native add-on belongs to wp-env's
  optional WordPress Playground runtime and isn't needed for the Docker runtime used here — leave it unapproved.
- Plugin with `blocks: yes`: see `plugin.md` "Blocks" for the extra scripts and dependencies.

## `sonar-project.properties` (only when `sonar` ≠ `none`)

```properties
sonar.organization=<sonar-organization>
sonar.projectKey=<sonar-project-key>
sonar.sources=<sonar-sources>
sonar.tests=tests
sonar.php.coverage.reportPaths=build/logs/clover.xml
sonar.php.tests.reportPath=build/logs/junit.xml
sonar.php.phpstan.reportPaths=build/logs/phpstan.json
sonar.exclusions=vendor/**,node_modules/**,build/**,languages/**
```

- Omit `sonar.organization` for a self-hosted server without organizations.
- The three report paths come from `composer test:coverage` (Clover + JUnit) and `composer lint:report` (PHPStan
  JSON) — the same script names `iru-setup-php-laravel` uses, so `iru-setup-php-github-workflows` runs one command
  set for every flavor.
- Plugin with `blocks: yes`: add `blocks` to `sonar.sources`, and `sonar.javascript.lcov.reportPaths` only if JS
  tests are added later.
