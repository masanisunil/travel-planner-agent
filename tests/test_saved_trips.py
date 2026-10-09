import unittest
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from saved_trips import _result_payload, delete_trip, get_trip, list_trips, rename_trip, save_trip


class SavedTripTests(unittest.TestCase):
    def setUp(self):
        self.connection = MagicMock()
        self.connection.__enter__.return_value = self.connection
        self.cursor = self.connection.cursor.return_value.__enter__.return_value

    def test_result_payload_is_json_safe_and_keeps_displayed_sections(self):
        payload = _result_payload(
            {
                "itinerary": "Day one",
                "flight_results": "Flight notes",
                "train_results": "Train notes",
                "bus_results": "Bus notes",
                "hotel_results": "Hotel notes",
                "messages": [AIMessage(content="Trip overview")],
                "llm_calls": 2,
            }
        )

        self.assertEqual(payload["overview"], "Trip overview")
        self.assertEqual(payload["itinerary"], "Day one")
        self.assertEqual(payload["train_results"], "Train notes")
        self.assertNotIn("messages", payload)
        self.assertNotIn("llm_calls", payload)

    @patch("saved_trips.psycopg.connect")
    def test_save_trip_persists_compact_result(self, connect):
        connect.return_value = self.connection
        save_trip(
            "postgresql://db/roam",
            {
                "id": "trip-1",
                "destination": "Kyoto",
                "duration": 3,
                "date": "2026-04-20",
                "budget": "Balanced",
                "result": {"itinerary": "Day one", "messages": [AIMessage(content="Overview")]},
            },
        )

        connect.assert_called_once_with(
            "postgresql://db/roam", autocommit=True, connect_timeout=10
        )
        params = self.cursor.execute.call_args_list[-1].args[1]
        self.assertEqual(params[:6], ("trip-1", "Kyoto", "Kyoto", 3, "2026-04-20", "Balanced"))
        self.assertEqual(params[6].obj["itinerary"], "Day one")
        self.assertEqual(params[6].obj["overview"], "Overview")

    @patch("saved_trips.psycopg.connect")
    def test_list_and_get_trip_map_database_rows(self, connect):
        connect.return_value = self.connection
        self.cursor.fetchall.return_value = [
            ("trip-1", "Kyoto spring", "Kyoto", 3, "2026-04-20", "Balanced")
        ]
        self.cursor.fetchone.return_value = (
            "trip-1", "Kyoto spring", "Kyoto", 3, "2026-04-20", "Balanced", {"itinerary": "Day one"}
        )

        self.assertEqual(list_trips("postgresql://db/roam")[0]["title"], "Kyoto spring")
        self.assertEqual(get_trip("postgresql://db/roam", "trip-1")["result"]["itinerary"], "Day one")

    @patch("saved_trips.psycopg.connect")
    def test_missing_rows_return_none_or_false(self, connect):
        connect.return_value = self.connection
        self.cursor.fetchone.return_value = None
        self.cursor.rowcount = 0

        self.assertIsNone(get_trip("postgresql://db/roam", "missing-trip"))
        self.assertFalse(rename_trip("postgresql://db/roam", "missing-trip", "Kyoto"))
        self.assertFalse(delete_trip("postgresql://db/roam", "missing-trip"))

    @patch("saved_trips.psycopg.connect")
    def test_database_configuration_and_connection_errors_are_reported(self, connect):
        with self.assertRaisesRegex(ValueError, "Missing database configuration"):
            list_trips(None)
        connect.assert_not_called()

        connect.side_effect = RuntimeError("database unavailable")
        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            list_trips("postgresql://db/roam")

    @patch("saved_trips.psycopg.connect")
    def test_rename_and_delete_report_whether_a_trip_was_updated(self, connect):
        connect.return_value = self.connection
        self.cursor.rowcount = 1

        self.assertTrue(rename_trip("postgresql://db/roam", "trip-1", "  Kyoto spring  "))
        self.assertEqual(
            self.cursor.execute.call_args.args[1], ("Kyoto spring", "trip-1")
        )
        self.assertTrue(delete_trip("postgresql://db/roam", "trip-1"))


if __name__ == "__main__":
    unittest.main()