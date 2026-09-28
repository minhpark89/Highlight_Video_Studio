"""Final launch verification against the shipped installer payload."""
import os
import subprocess
import sys
import time
import urllib.request

INSTALL = os.path.join(os.environ["LOCALAPPDATA"], "Highlight Desktop Test Final")
PROD_URL = "http://127.0.0.1:5080"


def prod():
    try:
        with urllib.request.urlopen(PROD_URL, timeout=5) as r:
            return r.status
    except Exception as exc:  # noqa: BLE001
        return f"ERROR:{exc}"


def main():
    sys.path.insert(0, INSTALL)
    from multi_pc import local_launcher as L

    print("production before :", prod())
    port = L.pick_free_port("127.0.0.1")
    print("ephemeral port    :", port)
    assert port != 5080

    os.environ["HIGHLIGHT_BUILD_CHANNEL"] = "desktop-test"
    env = dict(os.environ)
    env["HIGHLIGHT_PORT"] = str(port)
    env["HIGHLIGHT_BIND_HOST"] = "0.0.0.0"  # must be ignored

    proc = subprocess.Popen(
        [os.path.join(INSTALL, "runtime", "python.exe"), "run_server.py"],
        cwd=INSTALL, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    url = f"http://127.0.0.1:{port}/"
    for _ in range(90):
        time.sleep(1)
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                print("preview status    :", r.status, "at", url)
                break
        except Exception:  # noqa: BLE001
            if proc.poll() is not None:
                print(proc.stdout.read() if proc.stdout else "")
                raise SystemExit("preview exited early")
    else:
        proc.kill()
        print(proc.stdout.read() if proc.stdout else "")
        raise SystemExit("preview never ready")

    print("production during :", prod())
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("production after  :", prod())
    print("FINAL LAUNCH: PASS")


if __name__ == "__main__":
    main()
