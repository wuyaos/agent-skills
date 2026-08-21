# MoviePilot Plugin Release and Deployment

## Version release gate

Synchronize three locations:

1. `plugins.v2/<id>/__init__.py` → `plugin_version`
2. `package.v2.json` → plugin `version`
3. `package.v2.json` → newest `history.vX.Y.Z`

Use `scripts/update_metadata.py`; it is dry-run by default, rejects history overwrite, rewrites valid JSON, and rolls back both files if validation fails.

Run `scripts/validate_plugin.py` after metadata updates. A release is not ready while its report contains a failed check.

## Frontend assets

Vue render-mode plugins require their built `dist` assets in the distributed package. Build in a temporary directory when repository rules prohibit `node_modules` or lockfile changes.

For large/binary frontend assets, use MoviePilot's Release-based package mode when supported:

- Set `release=true` in plugin metadata.
- Create tag `<PluginId>_v<version>`.
- Upload `<plugin-id-lower>_v<version>.zip`.
- Confirm the archive includes `dist/index.html` and all referenced assets.

A successful GitHub push alone does not prove the running MoviePilot instance received the new files.

## Deployment gate

Use `moviepilot-debug/scripts/deploy_plugin.py` for a manifest dry-run. It excludes tests, bytecode, `.omc`, `.ralph`, `.pi`, editor state, and temporary diagnostics.

Before apply:

- Review add/overwrite/delete lists.
- Resolve unexpected hidden files.
- Confirm remote `onlyonce=false` before reload.
- Preserve full plugin configuration.
- Obtain authorization for upload, stale-file deletion, and reload.

After apply:

- Verify remote source version and manifest.
- Fetch form/page endpoints.
- Verify scheduler state without triggering it.
- Read plugin-specific logs.
- Perform a real business action only under separate explicit authorization.

## Git and repository checks

- Keep unrelated working-tree changes out of the commit.
- `package.v2.json` must parse immediately after every edit.
- History is newest first.
- Each plugin directory includes `AGENTS.md`.
- Plugin icons and Release assets follow repository-specific rules.
- Push evidence is `HEAD == origin/main`, not only a successful local commit.
