#!/usr/bin/env python3
"""Smoke test for Step 6 AI blocker plumbing."""

from pathlib import Path


def main():
    app_path = Path(__file__).resolve().parent.parent / 'portal' / 'app.py'
    text = app_path.read_text()
    assert 'def _workflow_blockers_text(workflow):' in text
    assert 'workflow_blockers = _workflow_blockers_text(workflow)' in text
    assert 'WORKFLOW BLOCKERS / MISSING INPUTS (from persisted workflow state)' in text
    assert 'Do NOT invent programs, partnerships, staff, statistics, or capabilities' in text
    assert 'blocker_suffix = f" Blockers: {workflow_blockers}." if workflow_blockers else ""' in text
    print('AI blocker prompt plumbing test passed')


if __name__ == '__main__':
    main()
