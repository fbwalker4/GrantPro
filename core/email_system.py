#!/usr/bin/env python3
"""
Email System for Grant Writing Business
Uses Resend API for transactional emails
"""

import os
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import json

# Resend configuration
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'Grant Writer Pro <noreply@grantwriterpro.local>')
FROM_NAME = os.environ.get('FROM_NAME', 'Grant Writer Pro')
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5001')

# Database path
from db_connection import LOCAL_DB_PATH as DB_PATH
from db_connection import get_connection
EMAIL_LOG_PATH = Path.home() / ".hermes" / "grant-system" / "tracking" / "email_log.db"
LEADS_PATH = Path.home() / ".hermes" / "grant-system" / "tracking" / "leads.db"


# ============ HTML EMAIL TEMPLATE ============

def wrap_in_html(body_content: str, subject: str = "", preheader: str = "") -> str:
    """Wrap content in professional HTML email template"""
    
    unsubscribe_link = f"{BASE_URL}/unsubscribe?email={{email}}"
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>{subject}</title>
    <!--[if mso]>
    <style type="text/css">
        table {{ border-collapse: collapse; }}
        td {{ padding: 0; }}
    </style>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333;">
    
    <!-- Preheader (hidden preview text) -->
    <span style="display: none; font-size: 1px; color: #fefefe; line-height: 1px; max-height: 0; max-width: 0; opacity: 0; overflow: hidden;">
        {preheader}
    </span>
    
    <!-- Header -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);">
        <tr>
            <td align="center" style="padding: 20px;">
                <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width: 600px;">
                    <tr>
                        <td style="padding: 20px 0; text-align: center;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700;">
                                📝 Grant Writer Pro
                            </h1>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
    
    <!-- Main Content -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width: 600px;">
                    <tr>
                        <td style="padding: 0 20px;">
                            {body_content}
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
    
    <!-- Footer -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f5;">
        <tr>
            <td align="center" style="padding: 30px 20px;">
                <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width: 600px;">
                    <tr>
                        <td style="text-align: center; color: #666666; font-size: 14px;">
                            <p style="margin: 0 0 10px;">
                                <strong>Grant Writer Pro</strong><br>
                                Mississippi Gulf Coast
                            </p>
                            <p style="margin: 0 0 15px;">
                                <a href="{BASE_URL}" style="color: #6366f1; text-decoration: none;">Visit Website</a> • 
                                <a href="{BASE_URL}/wizard" style="color: #6366f1; text-decoration: none;">Search Grants</a> • 
                                <a href="{BASE_URL}/dashboard" style="color: #6366f1; text-decoration: none;">Dashboard</a>
                            </p>
                            <p style="margin: 0; font-size: 12px; color: #999;">
                                © 2026 Grant Writer Pro. All rights reserved.<br>
                                <br>
                                <a href="{unsubscribe_link}" style="color: #999; text-decoration: underline;">
                                    Unsubscribe
                                </a> from these emails
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
    
