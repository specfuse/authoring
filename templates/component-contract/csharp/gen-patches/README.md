# Temporary patches to generated code

Every file here is a stop-gap for a generator defect that cannot be worked
around from `src/`. Each one is re-applied after every regen by
`scripts/apply-gen-patches.sh` (the spec repo's `scripts/post-generate.sh` calls
it) and checked on every pull request with `--check`. A patch lives until the
generator fix ships **and** the pin reaches it; then it is retired, not kept "just
in case".

The full procedure, with when a patch is the wrong tool, is in the Specfuse
authoring kit's C# component guide, §9.1.

## Active

A patch missing from this table fails `--check`.

| Patch | Generator issue | Since generator | What breaks without it |
|---|---|---|---|

## Retired

| Patch | Generator issue | Fixed in | Retired in |
|---|---|---|---|

## Making a patch

1. Regenerate on a clean branch, so `gen-src/` is exactly what the generator wrote.
2. Edit the generated file(s). Modify only: never create, delete or rename a generated file.
3. Write the patch, header first, then the diff:

   ```bash
   { printf 'Generator-Issue: clabonte/generator#NNNN\nGenerator-Version: 0.19.0\nReason: <one line: what is wrong in the generated code>\n\n'
     git diff -- <the edited gen-src files>; } > gen-patches/NNNN-<short-name>.patch
   ```

4. Add a row to **Active**, and an entry under **Known failure modes** in
   `docs/generated-code-expectations.md` naming the patch.
5. `./scripts/apply-gen-patches.sh --check` is green. Commit the patch, the patched
   files, this table and the expectations entry together.

## Retiring a patch

When `apply-gen-patches.sh` reports **already present** right after a regen, or
the issue is closed and the pin has reached the fix:

1. Confirm the regenerated code is right without the patch.
2. Delete the patch file and move its row to **Retired**.
3. Remove its **Known failure modes** entry, and any workaround that depended on it.
