<!--
Copyright 2026 Specfuse Contributors
Licensed under the Apache License, Version 2.0. See LICENSE.
-->

# Generator releases

The kit pins one generator release at a time (`generator.lock`). This page is the readable account of each pin bump: what the new generator changes for **spec authors** and **component repos**, what to do before you regenerate, which of the generator issues the kit was tracking it fixes, and what the kit changed to match.

The other two places release information lives:

- [`compatibility.md`](../compatibility.md) is the authoritative pin table: the kit version, the jar, its SHA-256 and the full verification record for each release. This page summarises it and does not repeat the evidence.
- The generator's own `CHANGELOG.md` is the complete list. It lives in the generator repository, which not every kit user can read, so this page is where its kit-facing content is restated.

Newest first. An entry is **pending** until the kit release that pins it is published.

## How to read an entry

| Part | Read it if |
|---|---|
| **Before you regenerate** | always: the changes that make a spec stop validating, or change what generated code does |
| **New in the spec** | you want to use what the release adds |
| **Component repos** | you own a repo that receives generated code |
| **Tracked issues** | you were waiting on a fix |
| **Kit changes** | you want to know what moved in the handbooks, rules and tooling |

## 0.21.0 (with 0.20.0)

**Status: pending.** Pinned by kit `v0.29.0` (jar sha256 `a78b5ea7…27f08a94`; full record in [`compatibility.md`](../compatibility.md) §58). Generator release date: 2026-10-28.

The kit goes straight from **0.19.0 to 0.21.0**. Generator 0.20.0 (2026-10-25) was never published to the release channel, so its changes reach kit users for the first time with this pin; everything below covers both releases.

### Before you regenerate

Things that validated or behaved one way on 0.19.0 and do not on 0.21.0.

**Spec authors**

- **`OPERATION_EMITS_FOREIGN_ENTITY` (ERROR, 0.21.0).** A generated operation whose `x-emits` names another entity's event now fails `validate` and `generate`. The event belongs to the operation of the entity it is about; move the `x-emits` entry there. See [`API_Handbook.md`](../handbooks/API_Handbook.md).
- **`TRIGGER_REQUIRES_EVENT_RUNTIME_IMPL` (load failure, 0.20.0).** A project that registers `azureFunctionTopicTrigger`, `heldEntityHydrationTrigger` or `hostedTopicConsumer` must also register `eventRuntimeImpl` in some C# group.
- **`ASYNC_SUBSCRIPTION_FILTER_TOO_LONG` (ERROR, 0.21.0).** A topic worker's `filterOverride` longer than the 1024 characters Service Bus accepts on one rule fails `validate`; shorten it or drop it. Filters the generator builds itself are split across rules instead.
- **Scenario `emit.expect` keys are checked (0.21.0)**, whatever `functionalTests.emitAssertions` says: an unknown key is an `ARAZZO_CROSS_SPEC_ERROR`. See [`Arazzo_Handbook.md`](../handbooks/Arazzo_Handbook.md).
- **Hidden rows answer 404, not 403 (0.21.0).** A request for a row the caller's visibility hides now returns 404, so its existence is not disclosed. Scenarios and tests that expected 403 for such a row change.
- **Python AI workers need `primary_model` (0.20.0).** The generated per-worker settings no longer name a model; set `<PREFIX>PRIMARY_MODEL`.
- **`VISIBILITY_NOT_ENFORCED` warnings on Python groups (0.21.0).** A Python group that reads a tenant-filtered table now gets this warning, so a project with Python groups will see new warnings on a spec that has not changed.

**C# component repos**

