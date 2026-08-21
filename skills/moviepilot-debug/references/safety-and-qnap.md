# MoviePilot Safety and qnap/Docker

## Operation classes

### Read-only

- `GET /api/v1/plugin/?state=all`
- Plugin form/page/status reads
- Scheduler list and next-run inspection
- `moviepilot status`, `doctor`, and bounded log reads
- Container file/version inspection

### State-changing despite GET or friendly naming

- Plugin reload/install/reset/uninstall
- Scheduler run
- Subscribe refresh/search triggers
- System restart/update
- Site connection tests when the remote service records activity

Treat these as writes and obtain explicit authorization.

### Business side effects

Check-in, shout, task claim, medal purchase, exchange, lottery, download, deletion, and notification tests need a separate explicit authorization. A deployment or login authorization does not automatically authorize them.

## Secret handling

- Use `MP_API_KEY` or a mode-0600 API-key file; never place an API key in a cron prompt or committed command example.
- Use `--set-secret KEY=FILE` for passwords, Cookies, Tokens, or credentials.
- Reports show only `configured=true/false` for secret fields.
- Delete temporary secret files after use; never store them in plugin source, tests, fixtures, logs, or Git.

## Complete plugin config updates

MoviePilot merges form defaults during plugin initialization. A partial `PUT /api/v1/plugin/{id}` can reset omitted fields, including dynamic `task_*`, `claim_*`, Cookie, password, retry, and notification settings.

Required procedure:

1. Fetch `/api/v1/plugin/form/{id}`.
2. Take the complete returned `model`.
3. Overlay only approved keys.
4. Block effective `onlyonce=true` unless a business action is authorized.
5. PUT the complete merged object.
6. Fetch the form again and compare changed keys.

Use `scripts/merge_plugin_config.py`; do not handcraft this flow.

## qnap profile

The current personal qnap deployment commonly uses:

```text
SSH host: qnap
Container: MP
Docker binary: /share/CACHEDEV9_DATA/.qpkg/container-station/bin/docker
Plugin source: /app/app/plugins/<plugin-id-lower>/
Config volume inside container: /config
Plugin logs: /config/logs/plugins/<plugin-id-lower>.log
```

Discover and verify these values rather than assuming they apply to another host.

Plugin directories under `/app/app/plugins` are Docker overlay data. A GitHub push does not update a running plugin, and container recreation may discard manual copies. Check plugin `repo_url`, installation state, and packaging mode before choosing an update path.

## Evidence order

For scheduled execution, prefer:

1. Scheduler registration, status, and `next_run`.
2. Plugin-specific log under `/config/logs/plugins/`.
3. Plugin status/page or persisted history.
4. General `moviepilot.log` only as supplementary evidence.

Do not conclude that a task did not run solely because the general log has no matching line.

## Deployment safeguards

- Exclude tests, `__pycache__`, `.pyc`, `.omc`, `.ralph`, `.pi`, editor state, and temporary diagnostics.
- Compare source and remote manifests.
- List stale files explicitly; delete them only with approval.
- Check remote `onlyonce=false` before reload.
- Verify remote version, form/page structure, config-presence booleans, scheduler registration, and logs after deployment.
- Do not use direct database writes for install/config/state repair.
