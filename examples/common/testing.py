"""Helpers for testing examples.

Example folders are named like `02-the-agent-loop`, which is not a valid Python
module name, and many of them contain a `main.py`. `load_example` imports an
example's file under a unique module name so tests never collide.

    # examples/02-agent-loop/tests/test_main.py
    from common.testing import load_example
    main = load_example(__file__)          # loads ../main.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_example(test_file: str, module: str = "main") -> ModuleType:
    """Import `<example folder>/<module>.py`, given the path of a test file inside `<example folder>/tests/`."""
    path = Path(test_file).resolve().parent.parent / f"{module}.py"
    name = f"example_{path.parent.name.replace('-', '_')}_{module}"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod
