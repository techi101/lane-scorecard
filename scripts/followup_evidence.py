"""Re-runnable week-over-week follow-up table on the app's simulated demo data.

Run: python scripts/followup_evidence.py
Writes docs/FOLLOWUP_EVIDENCE.md. Every row is SIMULATED; nothing here is a real observation.
"""
from collections import Counter
from datetime import timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.actions import CHANGE_POINTS, weekly_actions  # noqa: E402
from app.main import seed_demo  # noqa: E402
from app.scoring import summarize, today  # noqa: E402


class MemoryStore:
    """Just enough of the storage interface for seed_demo."""

    def __init__(self):
        self.rows = {}

    def get(self, pk, sk):
        return self.rows.get((pk, sk))

    def put(self, pk, sk, value, **_):
        self.rows[(pk, sk)] = value

    def put_many(self, pk, values):
        for value in values:
            self.rows[(pk, value["id"])] = value

    def list(self, pk):
        return [v for (p, _), v in self.rows.items() if p == pk]


def show(value):
    return "–" if value is None else f"{value:g}"


def main():
    store = MemoryStore()
    seed_demo(store)
    floors, checks = store.list("demo:floors"), store.list("demo:checks")
    end = today()
    weeks = [end - timedelta(days=7 * w) for w in (2, 1, 0)]
    lines = [
        "# Follow-up evidence (simulated)",
        "",
        "**All data below is SIMULATED** by the app's demo generator (`seed_demo`, fixed seed). "
        "It shows how the follow-up check behaves; it is not evidence of real waste reduction.",
        "",
        "The score columns are the displayed floor scores. The judgement compares only checks where both bins were seen: "
        f"a change is called clear only when it is at least {CHANGE_POINTS} points and larger than two standard errors (the noise band). "
        "This is a rule for a small pilot, not a statistical proof. "
        f"Regenerate with `python scripts/followup_evidence.py`. Generated for weeks ending {', '.join(w.isoformat() for w in weeks)}.",
        "",
        "| Floor | " + " | ".join(f"Score, week to {w.isoformat()}" for w in weeks) + " | Action this week | Outcome vs last week |",
        "|---|" + "---|" * (len(weeks) + 2),
    ]
    summaries = [summarize(floors, checks, w) for w in weeks]
    actions = weekly_actions(summaries[-1], checks, summaries[-2])
    tally = Counter()
    for action in actions:
        scores = [next(f["score"] for f in s["floors"] if f["id"] == action["floor_id"]) for s in summaries]
        o = action["outcome"]
        tally[o["status"]] += 1
        delta = "" if o["delta"] is None else f" (score {o['delta']:+g}"
        delta += f"; both-bin checks {o['change']:+g}, noise ±{o['noise']:g})" if "noise" in o else (")" if delta else "")
        lines.append(f"| {action['name']} | " + " | ".join(show(s) for s in scores) + f" | {action['title']} | {o['status']}{delta} |")
    lines += ["", "Outcome counts: " + ", ".join(f"{k} {v}" for k, v in sorted(tally.items())), ""]
    out = ROOT / "docs" / "FOLLOWUP_EVIDENCE.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
