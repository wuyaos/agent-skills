# Vuetify JSON and Configuration Contracts

## Form model

Use flat model keys:

```python
{"component": "VSwitch", "props": {"model": "task_7_daily_checkin"}}
```

Do not use dot-path binding:

```python
{"props": {"model": "task_switches.7.daily_checkin"}}
```

MoviePilot's Python-described form controls do not reliably bind nested dot notation. Keep backend normalization/migration separate from frontend field names.

## Prop names

Use kebab-case for Vuetify props serialized from Python:

```python
{"items-per-page": 10, "hide-default-footer": True, "no-data-text": "暂无数据"}
```

Avoid camelCase such as `itemsPerPage`; unsupported props can cause silent rendering failure.

## Proven layout patterns

Prefer repository-proven components:

- `VCard`, `VCardTitle`, `VCardText`
- `VRow`, `VCol`
- `VList`, `VListItem`
- Manual `VTable` with `thead/tbody/tr/td`
- `VAlert`, `VChip`, `VBtn`

Use `VDataTable` or less common timeline/expansion components only after validating them against the active frontend version.

## Form contract

`get_form()` returns:

```python
(conf: list[dict], model: dict)
```

The host merges stored configuration over the default model. A field omitted from both the form controls and explicit migration logic can be reset or become impossible to preserve safely.

For secret fields:

- Use password-style controls.
- Report only configured/not configured.
- Never render the value on a data page or include it in logs.

## Page contract

`get_page()` returns page JSON and should catch rendering errors with a small `VAlert` fallback. Keep page data bounded; do not embed unbounded history, huge logs, or binary content.

When a component silently fails:

1. Fetch `/api/v1/plugin/page/{PluginId}`.
2. Inspect the returned component tree.
3. Compare props with known working plugins on the same frontend version.
4. Inspect the actual browser DOM before assuming the backend page is wrong.
