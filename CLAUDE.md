# bigBangEnv — notes for Claude Code

The shared agent guide is AGENTS.md, imported here so Claude Code loads it:

@AGENTS.md

Handoff format: see AGENTS-HANDOFF.md.

Claude-specific reminders:
- Run `python3 -m pytest -q` before committing.
- Bundle shell steps into as few commands as you can; each unapproved command costs the owner a tap.
- Don't edit `.claude/settings.json` permissions in the same PR as other work. Permission changes go in their own PR for the owner to merge.
