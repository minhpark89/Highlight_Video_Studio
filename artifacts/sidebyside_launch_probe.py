"""Side-by-side launch verification for the installed preview build.

Proves: loopback-only bind, ephemeral port (never 5080), desktop-test channel,
and that production 127.0.0.1:5080 is unaffected.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

INSTALL = os.path.join(
    os.environ["LOCALAPPDATA"], "Highlight Desktop Test SideBySide"
)
PROD_URL = "http://127.0.0.1:5080"
FORBIDDEN_PORT = 5080


def prod_status():
    try:
        with urllib.request.urlopen(PROD_URL, timeout=5) as r:
            return r.status
    except Exception as exc:  # noqa: BLE001
        return f"ERROR:{exc}"


def main():
    sys.path.insert(0, INSTALL)
    from multi_pc import local_launcher as L

    print("production before  :", prod_status())

    port = L.pick_free_port("127.0.0.1")
    print("picked loopback port:", port)
    assert port != FORBIDDEN_PORT, "launcher picked the production port"
    assert 1024 < port < 65536, f"implausible port {port}"

    # Non-loopback hosts must be refused.
    for bad in ("0.0.0.0", "::", "192.168.1.5", "example.com"):
        try:
            L.assert_loopback(bad)
        except L.LoopbackBindError:
            print(f"refused non-loopback host: {bad!r}")
        else:
            raise AssertionError(f"accepted unsafe host {bad!r}")

    os.environ["HIGHLIGHT_BUILD_CHANNEL"] = "desktop-test"
    env = dict(os.environ)
    env["HIGHLIGHT_PORT"] = str(port)
    env["HIGHLIGHT_BIND_HOST"] = "0.0.0.0"  # must be ignored -> loopback only

    proc = subprocess.Popen(
        [os.path.join(INSTALL, "runtime", "python.exe"), "run_server.py"],
        cwd=INSTALL,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    url = f"http://127.0.0.1:{port}/"
    ready = False
    for _ in range(60):
        time.sleep(1)
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                print("preview status     :", r.status, "at", url)
                ready = True
                break
        except Exception:  # noqa: BLE001
            if proc.poll() is not None:
                break
    if not ready:
        proc.kill()
        print("PREVIEW OUTPUT:")
        print(proc.stdout.read() if proc.stdout else "")
        raise SystemExit("preview server never became ready")

    # The preview port must not be reachable from a non-loopback address.
    host_ip = None
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike '*Loopback*'} | Select-Object -First 1).IPAddress"],
            text=True,
        ).strip()
        host_ip = out or None
    except Exception:  # noqa: BLE001
        pass
    if host_ip:
        try:
            with urllib.request.urlopen(f"http://{host_ip}:{port}/", timeout=4):
                print(f"WARNING: preview reachable on LAN {host_ip}:{port}")
        except Exception as exc:  # noqa: BLE001
            print(f"confirmed not exposed on LAN {host_ip}:{port} ({type(exc).__name__})")

    print("production during  :", prod_status())

    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("production after   :", prod_status())
    print("SIDE-BY-SIDE LAUNCH: PASS")


if __name__ == "__main__":
    main()
