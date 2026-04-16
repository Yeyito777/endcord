## Deprecated command system

The legacy client-command system has been deprecated and is intentionally disabled.

What is disabled:
- the old command palette
- legacy `command_bindings` macros
- the legacy `@mention` / `@role` helper
- the legacy slash/app-command compose flow
- client commands such as `voice_start_call`, `goto`, `redraw`, `set`, etc.

Archived references:
- old user-facing command list: `deprecated/commands.md`
- archived client-command implementation: `endcord/deprecated/command_mode.py`
- archived mention/slash compose implementation: `endcord/deprecated/input_assist.py`