- **A generated `Tenant` query filter (0.21.0).** In a project that declares `tenancy`, every entity whose `belongsTo` chain reaches the tenant root is filtered by a named `Tenant` query filter in the generated `DbContext`, and the host **must register an `IRecordVisibilityResolver`**. Three consequences to check in hand-written code:
  - a hand-built `new <Context>(options)` (a design-time factory, a CLI tool, a test) throws `RecordVisibilityNotResolvedException` at its first filtered query;
  - a hand-written `ITransactionScopeFactory` that is not an `IRecordVisibilitySource` leaves the visibility unset inside generated handler and job bases, with the same result;
  - a hand-written, unnamed `HasQueryFilter(...)` on a generated entity that carries a generated filter now throws at model build. Generated `IgnoreQueryFilters` calls name the filters they drop (`QueryFilterNames`).

  `tenancy.enforcement: route` (below) is the transition switch for a project that cannot take the filter yet.
- **`Handle<Event>Async` is abstract and `HandleCoreAsync` is gone (0.20.0).** Every typed handler method on a generated event-handler base must be overridden; the deprecated raw-body hook is removed. A handler that only overrode `HandleCoreAsync` no longer compiles.
- **Authorization filters are registered for you (0.20.0).** `AddSpecfuseAuthorization()` now adds the role and scope filters to MVC, so a host that never added them starts answering 401/403 where it answered 200.
- **No `tenancy`: the tenant check allows (0.20.0).** Without a `tenancy` block, `ITenantResourceCheck` is the generated `RoleSufficientTenantResourceCheck` (the role gate is the whole decision) instead of a placeholder that threw. Register your own if you relied on the throw.
- **A required event `Context` (0.20.0).** When a payload lists `context` in `required`, the generated write sites set it through a `Supply<Event>Context` hook you override.
- **Timeouts retry (0.21.0).** A handler or job that runs past its spec `timeout` now throws `TimeoutException` and is retried instead of dead-lettered on its first attempt.
- **Python AI workers (0.20.0):** a delivery's inbox claim, its writes and its completion outbox row commit in one transaction, and state-transition workers return `TransitionResult`.

### New in the spec

