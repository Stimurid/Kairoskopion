"""Use this checkout's src package for direct Python test runs.

The Hub runs ``unittest discover`` without installing each isolated worktree.
An editable install from an earlier worktree can otherwise shadow new service
modules in this checkout. Python imports this file during normal startup.
"""

from pathlib import Path
import sys

_src = Path(__file__).resolve().parent / "src"
if _src.is_dir():
    _src_path = str(_src)
    if _src_path in sys.path:
        sys.path.remove(_src_path)
    sys.path.insert(0, _src_path)
