#!/usr/bin/env python3
"""
Fix 1: Add budget data to client intake and improve AI prompts for budget sections
"""
import json
import sqlite3

conn = sqlite3.connect('/Users/fbwalker4/.hermes/grant-system/tracking/grants.db')
cursor = conn.cursor()

# Get current intake data
cursor.execute("SELECT intake_data FROM clients WHERE id = 'client-hermes-001'")
current_data = cursor.fetchone()[0]

if current_data:
    intake = json.loads(current_data)
else:
    intake = {}

# Add budget data
intake['budget_info'] = {
    "total_project_cost": 250000,
    "requested_amount": 200000,
    "personnel": [
        {"role": "Program Director", "annual_salary": 65000, "fringe_rate": 0.30, "percent_time": 100},
        {"role": "Case Manager", "annual_salary": 42000, "fringe_rate": 0.30, "percent_time": 100},
        {"role": "Administrative Assistant", "annual_salary": 36000, "fringe_rate": 0.30, "percent_time": 50}
    ],
    "fringe_benefits_rate": 0.30,
    "travel": [
        {"purpose": "Annual conference attendance", "cost": 2500},
        {"purpose": "Staff training", "cost": 1500}
    ],
    "supplies": [
        {"item": "Office supplies", "annual_cost": 3000},
        {"item": "Program materials", "annual_cost": 8000}
    ],
    "equipment": [
        {"item": "Computer workstations (5)", "cost": 7500},
        {"item": "Software licenses", "cost": 2400}
    ],
    "contractual": [
        {"service": "Evaluation consultant", "cost": 15000}
    ],
    "indirect_rate": 0.10,
    "indirect_base": "modified_total_direct_costs",
    "cost_sharing": 50000,
    "match": {
        "cash": 25000,
        "in_kind": 25000
    }
}

# Update client
cursor.execute("UPDATE clients SET intake_data = ? WHERE id = 'client-hermes-001'", (json.dumps(intake),))
conn.commit()

print("Added budget data to client intake")
print(f"Budget info: {json.dumps(intake['budget_info'], indent=2)[:500]}...")

conn.close()
