# Attribution

Application source, frontend styling and SVG mark were authored for this workspace with OpenAI Codex. The earlier product plan was recovered from the user's Claude history and local research documents. No archived prototype source or third-party visual assets were copied.

Claude Code (Anthropic) later added the collection staff link and worker page (`web/worker.*`, worker endpoints in `app/main.py`, `tests/test_worker.py`; emoji are the device's system emoji, not bundled assets), the week-over-week follow-up check (`app/actions.py`, `app/report.py`, `web/app.js`), `scripts/followup_evidence.py`, `tests/test_outcome.py`, and the local AWS SAM CLI build and run.

Direct runtime dependencies:

- FastAPI: MIT.
- Uvicorn: BSD-3-Clause.
- Pillow: HPND / Pillow's distributed licence terms.
- Boto3: Apache-2.0.
- Mangum: MIT.

Development dependencies include pytest, HTTPX, Playwright, cfn-lint, AWS SAM CLI and AWS CLI (both Apache-2.0). These and all transitive dependencies retain their own distributed licences. Check the installed packages' licence files before redistributing dependency bundles. No dependency source or binaries are included in the source-only handoff ZIP.

The two-bin guidance is practical pilot advice, not a verbatim extract of a legal document. No external research effect size or regulatory-compliance claim is presented by the app.
