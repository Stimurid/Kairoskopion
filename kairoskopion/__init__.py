"""Load the source package when running Python from this checkout.

``python -m unittest discover -s tests`` does not use pytest's pythonpath
setting.  Without a checkout-local package, it may import an older installed
Kairoskopion which lacks the current citation modules.  The distributable
package remains the one under ``src`` (see pyproject.toml).
"""

from pathlib import Path

_source_package = Path(__file__).resolve().parent.parent / "src" / "kairoskopion"
__path__ = [str(_source_package)]

_source_init = _source_package / "__init__.py"
exec(compile(_source_init.read_bytes(), str(_source_init), "exec"))
