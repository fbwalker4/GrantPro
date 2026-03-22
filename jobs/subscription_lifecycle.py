#!/usr/bin/env python3
"""
Subscription Lifecycle Daily Job

Runs via cron once per day. Handles:
  1. Renewal reminders (30 days before subscription_end)
  2. Suspension reminders (weekly at day 7, 30, 60, 80)
  3. Final deletion warning (day 83 of suspension)
  4. Mark pending_deletion (day 90 of suspension)

Usage:
    python3 jobs/subscription_lifecycle.py
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths & logging
# ---------------------------------------------------------------------------
GRANT_SYSTEM = Path.home() / ".hermes" / "grant-system"
LOG_DIR = GRANT_SYSTEM / "tracking"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "subscription_lifecycle.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("subscription_lifecycle")

# Add core/ to sys.path so we can import shared modules
sys.path.insert(0, str(GRANT_SYSTEM / "core"))

from db_connection import get_connection
from user_models import log_subscription_event, purge_user_data, record_account_deletion


# ---------------------------------------------------------------------------
# 1. Renewal reminders
# ---------------------------------------------------------------------------
def send_renewal_reminders():
    """Send renewal reminders to users whose subscription_end is within 30 days
    and who haven't already received a reminder this cycle."""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now()
    cutoff = (now + timedelta(days=30)).isoformat()

    c.execute('''SELECT id, email, first_name, plan, subscription_end
                 FROM users
                 WHERE subscription_status = 'active'
                   AND renewal_reminder_sent = 0
                   AND subscription_end IS NOT NULL
                   AND subscription_end <= ?
                   AND subscription_end > ?''',
              (cutoff, now.isoformat()))
    rows = c.fetchall()
    conn.close()

    if not rows:
        logger.info("No renewal reminders to send.")
        return 0

    from email_system import send_renewal_reminder
    from stripe_payment import PLAN_PRICING

    sent = 0
    for row in rows:
        user_id = row[0] if not hasattr(row, 'keys') else row['id']
        email = row[1] if not hasattr(row, 'keys') else row['email']
        first_name = (row[2] if not hasattr(row, 'keys') else row['first_name']) or 'there'
        plan = row[3] if not hasattr(row, 'keys') else row['plan']
        sub_end = row[4] if not hasattr(row, 'keys') else row['subscription_end']

        pricing = PLAN_PRICING.get(plan, PLAN_PRICING.get('monthly', {}))
        amount = pricing.get('amount', 0)

        try:
            renewal_display = datetime.fromisoformat(sub_end).strftime('%B %d, %Y')
        except (ValueError, TypeError):
            renewal_display = sub_end or 'your next billing date'

        try:
            send_renewal_reminder(email, first_name, plan, renewal_display, amount)

            # Mark as sent
            conn2 = get_connection()
            c2 = conn2.cursor()
            c2.execute('UPDATE users SET renewal_reminder_sent = 1, updated_at = ? WHERE id = ?',
                       (now.isoformat(), user_id))
            conn2.commit()
            conn2.close()

            log_subscription_event(user_id, 'renewal_reminder_sent')
            sent += 1
            logger.info("Sent renewal reminder to %s (user %s)", email, user_id)
        except Exception as e:
            logger.error("Failed to send renewal reminder to %s: %s", email, e)

    logger.info("Renewal reminders: sent %d of %d.", sent, len(rows))
    return sent


# ---------------------------------------------------------------------------
# 2. Suspension reminders (day 7, 30, 60, 80)
# ---------------------------------------------------------------------------
SUSPENSION_REMINDER_DAYS = [7, 30, 60, 80]


