# Day 1 Evidence Run Map

## Effort map
- [x] `01-cli-testability-seam.md` (CLI Testability Seam)
- [x] `02-cli-idempotency-guards.md` (CLI idempotent guards)
- [x] `03-creation-phase.md` (Creation Phase: Pacing, Results Persistence & Ground Truth Segregation)
- [ ] `04-offline-reconciliation.md` (Offline Reconciliation)
- [ ] `05-metrics-report-emission.md` (Metrics Report Emission)

## Decisions-so-far
- Created tickets based on the finalized REBOUND Day 1 spec.
- Resolved Ticket 01: Refactored run_batch.main to accept argv for CLI testing.
- Resolved Ticket 02: Added --audit-path and --first-run flags with hard fail guards.
- Resolved Ticket 03: Creation Phase (Pacing, JSON dict serialization, Ground truth sourcing).
