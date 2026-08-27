#!/usr/bin/env python3
"""Optional current-policy stress runner. Not part of the V41 release gate."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
loader=unittest.TestLoader()
suite=loader.discover(str(ROOT/'tests'/'stress'),pattern='geometry_stress.py',top_level_dir=str(ROOT/'tests'/'stress'))
raise SystemExit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
