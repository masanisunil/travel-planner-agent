from threading import Event
import unittest

from trip_jobs import TripJobManager


class TripJobManagerTests(unittest.TestCase):
    def test_job_survives_repeated_state_reads_and_reports_progress(self):
        started = Event()
        release = Event()
        manager = TripJobManager(max_workers=1)

        def worker(progress):
            started.set()
            if not release.wait(timeout=3):
                raise TimeoutError("test worker was not released")
            progress("Flights researched", 1, 3)
            progress("Hotels researched", 2, 3)
            progress("Research complete", 3, 3)
            return {"itinerary": "Completed"}

        manager.start("theme-toggle-check", worker, {"destination": "Bengaluru"}, 1)
        self.assertTrue(started.wait(timeout=2))
        self.assertFalse(manager.snapshot("theme-toggle-check")["done"])
        self.assertFalse(manager.snapshot("theme-toggle-check")["done"])
        release.set()

        for _ in range(100):
            snapshot = manager.snapshot("theme-toggle-check")
            if snapshot["done"]:
                break
            Event().wait(0.01)

        self.assertTrue(snapshot["done"])
        self.assertEqual(snapshot["completed"], 3)
        self.assertEqual(
            snapshot["steps"],
            ["Flights researched", "Hotels researched", "Research complete"],
        )
        self.assertEqual(snapshot["result"]["itinerary"], "Completed")
        manager.discard("theme-toggle-check")
        self.assertIsNone(manager.snapshot("theme-toggle-check"))

    def test_worker_failure_is_captured_without_exposing_exception_text(self):
        manager = TripJobManager(max_workers=1)

        def worker(progress):
            raise RuntimeError("private provider response")

        manager.start("failure-check", worker, {}, 1)
        for _ in range(100):
            snapshot = manager.snapshot("failure-check")
            if snapshot["done"]:
                break
            Event().wait(0.01)

        self.assertTrue(snapshot["done"])
        self.assertEqual(snapshot["error"], "RuntimeError")
        self.assertNotIn("private", str(snapshot))
        manager.discard("failure-check")


if __name__ == "__main__":
    unittest.main()
