"""Transparent scoring. Missing observations never count as clean bins."""
from datetime import date, datetime, timedelta, timezone
from statistics import mean, median

IST = timezone(timedelta(hours=5, minutes=30))
RATINGS = {"clean": 100, "few": 50, "mixed": 0, "unseen": None}
STREAMS = ("bio", "nonbio")
TIPS = {
    "bio": {
        "en": "Keep food scraps in the bio bin. Remove plastic bags and wrappers before putting food waste in it.",
        "hi": "खाने के बचे हिस्से जैविक कूड़ेदान में डालें। प्लास्टिक की थैली और रैपर अलग निकालें।",
    },
    "nonbio": {
        "en": "Empty leftover food into the bio bin. Keep dry packaging in the non-bio bin, following your collector’s instructions.",
        "hi": "बचा हुआ खाना जैविक कूड़ेदान में डालें। सूखी पैकिंग गैर-जैविक कूड़ेदान में रखें और कचरा लेने वाले के निर्देश मानें।",
    },
    "unseen": {
        "en": "Check both bins on the next round. There is not enough observed data for a score yet.",
        "hi": "अगले निरीक्षण में दोनों कूड़ेदान देखें। अभी स्कोर के लिए पर्याप्त जानकारी नहीं है।",
    },
}


def today():
    return datetime.now(IST).date()


def average(values):
    valid = [v for v in values if v is not None]
    return round(mean(valid), 1) if valid else None


def period(end: date):
    return end - timedelta(days=6), end


def summarize(floors, checks, end):
    start, end = period(end)
    rows = [c for c in checks if start.isoformat() <= c["date"] <= end.isoformat()]
    results = []
    for floor in floors:
        own = [c for c in rows if c["floor_id"] == floor["id"]]
        streams = {s: average([RATINGS[c[s]] for c in own]) for s in STREAMS}
        seen = sum(c[s] != "unseen" for c in own for s in STREAMS)
        complete = [c for c in own if all(c[s] != "unseen" for s in STREAMS)]
        results.append({
            "id": floor["id"], "name": floor["name"], "score": average(list(streams.values())),
            "streams": streams, "checks": len(own), "seen": seen,
            "coverage": round(100 * seen / (2 * len(own)), 1) if own else None,
            "complete_checks": len(complete),
            "both_clean": sum(all(c[s] == "clean" for s in STREAMS) for c in complete),
            "hazards": sum(c.get("hazard") is True for c in own),
            "worker_reports": sum(c.get("reporter") == "worker" for c in own),
        })
    scores = [f["score"] for f in results if f["score"] is not None]
    complete = [c for c in rows if all(c[s] != "unseen" for s in STREAMS)]
    clean_count = sum(all(c[s] == "clean" for s in STREAMS) for c in complete)
    cart = [c["kept_separate"] for c in rows if c["kept_separate"] is not None]
    return {
        "start": start.isoformat(), "end": end.isoformat(), "floors": results,
        "score": average(scores), "median": round(median(scores), 1) if scores else None,
        "checks": len(rows), "active_floors": len(scores), "total_floors": len(floors),
        "both_clean_rate": round(clean_count / len(complete) * 100, 1) if complete else None,
        "both_clean_count": clean_count, "complete_checks": len(complete),
        "separate_rate": round(sum(cart) / len(cart) * 100, 1) if cart else None,
        "cart_observed": len(cart),
        "hazards": sum(c.get("hazard") is True for c in rows),
        "worker_reports": sum(c.get("reporter") == "worker" for c in rows),
        "coverage": round(sum(c[s] != "unseen" for c in rows for s in STREAMS) / (2 * len(rows)) * 100, 1) if rows else None,
        "streams": {s: average([RATINGS[c[s]] for c in rows]) for s in STREAMS},
    }


def card_data(summary, floor_id):
    floor = next(f for f in summary["floors"] if f["id"] == floor_id)
    observed = {s: value for s, value in floor["streams"].items() if value is not None}
    weakest = min(observed, key=observed.get) if observed else "unseen"
    return {
        **floor, "median": summary["median"], "compared_floors": summary["active_floors"],
        "start": summary["start"], "end": summary["end"], "tip": TIPS[weakest],
        "weakest": weakest, "tip_source": "Reviewed two-bin pilot guidance (rule-based)",
    }
