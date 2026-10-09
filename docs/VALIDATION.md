# Validation performed

Validated on Windows, Python 3.12, on 8 October 2026.

| Check | Result |
|---|---|
| Backend and AWS SDK-contract suite | **20 passed** |
| JavaScript syntax (`node --check`) | Passed |
| AWS SAM template (`cfn-lint`) | Passed, no reported template errors |
| Desktop browser workflow, 1440px | Passed |
| Mobile layout and navigation, 390px | Passed; no page-width overflow |
| Photo upload with AI disabled | Passed; saved privately, no prediction fabricated, existing human rating unchanged |
| Operator login and session protection | Passed |
| Empty real pilot / populated simulated demo | Verified separately |
| Create floor → save check → dashboard score | Passed |
| Private card in a separate browser tab | Passed |
| Hindi scorecard | Rendered and visually inspected |
| Correct a check → recalculate → revoke old card | Passed |
| Browser JavaScript errors | None during the workflow |
| Weekly action plan | Passed: missing observations, collection mixing, contaminated bins, clean observations and seven-day filtering |
| Aggregate report download | Passed: authenticated, HTML escaped, bilingual action text, private notes and card tokens excluded |
| Follow-up check from weekly plan | Correct floor selected |
| Weekly plan desktop/mobile | Passed; no page-width overflow at 390px |
| PowerShell validation/deployment scripts | Parsed without syntax errors; cloud deployment not executed |
| Local setup doctor | Runtime dependencies ready; AWS CLI/SAM CLI missing from PATH |
| Running local server | Healthy at `http://127.0.0.1:8765` |
| Real AWS deployment / inference | **Not performed**; account access is not configured |
| Real bin-photo evaluation / environmental impact | **Not performed**; no real pilot evidence supplied |

The tests cover missing observations, seven-day boundaries, duplicate submissions, cross-workspace references, human confirmation, privacy, CSV formula protection, photo metadata stripping, AI failure handling, photo ownership, deletion, persistence across app restart, scheduled cards, maintenance, the DynamoDB SDK contract and the Lambda HTTP adapter.

Two dependency deprecation warnings were reported (Starlette's HTTPX test-client compatibility and Mangum's event-loop lookup). They did not fail tests; review them when updating dependencies.

Browser artifacts are in `artifacts/desktop-overview.png`, `desktop-check.png`, `desktop-weekly-plan.png`, `mobile-overview.png`, `mobile-check.png`, `mobile-weekly-plan.png`, and `scorecard-hindi.png`. They contain generated demo or isolated test data and must not be presented as real pilot results.

The full continuation check was run using `.venv/Scripts/python.exe scripts/validate.py --browser`. Its machine-readable record is `artifacts/validation.json`. Pytest now uses isolated system temporary directories, avoiding a permissions failure in the earlier `.local/pytest` directory. Existing pilot data was not used in tests.
