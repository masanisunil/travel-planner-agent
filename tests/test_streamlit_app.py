from threading import Event
import unittest
from pathlib import Path
from unittest.mock import patch

from langchain_core.messages import AIMessage
from streamlit.testing.v1 import AppTest
from trip_jobs import TripJobManager


class StreamlitRerunTests(unittest.TestCase):
    def test_theme_toggle_does_not_clear_pending_trip(self):
        app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
        app = AppTest.from_file(str(app_path), default_timeout=15).run()
        self.assertEqual(app.exception, [])
        worker_started = Event()
        release_worker = Event()
        start_job = TripJobManager.start

        def start_pending_job(manager, job_id, _worker, trip_details, total_steps):
            def fake_worker(progress):
                worker_started.set()
                progress("Flight research complete", 1, total_steps)
                progress("Hotel research complete", 2, total_steps)
                if not release_worker.wait(timeout=5):
                    raise TimeoutError("test worker was not released")
                progress("Train routes researched", 3, total_steps)
                progress("Bus routes researched", 4, total_steps)
                progress("Itinerary ready", 5, total_steps)
                progress("Trip overview ready", 6, total_steps)
                return {
                    "itinerary": "## Day 1\nExplore Bengaluru.",
                    "flight_results": "Flight reference data",
                    "train_results": "Train reference data",
                    "bus_results": "Bus reference data",
                    "hotel_results": "Hotel reference data",
                    "messages": [AIMessage(content="Trip overview")],
                    "llm_calls": 2,
                }

            start_job(manager, job_id, fake_worker, trip_details, total_steps)

        with patch.object(TripJobManager, "start", new=start_pending_job):
            app.button[0].click().run()
            self.assertEqual(app.exception, [])
            self.assertTrue(worker_started.wait(timeout=2))
            job_id = app.session_state["generation_job_id"]
            self.assertIsNotNone(job_id)

            app.toggle(key="dark_mode").set_value(True).run()
            self.assertEqual(app.exception, [])
            self.assertEqual(app.session_state["generation_job_id"], job_id)
            self.assertTrue(app.session_state["dark_mode"])
            self.assertTrue(any("Flight research complete" in item.value for item in app.markdown))
            self.assertTrue(any("Hotel research complete" in item.value for item in app.markdown))

            release_worker.set()
            for _ in range(40):
                app.run()
                if app.session_state["active_trip"] is not None:
                    break
                Event().wait(0.05)

            self.assertEqual(app.exception, [])
            trip = app.session_state["active_trip"]
            self.assertEqual(trip["result"]["train_results"], "Train reference data")
            self.assertEqual(trip["result"]["bus_results"], "Bus reference data")
            self.assertTrue(any("Train reference data" in item.value for item in app.markdown))
            self.assertTrue(any("Bus reference data" in item.value for item in app.markdown))
            self.assertTrue(any("Explore Bengaluru" in item.value for item in app.markdown))
            self.assertTrue(any("Transport options" in tab.label for tab in app.tabs))
            self.assertIsNone(app.session_state["generation_job_id"])


if __name__ == "__main__":
    unittest.main()
