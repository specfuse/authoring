# Field Encryption — Runtime Contract

> **What this is.** `x-protection: {atRest: encrypted}` is a specification act with a
> runtime bill attached. From generator `0.13.0` the declaration emits a persistence
> path, and that path resolves contracts the application must provide. Nothing warns
> at build time and nothing fails at startup: the first symptom of an unsatisfied
> contract is an exception the first time an encrypted value is read or written.
>
> This page is the bill. It is written as contract — *a key provider*, *a failure
> classifier* — so it governs every target language. Names shown are the C# ones,
> because C# is the target that has them today.

Companion to `Vendor_Extensions.md` §1.5, which covers the authoring side: what to
declare, how columns are sized, which targets are encryptable, and why renaming one
is a data migration.

---

## 1. Register it, or it does not exist

Four contracts are resolved from the application's service provider. **Nothing generated
registers them for you**, and the generated DI helper is not called for you either —
adding it to your composition root is your step, beside the ones you already make for
repositories and the concurrency-token sink.

| Contract | Who provides it |
|---|---|
| **data key provider** | you |
| **key wrapper** (KEK) | you |
| **decryption-failure classifier** | you |
| **poisoned-field tracker** | generated code calls it; you register an implementation |

The two key contracts register as **throwing placeholder factories**. That combination
is load-bearing in two directions, and the generated code says so itself:

- a *try-add* registration yields to one you made first, so writing your own provider is
  all it takes to never meet the placeholder;
- validating the container on build **does not invoke an implementation factory** — it
  checks that a call site can be constructed, not that it succeeds — so wiring this up
  never changes whether a host boots.

What changes is the message on first resolution: a named *"not configured"* failure
telling you which contract is missing, instead of the framework's generic
*"unable to resolve service for type…"*.

**Failing at boot instead is opt-in.** A separate assertion helper, called from your
composition root once the container is built, turns an unwritten provider into a startup
failure. It is deliberately separate: an eager resolve inside the registration call would
stop every host that has not written a provider yet, which is exactly what the
registration call is shaped never to do.

---

## 2. Exactly one failure is absorbed

This is the rule that decides whether a bad day costs you a stack trace or your data.

A decryption failure is classified into a **closed set of two**: the one failure a
correctly operating system expects, and everything else.

| Disposition | Meaning |
|---|---|
| **crypto-shredded** | the key the envelope names was destroyed on purpose — the expected way a field becomes permanently unreadable |
| **unexpected** | anything else: tampered or truncated ciphertext, a key that should exist and does not, a defect |

**Only the first is absorbed. Everything else rethrows.**

Three properties of that set are deliberate and worth not re-litigating:

**Unexpected is the zero value.** An uninitialised field, a `default` expression or a path
that never assigns an outcome resolves to *unexpected* — a thrown, visible defect — never
to the permissive disposition. The contract fails closed.

**There is no "not encrypted yet" member**, and that is not an omission. Ciphertext lives
in a shadow column, so a row written before its property was encrypted carries a NULL
shadow value that never reaches the decrypt path at all. **Absence is not a decryption
failure**, and a row predating the migration is not something the classifier ever sees.

**Adding a third member is a visible contract change** — every classifier and every switch
over the set has to answer for it. That is the point of keeping it closed.

### Why an empty value must never stand in for a failed decrypt

The instinct is to mirror the try/catch-to-empty pattern used for JSON-backed value
objects. **Here it destroys data.** An empty value materialised in place of a failed
decrypt is written back by the save path as fresh, valid ciphertext, and the original is
unrecoverable. The failure has to surface, or the field has to be marked — never quietly
replaced.

---

## 3. A poisoned read needs somewhere to surface

A field that failed to decrypt must be distinguishable from a field that legitimately
holds nothing. Without that distinction the save path cannot know to leave the column
alone, which is how §2's data loss happens in practice.

Two halves, both on one contract: the read path **marks** a property it could not decrypt,
and generated code that needs the marks **reads them back**. Reading them off the contract
rather than off a member you declare is what keeps generated code from binding to yours.

Entities are keyed by **reference identity** — two materialisations of the same row are two
entities, each with its own marks — and implementations hold them **weakly**, so a
long-lived context does not pin every materialised row for as long as the tracker lives.

**The spec surface has an obligation here too.** From generator `0.13.0` an entity declaring
`atRest: encrypted` on one of its own properties must expose a `readOnly` string array named
`unavailableProperties`, or generation aborts. See `Vendor_Extensions.md` §1.5.

---

## 4. Keys are resolved by the envelope, never by ambient context

Every ciphertext carries the identifier of the key that wrote it. **Resolve by that
identifier.**

Resolving by "the currently active key", or by an ambient tenant taken from the request,
breaks three things at once: cross-tenant reads, batch jobs that touch more than one
tenant's rows, and any migration. It also makes rotation a rewrite — with envelope-bound
resolution, a rotated key is simply a key the provider still knows.

**Key scope is declared in the specification**, not inferred: the project file's
`encryption.keyScope` (`Project_File.md` §15) is carried into generated code, and a host
configured for a different scope than the project declares **refuses to continue** rather
than writing ciphertext keyed at a scope the specification never claimed. Declaring nothing
disables that check — the mismatch can never be raised.

---

## 5. A NULL ciphertext column is not a failure

It is a row written before the property was encrypted. Skip it **before** any key is
resolved. As §2 notes, the generated read path already does this by construction — a NULL
shadow value never reaches the decrypt path — but a hand-written migration or backfill that
reads the column directly has to make the same distinction itself.

---

## 6. One interceptor instance, not one per scope

Target-specific, and the kind of thing every consumer rediscovers.

In C#, registering the encryption interceptors per-scope or per-container **multiplies the
ORM's internal service providers**, and the host fails once an internal threshold is
crossed. Register them once, at the lifetime the ORM expects for interceptors.

This is an EF Core property rather than a Specfuse contract. It is recorded here because
the failure it produces — a host that works in tests and dies under load — is expensive to
diagnose from first principles.

---

## Checklist — you have adopted `atRest: encrypted`

1. Call the field-encryption registration from your composition root. Nothing calls it for you.
2. Implement and register a **data key provider** and a **key wrapper**. Until you do, the first encrypted read throws a named "not configured" failure — not a build error, not a boot error.
3. Implement a **failure classifier** that returns *crypto-shredded* for a deliberately destroyed key and *unexpected* for everything else. Fail closed.
4. Register a **poisoned-field tracker**, and expose `unavailableProperties` on every entity that encrypts one of its own properties.
5. Resolve keys **from the envelope's key id**. Never from ambient context.
6. Decide whether an unwritten provider should stop the host at startup; if so, call the assertion helper once the container is built.
7. Register interceptors **once**, not per scope.
8. Before renaming an encrypted property, an entity, or anything that rewrites a row's primary key — read `Vendor_Extensions.md` §1.5. It is a data migration, not a rename.
