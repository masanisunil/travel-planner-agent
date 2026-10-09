from threading import Event
import unittest
from pathlib import Path
from unittest.mock import patch

from langchain_core.messages import AIMessage
from streamlit.testing.v1 import AppTest
from trip_jobs import TripJobManager


class StreamlitRerunTests(unittest.TestCase):
    def setUp(self):
        self.dotenv_patch = patch("dotenv.load_dotenv")
        self.list_trips_patch = patch("saved_trips.list_trips", return_value=[])
        self.database_url_patch = patch(
            "main.get_database_url", return_value="postgresql://test.invalid/roam"
        )
        self.dotenv_patch.start()
        self.list_trips_mock = self.list_trips_patch.start()
        self.database_url_patch.start()
        self.addCleanup(self.dotenv_patch.stop)
        self.addCleanup(self.list_trips_patch.stop)
        self.addCleanup(self.database_url_patch.stop)

    def create_app(self):
        app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
        return AppTest.from_file(str(app_path), default_timeout=15)

    @staticmethod
    def saved_trip():
        return {
            "id": "trip-1",
            "title": "Kyoto spring",
            "destination": "Kyoto",
            "duration": 3,
            "date": "2026-04-20",
            "budget": "Balanced",
        }

    def test_theme_toggle_does_not_clear_pending_trip(self):
        app = self.create_app().run()
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

    def test_saved_trip_list_can_open_selected_trip(self):
        self.list_trips_mock.return_value = [self.saved_trip()]
        trip = {**self.saved_trip(), "result": {"itinerary": "Walk the Philosopher's Path."}}
        app = self.create_app().run()

        with patch("saved_trips.get_trip", return_value=trip) as get_trip:
            app.button(key="open_saved_trip").click().run()

        get_trip.assert_called_once_with("postgresql://test.invalid/roam", "trip-1")
        self.assertEqual(app.session_state["active_trip"], trip)
        self.assertTrue(any("Walk the Philosopher's Path." in item.value for item in app.markdown))

    def test_saved_trip_rename_rejects_blank_name(self):
        self.list_trips_mock.return_value = [self.saved_trip()]
        app = self.create_app().run()
        next(item for item in app.text_input if item.label == "Trip name").set_value("   ")

        with patch("saved_trips.rename_trip") as rename_trip:
            next(item for item in app.button if item.label == "Save name").click().run()

        rename_trip.assert_not_called()
        self.assertTrue(any("Enter a name for this trip." in item.value for item in app.error))

    def test_saved_trip_rename_saves_trimmed_name(self):
        self.list_trips_mock.return_value = [self.saved_trip()]
        app = self.create_app()
        app.session_state["active_trip"] = {
            **self.saved_trip(), "result": {"itinerary": "Day one"}
        }
        app.run()
        next(item for item in app.text_input if item.label == "Trip name").set_value("Kyoto, in spring")

        with patch("saved_trips.rename_trip", return_value=True) as rename_trip:
            next(item for item in app.button if item.label == "Save name").click().run()

        rename_trip.assert_called_once_with(
            "postgresql://test.invalid/roam", "trip-1", "Kyoto, in spring"
        )
        self.assertEqual(app.exception, [])
        self.assertEqual(app.session_state["active_trip"]["title"], "Kyoto, in spring")

    def test_delete_trip_can_be_cancelled(self):
        self.list_trips_mock.return_value = [self.saved_trip()]
        app = self.create_app().run()

        with patch("saved_trips.delete_trip") as delete_trip:
            app.button(key="request_delete_trip-1").click().run()
            self.assertEqual(app.session_state["delete_trip_confirmation"], "trip-1")
            app.button(key="cancel_delete_trip").click().run()

        delete_trip.assert_not_called()
        self.assertIsNone(app.session_state["delete_trip_confirmation"])

    def test_delete_trip_confirmation_deletes_and_clears_open_trip(self):
        self.list_trips_mock.return_value = [self.saved_trip()]
        app = self.create_app()
        app.session_state["active_trip"] = {
            **self.saved_trip(), "result": {"itinerary": "Day one"}
        }
        app.run()

        with patch("saved_trips.delete_trip", return_value=True) as delete_trip:
            app.button(key="request_delete_trip-1").click().run()
            app.button(key="confirm_delete_trip").click().run()

        delete_trip.assert_called_once_with("postgresql://test.invalid/roam", "trip-1")
        self.assertIsNone(app.session_state["active_trip"])
        self.assertIsNone(app.session_state["delete_trip_confirmation"])

    def completed_job(self, error=None):
        return {
            "trip_details": {
                "id": "job-1",
                "destination": "Kyoto",
                "duration": 3,
                "date": "2026-04-20",
                "budget": "Balanced",
            },
            "done": True,
            "error": error,
            "result": {"itinerary": "Day one in Kyoto", "messages": []},
        }

    def test_completed_job_saves_and_opens_trip(self):
        app = self.create_app()
        app.session_state["generation_job_id"] = "job-1"
        with patch.object(TripJobManager, "snapshot", return_value=self.completed_job()), patch.object(
            TripJobManager, "discard"
        ), patch("saved_trips.save_trip") as save_trip:
            app.run()

        saved_trip = app.session_state["active_trip"]
        self.assertEqual(saved_trip["destination"], "Kyoto")
        self.assertEqual(saved_trip["result"]["itinerary"], "Day one in Kyoto")
        save_trip.assert_called_once_with("postgresql://test.invalid/roam", saved_trip)
        self.assertIsNone(app.session_state["generation_job_id"])
        self.assertIsNone(app.session_state["history_error"])

    def test_completed_job_shows_warning_when_trip_save_fails(self):
        app = self.create_app()
        app.session_state["generation_job_id"] = "job-1"
        with patch.object(TripJobManager, "snapshot", return_value=self.completed_job()), patch.object(
            TripJobManager, "discard"
        ), patch("saved_trips.save_trip", side_effect=RuntimeError("database unavailable")):
            app.run()

        self.assertEqual(
            app.session_state["history_error"],
            "Your itinerary is ready, but it could not be saved to trip history.",
        )
        self.assertEqual(app.session_state["active_trip"]["destination"], "Kyoto")
        self.assertTrue(any("could not be saved to trip history" in item.value for item in app.warning))

    def test_failed_job_shows_user_facing_error_without_saving(self):
        app = self.create_app()
        app.session_state["generation_job_id"] = "job-1"
        with patch.object(
            TripJobManager,
            "snapshot",
            return_value=self.completed_job(error="RuntimeError"),
        ), patch.object(TripJobManager, "discard"), patch("saved_trips.save_trip") as save_trip:
            app.run()

        save_trip.assert_not_called()
        self.assertIsNone(app.session_state["generation_job_id"])
        self.assertIn("Trip planning could not finish.", app.session_state["generation_error"])
        self.assertTrue(any("Trip planning could not finish." in item.value for item in app.error))

    def test_itinerary_download_uses_expected_filename_and_all_sections(self):
        app = self.create_app()
        app.session_state["active_trip"] = {
            **self.saved_trip(),
            "result": {
                "itinerary": "Day one",
                "flight_results": "Flight notes",
                "train_results": "Train notes",
                "bus_results": "Bus notes",
                "hotel_results": "Hotel notes",
            },
        }
        with patch("streamlit.download_button") as download_button:
            app.run()

        download_button.assert_called_once()
        self.assertEqual(download_button.call_args.args[0], "Download itinerary")
        self.assertEqual(download_button.call_args.kwargs["file_name"], "roam-itinerary.md")
        document = download_button.call_args.kwargs["data"]
        for section in ("# Kyoto", "Day one", "Flight notes", "Train notes", "Bus notes", "Hotel notes"):
            self.assertIn(section, document)


if __name__ == "__main__":
    unittest.main()
