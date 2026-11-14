import unittest

from lidguard.monitor import Monitor


class Clock:
    def __init__(self):
        self.now = 0.0
    def __call__(self):
        return self.now
    def advance(self, seconds):
        self.now += seconds


def observation(state):
    return {"state": state, "score": 0.9 if state != "UNKNOWN" else None, "quality": {"passed": state != "UNKNOWN", "reason": "test"}}


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.monitor = Monitor(self.clock)

    def camera(self):
        return self.monitor.set_source("camera")["source_epoch"]

    def open_for(self, epoch, seconds):
        self.monitor.observe("camera", epoch, observation("OPEN"))
        for _ in range(int(seconds * 2)):
            self.clock.advance(0.5)
            self.monitor.observe("camera", epoch, observation("OPEN"))

    def test_continuous_open_threshold_acknowledgment_and_close(self):
        epoch = self.camera()
        self.open_for(epoch, 5)
        status = self.monitor.status()
        self.assertTrue(status["alarm"])
        self.assertEqual(status["open_seconds"], 5)
        status = self.monitor.acknowledge()
        self.assertTrue(status["acknowledged"])
        self.assertTrue(status["alarm"])
        self.clock.advance(0.5)
        status = self.monitor.observe("camera", epoch, observation("CLOSED"))
        self.assertFalse(status["alarm"])
        self.assertFalse(status["acknowledged"])
        self.assertEqual(status["open_seconds"], 0)

    def test_lost_stream_becomes_unknown_and_restart_starts_new_episode(self):
        epoch = self.camera()
        self.open_for(epoch, 4)
        self.clock.advance(2.01)
        status = self.monitor.status()
        self.assertEqual(status["state"], "UNKNOWN")
        self.assertTrue(status["stale"])
        self.assertEqual(status["open_seconds"], 0)
        self.assertFalse(status["alarm"])
        status = self.monitor.observe("camera", epoch, observation("OPEN"))
        self.assertFalse(status["stale"])
        self.assertEqual(status["open_seconds"], 0)

    def test_unknown_quality_breaks_continuity(self):
        epoch = self.camera()
        self.open_for(epoch, 4)
        self.clock.advance(0.5)
        self.monitor.observe("camera", epoch, observation("UNKNOWN"))
        self.clock.advance(0.5)
        status = self.monitor.observe("camera", epoch, observation("OPEN"))
        self.assertEqual(status["open_seconds"], 0)
        self.assertFalse(status["alarm"])

    def test_upload_snapshot_never_accumulates_duration(self):
        epoch = self.monitor.set_source("upload")["source_epoch"]
        self.monitor.observe("upload", epoch, observation("OPEN"))
        self.clock.advance(200)
        status = self.monitor.observe("upload", epoch, observation("OPEN"))
        self.assertEqual(status["open_seconds"], 0)
        self.assertFalse(status["alarm"])
        self.assertTrue(status["snapshot_only"])

    def test_source_switch_discards_old_inflight_frames(self):
        epoch = self.camera()
        self.open_for(epoch, 4)
        status = self.monitor.set_source("simulation")
        self.assertEqual(status["state"], "UNKNOWN")
        self.assertEqual(status["open_seconds"], 0)
        with self.assertRaises(ValueError):
            self.monitor.observe("camera", epoch, observation("OPEN"))

    def test_simulation_is_explicitly_labelled_and_separate(self):
        epoch = self.monitor.set_source("simulation")["source_epoch"]
        self.monitor.simulate("OPEN", epoch)
        self.clock.advance(6)
        status = self.monitor.status()
        self.assertTrue(status["simulation"])
        self.assertTrue(status["alarm"])
        self.assertIsNone(status["score"])
        status = self.monitor.set_source("camera")
        self.assertFalse(status["simulation"])
        self.assertFalse(status["alarm"])
        self.assertEqual(status["state"], "UNKNOWN")

    def test_reset_and_configuration_reject_stale_frames(self):
        epoch = self.camera()
        self.open_for(epoch, 4)
        status = self.monitor.configure(10)
        self.assertEqual(status["threshold_seconds"], 10)
        self.assertEqual(status["open_seconds"], 0)
        with self.assertRaises(ValueError):
            self.monitor.observe("camera", epoch, observation("OPEN"))
        for value in [float("nan"), float("inf"), 0, True, "5"]:
            with self.assertRaises(ValueError):
                self.monitor.configure(value)

    def test_events_preserve_evidence_loss_and_acknowledgment(self):
        epoch = self.camera()
        self.open_for(epoch, 5)
        self.monitor.acknowledge()
        self.clock.advance(3)
        text = self.monitor.csv()
        self.assertIn("alert_started", text)
        self.assertIn("alert_acknowledged", text)
        self.assertIn("evidence_lost", text)
        self.assertIn("camera", text)

    def test_alert_and_ack_survive_unknown_until_closed_without_new_alert(self):
        epoch = self.camera()
        self.open_for(epoch, 5)
        self.monitor.acknowledge()
        self.clock.advance(0.5)
        status = self.monitor.observe("camera", epoch, observation("UNKNOWN"))
        self.assertEqual(status["state"], "UNKNOWN")
        self.assertEqual(status["open_seconds"], 0)
        self.assertTrue(status["alarm"])
        self.assertTrue(status["alarm_unresolved"])
        self.assertTrue(status["acknowledged"])
        self.clock.advance(0.5)
        status = self.monitor.observe("camera", epoch, observation("OPEN"))
        self.assertTrue(status["alarm_unresolved"])
        self.assertTrue(status["acknowledged"])
        self.open_for(epoch, 5)
        status = self.monitor.status()
        self.assertTrue(status["alarm"])
        self.assertFalse(status["alarm_unresolved"])
        self.assertTrue(status["acknowledged"])
        self.assertEqual(sum(event["event"] == "alert_started" for event in self.monitor.events), 1)
        status = self.monitor.observe("camera", epoch, observation("CLOSED"))
        self.assertFalse(status["alarm"])
        self.assertFalse(status["alarm_unresolved"])
        self.assertFalse(status["acknowledged"])

    def test_alert_and_ack_survive_stale_stream_without_phantom_restart(self):
        epoch = self.camera()
        self.open_for(epoch, 5)
        self.monitor.acknowledge()
        self.clock.advance(2.01)
        status = self.monitor.status()
        self.assertEqual(status["state"], "UNKNOWN")
        self.assertTrue(status["stale"])
        self.assertEqual(status["open_seconds"], 0)
        self.assertTrue(status["alarm"])
        self.assertTrue(status["alarm_unresolved"])
        self.assertTrue(status["acknowledged"])
        self.monitor.status()
        self.assertEqual(sum(event["event"] == "alert_started" for event in self.monitor.events), 1)
        status = self.monitor.reset()
        self.assertFalse(status["alarm"])
        self.assertFalse(status["alarm_unresolved"])


if __name__ == "__main__":
    unittest.main()
