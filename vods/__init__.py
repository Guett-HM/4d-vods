"""4D-VODS command-line tools: run the simulators, record provenance, validate the
physics model and check that every published number matches the results.

The physics lives in ``sim/`` (``vods_sim.py`` for the data layer, ``samm_sim.py`` for the
self-aligning micro-matrix). This package only orchestrates it, so the scripts in ``sim/``
keep working on their own exactly as in v1.0.
"""
import os
import sys

__version__ = "1.1.0"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIM = os.path.join(ROOT, "sim")
RESULTS = os.path.join(ROOT, "results")
RESULTS_QUICK = os.path.join(ROOT, "results_quick")

if SIM not in sys.path:
    sys.path.insert(0, SIM)
