# GRANT TRACKING SYSTEM

## STATUS PIPELINE

| # | Status | Meaning |
|---|--------|----------|
| 1 | Lead | New prospect inquiry |
| 2 | Contacted | Initial outreach made |
| 3 | Qualified | Confirmed interest |
| 4 | Intake | Questionnaire completed |
| 5 | Docs | Required docs received |
| 6 | Drafting | AI writing narratives |
| 7 | Review | Client reviewing draft |
| 8 | Revisions | Making changes |
| 9 | Final | Ready to submit |
| 10 | Submitted | Application sent |
| 11 | Under Review | Awaiting decision |
| 12 | Funded | GRANT WON! |
| 13 | Not Funded | Denied |

---

## DATABASE FIELDS

| Field | Type |
|-------|------|
| Client Name | Text |
| Client Email | Text |
| Client Phone | Text |
| Organization | Text |
| Grant Name | Text |
| Funder | Text |
| Amount | Currency |
| Deadline | Date |
| Status | Select (1-13) |
| Submit Fee Paid | Checkbox |
| Success Fee | Currency |
| Success Fee Paid | Checkbox |
| Submitted Date | Date |
| Decision Date | Date |
| Notes | Long Text |

---

## SUCCESS FEE CALCULATOR

```
def calculate_fee(grant_amount, status):
    if status == "Funded":
        if grant_amount < 1000000:
            return 99 + 299
        else:
            return 99 + 499
    else:
        return 99
```

---

## REMINDER SCHEDULE

| When | Action |
|------|--------|
| Intake + 3 days | Follow up if docs not received |
| Deadline - 7 days | Confirm submission ready |
| Deadline - 1 day | Ensure submitted |
| Submitted + 30 days | Check status |
| If Funded | Send success invoice |
| Funded + 30 days | Follow up if not paid |
| If Not Funded | Send sympathy, ask for feedback |

---

## PAYMENT TRACKING

| Client | Grant | Amount | Submit Paid | Success Fee | Success Paid |
|--------|-------|--------|------------|-------------|----------------|
| | | | [ ] | $ | [ ] |
| | | | [ ] | $ | [ ] |
| | | | [ ] | $ | [ ] |

---

## QUICK STATS

Total Active Grants: ___
Submitted This Month: ___
Funded This Month: ___
Total Revenue: $___
Pending Success Fees: $___
