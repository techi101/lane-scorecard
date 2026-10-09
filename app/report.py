"""Standalone, printable aggregate report; deliberately excludes notes and photos."""
from html import escape

from .scoring import area_summary


def render_report(summary, actions, workspace, lang="en", goal=None):
    def show(value, suffix=""):
        return "Not observed" if value is None else f"{value}{suffix}"

    def change(o):
        if o is None or o["delta"] is None:
            return {"no_baseline": "No baseline", "insufficient_data": "Not observed"}.get(o and o["status"], "—")
        label = {"improved": "Clearly better", "worse": "Clearly worse", "no_clear_change": "No clear change",
                 "too_few_checks": "Too few checks"}[o["status"]]
        shown = o["change"] if o["status"] in ("improved", "worse") else o["delta"]
        return f"{label} ({shown:+g})"

    extra = "".join(f"{label}: <strong>{show(summary['streams'].get(key))}/100</strong> · " for key, label in
                    (("sanitary", "Sanitary bin"), ("special", "Special-care bin")) if summary["streams"].get(key) is not None)
    goal_html = "" if not goal else (
        f"<h2>Community goal (proposal)</h2><p>Target: both bins clean in at least {goal['target_rate']}% of checks "
        f"(minimum {goal['min_checks']} checks) for {goal['weeks']} weeks in a row. "
        f"Weeks met in the last {goal['weeks']}: <strong>{goal['weeks_met']}</strong> · current streak: <strong>{goal['streak']}</strong>.</p>"
        "<p>A community that holds the goal could apply for a shared benefit, for example priority for a public EV charging point "
        "or an e-rickshaw stand. This is a proposed pilot idea, not an existing government scheme. No household gets points or money.</p>")
    source = "DEMO — SIMULATED OBSERVATIONS" if workspace == "demo" else "REAL PILOT OBSERVATIONS"
    area_rows = "".join(
        f"<tr><th>{escape(a['area'])}</th><td>{a['locations']}</td><td>{show(a['score'])}</td><td>{a['checks']}</td><td>{a['hazards']}</td></tr>"
        for a in area_summary(summary)
    )
    rows = "".join(
        f"<tr><th>{escape(f['name'])}{'<br><small>' + escape(f['area']) + '</small>' if f.get('area') else ''}</th><td>{show(f['score'])}</td><td>{f['checks']}</td>"
        f"<td>{show(f['coverage'], '%')}</td><td>{f.get('hazards', 0)}</td><td>{change(f.get('outcome'))}</td></tr>" for f in actions
    )
    steps = "".join(
        f"<article><h3>{escape(a['name'])} · {escape(a['title'])}</h3>"
        f"<p>{escape(a['evidence'])}</p><p><strong>{escape(a['action'][lang])}</strong></p></article>"
        for a in actions
    )
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="referrer" content="no-referrer"><title>Lane Scorecard · Weekly report</title>
<style>body{{font:16px/1.6 system-ui,sans-serif;color:#163f33;max-width:900px;margin:40px auto;padding:0 24px}}
h1{{font:42px Georgia,serif}}h2{{margin-top:36px}}small,p{{color:#52634d}}table{{width:100%;border-collapse:collapse}}
th,td{{text-align:left;padding:12px;border-bottom:1px solid #d4dfca}}article{{border-left:3px solid #819c5a;padding-left:20px;margin:24px 0;break-inside:avoid}}
.source{{font-weight:700;color:#7a5323}}.metrics{{padding:20px;background:#eef3e7}}footer{{margin-top:40px;border-top:1px solid #d4dfca;font-size:13px}}
@media print{{body{{margin:0;max-width:none;font-size:12px}}h1{{font-size:28px}}thead{{display:table-header-group}}}}</style></head>
<body><p class="source">{source}</p><h1>Small checks. Better habits.</h1><p>Lane Scorecard · Weekly operator report<br>
{summary['start']} to {summary['end']} (inclusive)</p>
<div class="metrics">Campus score: <strong>{show(summary['score'])}/100</strong> ·
Both bins clean: <strong>{show(summary['both_clean_rate'], '%')}</strong> ·
Checks: <strong>{summary['checks']}</strong> · Coverage: <strong>{show(summary['coverage'], '%')}</strong><br>
Kept separate during collection: {show(summary['separate_rate'], '%')} ({summary['cart_observed']} observations)<br>
Reports from collection staff: <strong>{summary.get('worker_reports', 0)}</strong> · Dangerous items flagged: <strong>{summary.get('hazards', 0)}</strong><br>
{extra}Deep checks (below the top layer): <strong>{summary.get('deep_checks', 0)}</strong> · hidden wrong items found: <strong>{summary.get('hidden_found', 0)}</strong></div>
<h2>By campus area</h2><table><thead><tr><th>Area</th><th>Locations</th><th>Score /100</th><th>Checks</th><th>Dangerous items</th></tr></thead>
<tbody>{area_rows or '<tr><td colspan="5">No locations have been added.</td></tr>'}</tbody></table>
<h2>Observations by location</h2><table><thead><tr><th>Location</th><th>Score /100</th><th>Checks</th><th>Coverage</th><th>Dangerous items</th><th>Vs last week</th></tr></thead>
<tbody>{rows or '<tr><td colspan="6">No locations have been added.</td></tr>'}</tbody></table>
<h2>Next round: one action per location</h2>{steps or '<p>Add a floor and make the first check with permission.</p>'}
{goal_html}<h2>Reading this report</h2><p>Clean = 100; a few wrong items = 50; mixed = 0. Not seen is excluded.
Each location averages its available bin-type averages; the community score averages scored locations.
Coverage counts observed bins within recorded checks. It does not measure rounds that were never recorded.</p>
<p>Actions are rule-based: dangerous items flagged by collection staff first, then reported collection mixing, then missing observations, then separation at the bin.
Missing evidence is not a clean result. Locations are grouped by area, then listed alphabetically; this is not a public ranking.</p>
<p>"Vs last week" compares only checks where both bins were seen. It calls a change clear only when it is at least 5 points and larger than
two standard errors of the difference: a rule for a small pilot, not a statistical proof. With one check a day, weekly scores often move by about 30 points
without any real change, so most single weeks show no clear change.</p>
<footer><p>This report contains location-level aggregates and guidance. It excludes private notes, photos, access codes and scorecard links.
Share only with the intended community. Exported copies cannot be revoked and do not update after corrections.</p>
<p>{'All demo observations are simulated.' if workspace == 'demo' else 'Pilot observations are entered and confirmed by an operator.'}
An early trend does not prove environmental impact or causation. Use your browser's print command to save as PDF.</p></footer></body></html>"""
