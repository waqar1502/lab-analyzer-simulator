from __future__ import annotations

import json
from pathlib import Path

from .domain import ResultProfile, Worklist


class Catalog:
    def __init__(self, root: Path):
        self.root = root
        self.worklists: dict[str, Worklist] = {}
        self.profiles: dict[str, ResultProfile] = {}
        self.analyzers: dict[str, dict] = {}
        self.reload()

    def reload(self) -> None:
        self.worklists.clear()
        self.profiles.clear()
        self.analyzers.clear()
        for path in sorted((self.root / "fixtures" / "worklists").glob("*.json")):
            value = json.loads(path.read_text(encoding="utf-8"))
            worklist = Worklist.from_dict(value)
            self.worklists[worklist.sample_identifier] = worklist
        for path in sorted((self.root / "profiles" / "results").glob("*.json")):
            value = json.loads(path.read_text(encoding="utf-8"))
            profile = ResultProfile(
                profile_id=str(value["id"]),
                name=str(value["name"]),
                analyzer_type=str(value.get("analyzer_type", "generic")),
                tests=dict(value.get("tests", {})),
                processing_seconds=float(value.get("processing_seconds", 0)),
                processing_jitter_seconds=float(value.get("processing_jitter_seconds", 0)),
            )
            self.profiles[profile.profile_id] = profile
        for path in sorted((self.root / "profiles" / "analyzers").glob("*.json")):
            value = json.loads(path.read_text(encoding="utf-8"))
            self.analyzers[str(value["id"])] = value

    def get_worklist(self, sample_identifier: str) -> Worklist | None:
        return self.worklists.get(sample_identifier)

    def get_profile(self, profile_id: str) -> ResultProfile:
        try:
            return self.profiles[profile_id]
        except KeyError as error:
            raise KeyError(f"Unknown result profile: {profile_id}") from error

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.worklists:
            errors.append("no worklist fixtures found")
        if not self.profiles:
            errors.append("no result profiles found")
        for sample, worklist in self.worklists.items():
            if not worklist.ordered_tests:
                errors.append(f"worklist {sample} has no ordered tests")
        for profile_id, profile in self.profiles.items():
            if not profile.tests:
                errors.append(f"result profile {profile_id} has no test generators")
        return errors