</body>
</html>
"""


# ============ EMAIL TEMPLATES ============

def get_welcome_email(first_name: str = "there") -> Dict:
    """Get welcome email content"""
    subject = "Welcome to Grant Writer Pro - Let's Get You Funded"
    preheader = "Start finding and winning grants with AI assistance"
    
    body = """
    <h2 style="margin: 0 0 20px; color: #1e3a5f; font-size: 24px; font-weight: 700;">
        Welcome aboard, {first_name}! 🎉
    </h2>
    
    <p style="margin: 0 0 20px; font-size: 16px; color: #333;">
        We're excited to help you find and win grants. Our AI-powered platform makes grant research and writing easier than ever.
    </p>
    
    <!-- CTA Button -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
        <tr>
            <td align="center">
                <a href="{base_url}/wizard" style="display: inline-block; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: #ffffff; padding: 14px 32px; font-size: 16px; font-weight: 600; text-decoration: none; border-radius: 8px;">
                    🔍 Search Grants Now
                </a>
            </td>
        </tr>
    </table>
    
    <h3 style="margin: 30px 0 15px; color: #1e3a5f; font-size: 18px;">
        Here's what you can do right now:
    </h3>
    
    <ul style="margin: 0 0 20px; padding-left: 20px; color: #333;">
        <li style="margin-bottom: 10px;"><strong>Search 131+ federal grants</strong> - Find funding for your organization</li>
        <li style="margin-bottom: 10px;"><strong>AI-assisted writing</strong> - Get help drafting your applications</li>
        <li style="margin-bottom: 10px;"><strong>Guided submission</strong> - Submit directly to Grants.gov</li>
    </ul>
    
    <p style="margin: 30px 0 0; font-size: 14px; color: #666;">
        Need help? Just reply to this email - we're here to help you get funded!
    </p>
    
    <p style="margin: 10px 0 0; font-size: 16px; color: #333;">
        Best,<br>
        <strong>The Grant Writer Pro Team</strong>
    </p>
    """.format(first_name=first_name, base_url=BASE_URL)
    
    return {
        "subject": subject,
        "html": wrap_in_html(body, subject, preheader)
    }


def get_weekly_alerts_email(grants: List[Dict], count: int) -> Dict:
    """Get weekly grant alerts email content"""
    subject = f"🔔 {count} New Grants That Match Your Interests"
    preheader = f"You have {count} new grant opportunities waiting for you"
    
    # Build grants list HTML
    grants_html = ""
    for grant in grants[:8]:
        grants_html += f"""
        <tr>
            <td style="padding: 15px; background: #f8f9fa; border-radius: 8px; margin-bottom: 10px;">
                <h4 style="margin: 0 0 8px; font-size: 16px; color: #1e3a5f;">
                    {grant.get('title', 'Untitled Grant')}
                </h4>
                <p style="margin: 0 0 8px; font-size: 14px; color: #666;">
                    <strong>{grant.get('agency', 'Federal')}</strong> • 
                    ${grant.get('amount_min', 0):,.0f} - ${grant.get('amount_max', 0):,.0f}
                </p>
                <a href="{BASE_URL}/grant/{grant.get('id', '')}" style="color: #6366f1; text-decoration: none; font-size: 14px;">
                    View Details →
                </a>
            </td>
        </tr>
        """
    
    body = f"""
    <h2 style="margin: 0 0 20px; color: #1e3a5f; font-size: 24px; font-weight: 700;">
        New Grants Alert 🔔
    </h2>
    
    <p style="margin: 0 0 20px; font-size: 16px; color: #333;">
        Here are {count} new funding opportunities that might be a great fit for your organization:
    </p>
    
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 20px 0;">
        {grants_html}
    </table>
    
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
        <tr>
            <td align="center">
                <a href="{BASE_URL}/dashboard" style="display: inline-block; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: #ffffff; padding: 14px 32px; font-size: 16px; font-weight: 600; text-decoration: none; border-radius: 8px;">
                    View All Saved Grants
                </a>
            </td>
        </tr>
    </table>
    
    <p style="margin: 20px 0 0; font-size: 14px; color: #666;">
        Too many emails? <a href="{BASE_URL}/profile" style="color: #6366f1;">Update your notification preferences</a>
    </p>
    """
    
    return {
        "subject": subject,
        "html": wrap_in_html(body, subject, preheader)
    }


def get_deadline_reminder_email(grant: Dict, days_until: int) -> Dict:
    """Get deadline reminder email content"""
    subject = f"⏰ Deadline Alert: {grant.get('title', 'Grant')} due in {days_until} days"
    preheader = f"Don't miss out - only {days_until} days left to apply!"
    
    urgency_color = "#dc2626" if days_until <= 3 else "#f59e0b" if days_until <= 7 else "#6366f1"
    
    body = f"""
    <h2 style="margin: 0 0 20px; color: #1e3a5f; font-size: 24px; font-weight: 700;">
        ⏰ Grant Deadline Alert
    </h2>
    
    <div style="background: {urgency_color}; color: white; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
        <div style="font-size: 32px; font-weight: 700;">{days_until}</div>
        <div style="font-size: 14px; opacity: 0.9;">days remaining</div>
    </div>
    
    <h3 style="margin: 20px 0 10px; color: #1e3a5f; font-size: 18px;">
        {grant.get('title', 'Untitled Grant')}
    </h3>
    
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 15px 0; background: #f8f9fa; border-radius: 8px;">
        <tr>
            <td style="padding: 15px;">
                <p style="margin: 5px 0; font-size: 14px; color: #666;">
                    <strong>🏛️ Agency:</strong> {grant.get('agency', 'Federal')}
                </p>
                <p style="margin: 5px 0; font-size: 14px; color: #666;">
                    <strong>💰 Amount:</strong> ${grant.get('amount_min', 0):,.0f} - ${grant.get('amount_max', 0):,.0f}
                </p>
                <p style="margin: 5px 0; font-size: 14px; color: #666;">
                    <strong>📅 Deadline:</strong> {grant.get('deadline', 'TBD')}
                </p>
            </td>
        </tr>
    </table>
    
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
        <tr>
            <td align="center">
                <a href="{BASE_URL}/grant/{grant.get('id', '')}" style="display: inline-block; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: #ffffff; padding: 14px 32px; font-size: 16px; font-weight: 600; text-decoration: none; border-radius: 8px;">
                    Start Application →
                </a>
            </td>
        </tr>
    </table>
    
    <p style="margin: 20px 0 0; font-size: 14px; color: #666;">
        Don't wait until the last minute! Start your application now to have time for revisions.
    </p>
    """
    
    return {
        "subject": subject,
        "html": wrap_in_html(body, subject, preheader)
    }


def get_grant_saved_confirmation_email(grant: Dict) -> Dict:
    """Get grant saved confirmation email"""
    subject = f"✅ Grant Saved: {grant.get('title', 'Grant')}"
    preheader = "Your grant has been saved to your dashboard"
    
    body = f"""
    <h2 style="margin: 0 0 20px; color: #10b981; font-size: 24px; font-weight: 700;">
        ✅ Grant Saved!
    </h2>
    
    <p style="margin: 0 0 20px; font-size: 16px; color: #333;">
        We've saved this grant to your dashboard. Here's a quick summary:
    </p>
    
    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
        <h3 style="margin: 0 0 10px; color: #1e3a5f; font-size: 18px;">
            {grant.get('title', 'Untitled Grant')}
        </h3>
        <p style="margin: 5px 0; font-size: 14px; color: #666;">
            <strong>🏛️ Agency:</strong> {grant.get('agency', 'Federal')}
        </p>
        <p style="margin: 5px 0; font-size: 14px; color: #666;">
            <strong>💰 Funding:</strong> ${grant.get('amount_min', 0):,.0f} - ${grant.get('amount_max', 0):,.0f}
        </p>
        <p style="margin: 5px 0; font-size: 14px; color: #666;">
            <strong>📅 Deadline:</strong> {grant.get('deadline', 'TBD')}
        </p>
    </div>
    
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
        <tr>
            <td align="center">
                <a href="{BASE_URL}/grant/{grant.get('id', '')}" style="display: inline-block; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: #ffffff; padding: 14px 32px; font-size: 16px; font-weight: 600; text-decoration: none; border-radius: 8px;">
                    View Grant Details
                </a>
            </td>
        </tr>
    </table>
    """
    
    return {
        "subject": subject,
        "html": wrap_in_html(body, subject, preheader)
    }


def get_unsubscribe_confirmation_email(email: str) -> Dict:
    """Get unsubscribed confirmation"""
    subject = "You're Unsubscribed - We'll Miss You!"
    preheader = "You've been removed from our email list"
    
    body = f"""
    <h2 style="margin: 0 0 20px; color: #1e3a5f; font-size: 24px; font-weight: 700;">
        You're Unsubscribed 😢
    </h2>
    
    <p style="margin: 0 0 20px; font-size: 16px; color: #333;">
        You've been removed from our grant alert emails. We'll miss you!
    </p>
    
    <p style="margin: 0 0 20px; font-size: 14px; color: #666;">
        If you unsubscribed by mistake, or want to resubscribe in the future, 
        just visit our site and sign up again.
    </p>
    
    <p style="margin: 30px 0 0; font-size: 14px; color: #666;">
        Best,<br>
        <strong>The Grant Writer Pro Team</strong>
    </p>
    """
    
    return {
        "subject": subject,
        "html": wrap_in_html(body, subject, preheader)
    }


# ============ RESEND INTEGRATION ============

def send_via_resend(to_email: str, subject: str, html_body: str) -> Dict:
    """Send email via Resend API"""
    
    if not RESEND_API_KEY:
        return {
            "success": False,
            "message": "RESEND_API_KEY not configured",
            "resend_id": None
        }
    
    try:
        import resend
        
        response = resend.emails.send({
            "from": FROM_EMAIL,
            "to": to_email,
            "subject": subject,
            "html": html_body
        })
        
        return {
            "success": True,
            "message": "Email sent successfully",
            "resend_id": response.get("id")
        }
    except ImportError:
        return {
            "success": False,
            "message": "resend package not installed (pip install resend)",
            "resend_id": None
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Resend API error: {str(e)}",
            "resend_id": None
        }


def send_email(to_email: str, subject: str, html_body: str, template_name: str = None) -> Dict:
    """Send an email via Resend"""
    
    # Try Resend
    result = send_via_resend(to_email, subject, html_body)
    
    # Always log
    log_email(to_email, subject, template_name, result)
    
    if result["success"]:
        return {
            "success": True,
            "message": f"Sent via Resend: {result['resend_id']}",
            "method": "resend"
        }
    
    # Fallback
    return {
        "success": True,
        "message": f"Resend unavailable, logged: {result['message']}",
        "method": "queued"
    }


# ============ EMAIL LOGGING ============

def init_email_db():
    """Initialize email database.

    On Postgres the tables are created via supabase_migration.sql.
    """
    EMAIL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = get_connection()
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS email_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                to_email TEXT NOT NULL,
                subject TEXT NOT NULL,
                template_name TEXT,
                status TEXT DEFAULT 'sent',
                method TEXT,
                resend_id TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS email_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                to_email TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                template_name TEXT,
                scheduled_for TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        ''')
    except Exception:
        pass  # Tables already exist on Postgres

    try:
        conn.commit()
    except Exception:
        pass
    conn.close()


def log_email(to_email: str, subject: str, template_name: str, result: Dict):
    """Log email to database"""
    init_email_db()
    
    conn = get_connection()
    conn.execute('''
        INSERT INTO email_log (to_email, subject, template_name, status, method, resend_id, error_message, sent_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        to_email,
        subject,
        template_name,
        "sent" if result["success"] else "failed",
        result.get("method"),
        result.get("resend_id"),
        result.get("message"),
        datetime.now().isoformat() if result["success"] else None
    ))
    conn.commit()
    conn.close()


def get_email_stats() -> Dict:
    """Get email statistics"""
    init_email_db()
    
    conn = get_connection()
    
    total = conn.execute("SELECT COUNT(*) FROM email_log WHERE status = 'sent'").fetchone()[0]
    
    by_template = conn.execute('''
        SELECT template_name, COUNT(*) as count 
        FROM email_log 
        GROUP BY template_name
    ''').fetchall()
    
    recent = conn.execute('''
        SELECT * FROM email_log 
        ORDER BY created_at DESC 
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    return {
        "total_sent": total,
        "by_template": [dict(t) for t in by_template],
        "recent": [dict(r) for r in recent]
    }


def get_award_congratulations_email(grant_name: str, org_name: str, testimonial_url: str) -> Dict:
    """Get award congratulations email content"""
    subject = f"Congratulations on your {grant_name} award!"
    preheader = f"Great news for {org_name} - share your experience with GrantPro"

    body = f"""
    <h2 style="margin: 0 0 20px; color: #10b981; font-size: 24px; font-weight: 700;">
        Congratulations, {org_name}!
    </h2>

    <p style="margin: 0 0 20px; font-size: 16px; color: #333;">
        We are thrilled to see that your organization has been awarded the
        <strong>{grant_name}</strong> grant. This is a tremendous achievement and
        a testament to the hard work you put into your application.
    </p>

    <p style="margin: 0 0 20px; font-size: 16px; color: #333;">
        Your success story can inspire other organizations seeking funding.
        Would you take a moment to share your experience with Grant Writer Pro?
    </p>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
        <tr>
            <td align="center">
                <a href="{testimonial_url}" style="display: inline-block; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: #ffffff; padding: 14px 32px; font-size: 16px; font-weight: 600; text-decoration: none; border-radius: 8px;">
                    Share Your Experience
                </a>
            </td>
        </tr>
    </table>

    <p style="margin: 20px 0 0; font-size: 14px; color: #666;">
        Thank you for choosing Grant Writer Pro. We look forward to helping you
        with future grant opportunities!
    </p>

    <p style="margin: 10px 0 0; font-size: 16px; color: #333;">
        Best,<br>
        <strong>The Grant Writer Pro Team</strong>
    </p>
    """

    return {
        "subject": subject,
        "html": wrap_in_html(body, subject, preheader)
    }


def send_award_congratulations(email: str, grant_name: str, org_name: str, testimonial_url: str) -> Dict:
    """Send award congratulations email with testimonial link.

    If Resend is not configured the email content is logged to the console
    so the message is never silently lost.
    """
    content = get_award_congratulations_email(grant_name, org_name, testimonial_url)
    result = send_email(email, content["subject"], content["html"], "award_congratulations")

    if result.get("method") == "queued":
        # Resend unavailable — print to console so the operator can see it
        print(f"[EMAIL] To: {email}")
        print(f"[EMAIL] Subject: {content['subject']}")
        print(f"[EMAIL] Testimonial URL: {testimonial_url}")

    return result


# ============ SUBSCRIPTION LIFECYCLE EMAIL TEMPLATES ============

def get_renewal_reminder_email(first_name: str, plan: str, renewal_date: str, amount: float) -> Dict:
    """Upcoming renewal reminder"""
    subject = f"Your GrantPro subscription renews on {renewal_date}"
    preheader = f"Your {plan} plan will automatically renew"

    plan_label = plan.replace('_', ' ').title()

    body = f"""
    <h2 style="margin: 0 0 20px; color: #1e3a5f; font-size: 24px; font-weight: 700;">
        Hi {first_name}, your subscription is renewing soon
    </h2>

    <p style="margin: 0 0 20px; font-size: 16px; color: #333;">
        Just a heads-up that your <strong>{plan_label}</strong> plan will automatically renew on
        <strong>{renewal_date}</strong> for <strong>${amount:,.2f}</strong>.
    </p>

    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
        <p style="margin: 5px 0; font-size: 14px; color: #666;">
            <strong>Plan:</strong> {plan_label}
        </p>
        <p style="margin: 5px 0; font-size: 14px; color: #666;">
            <strong>Amount:</strong> ${amount:,.2f}
        </p>
        <p style="margin: 5px 0; font-size: 14px; color: #666;">
            <strong>Renewal date:</strong> {renewal_date}
        </p>
    </div>

    <p style="margin: 0 0 20px; font-size: 16px; color: #333;">
        No action is needed if you'd like to continue. If you want to update your payment method
        or change your plan, you can do so from your account.
    </p>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
        <tr>
            <td align="center">
                <a href="{BASE_URL}/subscription/manage" style="display: inline-block; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: #ffffff; padding: 14px 32px; font-size: 16px; font-weight: 600; text-decoration: none; border-radius: 8px;">
                    Manage Subscription
                </a>
            </td>
        </tr>
    </table>

    <p style="margin: 20px 0 0; font-size: 16px; color: #333;">
        Best,<br>
        <strong>The Grant Writer Pro Team</strong>
    </p>
    """

    return {
        "subject": subject,
        "html": wrap_in_html(body, subject, preheader)
    }


def get_dunning_email_1(first_name: str) -> Dict:
    """First dunning email -- calm and helpful"""
    subject = "Your GrantPro payment didn't go through"
    preheader = "We had trouble processing your payment"

    body = f"""
    <h2 style="margin: 0 0 20px; color: #1e3a5f; font-size: 24px; font-weight: 700;">
        Hi {first_name}, your payment didn't go through
    </h2>

    <p style="margin: 0 0 20px; font-size: 16px; color: #333;">
        This happens sometimes. Your card may have expired, or your bank may have
        flagged the transaction. We'll retry automatically, but you can also update
        your payment method right now to avoid any interruption to your service.
    </p>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
        <tr>
            <td align="center">
                <a href="{BASE_URL}/subscription/manage" style="display: inline-block; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: #ffffff; padding: 14px 32px; font-size: 16px; font-weight: 600; text-decoration: none; border-radius: 8px;">
                    Update Payment Method
                </a>
            </td>
        </tr>
    </table>

    <p style="margin: 20px 0 0; font-size: 14px; color: #666;">
        If you have any questions, just reply to this email. We're happy to help.
    </p>

    <p style="margin: 10px 0 0; font-size: 16px; color: #333;">
        Best,<br>
        <strong>The Grant Writer Pro Team</strong>
    </p>
    """

    return {
        "subject": subject,
        "html": wrap_in_html(body, subject, preheader)
    }


def get_dunning_email_2(first_name: str) -> Dict:
    """Second dunning email -- more direct"""
    subject = "Action needed: Update your payment method"
    preheader = "We've retried your payment and it still didn't work"

    body = f"""
    <h2 style="margin: 0 0 20px; color: #1e3a5f; font-size: 24px; font-weight: 700;">
        {first_name}, we still can't process your payment
    </h2>

    <p style="margin: 0 0 20px; font-size: 16px; color: #333;">
        We've retried your payment and it still didn't work. Please update your payment
        method to keep your GrantPro subscription active and maintain access to your
        saved grants, applications, and AI writing tools.
    </p>

    <div style="background: #fef3c7; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f59e0b;">
        <p style="margin: 0; font-size: 14px; color: #92400e;">
            <strong>Your account is currently past due.</strong> Your access will continue for now,
            but please update your payment to avoid any service interruption.
        </p>
    </div>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
        <tr>
            <td align="center">
                <a href="{BASE_URL}/subscription/manage" style="display: inline-block; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: #ffffff; padding: 14px 32px; font-size: 16px; font-weight: 600; text-decoration: none; border-radius: 8px;">
                    Update Payment Method Now
                </a>
            </td>
        </tr>
    </table>

    <p style="margin: 10px 0 0; font-size: 16px; color: #333;">
        Best,<br>
        <strong>The Grant Writer Pro Team</strong>
    </p>
    """

    return {
        "subject": subject,
        "html": wrap_in_html(body, subject, preheader)
    }


def get_dunning_email_3(first_name: str, suspension_date: str) -> Dict:
    """Third dunning email -- clear consequences"""
    subject = f"Your GrantPro account will be suspended on {suspension_date}"
    preheader = "Final notice: please update your payment method"

    body = f"""
    <h2 style="margin: 0 0 20px; color: #dc2626; font-size: 24px; font-weight: 700;">
        {first_name}, this is your final payment notice
    </h2>

    <p style="margin: 0 0 20px; font-size: 16px; color: #333;">
        We've been unable to process your subscription payment after multiple attempts.
        If we don't receive payment, your account will be suspended on
        <strong>{suspension_date}</strong>.
    </p>

    <div style="background: #fee2e2; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #dc2626;">
        <p style="margin: 0 0 10px; font-size: 14px; color: #991b1b;">
            <strong>What happens if your account is suspended:</strong>
        </p>
        <ul style="margin: 0; padding-left: 20px; font-size: 14px; color: #991b1b;">
            <li>You'll lose access to your saved grants and applications</li>
            <li>AI writing tools will be disabled</li>
            <li>After 90 days, your data will be permanently deleted</li>
        </ul>
    </div>

    <p style="margin: 0 0 20px; font-size: 16px; color: #333;">
        You can fix this right now by updating your payment method:
    </p>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
        <tr>
            <td align="center">
                <a href="{BASE_URL}/subscription/manage" style="display: inline-block; background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); color: #ffffff; padding: 14px 32px; font-size: 16px; font-weight: 600; text-decoration: none; border-radius: 8px;">
                    Update Payment Method Now
                </a>
            </td>
        </tr>
    </table>

    <p style="margin: 10px 0 0; font-size: 16px; color: #333;">
        Best,<br>
        <strong>The Grant Writer Pro Team</strong>
    </p>
    """

    return {
        "subject": subject,
        "html": wrap_in_html(body, subject, preheader)
    }


def get_account_suspended_email(first_name: str, deletion_date: str) -> Dict:
    """Account suspended notification"""
    subject = "Your GrantPro account has been suspended"
    preheader = "Your account access has been suspended due to non-payment"

    body = f"""
    <h2 style="margin: 0 0 20px; color: #dc2626; font-size: 24px; font-weight: 700;">
        {first_name}, your account has been suspended
    </h2>

    <p style="margin: 0 0 20px; font-size: 16px; color: #333;">
        Due to multiple failed payment attempts, your GrantPro subscription has been suspended.
        You no longer have access to paid features, but your data is safe for now.
    </p>

    <div style="background: #fee2e2; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #dc2626;">
        <p style="margin: 0; font-size: 14px; color: #991b1b;">
            <strong>Your data will be permanently deleted on {deletion_date}</strong> unless
            you reactivate your subscription before then.
        </p>
    </div>

    <p style="margin: 0 0 10px; font-size: 16px; color: #333;">
        You can reactivate at any time by updating your payment method:
    </p>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
        <tr>
            <td align="center">
                <a href="{BASE_URL}/subscription/manage" style="display: inline-block; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: #ffffff; padding: 14px 32px; font-size: 16px; font-weight: 600; text-decoration: none; border-radius: 8px;">
                    Reactivate Subscription
                </a>
            </td>
        </tr>
    </table>

    <p style="margin: 0 0 20px; font-size: 14px; color: #666;">
        Want to export your data before deletion? You can download it here:
    </p>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 10px 0 30px;">
        <tr>
            <td align="center">
                <a href="{BASE_URL}/account/export-data" style="display: inline-block; background: #f4f4f5; color: #333; padding: 12px 28px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 8px; border: 1px solid #d4d4d8;">
                    Export My Data
                </a>
            </td>
        </tr>
    </table>

    <p style="margin: 10px 0 0; font-size: 16px; color: #333;">
        Best,<br>
        <strong>The Grant Writer Pro Team</strong>
    </p>
    """

    return {
        "subject": subject,
        "html": wrap_in_html(body, subject, preheader)
    }


def get_suspension_reminder_email(first_name: str, days_remaining: int, deletion_date: str) -> Dict:
    """Periodic reminder during suspension"""
    subject = f"Your GrantPro data will be deleted in {days_remaining} days"
    preheader = f"You have {days_remaining} days to reactivate before data deletion"

    body = f"""
    <h2 style="margin: 0 0 20px; color: #1e3a5f; font-size: 24px; font-weight: 700;">
        {first_name}, your data deletion is approaching
    </h2>

    <div style="background: #dc2626; color: white; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
        <div style="font-size: 32px; font-weight: 700;">{days_remaining}</div>
        <div style="font-size: 14px; opacity: 0.9;">days until data deletion</div>
    </div>

    <p style="margin: 0 0 20px; font-size: 16px; color: #333;">
        Your GrantPro account was suspended due to payment issues. All of your data,
        including saved grants, applications, and organization details, will be
        <strong>permanently deleted on {deletion_date}</strong>.
    </p>

    <p style="margin: 0 0 20px; font-size: 16px; color: #333;">
        To keep your data and restore access, reactivate your subscription:
    </p>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
        <tr>
            <td align="center">
                <a href="{BASE_URL}/subscription/manage" style="display: inline-block; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: #ffffff; padding: 14px 32px; font-size: 16px; font-weight: 600; text-decoration: none; border-radius: 8px;">
                    Reactivate Subscription
                </a>
            </td>
        </tr>
    </table>

    <p style="margin: 0 0 20px; font-size: 14px; color: #666;">
        Or export your data before it's deleted:
        <a href="{BASE_URL}/account/export-data" style="color: #6366f1; text-decoration: none;">Export My Data</a>
    </p>

    <p style="margin: 10px 0 0; font-size: 16px; color: #333;">
        Best,<br>
        <strong>The Grant Writer Pro Team</strong>
    </p>
    """

    return {
        "subject": subject,
        "html": wrap_in_html(body, subject, preheader)
    }


def get_cancellation_confirmation_email(first_name: str, end_date: str) -> Dict:
    """Cancellation confirmation"""
    subject = "Your GrantPro subscription has been canceled"
    preheader = "Your subscription will remain active until the end of your billing period"

    body = f"""
    <h2 style="margin: 0 0 20px; color: #1e3a5f; font-size: 24px; font-weight: 700;">
        {first_name}, your cancellation is confirmed
    </h2>

    <p style="margin: 0 0 20px; font-size: 16px; color: #333;">
        We're sorry to see you go. Your GrantPro subscription has been canceled, but you'll
        continue to have full access until <strong>{end_date}</strong>.
    </p>

    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
        <p style="margin: 0 0 10px; font-size: 14px; color: #666;">
            <strong>What happens next:</strong>
        </p>
        <ul style="margin: 0; padding-left: 20px; font-size: 14px; color: #666;">
            <li style="margin-bottom: 8px;">Your access continues until {end_date}</li>
            <li style="margin-bottom: 8px;">After that, you'll move to the free plan (search only)</li>
            <li style="margin-bottom: 8px;">Your saved grants and applications will still be visible but read-only</li>
            <li>You can resubscribe at any time to regain full access</li>
        </ul>
    </div>

    <p style="margin: 0 0 20px; font-size: 16px; color: #333;">
        Changed your mind? You can reactivate anytime before {end_date}:
    </p>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
        <tr>
            <td align="center">
                <a href="{BASE_URL}/subscription/manage" style="display: inline-block; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: #ffffff; padding: 14px 32px; font-size: 16px; font-weight: 600; text-decoration: none; border-radius: 8px;">
                    Reactivate Subscription
                </a>
            </td>
        </tr>
    </table>

    <p style="margin: 10px 0 0; font-size: 16px; color: #333;">
        Best,<br>
        <strong>The Grant Writer Pro Team</strong>
    </p>
    """

    return {
        "subject": subject,
        "html": wrap_in_html(body, subject, preheader)
    }


def get_final_deletion_warning_email(first_name: str, deletion_date: str) -> Dict:
    """Last-chance warning before permanent data deletion"""
    subject = "Last chance: Your GrantPro data will be permanently deleted in 7 days"
    preheader = "This is your final warning before permanent data deletion"

    body = f"""
    <h2 style="margin: 0 0 20px; color: #dc2626; font-size: 24px; font-weight: 700;">
        {first_name}, this is your final warning
    </h2>

    <div style="background: #dc2626; color: white; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
        <div style="font-size: 18px; font-weight: 700;">PERMANENT DELETION ON {deletion_date.upper()}</div>
        <div style="font-size: 14px; opacity: 0.9; margin-top: 8px;">7 days remaining</div>
    </div>

    <p style="margin: 0 0 20px; font-size: 16px; color: #333;">
        Your GrantPro account has been suspended for over 80 days. In 7 days, on
        <strong>{deletion_date}</strong>, all of your data will be <strong>permanently
        and irreversibly deleted</strong>, including:
    </p>

    <ul style="margin: 0 0 20px; padding-left: 20px; color: #333;">
        <li style="margin-bottom: 8px;">All saved grants and applications</li>
        <li style="margin-bottom: 8px;">Organization details and grant readiness profile</li>
        <li style="margin-bottom: 8px;">Draft grant documents</li>
        <li style="margin-bottom: 8px;">Account history and preferences</li>
    </ul>

    <p style="margin: 0 0 10px; font-size: 16px; color: #333;">
        <strong>You have two options:</strong>
    </p>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 20px 0;">
        <tr>
            <td align="center" style="padding: 5px;">
                <a href="{BASE_URL}/subscription/manage" style="display: inline-block; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: #ffffff; padding: 14px 32px; font-size: 16px; font-weight: 600; text-decoration: none; border-radius: 8px;">
                    Reactivate Subscription
                </a>
            </td>
        </tr>
        <tr>
            <td align="center" style="padding: 10px;">
                <a href="{BASE_URL}/account/export-data" style="display: inline-block; background: #f4f4f5; color: #333; padding: 12px 28px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 8px; border: 1px solid #d4d4d8;">
                    Export My Data Before Deletion
                </a>
            </td>
        </tr>
    </table>

    <p style="margin: 10px 0 0; font-size: 16px; color: #333;">
        Best,<br>
        <strong>The Grant Writer Pro Team</strong>
    </p>
    """

    return {
        "subject": subject,
        "html": wrap_in_html(body, subject, preheader)
    }


# ============ SUBSCRIPTION LIFECYCLE SEND WRAPPERS ============

def send_renewal_reminder(email: str, first_name: str, plan: str, renewal_date: str, amount: float) -> Dict:
    """Send renewal reminder email"""
    content = get_renewal_reminder_email(first_name, plan, renewal_date, amount)
    return send_email(email, content["subject"], content["html"], "renewal_reminder")


def send_dunning_email(email: str, first_name: str, attempt_number: int, suspension_date: str = None) -> Dict:
    """Send appropriate dunning email based on attempt number"""
    if attempt_number == 1:
        content = get_dunning_email_1(first_name)
    elif attempt_number == 2:
        content = get_dunning_email_2(first_name)
    else:
        content = get_dunning_email_3(first_name, suspension_date or "soon")
    return send_email(email, content["subject"], content["html"], f"dunning_{attempt_number}")


def send_account_suspended_email(email: str, first_name: str, deletion_date: str) -> Dict:
    """Send account suspended notification"""
    content = get_account_suspended_email(first_name, deletion_date)
    return send_email(email, content["subject"], content["html"], "account_suspended")


def send_suspension_reminder(email: str, first_name: str, days_remaining: int, deletion_date: str) -> Dict:
    """Send periodic suspension reminder"""
    content = get_suspension_reminder_email(first_name, days_remaining, deletion_date)
    return send_email(email, content["subject"], content["html"], "suspension_reminder")


def send_cancellation_confirmation(email: str, first_name: str, end_date: str) -> Dict:
    """Send cancellation confirmation email"""
    content = get_cancellation_confirmation_email(first_name, end_date)
    return send_email(email, content["subject"], content["html"], "cancellation_confirmation")


def send_final_deletion_warning(email: str, first_name: str, deletion_date: str) -> Dict:
    """Send final deletion warning email"""
    content = get_final_deletion_warning_email(first_name, deletion_date)
    return send_email(email, content["subject"], content["html"], "final_deletion_warning")


# ============ CONVENIENCE FUNCTIONS ============

def send_welcome_email(email: str, first_name: str = "there") -> Dict:
    """Send welcome email"""
    content = get_welcome_email(first_name)
    return send_email(email, content["subject"], content["html"], "welcome")


def send_weekly_alerts(grants: List[Dict]) -> Dict:
    """Send weekly alerts to all leads"""
    try:
        conn = get_connection()
        leads = conn.execute('SELECT * FROM leads WHERE status = ?', ('active',)).fetchall()
    except Exception:
        return {"sent": 0, "message": "No leads table"}
    conn.close()
    
    if not leads:
        return {"sent": 0, "message": "No active leads"}
    
    content = get_weekly_alerts_email(grants, len(grants))
    
    results = []
    for lead in leads:
        result = send_email(lead["email"], content["subject"], content["html"], "weekly_alerts")
        results.append({"email": lead["email"], "success": result["success"]})
    
    return {
        "sent": len([r for r in results if r["success"]]),
        "total": len(leads)
    }


def send_deadline_reminder(email: str, grant: Dict, days_until: int) -> Dict:
    """Send deadline reminder"""
    content = get_deadline_reminder_email(grant, days_until)
    return send_email(email, content["subject"], content["html"], "deadline_reminder")


# Initialize
init_email_db()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "test":
            result = send_welcome_email("test@example.com", "Test User")
            print(f"Result: {result}")
            
        elif cmd == "stats":
            stats = get_email_stats()
            print(f"Total sent: {stats['total_sent']}")
            
        elif cmd == "leads":
            try:
                conn = get_connection()
                leads = conn.execute('SELECT * FROM leads').fetchall()
                print(f"Active leads: {len(leads)}")
                for lead in leads:
                    print(f"  - {lead['email']}")
                conn.close()
            except Exception:
                print("No leads table")
