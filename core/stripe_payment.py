#!/usr/bin/env python3
"""
Stripe Payment Integration for Grant Writing System
Handles recurring subscriptions (monthly/annual) and webhooks
"""

import os
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path

# Stripe integration - only load if API key available
STRIPE_API_KEY = os.getenv('STRIPE_API_KEY')

if STRIPE_API_KEY:
    import stripe
    stripe.api_key = STRIPE_API_KEY

from db_connection import LOCAL_DB_PATH as DB_PATH
from db_connection import get_connection

# Plan pricing
PLAN_PRICING = {
    'monthly': {
        'stripe_price_id_monthly': os.getenv('STRIPE_MONTHLY_PRICE_ID', 'price_monthly_placeholder'),
        'amount': 19.95,
        'interval': 'month',
        'grants': 3,
        'client_limit': 1,
    },
    'annual': {
        'stripe_price_id_annual': os.getenv('STRIPE_ANNUAL_PRICE_ID', 'price_annual_placeholder'),
        'amount': 199.00,
        'interval': 'year',
        'grants': 3,
        'client_limit': 1,
    },
    'enterprise_5': {
        'stripe_price_id_enterprise_5': os.getenv('STRIPE_ENTERPRISE_5_PRICE_ID', 'price_enterprise_5_placeholder'),
        'amount': 44.95,
        'interval': 'month',
        'grants': 999,
        'client_limit': 5,
    },
    'enterprise_10': {
        'stripe_price_id_enterprise_10': os.getenv('STRIPE_ENTERPRISE_10_PRICE_ID', 'price_enterprise_10_placeholder'),
        'amount': 74.95,
        'interval': 'month',
        'grants': 999,
        'client_limit': 10,
    },
    'enterprise_15': {
        'stripe_price_id_enterprise_15': os.getenv('STRIPE_ENTERPRISE_15_PRICE_ID', 'price_enterprise_15_placeholder'),
        'amount': 99.95,
        'interval': 'month',
        'grants': 999,
        'client_limit': None,  # Unlimited
    }
}

# Enterprise plan names for suspension threshold logic
ENTERPRISE_PLANS = ('enterprise_5', 'enterprise_10', 'enterprise_15')


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


