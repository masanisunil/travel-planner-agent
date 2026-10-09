from contextlib import redirect_stdout
from io import StringIO
import os
import sys
from threading import Barrier
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from langchain_core.messages import AIMessage, HumanMessage

import main


class TravelGraphTests(unittest.TestCase):
    def tearDown(self):
        main.get_llm.cache_clear()

    def test_research_is_parallel_and_joined_before_model_calls(self):
        barrier = Barrier(4)
        prompts = []

        def flight_search(query):
            barrier.wait(timeout=3)
            return "Flight reference data"

        def hotel_search(query):
            barrier.wait(timeout=3)
            return "Hotel reference data"

        def train_search(query):
            barrier.wait(timeout=3)
            return "Train reference data"

        def bus_search(query):
            barrier.wait(timeout=3)
            return "Bus reference data"

        def model_invoke(messages):
            prompts.append(messages)
            return AIMessage(content="Itinerary" if len(prompts) == 1 else "Final response")

        providers = {
            "tools.flight_tool": SimpleNamespace(search_flight=flight_search),
            "tools.tavily_tool": SimpleNamespace(
                tavily_search=lambda query: (
                    train_search(query) if "train" in query else
                    bus_search(query) if "bus" in query else
                    hotel_search(query)
                )
            ),
        }
        with patch.dict(sys.modules, providers), patch.object(
            main, "get_llm", return_value=SimpleNamespace(invoke=model_invoke)
        ):
            result = main.graph.compile().invoke({
                "messages": [HumanMessage(content="Bengaluru for 2 days")],
                "user_query": "Bengaluru for 2 days",
                "origin_city": "Chennai",
                "destination_city": "Bengaluru",
                "llm_calls": 0,
            })

        self.assertEqual(len(prompts), 2)
        self.assertIn("Flight reference data", prompts[0][-1].content)
        self.assertIn("Hotel reference data", prompts[0][-1].content)
        self.assertIn("Train reference data", prompts[0][-1].content)
        self.assertIn("Bus reference data", prompts[0][-1].content)
        self.assertEqual(result["train_results"], "Train reference data")
        self.assertEqual(result["bus_results"], "Bus reference data")
        self.assertIn("Bengaluru for 2 days", prompts[1][-1].content)
        self.assertEqual(result["llm_calls"], 2)
        self.assertEqual(len(result["messages"]), 7)
        self.assertEqual(result["messages"][-1].content, "Final response")

    def test_model_is_cached_and_has_bounded_requests(self):
        main.get_llm.cache_clear()
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}), patch.object(main, "ChatGroq") as constructor:
            self.assertIs(main.get_llm(), main.get_llm())
        constructor.assert_called_once()
        self.assertEqual(constructor.call_args.kwargs["timeout"], 60)
        self.assertEqual(constructor.call_args.kwargs["max_retries"], 2)

    def test_missing_model_key_is_rejected_before_client_creation(self):
        main.get_llm.cache_clear()
        with patch.dict(os.environ, {}, clear=True), patch.object(main, "ChatGroq") as constructor:
            with self.assertRaisesRegex(ValueError, "GROQ_API_KEY"):
                main.get_llm()
        constructor.assert_not_called()

    def test_blank_query_does_not_open_database(self):
        with patch.dict(os.environ, {"POSTGRES_URL": "postgresql://test.invalid/test"}), patch(
            "builtins.input", return_value="  "
        ), patch.object(main.psycopg, "connect") as connect, redirect_stdout(StringIO()):
            self.assertEqual(main.run_cli(), 1)
        connect.assert_not_called()

    def test_cli_closes_database_and_prints_only_final_response(self):
        output = StringIO()
        with patch.dict(os.environ, {"POSTGRES_URL": "postgresql://test.invalid/test"}), patch(
            "builtins.input", return_value="Bengaluru"
        ), patch.object(main, "get_llm"), patch.object(main.psycopg, "connect") as connect, patch.object(
            main, "PostgresSaver"
        ), patch.object(main.graph, "compile") as compile_graph, redirect_stdout(output):
            compile_graph.return_value.invoke.return_value = {
                "messages": [AIMessage(content="Intermediate research"), AIMessage(content="Final travel plan")]
            }
            self.assertEqual(main.run_cli(), 0)
        connect.return_value.__exit__.assert_called_once()
        self.assertEqual(connect.call_args.kwargs["connect_timeout"], 10)
        self.assertIn("Final travel plan", output.getvalue())
        self.assertNotIn("Intermediate research", output.getvalue())

    def test_cli_closes_database_on_provider_failure(self):
        output = StringIO()
        with patch.dict(os.environ, {"POSTGRES_URL": "postgresql://test.invalid/test"}), patch(
            "builtins.input", return_value="Bengaluru"
        ), patch.object(main, "get_llm"), patch.object(main.psycopg, "connect") as connect, patch.object(
            main, "PostgresSaver"
        ), patch.object(main.graph, "compile") as compile_graph, redirect_stdout(output):
            compile_graph.return_value.invoke.side_effect = RuntimeError("sensitive provider details")
            self.assertEqual(main.run_cli(), 1)
        connect.return_value.__exit__.assert_called_once()
        self.assertIn("RuntimeError", output.getvalue())
        self.assertNotIn("sensitive provider details", output.getvalue())


if __name__ == "__main__":
    unittest.main()