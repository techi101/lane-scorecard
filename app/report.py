"""Standalone, printable aggregate report; deliberately excludes notes and photos."""
from html import escape

from .scoring import area_summary


def render_report(summary, actions, workspace, lang="en", goal=None):
    def t(en, hi):
        return hi if lang == "hi" else en

    def show(value, suffix=""):
        return t("Not observed", "नहीं देखा गया") if value is None else f"{value}{suffix}"

    def change(o):
        if o is None or o["delta"] is None:
            return {"no_baseline": t("No baseline", "पिछला स्कोर नहीं"), "insufficient_data": t("Not observed", "नहीं देखा गया")}.get(o and o["status"], "—")
        label = {"improved": t("Clearly better", "स्पष्ट सुधार"), "worse": t("Clearly worse", "स्पष्ट गिरावट"), "no_clear_change": t("No clear change", "स्पष्ट बदलाव नहीं"),
                 "too_few_checks": t("Too few checks", "बहुत कम निरीक्षण")}[o["status"]]
        shown = o["change"] if o["status"] in ("improved", "worse") else o["delta"]
        return f"{label} ({shown:+g})"

    extra = "".join(f"{label}: <strong>{show(summary['streams'].get(key))}/100</strong> · " for key, label in
                    (("sanitary", t("Sanitary bin", "सैनिटरी डिब्बा")), ("special", t("Special-care bin", "विशेष देखभाल डिब्बा"))) if summary["streams"].get(key) is not None)
    goal_html = "" if not goal else (
        f"<h2>Community goal (proposal)</h2><p>Target: both bins clean in at least {goal['target_rate']}% of checks "
        f"(minimum {goal['min_checks']} checks) for {goal['weeks']} weeks in a row. "
        f"Weeks met in the last {goal['weeks']}: <strong>{goal['weeks_met']}</strong> · current streak: <strong>{goal['streak']}</strong>.</p>"
        "<p>A community that holds the goal could apply for a shared benefit, for example priority for a public EV charging point "
        "or an e-rickshaw stand. This is a proposed pilot idea, not an existing government scheme. No household gets points or money.</p>")
    if goal and lang == "hi":
        goal_html = (f"<h2>सामुदायिक लक्ष्य (प्रस्ताव)</h2><p>लक्ष्य: लगातार {goal['weeks']} सप्ताह तक कम-से-कम "
                     f"{goal['target_rate']}% निरीक्षणों में दोनों डिब्बे साफ़ (न्यूनतम {goal['min_checks']} निरीक्षण)। "
                     f"पिछले {goal['weeks']} सप्ताह में लक्ष्य पूरा करने वाले सप्ताह: <strong>{goal['weeks_met']}</strong> · "
                     f"वर्तमान लगातार सप्ताह: <strong>{goal['streak']}</strong>।</p>"
                     "<p>लक्ष्य बनाए रखने वाला समुदाय सार्वजनिक EV चार्जिंग या ई-रिक्शा स्टैंड जैसी साझा सुविधा के लिए प्राथमिकता माँग सकता है। "
                     "यह पायलट का प्रस्ताव है, मौजूदा सरकारी योजना नहीं। किसी घर को अंक या पैसा नहीं मिलता।</p>")
    source = t("DEMO — SIMULATED OBSERVATIONS", "डेमो — काल्पनिक निरीक्षण") if workspace == "demo" else t("REAL PILOT OBSERVATIONS", "वास्तविक पायलट निरीक्षण")
    area_rows = "".join(
        f"<tr><th>{escape(a['area'])}</th><td>{a['locations']}</td><td>{show(a['score'])}</td><td>{a['checks']}</td><td>{a['hazards']}</td></tr>"
        for a in area_summary(summary)
    )
    rows = "".join(
        f"<tr><th>{escape(f['name'])}{'<br><small>' + escape(f['area']) + '</small>' if f.get('area') else ''}</th><td>{show(f['score'])}</td><td>{f['checks']}</td>"
        f"<td>{show(f['coverage'], '%')}</td><td>{f.get('hazards', 0)}</td><td>{change(f.get('outcome'))}</td></tr>" for f in actions
    )
    steps = "".join(
        f"<article><h3>{escape(a['name'])} · {escape(a.get('title_hi', a['title']) if lang == 'hi' else a['title'])}</h3>"
        f"<p>{escape(a.get('evidence_hi', a['evidence']) if lang == 'hi' else a['evidence'])}</p><p><strong>{escape(a['action'][lang])}</strong></p></article>"
        for a in actions
    )
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="referrer" content="no-referrer"><title>Lane Scorecard · {t('Weekly report', 'साप्ताहिक रिपोर्ट')}</title>
<style>body{{font:16px/1.6 system-ui,sans-serif;color:#163f33;max-width:900px;margin:40px auto;padding:0 24px}}
h1{{font:42px Georgia,serif}}h2{{margin-top:36px}}small,p{{color:#52634d}}table{{width:100%;border-collapse:collapse}}
th,td{{text-align:left;padding:12px;border-bottom:1px solid #d4dfca}}article{{border-left:3px solid #819c5a;padding-left:20px;margin:24px 0;break-inside:avoid}}
.source{{font-weight:700;color:#7a5323}}.metrics{{padding:20px;background:#eef3e7}}footer{{margin-top:40px;border-top:1px solid #d4dfca;font-size:13px}}
@media print{{body{{margin:0;max-width:none;font-size:12px}}h1{{font-size:28px}}thead{{display:table-header-group}}}}</style></head>
<body><p class="source">{source}</p><h1>{t('Small checks. Better habits.', 'छोटे निरीक्षण। बेहतर आदतें।')}</h1><p>Lane Scorecard · {t('Weekly operator report', 'संचालक की साप्ताहिक रिपोर्ट')}<br>
{summary['start']} {t('to', 'से')} {summary['end']} {t('(inclusive)', '(दोनों दिन सहित)')}</p>
<div class="metrics">{t('Campus score', 'परिसर का स्कोर')}: <strong>{show(summary['score'])}/100</strong> ·
{t('Both bins clean', 'दोनों डिब्बे साफ़')}: <strong>{show(summary['both_clean_rate'], '%')}</strong> ·
{t('Checks', 'निरीक्षण')}: <strong>{summary['checks']}</strong> · {t('Coverage', 'कवरेज')}: <strong>{show(summary['coverage'], '%')}</strong><br>
{t('Kept separate during collection', 'संग्रह में अलग रखा')}: {show(summary['separate_rate'], '%')} ({summary['cart_observed']} {t('observations', 'निरीक्षण')})<br>
{t('Reports from collection staff', 'संग्रह कर्मचारियों की रिपोर्ट')}: <strong>{summary.get('worker_reports', 0)}</strong> · {t('Dangerous items flagged', 'खतरनाक चीज़ों की रिपोर्ट')}: <strong>{summary.get('hazards', 0)}</strong><br>
{extra}{t('Deep checks (below the top layer)', 'गहरी जाँच (ऊपर की परत के नीचे)')}: <strong>{summary.get('deep_checks', 0)}</strong> · {t('hidden wrong items found', 'छिपी गलत चीज़ें मिलीं')}: <strong>{summary.get('hidden_found', 0)}</strong></div>
<h2>{t('By campus area', 'परिसर के क्षेत्र के अनुसार')}</h2><table><thead><tr><th>{t('Area', 'क्षेत्र')}</th><th>{t('Locations', 'जगहें')}</th><th>{t('Score /100', 'स्कोर /100')}</th><th>{t('Checks', 'निरीक्षण')}</th><th>{t('Dangerous items', 'खतरनाक चीज़ें')}</th></tr></thead>
<tbody>{area_rows or '<tr><td colspan="5">' + t('No locations have been added.', 'अभी कोई जगह नहीं जोड़ी गई।') + '</td></tr>'}</tbody></table>
<h2>{t('Observations by location', 'जगह के अनुसार निरीक्षण')}</h2><table><thead><tr><th>{t('Location', 'जगह')}</th><th>{t('Score /100', 'स्कोर /100')}</th><th>{t('Checks', 'निरीक्षण')}</th><th>{t('Coverage', 'कवरेज')}</th><th>{t('Dangerous items', 'खतरनाक चीज़ें')}</th><th>{t('Vs last week', 'पिछले सप्ताह की तुलना में')}</th></tr></thead>
<tbody>{rows or '<tr><td colspan="6">' + t('No locations have been added.', 'अभी कोई जगह नहीं जोड़ी गई।') + '</td></tr>'}</tbody></table>
<h2>{t('Next round: one action per location', 'अगला चक्कर: हर जगह के लिए एक सुधार')}</h2>{steps or '<p>' + t('Add a floor and make the first check with permission.', 'अनुमति लेकर जगह जोड़ें और पहला निरीक्षण करें।') + '</p>'}
{goal_html}<h2>{t('Reading this report', 'इस रिपोर्ट को समझें')}</h2>{t(f'''<p>Clean = 100; a few wrong items = 50; mixed = 0. Not seen is excluded.
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
An early trend does not prove environmental impact or causation. Use your browser's print command to save as PDF.</p></footer>''', '''<p>साफ़ = 100; कुछ गलत चीज़ें = 50; मिला हुआ = 0। नहीं देखे गए डिब्बे शामिल नहीं हैं।
हर जगह का स्कोर उपलब्ध डिब्बा-प्रकारों के औसत से बनता है; परिसर का स्कोर स्कोर वाली जगहों का औसत है।
कवरेज दर्ज निरीक्षणों में देखे गए डिब्बे गिनता है। जो चक्कर दर्ज ही नहीं हुए, उन्हें नहीं मापता।</p>
<p>सुझाव निर्धारित नियमों पर आधारित हैं: पहले कर्मचारियों की बताई खतरनाक चीज़ें, फिर संग्रह में मिलावट, अधूरे निरीक्षण और डिब्बों में अलगाव।
जानकारी न होने को साफ़ नहीं गिनते। जगहें क्षेत्र और नाम के क्रम में हैं; यह सार्वजनिक रैंकिंग नहीं है।</p>
<p>पिछले सप्ताह की तुलना में केवल वे निरीक्षण आते हैं जिनमें दोनों डिब्बे देखे गए। कम-से-कम 5 अंक और अंतर की दो मानक त्रुटियों से अधिक बदलाव को स्पष्ट कहते हैं।
यह छोटे पायलट का नियम है, सांख्यिकीय प्रमाण नहीं। एक दैनिक निरीक्षण पर साप्ताहिक स्कोर लगभग 30 अंक बदल सकता है, भले वास्तविक बदलाव न हो।</p>
<footer><p>यह रिपोर्ट जगह के स्तर पर संयुक्त आँकड़े और मार्गदर्शन देती है। निजी टिप्पणी, फ़ोटो, एक्सेस कोड और कार्ड लिंक शामिल नहीं हैं।
केवल संबंधित समुदाय से साझा करें। डाउनलोड की गई प्रतियाँ वापस नहीं ली जा सकतीं और सुधार के बाद अपडेट नहीं होतीं।</p>
<p>डेमो निरीक्षण काल्पनिक हैं। वास्तविक पायलट निरीक्षण संचालक दर्ज करके पुष्टि करता है। शुरुआती रुझान पर्यावरणीय प्रभाव या उसका कारण साबित नहीं करता।
PDF सहेजने के लिए ब्राउज़र का प्रिंट विकल्प उपयोग करें।</p></footer>''')}</body></html>"""
