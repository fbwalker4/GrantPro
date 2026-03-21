# GrantPro - AI-Powered Grant Writing System

An end-to-end grant writing platform powered by Google Gemini AI. Built for consultants, nonprofits, agencies, and small businesses who write federal grants.

**Website**: https://grantpro.org
**Local Server**: http://localhost:5001
**Business**: Futurespec Consulting, LLC

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture Overview](#architecture-overview)
3. [Tech Stack](#tech-stack)
4. [Database Schema](#database-schema)
5. [Route Map](#route-map)
6. [Features](#features)
7. [Template System](#template-system)
8. [Subscription Model](#subscription-model)
9. [Grants.gov Integration](#grantsgov-integration)
10. [Automated Jobs](#automated-jobs)
11. [Award Detection & Testimonials](#award-detection--testimonials)
12. [PDF Branding](#pdf-branding)
13. [Environment Variables](#environment-variables)
14. [Getting Started](#getting-started)
15. [Production Deployment](#production-deployment)
16. [Vercel Deployment](#vercel-deployment)
17. [Security](#security)
18. [File Reference](#file-reference)
19. [Changelog](#changelog)

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

---

## Architecture Overview

```
~/.hermes/grant-system/
├── portal/                         # Flask web application
│   ├── app.py                      # Main Flask app (3,568 lines, all routes)
│   ├── requirements.txt            # Python dependencies
│   ├── static/
│   │   └── images/
│   │       └── gp_logo.png         # GrantPro logo
│   └── templates/                  # 46 Jinja2 HTML templates
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
│       ├── onboarding.html         # New user onboarding wizard
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
├── api/                            # Vercel serverless entry point
│   └── index.py                    # WSGI adapter for Vercel deployment
├── core/                           # Backend business logic
│   ├── user_models.py              # User auth, profiles, subscriptions
│   ├── grant_db.py                 # Grant/client/draft database operations
│   ├── email_system.py             # Transactional email (Resend API)
│   ├── stripe_payment.py           # Stripe subscription integration
│   ├── budget_builder.py           # Budget category builder
│   ├── deadline_reminder.py        # Deadline notification system
│   ├── pdf_utils.py                # PDF generation with "Assembled by GrantPro.org" branding
│   ├── db_connection.py            # Database connection factory (Supabase Postgres + SQLite emergency fallback)
│   └── cli.py                      # Command-line interface
├── jobs/                           # Automated background jobs
│   ├── sync_grants_gov.py          # Daily Grants.gov catalog sync
│   └── check_awards.py             # Award winner detection via USAspending.gov
├── research/                       # Grant research engine
│   ├── grant_researcher.py         # Grant search, filtering, matching
│   ├── iot_grants_db.json          # 131 federal grant opportunities
│   └── grants.db                   # Research SQLite database (legacy, read-only)
├── templates/                      # Agency template definitions
│   └── agency_templates.json       # 21 agency templates (1,121 lines)
├── tracking/                       # Legacy data storage (no longer primary)
│   └── clients.json                # Legacy client records
├── archive/sqlite-deprecated/      # Archived SQLite databases (pre-migration)
├── data/                           # Runtime data
│   └── deadline_reminders.json     # Reminder state
├── supabase_migration.sql          # Supabase Postgres schema (19 tables)
├── .env                            # Local env vars (not committed — loads GP_ vars)
├── archive/                        # Archived test/utility scripts
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
├── intake/                         # Intake form template
│   └── questionnaire.html
├── invoices/                       # Invoice template
│   └── template.html
├── marketing/                      # Marketing assets
│   └── landing-page.html
├── documents/                      # Uploaded documents (empty)
├── drafts/                         # Draft exports (empty)
├── output/                         # Generated file output (empty)
├── reviews/                        # Grant reviews (empty)
├── vercel.json                     # Vercel deployment configuration
├── .env.example                    # Environment variable template
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

| Layer | Technology | Version / Notes |
|-------|-----------|-----------------|
| **Language** | Python 3.x | 3.10+ recommended |
| **Web framework** | Flask | >= 2.3.0 |
| **Database** | Supabase Postgres | Via `psycopg2` driver; compatibility wrapper in `core/db_connection.py` |
| **AI engine** | Google Gemini | via `google-genai` >= 1.0.0 |
| **Payments** | Stripe | via `stripe` >= 5.0.0 |
| **PDF generation** | ReportLab | >= 4.0.0 (SF-424 forms, paper packages) |
| **DOCX generation** | python-docx | >= 0.8.0 |
| **HTTP client** | Requests | >= 2.28.0 |
| **Email** | Resend API | Optional; console fallback in dev |
| **Templating** | Jinja2 | Bundled with Flask |
| **Fonts** | Inter + Playfair Display | Google Fonts CDN |
| **CSS** | Custom dark theme | CSS custom properties, no framework |
| **JavaScript** | Vanilla JS only | No React/Vue/Angular |
| **Auth** | Custom PBKDF2 | 100,000 iterations, SHA-256 |

### What Was Rejected (and Why)

- **OpenRouter** -- unnecessary middleman for AI
- **Next.js/React** -- over-engineering for this use case
- **Auth0/Clerk** -- adds cost and third-party dependency

---

## Database Schema

All 19 tables live in a single Supabase Postgres database. The schema is defined in `supabase_migration.sql` and managed via the Supabase dashboard. Both local development and production (Vercel) connect to the same Supabase Postgres instance. `core/db_connection.py` provides a compatibility wrapper that exposes a cursor-based interface (similar to SQLite's `Row` factory) over `psycopg2`. SQLite is retained only as an emergency fallback if the Postgres connection is unavailable.

### users (23 columns)

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | TEXT | PK | Format: `user-YYYYMMDD-HHMMSS` |
| email | TEXT | UNIQUE NOT NULL | Login identifier |
| password_hash | TEXT | NOT NULL | PBKDF2 `salt$hash` |
| first_name | TEXT | | |
| last_name | TEXT | | |
| organization_name | TEXT | | |
| organization_type | TEXT | | |
| phone | TEXT | | |
| role | TEXT | `'user'` | `'user'` or `'admin'` |
| verified | INTEGER | | Email verification flag |
| verification_token | TEXT | | Email verification token |
| created_at | TEXT | | ISO 8601 |
| updated_at | TEXT | | ISO 8601 |
| last_login | TEXT | | ISO 8601 |
| plan | TEXT | `'free'` | `'free'`, `'monthly'`, `'annual'`, `'enterprise'` |
| grants_this_month | INTEGER | 0 | Usage counter |
| max_grants_per_month | INTEGER | 0 | Plan limit (0=free, 3=paid, 999=enterprise) |
| subscription_status | TEXT | `'inactive'` | `'active'`, `'inactive'`, `'canceled'` |
| stripe_customer_id | TEXT | | Stripe customer ID |
| stripe_subscription_id | TEXT | | Stripe subscription ID |
| subscription_start | TEXT | | ISO 8601 |
| subscription_end | TEXT | | ISO 8601 |
| onboarding_completed | INTEGER | 0 | 1 when onboarding wizard finished |

### user_profiles

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| user_id | TEXT | PK, FK | References users.id |
| bio | TEXT | | |
| interests | TEXT | | |
| eligible_entities | TEXT | | JSON array |
| funding_amount_min | INTEGER | | |
| funding_amount_max | INTEGER | | |
| preferred_categories | TEXT | | |
| notify_deadlines | INTEGER | 1 | |
| notify_new_grants | INTEGER | 1 | |
| reminder_days | TEXT | `'7,3,1'` | Comma-separated days before deadline |

### organization_details

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| user_id | TEXT | PK, FK | |
| ein | TEXT | | Employer Identification Number |
| duns | TEXT | | DUNS number |
| uei | TEXT | | Unique Entity Identifier |
| address_line1 | TEXT | | |
| address_line2 | TEXT | | |
| city | TEXT | | |
| state | TEXT | | |
| zip_code | TEXT | | |
| country | TEXT | `'USA'` | |
| phone | TEXT | | |
| website | TEXT | | |
| created_at | TEXT | | |
| updated_at | TEXT | | |

### organization_profile

| Column | Type | Notes |
|--------|------|-------|
| user_id | TEXT | PK, FK |
| annual_revenue | TEXT | |
| year_founded | INTEGER | |
| employees | TEXT | |
| organization_type | TEXT | |

### mission_focus

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | PK, autoincrement |
| user_id | TEXT | FK |
| focus_area | TEXT | UNIQUE per user |

### past_grant_experience

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | PK, autoincrement |
| user_id | TEXT | FK |
| grant_name | TEXT | |
| funding_organization | TEXT | |
| year_received | INTEGER | |
| amount_received | INTEGER | |
| status | TEXT | |

### clients

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | TEXT | PK | Format: `client-YYYYMMDD-HHMMSS` |
| user_id | TEXT | | FK to users (added via migration) |
| organization_name | TEXT | | |
| contact_name | TEXT | | |
| contact_email | TEXT | | |
| status | TEXT | `'new'` | |
| current_stage | TEXT | `'new'` | |
| created_at | TEXT | | |
| updated_at | TEXT | | |
| intake_data | TEXT | | JSON blob |
| notes | TEXT | | |

### grants

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | TEXT | PK | Format: `grant-YYYYMMDD-HHMMSS` |
| client_id | TEXT | FK | References clients.id |
| grant_name | TEXT | | |
| agency | TEXT | | e.g., `NSF`, `DOE` |
| amount | REAL | | Requested amount |
| deadline | TEXT | | |
| status | TEXT | `'research'` | `'draft'`, `'research'`, `'assigned'`, `'submitted'`, `'funded'`, `'rejected'` |
| assigned_at | TEXT | | |
| submitted_at | TEXT | | |
| result | TEXT | | |
| opportunity_number | TEXT | | Migration-added |
| cfda | TEXT | | CFDA number, migration-added |
| template | TEXT | | Agency template key, migration-added |
| submission_date | TEXT | | When submitted, migration-added |
| confirmation_number | TEXT | | Portal confirmation, migration-added |
| portal_used | TEXT | | e.g., Grants.gov, migration-added |
| submission_notes | TEXT | | Free-text notes, migration-added |
| amount_funded | REAL | | Actual funded amount, migration-added |
| rejection_reason | TEXT | | Migration-added |
| notification_date | TEXT | | When notified of outcome, migration-added |

### drafts

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | TEXT | PK | |
| client_id | TEXT | FK | |
| grant_id | TEXT | FK | References grants.id |
| section | TEXT | | Section ID (e.g., `project_summary`) |
| content | TEXT | | User/AI-generated content |
| version | INTEGER | 1 | |
| created_at | TEXT | | |
| updated_at | TEXT | | |
| status | TEXT | `'draft'` | |

### documents

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | TEXT | PK | |
| client_id | TEXT | FK | |
| doc_type | TEXT | | |
| file_path | TEXT | | |
| uploaded_at | TEXT | | |
| status | TEXT | `'pending'` | |

### invoices

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | TEXT | PK | |
| client_id | TEXT | FK | |
| invoice_type | TEXT | | |
| amount | REAL | | |
| status | TEXT | `'pending'` | |
| created_at | TEXT | | |
| paid_at | TEXT | | |
| grant_id | TEXT | | |

### saved_grants

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | PK, autoincrement |
| user_id | TEXT | FK, UNIQUE with grant_id |
| grant_id | TEXT | |
| notes | TEXT | |
| saved_at | TEXT | |

### user_applications

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | TEXT | PK | |
| user_id | TEXT | FK | |
| grant_id | TEXT | | |
| status | TEXT | `'draft'` | |
| progress | INTEGER | 0 | Percentage |
| started_at | TEXT | | |
| updated_at | TEXT | | |
| submitted_at | TEXT | | |
| notes | TEXT | | |

### password_resets

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| email | TEXT | NOT NULL | |
| token | TEXT | NOT NULL | |
| created_at | TEXT | | |
| expires_at | TEXT | | |
| used | INTEGER | 0 | |

### leads

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER | PK, autoincrement | |
| email | TEXT | UNIQUE NOT NULL | |
| created_at | TIMESTAMP | CURRENT_TIMESTAMP | |
| status | TEXT | `'active'` | `'active'` or `'unsubscribed'` |
| source | TEXT | `'landing_page'` | |

### guest_saves

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | PK, autoincrement |
| session_id | TEXT | |
| grant_id | TEXT | |
| saved_at | TEXT | |

---

## Route Map

All routes are defined in `portal/app.py`. Decorators are listed in order of application.

### Public Routes (no auth required)

| Route | Method | Function | Decorators | Description |
|-------|--------|----------|------------|-------------|
| `/` | GET | `index` | -- | Landing page (redirects to dashboard if logged in) |
| `/about` | GET | `about` | -- | About page |
| `/pricing` | GET | `pricing` | -- | Pricing tiers page |
| `/help`, `/faq` | GET | `help_page` | -- | FAQ / help page |
| `/terms` | GET | `terms` | -- | Terms of Service |
| `/privacy` | GET | `privacy` | -- | Privacy Policy |
| `/refund` | GET | `refund` | -- | Refund Policy |
| `/contact` | GET, POST | `contact` | csrf_required | Contact form |
| `/unsubscribe` | GET, POST | -- | csrf_required (POST) | Email unsubscribe |
| `/static/images/<path>` | GET | `serve_image` | -- | Static image serving |

### Auth Routes

| Route | Method | Function | Decorators | Description |
|-------|--------|----------|------------|-------------|
| `/login` | GET, POST | `login` | csrf_required | User login |
| `/signup` | GET, POST | `signup` | csrf_required | User registration |
| `/logout` | GET | `logout` | -- | Logout (clears session) |
| `/forgot-password` | GET, POST | `forgot_password` | csrf_required | Request password reset |
| `/reset-password/<token>` | GET, POST | `reset_password` | csrf_required | Reset password with token |

### User Routes (login_required)

| Route | Method | Function | Decorators | Description |
|-------|--------|----------|------------|-------------|
| `/dashboard` | GET | `dashboard` | login_required | User dashboard with stats |
| `/profile` | GET, POST | `profile` | login_required, csrf_required | Edit profile and preferences |
| `/onboarding` | GET, POST | `onboarding` | login_required, csrf_required | New user onboarding wizard |
| `/settings` | GET | `settings` | login_required | User settings page |

### Subscription & Payment Routes

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
| `/grants` | GET | `grants_list` | login_required | Saved grants list |
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

### Submission & Tracking Routes

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
| `/api/copy-section` | POST | `copy_section` | login_required, csrf_required | Copy section content |

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

### Admin Routes (login_required + admin_required)

| Route | Method | Function | Decorators | Description |
|-------|--------|----------|------------|-------------|
| `/admin` | GET | `admin_index` | -- (checks role inline) | Admin dashboard |
| `/admin/dashboard` | GET | `admin_dashboard` | -- | Admin dashboard redirect |
| `/admin/grants` | GET | `admin_grants` | login_required, admin_required | Manage all grants |
| `/admin/grants/<action>` | GET, POST | `admin_grants` | login_required, admin_required | Grant CRUD actions |
| `/admin/templates` | GET, POST | `admin_templates` | login_required, admin_required | Template CMS |
| `/admin/leads` | GET | `admin_leads` | login_required, admin_required | View leads/subscribers |
| `/admin/leads/delete/<id>` | GET | `admin_leads_delete` | login_required, admin_required | Delete a lead |
| `/admin/emails` | GET | `admin_emails` | login_required, admin_required | Email management |
| `/admin/emails/send-test` | POST | `admin_send_test` | login_required, admin_required | Send test email |
| `/admin/export-leads` | GET | `admin_export_leads` | login_required, admin_required | Export leads as CSV |

---

## Features

### User Authentication & Accounts

- Email/password signup and login
- PBKDF2 password hashing (100,000 iterations, SHA-256)
- Password reset via token (email or console)
- Session management with secure cookies (HttpOnly, SameSite=Strict)
- Role-based access: `user` and `admin`
- Multi-step onboarding wizard for new users (org details, focus areas, grant history)

### Subscription Management

- Six tiers: Free, Monthly ($19.95), Annual ($199.95), Enterprise 5/10/Unlimited
- Stripe Checkout integration for payment
- Subscription lifecycle: create, manage, cancel
- Stripe webhook handler for status updates
- Plan-based feature gating via `@paid_required` decorator
- Usage tracking (grants per month)

### Grant Discovery

- **Grant Wizard**: Multi-step questionnaire that matches users to grants by eligibility, focus area, and funding range
- **Search**: Full-text search across 131 federal grant opportunities
- **Eligibility Checker**: Question-based filtering by organization type, size, and focus
- **Save/Favorite**: Save grants for later (works for guests and logged-in users)
- **Recommendations**: AI-matched grant suggestions based on wizard answers

### Grant Writing

- **AI Content Generation**: Google Gemini generates section content using organization intake data (mission, budget, programs, service area)
- **Section-by-Section Editing**: Edit each section individually with agency-specific guidance
- **Template-Ordered Sections**: Sections presented in the exact order required by the funding agency
- **Budget Builder**: Standard federal budget categories (personnel, fringe, equipment, supplies, travel, consultants, other)
- **Retry Logic**: Exponential backoff (3 retries) for transient API/SSL errors
- **Rate Limiting**: 10 AI generation requests per minute per IP

### Guided Submission

- Side-by-side workflow: grant content on the left, submission instructions on the right
- Copy-to-clipboard buttons for each section
- Compact mode toggle for focused viewing
- Progress tracking per section
- Download as DOCX, PDF, or TXT

### Paper Submission

- SF-424 form generation with organization data pre-filled
- Full paper submission package as PDF (ReportLab)
- Individual form downloads (SF-424, SF-424A, etc.)
- Print-optimized layout

### Post-Submission Tracking

- **Mark Submitted**: Record submission date, confirmation number, portal used, notes
- **Status Updates**: Track outcomes -- funded (with amount) or rejected (with reason)
- **Notification Date**: Record when outcome notification was received
- **Dashboard Stats**: Active grants, submitted count, total funded amount

### Application Cloning

- Clone any grant application with all sections and content
- Creates a new grant with " (Copy)" suffix
- Useful for applying to similar grants or resubmitting

### Deadline Management

- Countdown timers on grant detail pages
- Configurable reminder days (default: 7, 3, 1 days before deadline)
- ICS calendar export for any grant deadline
- File-based reminder system (cron-compatible)

### Admin Panel

- **Templates**: Full CMS for agency templates (add, edit, delete sections)
- **Grants**: View and manage all user grants
- **Users**: View all registered users
- **Leads**: View, delete, and export newsletter subscribers as CSV
- **Emails**: Send test emails, view email configuration

### Accessibility

- ARIA labels on interactive elements
- Skip navigation link
- Mobile hamburger menu
- Semantic HTML throughout
- High-contrast dark theme with accessible color ratios

---

## Template System

### 21 Agency Templates

Templates are defined in `templates/agency_templates.json` and provide structured guidance for each federal agency's grant requirements.

| # | Template Key | Agency | Sections | Notes |
|---|-------------|--------|----------|-------|
| 1 | `nsf` | National Science Foundation | 10 | 15-page project description |
| 2 | `doe` | Department of Energy | 7 | |
| 3 | `nih` | National Institutes of Health | 8 | |
| 4 | `usda` | Department of Agriculture | 6 | |
| 5 | `epa` | Environmental Protection Agency | 4 | |
| 6 | `dot` | Department of Transportation | 4 | |
| 7 | `nist` | National Institute of Standards and Technology | 3 | |
| 8 | `nea` | National Endowment for the Arts | 5 | |
| 9 | `nea_challenge` | NEA Challenge America | 4 | |
| 10 | `generic` | Generic Federal Grant | 8 | Default fallback |
| 11 | `artist_individual` | Artist Individual | 5 | For individual artists, not orgs |
| 12 | `micro_grant` | Micro-Grant | 4 | Under $5K |
| 13 | `small_business` | Small Business Grant | 5 | SBIR/STTR |
| 14 | `community_project` | Community Project | 5 | |
| 15 | `education` | Department of Education | 7 | |
| 16 | `hud` | Housing and Urban Development | 7 | |
| 17 | `nasa` | NASA | 7 | |
| 18 | `dod` | Department of Defense | 7 | |
| 19 | `fema` | FEMA | 7 | |
| 20 | `dol` | Department of Labor | 8 | |
| 21 | `doj` | Department of Justice | 8 | |

### Template Structure

Each template includes:

```json
{
  "name": "National Science Foundation (NSF)",
  "full_name": "National Science Foundation",
  "forms": ["SF424", "NSF Cover Sheet", "..."],
  "cfda": "47.076",
  "system": "Research.gov / FastLane",
  "required_sections": [
    {
      "id": "project_summary",
      "name": "Project Summary",
      "required": true,
      "max_pages": 1,
      "max_chars": 3000,
      "guidance": "Must contain: (1) a statement of...",
      "components": ["overview", "intellectual_merit", "broader_impacts"]
    }
  ]
}
```

### How Templates Map to Grants

1. User selects a grant from the 131-grant research database
2. System matches the grant's `agency` field to a template key (e.g., `NSF` -> `nsf`)
3. The template's `required_sections` define the grant application structure
4. Each section displays guidance text, page/character limits, required badge, and AI generate button
5. If no agency match is found, the `generic` template is used as a fallback

---

## Subscription Model

| Tier | Price | Grants/Month | Organizations | Key Features |
|------|-------|--------------|---------------|--------------|
| **Free** | $0 | 0 | -- | Search grants, save favorites, eligibility checker, wizard |
| **Monthly** | $19.95/mo | 3 | 1 | AI writing, guided submission, paper submission, downloads, cloning, templates |
| **Annual** | $199.95/yr | 3/mo | 1 | Same as Monthly, save $39.45/year |
| **Enterprise 5** | $44.95/mo | Unlimited | Up to 5 client agencies | Everything in Monthly + multi-client management |
| **Enterprise 10** | $74.95/mo | Unlimited | Up to 10 clients | Everything in Enterprise 5 + white-label reports |
| **Enterprise Unlimited** | $99.95/mo | Unlimited | Unlimited | Everything, no caps |

### Anti-Reseller Policy

- **Free/Monthly/Annual**: Only for grants submitted in the account holder's organization name
- **Enterprise tiers**: Required if writing grants for clients (resale permitted)
- **Rationale**: Prevents users from purchasing a base plan and reselling access to multiple organizations

### Feature Gating

The `@paid_required` decorator gates these features behind a paid plan:
- Starting a grant application (`/start-grant`)
- AI content generation (`/grant/<id>/generate/<section>`)
- Guided submission workflow
- Paper submission and PDF packages
- Grant downloads (DOCX/PDF/TXT)
- Mark submitted / update status
- Clone grant applications

---

## Grants.gov Integration

GrantPro maintains a `grants_catalog` Postgres table in Supabase that serves as the canonical source of grant opportunities.

### Data Pipeline

1. **Seed data**: The original 131 grants from `research/iot_grants_db.json` were loaded into the `grants_catalog` table as the initial dataset.
2. **Daily sync**: `jobs/sync_grants_gov.py` pulls new and updated opportunities from the Grants.gov API every 24 hours.
3. **Auto-archiving**: Grants past their close date are automatically marked as `archived` during each sync run, keeping the catalog current.
4. **Dynamic counts**: Templates reference the live grant count from `grants_catalog` rather than a hardcoded number, so the landing page and search always reflect the real catalog size.

### grants_catalog Table

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | PK, autoincrement |
| opportunity_id | TEXT | Grants.gov opportunity ID, UNIQUE |
| title | TEXT | Grant title |
| agency | TEXT | Funding agency |
| cfda | TEXT | CFDA/Assistance Listing number |
| close_date | TEXT | Application deadline |
| amount | REAL | Estimated funding |
| status | TEXT | `active`, `archived` |
| synced_at | TEXT | Last sync timestamp |

---

## Automated Jobs

Background jobs live in the `jobs/` directory and are designed to run via cron.

| Job | File | Schedule | Description |
|-----|------|----------|-------------|
| Grants.gov sync | `jobs/sync_grants_gov.py` | Daily at 2:00 AM | Pulls new opportunities from Grants.gov API, updates existing records, archives expired grants |
| Award detection | `jobs/check_awards.py` | Daily at 6:00 AM | Cross-references USAspending.gov awards against GrantPro users to detect wins |
| Deadline reminders | `core/deadline_reminder.py` | Weekdays at 8:00 AM | Sends reminder emails for upcoming grant deadlines |

### Cron Setup

```bash
crontab -e

# Grants.gov daily sync
0 2 * * * /usr/bin/python3 ~/.hermes/grant-system/jobs/sync_grants_gov.py

# Award winner detection
0 6 * * * /usr/bin/python3 ~/.hermes/grant-system/jobs/check_awards.py

# Deadline reminders (weekdays)
0 8 * * 1-5 /usr/bin/python3 ~/.hermes/grant-system/core/deadline_reminder.py
```

---

## Award Detection & Testimonials

### How It Works

1. **Detection**: `jobs/check_awards.py` queries the USAspending.gov API daily and cross-references awarded grants against GrantPro users by organization name and grant opportunity number.
2. **Congratulations email**: When a match is found, the system sends an automated congratulations email to the user with a unique token-based link to submit a testimonial.
3. **Testimonial form**: The user clicks the link, which loads `testimonial_form.html` -- a simple form where they can share their experience. The token ensures only verified award winners can submit.
4. **Admin approval**: Submitted testimonials appear in `admin_testimonials.html` where admins can review, approve, or reject them.
5. **Landing page display**: Approved testimonials are displayed on the public landing page to build social proof.

### Token Flow

```
check_awards.py detects win
  → generates secure token (secrets.token_urlsafe)
  → stores token + user_id + grant_id in testimonial_tokens table
  → sends congratulations email with /testimonial/<token> link
  → user submits form → testimonial saved as "pending"
  → admin approves → testimonial displayed on landing page
```

---

## PDF Branding

Every PDF generated by GrantPro (paper submission packages, SF-424 forms, grant downloads) includes an **"Assembled by GrantPro.org"** footer on every page. This is handled by `core/pdf_utils.py` which provides a shared ReportLab canvas callback used across all PDF generation points.

---

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `GP_DATABASE_URL` | Supabase Postgres pooler connection string | `postgresql://postgres.xxx:...@aws-0-us-east-1.pooler.supabase.com:6543/postgres` |
| `GP_SUPABASE_URL` | Supabase project URL | `https://xxx.supabase.co` |
| `GP_SUPABASE_KEY` | Supabase service role key | `eyJhbGciOi...` |
| `GOOGLE_API_KEY` | Google AI (Gemini) API key | `AIzaSy...` |
| `STRIPE_API_KEY` | Stripe secret key | `sk_live_...` |
| `STRIPE_MONTHLY_PRICE_ID` | Stripe price ID for monthly plan | `price_...` |
| `STRIPE_ANNUAL_PRICE_ID` | Stripe price ID for annual plan | `price_...` |
| `STRIPE_ENTERPRISE_5_PRICE_ID` | Stripe price ID for Enterprise 5 plan | `price_...` |
| `STRIPE_ENTERPRISE_10_PRICE_ID` | Stripe price ID for Enterprise 10 plan | `price_...` |
| `STRIPE_ENTERPRISE_UNLIMITED_PRICE_ID` | Stripe price ID for Enterprise Unlimited plan | `price_...` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask session secret key | Auto-generated and persisted to `.secret_key` |
| `RESEND_API_KEY` | Resend API key for transactional email | Console fallback |
| `FROM_EMAIL` | Sender email address | `Grant Writer Pro <noreply@grantwriterpro.local>` |
| `FROM_NAME` | Sender display name | `Grant Writer Pro` |
| `BASE_URL` | Base URL for email links | `http://localhost:5001` |
| `DOMAIN_NAME` | Production domain | `grantpro.org` |
| `HTTPS` | Set to `true` to enable secure cookies | `false` |

### Where to Set

Store environment variables in `.env` at the project root (not committed). Copy `.env.example` to `.env` and fill in the values.

### How to Get API Keys

| Service | URL | Notes |
|---------|-----|-------|
| Google AI Studio | https://aistudio.google.com/app/apikey | Free tier available |
| Stripe | https://dashboard.stripe.com/apikeys | Requires Stripe account |
| Resend | https://resend.com | 3,000 free emails/month |

---

## Getting Started

### Prerequisites

- Python 3.10 or later
- pip (Python package manager)

### Step-by-Step Setup

```bash
# 1. Clone the repository
git clone <repo-url> ~/.hermes/grant-system
cd ~/.hermes/grant-system

# 2. Install Python dependencies
pip install -r portal/requirements.txt
pip install psycopg2-binary

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

# 4. Start the server (connects to Supabase Postgres on startup — no local DB setup needed)
cd portal
python3 app.py

# 5. Open in browser
# http://localhost:5001
```

### Database

The app connects to Supabase Postgres on startup using the `GP_DATABASE_URL` connection string. No local database initialization is required. The schema is defined in `supabase_migration.sql` (19 tables) and managed via the Supabase dashboard. Schema migrations for new columns run automatically via `migrate_*` functions in `app.py`. If the Postgres connection is unavailable, the app falls back to local SQLite as an emergency measure.

### Test Credentials

```
Admin:  rusty@test.com / admin123
Test:   hermes-test-final@example.com / testpass123 (org: Gulf Coast Community Development Corp)
```

### Creating an Admin User

Sign up through `/signup`, then manually update the role in the database via the Supabase SQL Editor or `psql`:

```sql
UPDATE users SET role='admin' WHERE email='your@email.com';
```

---

## Production Deployment

### Requirements

1. **HTTPS**: Run behind nginx or Caddy as a reverse proxy. Set `HTTPS=true` in environment to enable secure cookies.

2. **Domain**: Point `grantpro.org` (or your domain) to the server.

3. **Stripe**: Switch from test keys (`sk_test_`) to live keys (`sk_live_`). Configure webhook endpoint at `https://yourdomain.com/webhook/stripe`.

4. **Email**: Set `RESEND_API_KEY` for transactional email (password resets, notifications). Without it, emails print to console only.

5. **Cron Jobs**: Set up deadline reminder cron:
   ```bash
   crontab -e
   # Add:
   0 8 * * 1-5 /usr/bin/python3 /path/to/grant-system/core/deadline_reminder.py
   ```

6. **Secret Key**: Set a strong, persistent `SECRET_KEY` environment variable (do not rely on auto-generation in production).

7. **Firewall**: Allow only ports 80 and 443. The Flask app listens on port 5001 internally.

8. **Backups**: Supabase provides automatic daily backups. Enable Point-in-Time Recovery (PITR) for production.

### Production Checklist

- [ ] HTTPS via reverse proxy (nginx/Caddy)
- [ ] Strong `SECRET_KEY` set as environment variable
- [ ] `HTTPS=true` environment variable set
- [ ] Stripe live keys configured
- [ ] Stripe webhook endpoint configured and verified
- [ ] Resend API key set for email
- [ ] Cron job for deadline reminders
- [ ] Firewall rules (80/443 only)
- [ ] Supabase automatic backups enabled (PITR recommended)
- [ ] Log rotation for `tracking/app.log`

---

## Vercel Deployment

GrantPro can be deployed to Vercel as a serverless Python application.

### Configuration Files

- **`vercel.json`**: Routes all requests to the `api/index.py` serverless function. Configures Python runtime and build settings.
- **`api/index.py`**: WSGI adapter that wraps the Flask app for Vercel's serverless environment.
- **`core/db_connection.py`**: Database connection factory that connects to Supabase Postgres via `GP_DATABASE_URL`. Provides a compatibility wrapper (cursor-based, dict-style rows) so existing SQLite-style code works unchanged. Falls back to local SQLite only as an emergency measure.
- **`.env.example`**: Template listing all required and optional environment variables.

### Deployment Steps

```bash
# 1. Install Vercel CLI
npm i -g vercel

# 2. Login and link project
vercel login
vercel link

# 3. Set environment variables
vercel env add GOOGLE_API_KEY
vercel env add STRIPE_API_KEY
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

### Supabase Postgres

Both local development and Vercel production connect to the same Supabase Postgres database. The pooler host is `aws-0-us-east-1.pooler.supabase.com` (port 6543, transaction mode). Set `GP_DATABASE_URL` in Vercel environment variables with the full connection string. No separate database setup is needed for Vercel -- it shares the same Supabase instance as local dev.

---

## Security

### Authentication & Sessions

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

### Server Fingerprint Stripping

A custom WSGI middleware (`_ServerHeaderStripper`) overrides the `Server` header after Werkzeug sets it, preventing server version disclosure.

### Data Privacy

- All data stored in Supabase Postgres (hosted, encrypted at rest)
- No third-party analytics or tracking
- User owns all their data

### Authorization

- `@login_required` -- must be authenticated
- `@paid_required` -- must have active paid plan
- `@admin_required` -- must have `role='admin'`
- `user_owns_client()` / `user_owns_grant()` -- resource-level authorization (admin bypasses)
- `@before_request` injects current user into `g.user` for template access

---

## File Reference

| File | Purpose |
|------|---------|
| `portal/app.py` | Main Flask application -- all routes, middleware, migrations (3,568 lines) |
| `portal/requirements.txt` | Python package dependencies |
| `core/user_models.py` | User CRUD, auth (PBKDF2), profiles, saved grants, onboarding |
| `core/grant_db.py` | Grant/client/draft/document/invoice database schema and CRUD |
| `core/stripe_payment.py` | Stripe subscription creation, cancellation, webhooks |
| `core/email_system.py` | Transactional email via Resend API (console fallback) |
| `core/budget_builder.py` | Federal budget category definitions and builder |
| `core/deadline_reminder.py` | File-based deadline reminder system |
| `core/pdf_utils.py` | PDF branding utilities ("Assembled by GrantPro.org" footer) |
| `core/db_connection.py` | Database connection factory (Supabase Postgres + SQLite emergency fallback) |
| `core/cli.py` | Command-line interface for grant operations |
| `jobs/sync_grants_gov.py` | Daily Grants.gov catalog sync job |
| `jobs/check_awards.py` | Award winner detection via USAspending.gov |
| `api/index.py` | Vercel serverless WSGI entry point |
| `research/grant_researcher.py` | Grant search engine -- search, filter, match from JSON database |
| `research/iot_grants_db.json` | 131 federal grant opportunity records |
| `templates/agency_templates.json` | 21 agency template definitions (sections, guidance, limits) |
| `portal/templates/layout.html` | Base HTML template (dark theme, Inter/Playfair fonts, nav, CSS) |
| `vercel.json` | Vercel deployment configuration |
| `.env.example` | Environment variable template for new deployments |
| `portal/templates/testimonial_form.html` | Token-based testimonial submission form |
| `portal/templates/testimonial_thankyou.html` | Testimonial submission confirmation page |
| `portal/templates/admin_testimonials.html` | Admin testimonial approval workflow |
| `AI_PROMPTS.md` | Prompt templates for AI section generation |
| `INTAKE_QUESTIONS.md` | 37 client intake questions |
| `DOCUMENT_CHECKLIST.md` | Required documents by grant type |
| `AGREEMENT.md` | Client service agreement template |
| `TRACKING.md` | Pipeline stage definitions |
| `docs/competitive-analysis.md` | Market research and competitor pricing |
| `docs/comprehensive-testing-report.md` | Full testing results across all templates |
| `docs/user-testing-report.md` | User testing feedback |
| `.gitignore` | Excludes .env, .db, __pycache__, IDE files |

---

## Changelog

### 2026-03-20 (Wave 11: Supabase Postgres Migration)

- Migrated primary database from SQLite to Supabase Postgres (19 tables)
- Added `supabase_migration.sql` defining the full schema
- Updated `core/db_connection.py` with psycopg2 driver and compatibility wrapper (cursor-based, dict-style rows)
- Both local dev and Vercel production now connect to the same Supabase Postgres instance
- SQLite retained only as emergency fallback
- Archived all SQLite `.db` files to `archive/sqlite-deprecated/`
- Added `GP_DATABASE_URL`, `GP_SUPABASE_URL`, `GP_SUPABASE_KEY` environment variables
- Removed Turso (libSQL) dependency

### 2026-03-20 (Wave 10: Vercel Deployment & Database Abstraction)

- Added Vercel serverless deployment support (`vercel.json`, `api/index.py`)
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

### 2026-03-16 (Phase 2: Payments & Legal)

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

## Support

- **Email**: Via contact form at `/contact`
- **Docs**: This README, in-app help at `/help`
- **Logs**: `tracking/app.log` (structured, timestamped)
