"""Optional Picamera2 capture. Import and camera activation are explicit."""

import io
import threading


class PiCameraService:
    def __init__(self):
        self.camera = None
        self.lock = threading.Lock()

    def start(self):
        with self.lock:
            if self.camera is not None:
                return {"ok": True, "running": True, "hardware_tested_in_this_package": False}
            try:
                from picamera2 import Picamera2
            except ImportError as exc:
                raise RuntimeError("Picamera2 is unavailable. This option requires a supported Raspberry Pi OS, python3-picamera2, and a connected CSI camera. Use USB webcam or image upload otherwise.") from exc
            camera = None
            try:
                camera = Picamera2()
                configuration = camera.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"})
                camera.configure(configuration)
                camera.start()
                self.camera = camera
            except Exception as exc:
                if camera is not None:
                    try:
                        camera.close()
                    except Exception:
                        pass
                raise RuntimeError("The CSI camera could not start. Check the cable with the Pi powered off, verify detection with rpicam-hello, and close other camera applications.") from exc
            return {"ok": True, "running": True, "hardware_tested_in_this_package": False}

    def frame(self):
        with self.lock:
            if self.camera is None:
                raise RuntimeError("CSI camera has not been started. Use the explicit Start Pi camera control first.")
            output = io.BytesIO()
            try:
                self.camera.capture_file(output, format="jpeg")
            except Exception as exc:
                raise RuntimeError("CSI camera frame capture failed. Check the camera connection and restart capture.") from exc
            return output.getvalue()

    def stop(self):
        with self.lock:
            if self.camera is not None:
                camera = self.camera
                self.camera = None
                try:
                    camera.stop()
                finally:
                    camera.close()
            return {"ok": True, "running": False, "hardware_tested_in_this_package": False}
