# Lane Scorecard: small checks, better waste habits

**Theme:** Waste and Energy — waste segregation.

**Status:** complete local pilot application, with an AWS deployment template and supporting scripts. Live AWS deployment and real environmental impact have not been verified.

## The problem

Two labelled bins do not tell hostel staff whether waste is being separated consistently or mixed again at collection. Lane Scorecard turns short, repeated observations into private floor-level feedback and a weekly follow-up plan.

## The build

An operator sets up permitted floors, records both bin ratings and optionally notes what happens during collection. The app calculates transparent seven-day scores, keeps missing evidence visible, and compares consecutive weeks. Residents can receive a private English/Hindi scorecard with one practical action. A weekly operator report summarises scores, coverage and follow-up actions while excluding private notes and photos.

The app runs locally with FastAPI and SQLite. Its responsive browser interface supports phone-based checks. Demo data and real-pilot data are kept separate. Corrections revoke old scorecard links, and every final rating remains a human decision.

## The people who handle the bins

Housekeeping and sanitation staff see every bin at every pickup, and when residents mix waste they are the ones who sort it by hand, including broken glass, blades and unwrapped sanitary waste. Many do not read English, and some do not read at all.

The warden creates a secret, revocable **collection staff link** and shares it on WhatsApp. It opens a picture-only page: tap the floor, tap a face for the green (wet) bin and the blue (dry) bin, tap the red button if something dangerous was in it, and press send. Every tap is spoken in Hindi. There is no sign-in and nothing to read. Reports count as checks in a separate **collection** round, so daily staff reports also give the follow-up check enough data to see real change.

Dangerous items come first in the weekly plan (“Make the bins safe to handle”) and have their own column in the warden's report. This design has not yet been tested with real staff; a short conversation with a hostel's housekeeping team is the next step.

## Specific feedback, not generic tips

Checks and staff reports can tag what was wrong: plastic in the green bin, food in the blue bin, or everything in one bag. The floor's scorecard then says what went wrong most often and in how many checks, why it matters, how many of the other floors avoided it, and one thing to try. The text is a fixed, reviewed English/Hindi template rather than AI-generated, and the comparison is floor-level only, never room or person.

## Checking whether a fix worked

The user is the hostel warden. Each week the warden decides which floor needs attention and what to do. The plan and the weekly report then compare each floor with the previous week and say whether the score improved, got worse, or showed no clear change.

The comparison uses only checks where both bins were seen, and calls a change clear only when it is at least 5 points and larger than two standard errors of the week-to-week difference. This is a rule for a small pilot, not a statistical proof. It matters: on the simulated demo data, with one check a day, a floor's weekly score often moves by about 30 points with no real change, so a naive "down 20 points" label would mislead the warden. Running both daily rounds, or comparing over longer windows, is needed to detect real change. `python scripts/followup_evidence.py` regenerates the table in [FOLLOWUP_EVIDENCE.md](FOLLOWUP_EVIDENCE.md); every row there is simulated.

## Where AWS fits

The supplied SAM template deploys the app with API Gateway and Lambda, persistent records in DynamoDB, private photo storage in S3, a weekly EventBridge trigger and CloudWatch logs. Optional Bedrock Nova photo suggestions are implemented with a manual fallback. The deployment helper stages runtime files, builds for Linux and uses a guided SAM changeset review.

These integrations have local infrastructure and SDK-contract validation. A real AWS demo must be recorded after deployment; a template or stubbed test is not proof of a live AWS integration.

## What can be claimed

Working local observation, scoring, action-plan, report and scorecard workflows. No claim of real waste reduction, model accuracy, deployment success or competition eligibility should be added until supported by evidence.

## Provenance and credits

The initial implementation began before the event's published opening. Under the published rules this is not an eligible new entry; obtain an organiser's ruling before using this as a competition submission. See [BUILD_RECORD.md](BUILD_RECORD.md).

OpenAI Codex assisted implementation. Earlier planning and research used Claude. Claude Code implemented the collection staff link and picture-only worker page, the week-over-week follow-up check, the simulated evidence script, and the local AWS SAM build and run (`sam validate`, `sam build`, `sam local start-api`). Dependencies and credits are recorded in [ATTRIBUTION.md](ATTRIBUTION.md).

This document is a project writeup, not a submitted entry. No public repository or YouTube video link has been created by this continuation.
