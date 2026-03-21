"""Health check endpoint — returns only status, no diagnostic details."""
import os
import sys
import json
from pathlib import Path

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
    try:
        import db_connection
        conn = db_connection.get_connection()
        conn.execute("SELECT 1").fetchone()
        conn.close()
        return json.dumps({"status": "ok"}), 200, {"Content-Type": "application/json"}
    except Exception:
        return json.dumps({"status": "error"}), 500, {"Content-Type": "application/json"}
