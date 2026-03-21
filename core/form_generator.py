"""
SF-424 form generator for GrantPro.

Generates a 3-page SF-424 (Application for Federal Assistance) as a PDF
BytesIO buffer using reportlab canvas drawing. Fields are populated from
grant, organization, and budget data passed in by the caller.
"""

import io
from datetime import datetime

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white


# ---------------------------------------------------------------------------
# Page constants
# ---------------------------------------------------------------------------
W, H = letter  # 612 x 792
MARGIN = 36  # 0.5 inch

# Colours
YELLOW_FILL = HexColor("#FFFDE7")
RED_BORDER = HexColor("#D32F2F")
GRAY_TEXT = HexColor("#999999")
DARK_GRAY = HexColor("#333333")
TITLE_BG = HexColor("#1A237E")
LIGHT_GRAY_BG = HexColor("#F5F5F5")


# ---------------------------------------------------------------------------
# Low-level drawing helpers
# ---------------------------------------------------------------------------

def _draw_footer(c, page_num):
    """GrantPro branded footer."""
    c.saveState()
    c.setFont("Helvetica", 7)
    c.setFillColor(GRAY_TEXT)
    c.drawString(MARGIN, 0.5 * inch, "Assembled by GrantPro.org")
    c.drawRightString(W - MARGIN, 0.5 * inch, f"Page {page_num}")
    c.restoreState()


def _draw_omb_header(c, omb_number, exp_date):
    """OMB number and expiration in top-right corner."""
    c.setFont("Helvetica", 7)
    c.setFillColor(DARK_GRAY)
    c.drawRightString(W - MARGIN, H - MARGIN + 4, f"OMB Number: {omb_number}")
    c.drawRightString(W - MARGIN, H - MARGIN - 6, f"Expiration Date: {exp_date}")


