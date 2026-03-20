#!/usr/bin/env python3
"""
Stripe Payment Integration for Grant Writing System
Handles recurring subscriptions (monthly/annual) and webhooks
"""

import os
import json
from datetime import datetime
from pathlib import Path

# Stripe integration - only load if API key available
STRIPE_API_KEY = os.getenv('STRIPE_API_KEY')

if STRIPE_API_KEY:
    import stripe
    stripe.api_key = STRIPE_API_KEY

DB_PATH = Path.home() / ".hermes" / "grant-system" / "tracking" / "grants.db"

# Plan pricing
PLAN_PRICING = {
    'monthly': {
        'stripe_price_id_monthly': os.getenv('STRIPE_MONTHLY_PRICE_ID', 'price_monthly_placeholder'),
        'amount': 19.95,
        'interval': 'month',
        'grants': 3,
    },
    'annual': {
        'stripe_price_id_annual': os.getenv('STRIPE_ANNUAL_PRICE_ID', 'price_annual_placeholder'),
        'amount': 199.00,
        'interval': 'year',
        'grants': 3,
    },
    'enterprise': {
        'stripe_price_id_enterprise': os.getenv('STRIPE_ENTERPRISE_PRICE_ID', 'price_enterprise_placeholder'),
        'amount': 0,  # Custom pricing
        'interval': 'year',
        'grants': 999,
    }
}

def get_stripe_customer(user_email, user_name=None):
    """Create or get Stripe customer"""
    if not STRIPE_API_KEY:
        return None, "Stripe not configured"
    
    try:
        # Try to find existing customer
        customers = stripe.Customer.list(email=user_email, limit=1)
        if customers.data:
            return customers.data[0].id, None
        
        # Create new customer
        customer = stripe.Customer.create(
            email=user_email,
            name=user_name or "",
            metadata={'source': 'grant_pro'}
        )
        return customer.id, None
    except Exception as e:
        return None, str(e)


def create_checkout_session(user_email, user_id, plan_type='monthly', success_url=None, cancel_url=None):
    """Create Stripe checkout session for subscription"""
    if not STRIPE_API_KEY:
        return None, "Stripe not configured. Set STRIPE_API_KEY environment variable."
    
    pricing = PLAN_PRICING.get(plan_type, PLAN_PRICING['monthly'])
    
    try:
        customer_id, error = get_stripe_customer(user_email)
        if error:
            return None, error
        
        # Build success/cancel URLs
        base_url = os.getenv('APP_URL', 'http://localhost:5001')
        success_url = success_url or f"{base_url}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = cancel_url or f"{base_url}/subscription/cancel"
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': pricing.get(f'stripe_price_id_{plan_type}'),
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'user_id': user_id,
                'plan': plan_type
            }
        )
        return session.url, None
    except Exception as e:
        return None, str(e)


def create_portal_session(customer_id, return_url=None):
    """Create Stripe customer portal session for subscription management"""
    if not STRIPE_API_KEY:
        return None, "Stripe not configured"
    
    try:
        base_url = os.getenv('APP_URL', 'http://localhost:5001')
        return_url = return_url or f"{base_url}/dashboard"
        
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url
        )
        return session.url, None
    except Exception as e:
        return None, str(e)


def handle_webhook(payload, sig_header):
    """Handle Stripe webhook events"""
    if not STRIPE_API_KEY:
        return None, "Stripe not configured"
    
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    if not webhook_secret:
        return None, "Webhook secret not configured"
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        return None, "Invalid payload"
    except stripe.error.SignatureVerificationError:
        return None, "Invalid signature"
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        return handle_checkout_complete(event['data']['object'])
    elif event['type'] == 'customer.subscription.updated':
        return handle_subscription_update(event['data']['object'])
    elif event['type'] == 'customer.subscription.deleted':
        return handle_subscription_cancel(event['data']['object'])
    elif event['type'] == 'invoice.payment_failed':
        return handle_payment_failed(event['data']['object'])
    
    return {"status": "ignored", "event": event['type']}, None


