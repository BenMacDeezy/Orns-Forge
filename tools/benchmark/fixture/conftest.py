"""Put ``src/`` on sys.path so the fixture's tests can `import ledgerkit`
without an install step (this fixture is exercised by copying/checking out
the tree, not by pip-installing it)."""

import pathlib
import sys

_SRC = (pathlib.Path(__file__).parent / "src").resolve()
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
