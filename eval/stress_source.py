"""Stress test 2 (dependency failure): run the pipeline on each broken source
input in fixtures/testing/stress/ and report what happened.

    python -m eval.stress_source

For each case it records: did the run complete, halt (kill switch) or crash;
was anything staged for approval (could a reviewer publish it?); and the
message a person would see. Nothing is ever published (publishing needs
`approve`). Results go to out/stress/<timestamp>.json.

Safe behaviour = nothing staged for approval from a broken source, and a
message a person can understand. A crash stages nothing either, but shows a
raw Python error instead of an explanation.
"""
from __future__ import annotations

import io
import json
import sys
import traceback
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path

from harness.config import OSLO, OUT_DIR, ROOT, load_config
from harness.pipeline import run
from harness.sources import SourceFormatError, SourceUnavailable

NOW = datetime(2026, 11, 2, 8, 0, tzinfo=OSLO)
STRESS_DIR = ROOT / "fixtures" / "testing" / "stress"


def run_case(name: str, base: Path, offline_file: Path | None = None, source: str = "synthetic") -> dict:
    log = io.StringIO()
    result = {"case": name}
    try:
        with redirect_stdout(log):
            report = run(load_config(), NOW, source=source, offline_file=offline_file,
                         classifier="baseline", base=base, log=print)
    except SourceFormatError as e:
        result.update(status="source_unreadable", message=str(e), staged_for_approval=False)
    except SourceUnavailable as e:
        result.update(status="source_unavailable", message=str(e), staged_for_approval=False)
    except Exception as e:  # what a crash looks like to the person running it
        result.update(status="CRASH", message=f"{type(e).__name__}: {e}",
                      traceback=traceback.format_exc(limit=3), staged_for_approval=False)
    else:
        run_dir = base / "staging" / report["run_id"]
        staged = (run_dir / "READY_FOR_APPROVAL").exists()
        result.update(
            status="halted" if report["halted"] else "completed",
            message=report["halted_reason"] or "",
            counts=report["counts"],
            staged_for_approval=staged,
            accepted_staged=report["counts"]["accepted"] if staged else 0,
        )
    result["log"] = log.getvalue().strip().splitlines()
    return result


def main() -> int:
    stamp = datetime.now(OSLO).strftime("%Y%m%d-%H%M%S")
    out = OUT_DIR / "stress" / stamp
    cases = sorted(STRESS_DIR.glob("*.json"))
    if not cases:
        print("No inputs in fixtures/testing/stress/. Run: python -m eval.make_stress_inputs")
        return 2

    results = [run_case(p.stem, out / p.stem, offline_file=p) for p in cases]
    results.append(run_case("10_source_unreachable", out / "unreachable", source="kulturnett"))

    print(f"{'Case':28} {'Status':19} Staged?")
    print("-" * 100)
    for r in results:
        staged = "YES" if r["staged_for_approval"] else "no"
        if r["staged_for_approval"]:
            staged += f" ({r['accepted_staged']} events, waiting for a human)"
        print(f"{r['case']:28} {r['status']:19} {staged}")
        if r["message"]:
            print(f"{'':28} -> {r['message']}")
    crashes = [r for r in results if r["status"] == "CRASH"]
    for r in crashes:
        print(f"\n{r['case']}: what the person sees:\n{r['traceback']}")

    out.mkdir(parents=True, exist_ok=True)
    out_file = OUT_DIR / "stress" / f"{stamp}.json"
    out_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nFull results: {out_file}")
    return 1 if crashes else 0


if __name__ == "__main__":
    sys.exit(main())
