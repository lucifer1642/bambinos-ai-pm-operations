# n8n setup

Import `workflows_or_scripts/n8n_renewal_reconciliation.json`.

## Webhook contract
POST JSON body:
```json
{
  "invoices": [],
  "faculty_forms": [],
  "booking_requests": [],
  "schedule_bookings": [],
  "reference_students": []
}
```
Use the five assessment CSVs converted to JSON arrays for a test execution. The response includes `summary`, `auto_approved_ready`, `exceptions`, `message_drafts`, and `booking_backlog`.

## Production hardening before activating writes
- Authenticate webhook (HMAC/API key), restrict IPs, validate schema and payload size.
- Replace request-supplied arrays with parameterized DB reads and gateway API verification.
- Use DB transaction + unique key `(invoice_id, renewal_term)`; re-read batch capacity immediately before booking.
- Add retries with exponential backoff, dead-letter queue, audit table, metrics, alerting and manual replay.
- Connect WhatsApp Business API only after human approval; use approved templates and opt-out controls.
- Keep schedule generation as a separate node/service; never infer missing classschedule IDs or fabricate session dates.
