from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import load_settings
from .simulation.engine import SimulationEngine
from .web.server import serve


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Standalone HL7/MLLP laboratory analyzer simulator")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="project root containing profiles/ and fixtures/")
    parser.add_argument("--config", type=Path, help="optional JSON configuration file")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    web = commands.add_parser("web", help="start the browser control panel and REST API")
    web.add_argument("--host", default=None)
    web.add_argument("--port", type=int, default=None)
    query = commands.add_parser("query", help="load a fixture worklist or query a live host")
    query.add_argument("sample_identifier")
    query.add_argument("--scenario", default="normal")
    run = commands.add_parser("run", help="run a result profile for a sample")
    run.add_argument("--sample", dest="sample_identifier", default=None)
    run.add_argument("--profile", dest="profile_id", default="cbc-normal")
    run.add_argument("--scenario", default="normal")
    commands.add_parser("validate", help="validate all profile and fixture files")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings(args.config)
    engine = SimulationEngine(args.root, settings)
    if args.command == "validate":
        errors = engine.catalog.validate()
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        print(f"Validated {len(engine.catalog.worklists)} worklists and {len(engine.catalog.profiles)} result profiles.")
        return 0
    if args.command == "web":
        serve(engine, args.host or settings.bind_host, args.port or settings.web_port)
        return 0
    if args.command == "query":
        worklist = engine.query(args.sample_identifier, args.scenario)
        print(json.dumps(engine._worklist_dict(worklist), indent=2))
        return 0
    if args.command == "run":
        run = engine.run(args.profile_id, args.sample_identifier, args.scenario)
        print(json.dumps({field: getattr(run, field) for field in run.__slots__}, indent=2, default=str))
        print(engine.messages[-2]["message"])
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