def handle_checkout_complete(session):
    """Handle successful checkout"""
    import sqlite3
    
    user_id = session.get('metadata', {}).get('user_id')
    customer_id = session.get('customer')
    subscription_id = session.get('subscription')
    
    if not user_id:
        return None, "No user_id in session metadata"
    
    # Get subscription details
    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        plan_interval = subscription['items']['data'][0]['price']['recurring']['interval']
        plan_type = 'monthly' if plan_interval == 'month' else 'annual'
    except Exception:
        plan_type = 'monthly'  # Default
    
    # Update user in database
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    # Calculate subscription end date
    try:
        current_period_end = datetime.fromtimestamp(subscription['current_period_end'])
        sub_end = current_period_end.isoformat()
    except (KeyError, TypeError, ValueError, OSError):
        sub_end = None
    
    c.execute('''UPDATE users SET 
                  plan = ?, 
                  max_grants_per_month = 3,
                  subscription_status = 'active',
                  stripe_customer_id = ?,
                  stripe_subscription_id = ?,
                  subscription_start = ?,
                  subscription_end = ?,
                  updated_at = ?
                  WHERE id = ?''', 
              (plan_type, customer_id, subscription_id, now, sub_end, now, user_id))
    
    conn.commit()
    conn.close()
    
    return {"status": "success", "user_id": user_id, "plan": plan_type}, None


def handle_subscription_update(subscription):
    """Handle subscription updates (plan changes, etc.)"""
    import sqlite3
    
    customer_id = subscription.get('customer')
    status = subscription.get('status')
    plan_interval = subscription['items']['data'][0]['price']['recurring']['interval']
    
    plan_type = 'monthly' if plan_interval == 'month' else 'annual'
    
    try:
        current_period_end = datetime.fromtimestamp(subscription['current_period_end'])
        sub_end = current_period_end.isoformat()
    except (KeyError, TypeError, ValueError, OSError):
        sub_end = None
    
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    db_status = 'active' if status == 'active' else 'past_due'
    
    c.execute('''UPDATE users SET 
                  subscription_status = ?,
                  subscription_end = ?,
                  updated_at = ?
                  WHERE stripe_customer_id = ?''', 
              (db_status, sub_end, now, customer_id))
    
    conn.commit()
    conn.close()
    
    return {"status": "updated", "customer": customer_id}, None


def handle_subscription_cancel(subscription):
    """Handle subscription cancellation"""
    import sqlite3
    
    customer_id = subscription.get('customer')
    
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    # Downgrade to free
    c.execute('''UPDATE users SET 
                  plan = 'free',
                  max_grants_per_month = 0,
                  subscription_status = 'cancelled',
                  subscription_end = ?,
                  updated_at = ?
                  WHERE stripe_customer_id = ?''', 
              (now, now, customer_id))
    
    conn.commit()
    conn.close()
    
    return {"status": "cancelled", "customer": customer_id}, None


def handle_payment_failed(invoice):
    """Handle failed payment"""
    import sqlite3
    
    customer_id = invoice.get('customer')
    
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    c.execute('''UPDATE users SET 
                  subscription_status = 'past_due',
                  updated_at = ?
                  WHERE stripe_customer_id = ?''', 
              (now, customer_id))
    
    conn.commit()
    conn.close()
    
    return {"status": "payment_failed", "customer": customer_id}, None


def get_subscription_status(user_id):
    """Get current subscription status for a user"""
    import sqlite3
    
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('''SELECT plan, subscription_status, subscription_start, subscription_end, 
                  grants_this_month, max_grants_per_month
                  FROM users WHERE id = ?''', (user_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            'plan': row[0],
            'status': row[1],
            'start': row[2],
            'end': row[3],
            'grants_used': row[4],
            'grants_allowed': row[5]
        }
    return None


def cancel_subscription(user_id):
    """Cancel user's subscription"""
    import sqlite3
    
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('SELECT stripe_subscription_id, stripe_customer_id FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    
    if not row or not row[0]:
        return False, "No active subscription"
    
    subscription_id, customer_id = row
    
    if not STRIPE_API_KEY:
        # Just update locally
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute('''UPDATE users SET 
                      plan = 'free',
                      max_grants_per_month = 0,
                      subscription_status = 'cancelled',
                      updated_at = ?
                      WHERE id = ?''', 
                  (datetime.now().isoformat(), user_id))
        conn.commit()
        conn.close()
        return True, "Subscription cancelled (Stripe not configured)"
    
    try:
        # Cancel at period end
        stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
        
        # Update locally
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute('''UPDATE users SET 
                      subscription_status = 'canceling',
                      updated_at = ?
                      WHERE id = ?''', 
                  (datetime.now().isoformat(), user_id))
        conn.commit()
        conn.close()
        
        return True, "Subscription will cancel at period end"
    except Exception as e:
        return False, str(e)
