# Lane Scorecard: small checks, better waste habits

**Theme:** Waste and Energy — waste segregation.

**Status:** live on AWS (stack `lane-scorecard`, us-east-1) at https://ss9ib2qbek.execute-api.us-east-1.amazonaws.com. It runs on Lambda, API Gateway, DynamoDB, S3, EventBridge and CloudWatch. Bedrock is switched off while AWS reviews our new account's quota. First real campus checks were recorded on 9 Oct 2026. Real environmental impact has not been measured.

## The problem

Two labelled bins do not tell campus staff whether waste is being separated consistently or mixed again at collection. Lane Scorecard turns short, repeated observations into private location-level feedback and a weekly follow-up plan.

## The build

An operator sets up permitted locations, records both bin ratings and optionally notes what happens during collection. The app calculates transparent seven-day scores, keeps missing evidence visible, and compares consecutive weeks. Residents can receive a private English/Hindi scorecard with one practical action. A weekly operator report summarises scores, coverage and follow-up actions while excluding private notes and photos.

The app is a Python FastAPI application running on AWS Lambda, with DynamoDB storage; the same code runs locally with SQLite for development. Its responsive browser interface supports phone-based checks. Demo data and real-pilot data are kept separate. Corrections revoke old scorecard links, and every final rating remains a human decision.

## The people who handle the bins

Housekeeping and sanitation staff see every bin at every pickup, and when residents mix waste they are the ones who sort it by hand, including broken glass, blades and unwrapped sanitary waste. Many do not read English, and some do not read at all.

The pilot lead creates a secret, revocable **collection staff link** and shares it on WhatsApp. It opens a picture-only page: tap the location, tap a face for the green (wet) bin and the blue (dry) bin, tap the red button if something dangerous was in it, and press send. Every tap is spoken in Hindi. There is no sign-in and nothing to read. Reports count as checks in a separate **collection** round, so daily staff reports also give the follow-up check enough data to see real change.

Dangerous items come first in the weekly plan (“Make the bins safe to handle”) and have their own column in the pilot lead's report. This design has not yet been tested with real staff; a short conversation with a campus housekeeping team is the next step.

## Specific feedback, not generic tips

Checks and staff reports can tag what was wrong: plastic in the green bin, food in the blue bin, or everything in one bag. The location's scorecard then says what went wrong most often and in how many checks, why it matters, how many of the other locations avoided it, and one thing to try. The text is a fixed, reviewed English/Hindi template rather than AI-generated, and the comparison is location-level only, never room or person.

## Checking whether a fix worked

The user is the campus pilot lead. Each week the pilot lead decides which location needs attention and what to do. The plan and the weekly report then compare each location with the previous week and say whether the score improved, got worse, or showed no clear change.

The comparison uses only checks where both bins were seen, and calls a change clear only when it is at least 5 points and larger than two standard errors of the week-to-week difference. This is a rule for a small pilot, not a statistical proof. It matters: on the simulated demo data, with one check a day, a location's weekly score often moves by about 30 points with no real change, so a naive "down 20 points" label would mislead the pilot lead. Running both daily rounds, or comparing over longer windows, is needed to detect real change. `python scripts/followup_evidence.py` regenerates the table in [FOLLOWUP_EVIDENCE.md](FOLLOWUP_EVIDENCE.md); every row there is simulated.

## Where AWS fits

The whole stack is defined in one AWS SAM template and is live in us-east-1 (architecture diagram: [docs/images/architecture.png](images/architecture.png)):

- **AWS Lambda** runs the app: scoring, the weekly plan, scorecards, staff reports, sign-in and photo checks.
- **Amazon API Gateway** (HTTP API) is the public HTTPS address, with throttling.
- **Amazon DynamoDB** stores locations, checks, scorecards, the audit log and sessions, with demo and real-pilot data kept apart.
- **Amazon S3** (private) stores bin photos with metadata removed.
- **Amazon EventBridge** makes the weekly scorecards every Monday at 08:00 IST.
- **Amazon CloudWatch** keeps the logs; **IAM** gives the function access only to its own table, bucket and model.
- **Amazon Bedrock** (Nova Lite) suggests a bin rating from a photo and reads receipt photos, always with a human making the final decision. It is coded and permissioned, but switched off: our new account's Bedrock quota is currently 0, and an AWS quota case is open.

Changes are deployed through a reviewed SAM changeset.

## First real campus data

On the evening of 9 Oct 2026 we recorded 9 real checks, with 14 photos, at 9 bin locations on the NSUT campus. The blue (dry) bin was clean in all 7 checks where it was visible. The green (wet) bin was never clean: mixed in 5 and a few wrong items in 2. Plastic in the green bin was tagged in 6 of 9 checks. The useful fix is therefore narrow: keep plastic out of the green bin. This is one evening at one campus, the ratings were read from photos and are being confirmed by the team, and it is an early signal, not proof of impact.

## What can be claimed

A working, deployed observation, scoring, action-plan, report, scorecard and staff-reporting workflow on AWS, and a first evening of real campus checks. No claim of real waste reduction, AI accuracy or competition eligibility is made.

## Provenance and credits

The initial implementation began before the event's published opening. Under the published rules this is not an eligible new entry; obtain an organiser's ruling before using this as a competition submission. See [BUILD_RECORD.md](BUILD_RECORD.md).

OpenAI Codex assisted implementation. Earlier planning and research used Claude. Claude Code implemented the collection staff link and picture-only worker page, the week-over-week follow-up check, the simulated evidence script, and the local AWS SAM build and run (`sam validate`, `sam build`, `sam local start-api`). Dependencies and credits are recorded in [ATTRIBUTION.md](ATTRIBUTION.md).

Demo video: https://youtu.be/LxuLfnb2GZ0
