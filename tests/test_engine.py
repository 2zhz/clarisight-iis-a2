import unittest
from engine import ClariSightEngine, FrameInput, DetectedObject


class TestClariSightEngine(unittest.TestCase):
    def setUp(self):
        self.engine = ClariSightEngine()

    def test_navigation_suppresses_distant_clutter(self):
        self.engine.set_mode("navigation")
        resp = self.engine.load_scenario("hallway_nav")
        self.assertEqual(resp.tier, 1)
        self.assertEqual(resp.status, "ok")
        self.assertIn("Chair ahead", resp.speech_text)
        self.assertEqual(resp.suppressed_count, 2)
        self.assertEqual(resp.earcon, "urgent_double")

    def test_clear_path_uses_tier0_earcon_only(self):
        self.engine.set_mode("navigation")
        frame = FrameInput(
            scenario_id="clear_test",
            scene_title="Empty Corridor",
            brightness=0.80,
            sharpness=0.85,
            target_query=None,
            detections=[
                DetectedObject("wall poster", 3.5, "2 o'clock", 0.90, hazard=False)
            ]
        )
        resp = self.engine.process_frame(frame)
        self.assertEqual(resp.tier, 0)
        self.assertEqual(resp.earcon, "sonar")
        self.assertEqual(resp.suppressed_count, 1)

    def test_low_light_and_low_confidence_triggers_uncertainty_gate(self):
        self.engine.set_mode("object_finding", "medicine bottle")
        resp = self.engine.load_scenario("low_light_failure")
        self.assertTrue(resp.uncertainty_flag)
        self.assertEqual(resp.status, "uncertain")
        self.assertEqual(resp.earcon, "uncertainty_low")
        self.assertIn("Uncertain view", resp.speech_text)
        self.assertIsNotNone(resp.guidance_hint)

    def test_recovery_after_stabilisation(self):
        self.engine.set_mode("object_finding", "medicine bottle")
        resp = self.engine.load_scenario("low_light_recovered")
        self.assertFalse(resp.uncertainty_flag)
        self.assertEqual(resp.status, "ok")
        self.assertIn("Found medicine bottle", resp.speech_text)

    def test_busy_kitchen_prioritises_hazard_with_target(self):
        self.engine.set_mode("object_finding", "keys")
        resp = self.engine.load_scenario("busy_kitchen")
        self.assertEqual(resp.status, "ok")
        self.assertIn("Caution: kettle", resp.speech_text)
        self.assertIn("Found keys", resp.speech_text)
        self.assertEqual(resp.suppressed_count, 2)

    def test_barge_in_and_detail_request(self):
        self.engine.load_scenario("hallway_nav")
        detail = self.engine.request_detail()
        self.assertEqual(detail.tier, 2)
        self.assertEqual(detail.suppressed_count, 0)

        stopped = self.engine.barge_in_interrupt()
        self.assertEqual(stopped.status, "interrupted")
        self.assertFalse(self.engine.speaking_active)

    def test_user_correction_logged(self):
        self.engine.load_scenario("low_light_failure")
        resp = self.engine.report_correction("Wrong bottle label")
        self.assertEqual(resp.status, "corrected")
        self.assertEqual(len(self.engine.correction_log), 1)


if __name__ == "__main__":
    unittest.main()
