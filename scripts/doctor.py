"""Read-only setup check. Cloud identity is checked only with --aws."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def inspect(profile=None, check_aws=False):
    checks = []

    def add(name, ok, detail, required=True):
        checks.append({"check": name, "ok": ok, "detail": detail, "required": required})

    add("Python", sys.version_info >= (3, 12), sys.version.split()[0])
    for package in ["fastapi", "uvicorn", "Pillow", "boto3", "mangum"]:
        try:
            add(package, True, importlib.metadata.version(package))
        except importlib.metadata.PackageNotFoundError:
            add(package, False, "Run setup.ps1 to install runtime requirements.")
    root = Path(__file__).resolve().parent.parent
    add("App sources", all((root / name).is_file() for name in ["app/main.py", "web/index.html", "template.yaml"]), "Application, web entry point and SAM template.")
    for name in ["aws", "sam", "docker"]:
        location = shutil.which(name)
        add(name, bool(location), "Installed on PATH." if location else "Missing from PATH; see docs/AWS.md.", required=check_aws)
    if check_aws:
        if shutil.which("docker"):
            try:
                result = subprocess.run(["docker", "info", "--format", "{{.OSType}}"], capture_output=True, text=True, timeout=20)
                add("Linux Docker engine", result.returncode == 0 and result.stdout.strip() == "linux", "Linux engine ready." if result.returncode == 0 and result.stdout.strip() == "linux" else "Start Docker Desktop using Linux containers.")
            except (OSError, subprocess.TimeoutExpired):
                add("Linux Docker engine", False, "Docker did not respond within 20 seconds.")
        os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
        try:
            import boto3
            from botocore.config import Config
            session = boto3.Session(profile_name=profile, region_name="us-east-1")
            response = session.client("sts", config=Config(connect_timeout=3, read_timeout=5, retries={"total_max_attempts": 1})).get_caller_identity()
            add("AWS identity", bool(response.get("Account")), "Authentication succeeded. Deployment permissions and Bedrock access still need verification.")
        except Exception as exc:
            add("AWS identity", False, f"Authentication unavailable ({type(exc).__name__}). Configure a named AWS profile; do not put credentials in the project.")
    return {"mode": "deployment prerequisites" if check_aws else "local setup", "checks": checks,
            "ready": all(c["ok"] for c in checks if c["required"]),
            "cloud_checked": check_aws, "resources_created": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aws", action="store_true", help="Also check Docker's Linux engine and AWS STS identity; creates no resources.")
    parser.add_argument("--profile", help="Named AWS profile, used only with --aws.")
    args = parser.parse_args()
    result = inspect(args.profile, args.aws)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["ready"] else 1)
