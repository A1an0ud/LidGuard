"""Evidence-continuity monitor with separate camera, upload and simulation sources."""

from __future__ import annotations

import csv
import io
import math
import threading
import time
from datetime import datetime, timezone


class Monitor:
    SOURCES = {"camera", "upload", "simulation"}
    STATES = {"OPEN", "CLOSED", "UNKNOWN"}
    MAX_GAP = 2.0

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.RLock()
        self.source = "simulation"
        self.source_epoch = 0
        self.threshold_seconds = 5.0
        self.events = []
        self._clear()
        self._log("monitor_started", "Engineering demonstration only")

    def _clear(self):
        self.state = "UNKNOWN"
        self.score = None
        self.quality = {"passed": False, "reason": "no_observation", "eye_presence_verified": False}
        self.last_sample = None
        self.open_since = None
        self.open_seconds = 0.0
        self.alarm = False
        self.alarm_unresolved = False
        self.acknowledged = False
        self.stale = False

    def _log(self, event, detail=""):
        self.events.append({
            "sequence": len(self.events) + 1,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "source": self.source,
            "source_epoch": self.source_epoch,
            "event": event,
            "state": self.state,
            "observed_open_seconds": round(self.open_seconds, 3),
            "threshold_seconds": self.threshold_seconds,
            "score": "" if self.score is None else self.score,
            "detail": detail,
        })

    def _update_alarm(self):
        active = self.state == "OPEN" and self.source != "upload" and self.open_seconds >= self.threshold_seconds
        if active and not self.alarm:
            self.alarm = True
            self.alarm_unresolved = False
            self.acknowledged = False
            self._log("alert_started", "Experimental duration exceeded; manual assessment required")
        elif active and self.alarm:
            self.alarm_unresolved = False
        elif self.state == "CLOSED" and self.alarm:
            self.alarm = False
            self.alarm_unresolved = False
            self.acknowledged = False
            self._log("alert_condition_ended", "A closed state was observed; this is not clinical clearance")
        elif self.alarm:
            self.alarm_unresolved = True

    def _refresh(self):
        now = self.clock()
        if self.source == "simulation" and self.state == "OPEN" and self.open_since is not None:
            self.open_seconds = max(0.0, now - self.open_since)
        elif self.source == "camera" and self.last_sample is not None and now - self.last_sample > self.MAX_GAP:
            if not self.stale:
                self.state = "UNKNOWN"
                self.score = None
                self.quality = {"passed": False, "reason": "camera_stream_stale", "eye_presence_verified": False}
                self.open_seconds = 0.0
                self.open_since = None
                self.stale = True
                self._log("evidence_lost", "No camera inference for more than 2 seconds; continuity reset")
        self._update_alarm()

    def status(self):
        with self.lock:
            self._refresh()
            age = None if self.last_sample is None else max(0.0, self.clock() - self.last_sample)
            return {
                "source": self.source,
                "source_epoch": self.source_epoch,
                "state": self.state,
                "score": self.score,
                "quality": self.quality,
                "open_seconds": round(self.open_seconds, 3),
                "threshold_seconds": self.threshold_seconds,
                "alarm": self.alarm,
                "alarm_unresolved": self.alarm_unresolved,
                "acknowledged": self.acknowledged,
                "stale": self.stale,
                "sample_age_seconds": None if age is None else round(age, 3),
                "max_sample_gap_seconds": self.MAX_GAP,
                "events_count": len(self.events),
                "simulation": self.source == "simulation",
                "snapshot_only": self.source == "upload",
                "limitations": "Research demo. Manual eye ROI. No eye-presence verification, clinical validation or NIR validation. Alert threshold is experimental.",
            }

    def set_source(self, source):
        if source not in self.SOURCES:
            raise ValueError("source must be camera, upload or simulation")
        with self.lock:
            self.source = source
            self.source_epoch += 1
            self._clear()
            self._log("source_changed", "Continuity reset")
            return self.status()

    def _check_epoch(self, source, epoch):
        if source != self.source or type(epoch) is not int or epoch != self.source_epoch:
            raise ValueError("Source changed. Use the current source_epoch from /api/source or /api/status.")

    def observe(self, source, epoch, prediction):
        if source not in {"camera", "upload"}:
            raise ValueError("Image prediction source must be camera or upload")
        with self.lock:
            self._check_epoch(source, epoch)
            self._refresh()
            now = self.clock()
            new_state = prediction["state"]
            if new_state not in self.STATES:
                raise ValueError("Unsupported state")
            old_state = self.state
            previous = self.last_sample
            if source == "camera" and new_state == "OPEN" and old_state == "OPEN" and previous is not None and now - previous <= self.MAX_GAP:
                self.open_seconds += max(0.0, now - previous)
            else:
                self.open_seconds = 0.0
            self.state = new_state
            self.score = prediction.get("score")
            self.quality = prediction.get("quality", {})
            self.last_sample = now
            self.stale = False
            if new_state != old_state or source == "upload":
                self._log("observation_changed", self.quality.get("reason", ""))
            self._update_alarm()
            return self.status()

    def simulate(self, state, epoch):
        if state not in self.STATES:
            raise ValueError("state must be OPEN, CLOSED or UNKNOWN")
        with self.lock:
            self._check_epoch("simulation", epoch)
            self._refresh()
            if state != self.state:
                self.open_seconds = 0.0
                self.open_since = self.clock() if state == "OPEN" else None
            self.state = state
            self.score = None
            self.quality = {"passed": False, "reason": "simulated_input", "eye_presence_verified": False}
            self.last_sample = self.clock()
            self._log("simulated_state_selected", "Manual simulation; no image classification")
            return self.status()

    def reset(self):
        with self.lock:
            self.source_epoch += 1
            self._clear()
            self._log("monitor_reset", "Timer reset; historical events retained")
            return self.status()

    def configure(self, threshold):
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or not 0.5 <= threshold <= 3600:
            raise ValueError("threshold_seconds must be a finite number from 0.5 to 3600")
        with self.lock:
            self.threshold_seconds = float(threshold)
            self.source_epoch += 1
            self._clear()
            self._log("threshold_changed", "Experimental setting; continuity reset")
            return self.status()

    def acknowledge(self):
        with self.lock:
            self._refresh()
            if self.alarm:
                self.acknowledged = True
                self._log("alert_acknowledged", "Acknowledgment does not clear an ongoing alert condition")
            return self.status()

    def csv(self):
        with self.lock:
            self._refresh()
            stream = io.StringIO(newline="")
            fields = ["sequence", "timestamp_utc", "source", "source_epoch", "event", "state", "observed_open_seconds", "threshold_seconds", "score", "detail"]
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(self.events)
            return stream.getvalue()
