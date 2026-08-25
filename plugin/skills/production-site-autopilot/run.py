#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

RUNTIME_ROOT = Path(__file__).resolve().parent / "runtime"
sys.path.insert(0, str(RUNTIME_ROOT))

from production_site_autopilot.cli import main

raise SystemExit(main())
