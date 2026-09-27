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

    def test_derived_and_registered_custom_generators(self) -> None:
        profile = ResultProfile(
            "p",
            "Profile",
            "chemistry",
            {
                "A": {"type": "fixed", "value": "10"},
                "B": {"type": "fixed", "value": "2"},
                "RATIO": {"type": "derived", "sources": ["A", "B"], "operation": "ratio", "decimals": 1},
                "CUSTOM": {"type": "custom", "name": "double", "decimals": 0},
            },
        )
        generator = ResultGenerator(1)
        generator.register_custom("double", lambda test, spec, generated: float(generated["A"]) * 2)
        results = generator.generate_all(
            [OrderedTest("A", "A"), OrderedTest("B", "B"), OrderedTest("RATIO", "Ratio"), OrderedTest("CUSTOM", "Custom")],
            profile,
        )
        self.assertEqual(["10", "2", "5.0", "20"], [result.value for result in results])


if __name__ == "__main__":
    unittest.main()
