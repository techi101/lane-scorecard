# Follow-up evidence (simulated)

**All data below is SIMULATED** by the app's demo generator (`seed_demo`, fixed seed). It shows how the follow-up check behaves; it is not evidence of real waste reduction.

The score columns are the displayed floor scores. The judgement compares only checks where both bins were seen: a change is called clear only when it is at least 5 points and larger than two standard errors (the noise band). This is a rule for a small pilot, not a statistical proof. Regenerate with `python scripts/followup_evidence.py`. Generated for weeks ending 2026-09-25, 2026-10-02, 2026-10-09.

| Floor | Score, week to 2026-09-25 | Score, week to 2026-10-02 | Score, week to 2026-10-09 | Action this week | Outcome vs last week |
|---|---|---|---|---|---|
| Fifth floor | 45.2 | 85.2 | 64.3 | Keep collection separate | no_clear_change (score -20.9; both-bin checks -20.8, noise ±32.7) |
| First floor | 75 | 80.3 | 57.1 | Keep collection separate | no_clear_change (score -23.2; both-bin checks -18.3, noise ±27.6) |
| Fourth floor | 72 | 71.4 | 50 | Improve separation at the bin | no_clear_change (score -21.4; both-bin checks -21.4, noise ±33.5) |
| Ground floor | 75 | 85.7 | 46.5 | Keep collection separate | worse (score -39.2; both-bin checks -39.3, noise ±31.4) |
| Second floor | 54.1 | 64.2 | 53.5 | Improve separation at the bin | no_clear_change (score -10.7; both-bin checks -10.7, noise ±29.5) |
| Third floor | 65.5 | 72 | 50 | Keep collection separate | no_clear_change (score -22; both-bin checks -16.7, noise ±38.4) |

Outcome counts: no_clear_change 5, worse 1
