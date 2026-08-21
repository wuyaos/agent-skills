---
name: moviepilot-debug
description: "Use when diagnosing a running MoviePilot V2/V3 instance: plugin loading/UI/API, schedulers, logs, config, Docker/qnap deployment, or version mismatches. Default to read-only; load moviepilot-v2-plugin-dev for source changes."
---

# MoviePilot Runtime Debug

## Overview

Collect reproducible runtime evidence with deterministic scripts. Diagnose first; do not mutate configuration, reload plugins, trigger schedulers, or deploy code unless the user explicitly authorizes that operation.

## Rules

- Default to read-only probes. HTTP `GET` is not automatically safe: reload, install, reset, restart, refresh, and scheduler-run endpoints have side effects.
- Never print API keys, passwords, Cookies, Tokens, or raw sensitive configuration. Read API keys from `MP_API_KEY` or `--api-key-file`; read plugin secrets from files.
- Never update a plugin with a partial config body. Fetch the complete form model, merge named fields, and verify the complete result.
- Do not operate directly on the MoviePilot database. Prefer CLI, API, plugin logs, and page/status data.
- Real check-in, shout, claim, purchase, lottery, download, or scheduler execution needs separate authorization.
- Use scripts before handcrafted curl/SSH commands. If a script reports an unsupported case, explain the gap before using a manual fallback.

## Workflow

1. Classify the symptom as runtime, config, source, or deployment.
2. Run the read-only probe:

```bash
MP_BASE_URL=http://127.0.0.1:3000 \
python3 scripts/probe_plugin.py --plugin <PluginClassName> \
  --api-key-file /secure/mp-api-key --pretty
```

For qnap/Docker evidence, add `--ssh-host`, `--container`, and `--docker-bin`. When Pi provides native OctSSH tools, preserve their confirmation boundary; use this script for the deterministic probe/plan where appropriate.

3. If evidence points to source or contract code, load `moviepilot-v2-plugin-dev` and return here after the change.
4. For config changes, dry-run a complete merge, then apply only after authorization:

```bash
python3 scripts/merge_plugin_config.py ... --set enabled=false --pretty
python3 scripts/merge_plugin_config.py ... --set enabled=false --apply --pretty
```

Secret fields require `--set-secret KEY=FILE`. Effective `onlyonce=true` is blocked unless `--allow-business-action` is present.

5. For deployment, inspect the manifest plan first:

```bash
python3 scripts/deploy_plugin.py ... --pretty
```

`--apply` writes files; stale-file deletion additionally requires `--allow-delete-stale`; reload additionally requires `--reload` and a verified `onlyonce=false` configuration.
6. Run `probe_plugin.py` again and compare pre/post evidence.

## References

- [Safety and qnap/Docker](references/safety-and-qnap.md)
- [Runtime runbooks](references/runtime-runbooks.md)
- [API reference](references/api-runtime.md)
- [CLI reference](references/cli-runtime.md)
