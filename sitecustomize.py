"""Prefer this checkout's src package for commands launched at the repo root.

Python loads sitecustomize during startup when the current directory is on
sys.path.  This also covers ``python -m unittest discover -s tests``, which
does not read pytest's ``pythonpath`` setting and can otherwise import an
older installed copy of kairoskopion.
"""

from pathlib import Path
import sys


_root = Path(__file__).resolve().parent
_src = _root / "src"
if (_src / "kairoskopion" / "__init__.py").is_file():
    _path = str(_src)
    if _path in sys.path:
        sys.path.remove(_path)
    sys.path.insert(0, _path)
