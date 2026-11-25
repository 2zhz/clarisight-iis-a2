"""
ClariSight Local Prototype Server
---------------------------------
Zero-dependency Python 3 server (uses only standard library).
Run with: python3 server.py
Then open: http://127.0.0.1:8000
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
from urllib.parse import urlparse
from engine import ClariSightEngine

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
ENGINE = ClariSightEngine()
# Initialise with Scenario 1 so the UI has an immediate inspectable state
ENGINE.load_scenario("hallway_nav")


class ClariSightHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            return self._send_json(ENGINE.get_state())
        if parsed.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            data = json.loads(raw_body) if raw_body.strip() else {}
        except json.JSONDecodeError:
            return self._send_json({"error": "Invalid JSON body"}, status=400)

        try:
            if parsed.path == "/api/scenario":
                scenario_id = data.get("scenario_id", "hallway_nav")
                if data.get("sync_mode", True):
                    # Optional sync to scenario's default mode
                    from engine import SCENARIOS
                    if scenario_id in SCENARIOS:
                        ENGINE.set_mode(SCENARIOS[scenario_id]["mode_default"], SCENARIOS[scenario_id].get("target_query"))
                ENGINE.load_scenario(
                    scenario_id,
                    live_brightness=data.get("live_brightness"),
                    live_sharpness=data.get("live_sharpness")
                )
                return self._send_json(ENGINE.get_state())

            if parsed.path == "/api/mode":
                ENGINE.set_mode(data.get("mode", "navigation"), data.get("target_query"))
                if ENGINE.last_frame:
                    ENGINE.load_scenario(ENGINE.last_frame.scenario_id)
                return self._send_json(ENGINE.get_state())

            if parsed.path == "/api/verbosity":
                ENGINE.set_verbosity(data.get("level", "adaptive"))
                if ENGINE.last_frame:
                    ENGINE.process_frame(ENGINE.last_frame, requested_detail=(data.get("level") == "detailed"))
                return self._send_json(ENGINE.get_state())

            if parsed.path == "/api/detail":
                ENGINE.request_detail()
                return self._send_json(ENGINE.get_state())

            if parsed.path == "/api/barge_in":
                ENGINE.barge_in_interrupt()
                return self._send_json(ENGINE.get_state())

            if parsed.path == "/api/correct":
                ENGINE.report_correction(data.get("note", "Incorrect object or alert"))
                return self._send_json(ENGINE.get_state())

            return self._send_json({"error": "Unknown endpoint"}, status=404)
        except ValueError as exc:
            return self._send_json({"error": str(exc)}, status=400)

    def log_message(self, format, *args):
        # Cleaner console output
        print(f"[ClariSight] {self.address_string()} - {format % args}")


def run(host="127.0.0.1", port=8000):
    server = HTTPServer((host, port), ClariSightHandler)
    print(f"ClariSight Prototype running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == "__main__":
    run()
