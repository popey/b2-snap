#!/usr/bin/env python3
"""Check an existing application window; ghvmctl owns the desktop and launch."""
import ast
import json
from pathlib import Path
import re
import subprocess
import time


def run(*args):
    return subprocess.run(args, capture_output=True, text=True, timeout=10)


def matching_windows(package):
    window_class = package.get('desktop_class')
    title = package.get('desktop_title')
    assert window_class or title, 'Window selector must be configured'
    selector = ['--class', '^' + re.escape(window_class) + '$'] if window_class else ['--name', re.escape(title)]
    windows = run('xdotool', 'search', '--onlyvisible', *selector).stdout.split()
    if title and not window_class:
        # SDL can set only _NET_WM_NAME, which xdotool search can miss.
        # GNOME's title-bar helper can also match before the real client, so
        # inspect managed clients even when xdotool returned some windows.
        clients = run('xprop', '-root', '_NET_CLIENT_LIST').stdout
        for wid in re.findall(r'0x[0-9a-fA-F]+', clients):
            prop = run('xprop', '-id', wid, '_NET_WM_NAME').stdout
            try:
                name = ast.literal_eval(prop.partition(' = ')[2].strip())
            except (ValueError, SyntaxError):
                continue
            if isinstance(name, str) and title in name and wid not in windows:
                windows.append(wid)
    return windows


def check_window(package, wid):
    if 'Map State: IsViewable' not in run('xwininfo', '-id', wid).stdout:
        return None
    geometry = run('xdotool', 'getwindowgeometry', '--shell', wid)
    if geometry.returncode:
        return None
    fields = dict(line.split('=', 1) for line in geometry.stdout.splitlines() if '=' in line)
    if int(fields.get('WIDTH', 0)) < 200 or int(fields.get('HEIGHT', 0)) < 100:
        return None
    if package.get('desktop_decorated'):
        frame = run('xprop', '-id', wid, '_NET_FRAME_EXTENTS').stdout
        extents = re.findall(r'\d+', frame.partition('=')[2])
        if len(extents) != 4 or int(extents[2]) < 10:
            return None
    return {'window':wid, 'title':run('xdotool', 'getwindowname', wid).stdout.strip(),
            'window_class':package.get('desktop_class'), 'geometry':fields,
            'decorated_required':package.get('desktop_decorated', False)}


def ensure_active_window(wid):
    target = int(wid, 16 if wid.startswith('0x') else 10)

    def active():
        result = run('xdotool', 'getactivewindow')
        return result.returncode == 0 and result.stdout.strip().isdigit() and int(result.stdout) == target

    if active():
        return
    # --sync can wait forever for a focus event when the window is already
    # active. Ask once, then verify the actual active window explicitly.
    run('xdotool', 'windowactivate', wid)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if active():
            return
        time.sleep(0.25)
    raise RuntimeError('Application window is not active for screenshot')


def main():
    package = json.loads(Path('/home/ubuntu/input.json').read_text())['package']
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        for wid in matching_windows(package):
            result = check_window(package, wid)
            if result is None:
                continue
            time.sleep(10)
            if check_window(package, wid) is None:
                raise RuntimeError('Application window disappeared after startup')
            ensure_active_window(wid)
            result['visible_for_seconds'] = 10
            Path('/home/ubuntu/window.json').write_text(json.dumps(result, indent=2))
            return
        time.sleep(1)
    raise RuntimeError('No visible application window within 180 seconds')


if __name__ == '__main__':
    main()
