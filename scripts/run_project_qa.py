"""Run this checkout's pytest suite with a short, unique Windows basetemp."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
spec = importlib.util.find_spec("kairoskopion")
if spec is None or not Path(spec.origin).resolve().is_relative_to(SRC):
    raise SystemExit("Wrong kairoskopion import origin")

environment = os.environ.copy()
environment["PYTHONPATH"] = str(SRC) + os.pathsep + environment.get("PYTHONPATH", "")
temp_root = Path(environment.get("KAIROSKOPION_QA_TEMP_ROOT", "C:\\" if os.name == "nt" else tempfile.gettempdir()))
with tempfile.TemporaryDirectory(prefix="tcq_", dir=temp_root) as basetemp:
    command = [sys.executable, "-m", "pytest", "-q", "--basetemp", basetemp]
    print("import_origin=" + str(spec.origin), flush=True)
    print("command=" + " ".join(command), flush=True)
    raise SystemExit(subprocess.call(command, cwd=ROOT, env=environment))
