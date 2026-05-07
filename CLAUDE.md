# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

- Python 3.14 virtual environment at `.venv/`
- Activate with `source .venv/bin/activate`
- Install packages: `pip install <package>`
- Run the project: `python main.py`

## OpenSpec Workflow

This project uses OpenSpec for spec-driven development. The `openspec` CLI (Node.js) is on PATH.

**Slash commands:**
- `/opsx:propose` — Propose a new change: creates `openspec/changes/<name>/` with `proposal.md`, `design.md`, `tasks.md`
- `/opsx:apply` — Implement pending tasks from a change
- `/opsx:explore` — Think through ideas before proposing
- `/opsx:archive` — Archive a completed change

**Directory layout:**
- `openspec/config.yaml` — Project context and per-artifact rules (edit this to add tech stack, conventions, etc.)
- `openspec/changes/<name>/` — Active changes with their artifacts
- `openspec/changes/archive/` — Completed changes
- `openspec/specs/` — Standalone specs

**Key CLI commands:**
```bash
openspec new change "<name>"               # scaffold a new change
openspec status --change "<name>" --json   # check artifact readiness
openspec instructions <artifact> --change "<name>" --json  # get build instructions
openspec list --json                       # list all changes
```

The typical flow is: `/opsx:propose` → `/opsx:apply` → `/opsx:archive`.
