# Bambinos.live | AI Program Manager (Operations) Take-Home

## What this submission contains
- `data/`: five masked assessment CSV datasets from the official `ops/data/` asset paths.
- `src/reconcile.py`: deterministic reconciliation engine; outputs ready-for-approval rows, reason-coded exceptions, message drafts, and booking backlog.
- `results/`: generated outputs from the included data.
- `workflows_or_scripts/n8n_renewal_reconciliation.json`: importable n8n webhook → reconciliation Code node → JSON response workflow.
- `prompts/`: safe exception-message drafting prompt.
- `docs/case_report.pdf`: executive case report and operating plan.

## Run locally
```bash
python -m pip install pandas
python src/reconcile.py --data data
```
The script writes CSV/JSON outputs to `results/`.

## Run the n8n prototype
1. In n8n, choose **Workflows → Import from File** and import `workflows_or_scripts/n8n_renewal_reconciliation.json`.
2. Activate only in a test workspace. Send a POST to the generated webhook URL with JSON arrays named `invoices`, `faculty_forms`, `booking_requests`, `schedule_bookings`, and `reference_students`.
3. The response contains `auto_approved_ready`, `exceptions`, `message_drafts`, and `booking_backlog`.
4. The prototype deliberately does not write to a production database, create actual class schedules, or send WhatsApp messages. Add authenticated DB/gateway nodes, idempotency, human approval gates, and provider credentials before production use.

## Decision policy
Auto-approval is only a **ready-to-create booking request** decision: full gateway status `Paid`, matching invoice/form/student IDs, matching course/teacher, matching invoice net amount, same current batch, matching days/time, and available capacity. Existing booking requests are not duplicated. Batch changes, payment uncertainty, contact mismatch, capacity conflicts, and identity mismatches are routed to owners.

## Dataset caveat
The source tables contain masked production-style records. Masked mobile/email values cannot support fuzzy identity resolution; the prototype requires human verification for contact mismatches. The dataset is a small assessment snapshot, not a statistically representative operating baseline. The 24 purchased sessions are not expanded into actual class dates by this prototype because class-schedule availability/IDs are not provided for all future sessions.

## AI use
AI is used only for drafting human-readable exception communications. Reconciliation and approval eligibility are deterministic rules, not an LLM decision. This avoids probabilistic decisions about money, identity, or child scheduling.
