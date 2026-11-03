"""Minimal web app for the tutor proof of concept (Python standard library only).

Run:   python -m tutor.app                 # http://localhost:8000  (learner)
                                           # http://localhost:8000/teacher  (teacher)
Options: --port 8000 --config tutor/config.json --data-dir runs

Intended for local demos and small supervised pilots on a trusted network. It has no
login system; learners enter a pseudonymous code given by the teacher.
"""
from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .engine import DEFAULT_CONFIG, DEFAULT_DATA, Tutor, TutorError

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
PAGES = {"/": "index.html", "/teacher": "teacher.html"}
MAX_BODY = 16_384
CTYPES = {".js": "text/javascript", ".css": "text/css", ".woff2": "font/woff2", ".html": "text/html"}


def make_handler(tutor: Tutor):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # quiet default access log
            pass

        def _send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype + ("; charset=utf-8" if "text" in ctype or "json" in ctype else ""))
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = self.path.split("?")[0]
            if path in PAGES:
                with open(os.path.join(STATIC, PAGES[path]), "rb") as fh:
                    return self._send(200, fh.read(), "text/html")
            if path == "/api/teacher":
                return self._send(200, tutor.teacher_summary())
            if path.startswith("/static/"):
                full = os.path.realpath(os.path.join(STATIC, path[len("/static/"):]))
                if full.startswith(os.path.realpath(STATIC) + os.sep) and os.path.isfile(full):
                    ctype = CTYPES.get(os.path.splitext(full)[1], "application/octet-stream")
                    with open(full, "rb") as fh:
                        return self._send(200, fh.read(), ctype)
            return self._send(404, {"error": "not found"})

        def do_POST(self):
            path = self.path.split("?")[0]
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                return self._send(413, {"error": "request too large"})
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
                lid = body.get("learner_id")
                if path == "/api/start":
                    out = tutor.start(lid)
                elif path == "/api/next":
                    out = tutor.next_problem(lid, body.get("method"))
                elif path == "/api/choose":
                    out = tutor.choose(lid, body.get("arm"))
                elif path == "/api/answer":
                    out = tutor.answer(lid, str(body.get("answer", "")))
                elif path == "/api/rate":
                    out = tutor.rate(lid, int(body.get("helpful", 0))) if body.get("helpful") else tutor.skip_rating(lid)
                elif path == "/api/config":
                    out = tutor.set_config(body.get("config", {}))
                else:
                    return self._send(404, {"error": "not found"})
                return self._send(200, out)
            except TutorError as e:
                return self._send(400, {"error": str(e)})
            except (ValueError, TypeError, KeyError) as e:
                return self._send(400, {"error": f"bad request: {e}"})

    return Handler


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    ap.add_argument("--data-dir", default=DEFAULT_DATA)
    a = ap.parse_args()
    tutor = Tutor(a.config, data_dir=a.data_dir)
    srv = ThreadingHTTPServer((a.host, a.port), make_handler(tutor))
    print(f"Tutor running: learner page http://{a.host}:{a.port}/  teacher page http://{a.host}:{a.port}/teacher")
    print(f"Logs and state: {tutor.dir}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
