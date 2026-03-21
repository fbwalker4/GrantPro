"""Minimal health check endpoint for Vercel debugging"""
import json
import os
import sys
import traceback

def handler(request):
    """WSGI-compatible health check"""
    try:
        # Test imports step by step
        steps = []

        from pathlib import Path
        _root = Path(__file__).parent.parent
        sys.path.insert(0, str(_root))
        sys.path.insert(0, str(_root / "core"))
        sys.path.insert(0, str(_root / "research"))
        sys.path.insert(0, str(_root / "portal"))
        steps.append("paths OK")

        os.environ.setdefault("VERCEL", "1")
        steps.append("env OK")

        import db_connection
        steps.append(f"db_connection OK (path={db_connection.LOCAL_DB_PATH})")

        import user_models
        steps.append("user_models OK")

        import grant_db
        steps.append("grant_db OK")

        from portal.app import app as flask_app
        steps.append("flask app imported OK")

        body = json.dumps({"status": "ok", "steps": steps}, indent=2)
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": body
        }
    except Exception as e:
        body = json.dumps({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "steps": steps if 'steps' in dir() else []
        }, indent=2)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": body
        }
