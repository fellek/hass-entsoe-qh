from __future__ import annotations

import sys
from pathlib import Path


project_root = Path(__file__).resolve().parents[1]
project_components = project_root / "custom_components"

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if str(project_components) not in sys.path:
    sys.path.insert(0, str(project_components))
