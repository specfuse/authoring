# schemas/

Machine-readable enforcement of the conventions documented in `handbooks/`. Two pieces:

- **`arazzo-extensions/`** — JSON Schemas (Draft 2020-12) for the Arazzo vendor extensions (`x-actors`, `x-async`, `x-as`, `x-doc`, `x-mcp`, `x-recipe`, `x-sample`, `x-setup`, `x-ui`, `x-version`) plus a composed schema (`specfuse-arazzo-combined.schema.json`) that attaches them at the correct paths in an Arazzo document. The `x-sample` schema also applies to OpenAPI property annotations (see `handbooks/API_Handbook.md` §10).
- **`spectral/`** — Three Spectral rulesets:
  - `specfuse-openapi.yaml` — OpenAPI 3.x conventions
  - `specfuse-asyncapi.yaml` — AsyncAPI 3.0 conventions
  - `specfuse-arazzo.yaml` — Arazzo 1.0.1 scenario/recipe conventions

The `$id` base for the JSON Schemas is `https://schemas.specfuse.dev/arazzo/...`. The IDs are stable identifiers — projects do not need to host the URL; tooling resolves locally via the path.

## How to consume

### JSON Schemas

Reference them from project specs (or from doc-generation tooling) by relative path:

```yaml
# In a project's Arazzo document or vendor-extension doc-generator config
$ref: ../../spec-authoring-kit/schemas/arazzo-extensions/x-sample.schema.json
```

For Arazzo documents the composed schema is the easiest entry point:

```yaml
$ref: ../../spec-authoring-kit/schemas/arazzo-extensions/specfuse-arazzo-combined.schema.json
```

### Spectral rulesets

Extend the kit rulesets in your project's own `.spectral.yaml`:

```yaml
extends:
  - ../spec-authoring-kit/schemas/spectral/specfuse-openapi.yaml
  - ../spec-authoring-kit/schemas/spectral/specfuse-asyncapi.yaml
  - ../spec-authoring-kit/schemas/spectral/specfuse-arazzo.yaml

rules:
  # Project-specific overlays go here (see "What the project must provide" below).
```

The AsyncAPI and Arazzo rulesets reference custom Spectral functions (e.g., `asyncChannelMessageCompleteness`, `arazzoAsActorExists`). Those functions are not bundled in the kit yet — projects need to provide them at `functions/{functionName}.js` relative to the ruleset that loads them, or via Spectral's `functionsDir` config. Importing the JS implementations from the generator (or maintaining a kit-side copy) is on the Phase 7+ roadmap.

## What the project must provide (overlays)

The kit's rules are deliberately **structural** for values that are project-defined. Projects layer the value-set constraints in their own overlay:

| Value set | Kit rule (shape only) | Project overlay must add |
|---|---|---|
| Role enum | `specfuse-auth-roles-pascal` (OpenAPI), `specfuse-arazzo-actors-role-shape` (Arazzo) | An enumeration rule constraining `x-roles[*]` and `x-actors.*.role` to the project's declared role set (typically `common/enums.yaml#/Role`). |
| Domain list | `specfuse-arazzo-domain-shape` (Arazzo), `specfuse-async-channel-domain-kebab` (AsyncAPI), `specfuse-async-operation-tag-pascal` (AsyncAPI) | An enumeration rule constraining `x-domain` (kebab-case) and the AsyncAPI operation tag (PascalCase) to the project's declared domain list. |
| Channel address prefix | `specfuse-async-channel-address-format` (shape only) | A pattern rule pinning the prefix (e.g., `^myproject\.events$` for the shared event topic, `^myproject\.scheduling\.[a-z-]+$` for scheduled triggers). |
| Path-pattern action endpoints | `specfuse-post-201-location` (excludes `/bulk/` and `/_system/` only) | Optional: exclusions for the project's bespoke action verbs (e.g., `/dismiss`, `/process`). |

A minimal project overlay looks like:

```yaml
# myproject/.spectral.yaml
extends:
  - ../spec-authoring-kit/schemas/spectral/specfuse-openapi.yaml
  - ../spec-authoring-kit/schemas/spectral/specfuse-asyncapi.yaml
  - ../spec-authoring-kit/schemas/spectral/specfuse-arazzo.yaml

rules:
  myproject-auth-roles-enum:
    description: "x-roles values must come from common/enums.yaml#/Role"
    severity: error
    given: $.paths[*][*][?(@.security)]["x-roles"][*]
    then:
      function: enumeration
      functionOptions:
        values: [Admin, Customer, Authenticated]   # project-specific

  myproject-async-event-topic-must-be-shared:
    description: "All event-topic channels must use the literal myproject.events address"
    severity: error
    given: "$.channels[?(@['x-channel-type'] == 'event-topic')].address"
    then:
      function: pattern
      functionOptions:
        match: "^myproject\\.events$"
```

## Rename tracking

The kit renamed all Spectral rule identifiers from the legacy `rm-*` prefix (inherited from RestoManager) to `specfuse-*`. The 12 rules whose renames were declared canonical in `compatibility.md` §1 are tracked there; this commit applied the same `rm-* -> specfuse-*` rule mechanically to every other ruleset entry as well. See `compatibility.md` for the generator-side follow-up.
