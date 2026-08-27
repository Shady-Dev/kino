#!/usr/bin/env python3
"""Shim: kept so anything calling the old path (localfetch.sh on the Mac) keeps
working. The orchestrator logic now lives in run.py, driven by registry.py.

    python3 scripts/providers/run.py nexxo
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run

if __name__ == "__main__":
    sys.exit(run.main(["nexxo"]))