- **`x-entity.uniqueBy` `where:` and `nullsDistinct: false` (0.20.0).** A unique index can be conditional ("one active per parent") and can treat NULL as a value. See [`Vendor_Extensions.md`](../handbooks/Vendor_Extensions.md).
- **`x-protection.unmask` (0.20.0).** A masked property declares who may unmask it: roles, or the holder of the row (`holder: { property, caller }`). `x-unmask` is now allowed on PUT and PATCH, so a granted field is written instead of dropped as a mask echo. Four new validation codes check the declaration. Kit issue [#182](https://github.com/specfuse/authoring/issues/182).
- **`x-entity.visibility` (0.21.0).** `subTenant`, `tenantWide` or `grantFiltered` (with a `scope` property), and `unscopedRows`, narrow which rows a caller sees inside a tenant. A declaration the generator cannot enforce is a `validate` finding, never a silent no-op.
- **`tenancy.enforcement: route` (0.21.0).** Deprecated on arrival: suppresses the `Tenant` query filter for a project whose list routes do not yet carry the tenant path parameter.
- **`workerPlacement` (0.20.0)** in the project file says whether each topic worker runs on Azure Functions or in a generic host; the new `hostedTopicConsumer` artifact renders the generic-host consumers.
- **`functionalTests.emitAssertions: "strict"` (0.21.0)** makes a generated scenario test fail when a step's declared `x-async.emit` event is never published.
- **`generateUserHelper` (0.20.0)** makes `authorizationRuntime` emit a default `UserHelper.GetUser(ClaimsPrincipal)`; `PROJECT_AUTHORIZATION_RUNTIME_MISSING` warns when role-gated controllers have no authorization runtime.
- **New opt-in Test-group artifacts (0.21.0):** `tenantIsolationTest` (isolation tests over a seeded foreign tenant) and `bareIgnoreSourceScanTest` (fails when hand-written C# calls `IgnoreQueryFilters()` with no argument).
- **Single-tenant C# projects compile services (0.20.0).** `tenancy` is no longer required to register `service` or the event runtime; the three `PROJECT_*_TENANCY_REQUIRED` codes are removed.

### Component repos

- The generator publishes [`CONSUMER-CONTRACT.md`](https://github.com/clabonte/generator/blob/main/docs/CONSUMER-CONTRACT.md) (0.20.0): what its consumer verification harness reads from a component repo, declared a stable interface. The kit's C# starter contract follows it ([`csharp-component-guide.md`](csharp-component-guide.md) §6).
- Worth knowing from the fixes: the generated inbox treats only a key violation as a duplicate; `validate` warns `WORKER_TIMEOUT_EXCEEDS_FUNCTIONS_LOCK_RENEWAL` when a Functions worker can outlive its message lock; `x-manual` operations on an aggregate service compile; OpenAPI specs over 3 MB parse.
- New C# facts for the host: a hand-built `DbContext` needs `UseRecordVisibility(...)`; a `generateUserHelper` project must delete any hand-written `UserHelper` (CS0101); `tenantIsolationTest` needs the Test project to reference Infrastructure; generic-host workers need a `ServiceBusClient` and `AzureServiceBus:TopicName`. Details in [`csharp-component-guide.md`](csharp-component-guide.md) §4 and [`Project_File.md`](../handbooks/Project_File.md) §17.

### Tracked issues

| Issue | What it was | Status |
|---|---|---|
| [clabonte/generator#2882](https://github.com/clabonte/generator/issues/2882) | a kebab-case project name gave an invalid Python package root | fixed in 0.20.0 (`hello-orders` gives `hello_orders_*`) |
| [clabonte/generator#2883](https://github.com/clabonte/generator/issues/2883) | single-tenant C# projects could not compile services | fixed in 0.20.0 |
| [clabonte/generator#2884](https://github.com/clabonte/generator/issues/2884) | names from another project leaked into every project's output | fixed in 0.20.0 |
| [clabonte/generator#2885](https://github.com/clabonte/generator/issues/2885) | publish the consumer contract the QA harness reads | fixed in 0.20.0 (`CONSUMER-CONTRACT.md`) |
| [clabonte/generator#2768](https://github.com/clabonte/generator/issues/2768) | declare in the spec who may unmask a field | fixed in 0.20.0 (`x-protection.unmask`) |

The kit's hold on releases for #2882 to #2884 ends with this pin.

### Kit changes

- `add-component` no longer refuses single-tenant C# projects or kebab-case Python project names, and derives Python package roots exactly as the generator now does.
- Handbooks document the new extensions, project-file keys, artifacts and validation codes above; Spectral checks the shape of `uniqueBy` `where` / `nullsDistinct`, `x-protection.unmask` and `x-entity.visibility`.
- The C# component guide drops the "tenancy is required" workaround and documents the `Tenant` query filter and the resolver the host must register.
- Full record: the `compatibility.md` row for this kit release.

## Earlier releases

Pin bumps before this page existed are recorded only in [`compatibility.md`](../compatibility.md), one row per kit release:

| Generator | Pinned by kit |
|---|---|
| 0.20.0 | never published; folded into 0.21.0 above |
| 0.19.0 | `v0.28.0` |
| 0.18.0 | `v0.27.0` |
| 0.17.0 | `v0.26.0` |
| 0.16.0 | `v0.25.0` |
| 0.15.0 | `v0.24.0` |
| 0.14.0 | `v0.23.0` |
| 0.13.0 | `v0.20.0` to `v0.22.0` |
| 0.12.0 | `v0.18.0`, `v0.19.0` |
| 0.11.0 | `v0.17.0` |
| 0.9.0 | `v0.15.0`, `v0.16.0` |
| 0.8.0 | `v0.14.0` |
| 0.7.0 | `v0.12.0` to `v0.13.1` |
| 0.6.0 | `v0.11.0` |
| 0.5.8 | `v0.8.0` to `v0.10.0` |

## Adding an entry

At every pin bump (the `bump-generator-pin` skill), add an entry at the top in the shape above, marked **pending**, in the same PR as the `generator.lock` change; flip it to the kit version when that release is published. Write it for the reader who regenerates tomorrow: what breaks first, then what is new, then the issue table. Link the handbook section that explains each item rather than restating it.
