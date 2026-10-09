# Problem statement and scope

**Track fit:** Waste and Energy → waste segregation, under WeMakeDevs × AWS Environmental Hacks.

The official event provides open environmental tracks. It asks teams to choose a concrete problem inside a track; it does not assign this exact statement to Lane Scorecard.

## Our problem statement

How can hostel staff and student volunteers identify where two-bin waste segregation breaks down, give each floor useful feedback, and track changes over time without collecting resident identities?

## Who uses it

- A permitted hostel operator or volunteer records visible bin conditions.
- Residents receive a private, floor-level scorecard with one practical action.
- A warden or collection coordinator reviews weekly aggregate reports and collection problems.

## The complete workflow

1. Sign in and select the real pilot workspace.
2. Add floors after obtaining permission.
3. Record the date, round, both bin ratings and whether collection stayed separate. Attach permitted photos if useful.
4. Review the weekly dashboard and coverage. Missing observations remain missing.
5. Open the weekly plan for one evidence-based action per floor.
6. Generate a private English/Hindi floor scorecard or download a weekly operator report.
7. Repeat the check and compare weeks. Correct errors in the observation log; old cards are revoked on corrections.

## Requirements mapped to working features

| Need | Implementation | Evidence |
|---|---|---|
| Find segregation problems | Separate bio/non-bio ratings and seven-day floor scores | Backend scoring and browser checks |
| Distinguish uncertainty | Not-seen rating and explicit observation coverage | Missing-data and boundary tests |
| Identify downstream mixing | Collection observation and follow-up action | Weekly action tests |
| Give useful feedback | Private bilingual scorecards and weekly action plan | Browser flow and action tests |
| Check change over time | Four-week chart and previous-week comparison | Dashboard and scoring tests |
| Protect private details | Operator login, private photos, aggregate-only report, revocable card links | Access-control and redaction tests |
| Support phone-based checks | Responsive check form, mobile navigation and report access | 390px browser workflow |
| Persist observations | SQLite locally; DynamoDB adapter for AWS | Persistence tests and SDK contract tests |
| Deploy to AWS | SAM template, staging script and deployment wrapper | Infrastructure lint; live deployment pending |
| Optional photo assistance | Bedrock Nova suggestion, human confirmation and manual fallback | SDK contract and failure-path tests; real inference pending |

## Success measures for a real pilot

Measure both-bins-clean rate, per-bin scores, observed-bin coverage, participating floors and reported collection separation. Record the count and observation window beside each percentage. Obtain permission and collect a baseline before distributing feedback, then repeat a comparable observation routine. A change in this small pilot is an early signal, not proof of causation, waste diversion or carbon savings.

The application does not weigh waste, identify residents, certify legal compliance, or automatically send messages. Demo records are simulated; the real pilot starts empty.

## Event eligibility and sources

The build record states that the first implementation began on 8 October 2026 at approximately 02:50 IST, before the published 08:00 IST opening. The official rules exclude projects begun before opening, even if rewritten. This project fits the theme but must not be described as an eligible new competition entry without an organiser's ruling. See [BUILD_RECORD.md](BUILD_RECORD.md); continuation work does not change its provenance.

Sources checked on 8 October 2026:

- [Official event tracks and judging](https://www.wemakedevs.org/aws/env)
- [Official event rules](https://www.wemakedevs.org/aws/env/rules)

AI assistance: OpenAI Codex for implementation; prior product research and planning used Claude. See [ATTRIBUTION.md](ATTRIBUTION.md).
