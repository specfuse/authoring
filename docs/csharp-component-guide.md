<!--
Copyright 2026 Specfuse Contributors
Licensed under the Apache License, Version 2.0. See LICENSE.
-->

# Setting up a C# component repo

[Setting up component repos](component-repos.md) says what every component repo, in any language, has to get right. This guide is the C# version in full: the layout the generator writes into, the build wiring and host files the generator never writes, the seams generated code calls by name, how hand-written code extends generated code without ever editing it, the mechanical contract that keeps all of that true, and the regen flow. It ends in an **audit checklist** (§10) that a person or a coding agent can run against an existing repo and report on, check by check.

It is written to be handed to Claude. Every rule has a reason, a way to verify it from a shell, and a pointer to the section that explains the fix. The interactive companion, [`csharp-component.html`](csharp-component.html), is the same material as a map you click through.

Project names in this guide use `HelloOrders`, the root namespace of the kit's bundled example [`hello-orders`](../examples/hello-orders/) (which itself generates only a Domain group): the solution is `HelloOrders`, the layered projects are `HelloOrders.Domain`, `HelloOrders.Infrastructure`, `HelloOrders.Api`, and so on. Substitute your own root namespace throughout.

> **New repo?** `specfuse authoring add-component csharp <Dir>` ([`add-component.md`](add-component.md)) seeds most of the host files in §2 and §4 once, with the package versions the kit's pinned generator compiles against: the solution, `Directory.Build.props`, the Domain, Infrastructure and Api projects, `Program.cs`, `UserHelper`, `ExceptionFilter`, `.gitignore` and a `CLAUDE.md`. `global.json`, `.gitattributes`, the Application and Test projects and the §6 contract are yours to add. This guide is what the seed implements, and what to check when a repo was set up some other way.

## How to use this guide with Claude

Open a Claude Code session in the component repo and paste:

```
Read docs/csharp-component-guide.md from the Specfuse authoring kit (or the copy at <path>).
Audit this repository against every check in §10, in order. For each check, run the
verification command, then report one line: the check ID, PASS or FAIL, and the
evidence (a path, a line, a command output). Do not fix anything yet. When the audit
is complete, list the FAILs grouped by the section that explains the fix, and
propose the smallest change for each. Wait for my approval before editing.
```

For a new repo, replace "Audit" with "Set up this repository so that every check in §10 passes, starting from §1", and keep the approval step: the host files in §2 and §4 are yours to own, so the first version deserves a look.

## 0. The model in one paragraph

Generation runs **from the spec repo**. The project file there names, for each C# group, a `destination` (`../Backend/`) and a `basePackage` (`HelloOrders.Domain`); the generator writes that group's files into `<destination>/<basePackage>/gen-src/` and, with `cleanGenerated: true`, wipes that folder first on every full-group regen. It writes **only** `gen-src/`, plus a `CHANGELOG.md` and a bookkeeping manifest beside it. Everything that makes the generated code compile and run (the solution, the project files, `Directory.Build.props`, `Program.cs`, the handful of classes generated code calls by name) is yours, written once and never regenerated. Everything that extends the generated code lives in `src/` beside `gen-src/`, through `partial` classes, generated `*Base` classes you derive from, and `partial` hook methods. A small mechanical contract (`gen-contract.yml`) keeps that split true on every pull request.

## 1. Layout

```
~/work/hello-orders/
├── hello-orders-specs/                 the spec repo: specs, hello-orders-project.json, .specfuse/state/
└── Backend/                            this repo
    ├── HelloOrders.slnx
    ├── Directory.Build.props           compiles src/ and gen-src/ in every project (§2)
    ├── global.json
    ├── gen-contract.yml                the mechanical contract (§6)
    ├── HelloOrders.Domain/
    │   ├── HelloOrders.Domain.csproj
    │   ├── CHANGELOG.md                written by the generator: the regen-over-regen surface diff
    │   ├── gen-src/                    generated; wiped and rewritten on every full-group regen
    │   │   ├── Entities/  ValueObjects/  Enums/  Models/  Events/  Snapshots/
    │   │   ├── Services/  Repositories/  Mappers/  Exceptions/  Validators/
    │   │   └── ConfigureServices.g.cs  AddServices()
    │   └── src/                        yours: partial classes, custom services, mapper hooks
    ├── HelloOrders.Infrastructure/
    │   ├── gen-src/                    DbContext, Configurations/, Repositories/, Converters/, Events/, Interceptors/
    │   └── src/                        yours: EF migrations, external services, the host-side contracts (§4)
    ├── HelloOrders.Application/        only with an Application group: handlers and jobs
    │   ├── gen-src/<Domain>/Handlers/  I{X}Handler + {X}HandlerBase
    │   ├── gen-src/<Domain>/Jobs/      I{X}JobHandler + {X}JobHandlerBase
    │   ├── gen-src/<Domain>/Registration/  Add{Domain}Workers()
    │   └── src/<Domain>/Handlers/      yours: the concrete handlers (§5)
    ├── HelloOrders.Api/
    │   ├── gen-src/                    Controllers/, Models/, Mappers/, Authorization/, Application/Interfaces/
    │   └── src/                        Program.cs, Utils/UserHelper.cs, Filters/ExceptionFilter.cs, your application services
    └── HelloOrders.Test/               only with a Test group
        ├── gen-src/                    Fakes/ (A.Order()), Fixtures/, Functional/Api/, Generated/Unit/
        └── src/                        yours: ApiTestFixture, ApiTestBase, InMemoryDbTestHelper, hand-written tests
```

The rules behind the picture:

