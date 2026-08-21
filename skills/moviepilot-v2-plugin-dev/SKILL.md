---
name: moviepilot-v2-plugin-dev
description: "Use when creating, migrating, or changing MoviePilot V2-format plugin source, Vuetify/Vue UI, APIs, schedulers, package.v2.json metadata, versions, or releases. For live runtime evidence use moviepilot-debug first; diagnose-fix-deploy tasks use both."
---

# MoviePilot Plugin Development

## Overview

Develop MoviePilot V2-format plugins with deterministic contract checks. Use the model for business design and implementation; use bundled scripts for metadata edits, validation, and release gates.

## Rules

- Read repository and plugin `AGENTS.md` before editing. Keep changes minimal and preserve existing configuration/data contracts unless migration is explicitly required.
- Never place credentials, Cookies, Tokens, or API keys in source, tests, fixtures, commands, or reports.
- Do not trigger real check-in, shout, claim, purchase, lottery, download, deletion, or scheduler execution without separate authorization.
- Use flat form model keys and kebab-case Vuetify props. `get_api()` paths are relative and must not repeat the plugin class ID.
- Plugin class/package key uses PascalCase; `plugins.v2/<directory>` uses lowercase.
- Do not manually patch adjacent `package.v2.json` history lines. Use `update_metadata.py`.

## Workflow

1. Identify the lowercase plugin directory and PascalCase class/package key.
2. Run the deterministic baseline:

```bash
python3 scripts/validate_plugin.py \
  --repo /path/to/MoviePilot-Plugins \
  --plugin <lowercase-id> \
  --class-name <PluginClassName> --pretty
```

3. Inspect only the checks and references relevant to the requested surface. Implement code and focused offline tests.
4. When changing the version, dry-run metadata synchronization first:

```bash
python3 scripts/update_metadata.py --repo ... --plugin ... \
  --class-name ... --version X.Y.Z --history "变更说明" --pretty
```

Apply only after reviewing the plan:

```bash
... --apply --pretty
```

5. Run focused tests, then `validate_plugin.py` again. Add `--pyflakes` when the plugin baseline is expected to be clean.
6. For runtime installation, scheduler, logs, configuration, or deployment evidence, switch to `moviepilot-debug`. After a source fix, return there for deployment and post-change probing.

## References

- [Runtime-derived contracts](references/runtime-contracts.md)
- [Vuetify and configuration](references/vuetify-and-config.md)
- [Release and deployment](references/release-and-deploy.md)
- [Full V2 development reference](references/V2_Plugin_Development.md)
- Minimal scaffold: `templates/minimal_v2_plugin/`
