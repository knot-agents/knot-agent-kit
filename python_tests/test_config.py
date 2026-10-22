from __future__ import annotations

from pathlib import Path
import stat
import tempfile
import unittest

from knot_agent_kit.config import (
    default_config_path,
    read_config,
    resolved_settings,
    write_config,
)


class ConfigTests(unittest.TestCase):
    def test_unix_path_matches_node_client(self):
        path = default_config_path({}, platform="posix", home=Path("/tmp/home"))
        self.assertEqual(path, Path("/tmp/home/.config/knot/agent-kit.json"))

    def test_round_trip_and_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "knot" / "agent-kit.json"
            write_config({"token": "secret", "checkpoint": "next"}, path)
            self.assertEqual(read_config(path)["token"], "secret")
            if path.stat().st_mode:
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_environment_overrides_saved_values(self):
        settings = resolved_settings(
            {"baseUrl": "https://saved.example", "token": "saved"},
            {"KNOT_BASE_URL": "https://env.example/", "KNOT_AGENT_TOKEN": "env"},
        )
        self.assertEqual(settings["base_url"], "https://env.example")
        self.assertEqual(settings["token"], "env")


if __name__ == "__main__":
    unittest.main()
