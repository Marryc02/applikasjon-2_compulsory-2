"""Command line entry point.

    python -m harness run [--source synthetic|kulturnett] [--offline FILE] [--now ISO]
                          [--classifier auto|llm|baseline]
    python -m harness review [--run-id ID]             # decide on needs-review events
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
from .classify import load_categories
from .publish import apply_review, approve, latest_ready_run
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

    v = sub.add_parser("review", help="go through the needs-review queue of a staged run")
    v.add_argument("--run-id")

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

    if args.cmd == "review":
        run_dir = OUT_DIR / "staging" / args.run_id if args.run_id else latest_ready_run()
        if not run_dir or not (run_dir / "READY_FOR_APPROVAL").exists():
            print("No staged run is waiting for approval.")
            return 1
        try:
            return _review(run_dir)
        except (EOFError, KeyboardInterrupt):
            print("\nReview stopped. Nothing was saved.")
            return 1

    if args.cmd == "approve":
        run_dir = OUT_DIR / "staging" / args.run_id if args.run_id else latest_ready_run()
        if not run_dir or not run_dir.exists():
            print("No staged run is waiting for approval.")
            return 1
        report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
        print(f"Run {run_dir.name}: {json.dumps(report['counts'])}")
        waiting = report["counts"].get("needs_review", 0)
        if waiting:
            print(f"Note: {waiting} event(s) still need review and will NOT be published. "
                  "Run `python -m harness review` first to decide on them.")
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


def _ask_categories(allowed: set[str], current: list[str]) -> list[str]:
    default = [c for c in current if c in allowed][:3]
    while True:
        hint = f" [{', '.join(default)}]" if default else ""
        answer = input(f"  Categories, comma-separated{hint}: ").strip()
        cats = [c.strip() for c in answer.split(",") if c.strip()] if answer else default
        unknown = [c for c in cats if c not in allowed]
        if 1 <= len(cats) <= 3 and not unknown:
            return cats
        print(f"  Choose 1–3 of: {', '.join(sorted(allowed))}")


def _review(run_dir: Path) -> int:
    queue = json.loads((run_dir / "needs_review.json").read_text(encoding="utf-8"))
    if not queue:
        print("Nothing to review: the needs-review queue is empty.")
        return 0
    allowed, _ = load_categories()
    print(f"Run {run_dir.name}: {len(queue)} event(s) need review.\n")
    decisions: dict[str, tuple] = {}
    for i, ev in enumerate(queue, start=1):
        print(f"[{i}/{len(queue)}] {ev['title']}")
        print(f"  When:   {ev['start']}{' (all day)' if ev.get('all_day') else ''}")
        print(f"  Where:  {ev['venue_name']}, {ev['kommune']}")
        print(f"  Price:  {ev.get('price') or '-'}    Organizer: {ev.get('organizer') or '-'}")
        if ev.get("description"):
            print(f"  About:  {ev['description']}")
        print(f"  System: youth={ev.get('youth') or '?'}, categories={ev.get('categories') or []}, "
              f"why review: {', '.join(ev.get('reasons', []))}")
        print(f"  Link:   {ev['source_url']}")
        while True:
            choice = input("  [a]ccept for youth / [n]ot for youth / [d]rop / [s]kip / [q]uit: ").strip().lower()
            if choice in {"a", "n", "d", "s", "q"}:
                break
        if choice == "q":
            break
        if choice == "a":
            decisions[ev["id"]] = ("accept", _ask_categories(allowed, ev.get("categories", [])))
        elif choice == "n":
            decisions[ev["id"]] = ("not_youth",)
        elif choice == "d":
            decisions[ev["id"]] = ("drop",)
        print()
    if not decisions:
        print("No decisions made; nothing changed.")
        return 0
    counts = {k: sum(d[0] == k for d in decisions.values()) for k in ("accept", "not_youth", "drop")}
    print(f"Decisions: {counts['accept']} accept, {counts['not_youth']} not for youth, {counts['drop']} drop.")
    if input("Save these decisions? [y/N] ").strip().lower() != "y":
        print("Not saved.")
        return 1
    result = apply_review(run_dir, decisions, allowed)
    print(f"Saved. {result['still_waiting']} event(s) still waiting. "
          "Next: check the digest and run `python -m harness approve`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
