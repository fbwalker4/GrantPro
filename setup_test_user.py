#!/usr/bin/env python3
import sqlite3
import json

conn = sqlite3.connect('/Users/fbwalker4/.hermes/grant-system/tracking/grants.db')
cursor = conn.cursor()

# Get user id
cursor.execute("SELECT id FROM users WHERE email = 'hermes-test-final@example.com'")
user = cursor.fetchone()

if not user:
    print("User not found")
    exit(1)

user_id = user[0]
print(f"User ID: {user_id}")

# Update user
cursor.execute("""
    UPDATE users SET 
        organization_name = 'Gulf Coast Community Development Corp',
        organization_type = 'Nonprofit',
        verified = 1,
        onboarding_completed = 1
    WHERE email = 'hermes-test-final@example.com'
""")

# Create client with full intake data
intake_data = {
    "mission": "To empower low-income families on the Mississippi Gulf Coast through after-school programs, job training, affordable housing, and community development initiatives.",
    "description": "Founded in 1995, Gulf Coast CDC operates 5 community centers across the Gulf Coast region. We have successfully completed 50+ federal grants totaling $10M in funding. Our focus areas include youth development, workforce training, housing assistance, and disaster resilience.",
    "programs": "After-school tutoring and mentorship (500+ youth annually), Job training and workforce development (200+ adults/year), Affordable housing counseling (100+ families/year), Emergency disaster relief",
    "ein": "64-1234567",
    "duns": "123456789",
    "year_founded": 1995,
    "annual_budget": 2500000,
    "staff_count": 45,
    "board_size": 12,
    "service_area": "Mississippi Gulf Coast (Hancock, Harrison, Jackson counties)",
    "population_served": "Low-income families, at-risk youth, unemployed adults, disaster-affected residents",
    "previous_grants": "HUD CDBG ($500K), DOE IEEC ($250K), USDA Rural Development ($150K)",
    "website": "www.gulfcoastcdc.org"
}

cursor.execute("""
    INSERT OR REPLACE INTO clients 
    (id, organization_name, contact_name, contact_email, status, current_stage, intake_data, user_id, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
""", (
    'client-hermes-001',
    'Gulf Coast Community Development Corp',
    'Hermes Tester',
    'hermes-test-final@example.com',
    'active',
    'research',
    json.dumps(intake_data),
    user_id
))

conn.commit()
print("Client created with full intake data")

# Verify
cursor.execute("SELECT organization_name, intake_data FROM clients WHERE id = 'client-hermes-001'")
client = cursor.fetchone()
print(f"Client: {client[0]}")
print(f"Intake data length: {len(client[1]) if client[1] else 0}")

conn.close()