def _get_user_by_customer_id(customer_id):
    """Look up a user row by stripe_customer_id. Returns dict or None."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE stripe_customer_id = ?', (customer_id,))
    row = c.fetchone()
    conn.close()
    if row:
        from user_models import USER_COLUMNS
        return dict(row) if hasattr(row, 'keys') else dict(zip(USER_COLUMNS, row))
    return None


def _reset_dunning_fields(cursor, customer_id, now):
    """Clear all dunning/suspension fields after a successful payment."""
    cursor.execute('''UPDATE users SET
                      payment_failure_count = 0,
                      first_payment_failure_at = NULL,
                      last_dunning_email_at = NULL,
                      suspended_at = NULL,
                      data_deletion_eligible_at = NULL,
                      renewal_reminder_sent = 0,
                      updated_at = ?
                      WHERE stripe_customer_id = ?''',
                   (now, customer_id))


# ============================================================
# Webhook dispatcher
# ============================================================

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

    # Check idempotency -- skip already-processed events
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM subscription_events WHERE stripe_event_id = ?", (event['id'],))
    if c.fetchone():
        conn.close()
        return {"status": "duplicate", "event": event['type']}, None

    # Record the event ID immediately to prevent concurrent duplicates
    now = datetime.now()
    idempotency_id = f"stripe-{now.strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4)}"
    c.execute('''INSERT INTO subscription_events (id, user_id, event_type, stripe_event_id, metadata, created_at)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (idempotency_id, 'webhook', event['type'], event['id'], None, now.isoformat()))
    conn.commit()
    conn.close()

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        return handle_checkout_complete(event['data']['object'])
    elif event['type'] == 'customer.subscription.updated':
        return handle_subscription_update(event['data']['object'])
    elif event['type'] == 'customer.subscription.deleted':
        return handle_subscription_cancel(event['data']['object'])
    elif event['type'] == 'invoice.payment_failed':
        return handle_payment_failed(event['data']['object'])
    elif event['type'] == 'invoice.paid':
        return handle_payment_success(event['data']['object'])
    elif event['type'] == 'invoice.upcoming':
        return handle_invoice_upcoming(event['data']['object'])

    return {"status": "ignored", "event": event['type']}, None


# ============================================================
# Checkout complete
# ============================================================

def handle_checkout_complete(session):
    """Handle successful checkout -- also resets dunning fields for reactivations."""
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
    conn = get_connection()
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

    # Reset dunning fields in case this is a reactivation
    _reset_dunning_fields(c, customer_id, now)

    conn.commit()
    conn.close()

    # Log event
    from user_models import log_subscription_event
    log_subscription_event(user_id, 'checkout_complete', metadata={'plan': plan_type})

    return {"status": "success", "user_id": user_id, "plan": plan_type}, None


# ============================================================
# Subscription update
# ============================================================

def handle_subscription_update(subscription):
    """Handle subscription updates (plan changes, etc.)"""
    customer_id = subscription.get('customer')
    status = subscription.get('status')
    plan_interval = subscription['items']['data'][0]['price']['recurring']['interval']

    plan_type = 'monthly' if plan_interval == 'month' else 'annual'

    try:
        current_period_end = datetime.fromtimestamp(subscription['current_period_end'])
        sub_end = current_period_end.isoformat()
    except (KeyError, TypeError, ValueError, OSError):
        sub_end = None

    conn = get_connection()
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


# ============================================================
# Subscription cancel (webhook from Stripe)
# ============================================================

def handle_subscription_cancel(subscription):
    """Handle subscription cancellation from Stripe.

    Distinguishes voluntary (user-initiated cancel at period end) from
    involuntary (past_due -> suspended -> cancelled by Stripe).
    In both cases the user is downgraded to free.
    """
    customer_id = subscription.get('customer')

    # Look up user to determine cancellation type
    user = _get_user_by_customer_id(customer_id)
    was_suspended = user and user.get('subscription_status') == 'suspended'

    conn = get_connection()
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

    # Log event
    if user:
        from user_models import log_subscription_event
        event_type = 'subscription_cancelled_involuntary' if was_suspended else 'subscription_cancelled_voluntary'
        log_subscription_event(
            user.get('id'), event_type,
            metadata={'customer_id': customer_id, 'was_suspended': was_suspended}
        )

    return {"status": "cancelled", "customer": customer_id}, None


# ============================================================
# Payment failed (dunning escalation)
# ============================================================

def handle_payment_failed(invoice):
    """Handle failed payment with dunning escalation.

    Failure thresholds:
      - Monthly/Annual: suspend on 3rd failure
      - Enterprise plans: suspend on 4th failure (extra grace)
    """
    customer_id = invoice.get('customer')

    # Look up user
    user = _get_user_by_customer_id(customer_id)
    if not user:
        return {"status": "payment_failed", "customer": customer_id, "note": "user not found"}, None

    user_id = user.get('id')
    plan = user.get('plan', 'monthly')
    suspension_threshold = 4 if plan in ENTERPRISE_PLANS else 3

    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()

    # Record first failure timestamp
    first_failure = user.get('first_payment_failure_at') or now

    # Atomic increment of payment_failure_count to avoid race conditions
    c.execute('''UPDATE users SET
                  subscription_status = 'past_due',
                  payment_failure_count = payment_failure_count + 1,
                  first_payment_failure_at = ?,
                  last_dunning_email_at = ?,
                  updated_at = ?
                  WHERE stripe_customer_id = ?''',
              (first_failure, now, now, customer_id))

    # Read back the new count
    c.execute('SELECT payment_failure_count FROM users WHERE stripe_customer_id = ?', (customer_id,))
    current_count = c.fetchone()[0]

    conn.commit()
    conn.close()

    # Log event
    from user_models import log_subscription_event
    log_subscription_event(user_id, 'payment_failed', metadata={
        'attempt': current_count, 'plan': plan
    })

    # Send appropriate dunning email
    try:
        from email_system import send_dunning_email, send_account_suspended_email
        email = user.get('email')
        first_name = user.get('first_name') or 'there'

        if current_count < suspension_threshold:
            # Calculate suspension date for email 3
            suspension_date = (datetime.fromisoformat(first_failure) + timedelta(days=14)).strftime('%B %d, %Y')
            send_dunning_email(email, first_name, current_count, suspension_date=suspension_date)
        else:
            # Suspend the account
            deletion_date = (datetime.now() + timedelta(days=90)).isoformat()
            conn2 = get_connection()
            c2 = conn2.cursor()
            c2.execute('''UPDATE users SET
                          subscription_status = 'suspended',
                          suspended_at = ?,
                          data_deletion_eligible_at = ?,
                          plan_before_suspension = ?,
                          updated_at = ?
                          WHERE stripe_customer_id = ?''',
                       (now, deletion_date, plan, now, customer_id))
            conn2.commit()
            conn2.close()

            log_subscription_event(user_id, 'account_suspended', metadata={
                'failure_count': current_count, 'deletion_eligible': deletion_date
            })

            deletion_display = (datetime.now() + timedelta(days=90)).strftime('%B %d, %Y')
            send_account_suspended_email(email, first_name, deletion_display)
    except Exception:
        pass  # Don't let email errors break the webhook

    return {"status": "payment_failed", "customer": customer_id, "attempt": current_count}, None


# ============================================================
# Payment success (resets dunning state)
# ============================================================

def handle_payment_success(invoice):
    """Handle successful invoice payment -- resets all dunning state."""
    customer_id = invoice.get('customer')

    user = _get_user_by_customer_id(customer_id)
    if not user:
        return {"status": "invoice_paid", "customer": customer_id, "note": "user not found"}, None

    user_id = user.get('id')
    was_suspended = user.get('subscription_status') in ('suspended', 'past_due')

    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()

    # Reactivate if previously suspended or past_due
    if was_suspended:
        # If user was suspended, also restore their plan from plan_before_suspension
        restore_plan = user.get('plan_before_suspension')
        if restore_plan and user.get('subscription_status') == 'suspended':
            c.execute('''UPDATE users SET
                          subscription_status = 'active',
                          plan = ?,
                          plan_before_suspension = NULL,
                          updated_at = ?
                          WHERE stripe_customer_id = ?''',
                      (restore_plan, now, customer_id))
        else:
            c.execute('''UPDATE users SET
                          subscription_status = 'active',
                          updated_at = ?
                          WHERE stripe_customer_id = ?''',
                      (now, customer_id))

    # Reset all dunning fields
    _reset_dunning_fields(c, customer_id, now)

    conn.commit()
    conn.close()

    # Log event
    from user_models import log_subscription_event
    log_subscription_event(user_id, 'payment_success', metadata={
        'reactivated': was_suspended, 'customer_id': customer_id
    })

    return {"status": "invoice_paid", "customer": customer_id, "reactivated": was_suspended}, None


# ============================================================
# Invoice upcoming (renewal reminder)
# ============================================================

def handle_invoice_upcoming(invoice):
    """Handle upcoming invoice -- send renewal reminder if not already sent."""
    customer_id = invoice.get('customer')

    user = _get_user_by_customer_id(customer_id)
    if not user:
        return {"status": "invoice_upcoming", "customer": customer_id, "note": "user not found"}, None

    user_id = user.get('id')
    already_sent = bool(user.get('renewal_reminder_sent'))

    if not already_sent:
        # Mark as sent
        conn = get_connection()
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute('UPDATE users SET renewal_reminder_sent = 1, updated_at = ? WHERE id = ?', (now, user_id))
        conn.commit()
        conn.close()

        # Send reminder email
        try:
            from email_system import send_renewal_reminder
            plan = user.get('plan', 'monthly')
            pricing = PLAN_PRICING.get(plan, PLAN_PRICING['monthly'])
            amount = pricing.get('amount', 0)
            renewal_date = user.get('subscription_end', 'your next billing date')
            # Format date nicely if ISO
            try:
                renewal_date = datetime.fromisoformat(renewal_date).strftime('%B %d, %Y')
            except (ValueError, TypeError):
                pass
            send_renewal_reminder(
                user.get('email'),
                user.get('first_name') or 'there',
                plan,
                renewal_date,
                amount
            )
        except Exception:
            pass  # Don't break the webhook over email

        from user_models import log_subscription_event
        log_subscription_event(user_id, 'renewal_reminder_sent')

    return {"status": "invoice_upcoming", "customer": customer_id, "reminder_sent": not already_sent}, None


# ============================================================
# Subscription status query
# ============================================================

def get_subscription_status(user_id):
    """Get current subscription status for a user"""
    conn = get_connection()
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


# ============================================================
# Pause subscription (user-initiated)
# ============================================================

def pause_subscription(user_id, months=1):
    """Pause a user's subscription for 1 or 3 months.

    Rules:
    - Max one pause per 12-month period
    - Pause duration: 1 or 3 months
    - Stripe subscription paused via pause_collection
    - User data preserved, account goes read-only
    - Auto-reactivates when pause ends
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT stripe_subscription_id, pause_count_this_year, plan, pause_started_at FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    conn.close()

    if not row or not row[0]:
        return False, "No active subscription"

    subscription_id = row[0]
    pause_count = row[1] or 0
    plan = row[2]
    last_pause_started = row[3]

    # Check if user has paused within the last 12 months (rolling window, not calendar year)
    if last_pause_started:
        try:
            last_pause = datetime.fromisoformat(last_pause_started)
            if (datetime.now() - last_pause).days < 365:
                return False, "You can only pause once per 12-month period."
        except (ValueError, TypeError):
            pass
    elif pause_count >= 1:
        return False, "You have already used your pause this year. Pausing is limited to once per 12 months."

    if months not in (1, 3):
        return False, "Pause duration must be 1 or 3 months."

    now = datetime.now()
    pause_end = now + timedelta(days=months * 30)

    if STRIPE_API_KEY:
        try:
            # Pause billing collection in Stripe
            stripe.Subscription.modify(
                subscription_id,
                pause_collection={
                    'behavior': 'void',
                    'resumes_at': int(pause_end.timestamp())
                }
            )
        except Exception as e:
            return False, f"Stripe error: {str(e)}"

    # Update local state
    conn = get_connection()
    c = conn.cursor()
    c.execute('''UPDATE users SET
                  subscription_status = 'paused',
                  pause_started_at = ?,
                  pause_ends_at = ?,
                  pause_count_this_year = ?,
                  updated_at = ?
                  WHERE id = ?''',
              (now.isoformat(), pause_end.isoformat(), pause_count + 1, now.isoformat(), user_id))
    conn.commit()
    conn.close()

    # Log event
    from user_models import log_subscription_event
    log_subscription_event(user_id, 'subscription_paused', metadata={'months': months, 'resumes_at': pause_end.isoformat()})

    return True, f"Subscription paused until {pause_end.strftime('%B %d, %Y')}"


