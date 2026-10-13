# Sample code and tests (Step 9)

A deliberately small vertical slice that follows `iru-php-code-one-task/reference/laravel.md`: thin controller →
Form Request (validation) → route-level policy check (authorization) → action (work) → `JsonResource` (response),
plus feature tests covering success, validation, authorization and authentication. It reuses the skeleton's `User`
model, factory and migration, so it adds no migration. Verified with Laravel 13.36, Pest 5.3 / PHPUnit 12.5,
Larastan 3.13 at level 9, Pint 1.32: all tests pass, 100% line coverage of `app/`, zero PHPStan errors,
`pint --test` clean. Files keep the skeleton's style (no `declare(strict_types=1);`, non-final classes) — Pint's
`laravel` preset and the arch presets accept it.

## Production code

`app/Actions/RenameUser.php`:

```php
<?php

namespace App\Actions;

use App\Models\User;

class RenameUser
{
    /**
     * @param  array{name: string}  $data
     */
    public function handle(User $user, array $data): User
    {
        $user->update(['name' => $data['name']]);

        return $user;
    }
}
```

`app/Http/Requests/RenameUserRequest.php`:

```php
<?php

namespace App\Http\Requests;

use Illuminate\Contracts\Validation\ValidationRule;
use Illuminate\Foundation\Http\FormRequest;

class RenameUserRequest extends FormRequest
{
    /**
     * Authorization runs on the route (`->can('update', 'user')`), before this request validates.
     */
    public function authorize(): bool
    {
        return true;
    }

    /**
     * @return array<string, ValidationRule|array<mixed>|string>
     */
    public function rules(): array
    {
        return [
            'name' => ['required', 'string', 'max:255'],
        ];
    }
}
```

`app/Http/Resources/UserResource.php`:

```php
<?php

namespace App\Http\Resources;

use App\Models\User;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/**
 * @mixin User
 */
class UserResource extends JsonResource
{
    /**
     * @return array<string, mixed>
     */
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
        ];
    }
}
```

`app/Policies/UserPolicy.php` (auto-discovered for `App\Models\User`):

```php
<?php

namespace App\Policies;

use App\Models\User;

class UserPolicy
{
    /**
     * A user may only change their own profile.
     */
    public function update(User $user, User $model): bool
    {
        return $user->is($model);
    }
}
```

`app/Http/Controllers/UserController.php`:

```php
<?php

namespace App\Http\Controllers;

use App\Actions\RenameUser;
use App\Http\Requests\RenameUserRequest;
use App\Http\Resources\UserResource;
use App\Models\User;

class UserController extends Controller
{
    public function update(RenameUserRequest $request, User $user, RenameUser $renameUser): UserResource
    {
        /** @var array{name: string} $data */
        $data = $request->validated();

        return new UserResource($renameUser->handle($user, $data));
    }
}
```

(The `@var` narrows `validated()`'s `array<string, mixed>` for PHPStan level 9 — without it Larastan reports
`argument.type` on the `handle()` call.)