def _draw_title_bar(c, title, y, height=20):
    """Dark navy title bar with white centred text."""
    c.setFillColor(TITLE_BG)
    c.rect(MARGIN, y, W - 2 * MARGIN, height, fill=1, stroke=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(W / 2, y + 5, title)
    c.setFillColor(black)
    return y


def _draw_field_box(c, x, y, w, h, label, value, required=False,
                    label_size=6.5, value_size=9):
    """Bordered field box with small label at top and value below."""
    # Fill for required fields
    if required:
        c.setFillColor(YELLOW_FILL)
        c.rect(x, y, w, h, fill=1, stroke=0)
    # Border
    if required:
        c.setStrokeColor(RED_BORDER)
        c.setLineWidth(0.75)
    else:
        c.setStrokeColor(black)
        c.setLineWidth(0.5)
    c.rect(x, y, w, h, fill=0, stroke=1)
    c.setStrokeColor(black)
    c.setLineWidth(0.5)
    # Label
    c.setFillColor(HexColor("#555555"))
    c.setFont("Helvetica", label_size)
    label_y = y + h - label_size - 2
    c.drawString(x + 3, label_y, label)
    # Value
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", value_size)
    if value:
        value_y = label_y - value_size - 3
        if value_y < y + 2:
            value_y = y + 2
        # Truncate long values to fit box width
        text = str(value)
        c.drawString(x + 4, value_y, text)


def _draw_checkbox(c, x, y, label, checked=False, size=8):
    """Small checkbox with label text."""
    c.setLineWidth(0.5)
    c.rect(x, y, size, size, fill=0, stroke=1)
    if checked:
        c.setFont("ZapfDingbats", size - 1)
        c.drawString(x + 1, y + 1, "4")  # checkmark
    c.setFont("Helvetica", 7)
    c.setFillColor(black)
    c.drawString(x + size + 2, y + 1, label)


def _draw_section_header(c, y, full_w, text):
    """Light gray sub-section header bar."""
    c.setFillColor(LIGHT_GRAY_BG)
    c.rect(MARGIN, y, full_w, 14, fill=1, stroke=1)
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(MARGIN + 3, y + 3, text)
    return y


def _money(val):
    """Format number as $X,XXX."""
    try:
        val = float(val)
    except (TypeError, ValueError):
        return "$0"
    if val == 0:
        return "$0"
    return f"${val:,.0f}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_sf424_pages(grant_data, org_data, budget_data):
    """Generate SF-424 form pages as a PDF BytesIO buffer.

    Args:
        grant_data: dict with keys:
            grant_name, agency, amount, deadline, template
        org_data: dict with keys:
            legal_name, ein, uei, address, city, state, zip,
            contact_name, contact_title, contact_phone, contact_email
        budget_data: dict with keys:
            grand_total, match_total, total_direct, indirect_total,
            personnel_total, fringe_total, travel_total, equipment_total,
            supplies_total, contractual_total, construction_total,
            other_total
    Returns:
        BytesIO containing the 3-page SF-424 PDF.
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    full_w = W - 2 * MARGIN
    half_w = full_w / 2
    today = datetime.now().strftime("%m/%d/%Y")
    page_num = [1]

    def new_page():
        _draw_footer(c, page_num[0])
        c.showPage()
        page_num[0] += 1

    # Safely pull values with defaults
    g = grant_data or {}
    o = org_data or {}
    b = budget_data or {}

    legal_name = o.get('legal_name', '') or ''
    ein = o.get('ein', '') or ''
    uei = o.get('uei', '') or ''
    street = o.get('address', '') or ''
    city = o.get('city', '') or ''
    state = o.get('state', '') or ''
    zipcode = o.get('zip', '') or ''
    contact_name = o.get('contact_name', '') or ''
    contact_title = o.get('contact_title', '') or ''
    contact_phone = o.get('contact_phone', '') or ''
    contact_email = o.get('contact_email', '') or ''

    # Split contact_name into first/last
    name_parts = contact_name.strip().split() if contact_name else []
    first_name = name_parts[0] if len(name_parts) >= 1 else ''
    last_name = ' '.join(name_parts[1:]) if len(name_parts) >= 2 else ''

    project_title = g.get('grant_name', '') or ''
    agency = g.get('agency', '') or ''
    amount = float(g.get('amount', 0) or 0)
    deadline = g.get('deadline', '') or ''

    fed_amount = float(b.get('grand_total', 0) or 0) or amount
    match_total = float(b.get('match_total', 0) or 0)
    total_amount = fed_amount + match_total

    # =====================================================================
    # PAGE 1 — Application info, applicant info, address, contact
    # =====================================================================
    _draw_omb_header(c, "4040-0004", "12/31/2025")
    y = _draw_title_bar(c, "APPLICATION FOR FEDERAL ASSISTANCE  SF-424",
                        H - MARGIN - 28, 22)

    # Row: Type of Submission / Type of Application
    row_y = y - 42
    # Field 1: Type of Submission
    c.setStrokeColor(RED_BORDER)
    c.setLineWidth(0.75)
    c.setFillColor(YELLOW_FILL)
    c.rect(MARGIN, row_y, half_w, 40, fill=1, stroke=1)
    c.setStrokeColor(black)
    c.setLineWidth(0.5)
    c.setFillColor(DARK_GRAY)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(MARGIN + 3, row_y + 30, "* 1. Type of Submission:")
    _draw_checkbox(c, MARGIN + 8, row_y + 18, "Preapplication", False)
    _draw_checkbox(c, MARGIN + 90, row_y + 18, "Application", True)
    _draw_checkbox(c, MARGIN + 165, row_y + 18, "Changed/Corrected", False)

    # Field 2: Type of Application
    c.setStrokeColor(RED_BORDER)
    c.setLineWidth(0.75)
    c.setFillColor(YELLOW_FILL)
    c.rect(MARGIN + half_w, row_y, half_w, 40, fill=1, stroke=1)
    c.setStrokeColor(black)
    c.setLineWidth(0.5)
    c.setFillColor(DARK_GRAY)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(MARGIN + half_w + 3, row_y + 30, "* 2. Type of Application:")
    _draw_checkbox(c, MARGIN + half_w + 8, row_y + 18, "New", True)
    _draw_checkbox(c, MARGIN + half_w + 60, row_y + 18, "Continuation", False)
    _draw_checkbox(c, MARGIN + half_w + 140, row_y + 18, "Revision", False)

    # Fields 3-4
    row_y -= 22
    _draw_field_box(c, MARGIN, row_y, half_w, 20,
                    "3. Date Received:", today)
    _draw_field_box(c, MARGIN + half_w, row_y, half_w, 20,
                    "4. Applicant Identifier:", "")

    # Fields 5a-5b
    row_y -= 22
    _draw_field_box(c, MARGIN, row_y, half_w, 20,
                    "5a. Federal Entity Identifier:", "")
    _draw_field_box(c, MARGIN + half_w, row_y, half_w, 20,
                    "5b. Federal Award Identifier:", "")

    # Section 8 header - Applicant Information
    row_y -= 16
    _draw_section_header(c, row_y, full_w, "8. APPLICANT INFORMATION:")

    # 8a. Legal Name
    row_y -= 22
    _draw_field_box(c, MARGIN, row_y, full_w, 20,
                    "* a. Legal Name:", legal_name, required=True)

    # 8b. EIN, 8c. UEI
    row_y -= 22
    _draw_field_box(c, MARGIN, row_y, full_w * 0.5, 20,
                    "* b. Employer/Taxpayer ID (EIN/TIN):", ein, required=True)
    _draw_field_box(c, MARGIN + full_w * 0.5, row_y, full_w * 0.5, 20,
                    "* c. UEI:", uei, required=True)

    # 8d. Address header
    row_y -= 14
    _draw_section_header(c, row_y, full_w, "d. Address:")

    # Street
    row_y -= 28
    _draw_field_box(c, MARGIN, row_y, full_w, 26,
                    "* Street1:", street, required=True)

    # City, State, Zip
    row_y -= 28
    col_w = full_w / 3
    _draw_field_box(c, MARGIN, row_y, col_w, 26,
                    "* City:", city, required=True)
    _draw_field_box(c, MARGIN + col_w, row_y, col_w, 26,
                    "* State:", state, required=True)
    _draw_field_box(c, MARGIN + 2 * col_w, row_y, col_w, 26,
                    "* Zip / Postal Code:", zipcode, required=True)

    # Country
    row_y -= 28
    _draw_field_box(c, MARGIN, row_y, full_w, 26,
                    "* Country:", "USA: UNITED STATES", required=True)

    # 8f. Contact person header
    row_y -= 14
    _draw_section_header(c, row_y, full_w,
                         "f. Name and contact information of person to be contacted:")

    # Name fields
    row_y -= 28
    _draw_field_box(c, MARGIN, row_y, full_w * 0.5, 18,
                    "* First Name:", first_name, required=True)
    _draw_field_box(c, MARGIN + full_w * 0.5, row_y, full_w * 0.5, 18,
                    "* Last Name:", last_name, required=True)

    # Title, Phone, Email
    row_y -= 28
    _draw_field_box(c, MARGIN, row_y, full_w * 0.35, 18,
                    "Title:", contact_title)
    _draw_field_box(c, MARGIN + full_w * 0.35, row_y, full_w * 0.25, 18,
                    "Phone Number:", contact_phone)
    _draw_field_box(c, MARGIN + full_w * 0.6, row_y, full_w * 0.4, 18,
                    "* Email:", contact_email, required=True)

    _draw_footer(c, page_num[0])

    # =====================================================================
    # PAGE 2 — Agency, CFDA, funding opportunity, project title
    # =====================================================================
    new_page()
    _draw_omb_header(c, "4040-0004", "12/31/2025")
    y = H - MARGIN - 16

    # Field 9 - Type of Applicant
    y -= 28
    _draw_field_box(c, MARGIN, y, full_w, 26,
                    "* 9. Type of Applicant 1: Select Applicant Type:",
                    "M: Nonprofit with 501(c)(3) IRS Status",
                    required=True, value_size=8)

    # Field 10 - Federal Agency
    y -= 22
    _draw_field_box(c, MARGIN, y, full_w, 20,
                    "* 10. Name of Federal Agency:", agency, required=True)

    # Field 11 - CFDA
    y -= 30
    _draw_field_box(c, MARGIN, y, full_w * 0.3, 28,
                    "11. Catalog of Federal Domestic Assistance Number:",
                    g.get('cfda_number', ''))
    _draw_field_box(c, MARGIN + full_w * 0.3, y, full_w * 0.7, 28,
                    "CFDA Title:", g.get('cfda_title', ''))

    # Field 12 - Funding Opportunity
    y -= 30
    _draw_field_box(c, MARGIN, y, full_w * 0.4, 28,
                    "* 12. Funding Opportunity Number:",
                    g.get('funding_opp_number', ''), required=True)
    _draw_field_box(c, MARGIN + full_w * 0.4, y, full_w * 0.6, 28,
                    "* Title:", g.get('funding_opp_title', ''), required=True)

    # Field 13
    y -= 22
    _draw_field_box(c, MARGIN, y, full_w, 20,
                    "13. Competition Identification Number:", "")

    # Field 14
    y -= 36
    _draw_field_box(c, MARGIN, y, full_w, 34,
                    "14. Areas Affected by Project:",
                    g.get('areas_affected', ''), value_size=8)

    # Field 15 - Project Title
    y -= 50
    _draw_field_box(c, MARGIN, y, full_w, 48,
                    "* 15. Descriptive Title of Applicant's Project:",
                    project_title, required=True, value_size=10)

    _draw_footer(c, page_num[0])

    # =====================================================================
    # PAGE 3 — Congressional districts, dates, funding, certifications
    # =====================================================================
    new_page()
    _draw_omb_header(c, "4040-0004", "12/31/2025")
    y = H - MARGIN - 16

    # Field 16 - Congressional Districts
    y -= 42
    c.setFillColor(LIGHT_GRAY_BG)
    c.rect(MARGIN, y, full_w, 40, fill=1, stroke=1)
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(MARGIN + 3, y + 32, "16. Congressional Districts Of:")
    congress_dist = o.get('congressional_district', '') or \
                    (f"{state}-" if state else '')
    _draw_field_box(c, MARGIN, y, full_w * 0.5, 26,
                    "* a. Applicant:", congress_dist, required=True)
    _draw_field_box(c, MARGIN + full_w * 0.5, y, full_w * 0.5, 26,
                    "* b. Program/Project:", congress_dist, required=True)

    # Field 17 - Proposed Project Dates
    y -= 42
    c.setFillColor(LIGHT_GRAY_BG)
    c.rect(MARGIN, y, full_w, 40, fill=1, stroke=1)
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(MARGIN + 3, y + 32, "17. Proposed Project:")
    start_date = g.get('start_date', '') or ''
    end_date = g.get('end_date', '') or ''
    _draw_field_box(c, MARGIN, y, full_w * 0.5, 26,
                    "* a. Start Date:", start_date, required=True)
    _draw_field_box(c, MARGIN + full_w * 0.5, y, full_w * 0.5, 26,
                    "* b. End Date:", end_date, required=True)

    # Field 18 - Estimated Funding
    y -= 16
    _draw_section_header(c, y, full_w, "18. Estimated Funding ($):")

    funding_labels = [
        ("* a. Federal", fed_amount),
        ("* b. Applicant", match_total),
        ("c. State", 0),
        ("d. Local", 0),
        ("e. Other", 0),
        ("f. Program Income", 0),
        ("* g. TOTAL", total_amount),
    ]
    for label, amt_val in funding_labels:
        y -= 24
        req = label.startswith("*")
        # Label box
        c.setStrokeColor(RED_BORDER if req else black)
        c.setLineWidth(0.75 if req else 0.5)
        c.rect(MARGIN, y, full_w * 0.6, 22, fill=0, stroke=1)
        c.setStrokeColor(black)
        c.setLineWidth(0.5)
        c.setFillColor(HexColor("#555555"))
        c.setFont("Helvetica", 7)
        c.drawString(MARGIN + 4, y + 12, label)
        # Amount box
        if req:
            c.setFillColor(YELLOW_FILL)
            c.rect(MARGIN + full_w * 0.6, y, full_w * 0.4, 22, fill=1, stroke=0)
        c.setStrokeColor(RED_BORDER if req else black)
        c.setLineWidth(0.75 if req else 0.5)
        c.rect(MARGIN + full_w * 0.6, y, full_w * 0.4, 22, fill=0, stroke=1)
        c.setStrokeColor(black)
        c.setLineWidth(0.5)
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(MARGIN + full_w * 0.6 + 8, y + 6, _money(amt_val))

    # Field 19 - Executive Order 12372
    y -= 30
    c.setFillColor(LIGHT_GRAY_BG)
    c.rect(MARGIN, y, full_w, 28, fill=1, stroke=1)
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(MARGIN + 3, y + 18,
                 "* 19. Is Application Subject to Review By State "
                 "Under Executive Order 12372 Process?")
    _draw_checkbox(c, MARGIN + 8, y + 5,
                   "c. Program is not covered by E.O. 12372.", True)

    # Field 20 - Delinquent on Federal Debt
    y -= 28
    c.setStrokeColor(RED_BORDER)
    c.setLineWidth(0.75)
    c.setFillColor(YELLOW_FILL)
    c.rect(MARGIN, y, full_w, 24, fill=1, stroke=1)
    c.setStrokeColor(black)
    c.setLineWidth(0.5)
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(MARGIN + 3, y + 14,
                 "* 20. Is the Applicant Delinquent On Any Federal Debt?")
    _draw_checkbox(c, MARGIN + 8, y + 2, "Yes", False)
    _draw_checkbox(c, MARGIN + 60, y + 2, "No", True)

    # Field 21 - Certification
    y -= 50
    c.setStrokeColor(black)
    c.rect(MARGIN, y, full_w, 48, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(MARGIN + 3, y + 36,
                 "21. *By signing this application, I certify (1) to the "
                 "statements contained in the list of certifications**")
    c.setFont("Helvetica", 7)
    c.drawString(MARGIN + 8, y + 24,
                 "and (2) that the statements herein are true, complete "
                 "and accurate to the best of my knowledge.")
    c.drawString(MARGIN + 8, y + 14,
                 "I also provide the required assurances and agree to "
                 "comply with any resulting terms if I accept an award.")
    c.drawString(MARGIN + 8, y + 4,
                 "I am aware that false, fictitious, or fraudulent "
                 "statements may subject me to criminal, civil, or "
                 "administrative penalties.")

    # Authorized Representative
    y -= 16
    _draw_section_header(c, y, full_w, "Authorized Representative:")

    # Signature fields
    y -= 20
    cw = full_w / 2
    _draw_field_box(c, MARGIN, y, cw, 18,
                    "* First Name:", first_name, required=True)
    _draw_field_box(c, MARGIN + cw, y, cw, 18,
                    "* Last Name:", last_name, required=True)

    y -= 20
    _draw_field_box(c, MARGIN, y, full_w * 0.35, 18,
                    "* Title:", contact_title, required=True)
    _draw_field_box(c, MARGIN + full_w * 0.35, y, full_w * 0.25, 18,
                    "* Phone:", contact_phone, required=True)
    _draw_field_box(c, MARGIN + full_w * 0.6, y, full_w * 0.4, 18,
                    "* Email:", contact_email, required=True)

    # Signature and date
    y -= 22
    sig_text = f"{contact_name} (electronically signed)" if contact_name else ""
    _draw_field_box(c, MARGIN, y, full_w * 0.65, 20,
                    "* Signature of Authorized Representative:", sig_text,
                    required=True, value_size=8)
    _draw_field_box(c, MARGIN + full_w * 0.65, y, full_w * 0.35, 20,
                    "* Date Signed:", today, required=True)

    _draw_footer(c, page_num[0])
    c.save()
    buf.seek(0)
    return buf
