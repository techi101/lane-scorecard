# Three-minute demonstration outline

This is the recording plan. The app is deployed on AWS, and the first real checks are from 9 Oct. Use the demo badge when showing generated data. Resolve competition eligibility before submitting; see BUILD_RECORD.md.

| Time | Show | Explain |
|---|---|---|
| 0:00–0:20 | Shared campus bins, with permission, or a clearly illustrative screen | “Checking bins is useful only if the people using them hear back. Lane Scorecard turns checks into one practical next step for each location.” |
| 0:20–0:55 | The collection staff page on a phone, ideally used by a real housekeeping worker with permission | “The person who sorts our mixed waste by hand can now report it without reading.” Tap the location, the faces for the green and blue bins, the red danger button, send; let the Hindi voice be heard. Then show the pilot lead's own check form briefly. |
| 0:55–1:20 | Dashboard | Explain the score, coverage and fully observed denominator. Show real results only if collected; otherwise keep the demo label visible. |
| 1:20–1:50 | Generate card; open in a signed-out window; switch to Hindi | Show the location/community comparison and one action. Copy a private link. Explain that no resident identities or bin photos appear on it. |
| 1:50–2:15 | Weekly plan, the “vs last week” line, and the downloadable report | The pilot lead's question: “Did last week's action work?” Show a location whose change clears the noise band and one that shows “no clear change”. Explain in one line: with one check a day, the weekly number often moves by about 30 points with no real change, so the app refuses to claim a change it can't support. Download the report and point to the “Vs last week” column. If Bedrock is connected, briefly show an actual suggestion during the earlier check step. |
| 2:15–2:40 | AWS console (us-east-1, signed in to account env-hacks) | Show the architecture diagram for 3 seconds, then: CloudFormation stack `lane-scorecard` → the Lambda function → DynamoDB table items (record a check first, then refresh to show the new item) → the private S3 photo bucket → CloudWatch logs of that request. If Bedrock has been approved by then, also show one real AI photo suggestion. Never show the access code or keys. |
| 2:40–3:00 | Results and limits | Report measured counts and coverage. “This is an early pilot signal, not proof of causation. Next we need a longer pilot and independently labelled photo evaluation.” |

## Short project description draft

Lane Scorecard helps campus operators return useful feedback to the people sharing waste bins. A volunteer records human-confirmed bio/non-bio observations, the app computes transparent location-level scores, and each location receives a private English/Hindi card with one practical improvement. Missing observations are visible, demo data is separate, and optional Bedrock photo suggestions never replace the human decision.

The weekly plan translates those observations into one follow-up per location, and the downloadable aggregate report gives pilot leads a printable summary without private notes or photos.

It is live on AWS: Lambda runs the app behind API Gateway, DynamoDB stores the records, private S3 holds bin photos, EventBridge makes the weekly scorecards, and CloudWatch keeps the logs, all defined in one SAM template. Bedrock Nova Lite photo suggestions are coded but switched off until AWS approves the new account's Bedrock quota.

AI tools used: OpenAI Codex for implementation and testing; Claude Code for earlier planning/research and, later, the week-over-week follow-up check and local AWS SAM run. Describe actual assistance accurately, including this project's true start time when relevant. Do not claim Strands, RAG, Polly or Telegram functionality in the current version.
