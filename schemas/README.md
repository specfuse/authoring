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

The AsyncAPI and Arazzo rulesets reference 15 custom Spectral functions (e.g., `asyncChannelMessageCompleteness`, `arazzoAsActorExists`, `asyncTriggerWhenCoherence`). The kit bundles their implementations under [`spectral/functions/`](spectral/functions/). Spectral discovers them automatically because that directory is `./functions/` relative to each ruleset file — no `functionsDir` setting is required.

If a project extends the kit's rulesets from a different working directory, ensure the relative `functions/` path still resolves, or set `functionsDir: <path-to-kit>/schemas/spectral/functions` explicitly in the project ruleset.

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
    given: $.paths[*][*][?(@ && @.security)]["x-roles"][*]
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

## Running Spectral so a crash cannot pass as clean

**The failure mode of a validation tool is silence.** When Spectral cannot run —
a null it chokes on, an unresolvable `$ref`, a mistyped ruleset path, an OOM, a
timeout — it emits no findings. A wrapper that asks *"did Spectral report
errors?"* gets **no**, and concludes the spec is clean. There is no partial
output and no non-zero finding count to notice. A project can sit in that state
for months believing it is gated.

So do not ask whether findings were reported. Ask whether Spectral ran:

| Exit code | Meaning | Verdict |
|---|---|---|
| `0` | findings below the fail severity | pass |
| `1` | findings at or above the fail severity | fail — real findings |
| `>= 2` | Spectral itself failed | **fail — a crash, not a clean spec** |
| any, empty report | Spectral produced nothing at all | **fail — a crash** |

The kit ships this as [`scripts/spectral-lint.sh`](../scripts/spectral-lint.sh)
and routes every CI invocation through it. Copy it, or inline the check:

```bash
spectral lint --ruleset "$RULESET" --fail-severity error "$TARGET" >"$REPORT" 2>&1
STATUS=$?
cat "$REPORT"

if [[ $STATUS -ge 2 ]]; then
  echo "Spectral FAILED TO RUN (exit $STATUS) — this is not a clean spec." >&2
  exit "$STATUS"
fi
if [[ ! -s "$REPORT" ]]; then
  echo "Spectral produced no report — treat as failure, not a clean run." >&2
  exit 1
fi
```

Adopt this in any wrapper you write, including ones that never touch these
rulesets. It is not specific to a rule or a bug; it is specific to the fact that
silence is the default shape of a broken lint run.

### Nulls abort the whole run

A concrete instance of the above, worth knowing because it is invisible without
deliberately checking. The upstream `spectral:oas` rule
`duplicated-entry-in-enum` has an unguarded recursive-descent filter:

```
$..[?(@property !== 'properties' && @.enum && @.enum.constructor.name === 'Array')]
```

There is no `@ &&` before `@.enum`. Any null value anywhere in the document
makes it throw `Cannot read properties of null (reading 'enum')`, which aborts
the entire run and emits zero findings. Reproduced with Spectral CLI 6.16.2 /
nimma 0.7.2 against a twelve-line OpenAPI document containing one
`example: null`. Nulls that trigger it include property-level `example: null`,
meaningful nulls inside example payloads (`effectiveTo: null` meaning
open-ended), and null schema nodes.

The kit turns that rule off and ships the null-safe
`specfuse-no-duplicate-enum-entries` in its place, so extending
`specfuse-openapi.yaml` gets the fix. **Overlay rules you write yourself are
still your responsibility**: put `@ &&` first in every filter that dereferences
`@`.

```yaml
given: $.components.schemas[?(@ && @["x-entity"])]     # safe
given: $.components.schemas[?(@["x-entity"])]          # crashes on a null schema node
```

Filters that only test `@property` never dereference `@` and need no guard.

Two regression fixtures under [`spectral/fixtures/`](spectral/fixtures/) pin this
in CI. Note that they assert the replacement rule still **fires**, not merely
that the run survives — a rule that stops crashing by never running is
indistinguishable from a fixed one if you only watch the error count fall.

## `$ref` resolution: which rules must run unresolved

**Spectral resolves `$ref`s before linting by default.** For most rules that is
what you want. For any rule that inspects *schema shape*, it inverts the rule's
meaning.

Take a rule forbidding inline enums. A compliant property —

```yaml
status:
  $ref: './StatusEnum.yaml'
```

