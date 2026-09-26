import unittest
from pathlib import Path

from lab_analyzer_simulator.catalog import Catalog


ROOT = Path(__file__).parents[1]


class ProfileContractTests(unittest.TestCase):
    def test_catalog_is_valid_and_every_fixture_can_run_with_a_matching_profile(self) -> None:
        catalog = Catalog(ROOT)
        self.assertEqual([], catalog.validate())
        for worklist in catalog.worklists.values():
            analyzer_type = worklist.metadata.get("analyzer_type")
            candidates = [profile for profile in catalog.profiles.values() if profile.analyzer_type == analyzer_type]
            self.assertTrue(candidates, worklist.sample_identifier)
            profile = candidates[0]
            for test in worklist.ordered_tests:
                self.assertTrue(test.code)
                self.assertTrue(profile.tests.get(test.code) or test.code not in profile.tests)


if __name__ == "__main__":
    unittest.main()
