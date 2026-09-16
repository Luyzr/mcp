import importlib.util
from pathlib import Path
import unittest


SERVER_PATH = Path(__file__).resolve().parents[1] / "local-deploy" / "server.py"
SPEC = importlib.util.spec_from_file_location("flypig_server", SERVER_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


class ArgumentValidationTests(unittest.TestCase):
    def transport(self, **overrides):
        values = {
            "command": "search-flight",
            "origin": "上海",
            "destination": "丽江",
            "dep_date": "2026-09-25",
            "dep_date_start": None,
            "dep_date_end": None,
            "back_date": None,
            "back_date_start": None,
            "back_date_end": None,
            "journey_type": None,
            "seat_class_name": None,
            "transport_no": None,
            "transfer_city": None,
            "dep_hour_start": None,
            "dep_hour_end": None,
            "arr_hour_start": None,
            "arr_hour_end": 13,
            "total_duration_hour": None,
            "max_price": None,
            "sort_type": 3,
        }
        values.update(overrides)
        return module._transport_arguments(**values)

    def test_builds_exact_argument_vector(self):
        self.assertEqual(
            self.transport(),
            [
                "search-flight", "--origin", "上海", "--destination", "丽江",
                "--dep-date", "2026-09-25", "--arr-hour-end", "13", "--sort-type", "3",
            ],
        )

    def test_shell_metacharacters_remain_one_argument(self):
        arguments = self.transport(destination="丽江; touch /tmp/not-executed")
        index = arguments.index("--destination") + 1
        self.assertEqual(arguments[index], "丽江; touch /tmp/not-executed")

    def test_rejects_invalid_calendar_date(self):
        with self.assertRaisesRegex(ValueError, "real date"):
            self.transport(dep_date="2026-02-30")

    def test_rejects_invalid_hour(self):
        with self.assertRaisesRegex(ValueError, "between 0 and 23"):
            self.transport(arr_hour_end=24)

    def test_rejects_nonpositive_price(self):
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            self.transport(max_price=0)


if __name__ == "__main__":
    unittest.main()
