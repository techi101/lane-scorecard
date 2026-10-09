# Three-minute demonstration outline

This is a recording plan, not a claim that the real pilot or AWS deployment is complete. Use the demo badge when showing generated data. Resolve competition eligibility before submitting; see BUILD_RECORD.md.

| Time | Show | Explain |
|---|---|---|
| 0:00–0:20 | Shared hostel bins, with permission, or a clearly illustrative screen | “Checking bins is useful only if the people using them hear back. Lane Scorecard turns checks into one practical next step for each floor.” |
| 0:20–0:55 | The collection staff page on a phone, ideally used by a real housekeeping worker with permission | “The person who sorts our mixed waste by hand can now report it without reading.” Tap the floor, the faces for the green and blue bins, the red danger button, send; let the Hindi voice be heard. Then show the warden's own check form briefly. |
| 0:55–1:20 | Dashboard | Explain the score, coverage and fully observed denominator. Show real results only if collected; otherwise keep the demo label visible. |
| 1:20–1:50 | Generate card; open in a signed-out window; switch to Hindi | Show the floor/community comparison and one action. Copy a private link. Explain that no resident identities or bin photos appear on it. |
| 1:50–2:15 | Weekly plan, the “vs last week” line, and the downloadable report | The warden's question: “Did last week's action work?” Show a floor whose change clears the noise band and one that shows “no clear change”. Explain in one line: with one check a day, the weekly number often moves by about 30 points with no real change, so the app refuses to claim a change it can't support. Download the report and point to the “Vs last week” column. If Bedrock is connected, briefly show an actual suggestion during the earlier check step. |
| 2:15–2:40 | AWS: the actual console if deployed; otherwise the local SAM run | If deployed: API Gateway, Lambda, DynamoDB items appearing, S3 and CloudWatch logs. If not deployed: show `sam build` succeeding and the app served by `sam local start-api` with the Lambda container in Docker, and say plainly that it is a local AWS run, not a cloud deployment. |
| 2:40–3:00 | Results and limits | Report measured counts and coverage. “This is an early pilot signal, not proof of causation. Next we need a longer pilot and independently labelled photo evaluation.” |

## Short project description draft

Lane Scorecard helps hostel operators return useful feedback to the people sharing waste bins. A volunteer records human-confirmed bio/non-bio observations, the app computes transparent floor-level scores, and each floor receives a private English/Hindi card with one practical improvement. Missing observations are visible, demo data is separate, and optional Bedrock photo suggestions never replace the human decision.

The weekly plan translates those observations into one follow-up per floor, and the downloadable aggregate report gives wardens a printable summary without private notes or photos.

The current implementation runs locally using SQLite. It includes an AWS deployment template and adapters for Lambda, API Gateway, DynamoDB, S3, Bedrock and a weekly EventBridge job. Replace this sentence with verified deployment details only after deployment succeeds.

AI tools used: OpenAI Codex for implementation and testing; Claude Code for earlier planning/research and, later, the week-over-week follow-up check and local AWS SAM run. Describe actual assistance accurately, including this project's true start time when relevant. Do not claim Strands, RAG, Polly or Telegram functionality in the current version.