Append to `routes/web.php` (keep the skeleton's `/` route; add the `use` line at the top). The `can:` middleware
runs before the Form Request resolves, so an unauthorized user gets 403, not 422:

```php
use App\Http\Controllers\UserController;

Route::patch('/users/{user}', [UserController::class, 'update'])
    ->middleware(['auth', 'can:update,user'])
    ->name('users.update');
```

The route lives in `web.php` because the skeleton has no `routes/api.php` until `php artisan install:api`
(Sanctum). JSON requests in tests get 401 from `auth` and skip CSRF (Laravel disables it while running tests).

## Pest tests (`test-framework: pest`)

`tests/Pest.php` — replace the boilerplate `pest --init` writes (it carries an example `toBeOne` expectation and a
`something()` helper):

```php
<?php

use Tests\TestCase;

/*
|--------------------------------------------------------------------------
| Test Case
|--------------------------------------------------------------------------
|
| Feature tests boot the application through Tests\TestCase. Unit tests stay
| on PHPUnit's plain TestCase: no container, no database.
|
*/

pest()->extend(TestCase::class)->in('Feature');
```

With an integration suite (Step 10) the last line becomes `->in('Feature', 'Integration');`.

`tests/Unit/ArchTest.php`:

```php
<?php

arch()->preset()->php();

arch()->preset()->security();

arch()->preset()->laravel();

arch('actions expose a single handle() entry point')
    ->expect('App\Actions')
    ->toHaveMethod('handle');
```

`tests/Feature/RenameUserTest.php`:

```php
<?php

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;

uses(RefreshDatabase::class);

it('lets a user rename themselves', function () {
    $user = User::factory()->create(['name' => 'Ada']);

    $this->actingAs($user)
        ->patchJson(route('users.update', $user), ['name' => 'Ada Lovelace'])
        ->assertOk()
        ->assertJsonPath('data.name', 'Ada Lovelace');

    $this->assertDatabaseHas('users', ['id' => $user->id, 'name' => 'Ada Lovelace']);
});

it('rejects an empty name', function () {
    $user = User::factory()->create();

    $this->actingAs($user)
        ->patchJson(route('users.update', $user), ['name' => ''])
        ->assertUnprocessable()
        ->assertJsonValidationErrors(['name']);
});

it('forbids renaming someone else', function () {
    $other = User::factory()->create(['name' => 'Grace']);

    $this->actingAs(User::factory()->create())
        ->patchJson(route('users.update', $other), ['name' => 'Mallory'])
        ->assertForbidden();

    $this->assertDatabaseHas('users', ['id' => $other->id, 'name' => 'Grace']);
});

it('requires authentication', function () {
    $user = User::factory()->create();

    $this->patchJson(route('users.update', $user), ['name' => 'Anonymous'])
        ->assertUnauthorized();
});
```

`tests/Feature/HomePageTest.php`:

```php
<?php

it('serves the home page', function () {
    $this->get('/')->assertOk();
});
```

`tests/Unit/RenameUserRequestTest.php` (no container — `rules()` is plain PHP):

```php
<?php

use App\Http\Requests\RenameUserRequest;

it('requires a short string name', function () {
    expect((new RenameUserRequest)->rules())
        ->toBe(['name' => ['required', 'string', 'max:255']]);
});
```

## PHPUnit tests (`test-framework: phpunit`)

No arch tests (Pest-only feature). `tests/Feature/RenameUserTest.php`:

```php
<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use PHPUnit\Framework\Attributes\Test;
use Tests\TestCase;

class RenameUserTest extends TestCase
{
    use RefreshDatabase;

    #[Test]
    public function a_user_can_rename_themselves(): void
    {
        $user = User::factory()->create(['name' => 'Ada']);

        $this->actingAs($user)
            ->patchJson(route('users.update', $user), ['name' => 'Ada Lovelace'])
            ->assertOk()
            ->assertJsonPath('data.name', 'Ada Lovelace');

        $this->assertDatabaseHas('users', ['id' => $user->id, 'name' => 'Ada Lovelace']);
    }

    #[Test]
    public function an_empty_name_is_rejected(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)
            ->patchJson(route('users.update', $user), ['name' => ''])
            ->assertUnprocessable()
            ->assertJsonValidationErrors(['name']);
    }

    #[Test]
    public function renaming_someone_else_is_forbidden(): void
    {
        $other = User::factory()->create(['name' => 'Grace']);

        $this->actingAs(User::factory()->create())
            ->patchJson(route('users.update', $other), ['name' => 'Mallory'])
            ->assertForbidden();

        $this->assertDatabaseHas('users', ['id' => $other->id, 'name' => 'Grace']);
    }

    #[Test]
    public function guests_must_authenticate(): void
    {
        $user = User::factory()->create();

        $this->patchJson(route('users.update', $user), ['name' => 'Anonymous'])
            ->assertUnauthorized();
    }

    #[Test]
    public function the_home_page_is_served(): void
    {
        $this->get('/')->assertOk();
    }
}
```

`tests/Unit/RenameUserRequestTest.php`:

```php
<?php

namespace Tests\Unit;

use App\Http\Requests\RenameUserRequest;
use PHPUnit\Framework\Attributes\Test;
use PHPUnit\Framework\TestCase;

class RenameUserRequestTest extends TestCase
{
    #[Test]
    public function the_name_must_be_a_short_string(): void
    {
        $this->assertSame(['name' => ['required', 'string', 'max:255']], (new RenameUserRequest)->rules());
    }
}
```

## Integration test (Step 10 only)

`tests/Integration/UserPersistenceTest.php` (Pest form; with PHPUnit, the same two tests as a `Tests\TestCase`
subclass using `RefreshDatabase` and `$this->expectException(...)`). Verified against MySQL 8.4:

```php
<?php

use App\Models\User;
use Illuminate\Database\UniqueConstraintViolationException;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;

uses(RefreshDatabase::class);

it('runs against the configured database server, not in-memory SQLite', function () {
    expect(DB::connection()->getDriverName())->not->toBe('sqlite');
});

it('enforces the unique e-mail index', function () {
    User::factory()->create(['email' => 'ada@example.com']);

    User::factory()->create(['email' => 'ada@example.com']);
})->throws(UniqueConstraintViolationException::class);
```

Import the exception class (`use Illuminate\Database\UniqueConstraintViolationException;`) rather than writing
it fully qualified inline — Pint's `fully_qualified_strict_types` fixer flags the inline form.
