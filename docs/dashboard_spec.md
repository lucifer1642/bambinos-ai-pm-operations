# Ops Head dashboard specification

**Refresh:** event-driven (near real time), plus 09:00 reconciliation sweep. **Timezone:** show region-local time and UTC timestamp.

## KPI strip
Paid renewals | eligible straight-through | paid invoices >12h without form | unapproved forms | unscheduled booking requests | p95 payment-to-first-class | exception SLA breaches | handling minutes saved.

## Main views
1. **Renewal funnel:** Paid → intent/form → reconciled → booking request → batch allocated → schedule created → first class attended.
2. **Exception work queue:** invoice/student masked IDs, reason code, owner, age, SLA deadline, next action, latest update. Sort by child’s next class start and age.
3. **Capacity heatmap:** course × batch with active/max seats, pending renewals, failed allocation, alternate batch options.
4. **Quality panel:** duplicate writes prevented, payment mismatches, manual overrides, false-positive/false-negative review outcomes.

## Alerts
- Paid invoice has no renewal intent/form after 12h → teacher; +4h → faculty lead.
- Fully paid booking request not allocated within 2h → Scheduling Ops lead.
- Any failed/partial payment → Finance queue; never auto-approve.
- Any duplicate idempotency key, schedule collision or capacity race → pause that invoice's automation and page Ops.

## Hours saved
Measure from a 2-week time study: (baseline median active handling minutes per renewal − post-launch median) × completed renewals / 60. Do not report theoretical automation time as realized savings.
