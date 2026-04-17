## Slash client commands

Endcord local/client commands are now typed directly in the main prompt as `/command`.

How it works:
- type `/` in the prompt to open live slash-command autocomplete
- recognized commands and supported fixed args get a light highlight in the input line
- use `Tab` / `Shift+Tab` to cycle suggestions Exocortex-style without leaving the prompt
- use the command-popup navigation keys (`Alt+Up/Down` by default, reusing the same bindings as extra-window navigation) to browse suggestions manually
- press `Enter` on a selected suggestion to insert it, or just keep typing and press `Enter` to run the command
- press `Esc` while Tab-cycling to restore the text you originally typed
- `/help` opens the full local command list in the extra window
- unknown `/...` input is sent as a normal Discord message instead of being swallowed by the client

Examples:
- `/goto <#channel_id>`
- `/voice_start_call`
- `/redraw`
- `/set theme_path = /path/to/theme.ini`
- `/switch_tab next`

Still deprecated / disabled:
- the old command palette
- legacy `[command_bindings]` macros
- the legacy `@mention` / `@role` helper
- the legacy slash/app-command compose flow

Archived references:
- old command-palette docs: `deprecated/commands.md`
- archived legacy parser / bindings implementation: `endcord/deprecated/command_mode.py`
- archived mention / slash compose implementation: `endcord/deprecated/input_assist.py`
