#!/usr/bin/env python3
import argparse
import curses
import os

from endcord import config, defaults, tui

CFG_PATH = os.path.expanduser('~/.config/endcord/config.ini')


def build_ui(stdscr, trace_file):
    if trace_file:
        os.environ['ENDCORD_CURSOR_TRACE'] = trace_file
    cfg, _, _ = config.merge_configs(CFG_PATH, None)
    keybindings = config.load_config(CFG_PATH, defaults.keybindings, section='keybindings')
    command_bindings = config.load_config(CFG_PATH, defaults.command_bindings, section='command_bindings', merge=True)
    if cfg['vim_mode']:
        vim_keybindings = config.load_config(CFG_PATH, defaults.vim_mode_bindings, section='vim_mode_bindings', merge=True)
        keybindings = config.merge_keybindings(keybindings, vim_keybindings, command_bindings)
    keybindings = config.normalize_keybindings(keybindings)
    return tui.TUI(stdscr, cfg, keybindings, command_bindings)


def run_probe(stdscr, prompt, trace_file):
    ui = build_ui(stdscr, trace_file)
    insert_key = ui.keybindings['insert_mode'][0]

    ui.insert_mode = True
    input_text, _, _, action = ui.wait_input(prompt, init_text='a', reset=False, keep_cursor=True, press=27)
    ui.update_status_line('left', 'right')
    ui.flush_updates_now()
    ui.wait_input(prompt, init_text=input_text, reset=False, keep_cursor=True, press=ord('x'))
    print('leave-insert', action, repr(input_text), ui.win_prompt.getbegyx(), ui.win_input_line.getbegyx())

    ui.insert_mode = False
    input_text, _, _, action = ui.wait_input(prompt, init_text='abc', reset=False, keep_cursor=True, press=insert_key)
    ui.update_status_line('left', 'right')
    ui.flush_updates_now()
    ui.wait_input(prompt, init_text=input_text, reset=False, keep_cursor=True, press=ord('x'))
    print('enter-insert', action, repr(input_text), ui.win_prompt.getbegyx(), ui.win_input_line.getbegyx())


def main():
    parser = argparse.ArgumentParser(description='Reproduce vim cursor mode-switch handoff.')
    parser.add_argument('--trace-file', help='Write JSONL cursor trace here')
    parser.add_argument('--prompt', default='[Paramount] > ')
    args = parser.parse_args()
    curses.wrapper(run_probe, args.prompt, args.trace_file)


if __name__ == '__main__':
    main()
