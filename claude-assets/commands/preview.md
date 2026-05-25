Launch the Redocly documentation preview server for live viewing of the API specifications.

*Enforces: (general — no single handbook)*

## Steps

1. **Start the preview server** — Run `./scripts/serve-docs.sh` in the background using `run_in_background: true`. The server starts on port 8081 by default.

2. **Confirm it's running** — After a few seconds, check the output to verify the server started successfully. Look for the "Preview URL" line.

3. **Inform the user** — Tell the user the docs are available at http://localhost:8081 and that changes to spec files will auto-reload.

## Notes

- The server runs in the background so you can continue making changes to the specs.
- Changes to any YAML file under `api/specs/v1/` will trigger a live reload automatically.
- To stop the server, the user can press Ctrl+C in the terminal or kill the background process.
