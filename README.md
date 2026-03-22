# GrantPro - AI-Powered Grant Writing System

An end-to-end grant writing platform powered by Google Gemini 2.5 Flash AI. Built for consultants, nonprofits, agencies, and small businesses who write federal grants.

**Website**: https://grantpro.org
**Local Server**: http://localhost:5001
**Business**: Futurespec Consulting, LLC

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Tech Stack](#tech-stack)
4. [Database](#database)
5. [Complete Route Map](#complete-route-map)
6. [Key Features](#key-features)
7. [Axiom Architecture](#axiom-architecture)
8. [Environment Variables](#environment-variables)
9. [Getting Started](#getting-started)
10. [Deployment](#deployment)
11. [Security](#security)
12. [Troubleshooting](#troubleshooting)
13. [Changelog](#changelog)

---

## Project Overview

GrantPro is a self-hosted web application that helps users discover, write, and submit federal grant applications. It combines a live-synced catalog of federal grant opportunities (seeded from 131 grants, updated daily from Grants.gov) with 21 agency-specific templates and AI-powered content generation to guide users through the entire grant lifecycle -- from research to submission tracking.

### Who It's For

| Audience | Use Case | Recommended Plan |
|----------|----------|------------------|
| **Consultants** | Write grants for multiple clients | Enterprise |
| **Government agencies** | In-house grant writers | Monthly or Annual |
| **Nonprofits** | Write their own grants | Free (research) / Monthly (writing) |
| **Small businesses** | SBIR/STTR grants | Monthly or Annual |

### Business Model

Subscription SaaS with six tiers from free to Enterprise Unlimited ($99.95/mo), including three enterprise plans for consultants managing multiple client agencies. Payments processed via Stripe.

| Tier | Price | Grants/Month | Organizations | Key Features |
|------|-------|--------------|---------------|--------------|
| **Free** | $0 | 0 | -- | Search grants, save favorites, eligibility checker, wizard |
| **Monthly** | $19.95/mo | 3 | 1 | AI writing, guided submission, paper submission, downloads, cloning, templates |
| **Annual** | $199.95/yr | 3/mo | 1 | Same as Monthly, save $39.45/year |
| **Enterprise 5** | $44.95/mo | Unlimited | 5 total orgs | Everything in Monthly + org switcher, client management, enterprise dashboard |
| **Enterprise 10** | $74.95/mo | Unlimited | 10 total orgs | Everything in Enterprise 5 + white-label reports |
| **Enterprise Unlimited** | $99.95/mo | Unlimited | Unlimited orgs | Everything, no caps |

Enterprise org limits are TOTAL (including the consultant's own org). A consultant who only manages clients still counts toward the limit.

### Enterprise Org Switcher

Enterprise users see a "Working as: [Org Name]" dropdown in the sidebar. Each client organization has:
- Full profile (EIN, UEI, address, mission, programs, past grants — same depth as user profile)
- Its own Organization Vault (501(c)(3) letter, audit, board resolution, etc.)
- Its own grants, budget builders, and submission checklists
- Separate SF-424 form data (client's credentials, not the consultant's)

Switching orgs is instant — no logout/login. All data queries scope to the active org. Non-enterprise users see no switcher — everything works as before.

### Current State

Production-ready. Supabase Postgres database with 25+ tables, 6,800+ line Flask app with 90+ routes, 58 HTML templates, 21 agency templates with regulatory intelligence, structured budget builder, chained AI generation with APA standards, 16-point consistency review, submission checklist with 100% gate, document uploads, MOU generation, organization vault, paper submission (SF-424 forms), post-submission tracking, enterprise org switcher with per-client profiles/vaults, award detection, testimonial pipeline, and 1,773 live grants synced from Grants.gov.

---

## Architecture

```
~/.hermes/grant-system/
├── portal/                         # Flask web application
│   ├── app.py                      # Main Flask app (5,277 lines, all routes)
│   ├── requirements.txt            # Python dependencies
│   ├── static/
│   │   └── images/
│   │       └── gp_logo.png         # GrantPro logo
│   └── templates/                  # 51 Jinja2 HTML templates
│       ├── layout.html             # Base template (dark theme, nav, fonts)
│       ├── landing.html            # Public landing page
│       ├── about.html              # About page
│       ├── pricing.html            # Pricing tiers
│       ├── contact.html            # Contact form
│       ├── login.html              # Login form
│       ├── signup.html             # Registration form
│       ├── forgot_password.html    # Password reset request
│       ├── reset_password.html     # Password reset form
│       ├── dashboard.html          # User dashboard
│       ├── profile.html            # User profile editor
│       ├── onboarding.html         # New user onboarding wizard (Grant Readiness Profile)
│       ├── wizard.html             # Grant matching wizard
│       ├── wizard_recommendations.html # Wizard results
│       ├── eligibility.html        # Eligibility checker
│       ├── grants.html             # Saved grants list
│       ├── my_grants.html          # User's grant applications
│       ├── grant_info.html         # Grant detail (research view)
│       ├── grant_form.html         # Start a new grant application
│       ├── grant_detail.html       # Grant application detail
│       ├── grant_research.html     # Grant search/research
│       ├── section_form.html       # Edit a single grant section
│       ├── guided_submission.html  # Side-by-side submission workflow
│       ├── budget_builder.html     # Structured budget builder (axioms, MTDC, auto-calc)
│       ├── grant_checklist.html    # Submission readiness checklist (100% gate)
│       ├── paper_submission.html   # SF-424 / paper submission package
│       ├── mark_submitted.html     # Record submission confirmation
│       ├── select_client.html      # Client selector
│       ├── select_client_for_grant.html # Client selector for grants
│       ├── clients.html            # Client list
│       ├── client_form.html        # Add/edit client
│       ├── client_detail.html      # Client detail view
│       ├── intake_form.html        # Client intake questionnaire
│       ├── upgrade.html            # Plan upgrade page
│       ├── payment_manual.html     # Manual payment instructions
│       ├── payment_success.html    # Payment confirmation
│       ├── list_templates.html     # Browse agency templates
│       ├── view_template.html      # View single template
│       ├── admin.html              # Admin dashboard
│       ├── admin_grants.html       # Admin grant management
│       ├── admin_templates.html    # Admin template CMS
│       ├── admin_leads.html        # Admin leads management
│       ├── admin_emails.html       # Admin email tools
│       ├── admin_testimonials.html # Admin testimonial approval workflow
│       ├── testimonial_form.html   # Token-based testimonial submission form
│       ├── testimonial_thankyou.html # Testimonial submission confirmation
│       ├── terms.html              # Terms of Service
│       ├── privacy.html            # Privacy Policy
│       ├── refund.html             # Refund Policy
│       ├── help.html               # FAQ / Help
│       └── message.html            # Flash message page
├── core/                           # Backend business logic
│   ├── db_connection.py            # Database connection factory (Supabase Postgres + SQLite fallback)
│   ├── user_models.py              # User auth, profiles, subscriptions, grant readiness
│   ├── grant_db.py                 # Grant/client/draft/document/budget/checklist schema + CRUD
│   ├── email_system.py             # Transactional email (Resend API)
│   ├── stripe_payment.py           # Stripe subscription integration
│   ├── budget_builder.py           # Budget category builder (personnel, fringe, travel, etc.)
│   ├── deadline_reminder.py        # Deadline notification system
│   ├── pdf_utils.py                # PDF branding, markdown cleaning, redundancy detection
│   └── cli.py                      # Command-line interface
├── api/                            # Vercel serverless entry points
│   ├── index.py                    # WSGI adapter wrapping Flask app for Vercel
│   └── health.py                   # Health check endpoint (DB connectivity, module imports)
├── jobs/                           # Automated background jobs (cron)
│   ├── sync_grants_gov.py          # Daily Grants.gov catalog sync
│   ├── check_awards.py             # Award winner detection via USAspending.gov
│   └── README.md                   # Job documentation
├── research/                       # Grant research engine + regulatory data
│   ├── grant_researcher.py         # Grant search, filtering, matching
│   ├── iot_grants_db.json          # 131 federal grant opportunities (seed data)
│   ├── grants.db                   # Research SQLite database (legacy, read-only)
│   ├── agency_compliance_batch1.json         # Regulatory compliance data (batch 1)
│   └── agency_regulatory_requirements_batch2.json # Regulatory compliance data (batch 2)
├── templates/                      # Agency template definitions
│   └── agency_templates.json       # 21 agency templates with eligibility, compliance, ai_context
├── supabase_migration.sql          # Supabase Postgres schema (20 tables; 3 more in grant_db.py)
├── vercel.json                     # Vercel deployment configuration
├── .env.example                    # Environment variable template
├── requirements.txt                # Root-level Python dependencies
├── tracking/                       # Legacy data storage
│   └── clients.json                # Legacy client records
├── data/                           # Runtime data
│   └── deadline_reminders.json     # Reminder state
├── archive/                        # Archived test/utility scripts
│   ├── sqlite-deprecated/          # Pre-migration SQLite databases
│   ├── check_template.py
│   ├── fix_budget_data.py
│   ├── list_templates.py
│   ├── setup_test_user.py
│   ├── simple_test.py
│   ├── test_ai_org.py
│   ├── test_ai.py
│   ├── test_all_templates.py
│   ├── test_fast.py
│   ├── test_generic.py
│   ├── test_quick.py
│   ├── test_template.py
│   └── DEPRECATED.md
├── docs/                           # Documentation
│   ├── competitive-analysis.md
│   ├── comprehensive-testing-report.md
│   └── user-testing-report.md
├── documents/                      # Uploaded documents directory
├── drafts/                         # Draft exports directory
├── output/                         # Generated file output directory
├── reviews/                        # Grant reviews directory
├── intake/                         # Intake form template
│   └── questionnaire.html
├── invoices/                       # Invoice template
│   └── template.html
├── marketing/                      # Marketing assets
│   └── landing-page.html
├── AI_PROMPTS.md                   # AI prompt templates per section
├── INTAKE_QUESTIONS.md             # 37 client intake questions
├── DOCUMENT_CHECKLIST.md           # Required docs per grant type
├── AGREEMENT.md                    # Client service agreement
├── TRACKING.md                     # Pipeline stage definitions
├── README.md                       # This file
└── .gitignore                      # Git ignore rules
```

---

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Language** | Python 3.10+ | |
| **Web framework** | Flask >= 2.3.0 | Single monolith: `portal/app.py` |
| **Database** | Supabase Postgres | Via `psycopg2-binary` with `_HybridRow` / `_PgConnectionWrapper` in `core/db_connection.py` |
| **AI engine** | Google Gemini 2.5 Flash | Via `google-genai` >= 1.0.0 |
| **Payments** | Stripe >= 5.0.0 | Checkout, webhooks, subscription lifecycle |
| **PDF generation** | ReportLab >= 4.0.0 | SF-424 forms, paper packages, branded exports |
| **DOCX generation** | python-docx >= 0.8.0 | Grant downloads |
| **HTTP client** | Requests >= 2.28.0 | Grants.gov API, USAspending.gov API |
| **Email** | Resend API >= 0.7.0 | Console fallback in dev |
| **Hosting** | Vercel (serverless) | `api/index.py` WSGI adapter, `api/health.py` diagnostics |
| **Templating** | Jinja2 | Bundled with Flask |
| **Fonts** | Inter + Playfair Display | Google Fonts CDN |
| **CSS** | Custom dark theme | CSS custom properties, no framework |
| **JavaScript** | Vanilla JS only | No React/Vue/Angular |
| **Auth** | Custom PBKDF2 | 100,000 iterations, SHA-256 |

### Database Connection Architecture

`core/db_connection.py` provides a compatibility layer so the entire codebase can use SQLite-style `?` placeholders and `row['column']` access while running against Postgres:

- **`_sqlite_placeholder_to_pg()`** -- converts `?` to `%s`, translates `INSERT OR IGNORE` to `ON CONFLICT DO NOTHING`, etc.
- **`_HybridRow`** -- a `dict` subclass that also supports integer indexing (`row[0]`), bridging psycopg2's `RealDictRow` and SQLite's `Row`.
- **`_PgCursorWrapper`** -- wraps `RealDictCursor`, translates placeholders, skips `PRAGMA` statements.
- **`_PgConnectionWrapper`** -- wraps `psycopg2.connect()`, provides `conn.execute()` shortcut matching SQLite API.
- **`get_connection()`** -- returns Postgres if `GP_DATABASE_URL` is set, otherwise falls back to local SQLite.

### What Was Rejected (and Why)

- **OpenRouter** -- unnecessary middleman for AI
- **Next.js/React** -- over-engineering for this use case
- **Auth0/Clerk** -- adds cost and third-party dependency

---

## Database

All tables live in a single Supabase Postgres instance. **23 tables total**: 20 defined in `supabase_migration.sql` + 3 created by `core/grant_db.py` at runtime (`grant_documents`, `grant_readiness`, `grant_checklist`).

Both local development and Vercel production connect to the same Supabase Postgres instance via the connection pooler. SQLite is retained only as an emergency fallback.

### Table Summary (23 tables)

| # | Table | Source | Purpose |
|---|-------|--------|---------|
| 1 | `users` | migration.sql | User accounts (23 columns: auth, org, plan, Stripe, onboarding) |
| 2 | `user_profiles` | migration.sql | Bio, interests, entity types, notification prefs |
| 3 | `saved_grants` | migration.sql | User-bookmarked grants (UNIQUE user_id + grant_id) |
| 4 | `user_applications` | migration.sql | Grant application tracking (status, progress %) |
| 5 | `password_resets` | migration.sql | Token-based password reset flow |
| 6 | `organization_details` | migration.sql | EIN, DUNS, UEI, address, SAM.gov registration data |
| 7 | `organization_profile` | migration.sql | Revenue, founded year, employees, mission |
| 8 | `mission_focus` | migration.sql | Focus areas per user (UNIQUE user_id + focus_area) |
| 9 | `past_grant_experience` | migration.sql | Grant history: name, funder, year, amount, status |
| 10 | `clients` | migration.sql | Enterprise client orgs (consultant workflow) |
| 11 | `grants` | migration.sql | Grant applications with submission tracking (17 columns) |
| 12 | `documents` | migration.sql | Client documents (legacy) |
| 13 | `invoices` | migration.sql | Invoices per client per grant |
| 14 | `drafts` | migration.sql | Section content per grant (version-tracked) |
| 15 | `grants_catalog` | migration.sql | Federal grant opportunities (seeded from 131, synced daily) |
| 16 | `award_matches` | migration.sql | USAspending.gov award detections |
| 17 | `testimonials` | migration.sql | User testimonials with admin approval workflow |
| 18 | `grant_budget` | migration.sql | Structured budget data (personnel, fringe, travel, equipment, supplies, contractual, construction, other, participant support, indirect, match) |
| 19 | `guest_saves` | migration.sql | Unauthenticated grant bookmarks |
| 20 | `leads` | migration.sql | Newsletter subscribers |
| 21 | `grant_documents` | grant_db.py | Uploaded/generated documents per grant application |
| 22 | `grant_readiness` | grant_db.py | Grant readiness profile (applicant type, registrations, capacity) |
| 23 | `grant_checklist` | grant_db.py | Submission checklist items (self-certifications, completion tracking) |

### Key Schema Details

**grant_budget** -- The structured budget table stores all budget categories as JSON arrays (personnel, travel_items, equipment_items, contractual_items, other_items) plus scalar totals. Includes MTDC base calculation, indirect rate/type, and cost share (match_cash + match_inkind). This table is the single source of truth ("axiom") for all budget data -- AI reads it but never writes to it.

**grant_readiness** -- Stores the user's Grant Readiness Profile: applicant category, 501(c)(3) status, SAM.gov registration, UEI, Grants.gov account, construction experience, dedicated grants admin, largest grant managed, preferred funding range, and focus areas.

**grant_checklist** -- Tracks per-item completion of the submission checklist (self-certifications like lobbying disclosure, drug-free workplace, debarment). Auto-checked items (sections completed, documents uploaded) are computed at render time.

---

## Complete Route Map

All 80+ routes are defined in `portal/app.py` (5,277 lines). Decorators listed in application order.

### Public Routes (no auth required)

| Route | Method | Function | Description |
|-------|--------|----------|-------------|
| `/` | GET | `index` | Landing page (redirects to dashboard if logged in) |
| `/about` | GET | `about` | About page |
| `/pricing` | GET | `pricing` | Pricing tiers page |
| `/help`, `/faq` | GET | `help_page` | FAQ / help page |
| `/terms` | GET | `terms` | Terms of Service |
| `/privacy` | GET | `privacy` | Privacy Policy |
| `/refund` | GET | `refund` | Refund Policy |
| `/contact` | GET, POST | `contact` | Contact form (csrf_required) |
| `/unsubscribe` | GET, POST | -- | Email unsubscribe (csrf_required on POST) |
| `/static/images/<path>` | GET | `serve_image` | Static image serving |

### Auth Routes

| Route | Method | Function | Decorators | Description |
|-------|--------|----------|------------|-------------|
| `/login` | GET, POST | `login` | csrf_required | User login |
| `/signup` | GET, POST | `signup` | csrf_required | User registration |
| `/logout` | GET | `logout` | -- | Logout (clears session) |
| `/forgot-password` | GET, POST | `forgot_password` | csrf_required | Request password reset |
| `/reset-password/<token>` | GET, POST | `reset_password` | csrf_required | Reset password with token |

### User Routes

| Route | Method | Function | Decorators | Description |
|-------|--------|----------|------------|-------------|
| `/dashboard` | GET | `dashboard` | login_required | User dashboard with stats |
| `/profile` | GET, POST | `profile` | login_required, csrf_required | Edit profile and preferences |
| `/onboarding` | GET, POST | `onboarding` | login_required, csrf_required | Grant Readiness Profile onboarding wizard |
| `/settings` | GET | `settings` | login_required | User settings page |

### Subscription and Payment Routes

| Route | Method | Function | Decorators | Description |
|-------|--------|----------|------------|-------------|
| `/upgrade` | GET, POST | `upgrade` | login_required, csrf_required | Plan upgrade page |
| `/payment/checkout` | GET | `payment_checkout` | login_required | Stripe checkout redirect |
| `/payment/success` | GET | `payment_success` | login_required | Payment confirmation |
| `/payment/cancel` | GET | `payment_cancel` | -- | Payment cancellation |
| `/subscription/manage` | GET | `subscription_manage` | login_required | Manage subscription |
| `/subscription/cancel` | POST | `subscription_cancel` | login_required | Cancel subscription |
| `/webhook/stripe` | POST | `stripe_webhook` | -- | Stripe webhook handler |
| `/api/subscribe` | POST | `api_subscribe` | csrf_required | Newsletter subscribe |

### Grant Discovery Routes

| Route | Method | Function | Decorators | Description |
|-------|--------|----------|------------|-------------|
| `/wizard` | GET | `wizard` | login_required | Grant matching wizard |
| `/api/wizard/save` | POST | `wizard_save` | login_required, csrf_required | Save wizard answers |
| `/wizard/recommendations` | GET | `wizard_recommendations` | login_required | View wizard results |
| `/eligibility` | GET | `eligibility` | -- | Eligibility checker page |
| `/api/check-eligibility` | POST | `check_eligibility` | csrf_required | Run eligibility check |
| `/research` | GET | `research` | login_required | Grant research page |
| `/api/search-grants` | GET | `search_grants` | -- | Search grants API |
| `/api/grant/<grant_id>` | GET | `get_grant` | -- | Get single grant data |
| `/grants` | GET | `grants_list` | login_required | Saved grants list (with eligibility screening) |
| `/api/save-grant` | POST | `save_grant` | csrf_required_allow_guest | Save/favorite a grant |
| `/api/unsave-grant` | POST | `unsave_grant` | login_required, csrf_required | Remove saved grant |
| `/api/is-saved-grant/<id>` | GET | `is_saved_grant` | -- | Check if grant is saved |
| `/api/request-template` | POST | `request_template` | csrf_required | Request a template for a grant |

### Grant Application Routes

| Route | Method | Function | Decorators | Description |
|-------|--------|----------|------------|-------------|
| `/my-grants` | GET | `my_grants` | login_required | User's grant applications |
| `/apply` | GET | `apply` | login_required | Apply for a grant (select client) |
| `/grant-info/<grant_id>` | GET | `grant_info` | login_required | Grant info before starting |
| `/start-grant/<grant_id>` | GET, POST | `start_grant` | login_required, paid_required, csrf_required | Start a new application |
| `/grant/<grant_id>` | GET | `grant_detail` | login_required | View grant application |
| `/grant/<grant_id>/section/<section>` | GET, POST | `section_form` | login_required, csrf_required | Edit a section |
| `/grant/<grant_id>/generate/<section_id>` | POST | `generate_section` | rate_limit(10/60s), login_required, paid_required, csrf_required | AI-generate section content |
| `/grant/<grant_id>/use-template` | GET | `use_template` | login_required | Apply template to grant |
| `/grant/<grant_id>/clone` | POST | `clone_grant` | login_required, paid_required, csrf_required | Clone a grant application |

### Budget Builder Routes

| Route | Method | Function | Decorators | Description |
|-------|--------|----------|------------|-------------|
| `/grant/<grant_id>/budget-builder` | GET, POST | `budget_builder` | login_required, csrf_required | Structured budget builder (axiom data) |

### Submission Checklist and Document Routes

| Route | Method | Function | Decorators | Description |
|-------|--------|----------|------------|-------------|
| `/grant/<grant_id>/checklist` | GET | `grant_checklist` | login_required | Submission readiness checklist (100% gate) |
| `/grant/<grant_id>/checklist/complete-item` | POST | `complete_checklist_item` | login_required, csrf_required | Mark checklist item complete |
| `/grant/<grant_id>/run-consistency-check` | POST | `run_consistency_check` | login_required, csrf_required | AI consistency review of full application |
| `/grant/<grant_id>/upload-document` | POST | `upload_document` | login_required, csrf_required | Upload supporting document |
| `/grant/<grant_id>/documents` | GET | `grant_documents` | login_required | View uploaded documents |
| `/grant/<grant_id>/document/<doc_id>/delete` | POST | `delete_document` | login_required, csrf_required | Delete an uploaded document |
| `/grant/<grant_id>/generate-document` | POST | `generate_document` | login_required, paid_required, csrf_required | AI-generate MOU or letter of support |

### Submission and Tracking Routes

| Route | Method | Function | Decorators | Description |
|-------|--------|----------|------------|-------------|
| `/grant/<grant_id>/guided` | GET | `guided_submission` | login_required, paid_required | Side-by-side guided submission |
| `/grant/<grant_id>/paper-submission` | GET | `paper_submission` | login_required, paid_required | Paper/SF-424 submission page |
| `/grant/<grant_id>/paper-download` | GET | `paper_download` | login_required, paid_required | Download full paper package (PDF) |
| `/grant/<grant_id>/paper-download-form/<form>` | GET | `paper_download_form` | login_required, paid_required | Download individual SF-424 form |
| `/grant/<grant_id>/mark-submitted` | GET, POST | `mark_submitted` | login_required, paid_required, csrf_required | Record submission details |
| `/grant/<grant_id>/update-status` | POST | `update_status` | login_required, paid_required, csrf_required | Update funded/rejected status |
| `/grant/<grant_id>/download/<fmt>` | GET | `download_grant` | login_required, paid_required | Download as DOCX/PDF/TXT |
| `/grant/<grant_id>/calendar.ics` | GET | `grant_calendar` | login_required | Export deadline as ICS calendar event |
| `/api/copy-section` | POST | `copy_section` | login_required, csrf_required | Copy section content to clipboard |

### Client Management Routes

| Route | Method | Function | Decorators | Description |
|-------|--------|----------|------------|-------------|
| `/clients` | GET | `clients_list` | login_required | List user's clients |
| `/client/new` | GET, POST | `client_new` | login_required, csrf_required | Create new client |
| `/client/<client_id>` | GET | `client_detail` | login_required | View client |
| `/client/<client_id>/intake` | GET, POST | `client_intake` | login_required, csrf_required | Client intake form |
| `/client/<client_id>/grant/new` | GET, POST | `client_grant_new` | login_required, csrf_required | Start grant for client |

### Template Routes

| Route | Method | Function | Decorators | Description |
|-------|--------|----------|------------|-------------|
| `/templates` | GET | `list_templates` | login_required | Browse all agency templates |
| `/template/<template_name>` | GET | `view_template` | -- | View single template detail |

### Award and Testimonial Routes

| Route | Method | Function | Decorators | Description |
|-------|--------|----------|------------|-------------|
| `/testimonial/<token>` | GET | `testimonial_form` | -- | Token-based testimonial submission form |
| `/testimonial/<token>` | POST | `testimonial_submit` | -- | Submit testimonial |

### Admin Routes (login_required + admin_required)

| Route | Method | Function | Decorators | Description |
|-------|--------|----------|------------|-------------|
| `/admin` | GET | `admin_index` | checks role inline | Admin dashboard |
| `/admin/dashboard` | GET | `admin_dashboard` | -- | Admin dashboard redirect |
| `/admin/grants` | GET | `admin_grants` | login_required, admin_required | Manage all grants |
| `/admin/grants/<action>` | GET, POST | `admin_grants` | login_required, admin_required | Grant CRUD actions |
| `/admin/templates` | GET, POST | `admin_templates` | login_required, admin_required | Template CMS |
| `/admin/leads` | GET | `admin_leads` | login_required, admin_required | View leads/subscribers |
| `/admin/leads/delete/<id>` | GET | `admin_leads_delete` | login_required, admin_required | Delete a lead |
| `/admin/emails` | GET | `admin_emails` | login_required, admin_required | Email management |
| `/admin/emails/send-test` | POST | `admin_send_test` | login_required, admin_required | Send test email |
| `/admin/export-leads` | GET | `admin_export_leads` | login_required, admin_required | Export leads as CSV |
| `/admin/testimonials` | GET | `admin_testimonials` | login_required, admin_required | View pending testimonials |
| `/admin/testimonials/<tid>/approve` | POST | `admin_testimonial_approve` | login_required, admin_required | Approve testimonial |
| `/admin/testimonials/<tid>/reject` | POST | `admin_testimonial_reject` | login_required, admin_required | Reject testimonial |

---

## Key Features

### 1. Structured Budget Builder (LIVE)

User-entered budget data stored as structured axioms in `grant_budget` table. AI can read this data but cannot modify it -- only users can change budget figures.

- Standard federal categories: personnel, fringe, travel, equipment, supplies, contractual, construction, other, participant support
- Auto-calculated totals, MTDC (Modified Total Direct Costs) base, indirect costs
- Indirect rate types: de minimis (10%), negotiated NICRA, or agency-specific caps
- Cost share tracking (cash + in-kind match)
- Budget data injected into AI prompts for budget justification generation

### 2. Chained AI Generation (LIVE)

When generating any section, the AI receives all previously written sections so content stays consistent across the entire application.

- Sections see each other: project description references budget figures, evaluation plan references methodology
- Budget data injected from `grant_budget` axioms
- Organization data injected from Grant Readiness Profile
- Agency compliance rules injected from template `ai_context` field
- Retry logic with exponential backoff (3 retries) for transient API/SSL errors
- Rate limited: 10 requests per 60 seconds per IP

### 3. AI Consistency Review (LIVE)

Full-application review run via `/grant/<id>/run-consistency-check`. Uses Gemini 2.5 Flash to analyze all sections together and flag:

- Budget total mismatches between SF-424 and budget builder
- Project title inconsistencies across sections
- Redundant content (same sentences appearing in multiple sections, detected by `core/pdf_utils.py:detect_redundant_sentences()`)
- Missing required components
- Indirect cost rate inconsistencies
- Date/timeline discrepancies

### 4. Submission Checklist with 100% Gate (LIVE)

The checklist at `/grant/<id>/checklist` tracks four categories:

- **Standard Forms**: SF-424, SF-424A, SF-424B, agency-specific forms
- **Narrative Sections**: Every required section from agency template, linked to section editor
- **Required Documents**: Agency-template-specified documents (letters of support, org chart, audit report, NICRA)
- **Self-Certifications**: Lobbying disclosure, drug-free workplace, debarment/suspension

The "Submit" action is only enabled when the checklist reaches 100%. Print Draft is available at any completion level.

### 5. Eligibility Screening (LIVE)

Real-time screening on the grants list against the user's Grant Readiness Profile:

- **Grant type blocking**: Formula/entitlement grants flagged as non-competitive
- **Applicant type matching**: Each template defines `eligible_applicant_types`; mismatches shown grayed out
- **Registration warnings**: Missing SAM.gov, UEI, or Grants.gov account flagged with badges

### 6. Agency Regulatory Intelligence (LIVE)

All 21 templates enriched with compliance metadata from `research/agency_compliance_batch1.json` and `research/agency_regulatory_requirements_batch2.json`:

- Eligible applicant types per agency
- Compliance requirements: Davis-Bacon, Section 3, NEPA, Buy America, IRB, OMB Uniform Guidance, Single Audit
- Indirect cost rate rules (NICRA, de minimis, agency caps)
- Submission portal information (Grants.gov, Research.gov, NSPIRES, eBRAP, etc.)
- AI context guidance injected into generation prompts

### 7. Grant Readiness Profile (LIVE)

Multi-step onboarding wizard collects:

- Applicant type (nonprofit, state/local government, tribal, higher ed, small business, individual)
- Federal registrations: SAM.gov, UEI, Grants.gov account
- Capacity indicators: construction experience, grants administrator, largest grant managed
- Funding preferences and focus areas

Stored in `grant_readiness` table. Drives eligibility screening, AI generation context, checklist warnings, and wizard recommendations.

### 8. Document Upload + MOU Generator (LIVE)

- Upload supporting documents (PDF, DOCX, DOC, JPG, PNG) per grant application
- Track which required documents have been uploaded vs. missing
- AI-generate draft MOUs and letters of support based on grant scope, partner roles, and compliance framework
- Generated drafts downloadable as DOCX or PDF

### 9. Paper Submission / SF-424 Forms (LIVE)

- SF-424, SF-424A (Budget), SF-424B (Assurances) generation via ReportLab
- Organization data pre-filled from profile
- Full paper package as single PDF download
- Individual form downloads
- Print-optimized layout

### 10. Post-Submission Tracking (LIVE)

- Mark submitted with date, confirmation number, portal used, notes
- Update status: funded (with amount) or rejected (with reason)
- Notification date tracking
- Dashboard stats: active grants, submitted count, total funded amount

### 11. Enterprise Tiers (LIVE)

Three enterprise plans for consultants writing grants for client organizations:

- Enterprise 5: up to 5 client agencies, unlimited grants
- Enterprise 10: up to 10 clients, white-label reports
- Enterprise Unlimited: no caps

Anti-reseller policy: Free/Monthly/Annual plans restricted to account holder's own organization.

### 12. Award Detection + Testimonials (LIVE)

Automated pipeline:

1. `jobs/check_awards.py` queries USAspending.gov daily
2. Matches awards against GrantPro users by org name + opportunity number
3. Sends congratulations email with secure token link
4. User submits testimonial at `/testimonial/<token>`
5. Admin reviews at `/admin/testimonials`
6. Approved testimonials displayed on landing page

### 13. PDF/DOCX/TXT Export with Branding Toggle (LIVE)

`core/pdf_utils.py` provides:

- `clean_markdown()` -- converts markdown to ReportLab-compatible XML tags
- `split_markdown_sections()` -- parses heading/body pairs for structured PDF layout
- `detect_redundant_sentences()` -- finds duplicate content across sections
- `get_footer_callback(show_branding=True)` -- toggleable "Assembled by GrantPro.org" footer
- `add_grantpro_footer()` -- branded footer (left: branding text, right: page number)
- `_page_number_only()` -- page numbers only (no branding)

### 14. 21 Agency Templates

| # | Key | Agency | Sections |
|---|-----|--------|----------|
| 1 | `nsf` | National Science Foundation | 10 |
| 2 | `doe` | Department of Energy | 7 |
| 3 | `nih` | National Institutes of Health | 8 |
| 4 | `usda` | Department of Agriculture | 6 |
| 5 | `epa` | Environmental Protection Agency | 4 |
| 6 | `dot` | Department of Transportation | 4 |
| 7 | `nist` | National Institute of Standards and Technology | 3 |
| 8 | `nea` | National Endowment for the Arts | 5 |
| 9 | `nea_challenge` | NEA Challenge America | 4 |
| 10 | `generic` | Generic Federal Grant | 8 |
| 11 | `artist_individual` | Artist Individual | 5 |
| 12 | `micro_grant` | Micro-Grant | 4 |
| 13 | `small_business` | Small Business (SBIR/STTR) | 5 |
| 14 | `community_project` | Community Project | 5 |
| 15 | `education` | Department of Education | 7 |
| 16 | `hud` | Housing and Urban Development | 7 |
| 17 | `nasa` | NASA | 7 |
| 18 | `dod` | Department of Defense | 7 |
| 19 | `fema` | FEMA | 7 |
| 20 | `dol` | Department of Labor | 8 |
| 21 | `doj` | Department of Justice | 8 |

Each template includes: `name`, `full_name`, `forms`, `cfda`, `system`, `required_sections` (with id, name, required, max_pages, max_chars, guidance, components), `required_documents`, `eligibility` (eligible_applicant_types, formula_grant flag), `compliance` (requirements list, indirect_cost_rules, submission_portal), and `ai_context`.

---

## Axiom Architecture

GrantPro uses an "axiom" pattern: user-entered data is stored as structured records that AI can read but never modify. Only the user can change axioms through the UI. This prevents AI hallucination from corrupting source-of-truth data.

### What Counts as an Axiom

| Axiom | Storage | AI Reads It? | AI Writes It? |
|-------|---------|-------------|---------------|
| Budget line items (personnel, travel, equipment, etc.) | `grant_budget` table (JSON arrays + scalar totals) | Yes -- injected into prompts | No -- user edits via budget builder form only |
| Project title | `grants.grant_name` | Yes -- referenced in all section prompts | No -- user sets at grant creation |
| Organization name, type, EIN, UEI | `organization_details` + `grant_readiness` | Yes -- injected for org-specific content | No -- user sets in onboarding/profile |
| Requested amount | `grant_budget.requested_amount` | Yes -- budget justification references it | No |
| Indirect cost rate and type | `grant_budget.indirect_rate` + `indirect_rate_type` | Yes | No |
| Applicant type | `grant_readiness.applicant_category` | Yes -- drives eligibility language | No |

### How It Works in AI Generation

When `/grant/<id>/generate/<section>` is called:

1. All previously written sections are loaded and appended to the prompt as context ("OTHER SECTIONS ALREADY WRITTEN")
2. Budget data from `grant_budget` is loaded and formatted as structured text in the prompt
3. Organization data from the Grant Readiness Profile is injected
4. Agency compliance rules from the template's `ai_context` field are injected
5. The AI generates content that references these axioms without altering them
6. The generated content is saved to the `drafts` table; the axiom tables remain untouched

This means if a user changes a budget figure in the budget builder, they can regenerate the budget justification section and it will reflect the new numbers -- but the AI never "decides" to change the budget on its own.

---

## Environment Variables

Store in `.env` at the project root (not committed). Copy `.env.example` to `.env` and fill in values.

### Required for Core Functionality

| Variable | Description | Example |
|----------|-------------|---------|
| `GP_DATABASE_URL` | Supabase Postgres pooler URL | `postgresql://postgres.xxx:...@aws-0-us-east-1.pooler.supabase.com:6543/postgres` |
| `GP_SUPABASE_URL` | Supabase project URL | `https://xxx.supabase.co` |
| `GP_SUPABASE_KEY` | Supabase service role key | `eyJhbGciOi...` |
| `GOOGLE_API_KEY` | Google AI (Gemini 2.5 Flash) API key | `AIzaSy...` |

### Required for Payments

| Variable | Description |
|----------|-------------|
| `STRIPE_API_KEY` | Stripe secret key (`sk_test_` or `sk_live_`) |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret (`whsec_...`) |
| `STRIPE_MONTHLY_PRICE_ID` | Stripe Price ID for monthly plan ($19.95/mo) |
| `STRIPE_ANNUAL_PRICE_ID` | Stripe Price ID for annual plan ($199/yr) |
| `STRIPE_ENTERPRISE_5_PRICE_ID` | Stripe Price ID for Enterprise 5 ($44.95/mo) |
| `STRIPE_ENTERPRISE_10_PRICE_ID` | Stripe Price ID for Enterprise 10 ($74.95/mo) |
| `STRIPE_ENTERPRISE_UNLIMITED_PRICE_ID` | Stripe Price ID for Enterprise Unlimited ($99.95/mo) |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask session secret key | Auto-generated, persisted to `.secret_key` |
| `HTTPS` | Set `true` for secure cookies in production | `false` |
| `APP_URL` | Base URL for Stripe redirects and emails | `http://localhost:5001` |
| `BASE_URL` | Base URL for email system links | `http://localhost:5001` |
| `RESEND_API_KEY` | Resend API key for transactional email | Console fallback |
| `FROM_EMAIL` | Sender email address | `Grant Writer Pro <noreply@grantwriterpro.local>` |
| `FROM_NAME` | Sender display name | `Grant Writer Pro` |
| `DOMAIN_NAME` | Production domain | `grantpro.org` |

### Notes on GP_ Prefix

The `GP_` (or `GP-`) prefix keeps GrantPro's database variables separate on shared Vercel accounts. `core/db_connection.py` checks both `GP_DATABASE_URL` and `GP-DATABASE_URL` via `_gp_env()`.

### How to Get API Keys

| Service | URL | Notes |
|---------|-----|-------|
| Google AI Studio | https://aistudio.google.com/app/apikey | Free tier available |
| Stripe | https://dashboard.stripe.com/apikeys | Requires Stripe account |
| Resend | https://resend.com | 3,000 free emails/month |
| Supabase | https://supabase.com | Free tier: 500MB database |

---

## Getting Started

### Prerequisites

- Python 3.10 or later
- pip (Python package manager)
- A Supabase project (free tier works)

### Step-by-Step Setup

```bash
# 1. Clone the repository
git clone <repo-url> ~/.hermes/grant-system
cd ~/.hermes/grant-system

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Set up environment variables
cp .env.example .env
# Edit .env and fill in at minimum:
#   GP_DATABASE_URL="postgresql://postgres.xxx:...@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
#   GP_SUPABASE_URL="https://xxx.supabase.co"
#   GP_SUPABASE_KEY="eyJhbGciOi..."
#   GOOGLE_API_KEY="your-gemini-api-key"

# For Stripe (required for payments, not for local testing):
#   STRIPE_API_KEY="sk_test_..."
#   STRIPE_MONTHLY_PRICE_ID="price_..."
#   STRIPE_ANNUAL_PRICE_ID="price_..."

# 4. Initialize the database schema
#    Run supabase_migration.sql in Supabase SQL Editor to create the 20 migration tables.
#    The remaining 3 tables (grant_documents, grant_readiness, grant_checklist) are
#    created automatically by grant_db.py on first run.

# 5. Start the server
cd portal
python3 app.py

# 6. Open in browser
# http://localhost:5001
```

### Database

The app connects to Supabase Postgres on startup using `GP_DATABASE_URL`. No local database initialization is required beyond running `supabase_migration.sql` once. Schema migrations for new columns run automatically via `migrate_*` functions in `app.py`. If the Postgres connection is unavailable, the app falls back to local SQLite as an emergency measure.

### Test Credentials

```
Admin:  rusty@test.com / admin123
Test:   hermes-test-final@example.com / testpass123 (org: Gulf Coast Community Development Corp)
```

### Creating an Admin User

Sign up through `/signup`, then update the role via Supabase SQL Editor:

```sql
UPDATE users SET role='admin' WHERE email='your@email.com';
```

---

## Deployment

### Vercel (Primary)

GrantPro deploys to Vercel as a serverless Python application. All requests route through `api/index.py` which wraps the Flask app.

**Configuration files:**
- `vercel.json` -- routes `/api/health` to `api/health.py`, everything else to `api/index.py`
- `api/index.py` -- sets `VERCEL=1` env, imports Flask app, disables debug
- `api/health.py` -- diagnostics endpoint: tests DB connection, module imports, user/grant counts

**Deployment steps:**

```bash
# 1. Install Vercel CLI
npm i -g vercel

# 2. Login and link project
vercel login
vercel link

# 3. Set environment variables
vercel env add GOOGLE_API_KEY
vercel env add STRIPE_API_KEY
vercel env add STRIPE_WEBHOOK_SECRET
vercel env add STRIPE_MONTHLY_PRICE_ID
vercel env add STRIPE_ANNUAL_PRICE_ID
vercel env add STRIPE_ENTERPRISE_5_PRICE_ID
vercel env add STRIPE_ENTERPRISE_10_PRICE_ID
vercel env add STRIPE_ENTERPRISE_UNLIMITED_PRICE_ID
vercel env add GP_DATABASE_URL
vercel env add GP_SUPABASE_URL
vercel env add GP_SUPABASE_KEY
vercel env add RESEND_API_KEY
vercel env add SECRET_KEY

# 4. Deploy
vercel deploy
```

### Supabase Setup

1. Create a Supabase project at https://supabase.com
2. Run `supabase_migration.sql` in the SQL Editor to create all 20 tables
3. Copy the connection pooler URL (Settings > Database > Connection string > URI, port 6543 transaction mode)
4. Set `GP_DATABASE_URL` with the pooler URL

Both local development and Vercel production connect to the same Supabase instance.

### Self-Hosted Production

1. **HTTPS**: Run behind nginx or Caddy. Set `HTTPS=true` for secure cookies.
2. **Domain**: Point `grantpro.org` to the server.
3. **Stripe**: Switch from `sk_test_` to `sk_live_` keys. Configure webhook at `https://yourdomain.com/webhook/stripe`.
4. **Email**: Set `RESEND_API_KEY` for transactional email.
5. **Secret Key**: Set a strong, persistent `SECRET_KEY` (do not rely on auto-generation).
6. **Firewall**: Allow only ports 80/443. Flask listens on 5001 internally.
7. **Backups**: Enable Supabase PITR (Point-in-Time Recovery) for production.

### Automated Jobs (Cron)

```bash
crontab -e

# Grants.gov daily sync
0 2 * * * /usr/bin/python3 ~/.hermes/grant-system/jobs/sync_grants_gov.py

# Award winner detection
0 6 * * * /usr/bin/python3 ~/.hermes/grant-system/jobs/check_awards.py

# Deadline reminders (weekdays)
0 8 * * 1-5 /usr/bin/python3 ~/.hermes/grant-system/core/deadline_reminder.py
```

### Production Checklist

- [ ] HTTPS via reverse proxy (nginx/Caddy)
- [ ] Strong `SECRET_KEY` set as environment variable
- [ ] `HTTPS=true` environment variable set
- [ ] Stripe live keys configured
- [ ] Stripe webhook endpoint configured and verified
- [ ] Resend API key set for email
- [ ] Cron jobs for sync, awards, and reminders
- [ ] Firewall rules (80/443 only)
- [ ] Supabase automatic backups enabled (PITR recommended)
- [ ] Log rotation for `tracking/app.log`

---

## Security

### Authentication and Sessions

- Passwords hashed with **PBKDF2** (100,000 iterations, SHA-256, random 32-byte salt)
- Sessions: `HttpOnly`, `SameSite=Strict`, configurable `Secure` flag
- 1-hour session timeout (`PERMANENT_SESSION_LIFETIME=3600`)
- Auto-generated secret key persisted to `.secret_key` file (excluded from git)

### CSRF Protection

- Token generated per session (`secrets.token_hex(32)`)
- Enforced on all POST routes via `@csrf_required` decorator
- Token accepted from form field (`csrf_token`) or headers (`X-CSRF-Token` / `X-CSRFToken`)
- Guest-aware variant (`@csrf_required_allow_guest`) for mixed endpoints

### Rate Limiting

- In-memory sliding window rate limiter
- Default: 10 requests per 60 seconds per IP per endpoint
- AI generation: 10 requests per 60 seconds
- Login: rate-limited to prevent brute force
- Returns HTTP 429 when exceeded

### Security Headers (all responses)

| Header | Value |
|--------|-------|
| `Server` | `GrantPro` (Werkzeug fingerprint stripped via WSGI middleware) |
| `X-Powered-By` | `GrantPro` |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `X-XSS-Protection` | `1; mode=block` |
| `Content-Security-Policy` | Strict: `default-src 'self'`; inline scripts/styles; Google Fonts; Gemini API |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |

### Authorization

- `@login_required` -- must be authenticated
- `@paid_required` -- must have active paid plan
- `@admin_required` -- must have `role='admin'`
- `user_owns_client()` / `user_owns_grant()` -- resource-level authorization (admin bypasses)
- `@before_request` injects current user into `g.user` for template access

---

## Troubleshooting

### "No API key found" error

AI generation returns template text instead of generated content. Verify `GOOGLE_API_KEY` is set:
```bash
echo $GOOGLE_API_KEY
```

### "Invalid email or password" on login

Password hash mismatch after database reset. Use `admin123` for `rusty@test.com`, or create a new account via `/signup`.

### Connection refused on port 5001

Flask app not running. Check and restart:
```bash
lsof -i :5001
cd ~/.hermes/grant-system/portal && python3 app.py
```

### Stripe payments not working

Stripe API keys not configured. Add `STRIPE_API_KEY`, `STRIPE_MONTHLY_PRICE_ID`, and `STRIPE_ANNUAL_PRICE_ID` to your environment.

### Debug mode

```bash
# Edit the last line of portal/app.py:
# Change debug=False to debug=True
app.run(debug=True, host='0.0.0.0', port=5001)
```

---

## Changelog

### 2026-03-21 (Waves 12-13: Regulatory Intelligence and Submission Readiness)

- Added agency regulatory compliance data for all 21 templates (`research/agency_compliance_batch1.json`, `research/agency_regulatory_requirements_batch2.json`)
- Enriched every agency template with eligible applicant types, compliance requirements (Davis-Bacon, Section 3, NEPA, Buy America, IRB, OMB Uniform Guidance), indirect cost rate rules, and submission portal information
- Added AI context guidance fields to templates for regulatory-aware content generation
- Added submission checklist page (`portal/templates/grant_checklist.html`) with standard forms, narrative sections, required documents, self-certifications, and consistency checks
- Added document upload tracking per agency template requirements
- Added MOU and letter of support draft generation via AI
- Added Print Draft functionality for in-progress applications
- Submit action now gated behind 100% checklist completion
- Added `grant_documents`, `grant_readiness`, and `grant_checklist` tables in `grant_db.py`

### 2026-03-21 (Steps 1-4: Grant Readiness Profile and Eligibility Screening)

- Expanded onboarding wizard to collect Grant Readiness Profile: applicant type, SAM.gov/UEI/Grants.gov registration status, capacity indicators (construction experience, grants admin, largest grant managed), and funding preferences
- Added real-time eligibility screening on grants list: ineligible grants shown grayed out with explanation
- Added formula/entitlement grant blocking with non-competitive program explanation
- Added warning badges for missing federal prerequisites (SAM.gov, UEI, Grants.gov)
- AI generation now receives full regulatory context (agency compliance rules, user profile, template guidance, indirect cost rate rules, submission portal info)
- Profile data injected into all AI prompts for organization-accurate content generation

### 2026-03-20 (Wave 11: Supabase Postgres Migration)

- Migrated primary database from SQLite to Supabase Postgres (20 tables in migration SQL)
- Added `supabase_migration.sql` defining the full schema
- Updated `core/db_connection.py` with psycopg2 driver and compatibility wrapper (`_HybridRow`, `_PgCursorWrapper`, `_PgConnectionWrapper`)
- Both local dev and Vercel production now connect to the same Supabase Postgres instance
- SQLite retained only as emergency fallback
- Archived all SQLite `.db` files to `archive/sqlite-deprecated/`
- Added `GP_DATABASE_URL`, `GP_SUPABASE_URL`, `GP_SUPABASE_KEY` environment variables
- Removed Turso (libSQL) dependency

### 2026-03-20 (Wave 10: Vercel Deployment and Database Abstraction)

- Added Vercel serverless deployment support (`vercel.json`, `api/index.py`, `api/health.py`)
- Added `core/db_connection.py` with database abstraction layer
- Added `.env.example` documenting all environment variables
- Deployment-ready configuration for `vercel deploy`

### 2026-03-20 (Wave 9: Grants.gov Sync, Awards, Enterprise Tiers, PDF Branding)

- Added three enterprise subscription tiers: Enterprise 5 ($44.95/mo), Enterprise 10 ($74.95/mo), Enterprise Unlimited ($99.95/mo)
- Added `grants_catalog` table with seed data from original 131 grants
- Added `jobs/sync_grants_gov.py` for daily Grants.gov API sync with auto-archiving of expired grants
- Added `jobs/check_awards.py` for award winner detection via USAspending.gov API
- Added congratulations email flow with token-based testimonial submission
- Added testimonial form, thank-you page, and admin approval workflow (`testimonial_form.html`, `testimonial_thankyou.html`, `admin_testimonials.html`)
- Added approved testimonials display on landing page
- Added `core/pdf_utils.py` with "Assembled by GrantPro.org" footer on all generated PDFs
- Dynamic grant count in templates sourced from live `grants_catalog` table

### 2026-03-20 (Waves 5-8: Submission, Tracking, Cloning, Polish)

- Added paper submission workflow with SF-424 PDF generation (ReportLab)
- Added mark-submitted page with confirmation number, portal, and notes tracking
- Added post-submission status updates (funded with amount, rejected with reason)
- Added grant application cloning with all sections
- Added ICS calendar export for grant deadlines
- Added configurable deadline reminder days (7, 3, 1)
- Added admin email management and test email sending
- Added admin lead export to CSV
- Added unsubscribe workflow for newsletter leads
- Added WSGI middleware for server header stripping
- Added Content-Security-Policy, Permissions-Policy, Referrer-Policy headers
- Added compact mode toggle in guided submission
- Added 7 new submission tracking columns to grants table via migration
- Added `reminder_days` column to user_profiles via migration
- Moved all test/utility scripts to `archive/`

### 2026-03-18 (Waves 3-4: AI Quality, Security Hardening)

- Fixed budget placeholder issue in AI generation (budget data now injected into prompts)
- Added retry logic with exponential backoff (3 retries) for API errors
- Comprehensive AI testing across all 21 templates -- all passing
- Added CSRF protection on all POST routes
- Added in-memory rate limiting with sliding window
- Added security headers (X-Frame-Options, CSP, X-Content-Type-Options, etc.)
- Added `@paid_required` and `@admin_required` decorators
- Added resource-level authorization (`user_owns_client`, `user_owns_grant`)
- Added structured logging to file (`tracking/app.log`) and console
- Session security: HttpOnly, SameSite=Strict, configurable Secure flag

### 2026-03-17 (Waves 1-2: Core UX, Templates)

- Expanded from 14 to 21 agency templates (added Education, HUD, NASA, DOD, FEMA, DOL, DOJ)
- Added guided submission workflow (side-by-side, copy buttons, progress tracking)
- Added section-by-section editing with template guidance and AI generation
- Added multi-step onboarding wizard (org details, focus areas, grant history)
- Added user dashboard with stats (active grants, submitted, funded)
- Added eligibility checker with question-based filtering
- Added grant research search with filtering
- Added client management (add, edit, intake form)
- Added legal pages (Terms, Privacy, Refund, FAQ)
- Dark theme redesign with Inter + Playfair Display fonts

### 2026-03-16 (Phase 2: Payments and Legal)

- Added Stripe subscription integration (checkout, webhooks, management)
- Created all legal pages (Terms of Service, Privacy Policy, Refund Policy, FAQ)
- Added USA-only disclaimer
- Fixed template editor saving to wrong field
- Purchased domains: grantpro.org, grantpro.co

### 2026-03-15 (Phase 1: Initial Build)

- Initial system build
- 131 federal grants in research database
- 14 agency templates
- Web portal with auth, wizard, guided submission
- SQLite database with users, clients, grants, drafts tables
- Email system (Resend API with console fallback)
- Budget builder with standard federal categories
- Deadline reminder system

---

## Support

- **Email**: Via contact form at `/contact`
- **Docs**: This README, in-app help at `/help`
- **Logs**: `tracking/app.log` (structured, timestamped)
