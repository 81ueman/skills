#!/usr/bin/env python3
"""Focus the Herdr pane named in an agent-status OSC8 link.

Herdr routes a Control+click on a terminal URL matching the plugin's
`[[link_handlers]]` pattern to this action and passes the URL in
`HERDR_PLUGIN_CLICKED_URL` (also inside `HERDR_PLUGIN_CONTEXT_JSON`).

We speak the newline-delimited JSON socket API directly: `pane.focus` is the
only absolute pane-focus request, while the CLI wrapper only exposes directional
focus. The socket path comes from `HERDR_SOCKET_PATH` and is always set for a
plugin action.

Manual test (no click needed):
    HERDR_PLUGIN_CLICKED_URL='https://agent-status.local/pane/w1:p1' python3 focus-pane.py
or:
    python3 focus-pane.py 'w1:p1'
"""
from __future__ import annotations

import json
import os
import socket
import sys

PREFIX = "https://agent-status.local/pane/"


def pane_from_value(value):
    """Accept a full link URL or a bare pane id; return the pane id or None."""
    if not value:
        return None
    value = value.strip()
    if value.startswith(PREFIX):
        value = value[len(PREFIX):]
    return value or None


def clicked_url():
    url = os.environ.get("HERDR_PLUGIN_CLICKED_URL")
    if url:
        return url
    if len(sys.argv) > 1:
        return sys.argv[1]
    try:
        ctx = json.loads(os.environ.get("HERDR_PLUGIN_CONTEXT_JSON") or "{}")
        return ctx.get("clicked_url")
    except Exception:
        return None


def request(method, params, timeout=3.0):
    path = os.environ.get("HERDR_SOCKET_PATH")
    if not path:
        return None
    payload = (json.dumps({"id": "agent-status-focus", "method": method, "params": params}) + "\n").encode()
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(path)
        sock.sendall(payload)
        buf = b""
        while b"\n" not in buf:
            chunk = sock.recv(65536)
            if not chunk:
                break
            buf += chunk
    finally:
        sock.close()
    if not buf:
        return None
    try:
        return json.loads(buf.decode("utf-8", "replace").splitlines()[0])
    except Exception:
        return None


def main():
    pane = pane_from_value(clicked_url())
    if not pane:
        print("agent-status: no pane id in clicked url", file=sys.stderr)
        return 2
    res = request("pane.focus", {"pane_id": pane})
    if res is None:
        print(f"agent-status: focus {pane} failed (no Herdr socket)", file=sys.stderr)
        return 1
    if "error" in res:
        print(f"agent-status: focus {pane} failed: {res['error']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
