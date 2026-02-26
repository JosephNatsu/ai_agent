#!/usr/bin/env python3
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import shlex

from war_council_core import WarCouncil

ROOT = Path.cwd()
WEB_DIR = ROOT / "web"
HOST = "127.0.0.1"
PORT = 8765

council = WarCouncil(models_file=ROOT / "models.json")


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, file_path: Path):
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, "Not Found")
            return

        suffix = file_path.suffix.lower()
        content_type = "text/plain; charset=utf-8"
        if suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        elif suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif suffix == ".json":
            content_type = "application/json; charset=utf-8"

        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/models":
            self._send_json({"models": council.get_models()})
            return

        if path == "/api/history":
            self._send_json({"history": council.get_history()})
            return

        if path == "/api/memory/dates":
            query = parse_qs(parsed.query).get("q", [""])[0]
            if query:
                self._send_json({"dates": council.search_memory_dates(query)})
            else:
                self._send_json({"dates": council.list_memory_dates()})
            return

        if path == "/api/memory/date":
            date_value = parse_qs(parsed.query).get("date", [""])[0]
            if not date_value:
                self._send_json({"error": "缺少 date 参数"}, status=400)
                return
            self._send_json({"date": date_value, "history": council.get_date_history(date_value)})
            return

        if path == "/":
            self._send_file(WEB_DIR / "index.html")
            return

        safe = path.lstrip("/")
        target = (WEB_DIR / safe).resolve()
        if not str(target).startswith(str(WEB_DIR.resolve())):
            self.send_error(403, "Forbidden")
            return
        self._send_file(target)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            payload = self._read_json()
        except json.JSONDecodeError:
            self._send_json({"error": "JSON 格式错误"}, status=400)
            return

        if path == "/api/models":
            try:
                alias = str(payload.get("alias", "")).strip()
                transport = str(payload.get("transport", "")).strip()
                command = str(payload.get("command", "")).strip()
                tokens = shlex.split(command) if command else []
                model = council.add_model(alias, transport, tokens)
                self._send_json({"model": model, "models": council.get_models()})
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
            return

        if path == "/api/chat":
            text = str(payload.get("text", ""))
            collaborate = bool(payload.get("collaborate", False))
            try:
                result = council.chat(text, collaborate=collaborate)
                self._send_json(result)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
            return

        if path == "/api/reset":
            council.reset_history()
            self._send_json({"ok": True, "history": []})
            return

        self.send_error(404, "Not Found")

    def log_message(self, fmt, *args):
        return


def main():
    WEB_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"War Council Web 已启动: http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("War Council Web 已停止")


if __name__ == "__main__":
    main()
