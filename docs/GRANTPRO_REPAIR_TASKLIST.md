# GrantPro Repair Task List (Execution Plan)

Last updated: 2026-04-11
Owner: Hermes
Status: In Progress (local-only; no push/commit yet)

## Rules for this run
- Keep everything local until explicitly ready to push.
- Every task must include: implementation notes, test evidence, and result.
- After each completed task, update:
  1) `docs/GRANTPRO_REMAINING_WORK_CARD.md`
  2) `docs/GRANTPRO_WORKLOG.md`
- Retest completed areas before final closeout.

---

## Priority 0 — Tracking & Control
- [ ] Create and maintain Remaining Work Card
- [ ] Maintain step-by-step worklog
- [ ] Maintain running status summary (Done / Doing / Next)

---

## Priority 1 — Route and Navigation Integrity (Stop breakage)

### 1.1 Route inventory and link audit
- [ ] Build route map from `portal/app.py`
- [ ] Build link map from templates under `portal/templates/`
- [ ] Identify dead links and orphan routes
- [ ] Record findings in worklog

### 1.2 Fix dead/mismatched routes
- [ ] Resolve `/list-templates` mismatch (implement, redirect, or remove links)
- [ ] Resolve `/subscription/success` mismatch (implement or route to canonical success page)
- [ ] Resolve `/subscription/cancel` method mismatch (proper GET/POST behavior)
- [ ] Re-test affected pages and links

### 1.3 Research flow decision
- [ ] Confirm intended behavior for `/research` (real page vs redirect)
- [ ] Align code + templates + docs to the chosen behavior
- [ ] Re-test anonymous and authenticated flows

Definition of Done:
- No known dead links in primary nav/user flows
- All intended routes return expected status and behavior

---

## Priority 2 — CSRF and API Reliability

### 2.1 CSRF token handling consistency
- [ ] Audit frontend token source patterns in templates/scripts
- [ ] Standardize token retrieval and header usage for API POSTs
- [ ] Ensure pages that initiate API POSTs expose valid token source

### 2.2 API contract validation
- [ ] Validate `/api/save-grant`
- [ ] Validate `/api/unsave-grant`
- [ ] Validate `/api/check-eligibility`
- [ ] Validate template request and other mutating endpoints
- [ ] Record expected status codes/errors for missing token vs invalid payload

Definition of Done:
- No false 405/redirect confusion due to token handling
- Predictable CSRF failure behavior and success path

---

## Priority 3 — Performance Repair (grants/search heavy pages)

### 3.1 Baseline measurements
- [ ] Measure response size/time for `/grants`, `/search`, `/awards` (local + prod as reference)
- [ ] Save baseline to worklog

### 3.2 Grants page optimization
- [ ] Introduce pagination or server-side slicing
- [ ] Reduce rendered card payload/duplicate fields
- [ ] Keep filters functional and accurate

### 3.3 Follow-up tuning
- [ ] Verify page load improvement
- [ ] Ensure no regressions in sorting/filtering/saved state

Definition of Done:
- `/grants` response payload substantially reduced
- Route remains functionally correct

---

## Priority 4 — Testing and Regression Safety

### 4.1 Smoke test suite
- [ ] Create/update local smoke test script for critical routes
- [ ] Include auth, redirect, and API checks
- [ ] Add instructions to run repeatedly

### 4.2 Regression run
- [ ] Run smoke tests after each major change set
- [ ] Final full rerun at closeout
- [ ] Store results under `docs/test-reports/`

Definition of Done:
- Repeatable smoke test exists and passes for critical flows

---

## Priority 5 — Documentation & Handoff Quality

### 5.1 Update stale docs
- [ ] Reconcile old testing/security docs with current reality
- [ ] Mark stale reports as historical if no longer accurate

### 5.2 Final local release packet
- [ ] Write final status report (what changed, what passed, known risks)
- [ ] Include exact files modified
- [ ] Include final retest evidence

Definition of Done:
- Another dev can pick up from local files alone with no guesswork

---

## Exit Criteria (must all be true)
- [ ] Remaining Work Card shows no unresolved Priority 1 blockers
- [ ] CSRF/API mutating flows tested and documented
- [ ] `/grants` performance materially improved and verified
- [ ] Smoke tests pass
- [ ] Docs updated and local artifacts complete
- [ ] Final retest performed and logged
