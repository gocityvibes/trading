import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, time

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path.startswith('/health'):
            body = {"status": "ok", "time": int(time.time())}
            data = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        return

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    print(f"Listening on 0.0.0.0:{port}", flush=True)
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
