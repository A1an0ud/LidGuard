"""Small, inspectable RGB baseline. No executable model deserialization."""

from __future__ import annotations

import base64
import binascii
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError


FEATURE_SIZE = (30, 18)
MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_IMAGE_PIXELS = 8_000_000


def features(image: Image.Image) -> np.ndarray:
    image = ImageOps.exif_transpose(image).convert("L")
    image = image.resize(FEATURE_SIZE, Image.Resampling.BILINEAR)
    return np.asarray(image, dtype=np.float64).reshape(-1) / 255.0


def decode_image(data_url: str) -> Image.Image:
    if not isinstance(data_url, str) or len(data_url) > MAX_IMAGE_BYTES * 4 // 3 + 200:
        raise ValueError("Image is missing or exceeds the 4 MiB image limit.")
    if not data_url.startswith(("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,")):
        raise ValueError("Use a base64 PNG, JPEG or WebP data URL.")
    try:
        raw = base64.b64decode(data_url.split(",", 1)[1], validate=True)
        if len(raw) > MAX_IMAGE_BYTES:
            raise ValueError("Image exceeds the 4 MiB limit.")
        image = Image.open(io.BytesIO(raw))
        if image.width * image.height > MAX_IMAGE_PIXELS:
            raise ValueError("Image exceeds the 8-megapixel processing limit.")
        image.load()
        return ImageOps.exif_transpose(image).convert("RGB")
    except (binascii.Error, UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("The supplied image cannot be decoded safely.") from exc


class EyeBaseline:
    def __init__(self, model_path: Path):
        self.path = Path(model_path)
        self.data = json.loads(self.path.read_text(encoding="utf-8"))
        if self.data.get("schema_version") != 1 or self.data.get("feature_size") != list(FEATURE_SIZE):
            raise ValueError("Unsupported model format.")
        self.mean = np.asarray(self.data["scaler_mean"], dtype=np.float64)
        self.scale = np.asarray(self.data["scaler_scale"], dtype=np.float64)
        self.weights = np.asarray(self.data["weights"], dtype=np.float64)
        self.intercept = float(self.data["intercept"])
        size = FEATURE_SIZE[0] * FEATURE_SIZE[1]
        if any(x.shape != (size,) for x in (self.mean, self.scale, self.weights)):
            raise ValueError("Invalid model dimensions.")
        if not all(np.all(np.isfinite(x)) for x in (self.mean, self.scale, self.weights)) or not np.isfinite(self.intercept):
            raise ValueError("Model contains non-finite values.")
        if np.any(self.scale <= 0):
            raise ValueError("Model scale must be positive.")

    def info(self) -> dict:
        return {
            "name": self.data["name"],
            "modality": "RGB eye-region crops",
            "feature_size": self.data["feature_size"],
            "labels": ["CLOSED", "OPEN"],
            "decision_score_minimum": 0.75,
            "score_is_calibrated": False,
            "eye_presence_detection": False,
            "partial_opening_detection": False,
            "corneal_exposure_detection": False,
            "clinical_validation": False,
            "nir_validation": False,
            "evaluation": self.data["evaluation"],
            "limitations": [
                "Small RGB demonstration baseline. No validation on this device, NIR images or ICU patients.",
                "The operator must select an eye crop and confirm it is visible. Image-quality checks do not prove an eye is present.",
                "The score is an uncalibrated logistic model output, not a probability of clinical safety.",
                "OPEN is an image category and does not establish corneal exposure or injury.",
                "The 0.75 abstention threshold and alert duration are engineering demo settings, not clinical thresholds.",
            ],
            "training_source": self.data["training_source"],
        }

    def predict(self, image: Image.Image, roi_confirmed: bool = False) -> dict:
        gray = np.asarray(image.convert("L"), dtype=np.float64)
        mean = float(gray.mean())
        std = float(gray.std())
        clipped = float(np.mean((gray < 3) | (gray > 252)))
        checks = {
            "minimum_resolution": image.width >= 24 and image.height >= 14,
            "illumination": 12 <= mean <= 243,
            "contrast": std >= 10,
            "not_mostly_clipped": clipped < 0.95,
            "operator_confirmed_eye_roi": roi_confirmed is True,
        }
        quality = {
            "passed": all(checks.values()),
            "checks": checks,
            "width": image.width,
            "height": image.height,
            "mean_brightness": round(mean, 2),
            "contrast_std": round(std, 2),
            "eye_presence_verified": False,
            "reason": "ok" if all(checks.values()) else ", ".join(k for k, v in checks.items() if not v),
        }
        if not quality["passed"]:
            return {"state": "UNKNOWN", "score": None, "p_open": None, "quality": quality}
        vector = (features(image) - self.mean) / self.scale
        logit = float(vector @ self.weights + self.intercept)
        p_open = float(1.0 / (1.0 + np.exp(-np.clip(logit, -700.0, 700.0))))
        score = max(p_open, 1.0 - p_open)
        state = "OPEN" if p_open >= 0.5 else "CLOSED"
        if score < 0.75:
            state = "UNKNOWN"
            quality["reason"] = "ambiguous_model_score"
        return {"state": state, "score": round(score, 6), "p_open": round(p_open, 6), "quality": quality}
