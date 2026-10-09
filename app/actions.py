"""Explainable follow-up actions derived only from observed weekly evidence."""
from math import sqrt
from statistics import mean, variance

from .scoring import ALL_STREAMS, ISSUES, RATINGS, STREAM_LABELS, STREAMS, TIPS, top_issue


CHANGE_POINTS = 5
MIN_CHECKS = 3


def check_values(rows):
    """One 0-100 value per check where BOTH bins were seen: the mean of the two bins.

    Checks with an unseen bin are left out so every value measures the same thing. Mixing
    one-bin and two-bin checks would make the comparison depend on which bin was missed.
    """
    return [sum(RATINGS[c[s]] for s in STREAMS) / len(STREAMS)
            for c in rows if all(RATINGS[c[s]] is not None for s in STREAMS)]


def outcome(floor, previous_floor, current=(), earlier=()):
    """Has the floor clearly changed since last week, by our rule?

    `delta` is the change in the displayed floor score, shown as a description only.
    The judgement uses ONE statistic for both change and variation: the per-check values of
    checks where both bins were seen (`current`, `earlier`). A change is claimed only when the
    difference of their means clears CHANGE_POINTS and two standard errors. This is a product
    rule for a small pilot, not a statistical proof: repeated checks of one floor are not
    independent samples.
    """
    if floor["score"] is None:
        return {"status": "insufficient_data", "delta": None}
    if previous_floor is None or previous_floor["score"] is None:
        return {"status": "no_baseline", "delta": None}
    delta = round(floor["score"] - previous_floor["score"], 1)
    counts = {"compared_checks": [len(earlier), len(current)]}
    if len(current) < MIN_CHECKS or len(earlier) < MIN_CHECKS:
        return {"status": "too_few_checks", "delta": delta, **counts}
    change = mean(current) - mean(earlier)
    noise = 2 * sqrt(variance(current) / len(current) + variance(earlier) / len(earlier))
    if abs(change) < max(CHANGE_POINTS, noise):
        status = "no_clear_change"
    else:
        status = "improved" if change > 0 else "worse"
    return {"status": status, "delta": delta, "change": round(change, 1), "noise": round(noise, 1), **counts}


def weekly_actions(summary, checks, previous=None):
    rows = [c for c in checks if summary["start"] <= c["date"] <= summary["end"]]
    previous_floors = {f["id"]: f for f in previous["floors"]} if previous else {}
    earlier_rows = [c for c in checks if previous["start"] <= c["date"] <= previous["end"]] if previous else []
    actions = []
    for floor in sorted(summary["floors"], key=lambda f: f["name"].casefold()):
        own = [c for c in rows if c["floor_id"] == floor["id"]]
        mixed_collection = sum(c["kept_separate"] is False for c in own)
        missing = floor["expected"] - floor["seen"]
        observed = {s: floor["streams"][s] for s in ALL_STREAMS if floor["streams"][s] is not None}
        if floor["hazards"]:
            # Worker safety comes before every segregation goal.
            kind, title = "safety", "Make the bins safe to handle"
            evidence = f"Workers flagged a dangerous item (glass, blade, needle or unwrapped sanitary waste) in {floor['hazards']} collection(s)."
            action = {"en": "Ask residents to wrap broken glass and blades in paper and mark them, and to wrap sanitary waste separately. Make sure collection staff have gloves.",
                      "hi": "निवासियों से कहें कि टूटा काँच और ब्लेड कागज़ में लपेटकर उस पर निशान लगाएँ, और सैनिटरी कचरा अलग लपेटें। सफ़ाई कर्मचारियों के पास दस्ताने हों।"}
        elif not floor["checks"]:
            kind, title = "observe", "Make the first check"
            evidence = "No checks were recorded for this location in the selected week."
            action = {"en": "Visit both bins with permission and record their visible condition.",
                      "hi": "अनुमति लेकर दोनों कूड़ेदान देखें और उनकी दिखाई देने वाली स्थिति दर्ज करें।"}
        elif mixed_collection:
            kind, title = "collection", "Keep collection separate"
            evidence = f"Waste was reported mixed during {mixed_collection} collection observation(s)."
            action = {"en": "Discuss a separate collection round or separate containers with the collection team, then observe the next pickup.",
                      "hi": "कचरा लेने वाली टीम से अलग डिब्बों या अलग चक्कर की बात करें। अगली बार देखें कि कचरा अलग रखा गया या नहीं।"}
        elif missing:
            kind, title = "observe", "Fill the observation gaps"
            evidence = f"{missing} of {floor['expected']} bin ratings were marked not seen."
            action = {"en": "Check both bins on the next round. Keep missing observations visible when sharing this week's score.",
                      "hi": "अगले निरीक्षण में दोनों कूड़ेदान देखें। इस हफ़्ते का स्कोर साझा करते समय अधूरे निरीक्षण भी बताएँ।"}
        elif observed and min(observed.values()) < 100:
            weakest = min(observed, key=observed.get)
            kind, title = "segregation", "Improve separation at the bin"
            issue = top_issue(floor)
            if issue:
                # A tagged mistake gives specific advice instead of a generic bin tip.
                evidence = f"{ISSUES[issue]['what']['en']} Seen in {floor['issues'][issue]} of {floor['checks']} check(s)."
                action = ISSUES[issue]["fix"]
            else:
                evidence = f"The {STREAM_LABELS[weakest]} bin averaged {observed[weakest]:g}/100 across recorded checks."
                action = TIPS[weakest]
        else:
            kind, title = "maintain", "Keep checking consistently"
            evidence = f"Every rated bin was clean in all {floor['checks']} recorded check(s)."
            action = {"en": "Keep the same checking routine and share the location's feedback. Confirm separation during collection when possible.",
                      "hi": "नियमित निरीक्षण जारी रखें और जगह का फ़ीडबैक साझा करें। संभव हो तो देखें कि उठाते समय कचरा अलग रहता है।"}
        actions.append({"floor_id": floor["id"], "name": floor["name"], "kind": kind,
                        "title": title, "evidence": evidence, "action": action,
                        "checks": floor["checks"], "coverage": floor["coverage"], "score": floor["score"],
                        "hazards": floor["hazards"], "worker_reports": floor["worker_reports"],
                        "outcome": outcome(floor, previous_floors.get(floor["id"]), check_values(own),
                                           check_values([c for c in earlier_rows if c["floor_id"] == floor["id"]]))})
    return actions
