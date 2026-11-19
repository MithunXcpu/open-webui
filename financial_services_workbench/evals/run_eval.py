#!/usr/bin/env python3
"""Scorecard runner. Usage: python evals/run_eval.py"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fsw.eval import main

if __name__ == "__main__":
    raise SystemExit(main())