— is inlined during resolution, at which point it is indistinguishable from a
hand-written inline enum. The rule fires. Worse, the finding is reported at the
*target's* location rather than the referencing property, so the paths look
nothing like where the supposed violation is. The net effect is a rule that
flags precisely the pattern it exists to require: every correct `$ref` is a
violation, an actual inline enum is also a violation, and the rule cannot tell
them apart.

The fix is `resolved: false`, which keeps `$ref`s intact — the whole point,
since a `$ref` *is* the compliant form:

```yaml
specfuse-no-inline-enums:
  resolved: false
  given: $.components.schemas[*].properties[?(@ && @.enum)]
  then:
    function: falsy
```

Both kit rules of this shape (`specfuse-no-inline-enums`,
`specfuse-no-inline-objects`) already carry it. If you write overlay rules that
inspect schema shape, they need it too.

**A second, less obvious case: rules that key on the `$ref`'s NAME.** Resolution
does not just inline the target, it erases which target it was. The
`specfuse-read-model-*` and `specfuse-projection-coherence` rules all decide
something from the referenced schema's *name* — is this embed an entity, a
`Basic*` projection, or a plain enum — so a resolved document leaves them
nothing to decide from. They carry `resolved: false` for that reason rather
than the inline-vs-`$ref` one. The generator's equivalent checks scan the raw
YAML for the same reason.

### Auditing your own ruleset for resolution sensitivity

`$ref` resolution affects **every rule that inspects schema shape**, not just
the obvious two. The audit is cheap and worth doing once: run the whole ruleset
forced-unresolved and diff the per-rule finding counts against the resolved run.
Anything that moves is resolution-sensitive and needs a deliberate decision
about which mode is correct for it.

When you fix a rule this way, verify it in both directions. **A rule that stops
false-positiving by never firing at all looks identical to a fixed rule if you
only measure the error count going down.** Build a fixture with a genuine inline
enum, a genuine inline object, and a compliant `$ref`, then assert the rule
catches the first two and ignores the third.

## Auditing your own ruleset for rules that select nothing

A Spectral rule only speaks when a document violates it. So a rule whose `given`
selects **zero nodes** is indistinguishable from a rule that passes: both emit
silence, and silence is what CI reads as success. A clean run and a dead rule
look identical forever.

