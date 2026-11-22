import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import server


class TestJarvisServer(unittest.TestCase):
    def test_extract_search_terms_variations(self):
        cases = [
            ("find emails from Glassdoor", "Glassdoor"),
            ("search emails about invoice", "invoice"),
            ("show me emails from John Doe", "John Doe"),
            ("summarize emails from Amazon", "Amazon"),
            ("what are my emails regarding project deadline", "project deadline"),
        ]
        for query, expected in cases:
            cleaned = server.extract_search_terms(query)
            self.assertEqual(cleaned, expected, f"Failed on: {query}")

    def test_telemetry_structure(self):
        data = server.get_telemetry()
        self.assertIn("host_platform", data)
        self.assertIn("engine_version", data)
        self.assertIn("cpu_utilization", data)
        self.assertIn("total_emails_indexed", data)
        self.assertIn("timestamp", data)

    def test_html_dashboard_exists(self):
        index_file = Path(__file__).parent.parent / "index.html"
        self.assertTrue(index_file.exists(), "index.html does not exist in root directory")
        content = index_file.read_text(encoding="utf-8")
        self.assertIn("J.A.R.V.I.S.", content)
        self.assertIn("Google Identity Services", content)


if __name__ == "__main__":
    unittest.main()
