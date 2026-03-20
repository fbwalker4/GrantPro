#!/usr/bin/env python3
"""
Deadline Reminder System - Track and notify about grant deadlines
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
import os

class DeadlineReminder:
    """Manage grant deadline reminders"""
    
    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = Path.home() / ".hermes" / "grant-system" / "data"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.reminders_file = self.data_dir / "deadline_reminders.json"
        self.reminders = self._load_reminders()
    
    def _load_reminders(self):
        """Load reminders from file"""
        if self.reminders_file.exists():
            with open(self.reminders_file) as f:
                return json.load(f)
        return {"reminders": [], "settings": self._default_settings()}
    
    def _save_reminders(self):
        """Save reminders to file"""
        with open(self.reminders_file, 'w') as f:
            json.dump(self.reminders, f, indent=2, default=str)
    
    def _default_settings(self):
        """Default reminder settings"""
        return {
            "email_enabled": False,
            "email_recipients": [],
            "reminder_days": [7, 3, 1],  # Days before deadline
            "telegram_enabled": True,
            "telegram_chat_id": None
        }
    
    def add_grant_deadline(self, grant_id, grant_title, deadline_date, grant_url=""):
        """Add a grant deadline to track"""
        # Parse deadline date
        if isinstance(deadline_date, str):
            try:
                deadline = datetime.strptime(deadline_date, "%Y-%m-%d")
            except ValueError:
                try:
                    deadline = datetime.strptime(deadline_date, "%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    return {"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}
        else:
            deadline = deadline_date
        
        reminder = {
            "id": f"reminder_{len(self.reminders['reminders']) + 1}",
            "grant_id": grant_id,
            "title": grant_title,
            "deadline": deadline.isoformat(),
            "grant_url": grant_url,
            "created_at": datetime.now().isoformat(),
            "notifications": [],
            "status": "active"
        }
        
        # Check for duplicates
        for existing in self.reminders['reminders']:
            if existing.get('grant_id') == grant_id and existing.get('status') == 'active':
                return {"success": False, "error": "Deadline already tracked for this grant"}
        
        self.reminders['reminders'].append(reminder)
        self._save_reminders()
        
        return {"success": True, "reminder": reminder}
    
    def remove_deadline(self, reminder_id):
        """Remove a deadline reminder"""
        for i, reminder in enumerate(self.reminders['reminders']):
            if reminder['id'] == reminder_id:
                self.reminders['reminders'][i]['status'] = 'removed'
                self._save_reminders()
                return {"success": True}
        return {"success": False, "error": "Reminder not found"}
    
    def get_upcoming(self, days_ahead=30):
        """Get upcoming deadlines within specified days"""
        now = datetime.now()
        upcoming = []
        
        for reminder in self.reminders['reminders']:
            if reminder.get('status') != 'active':
                continue
            
            deadline = datetime.fromisoformat(reminder['deadline'])
            days_until = (deadline - now).days
            
            if 0 <= days_until <= days_ahead:
                reminder_copy = reminder.copy()
                reminder_copy['days_until'] = days_until
                reminder_copy['urgency'] = self._get_urgency(days_until)
                upcoming.append(reminder_copy)
        
        # Sort by deadline
        upcoming.sort(key=lambda x: x['deadline'])
        return upcoming
    
    def get_overdue(self):
        """Get overdue deadlines"""
        now = datetime.now()
        overdue = []
        
        for reminder in self.reminders['reminders']:
            if reminder.get('status') != 'active':
                continue
            
            deadline = datetime.fromisoformat(reminder['deadline'])
            if deadline < now:
                days_overdue = (now - deadline).days
                reminder_copy = reminder.copy()
                reminder_copy['days_overdue'] = days_overdue
                overdue.append(reminder_copy)
        
        return overdue
    
    def _get_urgency(self, days_until):
        """Get urgency level based on days until deadline"""
        if days_until <= 1:
            return "critical"
        elif days_until <= 3:
            return "high"
        elif days_until <= 7:
            return "medium"
        else:
            return "low"
    
    def check_reminders(self):
        """Check which reminders need to be sent"""
        now = datetime.now()
        to_notify = []
        reminder_days = self.reminders['settings'].get('reminder_days', [7, 3, 1])
        
        for reminder in self.reminders['reminders']:
            if reminder.get('status') != 'active':
                continue
            
            deadline = datetime.fromisoformat(reminder['deadline'])
            days_until = (deadline - now).days
            
            # Check if we should notify
            if days_until in reminder_days:
                # Check if we haven't already notified
                notification_key = f"notified_{days_until}d"
                if notification_key not in reminder.get('notifications', []):
                    reminder_copy = reminder.copy()
                    reminder_copy['days_until'] = days_until
                    reminder_copy['notify_type'] = f"{days_until}-day"
                    to_notify.append(reminder_copy)
        
        return to_notify
    
    def mark_notified(self, reminder_id, days_before):
        """Mark a reminder as notified"""
        for reminder in self.reminders['reminders']:
            if reminder['id'] == reminder_id:
                notification_key = f"notified_{days_before}d"
                if 'notifications' not in reminder:
                    reminder['notifications'] = []
                if notification_key not in reminder['notifications']:
                    reminder['notifications'].append(notification_key)
                    self._save_reminders()
                return {"success": True}
        return {"success": False, "error": "Reminder not found"}
    
    def get_all(self):
        """Get all active reminders"""
        return [r for r in self.reminders['reminders'] if r.get('status') == 'active']
    
    def update_settings(self, **kwargs):
        """Update reminder settings"""
        self.reminders['settings'].update(kwargs)
        self._save_reminders()
        return {"success": True, "settings": self.reminders['settings']}
    
    def get_settings(self):
        """Get current settings"""
        return self.reminders['settings']
    
    def generate_calendar_link(self, reminder):
        """Generate Google Calendar link for a deadline"""
        deadline = datetime.fromisoformat(reminder['deadline'])
        
        # Format: YYYYMMDDTHHMMSSZ
        start = deadline.strftime("%Y%m%dT090000Z")
        end = deadline.strftime("%Y%m%dT100000Z")
        
        title = urllib.parse.quote(f"Grant Deadline: {reminder['title']}")
        details = urllib.parse.quote(reminder.get('grant_url', ''))
        
        calendar_url = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={title}&dates={start}/{end}&details={details}"
        
        return calendar_url
    
    def export_ics(self, reminder):
        """Export reminder as ICS file content"""
        from datetime import datetime
        
        deadline = datetime.fromisoformat(reminder['deadline'])
        
        ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Grant Reminder//EN
BEGIN:VEVENT
UID:{reminder['id']}@grant-system
DTSTAMP:{datetime.now().strftime("%Y%m%dT%H%M%S")}
DTSTART:{deadline.strftime("%Y%m%dT090000")}
SUMMARY:Grant Deadline: {reminder['title']}
DESCRIPTION:{reminder.get('grant_url', '')}
END:VEVENT
END:VCALENDAR"""
        
        return ics


if __name__ == "__main__":
    import urllib.parse
    
    # Demo
    reminders = DeadlineReminder()
    
    # Add some test deadlines
    from datetime import datetime, timedelta
    
    today = datetime.now()
    reminders.add_grant_deadline(
        "NSF-2025-001",
        "Smart and Connected Communities",
        (today + timedelta(days=7)).strftime("%Y-%m-%d"),
        "https://www.grants.gov"
    )
    
    reminders.add_grant_deadline(
        "DOE-2025-001", 
        "Small Business Innovation Research",
        (today + timedelta(days=3)).strftime("%Y-%m-%d"),
        "https://www.grants.gov"
    )
    
    print("=== Upcoming Deadlines ===")
    upcoming = reminders.get_upcoming(30)
    for u in upcoming:
        print(f"- {u['title']}: {u['days_until']} days ({u['urgency']})")
        print(f"  Calendar: {reminders.generate_calendar_link(u)}")
    
    print("\n=== Check Reminders ===")
    to_notify = reminders.check_reminders()
    print(f"Need to notify: {len(to_notify)}")
    for n in to_notify:
        print(f"- {n['title']}: {n['notify_type']} reminder")