Eleven rules in `specfuse-openapi.yaml` — nine at `severity: error` — sat inert
for the entire life of the kit for exactly that reason (authoring #73). They
shared this `given`:

```yaml
given: $.paths[*][get,post,put,patch,delete][?(@ && @.security)]
```

which reads as "every secured operation" and evaluates as something else. A
JSONPath filter selects among the node's **children**, so after the method union
has already selected the operation, `[?(@ && @.security)]` asks *which
properties of this operation are themselves objects with a truthy `.security`* —
`summary`, `parameters`, `responses`, none of which is. The empty set, in every
valid OpenAPI document. The filter has to sit one level up, where the operation
is itself the child being filtered:

```yaml
given: $.paths[*][?(["get","post","put","patch","delete"].indexOf(@property) !== -1 && @.security)]
```

### The check

`scripts/spectral-rule-coverage.py` audits this automatically. For each rule it
synthesises a probe with the same `given` and the same `resolved` setting, and a
`then` that fails against any value at all:

```yaml
then: { function: schema, functionOptions: { schema: { not: {} } } }
```

`not: {}` matches nothing, so every selected node reports. The finding count per
rule is therefore the number of nodes its `given` actually selects, and zero
means the rule is inert. Run it over the corpus you already lint:

```bash
scripts/spectral-rule-coverage.py \
  --ruleset schemas/spectral/specfuse-openapi.yaml \
  --allowlist schemas/spectral/coverage-allowlist.yaml \
  bundled.yaml 'fixtures/*.yaml'
```

A rule can also select nothing because your corpus contains no instance of the
construct it targets. Those go in the allowlist **with a reason**, and the check
runs in both directions — an entry that starts matching also fails the build, so
the allowlist cannot decay into a blanket exemption. Prefer adding the construct
to a fixture over adding a line to the allowlist.

One caveat worth knowing if you write your own version: Spectral compiles every
rule's JSONPath into a single traversal program, and structurally similar
expressions can **suppress one another** when probed together. Probing
`specfuse-404-predefined` alongside `specfuse-400-predefined` reports zero for
the first; probing it alone reports eleven. The script re-probes every apparent
zero-match in isolation before believing it, because a harness that reported a
live rule as dead would be making the same mistake it exists to catch.

### What this does not prove

It proves a rule **selects**. It does not prove a rule **rejects** — a `then`
can be silent on a live `given` too, and three of those eleven rules stayed
silent even after their JSONPath was repaired:

- `function: pattern` reports nothing when the field is **absent**, so a
  `field: $ref` + `pattern` check passed any response that declared no `$ref` at
  all. Pair it with a `truthy` check on the same field.
- A `field: $ref` check on the **resolved** document sees a ref that has already
  been inlined. See the `resolved: false` section above; the same trap catches
  any rule keying off a ref's name, including
  `specfuse-list-response-requires-pagination-params`.

The layer above this one is a fixture that violates each rule once and asserts
the finding appears. `schemas/spectral/fixtures/inert-rules-regression.yaml` is
that fixture for the twelve OpenAPI rules above; the thirteenth is asserted
against the AsyncAPI ruleset. CI asserts every one of them fires.

## Turning the ruleset on against existing specs

Switching a lint gate on against specs that predate it tends to produce a large
first number. Both obvious responses fail:

- **Block every PR until all of them are fixed.** Nothing merges for weeks, so
  in practice the gate gets disabled or bypassed — which is usually how a gate
  ends up broken in the first place.
- **Run it non-blocking.** Errors accumulate exactly as before and the gate
  reports into a void.

Neither converges. What works is a **per-rule baseline ratchet**: commit the
current error count for each rule, then fail only on regression.

```json
{ "specfuse-emits-required-on-writes": 33 }
```

| Condition | Result |
|---|---|
| A rule exceeds its baseline | fail — regression |
| A rule absent from the baseline reports anything | fail — newly violated rule |
| A rule is below its baseline | pass, and report that it can be lowered |

Inherited debt does not block PRs; new debt does. The gate is useful from day
one without a cleanup project as a precondition.

Three details decide whether it actually converges:

1. **Per-rule, never a single total.** A total-only ratchet lets someone
   introduce three new violations while fixing three old ones and call it even.
   Per-rule means a fix in one area cannot mask a regression in another.
2. **Report improvements and prompt to lock them in.** When a count drops, say
   so and tell the author to re-baseline. Otherwise the baseline silently
   retains headroom for errors that no longer exist, and the ratchet stops
   ratcheting.
3. **Test that it fails.** A ratchet that never fires is indistinguishable from
   one that works. Delete a required field from an entity and confirm the gate
   fails with the right message — do not settle for watching a clean tree pass.

Same principle as the empty-report check above: the failure mode of a validation
tool is silence, so the thing worth testing is that it makes noise when it
should.

### A reference implementation

`scripts/spectral-ratchet.py` implements the pattern above. It is a **reference
implementation, not a supported kit tool** — documented, working, and carrying
no compatibility guarantee across kit releases. Copy it into your project and
own it. The kit is a spec-authoring contract, deliberately not a CI product.

```bash
# seed a baseline from where you are today
scripts/spectral-ratchet.py --ruleset <ruleset> --baseline .spectral-baseline.json <targets> --update

# then, in CI
scripts/spectral-ratchet.py --ruleset <ruleset> --baseline .spectral-baseline.json <targets>
```

Exit `0` pass, `1` regression, `2` could not run. It counts error-severity
findings only, per rule.

Two behaviours worth knowing before you wire it up:

**It refuses to accept silence.** A crashed Spectral produces no findings, and
zero findings is under every baseline — so without a guard a crash reads as a
clean run *and* as an improvement, and `--update` would then rewrite every
baseline to zero and permanently disarm the gate. The script treats a Spectral
exit `>= 2`, an empty or unparseable report, and a total of zero against a
non-empty baseline as **could not run**. `--update` additionally refuses when
half or more of the baselined rules go to zero at once, which is what a partial
crash or a mistyped target looks like; pass `--force` when the cleanup is real.

**Rule IDs in a committed baseline are a coupling surface.** This kit renamed
every rule once already (`rm-*` → `specfuse-*`), and a rename turns *"rule not
in the baseline"* into a hard failure on every rule simultaneously. The script
detects that shape — every baselined rule silent while unknown rules fire — and
tells you to re-baseline rather than reporting a wall of spurious regressions.
Re-baseline deliberately across any release that renames rules, and read the
diff rather than trusting the counts to carry over.

## Rename tracking

The kit renamed all Spectral rule identifiers from the legacy `rm-*` prefix (inherited from the source project) to `specfuse-*`. The 12 rules whose renames were declared canonical in `compatibility.md` §1 are tracked there; this commit applied the same `rm-* -> specfuse-*` rule mechanically to every other ruleset entry as well. See `compatibility.md` for the generator-side follow-up.
