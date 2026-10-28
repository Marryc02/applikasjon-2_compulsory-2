"""Command line entry point.

    python -m harness run [--offline [FILE]] [--now ISO] [--classifier auto|llm|baseline]
    python -m harness approve [--run-id ID] [--yes]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from .config import OUT_DIR, OSLO, ROOT, load_config, load_dotenv
from .pipeline import run
from .publish import approve, latest_ready_run

DEFAULT_FIXTURE = ROOT / "fixtures" / "ticketmaster_sample_SYNTHETIC.json"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="harness", description="Hamar youth events pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="collect, validate, classify and stage events")
    r.add_argument("--offline", nargs="?", const=str(DEFAULT_FIXTURE), metavar="FILE",
                   help="use a saved Ticketmaster response instead of the live API")
    r.add_argument("--now", help="pretend the run happens at this time (ISO 8601), for reproducible runs")
    r.add_argument("--classifier", choices=["auto", "llm", "baseline"], default="auto")
    r.add_argument("--config", type=Path)

    a = sub.add_parser("approve", help="publish a staged run after human review")
    a.add_argument("--run-id")
    a.add_argument("--yes", action="store_true", help="skip the confirmation question")

    args = p.parse_args(argv)
    load_dotenv()

    if args.cmd == "run":
        now = datetime.fromisoformat(args.now) if args.now else datetime.now(OSLO)
        if now.tzinfo is None:
            now = now.replace(tzinfo=OSLO)
        report = run(load_config(args.config), now, Path(args.offline) if args.offline else None, args.classifier)
        return 2 if report["halted"] else 0

    if args.cmd == "approve":
        run_dir = OUT_DIR / "staging" / args.run_id if args.run_id else latest_ready_run()
        if not run_dir or not run_dir.exists():
            print("No staged run is waiting for approval.")
            return 1
        report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
        print(f"Run {run_dir.name}: {json.dumps(report['counts'])}")
        print(f"Review these before approving:\n  {run_dir / 'digest.md'}\n  {run_dir / 'events.json'}\n"
              f"  {run_dir / 'needs_review.json'}\n  {run_dir / 'rejected.json'}")
        if not args.yes and input("Publish this run? [y/N] ").strip().lower() != "y":
            print("Not published.")
            return 1
        public = approve(run_dir)
        print(f"Published to {public}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
