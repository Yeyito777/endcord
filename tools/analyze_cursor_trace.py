#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load_events(path):
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line:
            yield json.loads(line)


def main():
    if len(sys.argv) != 2:
        print('usage: analyze_cursor_trace.py TRACE.jsonl', file=sys.stderr)
        sys.exit(2)

    anomalies = []
    handoff = False
    for event in load_events(sys.argv[1]):
        kind = event['event']
        if kind == 'return_input_code' and event.get('code') in (26, 28):
            handoff = True
        elif kind == 'wait_input_begin':
            handoff = False

        if kind == 'draw_prompt':
            prompt_beg = event.get('win_prompt_beg')
            input_beg = event.get('win_input_line_beg')
            prompt = event.get('prompt') or ''
            if prompt_beg and input_beg:
                expected_x = prompt_beg[1] + len(prompt)
                if input_beg[0] != prompt_beg[0] or input_beg[1] != expected_x:
                    anomalies.append((kind, 'prompt/input window mismatch', event))

        if kind == 'sync_terminal_cursor_state' and event.get('should_show'):
            input_beg = event.get('win_input_line_beg')
            input_max = event.get('win_input_line_max')
            term_row = event.get('term_row')
            term_col = event.get('term_col')
            if input_beg and input_max and term_row is not None and term_col is not None:
                expected_row = input_beg[0] + 1
                min_col = input_beg[1] + 1
                max_col = input_beg[1] + input_max[1]
                if term_row != expected_row or not (min_col <= term_col <= max_col):
                    anomalies.append((kind, 'terminal cursor outside input window', event))
            if event.get('defer_terminal_cursor'):
                anomalies.append((kind, 'terminal cursor shown during deferred handoff', event))
            if handoff:
                anomalies.append((kind, 'terminal cursor shown during mode-switch handoff', event))

    if not anomalies:
        print('No cursor-trace anomalies detected.')
        return

    print(f'{len(anomalies)} cursor-trace anomalies detected:')
    for kind, message, event in anomalies[:20]:
        print(f'- {kind}: {message}')
        print(json.dumps(event, sort_keys=True))
    if len(anomalies) > 20:
        print(f'... and {len(anomalies) - 20} more')
    sys.exit(1)


if __name__ == '__main__':
    main()