# ============================================================
# Reactivate paused subscription
# ============================================================

def reactivate_subscription(user_id):
    """Reactivate a paused subscription early."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT stripe_subscription_id, subscription_status FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    conn.close()

    if not row or not row[0]:
        return False, "No subscription found"

    subscription_id = row[0]
    status = row[1]

    if status != 'paused':
        return False, "Subscription is not currently paused"

    if STRIPE_API_KEY:
        try:
            stripe.Subscription.modify(subscription_id, pause_collection='')
        except Exception as e:
            return False, f"Stripe error: {str(e)}"

    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''UPDATE users SET
                  subscription_status = 'active',
                  pause_started_at = NULL,
                  pause_ends_at = NULL,
                  updated_at = ?
                  WHERE id = ?''', (now, user_id))
    conn.commit()
    conn.close()

    from user_models import log_subscription_event
    log_subscription_event(user_id, 'subscription_reactivated', metadata={'from_status': 'paused'})

    return True, "Subscription reactivated"


# ============================================================
# Cancel subscription (user-initiated)
# ============================================================

def cancel_subscription(user_id, reason=None):
    """Cancel user's subscription at period end.

    Args:
        user_id: The user ID.
        reason: Optional cancellation reason string.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT stripe_subscription_id, stripe_customer_id FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    conn.close()

    if not row or not row[0]:
        return False, "No active subscription"

    subscription_id, customer_id = row

    if not STRIPE_API_KEY:
        # Just update locally
        conn = get_connection()
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute('''UPDATE users SET
                      plan = 'free',
                      max_grants_per_month = 0,
                      subscription_status = 'cancelled',
                      cancellation_reason = ?,
                      updated_at = ?
                      WHERE id = ?''',
                  (reason, now, user_id))
        conn.commit()
        conn.close()

        from user_models import log_subscription_event
        log_subscription_event(user_id, 'subscription_cancel_requested', metadata={'reason': reason})

        return True, "Subscription cancelled (Stripe not configured)"

    try:
        # Cancel at period end
        sub = stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)

        # Derive cancellation_effective_at from Stripe's current_period_end
        try:
            effective_at = datetime.fromtimestamp(sub['current_period_end']).isoformat()
        except (KeyError, TypeError, ValueError, OSError):
            effective_at = None

        # Update locally
        conn = get_connection()
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute('''UPDATE users SET
                      subscription_status = 'canceling',
                      cancellation_reason = ?,
                      cancellation_effective_at = ?,
                      updated_at = ?
                      WHERE id = ?''',
                  (reason, effective_at, now, user_id))
        conn.commit()
        conn.close()

        from user_models import log_subscription_event
        log_subscription_event(user_id, 'subscription_cancel_requested', metadata={
            'reason': reason, 'effective_at': effective_at
        })

        # Send cancellation confirmation email
        try:
            from email_system import send_cancellation_confirmation
            user = _get_user_by_customer_id(customer_id)
            if user:
                end_display = effective_at
                try:
                    end_display = datetime.fromisoformat(effective_at).strftime('%B %d, %Y')
                except (ValueError, TypeError):
                    pass
                send_cancellation_confirmation(
                    user.get('email'),
                    user.get('first_name') or 'there',
                    end_display
                )
        except Exception:
            pass

        return True, "Subscription will cancel at period end"
    except Exception as e:
        return False, str(e)
