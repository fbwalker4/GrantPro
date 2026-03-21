"""Minimal health check for Vercel debugging"""
import os
import sys
import json
import traceback
from pathlib import Path

# Setup paths
_root = Path(__file__).parent.parent
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "core"))
sys.path.insert(0, str(_root / "research"))
sys.path.insert(0, str(_root / "portal"))
os.environ.setdefault("VERCEL", "1")

from flask import Flask
app = Flask(__name__)

@app.route("/api/health")
def health():
    steps = []
    try:
        import db_connection
        steps.append(f"db_connection OK (path={db_connection.LOCAL_DB_PATH})")
        steps.append(f"GP_DATABASE_URL={'SET' if db_connection.GP_DATABASE_URL else 'NOT SET'}")
        steps.append(f"VERCEL={os.environ.get('VERCEL', 'not set')}")

        import user_models
        steps.append("user_models OK")

        import grant_db
        steps.append("grant_db OK")

        from portal.app import app as main_app
        steps.append("portal.app imported OK")

        return json.dumps({"status": "ok", "steps": steps}, indent=2), 200, {"Content-Type": "application/json"}
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "steps": steps
        }, indent=2), 500, {"Content-Type": "application/json"}