def send_suspension_reminders():
    """Send periodic reminders to suspended users at specific day milestones."""
    conn = get_connection()
    c = conn.cursor()

    c.execute('''SELECT id, email, first_name, suspended_at, data_deletion_eligible_at,
                        last_dunning_email_at
                 FROM users
                 WHERE subscription_status = 'suspended'
                   AND suspended_at IS NOT NULL
                   AND data_deletion_eligible_at IS NOT NULL''')
    rows = c.fetchall()
    conn.close()

    if not rows:
        logger.info("No suspended users to remind.")
        return 0

    from email_system import send_suspension_reminder

    now = datetime.now()
    sent = 0

    for row in rows:
        user_id = row[0] if not hasattr(row, 'keys') else row['id']
        email = row[1] if not hasattr(row, 'keys') else row['email']
        first_name = (row[2] if not hasattr(row, 'keys') else row['first_name']) or 'there'
        suspended_at_str = row[3] if not hasattr(row, 'keys') else row['suspended_at']
        deletion_at_str = row[4] if not hasattr(row, 'keys') else row['data_deletion_eligible_at']
        last_dunning_str = row[5] if not hasattr(row, 'keys') else row['last_dunning_email_at']

        try:
            suspended_at = datetime.fromisoformat(suspended_at_str)
            deletion_at = datetime.fromisoformat(deletion_at_str)
        except (ValueError, TypeError):
            continue

        days_suspended = (now - suspended_at).days
        days_remaining = max(0, (deletion_at - now).days)

        # Don't re-send if we already emailed today
        if last_dunning_str:
            try:
                last_sent = datetime.fromisoformat(last_dunning_str)
                if (now - last_sent).days < 1:
                    continue
            except (ValueError, TypeError):
                pass

        # Check if we're at a reminder milestone
        for milestone in SUSPENSION_REMINDER_DAYS:
            if days_suspended >= milestone and days_suspended < milestone + 1:
                try:
                    deletion_display = deletion_at.strftime('%B %d, %Y')
                    send_suspension_reminder(email, first_name, days_remaining, deletion_display)

                    conn2 = get_connection()
                    c2 = conn2.cursor()
                    c2.execute('UPDATE users SET last_dunning_email_at = ?, updated_at = ? WHERE id = ?',
                               (now.isoformat(), now.isoformat(), user_id))
                    conn2.commit()
                    conn2.close()

                    log_subscription_event(user_id, 'suspension_reminder_sent', metadata={
                        'days_suspended': days_suspended, 'days_remaining': days_remaining
                    })
                    sent += 1
                    logger.info("Sent suspension reminder to %s (day %d, %d remaining)",
                                email, days_suspended, days_remaining)
                except Exception as e:
                    logger.error("Failed to send suspension reminder to %s: %s", email, e)
                break  # Only one email per user per run

    logger.info("Suspension reminders: sent %d.", sent)
    return sent


# ---------------------------------------------------------------------------
# 3. Final deletion warning (day 83)
# ---------------------------------------------------------------------------
def send_final_deletion_warnings():
    """Send final warning at day 83 (7 days before deletion)."""
    conn = get_connection()
    c = conn.cursor()

    c.execute('''SELECT id, email, first_name, suspended_at, data_deletion_eligible_at
                 FROM users
                 WHERE subscription_status = 'suspended'
                   AND suspended_at IS NOT NULL
                   AND data_deletion_eligible_at IS NOT NULL''')
    rows = c.fetchall()
    conn.close()

    if not rows:
        return 0

    from email_system import send_final_deletion_warning

    now = datetime.now()
    sent = 0

    for row in rows:
        user_id = row[0] if not hasattr(row, 'keys') else row['id']
        email = row[1] if not hasattr(row, 'keys') else row['email']
        first_name = (row[2] if not hasattr(row, 'keys') else row['first_name']) or 'there'
        suspended_at_str = row[3] if not hasattr(row, 'keys') else row['suspended_at']
        deletion_at_str = row[4] if not hasattr(row, 'keys') else row['data_deletion_eligible_at']

        try:
            suspended_at = datetime.fromisoformat(suspended_at_str)
            deletion_at = datetime.fromisoformat(deletion_at_str)
        except (ValueError, TypeError):
            continue

        days_suspended = (now - suspended_at).days

        # Send at day 83 (within a 1-day window to avoid re-sends)
        if 83 <= days_suspended < 84:
            try:
                deletion_display = deletion_at.strftime('%B %d, %Y')
                send_final_deletion_warning(email, first_name, deletion_display)

                conn2 = get_connection()
                c2 = conn2.cursor()
                c2.execute('UPDATE users SET last_dunning_email_at = ?, updated_at = ? WHERE id = ?',
                           (now.isoformat(), now.isoformat(), user_id))
                conn2.commit()
                conn2.close()

                log_subscription_event(user_id, 'final_deletion_warning_sent', metadata={
                    'deletion_date': deletion_at_str
                })
                sent += 1
                logger.info("Sent final deletion warning to %s", email)
            except Exception as e:
                logger.error("Failed to send final deletion warning to %s: %s", email, e)

    logger.info("Final deletion warnings: sent %d.", sent)
    return sent


