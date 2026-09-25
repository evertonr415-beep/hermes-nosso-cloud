#!/usr/bin/env python3
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import boto3

required = [
    "HERMES_BUCKET_NAME",
    "HERMES_BUCKET_REGION",
    "HERMES_BUCKET_ENDPOINT",
    "HERMES_BUCKET_ACCESS_KEY",
    "HERMES_BUCKET_SECRET_KEY",
]
missing = [k for k in required if not os.environ.get(k)]
if missing:
    raise SystemExit("bucket backup skipped: missing " + ", ".join(missing))

bucket = os.environ["HERMES_BUCKET_NAME"]
region = os.environ["HERMES_BUCKET_REGION"]
endpoint = os.environ["HERMES_BUCKET_ENDPOINT"]
access_key = os.environ["HERMES_BUCKET_ACCESS_KEY"]
secret_key = os.environ["HERMES_BUCKET_SECRET_KEY"]

stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
tmp = Path(tempfile.gettempdir()) / f"hermes-quick-{stamp}.zip"
key = f"backups/quick/{stamp}.zip"

env = os.environ.copy()
env.setdefault("HERMES_HOME", "/opt/data")

try:
    subprocess.run(
        ["hermes", "backup", "--quick", "--output", str(tmp), "--label", "railway-auto"],
        check=True,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )
    s3.upload_file(str(tmp), bucket, key)
    print(f"[bucket-backup] uploaded {key} ({tmp.stat().st_size} bytes)")
finally:
    try:
        tmp.unlink(missing_ok=True)
    except Exception:
        pass
