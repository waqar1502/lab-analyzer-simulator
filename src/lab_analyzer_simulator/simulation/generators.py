from __future__ import annotations

import random
from typing import Any

from ..domain import OrderedTest, ResultProfile, ResultValue


class ResultGenerator:
    def __init__(self, seed: int | None = 42):
        self.random = random.Random(seed)

    def generate(self, test: OrderedTest, profile: ResultProfile) -> ResultValue:
        spec: dict[str, Any] = profile.tests.get(test.code, {"type": "range", "min": 0, "max": 100, "decimals": 1})
        kind = spec.get("type", "range")
        if kind == "fixed":
            value = spec.get("value", "0")
        elif kind == "choice":
            value = self.random.choice(spec.get("values", ["NORMAL"]))
        elif kind == "percentage":
            value = self.random.uniform(float(spec.get("min", 0)), float(spec.get("max", 100)))
        elif kind == "derived":
            value = self.random.uniform(float(spec.get("min", 0)), float(spec.get("max", 100)))
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

