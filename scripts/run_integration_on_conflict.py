#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import pytest  # noqa: F401
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pytest"])

assert os.environ.get("DATABASE_URL") or os.environ.get("DATA_SVC_DATABASE_URL"), "missing DSN"
print("dsn_set", True)

root = Path("/tmp/itest_run")
if root.exists():
    shutil.rmtree(root)
(root / "tests" / "integration").mkdir(parents=True)
shutil.copytree("/tmp/integration_tests", root / "tests" / "integration", dirs_exist_ok=True)
(root / "tests" / "__init__.py").write_text("")

rc = subprocess.call(
    [sys.executable, "-m", "pytest", str(root / "tests" / "integration"), "-q", "-s"],
    cwd="/app",
)
sys.exit(rc)
