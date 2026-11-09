#!/usr/bin/env python3
"""Read-only diagnostics; never supplies desktop acceptance evidence."""
import json
import re
import subprocess

def read(*args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=10)
    return {'argv': args, 'returncode': result.returncode,
            'stdout': result.stdout[:32768], 'stderr': result.stderr[:4096]}

clients = read('xprop', '-root', '_NET_CLIENT_LIST')
print(json.dumps(clients))
print(json.dumps(read('xdotool', 'search', '--onlyvisible', '--name', 'b2')))
for wid in re.findall(r'0x[0-9a-fA-F]+', clients['stdout']):
    for args in (
        ('xprop', '-id', wid, '_NET_WM_NAME', 'WM_NAME', 'WM_CLASS',
         '_NET_FRAME_EXTENTS', '_GTK_FRAME_EXTENTS', 'WM_STATE', '_NET_WM_STATE', '_MOTIF_WM_HINTS'),
        ('xwininfo', '-id', wid),
        ('xdotool', 'getwindowgeometry', '--shell', wid),
    ):
        print(json.dumps(read(*args)))
