"""Run existing checks with isolated test data. Never connects to AWS."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", action="store_true", help="Include the desktop/mobile browser workflow.")
    args = parser.parse_args()
    python = sys.executable
    lint = shutil.which("cfn-lint") or str(Path(python).parent / ("cfn-lint.exe" if os.name == "nt" else "cfn-lint"))
    temporary = str(Path(tempfile.gettempdir()) / ("lane-validation-" + uuid4().hex))
    commands = [
        ("Backend and AWS SDK contracts", [python, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--basetemp", temporary]),
        ("JavaScript syntax", ["node", "--check", "web/app.js"]),
        ("SAM infrastructure lint", [lint, "template.yaml"]),
    ]
    if args.browser:
        commands.append(("Desktop and mobile browser workflow", [python, "tests/browser_check.py"]))
    env = dict(os.environ)
    for name in ["LANE_TABLE", "LANE_PHOTO_BUCKET", "LANE_ENABLE_AI", "LANE_ADMIN_CODE", "LANE_DATA_DIR", "LANE_ORIGIN", "LANE_SECURE_COOKIE", "AWS_LAMBDA_FUNCTION_NAME"]:
        env.pop(name, None)
    env["AWS_EC2_METADATA_DISABLED"] = "true"
    results = []
    for name, command in commands:
        print(f"\n{name}", flush=True)
        try:
            code = subprocess.run(command, cwd=ROOT, env=env).returncode
            results.append({"check": name, "passed": code == 0, "exit_code": code})
        except FileNotFoundError:
            print("Required tool missing. Install requirements-dev.txt and Node.js.", flush=True)
            results.append({"check": name, "passed": False, "exit_code": None})
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "checks": results, "real_aws_tested": False}
    output = ROOT / "artifacts" / "validation.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\nValidation record: {output}")
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
