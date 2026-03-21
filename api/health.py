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
        raw_url = os.environ.get('GP_DATABASE_URL', 'NONE')
        steps.append(f"raw GP_DATABASE_URL env: {'SET (' + raw_url[:30] + '...)' if raw_url != 'NONE' else 'NONE'}")
        steps.append(f"VERCEL={os.environ.get('VERCEL', 'not set')}")

        # Test direct connection
        try:
            conn = db_connection.get_connection()
            steps.append(f"connection type: {type(conn).__name__}")
            row = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
            steps.append(f"users count: {row[0] if row else 'null'}")
            conn.close()
        except Exception as ce:
            steps.append(f"connection error: {ce}")

        import user_models
        steps.append("user_models OK")

        import grant_db
        steps.append("grant_db OK")

        from portal.app import app as main_app
        steps.append("portal.app imported OK")

        # Test user lookup
        user = user_models.get_user_by_email('sarah@rivercityyouth.org')
        if user:
            steps.append(f"test user found: {user.get('first_name')} {user.get('last_name')}")
            steps.append(f"plan: {user.get('plan')}")
            pw_ok = user_models.verify_password('TestGrant2026!', user.get('password_hash', ''))
            steps.append(f"password verify: {pw_ok}")
        else:
            steps.append("test user NOT FOUND")

        return json.dumps({"status": "ok", "steps": steps}, indent=2), 200, {"Content-Type": "application/json"}
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "steps": steps
        }, indent=2), 500, {"Content-Type": "application/json"}
