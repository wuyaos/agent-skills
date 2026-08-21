# MyPlugin

## Structure

- `__init__.py`: MoviePilot plugin entry, configuration form, and data page.
- `requirements.txt`: Optional plugin dependencies.

## Constraints

- Keep `plugin_version` synchronized with `package.v2.json` version and newest history entry.
- Use flat form model keys and kebab-case Vuetify props.
- Keep real external side effects behind explicit user authorization.
