<!--
Copyright 2026 Specfuse Contributors
Licensed under the Apache License, Version 2.0. See LICENSE.
-->

# Security Policy

## Reporting a Vulnerability

Report vulnerabilities via this repo's **GitHub Security Advisories**
(Security tab → Report a vulnerability).

We will acknowledge receipt within **5 business days** and aim to provide
a remediation timeline within **14 days** of triage. We will keep reporters
informed of progress and credit reporters in the release notes unless
anonymity is requested.

Please do **not** open a public issue for security vulnerabilities.

## Scope note

The kit ships handbooks, samples, templates, Claude assets, and a thin
generator launcher (`specfuse-authoring generate`). The generator binary itself is
distributed separately as a pinned, checksum-verified release asset; the
launcher refuses any jar whose SHA-256 does not match the pin in
`generator.lock`. Report launcher/verification issues here; report generator
binary issues through the channel named in your generator-access agreement.

## Supported Versions

This project is pre-1.0. Only the **`main` branch** (HEAD) and the latest
published `specfuse-authoring` release receive security fixes. Older commits and
non-`main` branches are not supported.
