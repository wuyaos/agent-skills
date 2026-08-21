# Runtime-derived MoviePilot Plugin Contracts

These rules come from repeated V2/V3 runtime validation and should be checked before inventing a workaround.

## Identity and loading

- The Python entry class and `package.v2.json` key use the PascalCase plugin ID, for example `SiteAutoTask`.
- The source directory uses lowercase, for example `plugins.v2/siteautotask/`.
- API paths and runtime plugin IDs use the class/package ID, not the lowercase directory.
- `get_api()` route paths are relative; the framework prepends `/api/v1/plugin/{PluginId}`.
- Custom API routes are generally registered only while the plugin is enabled.
- `get_page()` must contain a nontrivial implementation for host page detection; a pass/docstring/NotImplemented body can be treated as no page.

## Duplicate module identities

MoviePilot can load plugin code from the active source and backup/cache paths. The same plugin-defined class can therefore exist as multiple Python class objects.

Avoid:

```python
isinstance(value, PluginDefinedType)
handler_cls is type(handler)
```

Prefer stable identifiers, class names, protocols, or duck typing when crossing plugin-loader boundaries.

## Configuration lifecycle

- `init_plugin(config=None)` must tolerate missing configuration.
- The host can merge default form models with stored configuration and call `init_plugin` again after saves or reloads.
- Every persisted configuration field that users can retain should have a form control or explicit migration/preservation logic.
- Never submit a partial plugin config during remote debugging. Missing fields can reset to defaults.
- One-shot fields must be consumed and persisted back as false before any reload-sensitive scheduling.
- Dynamic `task_*`, `claim_*`, Cookie, password, retry, and notification fields require full-config preservation.

## Service and execution safety

- Service IDs must be stable and unique.
- Scheduler functions should be public, no-argument entrypoints when possible.
- Reload can interrupt process-local timers and background schedulers. Persist future trigger state only when recovery semantics are explicitly required.
- A GET endpoint name does not guarantee a read-only operation. Reload, reset, scheduler-run, refresh, install, and restart routes mutate state.

## Browser-derived APIs

When adapting a redesigned site:

1. Inspect public frontend assets and request contracts.
2. Use an existing authorized browser session for GET-only response-shape validation.
3. Keep passwords and Cookies out of tool output.
4. Reproduce browser security headers for writes: Origin, Referer, CSRF, and idempotency keys when required.
5. Validate login separately from the business action.
6. Obtain explicit authorization before the first real check-in, purchase, claim, shout, or lottery.
