"""Support ticket helpers for GrantPro."""

from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from db_connection import get_connection

OPEN_STATUSES = {'open', 'triaged', 'waiting_on_customer', 'escalated'}
CLOSED_STATUSES = {'resolved', 'closed'}
ALL_STATUSES = tuple(sorted(OPEN_STATUSES | CLOSED_STATUSES))


def _now() -> str:
    return datetime.utcnow().isoformat()


def _safe_json(value) -> str:
    try:
        return json.dumps(value or [], ensure_ascii=False)
    except Exception:
        return '[]'


def _normalize_ticket_row(row: dict) -> dict:
    row = dict(row or {})
    row.setdefault('title', row.get('subject') or 'Support Ticket')
    row.setdefault('subject', row.get('title') or 'Support Ticket')
    row.setdefault('status', 'open')
    row.setdefault('priority', 'normal')
    row.setdefault('category', 'general')
    row.setdefault('canned_response', '')
    row.setdefault('escalation_reason', '')
    return row


def build_ticket_context(user, workflow: dict | None = None, subject: str = '', body: str = '') -> dict:
    workflow = workflow or {}
    stage = (workflow.get('stage') or 'unknown').strip()
    missing = workflow.get('missing') or []
    skipped = workflow.get('skipped') or []
    deadline = workflow.get('deadline') or ''
    text = f"{subject}\n{body}".lower()

    priority = 'normal'
    status = 'open'
    escalation_reason = ''

    if 'urgent' in text or 'deadline' in text:
        priority = 'high'
        status = 'escalated'
        escalation_reason = 'User marked deadline/urgent in request.'
    elif deadline:
        priority = 'high'
        status = 'escalated'
        escalation_reason = f'Workflow deadline on {deadline} requires same-day review.'
    elif stage in {'drafting', 'review', 'submission_ready'}:
        priority = 'high'
        status = 'triaged'
    elif stage in {'waiting_for_docs', 'incomplete', 'blocked'} or missing or skipped:
        status = 'waiting_on_customer'

    canned_response = generate_canned_response(stage, subject, missing, skipped, deadline, priority)
    return {
        'priority': priority,
        'status': status,
        'escalation_reason': escalation_reason,
        'canned_response': canned_response,
        'workflow_stage': stage,
        'workflow_missing_json': _safe_json(missing),
        'workflow_deadline': deadline or None,
    }


def generate_canned_response(stage: str, subject: str, missing, skipped, deadline: str, priority: str) -> str:
    if deadline:
        return f"Thanks — we flagged this for priority handling because your workflow has a deadline on {deadline}."
    if missing:
        items = ', '.join(missing[:3])
        return f"Thanks for the ticket. We need a few workflow items first: {items}. Once those are uploaded, we can move this forward."
    if stage in {'drafting', 'review', 'submission_ready'}:
        return "Thanks — your request is in active workflow. We have triaged this for support review and will respond with the next action."
    if priority == 'high':
        return "Thanks — this has been prioritized for support review."
    return "Thanks — we received your support request and will review it shortly."


def create_support_ticket(user_id: str, subject: str, body: str, category: str = 'general', workflow: dict | None = None, source: str = 'portal') -> str:
    conn = get_connection()
    try:
        context = build_ticket_context({'id': user_id}, workflow=workflow, subject=subject, body=body)
        ticket_id = str(uuid4())
        conn.execute(
            '''INSERT INTO support_tickets (
                id, user_id, subject, title, body, category, status, priority, source,
                workflow_stage, workflow_missing_json, workflow_deadline, canned_response,
                escalation_reason, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                ticket_id, user_id, subject, subject, body, category, context['status'], context['priority'], source,
                context['workflow_stage'], context['workflow_missing_json'], context['workflow_deadline'], context['canned_response'],
                context['escalation_reason'], _now(), _now(),
            ),
        )
        conn.execute(
            'INSERT INTO support_ticket_messages (id, ticket_id, sender_type, body, created_at) VALUES (?, ?, ?, ?, ?)',
            (str(uuid4()), ticket_id, 'customer', body, _now()),
        )
        conn.commit()
        return ticket_id
    finally:
        conn.close()


def get_support_tickets_for_user(user_id: str, limit: int = 8):
    conn = get_connection()
    try:
        rows = conn.execute(
            '''SELECT id, title, subject, status, priority, category, canned_response, escalation_reason, updated_at, created_at
               FROM support_tickets WHERE user_id = ? ORDER BY COALESCE(updated_at, created_at) DESC LIMIT ?''',
            (user_id, limit),
        ).fetchall()
        return [_normalize_ticket_row(dict(row)) for row in rows]
    finally:
        conn.close()
