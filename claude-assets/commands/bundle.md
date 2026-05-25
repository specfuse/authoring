Bundle the API specifications into single files for code generation.

## OpenAPI Bundle

Run:
```bash
./scripts/bundle-spec.sh api/specs/v1/openapi.yaml output/openapi-bundled.yaml
```

## AsyncAPI Bundle (if async specs exist)

If `api/specs/v1/asyncapi.yaml` exists, also run:
```bash
./scripts/bundle-async-spec.sh api/specs/v1/asyncapi.yaml output/asyncapi-bundled.yaml
```

Report whether each bundle was created successfully. If either fails, analyze the error and suggest fixes.