# ---------------------------------------------------------------------------
# 4. Mark pending_deletion (day 90+)
# ---------------------------------------------------------------------------
def mark_pending_deletions():
    """Mark users whose 90-day grace period has expired as pending_deletion."""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now()

    c.execute('''SELECT id, email, data_deletion_eligible_at
                 FROM users
                 WHERE subscription_status = 'suspended'
                   AND data_deletion_eligible_at IS NOT NULL
                   AND data_deletion_eligible_at <= ?''',
              (now.isoformat(),))
    rows = c.fetchall()

    if not rows:
        conn.close()
        logger.info("No users eligible for pending_deletion.")
        return 0

    count = 0
    for row in rows:
        user_id = row[0] if not hasattr(row, 'keys') else row['id']
        email = row[1] if not hasattr(row, 'keys') else row['email']

        c.execute('''UPDATE users SET
                      subscription_status = 'pending_deletion',
                      deleted_at = ?,
                      updated_at = ?
                      WHERE id = ?''',
                  (now.isoformat(), now.isoformat(), user_id))
        count += 1
        logger.info("Marked user %s (%s) as pending_deletion.", user_id, email)

    conn.commit()
    conn.close()

    # Log events (separate connections since log_subscription_event manages its own)
    for row in rows:
        user_id = row[0] if not hasattr(row, 'keys') else row['id']
        log_subscription_event(user_id, 'marked_pending_deletion')

    logger.info("Marked %d users as pending_deletion.", count)
    return count


# ---------------------------------------------------------------------------
# 5. Purge expired deletions (72-hour grace period)
# ---------------------------------------------------------------------------
def purge_expired_deletions():
    """Purge accounts that are past the 72-hour grace period."""
    conn = get_connection()
    c = conn.cursor()

    # Find users with pending_deletion status and deleted_at > 72 hours ago
    cutoff = (datetime.now() - timedelta(hours=72)).isoformat()
    c.execute("SELECT id, email, plan FROM users WHERE subscription_status = 'pending_deletion' AND deleted_at IS NOT NULL AND deleted_at < ?", (cutoff,))
    users_to_purge = c.fetchall()
    conn.close()

    if not users_to_purge:
        logger.info("No expired deletions to purge.")
        return 0

    purged_count = 0
    for row in users_to_purge:
        user_id = row[0] if not hasattr(row, 'keys') else row['id']
        email = row[1] if not hasattr(row, 'keys') else row['email']
        plan = row[2] if not hasattr(row, 'keys') else row['plan']

        try:
            tables = purge_user_data(user_id)
            record_account_deletion(user_id, email, plan, 'user_requested', 'system', tables)
            purged_count += 1
            logger.info("Purged account: %s (%s)", user_id, email)
        except Exception as e:
            logger.error("ERROR purging %s (%s): %s", user_id, email, e)

    logger.info("Purged %d expired deletion(s).", purged_count)
    return purged_count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run_all():
    """Execute all subscription lifecycle tasks."""
    logger.info("=== Subscription Lifecycle Job Starting ===")
    start = datetime.now()

    renewal_count = send_renewal_reminders()
    reminder_count = send_suspension_reminders()
    warning_count = send_final_deletion_warnings()
    deletion_count = mark_pending_deletions()
    purge_count = purge_expired_deletions()

    elapsed = (datetime.now() - start).total_seconds()
    logger.info(
        "=== Job Complete (%.1fs) === renewals=%d, reminders=%d, warnings=%d, pending_deletions=%d, purged=%d",
        elapsed, renewal_count, reminder_count, warning_count, deletion_count, purge_count
    )

    return {
        'renewal_reminders': renewal_count,
        'suspension_reminders': reminder_count,
        'final_warnings': warning_count,
        'pending_deletions': deletion_count,
        'purged_accounts': purge_count,
    }


if __name__ == '__main__':
    run_all()
