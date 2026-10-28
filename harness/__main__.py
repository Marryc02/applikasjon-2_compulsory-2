"""Command line entry point.

    python -m harness run [--source synthetic|kulturnett] [--offline FILE] [--now ISO]
                          [--classifier auto|llm|baseline]
    python -m harness approve [--run-id ID] [--yes]
    python -m harness synth --now ISO --out FILE      # save a synthetic fixture
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from .config import OSLO, OUT_DIR, load_config, load_dotenv
from .pipeline import run
from .publish import approve, latest_ready_run
from .sources import SourceUnavailable
from .sources.synthetic import generate


def _parse_now(value: str | None) -> datetime:
    now = datetime.fromisoformat(value) if value else datetime.now(OSLO)
    return now if now.tzinfo else now.replace(tzinfo=OSLO)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="harness", description="Hamar youth events pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="collect, validate, classify and stage events")
    r.add_argument("--source", choices=["synthetic", "kulturnett"],
                   help="where to collect events (default: [source] in config.toml)")
    r.add_argument("--offline", metavar="FILE", help="replay saved records instead of collecting")
    r.add_argument("--now", help="pretend the run happens at this time (ISO 8601), for reproducible runs")
    r.add_argument("--classifier", choices=["auto", "llm", "baseline"], default="auto")
    r.add_argument("--config", type=Path)

    a = sub.add_parser("approve", help="publish a staged run after human review")
    a.add_argument("--run-id")
    a.add_argument("--yes", action="store_true", help="skip the confirmation question")

    s = sub.add_parser("synth", help="write synthetic records (with expected labels) to a file")
    s.add_argument("--now", required=True, help="run time the dates are relative to (ISO 8601)")
    s.add_argument("--out", required=True, type=Path)

    args = p.parse_args(argv)
    load_dotenv()

    if args.cmd == "run":
        cfg = load_config(args.config)
        try:
            report = run(cfg, _parse_now(args.now), args.source or cfg["source"]["default"],
                         Path(args.offline) if args.offline else None, args.classifier)
        except SourceUnavailable as e:
            print(f"Source unavailable: {e}")
            return 3
        return 2 if report["halted"] else 0

    if args.cmd == "approve":
        run_dir = OUT_DIR / "staging" / args.run_id if args.run_id else latest_ready_run()
        if not run_dir or not run_dir.exists():
            print("No staged run is waiting for approval.")
            return 1
        report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
        print(f"Run {run_dir.name}: {json.dumps(report['counts'])}")
        print("Review these before approving:")
        for name in ("digest.md", "events.json", "needs_review.json", "not_for_youth.json", "rejected.json"):
            print(f"  {run_dir / name}")
        if not args.yes and input("Publish this run? [y/N] ").strip().lower() != "y":
            print("Not published.")
            return 1
        print(f"Published to {approve(run_dir)}")
        return 0

    if args.cmd == "synth":
        now = _parse_now(args.now)
        data = {"_comment": f"SYNTHETIC events in the ASSUMED Kulturnett format, generated for {now.isoformat()}. "
                            "Not real events. '_expected' = the outcome a correct pipeline should produce.",
                "events": generate(now)}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {len(data['events'])} synthetic records to {args.out}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
