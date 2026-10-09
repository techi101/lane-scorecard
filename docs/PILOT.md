# Run an honest small pilot

## Before collecting

Get permission from the campus/space operator. Agree which shared bins can be checked, when observations can happen, who sees feedback, and when data should be deleted. Use location labels only. Do not photograph people, room numbers, documents or other identifying details. Do not handle hazardous waste to improve a photo.

The app supports the site's existing bio/non-bio arrangement. It does not certify national waste-rule compliance, and it cannot verify how collectors actually process waste later.

## Observation sheet

If the app is unavailable, record these fields on paper, then enter the original observation date later:

| Date | Round | Location | Bio | Non-bio | Kept separate on collection? | Note |
|---|---|---|---|---|---|---|
| Actual date | Morning/evening | Consented location label | Clean/few/mixed/not seen | Same choices | Yes/no/not observed | No personal information |

Inspect the same locations at comparable times. Empty or obscured bins should be “not seen”, rather than assumed clean. Missing entire rounds are not automatically represented in the app, so keep a separate record of planned vs completed rounds.

Collect a baseline round, share the first scorecard, then repeat. Report counts, coverage and dates with any percentage. For example: “Both bins were clean in X of Y fully observed checks.” Do not turn a three-day before/after change into a causal claim.

## Evaluate the photo helper

The dashboard compares the AI suggestion with the operator's final rating. Because the operator may have seen the suggestion, this is **not a blind independent evaluation**.

For a stronger evaluation:

1. Collect permitted photos from actual pilot bins, covering both streams and all rating classes.
2. Two teammates label them independently, without seeing model predictions.
3. Resolve disagreements and document the rubric. Keep the held-out labels unchanged after running the model.
4. Create a JSONL file: one JSON object per line, using paths relative to that file.

```json
{"image":"photos/bin-01.jpg","stream":"bio","label":"few"}
{"image":"photos/bin-02.jpg","stream":"nonbio","label":"mixed"}
```

Validate without model calls:

```powershell
.venv\Scripts\python.exe scripts/evaluate_photos.py path/to/labels.jsonl --validate-only
```

After connecting AWS and explicitly enabling AI, run the same command without `--validate-only`. It will make billable Bedrock calls and save per-stream counts, agreement, failures and a confusion table. Keep photographs and labels outside public source control unless you have suitable permission.

No real evaluation images or performance results are bundled with this app. Do not use browser-test images as environmental evidence.
