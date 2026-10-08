"""Bounded yt-dlp progress monitoring and cleanup of its owned process tree."""
from collections import deque
from pathlib import Path
import subprocess
import threading
import time


class DownloadStalled(RuntimeError):
    pass


def stop_tree(process):
    if process.poll() is not None:
        return
    if __import__("os").name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       capture_output=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        process.kill()
    process.wait(timeout=15)


def run_download(command, output, progress=None, *, idle_timeout=180, maximum=7200):
    output = Path(output)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", errors="replace", bufsize=1,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    lines = deque(maxlen=80)
    state = {"bytes": None, "changed": time.monotonic(), "line": ""}

    def read_lines():
        for line in process.stdout:
            lines.append(line.rstrip())
            if "__HVS_PROGRESS__" in line:
                value = line.split("__HVS_PROGRESS__", 1)[1].strip()
                if value.split(" ")[0] != state["bytes"]:
                    state.update(bytes=value.split(" ")[0], changed=time.monotonic(), line=value)

    reader = threading.Thread(target=read_lines, daemon=True, name="download-progress")
    reader.start()
    started = time.monotonic()
    last_report = 0
    previous_size = -1
    try:
        while process.poll() is None:
            now = time.monotonic()
            try:
                size = sum(path.stat().st_size for path in output.parent.glob(output.stem + "*") if path.is_file())
                if size != previous_size:
                    previous_size = size
                    state["changed"] = now
            except OSError:
                pass
            if now - state["changed"] > idle_timeout or now - started > maximum:
                stop_tree(process)
                raise DownloadStalled("Tải YouTube không tiến triển; đã giữ phần tải để tiếp tục khi thử lại.")
            if progress and now - last_report >= 3:
                progress(f"Đang tải YouTube: {max(previous_size, 0) / 1048576:.1f} MB; đang theo dõi kết nối.")
                last_report = now
            time.sleep(0.25)
        reader.join(timeout=5)
        return subprocess.CompletedProcess(command, process.returncode, "", "\n".join(lines))
    except BaseException:
        stop_tree(process)
        raise
    finally:
        reader.join(timeout=5)
        process.stdout.close()
