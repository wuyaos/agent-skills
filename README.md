# agent-skills

Personal collection of [Agent Skills](https://agentskills.io/) — self-contained capability packages for AI coding agents (pi, Claude Code, Codex, Cursor, etc.).

Each skill is a folder under `skills/` containing a `SKILL.md` (metadata + instructions) plus optional scripts, references, and templates.

## Skills

| Skill | Description |
|---|---|
| [`moviepilot-debug`](skills/moviepilot-debug/) | Debug and analyze a running MoviePilot V2 instance with local CLI and API probes — plugin not loaded, scheduler not firing, log 404, recognition/search failures, startup issues. |
| [`moviepilot-v2-plugin-dev`](skills/moviepilot-v2-plugin-dev/) | Build and maintain MoviePilot V2 plugins using the official V2 development contract — `get_form`/`get_page`/`get_api`/`get_service` wiring, `package.v2.json` metadata, version sync, registration/render troubleshooting. |
| [`qnap-qpkg-dev`](skills/qnap-qpkg-dev/) | Build, validate, and troubleshoot QNAP QPKG packages with QDK. |
| [`zotero-word-field-insert`](skills/zotero-word-field-insert/) | Convert `[n]` bracket-style citation markers into Zotero dynamic fields inside `.docx` without breaking Word formatting (Windows + Word + Zotero). |

## Install

Pick whichever matches your agent harness. All three work with this repo's `skills/` directory layout.

### pi

```bash
pi install git:github.com/wuyaos/agent-skills
```

Pi auto-discovers skills under the `skills/` directory. See [pi skills docs](https://github.com/earendil-works/pi-coding-agent/blob/main/docs/skills.md).

### openskills

```bash
# project-level (.agents/skills/)
npx openskills install wuyaos/agent-skills

# or global
npx openskills install -g wuyaos/agent-skills
```

### skills (Vercel)

```bash
npx skills add wuyaos/agent-skills
```

## Layout

```
agent-skills/
├── .gitignore
├── README.md
└── skills/
    ├── moviepilot-debug/SKILL.md
    ├── moviepilot-v2-plugin-dev/
    │   ├── SKILL.md
    │   ├── references/V2_Plugin_Development.md
    │   └── templates/minimal_v2_plugin/
    ├── qnap-qpkg-dev/SKILL.md
    └── zotero-word-field-insert/
        ├── SKILL.md
        └── insert_zotero_fields.py
```

## License

MIT
