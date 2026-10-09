"""Evaluate Bedrock suggestions against an independently human-labelled JSONL set.

Manifest row: {"image":"photos/bin-01.jpg", "stream":"bio", "label":"few"}
Run with LANE_ENABLE_AI=1 and configured AWS credentials. Invokes billable Bedrock.
Never invents results when no model is connected.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.vision import sanitize, suggest

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('manifest', type=Path)
parser.add_argument('--output', type=Path, default=Path('artifacts/evaluation.json'))
parser.add_argument('--validate-only', action='store_true', help='Validate files and labels without any AWS request.')
args = parser.parse_args()
rows = [json.loads(line) for line in args.manifest.read_text(encoding='utf-8').splitlines() if line.strip()]
if not rows:
    raise SystemExit('The manifest is empty. Collect and label real photos first.')
seen, prepared = set(), []
for row in rows:
    if row.get('stream') not in ('bio', 'nonbio') or row.get('label') not in ('clean', 'few', 'mixed', 'unseen'):
        raise SystemExit('Every row needs a valid stream and human label.')
    raw = sanitize((args.manifest.parent / row['image']).read_bytes())
    fingerprint = hashlib.sha256(raw).hexdigest()
    if fingerprint in seen:
        raise SystemExit('Duplicate image found. Use distinct photos to avoid inflated agreement.')
    seen.add(fingerprint)
    prepared.append((row, raw))
if args.validate_only:
    print(f'Validated {len(prepared)} distinct labelled photos. No model calls made.')
    raise SystemExit(0)
if os.getenv('LANE_ENABLE_AI') != '1':
    raise SystemExit('AI is disabled. Set LANE_ENABLE_AI=1 only when ready to run Bedrock evaluation.')
results = []
for row, raw in prepared:
    prediction = suggest(raw, row['stream'])
    results.append({**row, 'prediction':prediction})
summary = {}
for stream in ('bio','nonbio'):
    subset = [row for row in results if row['stream'] == stream]
    successful = [row for row in subset if row['prediction']['status'] == 'available']
    matches = sum(row['label'] == row['prediction']['rating'] for row in successful)
    summary[stream] = {'total':len(subset), 'available':len(successful), 'failed':len(subset)-len(successful), 'matched':matches, 'agreement':matches/len(successful) if successful else None, 'confusion':dict(Counter(row['label']+' -> '+row['prediction']['rating'] for row in successful))}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps({'summary':summary, 'results':results}, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(summary, indent=2))
print(f'Wrote {args.output}. Failures are reported separately, never counted as predictions.')
