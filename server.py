"""Loopback web application for the Gradient Lab practice workspace."""

import argparse
import json
import os
import signal
import socketserver
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from problems import BY_ID, catalog

ROOT = Path(__file__).resolve().parent
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}
SANDBOX = Path("/usr/bin/sandbox-exec")
RUN_TIMEOUT = 15
RUN_SLOTS = threading.BoundedSemaphore(1)


def command(scratch):
    python = [sys.executable, "-IB", str(ROOT / "judge.py")]
    if sys.platform != "darwin":
        return python
    return [str(SANDBOX), "-f", str(ROOT / "judge.sb"),
            "-D", "scratch=" + str(scratch), "-D", "home=" + str(Path.home()),
            "-D", "runtime=" + str(Path(sys.prefix).resolve()),
            "-D", "runner=" + str(ROOT / "judge.py"),
            "-D", "core=" + str(ROOT / "judge_core.py"),
            "-D", "questions=" + str(ROOT / "problems.py"),
            "-D", "sets=" + str(ROOT / "sets"), *python]


def run_submission(payload):
    if not RUN_SLOTS.acquire(blocking=False):
        return {"error": "有一份代码正在运行。等它结束后再试。"}
    try:
        with tempfile.TemporaryDirectory(prefix="gradient-lab-") as directory:
            scratch = Path(directory).resolve()
            env = {"PATH": "/usr/bin:/bin", "HOME": str(scratch), "TMPDIR": str(scratch),
                   "LANG": "en_US.UTF-8", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}
            with tempfile.TemporaryFile(dir=scratch) as result, tempfile.TemporaryFile(dir=scratch) as errors:
                with subprocess.Popen(command(scratch), cwd=scratch, env=env, start_new_session=True,
                                      stdin=subprocess.PIPE, stdout=result, stderr=errors) as process:
                    try:
                        process.communicate(json.dumps(payload).encode("utf-8"), timeout=RUN_TIMEOUT)
                    except subprocess.TimeoutExpired:
                        return {"error": f"超过 {RUN_TIMEOUT} 秒。检查死循环、过大的中间张量或阻塞操作。"}
                    finally:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                result.seek(0)
                try:
                    return json.loads(result.read(2_000_000))
                except (ValueError, UnicodeError):
                    errors.seek(0)
                    diagnostic = errors.read(700).decode("utf-8", errors="replace").strip()
                    return {"error": "判题进程未返回测试结果。" + (f"\n{diagnostic}" if diagnostic else "")}
    except OSError as error:
        return {"error": f"无法启动本地判题进程。{error}"}
    finally:
        RUN_SLOTS.release()


class LocalServer(ThreadingHTTPServer):
    def server_bind(self):
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(20)

    def host_ok(self):
        port = self.server.server_port
        return self.headers.get("Host") in {f"127.0.0.1:{port}", f"localhost:{port}"}

    def send_bytes(self, status, content, media_type):
        self.send_response(status)
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_json(self, status, data):
        self.send_bytes(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        if not self.host_ok():
            self.send_json(403, {"error": "只接受来自本机的访问。"})
        elif self.path == "/api/health":
            self.send_json(200, {"app": "gradient-lab", "judge": "ready"})
        elif self.path == "/api/problems":
            self.send_json(200, catalog())
        elif self.path in STATIC:
            name, kind = STATIC[self.path]
            self.send_bytes(200, (ROOT / "static" / name).read_bytes(), kind)
        else:
            self.send_json(404, {"error": "页面不存在。"})

    def do_POST(self):
        if (not self.host_ok() or self.headers.get("Origin") != "http://" + self.headers.get("Host", "")
                or self.headers.get("X-Gradient-Lab") != "practice"
                or self.headers.get_content_type() != "application/json"):
            self.send_json(403, {"error": "请求来源未得到验证。"})
            return
        if self.path != "/api/run":
            self.send_json(404, {"error": "接口不存在。"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 200_000:
                raise ValueError("Invalid content length")
            data = json.loads(self.rfile.read(length))
            if (not isinstance(data, dict) or not isinstance(data.get("id"), str)
                    or data["id"] not in BY_ID or data.get("mode") not in ("run", "submit")
                    or not isinstance(data.get("code"), str) or len(data["code"]) > 40_000):
                raise ValueError("Invalid payload")
        except (ValueError, UnicodeError):
            self.send_json(400, {"error": "题目或代码格式有误。"})
            return
        self.send_json(200, run_submission(data))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    with LocalServer(("127.0.0.1", args.port), Handler) as server:
        print(f"Gradient Lab · http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
