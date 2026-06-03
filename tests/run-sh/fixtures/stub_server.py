"""Tiny stub of the gwas-ce endpoints run.sh needs.

State is read from `${state_dir}/stub_config.json` per test:
{
  "dataset": { ... },
  "upload_url_status": 200,
  "finalize_status": 200,
  "token_valid": true
}
"""
import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


CONFIG_PATH: "Path | None" = None  # set in main


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _config(self) -> dict:
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text())
        return {}

    def _send_json(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def _consume_fail_count(self) -> bool:
        cfg = self._config()
        n = int(cfg.get("fail_count", 0))
        if n > 0:
            cfg["fail_count"] = n - 1
            CONFIG_PATH.write_text(json.dumps(cfg))
            return True  # fail this one
        return False

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200); self.end_headers(); return
        if self.path == "/api/falcon/dataset":
            if self._consume_fail_count():
                self._send_json(503, {"detail": "transient"}); return
            cfg = self._config()
            if not cfg.get("token_valid", True):
                self._send_json(401, {"detail": "expired"}); return
            self._send_json(200, cfg["dataset"]); return
        self.send_response(404); self.end_headers()

    def do_POST(self):
        if self.path.endswith("/upload-urls"):
            if self._consume_fail_count():
                self._send_json(503, {"detail": "transient"}); return
            cfg = self._config()
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length))
            files = body.get("files", [])
            uploads = [{"name": f["name"],
                        "url": f"http://127.0.0.1:{PUT_PORT}/put/{f['name']}"}
                       for f in files]
            self._send_json(cfg.get("upload_url_status", 200),
                            {"uploads": uploads}); return
        if self.path.endswith("/finalize"):
            if self._consume_fail_count():
                self._send_json(503, {"detail": "transient"}); return
            cfg = self._config()
            self._send_json(cfg.get("finalize_status", 200),
                            {"status": "ok"}); return
        self.send_response(404); self.end_headers()

    def do_PUT(self):
        # accept-any PUT for files
        length = int(self.headers.get("Content-Length", "0"))
        _ = self.rfile.read(length)
        cfg = self._config()
        if cfg.get("put_fail"):
            self.send_response(500); self.end_headers(); return
        self.send_response(200); self.end_headers()


PUT_PORT = 0  # set in main


def main():
    global CONFIG_PATH, PUT_PORT
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--state-dir", type=Path, required=True)
    args = p.parse_args()
    CONFIG_PATH = args.state_dir / "stub_config.json"
    PUT_PORT = args.port  # same server handles PUT
    HTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
