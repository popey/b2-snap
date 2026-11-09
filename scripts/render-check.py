#!/usr/bin/env python3
"""Reject blank ghvmctl window captures, without judging application semantics."""
import json
from pathlib import Path
import subprocess
from PIL import Image


def nonblank(image):
    width, height = image.size
    if width < 200 or height < 100:
        return False
    # Ignore borders, title bars, shadows and transparent screenshot padding.
    center = image.convert('RGB').crop((width // 5, height // 5, width * 4 // 5, height * 4 // 5))
    extrema = center.getextrema()
    colors = center.getcolors(maxcolors=32)
    return max(high - low for low, high in extrema) > 30 and (colors is None or len(colors) > 8)


def main():
    evidence = json.loads(Path('/home/ubuntu/window.json').read_text())
    window = evidence['window']
    if evidence.get('backend') == 'gnome':
        import importlib.util
        spec = importlib.util.spec_from_file_location('gnome_window', '/home/ubuntu/gnome-window.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.verify_focus(window), 'Screenshot does not belong to the selected GNOME application'
    else:
        active = subprocess.check_output(['xdotool', 'getactivewindow'], text=True, timeout=10)
        assert int(active) == int(window, 16 if window.startswith('0x') else 10), 'Screenshot does not belong to the selected application'
    with Image.open('/home/ubuntu/window.png') as image:
        passed = nonblank(image)
        result = {'nonblank':passed, 'size':image.size, 'window':window,
                  'scope':'nonuniform central content; not semantic or gameplay verification'}
    Path('/home/ubuntu/render.json').write_text(json.dumps(result, indent=2))
    print('Rendered application content detected' if passed else 'Waiting for application content', flush=True)
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