- **Sibling checkouts.** The `../Backend/` destinations in the project file resolve only when the spec repo and the component sit next to each other. Write the layout into this repo's README.
- **One project folder per group `basePackage`.** `HelloOrders.Domain` is both the folder, the `.csproj` name and the namespace root; generated namespaces are `HelloOrders.Domain.Entities`, `HelloOrders.Domain.Services`, and so on. Several groups share one `destination`, each writing into its own `basePackage` subfolder ([`Project_File.md` §7.1](../handbooks/Project_File.md#71-groups)).
- **`gen-src/` is generated, `src/` is yours.** Every generated C# file is a `.g.cs`, opens with `#nullable enable`, and carries the `<auto-generated>` header block with the line `Generated by the Specfuse Generator`. No `.g.cs` is ever outside `gen-src/`. The one non-C# file a C# group can write there is `gen-src/workers.json`, from `hostedTopicConsumer`; the starter contract's `gen_src_non_cs` fileset is where you admit it (§6.1).
- **Two files land beside `gen-src/`, not in it.** `CHANGELOG.md` is the generator's own surface diff for the group and is committed. `<Group>.generated-paths.json` is the generator's manifest of every path the group emitted and every file that moved since the last regen; **commit it** too. Its `capturedAt` comes from the spec repo's `<stateDir>/<group>.paths.json` baseline, not the clock, so a regen that moved nothing leaves it byte-identical; ignoring it throws away the old-to-new path mapping a layout-changing release hands you.

## 2. Build wiring

The generator emits no `.sln`, no `.csproj`, no `Directory.Build.props` and no `Program.cs` ([specfuse/authoring#177](https://github.com/specfuse/authoring/issues/177)). These are the host, seeded once and owned here.

### 2.1 `Directory.Build.props` at the solution root

```xml
<Project>
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <EnableDefaultCompileItems>false</EnableDefaultCompileItems>
    <!-- CS1591: generated code does not document every public member.
         CS8618: generated entities rely on EF Core to populate non-nullable members. -->
    <NoWarn>$(NoWarn);CS1591;CS8618</NoWarn>
  </PropertyGroup>
  <ItemGroup>
    <Compile Include="src\**\*.cs" />
    <Compile Include="gen-src\**\*.cs" />
  </ItemGroup>
</Project>
```

Default globbing is **off** on purpose: with it on, a `.cs` file anywhere in a project folder joins the build, so a stale file parked beside `gen-src/` compiles and shadows the generated one. With it off, the two `Compile` globs are the whole story, and a file is either generated or yours by where it sits. The same file is where `TreatWarningsAsErrors` goes once the build is clean.

### 2.2 One `.csproj` per layer, with the layering in the references

| Project | SDK | References | Packages the generated code needs (generator 0.21) |
|---|---|---|---|
| `HelloOrders.Domain` | `Microsoft.NET.Sdk` | none | `Riok.Mapperly`, `Microsoft.Extensions.Logging`, `Microsoft.AspNetCore.Http`, `Microsoft.Data.SqlClient`, `Newtonsoft.Json` |
| `HelloOrders.Infrastructure` | `Microsoft.NET.Sdk` | Domain | `Microsoft.EntityFrameworkCore` (+ `.Relational`, `.SqlServer`, `.InMemory`), `Azure.Messaging.ServiceBus`, `Azure.Storage.Blobs`, `Microsoft.Extensions.Http`, `Microsoft.Extensions.Configuration.EnvironmentVariables` |
| `HelloOrders.Application` | `Microsoft.NET.Sdk` | Domain | `Microsoft.Extensions.Logging` |
| `HelloOrders.Api` | `Microsoft.NET.Sdk.Web` | Domain, Application, Infrastructure | `Riok.Mapperly`, `Newtonsoft.Json` |
| `HelloOrders.Test` | `Microsoft.NET.Sdk` (`IsTestProject`) | all of the above | `xunit`, `xunit.runner.visualstudio`, `Microsoft.NET.Test.Sdk`, `Moq`, `AwesomeAssertions`, `Microsoft.AspNetCore.Mvc.Testing`, `Microsoft.EntityFrameworkCore.InMemory`, `coverlet.collector` |

The references are the Clean Architecture layering made compile-time: Domain references nothing in the solution; Infrastructure implements Domain's interfaces; Api talks to Domain and references Infrastructure **only** to wire it up in `Program.cs`. Infrastructure referencing Application is allowed when Application owns ports (interfaces its use cases need and Infrastructure implements), never for Application's behaviour. The exact versions are those the kit's pinned generator compiles against; `add-component` seeds them, [`compatibility.md`](../compatibility.md) says when a generator release needs a new one, and `dotnet build` names the missing package when it does.

Two libraries are deliberately **not** on the list: AutoMapper and FluentAssertions. Both became commercially licensed; generated code maps through Mapperly and asserts through AwesomeAssertions (the Apache-2.0 fork with the same `.Should()` API). Referencing FluentAssertions beside AwesomeAssertions makes every assertion ambiguous.

### 2.3 Solution, SDK pin and git

- `HelloOrders.slnx` (or `.sln`) lists every project; `global.json` pins the SDK (`"version": "10.0.100", "rollForward": "feature"`).
- `.gitignore` carries `bin/`, `obj/` and `TestResults/`, and **not** `*.generated-paths.json` (§1). Generated code itself is **committed**: every regen is then a reviewable diff, CI and teammates build without Java or generator access, and a spec change and its effect are visible side by side.
- `.gitattributes` normalises `*.cs`, `*.csproj`, `*.json` and `*.md` to LF so a regen on another OS does not rewrite every line.

## 3. Project-file groups for C#

The spec repo's project file declares one group per project folder. This is the shape that compiles together ([`Project_File.md` §8](../handbooks/Project_File.md#8-group-fields), artifact catalogue in [§11.1](../handbooks/Project_File.md#111-c--csharp-artifacts)):

```json
{ "language": "C#", "name": "Domain", "basePackage": "HelloOrders.Domain", "destination": "../Backend/", "cleanGenerated": true,
  "artifacts": ["domainProject", "domainValidation", "domainExceptions", "entity", "valueObject", "enum", "domainModel",
                "serviceInterface", "repositoryInterface", "service", "event", "snapshot", "snapshotContext",
                "tenancyMarker", "eventRuntime"] },
{ "language": "C#", "name": "Infrastructure", "basePackage": "HelloOrders.Infrastructure", "destination": "../Backend/", "cleanGenerated": true,
  "artifacts": ["infrastructureProject", "entityTypeConfiguration", "valueObjectConverter", "dbContext", "repository", "eventRuntimeImpl"] },
{ "language": "C#", "name": "Api", "basePackage": "HelloOrders.Api", "destination": "../Backend/", "cleanGenerated": true,
  "artifacts": ["apiProject", "apiModel", "apiMapper", "apiController", "applicationServiceInterface", "authorizationRuntime"] }
```

Add as the project grows:

| Group | `basePackage` | Artifacts | Notes |
|---|---|---|---|
| `Application` | `HelloOrders.Application` | `asyncEventHandler`, `asyncJobInterface`, `asyncConsumerRegistration` | One `I{X}Handler` + `{X}HandlerBase` per consumed event, per-domain `Add{Domain}Workers()` registrations. |
| `AzureFunctions` / `Workers` | `HelloOrders.AzureFunctions` / `.Workers` | `azureFunctionTopicTrigger`, `azureFunctionTimerTrigger`, `eventRuntimeFunctions` / `hostedTopicConsumer` | Set `configs.applicationPackage` to the Application group's `basePackage`. |
| `Test` | `HelloOrders.Test` | `entityBuilder`, `newDtoBuilder`, `updateDtoBuilder`, `valueObjectFake`, `apiModelFake`, `testSeed`, `serviceUnitTest`, `mapperTest`, `valueObjectTest`, `efConfigTest`, `authMatrixTest`, `authorizationConformanceTest`, `apiFunctionalTest`, `eventBuilder`, `eventContractTest`, `recipeFixture`, `scenarioFunctionalTest` | Needs the hand-written fixtures in §4.4. |

Three things the project file must get right for C#:

- **`tenancy` only for a multi-tenant project.** Without it, `eventRuntime` emits a do-nothing `ITenantScoped` contract and `tenancyMarker` emits nothing, so a single-tenant project compiles the services that take an `IEventCollector` (from generator 0.20.0, [clabonte/generator#2883](https://github.com/clabonte/generator/issues/2883)). With it, the `Tenant` query filter asks a hand-written `IRecordVisibilityResolver` (§4.3; [`Project_File.md` §4.1](../handbooks/Project_File.md#41-tenancy-c-only-today)). `dbContextClassname` names the EF Core context (`HelloOrdersDbContext`); unset, it derives from `name`.
- **`cleanGenerated: true` on every C# group.** The wipe is gated on a full-group regen; a run filtered with `--artifact` skips it, so partial output never deletes a sibling artifact's files ([§8.9](../handbooks/Project_File.md#89-cleangenerated)). `cleanScope` is not needed for C#: the default wipe target is `gen-src/` under the group's folder.
- **`functionalTests`** decides which generated API functional tests run in parallel (`collectionNamePattern`, `collectionGroups`); unset, every generated test shares one xUnit collection and the suite is serial.

## 4. The composition root and the seams generated code calls by name

The generator emits registrations and contracts; the host calls the registrations and implements the contracts. Nothing generated calls `Program.cs`, and several generated types reference a hand-written class **by name** and compile only once you provide it.

### 4.1 `Program.cs`

```csharp
using HelloOrders.Api.Authorization;
using HelloOrders.Api.Filters;
using HelloOrders.Domain;
using HelloOrders.Infrastructure;
using HelloOrders.Infrastructure.Concurrency;
using HelloOrders.Infrastructure.Events;
using Microsoft.AspNetCore.Authentication.JwtBearer;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddControllers(options => options.Filters.Add<ExceptionFilter>());

// Authentication: the generated [RoleRequired] filter challenges anonymous callers.
// JWT claim names are kept; the generated reader looks for `sub` and `roles`.
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options => options.MapInboundClaims = false);

// Generated registrations (gen-src/**/ConfigureServices.g.cs and friends).
builder.Services.AddServices();                 // Domain: I{Entity}Service -> Default{Entity}Service
builder.Services.AddRepositories();             // Infrastructure: I{Entity}Repository -> {Entity}Repository
builder.Services.AddSpecfuseAuthorization();    // Api: [RoleRequired] runtime, claims reader, placeholders
builder.Services.AddConcurrencyTokenSink();     // Infrastructure: ETag / If-Match plumbing

// Events are buffered per request and dispatched on commit. AddNullEventDispatcher drops
// them (local runs without a broker); production calls AddEventRuntime() for Azure Service Bus.
builder.Services.AddEventRuntimeCore().AddNullEventDispatcher();

var connectionString = builder.Configuration.GetConnectionString("Default");
if (string.IsNullOrEmpty(connectionString))
    builder.Services.AddInMemoryDatabase("HelloOrders");
else
    builder.Services.AddSqlServerDatabase(connectionString);

var app = builder.Build();
app.UseAuthentication();
app.UseAuthorization();
app.MapControllers();
app.Run();
```

With an Application group, add `builder.Services.Add{Domain}Workers()` per domain (or the aggregate `AddAllWorkers()`), which registers every concrete handler and job found by assembly scan. With field encryption declared in the spec, add `builder.Services.AddFieldEncryption()`; nothing generated calls it for you.

**An authentication scheme is required.** Since generator 0.20.0, `AddSpecfuseAuthorization()` registers the role and scope filters itself. They challenge an anonymous caller, and with no authentication scheme the challenge throws, so every role-gated request answers 500 instead of 401. The seed uses JWT bearer with `MapInboundClaims = false`, because the generated `ClaimsPrincipalReader` reads the `sub` and `roles` claims by those names; point `Authentication:Schemes:Bearer` at your identity provider, and use `dotnet user-jwts create --claim roles=<Role>` for a local token (the seeded README has the commands).

**Register your own implementations after the generated calls.** `AddServices()` and `AddRepositories()` register with a plain `AddScoped`, so the last registration wins: a custom `I{Entity}Service` goes right after `AddServices()`, a decorator after both. The placeholder contracts in §4.3 are the exception: they are registered with `TryAdd`, so for them order does not matter.

### 4.2 Two classes the API's generated code names

| Type | Who calls it | What it must do |
|---|---|---|
| `HelloOrders.Api.Utils.UserHelper` | every generated controller: `new CallerContext(UserHelper.GetUser(User))` | A static `GetUser(ClaimsPrincipal)` returning the generated `AuthenticatedUser`: user id, roles, tenant memberships from your identity provider's claims. Alternatively, `"generateUserHelper": true` in the project file (generator 0.20.0) makes `authorizationRuntime` emit a default one, taking the user id from `sub` and the roles from the default claims reader; delete a hand-written one first, since two fail the build with CS0101. |
| `HelloOrders.Api.Filters.ExceptionFilter` | nothing generated; you add it to `AddControllers` | Maps the generated domain exceptions (`NotFoundException`, `ConflictException`, `PreconditionFailedException`, …) to their `StatusCode` and `Errors` list. Without it a `NotFoundException` is a 500. |

### 4.3 Contracts registered as throwing placeholders

Generated registrations install a placeholder for every contract that has no generated implementation. The placeholder keeps the container building and **fails by name on first use**, so a forgotten one is never silent. Implement the ones your spec needs, in `src/` of the layer that owns the knowledge, and register them anywhere (TryAdd means order does not matter):

| Contract | Needed when | Placeholder behaviour |
|---|---|---|
| `ITenantResourceCheck` | the project declares `tenancy` | throws on the first role-gated request that reaches the tenant check; single-tenant projects get a generated `RoleSufficientTenantResourceCheck` instead |
| `IRecordVisibilityResolver` | the project declares `tenancy`: from generator 0.21.0 every entity whose `belongsTo` chain reaches the tenant root carries the generated `Tenant` query filter, which asks the resolver which tenants the caller may see | `AddSqlServerDatabase` registers a placeholder whose `ResolveAsync` throws, naming the interface, at the first query that reads a `Tenant`-filtered entity; `AddInMemoryDatabase` registers a default that sees everything (`RecordVisibility.All`). A hand-written background path sets the visibility with `RecordVisibilityAccessor.Use(...)`, and a hand-written argument-less `IgnoreQueryFilters()` now drops `Tenant` too: name the filters it drops, `IgnoreQueryFilters([QueryFilterNames.SoftDelete])` |
| `IPrincipalKeyResolver` | optimistic concurrency with principal-keyed tokens | `AddPrincipalKeyResolver()` installs a factory that throws `PrincipalKeyResolverNotConfiguredException` |
| `ICallerFieldResolver` | `x-populate-from` caller fields | `AddCallerFieldResolver()` placeholder throws, naming the method |
| `IDataKeyProvider`, `IKeyWrapper`, the decryption-failure policy | field encryption declared in the spec | `AddFieldEncryption()` placeholders throw `FieldEncryptionNotConfiguredException` naming the contract |
| the event dispatcher | always, when `eventRuntime` is registered | `AddNullEventDispatcher()` drops events; `AddEventRuntime()` dispatches to Azure Service Bus through the outbox |

### 4.4 What the generated tests expect from `HelloOrders.Test/src`

With a Test group, the generated tests derive from and call three hand-written types, by name, in these namespaces:

| Type | Namespace | Used by | Must provide |
|---|---|---|---|
| `ApiTestFixture` | `HelloOrders.Test.Fixtures` | every generated functional test (`[Collection]` fixture) | a `WebApplicationFactory<Program>` over the test database, with fake authentication so `CreateHttpClient(role)` can mint a caller |
| `ApiTestBase` | `HelloOrders.Test.Functional.Api` | `class OrdersApiTests(ApiTestFixture fixture) : ApiTestBase(fixture)` | `CreateHttpClient(role)` and `EnsureFakeData()`; the generated `AsAllowedRole` / `AsAnonymous` theories call both |
| `InMemoryDbTestHelper` | `HelloOrders.Test.Helpers` (or as `using`s allow) | generated EF configuration tests: `new InMemoryDbTestHelper($"config-test-{Guid.NewGuid():N}")` | an isolated in-memory `DbContext` per test |

The generated `TestSeed` (stable GUIDs and a pre-wired entity graph) and the `A.{Entity}()` builders point at each other; `EnsureFakeData()` is where you seed that graph into the test database. A bare `A.Order()` is not a self-contained row: it carries foreign keys to `TestSeed` ancestors, and a read through the generated query filters joins them.

## 5. Extending generated code

Never edit a file under `gen-src/`. A wrong generated file is fixed in the spec or in the generator, then regenerated; an edit disappears on the next run. The one exception, a tracked patch while a generator fix is pending, is §9.1. Four patterns cover everything else, all in `src/`, all in the generated type's own namespace.

### 5.1 `partial` classes

Every generated entity, DTO, mapper and hook class is `partial`. A computed property, a domain method, an extra attribute: a `partial class` in `src/` with the same namespace.

```csharp
// HelloOrders.Domain/src/Entities/Order.cs
namespace HelloOrders.Domain.Entities;

public partial class Order
{
    public bool IsDraft => Status == OrderStatus.Draft;
}
```

### 5.2 Derive from the generated `*Base`

For every event handler, scheduled job and gated application service the generator emits an interface plus an abstract base. The base holds the operational contract: logging scope, the spec-declared timeout, inbox deduplication and the shared transaction for handlers, per-item scopes for jobs, the `If-Match` precondition for application services. **The concrete class is yours and must derive from the base.**

```csharp
// HelloOrders.Application/src/Orders/Handlers/OrderPlacedHandler.cs
public sealed class OrderPlacedHandler(
    ILogger<OrderPlacedHandlerBase> logger,
    IEventInboxStore inbox,
    ITransactionScopeFactory scopeFactory,
    IOrderRepository orders) : OrderPlacedHandlerBase(logger, inbox, scopeFactory)
{
    protected override Task HandleOrderPlacedAsync(EventEnvelope envelope, OrderPlacedEvent body, CancellationToken ct)
        => /* the business logic, nothing else */;
}
```

The trap, and the reason §6 has two rules for it: `class OrderPlacedHandler : IOrderPlacedHandler` **also compiles**, is picked up by the generated assembly scan, and is invoked by the trigger exactly as if it had adopted the base, with none of the contract in effect. Nothing reports it. The same shape applies to `OrdersApplicationService : IOrdersApplicationService` without `OrdersApplicationServiceBase`: the precondition gate is a non-virtual method on the base, so the service silently drops `If-Match` and every concurrent write becomes a blind overwrite. Watch for it when a regen introduces a base for a class that already existed.

### 5.3 Mapper hooks

Values a request does not carry (a status, a timestamp, a default) are set in a generated `partial` hook the generator declares and you implement:

```csharp
// HelloOrders.Domain/src/Mappers/OrderDomainMapperHooks.cs
namespace HelloOrders.Domain.Mappers;

public static partial class OrderDomainMapperHooks
{
    static partial void OnAfterToOrder(NewOrder source, Order target)
    {
        target.Status = OrderStatus.Draft;
    }
}
```

Mapperly makes every mapping a compile-time method: a missing or mistyped mapping is a build error, not a runtime one.

### 5.4 Replace a generated default

`AddServices()` registers `IOrderService -> DefaultOrderService` with a plain `AddScoped`. A custom service derives from the default (or implements the interface) in `src/` and is registered after `AddServices()`; the later registration is the one DI resolves. Custom business logic that does not fit a generated operation is a hand-written class beside it, never an edit to the default.

What stays hand-written by design: operations marked `x-manual` in the spec ([`Vendor_Extensions.md` §4.5](../handbooks/Vendor_Extensions.md)), EF Core migrations (derived from the generated configurations, owned here), and everything the generator does not know your domain needs.

## 6. The generated-code contract

The split in §1 and the patterns in §5 are only as true as something checks them. A component repo guards them mechanically with a **contract file** and keeps the judgement calls in a **prose bar** the generator's own QA harness reads. The ownership is settled ([specfuse/authoring#171](https://github.com/specfuse/authoring/issues/171)): the rules are the component's, the engine is the loop's, and what the generator reads is published as a stable interface ([`CONSUMER-CONTRACT.md`](https://github.com/clabonte/generator/blob/main/docs/CONSUMER-CONTRACT.md)).

### 6.1 Seed the starter contract

The kit ships a starter for C# in [`templates/component-contract/csharp/`](../templates/component-contract/csharp/): 16 rules, green on a fresh seed, each with a mutation case proving it bites. Seed it by hand (its README has the exact commands) or wait for `add-component` to do it ([#181](https://github.com/specfuse/authoring/issues/181)):

| Block | Rules | What breaks without them |
|---|---|---|
| Markers and layout | `GEN-001` to `GEN-005` | a hand-written file hides under `gen-src/` and is wiped; a stale `.g.cs` outside it shadows the current output; a file without the header is linted and "fixed" by hand |
| Layering | `GEN-010` to `GEN-014` | Domain grows a dependency on persistence; Api reaches the DbContext directly; a project reference inverts a layer |
| Host wiring | `GEN-020`, `GEN-021` | half the solution stops compiling; an ignored path manifest loses the move record a layout change hands over |
| Hand-written code | `GEN-030` | a generated file copied into `src/` and edited |
| Extension points | `GEN-040` to `GEN-042` | a declared handler nobody wrote dead-letters every delivery; a service drops `If-Match`; a handler bypasses inbox dedup |

**The filesets assume the layout of §1:** project folders at the repo root, named `<Prefix>.Domain`, `<Prefix>.Infrastructure` and `<Prefix>.Api`, test projects ending in `.Test` or `Tests`. A repo laid out differently (projects under `src/`, a layer named otherwise) edits the `filesets:` block once when seeding; a scope that matches nothing reports an error rather than passing, so a wrong glob is never silent.

The engine is `specfuse.loop.gen_contract` (specfuse-loop 0.30+, part of `pipx install specfuse`). The seeded `scripts/check-gen-contract.sh` runs it; `scripts/test-gen-contract.sh` is the mutation test.

```bash
./scripts/check-gen-contract.sh            # every rule; 0 green, 1 violations, 2 cannot run
./scripts/check-gen-contract.sh --list     # what is enforced
./scripts/check-gen-contract.sh --explain GEN-040
./scripts/test-gen-contract.sh             # every rule bites
```

### 6.2 Grow it from review findings

A review finding that recurs becomes a rule, not a longer checklist. The bar for a new rule: green on the default branch the day it lands (or shipped with a `waived_until:` block that freezes today's count and names the event that ends it); a mutation case in `scripts/test-gen-contract.sh`; a `why:` that says what breaks in production. Project-specific shapes the generic checks cannot express (a tenancy marker on every entity, a value object's `Empty`, an event label's two segments) go in `scripts/gen_contract_checks.py` as `builtin` functions.

### 6.3 The prose bar

`docs/generated-code-expectations.md` (the starter ships a skeleton) is read by the generator's consumer-QA reviewer and by anyone reviewing a regen. Its five section names are the stable interface: **Standing expectations**, **Integration contract**, **Known failure modes**, **Accepted quirks**, **Do not report**. The last two are suppression lists; keep the do-not-report table pointing at the rule IDs, so the reviewer never re-judges what the gate decides.

### 6.4 Wire it as a gate

`.specfuse/verification.yml` (`specfuse init <repo>` creates it) carries a `code` gate set. That key is what the Specfuse loop runs as its exit oracle and what the generator's harness runs against every regen. The starter's `verification.snippet.yml` is the shape: `gen-contract` and `gen-patches` first (seconds, no toolchain), `build` with `needs: [gen-contract, gen-patches]`, `tests` with `needs: [build]`, so a structural breach never pays for the .NET chain. CI runs the same order: the starter's `.github/workflows/gen-contract.yml` runs the contract, its mutation test and the patch check on every PR with no SDK; the `dotnet build` / `dotnet test` job sits beside it.

## 7. Tests and coverage

- **Generated tests live in `gen-src/`, hand-written tests in `src/`.** The Test group emits builders, fakes, the seed, and whole suites (service unit tests, mapper tests, EF configuration tests, the authorization matrix, API functional tests, event contract tests). They are regenerated like everything else.
- **Coverage measures `src/` only.** A `coverlet.runsettings` you write (the starter does not ship one) excludes `**/gen-src/**` (and `**/Migrations/**`); generated tests exercising generated code count for nothing, so the number is about the code you wrote. A floor in `.coverage-floor` and a `coverage` gate with `needs: [tests]` ratchets it.
- **Unit tests mock everything** through the generated interfaces; a hand-built `DbContext` goes through `InMemoryDbTestHelper`. Functional tests go through `ApiTestFixture`. Mark integration tests with `[Trait("Category", "Integration")]` so `--filter "Category!=Integration"` is the daily run.
- **AwesomeAssertions, never FluentAssertions** (§2.2).

## 8. Agent instructions

Put the rules an agent will need in the first thirty lines of `CLAUDE.md` (or `AGENTS.md`), before anything else, because it reads them before it reads the error. The seed from `add-component` carries rules 1, 2 and 4; add 3 and 5 when you seed the contract (§6). An older repo writes all five in:

1. `*/gen-src/**` and every `*.g.cs` are generated from `../<spec-repo>`; the next regen overwrites them. **Never edit them.** If a task seems to need it, stop: the fix belongs in the spec or the generator. Say so and note that a regen is required. The only exception is a tracked patch (§9.1), and an agent proposes one rather than writing it.
2. Before writing a model, DTO, repository, mapper, service or controller by hand, check `gen-src/`. It probably exists.
3. Hand-written code goes in `src/`: `partial` classes in the generated namespace, concrete classes deriving from the generated `*Base`, `partial` mapper hooks. Never implement a generated `I{X}Handler` or `I{Tag}ApplicationService` directly.
4. The layering (§2.2) and where the seams live (§4).
5. The regen flow (§9), and that `./scripts/check-gen-contract.sh` and `./scripts/apply-gen-patches.sh --check` are the first things to run after any regen.

## 9. The regen flow

1. **The spec change merges** in the spec repo.
2. **Regenerate on a branch of this repo** with no uncommitted work. From the spec repo root (`cleanGenerated` deletes before it writes, so the tree must be disposable):
   ```bash
   cd ../hello-orders-specs
   ./scripts/specfuse/generate.sh Domain Infrastructure Api      # one jar run per group, bundled once
   ```
   `generate.sh` refuses a destination repo with uncommitted changes. With `scripts/post-generate.sh` wired in the spec repo (§9.1), each group's tracked patches go back on as soon as it is generated.
3. **Run the contract, then build.** `./scripts/check-gen-contract.sh` and `./scripts/apply-gen-patches.sh --check` first: a red rule is a generator defect or a hand-written file in the wrong place, and either is cheaper to see before the build. Then `dotnet build` and the unit tests. Fix the hand-written `src/` that the regen broke (a renamed member, a new abstract method on a base, a new placeholder contract); never the generated side.
4. **Review by file name, not by path.** A regen rewrites the whole tree, so diff size is not a signal. Diff changed models by file name (a moved file reads as delete plus add), diff each enum's **values**, diff operation parameter lists, trace every hand-written type that mirrors a generated one, and read `CHANGELOG.md` where the generator writes one. For C# it tracks Domain entities, value objects and services and the Test group's event builders, not controllers, DTOs or EF configuration, so it complements the file-by-file review rather than replacing it. Removals are the highest-risk content of a regen and nothing mechanical catches them.
5. **One PR per component**, containing the regen and only its required follow-ups. CI runs the contract and the mutation test, then the build.
6. **Merge, then advance the baseline** in the spec repo from the merged default branch, never from a local regen:
   ```bash
   cd ../hello-orders-specs
   ./scripts/specfuse/advance-state.sh --repo Backend --dry-run
   ./scripts/specfuse/advance-state.sh --repo Backend
   ```
   and open a spec-repo PR with only the changed `.specfuse/state/<group>.json` files ([`component-repos.md` §6](component-repos.md#6-advance-the-statedir-baseline-only-from-merged-component-code)).

When generated output is wrong, file it against the generator with the generated C# that is expected, never a proposed template change; the generator agent locates the template from the output shape. If the fix cannot wait, §9.1. When the spec is wrong, the component files a `specfuse:spec-issue` in the spec repo.

### 9.1 Temporary patches, until the generator is fixed

Sometimes generated code is wrong and the fix cannot wait for a generator release: it does not compile, or it does the wrong thing in a method you cannot override. "Never edit `gen-src/`" still holds in spirit: whatever you change must survive the next regen, be visible in review, and go away the moment the generator is fixed. A tracked patch does all three.

**First, look for a way that needs no patch.** In this order:

1. **The spec is wrong.** Fix it there and regenerate, or file a `specfuse:spec-issue` in the spec repo.
2. **Work around it from `src/`** with the §5 patterns: a `partial` member, an override on the generated `*Base` or `Default{Entity}Service`, a replacement registered after the generated call, a mapper hook. These survive every regen untouched. Mark each with a `// Workaround for clabonte/generator#NNNN` comment so it is found when the fix lands.
3. **Take the operation out of generation** with `x-manual` (§5.4) when the defect is confined to one operation and the hand-written version is small.
4. **Only then, patch `gen-src/`.**

Whichever you choose, file the defect against the generator first, with the generated C# you expected (§9). The patch names that issue; a patch without one is never removed.

**How a patch works.** `gen-patches/NNNN-<name>.patch` is a `git diff` of generated files, headed by `Generator-Issue:`, `Generator-Version:` and `Reason:` lines. `gen-patches/README.md` is the index: every active patch, its issue, and what breaks without it. The starter ships the index and `scripts/apply-gen-patches.sh`, which re-applies the patches after a regen and reports one line per patch:

| Report | Meaning | Do |
|---|---|---|
| `applied` | the patch went back on cleanly | commit it with the regen |
| `already present` | right after a regen, the generator now emits the fix itself | confirm, then retire the patch |
| `FAILED` | the generated code changed around it | re-derive the patch from the new output, or retire it if the defect is gone |

`--check` is the gate: every patch is applied, carries its header, is in the index, and only modifies existing files under `gen-src/`. A regen PR that forgot to re-apply a patch fails it.

**Re-apply on every regen, automatically.** The spec repo's `generate.sh` runs a project-owned `scripts/post-generate.sh` after each group. Have it call the component's script:

```bash
#!/bin/bash
# <spec-repo>/scripts/post-generate.sh <group> <language> <destination> <basePackage>
set -euo pipefail
if [ "$2" = "C#" ] && [ -x "$3/scripts/apply-gen-patches.sh" ]; then
  "$3/scripts/apply-gen-patches.sh" "$4"
fi
```

A `FAILED` patch exits non-zero and stops the run, so a regen never finishes with a patch silently dropped.

**Making one.** On a clean regen branch, edit the generated file, write the patch with its header and add the index row; the seeded `gen-patches/README.md` has the exact commands. Commit the patch, the patched files, the index row and a **Known failure modes** entry in `docs/generated-code-expectations.md` together. That entry is how the generator's consumer-QA reviewer learns the defect is known and tracked instead of reporting it again. A coding agent proposes a patch and waits; it never creates one on its own (§8).

**Keep patches small and away from the public surface.**

- Modify, never create or delete: a new type goes in `src/`. The path manifests record what the generator emits, and a patch that adds or removes a file makes them disagree with the tree.
- Leave the header block alone: `GEN-002` and `GEN-003` still apply to a patched file.
- The regen's `CHANGELOG.md` is written before the patch goes back on, while the baseline `advance-state.sh` captures comes from your merged, patched code. A patch that changes a tracked surface (a Domain entity, value object or service signature) therefore shows up in every regen's `CHANGELOG.md`. Say so in the PR rather than chasing it.

**Retiring one.** When the issue is fixed and the generator the spec repo runs (the kit's pin, or the project's `.specfuse/generator.lock`) reaches that release, regenerate and expect `already present`. Confirm the output is right without the patch, delete the patch file, move its row to **Retired**, and remove its expectations entry and any `src/` workaround tied to it. Review the index at every pin bump: a patch whose issue is closed but that still reports `applied` means the fix did not cover your case, so comment on or reopen the issue.

## 10. The audit checklist

Run from the component repo root. Every check names the section with the explanation and the fix. The IDs are stable; the interactive page uses the same ones.

### Layout (§1)

**CS-01 · The spec repo is a sibling checkout and every C# group's `destination` resolves to this repo.**
```bash
python3 -c 'import json,glob,os; p=glob.glob("../*/*-project.json")[0]; d=json.load(open(p)); print(p); [print(g["name"], os.path.realpath(os.path.join(os.path.dirname(p), g["destination"]))) for g in d["groups"] if g["language"] in ("C#","csharp")]'
```
Every printed path is this repo.

**CS-02 · One project folder per C# group `basePackage`, each with `gen-src/` and `src/`.**
```bash
for d in */gen-src; do p=${d%/gen-src}; [ -f "$p/$p.csproj" ] && [ -d "$p/src" ] && echo "ok  $p" || echo "FAIL $p"; done
```

**CS-03 · Nothing hand-written under `gen-src/`, no `.g.cs` outside it, every generated file marked.** Covered by `GEN-001` to `GEN-005`.
```bash
./scripts/check-gen-contract.sh --only GEN-001 GEN-002 GEN-003 GEN-004 GEN-005
```

### Build wiring (§2)

**CS-04 · `Directory.Build.props` turns default globbing off and compiles exactly `src\**\*.cs` and `gen-src\**\*.cs`.** `GEN-020`.
```bash
./scripts/check-gen-contract.sh --only GEN-020
```

**CS-05 · Project references express the layering.** Domain references nothing; Infrastructure never references Api; Api references Infrastructure only as the composition root. `GEN-013`, `GEN-014`, plus a look at the Api project:
```bash
./scripts/check-gen-contract.sh --only GEN-013 GEN-014 && grep -n ProjectReference *.Api/*.csproj
```

**CS-06 · A fresh regen builds with zero edits.**
```bash
dotnet build --nologo
```
Adding `-warnaserror` (or `TreatWarningsAsErrors`, §2.1) once the build is clean is a team choice, not a generator requirement.

**CS-07 · `global.json` pins the SDK; the solution lists every project.**
```bash
cat global.json && dotnet sln list 2>/dev/null || grep -c '<Project Path' *.slnx
```

**CS-08 · Generated code and the generator's path manifests are committed.** `GEN-021`, plus:
```bash
./scripts/check-gen-contract.sh --only GEN-021 && git ls-files '*/gen-src/*' | wc -l && git ls-files '*.generated-paths.json'
```
The count is positive and every C# group's manifest is listed.

### Composition root and seams (§4)

**CS-09 · `Program.cs` calls every generated registration the groups emit.**
```bash
grep -n 'AddServices\|AddRepositories\|AddSpecfuseAuthorization\|AddConcurrencyTokenSink\|AddEventRuntime\|AddInMemoryDatabase\|AddSqlServerDatabase\|Workers()' *.Api/src/Program.cs
```
One line per registration the generated `gen-src/**/*ServiceCollectionExtensions*.g.cs` and `ConfigureServices.g.cs` files define.

**CS-10 · Exactly one `UserHelper.GetUser(ClaimsPrincipal)` exists, hand-written or generated.**
```bash
grep -rln 'class UserHelper' */src */gen-src | wc -l
```
Prints `1`.

**CS-11 · An `ExceptionFilter` maps the generated domain exceptions and is added to `AddControllers`.**
```bash
grep -n 'ExceptionFilter' *.Api/src/Program.cs *.Api/src/Filters/ExceptionFilter.cs | head
```

**CS-12 · Every placeholder contract the spec needs has a hand-written implementation.** For each row of §4.3 that applies (tenancy declared, encryption declared, concurrency in use):
```bash
grep -rn 'ITenantResourceCheck\|IRecordVisibilityResolver\|IPrincipalKeyResolver\|ICallerFieldResolver\|IDataKeyProvider\|IKeyWrapper' */src --include='*.cs' | grep -v '^.*Test' | head
```
Each contract that applies has a `class … : I…` line, and `dotnet run --project *.Api` serves a role-gated request without a `NotConfigured` exception.

**CS-13 · With a Test group, `ApiTestFixture`, `ApiTestBase` (`CreateHttpClient`, `EnsureFakeData`) and `InMemoryDbTestHelper` exist in `src/` with the namespaces the generated tests import.**
```bash
grep -rln 'class ApiTestFixture\|class ApiTestBase\|class InMemoryDbTestHelper' *.Test/src && grep -rh '^using .*Test\.' *.Test/gen-src | sort -u
```

### Extension discipline (§5)

**CS-14 · Hand-written extensions are `partial` classes in the generated type's namespace, in `src/`.**
```bash
grep -rn 'partial class' */src --include='*.cs' | head
```
No generated type is redeclared non-partial, and `GEN-030` is green.

**CS-15 · Every generated `*Base` has a concrete class deriving from it and nothing implements a generated handler interface directly.** `GEN-040` to `GEN-042`.
```bash
./scripts/check-gen-contract.sh --only GEN-040 GEN-041 GEN-042
```

**CS-16 · Mapper hooks are implemented as `partial` methods on the generated `{Aggregate}DomainMapperHooks`, never by editing the mapper.**
```bash
grep -rn 'static partial void OnAfterTo' */src --include='*.cs' | head
```

**CS-17 · Custom services and decorators are registered after the generated `AddServices()` / `AddRepositories()` calls.**
```bash
grep -n 'AddServices\|AddRepositories\|AddScoped<I' *.Api/src/Program.cs
```
Every `AddScoped<I…Service` line comes after the `AddServices()` line.

### Contract and CI (§6, §7)

**CS-18 · `gen-contract.yml` is present, the engine runs, and every rule is green.**
```bash
./scripts/check-gen-contract.sh
```

**CS-19 · `docs/generated-code-expectations.md` exists with the five section names.**
```bash
grep -n -i '^#\+ *\(Standing expectations\|Integration contract\|Known failure modes\|Accepted quirks\|Do not report\)' docs/generated-code-expectations.md
```
Five lines.

**CS-20 · `.specfuse/verification.yml` has a `code` gate set with `gen-contract`, `gen-patches`, `build` (`needs: [gen-contract, gen-patches]`) and `tests` (`needs: [build]`).**
```bash
grep -n -A2 'name: *\(gen-contract\|gen-patches\|build\|tests\)$' .specfuse/verification.yml
```

**CS-21 · CI runs the contract before the build on every pull request.**
```bash
grep -n 'check-gen-contract\|dotnet build' .github/workflows/*.yml | head
```
The contract step appears before the build step, or in its own SDK-free workflow.

**CS-22 · Coverage excludes `gen-src/` and migrations.**
```bash
grep -n 'ExcludeByFile' coverlet.runsettings
```

**CS-23 · The mutation test exists and every rule bites.**
```bash
./scripts/test-gen-contract.sh
```
`0 missed`.

### Agent instructions and workflow (§8, §9)

**CS-24 · `CLAUDE.md` or `AGENTS.md` carries the five rules of §8 near the top.**
```bash
grep -n -i 'gen-src\|never edit\|partial\|Base\|check-gen-contract' CLAUDE.md AGENTS.md 2>/dev/null | head
```

**CS-25 · The README documents the sibling layout, the regen commands and the baseline step.**
```bash
grep -n 'generate.sh\|advance-state.sh\|\.\./' README.md | head
```

**CS-26 · Every temporary patch to generated code is applied, indexed, and names a generator issue.**
```bash
./scripts/apply-gen-patches.sh --check && grep -h '^Generator-Issue:' gen-patches/*.patch 2>/dev/null
```
Exit 0, and every issue listed is still open: a closed one is a patch to retire (§9.1).

## Where to go next

- [`component-repos.md`](component-repos.md): the language-neutral rules, the commit policy and the baseline step in full
- [`add-component.md`](add-component.md): the seeded host for a new C# repo
- [`Project_File.md`](../handbooks/Project_File.md): `destination`, `basePackage`, `cleanGenerated`, `tenancy`, the C# artifact catalogue
- [`templates/component-contract/csharp/`](../templates/component-contract/csharp/): the starter contract, its mutation test, the expectations skeleton and the patch tooling
- [`csharp-component.html`](csharp-component.html): this guide as an interactive map, with the checklist you can tick off and copy
