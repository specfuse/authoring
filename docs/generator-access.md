<!--
Copyright 2026 Specfuse Contributors
Licensed under the Apache License, Version 2.0. See LICENSE.
-->

# Generator access

The code generator is distributed as a **private** GitHub Release asset on
[`Specfuse/generator-dist`](https://github.com/Specfuse/generator-dist). The kit
itself is public; the generator binary is not. A client can author and validate
specs with only the public kit — running `specfuse-kit generate` is the one step
that needs access to the private distribution repo.

This page is for **maintainers** granting access, and for **clients** setting it
up. The access model is deliberately narrow: read-only, to one private repo.

---

## For maintainers — granting a client access

Pick the least-privilege option that fits how the client is organized.

### Option A — outside collaborator (simplest, per-person)

Add the client's GitHub user to `Specfuse/generator-dist` with the **Read** role:

```
Repo → Settings → Collaborators and teams → Add people → role: Read
```

Read is enough to download release assets. Do **not** grant Write/Triage/Admin.

### Option B — org team (best for a client with several engineers)

Create a team in the Specfuse org, give the team **Read** on
`Specfuse/generator-dist`, and add the client's members to the team. Revoking is
then a single team-membership change.

### Option C — fine-grained PAT for CI / headless use

When the client runs `generate` from CI or a machine without interactive login,
have them create a **fine-grained personal access token** scoped to exactly:

- **Resource owner:** `Specfuse`
- **Repository access:** only `Specfuse/generator-dist`
- **Permissions:** `Contents: Read-only`

They expose it as `SPECFUSE_TOKEN` (see client section). The token grants nothing
beyond reading that one repo's contents/releases.

### Revoking

- Option A: remove the collaborator.
- Option B: remove them from the team (or the team's access).
- Option C: revoke the PAT.

Revoking cuts off the generator immediately. The kit stays fully usable — only
`generate` stops resolving the jar. Nothing the client already cached is pushed
or pulled back, but they cannot fetch a new/updated jar.

> **Never** send a client a token you created. Tokens are created by the holder,
> scoped by them, and revocable by you via collaborator/team removal.

---

## For clients — setting up access

The CLI resolves the generator with **one** of the following. The GitHub CLI is
the simplest.

### Using the GitHub CLI (recommended)

```bash
# install gh: https://cli.github.com/
gh auth login        # authenticate as the user that was granted Read access
```

`specfuse-kit generate` detects `gh` and uses it transparently — no token to
manage.

### Using a token (CI / headless)

Create a fine-grained PAT as described in Option C above, then:

```bash
export SPECFUSE_TOKEN=github_pat_xxx
specfuse-kit generate <args>
```

In CI, store it as a secret and export it for the generate step only.

### What happens on first run

1. The CLI reads the generator pinned for your kit version
   ([`generator.lock`](../generator.lock)).
2. Downloads `specfuse-generator-<version>.jar` from the `Specfuse/generator-dist`
   release tagged `v<version>` (via `gh` or `SPECFUSE_TOKEN`).
3. **Verifies the SHA-256** against the pin and aborts on mismatch.
4. Caches it under `~/.specfuse/jars/` (override the root with `$SPECFUSE_HOME`)
   and runs `java -jar`. Later runs reuse the cache.

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `need the 'gh' CLI or SPECFUSE_TOKEN ...` | no auth available | `gh auth login`, or export `SPECFUSE_TOKEN` |
| `404` / `release not found` on download | no Read access, or wrong account | confirm the maintainer granted access to the authenticated user |
| `no generator is pinned for this kit version yet` | kit release predates a published generator | upgrade `specfuse-kit` once a generator-bearing release ships |
| `checksum mismatch on downloaded generator jar` | corrupted download or a tampered asset | delete `~/.specfuse/jars/` and retry; if it persists, report it — do not use the jar |
| `'java' not found` / wrong version | no JRE 17+ | install a JRE that meets `min_java` in `generator.lock` |

---

## Security notes

- **Least privilege:** grant only `Read` on only `Specfuse/generator-dist`. The
  generator needs nothing else.
- **Checksum pinning:** the kit verifies every jar against the SHA-256 committed
  in its public `generator.lock`. A swapped or corrupted asset fails closed.
- **Token hygiene:** prefer `gh` for humans; reserve `SPECFUSE_TOKEN` for CI,
  store it as a secret, scope it fine-grained, and rotate it on a schedule.
- **Revocation is clean:** removing access stops generation without affecting the
  client's specs, the public kit, or anything already generated.

See also: [`getting-started.md`](getting-started.md) §5–6.
