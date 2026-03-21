# Vercel serverless entry point
import sys
from pathlib import Path

# Add project paths so imports resolve correctly
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_project_root / "portal"))
sys.path.insert(0, str(_project_root / "core"))
sys.path.insert(0, str(_project_root / "research"))

from portal.app import app

# Vercel handler
app.debug = False
