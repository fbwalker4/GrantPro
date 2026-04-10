#!/usr/bin/env python3
"""Add organization_details fields to profile route."""
import re

with open('/Users/fbwalker4/.hermes/grant-system/portal/app.py', 'r') as f:
    content = f.read()

# 1. Fix GET handler - add organization_details loading
old_get = """    profile = user_models.get_profile(user['id'])
    profile_data = profile or {}
    return render_template('profile.html', profile=profile_data, user=user)"""

new_get = """    profile = user_models.get_profile(user['id'])
    profile_data = profile or {}
    # Load organization_details for SF-424 fields
    _c = get_db().cursor()
    _c.execute('SELECT ein, uei, address_line1, city, state, zip_code, mission_statement, congressional_district, organization_type FROM organization_details WHERE user_id=?', (user['id'],))
    _org = _c.fetchone()
    if _org:
        for col in ['ein','uei','address_line1','city','state','zip_code','mission_statement','congressional_district']:
            if col in _org and _org[col]:
                profile_data[col] = _org[col]
        if _org.get('organization_type'):
            profile_data['organization_type'] = _org['organization_type']
    return render_template('profile.html', profile=profile_data, user=user)"""

if old_get in content:
    content = content.replace(old_get, new_get)
    print("✓ GET handler updated with organization_details loading")
else:
    print("✗ GET handler pattern not found")
    # Find what's there
    idx = content.find("return render_template('profile.html'")
    if idx >= 0:
        print(f"  Found render_template at idx {idx}:")
        print(repr(content[idx-100:idx+100]))

# 2. Fix POST handler - add organization_details save
# Find the line: conn.commit() followed by flash success
old_post = """        conn.commit()
        flash('Profile saved!', 'success')
        return redirect(url_for('profile'))"""

new_post = """        conn.commit()

        # Save SF-424 required fields to organization_details
        ein = request.form.get('ein', '').strip()
        uei = request.form.get('uei', '').strip()
        address_line1 = request.form.get('address_line1', '').strip()
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()
        zip_code = request.form.get('zip_code', '').strip()
        mission_stmt = request.form.get('mission_statement', '').strip()
        cong_district = request.form.get('congressional_district', '').strip()
        org_type = request.form.get('organization_type', '').strip()
        _c.execute(
            "INSERT INTO organization_details "
            "(user_id, ein, uei, address_line1, city, state, zip_code, mission_statement, congressional_district, organization_type) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (user_id) DO UPDATE SET "
            "ein=COALESCE(EXCLUDED.ein,organization_details.ein),"
            "uei=COALESCE(EXCLUDED.uei,organization_details.uei),"
            "address_line1=COALESCE(EXCLUDED.address_line1,organization_details.address_line1),"
            "city=COALESCE(EXCLUDED.city,organization_details.city),"
            "state=COALESCE(EXCLUDED.state,organization_details.state),"
            "zip_code=COALESCE(EXCLUDED.zip_code,organization_details.zip_code),"
            "mission_statement=COALESCE(EXCLUDED.mission_statement,organization_details.mission_statement),"
            "congressional_district=COALESCE(EXCLUDED.congressional_district,organization_details.congressional_district),"
            "organization_type=COALESCE(EXCLUDED.organization_type,organization_details.organization_type)",
            (user['id'], ein, uei, address_line1, city, state, zip_code, mission_stmt, cong_district, org_type)
        )
        conn.commit()

        flash('Profile saved!', 'success')
        return redirect(url_for('profile'))"""

if old_post in content:
    content = content.replace(old_post, new_post)
    print("✓ POST handler updated with organization_details save")
else:
    print("✗ POST handler pattern not found")
    idx = content.find("conn.commit()\n        flash('Profile saved!")
    if idx >= 0:
        print(f"  Found at idx {idx}:")
        print(repr(content[idx:idx+200]))

with open('/Users/fbwalker4/.hermes/grant-system/portal/app.py', 'w') as f:
    f.write(content)
print("File saved")
