import unittest

from lab_analyzer_simulator.domain import OrderedTest, ResultProfile
from lab_analyzer_simulator.simulation.generators import ResultGenerator


class GeneratorTests(unittest.TestCase):
    def test_seeded_range_generator_is_reproducible(self) -> None:
        profile = ResultProfile("p", "Profile", "chemistry", {"X": {"type": "range", "min": 1, "max": 2, "decimals": 2}})
        test = OrderedTest("X", "Example")
        self.assertEqual(ResultGenerator(7).generate(test, profile).value, ResultGenerator(7).generate(test, profile).value)

    def test_choice_and_fixed_generators(self) -> None:
        profile = ResultProfile(
            "p",
            "Profile",
            "generic",
            {"FIXED": {"type": "fixed", "value": "POSITIVE"}, "CHOICE": {"type": "choice", "values": ["A"]}},
        )
        generator = ResultGenerator(1)
        self.assertEqual("POSITIVE", generator.generate(OrderedTest("FIXED", "Fixed"), profile).value)
        self.assertEqual("A", generator.generate(OrderedTest("CHOICE", "Choice"), profile).value)


if __name__ == "__main__":
    unittest.main()
