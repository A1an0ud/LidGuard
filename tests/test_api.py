import base64
import io
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import numpy as np
from PIL import Image

from lidguard.inference import EyeBaseline
from lidguard.monitor import Monitor
from lidguard.server import make_handler


ROOT = Path(__file__).resolve().parent.parent


def data_url(image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = EyeBaseline(ROOT / "models" / "rgb_lr.json")
        cls.monitor = Monitor()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.model, cls.monitor, ROOT / "web"))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, path, body=None):
        request = urllib.request.Request(self.base + path, data=None if body is None else json.dumps(body).encode(), headers={} if body is None else {"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.load(response)

    def test_no_eye_presence_confirmation_or_blank_image_is_unknown(self):
        state = self.request("/api/source", {"source": "upload"})
        common = {"source": "upload", "source_epoch": state["source_epoch"], "image": data_url(Image.new("RGB", (60, 36), "black"))}
        result = self.request("/api/predict", common)
        self.assertEqual(result["state"], "UNKNOWN")
        common["roi_confirmed"] = True
        result = self.request("/api/predict", common)
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertFalse(result["quality"]["eye_presence_verified"])
        self.assertEqual(result["open_seconds"], 0)

    def test_deterministic_image_inference_and_snapshot_only(self):
        state = self.request("/api/source", {"source": "upload"})
        array = np.tile(np.linspace(20, 230, 60, dtype=np.uint8), (36, 1))
        image = Image.fromarray(array).convert("RGB")
        body = {"source": "upload", "source_epoch": state["source_epoch"], "roi_confirmed": True, "image": data_url(image)}
        first = self.request("/api/predict", body)
        second = self.request("/api/predict", body)
        self.assertEqual(first["prediction"], second["prediction"])
        self.assertEqual(first["open_seconds"], 0)
        self.assertFalse(first["alarm"])
        self.assertTrue(first["snapshot_only"])

    def test_model_info_exposes_limits(self):
        info = self.request("/api/model-info")
        self.assertFalse(info["clinical_validation"])
        self.assertFalse(info["eye_presence_detection"])
        self.assertFalse(info["nir_validation"])
        self.assertEqual(info["evaluation"]["split"]["subject_overlap"], 0)

    def test_stale_epoch_is_rejected(self):
        state = self.request("/api/source", {"source": "camera"})
        self.request("/api/reset", {})
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request("/api/predict", {"source": "camera", "source_epoch": state["source_epoch"], "image": "invalid"})
        self.assertEqual(error.exception.code, 400)

    def test_pi_camera_does_not_start_on_frame_get(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request("/api/pi-frame.jpg")
        self.assertEqual(error.exception.code, 503)
        body = json.loads(error.exception.read())
        self.assertIn("not been started", body["error"])


if __name__ == "__main__":
    unittest.main()
