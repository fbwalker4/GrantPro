# Vercel serverless entry point
import os
import sys
from pathlib import Path

# Add project paths so imports resolve correctly
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_project_root / "portal"))
sys.path.insert(0, str(_project_root / "core"))
sys.path.insert(0, str(_project_root / "research"))

# Set VERCEL env so the app knows it's serverless
os.environ.setdefault("VERCEL", "1")

# Import Flask app
from portal.app import app

# Vercel handler
app.debug = False
