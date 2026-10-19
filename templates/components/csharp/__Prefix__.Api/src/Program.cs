// Seeded once by `specfuse authoring add-component`. Yours to change.
using {{Prefix}}.Api.Authorization;
using {{Prefix}}.Api.Filters;
using {{Prefix}}.Domain;
using {{Prefix}}.Infrastructure;
using {{Prefix}}.Infrastructure.Concurrency;
using {{Prefix}}.Infrastructure.Events;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers(options => options.Filters.Add<ExceptionFilter>());

// Generated registrations (gen-src/**/ConfigureServices.g.cs and friends).
builder.Services.AddServices();
builder.Services.AddRepositories();
builder.Services.AddSpecfuseAuthorization();
builder.Services.AddConcurrencyTokenSink();

// Events are buffered per request and dispatched on commit. AddNullEventDispatcher
// drops them, which suits local runs without a broker. In production, call
// AddEventRuntime() (Azure Service Bus topics) or register a dispatcher of your own.
builder.Services.AddEventRuntimeCore().AddNullEventDispatcher();

// ConnectionStrings:Default selects SQL Server; without it the app runs on an
// in-memory database, so it starts with no infrastructure at all.
var connectionString = builder.Configuration.GetConnectionString("Default");
if (string.IsNullOrEmpty(connectionString))
    builder.Services.AddInMemoryDatabase("{{Prefix}}");
else
    builder.Services.AddSqlServerDatabase(connectionString);

var app = builder.Build();
app.MapControllers();
app.Run();
