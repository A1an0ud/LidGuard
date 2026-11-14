"""Local-only HTTP service for the LidGuard engineering demonstration."""

from __future__ import annotations

import argparse
import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote

from .inference import EyeBaseline, decode_image
from .monitor import Monitor
from .pi_camera import PiCameraService


ROOT = Path(__file__).resolve().parent.parent
MAX_BODY = 6 * 1024 * 1024


def make_handler(model, monitor, web_root):
    web_root = Path(web_root).resolve()
    pi_camera = PiCameraService()

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, body, content_type="application/json; charset=utf-8", attachment=None):
            if isinstance(body, dict):
                body = json.dumps(body, allow_nan=False).encode("utf-8")
            elif isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if attachment:
                self.send_header("Content-Disposition", f'attachment; filename="{attachment}"')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/api/status":
                return self._send(200, monitor.status())
            if path == "/api/model-info":
                return self._send(200, model.info())
            if path == "/api/health":
                return self._send(200, {"ok": True, "application": "LidGuard", "version": "0.1.0"})
            if path == "/api/events.csv":
                return self._send(200, monitor.csv(), "text/csv; charset=utf-8", "lidguard_events.csv")
            if path == "/api/pi-frame.jpg":
                try:
                    return self._send(200, pi_camera.frame(), "image/jpeg")
                except RuntimeError as exc:
                    return self._send(503, {"error": str(exc)})
            if path.startswith("/api/"):
                return self._send(404, {"error": "Unknown API route"})
            relative = "index.html" if path == "/" else unquote(path).lstrip("/")
            file = (web_root / relative).resolve()
            if not file.is_relative_to(web_root) or not file.is_file():
                return self._send(404, {"error": "File not found"})
            return self._send(200, file.read_bytes(), mimetypes.guess_type(file.name)[0] or "application/octet-stream")

        def do_POST(self):
            origin = self.headers.get("Origin")
            host = self.headers.get("Host", "")
            if origin and origin != f"http://{host}":
                return self._send(403, {"error": "Cross-origin requests are not permitted"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 <= length <= MAX_BODY:
                    return self._send(413, {"error": "Request too large"})
                if self.headers.get("Content-Type", "").split(";", 1)[0] != "application/json":
                    return self._send(415, {"error": "Use application/json"})
                raw = self.rfile.read(length)
                data = json.loads(raw or b"{}")
                if not isinstance(data, dict):
                    raise ValueError("JSON body must be an object")
                path = urlsplit(self.path).path
                if path == "/api/source":
                    result = monitor.set_source(data.get("source"))
                elif path == "/api/predict":
                    source = data.get("source")
                    epoch = data.get("source_epoch")
                    with monitor.lock:
                        monitor._check_epoch(source, epoch)
                    image = decode_image(data.get("image"))
                    prediction = model.predict(image, data.get("roi_confirmed") is True)
                    result = monitor.observe(source, epoch, prediction)
                    result["prediction"] = prediction
                elif path == "/api/simulation":
                    result = monitor.simulate(data.get("state"), data.get("source_epoch"))
                elif path == "/api/reset":
                    result = monitor.reset()
                elif path == "/api/config":
                    result = monitor.configure(data.get("threshold_seconds"))
                elif path == "/api/ack":
                    result = monitor.acknowledge()
                elif path == "/api/pi-camera":
                    action = data.get("action")
                    if action == "start":
                        result = pi_camera.start()
                    elif action == "stop":
                        result = pi_camera.stop()
                    else:
                        raise ValueError("action must be start or stop")
                else:
                    return self._send(404, {"error": "Unknown API route"})
                return self._send(200, result)
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                return self._send(400, {"error": str(exc)})
            except RuntimeError as exc:
                return self._send(503, {"error": str(exc)})

        def log_message(self, format, *args):
            if args and str(args[1]) not in {"200", "304"}:
                super().log_message(format, *args)

    return Handler


def main():
    parser = argparse.ArgumentParser(description="LidGuard local engineering prototype")
    parser.add_argument("--host", default="127.0.0.1", choices=["127.0.0.1", "localhost"])
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--model", type=Path, default=ROOT / "models" / "rgb_lr.json")
    parser.add_argument("--open-browser", action="store_true", help="Open the local dashboard after the server starts")
    args = parser.parse_args()
    model = EyeBaseline(args.model)
    monitor = Monitor()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(model, monitor, ROOT / "web"))
    print(f"LidGuard prototype: http://{args.host}:{server.server_port}", flush=True)
    print("Research demonstration only. Press Ctrl+C to stop. Images are processed in memory and are not saved.", flush=True)
    if args.open_browser:
        import webbrowser
        opener = threading.Timer(0.5, lambda: webbrowser.open(f"http://{args.host}:{server.server_port}"))
        opener.daemon = True
        opener.start()
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
