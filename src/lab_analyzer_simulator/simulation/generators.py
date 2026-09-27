from __future__ import annotations

import random
from collections.abc import Callable, Iterable
from typing import Any

from ..domain import OrderedTest, ResultProfile, ResultValue


class ResultGenerator:
    def __init__(self, seed: int | None = 42):
        self.random = random.Random(seed)
        self.custom: dict[str, Callable[[OrderedTest, dict[str, Any], dict[str, str]], Any]] = {}

    def register_custom(self, name: str, generator: Callable[[OrderedTest, dict[str, Any], dict[str, str]], Any]) -> None:
        """Register an explicit custom generator; no expression evaluation is used."""
        if not name.strip():
            raise ValueError("custom generator name is required")
        self.custom[name] = generator

    def generate(self, test: OrderedTest, profile: ResultProfile, generated: dict[str, str] | None = None) -> ResultValue:
        generated = generated or {}
        spec: dict[str, Any] = profile.tests.get(test.code, {"type": "range", "min": 0, "max": 100, "decimals": 1})
        kind = spec.get("type", "range")
        if kind == "fixed":
            value = spec.get("value", "0")
        elif kind == "choice":
            value = self.random.choice(spec.get("values", ["NORMAL"]))
        elif kind == "percentage":
            value = self.random.uniform(float(spec.get("min", 0)), float(spec.get("max", 100)))
        elif kind == "derived":
            sources = [float(generated[source]) for source in spec.get("sources", []) if source in generated]
            if not sources:
                raise ValueError(f"derived test {test.code} has no generated source values")
            operation = spec.get("operation", "sum")
            if operation == "sum":
                value = sum(sources)
            elif operation == "difference":
                value = sources[0] - sum(sources[1:])
            elif operation == "ratio":
                if len(sources) != 2 or sources[1] == 0:
                    raise ValueError(f"derived ratio {test.code} requires two non-zero sources")
                value = sources[0] / sources[1]
            elif operation == "product":
                value = 1
                for source in sources:
                    value *= source
            else:
                raise ValueError(f"unsupported derived operation: {operation}")
        elif kind == "custom":
            name = str(spec.get("name", ""))
            if name not in self.custom:
                raise ValueError(f"custom generator is not registered: {name}")
            value = self.custom[name](test, spec, generated)
        else:
            value = self.random.uniform(float(spec.get("min", 0)), float(spec.get("max", 100)))
        if isinstance(value, float):
            value = f"{value:.{int(spec.get('decimals', 1))}f}"
        abnormal = str(spec.get("abnormal_flag", "N"))
        return ResultValue(
            code=test.code,
            name=test.name,
            value=str(value),
            units=str(spec.get("units", test.unit)),
            reference_range=str(spec.get("reference_range", test.reference_range)),
            abnormal_flag=abnormal,
            result_status="F",
        )

    def generate_all(self, tests: Iterable[OrderedTest], profile: ResultProfile) -> list[ResultValue]:
        generated: dict[str, str] = {}
        results: list[ResultValue] = []
        for test in tests:
            result = self.generate(test, profile, generated)
            generated[test.code] = result.value
            results.append(result)
        return results
